#!/usr/bin/env python3
"""
Timeline Comparison Service

Compares modification dates between automation and product (console) repositories
to definitively classify element_not_found and timeout errors.

Core Logic:
- If console changed AFTER automation: AUTOMATION_BUG (automation fell behind)
- If automation changed AFTER console: PRODUCT_BUG (product broke something)
- If element doesn't exist in console: AUTOMATION_BUG (using wrong selector)

This provides definitive classification based on git history comparison.
"""

import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import centralized configuration
from .shared_utils import REPOS, TIMEOUTS, THRESHOLDS


@dataclass
class ElementTimeline:
    """Timeline information for a UI element in the product repo."""
    element_id: str
    exists_in_console: bool
    last_modified_date: Optional[datetime] = None
    last_commit_sha: Optional[str] = None
    last_commit_message: Optional[str] = None
    file_path: Optional[str] = None
    search_patterns_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "exists_in_console": self.exists_in_console,
            "last_modified_date": self.last_modified_date.isoformat() if self.last_modified_date else None,
            "last_commit_sha": self.last_commit_sha,
            "last_commit_message": self.last_commit_message,
            "file_path": self.file_path,
            "search_patterns_used": self.search_patterns_used,
        }


@dataclass
class SelectorTimeline:
    """Timeline information for a selector in the automation repo."""
    selector: str
    exists_in_automation: bool
    last_modified_date: Optional[datetime] = None
    last_commit_sha: Optional[str] = None
    last_commit_message: Optional[str] = None
    file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selector": self.selector,
            "exists_in_automation": self.exists_in_automation,
            "last_modified_date": self.last_modified_date.isoformat() if self.last_modified_date else None,
            "last_commit_sha": self.last_commit_sha,
            "last_commit_message": self.last_commit_message,
            "file_path": self.file_path,
        }


@dataclass
class TimelineComparisonResult:
    """
    Result of comparing timelines between automation and product repos.

    Note: This provides FACTUAL DATA only. AI performs the classification
    based on this data. No pre-calculated classification is included.
    """
    selector: str
    element_id: str

    # Timeline data
    automation_timeline: Optional[SelectorTimeline] = None
    console_timeline: Optional[ElementTimeline] = None

    # Factual analysis (no classification - AI determines this)
    console_changed_after_automation: Optional[bool] = None
    days_difference: Optional[int] = None
    element_removed_from_console: bool = False
    element_never_existed: bool = False

    # Derived temporal signals
    stale_test_signal: bool = False  # True when product changed after test AND test not updated since
    product_commit_type: Optional[str] = None  # intentional_change | fix_or_revert | ambiguous

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selector": self.selector,
            "element_id": self.element_id,
            "automation_timeline": self.automation_timeline.to_dict() if self.automation_timeline else None,
            "console_timeline": self.console_timeline.to_dict() if self.console_timeline else None,
            "console_changed_after_automation": self.console_changed_after_automation,
            "days_difference": self.days_difference,
            "element_removed_from_console": self.element_removed_from_console,
            "element_never_existed": self.element_never_existed,
            "stale_test_signal": self.stale_test_signal,
            "product_commit_type": self.product_commit_type,
        }


@dataclass
class TimeoutPatternResult:
    """
    Result of analyzing timeout patterns across test failures.

    Note: Provides FACTUAL DATA only. AI uses this to determine classification.
    """
    total_failures: int
    timeout_count: int
    timeout_percentage: float
    # Factual flags for AI to use in classification
    multiple_timeouts: bool = False  # True if 2+ tests timed out
    majority_timeouts: bool = False  # True if >=50% of failures are timeouts
    env_was_unhealthy: bool = False  # Environment health status at time of analysis

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_failures": self.total_failures,
            "timeout_count": self.timeout_count,
            "timeout_percentage": round(self.timeout_percentage, 2),
            "multiple_timeouts": self.multiple_timeouts,
            "majority_timeouts": self.majority_timeouts,
            "env_was_unhealthy": self.env_was_unhealthy,
        }


