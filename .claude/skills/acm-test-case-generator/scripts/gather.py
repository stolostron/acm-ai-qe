#!/usr/bin/env python3
"""Stage 1: Gather data for test case generation (standalone).

Zero external dependencies -- uses only Python stdlib and gh CLI.
Produces gather-output.json with PR data, conventions, and area knowledge.

Usage:
    python gather.py ACM-30459 [--version 2.17] [--pr 5790] [--area governance]
                               [--skip-live] [--cluster-url URL] [--repo stolostron/console]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Telemetry (inlined from src/services/telemetry.py)
# ---------------------------------------------------------------------------

class PipelineTelemetry:
    def __init__(self, run_dir: str, jira_id: str):
        self.run_dir = Path(run_dir)
        self.jira_id = jira_id
        self.log_path = self.run_dir / "pipeline.log.jsonl"
        self._stage_start = None
        self._pipeline_start = time.monotonic()
        self._log_event("pipeline_start", {"jira_id": jira_id})

    def _log_event(self, event_type: str, data: dict = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "jira_id": self.jira_id,
        }
        if data:
            entry.update(data)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def start_stage(self, stage_name: str):
        self._stage_start = time.monotonic()
        self._log_event("stage_start", {"stage": stage_name})

    def end_stage(self, stage_name: str, metadata: dict = None):
        elapsed = 0.0
        if self._stage_start is not None:
            elapsed = time.monotonic() - self._stage_start
        data = {"stage": stage_name, "elapsed_seconds": round(elapsed, 2)}
        if metadata:
            data.update(metadata)
        self._log_event("stage_end", data)
        self._stage_start = None


# ---------------------------------------------------------------------------
# GitHub service (inlined from src/services/github_service.py)
# ---------------------------------------------------------------------------

def _run_gh(args: list, timeout: int = 30):
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


DEFAULT_SEARCH_REPOS = [
    "stolostron/console",
    "stolostron/multiclusterhub-operator",
]


def search_prs_for_jira(jira_id: str, repo: str = "stolostron/console"):
    """Search a single repo for PRs matching a JIRA ID. Returns list of dicts."""
    output = _run_gh([
        "search", "prs", jira_id,
        "--repo", repo,
        "--json", "number,title,state",
        "--limit", "5",
    ])
    if not output:
        return []
    try:
        results = json.loads(output)
        return [
            {"number": r["number"], "title": r["title"], "state": r["state"], "repo": repo}
            for r in results
        ]
    except (json.JSONDecodeError, KeyError, IndexError):
        return []


def search_prs_multi_repo(jira_id: str, repos: list = None):
    """Search multiple repos for PRs matching a JIRA ID. Returns deduplicated list."""
    if repos is None:
        repos = DEFAULT_SEARCH_REPOS
    all_prs = []
    seen = set()
    for repo in repos:
        prs = search_prs_for_jira(jira_id, repo)
        for pr in prs:
            key = (pr["repo"], pr["number"])
            if key not in seen:
                seen.add(key)
                all_prs.append(pr)
    return all_prs


def get_pr_metadata(pr_number: int, repo: str = "stolostron/console"):
    output = _run_gh([
        "pr", "view", str(pr_number),
        "--repo", repo,
        "--json", "title,body,files,additions,deletions,mergedAt,state",
    ])
    if not output:
        return None
    try:
        data = json.loads(output)
        files = [f["path"] for f in data.get("files", [])]
        return {
            "number": pr_number,
            "title": data.get("title", ""),
            "repo": repo,
            "state": data.get("state", ""),
            "body": data.get("body"),
            "files": files,
            "additions": data.get("additions", 0),
            "deletions": data.get("deletions", 0),
            "merged_at": data.get("mergedAt"),
            "diff_file": None,
        }
    except (json.JSONDecodeError, KeyError):
        return None


def get_pr_diff(pr_number: int, repo: str, output_path: Path = None):
    output = _run_gh([
        "pr", "diff", str(pr_number),
        "--repo", repo,
    ], timeout=60)
    if not output:
        return None
    if output_path:
        output_path.write_text(output, encoding="utf-8")
        return str(output_path)
    return output


def detect_area_from_files(files: list):
    area_patterns = {
        "governance": ["Governance", "governance", "policy", "Policy"],
        "rbac": ["rbac", "RBAC", "RoleAssignment", "ClusterPermission", "user-management"],
        "fleet-virt": ["Virtualization", "virtualization", "kubevirt", "fleet-virt"],
        "cclm": ["CCLM", "cclm", "LiveMigration", "live-migration", "CrossClusterMigration"],
        "mtv": ["MTV", "mtv", "forklift", "migration-toolkit", "ForkliftController"],
        "clusters": ["Clusters", "clusters", "ClusterSet", "ClusterDeployment", "ClusterPool"],
        "search": ["Search", "search", "SearchInput", "SearchRelated", "search-api"],
        "applications": ["Applications", "applications", "Subscription", "Channel"],
        "credentials": ["Credentials", "credentials", "CredentialsForm", "ProviderConnection"],
    }
    area_scores = {}
    for file_path in files:
        for area, patterns in area_patterns.items():
            for pattern in patterns:
                if pattern in file_path:
                    area_scores[area] = area_scores.get(area, 0) + 1
    if area_scores:
        return max(area_scores, key=area_scores.get)
    return None


# ---------------------------------------------------------------------------
# File service (inlined from src/services/file_service.py)
# ---------------------------------------------------------------------------

AREA_TO_COMPONENT_DIRS = {
    "governance": ["grc"],
    "rbac": ["rbac"],
    "fleet-virt": ["virt"],
    "clusters": ["clc", "bm"],
    "search": ["search"],
    "applications": ["alc"],
    "credentials": ["clc"],
    "cclm": ["virt"],
    "mtv": ["mtv"],
}


def _resolve_knowledge_dir():
    """Find the knowledge directory, checking multiple locations."""
    skill_dir = os.environ.get("CLAUDE_SKILL_DIR")
    if skill_dir:
        # Shared knowledge database (.claude/knowledge/test-case-generator/)
        claude_dir = Path(skill_dir).parent.parent
        shared = claude_dir / "knowledge" / "test-case-generator"
        if shared.exists():
            return shared
        # Legacy: skill-local knowledge
        p = Path(skill_dir) / "knowledge"
        if p.exists():
            return p

    # Fall back to app location (running from app directory)
    for candidate in [
        Path.cwd() / "knowledge",
        Path.cwd() / "apps" / "test-case-generator" / "knowledge",
    ]:
        if candidate.exists():
            return candidate

    return None


def _resolve_runs_dir():
    """Find the runs directory."""
    for candidate in [
        Path.cwd() / "runs" / "test-case-generator",
        Path.cwd() / "apps" / "test-case-generator" / "runs" / "test-case-generator",
    ]:
        if candidate.exists():
            return candidate
    return Path.cwd() / "runs" / "test-case-generator"


def read_conventions():
    kd = _resolve_knowledge_dir()
    if kd:
        path = kd / "conventions" / "test-case-format.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def read_html_templates():
    kd = _resolve_knowledge_dir()
    if kd:
        path = kd / "conventions" / "polarion-html-templates.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
    return ""


def read_area_knowledge(area: str):
    kd = _resolve_knowledge_dir()
    if kd:
        path = kd / "architecture" / f"{area}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
    return None


def find_existing_test_cases(version: str, area: str = None, max_count: int = 3):
    search_paths = []

    automation_workspace = os.environ.get("ACM_AUTOMATION_WORKSPACE")
    if automation_workspace:
        automation_base = Path(automation_workspace)
        if automation_base.exists():
            component_dirs = AREA_TO_COMPONENT_DIRS.get(area, []) if area else []
            for component_dir in component_dirs:
                tc_path = automation_base / component_dir / "test-cases" / version
                if tc_path.exists():
                    search_paths.append(tc_path)

    search_paths.append(_resolve_runs_dir())

    kd = _resolve_knowledge_dir()
    if kd:
        search_paths.append(kd / "examples")

    results = []
    for search_path in search_paths:
        if not search_path.exists():
            continue
        glob_pattern = "**/*.md" if "runs" in str(search_path) else "*.md"
        for md_file in sorted(
            search_path.glob(glob_pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            if md_file.name.startswith("RHACM4K-") or md_file.name == "test-case.md" or md_file.name.startswith("sample-"):
                results.append(str(md_file))
                if len(results) >= max_count:
                    return results
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def create_run_directory(jira_id: str) -> Path:
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    runs_dir = _resolve_runs_dir()
    run_dir = runs_dir / jira_id / f"{jira_id}-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def parse_args():
    parser = argparse.ArgumentParser(description="Stage 1: Gather data for test case generation")
    parser.add_argument("jira_id", help="JIRA ticket ID (e.g., ACM-30459)")
    parser.add_argument("--version", help="ACM version (e.g., 2.17)")
    parser.add_argument("--pr", type=int, help="PR number (auto-detected if omitted)")
    parser.add_argument("--area", help="Console area (auto-detected from PR paths)")
    parser.add_argument("--skip-live", action="store_true", help="Skip live cluster validation")
    parser.add_argument("--cluster-url", help="Console URL for live validation")
    parser.add_argument("--repo", default="stolostron/console", help="GitHub repo")
    return parser.parse_args()


def main():
    args = parse_args()
    jira_id = args.jira_id.upper()

    print(f"Stage 1: Gathering data for {jira_id}...")

    run_dir = create_run_directory(jira_id)
    telemetry = PipelineTelemetry(str(run_dir), jira_id)
    telemetry.start_stage("gather")

    area = args.area
    pr_data_list = []

    # --- PR Discovery (multi-repo) ---
    if args.pr:
        print(f"  Using specified PR #{args.pr} in {args.repo}")
        prs_found = [{"number": args.pr, "title": "", "state": "", "repo": args.repo}]
    else:
        repos_to_search = list(dict.fromkeys([args.repo] + DEFAULT_SEARCH_REPOS))
        print(f"  Searching for PRs associated with {jira_id} across {len(repos_to_search)} repo(s)...")
        prs_found = search_prs_multi_repo(jira_id, repos_to_search)
        if prs_found:
            print(f"  Found {len(prs_found)} PR(s):")
            for pr_info in prs_found:
                print(f"    PR #{pr_info['number']} ({pr_info['repo']}) - {pr_info['title']}")
        else:
            print(f"  No PRs found for {jira_id}")

    # --- PR Metadata + Diffs ---
    all_files = []
    all_diffs = []
    for pr_info in prs_found:
        print(f"  Fetching PR #{pr_info['number']} ({pr_info['repo']}) metadata...")
        metadata = get_pr_metadata(pr_info["number"], pr_info["repo"])
        if metadata:
            print(f"    {metadata['title']}")
            print(f"    Files: {len(metadata['files'])} changed ({metadata['additions']}+ / {metadata['deletions']}-)")
            pr_data_list.append(metadata)
            all_files.extend(metadata["files"])

            diff_text = get_pr_diff(pr_info["number"], pr_info["repo"])
            if diff_text:
                header = f"# PR #{pr_info['number']} ({pr_info['repo']})"
                all_diffs.append(f"{'=' * 60}\n{header}\n{'=' * 60}\n{diff_text}")
        else:
            print(f"    Failed to fetch PR #{pr_info['number']} metadata")

    # --- Write concatenated diff ---
    diff_path = run_dir / "pr-diff.txt"
    if all_diffs:
        diff_path.write_text("\n\n".join(all_diffs), encoding="utf-8")
        for pr_meta in pr_data_list:
            pr_meta["diff_file"] = str(diff_path)
        print(f"  Diff saved: {diff_path.name} ({len(all_diffs)} PR(s))")

    # --- Area Detection (across all PRs) ---
    if not area and all_files:
        area = detect_area_from_files(all_files)
        if area:
            print(f"  Area detected: {area}")

    # --- Version ---
    acm_version = args.version
    if not acm_version:
        print("  ACM version not specified (will be detected from JIRA)")

    # --- Existing Test Cases ---
    version_for_search = acm_version or "latest"
    existing = find_existing_test_cases(version_for_search, area=area)
    if existing:
        print(f"  Found {len(existing)} peer test case(s) for reference")
    else:
        print(f"  No existing test cases found for version {version_for_search}")

    # --- Conventions ---
    print("  Loading conventions...")
    conventions = read_conventions()
    html_templates = read_html_templates()
    if conventions:
        print(f"  Loaded test-case-format.md ({len(conventions)} chars)")
    else:
        print("  WARNING: test-case-format.md not found in knowledge directory")

    # --- Area Knowledge ---
    area_knowledge = None
    if area:
        area_knowledge = read_area_knowledge(area)
        if area_knowledge:
            print(f"  Loaded {area} architecture knowledge ({len(area_knowledge)} chars)")
        else:
            print(f"  No architecture knowledge found for area: {area}")

    # --- Classify PR files (across all PRs) ---
    test_files = []
    production_files = []
    for pr_meta in pr_data_list:
        for f in pr_meta.get("files", []):
            if ".test." in f or ".spec." in f or "/tests/" in f or "/__tests__/" in f:
                test_files.append(f)
            else:
                production_files.append(f)

    # --- Build Output ---
    pr_data = pr_data_list[0] if pr_data_list else None
    output = {
        "jira_id": jira_id,
        "acm_version": acm_version,
        "area": area,
        "pr_data": pr_data,
        "pr_data_list": pr_data_list,
        "existing_test_cases": existing,
        "conventions": conventions,
        "area_knowledge": area_knowledge,
        "html_templates": html_templates,
        "run_dir": str(run_dir),
        "timestamp": datetime.now().isoformat(),
        "options": {
            "skip_live": args.skip_live,
            "cluster_url": args.cluster_url,
            "repo": args.repo,
        },
        "test_files": test_files,
        "production_files": production_files,
    }

    # --- Write Output ---
    output_path = run_dir / "gather-output.json"
    output_path.write_text(
        json.dumps(output, indent=2, default=str),
        encoding="utf-8",
    )

    telemetry.end_stage("gather", {
        "pr_found": len(pr_data_list) > 0,
        "pr_count": len(pr_data_list),
        "pr_numbers": [p["number"] for p in pr_data_list],
        "area": area,
        "existing_test_cases_count": len(existing),
        "conventions_loaded": bool(conventions),
    })

    print()
    print(f"  Stage 1 complete. Output: {output_path}")
    print(f"  Run directory: {run_dir}")
    print()
    print(str(run_dir))


if __name__ == "__main__":
    main()
