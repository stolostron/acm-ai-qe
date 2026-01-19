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
    """Result of comparing timelines between automation and product repos."""
    selector: str
    element_id: str

    # Timeline data
    automation_timeline: Optional[SelectorTimeline] = None
    console_timeline: Optional[ElementTimeline] = None

    # Comparison results
    classification: str = "UNKNOWN"
    confidence: float = 0.0
    reasoning: str = ""

    # Detailed analysis
    console_changed_after_automation: Optional[bool] = None
    days_difference: Optional[int] = None
    element_removed_from_console: bool = False
    element_never_existed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selector": self.selector,
            "element_id": self.element_id,
            "automation_timeline": self.automation_timeline.to_dict() if self.automation_timeline else None,
            "console_timeline": self.console_timeline.to_dict() if self.console_timeline else None,
            "classification": self.classification,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "console_changed_after_automation": self.console_changed_after_automation,
            "days_difference": self.days_difference,
            "element_removed_from_console": self.element_removed_from_console,
            "element_never_existed": self.element_never_existed,
        }


@dataclass
class TimeoutPatternResult:
    """Result of analyzing timeout patterns across test failures."""
    total_failures: int
    timeout_count: int
    timeout_percentage: float
    is_infrastructure_pattern: bool
    classification: str
    confidence: float
    reasoning: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_failures": self.total_failures,
            "timeout_count": self.timeout_count,
            "timeout_percentage": round(self.timeout_percentage, 2),
            "is_infrastructure_pattern": self.is_infrastructure_pattern,
            "classification": self.classification,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
        }


