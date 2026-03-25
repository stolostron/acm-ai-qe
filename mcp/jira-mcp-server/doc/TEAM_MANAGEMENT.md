# Team Management Feature

## Overview

The Jira MCP Server now supports comprehensive team management, allowing you to define teams with multiple members and automatically assign them to issues as watchers. This feature enables better collaboration and ensures all team members stay informed about relevant issues.

## Key Features

### 1. **Team Configuration**
- Define teams with multiple members
- Configure teams via environment variables or dynamically at runtime
- Support for unlimited teams and team members

### 2. **Automatic Watcher Assignment**
- When a team is assigned to an issue, all team members are automatically added as watchers
- Team members receive notifications for all issue updates
- Ensures complete visibility across the team

### 3. **Flexible Team Management**
- Add, update, and remove teams at runtime
- List all configured teams and their members
- No need to restart the server when teams change

### 4. **Individual Watcher Control**
- Add or remove individual watchers
- Query all watchers on an issue
- Fine-grained control over notifications

## Configuration

### Important: Username vs Email

**⚠️ Use Usernames, Not Email Addresses**

The Jira API requires **usernames** (or account IDs for Jira Cloud), not email addresses:

- **Jira Server/Data Center**: Use the username (e.g., `"alice"`, not `"alice@example.com"`)
- **Jira Cloud**: Use the account ID or username (e.g., `"alice"` or `"5d123456789"`)

Email addresses will **not work** and will cause watcher additions to fail.

To find usernames:
1. Check the user's profile in Jira
2. Use the Jira API: `GET /rest/api/2/user/search?query=email@example.com`
3. Ask your Jira administrator

### Method 1: Environment Variable (Static)

Configure teams in your `.env` file:

```env
JIRA_TEAMS={"frontend": ["alice", "bob"], "backend": ["charlie", "david"], "devops": ["eve"]}
```

This is ideal for:
- Stable team structures
- Production environments
- Team configurations that rarely change

### Method 2: Dynamic Configuration (Runtime)

Use MCP tools to manage teams on the fly:

```python
# Add a new team
add_team(team_name="frontend", members=["alice", "bob", "charlie"])

# Update an existing team
add_team(team_name="frontend", members=["alice", "bob", "grace"])

# Remove a team
remove_team(team_name="old-team")

# List all teams
list_teams()
```

This is ideal for:
- Dynamic team structures
- Testing and development
- Temporary teams or project-based teams

## Usage Examples

### Creating Issues with Team Assignment

When creating a new issue, specify the `team` parameter to automatically add all team members as watchers:

```python
create_issue(
    project_key="PROJ",
    summary="Implement new login flow",
    description="Redesign the authentication system",
    issue_type="Story",
    priority="High",
    team="frontend"  # All frontend team members become watchers
)
```

### Assigning Teams to Existing Issues

Use the `assign_team_to_issue` tool to add a team to an existing issue:

```python
assign_team_to_issue(
    issue_key="PROJ-123",
    team_name="backend"
)
```

This returns:
```json
{
  "issue_key": "PROJ-123",
  "team_name": "backend",
  "successes": ["charlie", "david"],
  "failures": [],
  "total_added": 2,
  "total_failed": 0
}
```

### Managing Individual Watchers

#### Add a watcher
```python
add_watcher_to_issue(issue_key="PROJ-123", username="frank")
```

#### Remove a watcher
```python
remove_watcher_from_issue(issue_key="PROJ-123", username="frank")
```

#### List all watchers
```python
get_issue_watchers(issue_key="PROJ-123")
```

Returns:
```json
[
  {
    "username": "alice",
    "display_name": "Alice Smith",
    "email": "alice@example.com",
    "active": true
  },
  {
    "username": "bob",
    "display_name": "Bob Johnson",
    "email": "bob@example.com",
    "active": true
  }
]
```

## Available Tools

