#!/usr/bin/env python3
"""
Unit tests for ACM UI MCP Client Service

Note: The ACM UI MCP Client has been simplified in v2.2.
- MCP protocol calls are now handled by Claude Code's native MCP integration
- Python client provides only fallback CNV version detection for Phase 1
- Tests updated to reflect this simplified behavior
"""

import json
import os
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock

from src.services.acm_ui_mcp_client import (
    ACMUIMCPClient,
    ElementInfo,
    SearchResult,
    CNVVersionInfo,
    FleetVirtSelectors,
    get_acm_ui_mcp_client,
    is_acm_ui_mcp_available
)


class TestACMUIMCPClientInit:
    """Tests for ACM UI MCP Client initialization."""

    def test_init_without_config(self):
        """Test initialization - config parameter is now ignored."""
        with TemporaryDirectory() as tmpdir:
            # Point to non-existent config - should not matter now
            fake_config_path = Path(tmpdir) / 'nonexistent.json'
            client = ACMUIMCPClient(mcp_config_path=fake_config_path)

            # is_available always returns False (use Claude Code native MCP instead)
            assert client.is_available is False

    def test_init_with_valid_config(self):
        """Test initialization with valid MCP config - now ignored."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'mcp.json'
            config = {
                'mcpServers': {
                    'acm-ui': {
                        'command': 'node',
                        'args': ['server.js'],
                        'env': {'DEBUG': '1'}
                    }
                }
            }
            config_path.write_text(json.dumps(config))

            client = ACMUIMCPClient(mcp_config_path=config_path)

            # is_available always returns False now (use Claude Code native MCP)
            assert client.is_available is False

    def test_init_with_alternate_server_names(self):
        """Test initialization - config parsing removed in v2.2."""
        client = ACMUIMCPClient()
        # is_available always returns False now
        assert client.is_available is False

    def test_init_with_invalid_json(self):
        """Test initialization with invalid JSON config - now ignored."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'mcp.json'
            config_path.write_text('{ invalid json }')

            client = ACMUIMCPClient(mcp_config_path=config_path)

            assert client.is_available is False

    def test_init_with_missing_server(self):
        """Test initialization when server is not in config - now ignored."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'mcp.json'
            config = {
                'mcpServers': {
                    'other-server': {
                        'command': 'node',
                        'args': []
                    }
                }
            }
            config_path.write_text(json.dumps(config))

            client = ACMUIMCPClient(mcp_config_path=config_path)

            assert client.is_available is False


class TestCNVVersionDetection:
    """Tests for CNV version detection functionality."""

    def test_detect_cnv_version_from_env(self):
        """Test CNV version detection from environment variable."""
        client = ACMUIMCPClient()

        # Mock subprocess to fail (force fallback to env)
        with patch('src.services.acm_ui_mcp_client.run_subprocess') as mock_run:
            mock_run.return_value = (False, '', 'error')

            with patch.dict(os.environ, {'CNV_VERSION': '4.20.3'}):
                result = client.detect_cnv_version()

                assert result is not None
                assert result.version == '4.20.3'
                assert result.branch == 'release-4.20'
                assert result.detected_from == 'env'

    def test_detect_cnv_version_fallback_returns_none(self):
        """Test CNV version detection returns None when nothing available."""
        client = ACMUIMCPClient()

        # Mock subprocess to fail
        with patch('src.services.acm_ui_mcp_client.run_subprocess') as mock_run:
            mock_run.return_value = (False, '', 'error')

            # Clear environment variable
            with patch.dict(os.environ, {}, clear=True):
                if 'CNV_VERSION' in os.environ:
                    del os.environ['CNV_VERSION']

                result = client.detect_cnv_version()
                assert result is None

    def test_detect_cnv_version_from_cluster(self):
        """Test CNV version detection from cluster."""
        client = ACMUIMCPClient()

        # Mock subprocess to return valid CSV info
        with patch('src.services.acm_ui_mcp_client.run_subprocess') as mock_run:
            mock_run.return_value = (True, 'kubevirt-hyperconverged-operator.v4.19.2,4.19.2', '')

            # Clear env to force cluster detection
            with patch.dict(os.environ, {}, clear=True):
                result = client.detect_cnv_version()

                assert result is not None
                assert result.version == '4.19.2'
                assert result.branch == 'release-4.19'
                assert result.detected_from == 'cluster'


class TestFleetVirtSelectors:
    """Tests for Fleet Virt selectors functionality."""

    def test_get_fleet_virt_selectors_unavailable(self):
        """Test get_fleet_virt_selectors returns None (use Claude Code MCP instead)."""
        client = ACMUIMCPClient()
        result = client.get_fleet_virt_selectors()
        assert result is None

    def test_get_fleet_virt_selectors_with_version(self):
        """Test get_fleet_virt_selectors with version - returns None."""
        client = ACMUIMCPClient()
        result = client.get_fleet_virt_selectors(version='4.20')
        assert result is None


class TestFindTestIds:
    """Tests for find_test_ids functionality."""

    def test_find_test_ids_unavailable(self):
        """Test find_test_ids returns empty list (use Claude Code MCP instead)."""
        client = ACMUIMCPClient()
        result = client.find_test_ids('some/path')
        assert result == []

    def test_find_test_ids_with_repository(self):
        """Test find_test_ids with repository - returns empty list."""
        client = ACMUIMCPClient()
        result = client.find_test_ids('some/path', repository='kubevirt')
        assert result == []


class TestSearchCode:
    """Tests for search_code functionality."""

    def test_search_code_unavailable(self):
        """Test search_code returns empty list (use Claude Code MCP instead)."""
        client = ACMUIMCPClient()
        result = client.search_code('test-query')
        assert result == []

    def test_search_code_with_options(self):
        """Test search_code with options - returns empty list."""
        client = ACMUIMCPClient()
        result = client.search_code('test-query', repository='acm', max_results=50)
        assert result == []


class TestFindElementDefinition:
    """Tests for find_element_definition functionality."""

    def test_find_element_definition_returns_empty(self):
        """Test find_element_definition returns empty dict."""
        client = ACMUIMCPClient()
        result = client.find_element_definition('#my-element')
        assert result == {}

    def test_find_element_definition_with_options(self):
        """Test find_element_definition with options - returns empty dict."""
        client = ACMUIMCPClient()
        result = client.find_element_definition('#my-element', search_all_repos=False)
        assert result == {}


class TestGetElementInventory:
    """Tests for get_element_inventory functionality."""

    def test_get_element_inventory_unavailable(self):
        """Test get_element_inventory returns empty dict."""
        client = ACMUIMCPClient()
        result = client.get_element_inventory()
        assert result == {}

    def test_get_element_inventory_with_paths(self):
        """Test get_element_inventory with custom paths - returns empty dict."""
        client = ACMUIMCPClient()
        result = client.get_element_inventory(component_paths=['src/components/'])
        assert result == {}


class TestDataclasses:
    """Tests for dataclass structures."""

    def test_element_info_creation(self):
        """Test ElementInfo dataclass creation."""
        info = ElementInfo(
            selector='my-button',
            selector_type='data-testid',
            file_path='src/components/Button.tsx',
            line_number=42,
            context='<button data-testid="my-button">',
            repository='acm'
        )

        assert info.selector == 'my-button'
        assert info.selector_type == 'data-testid'
        assert info.file_path == 'src/components/Button.tsx'
        assert info.line_number == 42
        assert info.repository == 'acm'

    def test_element_info_defaults(self):
        """Test ElementInfo dataclass defaults."""
        info = ElementInfo(
            selector='test',
            selector_type='id',
            file_path='test.tsx'
        )

        assert info.line_number is None
        assert info.context is None
        assert info.repository == ''

    def test_search_result_creation(self):
        """Test SearchResult dataclass creation."""
        result = SearchResult(
            file_path='src/App.tsx',
            line_number=100,
            line_content='const App = () => {',
            repository='acm',
            url='https://github.com/...'
        )

        assert result.file_path == 'src/App.tsx'
        assert result.line_number == 100
        assert result.repository == 'acm'
        assert result.url is not None

    def test_cnv_version_info_creation(self):
        """Test CNVVersionInfo dataclass creation."""
        info = CNVVersionInfo(
            version='4.20.3',
            branch='release-4.20',
            detected_from='cluster',
            csv_name='kubevirt-hyperconverged-operator.v4.20.3'
        )

        assert info.version == '4.20.3'
        assert info.branch == 'release-4.20'
        assert info.detected_from == 'cluster'

    def test_fleet_virt_selectors_creation(self):
        """Test FleetVirtSelectors dataclass creation."""
        selectors = FleetVirtSelectors(
            selectors={'button': ['submitBtn', 'cancelBtn']},
            selector_file='cypress/views/selector.ts',
            version='4.20',
            total_count=2
        )

        assert 'button' in selectors.selectors
        assert selectors.total_count == 2

    def test_fleet_virt_selectors_defaults(self):
        """Test FleetVirtSelectors dataclass defaults."""
        selectors = FleetVirtSelectors()

        assert selectors.selectors == {}
        assert selectors.selector_file is None
        assert selectors.total_count == 0


class TestSingletonFunctions:
    """Tests for singleton helper functions."""

    def test_get_acm_ui_mcp_client_returns_same_instance(self):
        """Test get_acm_ui_mcp_client returns singleton."""
        # Reset singleton for test
        import src.services.acm_ui_mcp_client as module
        module._acm_ui_mcp_client = None

        client1 = get_acm_ui_mcp_client()
        client2 = get_acm_ui_mcp_client()

        assert client1 is client2

    def test_is_acm_ui_mcp_available_returns_bool(self):
        """Test is_acm_ui_mcp_available returns boolean."""
        result = is_acm_ui_mcp_available()
        assert isinstance(result, bool)
        # Should be False since MCP is handled by Claude Code native MCP
        assert result is False


class TestToDictHelper:
    """Tests for to_dict helper method."""

    def test_to_dict_with_dataclass(self):
        """Test to_dict converts dataclass to dict."""
        client = ACMUIMCPClient()
        info = CNVVersionInfo(
            version='4.20.3',
            branch='release-4.20',
            detected_from='env'
        )

        result = client.to_dict(info)

        assert isinstance(result, dict)
        assert result['version'] == '4.20.3'
        assert result['branch'] == 'release-4.20'

    def test_to_dict_with_non_dataclass(self):
        """Test to_dict with non-dataclass returns empty dict."""
        client = ACMUIMCPClient()

        result = client.to_dict({'not': 'a dataclass'})

        assert result == {}


class TestVersionToBranch:
    """Tests for version to branch conversion."""

    def test_version_to_branch_standard(self):
        """Test standard version to branch conversion."""
        client = ACMUIMCPClient()

        assert client._version_to_branch('4.20.3') == 'release-4.20'
        assert client._version_to_branch('4.19.0') == 'release-4.19'
        assert client._version_to_branch('5.0.1') == 'release-5.0'

    def test_version_to_branch_short_version(self):
        """Test short version returns main."""
        client = ACMUIMCPClient()

        assert client._version_to_branch('4') == 'main'
        assert client._version_to_branch('') == 'main'

    def test_version_to_branch_two_parts(self):
        """Test two-part version."""
        client = ACMUIMCPClient()

        assert client._version_to_branch('4.20') == 'release-4.20'
