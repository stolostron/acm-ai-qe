#!/usr/bin/env python3
"""
Unit tests for Stack Trace Parser Service
"""

import pytest
from src.services.stack_trace_parser import (
    StackTraceParser,
    StackFrame,
    ParsedStackTrace,
    parse_stack_trace
)


class TestStackTraceParser:
    """Tests for StackTraceParser class."""

    def setup_method(self):
        """Setup for each test."""
        self.parser = StackTraceParser()

    def test_parse_webpack_path(self):
        """Test parsing webpack:// paths."""
        trace = """
        Error: Element not found
            at webpack://app/./cypress/views/clusters/managedCluster.js:181:11
        """
        result = self.parser.parse(trace)

        assert result.total_frames >= 1
        frame = result.frames[0]
        assert 'cypress/views/clusters/managedCluster.js' in frame.file_path
        assert frame.line_number == 181
        assert frame.column_number == 11

    def test_parse_standard_nodejs_path(self):
        """Test parsing standard Node.js stack trace format."""
        trace = """
        AssertionError: expected 'foo' to equal 'bar'
            at Context.eval (/Users/test/project/cypress/tests/example.spec.js:42:15)
            at async Context.eval (/Users/test/project/cypress/tests/example.spec.js:45:3)
        """
        result = self.parser.parse(trace)

        assert result.error_type == "AssertionError"
        assert "expected 'foo' to equal 'bar'" in result.error_message
        assert result.total_frames >= 1

    def test_parse_anonymous_function(self):
        """Test parsing anonymous function frames."""
        trace = """
        Error: Timeout
            at Object.<anonymous> (cypress/tests/login.cy.js:10:5)
        """
        result = self.parser.parse(trace)

        assert result.total_frames >= 1
        frame = result.frames[0]
        assert frame.function_name == '<anonymous>'
        assert frame.line_number == 10

    def test_identify_test_file(self):
        """Test that test files are correctly identified."""
        trace = """
        Error: Test failed
            at webpack://app/./cypress/tests/login.spec.js:25:10
        """
        result = self.parser.parse(trace)

        assert result.test_file_frame is not None
        assert result.test_file_frame.is_test_file is True

    def test_identify_support_file(self):
        """Test that support/view files are correctly identified."""
        trace = """
        Error: Element not found
            at webpack://app/./cypress/views/common/dropdown.js:50:8
            at webpack://app/./cypress/tests/main.spec.js:100:5
        """
        result = self.parser.parse(trace)

        assert result.support_file_frame is not None
        assert result.support_file_frame.is_support_file is True
        assert 'views' in result.support_file_frame.file_path

    def test_identify_framework_file(self):
        """Test that framework files are correctly identified."""
        trace = """
        Error: Promise rejected
            at node_modules/cypress/lib/runner.js:500:10
            at webpack://app/./cypress/tests/test.spec.js:10:5
        """
        result = self.parser.parse(trace)

        # Root cause should not be the framework file
        assert result.root_cause_frame is not None
        assert result.root_cause_frame.is_framework_file is False

    def test_extract_failing_selector_cy_get(self):
        """Test extracting selector from cy.get() error."""
        error_msg = "Timed out retrying: cy.get('#my-button') found no element"
        selector = self.parser.extract_failing_selector(error_msg)

        assert selector == '#my-button'

    def test_extract_failing_selector_expected(self):
        """Test extracting selector from 'Expected to find' error."""
        error_msg = "Expected to find element: `.submit-button`, but never found it"
        selector = self.parser.extract_failing_selector(error_msg)

        assert selector == '.submit-button'

    def test_extract_failing_selector_data_test(self):
        """Test extracting data-test attribute selector."""
        error_msg = "Element not found: `[data-test=submit-form]`"
        selector = self.parser.extract_failing_selector(error_msg)

        assert selector == '[data-test=submit-form]'

    def test_extract_failing_selector_no_match(self):
        """Test that non-selector errors return None."""
        error_msg = "Network error: connection refused"
        selector = self.parser.extract_failing_selector(error_msg)

        assert selector is None

    def test_empty_trace(self):
        """Test handling of empty stack trace."""
        result = self.parser.parse("")

        assert result.raw_trace == ""
        assert result.total_frames == 0
        assert result.root_cause_frame is None

    def test_convenience_function(self):
        """Test the parse_stack_trace convenience function."""
        trace = "Error: Test\n    at test.js:10:5"
        result = parse_stack_trace(trace)

        assert isinstance(result, ParsedStackTrace)
        assert result.raw_trace == trace

    def test_get_context_range(self):
        """Test getting context line range around a frame."""
        frame = StackFrame(
            file_path="test.js",
            line_number=50,
            is_test_file=True
        )

        start, end = self.parser.get_context_range(frame, context_lines=10)

        assert start == 40
        assert end == 60

    def test_get_context_range_near_start(self):
        """Test context range when near the start of file."""
        frame = StackFrame(
            file_path="test.js",
            line_number=5,
            is_test_file=True
        )

        start, end = self.parser.get_context_range(frame, context_lines=10)

        assert start == 1  # Should not go below 1
        assert end == 15

    def test_deduplication(self):
        """Test that duplicate frames are removed."""
        trace = """
        Error: Duplicate test
            at test.js:10:5
            at test.js:10:5
            at test.js:10:5
        """
        result = self.parser.parse(trace)

        # Should deduplicate
        assert result.total_frames == 1

    def test_user_code_frames_count(self):
        """Test counting of user code frames (non-framework)."""
        trace = """
        Error: Test
            at node_modules/cypress/runner.js:100:10
            at cypress/tests/test.spec.js:50:5
            at cypress/views/page.js:25:10
        """
        result = self.parser.parse(trace)

        # node_modules is framework, others are user code
        assert result.user_code_frames == result.total_frames - 1 or result.user_code_frames == result.total_frames


