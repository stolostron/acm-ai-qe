#!/usr/bin/env python3
"""
Repository Analysis Service
Real git clone and repository file analysis for test automation codebases

Usage:
    Clones repositories for AI to have full access during analysis.
    Uses git for cloning and file access.
"""

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Import centralized configuration
from .shared_utils import REPOS, TIMEOUTS


@dataclass
class SelectorHistory:
    """Git history for a selector"""
    selector: str
    file_path: str
    last_modified_date: Optional[str] = None
    last_commit_sha: Optional[str] = None
    last_commit_message: Optional[str] = None
    days_since_modified: Optional[int] = None


class RepositoryAnalysisService:
    """
    Repository Analysis Service
    Real git clone for AI full access
    """

    # Known test automation repositories - use centralized config
    # Can be overridden via Z_STREAM_AUTOMATION_REPOS environment variable
    @property
    def KNOWN_REPOS(self) -> Dict[str, str]:
        return REPOS.KNOWN_REPOS

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize Repository Analysis Service.

        Args:
            base_path: Base directory for cloning repositories
                      Default: /tmp/z-stream-repos
        """
        self.logger = logging.getLogger(__name__)
        default_base = os.environ.get('Z_STREAM_REPO_BASE_PATH', '/tmp/z-stream-repos')
        self.base_path = Path(base_path or default_base)

        # Create base directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Repository base path: {self.base_path}")

    def _infer_repo_from_job(self, job_name: str) -> Optional[str]:
        """Infer repository URL from Jenkins job name"""
        job_lower = job_name.lower()

        for key, url in self.KNOWN_REPOS.items():
            if key in job_lower:
                self.logger.info(f"Inferred repository {url} from job {job_name}")
                return url

        return None

    def _get_head_commit(self, repo_path: Path) -> Optional[str]:
        """Get the HEAD commit SHA"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.DEFAULT_COMMAND
            )

            if result.returncode == 0:
                return result.stdout.strip()

        except Exception:
            pass

        return None

    def clone_to(
        self,
        repo_url: str,
        branch: Optional[str],
        target_path: Path
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Clone a repository to a specific target path.

        This method clones the repository to a persistent location (e.g., runs/<dir>/repos/)
        instead of /tmp, allowing AI to have full access to the repo during analysis.

        Args:
            repo_url: Git repository URL
            branch: Branch to checkout (e.g., 'release-2.15')
            target_path: Directory to clone into (will be created if doesn't exist)

        Returns:
            Tuple of (success, commit_sha, error_message)
        """
        try:
            # Create target directory if needed
            target_path.mkdir(parents=True, exist_ok=True)

            # Build clone command (full clone for git history access)
            cmd = ['git', 'clone']

            if branch:
                cmd.extend(['--branch', branch])

            cmd.extend([repo_url, str(target_path)])

            self.logger.info(f"Cloning repository to: {target_path}")
            self.logger.debug(f"Clone command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.GIT_CLONE
            )

            if result.returncode != 0:
                # Check if directory already has content (target exists)
                if target_path.exists() and list(target_path.iterdir()):
                    # Try cloning into empty temp dir and moving
                    error_msg = f"Target directory not empty: {target_path}"
                    self.logger.error(error_msg)
                    return False, None, error_msg

                error_msg = f"Git clone failed: {result.stderr}"
                self.logger.error(error_msg)
                return False, None, error_msg

            # Get commit SHA
            commit_sha = self._get_head_commit(target_path)

            self.logger.info(f"Repository cloned successfully to: {target_path}")
            self.logger.info(f"Commit SHA: {commit_sha}")

            return True, commit_sha, None

        except subprocess.TimeoutExpired:
            error_msg = "Git clone timed out after 180s"
            self.logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Git clone error: {str(e)}"
            self.logger.error(error_msg)
            return False, None, error_msg