class TimelineComparisonService:
    """
    Compare modification timelines between automation and product repositories.

    Uses git history to determine whether automation or product "fell behind"
    when a selector/element mismatch occurs.
    """

    # Console repository URL - use centralized config (can be overridden via env var)
    @property
    def CONSOLE_REPO_URL(self) -> str:
        return REPOS.CONSOLE_REPO_URL

    # KubeVirt plugin repository URL - use centralized config
    @property
    def KUBEVIRT_REPO_URL(self) -> str:
        return REPOS.KUBEVIRT_REPO_URL

    # Patterns to search for element IDs in console repo
    # Ordered by frequency in React/ACM codebases - data-testid patterns first
    # CRITICAL: Git history search uses [:3] slice, so most common patterns must be first
    ELEMENT_SEARCH_PATTERNS = [
        # data-testid is most common in React/ACM - check first
        'data-testid="{element_id}"',
        "data-testid='{element_id}'",
        'data-test-id="{element_id}"',
        "data-test-id='{element_id}'",
        # React testId prop
        'testId="{element_id}"',
        "testId='{element_id}'",
        # Standard id attribute (less common in React)
        'id="{element_id}"',
        "id='{element_id}'",
        'id: "{element_id}"',
        "id: '{element_id}'",
    ]

    # File extensions to search in console repo
    CONSOLE_EXTENSIONS = ['.tsx', '.jsx', '.ts', '.js']

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize Timeline Comparison Service.

        Args:
            base_path: Base directory for cloning repositories.
                      Default: /tmp/z-stream-repos
        """
        self.logger = logging.getLogger(__name__)
        default_base = os.environ.get('Z_STREAM_REPO_BASE_PATH', '/tmp/z-stream-repos')
        self.base_path = Path(base_path or default_base)
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.console_path: Optional[Path] = None
        self.automation_path: Optional[Path] = None
        self.kubevirt_path: Optional[Path] = None

    def clone_console_repo(self, branch: str = "main") -> Tuple[Optional[Path], Optional[str]]:
        """
        Clone the stolostron/console repository.

        Args:
            branch: Branch to checkout (should match automation branch, e.g., release-2.15)

        Returns:
            Tuple of (clone_path, error_message)
        """
        timestamp = int(time.time())
        clone_dir = self.base_path / f"console_{timestamp}"

        try:
            cmd = [
                'git', 'clone',
                '--branch', branch,
                '--depth', str(THRESHOLDS.GIT_SHALLOW_CLONE_DEPTH),  # Shallow clone with enough history
                self.CONSOLE_REPO_URL,
                str(clone_dir)
            ]

            self.logger.info(f"Cloning console repo at branch {branch}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.GIT_CLONE
            )

            if result.returncode != 0:
                # Try with main if branch doesn't exist
                if "not find remote branch" in result.stderr or "not found" in result.stderr.lower():
                    self.logger.warning(f"Branch {branch} not found in console, trying main")
                    cmd[3] = "main"
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=TIMEOUTS.GIT_CLONE
                    )

                if result.returncode != 0:
                    error = f"Git clone failed: {result.stderr}"
                    self.logger.error(error)
                    return None, error

            self.console_path = clone_dir
            self.logger.info(f"Console repo cloned to: {clone_dir}")
            return clone_dir, None

        except subprocess.TimeoutExpired:
            error = "Git clone timed out after 180s"
            self.logger.error(error)
            return None, error
        except Exception as e:
            error = f"Git clone error: {str(e)}"
            self.logger.error(error)
            return None, error

    def set_automation_path(self, path: Path):
        """Set the path to the automation repository."""
        self.automation_path = path

    def extract_element_id(self, selector: str) -> str:
        """
        Extract element ID from various selector formats.

        Examples:
            "#google" -> "google"
            "[data-testid='google']" -> "google"
            "#my-element" -> "my-element"
        """
        # Handle ID selectors: #google -> google
        if selector.startswith('#'):
            return selector[1:]

        # Handle attribute selectors: [data-testid='google'] -> google
        match = re.search(r"\[[\w-]+=['\"]([^'\"]+)['\"]\]", selector)
        if match:
            return match.group(1)

        # Handle data-* selectors: data-cy=google -> google
        match = re.search(r"data-[\w-]+=['\"]?([^'\"\]]+)['\"]?", selector)
        if match:
            return match.group(1)

        # Return as-is if no pattern matches
        return selector.strip('#.[]')

    def element_exists_in_console(self, element_id: str) -> Tuple[bool, Optional[str], List[str]]:
        """
        Check if an element ID exists in the console codebase.

        Args:
            element_id: The element ID to search for

        Returns:
            Tuple of (exists, file_path, patterns_searched)
        """
        if not self.console_path or not self.console_path.exists():
            self.logger.warning("Console repo not cloned")
            return False, None, []

        patterns_searched = []

        for pattern_template in self.ELEMENT_SEARCH_PATTERNS:
            pattern = pattern_template.format(element_id=element_id)
            patterns_searched.append(pattern)

            try:
                result = subprocess.run(
                    ['git', 'grep', '-l', pattern, '--', 'src/'],
                    cwd=self.console_path,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUTS.GIT_LOG
                )

                if result.returncode == 0 and result.stdout.strip():
                    files = result.stdout.strip().split('\n')
                    self.logger.info(f"Found element '{element_id}' with pattern '{pattern}' in {files[0]}")
                    return True, files[0], patterns_searched

            except Exception as e:
                self.logger.debug(f"Error searching for pattern {pattern}: {e}")

        self.logger.info(f"Element '{element_id}' not found in console repo")
        return False, None, patterns_searched

    def get_element_last_modified(self, element_id: str) -> Optional[ElementTimeline]:
        """
        Get when an element was last modified in the console repo.

        Args:
            element_id: The element ID to search for

        Returns:
            ElementTimeline with modification info
        """
        if not self.console_path:
            return None

        exists, file_path, patterns_searched = self.element_exists_in_console(element_id)

        timeline = ElementTimeline(
            element_id=element_id,
            exists_in_console=exists,
            file_path=file_path,
            search_patterns_used=patterns_searched,
        )

        if not exists:
            # Try to find when it was removed (search in git history)
            for pattern_template in self.ELEMENT_SEARCH_PATTERNS[:3]:  # Check main patterns
                pattern = pattern_template.format(element_id=element_id)
                try:
                    # Search for pattern in git history
                    result = subprocess.run(
                        ['git', 'log', '-1', '--format=%H|%ai|%s', '-S', pattern, '--', 'src/'],
                        cwd=self.console_path,
                        capture_output=True,
                        text=True,
                        timeout=TIMEOUTS.GIT_LOG
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        parts = result.stdout.strip().split('|', 2)
                        if len(parts) >= 3:
                            timeline.last_commit_sha = parts[0]
                            timeline.last_commit_message = parts[2]
                            try:
                                date_str = parts[1].split()[0]
                                timeline.last_modified_date = datetime.fromisoformat(date_str)
                            except Exception:
                                pass
                            self.logger.info(f"Element '{element_id}' was last seen in commit {parts[0][:8]}")
                            break
                except Exception as e:
                    self.logger.debug(f"Error searching git history: {e}")

            return timeline

        # Element exists - get its last modification date
        for pattern_template in self.ELEMENT_SEARCH_PATTERNS[:3]:
            pattern = pattern_template.format(element_id=element_id)
            try:
                result = subprocess.run(
                    ['git', 'log', '-1', '--format=%H|%ai|%s', '-S', pattern, '--', 'src/'],
                    cwd=self.console_path,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUTS.GIT_LOG
                )

                if result.returncode == 0 and result.stdout.strip():
                    parts = result.stdout.strip().split('|', 2)
                    if len(parts) >= 3:
                        timeline.last_commit_sha = parts[0]
                        timeline.last_commit_message = parts[2]
                        try:
                            date_str = parts[1].split()[0]
                            timeline.last_modified_date = datetime.fromisoformat(date_str)
                        except Exception:
                            pass
                        break
            except Exception as e:
                self.logger.debug(f"Error getting git log: {e}")

        return timeline

    def get_selector_last_modified(self, selector: str) -> Optional[SelectorTimeline]:
        """
        Get when a selector was last modified in the automation repo.

        Args:
            selector: The selector string (e.g., "#google")

        Returns:
            SelectorTimeline with modification info
        """
        if not self.automation_path:
            return None

        timeline = SelectorTimeline(
            selector=selector,
            exists_in_automation=False,
        )

        try:
            # Search for selector in automation repo
            result = subprocess.run(
                ['git', 'grep', '-l', selector, '--', 'cypress/'],
                cwd=self.automation_path,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.GIT_LOG
            )

            if result.returncode == 0 and result.stdout.strip():
                files = result.stdout.strip().split('\n')
                timeline.exists_in_automation = True
                timeline.file_path = files[0]

            # Get git history for selector
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%H|%ai|%s', '-S', selector, '--', 'cypress/'],
                cwd=self.automation_path,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.GIT_LOG
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split('|', 2)
                if len(parts) >= 3:
                    timeline.last_commit_sha = parts[0]
                    timeline.last_commit_message = parts[2]
                    try:
                        date_str = parts[1].split()[0]
                        timeline.last_modified_date = datetime.fromisoformat(date_str)
                    except Exception:
                        pass

        except Exception as e:
            self.logger.debug(f"Error getting selector history: {e}")

        return timeline

    def compare_timelines(self, selector: str) -> TimelineComparisonResult:
        """
        Compare modification timelines between automation and console repos.

        Returns FACTUAL DATA only - AI performs classification based on this data.

        Args:
            selector: The failing selector (e.g., "#google")

        Returns:
            TimelineComparisonResult with factual timeline data (no classification)
        """
        element_id = self.extract_element_id(selector)

        result = TimelineComparisonResult(
            selector=selector,
            element_id=element_id,
        )

        # Get automation timeline
        result.automation_timeline = self.get_selector_last_modified(selector)

        # Get console timeline
        result.console_timeline = self.get_element_last_modified(element_id)

        # Compute factual analysis (no classification - AI does this)
        result = self._compute_timeline_facts(result)

        return result

    def _compute_timeline_facts(self, result: TimelineComparisonResult) -> TimelineComparisonResult:
        """
        Compute factual timeline data without classification.

        AI will use this factual data to make classification decisions.
        """
        auto = result.automation_timeline
        console = result.console_timeline

        # Fact 1: Does element exist in console?
        if console and not console.exists_in_console:
            if console.last_modified_date:
                # Element was removed (we found it in git history)
                result.element_removed_from_console = True
            else:
                # Element never existed in history we can see
                result.element_never_existed = True

        # Fact 2: Compare dates if both are available
        if auto and auto.last_modified_date and console and console.last_modified_date:
            auto_date = auto.last_modified_date
            console_date = console.last_modified_date

            result.days_difference = abs((console_date - auto_date).days)
            result.console_changed_after_automation = console_date > auto_date

            # Fact 3: Stale test signal — product changed after test AND test not updated since
            result.stale_test_signal = console_date > auto_date

        # Fact 4: Classify the product commit message type
        if console and console.last_commit_message:
            result.product_commit_type = self._classify_commit_type(console.last_commit_message)

        return result

    @staticmethod
    def _classify_commit_type(message: str) -> str:
        """
        Classify a git commit message into a change type category.

        Uses conventional commit prefixes to determine whether the change
        was intentional (feature/refactor) vs a fix/revert vs ambiguous.

        Args:
            message: Git commit message string

        Returns:
            'intentional_change' for feat/refactor/chore/style/perf
            'fix_or_revert' for fix/revert/hotfix
            'ambiguous' if no conventional prefix matches
        """
        if not message:
            return "ambiguous"

        lower = message.lower().strip()

        # fix/revert patterns
        fix_patterns = re.compile(
            r'^(fix|revert|hotfix|bugfix)[\s(:!]'
        )
        if fix_patterns.match(lower):
            return "fix_or_revert"

        # Intentional change patterns
        intentional_patterns = re.compile(
            r'^(feat|feature|refactor|chore|style|perf|build|ci|docs|test)[\s(:!]'
        )
        if intentional_patterns.match(lower):
            return "intentional_change"

        return "ambiguous"

    def analyze_timeout_pattern(
        self,
        failed_tests: List[Dict[str, Any]],
        env_healthy: bool = True,
    ) -> TimeoutPatternResult:
        """
        Analyze timeout patterns across test failures.

        Returns FACTUAL DATA only - AI performs classification based on this data.

        Args:
            failed_tests: List of failed test dictionaries with error_message
            env_healthy: Whether the environment is healthy

        Returns:
            TimeoutPatternResult with factual pattern data (no classification)
        """
        total = len(failed_tests)
        timeout_count = 0

        for test in failed_tests:
            error = (test.get("error_message") or "").lower()
            if "timeout" in error or "timed out" in error:
                timeout_count += 1

        timeout_pct = (timeout_count / total * 100) if total > 0 else 0

        # Return factual data only - AI will determine classification
        return TimeoutPatternResult(
            total_failures=total,
            timeout_count=timeout_count,
            timeout_percentage=timeout_pct,
            multiple_timeouts=timeout_count >= THRESHOLDS.MULTIPLE_TIMEOUTS_MIN,
            majority_timeouts=timeout_pct >= THRESHOLDS.MAJORITY_TIMEOUT_PERCENT,
            env_was_unhealthy=not env_healthy,
        )

    def clone_console_to(
        self,
        branch: str,
        target_path: Path,
        acm_version: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Clone the console repository with improved branch detection.

        This method clones to a persistent location (e.g., runs/<dir>/repos/console)
        instead of /tmp, allowing AI to have full access during analysis.

        Branch selection priority:
        1. Specified branch (e.g., from automation repo)
        2. ACM version-based branch (e.g., release-2.15)
        3. Main branch as fallback

        Args:
            branch: Branch to checkout (should match automation branch)
            target_path: Directory to clone into
            acm_version: Optional ACM version string (e.g., "2.15", "2.14")

        Returns:
            Tuple of (success, error_message)
        """
        # Build list of branches to try
        branches_to_try = [branch]

        # Add ACM version-based branch if available and different
        if acm_version:
            version_branch = f"release-{acm_version}"
            if version_branch not in branches_to_try:
                branches_to_try.append(version_branch)

        # Always include main as fallback
        if "main" not in branches_to_try:
            branches_to_try.append("main")

        self.logger.info(f"Console clone: will try branches in order: {branches_to_try}")

        # Try each branch in order
        for try_branch in branches_to_try:
            # Verify branch exists before cloning
            if not self._verify_branch_exists(try_branch):
                self.logger.warning(f"Branch '{try_branch}' does not exist in console repo")
                continue

            success, error = self._try_clone_branch(try_branch, target_path)
            if success:
                self.logger.info(f"Console repo cloned successfully at branch: {try_branch}")
                return True, None

            self.logger.warning(f"Clone failed for branch '{try_branch}': {error}")
            # Clean up failed clone attempt
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)

        return False, f"Could not clone console repo (tried: {branches_to_try})"

    def _verify_branch_exists(self, branch: str) -> bool:
        """
        Verify a branch exists in the console repo using git ls-remote.

        Args:
            branch: Branch name to verify

        Returns:
            True if branch exists, False otherwise
        """
        try:
            result = subprocess.run(
                ['git', 'ls-remote', '--heads', self.CONSOLE_REPO_URL, branch],
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.GIT_LOG
            )
            exists = result.returncode == 0 and branch in result.stdout
            if exists:
                self.logger.debug(f"Branch '{branch}' exists in console repo")
            return exists
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout checking if branch '{branch}' exists")
            return False
        except Exception as e:
            self.logger.warning(f"Error checking branch existence: {e}")
            return False

    def _try_clone_branch(self, branch: str, target_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Attempt to clone a specific branch.

        Args:
            branch: Branch to clone
            target_path: Directory to clone into

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create target directory if needed
            target_path.mkdir(parents=True, exist_ok=True)

            cmd = [
                'git', 'clone',
                '--branch', branch,
                self.CONSOLE_REPO_URL,
                str(target_path)
            ]

            self.logger.info(f"Cloning console repo branch '{branch}' to: {target_path}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.GIT_CLONE
            )

            if result.returncode != 0:
                error = f"Git clone failed: {result.stderr}"
                return False, error

            self.console_path = target_path
            return True, None

        except subprocess.TimeoutExpired:
            return False, "Git clone timed out after 180s"
        except Exception as e:
            return False, f"Git clone error: {str(e)}"

    def cleanup(self):
        """Clean up cloned console and kubevirt repositories."""
        if self.console_path and self.console_path.exists():
            try:
                shutil.rmtree(self.console_path)
                self.logger.info(f"Cleaned up console repo: {self.console_path}")
                self.console_path = None
            except Exception as e:
                self.logger.warning(f"Failed to cleanup console repo: {e}")

        if self.kubevirt_path and self.kubevirt_path.exists():
            try:
                shutil.rmtree(self.kubevirt_path)
                self.logger.info(f"Cleaned up kubevirt repo: {self.kubevirt_path}")
                self.kubevirt_path = None
            except Exception as e:
                self.logger.warning(f"Failed to cleanup kubevirt repo: {e}")

    def clone_kubevirt_to(
        self,
        branch: str,
        target_path: Path
    ) -> Tuple[bool, Optional[str]]:
        """
        Clone the kubevirt-plugin repository with intelligent branch detection.

        This method clones to a persistent location (e.g., runs/<dir>/repos/kubevirt-plugin)
        instead of /tmp, allowing AI to have full access during analysis.

        The kubevirt-plugin repo contains virtualization feature UI components that
        are integrated into ACM console but maintained in a separate repository.

        Branch selection priority:
        1. Specified branch (e.g., from automation repo)
        2. Main branch as fallback

        Args:
            branch: Branch to checkout (should match automation branch if possible)
            target_path: Directory to clone into

        Returns:
            Tuple of (success, error_message)
        """
        # Build list of branches to try
        branches_to_try = [branch]

        # Always include main as fallback
        if "main" not in branches_to_try:
            branches_to_try.append("main")

        # Also try master as kubevirt-plugin may use it
        if "master" not in branches_to_try:
            branches_to_try.append("master")

        self.logger.info(f"KubeVirt clone: will try branches in order: {branches_to_try}")

        # Try each branch in order
        for try_branch in branches_to_try:
            # Verify branch exists before cloning
            if not self._verify_kubevirt_branch_exists(try_branch):
                self.logger.warning(f"Branch '{try_branch}' does not exist in kubevirt-plugin repo")
                continue

            success, error = self._try_clone_kubevirt_branch(try_branch, target_path)
            if success:
                self.logger.info(f"KubeVirt plugin repo cloned successfully at branch: {try_branch}")
                return True, None

            self.logger.warning(f"Clone failed for branch '{try_branch}': {error}")
            # Clean up failed clone attempt
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)

        return False, f"Could not clone kubevirt-plugin repo (tried: {branches_to_try})"

    def _verify_kubevirt_branch_exists(self, branch: str) -> bool:
        """
        Verify a branch exists in the kubevirt-plugin repo using git ls-remote.

        Args:
            branch: Branch name to verify

        Returns:
            True if branch exists, False otherwise
        """
        try:
            result = subprocess.run(
                ['git', 'ls-remote', '--heads', self.KUBEVIRT_REPO_URL, branch],
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.GIT_LS_REMOTE
            )
            exists = result.returncode == 0 and branch in result.stdout
            if exists:
                self.logger.debug(f"Branch '{branch}' exists in kubevirt-plugin repo")
            return exists
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Timeout checking if branch '{branch}' exists in kubevirt-plugin")
            return False
        except Exception as e:
            self.logger.warning(f"Error checking kubevirt branch existence: {e}")
            return False

    def _try_clone_kubevirt_branch(self, branch: str, target_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Attempt to clone a specific branch of kubevirt-plugin.

        Args:
            branch: Branch to clone
            target_path: Directory to clone into

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create target directory if needed
            target_path.mkdir(parents=True, exist_ok=True)

            cmd = [
                'git', 'clone',
                '--branch', branch,
                self.KUBEVIRT_REPO_URL,
                str(target_path)
            ]

            self.logger.info(f"Cloning kubevirt-plugin repo branch '{branch}' to: {target_path}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.GIT_CLONE
            )

            if result.returncode != 0:
                error = f"Git clone failed: {result.stderr}"
                return False, error

            self.kubevirt_path = target_path
            return True, None

        except subprocess.TimeoutExpired:
            return False, "Git clone timed out after 180s"
        except Exception as e:
            return False, f"Git clone error: {str(e)}"
