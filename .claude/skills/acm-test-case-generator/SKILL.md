---
name: acm-test-case-generator
description: >-
  Generate Polarion-ready ACM Console UI test cases from JIRA tickets. Runs a
  multi-phase subagent pipeline with JIRA investigation, PR diff analysis, UI
  discovery, synthesis, optional live validation, test case writing, and mandatory
  quality review. Use when asked to generate a test case, write test coverage, or
  process an ACM JIRA ticket for testing.
compatibility: >-
  Required MCPs: acm-source, jira, polarion. Recommended: neo4j-rhacm. Optional:
  acm-search, acm-kubectl, playwright. Also needs gh CLI. Run /onboard to configure.
metadata:
  author: acm-qe
  version: "2.0.0"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Bash(python ${CLAUDE_SKILL_DIR}/scripts/gather.py:*)
  - Bash(python ${CLAUDE_SKILL_DIR}/scripts/report.py:*)
  - Bash(python ${CLAUDE_SKILL_DIR}/scripts/review_enforcement.py:*)
  - Bash(python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py:*)
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
  - Bash(oc:*)
  - mcp__acm-source__set_acm_version
  - mcp__acm-source__set_cnv_version
  - mcp__acm-source__get_routes
  - mcp__acm-source__search_translations
  - mcp__acm-source__get_component_source
  - mcp__acm-source__search_code
  - mcp__jira__get_issue
  - mcp__jira__search_issues
  - mcp__polarion__get_polarion_work_items
  - mcp__polarion__get_polarion_test_case_summary
  - mcp__polarion__check_polarion_status
---

# ACM Console Test Case Generator

Subagent-orchestrated pipeline generating Polarion-ready test cases from JIRA tickets. Each investigation phase runs in an isolated subagent context, writes structured output to disk, and terminates -- preventing context pressure and recency bias. The orchestrator is thin routing logic only.

> **Mapping note:** This skill uses a 9-phase model (Phases 0-8) where data gathering and JIRA investigation are merged into Phase 1, and investigation is split into sequential phases (2-3). The app pipeline (`apps/test-case-generator/`) consolidates investigation into 1 parallel phase. See the app README for the mapping table.

## Pipeline Phases

Read `references/phase-gates.md` for gate rules and progress indicators.

### Phase 0: Determine Inputs

Resolve before starting the pipeline:

1. **JIRA ID** (required): The ticket to generate a test case for (e.g., ACM-30459)
2. **ACM Version**: From JIRA fix_versions, or ask: "Which ACM version?"
3. **PR Number**: Auto-detect from JIRA description/comments, or ask if not found
4. **Area**: Auto-detect from PR file paths (governance, rbac, fleet-virt, clusters, search, applications, credentials, cclm, mtv)
5. **Cluster URL** (optional): Run `oc whoami --show-server 2>/dev/null`. If logged in, derive console URL via `oc get route console -n openshift-console -o jsonpath='{.spec.host}' 2>/dev/null`. If unavailable, ask or skip live validation. In headless mode (`-p`), auto-detect only.
6. **CNV Version** (Fleet Virt only): Ask or auto-detect via `mcp__acm-source__detect_cnv_version`

If all inputs can be inferred from the JIRA ticket, proceed without asking.

### Phase 1: Gather Data + Investigate JIRA Story

Read `${CLAUDE_SKILL_DIR}/references/agents/data-gatherer.md`. Spawn a subagent (Agent tool, description: "Data Gathering + JIRA Investigation") with the full agent instructions and:

<input>
JIRA_ID: <value>
ACM_VERSION: <value>
AREA: <value>
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>

**Do NOT pre-create a run directory.** The agent runs `gather.py` internally, which creates the run directory at `runs/test-case-generator/<JIRA_ID>/<JIRA_ID>-<YYYY-MM-DDTHH-MM-SS>/` and prints the path on its last stdout line. The agent writes all artifacts to that directory and returns the path. Capture `RUN_DIR` from the agent's result.

The agent produces `gather-output.json`, `pr-diff.txt`, and `phase1-jira.json`.

Validate both artifacts:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/gather-output.json gather-output
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase1-jira.json phase1-jira
```

- `gather-output` FAIL: **stop the pipeline** (gather.py is deterministic — failures indicate a script bug, not an LLM issue).
- `phase1-jira` FAIL: enter Retry Protocol (schema: phase1-jira, agent: data-gatherer.md).

Read `gather-output.json` to fill in any unresolved inputs (PR number, area, repo). Record the run directory path.

Do NOT read `phase1-jira.json` into orchestrator context.
Show: "Phase 1 complete. Gathered N PRs, JIRA findings written to phase1-jira.json."

### Phase 2: Analyze PR Code Changes

Read `${CLAUDE_SKILL_DIR}/references/agents/code-analyzer.md`. Spawn a subagent (description: "Code Analysis") with the instructions and:

<input>
JIRA_ID: <value>
PR_NUMBER: <value>
REPO: <value>
ACM_VERSION: <value>
AREA: <value>
RUN_DIR: <path>
PR_DIFF_PATH: <path to pr-diff.txt>
KNOWLEDGE_DIR: ${CLAUDE_SKILL_DIR}/../../knowledge/test-case-generator
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>

Verify `phase2-code.json` exists. Run artifact validation:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase2-code.json phase2-code
```

