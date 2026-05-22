"""Version management tools: list_repos, list_versions, set_acm_version, set_cnv_version, get_current_version."""

from acm_source_mcp_server.config import (
    REPOS,
    QE_REPOS,
    ACM_VERSIONS,
    CNV_VERSIONS,
    ACM_LATEST,
    CNV_LATEST,
    ACM_MAIN_VERSION,
    CNV_MAIN_VERSION,
    acm_version_to_branch,
    cnv_version_to_branch,
    get_branch_for_repo,
    state,
)


async def list_repos() -> str:
    """Show current version status for all configured repositories."""
    lines = ["Repository Status:", ""]
    for key, info in REPOS.items():
        branch = get_branch_for_repo(key, state)
        lines.append(f"  {key}: {info['owner']}/{info['repo']} (branch: {branch})")
        lines.append(f"    {info['description']}")
    lines.append("")
    lines.append(f"Active ACM version: {state.acm_version} (branch: {acm_version_to_branch(state.acm_version)})")
    lines.append(f"Active CNV version: {state.cnv_version} (branch: {cnv_version_to_branch(state.cnv_version)})")
    lines.append("QE repos always use: main")
    return "\n".join(lines)


async def list_versions() -> str:
    """Show ALL supported versions with their branch mappings."""
    lines = ["ACM Console Versions:", ""]
    for v in ACM_VERSIONS:
        branch = acm_version_to_branch(v)
        marker = " (latest)" if v == ACM_LATEST else ""
        marker = " (main)" if v == ACM_MAIN_VERSION else marker
        lines.append(f"  ACM {v} -> {branch}{marker}")
    lines.append("")
    lines.append("CNV/kubevirt-plugin Versions:", )
    lines.append("")
    for v in CNV_VERSIONS:
        branch = cnv_version_to_branch(v)
        marker = " (latest)" if v == CNV_LATEST else ""
        marker = " (main)" if v == CNV_MAIN_VERSION else marker
        lines.append(f"  CNV {v} -> {branch}{marker}")
    lines.append("")
    lines.append("QE Repos (acm-e2e, search-e2e, app-e2e, grc-e2e): always use 'main' branch")
    return "\n".join(lines)


async def set_acm_version(version: str) -> str:
    """Set the ACM Console branch version. Accepts: '2.11'-'2.18', 'main', 'latest'."""
    valid = set(ACM_VERSIONS) | {"main", "latest"}
    if version not in valid:
        return f"Invalid ACM version '{version}'. Valid: {sorted(valid)}"
    state.acm_version = version
    branch = acm_version_to_branch(version)
    return f"ACM version set to {version} (branch: {branch})"


async def set_cnv_version(version: str) -> str:
    """Set the kubevirt-plugin branch version. Accepts: '4.14'-'4.22', 'main', 'latest'."""
    valid = set(CNV_VERSIONS) | {"main", "latest"}
    if version not in valid:
        return f"Invalid CNV version '{version}'. Valid: {sorted(valid)}"
    state.cnv_version = version
    branch = cnv_version_to_branch(version)
    return f"CNV version set to {version} (branch: {branch})"


async def get_current_version(repo: str = "acm") -> str:
    """Get the currently active version and branch for a repository."""
    if repo not in REPOS:
        return f"Unknown repo '{repo}'. Valid: {list(REPOS.keys())}"
    if repo in QE_REPOS:
        return f"Repo '{repo}' always uses branch: main"
    if repo == "kubevirt":
        return f"CNV version: {state.cnv_version} (branch: {cnv_version_to_branch(state.cnv_version)})"
    return f"ACM version: {state.acm_version} (branch: {acm_version_to_branch(state.acm_version)})"
