---
name: acm-test-case-generator
description: >-
  Use this skill when the user wants a FULL end-to-end Polarion-ready ACM Console UI
  test case from a JIRA ticket (e.g. ACM-30459): JIRA + PRs + UI discovery + synthesis
  + optional live validation + writing + mandatory quality review. This is the ONLY
  skill for that complete path. Do NOT use acm-test-case-writer or acm-qe-code-analyzer
  for the same request—they are partial workflows. Do NOT use acm-knowledge-base alone;
  it is reference-only. TRIGGER: generate/write test case from JIRA, Polarion test case
  for ACM ticket, test coverage for a story. DO NOT TRIGGER: PR-only diff analysis without
  JIRA-to-Polarion pipeline (use acm-qe-code-analyzer); review-only (use acm-test-case-reviewer).
compatibility: >-
  Required MCPs: acm-source, jira, polarion. Recommended: neo4j-rhacm. Optional:
  acm-search, acm-kubectl, playwright. Also needs gh CLI. Run /onboard to configure.
metadata:
  author: acm-qe
  version: "2.1.0"
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
  - mcp__acm-source__list_repos
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
  - mcp__polarion__get_polarion_work_item
  - mcp__polarion__get_polarion_test_case_summary
  - mcp__polarion__check_polarion_status
---

# ACM Console Test Case Generator

Subagent-orchestrated pipeline generating Polarion-ready test cases from JIRA tickets. Each investigation phase runs in an isolated subagent context, writes structured output to disk, and terminates -- preventing context pressure and recency bias. The orchestrator is thin routing logic only.

> **Mapping note:** This skill uses a 9-phase model (Phases 0-8) where data gathering and JIRA investigation are merged into Phase 1, and investigation is split into sequential phases (2-3). See the app README for the mapping table.

Read `${CLAUDE_SKILL_DIR}/references/pipeline-detail.md` for phase input schemas. Per-concern details are split for progressive loading:
- Phase 0: read `${CLAUDE_SKILL_DIR}/references/phase0-inputs.md` for credential resolution and MCP availability checks
- On validation failure: read `${CLAUDE_SKILL_DIR}/references/validation-protocol.md` for retry protocol
- Phase 1 (before creating run dir): read `${CLAUDE_SKILL_DIR}/references/run-directory.md` for artifact naming

## Pipeline Phases

Read `references/phase-gates.md` for gate rules and progress indicators.

### Phase 0: Determine Inputs

Resolve before starting the pipeline:

1. **JIRA ID** (required): The ticket to generate a test case for (e.g., ACM-30459)
2. **ACM Version**: From JIRA fix_versions, or ask: "Which ACM version?"
3. **PR Number**: Auto-detect from JIRA description/comments, or ask if not found
4. **Area**: Auto-detect from PR file paths (governance, rbac, fleet-virt, clusters, search, applications, credentials, cclm, mtv)
5. **Cluster URL** (optional): Run `oc whoami --show-server 2>/dev/null`. If logged in, derive console URL via `oc get route console -n openshift-console -o jsonpath='{.spec.host}' 2>/dev/null`. If unavailable, ask or skip live validation. In headless mode (`-p`), auto-detect only.
6. **Console Credentials** (optional): Resolve via the priority cascade in `pipeline-detail.md#phase-0-credential-resolution`.
7. **MCP Availability Check**: Run the MCP probe described in `pipeline-detail.md#phase-0-mcp-availability-check`. If REQUIRED MCPs are unavailable, warn the user. If IMPORTANT MCPs are unavailable, warn and proceed.

If all inputs can be inferred from the JIRA ticket, proceed without asking.

### Phase 1: Gather Data + Investigate JIRA Story

Read `${CLAUDE_SKILL_DIR}/references/agents/data-gatherer.md`. Spawn a subagent (Agent tool, description: "Data Gathering + JIRA Investigation") with the full agent instructions and the Phase 1 input from `pipeline-detail.md`.

- `gather-output` validation FAIL: **stop the pipeline** (gather.py is deterministic -- failures indicate a script bug, not an LLM issue).
- `phase1-jira` validation FAIL: enter Retry Protocol (see `pipeline-detail.md`).

Read `gather-output.json` to fill in any unresolved inputs (PR number, area, repo). Record the run directory path.

Do NOT read `phase1-jira.json` into orchestrator context.
Show: "Phase 1 complete. Gathered N PRs, JIRA findings written to phase1-jira.json."

### Phase 2: Analyze PR Code Changes

Read `${CLAUDE_SKILL_DIR}/references/agents/code-analyzer.md`. Spawn a subagent (description: "Code Analysis") with the instructions and the Phase 2 input from `pipeline-detail.md`.

If validation PASS: continue. If FAIL: enter Retry Protocol.

Show: "Phase 2 complete. Code analysis written to phase2-code.json."

### Phase 3: Discover UI Elements

Read `${CLAUDE_SKILL_DIR}/references/agents/ui-discoverer.md`. Spawn a subagent (description: "UI Discovery") with the instructions and the Phase 3 input from `pipeline-detail.md`.

If validation PASS: continue. If FAIL: enter Retry Protocol.

Show: "Phase 3 complete. UI elements written to phase3-ui.json."

### Pre-Synthesis Readiness Check

Run the pre-synthesis validation (see `pipeline-detail.md`).

If PASS: continue to Phase 4.
If FAIL: **stop the pipeline**. Upstream phases already exhausted their retry attempts. Report the missing data to the user.

### Phase 4: Synthesize

Read `${CLAUDE_SKILL_DIR}/references/agents/synthesizer.md`. Spawn a subagent (description: "Synthesis") with the instructions and the Phase 4 input from `pipeline-detail.md`.

If validation PASS: continue. If FAIL: enter Retry Protocol.

Show: "Phase 4 complete. Synthesized context written."

### Phase 5: Live Validation (conditional)

**Skip** if no cluster URL was resolved in Phase 0: "Skipping live validation -- no cluster available."

Read `${CLAUDE_SKILL_DIR}/references/agents/live-validator.md`. Spawn a subagent (description: "Live Validation") with the instructions and the Phase 5 input from `pipeline-detail.md`.

Verify `phase5-live-validation.md` exists. Apply live validation corrections per `pipeline-detail.md#phase-5-live-validation-corrections`.

Show: "Phase 5 complete. Live validation written."

### Phase 6: Write Test Case

Read `${CLAUDE_SKILL_DIR}/references/agents/test-case-writer.md`. Spawn a subagent (description: "Test Case Writing") with the instructions and the Phase 6 input from `pipeline-detail.md`.

If validation PASS: continue. If FAIL: enter Retry Protocol.

Show: "Phase 6 complete. Test case written."

### Phase 7: Quality Review (MANDATORY GATE)

Read `${CLAUDE_SKILL_DIR}/references/agents/quality-reviewer.md`. Spawn a subagent (description: "Quality Review") with the instructions and the Phase 7 input from `pipeline-detail.md`.

Read the review output. Run programmatic enforcement (see `pipeline-detail.md`).

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

## Safety Rules

1. **Read-only** -- never modify JIRA tickets, Polarion items, or cluster resources
2. **No assumptions** -- all UI labels, routes, selectors from MCP or investigation
3. **Evidence-based** -- every expected result traces to a source
4. **Quality gate** -- never deliver without passing review AND programmatic enforcement
5. **Skill feedback** -- if any skill file produces incorrect guidance during the pipeline, follow `${CLAUDE_SKILL_DIR}/references/skill-feedback.md` to report the issue
