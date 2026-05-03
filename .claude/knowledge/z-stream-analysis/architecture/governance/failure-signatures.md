# Governance Failure Signatures

Known failure patterns for GRC-related test failures.

---

## INFRASTRUCTURE Patterns

### Propagator TLS Certificate Corrupted
- **Error:** Policy creation returns 500 or propagator CrashLoopBackOff
- **Pattern:** All policy operations fail, existing policies on spokes continue
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** The TLS secret `propagator-webhook-server-cert` was corrupted. The service-CA operator manages this cert but doesn't auto-repair corruption (only rotates on schedule).
- **Diagnostic:** `oc get secret propagator-webhook-server-cert -n ocm -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -dates`
- **Fix:** Delete the secret and restart propagator (service-CA will regenerate)

### Propagator Pods Missing (Quota Blocked)
- **Error:** Policy compliance not updating, new policies not propagating
- **Pattern:** Propagator was killed and ResourceQuota prevents restart
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Explanation:** A ResourceQuota in the ocm namespace limits pod count below what's needed. After propagator pods crash, new pods can't be created.
- **Diagnostic:** `oc get pods -n ocm | grep propagator` (should show 2 pods), `oc get resourcequota -n ocm`

### Spoke Addon Not Deployed
- **Error:** Policy shows "no status" or NonCompliant for a specific cluster
- **Pattern:** Compliance missing from one spoke but present on others
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Diagnostic:** `oc get managedclusteraddon governance-policy-framework -n <spoke>`

## AUTOMATION_BUG Patterns

### Policy Name Assertion Mismatch
- **Error:** Expected policy name doesn't match
- **Pattern:** Test creates policy with dynamic name but asserts against static value
- **Classification:** AUTOMATION_BUG (80% confidence)

### Compliance Wait Timeout
- **Error:** Policy compliance did not reach expected state within timeout
- **Pattern:** Test waits for Compliant but policy stays NonCompliant
- **Classification:** Could be AUTOMATION_BUG (timeout too short), INFRASTRUCTURE (spoke addon slow), or PRODUCT_BUG (policy enforcement broken)
- **Diagnostic:** Check if same policy is compliant via `oc get policy -A`

## PRODUCT_BUG Patterns

### Policy Status Not Aggregating
- **Error:** Root policy shows wrong compliance despite spoke policies being correct
- **Pattern:** Individual cluster compliance is correct but aggregate is wrong
- **Classification:** PRODUCT_BUG (75% confidence)
- **Explanation:** Propagator aggregation logic has a bug