class TimelineComparisonService:
    """
    Compare modification timelines between automation and product repositories.

    Uses git history to determine whether automation or product "fell behind"
    when a selector/element mismatch occurs.
    """

    # Console repository URL
    CONSOLE_REPO_URL = "https://github.com/stolostron/console.git"

    # Patterns to search for element IDs in console repo
    ELEMENT_SEARCH_PATTERNS = [
        'id="{element_id}"',           # JSX: id="google"
        "id='{element_id}'",           # JSX: id='google'
        'id: "{element_id}"',          # Object: id: "google"
        "id: '{element_id}'",          # Object: id: 'google'
        'data-testid="{element_id}"',  # data-testid="google"
        "data-testid='{element_id}'",
        'data-test-id="{element_id}"',
        "data-test-id='{element_id}'",
        'testId="{element_id}"',       # React prop
        "testId='{element_id}'",
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
        self.base_path = Path(base_path or '/tmp/z-stream-repos')
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.console_path: Optional[Path] = None
        self.automation_path: Optional[Path] = None

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
                '--depth', '200',  # Shallow clone with enough history for git log -S
                self.CONSOLE_REPO_URL,
                str(clone_dir)
            ]

            self.logger.info(f"Cloning console repo at branch {branch}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180
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
                        timeout=180
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
                    timeout=30
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
                        timeout=30
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
                    timeout=30
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
                timeout=30
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
                timeout=30
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

        Args:
            selector: The failing selector (e.g., "#google")

        Returns:
            TimelineComparisonResult with classification
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

        # Classify based on timelines
        result = self._classify_by_timeline(result)

        return result

    def _classify_by_timeline(self, result: TimelineComparisonResult) -> TimelineComparisonResult:
        """Apply classification logic based on timeline comparison."""

        auto = result.automation_timeline
        console = result.console_timeline

        # Case 1: Element doesn't exist in console
        if console and not console.exists_in_console:
            if console.last_modified_date:
                # Element was removed
                result.element_removed_from_console = True
                result.classification = "AUTOMATION_BUG"
                result.confidence = 0.90
                result.reasoning = (
                    f"Element '{result.element_id}' was removed from console "
                    f"(last seen: {console.last_modified_date.strftime('%Y-%m-%d')}). "
                    f"Automation uses selector '{result.selector}' which no longer exists. "
                    "Automation needs to be updated with the new selector."
                )
            else:
                # Element never existed in history we can see
                result.element_never_existed = True
                result.classification = "AUTOMATION_BUG"
                result.confidence = 0.85
                result.reasoning = (
                    f"Element '{result.element_id}' not found in console codebase. "
                    f"Automation uses selector '{result.selector}' that may never have existed "
                    "or was removed long ago. Automation needs to use the correct selector."
                )
            return result

        # Case 2: Both have dates - compare them
        if auto and auto.last_modified_date and console and console.last_modified_date:
            auto_date = auto.last_modified_date
            console_date = console.last_modified_date

            result.days_difference = abs((console_date - auto_date).days)
            result.console_changed_after_automation = console_date > auto_date

            if console_date > auto_date:
                # Console changed AFTER automation was last updated
                result.classification = "AUTOMATION_BUG"
                result.confidence = 0.92
                result.reasoning = (
                    f"Console updated element on {console_date.strftime('%Y-%m-%d')} "
                    f"(commit: {console.last_commit_sha[:8] if console.last_commit_sha else 'N/A'}). "
                    f"Automation selector was last updated on {auto_date.strftime('%Y-%m-%d')} "
                    f"({result.days_difference} days before). "
                    "Automation fell behind product changes and needs updating."
                )
            else:
                # Automation was updated AFTER console
                result.classification = "PRODUCT_BUG"
                result.confidence = 0.85
                result.reasoning = (
                    f"Automation selector was updated on {auto_date.strftime('%Y-%m-%d')}, "
                    f"after console last changed element on {console_date.strftime('%Y-%m-%d')}. "
                    "Element exists in console but may not be rendering correctly. "
                    "This could be a product rendering issue or the element is conditionally hidden."
                )
            return result

        # Case 3: Only have automation date
        if auto and auto.last_modified_date and (not console or not console.last_modified_date):
            result.classification = "AUTOMATION_BUG"
            result.confidence = 0.75
            result.reasoning = (
                f"Automation uses selector '{result.selector}' "
                f"(last updated: {auto.last_modified_date.strftime('%Y-%m-%d')}), "
                "but cannot find corresponding element in console. "
                "Likely using incorrect or outdated selector."
            )
            return result

        # Case 4: No timeline data available
        result.classification = "UNKNOWN"
        result.confidence = 0.30
        result.reasoning = (
            "Unable to determine timeline comparison. "
            "Neither automation nor console modification dates could be retrieved. "
            "Manual review recommended."
        )
        return result

    def analyze_timeout_pattern(
        self,
        failed_tests: List[Dict[str, Any]],
        env_healthy: bool = True,
    ) -> TimeoutPatternResult:
        """
        Analyze timeout patterns across test failures.

        If multiple tests timeout, it's likely an infrastructure issue.

        Args:
            failed_tests: List of failed test dictionaries with error_message
            env_healthy: Whether the environment is healthy

        Returns:
            TimeoutPatternResult with classification
        """
        total = len(failed_tests)
        timeout_count = 0

        for test in failed_tests:
            error = (test.get("error_message") or "").lower()
            if "timeout" in error or "timed out" in error:
                timeout_count += 1

        timeout_pct = (timeout_count / total * 100) if total > 0 else 0

        result = TimeoutPatternResult(
            total_failures=total,
            timeout_count=timeout_count,
            timeout_percentage=timeout_pct,
            is_infrastructure_pattern=False,
            classification="UNKNOWN",
            confidence=0.0,
            reasoning="",
        )

        # Pattern detection
        if timeout_count >= 2 and timeout_pct >= 50:
            result.is_infrastructure_pattern = True
            result.classification = "INFRASTRUCTURE"
            result.confidence = 0.85
            result.reasoning = (
                f"{timeout_count} of {total} tests ({timeout_pct:.0f}%) timed out. "
                "This pattern suggests slow cluster or Jenkins environment. "
                "Check infrastructure performance before investigating individual tests."
            )
        elif not env_healthy and timeout_count >= 1:
            result.is_infrastructure_pattern = True
            result.classification = "INFRASTRUCTURE"
            result.confidence = 0.80
            result.reasoning = (
                f"Environment is unhealthy and {timeout_count} test(s) timed out. "
                "Infrastructure issues are likely causing the timeouts."
            )
        elif timeout_count == 1 and total > 1:
            result.classification = "ELEMENT_SPECIFIC"
            result.confidence = 0.60
            result.reasoning = (
                f"Only 1 of {total} tests timed out. "
                "This is likely an element-specific timeout, not infrastructure. "
                "Treat as element_not_found for classification."
            )
        else:
            result.reasoning = "No clear timeout pattern detected."

        return result

    def cleanup(self):
        """Clean up cloned console repository."""
        if self.console_path and self.console_path.exists():
            try:
                shutil.rmtree(self.console_path)
                self.logger.info(f"Cleaned up console repo: {self.console_path}")
                self.console_path = None
            except Exception as e:
                self.logger.warning(f"Failed to cleanup console repo: {e}")
