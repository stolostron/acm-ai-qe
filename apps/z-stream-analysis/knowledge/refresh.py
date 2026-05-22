#!/usr/bin/env python3
"""
Knowledge Database Refresh Script -- Z-Stream Analysis

Refreshes the knowledge YAML files from live sources:
  - ACM Source MCP (selectors, routes, components)
  - Neo4j Knowledge Graph (dependency chains, subsystem topology)
  - Connected cluster (component health, pod states)
  - Learned corrections from previous analysis runs

Usage:
    python -m knowledge.refresh                    # Refresh all
    python -m knowledge.refresh --components       # Refresh components only
    python -m knowledge.refresh --selectors        # Refresh selectors only
    python -m knowledge.refresh --dependencies     # Refresh dependencies only
    python -m knowledge.refresh --promote          # Promote learned/ entries
    python -m knowledge.refresh --acm-version 2.17 # Set ACM version
    python -m knowledge.refresh --dry-run          # Show what would change

Prerequisites:
    - PyYAML installed (pip install pyyaml)
    - For component refresh: oc CLI logged into ACM hub cluster
    - For selector refresh: ACM Source MCP server running (optional)
    - For dependency refresh: Neo4j KG running (optional)
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)

KNOWLEDGE_DIR = Path(__file__).parent
LEARNED_DIR = KNOWLEDGE_DIR / "learned"


def run_oc(args: list[str], timeout: int = 30) -> str:
    """Run an oc command and return stdout. Returns empty string on failure."""
    cmd = ["oc"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            print(f"  Warning: oc {' '.join(args[:3])}... returned {result.returncode}")
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  Warning: oc {' '.join(args[:3])}... timed out after {timeout}s")
        return ""
    except FileNotFoundError:
        print("Warning: oc CLI not found. Skipping cluster queries.")
        return ""


def check_cluster_access() -> bool:
    """Verify oc is logged in."""
    whoami = run_oc(["whoami"])
    if not whoami:
        print("Warning: Not logged into a cluster. Cluster-based refresh will be skipped.")
        return False
    server = run_oc(["whoami", "--show-server"])
    print(f"Connected as: {whoami}")
    print(f"Server: {server}")
    return True


def discover_mch_namespace() -> str | None:
    """Discover the MCH namespace."""
    output = run_oc(["get", "mch", "-A", "-o", "jsonpath={.items[0].metadata.namespace}"])
    if output:
        print(f"MCH namespace: {output}")
        return output
    return None


def get_acm_version(mch_ns: str | None) -> str:
    """Get the current ACM version from MCH status."""
    if not mch_ns:
        return "unknown"
    version = run_oc([
        "get", "mch", "-A", "-o",
        "jsonpath={.items[0].status.currentVersion}",
    ])
    return version or "unknown"


def refresh_components(mch_ns: str | None, acm_version: str, dry_run: bool = False) -> dict:
    """Refresh components.yaml from connected cluster."""
    print("\n--- Refreshing components ---")

    if not mch_ns:
        print("  No cluster access -- skipping component refresh")
        return {}

    # Get deployments in key namespaces
    namespaces = [
        mch_ns,
        "multicluster-engine",
        "open-cluster-management-hub",
        "hive",
    ]

    discovered = {}
    for ns in namespaces:
        deploys_json = run_oc(["get", "deployments", "-n", ns, "-o", "json"])
        if not deploys_json:
            continue
        try:
            deploys = json.loads(deploys_json)
            for d in deploys.get("items", []):
                name = d["metadata"]["name"]
                replicas = d.get("status", {}).get("readyReplicas", 0)
                desired = d.get("spec", {}).get("replicas", 1)
                labels = d.get("spec", {}).get("selector", {}).get("matchLabels", {})
                discovered[name] = {
                    "namespace": ns,
                    "ready": replicas,
                    "desired": desired,
                    "labels": labels,
                }
        except json.JSONDecodeError:
            continue

    print(f"  Discovered {len(discovered)} deployments across {len(namespaces)} namespaces")

    # Compare against existing components.yaml
    components_path = KNOWLEDGE_DIR / "components.yaml"
    if components_path.exists():
        with open(components_path) as f:
            existing = yaml.safe_load(f) or {}
        existing_components = set(existing.get("components", {}).keys())
        discovered_names = set(discovered.keys())

        new_components = discovered_names - existing_components
        if new_components:
            print(f"  New components found: {', '.join(sorted(new_components))}")

        if not dry_run and new_components:
            existing["acm_version"] = acm_version
            existing["last_refreshed"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            # Add new components with [NEW] tag
            components = existing.get("components", {})
            for name in new_components:
                info = discovered[name]
                components[name] = {
                    "subsystem": "[NEW] auto-discovered",
                    "type": "hub-deployment",
                    "namespace": info["namespace"],
                    "pod_label": next(
                        (f"{k}={v}" for k, v in info["labels"].items()),
                        f"app={name}",
                    ),
                    "notes": f"Auto-discovered on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}. Review and categorize.",
                }
            existing["components"] = components
            with open(components_path, "w") as f:
                yaml.dump(existing, f, default_flow_style=False, sort_keys=False)
            print(f"  Updated {components_path}")
    else:
        print(f"  Warning: {components_path} not found")

    return discovered


def refresh_selectors(acm_version: str, dry_run: bool = False) -> dict:
    """Refresh selectors.yaml -- requires ACM Source MCP (not called from this script directly)."""
    print("\n--- Selectors refresh ---")
    print("  Selector refresh requires ACM Source MCP server.")
    print("  To refresh selectors:")
    print(f"    1. Start ACM Source MCP server")
    print(f"    2. Use Claude Code to query get_acm_selectors for each feature area")
    print(f"    3. Update knowledge/selectors.yaml with the results")
    print(f"  Current ACM version: {acm_version}")
    return {}


def refresh_dependencies(dry_run: bool = False) -> dict:
    """Refresh dependencies.yaml -- requires Neo4j KG (not called from this script directly)."""
    print("\n--- Dependencies refresh ---")
    print("  Dependency refresh requires Neo4j Knowledge Graph.")
    print("  To refresh dependencies:")
    print("    1. Start Neo4j: podman start neo4j-rhacm neo4j-mcp")
    print("    2. Use Claude Code to query KG for transitive dependencies")
    print("    3. Update knowledge/dependencies.yaml with the results")
    return {}


def promote_learned(dry_run: bool = False) -> int:
    """Review and promote learned/ entries to main knowledge files."""
    print("\n--- Checking learned/ entries for promotion ---")

    if not LEARNED_DIR.exists():
        print("  No learned/ directory found")
        return 0

    promoted = 0

    # Check corrections
    corrections_path = LEARNED_DIR / "corrections.yaml"
    if corrections_path.exists():
        with open(corrections_path) as f:
            data = yaml.safe_load(f) or {}
        corrections = data.get("corrections", [])
        if corrections:
            print(f"  Found {len(corrections)} correction(s):")
            for c in corrections:
                print(f"    - {c.get('test_name', 'unknown')}: "
                      f"{c.get('original_classification')} -> {c.get('correct_classification')}")
                if c.get("pattern_to_add"):
                    print(f"      Pattern to add: {c['pattern_to_add']}")
            promoted += len(corrections)
        else:
            print("  No corrections to promote")

    # Check new patterns
    patterns_path = LEARNED_DIR / "new-patterns.yaml"
    if patterns_path.exists():
        with open(patterns_path) as f:
            data = yaml.safe_load(f) or {}
        patterns = data.get("patterns", [])
        if patterns:
            print(f"  Found {len(patterns)} new pattern(s):")
            for p in patterns:
                print(f"    - {p.get('id', 'unknown')}: {p.get('classification')} "
                      f"(confidence: {p.get('confidence', '?')})")

            if not dry_run:
                # Append to failure-patterns.yaml
                fp_path = KNOWLEDGE_DIR / "failure-patterns.yaml"
                if fp_path.exists():
                    with open(fp_path) as f:
                        fp_data = yaml.safe_load(f) or {}
                    existing_ids = {p["id"] for p in fp_data.get("patterns", [])}
                    new_patterns = [p for p in patterns if p.get("id") not in existing_ids]
                    if new_patterns:
                        fp_data["patterns"].extend(new_patterns)
                        with open(fp_path, "w") as f:
                            yaml.dump(fp_data, f, default_flow_style=False, sort_keys=False)
                        print(f"  Promoted {len(new_patterns)} pattern(s) to failure-patterns.yaml")

                        # Clear promoted patterns from learned
                        data["patterns"] = [
                            p for p in patterns if p.get("id") in existing_ids
                        ]
                        with open(patterns_path, "w") as f:
                            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            promoted += len(patterns)
        else:
            print("  No new patterns to promote")

    # Check selector changes
    selectors_path = LEARNED_DIR / "selector-changes.yaml"
    if selectors_path.exists():
        with open(selectors_path) as f:
            data = yaml.safe_load(f) or {}
        changes = data.get("changes", [])
        if changes:
            print(f"  Found {len(changes)} selector change(s):")
            for c in changes:
                print(f"    - {c.get('old_selector', '?')} -> {c.get('new_selector', '?')}")
            promoted += len(changes)
        else:
            print("  No selector changes to promote")

    if promoted == 0:
        print("  Nothing to promote")
    elif dry_run:
        print(f"\n  {promoted} entries found (dry-run mode -- no changes made)")
    else:
        print(f"\n  Processed {promoted} entries")

    return promoted


def main():
    parser = argparse.ArgumentParser(
        description="Refresh Z-Stream Analysis knowledge database from live sources",
    )
    parser.add_argument("--components", action="store_true", help="Refresh components only")
    parser.add_argument("--selectors", action="store_true", help="Refresh selectors only")
    parser.add_argument("--dependencies", action="store_true", help="Refresh dependencies only")
    parser.add_argument("--promote", action="store_true", help="Promote learned/ entries")
    parser.add_argument("--acm-version", default=None, help="Set ACM version for queries")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")

    args = parser.parse_args()

    # Determine ACM version
    acm_version = args.acm_version

    # Check cluster access (optional for some operations)
    has_cluster = check_cluster_access()
    mch_ns = discover_mch_namespace() if has_cluster else None

    if not acm_version:
        acm_version = get_acm_version(mch_ns) if mch_ns else "unknown"
    print(f"ACM version: {acm_version}")

    # If no specific flag, refresh everything
    refresh_all = not any([args.components, args.selectors, args.dependencies, args.promote])

    if args.components or refresh_all:
        refresh_components(mch_ns, acm_version, dry_run=args.dry_run)

    if args.selectors or refresh_all:
        refresh_selectors(acm_version, dry_run=args.dry_run)

    if args.dependencies or refresh_all:
        refresh_dependencies(dry_run=args.dry_run)

    if args.promote or refresh_all:
        promote_learned(dry_run=args.dry_run)

    print("\n--- Refresh complete ---")
    if args.dry_run:
        print("(dry-run mode -- no files were modified)")


if __name__ == "__main__":
    main()
