---
type: failures
subsystem: install
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - architecture/install/architecture.md
  - versions/acm-2x-to-5x-changes.md
version_notes:
  - "CSV and namespace references updated for ACM 5.0 (ocm namespace, v5.0.0-xxx CSV format)"
---

# Install Failure Signatures

Known failure patterns for Install (ACM/MCE installation) tests.

---

## INFRASTRUCTURE Patterns

### CSV Stuck in Pending Phase
- **Error:** `ClusterServiceVersion <name> phase is Pending`
- **Pattern:** CSV never progresses beyond Pending; all downstream tests fail
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** OLM can't resolve dependencies -- CatalogSource may be unhealthy or image pull failed
- **Diagnostic:** `oc get csv -n ocm -o wide`, `oc get catalogsource -n openshift-marketplace` *(Changed in ACM 5.0; previously namespace was `open-cluster-management` in ACM 2.x.)*

### CSV InstallReady but Not Succeeded
- **Error:** CSV phase stuck at `InstallReady` or `Installing`
- **Pattern:** Operator deployment pods fail to start (image pull, resource limits)
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Diagnostic:** `oc get csv -n ocm -o jsonpath='{.items[*].status.phase}'` *(Changed in ACM 5.0; previously namespace was `open-cluster-management` in ACM 2.x.)*

### CatalogSource Unhealthy
- **Error:** PackageManifest not found or CatalogSource connection timeout
- **Pattern:** Install tests can't find the operator package to install
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Diagnostic:** `oc get catalogsource -n openshift-marketplace -o wide`

### Image Pull Failure
- **Error:** `ImagePullBackOff` or `ErrImagePull` on operator pods
- **Pattern:** ACM_DS_TAG points to an image tag that doesn't exist in the registry
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Diagnostic:** `oc get pods -n ocm -o wide | grep -E 'ImagePull|ErrImage'` *(Changed in ACM 5.0; previously namespace was `open-cluster-management` in ACM 2.x.)*

### ROSA Cluster Not Ready
- **Error:** Test setup fails connecting to ROSA cluster
- **Pattern:** All install tests fail at cluster authentication
- **Classification:** INFRASTRUCTURE (90% confidence)

## AUTOMATION_BUG Patterns

### Hardcoded Version Expectation
- **Error:** Assertion fails comparing installed version to expected string
- **Pattern:** Test expects specific version string that changed in new release
- **Classification:** AUTOMATION_BUG (80% confidence)

### Stale CRD Assumption
- **Error:** Test creates a CR with fields that don't exist in the current CRD version
- **Pattern:** CRD schema changed between releases, test not updated
- **Classification:** AUTOMATION_BUG (80% confidence)

## PRODUCT_BUG Patterns

### MCH Reconciliation Failure
- **Error:** MultiClusterHub CR status shows `Progressing` indefinitely with error conditions
- **Pattern:** MCH operator is Running but can't reconcile components. CSV is Succeeded.
- **Classification:** PRODUCT_BUG (85% confidence)
- **Diagnostic:** `oc get mch -A -o yaml | grep -A5 'conditions'`

### Component Enablement Ignored
- **Error:** Disabled component still deploys, or enabled component not deployed
- **Pattern:** MCH spec.overrides.components doesn't match actual deployment state
- **Classification:** PRODUCT_BUG (85% confidence)
- **Diagnostic:** `oc get mch -A -o jsonpath='{.items[0].spec.overrides.components}'`
