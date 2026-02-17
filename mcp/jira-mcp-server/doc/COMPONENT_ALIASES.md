# Component Aliases Feature

This document provides a comprehensive guide to the Component Aliases feature in the Jira MCP Server.

## Overview

Component aliases allow you to use short, memorable names instead of long component names when creating or updating Jira issues. This feature is especially useful when:

- Component names are lengthy (e.g., "Advanced Cluster Management - User Interface")
- You work with the same components frequently
- You want to reduce typing and potential typos
- You want to standardize component naming across your team

## Features

- **Alias Resolution**: Automatically resolves aliases to actual component names
- **Mixed Usage**: Use aliases and actual component names together
- **Dynamic Configuration**: Add, update, and remove aliases at runtime
- **Environment Configuration**: Pre-configure aliases via environment variables
- **Case-Sensitive**: Aliases are case-sensitive for precise matching

## Configuration

### Static Configuration (Environment Variable)

Add component aliases to your `.env` file:

```env
JIRA_COMPONENT_ALIASES={"ui": "User Interface", "be": "Backend Services", "infra": "Infrastructure", "db": "Database"}
```

### Dynamic Configuration (Runtime)

Use MCP tools to manage aliases during runtime:

```python
# Add a new alias
add_component_alias(alias="ui", component_name="User Interface")

# Update an existing alias
add_component_alias(alias="ui", component_name="User Interface v2")

# Remove an alias
remove_component_alias(alias="ui")

# List all aliases
list_component_aliases()
```

## Usage Examples

### Creating Issues with Aliases

```python
# Use aliases in the components parameter
create_issue(
    project_key="ACM",
    summary="Fix login button",
    description="The login button is not responding to clicks",
    issue_type="Bug",
    priority="High",
    work_type="46654",
    due_date="2025-12-31",
    components=["ui", "be"]  # Will resolve to ["User Interface", "Backend Services"]
)
```

### Updating Issues with Aliases

```python
# Update components using aliases
update_issue(
    issue_key="ACM-123",
    priority="High",
    work_type="46654",
    due_date="2025-12-31",
    components=["ui", "db"]  # Mix of aliases
)
```

### Mixing Aliases with Actual Names

```python
# You can mix aliases with actual component names
create_issue(
    project_key="ACM",
    summary="Database optimization",
    description="Optimize database queries for better performance",
    issue_type="Task",
    priority="Medium",
    work_type="46654",
    due_date="2025-12-31",
    components=["db", "Performance Testing"]  # Alias + actual name
)
```

## MCP Tools

### `list_component_aliases`

List all configured component aliases.

**Returns**: A dictionary mapping aliases to actual component names

**Example**:
```python
aliases = list_component_aliases()
# Returns: {"ui": "User Interface", "be": "Backend Services", ...}
```

### `add_component_alias`

Add or update a component alias.

**Parameters**:
- `alias` (str): Short alias for the component (e.g., "ui", "be")
- `component_name` (str): Actual component name in Jira

**Returns**: Updated dictionary of all component aliases

**Example**:
```python
add_component_alias(alias="ui", component_name="User Interface")
add_component_alias(alias="fe", component_name="Frontend")
```

### `remove_component_alias`

Remove a component alias.

**Parameters**:
- `alias` (str): Alias to remove

**Returns**: Updated dictionary of remaining component aliases

**Raises**: `ValueError` if the alias doesn't exist

**Example**:
```python
remove_component_alias(alias="ui")
```

## Implementation Details

### How Alias Resolution Works

1. When you create or update an issue with components, the server checks each component name
2. If the component name matches an alias in the configuration, it's replaced with the actual component name
3. If no alias is found, the component name is used as-is (assumed to be the actual name)
4. The resolved component names are then sent to Jira

### Code Flow

```
User Input: ["ui", "Database"]
    ↓
Alias Resolution: 
    "ui" → "User Interface" (found in aliases)
    "Database" → "Database" (not an alias, used as-is)
    ↓
Result: ["User Interface", "Database"]
    ↓
Sent to Jira API
```

### Configuration Storage

Component aliases are stored in the `JiraConfig` class:

```python
class JiraConfig(BaseModel):
    # ... other fields ...
    component_aliases: Dict[str, str] = Field(
        default_factory=dict, 
        description="Component alias definitions mapping aliases to actual component names"
    )
```

