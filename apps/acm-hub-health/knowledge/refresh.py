#!/usr/bin/env python3
"""
Knowledge Database Refresh Script -- ACM Hub Health

Refreshes the knowledge YAML files from live sources:
  - Connected cluster (oc get -- read-only)
  - Existing knowledge files (merge, don't overwrite curated content)
  - Learned findings from previous investigations (promote)

Usage:
    python -m knowledge.refresh                 # Refresh all from connected cluster
    python -m knowledge.refresh --baseline      # Update healthy-baseline.yaml
    python -m knowledge.refresh --webhooks      # Update webhook-registry.yaml
    python -m knowledge.refresh --certs         # Update certificate-inventory.yaml
    python -m knowledge.refresh --addons        # Update addon-catalog.yaml
    python -m knowledge.refresh --promote       # List learned/ entries for manual promotion
    python -m knowledge.refresh --dry-run       # Show what would change without writing

Prerequisites:
    - oc CLI available and logged into an ACM hub cluster
    - PyYAML installed (pip install pyyaml)
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

# --- File headers (preserved on write, since yaml.dump strips comments) ---

BASELINE_HEADER = """\
# ACM Hub Healthy Baseline
# What "normal" looks like for a healthy ACM hub cluster.
# Used as a reference point, not as a strict checklist -- always discover
# what's actually deployed before comparing against this baseline.
#
# Populated by: refresh.py (oc get against a known-healthy cluster)
# Refresh frequency: after ACM version upgrade

"""

WEBHOOK_HEADER = """\
# ACM Webhook Registry
# Validating and mutating webhook configurations expected on an ACM hub.
# Use this to detect missing or misconfigured webhooks during health checks.
#
# Populated by: refresh.py (oc get validatingwebhookconfigurations, mutatingwebhookconfigurations)
# Refresh frequency: after ACM version upgrade

"""

CERT_HEADER = """\
# ACM Certificate Inventory
# TLS secrets and their roles across ACM namespaces.
# Use this to identify certificate-related failures and understand rotation expectations.
#
# Populated by: refresh.py (oc get secrets -l type=kubernetes.io/tls)
# Refresh frequency: after ACM version upgrade or cert rotation

"""

ADDON_HEADER = """\
# ACM Addon Catalog
# All managed cluster addons, their deployment expectations, and health checks.
# Use this to systematically verify addon health across managed clusters.
#
# Populated by: refresh.py (oc get managedclusteraddons -A, oc get clustermanagementaddons)
# Refresh frequency: after ACM version upgrade

