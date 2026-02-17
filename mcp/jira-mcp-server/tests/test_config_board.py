"""Tests for default board configuration fields in JiraConfig."""

import os
import pytest
from unittest.mock import patch

from jira_mcp_server.config import JiraConfig


class TestDefaultBoardConfig:
    def test_default_board_from_env(self):
        """Both JIRA_DEFAULT_BOARD_ID and JIRA_DEFAULT_BOARD_NAME are read from env."""
        with patch.dict(os.environ, {
            'JIRA_SERVER_URL': 'https://test.example.com',
            'JIRA_ACCESS_TOKEN': 'test-token',
            'JIRA_DEFAULT_BOARD_ID': '16103',
            'JIRA_DEFAULT_BOARD_NAME': 'ACM Console',
        }, clear=True):
            config = JiraConfig.from_env()
            assert config.default_board_id == 16103
            assert config.default_board_name == "ACM Console"

    def test_default_board_not_set(self):
        """Board defaults are None when env vars are not set."""
        with patch.dict(os.environ, {
            'JIRA_SERVER_URL': 'https://test.example.com',
            'JIRA_ACCESS_TOKEN': 'test-token',
        }, clear=True):
            config = JiraConfig.from_env()
            assert config.default_board_id is None
            assert config.default_board_name is None

    def test_default_board_id_only(self):
        """Only board ID set, name remains None."""
        with patch.dict(os.environ, {
            'JIRA_SERVER_URL': 'https://test.example.com',
            'JIRA_ACCESS_TOKEN': 'test-token',
            'JIRA_DEFAULT_BOARD_ID': '999',
        }, clear=True):
            config = JiraConfig.from_env()
            assert config.default_board_id == 999
            assert config.default_board_name is None

    def test_default_board_name_only(self):
        """Only board name set, ID remains None."""
        with patch.dict(os.environ, {
            'JIRA_SERVER_URL': 'https://test.example.com',
            'JIRA_ACCESS_TOKEN': 'test-token',
            'JIRA_DEFAULT_BOARD_NAME': 'My Board',
        }, clear=True):
            config = JiraConfig.from_env()
            assert config.default_board_id is None
            assert config.default_board_name == "My Board"
