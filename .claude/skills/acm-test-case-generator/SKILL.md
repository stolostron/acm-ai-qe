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
  - mcp__acm-source__list_versions
  - mcp__acm-source__detect_cnv_version
  - mcp__acm-source__get_route_component
  - mcp__acm-source__get_component_types
  - mcp__acm-source__get_acm_selectors
  - mcp__jira__get_issue
  - mcp__jira__search_issues
  - mcp__polarion__get_polarion_work_items
  - mcp__polarion__get_polarion_work_item
  - mcp__polarion__get_polarion_test_case_summary
  - mcp__polarion__check_polarion_status
  - mcp__neo4j-rhacm__read_neo4j_cypher
  - mcp__neo4j-rhacm__get_neo4j_schema
  - mcp__playwright__browser_navigate
  - mcp__playwright__browser_snapshot
  - mcp__playwright__browser_click
  - mcp__playwright__browser_fill_form
  - mcp__playwright__browser_take_screenshot
  - mcp__playwright__browser_console_messages
  - mcp__playwright__browser_network_requests
  - mcp__playwright__browser_wait_for
  - mcp__playwright__browser_hover
  - mcp__playwright__browser_close
  - mcp__acm-kubectl__clusters
  - mcp__acm-kubectl__kubectl
  - mcp__acm-kubectl__connect_cluster
  - mcp__acm-search__find_resources
  - mcp__acm-search__query_database
  - mcp__acm-search__get_database_stats
---

# ACM Console Test Case Generator

Subagent-orchestrated pipeline generating Polarion-ready test cases from JIRA tickets. Each investigation phase runs in an isolated subagent context, writes structured output to disk, and terminates -- preventing context pressure and recency bias. The orchestrator is thin routing logic only.

Read `${CLAUDE_SKILL_DIR}/references/pipeline-detail.md` for phase input schemas. Per-concern details are split for progressive loading:
- Phase 0: read `${CLAUDE_SKILL_DIR}/references/phase0-inputs.md` for credential resolution and MCP availability checks
- On validation failure: read `${CLAUDE_SKILL_DIR}/references/validation-protocol.md` for retry protocol
- Phase 1 (before creating run dir): read `${CLAUDE_SKILL_DIR}/references/run-directory.md` for artifact naming

## Pipeline Phases

Read `references/phase-gates.md` for gate rules and progress indicators.

**Subagent spawn discipline (all phases):** Each phase below names a `brief:` (a file under `${CLAUDE_SKILL_DIR}/references/agents/`). Do NOT read that brief into orchestrator context. Spawn the subagent with a prompt that tells IT to read the brief and follow it exactly, plus that phase's input from `pipeline-detail.md`. The orchestrator reads only the structured JSON/markdown outputs it needs for routing -- never the briefs.

**Model tiering (all phases):** Each spawn also names a `model:` -- pass it as the Agent tool's `model` param. Mechanical fetch/discovery/writing phases run on `sonnet`; the reasoning and gate phases (code-analysis, synthesis, quality-review) run on `opus`. If `CLAUDE_CODE_SUBAGENT_MODEL` is set in the environment it overrides these and forces one model on all subagents (savings lost, or a silent gate downgrade) -- leave it unset so the per-phase `model:` governs.

### Phase 0: Determine Inputs

Resolve before starting the pipeline:

1. **JIRA ID** (required): The ticket to generate a test case for (e.g., ACM-30459)
2. **ACM Version**: From JIRA fix_versions, or ask: "Which ACM version?"
3. **PR Number**: Auto-detect from JIRA description/comments, or ask if not found
4. **Area**: Auto-detect from PR file paths (governance, rbac, fleet-virt, clusters, search, applications, credentials, cclm, mtv)
5. **Cluster URL** (optional): Run `oc whoami --show-server 2>/dev/null`. If logged in, derive console URL via `oc get route console -n openshift-console -o jsonpath='{.spec.host}' 2>/dev/null`. If unavailable, ask or skip live validation. In headless mode (`-p`), auto-detect only.
6. **Console Credentials** (optional): Resolve via the priority cascade in `pipeline-detail.md#phase-0-credential-resolution`.
7. **MCP Availability Check**: Run the MCP probe described in `pipeline-detail.md#phase-0-mcp-availability-check`. If REQUIRED MCPs are unavailable, warn the user. If IMPORTANT MCPs are unavailable, warn and proceed.
8. **Model-tiering env check**: Run `echo "${CLAUDE_CODE_SUBAGENT_MODEL:-unset}"`. If it is set to any value, it overrides every per-phase `model:` below and forces one model on all subagents. Surface this to the user before proceeding: a cheaper value silently downgrades the Opus gate phases (code-analysis, synthesis, quality-review) -- weakening the correctness gate -- while an Opus value nullifies the Sonnet savings. Recommend leaving it unset (or `inherit` on v2.1.196+) so per-phase tiering governs.

