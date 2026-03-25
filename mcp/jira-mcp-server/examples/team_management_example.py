#!/usr/bin/env python3
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

"""
Example demonstrating team management features in Jira MCP Server.

This example shows how to:
1. Configure teams via environment variable
2. Add/update teams dynamically
3. Create issues with team assignment
4. Assign teams to existing issues
5. Manage individual watchers
6. List watchers on issues
"""

import asyncio
import os
import json
from jira_mcp_server.config import JiraConfig
from jira_mcp_server.client import JiraClient


async def main():
    print("=" * 60)
    print("Jira MCP Server - Team Management Example")
    print("=" * 60)
    print()
    
    # Example 1: Configure teams via environment variable
    print("1. Configuring teams via environment variable")
    print("-" * 60)
    
    # Set up teams in environment (normally done in .env file)
    teams = {
        "frontend": ["alice", "bob"],
        "backend": ["charlie", "david"],
        "devops": ["eve"]
    }
    os.environ["JIRA_TEAMS"] = json.dumps(teams)
    
    # Load configuration
    config = JiraConfig.from_env()
    print(f"Loaded teams: {list(config.teams.keys())}")
    print()
    
    # Example 2: Dynamic team management
    print("2. Dynamic team management")
    print("-" * 60)
    
    # Add a new team
    config.add_team("qa", ["frank", "grace"])
    print(f"Added 'qa' team: {config.get_team_members('qa')}")
    
    # Update an existing team
    config.add_team("frontend", ["alice", "bob", "henry"])
    print(f"Updated 'frontend' team: {config.get_team_members('frontend')}")
    
    # List all teams
    all_teams = config.list_teams()
    print(f"\nAll teams:")
    for team_name, members in all_teams.items():
        print(f"  - {team_name}: {', '.join(members)}")
    print()
    
    # Example 3: Using teams with Jira client (requires valid credentials)
    print("3. Using teams with Jira (requires valid credentials)")
    print("-" * 60)
    
    if config.server_url and config.access_token:
        try:
            # Initialize client
            client = JiraClient(config)
            await client.connect()
            print("✓ Connected to Jira")
            
            # Example: Create an issue with team assignment
            # Note: Uncomment and modify these examples for your Jira instance
            
            # issue = await client.create_issue(
            #     project_key="PROJ",
            #     summary="Example issue with team",
            #     description="This issue will have the frontend team as watchers",
            #     issue_type="Task",
            #     priority={"name": "Medium"}
            # )
            # print(f"✓ Created issue: {issue['key']}")
            #
            # # Add team as watchers
            # result = await client.add_team_as_watchers(
            #     issue['key'],
            #     config.get_team_members('frontend')
            # )
            # print(f"✓ Added {result['total_added']} watchers from 'frontend' team")
            #
            # # Get watchers
            # watchers = await client.get_watchers(issue['key'])
            # print(f"✓ Current watchers:")
            # for watcher in watchers:
            #     print(f"  - {watcher['display_name']} ({watcher['username']})")
            
            print("\n(Examples are commented out - uncomment to use with your Jira)")
            
        except Exception as e:
            print(f"✗ Could not connect to Jira: {e}")
            print("  Make sure JIRA_SERVER_URL and JIRA_ACCESS_TOKEN are set")
    else:
        print("✗ Jira credentials not configured")
        print("  Set JIRA_SERVER_URL and JIRA_ACCESS_TOKEN in .env file")
    
    print()
    
    # Example 4: Team management best practices
    print("4. Team management best practices")
    print("-" * 60)
    print("""
    Best Practices:
    
    1. **Define teams by function**: frontend, backend, devops, qa
    2. **Keep teams updated**: Use add_team() to update member lists
    3. **Use meaningful names**: Make team names clear and descriptive
    4. **Configure per environment**: Different teams for prod vs staging
    5. **Combine with labels**: Use labels + teams for full visibility
    
    Example workflow:
    
    1. Configure teams in .env or dynamically
    2. Create issue with team parameter:
       create_issue(..., team="frontend")
    3. All team members automatically become watchers
    4. Team members receive notifications on updates
    5. Add/remove individual watchers as needed
    """)
    
    print("=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

