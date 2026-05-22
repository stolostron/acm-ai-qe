# ACM Platform Architecture

How ACM is built and operates: operator hierarchy, install lifecycle,
component management, addon framework, resource distribution, and how
failures cascade through the stack.

---

## 1. The Operator Hierarchy

ACM is a layered stack of operators where each layer reconciles the layer below:

```
OLM (Operator Lifecycle Manager)
  -> MCH Operator (advanced-cluster-management CSV, namespace: ocm)
       -> Backplane Operator (multicluster-engine CSV, namespace: multicluster-engine)
            -> Component Operators & Deployments (~88 pods across 4 namespaces)
                 |- cluster-manager
                 |- hive-operator
                 |- managedcluster-import-controller
                 |- addon-manager
                 |- foundation-controller
                 |- grc-policy-propagator
                 |- search-api / search-indexer
                 |- subscription-controller
                 |- multicluster-observability-operator
                 |- console / acm-console
                 |- cluster-permission
                 |- siteconfig-controller
                 +- ~30+ deployments total
```

Each layer reconciles the layer below. If MCH operator is unhealthy, all
downstream components can't be managed. If backplane operator is unhealthy,
MCE components can't be deployed.

Key implication for failure classification: if MCH operator is at 0 replicas or
MCH status is not Running, classify ALL failures as INFRASTRUCTURE.

---

## 2. MultiClusterHub (MCH)

The top-level management object for ACM. Exactly ONE per hub cluster.

### Status Reporting

```yaml
status:
  phase: Running        # Running, Pending, Installing, Uninstalling, Error
  currentVersion: 2.16.0
  conditions:
  - type: Complete
    status: "True"
    reason: ComponentsAvailable
  components:           # Map keyed by component name
    search-api:
      kind: Deployment
      status: "True"    # Deployed and healthy
      reason: MinimumReplicasAvailable
    grc-policy-propagator:
      kind: Deployment
      status: "True"
      reason: MinimumReplicasAvailable
```

The `.status.components` map is keyed by deployment/resource name. Each entry
has `status` (boolean string), `reason`, `kind`, and `lastTransitionTime`.

### Component Enable/Disable

`.spec.overrides.components` controls which features are deployed:

**Enabled by default:** search, grc, app-lifecycle, console, cluster-lifecycle,
insights, multicluster-engine, cluster-permission

**Disabled by default:** multicluster-observability, fine-grained-rbac,
cnv-mtv-integrations, cluster-backup, submariner-addon, siteconfig, volsync

When a component is disabled, the MCH operator does NOT deploy it. Tests
targeting a disabled component fail with "element not found" or "page not
found" -- these are NOT automation bugs, they are INFRASTRUCTURE (feature not
enabled). Check `oc get mch -A -o jsonpath='{.items[0].spec.overrides.components}'`.

### MCH Operator Reconciliation

The MCH operator reconciles every ~5 minutes:
- Recreates deleted deployments
- Restores deployment specs (replicas, image)
- Does NOT reconcile: ConfigMap content, Secret content, NetworkPolicies,
  ResourceQuotas, webhook configurations (owned by other operators),
  database content inside pods

This means: to inject persistent bugs via the console image, you must scale
the MCH operator to 0 replicas first. Infrastructure-level issues (NetworkPolicy,
ResourceQuota, cert corruption, DB corruption) persist even with the operator running.

### Common Stuck States

- MCH stuck `Pending`: Usually an MCE dependency issue or a component operator
  failing to start
- MCH stuck `Uninstalling`: Finalizers on ACM resources not being removed,
  often caused by submariner or search-pause annotations (ACM-15538)
- MCH switching `Running` <-> `Pending`: A component is flapping

---

## 3. MultiClusterEngine (MCE)

The base platform that ACM builds on. Provides core multicluster capabilities:
cluster registration, import, provisioning (Hive), HyperShift, placement engine,
ManifestWork distribution, addon framework, and foundation services.

MCH **depends on** MCE. MCH operator creates/manages the MCE CR and adds
ACM-specific components on top (Search, GRC, ALC, Console, Observability, etc.).

MCE phase should be `Available`. If `Degraded`, it causes platform-wide
impact -- every ACM feature is affected.

---

## 4. Install Lifecycle

