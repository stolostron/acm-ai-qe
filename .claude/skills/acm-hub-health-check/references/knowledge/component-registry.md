# ACM Component Registry

Reference guide for ACM hub components. Use this to understand what components
exist, where they live, and what healthy looks like. This is NOT a checklist --
always discover what's actually deployed on the cluster first.

## Top-Level Control Plane

### MultiClusterHub (MCH)

The top-level ACM operator. Its status is the single best indicator of overall
ACM health. All ACM components are managed through MCH.

- **Namespace**: Varies by installation. Commonly `open-cluster-management`,
  but can be `ocm` or any custom namespace. **Always use `oc get mch -A`**
  (all namespaces) to find it -- never assume a fixed namespace.
- **Resource**: `multiclusterhubs.operator.open-cluster-management.io`
- **Check**: `oc get mch -A -o yaml`
- **Healthy**: `phase: Running`, all conditions True
- **Key status fields**:
  - `.status.phase` -- Running means healthy
  - `.status.conditions` -- look for Complete condition with "All hub components ready"
  - `.status.components` -- a **map** (not array) keyed by component name,
    each entry has `status`, `type`, `reason`, `kind`. Check all show `status: "True"`
  - `.spec.overrides.components` -- array of which features are enabled/disabled
- **Dependencies**: MCE must be healthy first
- **Impact when degraded**: Feature-specific or platform-wide depending on
  which component is failing
- **Important**: The MCH namespace is where most ACM hub pods are deployed.
  Once you discover the MCH namespace, use it for all subsequent pod checks
  instead of hardcoding `open-cluster-management`

### MultiClusterEngine (MCE)

The base platform operator. MCE provides the foundation that ACM builds on.
If MCE is degraded, everything is affected.

- **Namespace**: `multicluster-engine`
- **Resource**: `multiclusterengines.multicluster.openshift.io`
- **Check**: `oc get multiclusterengines -A -o yaml`
- **Healthy**: `phase: Available`, all conditions True
- **Key pods**: check `oc get pods -n multicluster-engine`
- **Impact when degraded**: Platform-wide -- every ACM feature depends on MCE

### OCP Cluster Version

The underlying OpenShift platform. ACM runs on top of OCP, so OCP health
directly affects ACM.

- **Check**: `oc get clusterversion`
- **Healthy**: Available=True, Progressing=False
- **Watch for**: Upgrade in progress (Progressing=True) can cause temporary
  pod disruptions that look like ACM issues but aren't

---

## Cluster Management

### Managed Clusters

Spoke clusters registered with the hub. Their availability indicates whether
the hub can communicate with them.

- **Resource**: `managedclusters.cluster.open-cluster-management.io`
- **Check**: `oc get managedclusters`
- **Healthy**: `AVAILABLE=True`, `JOINED=True`, `HUB ACCEPTED=True`
- **Key conditions**: `ManagedClusterConditionAvailable`,
  `ManagedClusterJoined`, `HubAcceptedManagedCluster`
- **If Unknown**: Hub hasn't heard from the spoke's klusterlet -- connectivity
  issue, not necessarily spoke-side failure

### Klusterlet (spoke-side agent)

Runs on each managed cluster, maintains heartbeat with hub via lease renewal.

- **Namespace** (on spoke): `open-cluster-management-agent`
- **Pod label**: `app=klusterlet`
- **Hub-side check**: Managed cluster lease in the cluster's namespace
  `oc get lease -n <cluster-namespace>`
- **Impact when down**: All spoke-dependent features fail for that cluster
  (search, governance, observability, apps)

### Cluster Lifecycle Controllers

Handle cluster creation, import, and upgrade operations.

- **Namespace**: MCH namespace (discover dynamically) and `hive`
- **Key deployments**:
  - `managedcluster-import-controller` -- imports clusters, deploys klusterlet
  - `cluster-curator` -- orchestrates upgrades via curator pods
  - `cluster-manager` -- core cluster management
  - `registration-operator` -- hub-side registration
  - `placement-controller` (in `open-cluster-management-hub`) -- placement decisions
- **Hive** (in `hive` namespace):
  - `hive-controllers` (Deployment) -- provisions cloud infrastructure for
    new clusters. Runs with `--disabled-controllers clustersync,machinepool`
    because those run as separate StatefulSets.
  - `hive-operator` (Deployment, in `multicluster-engine`) -- manages Hive
    installation. Watches HiveConfig CR.
  - `hiveadmission` (Deployment, 2 replicas) -- webhook admission for
    ClusterDeployment operations. failurePolicy: Fail.
  - `hive-clustersync` (StatefulSet) -- syncs SyncSets to provisioned clusters
  - `hive-machinepool` (StatefulSet) -- manages MachinePool resources
  - `HiveConfig` (cluster-scoped CR) -- intermediate configuration CR between
    MCE operator and Hive controllers. If missing, hive-operator deploys
    nothing. Check `oc get hiveconfig -o yaml` for status conditions.
