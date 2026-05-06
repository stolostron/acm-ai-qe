---
name: acm-data-enricher
description: Enrich test failure data with AI-analyzed context -- resolve page objects, verify selector existence in product source, analyze selector change history, and fill feature knowledge gaps. Use when test failure data needs enrichment before classification analysis.
compatibility: "Requires acm-source MCP for selector verification. Optional: jira MCP (for commit intent disambiguation). Needs gh CLI for git history analysis."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Data Enricher

Enriches test failure data (`core-data.json`) with information that requires intelligent code analysis. Runs after data gathering and before AI classification analysis.

**Standalone operation:** Works independently when given a run directory path containing `core-data.json` and cloned repos (`repos/automation/`, `repos/console/`). Can also be used to re-enrich an existing dataset.

## Knowledge Directory

KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/z-stream-analysis/

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

For each unique `failing_selector`, use the acm-source MCP tools directly to verify whether it exists in the official product source code. This replaces simple grep -- it handles PatternFly class derivation (e.g., `pf-v6-c-tree-view` -> component `TreeView`), route-aware verification, and false positive detection.

**Critical:** Set ACM version via `set_acm_version` before any search. For VM selectors, also set CNV version via `set_cnv_version`.

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

Output: `feature_knowledge.ai_enrichment` in core-data.json, plus `${KNOWLEDGE_DIR}/learned/feature-gaps.yaml`.

## Constraints

- **Read-only on repos/** -- never modify cloned repository files
- **Never write to base.yaml** -- discoveries go to `${KNOWLEDGE_DIR}/learned/` only
- **Time-efficient** -- deduplicate by file/selector, don't re-verify duplicates
- **MCP version setup** -- ALWAYS call `set_acm_version` before any `search_code` call
- **Single write** -- read core-data.json once, update in memory, write once at end
- **JIRA is optional** -- only query JIRA if commit intent is ambiguous
- **Validate before writing** -- every AI-generated failure path must pass schema validation
- **Graceful degradation** -- if Task 4 fails, set `ai_enrichment: {"error": "...", "fallback": "base_playbook_only"}`

## Gotchas

1. **PatternFly class names are not data-test selectors** -- A selector like `pf-v6-c-tree-view` is a CSS class from PatternFly, not a `data-test` attribute. Derive the component name (`TreeView`) and search for it via `search_code(query, repo, scope="components")`, not `search_code` with the raw class string.
2. **Hex color values trigger false positive selector matches** -- Strings like `#c0c0c0` or `#ffffff` in test errors are color values, not selectors. Skip selector verification for any string that matches a hex color pattern.
3. **`git log -S` is case-sensitive** -- Searching for `data-test="SearchBar"` will NOT find commits that changed `data-test="searchbar"`. When selector case is uncertain, run two searches or use `git log -S --regexp-ignore-case`.
4. **The `direction` field in selector timeline must be computed** -- `recent_selector_changes.direction` must be one of `added`, `removed`, `renamed`, `modified`. Never leave it empty or set it to the raw commit message. Compute it from the diff hunks.
5. **Schema validation catches silent corruption** -- AI-generated failure paths can have valid-looking YAML but invalid field values (wrong types, missing required keys). Always validate against the schema before writing to `${KNOWLEDGE_DIR}/learned/`.