## Best Practices

1. **Use Short, Memorable Aliases**: Keep aliases short (2-5 characters) for maximum efficiency
   - Good: `ui`, `be`, `db`, `infra`
   - Avoid: `user_interface_component`, `backend_services_v2`

2. **Document Your Aliases**: Keep a team document of standard aliases
   ```
   ui    → User Interface
   be    → Backend Services
   db    → Database
   infra → Infrastructure
   fe    → Frontend
   api   → API Gateway
   ```

3. **Consistency**: Use the same aliases across your team for better collaboration

4. **Case Sensitivity**: Remember aliases are case-sensitive
   - `ui` ≠ `UI` ≠ `Ui`

5. **Fallback to Actual Names**: If you're unsure, use the actual component name - it will work fine

6. **Environment vs Runtime**: 
   - Use environment variables for stable, team-wide aliases
   - Use runtime tools for experimental or temporary aliases

## Testing

The component alias feature includes comprehensive tests in `tests/test_component_aliases.py`:

- Configuration from environment variables
- Adding, updating, and removing aliases
- Alias resolution (single and batch)
- Mixed usage of aliases and actual names
- Error handling for non-existent aliases
- Coexistence with team management feature

## Troubleshooting

### Alias Not Resolving

**Problem**: Component alias is not being resolved to actual name

**Solutions**:
1. Check if the alias is configured: `list_component_aliases()`
2. Verify case sensitivity (aliases are case-sensitive)
3. Ensure the alias was added successfully
4. Check for typos in the alias name

### Component Not Found in Jira

**Problem**: Jira returns "component not found" error

**Solutions**:
1. Verify the actual component name exists in Jira
2. Check the component name spelling (even after alias resolution)
3. Use `get_project_components(project_key)` to see available components
4. Ensure you have permissions to use the component

### Alias Conflicts

**Problem**: An alias matches an actual component name

**Solution**: The alias will take precedence. Consider renaming the alias to avoid confusion.

## API Reference

### Configuration Methods

```python
# Get actual component name from alias (or return as-is)
config.get_component_name(alias_or_name: str) -> str

# Resolve a list of aliases/names
config.resolve_component_names(aliases_or_names: List[str]) -> List[str]

# Add or update an alias
config.add_component_alias(alias: str, component_name: str) -> None

# Remove an alias
config.remove_component_alias(alias: str) -> None

# List all aliases
config.list_component_aliases() -> Dict[str, str]
```

## Examples from Real Use Cases

### Red Hat Advanced Cluster Management

```python
# Configure common ACM component aliases
add_component_alias("addon", "Hypershift Addon Operator")
add_component_alias("hcp", "Hosted Control Planes")
add_component_alias("infra", "Infrastructure Management")
add_component_alias("ui", "Web Console")

# Create issue using aliases
create_issue(
    project_key="ACM",
    summary="Fix addon deployment issue",
    description="Addon fails to deploy on new clusters",
    issue_type="Bug",
    priority="High",
    work_type="46651",  # Incident & Support
    due_date="2025-11-30",
    components=["addon", "hcp"]  # Resolves to actual component names
)
```

### Multi-Component Projects

```python
# Configure aliases for different areas
add_component_alias("fe", "Frontend React Application")
add_component_alias("be", "Backend Node.js Services")
add_component_alias("db", "PostgreSQL Database")
add_component_alias("auth", "Authentication Service")
add_component_alias("api", "REST API Gateway")

# Create issue affecting multiple components
create_issue(
    project_key="MYAPP",
    summary="Performance degradation across stack",
    description="Response times increased by 50% in production",
    issue_type="Bug",
    priority="Critical",
    work_type="46651",
    due_date="2025-11-20",
    components=["fe", "api", "db"]  # Three components with short aliases
)
```

## Conclusion

Component aliases significantly improve the efficiency of working with Jira through the MCP server. By using short, memorable aliases, you can:

- Create and update issues faster
- Reduce typing errors
- Maintain consistency across your team
- Focus on the task rather than remembering exact component names

For more information, see the main README.md file or check the implementation in `jira_mcp_server/config.py` and `jira_mcp_server/server.py`.

