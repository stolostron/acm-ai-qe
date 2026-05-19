---
name: acm-qe-code-analyzer
description: >-
  Use when the user wants GitHub PR diff analysis for any ACM-related repo
  to understand what changed (components, UI, filters, field order, controllers,
  CRDs, webhooks) and what to test -- WITHOUT running the full JIRA-to-Polarion
  test case generator pipeline. Defaults to stolostron/console and kubevirt-plugin
  when no repo is specified (backward compatible with acm-test-case-generator).
  TRIGGER: analyze PR #N, what changed in this merge, test impact of this diff.
  DO NOT TRIGGER: user wants Polarion test case from ACM-#### end-to-end
  (use acm-test-case-generator); user wants only domain facts (use acm-knowledge-base).
compatibility: "Requires gh CLI (gh auth login). Uses acm-source MCP for source verification (console repos). Optional: neo4j-rhacm MCP for dependency analysis. Optional: jira MCP for coverage gap analysis."
metadata:
  author: acm-qe
  version: "1.1.0"
---

# ACM Code Change Analyzer

Analyzes PR diffs to understand exactly what changed and what needs testing. Works with any stolostron or ACM-related repo. Defaults to `stolostron/console` and `kubevirt-ui/kubevirt-plugin` when no repo is specified (backward compatible).

## Repo Parameter

This skill accepts a **repo** parameter. If not provided, defaults to `stolostron/console`.

Supported repo categories:
- **Console repos** (default): `stolostron/console`, `kubevirt-ui/kubevirt-plugin` -- full UI analysis (components, routes, translations, PatternFly)
- **Backend/operator repos**: Any stolostron repo (e.g., `stolostron/multicluster-controlplane`, `stolostron/governance-policy-propagator`, `stolostron/registration-operator`, `stolostron/cluster-curator-controller`) -- focus on controller logic, CRD changes, webhook changes, API changes
- **Addon repos**: `stolostron/klusterlet-addon-controller`, `stolostron/addon-framework` -- focus on ManifestWork templates, addon lifecycle
- **Other**: Any GitHub repo with ACM-related code -- generic code analysis

When the repo is NOT a console repo, skip console-specific steps (translations, PatternFly analysis, route discovery) and focus on: controller reconciliation logic, CRD schema changes, webhook validation changes, API endpoint changes, RBAC/ClusterRole definitions, and ManifestWork templates.

## Prerequisites

- `gh` CLI authenticated (`gh auth login`)
- acm-source MCP server available for source verification (console repos)

## Process

### Step 1: Get PR Metadata
```bash
gh pr view <N> --repo <REPO> --json title,body,files,additions,deletions,mergedAt,state
```
Default `<REPO>` is `stolostron/console` if not specified.

### Step 2: Get Full PR Diff
```bash
gh pr diff <N> --repo <REPO>
```

### Step 3: Set ACM Version (console repos)
Use the acm-source MCP `set_acm_version` to set the version before any source lookups.
For non-console repos, skip this step unless the repo is indexed by acm-source MCP.

### Step 4: Analyze Each Changed File

For each changed file in the diff, identify:

**All repos:**
- **New API interactions** -- fetch calls, resource creation, status checks
- **Conditional logic** -- feature flags, RBAC checks, state-dependent rendering
- **Error handling** -- new error messages, validation rules, edge cases
- **CRD schema changes** -- new fields, removed fields, validation rules
- **Webhook changes** -- new validating/mutating webhooks, changed validation logic
- **Controller logic** -- reconciliation changes, new watchers, status updates

**Console repos only:**
- **New UI components** -- new pages, modals, wizards, table columns, description list fields
- **Modified UI elements** -- changed labels, new buttons, removed options
- **New routes** -- navigation paths added to `NavigationPath.tsx`
- **Translation strings** -- new i18n keys (what the user sees in the UI)
- **Filtering functions** -- label filters, search filters, data transformations
- **UI interaction model** -- PatternFly component type (ToolbarFilter, TextInput, Select, Switch) to determine test interaction patterns

**Backend/operator repos only:**
- **Controller reconciliation logic** -- new watchers, changed predicates, status updates
- **RBAC changes** -- ClusterRole definitions, aggregation labels, permissions
- **ManifestWork template changes** -- what gets deployed to spokes
- **Status condition changes** -- new conditions, changed meanings
- **Leader election or HA behavior** -- changes to replica counts, lease configuration

### Step 5: Read Full Source of Key Changed Files

**Console repos (MANDATORY):** Read the complete source code of the primary changed component via acm-source MCP `get_component_source`. Do NOT rely solely on the diff. The full source reveals:
- Array construction patterns (field order in description lists)
- Import chains (what utility functions are used)
- Conditional rendering (what conditions control visibility)
- The component's complete API (props, state, hooks)

**Non-console repos:** Read full source via `gh` CLI:
```bash
gh api repos/<REPO>/contents/<filepath>?ref=<branch> --jq '.content' | base64 -d
```

### Step 6: Verify Filtering Functions Against Source (console repos only)

If the diff introduces or modifies filtering functions:
1. Read the utility file source via `get_component_source`
2. Extract exact filter conditions (string comparisons, `startsWith`, regex patterns)
3. Do NOT copy filter rules from the PR diff alone -- the merged source is authoritative

