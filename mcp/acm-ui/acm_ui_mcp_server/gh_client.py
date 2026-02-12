import subprocess
import json
import logging
from typing import Optional, Dict, Any, List
from functools import lru_cache

logger = logging.getLogger(__name__)

# Supported repositories
REPOS = {
    # Source code repositories
    "acm": "stolostron/console",
    "kubevirt": "kubevirt-ui/kubevirt-plugin",
    # QE automation repositories (organized by component)
    "acm-e2e": "stolostron/clc-ui-e2e",      # Cluster Lifecycle + RBAC UI (ACM 2.15+)
    "search-e2e": "stolostron/search-e2e-test",  # Search component
    "app-e2e": "stolostron/application-ui-test",  # Applications (ALC)
    "grc-e2e": "stolostron/acmqe-grc-test",       # Governance (GRC)
}

DEFAULT_REPO = "acm"

# =============================================================================
# VERSION MAPPINGS (Independent - ACM and CNV versions are NOT correlated)
# =============================================================================

# ACM Version to Console Branch Mapping
# ACM version determines which stolostron/console branch to use
ACM_VERSIONS = {
    "2.11": "release-2.11",
    "2.12": "release-2.12",
    "2.13": "release-2.13",
    "2.14": "release-2.14",
    "2.15": "release-2.15",
    "2.16": "release-2.16",
    "2.17": "main",  # Next unreleased
}

# CNV Version to KubeVirt-Plugin Branch Mapping
# CNV version should match the OCP/CNV version on your target managed cluster
CNV_VERSIONS = {
    "4.14": "release-4.14",
    "4.15": "release-4.15",
    "4.16": "release-4.16",
    "4.17": "release-4.17",
    "4.18": "release-4.18",
    "4.19": "release-4.19",
    "4.20": "release-4.20",
    "4.21": "release-4.21",
    "4.22": "main",  # Next unreleased
}

# Current version state markers
MAIN_ACM_VERSION = "2.17"
LATEST_ACM_GA = "2.16"
MAIN_CNV_VERSION = "4.22"
LATEST_CNV_GA = "4.21"


class GitHubClient:
    def __init__(self):
        self._check_gh_installed()

    def _check_gh_installed(self):
        try:
            subprocess.run(["gh", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("GitHub CLI (gh) is not installed or not in PATH.")

    def _get_repo(self, repo_key: str) -> str:
        """Gets the full repo name from the key."""
        return REPOS.get(repo_key, REPOS[DEFAULT_REPO])

    def _run_gh_command(self, args: list[str]) -> str:
        """Runs a gh command and returns the stdout."""
        try:
            result = subprocess.run(
                ["gh"] + args,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"gh command failed: {e.stderr}")
            raise RuntimeError(f"GitHub CLI command failed: {e.stderr}")

    @lru_cache(maxsize=200)
    def get_file_content(self, path: str, ref: str, repo_key: str = DEFAULT_REPO) -> str:
        """Fetches the content of a file from the repository."""
        repo = self._get_repo(repo_key)
        endpoint = f"repos/{repo}/contents/{path}?ref={ref}"
        try:
            content = self._run_gh_command([
                "api",
                endpoint,
                "-H", "Accept: application/vnd.github.v3.raw"
            ])
            return content
        except RuntimeError:
            return ""

    @lru_cache(maxsize=50)
    def get_tree(self, path: str, ref: str, repo_key: str = DEFAULT_REPO, recursive: bool = False) -> List[Dict[str, Any]]:
        """Fetches the file tree of a directory."""
        repo = self._get_repo(repo_key)
        endpoint = f"repos/{repo}/contents/{path}?ref={ref}"
        try:
            output = self._run_gh_command(["api", endpoint])
            return json.loads(output)
        except RuntimeError:
            return []

    def validate_ref(self, ref: str, repo_key: str = DEFAULT_REPO) -> bool:
        """Checks if a branch or tag exists."""
        repo = self._get_repo(repo_key)
        try:
            self._run_gh_command(["api", f"repos/{repo}/commits/{ref}", "--silent"])
            return True
        except RuntimeError:
            return False

    def search_code_in_repo(self, query: str, repo_key: str = DEFAULT_REPO) -> List[Dict[str, Any]]:
        """
        Searches for code in the repository using gh search code.
        Returns list of matching file paths.
        """
        repo = self._get_repo(repo_key)
        try:
            output = self._run_gh_command([
                "search", "code", query,
                "--repo", repo,
                "--json", "path",
                "--limit", "20"
            ])
            return json.loads(output) if output else []
        except RuntimeError:
            return []

    @staticmethod
    def get_available_repos() -> Dict[str, str]:
        """Returns the available repositories."""
        return REPOS.copy()
