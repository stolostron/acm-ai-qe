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

"""Tests for team management functionality."""

import os
import json
import pytest
from jira_mcp_server.config import JiraConfig


class TestTeamConfiguration:
    """Test team configuration in JiraConfig."""
    
    def test_teams_from_env(self):
        """Test loading teams from environment variable."""
        teams = {
            "frontend": ["alice", "bob"],
            "backend": ["charlie", "david"]
        }
        os.environ["JIRA_TEAMS"] = json.dumps(teams)
        
        config = JiraConfig.from_env()
        
        assert "frontend" in config.teams
        assert "backend" in config.teams
        assert config.teams["frontend"] == ["alice", "bob"]
        assert config.teams["backend"] == ["charlie", "david"]
    
    def test_empty_teams_env(self):
        """Test with empty or missing JIRA_TEAMS environment variable."""
        os.environ["JIRA_TEAMS"] = ""
        
        config = JiraConfig.from_env()
        
        assert config.teams == {}
    
    def test_invalid_teams_json(self):
        """Test with invalid JSON in JIRA_TEAMS."""
        os.environ["JIRA_TEAMS"] = "invalid json"
        
        config = JiraConfig.from_env()
        
        # Should default to empty dict on invalid JSON
        assert config.teams == {}
    
    def test_get_team_members(self):
        """Test getting team members."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={"frontend": ["alice", "bob"]}
        )
        
        members = config.get_team_members("frontend")
        
        assert members == ["alice", "bob"]
    
    def test_get_team_members_not_found(self):
        """Test getting members of non-existent team."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={"frontend": ["alice", "bob"]}
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.get_team_members("nonexistent")
        
        assert "not found" in str(exc_info.value).lower()
        assert "frontend" in str(exc_info.value)
    
    def test_add_team(self):
        """Test adding a new team."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={}
        )
        
        config.add_team("devops", ["eve", "frank"])
        
        assert "devops" in config.teams
        assert config.teams["devops"] == ["eve", "frank"]
    
    def test_update_team(self):
        """Test updating an existing team."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={"frontend": ["alice", "bob"]}
        )
        
        config.add_team("frontend", ["alice", "bob", "grace"])
        
        assert config.teams["frontend"] == ["alice", "bob", "grace"]
    
    def test_remove_team(self):
        """Test removing a team."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={"frontend": ["alice", "bob"], "backend": ["charlie"]}
        )
        
        config.remove_team("frontend")
        
        assert "frontend" not in config.teams
        assert "backend" in config.teams
    
    def test_remove_team_not_found(self):
        """Test removing a non-existent team."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={}
        )
        
        with pytest.raises(ValueError) as exc_info:
            config.remove_team("nonexistent")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_list_teams(self):
        """Test listing all teams."""
        teams = {
            "frontend": ["alice", "bob"],
            "backend": ["charlie", "david"]
        }
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams=teams
        )
        
        all_teams = config.list_teams()
        
        assert all_teams == teams
        # Verify it's a copy, not a reference
        all_teams["newteam"] = ["someone"]
        assert "newteam" not in config.teams
    
    def test_multiple_teams(self):
        """Test managing multiple teams."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={}
        )
        
        # Add multiple teams
        config.add_team("frontend", ["alice", "bob"])
        config.add_team("backend", ["charlie", "david"])
        config.add_team("devops", ["eve"])
        
        assert len(config.teams) == 3
        assert config.get_team_members("frontend") == ["alice", "bob"]
        assert config.get_team_members("backend") == ["charlie", "david"]
        assert config.get_team_members("devops") == ["eve"]
    
    def test_team_with_empty_members(self):
        """Test team with empty member list."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={}
        )
        
        config.add_team("empty-team", [])
        
        assert "empty-team" in config.teams
        assert config.teams["empty-team"] == []


class TestTeamIntegration:
    """Integration tests for team management (requires mocking or real Jira instance)."""
    
    def test_team_configuration_lifecycle(self):
        """Test complete lifecycle of team configuration."""
        config = JiraConfig(
            server_url="https://test.atlassian.net",
            access_token="test-token",
            teams={}
        )
        
        # Start with no teams
        assert len(config.list_teams()) == 0
        
        # Add a team
        config.add_team("team1", ["user1", "user2"])
        assert len(config.list_teams()) == 1
        
        # Update the team
        config.add_team("team1", ["user1", "user2", "user3"])
        assert len(config.get_team_members("team1")) == 3
        
        # Add another team
        config.add_team("team2", ["user4"])
        assert len(config.list_teams()) == 2
        
        # Remove a team
        config.remove_team("team1")
        assert len(config.list_teams()) == 1
        assert "team2" in config.teams

