import os
import subprocess
import logging
import json
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from .gh_client import (
    GitHubClient, REPOS, DEFAULT_REPO,
    ACM_VERSIONS, CNV_VERSIONS,
    MAIN_ACM_VERSION, LATEST_ACM_GA,
    MAIN_CNV_VERSION, LATEST_CNV_GA
)
from .analyzer import UIAnalyzer

# Common PatternFly v6 selectors (reference catalog)
PATTERNFLY_SELECTORS = {
    "button": {
        "primary": ".pf-v6-c-button.pf-m-primary",
        "secondary": ".pf-v6-c-button.pf-m-secondary",
        "link": ".pf-v6-c-button.pf-m-link",
        "danger": ".pf-v6-c-button.pf-m-danger",
        "plain": ".pf-v6-c-button.pf-m-plain",
    },
    "menu": {
        "toggle": ".pf-v6-c-menu-toggle",
        "content": ".pf-v6-c-menu__content",
        "item": ".pf-v6-c-menu__item",
        "list": ".pf-v6-c-menu__list",
    },
    "dropdown": {
        "toggle": ".pf-v6-c-dropdown__toggle",
        "menu": ".pf-v6-c-dropdown__menu",
        "item": ".pf-v6-c-dropdown__menu-item",
    },
    "table": {
        "table": ".pf-v6-c-table",
        "row": ".pf-v6-c-table tr",
        "cell": ".pf-v6-c-table td",
        "header": ".pf-v6-c-table th",
        "sortable": ".pf-v6-c-table__sort",
    },
    "modal": {
        "modal": ".pf-v6-c-modal-box",
        "header": ".pf-v6-c-modal-box__header",
        "body": ".pf-v6-c-modal-box__body",
        "footer": ".pf-v6-c-modal-box__footer",
        "close": ".pf-v6-c-modal-box__close",
    },
    "wizard": {
        "wizard": ".pf-v6-c-wizard",
        "nav": ".pf-v6-c-wizard__nav",
        "navItem": ".pf-v6-c-wizard__nav-item",
        "main": ".pf-v6-c-wizard__main",
        "footer": ".pf-v6-c-wizard__footer",
    },
    "form": {
        "form": ".pf-v6-c-form",
        "group": ".pf-v6-c-form__group",
        "label": ".pf-v6-c-form__label",
        "control": ".pf-v6-c-form-control",
        "helperText": ".pf-v6-c-form__helper-text",
    },
    "tree": {
        "treeView": ".pf-v6-c-tree-view",
        "node": ".pf-v6-c-tree-view__node",
        "nodeText": ".pf-v6-c-tree-view__node-text",
        "nodeToggle": ".pf-v6-c-tree-view__node-toggle",
    },
    "tabs": {
        "tabs": ".pf-v6-c-tabs",
        "list": ".pf-v6-c-tabs__list",
        "item": ".pf-v6-c-tabs__item",
        "link": ".pf-v6-c-tabs__link",
    },
    "alert": {
        "alert": ".pf-v6-c-alert",
        "success": ".pf-v6-c-alert.pf-m-success",
        "danger": ".pf-v6-c-alert.pf-m-danger",
        "warning": ".pf-v6-c-alert.pf-m-warning",
        "info": ".pf-v6-c-alert.pf-m-info",
    },
    "chip": {
        "chip": ".pf-v6-c-chip",
        "chipGroup": ".pf-v6-c-chip-group",
        "text": ".pf-v6-c-chip__text",
    },
    "label": {
        "label": ".pf-v6-c-label",
        "text": ".pf-v6-c-label__text",
    },
    "select": {
        "select": ".pf-v6-c-select",
        "toggle": ".pf-v6-c-select__toggle",
        "menu": ".pf-v6-c-select__menu",
    },
    "emptyState": {
        "emptyState": ".pf-v6-c-empty-state",
        "icon": ".pf-v6-c-empty-state__icon",
        "title": ".pf-v6-c-empty-state__title-text",
        "body": ".pf-v6-c-empty-state__body",
    },
}

# Initialize FastMCP
mcp = FastMCP("acm-ui")

# Search paths for each repository
SEARCH_PATHS = {
    # Source code repositories
    "acm": [
        "frontend/src/components",
        "frontend/src/routes",
        "frontend/src/ui-components",
        "frontend/packages/multicluster-sdk/src/components",
    ],
    "kubevirt": [
        "src/views/virtualmachines",
        "src/views/search",
        "src/multicluster/components",
        "src/utils/components",
        "cypress/views",
    ],
    # QE automation repositories
    "acm-e2e": [
        "cypress/views",
        "cypress/views/common",
        "cypress/support",
    ],
    "search-e2e": [
        "tests/cypress/views",
        "tests/cypress/support",
    ],
    "app-e2e": [
        "tests/cypress/views",
        "tests/cypress/support",
    ],
    "grc-e2e": [
        "tests/cypress/support",
        "tests/cypress/support/ui",
    ],
}

# ACM Console selector files to scan (for source-based selector extraction)
ACM_SELECTOR_PATHS = [
    "frontend/src/ui-components/AcmTable",
    "frontend/src/ui-components/AcmForm",
    "frontend/src/ui-components/AcmButton",
    "frontend/src/ui-components/AcmModal",
    "frontend/src/ui-components/AcmSearchInput",
    "frontend/src/routes/Infrastructure/Clusters",
    "frontend/src/routes/Credentials",
    "frontend/src/routes/UserManagement",
]

