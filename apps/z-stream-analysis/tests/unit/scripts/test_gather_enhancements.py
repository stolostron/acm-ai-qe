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
from src.services.feature_area_service import FeatureAreaService


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


class TestConsoleLogCredentialFallback:
    """Tests for _extract_credentials_from_console_log fallback method."""

    @pytest.fixture
    def gatherer(self):
        """Create a DataGatherer instance with mocked services."""
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None):
            gatherer = DataGatherer()
            gatherer.output_dir = Path('/tmp/test')
            gatherer.verbose = False
            gatherer.logger = Mock()
            gatherer.gathered_data = {}
            return gatherer

    def test_extracts_kubeadmin_format1(self, gatherer, tmp_path):
        """Format 1: flags before URL."""
        console = tmp_path / 'console-log.txt'
        console.write_text(
            '+ oc login --insecure-skip-tls-verify '
            '-u kubeadmin -p WXHWj-C25aT-fQ9cF-FQFUB '
            'https://api.example.com:6443\n'
        )
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is not None
        api_url, user, password = result
        assert api_url == 'https://api.example.com:6443'
        assert user == 'kubeadmin'
        assert password == 'WXHWj-C25aT-fQ9cF-FQFUB'

    def test_extracts_kubeadmin_format2(self, gatherer, tmp_path):
        """Format 2: --server prefix."""
        console = tmp_path / 'console-log.txt'
        console.write_text(
            '+ oc login -u kubeadmin -p secret123 '
            '--server https://api.cluster.example.com:6443 '
            '--insecure-skip-tls-verify=true\n'
        )
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is not None
        api_url, user, password = result
        assert api_url == 'https://api.cluster.example.com:6443'
        assert user == 'kubeadmin'
        assert password == 'secret123'

    def test_prioritizes_admin_over_test_users(self, gatherer, tmp_path):
        """Admin credentials should be returned even if test users appear first."""
        console = tmp_path / 'console-log.txt'
        console.write_text(
            '+ oc login -u clc-e2e-admin-cluster -p test-RBAC-4-e2e '
            '--server https://api.example.com:6443 --insecure-skip-tls-verify=true\n'
            '+ oc login -u kubeadmin -p realPassword '
            'https://api.example.com:6443\n'
        )
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is not None
        _, user, password = result
        assert user == 'kubeadmin'
        assert password == 'realPassword'

    def test_falls_back_to_first_match_when_no_admin(self, gatherer, tmp_path):
        """When no admin credentials exist, return the first match."""
        console = tmp_path / 'console-log.txt'
        console.write_text(
            '+ oc login -u clc-e2e-user -p testPass '
            '--server https://api.example.com:6443\n'
        )
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is not None
        _, user, password = result
        assert user == 'clc-e2e-user'
        assert password == 'testPass'

    def test_skips_masked_passwords(self, gatherer, tmp_path):
        """Masked passwords (all asterisks) should be skipped."""
        console = tmp_path / 'console-log.txt'
        console.write_text(
            '+ oc login -u kubeadmin -p **** '
            'https://api.example.com:6443\n'
            '+ oc login -u kubeadmin -p ******** '
            'https://api.example.com:6443\n'
        )
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is None

    def test_returns_none_when_no_console_log(self, gatherer, tmp_path):
        """Missing console log file should return None."""
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is None

    def test_returns_none_when_no_oc_login_lines(self, gatherer, tmp_path):
        """Console log without oc login commands should return None."""
        console = tmp_path / 'console-log.txt'
        console.write_text(
            'Running tests...\n'
            'Test completed\n'
            'Build finished\n'
        )
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is None

    def test_skips_lines_without_password(self, gatherer, tmp_path):
        """Lines with oc login but no -p flag should be skipped."""
        console = tmp_path / 'console-log.txt'
        console.write_text(
            '+ oc login --token=sha256~abc https://api.example.com:6443\n'
            "echo 'oc login will be done shortly'\n"
        )
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is None

    def test_handles_incomplete_oc_login(self, gatherer, tmp_path):
        """oc login with -p but missing -u or URL should be skipped."""
        console = tmp_path / 'console-log.txt'
        console.write_text(
            '+ oc login -p somepassword\n'
        )
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is None

    def test_admin_user_also_matches(self, gatherer, tmp_path):
        """The 'admin' username should also get priority."""
        console = tmp_path / 'console-log.txt'
        console.write_text(
            '+ oc login -u admin -p adminPass '
            'https://api.example.com:6443\n'
        )
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        assert result is not None
        _, user, _ = result
        assert user == 'admin'

    def test_handles_read_errors_gracefully(self, gatherer, tmp_path):
        """File read errors should return None, not raise."""
        console = tmp_path / 'console-log.txt'
        console.write_bytes(b'\x80\x81\x82 oc login -u kubeadmin -p pass https://api.x.com:6443\n')
        result = gatherer._extract_credentials_from_console_log(tmp_path)
        # Should not crash; may or may not find credentials depending on encoding
        assert result is None or len(result) == 3