- **Provisioning resources** (created per provisioning operation):
  - `ClusterProvision` -- tracks a single provisioning attempt. Created by
    hive-controllers. Multiple ClusterProvisions exist if retries occurred.
    Check: `oc get clusterprovision -n <cluster-ns>`
  - Install Pod -- runs `openshift-install create cluster`. Ephemeral pod
    created in the cluster's namespace. Label: `hive.openshift.io/install=true`.
    Logs contain cloud-specific provisioning output.
  - `ClusterImageSet` -- defines an available OCP release version for
    provisioning. Cluster-scoped. Managed by `cluster-image-set-controller`.
    If the referenced release image doesn't exist in the registry (common
    in disconnected environments), provisioning fails at install pod.
    Check: `oc get clusterimagesets`
- **Check**: `oc get pods -n <mch-namespace> -l app=managedcluster-import-controller`

### Add-on Manager

Deploys and manages add-ons on spoke clusters (search-collector, governance
framework, metrics-collector, application-manager, etc.).

- **Namespace**: MCH namespace (discover dynamically)
- **Pod label**: `app=addon-manager`
- **Impact when down**: New add-on deployments stop; existing add-ons continue
  but can't be updated
- **Related**: `oc get managedclusteraddons -A` shows all deployed add-ons

---

## Search

Indexes resources across all managed clusters for cross-cluster search queries.

- **Namespace**: Same as MCH namespace (discover dynamically)
- **MCH component**: `search` (enabled by default)
- **Key pods** (look for pods matching `search-*` in the MCH namespace):
  - `search-api` -- serves search queries to console
  - `search-indexer` -- processes and indexes data
  - `search-collector` -- hub-side collector deployment
  - `search-postgres` -- PostgreSQL storage backend (ACM 2.12+, replaced redisgraph)
  - `search-v2-operator-controller-manager` -- search v2 operator
  - On spokes: `search-collector` add-on collects resource data
- **Healthy**: All pods Running, low restart count, queries return results
- **Data flow**: collector addon (spoke) -> indexer (hub) -> postgres (hub) -> api (hub) -> console
- **Common issues**:
  - Postgres uses emptyDir (not PVC) -- pod restart = all indexed data lost, re-collection takes 10-30 min
  - Collector addon not on spoke -> resources from that spoke missing (no error, just empty results)
  - Index rebuild after restart -> temporarily stale results
- **Legacy note**: Older ACM versions (pre-2.12) used `search-redisgraph` instead
  of `search-postgres`. Check what's actually deployed.

---

## Governance / Policy (GRC)

Policy engine that propagates and enforces policies across managed clusters.

- **Namespace**: MCH namespace (discover dynamically)
- **MCH component**: `grc` (enabled by default)
- **Key pods**:
  - `grc-policy-propagator` (label: `app=grc-policy-propagator`) -- distributes
    policies from hub to managed clusters
- **Add-ons** (on spoke clusters):
  - `governance-policy-framework` -- core framework, runs sync controllers
  - `config-policy-controller` -- enforces ConfigurationPolicy
  - `cert-policy-controller` -- enforces CertificatePolicy
  - `iam-policy-controller` -- enforces IAM policies
- **Data flow**: Policy (hub) -> propagator -> work-manager -> spoke controllers
  -> compliance status back to hub
- **Common issues**:
  - Propagator down -> policies don't distribute
  - Addon missing on spoke -> compliance status "Unknown"
  - work-manager backlog -> compliance updates delayed

---

## Observability

Collects metrics from managed clusters and provides Grafana dashboards on the hub.
Requires S3-compatible storage.

- **Namespace**: `open-cluster-management-observability` (separate from main ACM namespace)
- **MCH component**: `multicluster-observability-operator` (disabled by default on some versions)
- **Operator**: `multicluster-observability-operator` (lives in the MCH namespace)
- **Key pods** (in `open-cluster-management-observability`):
  - `observability-thanos-query` + `observability-thanos-query-frontend` -- query layer
  - `observability-thanos-receive-default-*` -- receives metrics from spokes (StatefulSet, typically 3 replicas)
  - `observability-thanos-store-shard-*` -- persists to S3 storage (sharded StatefulSets)
  - `observability-thanos-compact` -- compacts historical data
  - `observability-thanos-rule` -- evaluates recording/alerting rules
  - `observability-grafana` -- visualization dashboards
  - `observability-alertmanager` -- alert routing (typically 3 replicas)
  - `observability-observatorium-api` + `observability-observatorium-operator` -- API gateway
  - `observability-rbac-query-proxy` -- RBAC-aware query proxy
  - `endpoint-observability-operator` -- manages spoke-side observability
  - `metrics-collector-deployment` -- hub-side metrics collector
  - `uwl-metrics-collector-deployment` -- user workload metrics collector
  - Memcached pods for query-frontend and store caching
  - Optional: `minio` if using Minio for S3 storage
