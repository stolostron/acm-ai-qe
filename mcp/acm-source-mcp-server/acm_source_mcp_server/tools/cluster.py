"""Cluster tools: detect_cnv_version, get_cluster_virt_info."""

import re
from acm_source_mcp_server.config import (
    CNV_VERSIONS,
    cnv_version_to_branch,
    state,
)
from acm_source_mcp_server.github import run_command


async def detect_cnv_version() -> str:
    """Detect CNV version from the current cluster via oc CLI and auto-set the branch."""
    rc, stdout, stderr = await run_command([
        "oc", "get", "csv", "-n", "openshift-cnv",
        "-o", "jsonpath={.items[0].spec.version}",
    ])
    if rc != 0:
        alt_rc, alt_stdout, alt_stderr = await run_command([
            "oc", "get", "csv", "-n", "openshift-cnv",
            "-o", "jsonpath={.items[*].metadata.name}",
        ])
        if alt_rc != 0:
            return f"Failed to detect CNV version. Is oc logged in? Error: {stderr or alt_stderr}"
        return f"CNV CSVs found but version extraction failed. CSVs: {alt_stdout}"

    version_full = stdout.strip().strip("{}")
    match = re.match(r"(\d+\.\d+)", version_full)
    if not match:
        return f"Could not parse CNV version from: {version_full}"

    detected = match.group(1)
    if detected in CNV_VERSIONS:
        state.cnv_version = detected
        branch = cnv_version_to_branch(detected)
        return f"Detected CNV {version_full}. Set version to {detected} (branch: {branch})"
    else:
        return f"Detected CNV {version_full} but version {detected} is not in supported range ({CNV_VERSIONS[0]}-{CNV_VERSIONS[-1]})"


async def get_cluster_virt_info() -> str:
    """Get CNV/Fleet Virtualization status from the current cluster."""
    results = []

    # CNV operator status
    rc, stdout, stderr = await run_command([
        "oc", "get", "csv", "-n", "openshift-cnv",
        "-o", "custom-columns=NAME:.metadata.name,VERSION:.spec.version,PHASE:.status.phase",
        "--no-headers",
    ])
    if rc == 0 and stdout.strip():
        results.append("CNV Operator:")
        results.append(f"  {stdout.strip()}")
    else:
        results.append("CNV Operator: Not found or not accessible")

    # HyperConverged CR
    rc, stdout, stderr = await run_command([
        "oc", "get", "hyperconverged", "-n", "openshift-cnv",
        "-o", "custom-columns=NAME:.metadata.name,STATUS:.status.conditions[0].type",
        "--no-headers",
    ])
    if rc == 0 and stdout.strip():
        results.append(f"\nHyperConverged CR:")
        results.append(f"  {stdout.strip()}")

    # VirtualMachine count
    rc, stdout, stderr = await run_command([
        "oc", "get", "vm", "-A", "--no-headers",
    ])
    if rc == 0:
        vm_count = len([l for l in stdout.strip().split("\n") if l.strip()])
        results.append(f"\nVirtualMachines: {vm_count} total across all namespaces")
    else:
        results.append("\nVirtualMachines: Unable to query (may need permissions)")

    # MTV operator
    rc, stdout, stderr = await run_command([
        "oc", "get", "csv", "-n", "openshift-mtv",
        "-o", "custom-columns=NAME:.metadata.name,VERSION:.spec.version,PHASE:.status.phase",
        "--no-headers",
    ])
    if rc == 0 and stdout.strip():
        results.append(f"\nMTV (Migration Toolkit for Virtualization):")
        results.append(f"  {stdout.strip()}")
    else:
        # Try alternate namespace
        rc, stdout, stderr = await run_command([
            "oc", "get", "csv", "-A",
            "-o", "custom-columns=NAME:.metadata.name,NS:.metadata.namespace,PHASE:.status.phase",
            "--no-headers",
        ])
        if rc == 0:
            mtv_lines = [l for l in stdout.split("\n") if "forklift" in l.lower() or "mtv" in l.lower()]
            if mtv_lines:
                results.append(f"\nMTV (Migration Toolkit for Virtualization):")
                for line in mtv_lines:
                    results.append(f"  {line.strip()}")
            else:
                results.append("\nMTV: Not installed")
        else:
            results.append("\nMTV: Not found")

    # ACM multicluster-engine + virt addon
    rc, stdout, stderr = await run_command([
        "oc", "get", "managedclusteraddons", "-A",
        "--no-headers",
    ])
    if rc == 0 and stdout.strip():
        virt_addons = [l for l in stdout.split("\n") if "virt" in l.lower() or "kubevirt" in l.lower()]
        if virt_addons:
            results.append(f"\nVirtualization ManagedClusterAddons:")
            for line in virt_addons:
                results.append(f"  {line.strip()}")

    if not results:
        return "No virtualization information available. Is oc logged in to a cluster?"

    return "\n".join(results)
