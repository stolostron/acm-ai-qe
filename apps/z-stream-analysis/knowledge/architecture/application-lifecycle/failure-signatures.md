# Application Lifecycle Failure Signatures

Known failure patterns for ALC-related test failures.

---

## INFRASTRUCTURE Patterns

### applications.app.k8s.io CRD Missing
- **Error:** `resource mapping not found for name: '<name>' -- applications.app.k8s.io`
- **Pattern:** `oc apply` succeeds for namespaces/subscriptions but fails on Application CR
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Explanation:** The Application CRD is not registered on the cluster. ACM installation is incomplete.
- **Diagnostic:** `oc get crd applications.app.k8s.io`
- **Impact:** Affects all tests that create Application CRs via CLI

### ApplicationSet CRD Missing
- **Error:** ArgoCD appset operations fail, expected routes never appear
- **Pattern:** ArgoCD-specific tests fail but non-ArgoCD tests pass
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Diagnostic:** `oc get crd applicationsets.argoproj.io`

### Subscription Reconciliation Timeout
- **Error:** `subscription is not ready within time limit` or `Route is not ready within time limit`
- **Pattern:** Subscription-based deployment tests timeout
- **Classification:** Depends on controller health — see disambiguation below
- **Diagnostic:** `oc get pods -n ocm -l app=multicluster-operators-hub-subscription`
- **Disambiguation:**
  - If subscription-controller pod is **unhealthy** (CrashLooping, not Running, pending): **INFRASTRUCTURE** (80% confidence) — controller can't reconcile due to environment issue
  - If subscription-controller pod is **healthy** (Running, Ready) but subscriptions still not reconciling: **PRODUCT_BUG** (80% confidence) — likely ACM-32244 (timestamp comparison bug causes controller to skip reconciliation). See `known_jira_bugs` in `knowledge/failure-patterns.yaml`
  - If external channel endpoint is unreachable (Minio, Git, Helm repo down): **INFRASTRUCTURE** — see external service signatures below

### ArgoCD Sync Stuck
- **Error:** Expected route/resource never appears within timeout
- **Pattern:** ArgoCD appset tests timeout waiting for deployed resources
- **Classification:** INFRASTRUCTURE (80% confidence)
- **Diagnostic:** `oc get application -n openshift-gitops -o yaml | grep syncStatus`

### Ansible Tower Unreachable
- **Error:** `Ansible posthook is not triggered within time limit`
- **Pattern:** Ansible integration tests timeout
- **Classification:** INFRASTRUCTURE (80% confidence)
- **Explanation:** Tower host not reachable or 'Demo Workflow Template' doesn't exist
- **Diagnostic:** Check TOWER_HOST connectivity from hub
- **Version check:** If AAP operator >= 2.5 and test uses workflow job template, reclassify as PRODUCT_BUG (see `knowledge/version-constraints.yaml`)

### External Object Storage (Minio) Unreachable
- **Error:** `subscription is not ready within time limit` with objectBucket channel type
- **Pattern:** Object Storage subscription tests timeout; non-objectstorage tests in the same suite pass. Console log may contain `minio.*connection refused` or `objectstore.*fail`
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Explanation:** External Minio server (typically on a different cluster, e.g., `hivemind-b`) is down or unreachable. The subscription controller cannot pull content from the objectBucket channel.
- **Diagnostic:** Check `OBJECTSTORE_PRIVATE_URL` from Jenkins parameters; search console log for `minio`, `objectstore`, or `S3` connection errors
- **Key indicator:** Tests creating objectBucket channels fail, but Git/Helm channel tests pass

### External Gogs Git Server Unreachable
- **Error:** `failed to push to testrepo Git repository` or `SSL certificate problem: self signed certificate in certificate chain`
- **Pattern:** Git-based subscription tests fail at setup (before test assertions), Helm channel tests pass
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Explanation:** External Gogs Git server used for test repos is down or has SSL certificate issues. CI runner deploys Gogs but it may fail to start or have cert chain problems.
- **Diagnostic:** Search console log for `gogs`, `failed to push`, `SSL certificate problem`; check if `failed to create testrepo` or `User already exists` errors appear

### External MTLS Test Environment Setup Failure
- **Error:** `MTLS Test Environment setup failure or already operational`
- **Pattern:** mTLS/certificate-related tests fail at setup phase, non-mTLS tests pass
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Explanation:** MTLS test environment could not be established. The Gogs server with custom TLS certs failed to initialize, so mTLS subscription tests have no Git endpoint to pull from.
- **Diagnostic:** Search console log for `MTLS Test Environment setup failure`, `SSL certificate problem`, `self signed certificate`

### Prometheus Metrics Not Configured
- **Error:** `Timed out retrying` on histogram/metrics tests
- **Pattern:** ACM Alerts tests for metric histograms timeout
- **Classification:** INFRASTRUCTURE (80% confidence)
- **Explanation:** ServiceMonitor for ALC metrics not deployed or Prometheus not scraping
- **Diagnostic:** `oc get servicemonitor -n ocm | grep subscription`

## AUTOMATION_BUG Patterns

### cy.readFile on Directory (EISDIR)
- **Error:** `cy.readFile('cypress/downloads/') failed — EISDIR: illegal operation on a directory`
- **Pattern:** CSV export test reads directory instead of file
- **Classification:** AUTOMATION_BUG (95% confidence)
- **Fix:** Change `cy.readFile('cypress/downloads/')` to `cy.readFile('cypress/downloads/<file>.csv')`

### PF6 Menu Portal Visibility
- **Error:** `cy.click() failed because element has visibility:hidden` on `.pf-v6-c-menu__item-text`
- **Pattern:** Menu item clicks fail in ALC tests using `.within()` scope
- **Classification:** AUTOMATION_BUG (90% confidence)
- **Explanation:** PF6 menu portals render outside `.within()` scope
- **Fix:** Use `{ withinSubject: null }` -- pattern already exists at common.js line 327

### Button Text Mismatch
- **Error:** `Expected to find content: 'search channel' within the selector: 'button'`
- **Pattern:** UI button text changed but test expects old text
- **Classification:** AUTOMATION_BUG (75% confidence)

### Cascading Test Dependency
- **Error:** `oc delete subscription <name>` fails with NotFound or `oc project <ns>` fails
- **Pattern:** Test depends on resource created by prior test that failed
- **Classification:** NO_BUG (if cascading from prior test) or AUTOMATION_BUG (if test isolation issue)

## PRODUCT_BUG Patterns

### Application Health Status Inverted
- **Error:** Healthy apps show Unhealthy indicator, vice versa
- **Pattern:** Health assertions fail across all applications
- **Classification:** PRODUCT_BUG (90% confidence)
- **File:** `backend/src/routes/aggregators/applications.ts`

### Application Count Inflated
- **Error:** App count assertion fails (expected N, got N+3)
- **Pattern:** Count is consistently 3 higher than actual
- **Classification:** PRODUCT_BUG (90% confidence)
- **File:** `backend/src/routes/aggregators/statuses.ts`

### Ansible Tower Returns Empty Results
- **Error:** Template selection dropdown is empty
- **Pattern:** Ansible automation tests can't select job templates
- **Classification:** PRODUCT_BUG (80% confidence) -- if AAP operator is healthy
- **Explanation:** ansibletower.ts proxy intercepts and returns {count:0, results:[]}
- **File:** `backend/src/routes/ansibletower.ts`