### Team Management

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_teams` | List all configured teams | None |
| `add_team` | Add or update a team | `team_name`, `members` |
| `remove_team` | Remove a team | `team_name` |
| `assign_team_to_issue` | Assign team to an issue | `issue_key`, `team_name` |
| `search_issues_by_team` | Find issues assigned to team members | `team_name`, `project_key` (opt), `status` (opt) |

### Watcher Management

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_issue_watchers` | Get all watchers on an issue | `issue_key` |
| `add_watcher_to_issue` | Add a single watcher | `issue_key`, `username` |
| `remove_watcher_from_issue` | Remove a watcher | `issue_key`, `username` |

## Searching for Team Issues

### Finding Issues Assigned to a Team

Use the `search_issues_by_team` tool to find all issues assigned to any team member:

```python
# Find all issues assigned to frontend team
search_issues_by_team(team_name="frontend")

# Find open issues assigned to backend team
search_issues_by_team(
    team_name="backend",
    status="Open"
)

# Find frontend team issues in a specific project
search_issues_by_team(
    team_name="frontend",
    project_key="PROJ",
    status="In Progress"
)
```

### How It Works

The tool automatically generates the appropriate JQL query:

**Example:** For a team with members `["alice", "bob", "charlie"]`:

```python
search_issues_by_team(team_name="frontend", project_key="PROJ", status="Open")
```

Generates:
```jql
project = PROJ AND (assignee = "alice" OR assignee = "bob" OR assignee = "charlie") AND status = "Open"
```

### Use with AI Assistants

Simply ask natural language questions:
- "Find all issues assigned to the frontend team"
- "Show me open issues for the backend team"
- "What issues is the devops team working on?"
- "List all In Progress issues assigned to the QA team"

## Use Cases

### 1. Sprint Planning
```python
# Create a sprint issue and assign it to the development team
create_issue(
    project_key="PROJ",
    summary="Sprint 23 Planning",
    description="Plan work for sprint 23",
    issue_type="Task",
    team="development",
    labels=["sprint-23", "planning"]
)

# Review what the team is currently working on
issues = search_issues_by_team(
    team_name="development",
    status="In Progress"
)
print(f"Team has {len(issues)} issues in progress")
```

### 2. Incident Management
```python
# Create a critical incident and notify the on-call team
create_issue(
    project_key="PROJ",
    summary="Production outage - Login service down",
    description="Users unable to login",
    issue_type="Bug",
    priority="Critical",
    team="oncall"
)
```

### 3. Cross-Team Collaboration
```python
# Assign multiple teams to a large initiative
assign_team_to_issue(issue_key="PROJ-100", team_name="frontend")
assign_team_to_issue(issue_key="PROJ-100", team_name="backend")
assign_team_to_issue(issue_key="PROJ-100", team_name="devops")
```

### 4. Feature Development
```python
# Configure a feature team dynamically
add_team(
    team_name="payment-feature",
    members=["alice", "bob", "charlie", "eve"]
)

# Assign all payment-related issues to the feature team
assign_team_to_issue(issue_key="PROJ-201", team_name="payment-feature")
assign_team_to_issue(issue_key="PROJ-202", team_name="payment-feature")

# Check team's workload
workload = search_issues_by_team(team_name="payment-feature")
print(f"Payment feature team has {len(workload)} total issues")
```

### 5. Team Capacity Planning
```python
# Check team workload across different statuses
in_progress = search_issues_by_team(
    team_name="frontend",
    status="In Progress"
)

open_issues = search_issues_by_team(
    team_name="frontend",
    status="Open"
)

print(f"Frontend team:")
print(f"  - Working on: {len(in_progress)} issues")
print(f"  - Backlog: {len(open_issues)} issues")
```

## Benefits

### 1. **Improved Visibility**
All team members are automatically notified of updates, ensuring everyone stays informed.

### 2. **Simplified Collaboration**
No need to add watchers one by one—assign the entire team with a single command.

### 3. **Flexible Configuration**
Teams can be configured statically in environment variables or dynamically at runtime.

### 4. **Scalability**
Easily manage large teams across multiple projects without manual watcher management.

### 5. **Environment-Specific Teams**
Different team configurations for production, staging, and development environments.

## Implementation Details

### Backend Components

1. **config.py**: Extended with team configuration support
   - `teams` field in `JiraConfig`
   - Methods: `get_team_members()`, `add_team()`, `remove_team()`, `list_teams()`

