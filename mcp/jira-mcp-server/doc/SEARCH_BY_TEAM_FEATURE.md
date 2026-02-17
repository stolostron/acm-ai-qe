# Search Issues by Team Feature

## Overview

Added a new `search_issues_by_team` tool that allows you to find all Jira issues assigned to any member of a configured team. This enhancement makes it easy to track team workload and see what issues a team is working on.

## Date
2025-11-14

## Feature Description

The new tool automatically generates JQL queries to search for issues where the assignee is one of the team members. This is different from the watcher functionality - it specifically finds issues **assigned to** team members, not just watched by them.

## Key Difference

**Watchers vs Assignees:**
- **Watchers**: Team members who receive notifications about issue updates
- **Assignees**: Team members who are responsible for working on issues

The `search_issues_by_team` tool searches for **assignees**, making it perfect for:
- Tracking team workload
- Sprint planning
- Capacity management
- Finding who's working on what

## Changes Made

### 1. New MCP Tool: `search_issues_by_team`

**File**: `jira_mcp_server/server.py`

**Location**: Added after `search_issues` tool (lines 198-256)

**Parameters**:
- `team_name` (required): Name of the team to search for
- `project_key` (optional): Filter by specific project
- `status` (optional): Filter by issue status
- `max_results` (optional): Maximum results to return (default: 100)

**Returns**: List of `IssueResponse` objects

### 2. Documentation Updates

**Files Updated**:
- `README.md`: Added tool description and examples
- `TEAM_MANAGEMENT.md`: Added comprehensive "Searching for Team Issues" section
- `TEAM_QUICKSTART.md`: Added quick examples and AI assistant usage

## Usage Examples

### Basic Usage

```python
# Find all issues assigned to frontend team
search_issues_by_team(team_name="frontend")
```

### With Filters

```python
# Find open issues assigned to backend team
search_issues_by_team(
    team_name="backend",
    status="Open"
)

# Find frontend team issues in specific project
search_issues_by_team(
    team_name="frontend",
    project_key="PROJ",
    status="In Progress"
)
```

### With AI Assistants

Simply ask natural language questions:
- "Find all issues assigned to the frontend team"
- "Show me open issues for the backend team"
- "What issues is the devops team working on?"
- "List all In Progress issues assigned to the QA team"

## How It Works

The tool automatically generates JQL queries based on team configuration:

**Example:**

For a team configured as:
```json
{"frontend": ["alice", "bob", "charlie"]}
```

The call:
```python
search_issues_by_team(
    team_name="frontend",
    project_key="PROJ",
    status="Open"
)
```

Generates the JQL:
```jql
project = PROJ AND (assignee = "alice" OR assignee = "bob" OR assignee = "charlie") AND status = "Open"
```

## Use Cases

### 1. Sprint Planning
```python
# Check team's current workload before planning
in_progress = search_issues_by_team(
    team_name="development",
    status="In Progress"
)
print(f"Team has {len(in_progress)} issues in progress")
```

### 2. Capacity Management
```python
# Analyze team workload across different statuses
in_progress = search_issues_by_team(team_name="frontend", status="In Progress")
open_issues = search_issues_by_team(team_name="frontend", status="Open")

print(f"Frontend team:")
print(f"  - Working on: {len(in_progress)} issues")
print(f"  - Backlog: {len(open_issues)} issues")
```

### 3. Feature Team Tracking
```python
# Track progress of a feature team
feature_team_issues = search_issues_by_team(team_name="payment-feature")
print(f"Payment feature team has {len(feature_team_issues)} total issues")
```

### 4. Cross-Project Visibility
```python
# See what a team is working on across multiple projects
all_team_work = search_issues_by_team(team_name="platform")
# Returns issues from all projects
```

## Implementation Details

### JQL Generation Logic

1. **Get team members** from configuration
2. **Build assignee clause**: `(assignee = "user1" OR assignee = "user2" OR ...)`
3. **Add optional filters**:
   - Project: `project = PROJ`
   - Status: `status = "Open"`
