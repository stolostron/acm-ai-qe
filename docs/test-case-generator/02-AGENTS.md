# Agent Definitions

Seven specialized subagents, each with a dedicated role in the pipeline. Agent definitions are in `references/agents/`. Each subagent runs in an isolated context, receives file paths as input, uses designated MCP tools, writes structured output to disk, and terminates.

## Agent Summary

| Agent | File | Phase | Tools | Input | Output |
|-------|------|-------|-------|-------|--------|
| JIRA Investigator | `jira-investigator.md` | 2 | jira, polarion, neo4j-rhacm, bash | JIRA ID | `phase2-jira.json` |
| Code Analyzer | `code-analyzer.md` | 3 | acm-ui, neo4j-rhacm, bash | PR number, repo, version | `phase3-code.json` |
| UI Discoverer | `ui-discoverer.md` | 4 | acm-ui, neo4j-rhacm, bash | Version, area, feature name | `phase4-ui.json` |
| Synthesizer | `synthesizer.md` | 5 | — | Phase 2-4 outputs | `synthesized-context.md` |
| Live Validator | `live-validator.md` | 6 | playwright, acm-search, acm-kubectl, bash | Console URL, feature path | `phase6-live-validation.md` |
| Test Case Writer | `test-case-writer.md` | 7 | acm-ui | Run dir, synthesized context | `test-case.md`, `analysis-results.json` |
| Quality Reviewer | `quality-reviewer.md` | 8 | acm-ui, polarion | test-case.md path, version, area | PASS or NEEDS_FIXES (`phase8-review.md`) |

---

## JIRA Investigator

**Phase:** 2
**File:** `references/agents/jira-investigator.md`
**Tools:** jira, polarion, neo4j-rhacm, bash

### Purpose

Deep JIRA investigation: reads the story, comments, linked tickets, and acceptance criteria. Searches Polarion for existing test coverage. Identifies test scenarios from the acceptance criteria.

### MCP Tool Usage

| Tool | MCP Server | Purpose |
|------|-----------|---------|
| `get_issue` | jira | Fetch full ticket details (summary, description, ACs, fix_versions, status) |
| `search_issues` | jira | Find linked tickets via JQL (parent epics, sibling stories, QE tracking) |
| `get_project_components` | jira | List JIRA project components for the area |
| `get_polarion_work_items` | polarion | Search for existing test cases matching the feature |
| `get_polarion_test_case_summary` | polarion | Quick summary of existing coverage |
| `read_neo4j_cypher` | neo4j-rhacm | Component architecture context |
| `gh pr view` | bash | PR metadata and description |

### Output Structure

Structured JSON written to `phase2-jira.json`:

```json
{
  "story_summary": "[JIRA ID] - [summary]",
  "fix_version": "[version]",
  "status": "[status]",
  "acceptance_criteria": ["AC bullet 1", "AC bullet 2"],
  "linked_tickets": [{"key": "[ticket]", "relationship": "[type]"}],
  "comments_summary": ["design decisions", "testing notes"],
  "existing_polarion_coverage": ["existing test cases or empty"],
  "test_scenarios": ["scenario from ACs"],
  "anomalies": []
}
```

---

## Code Analyzer

**Phase:** 3
**File:** `references/agents/code-analyzer.md`
**Tools:** acm-ui, neo4j-rhacm, bash

### Purpose

Reads the full PR diff to understand what changed and what needs testing. Identifies new UI elements, modified behavior, affected routes, and the interaction model for new interactive elements.

### Process

1. Fetch PR metadata via `gh pr view`
2. Read the full PR diff from `pr-diff.txt`
3. Set ACM version in acm-ui MCP
4. For each changed file, identify: new UI components, modified elements, new routes, API interactions, conditional logic, error handling, translation strings, UI interaction model
5. **MANDATORY: Read full source of PRIMARY target file** via `get_component_source` (not just the diff)
6. For multi-story PRs: tag each file with its story, focus output on target story
7. Distinguish test files (`.test.tsx`) from production code — mark test-derived claims as "FROM TEST MOCK DATA"
8. Cross-reference findings with `knowledge/architecture/<area>.md` — flag contradictions
9. Check component dependencies via Neo4j
10. Verify UI strings via `search_translations`
11. Map changes to test scenarios

### UI Interaction Model Identification

For new interactive elements (filters, inputs, toggles), the analyzer identifies the PatternFly component type:

| Component | Interaction | Test Step Pattern |
|-----------|------------|-------------------|
| `ToolbarFilter` with dropdown | Click filter, select from dropdown | "Select the Label filter and choose a value" |
| `TextInput` | Type text, press Enter | "Type a search term and press Enter" |
| `Select` (single) | Click dropdown, select one | "Select an option from the dropdown" |
| `Select` (multi) | Click dropdown, check multiple | "Select multiple values" |
| `Switch` | Click toggle | "Toggle the switch" |

