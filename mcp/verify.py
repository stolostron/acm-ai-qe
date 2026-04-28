#!/usr/bin/env python3
"""Standalone health checker for the AI Systems Suite MCP infrastructure.

Verifies prerequisites, artifacts (venvs, configs, credentials), and
optionally tests live connectivity to MCP backends.

Usage:
    python3 mcp/verify.py              # All apps, Tiers 1+2
    python3 mcp/verify.py --app 2      # Z-Stream only
    python3 mcp/verify.py --live       # Include connectivity checks
    python3 mcp/verify.py --json       # Machine-readable output
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MCP_DIR = REPO_ROOT / "mcp"
EXTERNAL_DIR = MCP_DIR / ".external"
APPS_DIR = REPO_ROOT / "apps"

APP_MCP_MAP = {
    1: {
        "name": "ACM Hub Health",
        "dir": "acm-hub-health",
        "mcps": ["acm-ui", "neo4j-rhacm", "acm-search"],
    },
    2: {
        "name": "Z-Stream Analysis",
        "dir": "z-stream-analysis",
        "mcps": ["acm-ui", "jira", "jenkins", "polarion", "neo4j-rhacm"],
    },
    3: {
        "name": "Test Case Generator",
        "dir": "test-case-generator",
        "mcps": [
            "acm-ui", "jira", "polarion", "neo4j-rhacm",
            "acm-search", "acm-kubectl", "playwright",
        ],
    },
}

ALL_MCPS = [
    "acm-ui", "jira", "jenkins", "polarion",
    "neo4j-rhacm", "acm-search", "acm-kubectl", "playwright",
]

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SKIP = "SKIP"

STATUS_COLORS = {
    PASS: "\033[0;32m",
    WARN: "\033[1;33m",
    FAIL: "\033[0;31m",
    SKIP: "\033[0;36m",
}
NC = "\033[0m"


def run(cmd, timeout=10):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def check_tool_version(tool, cmd, min_version=None):
    rc, out, _ = run(cmd)
    if rc != 0:
        return FAIL, "not found", None
    version = out.split()[-1] if out else "unknown"
    version = version.lstrip("v")
    if min_version and not _version_gte(version, min_version):
        return WARN, version, f"need {min_version}+"
    return PASS, version, None


def _version_gte(actual, minimum):
    def parse(v):
        parts = []
        for p in v.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return parts

    a, m = parse(actual), parse(minimum)
    for i in range(max(len(a), len(m))):
        av = a[i] if i < len(a) else 0
        mv = m[i] if i < len(m) else 0
        if av > mv:
            return True
        if av < mv:
            return False
    return True


# -- Tier 1: Prerequisites --

def check_prerequisites(needed_mcps):
    results = []

    status, ver, note = check_tool_version(
        "Python", "python3 --version 2>&1", "3.10",
    )
    results.append(("Python", status, ver, note))

    needs_node = any(m in needed_mcps for m in ["acm-search", "acm-kubectl", "playwright"])
    if needs_node:
        status, ver, note = check_tool_version(
            "Node.js", "node --version 2>&1", "18.0.0",
        )
        results.append(("Node.js", status, ver, note))

    rc, _, _ = run("command -v gh")
    if rc == 0:
        rc2, _, _ = run("gh auth status 2>&1")
        if rc2 == 0:
            results.append(("gh CLI", PASS, "authenticated", None))
        else:
            results.append(("gh CLI", WARN, "installed, not authenticated", None))
    else:
        results.append(("gh CLI", WARN, "not found", None))

    rc, out, _ = run("jq --version 2>&1")
    if rc == 0:
        results.append(("jq", PASS, out.strip(), None))
    else:
        results.append(("jq", WARN, "not found", None))

    needs_oc = any(m in needed_mcps for m in ["acm-search", "acm-kubectl"])
    if needs_oc:
        rc, out, _ = run("oc version --client 2>&1 | head -1")
        if rc == 0 and out:
            ver = out.split()[-1] if out else "unknown"
            results.append(("oc CLI", PASS, ver, None))
        else:
            results.append(("oc CLI", WARN, "not found", None))

    needs_uvx = any(m in needed_mcps for m in ["polarion", "neo4j-rhacm"])
    if needs_uvx:
        rc, _, _ = run("command -v uvx")
        if rc == 0:
            results.append(("uvx", PASS, "available", None))
        else:
            results.append(("uvx", WARN, "not found", None))

    needs_podman = "neo4j-rhacm" in needed_mcps
    if needs_podman:
        rc, out, _ = run("podman --version 2>&1")
        if rc == 0:
            ver = out.split()[-1] if out else "unknown"
            results.append(("Podman", PASS, ver, None))
        else:
            results.append(("Podman", WARN, "not found (optional)", None))

    return results


# -- Tier 2: Artifacts --

def check_artifacts(app_nums, needed_mcps):
    results = []

    for num in app_nums:
        app = APP_MCP_MAP[num]
        mcp_json = APPS_DIR / app["dir"] / ".mcp.json"
        if mcp_json.exists():
            try:
                with open(mcp_json, encoding="utf-8") as f:
                    data = json.load(f)
                server_count = len(data.get("mcpServers", {}))
                results.append((
                    f"{app['name']} .mcp.json",
                    PASS,
                    f"{server_count} servers",
                    None,
                ))
            except json.JSONDecodeError:
                results.append((
                    f"{app['name']} .mcp.json",
                    FAIL,
                    "invalid JSON",
                    None,
                ))
        else:
            results.append((
                f"{app['name']} .mcp.json",
                FAIL,
                "missing",
                "run: bash mcp/setup.sh",
            ))

    venv_checks = {
        "acm-ui": (
            MCP_DIR / "acm-ui-mcp-server" / ".venv",
            "import acm_ui_mcp_server",
        ),
        "jira": (
            EXTERNAL_DIR / "jira-mcp-server" / ".venv",
            "import jira_mcp_server",
        ),
        "jenkins": (
            EXTERNAL_DIR / "jenkins-mcp" / ".venv",
            "import mcp, httpx",
        ),
    }

    for mcp_name, (venv_path, import_check) in venv_checks.items():
        if mcp_name not in needed_mcps:
            continue
        python_bin = venv_path / "bin" / "python"
        if python_bin.exists():
            try:
                result = subprocess.run(
                    [str(python_bin), "-c", import_check],
                    capture_output=True, text=True, timeout=10,
                )
                rc = result.returncode
            except (subprocess.TimeoutExpired, Exception):
                rc = -1
            if rc == 0:
                results.append((f"{mcp_name} venv", PASS, "importable", None))
            else:
                results.append((
                    f"{mcp_name} venv",
                    WARN,
                    "venv exists, import failed",
                    None,
                ))
        else:
            results.append((
                f"{mcp_name} venv",
                FAIL,
                "missing",
                "run: bash mcp/setup.sh",
            ))

    cred_checks = {
        "jira": EXTERNAL_DIR / "jira-mcp-server" / ".env",
        "jenkins": EXTERNAL_DIR / "jenkins-mcp" / ".env",
        "polarion": MCP_DIR / "polarion" / ".env",
    }

    for mcp_name, env_path in cred_checks.items():
        if mcp_name not in needed_mcps:
            continue
        if env_path.exists():
            content = env_path.read_text(encoding="utf-8")
            if "PASTE_YOUR" in content:
                results.append((
                    f"{mcp_name} credentials",
                    WARN,
                    "placeholder values",
                    f"edit {env_path}",
                ))
            else:
                results.append((f"{mcp_name} credentials", PASS, "configured", None))
        else:
            results.append((
                f"{mcp_name} credentials",
                FAIL,
                "missing",
                "run: bash mcp/setup.sh",
            ))

    if "neo4j-rhacm" in needed_mcps:
        rc, out, _ = run("podman ps --format '{{.Names}}' 2>/dev/null")
        if rc == 0 and "neo4j-rhacm" in out:
            results.append(("neo4j-rhacm container", PASS, "running", None))
        else:
            rc2, out2, _ = run("podman ps -a --format '{{.Names}}' 2>/dev/null")
            if rc2 == 0 and "neo4j-rhacm" in out2:
                results.append((
                    "neo4j-rhacm container",
                    WARN,
                    "stopped",
                    "run: podman start neo4j-rhacm",
                ))
            else:
                results.append((
                    "neo4j-rhacm container",
                    WARN,
                    "not created (optional)",
                    None,
                ))

    return results


# -- Tier 3: Connectivity (--live only) --

def check_connectivity(needed_mcps):
    results = []

    rc, _, _ = run("gh api user -q .login 2>&1", timeout=15)
    if rc == 0:
        results.append(("GitHub API", PASS, "reachable", None))
    else:
        results.append(("GitHub API", WARN, "unreachable or not authenticated", None))

    if "neo4j-rhacm" in needed_mcps:
        rc, _, _ = run(
            "podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph 'RETURN 1' 2>&1",
            timeout=15,
        )
        if rc == 0:
            results.append(("Neo4j Bolt", PASS, "responding", None))
        else:
            results.append(("Neo4j Bolt", WARN, "not responding", None))

    if "jira" in needed_mcps:
        rc, _, _ = run(
            "python3 -c \"import urllib.request; urllib.request.urlopen('https://redhat.atlassian.net', timeout=10)\" 2>&1",
            timeout=15,
        )
        if rc == 0:
            results.append(("JIRA API", PASS, "reachable", None))
        else:
            results.append(("JIRA API", WARN, "unreachable", None))

    if "polarion" in needed_mcps:
        rc, _, _ = run(
            "python3 -c \"import urllib.request, ssl; ctx=ssl._create_unverified_context(); urllib.request.urlopen('https://polarion.engineering.redhat.com/polarion/', timeout=10, context=ctx)\" 2>&1",
            timeout=15,
        )
        if rc == 0:
            results.append(("Polarion API", PASS, "reachable (VPN)", None))
        else:
            results.append(("Polarion API", WARN, "unreachable (need VPN?)", None))

    if "acm-search" in needed_mcps:
        rc, out, _ = run("oc whoami 2>&1", timeout=10)
        if rc == 0:
            rc2, _, _ = run("oc get namespace acm-search 2>&1", timeout=10)
            if rc2 == 0:
                results.append(("acm-search on-cluster", PASS, "deployed", None))
            else:
                results.append((
                    "acm-search on-cluster",
                    WARN,
                    "namespace not found",
                    None,
                ))
        else:
            results.append(("acm-search on-cluster", SKIP, "not logged in", None))

    return results


# -- Output --

def print_table(title, results, use_color=True):
    print(f"\n  {title}")
    print(f"  {'=' * len(title)}")
    for name, status, detail, note in results:
        if use_color:
            color = STATUS_COLORS.get(status, "")
            status_str = f"{color}{status:4s}{NC}"
        else:
            status_str = f"{status:4s}"
        line = f"    {status_str}  {name:<30s}  {detail}"
        if note:
            line += f"  ({note})"
        print(line)


def build_json(prereqs, artifacts, connectivity):
    def to_dicts(results):
        return [
            {"name": n, "status": s, "detail": d, "note": note}
            for n, s, d, note in results
        ]

    output = {
        "prerequisites": to_dicts(prereqs),
        "artifacts": to_dicts(artifacts),
    }
    if connectivity is not None:
        output["connectivity"] = to_dicts(connectivity)
    output["all_passed"] = all(
        r[1] != FAIL
        for section in [prereqs, artifacts] + ([connectivity] if connectivity else [])
        for r in section
    )
    return output


def main():
    parser = argparse.ArgumentParser(description="Verify MCP setup health")
    parser.add_argument(
        "--app", type=int, choices=[1, 2, 3],
        help="Scope to app: 1=Hub Health, 2=Z-Stream, 3=Test Case Gen",
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Enable Tier 3 connectivity checks",
    )
    parser.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Machine-readable JSON output",
    )
    args = parser.parse_args()

    if args.app:
        app_nums = [args.app]
        needed_mcps = APP_MCP_MAP[args.app]["mcps"]
    else:
        app_nums = [1, 2, 3]
        needed_mcps = list(ALL_MCPS)

    prereqs = check_prerequisites(needed_mcps)
    artifacts = check_artifacts(app_nums, needed_mcps)
    connectivity = check_connectivity(needed_mcps) if args.live else None

    if args.json_output:
        print(json.dumps(build_json(prereqs, artifacts, connectivity), indent=2))
    else:
        scope = APP_MCP_MAP[args.app]["name"] if args.app else "All Apps"
        print(f"\n  MCP Health Check — {scope}")
        print(f"  {'—' * 40}")
        print_table("Prerequisites", prereqs)
        print_table("Artifacts", artifacts)
        if connectivity:
            print_table("Connectivity", connectivity)

        has_fail = any(r[1] == FAIL for r in prereqs + artifacts + (connectivity or []))
        has_warn = any(r[1] == WARN for r in prereqs + artifacts + (connectivity or []))
        print()
        if has_fail:
            print(f"  {STATUS_COLORS[FAIL]}Some checks failed. Run: bash mcp/setup.sh{NC}")
        elif has_warn:
            print(f"  {STATUS_COLORS[WARN]}Some warnings. Setup may work with reduced functionality.{NC}")
        else:
            print(f"  {STATUS_COLORS[PASS]}All checks passed.{NC}")
        print()

    sys.exit(1 if any(r[1] == FAIL for r in prereqs + artifacts + (connectivity or [])) else 0)


if __name__ == "__main__":
    main()
