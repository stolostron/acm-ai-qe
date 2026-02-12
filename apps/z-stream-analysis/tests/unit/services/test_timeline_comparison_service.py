#!/usr/bin/env python3
"""
Unit tests for TimelineComparisonService.

Tests the core logic for extracting factual timeline data from
automation and console repositories.

Note: Classification is now performed by AI, so these tests focus on
factual data extraction, not classification logic.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.services.timeline_comparison_service import (
    TimelineComparisonService,
    TimelineComparisonResult,
    ElementTimeline,
    SelectorTimeline,
    TimeoutPatternResult,
)


class TestElementIdExtraction:
    """Test selector to element ID extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TimelineComparisonService()

    def test_extract_id_from_hash_selector(self):
        """Test extracting ID from #selector format."""
        assert self.service.extract_element_id("#google") == "google"
        assert self.service.extract_element_id("#my-element") == "my-element"
        assert self.service.extract_element_id("#btn_submit") == "btn_submit"

    def test_extract_id_from_attribute_selector(self):
        """Test extracting ID from [data-testid='value'] format."""
        assert self.service.extract_element_id("[data-testid='google']") == "google"
        assert self.service.extract_element_id('[data-testid="submit-btn"]') == "submit-btn"
        assert self.service.extract_element_id("[data-cy='modal']") == "modal"

    def test_extract_id_from_plain_selector(self):
        """Test extracting ID from plain text."""
        assert self.service.extract_element_id("google") == "google"
        assert self.service.extract_element_id(".google") == "google"


class TestTimelineFactualData:
    """Test that timeline comparison returns factual data without classification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TimelineComparisonService()

    def test_timeline_result_has_factual_fields(self):
        """Test that TimelineComparisonResult contains factual data fields."""
        result = TimelineComparisonResult(
            selector="#google",
            element_id="google",
            console_timeline=ElementTimeline(
                element_id="google",
                exists_in_console=False,
                last_modified_date=datetime(2025, 1, 1),
            ),
            automation_timeline=SelectorTimeline(
                selector="#google",
                exists_in_automation=True,
                last_modified_date=datetime(2024, 6, 1),
            ),
        )

        # Verify factual fields exist
        assert result.selector == "#google"
        assert result.element_id == "google"
        assert result.console_timeline is not None
        assert result.automation_timeline is not None

        # Verify no classification fields (AI does classification now)
        assert not hasattr(result, 'classification')
        assert not hasattr(result, 'confidence')
        assert not hasattr(result, 'reasoning')

    def test_compute_timeline_facts_console_newer(self):
        """Test computing timeline facts when console was modified more recently."""
        result = TimelineComparisonResult(
            selector="#google",
            element_id="google",
            console_timeline=ElementTimeline(
                element_id="google",
                exists_in_console=True,
                last_modified_date=datetime(2026, 1, 10),
            ),
            automation_timeline=SelectorTimeline(
                selector="#google",
                exists_in_automation=True,
                last_modified_date=datetime(2025, 6, 1),
            ),
        )

        factual_result = self.service._compute_timeline_facts(result)

        assert factual_result.console_changed_after_automation is True
        assert factual_result.days_difference is not None
        assert factual_result.days_difference > 0

    def test_compute_timeline_facts_automation_newer(self):
        """Test computing timeline facts when automation was modified more recently."""
        result = TimelineComparisonResult(
            selector="#google",
            element_id="google",
            console_timeline=ElementTimeline(
                element_id="google",
                exists_in_console=True,
                last_modified_date=datetime(2025, 6, 1),
            ),
            automation_timeline=SelectorTimeline(
                selector="#google",
                exists_in_automation=True,
                last_modified_date=datetime(2026, 1, 10),
            ),
        )

        factual_result = self.service._compute_timeline_facts(result)

        assert factual_result.console_changed_after_automation is False

    def test_compute_timeline_facts_element_not_in_console(self):
        """Test computing timeline facts when element doesn't exist in console."""
        result = TimelineComparisonResult(
            selector="#google",
            element_id="google",
            console_timeline=ElementTimeline(
                element_id="google",
                exists_in_console=False,
                last_modified_date=datetime(2025, 1, 1),  # Removed on this date
            ),
            automation_timeline=SelectorTimeline(
                selector="#google",
                exists_in_automation=True,
                last_modified_date=datetime(2024, 6, 1),
            ),
        )

        factual_result = self.service._compute_timeline_facts(result)

        assert factual_result.element_removed_from_console is True

    def test_compute_timeline_facts_element_never_existed(self):
        """Test computing timeline facts when element never existed in console."""
        result = TimelineComparisonResult(
            selector="#nonexistent",
            element_id="nonexistent",
            console_timeline=ElementTimeline(
                element_id="nonexistent",
                exists_in_console=False,
                last_modified_date=None,  # Never existed
            ),
            automation_timeline=SelectorTimeline(
                selector="#nonexistent",
                exists_in_automation=True,
            ),
        )

        factual_result = self.service._compute_timeline_facts(result)

        assert factual_result.element_never_existed is True


