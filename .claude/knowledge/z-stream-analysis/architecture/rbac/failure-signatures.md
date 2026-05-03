# RBAC Failure Signatures

Known failure patterns for RBAC-related test failures.

---

## INFRASTRUCTURE Patterns

### IDP Authentication Failure
- **Error:** HTML contains `data-test-id="login"` or `class="no-js"` for non-admin users
- **Pattern:** All non-admin IDP user tests fail with blank page or login stuck
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Explanation:** IDP (HTPasswd/LDAP) not configured or not functional on the cluster
- **Diagnostic:** `oc get oauth cluster -o jsonpath='{.spec.identityProviders}'`

### MCRA/ClusterPermission CRD Missing
- **Error:** "the server doesn't have a resource type multiclusterroleassignments"
- **Pattern:** All role assignment tests fail
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Explanation:** FG-RBAC CRDs not registered (fine-grained-rbac not enabled in MCH)
- **Diagnostic:** `oc get crd multiclusterroleassignments.rbac.open-cluster-management.io`

## AUTOMATION_BUG Patterns

### OUIA Component ID Not Found
- **Error:** `Expected to find element: tr[data-ouia-component-id='clc-e2e-hub-view']`
- **Pattern:** Test uses OUIA ID that was never in the product
- **Classification:** AUTOMATION_BUG (95% confidence)
- **Diagnostic:** `console_search.found = false`, `element_never_existed = true`

### Undefined Variable in RBAC Assertion
- **Error:** `expected '<h4>' to contain undefined`
- **Pattern:** Test variable not initialized in clusterSet_rbac.spec.js
- **Classification:** AUTOMATION_BUG (90% confidence)

## PRODUCT_BUG Patterns

### Subject Name Corruption
- **Error:** Permissions don't work for the intended user after wizard completion
- **Pattern:** MCRA created successfully but ClusterPermission targets wrong user
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** roleAssignmentWizardHelper.ts appends '-system' to subject name
- **File:** `frontend/src/wizards/RoleAssignment/roleAssignmentWizardHelper.ts`

### MCRA SSE Events Dropped
- **Error:** Role assignment created but table doesn't update. Manual refresh shows it.
- **Pattern:** `expected to find content 'X' within the element: <td>` -- element exists but data not in it
- **Classification:** PRODUCT_BUG (85% confidence)
- **Explanation:** events.ts eventFilter() silently drops MCRA events
- **File:** `backend/src/routes/events.ts`

### ManagedClusterSet SSE Events Dropped
- **Error:** ClusterSet created but table doesn't update
- **Pattern:** Same stale UI pattern as MCRA event dropping
- **Classification:** PRODUCT_BUG (85% confidence)
- **File:** `backend/src/routes/events.ts`

### Username Reversed
- **Error:** RBAC tests timeout at login -- "Unable to find User menu" after 2 minutes
- **Pattern:** Non-admin IDP users can't log in through console
- **Classification:** PRODUCT_BUG (80% confidence)
- **Explanation:** username.ts reverses kube:admin to admin:kube
- **Diagnostic:** Compare `/api/username` response vs `oc whoami`
- **File:** `backend/src/routes/username.ts`
