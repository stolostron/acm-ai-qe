# Polarion MCP Server

Read-only access to Polarion test cases and work items via the Model Context Protocol (MCP).

Part of the [AI Systems Suite](../../README.md). Provides access to RHACM4K test case content for reference during test plan generation and pipeline failure analysis.

**Base Package:** [`polarion-mcp`](https://pypi.org/project/polarion-mcp/) (via `uvx`)
**Wrapper Script:** `polarion-mcp-wrapper.py` (this directory)
**Primary Project:** `RHACM4K` (Red Hat Advanced Cluster Management for Kubernetes)

---

## Architecture

The Polarion MCP runs as a wrapper around the base `polarion-mcp` package:

```
AI Agent (Claude Code / Cursor)
  └─ MCP protocol (stdio)
       └─ uvx (runs polarion-mcp in isolated env)
            └─ polarion-mcp-wrapper.py
                 ├─ Patches SSL verification (Red Hat internal CA)
                 ├─ Patches request timeouts (30s vs 8s default)
                 ├─ Registers 3 enhanced tools
                 └─ Delegates to polarion_mcp.server.run()
                      └─ Base polarion-mcp tools (14 tools)
```

The wrapper exists because Red Hat's internal Polarion instance uses certificates not in the default CA bundle. Without SSL patching, all requests fail with certificate errors.

---

## Prerequisites

- Python 3.10+
- `uvx` (from `uv` package)
- Network access to Red Hat internal Polarion instance (VPN)
- Polarion JWT Personal Access Token

## New User Setup

### Step 1: Install `uv` (provides `uvx`)

```bash
# macOS / Linux
pip install uv

# Or via pipx
pipx install uv

# Verify
uvx --version
```

`uvx` runs Python packages in isolated environments without permanent installation.

### Step 2: Generate a Polarion Personal Access Token (PAT)

1. Log in to Polarion at https://polarion.engineering.redhat.com/polarion
2. Click your user icon (top-right) > **My Account**
3. Go to the **Personal Access Tokens** tab
4. Click **Create Token**
5. Set a description (e.g., "MCP Server") and expiration date
6. Copy the generated JWT token (you won't be able to see it again)

**Note:** You must be on the Red Hat VPN to access Polarion.

### Step 3: Configure MCP

Add to your project's `.mcp.json` or `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "polarion": {
      "command": "uvx",
      "args": ["--with", "polarion-mcp", "python",
               "/absolute/path/to/ai_systems_v2/mcp/polarion/polarion-mcp-wrapper.py"],
      "env": {
        "POLARION_BASE_URL": "https://polarion.engineering.redhat.com/polarion",
        "POLARION_PAT": "your-jwt-token-here"
      },
      "timeout": 90
    }
  }
}
```

Replace `/absolute/path/to/ai_systems_v2` with the actual path on your machine.

**Key points:**
- `uvx` creates an isolated Python environment with `polarion-mcp` installed
- The wrapper script patches SSL verification for Red Hat's internal CA
- `POLARION_PAT` can also be set at runtime via the `set_polarion_token` tool
- Timeout is 90s (higher than other MCPs due to Polarion's slower API)

### Step 4: Verify the connection

After restarting your MCP client (Claude Code, Cursor), run:
- `check_polarion_status` — should show authenticated
- `get_polarion_project(project_id="RHACM4K")` — should return project details

If you get a 401 error, your token may be expired. Generate a new one (Step 2) and update your config or call `set_polarion_token`.

---

## Tools Reference

### Working Tools (17 total)

#### Base Tools (from polarion-mcp package)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `check_polarion_status` | Verify authentication and connection | None |
| `set_polarion_token` | Set/update JWT token at runtime | `token` |
| `get_polarion_project` | Get single project details | `project_id`, `fields` |
| `get_polarion_work_items` | Search work items with Lucene query | `project_id`, `query`, `limit`, `page_number` |
| `get_polarion_work_item` | Get single work item details | `project_id`, `work_item_id`, `fields` |
| `get_polarion_work_items_details` | Batch get details for multiple items | `project_id`, `work_item_ids` (comma-separated string), `custom_fields` |
| `get_polarion_work_item_text` | Get formatted text content | `project_id`, `work_item_id` |
| `get_polarion_work_item_revisions` | Get revision history | `project_id`, `work_item_id` |
| `get_polarion_work_item_at_revision` | Get item at specific revision | `project_id`, `work_item_id`, `revision_id` |
| `get_polarion_document` | Access structured documents | `project_id`, `space_id`, `document_name` |
| `get_polarion_projects` | List all projects | `limit` |
| `open_polarion_login` | Open login page for auth | None |
| `create_polarion_work_item` | Create new work item (needs passcode) | `passcode`, `project_id`, `work_item_type`, `title`, ... |
| `polarion_github_requirements_coverage` | Requirements coverage analysis | `project_id`, `topic` |

#### Enhanced Tools (added by wrapper)

| Tool | Purpose | Parameters |
|------|---------|------------|
| `get_polarion_test_steps` | Fetch test step content (step HTML + expected results) | `project_id`, `work_item_id` |
| `get_polarion_test_case_summary` | Quick overview: title, setup status, step count, step titles | `project_id`, `work_item_id` |
| `get_polarion_setup_html` | Get raw Setup section HTML | `project_id`, `work_item_id` |

Enhanced tools use the Polarion REST API `/teststeps` endpoint directly and have 30s timeout (vs base 8s).

### Tools with Known Issues

| Tool | Status | Issue |
|------|--------|-------|
| `get_polarion_projects` | 403 Forbidden | User lacks permission to list ALL projects. Use specific `project_id` instead. |
| `get_polarion_work_item_text` | Partial | Returns empty content for some work items. Use `get_polarion_work_item` with `fields="@all"` instead. |
| `get_polarion_document` | Requires setup | Needs `space_id` and `document_name` (not discoverable via API). |
| `get_polarion_work_item_at_revision` | Requires setup | Needs `revision_id` from `get_polarion_work_item_revisions` first. |
| `polarion_github_requirements_coverage` | Requires setup | Needs connected GitHub repo context. |

---

## Query Syntax

`get_polarion_work_items` uses Lucene query syntax.

### Verified Searchable Fields

| UI Label | Query Field | Example Values |
|----------|-------------|----------------|
| Type | `type` | `testcase`, `requirement` |
| Status | `status` | `proposed`, `approved`, `inactive` |
| Level | `caselevel` | `system`, `integration`, `component` |
| Component | `casecomponent` | `virtualization`, `Cluster Lifecycle` |
| Test Type | `testtype` | `functional`, `nonfunctional` |
| Subtype 1 | `subtype1` | `system`, `-` |
| Pos/Neg | `caseposneg` | `positive`, `negative` |
| Importance | `caseimportance` | `critical`, `high`, `medium`, `low` |
| Automation | `caseautomation` | `notautomated`, `automated`, `manualonly` |
| Author | `author.id` | `ashafi`, `username` |
| Title | `title` | `"RBAC UI"`, `"[FG-RBAC-2.16]"` |
| Description | `description` | `RBAC`, `migration` |
| Product/Release | `product` | `rhacm2-16`, `rhacm2-15` |

**Fields that do NOT work:** `subcomponent`, `tags`

### Query Examples

```lucene
# Find proposed virtualization test cases by author
type:testcase AND author.id:ashafi AND casecomponent:virtualization AND status:proposed