# QE Repo Selector Catalog (organized by component)
# Each entry maps a repo key to its component name and selector file paths
QE_SELECTOR_CATALOG = {
    "acm-e2e": {
        "name": "Cluster Lifecycle + RBAC",
        "short": "clc",
        "files": [
            "cypress/views/common/commonSelectors.js",
            "cypress/views/header.js",
            "cypress/views/yamlEditor.js",
        ]
    },
    "search-e2e": {
        "name": "Search",
        "short": "search",
        "files": [
            "tests/cypress/views/search.js",
            "tests/cypress/views/savedSearches.js",
            "tests/cypress/views/suggestedSearches.js",
        ]
    },
    "app-e2e": {
        "name": "Applications (ALC)",
        "short": "app",
        "files": [
            "tests/cypress/support/selectors.js",
            "tests/cypress/views/application.js",
            "tests/cypress/views/common.js",
        ]
    },
    "grc-e2e": {
        "name": "Governance (GRC)",
        "short": "grc",
        "files": [
            "tests/cypress/support/views.js",
            "tests/cypress/support/ui/policy-actions.js",
            "tests/cypress/support/constants.js",
        ]
    },
}


def _run_oc_command(args: List[str]) -> tuple[bool, str]:
    """Runs an oc command and returns (success, output)."""
    try:
        result = subprocess.run(
            ["oc"] + args,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except FileNotFoundError:
        return False, "oc CLI not found"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def _detect_cnv_version() -> tuple[str, str]:
    """
    Detects the CNV/OpenShift Virtualization version from the current cluster.
    Returns (version, error_message).
    """
    # Try HyperConverged CR first (most reliable)
    success, output = _run_oc_command([
        "get", "hyperconverged", "kubevirt-hyperconverged",
        "-n", "openshift-cnv",
        "-o", "jsonpath={.status.versions[?(@.name==\"operator\")].version}"
    ])
    if success and output:
        return output, ""

    # Fallback: Try CSV
    success, output = _run_oc_command([
        "get", "csv", "-n", "openshift-cnv",
        "-o", "jsonpath={.items[?(@.metadata.name=~\"kubevirt-hyperconverged.*\")].spec.version}"
    ])
    if success and output:
        # May return multiple, take first
        return output.split()[0] if output else "", ""

    return "", "CNV not installed or not accessible"


def _cnv_version_to_branch(cnv_version: str) -> str:
    """
    Converts a CNV version (e.g., '4.20.3') to a kubevirt-plugin branch (e.g., 'release-4.20').
    """
    if not cnv_version:
        return "main"

    parts = cnv_version.split('.')
    if len(parts) >= 2:
        major_minor = f"{parts[0]}.{parts[1]}"
        return f"release-{major_minor}"
    return "main"


# Global state
class ServerState:
    def __init__(self):
        self.gh_client = GitHubClient()
        self.analyzer = UIAnalyzer()

        # ACM version tracking (for stolostron/console)
        default_acm = os.getenv("DEFAULT_ACM_VERSION", LATEST_ACM_GA)
        self.active_acm_version = default_acm  # Semantic version (e.g., "2.16")
        self.acm_branch = ACM_VERSIONS.get(default_acm, f"release-{default_acm}")

        # CNV version tracking (for kubevirt-plugin)
        default_cnv = os.getenv("DEFAULT_CNV_VERSION", LATEST_CNV_GA)
        self.active_cnv_version = default_cnv  # Semantic version (e.g., "4.20")
        self.cnv_branch = CNV_VERSIONS.get(default_cnv, f"release-{default_cnv}")

        # For cluster auto-detection
        self.detected_cnv_version = ""

    def get_version(self, repo_key: str) -> str:
        """Gets the current branch for a repository."""
        if repo_key == "kubevirt":
            return self.cnv_branch
        # QE automation repos always use main branch
        if repo_key in ("acm-e2e", "search-e2e", "app-e2e", "grc-e2e"):
            return "main"
        return self.acm_branch

    def set_version(self, repo_key: str, branch: str):
        """Sets the branch for a repository (low-level)."""
        if repo_key == "kubevirt":
            self.cnv_branch = branch
        else:
            self.acm_branch = branch

    def set_acm_version(self, version: str) -> tuple[bool, str]:
        """Sets ACM version and corresponding branch. Returns (success, message)."""
        if version == "latest":
            version = LATEST_ACM_GA
        elif version == "main":
            version = MAIN_ACM_VERSION

        if version in ACM_VERSIONS:
            branch = ACM_VERSIONS[version]
            if self.gh_client.validate_ref(branch, "acm"):
                self.active_acm_version = version
                self.acm_branch = branch
                return True, f"ACM {version} -> {branch}"
            return False, f"Branch '{branch}' not found in stolostron/console"
        return False, f"Unknown ACM version '{version}'. Available: {list(ACM_VERSIONS.keys())}"

    def set_cnv_version(self, version: str) -> tuple[bool, str]:
        """Sets CNV version and corresponding branch. Returns (success, message)."""
        if version == "latest":
            version = LATEST_CNV_GA
        elif version == "main":
            version = MAIN_CNV_VERSION

        if version in CNV_VERSIONS:
            branch = CNV_VERSIONS[version]
            if self.gh_client.validate_ref(branch, "kubevirt"):
                self.active_cnv_version = version
                self.cnv_branch = branch
                return True, f"CNV {version} -> {branch}"
            return False, f"Branch '{branch}' not found in kubevirt-ui/kubevirt-plugin"
        return False, f"Unknown CNV version '{version}'. Available: {list(CNV_VERSIONS.keys())}"

    def get_acm_version_label(self) -> str:
        """Returns a human-readable label for current ACM version."""
        v = self.active_acm_version
        if v == LATEST_ACM_GA:
            return f"{v} (Latest GA)"
        elif v == MAIN_ACM_VERSION:
            return f"{v} (Development)"
        return v

    def get_cnv_version_label(self) -> str:
        """Returns a human-readable label for current CNV version."""
        v = self.active_cnv_version
        if v == LATEST_CNV_GA:
            return f"{v} (Latest GA)"
        elif v == MAIN_CNV_VERSION:
            return f"{v} (Development)"
        return v

state = ServerState()
logger = logging.getLogger(__name__)


@mcp.tool()
def list_repos() -> str:
    """
    Lists all available repositories and their current version settings.
    Shows active ACM and CNV versions with their corresponding branches.
    """
    output = ["=== ACM UI MCP Server ===", ""]

    # Active versions
    output.append("Active Versions:")
    acm_label = state.get_acm_version_label()
    cnv_label = state.get_cnv_version_label()
    output.append(f"  ACM:  {acm_label} -> stolostron/console @ {state.acm_branch}")
    output.append(f"  CNV:  {cnv_label} -> kubevirt-ui/kubevirt-plugin @ {state.cnv_branch}")

    if state.detected_cnv_version:
        output.append(f"\n  (Auto-detected CNV from cluster: {state.detected_cnv_version})")

    output.append("")
    output.append("Note: ACM and CNV versions are INDEPENDENT.")
    output.append("      - ACM version = which ACM Console features to look up")
    output.append("      - CNV version = Fleet Virt UI on your target managed cluster")

    output.append("")
    output.append("Commands:")
    output.append("  set_acm_version('2.16')    # Set ACM Console version")
    output.append("  set_cnv_version('4.20')    # Set Fleet Virt UI version")
    output.append("  detect_cnv_version()       # Auto-detect CNV from cluster")
    output.append("  list_versions()            # Show all supported versions")

    return "\n".join(output)


@mcp.tool()
def detect_cnv_version() -> str:
    """
    Detects the CNV/OpenShift Virtualization version from the current cluster
    and automatically sets the correct kubevirt-plugin branch.

    Requires: 'oc' CLI logged into a cluster with CNV installed.

    The kubevirt-plugin branches follow CNV versions:
    - CNV 4.20.x -> release-4.20 branch
    - CNV 4.19.x -> release-4.19 branch

    This is important because Fleet Virtualization UI selectors may differ between versions.
    """
    cnv_version, error = _detect_cnv_version()

    if error or not cnv_version:
        return f"Could not detect CNV version: {error or 'No version found'}. Is 'oc' logged in to a cluster with CNV installed?"

    state.detected_cnv_version = cnv_version
    branch = _cnv_version_to_branch(cnv_version)

    # Extract major.minor for semantic version
    parts = cnv_version.split('.')
    semantic_version = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else cnv_version

    # Validate the branch exists
    if state.gh_client.validate_ref(branch, "kubevirt"):
        state.active_cnv_version = semantic_version
        state.cnv_branch = branch
        return f"""CNV Version Detected: {cnv_version}
Mapped to kubevirt-plugin branch: {branch}

Fleet Virt UI now set to: CNV {semantic_version} -> {branch}
You can now use find_test_ids(), get_component_source() with repo='kubevirt'
to get selectors matching your cluster's CNV version.

Note: ACM Console unchanged ({state.active_acm_version}). Use set_acm_version() to change."""
    else:
        # Try main if specific branch doesn't exist
        state.active_cnv_version = MAIN_CNV_VERSION
        state.cnv_branch = "main"
        return f"""CNV Version Detected: {cnv_version}
Branch '{branch}' not found in kubevirt-plugin, using 'main' instead.

Note: Some selectors may differ from your cluster's version."""


@mcp.tool()
def get_cluster_virt_info() -> str:
    """
    Gets comprehensive virtualization info from the current cluster.
    Includes CNV version, console plugins, and Fleet Virt status.

    Useful for understanding what UI components are available.
    """
    output = ["=== Cluster Virtualization Info ===\n"]

    # CNV Version
    cnv_version, cnv_error = _detect_cnv_version()
    if cnv_version:
        output.append(f"CNV/OpenShift Virtualization: {cnv_version}")
        output.append(f"  -> kubevirt-plugin branch: {_cnv_version_to_branch(cnv_version)}")
    else:
        output.append(f"CNV: Not detected ({cnv_error})")

    # Check console plugins
    success, plugins = _run_oc_command([
        "get", "consoleplugin", "-o", "jsonpath={.items[*].metadata.name}"
    ])
    if success and plugins:
        plugin_list = plugins.split()
        output.append(f"\nConsole Plugins: {len(plugin_list)}")
        for p in plugin_list:
            if "kubevirt" in p.lower() or "virt" in p.lower():
                output.append(f"  - {p} (virtualization)")
            elif "acm" in p.lower() or "multicluster" in p.lower():
                output.append(f"  - {p} (ACM)")

    # Check if Fleet Virt perspective is available
    success, _ = _run_oc_command([
        "get", "consoleplugin", "kubevirt-plugin", "-o", "name"
    ])
    if success:
        output.append("\nFleet Virtualization: ENABLED (kubevirt-plugin console plugin found)")
    else:
        output.append("\nFleet Virtualization: NOT AVAILABLE (kubevirt-plugin not found)")

    # ACM Hub check
    success, _ = _run_oc_command([
        "get", "multiclusterhub", "-A", "-o", "name"
    ])
    if success:
        output.append("ACM Hub: INSTALLED")
    else:
        output.append("ACM Hub: NOT DETECTED")

    return "\n".join(output)


@mcp.tool()
def set_version(version: str, repo: str = "acm") -> str:
    """
    Sets the active branch for a repository (low-level).

    Prefer using set_acm_version() or set_cnv_version() for semantic version switching.

    Args:
        version: Branch name (e.g., 'release-2.15', 'main', 'release-4.20')
        repo: Repository key - 'acm' for stolostron/console, 'kubevirt' for kubevirt-ui/kubevirt-plugin
    """
    if repo not in REPOS:
        return f"Error: Unknown repo '{repo}'. Available: {list(REPOS.keys())}"

    if state.gh_client.validate_ref(version, repo):
        state.set_version(repo, version)
        return f"Active version for {repo} ({REPOS[repo]}) set to {version}"
    else:
        return f"Error: Version '{version}' not found in {REPOS[repo]}"


@mcp.tool()
def set_acm_version(version: str) -> str:
    """
    Sets the ACM Console (stolostron/console) branch by ACM version number.
    Does NOT affect kubevirt-plugin - use set_cnv_version() or detect_cnv_version() for that.

    Args:
        version: ACM version (e.g., '2.16', '2.15', 'latest', 'main')
                 - 'latest' = latest GA version (currently 2.16)
                 - 'main' = next unreleased version (currently 2.17)

    Examples:
        set_acm_version('2.16')  # Use ACM 2.16 console features
        set_acm_version('main')  # Use development/next release
        set_acm_version('latest') # Use latest GA version
    """
    success, message = state.set_acm_version(version)

    if success:
        label = state.get_acm_version_label()
        return f"""ACM Console set to {label}
  -> stolostron/console @ {state.acm_branch}

Note: kubevirt-plugin unchanged (CNV {state.active_cnv_version}).
      Use set_cnv_version() or detect_cnv_version() to change Fleet Virt UI version."""
    else:
        return f"Error: {message}"


@mcp.tool()
def set_cnv_version(version: str) -> str:
    """
    Sets the kubevirt-plugin branch for Fleet Virtualization UI by CNV version number.
    Use this to match the CNV version on your target managed cluster.
    Does NOT affect ACM Console - use set_acm_version() for that.

    Args:
        version: CNV version (e.g., '4.20', '4.21', 'latest', 'main')
                 - 'latest' = latest GA version (currently 4.21)
                 - 'main' = next unreleased version

    Alternative: Use detect_cnv_version() to auto-detect CNV from connected cluster.

    Examples:
        set_cnv_version('4.20')  # Match CNV 4.20 on your spoke cluster
        set_cnv_version('4.21')  # Match CNV 4.21
        set_cnv_version('latest') # Use latest GA CNV version
    """
    success, message = state.set_cnv_version(version)

    if success:
        label = state.get_cnv_version_label()
        return f"""Fleet Virt UI set to CNV {label}
  -> kubevirt-ui/kubevirt-plugin @ {state.cnv_branch}

Note: ACM Console unchanged ({state.active_acm_version}).
      Use set_acm_version() to change ACM Console version."""
    else:
        return f"Error: {message}"


@mcp.tool()
def list_versions() -> str:
    """
    Lists all supported ACM and CNV versions with their branch mappings.
    Shows which versions are currently active for each repo.

    ACM and CNV versions are INDEPENDENT:
    - ACM version = which ACM Console features to look up (stolostron/console)
    - CNV version = Fleet Virt UI matching your target managed cluster (kubevirt-plugin)
    """
    output = ["=== Supported Versions ===", ""]

    # ACM Versions
    output.append("ACM Console (stolostron/console):")
    for version, branch in sorted(ACM_VERSIONS.items(), key=lambda x: x[0]):
        markers = []
        if version == state.active_acm_version:
            markers.append("ACTIVE")
        if version == LATEST_ACM_GA:
            markers.append("LATEST GA")
        if version == MAIN_ACM_VERSION:
            markers.append("DEV")

        marker_str = f"  [{', '.join(markers)}]" if markers else ""
        output.append(f"  {version}  -> {branch}{marker_str}")

    output.append("")

    # CNV Versions
    output.append("Fleet Virt UI (kubevirt-ui/kubevirt-plugin):")
    for version, branch in sorted(CNV_VERSIONS.items(), key=lambda x: x[0]):
        markers = []
        if version == state.active_cnv_version:
            markers.append("ACTIVE")
        if version == LATEST_CNV_GA:
            markers.append("LATEST GA")
        if version == MAIN_CNV_VERSION:
            markers.append("DEV")

        marker_str = f"  [{', '.join(markers)}]" if markers else ""
        output.append(f"  {version}  -> {branch}{marker_str}")

    output.append("")
    output.append("Commands:")
    output.append("  set_acm_version('2.16')   # Set ACM Console version")
    output.append("  set_cnv_version('4.20')   # Set Fleet Virt UI version")
    output.append("  detect_cnv_version()      # Auto-detect CNV from cluster")

    return "\n".join(output)


@mcp.tool()
def get_current_version(repo: str = "acm") -> str:
    """
    Returns the currently active version for a repository.

    Args:
        repo: Repository key - 'acm' or 'kubevirt'
    """
    if repo not in REPOS:
        return f"Error: Unknown repo '{repo}'. Available: {list(REPOS.keys())}"

    if repo == "acm":
        return f"ACM: {state.active_acm_version} -> {state.acm_branch}"
    else:
        return f"CNV: {state.active_cnv_version} -> {state.cnv_branch}"


@mcp.tool()
def find_test_ids(component_path: str, repo: str = "acm") -> str:
    """
    Searches for data-testid, id, aria-label, and data-test attributes in a specific file.

    Args:
        component_path: Path to the file in the repository
        repo: Repository key - 'acm' for ACM Console, 'kubevirt' for Fleet Virt UI

    Examples:
        - find_test_ids('frontend/src/ui-components/AcmTable/AcmTableToolbar.tsx', 'acm')
        - find_test_ids('src/views/search/components/SearchBar.tsx', 'kubevirt')
        - find_test_ids('cypress/views/selector-common.ts', 'kubevirt')
    """
    if repo not in REPOS:
        return f"Error: Unknown repo '{repo}'. Available: {list(REPOS.keys())}"

    version = state.get_version(repo)
    content = state.gh_client.get_file_content(component_path, version, repo)
    if not content:
        return f"Error: Could not retrieve content for {component_path} at {version} in {REPOS[repo]}"

    ids = state.analyzer.extract_test_ids(content)
    if not ids:
        return "No automation attributes found."

    # Format output
    output = [f"Found {len(ids)} attributes in {REPOS[repo]}/{component_path}:"]
    for item in ids:
        output.append(f"- {item['attribute']}='{item['value']}' (Line {item['line']})")
        output.append(f"  Context: {item['context']}")
        output.append("---")

    return "\n".join(output)


@mcp.tool()
def get_component_source(path: str, repo: str = "acm") -> str:
    """
    Retrieves the raw source code for a file.

    Args:
        path: Path to the file in the repository
        repo: Repository key - 'acm' or 'kubevirt'

    Examples:
        - get_component_source('frontend/src/routes/Infrastructure/VirtualMachines/VirtualMachines.tsx', 'acm')
        - get_component_source('src/multicluster/components/CrossClusterMigration/CrossClusterMigration.tsx', 'kubevirt')
    """
    if repo not in REPOS:
        return f"Error: Unknown repo '{repo}'. Available: {list(REPOS.keys())}"

    version = state.get_version(repo)
    content = state.gh_client.get_file_content(path, version, repo)
    if not content:
        return f"Error: File not found or empty: {path} in {REPOS[repo]}"
    return content


@mcp.tool()
def search_component(query: str, repo: str = "acm") -> str:
    """
    Searches for a component file by name in the repository.
    Uses heuristic search in common directories for each repo.

    Args:
        query: Search term (e.g., 'SearchBar', 'Migration', 'TreeView')
        repo: Repository key - 'acm' or 'kubevirt'
    """
    if repo not in REPOS:
        return f"Error: Unknown repo '{repo}'. Available: {list(REPOS.keys())}"

    version = state.get_version(repo)
    search_paths = SEARCH_PATHS.get(repo, [])

    results = []

    for base_path in search_paths:
        tree = state.gh_client.get_tree(base_path, version, repo)
        if isinstance(tree, list):
            for item in tree:
                if query.lower() in item.get('name', '').lower():
                    results.append(item['path'])

    if not results:
        return f"No components found matching '{query}' in {REPOS[repo]} common paths."

    return f"Found components in {REPOS[repo]}:\n" + "\n".join(results)


@mcp.tool()
def search_code(query: str, repo: str = "acm") -> str:
    """
    Searches for code containing the query string in a repository.
    Uses GitHub code search.

    Args:
        query: Search term (e.g., 'data-test-id', 'CrossClusterMigration', 'vm-search-input')
        repo: Repository key - 'acm' or 'kubevirt'
    """
    if repo not in REPOS:
        return f"Error: Unknown repo '{repo}'. Available: {list(REPOS.keys())}"

    results = state.gh_client.search_code_in_repo(query, repo)

    if not results:
        return f"No code found matching '{query}' in {REPOS[repo]}"

    output = [f"Found {len(results)} files matching '{query}' in {REPOS[repo]}:"]
    for item in results:
        path = item.get('path', 'unknown')
        output.append(f"  - {path}")
        output.append(f"    URL: https://github.com/{REPOS[repo]}/blob/main/{path}")

    return "\n".join(output)


@mcp.tool()
def get_fleet_virt_selectors() -> str:
    """
    Returns common Fleet Virtualization UI selectors from kubevirt-plugin.
    Useful for Cypress test automation.
    """
    # Fetch the selector files from kubevirt-plugin
    selector_files = [
        "cypress/views/selector.ts",
        "cypress/views/selector-common.ts",
        "cypress/views/actions.ts",
    ]

    version = state.get_version("kubevirt")
    output = ["Fleet Virtualization UI Selectors (kubevirt-plugin):"]

    for file_path in selector_files:
        content = state.gh_client.get_file_content(file_path, version, "kubevirt")
        if content:
            output.append(f"\n=== {file_path} ===")
            # Extract export const lines (selector definitions)
            for line in content.split('\n'):
                if line.strip().startswith('export const') or line.strip().startswith('export const'):
                    output.append(line.strip())

    output.append(f"\nSource: https://github.com/kubevirt-ui/kubevirt-plugin/tree/{version}/cypress/views")
    return "\n".join(output)


@mcp.tool()
def get_route_component(url_path: str) -> str:
    """
    Attempts to map a URL path to source files in both ACM and kubevirt-plugin repos.
    Note: This is a heuristic mapping based on standard UI structure.
    """
    path_parts = url_path.lower().strip('/').split('/')

    results = []

    # ACM Console mappings
    if "infrastructure" in path_parts:
        if "clusters" in path_parts:
            results.append("ACM: frontend/src/routes/Infrastructure/Clusters/Clusters.tsx")
        if "virtualmachines" in path_parts:
            results.append("ACM: frontend/src/routes/Infrastructure/VirtualMachines/VirtualMachines.tsx")

    if "credentials" in path_parts:
        results.append("ACM: frontend/src/routes/Credentials/Credentials.tsx")

    # Fleet Virtualization (kubevirt-plugin) mappings
    if "virtualmachine" in path_parts or "all-clusters" in path_parts:
        results.append("KubeVirt: src/views/virtualmachines/navigator/VirtualMachineNavigator.tsx")
        results.append("KubeVirt: src/views/virtualmachines/tree/VirtualMachineTreeView.tsx")
        results.append("KubeVirt: src/views/virtualmachines/list/VirtualMachinesList.tsx")

    if "search" in path_parts:
        results.append("KubeVirt: src/views/search/VirtualMachineSearchResults.tsx")
        results.append("KubeVirt: src/views/search/components/SearchBar.tsx")

    if "migration" in path_parts or "cclm" in path_parts:
        results.append("KubeVirt: src/multicluster/components/CrossClusterMigration/CrossClusterMigration.tsx")
        results.append("KubeVirt: src/multicluster/components/CrossClusterMigration/CrossClusterMigrationWizard.tsx")

    if not results:
        return "Could not automatically map URL to component. Try using search_component with repo='acm' or repo='kubevirt'."

    return "Possible source files:\n" + "\n".join(results)


# =============================================================================
# NEW TOOLS - Translation, Selectors, Types, Wizards, Routes
# =============================================================================

@mcp.tool()
def search_translations(query: str, exact: bool = False) -> str:
    """
    Searches ACM Console translation strings for matching text.
    Useful for finding exact UI text (button labels, messages, etc.) for test cases.

    Args:
        query: Text to search for (e.g., 'Create cluster', 'role assignment', 'error')
        exact: If True, only return exact matches. Default False for partial matches.

    Examples:
        search_translations('Create role assignment')  # Find button text
        search_translations('validate')  # Find all validation messages
        search_translations('error')  # Find all error-related strings

    Returns:
        Matching translation keys and their English values.
    """
    version = state.get_version("acm")

    # Fetch the English translation file
    content = state.gh_client.get_file_content(
        "frontend/public/locales/en/translation.json",
        version,
        "acm"
    )

    if not content:
        return "Error: Could not fetch translation file from stolostron/console"

    try:
        translations = json.loads(content)
    except json.JSONDecodeError:
        return "Error: Could not parse translation file"

    results = state.analyzer.search_translations(translations, query, exact)

    if not results:
        return f"No translations found matching '{query}'"

    output = [f"Found {len(results)} translation(s) matching '{query}':", ""]

    # Limit output to 30 results to avoid overwhelming output
    for item in results[:30]:
        key = item['key']
        value = item['value']
        # Truncate long values
        if len(str(value)) > 100:
            value = str(value)[:100] + "..."
        output.append(f"Key: {key}")
        output.append(f"Value: {value}")
        output.append("---")

    if len(results) > 30:
        output.append(f"... and {len(results) - 30} more matches")

    output.append(f"\nSource: stolostron/console @ {version}")
    output.append("File: frontend/public/locales/en/translation.json")

    return "\n".join(output)


@mcp.tool()
def get_acm_selectors(source: str = "both", component: str = "all") -> str:
    """
    Returns ACM Console UI selectors for test automation.

    Args:
        source: Where to get selectors from:
                - 'catalog': Curated selectors from QE repos (organized, proven)
                - 'source': Extract from stolostron/console source files (complete, raw)
                - 'both': Return both (default)
        component: Filter by component (default 'all'):
                - 'all': All components
                - 'clc': Cluster Lifecycle + RBAC (clc-ui-e2e)
                - 'search': Search component (search-e2e-test)
                - 'app': Applications/ALC (application-ui-test)
                - 'grc': Governance/GRC (acmqe-grc-test)

    Examples:
        get_acm_selectors()  # Get all selectors from all components
        get_acm_selectors('catalog')  # Get curated selectors only
        get_acm_selectors('catalog', 'search')  # Get Search selectors only
        get_acm_selectors('catalog', 'grc')  # Get GRC selectors only

    Returns:
        Organized selector catalog and/or extracted selectors from source.
    """
    output = ["=== ACM Console Selectors ===", ""]

    # Catalog selectors from QE repos
    if source in ["catalog", "both"]:
        output.append("## Curated Selectors (from QE automation repos)")
        output.append("Proven selectors used in ACM component automation:")
        output.append("")

        # Iterate through QE_SELECTOR_CATALOG
        for repo_key, config in QE_SELECTOR_CATALOG.items():
            # Filter by component if specified
            if component != "all" and config["short"] != component:
                continue

            output.append(f"### {config['name']} ({repo_key})")
            output.append("")

            for file_path in config["files"]:
                content = state.gh_client.get_file_content(file_path, "main", repo_key)
                if content:
                    output.append(f"#### {file_path}")
                    # Extract export statements and selector definitions
                    selector_lines = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if (line.startswith('export ') or
                            'data-test' in line or
                            'aria-label' in line or
                            'data-label' in line or
                            '.pf-v5-c-' in line or
                            '.pf-v6-c-' in line or
                            (line.startswith('const ') and '=' in line and ':' in line)):
                            selector_lines.append(f"  {line}")

                    # Limit output per file
                    if selector_lines:
                        for line in selector_lines[:20]:
                            output.append(line)
                        if len(selector_lines) > 20:
                            output.append(f"  ... and {len(selector_lines) - 20} more")
                    else:
                        output.append("  (No selector definitions found - may use inline selectors)")
                    output.append("")

            output.append(f"Source: {REPOS.get(repo_key, repo_key)} @ main")
            output.append("")

        if component != "all":
            output.append(f"Filter: component='{component}'")
            output.append("Use component='all' to see all components.")
            output.append("")

    # Source selectors from stolostron/console
    if source in ["source", "both"]:
        output.append("## Source Selectors (from stolostron/console)")
        output.append(f"Extracted from ACM Console @ {state.acm_branch}:")
        output.append("")

        # Scan key UI component directories
        sample_files = [
            "frontend/src/ui-components/AcmTable/AcmTable.tsx",
            "frontend/src/ui-components/AcmButton/AcmButton.tsx",
            "frontend/src/ui-components/AcmSearchInput/AcmSearchInput.tsx",
        ]

        version = state.get_version("acm")
        for file_path in sample_files:
            content = state.gh_client.get_file_content(file_path, version, "acm")
            if content:
                ids = state.analyzer.extract_test_ids(content)
                if ids:
                    output.append(f"### {file_path}")
                    for item in ids[:10]:  # Limit to 10 per file
                        output.append(f"  {item['attribute']}='{item['value']}'")
                    if len(ids) > 10:
                        output.append(f"  ... and {len(ids) - 10} more")
                    output.append("")

        output.append(f"Source: stolostron/console @ {version}")
        output.append("")
        output.append("Tip: Use find_test_ids(path, 'acm') to extract all selectors from a specific file.")

    # Add available components reference
    output.append("")
    output.append("---")
    output.append("Available components: all, clc, search, app, grc")

    return "\n".join(output)


@mcp.tool()
def get_component_types(path: str, repo: str = "acm") -> str:
    """
    Extracts TypeScript type and interface definitions from a source file.
    Useful for understanding data models, props, and state structures.

    Args:
        path: Path to the TypeScript file in the repository
        repo: Repository key - 'acm' or 'kubevirt'

    Examples:
        get_component_types('frontend/src/routes/UserManagement/RoleAssignments/model/role-assignment-preselected.ts', 'acm')
        get_component_types('src/utils/types.ts', 'kubevirt')

    Returns:
        Extracted type/interface definitions with their fields.
    """
    if repo not in ["acm", "kubevirt"]:
        return f"Error: Unknown repo '{repo}'. Use 'acm' or 'kubevirt'."

    version = state.get_version(repo)
    content = state.gh_client.get_file_content(path, version, repo)

    if not content:
        return f"Error: Could not fetch file {path} from {REPOS[repo]} @ {version}"

    types = state.analyzer.extract_types(content)

    if not types:
        return f"No type or interface definitions found in {path}"

    output = [f"Found {len(types)} type/interface definition(s) in {path}:", ""]

    for type_info in types:
        output.append(f"### {type_info['name']} (Line {type_info['line']})")
        output.append("```typescript")
        output.append(type_info['definition'])
        output.append("```")

        if type_info['fields']:
            output.append("Fields:")
            for field in type_info['fields']:
                optional = "?" if field['optional'] else ""
                output.append(f"  - {field['name']}{optional}: {field['type']}")

        output.append("")

    output.append(f"Source: {REPOS[repo]} @ {version}")

    return "\n".join(output)


@mcp.tool()
def get_wizard_steps(path: str, repo: str = "acm") -> str:
    """
    Analyzes a wizard component to extract step structure and visibility conditions.
    Useful for understanding wizard flow and writing test cases for wizard-based features.

    Args:
        path: Path to the wizard component file
        repo: Repository key - 'acm' or 'kubevirt'

    Examples:
        get_wizard_steps('frontend/src/wizards/RoleAssignment/RoleAssignmentWizardModal.tsx', 'acm')
        get_wizard_steps('src/views/virtualmachines/wizards/CreateVMWizard.tsx', 'kubevirt')

    Returns:
        Wizard steps with their names, order, and visibility conditions.
    """
    if repo not in ["acm", "kubevirt"]:
        return f"Error: Unknown repo '{repo}'. Use 'acm' or 'kubevirt'."

    version = state.get_version(repo)
    content = state.gh_client.get_file_content(path, version, repo)

    if not content:
        return f"Error: Could not fetch file {path} from {REPOS[repo]} @ {version}"

    steps = state.analyzer.extract_wizard_steps(content)

    if not steps:
        return f"No wizard steps found in {path}. Make sure this file contains PatternFly WizardStep components."

    output = [f"Found {len(steps)} wizard step(s) in {path}:", ""]

    output.append("## Wizard Flow")
    output.append("```")
    for step in steps:
        step_num = step['order']
        step_name = step.get('name', 'Unknown')
        step_id = step.get('id', '')
        hidden = step.get('isHidden')

        id_str = f" (id: {step_id})" if step_id else ""
        output.append(f"Step {step_num}: {step_name}{id_str}")

        if hidden:
            output.append(f"  └─ isHidden: {hidden}")
    output.append("```")

    output.append("")
    output.append("## Visibility Conditions")

    has_conditions = False
    for step in steps:
        hidden = step.get('isHidden')
        if hidden:
            has_conditions = True
            output.append(f"- **{step.get('name', 'Unknown')}**: Hidden when `{hidden}`")

    if not has_conditions:
        output.append("All steps are always visible (no conditional logic).")

    output.append("")
    output.append(f"Source: {REPOS[repo]} @ {version}")

    return "\n".join(output)


@mcp.tool()
def get_routes(repo: str = "acm") -> str:
    """
    Extracts navigation paths and route definitions from ACM Console.
    Useful for understanding the full navigation structure of the UI.

    Args:
        repo: Repository key - currently only 'acm' is supported

    Examples:
        get_routes()  # Get all ACM Console navigation paths

    Returns:
        List of navigation paths with their URL patterns.
    """
    if repo != "acm":
        return "Error: get_routes currently only supports 'acm' repository."

    version = state.get_version("acm")

    # Fetch the NavigationPath file
    content = state.gh_client.get_file_content(
        "frontend/src/NavigationPath.tsx",
        version,
        "acm"
    )

    if not content:
        # Try alternate path
        content = state.gh_client.get_file_content(
            "frontend/src/NavigationPath.ts",
            version,
            "acm"
        )

    if not content:
        return "Error: Could not fetch NavigationPath file from stolostron/console"

    paths = state.analyzer.extract_navigation_paths(content)

    if not paths:
        return "No navigation paths found in NavigationPath file"

    output = [f"Found {len(paths)} navigation path(s) in ACM Console:", ""]

    # Group by top-level route
    groups = {}
    for path_info in paths:
        name = path_info['name']
        path = path_info['path']

        # Determine group
        parts = path.strip('/').split('/')
        if len(parts) > 1:
            group = parts[1] if parts[0] == 'multicloud' else parts[0]
        else:
            group = 'root'

        if group not in groups:
            groups[group] = []
        groups[group].append(path_info)

    # Output by group
    for group, items in sorted(groups.items()):
        output.append(f"## {group.title()}")
        for item in items:
            output.append(f"  {item['name']}: {item['path']}")
        output.append("")

    output.append(f"Source: stolostron/console @ {version}")
    output.append("File: frontend/src/NavigationPath.tsx")

    return "\n".join(output)


@mcp.tool()
def get_patternfly_selectors(component: str = "") -> str:
    """
    Returns common PatternFly v6 CSS selectors for test automation.
    These selectors are useful when data-testid attributes are not available.

    Args:
        component: Optional - filter by component type (e.g., 'button', 'modal', 'table')
                   Leave empty to get all selectors.

    Examples:
        get_patternfly_selectors()  # Get all PatternFly selectors
        get_patternfly_selectors('button')  # Get button selectors only
        get_patternfly_selectors('modal')  # Get modal selectors only

    Returns:
        PatternFly v6 CSS selector reference catalog.
    """
    output = ["=== PatternFly v6 Selector Reference ===", ""]
    output.append("These selectors work with PatternFly v6 components in ACM Console.")
    output.append("Use as fallback when data-testid is not available.")
    output.append("")

    if component:
        # Filter to specific component
        component_lower = component.lower()
        if component_lower in PATTERNFLY_SELECTORS:
            selectors = PATTERNFLY_SELECTORS[component_lower]
            output.append(f"## {component.title()}")
            for name, selector in selectors.items():
                output.append(f"  {name}: {selector}")
        else:
            available = list(PATTERNFLY_SELECTORS.keys())
            return f"Unknown component '{component}'. Available: {', '.join(available)}"
    else:
        # Return all selectors
        for comp_name, selectors in PATTERNFLY_SELECTORS.items():
            output.append(f"## {comp_name.title()}")
            for name, selector in selectors.items():
                output.append(f"  {name}: {selector}")
            output.append("")

    output.append("")
    output.append("Usage in Cypress:")
    output.append("  cy.get('.pf-v6-c-button.pf-m-primary').click()")
    output.append("  cy.get('.pf-v6-c-modal-box').should('be.visible')")
    output.append("")
    output.append("Note: Prefer data-testid selectors when available for stability.")

    return "\n".join(output)
