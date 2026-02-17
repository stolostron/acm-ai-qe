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
Component Alias Management Example

This example demonstrates how to use component aliases in the Jira MCP Server.
"""

import sys
import os

# Add parent directory to path to import jira_mcp_server
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from jira_mcp_server.config import JiraConfig


def main():
    """Demonstrate component alias functionality."""
    
    print("=" * 60)
    print("Component Alias Management Example")
    print("=" * 60)
    print()
    
    # Create a config instance
    config = JiraConfig(
        server_url="https://example.atlassian.net",
        access_token="dummy-token",
        component_aliases={}
    )
    
    # 1. Add component aliases
    print("1. Adding component aliases...")
    config.add_component_alias("ui", "User Interface")
    config.add_component_alias("be", "Backend Services")
    config.add_component_alias("db", "Database")
    config.add_component_alias("infra", "Infrastructure")
    print("   Added 4 aliases")
    print()
    
    # 2. List all aliases
    print("2. Listing all component aliases:")
    aliases = config.list_component_aliases()
    for alias, component_name in aliases.items():
        print(f"   {alias:10s} → {component_name}")
    print()
    
    # 3. Resolve individual aliases
    print("3. Resolving individual aliases:")
    test_inputs = ["ui", "be", "Unknown Component", "db"]
    for input_name in test_inputs:
        resolved = config.get_component_name(input_name)
        if input_name in aliases:
            print(f"   '{input_name}' → '{resolved}' (alias resolved)")
        else:
            print(f"   '{input_name}' → '{resolved}' (not an alias, used as-is)")
    print()
    
    # 4. Resolve a list of component names (mix of aliases and actual names)
    print("4. Resolving a list of component names:")
    component_list = ["ui", "be", "Performance Testing", "db"]
    print(f"   Input:    {component_list}")
    resolved_list = config.resolve_component_names(component_list)
    print(f"   Resolved: {resolved_list}")
    print()
    
    # 5. Update an existing alias
    print("5. Updating an existing alias:")
    print(f"   Before: ui → {config.get_component_name('ui')}")
    config.add_component_alias("ui", "User Interface v2")
    print(f"   After:  ui → {config.get_component_name('ui')}")
    print()
    
    # 6. Remove an alias
    print("6. Removing an alias:")
    print(f"   Current aliases: {list(config.list_component_aliases().keys())}")
    config.remove_component_alias("infra")
    print(f"   After removing 'infra': {list(config.list_component_aliases().keys())}")
    print()
    
    # 7. Demonstrate use case: Creating an issue with components
    print("7. Example: Components for creating a Jira issue")
    components_to_use = ["ui", "be", "Integration Testing"]
    print(f"   Components specified: {components_to_use}")
    resolved_components = config.resolve_component_names(components_to_use)
    print(f"   Components sent to Jira: {resolved_components}")
    print()
    
    # 8. Load from environment variable (simulation)
    print("8. Loading aliases from environment variable:")
    os.environ["JIRA_COMPONENT_ALIASES"] = '{"fe": "Frontend", "api": "API Gateway"}'
    config2 = JiraConfig.from_env()
    print(f"   Loaded aliases: {config2.list_component_aliases()}")
    print()
    
    print("=" * 60)
    print("Component Alias Example Complete!")
    print("=" * 60)
    print()
    print("Key Takeaways:")
    print("  - Aliases make component names shorter and easier to use")
    print("  - Mix aliases with actual component names freely")
    print("  - Manage aliases dynamically at runtime or via environment")
    print("  - Aliases are case-sensitive")
    print("  - Unknown aliases are used as-is (assumed to be actual names)")


if __name__ == "__main__":
    main()