- **Add-on**: `observability-controller` on spokes (manages metrics-collector)
- **Resource**: `MultiClusterObservability` CR
- **Storage**: Observability uses many PVCs -- alertmanager, compactor, receive,
  rule, and store shards all have dedicated PVs. Check all with
  `oc get pvc -n open-cluster-management-observability`
- **Known Thanos alerts**: `ACMThanosCompactHalted`, `ACMThanosCompactHighCompactionFailures`,
  `ACMThanosCompactBucketHighOperationFailures`, `ACMThanosCompactHasNotRun`
- **Common issues**:
  - S3 storage misconfigured -> thanos-store CrashLoop (most common issue)
  - Thanos store BucketStore InitialSync failures -> high restart counts on
    store shards (may self-recover but accumulates restarts)
  - PVCs full -> compactor or receive stuck
  - metrics-collector addon missing on spoke -> no metrics from that cluster
- **Note**: This is typically the largest deployment on the hub (30+ pods).
  Pod naming uses `observability-` prefix consistently.

---

## Application Lifecycle (ALC)

Manages application deployment across clusters via subscriptions or GitOps.

- **Namespace**: MCH namespace (discover dynamically)
- **MCH component**: `app-lifecycle` (enabled by default)
- **Key pods**:
  - `subscription-controller` (label: `app=subscription-controller`) -- reconciles subscriptions
  - `channel-controller` (label: `app=channel-controller`) -- manages channels
  - `multicluster-operators-subscription` -- core subscription operator
- **Add-on**: `application-manager` on spokes
- **Two deployment models**:
  1. Subscription: Channel (Git/Helm/Object) -> Subscription -> PlacementRule -> ManifestWork
  2. ArgoCD/GitOps: ApplicationSet -> GitOps Addon Controller -> OpenShift GitOps on spokes
- **Common issues**:
  - Channel auth failure (Git credentials) -> subscription stuck, no explicit error
  - PlacementRule matches no clusters -> app not deployed anywhere
  - GitOps path requires OpenShift GitOps Operator (external) -- if missing, ArgoCD path fails silently

---

## Console

The ACM web console, delivered as OpenShift dynamic plugins.

- **Namespaces**: MCH namespace (ACM plugin) and `multicluster-engine` (MCE plugin)
- **MCH component**: `console` (enabled by default)
- **Key pods** (in MCH namespace):
  - `console-chart-console-v2-*` -- the console frontend (typically 2 replicas)
  - `acm-cli-downloads-*` -- CLI download server
  - `multicluster-integrations-*` -- integration layer
- **Console plugins**: Check `oc get consoleplugins` for registered plugins.
  Common plugins: `acm`, `mce`, `kubevirt-plugin`, `forklift-console-plugin`,
  `gitops-plugin`, `monitoring-plugin`, `networking-console-plugin`
- **Auth**: Flows through OpenShift OAuth
- **Impact**: Console is the UI for ALL features. If console pods are down, all
  UI functionality fails
- **Common issues**:
  - ConsolePlugin CR missing -> entire feature tabs disappear (no error, just missing nav)
  - Console pod crash -> UI errors across all features
  - OAuth misconfiguration -> login redirect loops
- **Note**: In ACM 2.16+, `console-api` is integrated into the console chart.
  The separate `console-api` deployment may not exist. Check what's actually
  deployed rather than assuming specific pod names.

---

## RBAC / User Management

Fine-grained RBAC for multi-cluster access control.

- **Namespace**: MCH namespace (discover dynamically)
- **MCH component**: `fine-grained-rbac` (disabled by default)
- **Key pods**:
  - `multicluster-role-assignment-controller` -- manages MCRA resources
  - `cluster-permission-*` -- cluster permission controller
- **Key resources**:
  - `MultiClusterRoleAssignment` (MCRA) CRD
  - `ClusterPermission` CRD
