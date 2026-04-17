# /generate -- Generate a test case from a JIRA ticket

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
- Input: ACM version, CNV version (if Fleet Virt), feature name, area
- Agent file: `.claude/agents/ui-discovery.md`
- Output: UI DISCOVERY RESULTS block (selectors, translations, routes, wizard steps)

Wait for all three to return. Show a brief summary of what each discovered.

## Phase 2: Synthesize

```
[Phase 2] Synthesizing investigation results...
```

Merge all three agent outputs into a single **SYNTHESIZED CONTEXT** block. This block is the primary input to Phase 4 (test-case-generator agent). Format:

```
SYNTHESIZED CONTEXT
===================

--- FEATURE INVESTIGATION ---
[paste full output from feature-investigator agent]

--- CODE CHANGE ANALYSIS ---
[paste full output from code-change-analyzer agent]

--- UI DISCOVERY RESULTS ---
[paste full output from ui-discovery agent]

--- TEST PLAN ---
Scenarios: [N]
Steps: [estimated count, typically 5-10 for medium complexity]
Setup: [prerequisites, test users, resources needed]
Per-step validations: [what each step validates — UI action + expected result]
CLI checkpoints: [where backend validation is needed mid-test]
Teardown: [resources to clean up]

Conflict resolution (if agents disagree):
- UI elements (labels, routes, selectors): trust UI Discovery (reads source directly)
- Business requirements (ACs, scope): trust Feature Investigator (reads JIRA)
- What changed (files, diff): trust Code Change Analyzer (reads the diff)
```

The TEST PLAN section is written by you (the orchestrator) based on the three investigation blocks. Show the plan to the user.

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

If `--skip-live` IS set or no cluster URL:
```
[Phase 3] Skipping live validation. (reason: [--skip-live | no cluster URL])
```

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

**Review loop:**
1. If verdict = **PASS** -> proceed to Stage 3
2. If verdict = **NEEDS_FIXES**:
   a. Fix all BLOCKING issues in the test case markdown
   b. Re-launch quality-reviewer with the same inputs PLUS the previous review output (so it can use the re-review protocol to check only previously reported issues)
   c. Repeat until PASS (max 3 iterations)
3. If still failing after 3 iterations, show the remaining issues to the user

```
Quality review PASSED. Generating reports.
```

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
