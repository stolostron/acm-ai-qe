# Automation Failure Signatures

Known failure patterns for Ansible Automation tests.

---

## INFRASTRUCTURE Patterns

### AAP Operator Not Installed
- **Error:** Template dropdown empty, no automation templates available
- **Pattern:** All Ansible-related tests fail
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Diagnostic:** `oc get subscriptions.operators.coreos.com -n openshift-operators | grep aap`

### Ansible Tower Unreachable
- **Error:** `Ansible posthook is not triggered within time limit`
- **Pattern:** Hook execution tests timeout
- **Classification:** INFRASTRUCTURE (80% confidence)
- **Diagnostic:** Check TOWER_HOST connectivity from hub cluster

### Automation Template h1 Not Found
- **Error:** `Expected to find element: h1` in automation spec files
- **Pattern:** 7+ sequential tests fail identically (cascading navigation failure)
- **Classification:** AUTOMATION_BUG (90% confidence)
- **Explanation:** First test in the spec file has a navigation issue, cascading to all subsequent tests

## AUTOMATION_BUG Patterns

### Pre-upgrade Text Removed
- **Error:** `Expected to find dt:contains('Pre-upgrade Ansible templates')`
- **Pattern:** 4 tests fail on same text
- **Classification:** AUTOMATION_BUG (95% confidence)
- **Explanation:** Product renamed "Pre-upgrade" to "Pre-update". The test expects old text.
- **Fix:** Update expected text in test code

### Button Disabled for RBAC Role
- **Error:** Button has `pf-m-aria-disabled` attribute
- **Pattern:** RBAC role tests expect button to be enabled
- **Classification:** AUTOMATION_BUG (80% confidence)
- **Explanation:** RBAC role correctly disables the button; test expectation is wrong

## PRODUCT_BUG Patterns

### Ansible Tower Returns Empty Results
- **Error:** Template selection dropdown empty despite AAP operator being healthy
- **Pattern:** AAP CSV phase=Succeeded but no templates shown
- **Classification:** PRODUCT_BUG (80% confidence)
- **Explanation:** ansibletower.ts proxy intercepts and returns `{count:0, results:[]}` without contacting Tower
- **Diagnostic:** Check AAP operator health AND probe the console's ansibletower endpoint. If AAP healthy but endpoint returns empty -> PRODUCT_BUG.
- **File:** `backend/src/routes/ansibletower.ts`

### ClusterCurator SSE Events Dropped
- **Error:** Automation status doesn't update after hook execution
- **Pattern:** Curator status stale until manual page refresh
- **Classification:** PRODUCT_BUG (85% confidence)
- **Explanation:** events.ts eventFilter() drops ClusterCurator events
- **File:** `backend/src/routes/events.ts`
