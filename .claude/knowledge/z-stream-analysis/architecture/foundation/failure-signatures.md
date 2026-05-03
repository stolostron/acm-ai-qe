# Foundation Failure Signatures

Known failure patterns for Foundation (ServerFoundation / addon-framework) tests.

---

## INFRASTRUCTURE Patterns

### RBAC Forbidden on Addon Operations
- **Error:** `clusterrolebindings is forbidden: User system:serviceaccount:multicluster-engine:cluster-proxy cannot update`
- **Pattern:** Addon operations fail with 403 Forbidden after cluster upgrade
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Explanation:** Post-upgrade RBAC re-propagation not complete. ClusterRoleBinding needs recreation.
- **Diagnostic:** `oc get clusterrolebinding cluster-proxy-addon-agent-tokenreview -o yaml`
- **Expected resolution:** 5-15 minutes after upgrade

### CRD Not Found on Server
- **Error:** `the server doesn't have a resource type "managedclusters" in group "clusterview.open-cluster-management.io"`
- **Pattern:** Tests querying ClusterView CRDs fail with "does not exist on the server"
- **Classification:** INFRASTRUCTURE if CRD is version-specific (85% confidence), AUTOMATION_BUG if test assumes CRD exists in all versions
- **Diagnostic:** `oc get crd managedclusters.clusterview.open-cluster-management.io`

### Addon Not Available
- **Error:** `ManagedClusterAddon <name> status is Progressing` or `Unknown`
- **Pattern:** Addon health checks timeout waiting for Available state
- **Classification:** INFRASTRUCTURE (80% confidence)
- **Explanation:** Addon controller hasn't finished reconciliation (common post-upgrade)
- **Diagnostic:** `oc get managedclusteraddon -A`

### Managed Cluster Not Joined
- **Error:** `ManagedCluster <name> condition ManagedClusterJoined is False`
- **Pattern:** Tests requiring healthy spoke clusters fail at setup
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Diagnostic:** `oc get managedclusters -o wide`

### Import Controller Unhealthy
- **Error:** Timeout waiting for managed cluster import
- **Pattern:** All import-related tests fail, non-import Foundation tests may pass
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Diagnostic:** `oc get pods -n multicluster-engine -l app=managedcluster-import-controller-v2`

### Cluster-Proxy Connection Refused
- **Error:** `dial tcp <ip>:443: connect: connection refused` via cluster-proxy
- **Pattern:** Tests using cluster-proxy to reach spoke API fail
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Diagnostic:** `oc get managedclusteraddon cluster-proxy -n <cluster> -o yaml`

## AUTOMATION_BUG Patterns

### Stale Cluster Reference
- **Error:** Test references a managed cluster name that no longer exists
- **Pattern:** Cluster was destroyed/re-provisioned between test suite updates
- **Classification:** AUTOMATION_BUG (80% confidence)

### Hardcoded Timeout Too Short
- **Error:** Timeout after 60s/120s waiting for addon Available
- **Pattern:** Addon reaches Available at 130s but test gives up at 120s
- **Classification:** AUTOMATION_BUG (75% confidence) -- if addon eventually reaches Available

## PRODUCT_BUG Patterns

### Addon Status Stuck in Progressing
- **Error:** ManagedClusterAddon stays in Progressing indefinitely
- **Pattern:** Addon controller is Running but never transitions addon to Available. Other addons on same cluster are fine.
- **Classification:** PRODUCT_BUG (80% confidence)
- **Diagnostic:** Check addon controller logs: `oc logs -n open-cluster-management -l app=addon-manager --tail=100`

### Work-Agent Not Processing ManifestWork
- **Error:** ManifestWork stays in `Applied=False` on spoke
- **Pattern:** Work-agent pod is Running, but ManifestWorks created by hub are not applied
- **Classification:** PRODUCT_BUG (80% confidence)
- **Diagnostic:** `oc get manifestwork -n <cluster> -o yaml` on hub, check work-agent logs on spoke
