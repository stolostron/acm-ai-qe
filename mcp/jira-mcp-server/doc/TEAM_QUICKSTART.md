# Team Management Quick Start Guide

## 🚀 Get Started in 5 Minutes

This guide will help you quickly set up and use team management in the Jira MCP Server.

## Step 1: Configure Your Teams (30 seconds)

Add teams to your `.env` file:

```env
JIRA_TEAMS={"frontend": ["alice", "bob"], "backend": ["charlie", "david"]}
```

**Format:** JSON with team names as keys and member arrays as values.

**⚠️ Important:** Use **usernames**, not email addresses! Email addresses will not work.
- ✅ Good: `"alice"`, `"bob"`
- ❌ Bad: `"alice@example.com"`, `"bob@example.com"`

## Step 2: Create an Issue with Team Assignment (1 minute)

When creating a new issue, add the `team` parameter:

```python
create_issue(
    project_key="PROJ",
    summary="Fix login bug",
    description="Users can't log in",
    issue_type="Bug",
    priority="High",
    team="frontend"  # 👈 All frontend members become watchers
)
```

✅ **Result:** Issue created, and alice + bob are automatically added as watchers!

## Step 3: Assign Team to Existing Issue (30 seconds)

For existing issues, use `assign_team_to_issue`:

```python
assign_team_to_issue(
    issue_key="PROJ-123",
    team_name="backend"
)
```

✅ **Result:** charlie + david are now watching PROJ-123!

## Common Commands

### View All Configured Teams
```python
list_teams()
```

### Add a New Team (Runtime)
```python
add_team(
    team_name="devops",
    members=["eve", "frank"]
)
```

### See Who's Watching an Issue
```python
get_issue_watchers(issue_key="PROJ-123")
```

### Add Individual Watcher
```python
add_watcher_to_issue(issue_key="PROJ-123", username="grace")
```

### Remove Individual Watcher
```python
remove_watcher_from_issue(issue_key="PROJ-123", username="grace")
```

### Find Issues Assigned to a Team
```python
search_issues_by_team(team_name="frontend")

# With filters
search_issues_by_team(
    team_name="backend",
    project_key="PROJ",
    status="In Progress"
)
```

## Example: AI Assistant Usage

With Claude Code, Cursor, or Gemini CLI, you can simply ask:

```
"Create a new bug for the login issue and assign it to the frontend team"

"Show me who is watching PROJ-123"

"Assign the backend team to PROJ-456"

"Add alice as a watcher to PROJ-789"

"Find all issues assigned to the frontend team"

"Show me open issues for the backend team"
```

## Real-World Scenarios

### Scenario 1: Sprint Planning
```python
# Create sprint task, notify entire dev team
create_issue(
    project_key="PROJ",
    summary="Sprint 24 Planning",
    description="Plan work for next sprint",
    team="development"
)
```

### Scenario 2: Critical Incident
```python
# Urgent bug, notify on-call team immediately
create_issue(
    project_key="PROD",
    summary="Service Down - Payment Processing",
    description="All payment transactions failing",
    issue_type="Bug",
    priority="Critical",
    team="oncall"
)
```

### Scenario 3: Cross-Team Feature
```python
# Create feature issue
issue = create_issue(
    project_key="PROJ",
    summary="New Payment Gateway Integration",
    description="Integrate Stripe payment gateway",
    team="backend"
)

# Add frontend team too
assign_team_to_issue(
    issue_key=issue.key,
    team_name="frontend"
)
```

## Configuration Options

### Option 1: Static (via Environment)
Best for: Stable teams, production

```env
JIRA_TEAMS={"team1": ["user1", "user2"], "team2": ["user3"]}
```

### Option 2: Dynamic (via API)
Best for: Temporary teams, testing

```python
add_team(team_name="feature-team", members=["alice", "bob", "eve"])
# Use the team
create_issue(..., team="feature-team")
# Remove when done
remove_team(team_name="feature-team")
```

## Tips & Best Practices

### ✅ Do's
- Use descriptive team names (`frontend`, `backend`, not `team1`)
- Keep teams focused (5-10 members ideal)
- Review team membership regularly
- Use teams for visibility, assignee for responsibility

### ❌ Don'ts
- Don't create teams with too many members (>20)
- Don't use generic names like `group1` or `team-a`
- Don't forget to remove obsolete teams

## Troubleshooting

### Team not found?
```bash
# Check available teams
list_teams()

# Add the team if missing
add_team(team_name="myteam", members=["user1", "user2"])
```

### Some team members not added?
This is normal if:
- User doesn't exist in Jira
- User doesn't have access to the project
- Username is incorrect
- **You used email instead of username** ← Common mistake!

Check the response for `failures` array to see which users failed.

**Fix:** Use usernames instead of email addresses in your team configuration.

### Permission denied?
Ensure:
1. You have permission to add watchers
2. Team members have access to the project
3. Usernames are correct

## Next Steps

1. **Read Full Documentation**: See [TEAM_MANAGEMENT.md](TEAM_MANAGEMENT.md)
2. **Try Examples**: Run `python3 examples/team_management_example.py`
3. **Configure Your Teams**: Update your `.env` file
4. **Start Using**: Create issues with team assignment

## Quick Reference

| Action | Command |
|--------|---------|
| List teams | `list_teams()` |
| Add team | `add_team(name, members)` |
| Remove team | `remove_team(name)` |
| Create with team | `create_issue(..., team="name")` |
| Assign team | `assign_team_to_issue(key, team)` |
| Get watchers | `get_issue_watchers(key)` |
| Add watcher | `add_watcher_to_issue(key, user)` |
| Remove watcher | `remove_watcher_from_issue(key, user)` |
| Find team issues | `search_issues_by_team(team, ...)` |

---

**Need Help?** Check [TEAM_MANAGEMENT.md](TEAM_MANAGEMENT.md) or [README.md](README.md)

**Found a Bug?** Open an issue on GitHub

**Have Feedback?** We'd love to hear from you!