If PASS: continue. If FAIL: enter Retry Protocol (schema: phase2-code, agent: code-analyzer.md).

Show: "Phase 2 complete. Code analysis written to phase2-code.json."

### Phase 3: Discover UI Elements

Read `${CLAUDE_SKILL_DIR}/references/agents/ui-discoverer.md`. Spawn a subagent (description: "UI Discovery") with the instructions and:

<input>
ACM_VERSION: <value>
CNV_VERSION: <value or "N/A">
AREA: <value>
FEATURE_NAME: <JIRA summary>
RUN_DIR: <path>
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>

Verify `phase3-ui.json` exists. Run artifact validation:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase3-ui.json phase3-ui
```

If PASS: continue. If FAIL: enter Retry Protocol (schema: phase3-ui, agent: ui-discoverer.md).

Show: "Phase 3 complete. UI elements written to phase3-ui.json."

### Pre-Synthesis Readiness Check

Before synthesis, verify minimum viable data exists across all investigation artifacts:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py --pre-synthesis <RUN_DIR>
```

If PASS: continue to Phase 4.

If FAIL: **stop the pipeline**. The check reports exactly which minimum data points are missing (e.g., empty acceptance criteria, missing entry point). Upstream phases already exhausted their retry attempts -- there is nothing left to retry. Report the missing data to the user.

### Phase 4: Synthesize

Read `${CLAUDE_SKILL_DIR}/references/agents/synthesizer.md`. Spawn a subagent (description: "Synthesis") with the instructions and:

<input>
JIRA_ID: <value>
ACM_VERSION: <value>
AREA: <value>
CLUSTER_URL: <value or "NONE">
RUN_DIR: <path>
SYNTHESIS_TEMPLATE_PATH: ${CLAUDE_SKILL_DIR}/references/synthesis-template.md
KNOWLEDGE_DIR: ${CLAUDE_SKILL_DIR}/../../knowledge/test-case-generator
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>

Verify `synthesized-context.md` exists. Run artifact validation:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/synthesized-context.md synthesized-context
```

If PASS: continue. If FAIL: enter Retry Protocol (schema: synthesized-context, agent: synthesizer.md).

Show: "Phase 4 complete. Synthesized context written."

### Phase 5: Live Validation (conditional)

**Skip** if no cluster URL was resolved in Phase 0: "Skipping live validation -- no cluster available."

Read `${CLAUDE_SKILL_DIR}/references/agents/live-validator.md`. Spawn a subagent (description: "Live Validation") with the instructions and:

<input>
CONSOLE_URL: <value>
ACM_VERSION: <value>
RUN_DIR: <path>
SYNTHESIZED_CONTEXT_PATH: <path to synthesized-context.md>
GATHER_OUTPUT_PATH: <path to gather-output.json>
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>

Verify `phase5-live-validation.md` exists. Show: "Phase 5 complete. Live validation written."

#### Apply Live Validation Corrections

After the live validator subagent returns, check its output for a `## Corrections` section.
If corrections exist:
1. Parse each correction row (Field, Phase 3 Value, Correct Value, Evidence)
2. Update the synthesized context with the corrected values
3. Specifically: if `entry_point` was corrected, use the live-validated value for the test case
4. Log: "Correction applied: {field} changed from '{old}' to '{new}' (source: live validation)"

Arbitration rule: For user-visible labels (tab names, button text, breadcrumbs, column headers),
live UI observation ALWAYS overrides source-code-inferred values. Source code tells you the route
exists; the live UI tells you what label the user sees.

### Phase 6: Write Test Case

Read `${CLAUDE_SKILL_DIR}/references/agents/test-case-writer.md`. Spawn a subagent (description: "Test Case Writing") with the instructions and:

<input>
JIRA_ID: <value>
ACM_VERSION: <value>
AREA: <value>
RUN_DIR: <path>
SYNTHESIZED_CONTEXT_PATH: <path to synthesized-context.md>
LIVE_VALIDATION_PATH: <path to phase5-live-validation.md or "N/A">
GATHER_OUTPUT_PATH: <path to gather-output.json>
SKILL_DIR: ${CLAUDE_SKILL_DIR}
KNOWLEDGE_DIR: ${CLAUDE_SKILL_DIR}/../../knowledge/test-case-generator
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>

