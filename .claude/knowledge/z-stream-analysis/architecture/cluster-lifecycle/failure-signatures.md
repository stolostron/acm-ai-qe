# Cluster Lifecycle Failure Signatures

Known failure patterns for CLC-related test failures.

---

## INFRASTRUCTURE Patterns

### Managed Clusters NotReady
- **Error:** Various -- timeout waiting for cluster operations, "Transferred" not found, destroy button disabled
- **Pattern:** 5/6 managed clusters in NotReady/Unknown state, mass CLC test failures
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** Managed cluster connectivity issues affect all operations that require spoke interaction
- **Diagnostic:** `oc get managedclusters` -- check Available column
- **Impact:** VM scheduling, cluster transfer, addon health, policy compliance

### Hive Webhook Misconfigured
- **Error:** `failed calling webhook "clusterdeploymentvalidators"` (500 error)
- **Pattern:** All cluster creation/modification/deletion fails
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Explanation:** The webhook service is unreachable or CA bundle is corrupted. Hive operator manages this webhook, NOT MCH operator.
- **Diagnostic:** `oc get validatingwebhookconfiguration clusterdeploymentvalidators.admission.hive.openshift.io -o yaml`

### Application CRD Missing
- **Error:** `resource mapping not found for name: '<name>' -- applications.app.k8s.io`
- **Pattern:** `oc apply` fails on Application CRs but succeeds on namespaces/subscriptions
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Explanation:** The `applications.app.k8s.io` CRD is not registered. ACM installation incomplete.
- **Diagnostic:** `oc get crd applications.app.k8s.io`

### Corrupted Bash Environment on CI Runner
- **Error:** `/usr/bin/bash: which: syntax error` or `Error importing function definition for 'which'`
- **Pattern:** Tests that use `cy.exec()` with bash commands fail
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** CI runner's bash environment has a corrupted `which` function definition

## AUTOMATION_BUG Patterns

### Perspective Switcher Race Condition
- **Error:** `Expected to find element: [data-test-id="cluster-dropdown-toggle"]`
- **Pattern:** goToClusters() navigation fails on OCP 4.20+
- **Classification:** AUTOMATION_BUG (90% confidence)
- **Explanation:** Synchronous jQuery check races with async perspective switcher rendering
- **File:** `cypress/views/header.js` lines 94-113
- **Fix:** Replace `$body.find()` with `cy.get()` with timeout

### cluster-dropdown-toggle Selector Dead
- **Error:** `Expected to find element: [data-test-id="cluster-dropdown-toggle"]`
- **Pattern:** 8+ tests fail on same selector defined in header.js:106
- **Classification:** AUTOMATION_BUG (95% confidence)
- **Explanation:** This selector was removed from OCP 4.20+. Tests should use perspective-switcher-toggle.

### Non-Idempotent Namespace Creation
- **Error:** `oc create ns <name>` fails with "AlreadyExists"
- **Pattern:** Test uses `oc create ns` without `{failOnNonZeroExit: false}`
- **Classification:** AUTOMATION_BUG (90% confidence)
- **Fix:** Use `oc create ns <name> --dry-run=client -o yaml | oc apply -f -`

### Undefined Variable in Assertion
- **Error:** `expected '<h4>' to contain undefined`
- **Pattern:** Test passes uninitialized variable as expected text
- **Classification:** AUTOMATION_BUG (90% confidence)

### Overly Strict oc apply Assertion
- **Error:** `expected 'unchanged' to include 'configured'`
- **Pattern:** Test expects 'configured' but `oc apply` returns 'unchanged'
- **Classification:** AUTOMATION_BUG (90% confidence)
- **Fix:** Accept both 'configured' and 'unchanged' as success states

## PRODUCT_BUG Patterns

### Hive API Version Changed
- **Error:** 404 "the server could not find the requested resource" on cluster creation
- **Pattern:** ClusterDeployment API call uses wrong version
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** resource.ts changes hive.openshift.io/v1 to v1beta1 which doesn't exist
- **File:** `frontend/src/resources/resource.ts`

### Console Proxy Returns Fake 500
- **Error:** "Internal error occurred: admission webhook timed out"
- **Pattern:** Cluster creation fails at submit step with realistic error message
- **Classification:** PRODUCT_BUG (80% confidence) -- verify webhook actually exists first
- **Explanation:** proxy.ts intercepts ClusterDeployment POST and returns canned 500
- **File:** `backend/src/routes/proxy.ts`

### ManagedClusterAction 504 Timeout
- **Error:** Gateway Timeout after 12-second delay
- **Pattern:** Operations on managed clusters hang then fail
- **Classification:** INFRASTRUCTURE (70%) or PRODUCT_BUG (30%)
- **Explanation:** proxy.ts adds artificial 12s delay then returns 504 for MCA POST
- **File:** `backend/src/routes/proxy.ts`

### ClusterSet Transfer with Degraded Clusters
- **Error:** "Transferred" text not found in table cell
- **Pattern:** ClusterSet transfer appears to succeed but UI doesn't update
- **Classification:** INFRASTRUCTURE (if managed clusters NotReady) or PRODUCT_BUG (if transfer logic broken)
- **Diagnostic:** Check managed cluster health first. If degraded -> INFRASTRUCTURE.

### Pre-upgrade to Pre-update Rename
- **Error:** `Expected to find dt:contains('Pre-upgrade Ansible templates')`
- **Pattern:** 4+ automation template tests fail on same text
- **Classification:** AUTOMATION_BUG (95% confidence) -- intentional product text change
- **Explanation:** Product renamed "Pre-upgrade" to "Pre-update" in Ansible template labels. The test expects the old text.
- **Fix:** Update test expected text to "Pre-update"
