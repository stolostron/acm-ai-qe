# CLI-in-Test-Steps Rules

## Default Rule

Test steps are **UI-focused**. The tester interacts with the ACM Console UI (click, navigate, fill forms, observe results).

## When CLI Is Allowed in Test Steps

CLI (`oc`, `kubectl`, `curl`) is allowed mid-test ONLY for **backend validation**:

1. **Verify resource YAML state** after a UI action created/modified a resource
2. **Check config changes** that are not visible in the UI
3. **Verify API responses** for backend-only behavior
4. **Confirm no resource was created** (negative test for in-memory operations)

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
