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

"""Configuration management for Jira MCP Server."""

import os
import json
from typing import Optional, Dict, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(override=True)


class JiraConfig(BaseModel):
    """Configuration for Jira connection."""

    server_url: str = Field(..., description="Jira server URL")
    access_token: str = Field(..., description="Jira personal access token or API token")
    email: Optional[str] = Field(default=None, description="Email for Jira Cloud authentication")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_results: int = Field(default=100, description="Maximum results per request")
    teams: Dict[str, List[str]] = Field(default_factory=dict, description="Team definitions mapping team names to member usernames")
    component_aliases: Dict[str, str] = Field(default_factory=dict, description="Component alias definitions mapping aliases to actual component names")

    @classmethod
    def from_env(cls) -> "JiraConfig":
        """Create configuration from environment variables.
        
        Teams can be configured via JIRA_TEAMS environment variable as JSON:
        JIRA_TEAMS='{"frontend": ["alice", "bob"], "backend": ["charlie", "david"]}'
        
        Component aliases can be configured via JIRA_COMPONENT_ALIASES environment variable as JSON:
        JIRA_COMPONENT_ALIASES='{"ui": "User Interface", "be": "Backend Services", "infra": "Infrastructure"}'
        """
        teams_json = os.getenv("JIRA_TEAMS", "{}")
        teams = {}
        try:
            teams = json.loads(teams_json)
        except json.JSONDecodeError:
            # If teams JSON is invalid, just use empty dict
            pass
        
        component_aliases_json = os.getenv("JIRA_COMPONENT_ALIASES", "{}")
        component_aliases = {}
        try:
            component_aliases = json.loads(component_aliases_json)
        except json.JSONDecodeError:
            # If component aliases JSON is invalid, just use empty dict
            pass
        
        return cls(
            server_url=os.getenv("JIRA_SERVER_URL", ""),
            access_token=os.getenv("JIRA_ACCESS_TOKEN", ""),
            email=os.getenv("JIRA_EMAIL"),
            verify_ssl=os.getenv("JIRA_VERIFY_SSL", "true").lower() == "true",
            timeout=int(os.getenv("JIRA_TIMEOUT", "30")),
            max_results=int(os.getenv("JIRA_MAX_RESULTS", "100")),
            teams=teams,
            component_aliases=component_aliases,
        )

    def is_cloud(self) -> bool:
        """Check if this is a Jira Cloud instance."""
        return "atlassian.net" in self.server_url.lower()

    def validate_required_fields(self) -> None:
        """Validate that required fields are present."""
        if not self.server_url:
            raise ValueError("JIRA_SERVER_URL is required")
        if not self.access_token:
            raise ValueError("JIRA_ACCESS_TOKEN is required")
        if self.is_cloud() and not self.email:
            raise ValueError("JIRA_EMAIL is required for Jira Cloud instances")
    
    def get_team_members(self, team_name: str) -> List[str]:
        """Get members of a team by name.
        
        Args:
            team_name: Name of the team
            
        Returns:
            List of member usernames
            
        Raises:
            ValueError: If team doesn't exist
        """
        if team_name not in self.teams:
            raise ValueError(f"Team '{team_name}' not found. Available teams: {list(self.teams.keys())}")
        return self.teams[team_name]
    
    def add_team(self, team_name: str, members: List[str]) -> None:
        """Add or update a team.
        
        Args:
            team_name: Name of the team
            members: List of member usernames
        """
        self.teams[team_name] = members
    
    def remove_team(self, team_name: str) -> None:
        """Remove a team.
        
        Args:
            team_name: Name of the team to remove
            
        Raises:
            ValueError: If team doesn't exist
        """
        if team_name not in self.teams:
            raise ValueError(f"Team '{team_name}' not found")
        del self.teams[team_name]
    
    def list_teams(self) -> Dict[str, List[str]]:
        """List all configured teams.
        
        Returns:
            Dictionary mapping team names to member lists
        """
        return self.teams.copy()
    
    def get_component_name(self, alias_or_name: str) -> str:
        """Get the actual component name from an alias or return the name if not an alias.
        
        Args:
            alias_or_name: Component alias or actual component name
            
        Returns:
            Actual component name
        """
        # If it's an alias, return the actual name
        if alias_or_name in self.component_aliases:
            return self.component_aliases[alias_or_name]
        # Otherwise return the input as-is (assuming it's the actual component name)
        return alias_or_name
    
    def resolve_component_names(self, aliases_or_names: List[str]) -> List[str]:
        """Resolve a list of component aliases to actual component names.
        
        Args:
            aliases_or_names: List of component aliases or actual component names
            
        Returns:
            List of actual component names
        """
        return [self.get_component_name(item) for item in aliases_or_names]
    
    def add_component_alias(self, alias: str, component_name: str) -> None:
        """Add or update a component alias.
        
        Args:
            alias: Short alias for the component
            component_name: Actual component name in Jira
        """
        self.component_aliases[alias] = component_name
    
    def remove_component_alias(self, alias: str) -> None:
        """Remove a component alias.
        
        Args:
            alias: Alias to remove
            
        Raises:
            ValueError: If alias doesn't exist
        """
        if alias not in self.component_aliases:
            raise ValueError(f"Component alias '{alias}' not found")
        del self.component_aliases[alias]
    
    def list_component_aliases(self) -> Dict[str, str]:
        """List all configured component aliases.
        
        Returns:
            Dictionary mapping aliases to actual component names
        """
        return self.component_aliases.copy()