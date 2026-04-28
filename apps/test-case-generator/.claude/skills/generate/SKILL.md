---
description: |
  Generate a Polarion-ready test case from a JIRA ticket using a 6-phase
  subagent pipeline: gather, parallel investigation (3 agents), synthesis,
  optional live validation, test case writing, mandatory quality review,
  and deterministic report generation.
when_to_use: |
  When the user wants to generate a test case from a JIRA ticket, or asks
  to run the pipeline, or says "generate", "create test case", "write test
  case for ACM-XXXXX", or provides a JIRA ticket and asks for test coverage.
argument-hint: "<JIRA_ID> [--version <VERSION>] [--pr <PR_NUMBER>] [--area <AREA>] [--skip-live] [--cluster-url <URL>] [--repo <REPO>]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Bash(python -m src.scripts.gather:*)
  - Bash(python -m src.scripts.log_phase:*)
  - Bash(python -m src.scripts.report:*)
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
  - mcp__acm-ui__set_acm_version
  - mcp__acm-ui__set_cnv_version
  - mcp__acm-ui__get_routes
  - mcp__acm-ui__search_translations
  - mcp__jira__get_issue
  - mcp__jira__search_issues
  - mcp__polarion__get_polarion_work_items
  - mcp__polarion__get_polarion_test_case_summary
  - mcp__polarion__check_polarion_status
---

# Generate a test case from a JIRA ticket

Usage: `/generate <JIRA_ID> [--version <VERSION>] [--pr <PR_NUMBER>] [--area <AREA>] [--skip-live] [--cluster-url <URL>] [--repo <REPO>]`

## Arguments