Verify `test-case.md` and `analysis-results.json` exist. Run artifact validation:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/analysis-results.json analysis-results
```

If PASS: continue. If FAIL: enter Retry Protocol (schema: analysis-results, agent: test-case-writer.md).

Show: "Phase 6 complete. Test case written."

### Phase 7: Quality Review (MANDATORY GATE)

Read `${CLAUDE_SKILL_DIR}/references/agents/quality-reviewer.md`. Spawn a subagent (description: "Quality Review") with the instructions and:

<input>
ACM_VERSION: <value>
AREA: <value>
RUN_DIR: <path>
TEST_CASE_PATH: <path to test-case.md>
GATHER_OUTPUT_PATH: <path to gather-output.json>
SKILL_DIR: ${CLAUDE_SKILL_DIR}
KNOWLEDGE_DIR: ${CLAUDE_SKILL_DIR}/../../knowledge/test-case-generator
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>

Read the review output. Run programmatic enforcement:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/review_enforcement.py <review-output-file>
```

**If PASS:** proceed to Phase 8.

**If NEEDS_FIXES -- 3-tier escalation:**

**Tier 1 (inline MCP):** Parse BLOCKING issues. Make 1-3 targeted MCP calls (`set_acm_version`, `search_translations`, `get_component_source`) for correct values. Fix `test-case.md` via Edit. Spawn NEW quality-reviewer subagent. Re-run enforcement.

**Tier 2 (writer retry):** Spawn NEW test-case-writer subagent with `MODE: REVISION` and reviewer flags. Spawn NEW quality-reviewer subagent. Re-run enforcement.

**Tier 3 (proceed):** Mark unresolvable steps with `[MANUAL VERIFICATION REQUIRED: <issue>]`. Proceed to Phase 8.

Show: "Quality review PASSED." or "Quality review: N steps flagged for manual verification."

### Phase 8: Generate Reports

```bash
python ${CLAUDE_SKILL_DIR}/scripts/report.py <run-directory>
```

Show the final summary with all output file paths.

## Retry Protocol

When artifact validation fails for an AI-produced phase (1, 2, 3, 4, or 6), retry up to 3 times before proceeding with incomplete data.

**For each attempt:** Re-spawn the SAME agent type with the original `<input>` block PLUS a `<retry>` block appended:

```
<retry>
ATTEMPT: N of 3
PREVIOUS_OUTPUT_PATH: <path to the invalid artifact>
VALIDATION_ERRORS:
- [error lines from validate_artifact.py]
INSTRUCTION: Review the validation errors above. Re-investigate where data is
missing or malformed — do not add placeholder values. Write corrected output
to the same path.
</retry>
```

**After 3 failures:** Proceed with incomplete data:
1. Write `validation-warnings.json` to the run directory containing the phase name, schema, attempt count, and final errors
2. Print: `"Phase N: validation failed after 3 attempts. Proceeding with incomplete data."`
3. Pass `VALIDATION_WARNINGS_PATH` in all downstream `<input>` blocks so agents are aware of gaps

**Phase 1 exception:** `gather-output.json` is produced by deterministic Python (gather.py) within the data-gatherer agent. Validation failure means a script bug — stop the pipeline immediately instead of retrying. However, `phase1-jira.json` is AI-produced and follows the normal retry protocol.

**Phase 5 and 7 exceptions:** Phase 5 (live validation) produces unstructured markdown — no schema validation. Phase 7 (quality review) has its own enforcement via `review_enforcement.py` — no change.

## Run Directory

Each run: `runs/test-case-generator/<JIRA_ID>/<JIRA_ID>-<YYYY-MM-DDTHH-MM-SS>/` (e.g., `runs/test-case-generator/ACM-32280/ACM-32280-2026-05-04T15-09-19/`).

The directory is created by `gather.py` — do NOT pre-create it. The orchestrator captures the path from gather.py's stdout (last line) via the data-gatherer agent.

```
gather-output.json        -- Phase 1: PR metadata, conventions
pr-diff.txt               -- Phase 1: full PR diff
phase1-jira.json          -- Phase 1: JIRA findings
phase2-code.json          -- Phase 2: code analysis
phase3-ui.json            -- Phase 3: UI elements
synthesized-context.md    -- Phase 4: merged test plan
phase5-live-validation.md -- Phase 5: live results (optional)
test-case.md              -- Phase 6: primary deliverable
analysis-results.json     -- Phase 6: investigation metadata
test-case-description.html -- Phase 8: Polarion description HTML
test-case-setup.html      -- Phase 8: Polarion setup HTML
test-case-steps.html      -- Phase 8: Polarion steps HTML
validation-warnings.json  -- Retry Protocol: present only if validation failed after 3 attempts
review-results.json       -- Phase 8: structural validation
SUMMARY.txt               -- Phase 8: human-readable summary
```

## Safety Rules

1. **Read-only** -- never modify JIRA tickets, Polarion items, or cluster resources
2. **No assumptions** -- all UI labels, routes, selectors from MCP or investigation
3. **Evidence-based** -- every expected result traces to a source
4. **Quality gate** -- never deliver without passing review AND programmatic enforcement
