# Verdict Format -- Report Structure and Run Directory Layout

How to structure the validation report, record evidence, and determine verdicts.

## Run Directory Layout

```
runs/test-case-validator/<POLARION_ID>/<POLARION_ID>-<TIMESTAMP>/
  validation-report.md          # Primary deliverable: full report
  execution-plan.json           # Parsed test case structure (Phase 1 output)
  environment-readiness.md      # Phase 2 readiness table
  evidence/
    step-1-pre-snapshot.txt     # Accessibility snapshot before step 1
    step-1-post-snapshot.txt    # Accessibility snapshot after step 1
    step-1-screenshot.png       # Visual screenshot after step 1
    step-2-pre-snapshot.txt
    step-2-post-snapshot.txt
    step-2-screenshot.png
    ...
    setup-output.txt            # Combined setup command outputs
    teardown-output.txt         # Combined teardown command outputs
    console-errors.txt          # Browser console errors (if any)
```

Timestamp format: `YYYY-MM-DDTHH-MM-SS` (e.g., `2026-06-23T14-30-00`)

## Per-Step Verdict Rules

### PASS

All conditions must be true:
- Every action in the step executed without error
- Every bullet in Expected Result was confirmed by evidence
- No unhandled browser console errors occurred during the step

### FAIL

Any of these conditions:
- An expected result was contradicted by the evidence (text not found, wrong count, wrong order)
- An action produced an error state (form validation error, server error page)
- CLI command returned non-zero exit code with output contradicting expected

Record: what was expected vs what was actually found.

### BLOCKED