- `JIRA_ID` (required): The JIRA ticket ID (e.g., ACM-30459)
- `--version`: ACM version override (default: detected from JIRA fix_versions)
- `--pr`: PR number override (default: auto-detected from JIRA or search)
- `--area`: Area override (default: auto-detected from PR file paths)
- `--skip-live`: Skip live cluster validation
- `--cluster-url`: Console URL for live validation (e.g., https://console-openshift-console.apps.hub.example.com)
- `--repo`: Repository override (default: stolostron/console)

## Phase 0: Ask Questions and Determine Inputs

Before running the pipeline, check if critical information is missing:

1. If `--version` is not provided and cannot be detected from JIRA, ask: "Which ACM version?"
2. If the area is Fleet Virt, ask: "What CNV version on the spoke cluster?"
3. If `--skip-live` is not set and `--cluster-url` is not provided, ask: "Do you have a hub console URL for live validation, or should I skip it?"
4. If the JIRA ticket has multiple acceptance criteria with distinct flows, ask: "Which specific flow/scenario should this test case cover?"

If all info is available (from args or inferable from JIRA), proceed without asking.

Before executing the pipeline, read these supporting files:
- [phase-gates.md](phase-gates.md) -- Phase tracking format, gate rules, STOP checkpoints
- [synthesis-template.md](synthesis-template.md) -- Phase 2 synthesis template and scope gating

## Stage 1: Gather

```
[Phase 0] Determining area and inputs...
```

Run the gather script:
```bash
python -m src.scripts.gather $JIRA_ID [options from above]
```

Read the output to find the run directory path. Show a summary:
```
Stage 1 complete. Found PR #NNNN, N files changed. Area: [area]. Loaded N peer test cases.
```

## Phase 1: Parallel Investigation

```
[Phase 1] Launching 3 parallel investigation agents...
```

Launch three agents **in parallel** (do not wait for one to finish before starting the next):

### Agent A: Feature Investigator
- Input: JIRA ID from `gather-output.json`
- Agent file: `.claude/agents/feature-investigator.md`
- Output: FEATURE INVESTIGATION block (story, ACs, comments, linked tickets, existing Polarion coverage, test scenarios)

### Agent B: Code Change Analyzer
- Input: PR number, repo, ACM version from `gather-output.json`
- Agent file: `.claude/agents/code-change-analyzer.md`
- Output: CODE CHANGE ANALYSIS block (changed components, new UI elements, routes, translations, test scenarios)

### Agent C: UI Discovery
- Input: ACM version, CNV version (if Fleet Virt), feature name, area, cluster URL (if `--cluster-url` provided), credentials
- Agent file: `.claude/agents/ui-discovery.md`
- Output: UI DISCOVERY RESULTS block (selectors, translations, routes, wizard steps, live verification status)
- If `--cluster-url` was provided, include the cluster URL and credentials in the agent prompt so it can perform Step 9 (live browser verification). The agent will verify that discovered UI elements actually render on the cluster.

Wait for all three to return. **Save each agent's full output to the run directory:**

```
Write agent A output -> <run-dir>/phase1-feature-investigation.md
Write agent B output -> <run-dir>/phase1-code-change-analysis.md
Write agent C output -> <run-dir>/phase1-ui-discovery.md
```

Show a brief summary of what each discovered.

## Phase 2: Synthesize

```
[Phase 2] Synthesizing investigation results...
```

Read [synthesis-template.md](synthesis-template.md) for the SYNTHESIZED CONTEXT block template, scope gating rules, and AC vs implementation cross-reference procedure.

After building the synthesized context, **save it to the run directory:**

```
Write synthesized context -> <run-dir>/phase2-synthesized-context.md
```

Show the plan to the user.

**STOP checkpoint:**
```
Investigation complete. [N] test scenarios identified. Starting [live validation | test case writing].
```

## Phase 3: Live Validation (conditional)

If `--skip-live` is NOT set and a cluster URL is available:

```
[Phase 3] Running live validation...
```

- Launch the live-validator agent with: console URL, feature path, steps to verify
- Agent file: `.claude/agents/live-validator.md`
- Output: LIVE VALIDATION RESULTS (confirmed behavior, discrepancies, screenshots)
- **Save the agent's full output:** `Write -> <run-dir>/phase3-live-validation.md`

If `--skip-live` IS set or no cluster URL:
```
[Phase 3] Skipping live validation. (reason: [--skip-live | no cluster URL])
```
Write a brief note: `Write "Live validation skipped: [reason]" -> <run-dir>/phase3-live-validation.md`

## Phase 4: Generate Test Case

```
[Phase 4] Writing test case...
```

Launch the test-case-generator agent with:
- Run directory path
- Synthesized context from Phase 2 (merged investigation outputs)
- Live validation results from Phase 3 (if available)

Agent file: `.claude/agents/test-case-generator.md`

Output: `test-case.md` and `analysis-results.json` written to the run directory.

**STOP checkpoint:**
```
Test case written: [filename] ([N] steps, [complexity]). Running quality review.
```

## Phase 4.5: Quality Review (MANDATORY GATE)

```
[Phase 4.5] Running quality review...
```

Launch the quality-reviewer agent with:
- Path to the generated `test-case.md`
- ACM version
- Area

Agent file: `.claude/agents/quality-reviewer.md`

**Review loop with enforcement:**

After the quality reviewer returns, **save its full output:**
```
Write reviewer output -> <run-dir>/phase4.5-quality-review.md
```

Then BEFORE accepting the verdict:

1. **Check the JSON verification block.** The reviewer's output MUST start with a JSON block containing `mcp_verifications`. Parse it and check:
   - `mcp_verifications` array has at least 3 entries
   - `ac_vs_implementation_checked` is true
   - `knowledge_file_cross_referenced` is true
   If the JSON block is missing or any check fails, override the verdict to `NEEDS_FIXES` and re-launch with: "Your review is missing mandatory MCP verifications. You MUST: (1) call at least 3 MCP tools and list results in the JSON block, (2) check AC vs implementation, (3) cross-reference knowledge file."

2. If verdict = **PASS** (and JSON checks pass) -> proceed to Stage 3
3. If verdict = **NEEDS_FIXES**:
   a. Fix all BLOCKING issues in the test case markdown
   b. Re-launch quality-reviewer with the same inputs PLUS the previous review output (so it can use the re-review protocol to check only previously reported issues)
   c. Repeat until PASS (max 3 iterations)
4. If still failing after 3 iterations, show the remaining issues to the user

```
Quality review PASSED. Generating reports.
```

## Phase Telemetry

After each AI phase completes, run `log_phase` to write a telemetry entry to `pipeline.log.jsonl`:

```bash
# After Phase 1:
python -m src.scripts.log_phase <run-dir> phase_1 --agents 3

# After Phase 2:
python -m src.scripts.log_phase <run-dir> phase_2 --scenarios N

# After Phase 3:
python -m src.scripts.log_phase <run-dir> phase_3 --live true --cluster_version 2.17.x
# Or if skipped:
python -m src.scripts.log_phase <run-dir> phase_3 --live false --reason skipped

# After Phase 4:
python -m src.scripts.log_phase <run-dir> phase_4 --steps N --complexity medium

# After Phase 4.5:
python -m src.scripts.log_phase <run-dir> phase_4_5 --verdict PASS --mcp_verifications N --iterations 1
```

This is a deterministic Python script — it ALWAYS writes, regardless of what the AI agent does. It fills the telemetry gap between Stage 1 (gather.py) and Stage 3 (report.py).

## Stage 3: Report

```
[Stage 3] Generating reports...
```

Run the report script:
```bash
python -m src.scripts.report <run-directory>
```

Show the summary including:
- Structural validation result (PASS/FAIL)
- Polarion HTML generation status
- Pipeline timing
- Output file paths

```
Pipeline complete.
  Test case:  runs/ACM-30459/.../test-case.md
  Setup HTML: runs/ACM-30459/.../test-case-setup.html
  Steps HTML: runs/ACM-30459/.../test-case-steps.html
  Summary:    runs/ACM-30459/.../SUMMARY.txt
```