class TestTimeoutPatternAnalysis:
    """Test timeout pattern detection for factual data extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TimelineComparisonService()

    def test_multiple_timeouts_detected(self):
        """Test that multiple timeouts are detected factually."""
        failed_tests = [
            {"test_name": "test1", "error_message": "Timed out after 30000ms"},
            {"test_name": "test2", "error_message": "Timeout waiting for element"},
            {"test_name": "test3", "error_message": "Timed out retrying"},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests)

        assert result.timeout_count == 3
        assert result.total_failures == 3
        assert result.timeout_percentage >= 50
        assert result.multiple_timeouts is True
        assert result.majority_timeouts is True
        # No classification field (AI determines classification)
        assert not hasattr(result, 'classification') or result.to_dict().get('classification') is None

    def test_single_timeout_not_majority(self):
        """Test that a single timeout among multiple failures is detected."""
        failed_tests = [
            {"test_name": "test1", "error_message": "Timed out waiting for #google"},
            {"test_name": "test2", "error_message": "Element not found: #button"},
            {"test_name": "test3", "error_message": "AssertionError: expected true"},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests)

        assert result.timeout_count == 1
        assert result.total_failures == 3
        assert result.multiple_timeouts is False
        assert result.majority_timeouts is False

    def test_unhealthy_env_flag_set(self):
        """Test that unhealthy environment flag is set when specified."""
        failed_tests = [
            {"test_name": "test1", "error_message": "Timed out after 30000ms"},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests, env_healthy=False)

        assert result.env_was_unhealthy is True
        assert result.timeout_count == 1

    def test_no_timeouts(self):
        """Test behavior with no timeout errors."""
        failed_tests = [
            {"test_name": "test1", "error_message": "Element not found"},
            {"test_name": "test2", "error_message": "AssertionError"},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests)

        assert result.timeout_count == 0
        assert result.total_failures == 2
        assert result.multiple_timeouts is False
        assert result.majority_timeouts is False


class TestStaleTestSignal:
    """Test stale_test_signal and product_commit_type derivation."""

    def setup_method(self):
        self.service = TimelineComparisonService()

    def test_stale_test_signal_true_when_product_newer(self):
        """stale_test_signal should be True when product changed after automation."""
        result = TimelineComparisonResult(
            selector="#btn",
            element_id="btn",
            console_timeline=ElementTimeline(
                element_id="btn",
                exists_in_console=True,
                last_modified_date=datetime(2026, 2, 5),
                last_commit_message="refactor: standardize button labels",
            ),
            automation_timeline=SelectorTimeline(
                selector="#btn",
                exists_in_automation=True,
                last_modified_date=datetime(2025, 11, 20),
            ),
        )

        factual = self.service._compute_timeline_facts(result)

        assert factual.stale_test_signal is True
        assert factual.console_changed_after_automation is True
        assert factual.days_difference == 77

    def test_stale_test_signal_false_when_automation_newer(self):
        """stale_test_signal should be False when automation is newer."""
        result = TimelineComparisonResult(
            selector="#btn",
            element_id="btn",
            console_timeline=ElementTimeline(
                element_id="btn",
                exists_in_console=True,
                last_modified_date=datetime(2025, 6, 1),
            ),
            automation_timeline=SelectorTimeline(
                selector="#btn",
                exists_in_automation=True,
                last_modified_date=datetime(2026, 1, 10),
            ),
        )

        factual = self.service._compute_timeline_facts(result)

        assert factual.stale_test_signal is False
        assert factual.console_changed_after_automation is False

    def test_stale_test_signal_false_when_no_dates(self):
        """stale_test_signal should be False when dates are missing."""
        result = TimelineComparisonResult(
            selector="#btn",
            element_id="btn",
            console_timeline=ElementTimeline(
                element_id="btn",
                exists_in_console=True,
            ),
            automation_timeline=SelectorTimeline(
                selector="#btn",
                exists_in_automation=True,
            ),
        )

        factual = self.service._compute_timeline_facts(result)

        assert factual.stale_test_signal is False

    def test_product_commit_type_set_from_console_message(self):
        """product_commit_type should be derived from console commit message."""
        result = TimelineComparisonResult(
            selector="#btn",
            element_id="btn",
            console_timeline=ElementTimeline(
                element_id="btn",
                exists_in_console=True,
                last_modified_date=datetime(2026, 2, 5),
                last_commit_message="feat: add new button variant",
            ),
            automation_timeline=SelectorTimeline(
                selector="#btn",
                exists_in_automation=True,
                last_modified_date=datetime(2025, 11, 20),
            ),
        )

        factual = self.service._compute_timeline_facts(result)

        assert factual.product_commit_type == "intentional_change"

    def test_product_commit_type_none_when_no_console(self):
        """product_commit_type should be None when no console timeline."""
        result = TimelineComparisonResult(
            selector="#btn",
            element_id="btn",
            console_timeline=None,
            automation_timeline=SelectorTimeline(
                selector="#btn",
                exists_in_automation=True,
            ),
        )

        factual = self.service._compute_timeline_facts(result)

        assert factual.product_commit_type is None


class TestClassifyCommitType:
    """Test _classify_commit_type static method."""

    def test_feat_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("feat: add dropdown") == "intentional_change"
        assert TimelineComparisonService._classify_commit_type("feat(ui): new modal") == "intentional_change"

    def test_feature_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("feature: new page") == "intentional_change"

    def test_refactor_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("refactor: clean up utils") == "intentional_change"

    def test_chore_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("chore: update deps") == "intentional_change"

    def test_style_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("style: format code") == "intentional_change"

    def test_perf_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("perf: optimize render") == "intentional_change"

    def test_build_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("build: update webpack config") == "intentional_change"

    def test_ci_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("ci: add lint step") == "intentional_change"

    def test_docs_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("docs: update readme") == "intentional_change"

    def test_test_is_intentional(self):
        assert TimelineComparisonService._classify_commit_type("test: add unit tests") == "intentional_change"

    def test_fix_is_fix_or_revert(self):
        assert TimelineComparisonService._classify_commit_type("fix: null pointer crash") == "fix_or_revert"
        assert TimelineComparisonService._classify_commit_type("fix(auth): token refresh") == "fix_or_revert"

    def test_revert_is_fix_or_revert(self):
        assert TimelineComparisonService._classify_commit_type("revert: bad commit abc123") == "fix_or_revert"

    def test_hotfix_is_fix_or_revert(self):
        assert TimelineComparisonService._classify_commit_type("hotfix: critical issue") == "fix_or_revert"

    def test_bugfix_is_fix_or_revert(self):
        assert TimelineComparisonService._classify_commit_type("bugfix: edge case") == "fix_or_revert"

    def test_no_prefix_is_ambiguous(self):
        assert TimelineComparisonService._classify_commit_type("Update button styles") == "ambiguous"
        assert TimelineComparisonService._classify_commit_type("merge branch main") == "ambiguous"

    def test_empty_is_ambiguous(self):
        assert TimelineComparisonService._classify_commit_type("") == "ambiguous"
        assert TimelineComparisonService._classify_commit_type(None) == "ambiguous"

    def test_case_insensitive(self):
        assert TimelineComparisonService._classify_commit_type("FEAT: uppercase prefix") == "intentional_change"
        assert TimelineComparisonService._classify_commit_type("Fix: capitalized") == "fix_or_revert"

    def test_prefix_without_separator_is_ambiguous(self):
        """Words like 'feature-flag' should not match — need separator after prefix."""
        assert TimelineComparisonService._classify_commit_type("fixing something") == "ambiguous"


class TestTimelineResultSerialization:
    """Test serialization of timeline results."""

    def test_timeline_comparison_result_to_dict(self):
        """Test TimelineComparisonResult serialization."""
        result = TimelineComparisonResult(
            selector="#google",
            element_id="google",
            console_changed_after_automation=True,
            days_difference=45,
            element_removed_from_console=False,
            element_never_existed=False,
        )

        d = result.to_dict()

        assert d["selector"] == "#google"
        assert d["element_id"] == "google"
        assert d["console_changed_after_automation"] is True
        assert d["days_difference"] == 45
        assert d["element_removed_from_console"] is False
        assert d["element_never_existed"] is False
        assert d["stale_test_signal"] is False
        assert d["product_commit_type"] is None
        # No classification fields
        assert "classification" not in d
        assert "confidence" not in d
        assert "reasoning" not in d

    def test_timeline_result_with_temporal_fields(self):
        """Test serialization with stale_test_signal and product_commit_type."""
        result = TimelineComparisonResult(
            selector="#btn",
            element_id="btn",
            console_changed_after_automation=True,
            days_difference=77,
            stale_test_signal=True,
            product_commit_type="intentional_change",
        )

        d = result.to_dict()

        assert d["stale_test_signal"] is True
        assert d["product_commit_type"] == "intentional_change"

    def test_element_timeline_to_dict(self):
        """Test ElementTimeline serialization."""
        timeline = ElementTimeline(
            element_id="google",
            exists_in_console=True,
            last_modified_date=datetime(2026, 1, 10),
            last_commit_sha="abc123",
            last_commit_message="Update selector",
            file_path="src/components/Form.tsx",
        )

        d = timeline.to_dict()

        assert d["element_id"] == "google"
        assert d["exists_in_console"] is True
        assert "2026-01-10" in d["last_modified_date"]
        assert d["last_commit_sha"] == "abc123"

    def test_timeout_pattern_result_to_dict(self):
        """Test TimeoutPatternResult serialization."""
        result = TimeoutPatternResult(
            total_failures=5,
            timeout_count=3,
            timeout_percentage=60.0,
            multiple_timeouts=True,
            majority_timeouts=True,
            env_was_unhealthy=False,
        )

        d = result.to_dict()

        assert d["total_failures"] == 5
        assert d["timeout_count"] == 3
        assert d["timeout_percentage"] == 60.0
        assert d["multiple_timeouts"] is True
        assert d["majority_timeouts"] is True
        assert d["env_was_unhealthy"] is False
        # No classification fields
        assert "classification" not in d
        assert "confidence" not in d
        assert "reasoning" not in d
        assert "is_infrastructure_pattern" not in d


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TimelineComparisonService()

    def test_empty_selector(self):
        """Test handling of empty selector."""
        result = self.service.extract_element_id("")
        assert result == ""

    def test_complex_selector(self):
        """Test handling of complex selectors."""
        # Should extract the main identifier
        assert self.service.extract_element_id("#main-form input[type='text']") == "main-form input[type='text']"

    def test_analyze_empty_test_list(self):
        """Test timeout analysis with empty test list."""
        result = self.service.analyze_timeout_pattern([])

        assert result.total_failures == 0
        assert result.timeout_count == 0
        assert result.multiple_timeouts is False
        assert result.majority_timeouts is False

    def test_analyze_none_error_message(self):
        """Test timeout analysis with None error message."""
        failed_tests = [
            {"test_name": "test1", "error_message": None},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests)

        assert result.timeout_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
