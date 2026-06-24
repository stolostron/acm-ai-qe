# Evidence and Reporting

How evidence is captured, verdicts are computed, and the final validation report is structured.

## Evidence Capture Strategy

Evidence is captured at every significant point during execution to provide an audit trail:

```
┌───────────────────────────────────────────────────────────┐
│                    Per-Step Evidence                        │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Pre-action:   browser_snapshot → step-{i}-pre.txt       │
│       ↓                                                   │
│  [Actions execute]                                        │
│       ↓                                                   │
│  Post-action:  browser_snapshot → step-{i}-post.txt      │
│                browser_screenshot → step-{i}.png          │
│       ↓                                                   │
│  On failure:   browser_console_messages → errors.txt      │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Evidence Types

| Type | Format | Content | When Captured |
|------|--------|---------|---------------|
| Accessibility snapshot | `.txt` (YAML tree) | Full page DOM tree with roles, names, refs | Before and after each step |
| Screenshot | `.png` | Visual page capture | After each step (post-verification) |
| CLI output | `.txt` | Command stdout/stderr | After each setup/teardown/CLI step |
| Console errors | `.txt` | Browser JavaScript errors | On FAIL or BLOCKED verdicts |

### File Naming Convention

```
evidence/
  step-{N}-pre-snapshot.txt      # Before step N actions
  step-{N}-post-snapshot.txt     # After step N actions + verification
  step-{N}-screenshot.png        # Visual capture after step N
  step-{N}-{description}.png     # Named screenshots for key moments
  setup-output.txt               # All setup commands and outputs
  teardown-output.txt            # All teardown commands and outputs
  console-errors.txt             # Aggregated browser errors
```

## Verdict Computation

### Per-Step Verdict Logic

```
For step i:
  expected_results = step.expected_results[]
  results = []
  
  for each expected in expected_results:
    result = verify(expected, current_snapshot)
    results.append(result)  // PASS, FAIL, or MANUAL_CHECK
  
  if any result is FAIL:
    step_verdict = FAIL
  elif all results are PASS:
    step_verdict = PASS
  elif all results are (PASS or MANUAL_CHECK):
    step_verdict = MANUAL_CHECK
  
  // BLOCKED is set during action execution if elements not found
```

### Overall Verdict Logic

```
step_verdicts = [step_1_verdict, step_2_verdict, ..., step_N_verdict]

if all are PASS:
  overall = ALL_PASS
elif all are (PASS or MANUAL_CHECK) and no FAIL/BLOCKED:
  overall = ALL_PASS_WITH_MANUAL
elif setup_failed_critically:
  overall = SETUP_FAILED
elif environment_prerequisites_missing:
  overall = BLOCKED
elif all are FAIL or BLOCKED:
  overall = FAILED
else:
  pass_count = count(PASS in step_verdicts)
  total = len(step_verdicts)
  overall = PARTIAL_PASS (pass_count/total steps passed)
```

## Report Structure

The `validation-report.md` follows a fixed structure:

### Section 1: Header and Metadata

```markdown
# Validation Report: RHACM4K-XXXXX

| Field | Value |
|-------|-------|
| Polarion ID | RHACM4K-XXXXX |
| Title | [Test case title] |
| Area | [Applications / Governance / RBAC / ...] |
| Component | [Specific component] |
| Release | ACM [version] |
```

### Section 2: Environment

```markdown
## Environment

| Field | Value |
|-------|-------|
| Hub Cluster | [API URL] |
| Console URL | [Console URL] |
| ACM Version | [Detected version] |
| User | [Login identity] |
| Spoke Clusters | [Count and names, excluding local-cluster] |
| Execution Mode | [full / fail-fast] |
| Run Timestamp | [ISO timestamp] |
```

### Section 3: Prerequisites

```markdown
## Prerequisites

| Prerequisite | Status | Detail |
|-------------|--------|--------|
| [Name] | PRESENT / MISSING | [Specific finding] |
```

### Section 4: Setup Results

```markdown
## Setup Results

| Step | Command | Expected | Actual | Result |
|------|---------|----------|--------|--------|
| N | `command` | pattern | output | PASS/FAIL |
```

### Section 5: Step Results (Primary Table)

```markdown
## Test Step Results

