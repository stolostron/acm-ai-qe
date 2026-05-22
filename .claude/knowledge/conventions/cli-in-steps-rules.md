# CLI-in-Test-Steps Rules

## Default Rule

Test steps are **UI-focused**. The tester interacts with the ACM Console UI (click, navigate, fill forms, observe results).

## When CLI Is Allowed in Test Steps

CLI (`oc`, `kubectl`, `curl`) is allowed ONLY for **backend validation**, and MUST be placed in a **dedicated step** — not embedded within a UI-focused step:

1. **Verify resource YAML state** after a UI action created/modified a resource
2. **Check config changes** that are not visible in the UI
3. **Verify API responses** for backend-only behavior
4. **Confirm no resource was created** (negative test for in-memory operations)

## Backend Validation Placement

Place CLI backend validation in a DEDICATED step titled "Verify [what] via CLI (Backend Validation)". Place these steps AFTER all UI steps so the test flow is: UI verification first, then backend cross-check.

**Why:** Embedding CLI in UI steps creates an unclear context switch (browser → terminal) that testers may miss. Separate steps allow precise pass/fail attribution and map cleanly to automation (browser tests vs shell tests).

## When CLI Backend Validation Is NOT Needed

Do NOT add a CLI backend validation step when UI steps already provide full coverage of the behavior. Specifically, omit CLI cross-checks when:

- The UI displays data derived from a backend source (metric, API, resource) and the UI steps already verify the data is correct (values, counts, labels)
- The test is purely about UI rendering, column behavior, or display logic — not about resource creation or mutation
- The CLI step would only confirm what the UI already shows (consistency check), rather than verifying something the UI cannot show

CLI backend validation adds value when:
- A UI action creates or modifies a backend resource (e.g., creating a policy, role assignment, or cluster) and you need to verify the resource was written correctly
- The UI shows a summary but the full state is only visible via CLI (e.g., resource YAML fields not exposed in UI)
- The test verifies a backend-only behavior with no UI representation

**Rule of thumb:** If the UI already shows the data and your steps verify it, a CLI step repeating the same check is redundant complexity.

## When CLI Is NOT Allowed in Test Steps

- As a substitute for navigating the UI
- To create resources that should be created via UI (use Setup for prerequisites)
- To delete resources mid-test (use Teardown)
- To search for resources when the test is NOT about Search UI

## Exception: Search UI Tests

When the test case specifically tests the Search UI feature, using Search in the console IS the test step (not CLI). For non-Search tests, avoid telling the tester to "search for the resource" -- use direct navigation instead.

## Examples

**Allowed** (backend validation):
```markdown
### Step 6: Verify Backend Resource State

1. Verify the MCRA was created correctly:
\`\`\`bash
oc get multiclusterroleassignment -n open-cluster-management-global-set -o yaml | grep "subject-name"
\`\`\`

**Expected Result:**
- MCRA exists with correct `spec.subject.name`
- Status shows `Applied: True`
```

**NOT Allowed** (UI substitute):
```markdown
### Step 3: Check Policy Status
1. Run: oc get policy test-policy -n default -o jsonpath='{.status.compliant}'
# Wrong -- should navigate to Governance > Policies > test-policy and verify status in UI
```
