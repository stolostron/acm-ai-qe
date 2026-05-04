---
name: acm-test-case-generator
description: >-
  Generate Polarion-ready ACM Console UI test cases from JIRA tickets. Runs a
  multi-phase subagent pipeline with JIRA investigation, PR diff analysis, UI
  discovery, synthesis, optional live validation, test case writing, and mandatory
  quality review. Use when asked to generate a test case, write test coverage, or
  process an ACM JIRA ticket for testing.
compatibility: >-
  Required MCPs: acm-ui, jira, polarion. Recommended: neo4j-rhacm. Optional:
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
  - mcp__acm-ui__set_acm_version
  - mcp__acm-ui__set_cnv_version
  - mcp__acm-ui__get_routes
  - mcp__acm-ui__search_translations
  - mcp__acm-ui__get_component_source
  - mcp__acm-ui__search_code
  - mcp__jira__get_issue
  - mcp__jira__search_issues
  - mcp__polarion__get_polarion_work_items
  - mcp__polarion__get_polarion_test_case_summary
  - mcp__polarion__check_polarion_status
---

# ACM Console Test Case Generator

Subagent-orchestrated pipeline generating Polarion-ready test cases from JIRA tickets. Each investigation phase runs in an isolated subagent context, writes structured output to disk, and terminates -- preventing context pressure and recency bias. The orchestrator is thin routing logic only.

> **Mapping note:** This skill uses a 10-phase model where investigation is split into 3 sequential phases (2-4). The app pipeline (`apps/test-case-generator/`) consolidates these into 1 parallel phase. See the app README for the mapping table.

## Pipeline Phases

Read `references/phase-gates.md` for gate rules and progress indicators.

### Phase 0: Determine Inputs

Resolve before starting the pipeline:

1. **JIRA ID** (required): The ticket to generate a test case for (e.g., ACM-30459)
2. **ACM Version**: From JIRA fix_versions, or ask: "Which ACM version?"
3. **PR Number**: Auto-detect from JIRA description/comments, or ask if not found
4. **Area**: Auto-detect from PR file paths (governance, rbac, fleet-virt, clusters, search, applications, credentials, cclm, mtv)
5. **Cluster URL** (optional): Run `oc whoami --show-server 2>/dev/null`. If logged in, derive console URL via `oc get route console -n openshift-console -o jsonpath='{.spec.host}' 2>/dev/null`. If unavailable, ask or skip live validation. In headless mode (`-p`), auto-detect only.
6. **CNV Version** (Fleet Virt only): Ask or auto-detect via `mcp__acm-ui__detect_cnv_version`

If all inputs can be inferred from the JIRA ticket, proceed without asking.

### Phase 1: Gather Data

```bash
python ${CLAUDE_SKILL_DIR}/scripts/gather.py <JIRA_ID> [--version VERSION] [--pr PR_NUMBER] [--area AREA] [--repo REPO]
```

Produces `gather-output.json` and `pr-diff.txt`. Validate the output:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/gather-output.json gather-output
```

If FAIL: **stop the pipeline** (gather.py is deterministic — failures indicate a script bug, not an LLM issue). Report the error.

Read the JSON to fill in any unresolved inputs (PR number, area, repo). Record the run directory path.

Show: "Gathered PR #NNNN, N files changed. Area: [area]."

### Phase 2: Investigate JIRA Story

Read `${CLAUDE_SKILL_DIR}/references/agents/jira-investigator.md`. Spawn a subagent (Agent tool, description: "JIRA Investigation") with the full agent instructions and:

<input>
JIRA_ID: <value>
ACM_VERSION: <value>
AREA: <value>
RUN_DIR: <path>
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>

Verify `phase2-jira.json` exists. Run artifact validation:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase2-jira.json phase2-jira
```

If PASS: continue. If FAIL: enter Retry Protocol (schema: phase2-jira, agent: jira-investigator.md).

Do NOT read the validated artifact into orchestrator context.
Show: "Phase 2 complete. JIRA findings written to phase2-jira.json."

### Phase 3: Analyze PR Code Changes

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

Verify `phase3-code.json` exists. Run artifact validation:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase3-code.json phase3-code
```

If PASS: continue. If FAIL: enter Retry Protocol (schema: phase3-code, agent: code-analyzer.md).

Show: "Phase 3 complete. Code analysis written to phase3-code.json."

### Phase 4: Discover UI Elements

Read `${CLAUDE_SKILL_DIR}/references/agents/ui-discoverer.md`. Spawn a subagent (description: "UI Discovery") with the instructions and:

<input>
ACM_VERSION: <value>
CNV_VERSION: <value or "N/A">
AREA: <value>
FEATURE_NAME: <JIRA summary>
RUN_DIR: <path>
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>

Verify `phase4-ui.json` exists. Run artifact validation:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase4-ui.json phase4-ui
```