### How ACM Gets Installed

```
1. Admin creates Subscription for ACM operator in target namespace
2. OLM resolves dependencies: ACM requires MCE -> creates MCE Subscription
3. OLM creates InstallPlans -> installs CRDs and operator Deployments
4. MCH operator starts, waits for MCH CR creation
5. MCH operator ensures MCE CR exists, configures it
6. Backplane operator deploys MCE components
7. MCH operator deploys ACM components (based on enabled list)
8. Each component operator reconciles its own resources
9. MCH status transitions to Running when all components report healthy
```

### Upgrade Mechanics

```
1. New version appears in channel (e.g., release-2.16)
2. OLM creates InstallPlan for new CSV
3. CRDs updated first (cluster-scoped)
4. New CSV replaces old CSV, new operator pods roll out
5. Operators detect version change, update their managed components
6. MCH operator triggers component updates
```

**Upgrade failure modes:**
- CRD breaking changes (removing versions with stored data) -- ACM-28211
- Component ordering dependencies not met
- Addon framework timing during version transition
- CSV deletion ordering during MCH uninstall (ACM-15851)

---

## 5. Console Plugin Architecture

ACM console is an OCP dynamic plugin (ConsolePlugin CR). The OCP console loads
the ACM plugin at runtime. If the ACM plugin fails to register or load:
- The OCP console still works
- ACM navigation items (Fleet Management perspective) disappear
- All ACM UI tests fail with "element not found" errors
- Classification: INFRASTRUCTURE (plugin not loaded), not AUTOMATION_BUG

Registered plugins (typical): acm, mce, forklift, gitops, kubevirt, monitoring, networking

---

## 6. The Addon Framework

How ACM distributes agents from hub to managed (spoke) clusters.

### Architecture

```
Hub Cluster                              Spoke Cluster
-----------                              -------------
ClusterManagementAddon                   
  (hub-side definition)                  
         |                               
         v                               
ManagedClusterAddon                      
  (per-cluster, in cluster's NS)         
         |                               
         v                               
ManifestWork                             
  (contains addon manifests)             
         |                               
         v (via klusterlet work agent)   
                                         Addon Pod(s)
                                           |- search-collector
                                           |- governance-framework
                                           |- config-policy-controller
                                           |- application-manager
                                           |- metrics-collector
                                           +- etc.
```

### How Addon Health Is Reported Back

1. **Lease-based (default):** Addon pod renews a Lease object on the hub.
   If lease expires (~5 min), addon is considered unhealthy.
2. **Work-based:** Health inferred from ManifestWork status.
3. **Custom:** Addon registers a health check endpoint.

### Key Addons

| Addon | Purpose | Default |
|---|---|---|
| `search-collector` | Indexes spoke resources for hub search | Enabled |
| `governance-policy-framework` | Policy framework agent on spoke | Enabled |
| `config-policy-controller` | Enforces ConfigurationPolicy on spoke | Enabled |
| `application-manager` | Manages app resources on spoke | Enabled |
| `observability-controller` | Manages metrics-collector on spoke | Enabled (if obs on) |
| `cert-policy-controller` | Enforces certificate policies | Enabled |
| `cluster-proxy` | Proxy connectivity to spoke API | Enabled |
| `managed-serviceaccount` | Manages ServiceAccounts on spokes | Enabled |
| `work-manager` | Manages ManifestWork lifecycle | Enabled |

---

## 7. ManifestWork: Hub-to-Spoke Distribution

ManifestWork distributes Kubernetes resources from hub to spoke clusters.
Namespaced resource in the managed cluster's namespace on the hub.

### How It Gets Applied

```
Hub: ManifestWork created in cluster's namespace
  -> klusterlet work agent on spoke pulls content
  -> work agent applies each manifest to spoke
  -> work agent reports status back to ManifestWork.status
```

ManifestWork status shows per-resource results with Applied and Available
conditions.

**If klusterlet is disconnected**, ManifestWork changes can't be delivered.
This affects all addon deployments and RBAC propagation.

### ManifestWork for RBAC Propagation

```
MCRA -> ClusterPermission -> ManifestWork (Role + RoleBinding YAML)
  -> klusterlet applies on spoke -> user gets permissions
```

---

## 8. ManagedCluster Registration

