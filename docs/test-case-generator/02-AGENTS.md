# Agent Definitions

Six specialized agents, each with a dedicated role in the pipeline. Agent definitions are in `.claude/agents/`. Each agent receives specific inputs, uses designated MCP tools, and returns a structured output block.

## Agent Summary

| Agent | File | Phase | Tools | Input | Output |
|-------|------|-------|-------|-------|--------|
| Feature Investigator | `feature-investigator.md` | 1 (parallel) | jira, polarion, neo4j-rhacm, bash | JIRA ID | FEATURE INVESTIGATION block |
| Code Change Analyzer | `code-change-analyzer.md` | 1 (parallel) | acm-ui, neo4j-rhacm, bash | PR number, repo, version | CODE CHANGE ANALYSIS block |
| UI Discovery | `ui-discovery.md` | 1 (parallel) | acm-ui, neo4j-rhacm, playwright (conditional), bash | Version, area, feature name, cluster URL (optional) | UI DISCOVERY RESULTS block (+ live verification) |
| Live Validator | `live-validator.md` | 3 | playwright, acm-search, acm-kubectl, bash | Console URL, feature path | LIVE VALIDATION RESULTS block |
| Test Case Generator | `test-case-generator.md` | 4 | acm-ui | Run dir, synthesized context | `test-case.md`, `analysis-results.json` |
| Quality Reviewer | `quality-reviewer.md` | 4.5 | acm-ui, polarion | test-case.md path, version, area | PASS or NEEDS_FIXES |

---

## Feature Investigator

**Phase:** 1 (parallel)
**File:** `.claude/agents/feature-investigator.md`
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

```
FEATURE INVESTIGATION
=====================
Story: [JIRA ID] - [summary]
Fix Version: [version]
Status: [status]

Acceptance Criteria:
1. [AC bullet from JIRA]
2. [AC bullet]

Linked Tickets:
- [related-ticket]: [relationship]

Comments Summary:
- [design decisions, testing notes]

Existing Polarion Coverage:
- [existing test cases or "None found"]

Test Scenarios:
1. [scenario from ACs]
2. [scenario]
```

---

## Code Change Analyzer

**Phase:** 1 (parallel)
**File:** `.claude/agents/code-change-analyzer.md`
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

```
CODE CHANGE ANALYSIS
====================
PR: #NNNN - [title]
Files Changed: N (+additions, -deletions)

Changed Components:
- [file path]: [what changed]

New UI Elements:
- [element]: [description]

UI Interaction Models:
- [element]: [PatternFly component type] -- [interaction pattern]

Translation Strings:
- "[UI text]": [context]

Test Scenarios from Code Changes:
1. [scenario]
```

---

## UI Discovery

**Phase:** 1 (parallel)
**File:** `.claude/agents/ui-discovery.md`
**Tools:** acm-ui, neo4j-rhacm, playwright (conditional), bash

### Purpose

Discovers UI selectors, translations, routes, wizard steps, and test IDs from the ACM Console source code via the acm-ui MCP server. When a cluster URL is provided, performs optional live browser verification (Step 9) to confirm that discovered elements actually render on a real cluster.

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

```
UI DISCOVERY RESULTS
====================
ACM Version: [version]

Translations Found:
- [key] -> [UI string]

Routes Found:
- [route name] -> [path pattern]

Selectors Found:
- [component] -> [selector]

Test IDs Found:
- [test ID and location]

Component Structure:
- [how components fit together]
```

---

## Live Validator

**Phase:** 3 (conditional)
**File:** `.claude/agents/live-validator.md`
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

---

## Test Case Generator

**Phase:** 4
**File:** `.claude/agents/test-case-generator.md`
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

---

## Quality Reviewer

**Phase:** 4.5
**File:** `.claude/agents/quality-reviewer.md`
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

- **PASS:** Proceed to Stage 3
- **NEEDS_FIXES:** List blocking issues with fix instructions; orchestrator fixes and re-runs

### Re-Review Protocol

On re-review after fixes:
1. Re-read the updated test case
2. Re-check ONLY previously reported blocking issues
3. Verify each was actually fixed
4. Check that fixes didn't introduce new issues
5. Return new verdict