If PASS: continue. If FAIL: enter Retry Protocol (schema: phase4-ui, agent: ui-discoverer.md).

Show: "Phase 4 complete. UI elements written to phase4-ui.json."

### Pre-Synthesis Readiness Check

Before synthesis, verify minimum viable data exists across all investigation artifacts:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py --pre-synthesis <RUN_DIR>
```

If PASS: continue to Phase 5.

If FAIL: **stop the pipeline**. The check reports exactly which minimum data points are missing (e.g., empty acceptance criteria, missing entry point). Upstream phases already exhausted their retry attempts -- there is nothing left to retry. Report the missing data to the user.

### Phase 5: Synthesize

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

Show: "Phase 5 complete. Synthesized context written."

### Phase 6: Live Validation (conditional)

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

Verify `phase6-live-validation.md` exists. Show: "Phase 6 complete. Live validation written."

### Phase 7: Write Test Case

Read `${CLAUDE_SKILL_DIR}/references/agents/test-case-writer.md`. Spawn a subagent (description: "Test Case Writing") with the instructions and:

<input>
JIRA_ID: <value>
ACM_VERSION: <value>
AREA: <value>
RUN_DIR: <path>
SYNTHESIZED_CONTEXT_PATH: <path to synthesized-context.md>
LIVE_VALIDATION_PATH: <path to phase6-live-validation.md or "N/A">
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

Show: "Phase 7 complete. Test case written."

### Phase 8: Quality Review (MANDATORY GATE)

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

**If PASS:** proceed to Phase 9.

**If NEEDS_FIXES -- 3-tier escalation:**

**Tier 1 (inline MCP):** Parse BLOCKING issues. Make 1-3 targeted MCP calls (`set_acm_version`, `search_translations`, `get_component_source`) for correct values. Fix `test-case.md` via Edit. Spawn NEW quality-reviewer subagent. Re-run enforcement.

**Tier 2 (writer retry):** Spawn NEW test-case-writer subagent with `MODE: REVISION` and reviewer flags. Spawn NEW quality-reviewer subagent. Re-run enforcement.

**Tier 3 (proceed):** Mark unresolvable steps with `[MANUAL VERIFICATION REQUIRED: <issue>]`. Proceed to Phase 9.

Show: "Quality review PASSED." or "Quality review: N steps flagged for manual verification."

### Phase 9: Generate Reports

```bash
python ${CLAUDE_SKILL_DIR}/scripts/report.py <run-directory>
```

Show the final summary with all output file paths.

## Retry Protocol

When artifact validation fails for an AI-produced phase (2, 3, 4, 5, or 7), retry up to 3 times before proceeding with incomplete data.

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

**Phase 1 exception:** `gather-output.json` is produced by deterministic Python (gather.py), not an LLM. Validation failure means a script bug — stop the pipeline immediately instead of retrying.

**Phase 6 and 8 exceptions:** Phase 6 (live validation) produces unstructured markdown — no schema validation. Phase 8 (quality review) has its own enforcement via `review_enforcement.py` — no change.

## Run Directory

Each run: `runs/<JIRA_ID>/<timestamp>/`

```
gather-output.json        -- Phase 1: PR metadata, conventions
pr-diff.txt               -- Phase 1: full PR diff
phase2-jira.json          -- Phase 2: JIRA findings
phase3-code.json          -- Phase 3: code analysis
phase4-ui.json            -- Phase 4: UI elements
synthesized-context.md    -- Phase 5: merged test plan
phase6-live-validation.md -- Phase 6: live results (optional)
test-case.md              -- Phase 7: primary deliverable
analysis-results.json     -- Phase 7: investigation metadata
test-case-setup.html      -- Phase 9: Polarion setup HTML
test-case-steps.html      -- Phase 9: Polarion steps HTML
validation-warnings.json  -- Retry Protocol: present only if validation failed after 3 attempts
review-results.json       -- Phase 9: structural validation
SUMMARY.txt               -- Phase 9: human-readable summary
```

## Safety Rules

1. **Read-only** -- never modify JIRA tickets, Polarion items, or cluster resources
2. **No assumptions** -- all UI labels, routes, selectors from MCP or investigation
3. **Evidence-based** -- every expected result traces to a source
4. **Quality gate** -- never deliver without passing review AND programmatic enforcement