### Step 7: Check Component Dependencies

Use the neo4j-rhacm MCP (if available) to understand what depends on changed components and what might be affected:
```
read_neo4j_cypher("MATCH (dep)-[:DEPENDS_ON]->(t) WHERE t.label CONTAINS 'ComponentName' RETURN dep.label, dep.subsystem")
```

### Step 8: Verify UI Strings (console repos only)

Use acm-source MCP `search_translations` for any new labels found in the diff. Ensures test cases use exact strings users will see.

### Step 9: Map Changes to Test Scenarios

**All repos:**
- New validation -> test valid and invalid inputs
- New RBAC check -> test with different user roles
- New error path -> test the error scenario
- New conditional logic -> test each branch

**Console repos:**
- New UI element -> test it exists and works
- Modified behavior -> test old behavior is replaced
- New filter -> test filter behavior with matching and non-matching data

**Backend/operator repos:**
- Controller logic change -> test reconciliation behavior
- CRD schema change -> test new fields, validation, upgrade path
- Webhook change -> test admission validation accepts/rejects correctly
- ManifestWork change -> test spoke-side deployment
- RBAC change -> test permissions grant/deny

### Step 10: Coverage Gap Analysis

Cross-reference the conditional logic, error handling, and edge cases identified in Steps 4-9 against the JIRA story's Acceptance Criteria. If ACs are provided in the input, use them directly. Otherwise, retrieve them via the jira MCP `get_issue`.

For each code behavior found in the diff, ask:
- Does any AC explicitly describe this behavior? -> Covered.
- Does no AC mention it, but it affects what the user sees or can do? -> GAP.
- Is this purely internal logic with no user-visible effect? -> Skip.

Include a Coverage Gaps section in the output listing each gap with: description, code reference (file:function), and user impact. If all code paths map to ACs, state "No gaps found."

### Step 11: Follow-Up PR Detection

For each primary changed file, check for subsequent merged PRs that modify the same files:
```bash
gh pr list --search "path:<filepath>" --state merged --limit 5 --repo <REPO> --json number,title,mergedAt
```

Filter to PRs merged AFTER the target PR. Flag:
- Post-merge renames of components or functions
- Bug fixes that changed the behavior introduced by the target PR
- Refactors that moved or restructured the code

Include findings in the `follow_up_prs` section of the output. If no follow-up PRs exist, set to empty array.

## Analysis Heuristics

Read `${CLAUDE_SKILL_DIR}/references/analysis-rules.md` for mandatory analysis rules: full source reading, test file vs production code distinction, multi-story PR handling, area knowledge cross-referencing, MCP authority, and filter function extraction.

## Critical Rules

- **MANDATORY: Read full source of primary target file** via MCP (console repos) or gh CLI (other repos), not just the diff
- **Distinguish test files from production code.** Files ending in `.test.tsx`/`.test.ts` contain MOCK DATA (jest.mock, fixture objects). Mock data does NOT represent what the UI renders. Label any claim derived from test files as "FROM TEST MOCK DATA -- verify against production code."
- **Multi-story PRs:** If the PR references multiple JIRA stories, identify which files belong to which story. Tag each file with its story. Focus on the target story's files.
- **Cross-reference area knowledge:** If an area knowledge file exists (via acm-knowledge-base skill), verify that analysis of field order, filtering behavior, and component structure is consistent. Flag contradictions.
- **Never trust diff strings alone** for UI labels -- verify via `search_translations` (console repos)
- **If MCP source differs from PR diff** (function implementation, import path), trust the MCP source -- it reflects actual merged code

## Return Format

```
CODE CHANGE ANALYSIS
====================
PR: #NNNN - [title]
Repo: <REPO>
Repo Type: console | backend | addon | other
Files Changed: N (+ additions, - deletions)

Changed Components:
- [file path]: [what changed and why]

--- Console repos only ---
New UI Elements:
- [element]: [description] (in [component])

Modified UI Behavior:
- [before] -> [after] (in [component])

New Routes/Pages:
- [path]: [description]

Translation Strings:
- "[UI text]": [context]

Filtering Logic:
- [filter name]: [exact conditions from source]

--- Backend/operator repos only ---
CRD Schema Changes:
- [CRD name]: [field added/removed/modified] (impact: [what breaks])

Controller Logic Changes:
- [controller]: [what reconciliation behavior changed]

Webhook Changes:
- [webhook name]: [what validation changed]

RBAC Changes:
- [ClusterRole]: [permissions added/removed]

ManifestWork Changes:
- [template]: [what gets deployed differently to spokes]

--- All repos ---
New API Interactions:
- [resource type]: [operation] (in [component])

Conditional Logic Added:
- [condition]: [what it controls]

New Error Messages:
- "[message text]": [when it appears]

Component Dependencies:
- [component] is used by: [list of dependent components]

Test Scenarios from Code Changes:
1. [scenario derived from specific code change]

Backend Impact:
- [what K8s resources are created/modified]
- [what API calls are made]

Coverage Gaps:
- [gap description]: [code reference] -- [user impact]

Follow-Up PRs:
- PR #NNNN: [title] (merged [date]) -- [relevance: rename/fix/refactor]
```
