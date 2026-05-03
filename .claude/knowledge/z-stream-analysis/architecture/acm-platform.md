# ACM Platform Architecture (Failure Analysis Context)

How ACM is structured, what operators manage what, and how failures cascade
through the stack. This context helps classify whether a test failure is a
product bug, automation bug, or infrastructure issue.

---

## Operator Hierarchy

ACM is a layered stack where each operator reconciles the layer below:

```
OLM (Operator Lifecycle Manager)
  -> MCH Operator (advanced-cluster-management CSV, namespace: ocm)
       -> MCE / Backplane Operator (multicluster-engine CSV, namespace: multicluster-engine)
            -> Component Operators & Deployments (~88 pods across 4 namespaces)
```

If a higher layer is unhealthy, everything below it is affected. Key
implication for failure classification: if MCH operator is at 0 replicas or
MCH status is not Running, classify ALL failures as INFRASTRUCTURE.

## Key Custom Resources

| CR | API Group | Purpose | Failure signal |
|----|-----------|---------|----------------|
| MultiClusterHub | operator.open-cluster-management.io/v1 | Top-level ACM management | phase != Running |
| MultiClusterEngine | multicluster.openshift.io/v1 | Core cluster management | status != Available |
| ManagedCluster | cluster.open-cluster-management.io/v1 | Each managed cluster | Available != True |
| ManagedClusterAddon | addon.open-cluster-management.io/v1alpha1 | Per-cluster feature addon | Available != True |
| ClusterDeployment | hive.openshift.io/v1 | Hive-provisioned cluster | provision failures |
| ManagedClusterSet | cluster.open-cluster-management.io/v1beta2 | Cluster grouping | membership issues |
| MulticlusterRoleAssignment | rbac.open-cluster-management.io/v1alpha1 | FG-RBAC permission | subject name wrong |
| ClusterPermission | rbac.open-cluster-management.io/v1alpha1 | Spoke-level permission | applied to wrong user |
| Policy | policy.open-cluster-management.io/v1 | GRC policy | compliance status |

## Namespaces

| Namespace | What runs there | Pod count (typical) |
|-----------|----------------|---------------------|
| `ocm` | ACM hub components: console, search, GRC, insights, app-lifecycle, cluster-permission, observability operator | ~32 |
| `multicluster-engine` | MCE components: import controller, foundation, placement, addon-manager, hypershift | ~33 |
| `open-cluster-management-hub` | Hub controllers: registration, placement, work | ~18 |
| `hive` | Hive operator and controllers for cluster provisioning | ~5 |
| `openshift-gitops` | ArgoCD / GitOps operator (if installed) | ~5 |
| `openshift-cnv` | CNV operator (if installed, spoke-side) | varies |
| `openshift-mtv` | MTV / Forklift operator (if installed) | varies |

## MCH Component Management

MCH `.spec.overrides.components` controls which features are deployed.

**Enabled by default:** search, grc, app-lifecycle, console, cluster-lifecycle,
insights, multicluster-engine, cluster-permission

**Disabled by default:** multicluster-observability, fine-grained-rbac,
cnv-mtv-integrations, cluster-backup, submariner-addon, siteconfig, volsync

When a component is disabled, the MCH operator does NOT deploy it. Tests
targeting a disabled component fail with "element not found" or "page not
found" -- these are NOT automation bugs, they are INFRASTRUCTURE (feature not
enabled). Check `oc get mch -A -o jsonpath='{.items[0].spec.overrides.components}'`.

## MCH Operator Reconciliation

The MCH operator reconciles every ~5 minutes:
- Recreates deleted deployments
- Restores deployment specs (replicas, image)
- Does NOT reconcile: ConfigMap content, Secret content, NetworkPolicies,
  ResourceQuotas, webhook configurations (owned by other operators),
  database content inside pods

This means: to inject persistent bugs via the console image, you must scale
the MCH operator to 0 replicas first. Infrastructure-level issues (NetworkPolicy,
ResourceQuota, cert corruption, DB corruption) persist even with the operator running.

## Console Plugin Architecture

ACM console is an OCP dynamic plugin (ConsolePlugin CR). The OCP console loads
the ACM plugin at runtime. If the ACM plugin fails to register or load:
- The OCP console still works
- ACM navigation items (Fleet Management perspective) disappear
- All ACM UI tests fail with "element not found" errors
- Classification: INFRASTRUCTURE (plugin not loaded), not AUTOMATION_BUG

Registered plugins (typical): acm, mce, forklift, gitops, kubevirt, monitoring, networking

## Managed Cluster and Addon Framework

Each managed cluster has a klusterlet agent on the spoke. The hub deploys
addons via ManagedClusterAddon CRs. Standard addons on a typical cluster:

work-manager, application-manager, cert-policy-controller, cluster-proxy,
config-policy-controller, governance-policy-framework, hypershift-addon,
kubevirt-hyperconverged, managed-serviceaccount, mtv-operator,
search-collector, acm-roles (12 total)

If an addon is missing or degraded on a spoke, features dependent on that
addon fail on that spoke only. Example: search-collector missing = resources
from that spoke silently absent from search results.

## Webhook Architecture

ACM registers 11+ validating webhooks. Critical ones:
- `clusterdeploymentvalidators.admission.hive.openshift.io` (failurePolicy=Fail)
- `managedclustervalidators.admission.cluster.open-cluster-management.io`
- `managedclustersetbindingvalidators`

If a webhook service is down or CA bundle is corrupted, ALL resource operations
through that webhook fail with 500 errors. The MCH operator does NOT reconcile
webhook configurations (they're owned by their respective operators).

## TLS Certificate Management

19 TLS secrets in the ocm namespace, managed by OCP service-CA operator.
Automatic rotation on ~2 year schedule. If manually corrupted, service-CA
does NOT auto-repair (only rotates on schedule). MCH operator does NOT
reconcile cert content.

Critical certs: console-chart-console-certs, search-api-certs,
propagator-webhook-server-cert, multiclusterhub-operator-webhook