4. **Combine with AND**: `project = PROJ AND (assignee clause) AND status = "Open"`
5. **Execute search** using existing `search_issues` method

### Error Handling

- **Team not found**: Clear error message with available teams
- **Empty team**: ValueError if team has no members
- **Search failures**: Propagated with context information

## Testing

All tests passed successfully:

```
✓ Test 1: Importing modules
✓ Test 2: Creating config with teams
✓ Test 3: Verifying team members
✓ Test 4: Testing JQL generation logic
  Generated JQL: project = PROJ AND (assignee = "alice" OR assignee = "bob") AND status = "Open"
✓ Test 5: Testing JQL without filters
  Generated JQL: (assignee = "alice" OR assignee = "bob")
✓ Test 6: Verifying search_issues_by_team tool exists
  Server initialized successfully
```

## API Reference

### `search_issues_by_team`

Search for issues assigned to any member of a team.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_name` | str | Yes | Name of the team to search for |
| `project_key` | str | No | Project key to filter results (e.g., 'PROJ') |
| `status` | str | No | Status to filter results (e.g., 'Open', 'In Progress') |
| `max_results` | int | No | Maximum number of results (default: 100) |

**Returns:** `List[IssueResponse]`

**Raises:**
- `ValueError`: If team doesn't exist or has no members
- `Exception`: For search failures

## Benefits

1. **Simplified Queries**: No need to manually construct complex JQL with OR clauses
2. **Team-Centric**: Naturally organize work by team rather than individual
3. **Flexible Filtering**: Optional project and status filters for refined searches
4. **AI-Friendly**: Works seamlessly with natural language questions
5. **Workload Visibility**: Easy to see what each team is working on

## Comparison: Watchers vs Assignees

| Feature | Watchers | Assignees (this tool) |
|---------|----------|----------------------|
| **Purpose** | Get notifications | Responsible for work |
| **Tool** | `assign_team_to_issue` | `search_issues_by_team` |
| **Search By** | N/A (no search tool) | This new tool |
| **Use Case** | Keep team informed | Find team's work |
| **Action** | Add/remove watchers | Search assigned issues |

## Future Enhancements

Potential improvements:

1. **Additional Filters**: Priority, labels, components
2. **Date Ranges**: Created date, updated date filters
3. **Aggregation**: Group by status, priority, etc.
4. **Export**: Export results to CSV or JSON
5. **Trend Analysis**: Track team velocity over time

## Backward Compatibility

✅ **Fully backward compatible** - this is a new tool that doesn't affect existing functionality.

## Examples for Different Scenarios

### Daily Standup Preparation
```python
# See what the team worked on
team_issues = search_issues_by_team(
    team_name="backend",
    status="In Progress"
)
for issue in team_issues:
    print(f"{issue.key}: {issue.summary} (Assignee: {issue.assignee})")
```

### Sprint Review
```python
# Find completed work
completed = search_issues_by_team(
    team_name="frontend",
    status="Done"
)
print(f"Team completed {len(completed)} issues this sprint")
```

### Resource Planning
```python
# Check workload across teams
for team in ["frontend", "backend", "devops"]:
    issues = search_issues_by_team(team_name=team)
    print(f"{team}: {len(issues)} total issues")
```

## Documentation

All documentation has been updated with:
- Tool description and parameters
- Usage examples
- AI assistant integration examples
- Use case scenarios
- Quick reference guide

## Related Files

- `jira_mcp_server/server.py`: Implementation
- `README.md`: Main documentation
- `TEAM_MANAGEMENT.md`: Comprehensive team management guide
- `TEAM_QUICKSTART.md`: Quick start guide
- This document: Feature specification

## Authors

- AI Assistant (Claude Sonnet 4.5)
- User: rjung@redhat.com

## Status

✅ **Complete and Ready**
- Implementation: ✅ Done
- Testing: ✅ Passed
- Documentation: ✅ Updated
- Examples: ✅ Provided

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-14  
**Feature Type**: Enhancement

