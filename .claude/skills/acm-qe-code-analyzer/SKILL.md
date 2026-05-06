---
name: acm-qe-code-analyzer
description: Analyze GitHub PR diffs for ACM Console to identify changed components, new UI elements, modified behavior, filtering logic, field orders, and test scenarios. Use when writing test cases that need to understand what code changed in a PR.
compatibility: "Requires gh CLI (gh auth login). Uses acm-source MCP for source verification. Optional: neo4j-rhacm MCP for dependency analysis. Optional: jira MCP for coverage gap analysis."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Code Change Analyzer

Analyzes PR diffs from `stolostron/console` or `kubevirt-ui/kubevirt-plugin` to understand exactly what changed and what needs testing. Uses GitHub CLI for PR data and the acm-source MCP for source code verification.

## Prerequisites

- `gh` CLI authenticated (`gh auth login`)
- acm-source MCP server available for source verification

## Process

### Step 1: Get PR Metadata
```bash
gh pr view <N> --repo <repo> --json title,body,files,additions,deletions,mergedAt,state
```

### Step 2: Get Full PR Diff
```bash
gh pr diff <N> --repo <repo>
```

### Step 3: Set ACM Version
Use the acm-source MCP `set_acm_version` to set the version before any source lookups.

### Step 4: Analyze Each Changed File

For each changed file in the diff, identify:

- **New UI components** -- new pages, modals, wizards, table columns, description list fields
- **Modified UI elements** -- changed labels, new buttons, removed options
- **New routes** -- navigation paths added to `NavigationPath.tsx`
- **New API interactions** -- fetch calls, resource creation, status checks
- **Conditional logic** -- feature flags, RBAC checks, state-dependent rendering
- **Error handling** -- new error messages, validation rules, edge cases
- **Translation strings** -- new i18n keys (what the user sees in the UI)
- **Filtering functions** -- label filters, search filters, data transformations
- **UI interaction model** -- for interactive elements, identify the PatternFly component type (ToolbarFilter, TextInput, Select, Switch) to determine test interaction patterns

### Step 5: Read Full Source of Primary Target File

MANDATORY: Read the complete source code of the primary changed component via acm-source MCP `get_component_source`. Do NOT rely solely on the diff. The full source reveals:
- Array construction patterns (field order in description lists)
- Import chains (what utility functions are used)
- Conditional rendering (what conditions control visibility)
- The component's complete API (props, state, hooks)

### Step 6: Verify Filtering Functions Against Source

If the diff introduces or modifies filtering functions:
1. Read the utility file source via `get_component_source`
2. Extract exact filter conditions (string comparisons, `startsWith`, regex patterns)
3. Do NOT copy filter rules from the PR diff alone -- the merged source is authoritative

### Step 7: Check Component Dependencies

Use the neo4j-rhacm MCP (if available) to understand what depends on changed components and what might be affected.

### Step 8: Verify UI Strings

Use acm-source MCP `search_translations` for any new labels found in the diff. Ensures test cases use exact strings users will see.

### Step 9: Map Changes to Test Scenarios

- New UI element -> test it exists and works
- Modified behavior -> test old behavior is replaced
- New validation -> test valid and invalid inputs
- New RBAC check -> test with different user roles
- New error path -> test the error scenario
- New filter -> test filter behavior with matching and non-matching data

### Step 10: Coverage Gap Analysis

Cross-reference the conditional logic, error handling, and edge cases identified in Steps 4-9 against the JIRA story's Acceptance Criteria. If ACs are provided in the input, use them directly. Otherwise, retrieve them via the jira MCP `get_issue`.

For each code behavior found in the diff, ask:
- Does any AC explicitly describe this behavior? → Covered.
- Does no AC mention it, but it affects what the user sees or can do? → GAP.
- Is this purely internal logic with no user-visible effect? → Skip.

Include a Coverage Gaps section in the output listing each gap with: description, code reference (file:function), and user impact. If all code paths map to ACs, state "No gaps found."

## Critical Rules

- **MANDATORY: Read full source of primary target file** via MCP, not just the diff
- **Distinguish test files from production code.** Files ending in `.test.tsx`/`.test.ts` contain MOCK DATA (jest.mock, fixture objects). Mock data does NOT represent what the UI renders. Label any claim derived from test files as "FROM TEST MOCK DATA -- verify against production code."
- **Multi-story PRs:** If the PR references multiple JIRA stories, identify which files belong to which story. Tag each file with its story. Focus on the target story's files.
- **Cross-reference area knowledge:** If an area knowledge file exists (via acm-knowledge-base skill), verify that analysis of field order, filtering behavior, and component structure is consistent. Flag contradictions.
- **Never trust diff strings alone** for UI labels -- verify via `search_translations`
- **If MCP source differs from PR diff** (function implementation, import path), trust the MCP source -- it reflects actual merged code

## Return Format

The calling skill specifies what output format it needs. This skill provides raw analysis data. A typical analysis includes: changed components list, new UI elements, modified behavior, routes, translations, filtering logic, component dependencies, and derived test scenarios.
