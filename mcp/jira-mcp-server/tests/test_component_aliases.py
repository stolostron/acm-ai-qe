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

"""Tests for component alias functionality."""

import os
import json
import pytest
from jira_mcp_server.config import JiraConfig


class TestComponentAliasConfiguration:
    """Test component alias configuration in JiraConfig."""
    
    def test_component_aliases_from_env(self):
        """Test loading component aliases from environment variable."""
        aliases = {
            "ui": "User Interface",
            "be": "Backend Services",
            "infra": "Infrastructure"
        }
        os.environ["JIRA_COMPONENT_ALIASES"] = json.dumps(aliases)
        
        config = JiraConfig.from_env()
        
        assert "ui" in config.component_aliases
        assert "be" in config.component_aliases
        assert "infra" in config.component_aliases
        assert config.component_aliases["ui"] == "User Interface"
        assert config.component_aliases["be"] == "Backend Services"
        assert config.component_aliases["infra"] == "Infrastructure"
    
    def test_empty_component_aliases_env(self):
        """Test with empty or missing JIRA_COMPONENT_ALIASES environment variable."""
        os.environ["JIRA_COMPONENT_ALIASES"] = ""
        
        config = JiraConfig.from_env()
        
        assert config.component_aliases == {}
    
    def test_invalid_component_aliases_json(self):
        """Test with invalid JSON in JIRA_COMPONENT_ALIASES."""
        os.environ["JIRA_COMPONENT_ALIASES"] = "invalid json"
        
        config = JiraConfig.from_env()
        
        # Should default to empty dict on invalid JSON
        assert config.component_aliases == {}
    
    def test_get_component_name_with_alias(self):
        """Test getting component name from an alias."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={"ui": "User Interface"}
        )
        
        component_name = config.get_component_name("ui")
        
        assert component_name == "User Interface"
    
    def test_get_component_name_without_alias(self):
        """Test getting component name when not an alias."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={"ui": "User Interface"}
        )
        
        component_name = config.get_component_name("Backend Services")
        
        # Should return the input as-is
        assert component_name == "Backend Services"
    
    def test_resolve_component_names(self):
        """Test resolving a list of component aliases."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={
                "ui": "User Interface",
                "be": "Backend Services"
            }
        )
        
        resolved = config.resolve_component_names(["ui", "be", "Database"])
        
        assert resolved == ["User Interface", "Backend Services", "Database"]
    
    def test_resolve_component_names_empty_list(self):
        """Test resolving an empty list."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={"ui": "User Interface"}
        )
        
        resolved = config.resolve_component_names([])
        
        assert resolved == []
    
    def test_add_component_alias(self):
        """Test adding a new component alias."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={}
        )
        
        config.add_component_alias("ui", "User Interface")
        
        assert "ui" in config.component_aliases
        assert config.component_aliases["ui"] == "User Interface"
    
    def test_update_component_alias(self):
        """Test updating an existing component alias."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={"ui": "User Interface"}
        )
        
        config.add_component_alias("ui", "User Interface v2")
        
        assert config.component_aliases["ui"] == "User Interface v2"
    
    def test_remove_component_alias(self):
        """Test removing a component alias."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={"ui": "User Interface", "be": "Backend Services"}
        )
        
        config.remove_component_alias("ui")
        
        assert "ui" not in config.component_aliases
        assert "be" in config.component_aliases
    
    def test_remove_component_alias_not_found(self):
        """Test removing a non-existent component alias."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={}
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.remove_component_alias("nonexistent")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_list_component_aliases(self):
        """Test listing all component aliases."""
        aliases = {
            "ui": "User Interface",
            "be": "Backend Services",
            "infra": "Infrastructure"
        }
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases=aliases
        )
        
        all_aliases = config.list_component_aliases()
        
        assert all_aliases == aliases
        # Verify it's a copy, not a reference
        all_aliases["new"] = "New Component"
        assert "new" not in config.component_aliases
    
    def test_multiple_component_aliases(self):
        """Test managing multiple component aliases."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={}
        )
        
        # Add multiple aliases
        config.add_component_alias("ui", "User Interface")
        config.add_component_alias("be", "Backend Services")
        config.add_component_alias("db", "Database")
        
        assert len(config.component_aliases) == 3
        assert config.get_component_name("ui") == "User Interface"
        assert config.get_component_name("be") == "Backend Services"
        assert config.get_component_name("db") == "Database"
    
    def test_component_alias_with_spaces(self):
        """Test component alias with spaces in component name."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={}
        )
        
        config.add_component_alias("frontend", "Frontend User Interface")
        
        assert config.get_component_name("frontend") == "Frontend User Interface"
    
    def test_component_alias_case_sensitive(self):
        """Test that component aliases are case-sensitive."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={"ui": "User Interface"}
        )
        
        # Lowercase should be resolved
        assert config.get_component_name("ui") == "User Interface"
        
        # Uppercase should not be resolved (return as-is)
        assert config.get_component_name("UI") == "UI"


class TestComponentAliasIntegration:
    """Integration tests for component alias management."""
    
    def test_component_alias_lifecycle(self):
        """Test complete lifecycle of component alias configuration."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={}
        )
        
        # Start with no aliases
        assert len(config.list_component_aliases()) == 0
        
        # Add an alias
        config.add_component_alias("ui", "User Interface")
        assert len(config.list_component_aliases()) == 1
        
        # Update the alias
        config.add_component_alias("ui", "User Interface v2")
        assert config.get_component_name("ui") == "User Interface v2"
        
        # Add another alias
        config.add_component_alias("be", "Backend Services")
        assert len(config.list_component_aliases()) == 2
        
        # Remove an alias
        config.remove_component_alias("ui")
        assert len(config.list_component_aliases()) == 1
        assert "be" in config.component_aliases
    
    def test_mixed_resolution(self):
        """Test resolving a mix of aliases and actual component names."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            component_aliases={
                "ui": "User Interface",
                "be": "Backend Services"
            }
        )
        
        # Mix of aliases and actual names
        components = ["ui", "Database", "be", "Infrastructure"]
        resolved = config.resolve_component_names(components)
        
        assert resolved == [
            "User Interface",  # ui -> User Interface
            "Database",        # No alias, returned as-is
            "Backend Services", # be -> Backend Services
            "Infrastructure"   # No alias, returned as-is
        ]
    
    def test_teams_and_aliases_coexist(self):
        """Test that teams and component aliases can coexist."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={"frontend": ["alice", "bob"]},
            component_aliases={"ui": "User Interface"}
        )
        
        # Test teams functionality
        assert config.get_team_members("frontend") == ["alice", "bob"]
        
        # Test component aliases functionality
        assert config.get_component_name("ui") == "User Interface"
        
        # Both should be independent
        assert len(config.teams) == 1
        assert len(config.component_aliases) == 1