- **Add-on**: `acm-roles` on managed clusters (deploys RBAC roles to spokes)
- **Depends on**: console (serves RBAC endpoints), IDP configuration
- **When disabled**: User Management tab does not render in console (no error, just absent)
- **Common issues**:
  - Feature flag disabled -> User Management tab missing
  - No IDP configured -> user list empty
  - Console errors on RBAC endpoints -> 500 errors in User Management

---

## Virtualization (Fleet Virt)

Cross-cluster VM management. Optional feature requiring CNV on spoke clusters.

- **MCH component**: `cnv-mtv-integrations` (disabled by default)
- **Hub-side**: kubevirt-plugin console extension
- **Spoke-side**: Requires CNV (OpenShift Virtualization) operator
  - Namespace: `openshift-cnv`
  - Key operators: `kubevirt-hyperconverged`, `kubevirt-operator`, `cdi-operator`
- **Data flow**: VMs run on spokes -> search indexes VM resources -> hub UI displays them
- **Two prerequisites**: CNV on spoke (VMs exist) AND MCH flag on hub (fleet UI renders).
  Missing either causes different failures
- **Related**: MTV (Migration Toolkit for Virtualization) for VM migration,
  CCLM (Cross-Cluster Live Migration)

---

## Automation (ClusterCurator)

Integrates ACM with Ansible Automation Platform (AAP) for lifecycle hook
execution during cluster operations (install, upgrade, destroy, scale).

### cluster-curator-controller

- **Namespace**: `multicluster-engine` (owned by MCE, not MCH)
- **Pod label**: `name=cluster-curator-controller`
- **Expected replicas**: 2
- **Health check**: `oc get deploy cluster-curator-controller -n multicluster-engine`
- **Healthy**: 2/2 replicas available
- **CRD**: ClusterCurator (`cluster.open-cluster-management.io/v1beta1`)

### Console Integration

- **Backend proxy**: `ansibletower.ts` proxies AAP API calls for template
  discovery
- **SSE events**: ClusterCurator status changes via `events.ts`

### Common Issues

- AAP operator not installed -> template dropdown empty, hooks can't execute
- ansibletower.ts proxy returns empty results -> template selection broken
  (AAP healthy but console shows no templates)
- ClusterCurator Job timeout -> default 5-minute hook timeout too short
- Expired kubeconfig in hosted mode -> upgrade operations fail
- ACM ≤2.15 incompatible with OCP 4.21 upgrade API (ACM-30314)

### Dependencies

- MCE operator (owns the controller deployment)
- AAP operator (external, provides AnsibleJob CRD)
- Cluster lifecycle / Hive (target must be a managed cluster)

---

## Infrastructure Foundation

### Nodes

The underlying OCP worker/master nodes.

- **Check**: `oc get nodes`, `oc adm top nodes`
- **Healthy**: All nodes Ready, no MemoryPressure/DiskPressure/PIDPressure
- **Impact**: Node issues cause pod scheduling failures that look like ACM issues

### Certificates

TLS certificates for internal communication.

- **Check**: `oc get secrets -n <mch-namespace> -o json | jq '.items[] | select(.type=="kubernetes.io/tls") | .metadata.name'`
- **MCH webhook certs auto-rotate**, but custom certs may not
- **Impact**: Expired certs cause intermittent failures across components

### Storage

PVCs used by various ACM components.

- **Check**: `oc get pvc -n <mch-namespace>`, `oc get pvc -n open-cluster-management-observability`
- **Components using storage**: search (redisgraph/postgres), observability (thanos), etcd

---

## Common Namespaces Reference

| Namespace | What lives here |
|-----------|----------------|
| MCH namespace (varies: `open-cluster-management`, `ocm`, or custom) | Most ACM hub components, operators, MCH operator itself |
| `open-cluster-management-hub` | Hub-specific controllers (placement, work-manager, registration) |
| `multicluster-engine` | MCE operator and components |
| `open-cluster-management-observability` | Observability stack (Thanos, Grafana, ~30+ pods) |
| `open-cluster-management-backup` | Cluster backup resources |
| `open-cluster-management-global-set` | Global ManagedClusterSet resources |
| `open-cluster-management-policies` | Policy resources |
| `hive` | Hive cluster provisioning |
| `open-cluster-management-agent` | Klusterlet on spoke clusters |
| `open-cluster-management-agent-addon` | Add-ons on spoke clusters |
| `openshift-cnv` | CNV/KubeVirt on spoke clusters |

**Critical**: The MCH namespace is NOT always `open-cluster-management`. Some
installations use `ocm` or other custom namespaces. Always discover the actual
namespace with `oc get mch -A` first, then use that namespace for all subsequent
pod checks. Never hardcode `open-cluster-management`.

Discovery command: `oc get namespaces | grep -E 'open-cluster|multicluster|hive|ocm'`
