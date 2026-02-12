# JIRA MCP Server

Full JIRA integration for issue search, creation, management, team operations, and component aliases via the Model Context Protocol (MCP).

Part of the [AI Systems Suite](../../README.md). Used by the [Z-Stream Analysis](../../apps/z-stream-analysis/) application for JIRA correlation during pipeline failure analysis.

**Repository:** [github.com/stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server)

This is an **external server** maintained in a separate public GitHub repository.
The setup script (`mcp/setup.sh`) clones it into `mcp/jira/jira-mcp-server/` (gitignored).

---

## Prerequisites

- Python 3.10+
- Access to a JIRA instance (Cloud or Server/Data Center)
- JIRA Personal Access Token (see Step 3 below)

## New User Setup

The easiest way: run `bash mcp/setup.sh` from the repo root. It handles steps 1–5 automatically.

To set up manually:

### Step 1: Clone and install

```bash
# From the repository root:
git clone https://github.com/stolostron/jira-mcp-server.git mcp/jira/jira-mcp-server
pip install -e mcp/jira/jira-mcp-server
```

### Step 2: Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` with your JIRA credentials:

```env
JIRA_SERVER_URL=https://issues.redhat.com
JIRA_ACCESS_TOKEN=your-personal-access-token
JIRA_VERIFY_SSL=true
JIRA_TIMEOUT=30
JIRA_MAX_RESULTS=100

# Optional: Configure teams (JSON format with JIRA usernames, NOT email addresses)
JIRA_TEAMS={"my-team": ["user1", "user2"]}

# Optional: Configure component aliases
JIRA_COMPONENT_ALIASES={"ui": "User Interface", "be": "Backend Services"}
```

### Step 3: Get your JIRA API token

**For JIRA Cloud (Atlassian Cloud):**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token and set it as `JIRA_ACCESS_TOKEN` in your `.env`

**For JIRA Server/Data Center (e.g., Red Hat JIRA):**
1. Log in to your JIRA instance
2. Go to Profile > Personal Access Tokens
3. Create a new token with appropriate permissions
4. Copy the token and set it as `JIRA_ACCESS_TOKEN` in your `.env`

### Step 4: Verify the connection

```bash
# Start the server manually to test
python -m jira_mcp_server.main
```

If it starts without errors, authentication is working.

### Step 5: Configure MCP

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "python",
      "args": ["-m", "jira_mcp_server.main"],
      "cwd": "/absolute/path/to/jira-mcp-server"
    }
  }
}
```

The `cwd` must be the absolute path to the directory where `jira-mcp-server` was cloned and installed (where the `.env` file lives).

For Cursor IDE, add to `~/.cursor/mcp.json` with the same format plus `"timeout": 60`.

## Available Tools (23)

### Issue Operations

| Tool | Description |
|------|-------------|
| `search_issues` | JQL search for issues |
| `get_issue` | Get full issue details |
| `create_issue` | Create new bug/task |
| `update_issue` | Update issue fields |
| `transition_issue` | Move issue status (e.g., In Progress, Done) |
| `add_comment` | Add comment to issue |
| `log_time` | Log work time on issue |
| `link_issue` | Create links between issues (Blocks, Relates, etc.) |

### Project & Component

| Tool | Description |
|------|-------------|
| `get_projects` | List accessible projects |
| `get_project_components` | List components in a project |
| `get_link_types` | List available link types |
| `debug_issue_fields` | Show all raw fields for an issue |

### Team Management

| Tool | Description |
|------|-------------|
| `list_teams` | List configured teams |
| `add_team` | Add/update team configuration |
| `remove_team` | Remove team configuration |
| `search_issues_by_team` | Find issues assigned to team members |
| `assign_team_to_issue` | Add all team members as watchers |
| `add_watcher_to_issue` | Add a watcher to an issue |
| `remove_watcher_from_issue` | Remove a watcher from an issue |
| `get_issue_watchers` | List watchers on an issue |

### Component Aliases

| Tool | Description |
|------|-------------|
| `list_component_aliases` | List configured component aliases |
| `add_component_alias` | Add/update a component alias |
| `remove_component_alias` | Remove a component alias |

## Usage in Z-Stream Analysis

During Stage 2 (AI Analysis), the JIRA MCP is used in:

- **Phase D (Classification Routing)**: Search for related bugs and known issues
- **Phase E (Feature Context)**: Read feature stories and acceptance criteria to understand expected behavior

Example JQL queries used during analysis:

```jql
project = ACM AND type = Bug AND summary ~ "search" AND status != Closed
project = ACM AND fixVersion = "2.16.0" AND type = Story AND summary ~ "RBAC"
```

## Full Documentation

See the [jira-mcp-server repository](https://github.com/stolostron/jira-mcp-server) for complete documentation including:
- Authentication setup
- Environment variable configuration
- Team and component alias management
- JQL query syntax reference