class TestLoginToClusterFallback:
    """Tests for _login_to_cluster console log fallback integration."""

    @pytest.fixture
    def gatherer(self):
        """Create a DataGatherer with mocked services for login tests."""
        with patch.object(DataGatherer, '__init__', lambda x, **kwargs: None), \
             patch.object(FeatureAreaService, 'set_mch_namespace'):
            gatherer = DataGatherer()
            gatherer.output_dir = Path('/tmp/test')
            gatherer.verbose = False
            gatherer.logger = Mock()
            gatherer.gathered_data = {'jenkins': {'parameters': {}}}
            gatherer.env_service = Mock()
            gatherer.env_service.cli = 'oc'
            gatherer.cluster_investigation_service = Mock()
            gatherer.mch_namespace = 'open-cluster-management'
            yield gatherer

    def test_uses_jenkins_params_when_available(self, gatherer, tmp_path):
        """Should use Jenkins params and not try console log fallback."""
        gatherer.gathered_data['jenkins']['parameters'] = {
            'CYPRESS_HUB_API_URL': 'https://api.test.com:6443',
            'CYPRESS_OPTIONS_HUB_USER': 'kubeadmin',
            'OC_CLUSTER_PASS': 'jenkinsPass',
        }

        with patch.object(gatherer, '_persist_cluster_kubeconfig', return_value=None):
            with patch.object(gatherer, '_extract_credentials_from_console_log') as mock_fallback:
                gatherer._login_to_cluster(tmp_path)
                mock_fallback.assert_not_called()

        assert gatherer.gathered_data['cluster_access']['credential_source'] == 'jenkins_parameters'

    def test_falls_back_to_console_log(self, gatherer, tmp_path):
        """Should try console log when Jenkins params lack password."""
        gatherer.gathered_data['jenkins']['parameters'] = {
            'CYPRESS_HUB_API_URL': 'https://api.test.com:6443',
            'CYPRESS_OPTIONS_HUB_USER': 'kubeadmin',
        }

        console = tmp_path / 'console-log.txt'
        console.write_text(
            '+ oc login -u kubeadmin -p consolePass '
            'https://api.test.com:6443\n'
        )

        with patch.object(gatherer, '_persist_cluster_kubeconfig', return_value='/tmp/kc'):
            with patch.object(gatherer, '_discover_mch_namespace', return_value='ocm'):
                gatherer._login_to_cluster(tmp_path)

        access = gatherer.gathered_data['cluster_access']
        assert access['credential_source'] == 'console_log_fallback'
        assert access['has_credentials'] is True

    def test_records_no_credentials_when_both_fail(self, gatherer, tmp_path):
        """Should log warning when both methods fail."""
        gatherer.gathered_data['jenkins']['parameters'] = {}

        console = tmp_path / 'console-log.txt'
        console.write_text('no credentials here\n')

        gatherer._login_to_cluster(tmp_path)

        access = gatherer.gathered_data['cluster_access']
        assert access['has_credentials'] is False
        assert access['kubeconfig_path'] is None