# Find not-yet-automated test cases
type:testcase AND author.id:ashafi AND caseautomation:notautomated

# Find RBAC UI test cases by title pattern
type:testcase AND title:"[FG-RBAC-2.16]"

# Find ACM 2.16 test cases
type:testcase AND product:rhacm2-16

# Combine multiple filters
type:testcase AND casecomponent:virtualization AND status:proposed AND caseautomation:notautomated
```

---

## Authentication

- **Token Type:** JWT (Personal Access Token)
- **Storage:** Set at runtime via `set_polarion_token` tool, or via `POLARION_PAT` env var in MCP config

### Token Refresh Procedure

1. Run `check_polarion_status` to verify current token
2. If expired: Generate new PAT from Polarion UI (My Account > Personal Access Tokens)
3. Run `set_polarion_token(token="NEW_TOKEN_HERE")`
4. Verify: `get_polarion_project(project_id="RHACM4K")`

---

## Permission Model

```
ALLOWED (Read-Only Access to RHACM4K):
  - View project details
  - Search work items (test cases, requirements)
  - Read work item content (description, setup, steps)
  - View work item revisions
  - View work item attachments list
  - View linked work items

NOT ALLOWED:
  - List all Polarion projects (403 Forbidden)
  - Create/update work items (read-only access)
  - Delete work items
  - Modify test case content

LIMITATION:
  - Can only access project: RHACM4K
  - Other projects may require separate permissions
```

---

## Limitations and Workarounds

| Limitation | Workaround |
|------------|------------|
| Read-only access | Use Polarion web UI for modifications |
| `get_polarion_projects` returns 403 | Always use `project_id="RHACM4K"` directly |
| Single project access (RHACM4K) | Request additional project access if needed |
| `get_polarion_document` needs space_id (not discoverable) | Ask user for space name or use work item search |
| `get_polarion_work_item_text` returns empty | Use `get_polarion_work_item` with `fields="@all"` |
| `work_item_ids` parameter format | Must be comma-separated string, NOT an array |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Token expired | Regenerate PAT and call `set_polarion_token` |
| 403 on `get_polarion_projects` | Normal -- user lacks list-all permission | Use specific `project_id` instead |
| 403 on work item | User lacks project permission | Verify project access |
| Empty response | Wrong fields param | Try `fields="@all"` or use different tool |
| SSL certificate error | Wrapper not loaded | Verify wrapper script path in MCP config |
| Timeout | Polarion slow response | Timeout is 90s in config; wrapper sets 30s per request |

---

## Polarion API Endpoints

Used by the wrapper's enhanced tools:

| Endpoint | Tool |
|----------|------|
| `/rest/v1/projects/{pid}/workitems/{wid}` | `get_polarion_work_item`, `get_polarion_setup_html`, `get_polarion_test_case_summary` |
| `/rest/v1/projects/{pid}/workitems/{wid}/teststeps` | `get_polarion_test_steps`, `get_polarion_test_case_summary` |

Base URL: `https://polarion.engineering.redhat.com/polarion`

---

## File Structure

```
mcp/polarion/
├── README.md                    ← This file
└── polarion-mcp-wrapper.py      ← Custom wrapper (SSL patches + 3 enhanced tools)
```
