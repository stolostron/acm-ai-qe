# Console Failure Signatures

Known failure patterns for console-related test failures.

---

## INFRASTRUCTURE Patterns

### Blank Page (no-js)
- **Error:** HTML contains `class="no-js"` or `about:blank`
- **Pattern:** Page loads but JavaScript never executes
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Explanation:** Either IDP authentication failed (non-admin users stuck on login form) or the console plugin failed to load (the OCP console can't reach the ACM console service)
- **Sub-classification:** If admin user gets blank page -> likely timing issue (AUTOMATION_BUG). If non-admin IDP user -> likely IDP/OAuth configuration (INFRASTRUCTURE).
- **Diagnostic:** Check if same page works with kubeadmin. If yes -> IDP issue. If no -> console service issue.

### Console Pod CrashLoopBackOff
- **Error:** Various -- pages timeout, elements not found
- **Pattern:** Multiple diverse tests fail simultaneously
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Explanation:** Console pods are crashing, possibly due to resource limits (CPU throttle), bad image, or cert issues
- **Diagnostic:** `oc get pods -n ocm | grep console` -- check restarts and status

### Console Plugin Not Loaded
- **Error:** ACM navigation items missing (Fleet Management, Clusters, etc.)
- **Pattern:** OCP console works but ACM features absent
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** The ConsolePlugin CR for ACM is not registered or the console service is unreachable
- **Diagnostic:** `oc get consoleplugin acm -o yaml`

## AUTOMATION_BUG Patterns

### OCP Perspective Switcher Race Condition
- **Error:** `Expected to find element: [data-test-id="cluster-dropdown-toggle"]`
- **Pattern:** Navigation to clusters page fails on OCP 4.20+
- **Classification:** AUTOMATION_BUG (90% confidence)
- **Explanation:** header.js openMenu() uses synchronous `$body.find()` for perspective-switcher-toggle. On OCP 4.20+, the element hasn't rendered when the one-shot jQuery check runs. Falls through to else branch looking for cluster-dropdown-toggle which was removed.
- **File:** `cypress/views/header.js` lines 94-113
- **Fix:** Replace `$body.find()` with `cy.get('[data-test-id="perspective-switcher-toggle"]', { timeout: 30000 })`

### Cascading After-All Hook
- **Error:** Test name starts with `"after all" hook for "RHACM4K-..."`
- **Pattern:** Cleanup hook fails because a prior test left state corrupted
- **Classification:** NO_BUG (95% confidence)
- **Explanation:** The after-all hook is a cleanup step, not an independent test. It failed because the actual test before it already failed.
- **Fix:** Fix the root cause test; the hook will pass automatically
- **Note:** "before all" hooks are NOT cascading -- they represent genuine setup failures

### PF6 Component Type Mismatch
- **Error:** `expected to find element with role "checkbox"` but finds `role="switch"`
- **Pattern:** PF5->PF6 migration changed component types
- **Classification:** AUTOMATION_BUG (85% confidence)
- **Explanation:** PatternFly 6 changed some components (checkbox->switch, textbox->search role)
- **Fix:** Update Cypress assertion to match new PF6 component type

## PRODUCT_BUG Patterns

### SSE Event Dropping
- **Error:** `expected to find content 'X' within the element: <td>` (element exists but data not in it)
- **Pattern:** Resource created via API but UI table doesn't show it. Manual refresh reveals the change.
- **Classification:** PRODUCT_BUG (85% confidence)
- **Explanation:** events.ts eventFilter() silently drops events for specific resource types (ManagedClusterSet, MulticlusterRoleAssignment, ClusterCurator)
- **Diagnostic:** Check if `console_search.found = true` (selector exists in product). If yes AND element not rendered, suspect SSE data delivery issue.
- **File:** `backend/src/routes/events.ts`

### Username Reversed
- **Error:** RBAC tests timeout at login -- "Unable to find User menu" after 2 minutes
- **Pattern:** Non-admin IDP users can't log in through the console
- **Classification:** PRODUCT_BUG (80% confidence)
- **Explanation:** username.ts reverses the username parts (kube:admin -> admin:kube)
- **Diagnostic:** Compare `/api/username` response against `oc whoami`. If they differ -> PRODUCT_BUG.
- **File:** `backend/src/routes/username.ts`

### Hub Metadata Wrong
- **Error:** Features conditional on hub name or observability behave incorrectly
- **Pattern:** Subtle rendering issues across multiple pages
- **Classification:** PRODUCT_BUG (75% confidence)
- **Explanation:** hub.ts appends "-replica" to hub name and/or inverts observability flag
- **File:** `backend/src/routes/hub.ts`

### Application Health Inverted
- **Error:** Healthy apps show as Unhealthy, Unhealthy apps show as Healthy
- **Pattern:** Application status indicators are wrong across all apps
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** applications.ts inverts the health status logic
- **File:** `backend/src/routes/aggregators/applications.ts`

### Application Count Inflated
- **Error:** Application count is 3 higher than actual number
- **Pattern:** Assertion on exact application count fails
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** statuses.ts adds 3 to authorizedItems.length
- **File:** `backend/src/routes/aggregators/statuses.ts`

### Proxy Returns Fake Error
- **Error:** ClusterDeployment creation fails with "admission webhook timed out"
- **Pattern:** 500 error on cluster creation submit step
- **Classification:** PRODUCT_BUG (if console proxy is intercepting) or INFRASTRUCTURE (if actual webhook issue)
- **Diagnostic:** Check if the webhook service exists: `oc get svc -n hive`. If exists -> console proxy intercepting (PRODUCT_BUG). If missing -> genuine webhook issue (INFRASTRUCTURE).
- **File:** `backend/src/routes/proxy.ts`
