# Observability Failure Signatures

Known failure patterns for observability-related test failures.

---

## INFRASTRUCTURE Patterns

### MCO CR Not Created
- **Error:** Observability features missing or not functional
- **Pattern:** Observability-dependent tests fail, operator pod is healthy
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** The operator is deployed but the MCO CR with S3 storage config is not created
- **Diagnostic:** `oc get multiclusterobservability -A`

### S3 Storage Not Configured
- **Error:** Thanos can't start, MCO CR shows error conditions
- **Pattern:** MCO CR exists but observability pods not running
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Diagnostic:** `oc get multiclusterobservability -o yaml | grep -A5 conditions`

### metrics-collector Addon Missing
- **Error:** Dashboard shows no data for specific spoke
- **Pattern:** Metrics missing from one spoke but present on others
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Diagnostic:** `oc get managedclusteraddon observability-controller -n <spoke>`

## PRODUCT_BUG Patterns

### Observability Flag Inverted
- **Error:** UI elements conditional on observability show/hide incorrectly
- **Pattern:** Features that should appear when observability is installed don't, or vice versa
- **Classification:** PRODUCT_BUG (75% confidence)
- **Explanation:** hub.ts inverts the `isObservabilityInstalled` flag
- **File:** `backend/src/routes/hub.ts`
