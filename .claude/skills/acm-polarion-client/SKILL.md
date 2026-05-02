---
name: acm-polarion-client
description: Interface to Polarion for querying test cases, reading work item details, test steps, and setup sections in the RHACM4K project. Use when you need to check existing test coverage, read Polarion test case content, or verify Polarion metadata.
compatibility: "Requires MCP server: polarion (polarion-mcp + wrapper). Needs POLARION_BASE_URL, POLARION_PAT. VPN required. Run /onboard to configure."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Polarion Client

Provides access to Red Hat Polarion via the `polarion` MCP server. This skill exposes raw Polarion query capabilities for the RHACM4K project. It contains no app-specific workflow logic. The calling skill provides all instructions for what to query and how to use the results.

## Prerequisites

- VPN connection to Red Hat network (Polarion is internal)
- `polarion` MCP server configured with valid PAT token

## MCP Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `get_polarion_work_items(project_id, query)` | Search work items using Lucene query | `get_polarion_work_items(project_id="RHACM4K", query='type:testcase AND title:"labels"')` |
| `get_polarion_work_item(project_id, work_item_id, fields)` | Get full details of a specific work item | `get_polarion_work_item(project_id="RHACM4K", work_item_id="RHACM4K-63381", fields="@all")` |
| `get_polarion_test_case_summary(project_id, work_item_id)` | Quick summary: title, setup status, step count, step titles | `get_polarion_test_case_summary(project_id="RHACM4K", work_item_id="RHACM4K-63381")` |
| `get_polarion_test_steps(project_id, work_item_id)` | Get test step content (step text + expected results HTML) | `get_polarion_test_steps(project_id="RHACM4K", work_item_id="RHACM4K-63381")` |
| `get_polarion_setup_html(project_id, work_item_id)` | Get the Setup section HTML content | `get_polarion_setup_html(project_id="RHACM4K", work_item_id="RHACM4K-63381")` |
| `get_polarion_work_item_text(project_id, work_item_id)` | Get the description/text content | Sometimes returns empty -- use `fields="@all"` instead |
| `check_polarion_status()` | Verify Polarion connectivity | `check_polarion_status()` |

## Gotchas

1. **Project ID is ALWAYS `RHACM4K`** -- never use a different project ID for ACM test cases.
2. **Query syntax is Lucene, NOT JQL.** Polarion uses Apache Lucene query syntax. Example: `type:testcase AND title:"feature name"`, not `type = testcase AND title ~ "feature name"`.
3. **`work_item_ids` for batch operations use comma-separated STRING**, not an array.
4. **`get_polarion_work_item_text` sometimes returns empty** -- use `get_polarion_work_item(fields="@all")` as fallback to get the full description.
5. **`fields="@basic"` for quick checks, `fields="@all"` for full details** including relationships, approvals, and custom fields.

## Lucene Query Syntax

### Search by type and title
```
type:testcase AND title:"governance labels"
```

### Search by component
```
type:testcase AND casecomponent:"console"
```

### Search by status
```
type:testcase AND status:"proposed"
```

### Search by custom field
```
type:testcase AND caseautomation:"notautomated"
```

### Combine conditions
```
type:testcase AND title:"RBAC" AND status:"proposed" AND caseautomation:"notautomated"
```

## Work Item Fields

Key fields returned by `get_polarion_work_item(fields="@all")`:
- `id` -- Work item ID (e.g., "RHACM4K-63381")
- `type` -- "testcase", "requirement", etc.
- `title` -- Title string
- `description` -- HTML content
- `status` -- "draft", "proposed", "approved", etc.
- `setup` -- HTML content of the Setup section
- `casecomponent` -- Component field
- `caseimportance` -- "critical", "high", "medium", "low"
- `caselevel` -- "system", "integration", "component"
- `caseautomation` -- "automated", "notautomated", "manualonly"
- `testtype` -- "functional", "nonfunctional", etc.
- `approvals` -- List of approver IDs and their status

## Rules

- NEVER modify Polarion work items -- this skill is read-only
- Always use `project_id="RHACM4K"` for ACM test cases
- If the MCP is unavailable (VPN disconnected), note it and proceed without Polarion data
