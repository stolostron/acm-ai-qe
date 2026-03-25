# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file was developed with AI assistance.

"""Tests for configuration module."""

import os
import pytest
from unittest.mock import patch

from jira_mcp_server.config import JiraConfig


def test_config_from_env():
    """Test configuration creation from environment variables."""
    with patch.dict(os.environ, {
        'JIRA_SERVER_URL': 'https://test.atlassian.net',
        'JIRA_ACCESS_TOKEN': 'test-token',
        'JIRA_VERIFY_SSL': 'false',
        'JIRA_TIMEOUT': '60',
        'JIRA_MAX_RESULTS': '200'
    }):
        config = JiraConfig.from_env()
        
        assert config.server_url == 'https://test.atlassian.net'
        assert config.access_token == 'test-token'
        assert config.verify_ssl is False
        assert config.timeout == 60
        assert config.max_results == 200


def test_config_defaults():
    """Test configuration defaults."""
    with patch.dict(os.environ, {
        'JIRA_SERVER_URL': 'https://test.atlassian.net',
        'JIRA_ACCESS_TOKEN': 'test-token'
    }, clear=True):
        config = JiraConfig.from_env()
        
        assert config.verify_ssl is True  # default
        assert config.timeout == 30  # default
        assert config.max_results == 100  # default


def test_config_validation():
    """Test configuration validation."""
    config = JiraConfig(
        server_url="",
        access_token="test"
    )
    
    with pytest.raises(ValueError, match="JIRA_SERVER_URL is required"):
        config.validate_required_fields()
    
    config.server_url = "https://test.com"
    config.access_token = ""
    
    with pytest.raises(ValueError, match="JIRA_ACCESS_TOKEN is required"):
        config.validate_required_fields()
    
    # Should not raise when all fields are present
    config.access_token = "test"
    config.validate_required_fields()  # Should not raise