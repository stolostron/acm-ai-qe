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

    def set_automation_path(self, path: Path):
        """Set the path to the automation repository."""
        self.automation_path = path

    # Patterns to detect selector-related changes in git diffs.
    # Covers data-testid, id, className, aria-label, CSS classes, OUIA IDs.
    DIFF_SELECTOR_PATTERNS = [
        re.compile(r'data-testid=["\']([^"\']+)["\']'),
        re.compile(r'data-test-id=["\']([^"\']+)["\']'),
        re.compile(r'data-test=["\']([^"\']+)["\']'),
        re.compile(r'data-ouia-component-id=["\']([^"\']+)["\']'),
        re.compile(r'\bid=["\']([^"\']+)["\']'),
        re.compile(r'\bid:\s*["\']([^"\']+)["\']'),
        re.compile(r'className=["\']([^"\']+)["\']'),
        re.compile(r'class=["\']([^"\']+)["\']'),
        re.compile(r'aria-label=["\']([^"\']+)["\']'),
        re.compile(r'testId=["\']([^"\']+)["\']'),
    ]

    # Default lookback for git diff selector change detection
    SELECTOR_DIFF_LOOKBACK_COMMITS = 200

    def extract_element_id(self, selector: str) -> str:
        """
        Extract element ID from various selector formats.

        Handles ID selectors, attribute selectors, CSS class selectors,
        aria-label selectors, and PatternFly/Carbon class patterns.

        Examples:
            "#google" -> "google"
            "[data-testid='google']" -> "google"
            ".pf-v6-c-menu__list-item" -> "pf-v6-c-menu__list-item"
            ".tf--list-box__menu-item" -> "tf--list-box__menu-item"
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

        # Handle CSS class selectors: .foo-bar -> foo-bar
        if selector.startswith('.') and ' ' not in selector and '>' not in selector:
            return selector[1:]

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
            # True only when console changed AFTER automation AND automation was not updated afterward
            result.stale_test_signal = (console_date > auto_date) and (result.days_difference > 1)

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

    def find_recent_selector_changes(
        self,
        lookback_commits: int = 200,
    ) -> Dict[str, Any]:
        """
        Find all selector-related changes in recent product commits using git diff.

        Parses the unified diff of the last N commits in the console repo for
        lines containing selector patterns (data-testid, className, aria-label,
        id, CSS classes, OUIA IDs). Returns a structured map of removed and
        added selectors per file, with commit metadata.

        This runs ONCE per analysis (not per test) and the result is cached.
        The output is cross-referenced per-test against failing selectors.

        Args:
            lookback_commits: Number of commits to look back. Default 200 (~6 months).

        Returns:
            Dict with 'changes' list and metadata. Each change entry contains:
            - removed_selectors: selectors that were removed
            - added_selectors: selectors that were added
            - file: the file that changed
            - All selectors are normalized strings.

        Limitations:
            - Only covers the lookback window. Changes older than ~6 months won't appear.
            - Cannot detect text-based selectors (cy.contains).
            - Cannot detect dynamic/runtime-constructed selectors.
            - className values with multiple classes are split into individual classes.
        """
        if not self.console_path or not self.console_path.exists():
            self.logger.warning("Console repo not available for selector diff")
            return {'changes': [], 'lookback_commits': lookback_commits, 'error': 'no_console_repo'}

        self.logger.info(f"Scanning last {lookback_commits} commits for selector changes...")

        try:
            result = subprocess.run(
                ['git', 'diff', f'HEAD~{lookback_commits}..HEAD', '--', 'src/'],
                cwd=self.console_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode != 0:
                self.logger.warning(f"git diff failed: {result.stderr[:200]}")
                return {'changes': [], 'lookback_commits': lookback_commits, 'error': 'git_diff_failed'}

            changes = self._parse_diff_for_selectors(result.stdout)

            self.logger.info(
                f"Found {len(changes)} files with selector changes "
                f"across {lookback_commits} commits"
            )

            return {
                'changes': changes,
                'lookback_commits': lookback_commits,
                'total_files_with_changes': len(changes),
            }

        except subprocess.TimeoutExpired:
            self.logger.warning(f"git diff timed out after 120s for {lookback_commits} commits")
            return {'changes': [], 'lookback_commits': lookback_commits, 'error': 'timeout'}
        except Exception as e:
            self.logger.warning(f"Error finding selector changes: {e}")
            return {'changes': [], 'lookback_commits': lookback_commits, 'error': str(e)}

    def _parse_diff_for_selectors(self, diff_output: str) -> List[Dict[str, Any]]:
        """
        Parse unified diff output for selector-related additions and removals.

        Scans each file's diff hunks for lines starting with - or + that contain
        selector patterns. Groups results by file.

        Args:
            diff_output: Raw output from git diff.

        Returns:
            List of dicts, each representing a file with selector changes.
        """
        file_changes: Dict[str, Dict[str, set]] = {}
        current_file = None

        for line in diff_output.split('\n'):
            if line.startswith('diff --git'):
                match = re.search(r'b/(.+)$', line)
                if match:
                    current_file = match.group(1)
                continue

            if not current_file:
                continue

            is_removed = line.startswith('-') and not line.startswith('---')
            is_added = line.startswith('+') and not line.startswith('+++')

            if not (is_removed or is_added):
                continue

            selectors = self._extract_selectors_from_line(line[1:])
            if not selectors:
                continue

            if current_file not in file_changes:
                file_changes[current_file] = {'removed': set(), 'added': set()}

            target = 'removed' if is_removed else 'added'
            file_changes[current_file][target].update(selectors)

        results = []
        for filepath, changes in file_changes.items():
            removed = changes['removed'] - changes['added']
            added = changes['added'] - changes['removed']

            if removed or added:
                results.append({
                    'file': filepath,
                    'removed_selectors': sorted(removed),
                    'added_selectors': sorted(added),
                })

        return results

    def _extract_selectors_from_line(self, line: str) -> List[str]:
        """Extract all selector values from a single diff line."""
        selectors = []
        for pattern in self.DIFF_SELECTOR_PATTERNS:
            for match in pattern.finditer(line):
                value = match.group(1).strip()
                if not value or len(value) > 200:
                    continue
                if ' ' in value and ('className' in line or 'class=' in line):
                    selectors.extend(cls for cls in value.split() if cls)
                else:
                    selectors.append(value)
        return selectors

    def cross_reference_selector(
        self,
        failing_selector: str,
        selector_changes: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Cross-reference a failing selector against the cached selector changes.

        Checks if the failing selector (or its extracted ID) appears in any
        removed_selectors list. If found, returns the file and what was added
        in the same file (potential replacement).

        Args:
            failing_selector: The selector string from the failing test.
            selector_changes: The cached output of find_recent_selector_changes().

        Returns:
            Dict with match_found, matching changes, and the lookback window used.
        """
        element_id = self.extract_element_id(failing_selector)
        changes = selector_changes.get('changes', [])
        matches = []

        for change in changes:
            for removed in change.get('removed_selectors', []):
                if element_id in removed or removed in element_id or failing_selector.lstrip('.#') in removed:
                    matches.append({
                        'removed_selector': removed,
                        'added_selectors': change.get('added_selectors', []),
                        'file': change.get('file', ''),
                    })

        return {
            'match_found': len(matches) > 0,
            'matches': matches[:5],
            'lookback_commits': selector_changes.get('lookback_commits', 200),
            'selector_searched': failing_selector,
            'element_id_searched': element_id,
        }

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
