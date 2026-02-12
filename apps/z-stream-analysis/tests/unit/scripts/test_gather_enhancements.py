#!/usr/bin/env python3
"""
Unit tests for gather.py enhancements.

Tests functionality including:
- Stack trace pre-parsing (_parse_stack_trace_data)
- Timeline evidence collection (_collect_timeline_evidence)
- CNV version-based kubevirt branch detection
- AI instructions structure (v2.5 5-phase framework)
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


class TestTimelineEvidenceCollection:
    """Tests for _collect_timeline_evidence method."""

    @pytest.fixture
    def gatherer(self):
        """Create a DataGatherer instance with mocked services."""
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None):
            gatherer = DataGatherer()
            gatherer.output_dir = Path('/tmp/test')
            gatherer.verbose = False
            gatherer.logger = Mock()
            gatherer.gathered_data = {}

            # Mock timeline service
            gatherer.timeline_service = Mock()
            return gatherer

    def test_collect_empty_selectors_returns_empty(self, gatherer):
        """Empty selector list should return empty dict."""
        result = gatherer._collect_timeline_evidence([])
        assert result == {}

    def test_collect_deduplicates_selectors(self, gatherer):
        """Should deduplicate selectors before querying."""
        mock_comparison = Mock()
        mock_comparison.element_id = 'btn'
        mock_comparison.element_removed_from_console = False
        mock_comparison.element_never_existed = False
        mock_comparison.days_difference = None
        mock_comparison.console_changed_after_automation = None
        mock_comparison.stale_test_signal = False
        mock_comparison.product_commit_type = None
        mock_comparison.console_timeline = None
        mock_comparison.automation_timeline = None
        gatherer.timeline_service.compare_timelines.return_value = mock_comparison

        # Pass duplicate selectors
        result = gatherer._collect_timeline_evidence(['#btn', '#btn', '#btn'])

        # Should only query once
        assert gatherer.timeline_service.compare_timelines.call_count == 1

    def test_collect_limits_to_10_selectors(self, gatherer):
        """Should limit to 10 unique selectors for performance."""
        mock_comparison = Mock()
        mock_comparison.element_id = 'test'
        mock_comparison.element_removed_from_console = False
        mock_comparison.element_never_existed = False
        mock_comparison.days_difference = None
        mock_comparison.console_changed_after_automation = None
        mock_comparison.stale_test_signal = False
        mock_comparison.product_commit_type = None
        mock_comparison.console_timeline = None
        mock_comparison.automation_timeline = None
        gatherer.timeline_service.compare_timelines.return_value = mock_comparison

        # Pass 20 unique selectors
        selectors = [f'#selector-{i}' for i in range(20)]
        result = gatherer._collect_timeline_evidence(selectors)

        # Should only process 10
        assert gatherer.timeline_service.compare_timelines.call_count == 10
        assert len(result) == 10

    def test_collect_records_element_never_existed(self, gatherer):
        """Should record factual data when element never existed."""
        mock_comparison = Mock()
        mock_comparison.element_id = 'missing-btn'
        mock_comparison.element_removed_from_console = False
        mock_comparison.element_never_existed = True
        mock_comparison.days_difference = None
        mock_comparison.console_changed_after_automation = None
        mock_comparison.stale_test_signal = False
        mock_comparison.product_commit_type = None
        mock_comparison.console_timeline = None
        mock_comparison.automation_timeline = None
        gatherer.timeline_service.compare_timelines.return_value = mock_comparison

        result = gatherer._collect_timeline_evidence(['#missing-btn'])

        assert '#missing-btn' in result
        assert result['#missing-btn']['element_never_existed'] is True
        assert result['#missing-btn']['exists_in_console'] is False

    def test_collect_records_element_removed(self, gatherer):
        """Should record factual data when element was removed."""
        mock_comparison = Mock()
        mock_comparison.element_id = 'removed-btn'
        mock_comparison.element_removed_from_console = True
        mock_comparison.element_never_existed = False
        mock_comparison.days_difference = 30
        mock_comparison.console_changed_after_automation = None
        mock_comparison.stale_test_signal = False
        mock_comparison.product_commit_type = None
        mock_comparison.console_timeline = None
        mock_comparison.automation_timeline = None
        gatherer.timeline_service.compare_timelines.return_value = mock_comparison

        result = gatherer._collect_timeline_evidence(['#removed-btn'])

        assert result['#removed-btn']['element_removed'] is True
        assert result['#removed-btn']['exists_in_console'] is False
        assert result['#removed-btn']['days_difference'] == 30

    def test_collect_records_console_changed_after(self, gatherer):
        """Should record factual data when console changed after automation."""
        mock_comparison = Mock()
        mock_comparison.element_id = 'changed-btn'
        mock_comparison.element_removed_from_console = False
        mock_comparison.element_never_existed = False
        mock_comparison.days_difference = 15
        mock_comparison.console_changed_after_automation = True
        mock_comparison.stale_test_signal = True
        mock_comparison.product_commit_type = 'intentional_change'
        mock_comparison.console_timeline = None
        mock_comparison.automation_timeline = None
        gatherer.timeline_service.compare_timelines.return_value = mock_comparison

        result = gatherer._collect_timeline_evidence(['#changed-btn'])

        assert result['#changed-btn']['console_changed_after_automation'] is True
        assert result['#changed-btn']['exists_in_console'] is True
        assert result['#changed-btn']['days_difference'] == 15

    def test_collect_includes_stale_test_signal(self, gatherer):
        """Should include stale_test_signal and product_commit_type in evidence."""
        mock_comparison = Mock()
        mock_comparison.element_id = 'btn'
        mock_comparison.element_removed_from_console = False
        mock_comparison.element_never_existed = False
        mock_comparison.days_difference = 77
        mock_comparison.console_changed_after_automation = True
        mock_comparison.stale_test_signal = True
        mock_comparison.product_commit_type = 'intentional_change'
        mock_comparison.console_timeline = None
        mock_comparison.automation_timeline = None
        gatherer.timeline_service.compare_timelines.return_value = mock_comparison

        result = gatherer._collect_timeline_evidence(['#btn'])

        assert result['#btn']['stale_test_signal'] is True
        assert result['#btn']['product_commit_type'] == 'intentional_change'

    def test_collect_includes_timeline_details(self, gatherer):
        """Should include console and automation timeline details when available."""
        mock_console_timeline = Mock()
        mock_console_timeline.file_path = 'src/components/Button.tsx'
        mock_console_timeline.last_modified_date = datetime(2025, 1, 15)
        mock_console_timeline.last_commit_sha = 'abc123def456'
        mock_console_timeline.last_commit_message = 'Update button styles'

        mock_auto_timeline = Mock()
        mock_auto_timeline.file_path = 'cypress/views/selectors.js'
        mock_auto_timeline.last_modified_date = datetime(2024, 12, 1)
        mock_auto_timeline.last_commit_sha = 'xyz789ghi012'
        mock_auto_timeline.last_commit_message = 'Add selectors'

        mock_comparison = Mock()
        mock_comparison.element_id = 'btn'
        mock_comparison.element_removed_from_console = False
        mock_comparison.element_never_existed = False
        mock_comparison.days_difference = 45
        mock_comparison.console_changed_after_automation = True
        mock_comparison.stale_test_signal = True
        mock_comparison.product_commit_type = 'ambiguous'
        mock_comparison.console_timeline = mock_console_timeline
        mock_comparison.automation_timeline = mock_auto_timeline
        gatherer.timeline_service.compare_timelines.return_value = mock_comparison

        result = gatherer._collect_timeline_evidence(['#btn'])

        assert 'console_timeline' in result['#btn']
        assert result['#btn']['console_timeline']['file_path'] == 'src/components/Button.tsx'
        assert result['#btn']['console_timeline']['last_commit'] == 'abc123de'
        assert result['#btn']['console_timeline']['commit_message'] == 'Update button styles'

        assert 'automation_timeline' in result['#btn']
        assert result['#btn']['automation_timeline']['file_path'] == 'cypress/views/selectors.js'
        assert result['#btn']['automation_timeline']['last_commit'] == 'xyz789gh'

        # Verify factual fields
        assert result['#btn']['days_difference'] == 45
        assert result['#btn']['console_changed_after_automation'] is True
        assert result['#btn']['exists_in_console'] is True

    def test_collect_handles_exception_gracefully(self, gatherer):
        """Errors during timeline comparison should not propagate."""
        gatherer.timeline_service.compare_timelines.side_effect = Exception('Git error')

        result = gatherer._collect_timeline_evidence(['#error-selector'])

        assert '#error-selector' in result
        assert 'error' in result['#error-selector']


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


class TestAIInstructionsEnhancements:
    """Tests for AI instructions structure (v2.5 5-phase framework)."""

    @pytest.fixture
    def gatherer(self):
        """Create a DataGatherer instance."""
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None):
            gatherer = DataGatherer()
            gatherer.output_dir = Path('/tmp/test')
            gatherer.verbose = False
            gatherer.logger = Mock()
            return gatherer

    def test_ai_instructions_version(self, gatherer):
        """AI instructions should be version 2.5.0."""
        with patch('src.scripts.gather.is_acm_ui_mcp_available', return_value=False):
            with patch('src.scripts.gather.is_knowledge_graph_available', return_value=False):
                instructions = gatherer._build_ai_instructions()
                assert instructions['version'] == '2.5.0'

    def test_ai_instructions_include_investigation_framework(self, gatherer):
        """Should include 5-phase investigation framework."""
        with patch('src.scripts.gather.is_acm_ui_mcp_available', return_value=False):
            with patch('src.scripts.gather.is_knowledge_graph_available', return_value=False):
                instructions = gatherer._build_ai_instructions()
                assert 'investigation_framework' in instructions
                phases = instructions['investigation_framework']['phases']
                assert 'A' in phases
                assert 'B' in phases
                assert 'C' in phases
                assert 'D' in phases
                assert 'E' in phases

    def test_ai_instructions_include_precomputed_context(self, gatherer):
        """Should document precomputed context fields."""
        with patch('src.scripts.gather.is_acm_ui_mcp_available', return_value=False):
            with patch('src.scripts.gather.is_knowledge_graph_available', return_value=False):
                instructions = gatherer._build_ai_instructions()
                assert 'precomputed_context' in instructions
                fields = instructions['precomputed_context']['fields']
                assert 'parsed_stack_trace' in fields
                assert 'timeline_evidence' in fields
                assert 'detected_components' in fields

    def test_ai_instructions_include_evidence_requirements(self, gatherer):
        """Should include multi-evidence requirements."""
        with patch('src.scripts.gather.is_acm_ui_mcp_available', return_value=False):
            with patch('src.scripts.gather.is_knowledge_graph_available', return_value=False):
                instructions = gatherer._build_ai_instructions()
                assert 'evidence_requirements' in instructions
                evidence = instructions['evidence_requirements']
                assert 'evidence_tiers' in evidence
                assert 'minimum_requirement' in evidence
                assert 'classification_evidence_matrix' in evidence


class TestClassifySelectorType:
    """Tests for _classify_selector_type static method."""

    def test_id_selector(self):
        assert DataGatherer._classify_selector_type('#create-btn') == 'id'
        assert DataGatherer._classify_selector_type('#my-id') == 'id'

    def test_css_class_selector(self):
        assert DataGatherer._classify_selector_type('.my-class') == 'css_class'
        assert DataGatherer._classify_selector_type('.some-component') == 'css_class'

    def test_patternfly_v5_class(self):
        assert DataGatherer._classify_selector_type('.pf-v5-c-menu__item') == 'patternfly_class'
        assert DataGatherer._classify_selector_type('pf-v5-c-menu__item') == 'patternfly_class'

    def test_patternfly_v6_class(self):
        assert DataGatherer._classify_selector_type('.pf-v6-c-button') == 'patternfly_class'

    def test_patternfly_component_class(self):
        assert DataGatherer._classify_selector_type('.pf-c-dropdown') == 'patternfly_class'

    def test_patternfly_modifier_class(self):
        assert DataGatherer._classify_selector_type('.pf-m-primary') == 'patternfly_class'

    def test_patternfly_layout_class(self):
        assert DataGatherer._classify_selector_type('.pf-l-flex') == 'patternfly_class'

    def test_patternfly_utility_class(self):
        assert DataGatherer._classify_selector_type('.pf-u-mt-md') == 'patternfly_class'

    def test_attribute_selector(self):
        assert DataGatherer._classify_selector_type('[data-testid="x"]') == 'attribute'
        assert DataGatherer._classify_selector_type('[aria-label="Close"]') == 'attribute'

    def test_text_selector(self):
        assert DataGatherer._classify_selector_type('button') == 'text'
        assert DataGatherer._classify_selector_type('Create cluster') == 'text'

    def test_empty_selector(self):
        assert DataGatherer._classify_selector_type('') == 'unknown'
        assert DataGatherer._classify_selector_type('  ') == 'unknown'

    def test_none_like_input(self):
        # None is not a valid input per type hints but test defensive behavior
        assert DataGatherer._classify_selector_type('') == 'unknown'


class TestExtractTestIdsFromFile:
    """Tests for _extract_test_ids_from_file method."""

    @pytest.fixture
    def gatherer(self):
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None):
            gatherer = DataGatherer()
            gatherer.logger = Mock()
            return gatherer

    def test_extracts_data_testid(self, gatherer, tmp_path):
        """Should extract data-testid attributes."""
        test_file = tmp_path / 'Button.tsx'
        test_file.write_text(
            '<button data-testid="submit-btn">Submit</button>\n'
            '<input data-testid="name-input" />\n'
        )
        result = gatherer._extract_test_ids_from_file(test_file)
        assert len(result) == 2
        assert result[0]['attribute'] == 'data-testid'
        assert result[0]['value'] == 'submit-btn'
        assert result[0]['line'] == 1
        assert result[1]['value'] == 'name-input'

    def test_extracts_aria_label(self, gatherer, tmp_path):
        """Should extract aria-label attributes."""
        test_file = tmp_path / 'Modal.tsx'
        test_file.write_text('<button aria-label="Close modal">X</button>\n')
        result = gatherer._extract_test_ids_from_file(test_file)
        assert len(result) == 1
        assert result[0]['attribute'] == 'aria-label'
        assert result[0]['value'] == 'Close modal'

    def test_respects_max_ids(self, gatherer, tmp_path):
        """Should stop at max_ids limit."""
        lines = [f'<div data-testid="item-{i}" />' for i in range(50)]
        test_file = tmp_path / 'List.tsx'
        test_file.write_text('\n'.join(lines))
        result = gatherer._extract_test_ids_from_file(test_file, max_ids=5)
        assert len(result) == 5

    def test_nonexistent_file_returns_empty(self, gatherer, tmp_path):
        """Should return empty list for nonexistent file."""
        result = gatherer._extract_test_ids_from_file(tmp_path / 'missing.tsx')
        assert result == []

    def test_extracts_multiple_types(self, gatherer, tmp_path):
        """Should extract data-test and testId attributes."""
        test_file = tmp_path / 'Component.tsx'
        test_file.write_text(
            '<div data-test="grid-view" />\n'
            '<span testId="status-label" />\n'
            '<input data-test-id="search-box" />\n'
        )
        result = gatherer._extract_test_ids_from_file(test_file)
        attrs = {r['attribute'] for r in result}
        assert 'data-test' in attrs
        assert 'testId' in attrs
        assert 'data-test-id' in attrs


class TestSearchElementInRepos:
    """Tests for _search_element_in_repos method."""

    @pytest.fixture
    def gatherer(self):
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None):
            gatherer = DataGatherer()
            gatherer.logger = Mock()
            gatherer.console_repo_path = None
            gatherer.kubevirt_repo_path = None
            gatherer.acm_knowledge = Mock()
            gatherer.acm_knowledge.suggest_search_patterns.return_value = []
            return gatherer

    def test_no_repos_returns_empty(self, gatherer):
        """Should return empty result when no repos are available."""
        result = gatherer._search_element_in_repos('#some-btn')
        assert result['found_in_console'] is False
        assert result['locations'] == []
        assert result['component_files'] == []

    def test_classifies_selector_type(self, gatherer):
        """Should classify selector type in result."""
        result = gatherer._search_element_in_repos('.pf-v5-c-menu__item')
        assert result['selector_type'] == 'patternfly_class'

        result = gatherer._search_element_in_repos('#create-btn')
        assert result['selector_type'] == 'id'

    def test_searches_console_repo(self, gatherer, tmp_path):
        """Should search console repo and find matches."""
        # Set up mock console repo with frontend/src structure
        console_dir = tmp_path / 'console'
        src_dir = console_dir / 'frontend' / 'src'
        src_dir.mkdir(parents=True)

        # Create a component file with a testid
        component = src_dir / 'AcmDropdown.tsx'
        component.write_text('<button id="create-btn" data-testid="create-action">Create</button>')

        gatherer.console_repo_path = console_dir
        gatherer.acm_knowledge.suggest_search_patterns.return_value = ['id="create-btn"']

        result = gatherer._search_element_in_repos('#create-btn')
        assert result['found_in_console'] is True
        assert len(result['locations']) > 0
        assert 'AcmDropdown.tsx' in result['component_files']

    def test_deduplicates_by_file(self, gatherer, tmp_path):
        """Should not return duplicate entries for the same file."""
        console_dir = tmp_path / 'console'
        src_dir = console_dir / 'frontend' / 'src'
        src_dir.mkdir(parents=True)

        component = src_dir / 'Button.tsx'
        component.write_text(
            '<button id="my-btn">Click</button>\n'
            '<span id="my-btn-label">Label</span>\n'
        )

        gatherer.console_repo_path = console_dir
        # Two patterns that both match lines in the same file
        gatherer.acm_knowledge.suggest_search_patterns.return_value = [
            'id="my-btn"', 'my-btn'
        ]

        result = gatherer._search_element_in_repos('#my-btn')
        # File paths should be deduplicated
        file_paths = [loc['file'] for loc in result['locations']]
        assert len(file_paths) == len(set(file_paths))


class TestGatherElementInventory:
    """Tests for _gather_element_inventory method."""

    @pytest.fixture
    def gatherer(self):
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None):
            gatherer = DataGatherer()
            gatherer.logger = Mock()
            gatherer.console_repo_path = None
            gatherer.kubevirt_repo_path = None
            gatherer.acm_ui_mcp_client = None
            gatherer.acm_knowledge = Mock()
            gatherer.acm_knowledge.suggest_search_patterns.return_value = []
            gatherer.acm_knowledge.extract_selector_from_error.return_value = None
            gatherer._needs_kubevirt_repo = None
            gatherer.gathered_data = {
                'test_report': {'failed_tests': []},
                'element_inventory': {},
                'errors': []
            }
            return gatherer

    def test_skips_without_repos(self, gatherer, tmp_path):
        """Should skip when no repos are cloned."""
        gatherer._gather_element_inventory(tmp_path)
        # element_inventory should remain empty dict (unchanged)
        assert gatherer.gathered_data['element_inventory'] == {}

    def test_sets_source_local_repos(self, gatherer, tmp_path):
        """Should set source to local_repos."""
        console_dir = tmp_path / 'console'
        console_dir.mkdir()
        gatherer.console_repo_path = console_dir

        gatherer._gather_element_inventory(tmp_path)
        inv = gatherer.gathered_data['element_inventory']
        assert inv['source'] == 'local_repos'

    def test_processes_selectors_from_parsed_stack(self, gatherer, tmp_path):
        """Should extract selectors from parsed_stack_trace first."""
        console_dir = tmp_path / 'console'
        (console_dir / 'frontend' / 'src').mkdir(parents=True)
        gatherer.console_repo_path = console_dir

        gatherer.gathered_data['test_report']['failed_tests'] = [
            {
                'test_name': 'test_create',
                'error_message': 'element not found',
                'parsed_stack_trace': {'failing_selector': '#create-btn'}
            }
        ]

        gatherer._gather_element_inventory(tmp_path)
        inv = gatherer.gathered_data['element_inventory']
        assert '#create-btn' in inv['element_lookup']
        assert len(inv['failed_test_elements']) == 1
        assert inv['failed_test_elements'][0]['selector'] == '#create-btn'

    def test_deduplicates_selectors(self, gatherer, tmp_path):
        """Should not search the same selector twice."""
        console_dir = tmp_path / 'console'
        (console_dir / 'frontend' / 'src').mkdir(parents=True)
        gatherer.console_repo_path = console_dir

        gatherer.gathered_data['test_report']['failed_tests'] = [
            {
                'test_name': 'test_a',
                'error_message': '',
                'parsed_stack_trace': {'failing_selector': '#same-btn'}
            },
            {
                'test_name': 'test_b',
                'error_message': '',
                'parsed_stack_trace': {'failing_selector': '#same-btn'}
            }
        ]

        gatherer._gather_element_inventory(tmp_path)
        inv = gatherer.gathered_data['element_inventory']
        # Should only have one entry for #same-btn
        assert len(inv['failed_test_elements']) == 1

    def test_handles_exceptions_gracefully(self, gatherer, tmp_path):
        """Should catch exceptions and record error."""
        console_dir = tmp_path / 'console'
        console_dir.mkdir()
        gatherer.console_repo_path = console_dir

        # Force an exception by making gathered_data invalid
        gatherer.gathered_data = {
            'test_report': None,  # Will cause AttributeError
            'element_inventory': {},
            'errors': []
        }

        gatherer._gather_element_inventory(tmp_path)
        assert 'error' in gatherer.gathered_data['element_inventory']

    def test_saves_file_when_elements_found(self, gatherer, tmp_path):
        """Should save element-inventory.json when elements are looked up."""
        console_dir = tmp_path / 'console'
        src_dir = console_dir / 'frontend' / 'src'
        src_dir.mkdir(parents=True)

        # Create a real component file
        component = src_dir / 'Button.tsx'
        component.write_text('<button id="save-btn">Save</button>')

        gatherer.console_repo_path = console_dir
        gatherer.acm_knowledge.suggest_search_patterns.return_value = ['id="save-btn"']

        gatherer.gathered_data['test_report']['failed_tests'] = [
            {
                'test_name': 'test_save',
                'error_message': '',
                'parsed_stack_trace': {'failing_selector': '#save-btn'}
            }
        ]

        gatherer._gather_element_inventory(tmp_path)

        output_file = tmp_path / 'element-inventory.json'
        assert output_file.exists()

        import json
        data = json.loads(output_file.read_text())
        assert data['source'] == 'local_repos'
        assert '#save-btn' in data['element_lookup']

    def test_fleet_virt_deferred_to_phase2(self, gatherer, tmp_path):
        """Fleet Virt selectors should be deferred to Phase 2."""
        console_dir = tmp_path / 'console'
        console_dir.mkdir()
        gatherer.console_repo_path = console_dir

        gatherer._gather_element_inventory(tmp_path)
        inv = gatherer.gathered_data['element_inventory']
        assert inv['fleet_virt_selectors'] == 'deferred_to_phase2'


class TestInjectTemporalSummaries:
    """Tests for _inject_temporal_summaries method."""

    @pytest.fixture
    def gatherer(self):
        """Create a DataGatherer instance with mocked services."""
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None):
            gatherer = DataGatherer()
            gatherer.output_dir = Path('/tmp/test')
            gatherer.verbose = False
            gatherer.logger = Mock()
            gatherer.gathered_data = {
                'test_report': {'failed_tests': []},
                'investigation_hints': {'timeline_evidence': {}},
            }
            return gatherer

    def test_inject_matches_selector_to_test(self, gatherer):
        """Should inject temporal_summary into test with matching selector."""
        gatherer.gathered_data['test_report']['failed_tests'] = [
            {
                'test_name': 'test_create',
                'parsed_stack_trace': {'failing_selector': '#create-btn'},
                'extracted_context': {'test_file': None, 'page_objects': []},
            }
        ]
        gatherer.gathered_data['investigation_hints']['timeline_evidence'] = {
            '#create-btn': {
                'selector': '#create-btn',
                'stale_test_signal': True,
                'product_commit_type': 'intentional_change',
                'days_difference': 77,
                'console_timeline': {
                    'last_modified': '2026-02-05',
                    'commit_message': 'refactor: standardize buttons',
                },
                'automation_timeline': {
                    'last_modified': '2025-11-20',
                },
            }
        }

        gatherer._inject_temporal_summaries()

        ctx = gatherer.gathered_data['test_report']['failed_tests'][0]['extracted_context']
        assert 'temporal_summary' in ctx
        ts = ctx['temporal_summary']
        assert ts['stale_test_signal'] is True
        assert ts['product_commit_type'] == 'intentional_change'
        assert ts['days_difference'] == 77
        assert ts['product_last_modified'] == '2026-02-05'
        assert ts['product_commit_message'] == 'refactor: standardize buttons'
        assert ts['automation_last_modified'] == '2025-11-20'

    def test_inject_skips_test_without_selector(self, gatherer):
        """Should skip tests that don't have a failing selector."""
        gatherer.gathered_data['test_report']['failed_tests'] = [
            {
                'test_name': 'test_no_selector',
                'parsed_stack_trace': {},
                'extracted_context': {},
            }
        ]
        gatherer.gathered_data['investigation_hints']['timeline_evidence'] = {
            '#some-btn': {'stale_test_signal': False, 'product_commit_type': None}
        }

        gatherer._inject_temporal_summaries()

        ctx = gatherer.gathered_data['test_report']['failed_tests'][0]['extracted_context']
        assert 'temporal_summary' not in ctx

    def test_inject_skips_when_no_timeline_evidence(self, gatherer):
        """Should do nothing when timeline_evidence is empty."""
        gatherer.gathered_data['test_report']['failed_tests'] = [
            {
                'test_name': 'test_a',
                'parsed_stack_trace': {'failing_selector': '#btn'},
                'extracted_context': {},
            }
        ]
        gatherer.gathered_data['investigation_hints']['timeline_evidence'] = {}

        gatherer._inject_temporal_summaries()

        ctx = gatherer.gathered_data['test_report']['failed_tests'][0]['extracted_context']
        assert 'temporal_summary' not in ctx

    def test_inject_skips_errored_timeline_evidence(self, gatherer):
        """Should skip timeline evidence entries that have errors."""
        gatherer.gathered_data['test_report']['failed_tests'] = [
            {
                'test_name': 'test_err',
                'parsed_stack_trace': {'failing_selector': '#err-btn'},
                'extracted_context': {},
            }
        ]
        gatherer.gathered_data['investigation_hints']['timeline_evidence'] = {
            '#err-btn': {'selector': '#err-btn', 'error': 'Git error'}
        }

        gatherer._inject_temporal_summaries()

        ctx = gatherer.gathered_data['test_report']['failed_tests'][0]['extracted_context']
        assert 'temporal_summary' not in ctx

    def test_inject_creates_extracted_context_if_missing(self, gatherer):
        """Should create extracted_context dict if it doesn't exist."""
        gatherer.gathered_data['test_report']['failed_tests'] = [
            {
                'test_name': 'test_no_ctx',
                'parsed_stack_trace': {'failing_selector': '#btn'},
                # no extracted_context key
            }
        ]
        gatherer.gathered_data['investigation_hints']['timeline_evidence'] = {
            '#btn': {
                'selector': '#btn',
                'stale_test_signal': False,
                'product_commit_type': 'ambiguous',
                'days_difference': 10,
                'console_timeline': {'last_modified': '2026-01-01'},
                'automation_timeline': {'last_modified': '2025-12-22'},
            }
        }

        gatherer._inject_temporal_summaries()

        ctx = gatherer.gathered_data['test_report']['failed_tests'][0]['extracted_context']
        assert 'temporal_summary' in ctx
        assert ctx['temporal_summary']['stale_test_signal'] is False

    def test_inject_handles_missing_timeline_sub_fields(self, gatherer):
        """Should handle missing console_timeline and automation_timeline gracefully."""
        gatherer.gathered_data['test_report']['failed_tests'] = [
            {
                'test_name': 'test_minimal',
                'parsed_stack_trace': {'failing_selector': '#btn'},
                'extracted_context': {},
            }
        ]
        gatherer.gathered_data['investigation_hints']['timeline_evidence'] = {
            '#btn': {
                'selector': '#btn',
                'stale_test_signal': False,
                'product_commit_type': None,
                'days_difference': None,
                # no console_timeline or automation_timeline
            }
        }

        gatherer._inject_temporal_summaries()

        ts = gatherer.gathered_data['test_report']['failed_tests'][0]['extracted_context']['temporal_summary']
        assert ts['stale_test_signal'] is False
        assert 'product_last_modified' not in ts
        assert 'automation_last_modified' not in ts