### How a Cluster Joins

1. ManagedCluster resource created on hub
2. managedcluster-import-controller generates bootstrap kubeconfig + import secret
3. Klusterlet manifests applied to spoke
4. Klusterlet starts: registration-agent registers, work-agent pulls ManifestWorks
5. CSR approved (manual or auto)
6. Conditions transition: HubAccepted=True, Joined=True, Available=True

### Conditions

| Condition | True Means | False/Unknown Means |
|---|---|---|
| `HubAcceptedManagedCluster` | Hub accepted this cluster | CSR not approved |
| `ManagedClusterJoined` | Klusterlet registered | Registration failed |
| `ManagedClusterConditionAvailable` | Cluster is reachable | Lease expired, offline |

### Lease Renewal

Klusterlet maintains a Lease in the managed cluster's namespace on the hub.
Renewed every ~60s. If not renewed within 5 minutes:
- `ManagedClusterConditionAvailable` -> `Unknown`
- Cluster appears offline
- All spoke-dependent features affected

---

## 9. Managed Cluster and Addon Framework

Each managed cluster has a klusterlet agent on the spoke. The hub deploys
addons via ManagedClusterAddon CRs. Standard addons on a typical cluster:

work-manager, application-manager, cert-policy-controller, cluster-proxy,
config-policy-controller, governance-policy-framework, hypershift-addon,
kubevirt-hyperconverged, managed-serviceaccount, mtv-operator,
search-collector, acm-roles (12 total)

If an addon is missing or degraded on a spoke, features dependent on that
addon fail on that spoke only. Example: search-collector missing = resources
from that spoke silently absent from search results.

---

## 10. Namespace Conventions

The MCH namespace can vary -- `open-cluster-management`, `ocm`, or custom.
Always discover it: `oc get mch -A -o jsonpath='{.items[0].metadata.namespace}'`

| Namespace | Purpose | Pod Count (typical) |
|---|---|---|
| MCH namespace (varies) | MCH operator, console, search, grc, subscription, addon-manager, foundation | ~32 |
| `multicluster-engine` | Backplane operator, mce-console, cluster-manager, import controller, foundation, placement, addon-manager, hypershift | ~33 |
| `open-cluster-management-hub` | placement-controller, work-manager, registration, work controllers | ~18 |
| `open-cluster-management-agent` | Klusterlet (on spokes and local-cluster) | - |
| `open-cluster-management-agent-addon` | Addon agents (on spokes) | - |
| `open-cluster-management-observability` | Observability stack (if enabled) | - |
| `hive` | Hive operator and controllers | ~5 |
| `openshift-gitops` | ArgoCD / GitOps operator (if installed) | ~5 |
| `openshift-cnv` | CNV operator (if installed, spoke-side) | varies |
| `openshift-mtv` | MTV / Forklift operator (if installed) | varies |
| `<cluster-name>` | Per-managed-cluster NS: addons, ManifestWorks, secrets, leases | - |

---

## 11. Key CRDs

| CRD | Scope | API Group | Purpose | Key Status Fields |
|---|---|---|---|---|
| `MultiClusterHub` | Namespaced | operator.open-cluster-management.io/v1 | Top-level ACM config | `.status.phase`, `.status.components` |
| `MultiClusterEngine` | Cluster | multicluster.openshift.io/v1 | Base platform config | `.status.phase`, `.status.conditions` |
| `ManagedCluster` | Cluster | cluster.open-cluster-management.io/v1 | Represents a spoke | `.status.conditions` (Available, Joined) |
| `ManagedClusterAddon` | Namespaced | addon.open-cluster-management.io/v1alpha1 | Addon per cluster | `.status.conditions` (Available, Degraded) |
| `ClusterManagementAddon` | Cluster | addon.open-cluster-management.io/v1alpha1 | Hub-side addon def | `.spec.installStrategy` |
| `ManifestWork` | Namespaced | work.open-cluster-management.io/v1 | Resources for spoke | `.status.conditions` (Applied, Available) |
| `Placement` | Namespaced | cluster.open-cluster-management.io/v1beta1 | Cluster selection | `.status.numberOfSelectedClusters` |
| `PlacementDecision` | Namespaced | cluster.open-cluster-management.io/v1beta1 | Placement results | `.status.decisions[].clusterName` |
| `MultiClusterRoleAssignment` | Cluster | rbac.open-cluster-management.io/v1alpha1 | Fine-grained RBAC | `.status.conditions` |
| `ClusterPermission` | Namespaced | rbac.open-cluster-management.io/v1alpha1 | RBAC on spoke | ManifestWork for Roles/RoleBindings |
| `ClusterDeployment` | Namespaced | hive.openshift.io/v1 | Hive-provisioned cluster | provision failures |
| `ManagedClusterSet` | Cluster | cluster.open-cluster-management.io/v1beta2 | Cluster grouping | membership issues |
| `Policy` | Namespaced | policy.open-cluster-management.io/v1 | GRC policy | compliance status |

