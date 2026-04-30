# Infrastructure Failure Signatures

Known failure patterns for infrastructure-level issues that affect multiple subsystems.

---

## Broad Impact Patterns

### Mass Timeout Across Multiple Features
- **Error:** Various timeout errors across CLC, Search, Virt, GRC tests
- **Pattern:** 10+ tests from different feature areas all fail with timeouts
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** Cluster-wide issue: node pressure, API server degraded, or resource exhaustion
- **Diagnostic:** `oc get nodes`, `oc adm top nodes`, `oc get co`

### Managed Clusters NotReady
- **Error:** Various -- VM scheduling, cluster transfer, addon health
- **Pattern:** 5/6 managed clusters NotReady/Unknown
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Impact:** Affects Virtualization, CLC, Search (spoke data missing), GRC (compliance stale)
- **Diagnostic:** `oc get managedclusters`

### Console Pod CPU Throttle
- **Error:** Slow page loads, 500 on logout, 6-7 pod restarts
- **Pattern:** All features degraded, intermittent failures across all areas
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** Console pod CPU limit set too low (e.g., 50m vs normal ~500m)
- **Diagnostic:** `oc get deploy console-chart-console-v2 -n ocm -o jsonpath='{.spec.template.spec.containers[0].resources}'`

### ResourceQuota Blocking Pod Restarts
- **Error:** Pods gradually disappear, services become unavailable
- **Pattern:** Slow degradation -- components fail one by one over time
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Explanation:** ResourceQuota in ocm namespace limits pods below current count
- **Diagnostic:** `oc get resourcequota -n ocm`, compare `used` vs `hard` limits

### TLS Certificate Corrupted
- **Error:** Service returns TLS handshake errors, pod CrashLoopBackOff
- **Pattern:** Specific subsystem fails (depends on which cert is corrupted)
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Diagnostic:** `oc get secret <cert-name> -n ocm -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -dates`

### NetworkPolicy Blocking Communication
- **Error:** Service timeout, empty results, connection refused
- **Pattern:** All pods Running but specific service can't be reached
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Diagnostic:** `oc get networkpolicy -n ocm`

### Webhook Service Unreachable
- **Error:** `failed calling webhook` or 500 error on resource operations
- **Pattern:** All operations on specific resource type fail
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Diagnostic:** `oc get validatingwebhookconfiguration <name> -o yaml`

### Corrupted Bash Environment on CI Runner
- **Error:** `/usr/bin/bash: which: line 1: syntax error: unexpected end of file`
- **Pattern:** Appears in stderr of every `cy.exec()` call; `oc apply` on multi-document YAML may fail partway through
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** CI runner's bash `which` function definition is corrupted. Affects all pipelines using `cy.exec()` with bash commands.
- **Observed in:** ALC, GRC, Right Sizing pipelines
- **Fix:** `unset -f which` in CI runner profile

### Empty Credential Parameter
- **Error:** `oc login -u kubeadmin -p  --insecure-skip-tls-verify` (note the empty `-p`)
- **Pattern:** Login fails with 401 Unauthorized, cascades to all tests needing that cluster
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** Jenkins parameter for cluster password is empty. Pipeline was misconfigured or credential injection failed.
- **Diagnostic:** Check Jenkins parameter value -- if empty, pipeline was misconfigured
- **Impact:** All tests requiring `oc login` to that cluster fail with authentication errors

## Classification Guidance

Infrastructure issues have these characteristics:
1. **Broad impact** -- affects multiple test areas simultaneously
2. **Environment-dependent** -- same tests pass on a healthy cluster
3. **Not code-related** -- product and automation code are correct
4. **Often self-revealing** -- error messages reference cluster components (pods, nodes, webhooks)

Key distinction from PRODUCT_BUG:
- If ALL pods are healthy and env looks clean but feature doesn't work -> PRODUCT_BUG
- If pods are crashing, resources missing, or connectivity broken -> INFRASTRUCTURE
- If the error message references a selector that doesn't exist in code -> AUTOMATION_BUG
