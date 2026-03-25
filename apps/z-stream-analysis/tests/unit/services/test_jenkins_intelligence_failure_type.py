#!/usr/bin/env python3
"""Tests for refined failure type classification (GAP-01)."""

import pytest
from src.services.jenkins_intelligence_service import JenkinsIntelligenceService


class TestFailureTypeClassification:
    """Tests for _classify_failure_type with refined assertion types."""

    def setup_method(self):
        self.service = JenkinsIntelligenceService.__new__(JenkinsIntelligenceService)
        import logging
        self.service.logger = logging.getLogger(__name__)

    def test_assertion_data_equal(self):
        """Data assertion: expected value to equal another."""
        result = self.service._classify_failure_type("expected 'Ready' to equal 'Available'")
        assert result == 'assertion_data'

    def test_assertion_data_length(self):
        """Data assertion: expected array to have length."""
        result = self.service._classify_failure_type("expected [] to have length 5")
        assert result == 'assertion_data'

    def test_assertion_data_contain(self):
        """Data assertion: expected element to contain text."""
        result = self.service._classify_failure_type("expected '<div>' to contain 'cluster-name'")
        assert result == 'assertion_data'

    def test_assertion_data_boolean(self):
        """Data assertion: expected true to be false."""
        result = self.service._classify_failure_type("expected true to be false")
        assert result == 'assertion_data'

    def test_assertion_data_element_count(self):
        """Data assertion: expected to find N elements, but found M."""
        result = self.service._classify_failure_type("expected to find 5 elements, but found 0")
        assert result == 'assertion_data'

    def test_assertion_selector_exist(self):
        """Selector assertion: expected element to exist."""
        result = self.service._classify_failure_type("expected '#btn' to exist")
        assert result == 'assertion_selector'

    def test_assertion_selector_visible(self):
        """Selector assertion: expected element to be visible."""
        result = self.service._classify_failure_type("expected '.modal' to be.visible")
        assert result == 'assertion_selector'

    def test_assertion_generic(self):
        """Generic assertion without clear data/selector indicator."""
        result = self.service._classify_failure_type("AssertionError: some assert failed")
        assert result in ('assertion_selector', 'assertion_data')

    def test_timeout_unchanged(self):
        """Timeout type should remain unchanged."""
        result = self.service._classify_failure_type("Timed out retrying after 4000ms")
        assert result == 'timeout'

    def test_element_not_found_unchanged(self):
        """Element not found should remain unchanged."""
        result = self.service._classify_failure_type("Expected to find element: '#btn', but never found it")
        assert result == 'element_not_found'

    def test_network_unchanged(self):
        """Network error should remain unchanged."""
        result = self.service._classify_failure_type("Network error: connection refused")
        assert result == 'network'

    def test_server_error_unchanged(self):
        """Server error should remain unchanged."""
        result = self.service._classify_failure_type("500 Internal Server Error")
        assert result == 'server_error'


class TestIsDataAssertion:
    """Tests for _is_data_assertion static method."""

    def test_to_equal(self):
        assert JenkinsIntelligenceService._is_data_assertion("expected 'x' to equal 'y'") is True

    def test_to_have_length(self):
        assert JenkinsIntelligenceService._is_data_assertion("expected [] to have length 5") is True

    def test_to_contain(self):
        assert JenkinsIntelligenceService._is_data_assertion("expected '<div>' to contain 'text'") is True

    def test_to_be_true(self):
        assert JenkinsIntelligenceService._is_data_assertion("expected false to be true") is True

    def test_count_mismatch(self):
        assert JenkinsIntelligenceService._is_data_assertion("expected to find 5 elements, but found 0") is True

    def test_to_exist_is_not_data(self):
        assert JenkinsIntelligenceService._is_data_assertion("expected '#btn' to exist") is False

    def test_to_be_visible_is_not_data(self):
        assert JenkinsIntelligenceService._is_data_assertion("expected '.modal' to be visible") is False

    def test_empty_string(self):
        assert JenkinsIntelligenceService._is_data_assertion("") is False