### Output Structure

Structured JSON written to `phase3-code.json`:

```json
{
  "pr_number": 5790,
  "pr_title": "[title]",
  "files_changed": 12,
  "changed_components": [{"file": "[path]", "changes": "[what changed]"}],
  "new_ui_elements": [{"element": "[name]", "description": "[what it does]"}],
  "ui_interaction_models": [{"element": "[name]", "component_type": "[PatternFly type]", "interaction": "[pattern]"}],
  "translation_strings": [{"text": "[UI text]", "context": "[where used]"}],
  "test_scenarios": ["scenario from code changes"],
  "anomalies": []
}
```

---

## UI Discoverer

**Phase:** 4
**File:** `references/agents/ui-discoverer.md`
**Tools:** acm-ui, neo4j-rhacm, bash

### Purpose

Discovers UI selectors, translations, routes, wizard steps, and test IDs from the ACM Console source code via the acm-ui MCP server.

### MCP Tool Usage

| Tool | Purpose |
|------|---------|
| `set_acm_version` | Set target ACM version (MUST call first) |
| `set_cnv_version` | Set CNV version (Fleet Virt only) |
| `search_code` | Find components by name |
| `get_component_source` | Read full component source |
| `search_translations` | Find UI label strings |
| `get_routes` | Get navigation paths for area |
| `get_wizard_steps` | Analyze wizard structure |
| `get_acm_selectors` | Get ACM-specific selectors |
| `get_fleet_virt_selectors` | Get Fleet Virt selectors |
| `find_test_ids` | Find data-test attributes |
| `get_patternfly_selectors` | Get PatternFly component selectors |

### Output Structure

Structured JSON written to `phase4-ui.json`:

```json
{
  "acm_version": "[version]",
  "translations": [{"key": "[key]", "value": "[UI string]"}],
  "routes": [{"name": "[route name]", "path": "[path pattern]"}],
  "selectors": [{"component": "[name]", "selector": "[CSS selector]"}],
  "test_ids": ["[test ID and location]"],
  "component_structure": ["[how components fit together]"],
  "anomalies": []
}
```

---

## Synthesizer

**Phase:** 5
**File:** `references/agents/synthesizer.md`
**Tools:** — (no MCP tools; reads files from disk only)

### Purpose

Merges all three investigation outputs (Phases 2-4) into a unified context document. Applies scope gating, conflict resolution, coverage gap triage, and test design optimization. Produces the primary input for Phase 7 (test case writing).

### Process

1. Read `phase2-jira.json`, `phase3-code.json`, `phase4-ui.json` from the run directory
2. Read the synthesis template from `references/synthesis-template.md`
3. Concatenate investigation findings
4. Scope gate: filter to target JIRA story's ACs only
5. AC vs implementation cross-reference
6. Conflict resolution (ui-discoverer > jira-investigator > code-analyzer per domain)
7. Coverage gap triage (ADD/NOTE/SKIP)
8. Test design optimization (5 passes)
9. Write test plan with step estimates
10. Self-verification against synthesis template

### Output

Markdown written to `synthesized-context.md` containing all investigation data, discrepancies, and the test plan.

### Handling Incomplete Upstream Data

If `VALIDATION_WARNINGS_PATH` is present in input, one or more upstream phases produced incomplete artifacts after exhausting 3 retry attempts. The synthesizer proceeds with available data: missing fields are marked as `[DATA GAP: <field> unavailable from <phase>]`, empty `acceptance_criteria` triggers derivation from code analysis and UI discovery, and missing `entry_point` or `routes` are inferred from code analysis file paths (marked `[INFERRED -- not MCP-verified]`).

### Retry Handling

If the orchestrator's schema validator finds errors in the synthesizer's output, it re-spawns the agent with a `<retry>` block containing the specific validation errors. The synthesizer re-reads upstream artifacts and re-synthesizes the missing or malformed sections, preserving valid sections from the previous attempt.

---

## Live Validator

**Phase:** 6 (conditional)
**File:** `references/agents/live-validator.md`
**Tools:** playwright, acm-search, acm-kubectl, bash

### Purpose

Verifies feature behavior on a real ACM cluster using browser automation, oc CLI, and fleet-wide resource queries. This is the only agent that interacts with a live environment.

### Safety Rules

- **Read-only validation:** Never modify JIRA tickets, Polarion work items, or cluster resources
- Always `browser_snapshot()` before any interaction to get element refs
- Use short waits (1-3s) with snapshot checks between, not single long waits
- Document all discrepancies between source code expectations and live behavior

### Process