| Step | Title | Verdict | Details |
|------|-------|---------|---------
| 1 | [Title] | **PASS** | [Brief summary] |
| 2 | [Title] | **FAIL** | [What went wrong] |
```

### Section 6: Failure Details

For each FAIL or BLOCKED step, a detailed breakdown:

```markdown
## Failure Details

### Step N: [Title] -- FAIL

**Action:** [What was attempted]
**Expected:** [What the test case says should happen]
**Actual:** [What actually happened]
**Evidence:** [evidence/step-N-post-snapshot.txt], [evidence/step-N-screenshot.png]
**Analysis:** [Why it might have failed -- stale test case? environment issue? product bug?]
```

### Section 7: Teardown Results

When teardown runs (ALL_PASS or `--always-teardown`):

```markdown
## Teardown Results

| Step | Command | Safety Check | Result |
|------|---------|-------------|--------|
| N | `command` | PASS (in registry) | PASS/FAIL |
```

When teardown is skipped (PARTIAL_PASS / FAILED / BLOCKED):

```markdown
## Teardown Results

**SKIPPED** -- resources preserved for debugging.

### Created Resources Still on Cluster

| Type | Name | Namespace | Cluster | Created In |
|------|------|-----------|---------|------------|
| namespace | test-push-preserve | - | hub | Phase 3, Setup cmd 4 |
| applicationset | test-push-preserve | openshift-gitops | hub | Phase 4, Step 2 |

### Manual Cleanup Commands

oc delete ns test-push-preserve --ignore-not-found
oc delete placement test-push-preserve-placement -n openshift-gitops --ignore-not-found
```

### Section 8: Overall Verdict

```markdown
## Overall Verdict

ALL_PASS (N/N steps)
```

### Section 9: Evidence Files

```markdown
## Evidence Files

| File | Description |
|------|-------------|
| `evidence/step-1-screenshot.png` | [What it shows] |
```

### Section 10: Notes

Optional observations, workarounds applied, known issues encountered.

## Terminal Summary Output

After writing the report, a condensed summary is displayed in the terminal:

```
VALIDATION COMPLETE
===================
Test Case: RHACM4K-XXXXX - [Title]
Environment: https://console.apps.hub.example.com
ACM Version: 2.17.0

Results:
  Step 1: [Title] ................... PASS
  Step 2: [Title] ................... PASS
  Step 3: [Title] ................... FAIL (reason)
  Step 4: [Title] ................... BLOCKED (reason)
  Step 5: [Title] ................... PASS

Overall: PARTIAL_PASS (3/5 steps)

Report:   runs/test-case-validator/RHACM4K-XXXXX/.../validation-report.md
Evidence: runs/test-case-validator/RHACM4K-XXXXX/.../evidence/
```

## Failure Analysis Patterns

When a step fails, the report includes an analysis suggesting the likely cause:

| Observed Failure | Likely Cause | Suggested Action |
|-----------------|-------------|-----------------|
| Expected text not found, similar text exists | Test case text is stale (wording changed in new version) | Update test case expected text |
| Element count differs (e.g., expected 9, found 8) | Feature partially deployed or column conditionally hidden | Check ACM version, feature gate, prerequisites |
| Sort order wrong | Sort implementation changed or test data doesn't have enough variety | Verify with manual inspection |
| Navigation produces 404 | Route changed in new ACM version | Check current routes via `acm-source` MCP |
| CLI output doesn't match pattern | Resource not created or different state | Verify setup completed successfully |
| Tooltip content differs | UI text updated in newer PRs | Check source code for current tooltip string |

## Run Retention

Runs are saved indefinitely under `runs/test-case-validator/`. Each Polarion ID has its own directory with timestamped subdirectories, allowing historical comparison:

```
runs/test-case-validator/RHACM4K-64019/
  RHACM4K-64019-2026-06-20T10-00-00/    # First run -- PARTIAL_PASS
  RHACM4K-64019-2026-06-23T14-30-00/    # Second run after fix -- ALL_PASS
```

This supports tracking whether a test case started passing after a product fix was deployed.
