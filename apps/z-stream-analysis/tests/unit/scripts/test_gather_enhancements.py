#!/usr/bin/env python3
"""
Unit tests for gather.py enhancements.

Tests functionality including:
- Stack trace pre-parsing (_parse_stack_trace_data)
- CNV version-based kubevirt branch detection
- AI instructions structure (v4.0)
- Element inventory: selector classification, test ID extraction, repo search

These tests focus on the enhancement methods added to DataGatherer.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.scripts.gather import DataGatherer


class TestStackTracePreParsing:
    """Tests for _parse_stack_trace_data method."""

    @pytest.fixture
    def gatherer(self):
        """Create a DataGatherer instance with mocked services."""
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None):
            gatherer = DataGatherer()
            gatherer.output_dir = Path('/tmp/test')
            gatherer.verbose = False
            gatherer.logger = Mock()
            gatherer.acm_ui_mcp_client = None
            gatherer.gathered_data = {}

            # Mock stack parser
            gatherer.stack_parser = Mock()
            return gatherer

    def test_parse_empty_inputs_returns_none(self, gatherer):
        """Empty stack trace and error message should return None."""
        result = gatherer._parse_stack_trace_data(None, None)
        assert result is None

        result = gatherer._parse_stack_trace_data('', '')
        assert result is None

    def test_parse_extracts_root_cause(self, gatherer):
        """Stack trace parsing should extract root cause file and line."""
        # Mock parsed result
        mock_parsed = Mock()
        mock_parsed.root_cause_frame = Mock(file_path='cypress/e2e/test.cy.js', line_number=42)
        mock_parsed.test_file_frame = None
        mock_parsed.error_type = 'CypressError'
        mock_parsed.total_frames = 5
        mock_parsed.user_code_frames = 3
        gatherer.stack_parser.parse.return_value = mock_parsed
        gatherer.stack_parser.extract_failing_selector.return_value = None

        result = gatherer._parse_stack_trace_data(
            'at Context.eval (webpack://app/./cypress/e2e/test.cy.js:42:11)',
            ''
        )

        assert result is not None
        assert result['root_cause_file'] == 'cypress/e2e/test.cy.js'
        assert result['root_cause_line'] == 42
        assert result['error_type'] == 'CypressError'
        assert result['frames_count'] == 5

    def test_parse_extracts_failing_selector(self, gatherer):
        """Should extract failing selector from error message."""
        mock_parsed = Mock()
        mock_parsed.root_cause_frame = None
        mock_parsed.test_file_frame = None
        mock_parsed.error_type = 'Unknown'
        mock_parsed.total_frames = 0
        mock_parsed.user_code_frames = 0
        gatherer.stack_parser.parse.return_value = mock_parsed
        gatherer.stack_parser.extract_failing_selector.return_value = '#create-btn'

        result = gatherer._parse_stack_trace_data(
            '',
            "cy.get('#create-btn') - element not found"
        )

        assert result is not None
        assert result['failing_selector'] == '#create-btn'

    def test_parse_extracts_test_file(self, gatherer):
        """Should extract test file location from stack trace."""
        mock_parsed = Mock()
        mock_parsed.root_cause_frame = Mock(file_path='cypress/views/selectors.js', line_number=10)
        mock_parsed.test_file_frame = Mock(file_path='cypress/e2e/cluster.cy.ts', line_number=50)
        mock_parsed.error_type = 'AssertionError'
        mock_parsed.total_frames = 8
        mock_parsed.user_code_frames = 4
        gatherer.stack_parser.parse.return_value = mock_parsed
        gatherer.stack_parser.extract_failing_selector.return_value = None

        result = gatherer._parse_stack_trace_data(
            'at Object.<anonymous> (cypress/e2e/cluster.cy.ts:50:3)',
            ''
        )

        assert result is not None
        assert result['test_file'] == 'cypress/e2e/cluster.cy.ts'
        assert result['test_line'] == 50

    def test_parse_handles_exception_gracefully(self, gatherer):
        """Parsing errors should not raise, return None instead."""
        gatherer.stack_parser.parse.side_effect = Exception('Parse failed')
        gatherer.stack_parser.extract_failing_selector.side_effect = Exception('Extract failed')

        result = gatherer._parse_stack_trace_data(
            'some stack trace',
            'some error message'
        )

        assert result is None


    # TestTimelineEvidenceCollection removed — _collect_timeline_evidence was
    # removed in v4.0. Timeline data is now produced by the data-collector agent
    # (Task 3: recent_selector_changes + temporal_summary) with MCP verification.


class TestCNVVersionDetection:
    """Tests for CNV version-based kubevirt branch detection."""

    @pytest.fixture
    def gatherer(self):
        """Create a DataGatherer instance with mocked services."""
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None):
            gatherer = DataGatherer()
            gatherer.output_dir = Path('/tmp/test')
            gatherer.verbose = False
            gatherer.logger = Mock()
            gatherer.gathered_data = {'repositories': {}}
            gatherer.kubevirt_repo_path = None

            # Mock services
            gatherer.timeline_service = Mock()
            gatherer.acm_knowledge = Mock()
            gatherer.acm_ui_mcp_client = None
            return gatherer

    def test_clone_kubevirt_uses_detected_branch(self, gatherer):
        """Should use CNV version-detected branch when available."""
        # Mock CNV version detection
        mock_cnv_info = Mock()
        mock_cnv_info.version = '4.20.3'
        mock_cnv_info.branch = 'release-4.20'
        mock_cnv_info.detected_from = 'cluster'

        gatherer.acm_ui_mcp_client = Mock()
        gatherer.acm_ui_mcp_client.detect_cnv_version.return_value = mock_cnv_info

        gatherer.timeline_service.clone_kubevirt_to.return_value = (True, None)
        gatherer.acm_knowledge.validate_kubevirt_structure.return_value = {'src': True}

        repos_dir = Path('/tmp/repos')
        gatherer._clone_kubevirt_repo(repos_dir, 'main')

        # Should clone with detected branch, not the default
        gatherer.timeline_service.clone_kubevirt_to.assert_called_once()
        call_args = gatherer.timeline_service.clone_kubevirt_to.call_args
        assert call_args[1]['branch'] == 'release-4.20'

        # Should store CNV version info
        assert 'cnv_version' in gatherer.gathered_data['repositories']['kubevirt_plugin']
        assert gatherer.gathered_data['repositories']['kubevirt_plugin']['cnv_version']['version'] == '4.20.3'

    def test_clone_kubevirt_fallback_to_provided_branch(self, gatherer):
        """Should fall back to provided branch when CNV detection fails."""
        gatherer.acm_ui_mcp_client = Mock()
        gatherer.acm_ui_mcp_client.detect_cnv_version.return_value = None

        gatherer.timeline_service.clone_kubevirt_to.return_value = (True, None)
        gatherer.acm_knowledge.validate_kubevirt_structure.return_value = {'src': True}

        repos_dir = Path('/tmp/repos')
        gatherer._clone_kubevirt_repo(repos_dir, 'release-2.15')

        # Should use provided branch
        call_args = gatherer.timeline_service.clone_kubevirt_to.call_args
        assert call_args[1]['branch'] == 'release-2.15'

    def test_clone_kubevirt_without_mcp_client(self, gatherer):
        """Should work without MCP client configured."""
        gatherer.acm_ui_mcp_client = None

        gatherer.timeline_service.clone_kubevirt_to.return_value = (True, None)
        gatherer.acm_knowledge.validate_kubevirt_structure.return_value = {'src': True}

        repos_dir = Path('/tmp/repos')
        gatherer._clone_kubevirt_repo(repos_dir, 'main')

        # Should clone with provided branch
        call_args = gatherer.timeline_service.clone_kubevirt_to.call_args
        assert call_args[1]['branch'] == 'main'

    def test_clone_kubevirt_handles_detection_exception(self, gatherer):
        """Should handle CNV detection exceptions gracefully."""
        gatherer.acm_ui_mcp_client = Mock()
        gatherer.acm_ui_mcp_client.detect_cnv_version.side_effect = Exception('Cluster error')

        gatherer.timeline_service.clone_kubevirt_to.return_value = (True, None)
        gatherer.acm_knowledge.validate_kubevirt_structure.return_value = {'src': True}

        repos_dir = Path('/tmp/repos')
        gatherer._clone_kubevirt_repo(repos_dir, 'main')

        # Should not crash, should use fallback branch
        call_args = gatherer.timeline_service.clone_kubevirt_to.call_args
        assert call_args[1]['branch'] == 'main'

    def test_clone_kubevirt_records_branch_in_metadata(self, gatherer):
        """Should record cloned branch in repository metadata."""
        gatherer.acm_ui_mcp_client = None
        gatherer.timeline_service.clone_kubevirt_to.return_value = (True, None)
        gatherer.acm_knowledge.validate_kubevirt_structure.return_value = {'src': True}

        repos_dir = Path('/tmp/repos')
        gatherer._clone_kubevirt_repo(repos_dir, 'release-2.14')

        assert gatherer.gathered_data['repositories']['kubevirt_plugin']['branch'] == 'release-2.14'
        assert gatherer.gathered_data['repositories']['kubevirt_plugin']['cloned'] is True


    # TestAIInstructionsEnhancements removed — _build_ai_instructions() was removed
    # in v4.0. Stage 2 reads instructions from .claude/agents/analysis.md.

    # TestClassifySelectorType, TestExtractTestIdsFromFile, TestSearchElementInRepos,
    # TestGatherElementInventory removed — Step 10 (element inventory) was removed
    # in v4.0. Selector verification is now handled by data-collector agent Task 2.