---

## 12. Webhook Architecture

ACM registers 11+ validating webhooks. Critical ones:
- `clusterdeploymentvalidators.admission.hive.openshift.io` (failurePolicy=Fail)
- `managedclustervalidators.admission.cluster.open-cluster-management.io`
- `managedclustersetbindingvalidators`

If a webhook service is down or CA bundle is corrupted, ALL resource operations
through that webhook fail with 500 errors. The MCH operator does NOT reconcile
webhook configurations (they're owned by their respective operators).

---

## 13. TLS Certificate Management

19 TLS secrets in the ocm namespace, managed by OCP service-CA operator.
Automatic rotation on ~2 year schedule. If manually corrupted, service-CA
does NOT auto-repair (only rotates on schedule). MCH operator does NOT
reconcile cert content.

Critical certs: console-chart-console-certs, search-api-certs,
propagator-webhook-server-cert, multiclusterhub-operator-webhook

---

## 14. Cross-Subsystem Dependency Map

```
Infrastructure (MCE, klusterlet, addon-manager)
  |- ALL features depend on this layer
  |- klusterlet down -> spoke offline -> all spoke features fail
  +- addon-manager down -> no new addon deployments

Search (search-api, search-indexer, search-collector, postgres)
  |- Console VM page uses search for VM discovery
  |- RBAC UI uses search for resource discovery
  +- search-collector down on spoke -> that spoke's resources invisible

GRC (propagator, governance-framework addon, config-policy-controller)
  |- Depends on klusterlet for policy propagation
  +- Depends on ManifestWork for policy delivery

Console (console chart, console plugins)
  |- ALL UI tests depend on console health
  |- Proxies requests to search, observability, etc.
  +- ConsolePlugin CR missing -> feature tab disappears

Application Lifecycle (subscription-controller, channel-controller)
  |- Depends on klusterlet for ManifestWork delivery
  +- GitOps path depends on external OpenShift GitOps operator

Observability (thanos, grafana, metrics-collector addon)
  |- Only feature requiring external storage (S3)
  +- Depends on addon-manager for metrics-collector deployment

Fleet Virtualization
  |- Depends on Search for VM discovery
  |- Depends on Console plugin registration
  |- Depends on CNV on spokes (external to ACM)
  +- Depends on RBAC (MCRA) for VM access control
```

---

## 15. Diagnostic Quick Reference

### First-Pass Health Check

```bash
oc get mch -A                                      # MCH status
oc get multiclusterengines                          # MCE status
oc get csv -n <mch-namespace>                       # ACM CSV
oc get csv -n multicluster-engine                   # MCE CSV
oc get pods -n <mch-namespace>                      # ACM pods
oc get pods -n multicluster-engine                  # MCE pods
oc get pods -n open-cluster-management-hub          # Hub controllers
oc get managedclusters                              # Fleet health
oc get managedclusteraddons -A | grep -v "True"     # Unhealthy addons
```

### Common Failure Cascade Patterns

**Infrastructure failure -> all features:**
klusterlet disconnected -> search-collector can't send -> ManifestWork
can't be delivered -> policies not applied -> metrics gaps -> VM status stale

**Search failure -> UI features:**
search-postgres PVC not bound -> postgres can't start -> indexer stops ->
search-api returns empty -> Console VM page shows no VMs -> RBAC UI empty

**Component disabled -> silent failure:**
`fine-grained-rbac: enabled: false` -> MCRA operator not deployed ->
User Management tab not rendered -> no error, tab just isn't there