1. Verify environment: `oc whoami`, `oc get mch`, `oc get managedcluster`, `clusters()` via acm-kubectl
2. Navigate to feature: `browser_navigate(url)` → `browser_snapshot()`
3. Test feature flow: click, fill, observe, snapshot after each action
4. Verify backend: `oc get <resource> -o yaml`, `find_resources()` via acm-search
5. Check for errors: `browser_console_messages()`, `browser_network_requests()`
6. Document discrepancies

### Output

Markdown written to `phase6-live-validation.md` with cluster info, step-by-step verification results, discrepancies, and confirmed behaviors.

---

## Test Case Writer

**Phase:** 7
**File:** `references/agents/test-case-writer.md`
**Tools:** acm-ui (spot-check only)

### Purpose

Writes the Polarion-ready test case markdown from the synthesized investigation context. Does NOT perform primary investigation.

### Key Rules

- Reads conventions and peer test cases before writing
- Scope gate: only plans steps that map to target JIRA story's ACs
- MCP spot-check: verifies entry point route and key translations are current
- Finds component-specific parameterized routes, not just area-level routes
- Never states numeric thresholds without evidence from PR diff, JIRA AC, MCP, or area knowledge
- AC discrepancy notes: if synthesized context has discrepancies, includes Notes explaining each
- Self-reviews before writing the file

### Output

- `test-case.md` — primary deliverable
- `analysis-results.json` — investigation metadata

### Handling Incomplete Upstream Data

If `VALIDATION_WARNINGS_PATH` is present, upstream phases produced incomplete artifacts. The writer proceeds with available data: `[DATA GAP]` notes in the synthesized context are not filled with invented data, `[INFERRED]` claims that fail MCP spot-checks get `[MANUAL VERIFICATION REQUIRED]` added to the affected step's expected result, and `"validation_warnings_present": true` is recorded in `analysis-results.json`.

### Retry Handling

If the orchestrator's schema validator finds errors in `analysis-results.json`, it re-spawns the writer with a `<retry>` block. The writer fixes the malformed metadata fields without adding placeholder values, preserving valid data from the previous attempt. The `test-case.md` is not rewritten unless the errors indicate content issues.

---

## Quality Reviewer

**Phase:** 8
**File:** `references/agents/quality-reviewer.md`
**Tools:** acm-ui, polarion
**Knowledge dependencies:** Reads `knowledge/conventions/test-case-format.md`, `knowledge/conventions/area-naming-patterns.md`, `knowledge/conventions/cli-in-steps-rules.md` as validation reference. Also reads peer test cases from `gather-output.json` `existing_test_cases` field (or `knowledge/examples/sample-test-case.md` as fallback).

### Purpose

Validates the generated test case against conventions, verifies UI elements were discovered (not assumed), checks AC vs implementation consistency, and enforces Polarion metadata completeness.

### Review Steps

| Step | Check | Severity |
|------|-------|----------|
| 1 | Read the test case | — |
| 2 | Read conventions (3 files) | — |
| 3 | Structural validation (title, metadata, sections, steps, teardown) | Blocking/Warning |
| 4 | Discovered vs assumed (min 3 MCP checks; mandatory `get_component_source()` on primary file) | Blocking |
| 4.5 | AC vs implementation (JIRA ACs consistent with expected results, scope alignment, verify cited discrepancies via source) | Blocking |
| 4.6 | Knowledge file cross-reference (field order, filtering, component names vs area knowledge) | Blocking |
| 4.7 | Design efficiency (resource optimization, entry point selection, prerequisite completeness, step design) | Warning |
| 4.8 | Coverage gap verification (gaps triaged as ADD have test steps, NOTE gaps mentioned) | Warning |
| 5 | Polarion coverage check (search for duplicates) | Info |
| 6 | Peer consistency check (compare with existing test cases) | Info |
| 7 | Polarion HTML check (only on `/review`, not during `/generate`) | Warning |

### Verdict

- **PASS:** Proceed to Phase 9
- **NEEDS_FIXES:** List blocking issues with fix instructions; orchestrator fixes and re-runs

### Handling Incomplete Upstream Data

If `VALIDATION_WARNINGS_PATH` is present, upstream phases produced incomplete artifacts. The reviewer adjusts severity: steps marked `[MANUAL VERIFICATION REQUIRED]` due to upstream data gaps are NOT blocking (they are expected), steps marked `[INFERRED]` are flagged as WARNING (not BLOCKING), and steps where the writer invented data not present in the synthesized context are still flagged as BLOCKING.

### Re-Review Protocol

On re-review after fixes:
1. Re-read the updated test case
2. Re-check ONLY previously reported blocking issues
3. Verify each was actually fixed
4. Check that fixes didn't introduce new issues
5. Return new verdict