Any of these conditions:
- A required element could not be found in the snapshot after retries
- The page returned an error (403, 404, 500) instead of the expected content
- A prerequisite for the step was not met (previous step's state change failed)
- Navigation target does not exist or redirects to an unexpected page
- Timeout: waited 10s+ for an element that never appeared

Record: what was attempted and what prevented execution.

### MANUAL_CHECK

Any of these conditions:
- Expected result uses subjective language that cannot be programmatically verified
- Verification requires visual comparison without a baseline image
- Expected result references behavior that requires human judgment (e.g., "UI is responsive")
- Evidence was captured but automated comparison is inconclusive

Record: screenshot captured, what needs human review, and why automated verification is insufficient.

## Overall Verdict Rules

| Condition | Overall Verdict | Description |
|-----------|----------------|-------------|
| All steps PASS | `ALL_PASS` | Test case fully validated |
| All steps PASS or MANUAL_CHECK (no FAIL/BLOCKED) | `ALL_PASS_WITH_MANUAL` | Passed but some steps need human confirmation |
| >=1 FAIL, rest are PASS/MANUAL_CHECK | `PARTIAL_PASS` | Some steps failed, include count: "(N/M steps passed)" |
| Environment prerequisites missing | `BLOCKED` | Cannot execute -- environment not ready |
| All steps FAIL or BLOCKED | `FAILED` | Test case does not pass on this environment |
| Setup commands failed critically | `SETUP_FAILED` | Could not establish test preconditions |

## Validation Report Format

```markdown
# Validation Report: RHACM4K-XXXXX

**Test Case:** [Full title from the test case]
**Validated:** [timestamp]
**Environment:** [cluster URL]
**ACM Version:** [detected version]
**User:** [login identity]
**Execution Mode:** [full | fail-fast]

---

## Environment Readiness

| Prerequisite | Status | Detail |
|-------------|--------|--------|
| ACM version match | PRESENT | 2.17.0 (test requires 2.17) |
| cluster-admin access | PRESENT | kube:admin |
| multicluster-observability | PRESENT | Ready |
| managed clusters (>=2) | PRESENT | 3 clusters available |

**Readiness Verdict:** READY

---

## Setup Results

| # | Command | Expected | Actual | Result |
|---|---------|----------|--------|--------|
| 1 | `oc get mch ... -o jsonpath=...` | Version: 2.17.x | Version: 2.17.0 | PASS |
| 2 | `oc get mch ... -o jsonpath=...` | Phase: Running | Phase: Running | PASS |
| ... | ... | ... | ... | ... |

**Console Login:** PASS (kubeadmin via htpasswd)

---

## Step Results

| Step | Title | Verdict | Detail |
|------|-------|---------|--------|
| 1 | Verify GPU Count Column Appears | PASS | All 3 expected results confirmed |
| 2 | Verify GPU Count Values | PASS | All 4 expected results confirmed |
| 3 | Verify Tooltip Content | FAIL | Tooltip text mismatch (see below) |
| 4 | Verify Observability Link | BLOCKED | Tooltip did not open (prerequisite: Step 3) |
| 5 | Verify Numeric Sorting | PASS | Ascending and descending confirmed |
| 6 | Verify Second Cluster | PASS | Consistent behavior on cluster-2 |
| 7 | Verify Without Launch-Link | MANUAL_CHECK | Annotation removal requires approval |

---

## Failure Details

### Step 3: Verify Tooltip Content -- FAIL

**Action:** Clicked tooltip trigger adjacent to "GPU count" header
**Expected:** Tooltip text reads: "The count of GPUs on a Node is gathered from the "node_accelerator_card_info" metric..."
**Actual:** Tooltip text reads: "GPU count is derived from the node_accelerator_card_info metric..."
**Evidence:** [evidence/step-3-post-snapshot.txt], [evidence/step-3-screenshot.png]
**Analysis:** Text content differs from test case expectation. The test case may need updating to match current implementation.

### Step 4: Verify Observability Link -- BLOCKED

**Reason:** Tooltip from Step 3 did not display the expected content structure. Unable to locate "Observability metrics" link element.
**Evidence:** [evidence/step-4-pre-snapshot.txt]

---

## Teardown Results

| # | Command | Result |
|---|---------|--------|
| 1 | Restore launch-link annotation | PASS |
| 2 | Verify restoration | PASS |

---

## Summary

**Overall Verdict:** PARTIAL_PASS (5/7 steps passed)

**Breakdown:**
- PASS: 5 steps
- FAIL: 1 step (Step 3)
- BLOCKED: 1 step (Step 4)
- MANUAL_CHECK: 0 steps

**Recommendations:**
1. Step 3: Verify tooltip text against current source code -- may have been updated since test case was written
2. Step 4: Will likely pass once Step 3's expected text is corrected (tooltip DID open, content was different)

**Report saved to:** runs/test-case-validator/RHACM4K-64019/RHACM4K-64019-2026-06-23T14-30-00/validation-report.md
**Evidence directory:** runs/test-case-validator/RHACM4K-64019/RHACM4K-64019-2026-06-23T14-30-00/evidence/
```

## Evidence File Formats

### Snapshot Files (`.txt`)

Raw accessibility tree output from `browser_snapshot()`. Contains:
- Page URL
- Element tree with roles, names, values, and ref IDs
- Text content visible on page

### Screenshot Files (`.png`)

Binary PNG from `browser_take_screenshot()`. One per step (post-action state).

### Output Files

- `setup-output.txt`: Each setup command followed by its output, separated by `---`
- `teardown-output.txt`: Same format for teardown
- `console-errors.txt`: Any JavaScript errors captured via `browser_console_messages()`

## Execution Plan JSON Schema

Saved as `execution-plan.json` in the run directory for reproducibility:

```json
{
  "polarion_id": "RHACM4K-64019",
  "title": "GPU Count Column in Cluster Nodes Table",
  "area": "Clusters",
  "release": "2.17",
  "entry_point": {
    "path": "Infrastructure > Clusters > Cluster list > [cluster name] > Nodes",
    "route": "/multicloud/infrastructure/clusters/details/:namespace/:name/nodes"
  },
  "setup": {
    "prerequisites": [
      { "text": "ACM 2.17.x hub cluster", "check_type": "acm_version", "expected": "2.17" }
    ],
    "commands": [
      { "label": "Verify ACM 2.17+", "command": "oc get mch ...", "expected_pattern": "Version: 2.17.*", "is_state_changing": false }
    ]
  },
  "steps": [
    {
      "number": 1,
      "title": "Verify GPU Count Column Appears With Observability",
      "actions": [
        { "index": 1, "text": "Log into the ACM console as cluster-admin", "type": "UI_ACTION" }
      ],
      "expected_results": [
        "The Nodes table displays 9 columns..."
      ],
      "classification": "UI_ACTION",
      "has_state_change": false
    }
  ],
  "teardown": {
    "commands": [
      { "label": "Restore annotation", "command": "oc annotate ...", "expected_pattern": "annotated", "is_state_changing": true }
    ]
  }
}
```
