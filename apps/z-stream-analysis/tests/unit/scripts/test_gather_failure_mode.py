#!/usr/bin/env python3
"""Tests for failure mode classification (GAP-01 + GAP-02)."""

import pytest
from src.scripts.gather import DataGatherer


class TestClassifyFailureMode:
    """Tests for DataGatherer._classify_failure_mode static method."""

    def test_server_error(self):
        result = DataGatherer._classify_failure_mode('server_error', '500 error', None, None)
        assert result == 'server_error'

    def test_render_failure(self):
        result = DataGatherer._classify_failure_mode('', 'page has class no-js', None, None)
        assert result == 'render_failure'

    def test_data_incorrect_with_console_found(self):
        """Data assertion + selector exists = data_incorrect."""
        assertion = {'has_data_assertion': True, 'assertion_type': 'count_mismatch'}
        console = {'found': True}
        result = DataGatherer._classify_failure_mode('assertion_data', 'expected 0 to equal 5', console, assertion)
        assert result == 'data_incorrect'

    def test_data_incorrect_count_mismatch(self):
        """Count mismatch is data_incorrect even without console_search."""
        assertion = {'has_data_assertion': True, 'assertion_type': 'count_mismatch'}
        result = DataGatherer._classify_failure_mode('assertion_data', 'expected 0 to equal 5', None, assertion)
        assert result == 'data_incorrect'

    def test_element_missing(self):
        result = DataGatherer._classify_failure_mode('element_not_found', 'element not found', None, None)
        assert result == 'element_missing'

    def test_timeout_with_element(self):
        result = DataGatherer._classify_failure_mode('timeout', "Timed out: expected to find element: '#btn'", None, None)
        assert result == 'element_missing'

    def test_timeout_general(self):
        result = DataGatherer._classify_failure_mode('timeout', 'Timed out retrying after 4000ms', None, None)
        assert result == 'timeout_general'

    def test_assertion_data_type(self):
        result = DataGatherer._classify_failure_mode('assertion_data', 'expected 0 to equal 5', None, None)
        assert result == 'data_incorrect'

    def test_unknown_fallback(self):
        result = DataGatherer._classify_failure_mode('', 'some weird error', None, None)
        assert result == 'unknown'

    def test_blank_page_detection(self):
        result = DataGatherer._classify_failure_mode('', 'class="no-js" found in empty body', None, None)
        assert result == 'render_failure'