"""


# --- Utilities ---

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
            if result.stderr.strip():
                print(f"    stderr: {result.stderr.strip()[:200]}")
            return ""
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  Warning: oc {' '.join(args[:3])}... timed out after {timeout}s")
        return ""
    except FileNotFoundError:
        print("Error: oc CLI not found. Please install and log in first.")
        sys.exit(1)


def check_cluster_access() -> bool:
    """Verify oc is logged in and can access the cluster."""
    whoami = run_oc(["whoami"])
    if not whoami:
        print("Error: Not logged into a cluster. Run 'oc login' first.")
        return False
    server = run_oc(["whoami", "--show-server"])
    print(f"Connected as: {whoami}")
    print(f"Server: {server}")
    return True


def discover_mch_namespace() -> str | None:
    """Discover the MCH namespace (not always open-cluster-management)."""
    output = run_oc(["get", "mch", "-A", "-o", "jsonpath={.items[0].metadata.namespace}"])
    if output:
        print(f"MCH namespace: {output}")
        return output
    print("Warning: Could not find MultiClusterHub. Is ACM installed?")
    return None


def get_acm_version(mch_ns: str) -> str:
    """Get the current ACM version from MCH status."""
    version = run_oc([
        "get", "mch", "-n", mch_ns, "-o",
        "jsonpath={.items[0].status.currentVersion}",
    ])
    if not version:
        version = run_oc([
            "get", "mch", "-A", "-o",
            "jsonpath={.items[0].status.currentVersion}",
        ])
    return version or "unknown"


def load_yaml(path: Path) -> dict:
    """Load a YAML file, returning empty dict if missing or empty."""
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def write_yaml(path: Path, data: dict, header: str) -> None:
    """Write YAML data to file with a preserved header comment block."""
    with open(path, "w") as f:
        f.write(header)
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(f"  Updated {path.name}")


def _major_minor(version: str) -> str:
    """Extract major.minor from a version string (e.g., '2.17.0-76' -> '2.17')."""
    parts = version.split(".")
    if len(parts) >= 2:
        return f"{parts[0]}.{parts[1]}"
    return version


def check_version_drift(acm_version: str) -> list[tuple[str, str]]:
    """Compare cluster ACM version against all YAML file metadata.

    Compares on major.minor only -- build suffixes (e.g., 2.17.0-76) are
    ignored so that YAML files documenting '2.17' match cluster '2.17.0-76'.
    """
    yaml_files = [
        "healthy-baseline.yaml",
        "webhook-registry.yaml",
        "certificate-inventory.yaml",
        "addon-catalog.yaml",
        "dependency-chains.yaml",
    ]
    cluster_mm = _major_minor(acm_version)
    drifted = []
    for fname in yaml_files:
        data = load_yaml(KNOWLEDGE_DIR / fname)
        yaml_version = data.get("acm_version", "unknown")
        if _major_minor(yaml_version) != cluster_mm:
            drifted.append((fname, yaml_version))

    if drifted:
        print(f"\n  Version drift detected (cluster: {acm_version}):")
        for fname, yv in drifted:
            print(f"    {fname}: documents {yv}")
    else:
        print(f"\n  All YAML files match cluster version ({acm_version})")
    return drifted


# --- Refresh functions ---

def refresh_baseline(mch_ns: str, dry_run: bool = False) -> dict:
    """Capture a healthy baseline from the connected cluster."""
    print("\n--- Refreshing healthy baseline ---")

    acm_version = get_acm_version(mch_ns)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"ACM version: {acm_version}")

    # MCH status
    mch_phase = run_oc([
        "get", "mch", "-A", "-o", "jsonpath={.items[0].status.phase}",
    ])

    # MCE status
    mce_phase = run_oc([
        "get", "multiclusterengines", "-o",
        "jsonpath={.items[0].status.phase}",
    ])

    # Node count
    nodes_json = run_oc(["get", "nodes", "-o", "json"])
    node_count = 0
    if nodes_json:
        try:
            nodes = json.loads(nodes_json)
            node_count = len(nodes.get("items", []))
        except json.JSONDecodeError:
            pass

    # Pod counts per namespace
    namespaces = [
        mch_ns,
        "multicluster-engine",
        "open-cluster-management-hub",
        "open-cluster-management-observability",
        "hive",
    ]
    pod_counts = {}
    for ns in namespaces:
        count_str = run_oc([
            "get", "pods", "-n", ns, "--no-headers",
            "--field-selector=status.phase=Running",
            "-o", "name",
        ])
        pod_counts[ns] = len(count_str.splitlines()) if count_str else 0

    # Managed clusters
    mc_count_str = run_oc(["get", "managedclusters", "--no-headers", "-o", "name"])
    mc_count = len(mc_count_str.splitlines()) if mc_count_str else 0

    summary = {
        "acm_version": acm_version,
        "mch_phase": mch_phase,
        "mce_phase": mce_phase,
        "node_count": node_count,
        "managed_cluster_count": mc_count,
        "pod_counts": pod_counts,
    }

    print(f"  MCH phase: {mch_phase}")
    print(f"  MCE phase: {mce_phase}")
    print(f"  Nodes: {node_count}")
    print(f"  Managed clusters: {mc_count}")
    for ns, count in pod_counts.items():
        print(f"  Pods in {ns}: {count}")

    if not dry_run:
        baseline_path = KNOWLEDGE_DIR / "healthy-baseline.yaml"
        if baseline_path.exists():
            existing = load_yaml(baseline_path)
            existing["acm_version"] = acm_version
            existing["last_refreshed"] = today
            write_yaml(baseline_path, existing, BASELINE_HEADER)
        else:
            print(f"  Warning: {baseline_path} not found -- skipping write")
    else:
        print("  (dry-run -- no files modified)")

    return summary


def refresh_webhooks(mch_ns: str, dry_run: bool = False) -> dict:
    """Refresh webhook-registry.yaml by merging cluster state with curated content.

    Curated fields (owner, critical_for, if_broken) are preserved.
    Structural fields (failure_policy, namespace) are updated from the cluster.
    New webhooks are added with placeholder descriptions.
    Webhooks not found on the cluster are kept but flagged.
    """
    print("\n--- Refreshing webhook registry ---")

    acm_version = get_acm_version(mch_ns)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Query cluster for webhook configurations (full JSON for detail)
    v_json = run_oc(["get", "validatingwebhookconfigurations", "-o", "json"])
    m_json = run_oc(["get", "mutatingwebhookconfigurations", "-o", "json"])

    def parse_cluster_webhooks(raw_json: str) -> dict[str, dict]:
        """Extract ACM-related webhooks with failure_policy and namespace."""
        result = {}
        if not raw_json:
            return result
        try:
            for item in json.loads(raw_json).get("items", []):
                name = item["metadata"]["name"]
                if not any(kw in name for kw in [
                    "open-cluster-management", "hive", "multicluster", "ocm",
                ]):
                    continue
                hooks = item.get("webhooks", [])
                fp = hooks[0].get("failurePolicy", "Unknown") if hooks else "Unknown"
                ns = ""
                if hooks:
                    svc = hooks[0].get("clientConfig", {}).get("service", {})
                    ns = svc.get("namespace", "")
                result[name] = {"failure_policy": fp, "namespace": ns}
        except (json.JSONDecodeError, KeyError, IndexError):
            print("  Warning: Failed to parse webhook data")
        return result

    cluster_v = parse_cluster_webhooks(v_json)
    cluster_m = parse_cluster_webhooks(m_json)
    print(f"  Cluster: {len(cluster_v)} validating, {len(cluster_m)} mutating (ACM-related)")

    # Load existing YAML
    webhook_path = KNOWLEDGE_DIR / "webhook-registry.yaml"
    existing = load_yaml(webhook_path)
    existing_v = {w["name"]: w for w in existing.get("validating_webhooks", [])}
    existing_m = {w["name"]: w for w in existing.get("mutating_webhooks", [])}

    changes = []

    def merge_webhook_list(
        cluster_hooks: dict[str, dict],
        existing_hooks: dict[str, dict],
        label: str,
    ) -> list[dict]:
        """Merge cluster webhooks with existing YAML entries."""
        merged = []

        # Process webhooks found on the cluster
        for name in sorted(cluster_hooks):
            info = cluster_hooks[name]
            if name in existing_hooks:
                entry = existing_hooks[name].copy()
                # Clear stale "not found" notes
                if "note" in entry and "Not found on cluster" in str(entry.get("note", "")):
                    del entry["note"]
                    changes.append(f"  [{label}] {name}: back on cluster")
                # Update failure_policy if changed
                old_fp = entry.get("failure_policy")
                if old_fp and old_fp != info["failure_policy"]:
                    entry["failure_policy"] = info["failure_policy"]
                    changes.append(
                        f"  [{label}] {name}: failure_policy {old_fp} -> {info['failure_policy']}"
                    )
            else:
                # New webhook -- add with placeholder curated fields
                entry = {
                    "name": name,
                    "owner": "unknown -- review and update",
                    "namespace": info["namespace"] or "unknown",
                    "failure_policy": info["failure_policy"],
                    "critical_for": ["unknown"],
                    "if_broken": "Impact not yet documented -- review webhook purpose and update",
                }
                changes.append(f"  [{label}] NEW: {name}")
            merged.append(entry)

        # Keep entries not on the cluster but flag them
        for name, entry in existing_hooks.items():
            if name not in cluster_hooks:
                flagged = entry.copy()
                if "Not found on cluster" not in str(flagged.get("note", "")):
                    flagged["note"] = (
                        f"Not found on cluster as of {today}"
                        " -- may be version-specific or conditionally deployed"
                    )
                    changes.append(f"  [{label}] NOT ON CLUSTER: {name}")
                merged.append(flagged)

        return merged

    merged_v = merge_webhook_list(cluster_v, existing_v, "V")
    merged_m = merge_webhook_list(cluster_m, existing_m, "M")

    if changes:
        print("  Changes:")
        for c in changes:
            print(f"    {c}")
    else:
        print("  No changes (cluster matches registry)")

    output = {
        "acm_version": acm_version,
        "last_refreshed": today,
        "validating_webhooks": merged_v,
        "mutating_webhooks": merged_m,
        "common_webhook_issues": existing.get("common_webhook_issues", []),
    }

    if not dry_run:
        write_yaml(webhook_path, output, WEBHOOK_HEADER)
    else:
        print("  (dry-run -- no files modified)")

    return {"validating": len(merged_v), "mutating": len(merged_m), "changes": len(changes)}


def refresh_certs(mch_ns: str, dry_run: bool = False) -> dict:
    """Refresh certificate-inventory.yaml by merging cluster state with curated content.

    Curated fields (used_by, managed_by, rotation, if_corrupted) are preserved.
    New TLS secrets are added with placeholder descriptions.
    Secrets not found on the cluster are kept but flagged.
    """
    print("\n--- Refreshing certificate inventory ---")

    acm_version = get_acm_version(mch_ns)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Map actual namespace names to YAML keys
    ns_map = {
        mch_ns: "mch_namespace",
        "multicluster-engine": "multicluster-engine",
        "open-cluster-management-hub": "open-cluster-management-hub",
        "open-cluster-management-observability": "open-cluster-management-observability",
        "hive": "hive",
    }

    # Load existing YAML
    cert_path = KNOWLEDGE_DIR / "certificate-inventory.yaml"
    existing = load_yaml(cert_path)
    existing_certs = existing.get("certificates", {})

    changes = []
    merged_certs = {}

    for ns, yaml_key in ns_map.items():
        # Query cluster for TLS secrets in this namespace
        secrets_json = run_oc(["get", "secrets", "-n", ns, "-o", "json"])

        cluster_tls = set()
        if secrets_json:
            try:
                secrets = json.loads(secrets_json)
                cluster_tls = {
                    s["metadata"]["name"]
                    for s in secrets.get("items", [])
                    if s.get("type") == "kubernetes.io/tls"
                }
            except (json.JSONDecodeError, KeyError):
                pass

        # Get existing entries for this namespace
        existing_ns = existing_certs.get(yaml_key, {})
        existing_secrets = {s["secret"]: s for s in existing_ns.get("secrets", [])}

        merged_secrets = []

        # Merge: cluster secrets with existing curated content
        for secret_name in sorted(cluster_tls):
            if secret_name in existing_secrets:
                entry = existing_secrets[secret_name].copy()
                # Clear stale "not found" notes
                if "note" in entry and "Not found" in str(entry.get("note", "")):
                    del entry["note"]
                    changes.append(f"  {ns}: {secret_name} back on cluster")
                merged_secrets.append(entry)
            else:
                entry = {
                    "secret": secret_name,
                    "used_by": "unknown -- review and update",
                    "managed_by": "check service-ca-operator annotation",
                    "rotation": "unknown",
                    "if_corrupted": "Impact not yet documented -- review secret purpose and update",
                }
                merged_secrets.append(entry)
                changes.append(f"  NEW in {ns}: {secret_name}")

        # Keep entries not on the cluster but flag them
        for secret_name, entry in existing_secrets.items():
            if secret_name not in cluster_tls:
                flagged = entry.copy()
                if "Not found" not in str(flagged.get("note", "")):
                    flagged["note"] = f"Not found on cluster as of {today}"
                    changes.append(f"  NOT ON CLUSTER in {ns}: {secret_name}")
                merged_secrets.append(flagged)

        ns_entry = {}
        # Preserve namespace-level note (e.g., "Namespace varies" or "Only present when...")
        if "note" in existing_ns:
            ns_entry["note"] = existing_ns["note"]
        ns_entry["secrets"] = merged_secrets
        merged_certs[yaml_key] = ns_entry

        if merged_secrets:
            print(f"  {ns}: {len(cluster_tls)} TLS secrets on cluster, {len(merged_secrets)} in registry")

    if changes:
        print("  Changes:")
        for c in changes:
            print(f"    {c}")
    else:
        print("  No changes (cluster matches inventory)")

    output = {
        "acm_version": acm_version,
        "last_refreshed": today,
        "certificates": merged_certs,
        "certificate_check_commands": existing.get("certificate_check_commands", {}),
        "common_cert_issues": existing.get("common_cert_issues", []),
    }

    if not dry_run:
        write_yaml(cert_path, output, CERT_HEADER)
    else:
        print("  (dry-run -- no files modified)")

    return {"namespaces": len(merged_certs), "changes": len(changes)}


def refresh_addons(mch_ns: str, dry_run: bool = False) -> dict:
    """Refresh addon-catalog.yaml by merging cluster state with curated content.

    Curated fields (description, if_unhealthy, depends_on, known_issues, etc.)
    are preserved. New addon types are added with placeholder descriptions.
    Addon types not found on the cluster are kept but flagged.
    """
    print("\n--- Refreshing addon catalog ---")

    acm_version = get_acm_version(mch_ns)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Get all addon instances across clusters
    addons_json = run_oc(["get", "managedclusteraddons", "-A", "-o", "json"])
    if not addons_json:
        print("  No addons found or cluster access issue")
        return {}

    try:
        addons_data = json.loads(addons_json)
    except json.JSONDecodeError:
        print("  Failed to parse addon data")
        return {}

    # Aggregate by addon name
    cluster_addons: dict[str, dict] = {}
    for addon in addons_data.get("items", []):
        name = addon["metadata"]["name"]
        cluster = addon["metadata"]["namespace"]

        conditions = addon.get("status", {}).get("conditions", [])
        available = any(
            c.get("type") == "Available" and c.get("status") == "True"
            for c in conditions
        )

        if name not in cluster_addons:
            cluster_addons[name] = {"available": 0, "unavailable": 0, "unhealthy_clusters": []}
        if available:
            cluster_addons[name]["available"] += 1
        else:
            cluster_addons[name]["unavailable"] += 1
            cluster_addons[name]["unhealthy_clusters"].append(cluster)

    print(f"  Addon types on cluster: {len(cluster_addons)}")
    for name in sorted(cluster_addons):
        info = cluster_addons[name]
        total = info["available"] + info["unavailable"]
        if info["unavailable"] > 0:
            print(f"    {name}: {info['unavailable']}/{total} UNHEALTHY")
        else:
            print(f"    {name}: ALL OK ({total} clusters)")

    # Load existing YAML
    addon_path = KNOWLEDGE_DIR / "addon-catalog.yaml"
    existing = load_yaml(addon_path)
    existing_addons = {a["name"]: a for a in existing.get("addons", [])}

    changes = []
    merged_addons = []

    # Merge: all addon names from both cluster and YAML
    all_addon_names = sorted(set(list(cluster_addons.keys()) + list(existing_addons.keys())))

    for name in all_addon_names:
        on_cluster = name in cluster_addons
        in_yaml = name in existing_addons

        if in_yaml and on_cluster:
            entry = existing_addons[name].copy()
            # Clear stale "not found" notes
            if "note" in entry and "Not found on cluster" in str(entry.get("note", "")):
                del entry["note"]
                changes.append(f"  {name}: back on cluster")
            merged_addons.append(entry)
        elif on_cluster and not in_yaml:
            # New addon type -- add with placeholder curated fields
            info = cluster_addons[name]
            entry = {
                "name": name,
                "display_name": name.replace("-", " ").title(),
                "required": False,
                "default_enabled": False,
                "subsystem": "unknown -- review and categorize",
                "spoke_namespace": "unknown -- verify with: oc get managedclusteraddon {name} -n <cluster> -o jsonpath='{{.status.namespace}}'",
                "description": "Auto-discovered addon -- review and document purpose",
                "health_check": f"oc get managedclusteraddon {name} -n {{cluster}}",
                "if_unhealthy": "Impact not yet documented -- review addon purpose and update",
                "depends_on": ["work-manager"],
            }
            total = info["available"] + info["unavailable"]
            merged_addons.append(entry)
            changes.append(f"  NEW: {name} (on {total} clusters)")
        elif in_yaml and not on_cluster:
            # In YAML but not on cluster -- flag it
            entry = existing_addons[name].copy()
            if "Not found on cluster" not in str(entry.get("note", "")):
                entry["note"] = (
                    f"Not found on cluster as of {today}"
                    " -- may require enablement or be version-specific"
                )
                changes.append(f"  NOT ON CLUSTER: {name}")
            merged_addons.append(entry)

    if changes:
        print("  Changes:")
        for c in changes:
            print(f"    {c}")
    else:
        print("  No changes (cluster matches catalog)")

    output = {
        "acm_version": acm_version,
        "last_refreshed": today,
        "addons": merged_addons,
        "addon_check_commands": existing.get("addon_check_commands", {}),
        "health_check_methodology": existing.get("health_check_methodology", []),
    }

    if not dry_run:
        write_yaml(addon_path, output, ADDON_HEADER)
    else:
        print("  (dry-run -- no files modified)")

    return {"addon_types": len(merged_addons), "changes": len(changes)}


def promote_learned(dry_run: bool = False) -> int:
    """Review and list learned/ entries for promotion."""
    print("\n--- Checking learned/ entries for promotion ---")

    if not LEARNED_DIR.exists():
        print("  No learned/ directory found")
        return 0

    learned_files = list(LEARNED_DIR.glob("*.md")) + list(LEARNED_DIR.glob("*.yaml"))
    learned_files = [f for f in learned_files if f.name != ".gitkeep"]

    if not learned_files:
        print("  No learned entries to promote")
        return 0

    print(f"  Found {len(learned_files)} learned entries:")
    for f in learned_files:
        print(f"    - {f.name}")
        with open(f) as fh:
            lines = fh.readlines()[:5]
            for line in lines:
                print(f"      {line.rstrip()}")

    if not dry_run:
        print("\n  Review these entries and manually promote relevant ones")
        print("  into the main knowledge files (component-registry.md,")
        print("  failure-patterns.md, etc.).")

    return len(learned_files)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Refresh ACM Hub Health knowledge database from live sources",
    )
    parser.add_argument("--baseline", action="store_true", help="Update healthy-baseline.yaml")
    parser.add_argument("--webhooks", action="store_true", help="Update webhook-registry.yaml")
    parser.add_argument("--certs", action="store_true", help="Update certificate-inventory.yaml")
    parser.add_argument("--addons", action="store_true", help="Update addon-catalog.yaml")
    parser.add_argument("--promote", action="store_true", help="List learned/ entries for promotion")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")

    args = parser.parse_args()

    # If --promote only, no cluster access needed
    if args.promote and not any([args.baseline, args.webhooks, args.certs, args.addons]):
        promote_learned(dry_run=args.dry_run)
        return

    # Check cluster access
    if not check_cluster_access():
        sys.exit(1)

    mch_ns = discover_mch_namespace()
    if not mch_ns:
        sys.exit(1)

    acm_version = get_acm_version(mch_ns)
    print(f"ACM version: {acm_version}")

    # Check for version drift across all YAML files
    check_version_drift(acm_version)

    # If no specific flag, refresh everything
    refresh_all = not any([args.baseline, args.webhooks, args.certs, args.addons, args.promote])

    results = {}

    if args.baseline or refresh_all:
        results["baseline"] = refresh_baseline(mch_ns, dry_run=args.dry_run)

    if args.webhooks or refresh_all:
        results["webhooks"] = refresh_webhooks(mch_ns, dry_run=args.dry_run)

    if args.certs or refresh_all:
        results["certs"] = refresh_certs(mch_ns, dry_run=args.dry_run)

    if args.addons or refresh_all:
        results["addons"] = refresh_addons(mch_ns, dry_run=args.dry_run)

    if args.promote or refresh_all:
        results["learned_count"] = promote_learned(dry_run=args.dry_run)

    print("\n--- Refresh complete ---")
    if args.dry_run:
        print("(dry-run mode -- no files were modified)")


if __name__ == "__main__":
    main()
