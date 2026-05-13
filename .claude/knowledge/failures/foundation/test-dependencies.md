# Foundation Test Dependencies

External and internal dependencies required for Foundation (acmqe-autotest) tests.

---

## Spoke Cluster Requirements

Foundation tests require multiple managed clusters across cloud providers:

| Provider | Requirement | Impact if Missing |
|----------|-------------|-------------------|
| ROSA (AWS) | Imported, addons Available | RBAC, addon-framework tests fail |
| Azure (AKS) | Imported, addons Available | Cross-cloud registration tests fail |
| GKE (Google) | Imported, addons Available | Work-agent distribution tests fail |
| IKS (IBM) | Imported, addons Available | Import strategy tests fail |

If fewer than 4 managed clusters are healthy, tests depending on multi-cloud scenarios will fail
with timeout or assertion errors (not a product bug).

## Addon Dependencies

These addons must be deployed and `Available` on spoke clusters:

| Addon | Purpose | Check Command |
|-------|---------|---------------|
| `cluster-proxy` | Proxy API access to spoke | `oc get managedclusteraddon cluster-proxy -n <cluster>` |
| `registration-agent` | Cluster registration | `oc get managedclusteraddon registration -n <cluster>` |
| `managed-serviceaccount` | Token management | `oc get managedclusteraddon managed-serviceaccount -n <cluster>` |
| `work-manager` | ManifestWork execution | `oc get managedclusteraddon work-manager -n <cluster>` |

## RBAC Post-Upgrade Dependencies

After an ACM upgrade, the `cluster-proxy` addon requires a ClusterRoleBinding update:

- **Pattern:** `clusterrolebindings is forbidden: User system:serviceaccount:multicluster-engine:cluster-proxy cannot update`
- **Root cause:** Addon's ClusterRoleBinding not recreated after upgrade
- **Expected resolution:** 5-15 minutes after upgrade completes
- **Diagnostic:** `oc get clusterrolebinding cluster-proxy-addon-agent-tokenreview -o yaml`

## CRD Dependencies

| CRD | Required By | Version Notes |
|-----|-------------|---------------|
| `managedclusters.clusterview.open-cluster-management.io` | ClusterView tests | May not exist in all ACM versions |
| `managedserviceaccounts.authentication.open-cluster-management.io` | MSA tests | Requires MSA addon enabled |

## Import Strategy Tests

Foundation tests exercise multiple import strategies:
- Auto-import with annotations
- ImportOnly strategy (manual kubeconfig)
- Detach and re-import

If the import controller pod is unhealthy, all import-related tests cascade-fail.
Diagnostic: `oc get pods -n multicluster-engine -l app=managedcluster-import-controller-v2`