2. **client.py**: Added watcher management methods
   - `add_watcher()`: Add a single watcher
   - `remove_watcher()`: Remove a watcher
   - `get_watchers()`: List all watchers
   - `add_team_as_watchers()`: Bulk add team members

3. **server.py**: New MCP tools
   - Team management tools: `list_teams`, `add_team`, `remove_team`, `assign_team_to_issue`
   - Watcher management tools: `get_issue_watchers`, `add_watcher_to_issue`, `remove_watcher_from_issue`
   - Extended `create_issue` with `team` parameter

### Data Models

```python
class WatcherResponse(BaseModel):
    username: str
    display_name: str
    email: Optional[str]
    active: bool

class TeamAssignmentResponse(BaseModel):
    issue_key: str
    team_name: str
    successes: List[str]
    failures: List[Dict[str, str]]
    total_added: int
    total_failed: int

class TeamInfoResponse(BaseModel):
    teams: Dict[str, List[str]]
```

## Error Handling

The team management feature includes robust error handling:

1. **Missing Team**: Clear error message when referencing a non-existent team
2. **Partial Failures**: When adding team watchers, successes and failures are tracked separately
3. **Permission Errors**: Graceful handling when users don't have permission to add watchers
4. **Invalid Usernames**: Failed additions are reported without blocking successful ones

## Best Practices

### 1. **Team Naming**
- Use clear, descriptive names: `frontend`, `backend`, `devops`
- Avoid generic names: `team1`, `group-a`
- Consider including project context: `proj-frontend`, `proj-backend`

### 2. **Team Size**
- Keep teams focused (5-10 members ideal)
- Create specialized teams for different areas
- Use multiple teams for cross-functional work

### 3. **Configuration Management**
- Use environment variables for stable teams
- Use dynamic configuration for temporary teams
- Document team membership in your project

### 4. **Combining with Other Features**
- Use teams with labels for categorization
- Combine team assignment with specific assignees
- Use teams for notification, assignee for responsibility

### 5. **Security Considerations**
- Ensure team members have access to the project
- Use security levels to restrict comment visibility
- Review team membership regularly

## Troubleshooting

### Team Not Found
**Error**: `Team 'frontend' not found`

**Solution**: 
1. Check team configuration in `.env`
2. Use `list_teams()` to see available teams
3. Add the team with `add_team()`

### Permission Denied When Adding Watchers
**Error**: `Failed to add watcher alice to PROJ-123`

**Solution**:
1. Verify the user exists in Jira
2. **Use username, not email address!** (common issue)
3. Check if user has access to the project
4. Ensure you have permission to add watchers
5. For Jira Cloud, you may need to use account IDs instead of usernames

### Partial Team Assignment
**Issue**: Some team members added, others failed

**Explanation**: This is normal when:
- Some users don't have project access
- Some usernames are invalid
- Check the `failures` array in the response

## Future Enhancements

Potential future improvements to the team management feature:

1. **Team Hierarchies**: Support for nested teams (e.g., `engineering.frontend`)
2. **Team Roles**: Different roles within teams (lead, member, reviewer)
3. **Persistent Storage**: Save team configurations to database
4. **Team Analytics**: Track team activity and engagement
5. **Integration with Jira Groups**: Sync with native Jira groups
6. **Notification Preferences**: Per-team notification settings

## Migration Guide

If you're already using the Jira MCP Server, here's how to adopt team management:

### Step 1: Update Configuration
Add teams to your `.env` file:
```env
JIRA_TEAMS={"your-team": ["member1", "member2"]}
```

### Step 2: Test Team Assignment
Try assigning a team to an existing issue:
```python
assign_team_to_issue(issue_key="EXISTING-123", team_name="your-team")
```

### Step 3: Update Workflows
Modify your issue creation workflows to include team assignment:
```python
create_issue(..., team="your-team")
```

### Step 4: Train Your Team
Share this documentation with your team and demonstrate the new features.

## Support

For issues or questions about team management:
1. Check this documentation
2. Review the [README](README.md)
3. Open an issue on GitHub
4. Check Jira API documentation for watcher permissions

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-14  
**Minimum Server Version**: 1.0.0

