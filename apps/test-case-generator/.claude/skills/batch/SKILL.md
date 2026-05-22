---
description: |
  Generate test cases for multiple JIRA tickets in sequence, running the
  full pipeline for each and producing a summary table of results.
when_to_use: |
  When the user wants to generate test cases for multiple JIRA tickets at
  once, provides a comma-separated list of ticket IDs, or says "batch",
  "generate for all of these", or "run the pipeline for multiple tickets".
argument-hint: "<JIRA_IDS> [--version <VERSION>] [--skip-live]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Bash(python -m src.scripts.gather:*)
  - Bash(python -m src.scripts.report:*)
  - Bash(python:*)
  - Bash(python3:*)
  - Bash(gh:*)
  - Bash(git:*)
  - Bash(ls:*)
  - Bash(cat:*)
  - Bash(mkdir:*)
  - Bash(jq:*)
  - Bash(head:*)
  - Bash(tail:*)
  - Bash(grep:*)
  - Bash(find:*)
  - Bash(wc:*)
  - Bash(echo:*)
  - Bash(date:*)
  - Bash(basename:*)
  - Bash(dirname:*)
  - Bash(realpath:*)
  - mcp__acm-source__set_acm_version
  - mcp__acm-source__set_cnv_version
  - mcp__acm-source__get_routes
  - mcp__acm-source__search_translations
  - mcp__jira__get_issue
  - mcp__jira__search_issues
  - mcp__polarion__get_polarion_work_items
  - mcp__polarion__get_polarion_test_case_summary
  - mcp__polarion__check_polarion_status
---

# Generate test cases for multiple JIRA tickets

Usage: `/batch <JIRA_IDS> [--version <VERSION>] [--skip-live]`

## Arguments

- `JIRA_IDS` (required): Comma-separated JIRA ticket IDs (e.g., ACM-30459,ACM-30460,ACM-30461)
- `--version`: ACM version override (applied to all tickets)
- `--skip-live`: Skip live cluster validation for all tickets

## Process

For each JIRA ID in the comma-separated list:

1. Run `/generate <JIRA_ID> [options]`
2. Show the result (PASS/FAIL)
3. Continue to the next ticket regardless of result

After all tickets are processed, show a summary table:

```
Batch Results
=============
| JIRA ID    | Status  | Steps | Complexity | Output |
|------------|---------|-------|------------|--------|
| ACM-30459  | PASS    | 8     | medium     | runs/test-case-generator/ACM-30459/... |
| ACM-30460  | PARTIAL | 5     | simple     | runs/test-case-generator/ACM-30460/... (1 step needs manual verification) |
| ACM-30461  | FAIL    | -     | -          | Stage 1 failed: no JIRA ticket found |
```
