---
description: |
  Review an existing test case for quality, convention compliance, and
  correctness using the quality-reviewer agent.
when_to_use: |
  When the user wants to review, check, validate, or audit an existing test
  case file, or says "review this test case", "check quality", or provides
  a test case path asking for feedback.
argument-hint: "<PATH_TO_TEST_CASE> [--version <VERSION>] [--area <AREA>]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Agent
  - Bash(ls:*)
  - Bash(cat:*)
  - Bash(head:*)
  - Bash(find:*)
  - Bash(grep:*)
  - mcp__acm-source__set_acm_version
  - mcp__acm-source__search_translations
  - mcp__acm-source__get_routes
  - mcp__acm-source__get_wizard_steps
---

# Review an existing test case

Usage: `/review <PATH_TO_TEST_CASE> [--version <VERSION>] [--area <AREA>]`

## Arguments

- `PATH_TO_TEST_CASE` (required): Path to the test case markdown file
- `--version`: ACM version (default: extracted from test case Release field)
- `--area`: Console area (default: extracted from test case title tag)

## Process

1. Read the test case file
2. Launch the quality-reviewer agent with the file path, version, and area
3. Display the review results (blocking issues, warnings, suggestions, verdict)
4. If NEEDS_FIXES: offer to fix the identified issues
