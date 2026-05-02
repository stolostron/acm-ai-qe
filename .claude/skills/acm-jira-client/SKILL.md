---
name: acm-jira-client
description: Interface to Red Hat JIRA for reading tickets, searching with JQL, and extracting structured data from ACM project issues. Use when you need to read JIRA stories, bugs, epics, comments, acceptance criteria, fix versions, or search for related tickets.
compatibility: "Requires MCP server: jira (jira-mcp-server). Needs JIRA_SERVER_URL, JIRA_ACCESS_TOKEN, JIRA_EMAIL. Run /onboard to configure."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM JIRA Client

Provides access to Red Hat JIRA via the `jira` MCP server. This skill exposes raw JIRA capabilities -- reading tickets, searching with JQL, and listing project components. It contains no app-specific workflow logic. The calling skill provides all instructions for what to extract and how to analyze results.

## MCP Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `get_issue(issue_key)` | Full ticket details: summary, description, comments, fix_versions, components, labels, status, priority, assignee | `get_issue(issue_key="ACM-30459")` |
| `search_issues(jql)` | Search tickets using JQL query syntax | `search_issues(jql='project = ACM AND type = Bug AND status != Closed')` |
| `get_project_components(project_key)` | List all components in a project | `get_project_components(project_key="ACM")` |

## Gotchas

These are critical behavioral notes about the MCP tools:

1. **`get_issue` does NOT return issue links.** To find linked tickets, use `search_issues` with JQL patterns (see below).
2. **Comment parameter is `comment`, NOT `body`.** When creating comments (if the MCP supports it), use the correct field name.
3. **`get_issue` returns comments inline** in the response. Read ALL comments -- they contain implementation decisions, edge cases, design trade-offs, and QE feedback.
4. **JQL is case-sensitive for field names.** Use `fixVersion` not `fix_version`, `summary` not `title`.
5. **String values in JQL must be quoted.** Use `fixVersion = "ACM 2.17.0"` not `fixVersion = ACM 2.17.0`.

## JQL Reference

Read `references/jql-patterns.md` for the full pattern library. Key patterns:

### Find tickets by relationship
```
search_issues(jql='summary ~ "[QE] --- ACM-XXXXX"')           -- QE tracking ticket
search_issues(jql='parent = ACM-XXXXX')                        -- Sub-tasks
search_issues(jql='project = ACM AND summary ~ "keyword" AND type = Bug AND status != Closed')  -- Related bugs
```

### Find tickets by version and component
```
search_issues(jql='project = ACM AND fixVersion = "ACM 2.17.0" AND component = "Governance"')
search_issues(jql='project = ACM AND labels = "QE" AND fixVersion = "ACM 2.17.0"')
```

### Find tickets by text
```
search_issues(jql='project = ACM AND text ~ "label filtering"')
```

## ACM Project Component Mapping

Read `references/component-mapping.md` for the full mapping. Key components:

| Area | JIRA Component Value |
|------|---------------------|
| Governance | `Governance` |
| RBAC, Fleet Virt, CCLM, MTV | `Virtualization` |
| Clusters, Credentials | `Cluster Lifecycle` |
| Search | `Search` |
| Applications | `Application Lifecycle` |

If the area is not in this table, read the component from the source ticket's `components` field (returned by `get_issue`).

## JIRA Ticket Structure

A typical `get_issue` response contains:
- `summary` -- ticket title
- `description` -- detailed description, often with acceptance criteria
- `status` -- current state (Open, In Progress, Done, Closed)
- `fix_versions` -- which ACM release this targets
- `components` -- which ACM area (Governance, Virtualization, etc.)
- `labels` -- tags (QE, dev-complete, etc.)
- `comments` -- array of comments with author and body
- `priority` -- Critical, Major, Minor, etc.
- `assignee` -- who is working on it
- `issue_type` -- Story, Bug, Epic, Task, Sub-task

## Rules

- NEVER modify JIRA tickets -- this skill is read-only
- If the MCP is unavailable, note it and proceed with available data
- Always read ALL comments on a ticket -- they are the richest source of context
