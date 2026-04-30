---
name: acm-data-enricher
description: Enrich test failure data with AI-analyzed context -- resolve page objects, verify selector existence in product source, analyze selector change history, and fill feature knowledge gaps. Use when test failure data needs enrichment before classification analysis.
compatibility: "Uses acm-ui-source skill (requires acm-ui MCP) for selector verification. Optional: acm-jira-client (for commit intent disambiguation). Needs gh CLI for git history analysis."
---

# ACM Data Enricher

Enriches test failure data (`core-data.json`) with information that requires intelligent code analysis. Runs after data gathering and before AI classification analysis.

**Standalone operation:** Works independently when given a run directory path containing `core-data.json` and cloned repos (`repos/automation/`, `repos/console/`). Can also be used to re-enrich an existing dataset.

## Input

A run directory path containing:
- `core-data.json` -- primary data file with failed tests and metadata
- `repos/automation/` -- cloned test automation repo (Cypress, Playwright)
- `repos/console/` -- cloned product source repo (stolostron/console)
- `repos/kubevirt-plugin/` -- cloned kubevirt UI repo (if VM tests detected)

From `core-data.json`, read:
- `cluster_landscape.mch_version` -- ACM version for MCP queries
- `test_report.failed_tests` -- array of failed tests with stack traces
- `feature_grounding` -- which feature areas are affected
- `feature_knowledge.gap_detection` -- triggers for Task 4

## Tasks (execute in order)

Read `references/enrichment-tasks.md` for full task details. Summary:

### Task 1: Resolve Page Objects

For each failed test with a `failing_selector`, trace imports from the test file to find where the selector is defined in the automation repo. Follow import chains through `views/`, `selectors/`, `page/`, `helpers/`, `support/`, `constants/` paths.

Output: `extracted_context.page_objects` per test.

### Task 2: Verify Selector Existence in Product Source

For each unique `failing_selector`, use the acm-ui-source skill to verify whether it exists in the official product source code. This replaces simple grep -- it handles PatternFly class derivation (e.g., `pf-v6-c-tree-view` -> component `TreeView`), route-aware verification, and false positive detection.

**Critical:** Set ACM version via acm-ui-source before any search. For VM selectors, also set CNV version.

Output: `extracted_context.console_search` per test with `found`, `verification.method`, `verification.detail`.

### Task 3: Selector Timeline Analysis

For each unique `failing_selector`, analyze git history to determine if the selector was recently changed and whether the change was intentional or accidental. Uses `git log -S` on both product and automation repos, assesses commit intent, looks for replacement selectors, and optionally checks JIRA for ambiguous cases.

Output: `extracted_context.recent_selector_changes` and `extracted_context.temporal_summary` per test.

### Task 4: Feature Knowledge Gap Filling (conditional)

Run ONLY if gap detection thresholds are met:
- `overall_match_rate < 0.3` (less than 30% of errors matched)
- `gap_areas` has 3+ entries
- `stale_components` has 5+ entries

When triggered: read per-area `failure-signatures.md`, match unmatched errors, construct and validate failure path entries, resolve prerequisites from `cluster-diagnosis.json`.

Output: `feature_knowledge.ai_enrichment` in core-data.json, plus `knowledge/learned/feature-gaps.yaml`.

## Constraints

- **Read-only on repos/** -- never modify cloned repository files
- **Never write to base.yaml** -- discoveries go to `knowledge/learned/` only
- **Time-efficient** -- deduplicate by file/selector, don't re-verify duplicates
- **MCP version setup** -- ALWAYS call `set_acm_version` before any `search_code` call
- **Single write** -- read core-data.json once, update in memory, write once at end
- **JIRA is optional** -- only query JIRA if commit intent is ambiguous
- **Validate before writing** -- every AI-generated failure path must pass schema validation
- **Graceful degradation** -- if Task 4 fails, set `ai_enrichment: {"error": "...", "fallback": "base_playbook_only"}`