If all inputs can be inferred from the JIRA ticket, proceed without asking.

### Phase 1: Gather Data + Investigate JIRA Story

Spawn the Phase 1 subagent (Agent tool, description: "Data Gathering + JIRA Investigation", model: sonnet, brief: `agents/data-gatherer.md`) with the Phase 1 input from `pipeline-detail.md`.

- `gather-output` validation FAIL: **stop the pipeline** (gather.py is deterministic -- failures indicate a script bug, not an LLM issue).
- `phase1-jira` validation FAIL: enter Retry Protocol (see `pipeline-detail.md`).

Read `gather-output.json` to fill in any unresolved inputs (PR number, area, repo). Record the run directory path.

Do NOT read `phase1-jira.json` into orchestrator context.
Show: "Phase 1 complete. Gathered N PRs, JIRA findings written to phase1-jira.json."

### Phase 2: Analyze PR Code Changes

Spawn the Phase 2 subagent (description: "Code Analysis", model: opus, brief: `agents/code-analyzer.md`) with the Phase 2 input from `pipeline-detail.md`.

If validation PASS: continue. If FAIL: enter Retry Protocol.

Show: "Phase 2 complete. Code analysis written to phase2-code.json."

### Phase 3: Discover UI Elements

Spawn the Phase 3 subagent (description: "UI Discovery", model: sonnet, brief: `agents/ui-discoverer.md`) with the Phase 3 input from `pipeline-detail.md`.

If validation PASS: continue. If FAIL: enter Retry Protocol.

Show: "Phase 3 complete. UI elements written to phase3-ui.json."

### Pre-Synthesis Readiness Check

Run the pre-synthesis validation (see `pipeline-detail.md`).

If PASS: continue to Phase 4.
If FAIL: **stop the pipeline**. Upstream phases already exhausted their retry attempts. Report the missing data to the user.

### Phase 4: Synthesize

Spawn the Phase 4 subagent (description: "Synthesis", model: opus, brief: `agents/synthesizer.md`) with the Phase 4 input from `pipeline-detail.md`.

If validation PASS: continue. If FAIL: enter Retry Protocol.

Show: "Phase 4 complete. Synthesized context written."

### Phase 5: Live Validation (conditional)

**Skip** if no cluster URL was resolved in Phase 0: "Skipping live validation -- no cluster available."

Spawn the Phase 5 subagent (description: "Live Validation", model: sonnet, brief: `agents/live-validator.md`) with the Phase 5 input from `pipeline-detail.md`.

Verify `phase5-live-validation.md` exists. Apply live validation corrections per `pipeline-detail.md#phase-5-live-validation-corrections`.

Show: "Phase 5 complete. Live validation written."

### Phase 6: Write Test Case

Spawn the Phase 6 subagent (description: "Test Case Writing", model: sonnet, brief: `agents/test-case-writer.md`) with the Phase 6 input from `pipeline-detail.md`.

If validation PASS: continue. If FAIL: enter Retry Protocol.

Show: "Phase 6 complete. Test case written."

### Phase 7: Quality Review (MANDATORY GATE)

Spawn the Phase 7 subagent (description: "Quality Review", model: opus, brief: `agents/quality-reviewer.md`) with the Phase 7 input from `pipeline-detail.md`.

Read the review output. Run programmatic enforcement (see `pipeline-detail.md`).

**If PASS:** proceed to Phase 8.

**If NEEDS_FIXES -- 3-tier escalation:**

**Tier 1 (inline MCP):** Parse BLOCKING issues. Make 1-3 targeted MCP calls (`set_acm_version`, `search_translations`, `get_component_source`) for correct values. Fix `test-case.md` via Edit. Spawn a NEW quality-reviewer subagent (model: opus, brief: `agents/quality-reviewer.md`). Re-run enforcement.

**Tier 2 (writer retry -- single cycle):** Spawn a NEW test-case-writer subagent (model: sonnet, brief: `agents/test-case-writer.md`) with `MODE: REVISION` and ONLY the reviewer's BLOCKING deltas (not the full review). Spawn a NEW quality-reviewer subagent (model: opus, brief: `agents/quality-reviewer.md`) and re-run enforcement. Run this writer+reviewer cycle at most once; if it still fails, go to Tier 3.

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
