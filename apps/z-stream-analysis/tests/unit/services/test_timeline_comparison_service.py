#!/usr/bin/env python3
"""
Unit tests for TimelineComparisonService.

Tests the core logic for comparing modification timelines between
automation and console repositories to determine bug classification.
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


class TestTimelineClassification:
    """Test the timeline-based classification logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TimelineComparisonService()

    def test_classify_element_not_in_console(self):
        """Test classification when element doesn't exist in console."""
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

        classified = self.service._classify_by_timeline(result)

        assert classified.classification == "AUTOMATION_BUG"
        assert classified.confidence >= 0.85
        assert classified.element_removed_from_console is True
        assert "removed" in classified.reasoning.lower()

    def test_classify_console_changed_after_automation(self):
        """Test classification when console changed after automation."""
        result = TimelineComparisonResult(
            selector="#google",
            element_id="google",
            console_timeline=ElementTimeline(
                element_id="google",
                exists_in_console=True,
                last_modified_date=datetime(2026, 1, 10),  # Changed 10 days ago
                last_commit_sha="abc123",
            ),
            automation_timeline=SelectorTimeline(
                selector="#google",
                exists_in_automation=True,
                last_modified_date=datetime(2025, 6, 1),  # Not updated since 6 months ago
            ),
        )

        classified = self.service._classify_by_timeline(result)

        assert classified.classification == "AUTOMATION_BUG"
        assert classified.confidence >= 0.90
        assert classified.console_changed_after_automation is True
        assert classified.days_difference > 0
        assert "fell behind" in classified.reasoning.lower() or "automation" in classified.reasoning.lower()

    def test_classify_automation_changed_after_console(self):
        """Test classification when automation is more recent."""
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
                last_modified_date=datetime(2026, 1, 10),  # Updated recently
            ),
        )

        classified = self.service._classify_by_timeline(result)

        assert classified.classification == "PRODUCT_BUG"
        assert classified.confidence >= 0.80
        assert classified.console_changed_after_automation is False

    def test_classify_element_never_existed(self):
        """Test classification when element never existed in console."""
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

        classified = self.service._classify_by_timeline(result)

        assert classified.classification == "AUTOMATION_BUG"
        assert classified.element_never_existed is True

    def test_classify_no_timeline_data(self):
        """Test classification when no timeline data is available."""
        result = TimelineComparisonResult(
            selector="#unknown",
            element_id="unknown",
        )

        classified = self.service._classify_by_timeline(result)

        assert classified.classification == "UNKNOWN"
        assert classified.confidence < 0.50


class TestTimeoutPatternAnalysis:
    """Test timeout pattern detection for infrastructure issues."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TimelineComparisonService()

    def test_multiple_timeouts_infrastructure(self):
        """Test that multiple timeouts indicate infrastructure issue."""
        failed_tests = [
            {"test_name": "test1", "error_message": "Timed out after 30000ms"},
            {"test_name": "test2", "error_message": "Timeout waiting for element"},
            {"test_name": "test3", "error_message": "Timed out retrying"},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests)

        assert result.classification == "INFRASTRUCTURE"
        assert result.is_infrastructure_pattern is True
        assert result.timeout_count == 3
        assert result.timeout_percentage >= 50

    def test_single_timeout_not_infrastructure(self):
        """Test that a single timeout is not automatically infrastructure."""
        failed_tests = [
            {"test_name": "test1", "error_message": "Timed out waiting for #google"},
            {"test_name": "test2", "error_message": "Element not found: #button"},
            {"test_name": "test3", "error_message": "AssertionError: expected true"},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests)

        assert result.classification == "ELEMENT_SPECIFIC"
        assert result.is_infrastructure_pattern is False
        assert result.timeout_count == 1

    def test_unhealthy_env_with_timeout(self):
        """Test that timeout with unhealthy environment is infrastructure."""
        failed_tests = [
            {"test_name": "test1", "error_message": "Timed out after 30000ms"},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests, env_healthy=False)

        assert result.classification == "INFRASTRUCTURE"
        assert result.is_infrastructure_pattern is True

    def test_no_timeouts(self):
        """Test behavior with no timeout errors."""
        failed_tests = [
            {"test_name": "test1", "error_message": "Element not found"},
            {"test_name": "test2", "error_message": "AssertionError"},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests)

        assert result.timeout_count == 0
        assert result.is_infrastructure_pattern is False


class TestTimelineResultSerialization:
    """Test serialization of timeline results."""

    def test_timeline_comparison_result_to_dict(self):
        """Test TimelineComparisonResult serialization."""
        result = TimelineComparisonResult(
            selector="#google",
            element_id="google",
            classification="AUTOMATION_BUG",
            confidence=0.92,
            reasoning="Test reasoning",
            console_changed_after_automation=True,
            days_difference=45,
        )

        d = result.to_dict()

        assert d["selector"] == "#google"
        assert d["element_id"] == "google"
        assert d["classification"] == "AUTOMATION_BUG"
        assert d["confidence"] == 0.92
        assert d["console_changed_after_automation"] is True
        assert d["days_difference"] == 45

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
            is_infrastructure_pattern=True,
            classification="INFRASTRUCTURE",
            confidence=0.85,
            reasoning="3 of 5 tests (60%) timed out",
        )

        d = result.to_dict()

        assert d["total_failures"] == 5
        assert d["timeout_count"] == 3
        assert d["timeout_percentage"] == 60.0
        assert d["is_infrastructure_pattern"] is True
        assert d["classification"] == "INFRASTRUCTURE"


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
        assert result.is_infrastructure_pattern is False

    def test_analyze_none_error_message(self):
        """Test timeout analysis with None error message."""
        failed_tests = [
            {"test_name": "test1", "error_message": None},
        ]

        result = self.service.analyze_timeout_pattern(failed_tests)

        assert result.timeout_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