class TestStackFrame:
    """Tests for StackFrame dataclass."""

    def test_test_file_detection(self):
        """Test test file pattern detection."""
        frame = StackFrame(
            file_path="cypress/tests/login.spec.js",
            line_number=10
        )
        assert frame.is_test_file is True

        frame = StackFrame(
            file_path="cypress/views/page.js",
            line_number=10
        )
        assert frame.is_test_file is False

    def test_framework_file_detection(self):
        """Test framework file pattern detection."""
        frame = StackFrame(
            file_path="node_modules/cypress/lib/runner.js",
            line_number=10
        )
        assert frame.is_framework_file is True

        frame = StackFrame(
            file_path="cypress/tests/test.js",
            line_number=10
        )
        assert frame.is_framework_file is False

    def test_support_file_detection(self):
        """Test support file pattern detection."""
        frame = StackFrame(
            file_path="cypress/support/commands.js",
            line_number=10
        )
        assert frame.is_support_file is True

        frame = StackFrame(
            file_path="cypress/views/common/dropdown.js",
            line_number=10
        )
        assert frame.is_support_file is True


class TestAssertionValueExtraction:
    """Tests for assertion value extraction (GAP-01)."""

    def setup_method(self):
        self.parser = StackTraceParser()

    def test_extract_string_equality(self):
        """Test extracting expected/actual from string equality assertion."""
        error = "AssertionError: expected 'Ready' to equal 'Available'"
        result = self.parser.extract_assertion_values(error)
        assert result is not None
        assert result['has_data_assertion'] is True
        assert result['actual'] == 'Ready'
        assert result['expected'] == 'Available'
        assert result['assertion_type'] == 'value_mismatch'

    def test_extract_numeric_equality(self):
        """Test extracting expected/actual from numeric assertion."""
        error = "AssertionError: expected 0 to equal 5"
        result = self.parser.extract_assertion_values(error)
        assert result is not None
        assert result['actual'] == '0'
        assert result['expected'] == '5'
        assert result['assertion_type'] == 'count_mismatch'

    def test_extract_element_count(self):
        """Test extracting count from element count assertion."""
        error = "Timed out retrying after 4000ms: expected to find 5 elements, but found 0"
        result = self.parser.extract_assertion_values(error)
        assert result is not None
        assert result['assertion_type'] == 'count_mismatch'

    def test_extract_array_length(self):
        """Test extracting expected length from array assertion."""
        error = "AssertionError: expected [] to have length 5"
        result = self.parser.extract_assertion_values(error)
        assert result is not None
        assert result['expected'] == '5'
        assert result['assertion_type'] == 'count_mismatch'

    def test_extract_contain_text(self):
        """Test extracting text content assertion."""
        error = "expected '<div>' to contain 'clusterset-name'"
        result = self.parser.extract_assertion_values(error)
        assert result is not None
        assert result['assertion_type'] == 'content_missing'

    def test_extract_boolean_state(self):
        """Test extracting boolean state assertion."""
        error = "expected true to be false"
        result = self.parser.extract_assertion_values(error)
        assert result is not None
        assert result['assertion_type'] == 'state_mismatch'

    def test_no_assertion_in_selector_error(self):
        """Test that selector errors don't match assertion patterns."""
        error = "Expected to find element: '#my-button', but never found it"
        result = self.parser.extract_assertion_values(error)
        # This should NOT match -- it's about element existence, not data
        assert result is None

    def test_no_assertion_in_network_error(self):
        """Test that network errors don't match assertion patterns."""
        error = "Network error: connection refused"
        result = self.parser.extract_assertion_values(error)
        assert result is None

    def test_empty_message(self):
        """Test empty error message returns None."""
        result = self.parser.extract_assertion_values("")
        assert result is None

    def test_none_message(self):
        """Test None error message returns None."""
        result = self.parser.extract_assertion_values(None)
        assert result is None

    def test_deep_equal_assertion(self):
        """Test deep.equal assertion extraction."""
        error = "expected 'admin:kube' to deep.equal 'kube:admin'"
        result = self.parser.extract_assertion_values(error)
        assert result is not None
        assert result['actual'] == 'admin:kube'
        assert result['expected'] == 'kube:admin'
        assert result['assertion_type'] == 'value_mismatch'

    def test_property_assertion(self):
        """Test property assertion extraction."""
        error = "expected { count: 0 } to have property 'items'"
        result = self.parser.extract_assertion_values(error)
        assert result is not None
        assert result['assertion_type'] == 'property_missing'

    def test_raw_assertion_truncation(self):
        """Test that raw_assertion is truncated to 200 chars."""
        long_error = "expected '" + "x" * 300 + "' to equal 'y'"
        result = self.parser.extract_assertion_values(long_error)
        if result:
            assert len(result['raw_assertion']) <= 200
