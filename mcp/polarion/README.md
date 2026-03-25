# Polarion MCP Server

Read and write access to Polarion test cases, test runs, plans, and work items via the Model Context Protocol (MCP).

**MCP Server Name (in Cursor):** `polarion` (appears as `user-polarion` in tool names)
**Primary Project:** `RHACM4K` (Red Hat Advanced Cluster Management for Kubernetes)
**Base Package:** [`polarion-mcp`](https://pypi.org/project/polarion-mcp/) (via `uvx`)
**Wrapper Script:** `polarion-mcp-wrapper.py` (this directory)

---

## Architecture

The Polarion MCP runs as a wrapper around the base `polarion-mcp` package:

```
Cursor IDE
  └─ MCP protocol (stdio)
       └─ uvx (runs polarion-mcp in isolated env)
            └─ polarion-mcp-wrapper.py
                 ├─ Patches SSL verification (Red Hat internal CA)
                 ├─ Patches request timeouts (30s vs 8s default)
                 ├─ Registers 11 enhanced tools (3 original + 8 new)
                 └─ Delegates to polarion_mcp.server.run()
                      └─ Base polarion-mcp tools (14 tools)
```

The wrapper exists because Red Hat's internal Polarion instance uses certificates not in the default CA bundle. Without SSL patching, all requests fail with certificate errors.

---

## mcp.json Configuration

```json
{
  "polarion": {
    "command": "uvx",
    "args": ["--with", "polarion-mcp", "python",
             "/Users/ashafi/Documents/work/ai/tools/mcp/polarion/polarion-mcp-wrapper.py"],
    "cwd": "/Users/ashafi",
    "env": {
      "POLARION_BASE_URL": "https://polarion.engineering.redhat.com/polarion",
      "POLARION_PAT": "<JWT token -- set via env or set_polarion_token tool>"
    },
    "timeout": 90
  }
}
```

**Key points:**
- `uvx` creates an isolated Python environment with `polarion-mcp` installed
- The wrapper script is passed as the Python entry point
- `POLARION_BASE_URL` points to Red Hat's internal Polarion
- `POLARION_PAT` is the JWT Personal Access Token (can also be set at runtime via `set_polarion_token`)
- Timeout is 90s (higher than other MCPs due to Polarion's slower API)

---

## Tools Reference

### Total: 25 tools (14 base + 11 enhanced)

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

#### Enhanced Read Tools (added by wrapper)

| Tool | Purpose | Parameters | Status |
|------|---------|------------|--------|
| `get_polarion_test_steps` | Fetch test step content (step HTML + expected results) | `project_id`, `work_item_id` | Tested |
| `get_polarion_test_case_summary` | Quick overview: title, setup status, step count, step titles | `project_id`, `work_item_id` | Tested |
| `get_polarion_setup_html` | Get raw Setup section HTML | `project_id`, `work_item_id` | Tested |
| `list_polarion_test_runs` | List/filter test runs by query, status, plan | `project_id`, `query`, `limit`, `page_number` | Tested |
| `get_polarion_test_run_info` | Get test run details + pass/fail/blocked statistics | `project_id`, `test_run_id`, `include_records` | Tested |
| `list_polarion_plans` | List/search test plans | `project_id`, `query`, `status`, `limit`, `page_number` | Tested |

#### Enhanced Write Tools (added by wrapper)

| Tool | Purpose | Parameters | Status |
|------|---------|------------|--------|
| `update_polarion_work_item` | Update any work item field (title, description, status, setup, custom) | `project_id`, `work_item_id`, `title`, `description_html`, `status`, `setup_html`, `custom_fields_json` | Tested |
| `update_polarion_setup` | Push setup section HTML to a test case | `project_id`, `work_item_id`, `setup_html` | Tested |
| `update_polarion_test_steps` | Create or update test steps (PATCH in-place or bulk POST) | `project_id`, `work_item_id`, `steps_json` | Tested |
| `create_polarion_test_run` | Create test run + associate with a plan | `project_id`, `test_run_id`, `title`, `plan_id`, `custom_fields_json` | Tested |
| `upload_polarion_test_results` | Upload test results to a test run | `project_id`, `test_run_id`, `results_json` | Tested |

### Tools with Known Issues

| Tool | Status | Issue |
|------|--------|-------|
| `get_polarion_projects` | 403 Forbidden | User lacks permission to list ALL projects. Use specific `project_id` instead. |
| `get_polarion_work_item_text` | Partial | Returns empty content for some work items. Use `get_polarion_work_item` with `fields="@all"` instead. |
| `get_polarion_document` | Requires setup | Needs `space_id` and `document_name` (not discoverable via API). |
| `get_polarion_work_item_at_revision` | Requires setup | Needs `revision_id` from `get_polarion_work_item_revisions` first. |
| `polarion_github_requirements_coverage` | Requires setup | Needs connected GitHub repo context. |

---

## Write Tool Behavior Details

### `update_polarion_test_steps` - Step Update Logic

The Polarion test steps API has specific constraints:
- **POST** only works when a work item has NO existing steps (initial bulk creation)
- **PATCH** updates individual steps in-place (steps are **1-indexed**, not 0-indexed)
- **DELETE** returns 403 for our PAT (not permitted)

**Behavior:**
1. **No steps exist:** Creates all steps via POST (bulk creation with `keys` + `values`)
2. **Steps already exist, same count:** PATCHes each step in-place
3. **Steps already exist, new > existing:** Updates existing steps, reports extras couldn't be added
4. **Steps already exist, new < existing:** Updates provided steps, extra existing steps remain unchanged

### `create_polarion_test_run` - Plan Association

Plan association uses a two-step process (as documented in the `acm-workflows` repo):
1. **POST** creates the test run
2. **PATCH** sets the `plannedin` attribute to associate with a plan

### `upload_polarion_test_results` - Test Record Format

Test records use a **relationship** to reference the test case (not an attribute):
```json
{
  "data": [{
    "type": "testrecords",
    "attributes": {
      "result": "passed",
      "executed": "2026-02-15T22:39:28.000Z"
    },
    "relationships": {
      "testCase": {
        "data": {
          "type": "workitems",
          "id": "RHACM4K/RHACM4K-61726"
        }
      }
    }
  }]
}
```

Valid `result` values: `"passed"`, `"failed"`, `"blocked"`

---

## Query Syntax

`get_polarion_work_items` uses Lucene query syntax. `list_polarion_test_runs` and `list_polarion_plans` also support Lucene queries.

### Verified Searchable Fields (Work Items)

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

### Test Run Queries

```
status:finished                        # By status
title:ServerFoundation                 # By title keyword
plannedin.KEY:ACM_2_16                # By plan association
```

### Plan Queries

```
ACM_2_16                              # Free-text search (matches name and ID)
id:ACM_2_16                           # Exact ID match
status:open                           # By status
```

### Work Item Query Examples

```lucene
# Find proposed virtualization test cases by author
type:testcase AND author.id:ashafi AND casecomponent:virtualization AND status:proposed

# Find RBAC UI test cases by title pattern
type:testcase AND title:"[FG-RBAC-2.16]"

# Find ACM 2.16 test cases
type:testcase AND product:rhacm2-16
```

---

## Authentication

- **Token Type:** JWT (Personal Access Token)
- **Current Expiration:** Jan 31, 2027
- **Subject:** `ashafi`
- **Storage:** Set at runtime via `set_polarion_token` tool, or via `POLARION_PAT` env var in `mcp.json`

### Token Refresh Procedure

1. Run `check_polarion_status` to verify current token
2. If expired: Generate new PAT from Polarion UI (My Account > Personal Access Tokens)
3. Run `set_polarion_token(token="NEW_TOKEN_HERE")`
4. Verify: `get_polarion_project(project_id="RHACM4K")`

---

## Permission Model

```
ALLOWED (Read + Write on RHACM4K):
  READ:
    - View project details
    - Search work items (test cases, requirements)
    - Read work item content (description, setup, steps)
    - View work item revisions, attachments, linked items
    - List test runs, test plans
    - Get test run info and statistics
  WRITE:
    - Update work item fields (title, description, status, setup, custom fields)
    - Update test step content (PATCH in-place)
    - Create test runs
    - Upload test results to test runs
    - Associate test runs with plans

NOT ALLOWED:
  - List all Polarion projects (403 Forbidden)
  - Delete work items or test runs (403 Forbidden)
  - Delete individual test steps (403 Forbidden)
  - Create test steps on a work item that already has steps (POST blocked)

LIMITATION:
  - Can only access project: RHACM4K
  - Other projects may require separate permissions
```

---

## Limitations and Workarounds

| Limitation | Workaround |
|------------|------------|
| `get_polarion_projects` returns 403 | Always use `project_id="RHACM4K"` directly |
| Single project access (RHACM4K) | Request additional project access if needed |
| Can't DELETE test steps (403) | Use PATCH to update in-place; step count must match |
| Can't DELETE test runs (403) | Mark as `invalid` status via PATCH |
| Can't POST steps when steps exist | PATCH existing steps in-place; POST only works on empty |
| Test records page size max 100 | Tool handles pagination automatically |
| `get_polarion_document` needs space_id | Ask user for space name or use work item search |
| `get_polarion_work_item_text` returns empty | Use `get_polarion_work_item` with `fields="@all"` |
| `work_item_ids` parameter format | Must be comma-separated string, NOT an array |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| 401 Unauthorized | Token expired | Regenerate PAT and call `set_polarion_token` |
| 403 on `get_polarion_projects` | Normal -- user lacks list-all permission | Use specific `project_id` instead |
| 403 on DELETE | DELETE not permitted for this PAT | Use PATCH to update status instead |
| 403 on work item | User lacks project permission | Verify project access |
| 400 on POST teststeps | Work item already has steps | Use PATCH on individual steps instead |
| Empty response | Wrong fields param | Try `fields="@all"` or use different tool |
| SSL certificate error | Wrapper not loaded | Verify wrapper script path in `mcp.json` |
| Timeout | Polarion slow response | Timeout is 90s in config; wrapper sets 30s per request |

---

## Polarion API Endpoints

Used by the wrapper's enhanced tools:

| Endpoint | Tools |
|----------|-------|
| `GET /projects/{pid}/workitems/{wid}` | `get_polarion_work_item`, `get_polarion_setup_html`, `get_polarion_test_case_summary` |
| `PATCH /projects/{pid}/workitems/{wid}` | `update_polarion_work_item`, `update_polarion_setup` |
| `GET /projects/{pid}/workitems/{wid}/teststeps` | `get_polarion_test_steps`, `get_polarion_test_case_summary`, `update_polarion_test_steps` |
| `POST /projects/{pid}/workitems/{wid}/teststeps` | `update_polarion_test_steps` (when empty) |
| `PATCH /projects/{pid}/workitems/{wid}/teststeps/{idx}` | `update_polarion_test_steps` (1-indexed) |
| `GET /projects/{pid}/testruns` | `list_polarion_test_runs` |
| `GET /projects/{pid}/testruns/{rid}` | `get_polarion_test_run_info` |
| `POST /projects/{pid}/testruns` | `create_polarion_test_run` |
| `PATCH /projects/{pid}/testruns/{rid}` | `create_polarion_test_run` (plan association) |
| `GET /projects/{pid}/testruns/{rid}/testrecords` | `get_polarion_test_run_info` |
| `POST /projects/{pid}/testruns/{rid}/testrecords` | `upload_polarion_test_results` |
| `GET /projects/{pid}/plans` | `list_polarion_plans` |

Base URL: `https://polarion.engineering.redhat.com/polarion`

---

## Inspiration

The test run read/write tools were inspired by the [`stolostron/acm-workflows`](https://github.com/stolostron/acm-workflows/tree/main/Claude/plugins/polarion-tools) Claude plugin (maintainer: hchenxa, ACM QE Team), which provides CLI-based test run management. This MCP integrates those capabilities directly into the Cursor MCP protocol alongside work item management.

---

## Related Files

| File | Purpose |
|------|---------|
| `~/.cursor/mcp.json` | MCP server configuration (path to wrapper) |
| `/Users/ashafi/Documents/work/automation/.cursorrules` | AI rules referencing Polarion MCP (query syntax, defaults, behaviors) |
| `~/.cursor/skills/write-testcase-console/SKILL.md` | Test case writing skill (uses Polarion MCP) |
| `~/.cursor/skills/active-sprint-tasks/SKILL.md` | Sprint tasks skill (uses Polarion MCP) |
| `/Users/ashafi/Documents/work/automation/tools/polarion/` | Older standalone CLI tool (not this MCP) |
