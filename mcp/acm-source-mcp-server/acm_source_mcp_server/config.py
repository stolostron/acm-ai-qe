"""Version state management and repository configuration."""

from dataclasses import dataclass, field


REPOS = {
    "acm": {
        "owner": "stolostron",
        "repo": "console",
        "description": "ACM Console source code",
    },
    "kubevirt": {
        "owner": "kubevirt-ui",
        "repo": "kubevirt-plugin",
        "description": "Fleet Virtualization UI",
    },
    "acm-e2e": {
        "owner": "stolostron",
        "repo": "clc-ui-e2e",
        "description": "Cluster Lifecycle + RBAC selectors",
    },
    "search-e2e": {
        "owner": "stolostron",
        "repo": "search-e2e-test",
        "description": "Search component selectors",
    },
    "app-e2e": {
        "owner": "stolostron",
        "repo": "application-ui-test",
        "description": "Applications selectors",
    },
    "grc-e2e": {
        "owner": "stolostron",
        "repo": "acmqe-grc-test",
        "description": "Governance selectors",
    },
}

QE_REPOS = {"acm-e2e", "search-e2e", "app-e2e", "grc-e2e"}

ACM_VERSIONS = [f"2.{v}" for v in range(11, 19)]  # 2.11 through 2.18
CNV_VERSIONS = [f"4.{v}" for v in range(14, 23)]  # 4.14 through 4.22

ACM_LATEST = "2.16"
CNV_LATEST = "4.21"

ACM_MAIN_VERSION = "2.18"
CNV_MAIN_VERSION = "4.22"


def acm_version_to_branch(version: str) -> str:
    """Map ACM version string to git branch name."""
    if version == "main" or version == ACM_MAIN_VERSION:
        return "main"
    if version == "latest":
        return f"release-{ACM_LATEST}"
    return f"release-{version}"


def cnv_version_to_branch(version: str) -> str:
    """Map CNV version string to git branch name."""
    if version == "main" or version == CNV_MAIN_VERSION:
        return "main"
    if version == "latest":
        return f"release-{CNV_LATEST}"
    return f"release-{version}"


def get_branch_for_repo(repo_key: str, state: "VersionState") -> str:
    """Get the active branch for a given repo key."""
    if repo_key in QE_REPOS:
        return "main"
    if repo_key == "kubevirt":
        return cnv_version_to_branch(state.cnv_version)
    return acm_version_to_branch(state.acm_version)


@dataclass
class VersionState:
    """In-memory version state (resets on server restart)."""

    acm_version: str = field(default=ACM_LATEST)
    cnv_version: str = field(default=CNV_LATEST)


# Singleton state instance
state = VersionState()
