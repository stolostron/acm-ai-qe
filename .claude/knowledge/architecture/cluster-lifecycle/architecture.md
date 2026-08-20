---
type: architecture
subsystem: cluster-lifecycle
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - data-flow/cluster-lifecycle/data-flow.md
  - health/cluster-lifecycle/known-issues.md
  - failures/cluster-lifecycle/failure-signatures.md
  - versions/acm-2x-to-5x-changes.md
version_notes:
  - "registration-operator renamed to cluster-manager (3 replicas) in ACM 5.0"
  - "managedcluster-import-controller moved to multicluster-engine namespace"
  - "hive-operator moved from hive to multicluster-engine namespace"
  - "cluster-curator-controller runs in multicluster-engine namespace"
---

# Cluster Lifecycle (CLC) -- Architecture

## What Cluster Lifecycle Does

Cluster Lifecycle manages the full lifecycle of managed clusters in ACM:
provisioning new clusters, importing existing ones, upgrading them, and
deprovisioning. It spans multiple operators (Hive, MCE, registration-operator,
ClusterCurator) across different namespaces and involves three distinct
operational flows with different controller stacks.

CLC is the largest subsystem by bug count (233 bugs in 2.15-2.17), primarily
because it sits at the intersection of cloud provider APIs, Kubernetes
cluster bootstrapping, and multi-cluster agent deployment.

---

## Three Core Flows

### 1. Create (Provisioning via Hive)

Creates new OCP clusters on cloud providers (AWS, Azure, GCP, vSphere,
bare metal, KubeVirt). Uses Hive's ClusterDeployment CRD as the
primary API surface.

```
User creates ClusterDeployment + InstallConfig
  -> hive-controllers provisions infrastructure via cloud APIs
  -> Install pod runs openshift-install in cluster's namespace
  -> Cluster boots, kubeconfig generated
  -> managedcluster-import-controller auto-imports
  -> klusterlet deployed to new cluster
  -> ManagedCluster becomes Available
```

Key namespace: each ClusterDeployment gets its own namespace (matching
the cluster name) where install pods, secrets, and logs reside.

### 2. Import (Existing Clusters)

Brings existing clusters under ACM management without provisioning them.
Two sub-flows:

**Manual import:** User creates ManagedCluster CR -> import-controller
generates klusterlet manifests -> user applies to spoke -> klusterlet
registers with hub.

**Auto-import:** Triggered automatically when a ClusterDeployment or
HostedCluster completes provisioning. Import-controller detects the new
cluster and deploys klusterlet without user intervention.

### 3. Upgrade (via ClusterCurator)

Orchestrates OCP cluster upgrades with optional pre/post Ansible hooks.

```
User creates/updates ClusterCurator CR with desired version
  -> cluster-curator controller creates upgrade Job
  -> (optional) Pre-upgrade AnsibleJob runs via AAP
  -> Curator triggers OCP upgrade via ClusterVersion API
  -> Monitors upgrade progress
  -> (optional) Post-upgrade AnsibleJob runs
  -> ClusterCurator status updated
```

ClusterCurator uses AnsibleJob CRDs and JobTemplate CRDs for AAP
integration. Without AAP, upgrades proceed without hooks.

---

## HyperShift / Hosted Control Planes

HyperShift provides a separate cluster topology where control planes
run as pods on the hub (or a management cluster) rather than on dedicated
nodes. This fundamentally changes the namespace model and certificate
management.

### How It Differs

- **Namespace model:** Each hosted cluster gets a namespace on the
  management cluster where control plane pods run. The HostedCluster
  and NodePool CRDs live in this namespace.
- **Import path:** hypershift-addon-operator on the hub watches for
  HostedCluster completion and triggers auto-import via
  managedcluster-import-controller. The ManagedCluster CR is created
  automatically.
- **Certificate management:** Kubeconfig secrets are mounted into
  control plane pods. When certs rotate, the mounted secrets update
  but pods don't automatically restart -- controllers reading the
  mounted kubeconfig continue using stale credentials until the pod
  restarts. This is a known source of bugs (8 bugs across MCE 2.4-2.8).
- **Detach semantics:** Detaching a hosted cluster must NOT delete the
  hosting namespace, because that namespace contains the control plane.
  This was the root cause of ACM-15018 (detach destroying hosted clusters).

### Key Components

- **hypershift-addon-manager:** (deployment: `hypershift-addon-manager` in `multicluster-engine`, 1 replica) Manages the HyperShift addon on the
  hub. Watches HostedCluster resources and triggers auto-import.
- **HyperShift Operator:** Manages HostedCluster and NodePool lifecycle.
- **external-managed-kubeconfig:** Secret generated for existing HCPs
  that need to be imported (ACM-22317 fixed the backfill case).

---

## Key Components

### managedcluster-import-controller

- **Deployment name:** `managedcluster-import-controller-v2`
- **Pod label:** `app=managedcluster-import-controller-v2`
- **Namespace:** `multicluster-engine`
- **Replicas:** 2

Watches ManagedCluster CRs and deploys klusterlet to spoke clusters.
Generates import manifests (klusterlet deployment, bootstrap kubeconfig
secret, CRDs). For auto-import, detects completed ClusterDeployments
and HostedClusters.

**Critical behavior:** On ManagedCluster deletion, it cleans up klusterlet
from the spoke. On detach (removing the ManagedCluster without destroying
the cluster), it must NOT delete the namespace if a HostedCluster exists
in it (ACM-15018 fix).

### cluster-curator-controller

- **Deployment name:** `cluster-curator-controller`
- **Pod label:** `app=cluster-curator-controller`
- **Namespace:** `multicluster-engine`
- **Replicas:** 2

Watches ClusterCurator CRs and orchestrates cluster upgrades. Creates
Job pods that drive the upgrade workflow. Supports pre/post-upgrade
hooks via AnsibleJob CRDs referencing AAP templates.

**Known issue:** Curator logic incompatible with OCP 4.21 upgrade API
changes (ACM-30314). Curator pods run in the cluster's namespace.

### cluster-manager

- **Deployment name:** `cluster-manager`
- **Pod label:** `app=cluster-manager`
- **Namespace:** `multicluster-engine`
- **Replicas:** 3

Core cluster management operator. Deploys hub-side components in
`open-cluster-management-hub` namespace:
- `cluster-manager-registration-controller` (3 replicas)
- `cluster-manager-placement-controller` (3 replicas)
- `cluster-manager-work-webhook` (3 replicas)
- `cluster-manager-registration-webhook` (3 replicas)
- `cluster-manager-addon-manager-controller` (3 replicas)
- `cluster-manager-addon-webhook` (3 replicas)

The ClusterManager CR (`operator.open-cluster-management.io/v1`) controls
the deployment mode.

### hive-operator

- **Pod label:** `app=hive-operator`
- **Namespace:** `multicluster-engine` (Changed in ACM 5.0; previously in `hive` namespace in ACM 2.x)
- **Replicas:** 1

Manages Hive controllers and CRDs. The operator itself runs in the MCE namespace
but deploys hive-controllers into the `hive` namespace.

### hive-controllers

- **Pod label:** `app=hive-controllers`
- **Namespace:** `hive`

Provisions cloud infrastructure for new clusters. Watches ClusterDeployment,
ClusterPool, ClusterClaim CRDs. Runs install pods with `openshift-install`
binary. Manages cloud credentials, DNS, and networking.

Separate namespace (`hive`) from the rest of ACM. Hive operator manages
its own lifecycle independently. ClusterDeployment webhooks validate
configurations.

### hive-clustersync

- **Kind:** StatefulSet (not Deployment)
- **Pod label:** `app=hive-clustersync`
- **Namespace:** `hive`
- **Replicas:** 1

Syncs cluster state between Hive and managed clusters.

### registration-operator (logical, covered by cluster-manager)

No standalone `registration-operator` deployment exists on ACM 5.0. The
registration functionality is provided by the `cluster-manager` deployment
in the `multicluster-engine` namespace (3 replicas), which deploys and manages
the registration controller, work controller, and placement controller
in `open-cluster-management-hub`. Changed in ACM 5.0; previously existed as
a standalone deployment in ACM 2.x.

### placement-controller

- **Pod label:** `app=placement-controller`
- **Namespace:** `open-cluster-management-hub`

Evaluates Placement resources to determine which managed clusters
match placement criteria. Produces PlacementDecision resources listing
selected clusters. Used by GRC (policy distribution), Application
(subscription/AppSet targeting), and CLC itself (ClusterPool claims).

### cluster-permission-controller

- **Deployment name:** `cluster-permission`
- **Pod label:** `app=cluster-permission`
- **Namespace:** `multicluster-engine`
- **Replicas:** 1

Propagates RBAC rules to managed clusters via ManifestWork. Watches
ClusterPermission CRs and creates ManifestWork resources containing
Roles, RoleBindings, ClusterRoles, and ClusterRoleBindings.

**Known issue:** Prior to fixes (ACM-24032, ACM-25572), this controller
used `Owns` watch on ManifestWork, caching all ManifestWorks across
all clusters. At scale (1000+ clusters), this caused OOM. Also had
aggressive informer resync causing hot-loop reconciliation.

---

## Key CRDs

| CRD | API Group | Purpose |
|-----|-----------|---------|
| ClusterDeployment | hive.openshift.io/v1 | Defines a Hive-provisioned cluster |
| ManagedCluster | cluster.open-cluster-management.io/v1 | Represents a managed cluster on the hub |
| ManagedClusterSet | cluster.open-cluster-management.io/v1beta2 | Groups clusters for RBAC and placement |
| ClusterPool | hive.openshift.io/v1 | Pool of pre-provisioned clusters |
| ClusterClaim | hive.openshift.io/v1 | Claims a cluster from a pool |
| ClusterCurator | cluster.open-cluster-management.io/v1beta1 | Automation workflow orchestration |
| ClusterImageSet | hive.openshift.io/v1 | Available OCP versions for provisioning |

---

## Webhooks (Critical)

Hive registers several validating webhooks with `failurePolicy=Fail`:
- `clusterdeploymentvalidators.admission.hive.openshift.io`
- `clusterimagesetvalidators.admission.hive.openshift.io`
- `machinepoolvalidators.admission.hive.openshift.io`

If ANY of these webhook services are unreachable, ALL operations on those
resource types fail with 500 "failed calling webhook" errors. The webhook
configuration is managed by the Hive operator, NOT the MCH operator.

---

## ClusterPool

ClusterPool pre-provisions a pool of clusters that can be claimed
on-demand via ClusterClaim resources. Reduces cluster provisioning
time from 30-45 min to near-instant.

```
ClusterPool (desired size N)
  -> hive-controllers maintains N hibernating ClusterDeployments
  -> User creates ClusterClaim
  -> Hive assigns an available ClusterDeployment
  -> Cluster resumes from hibernation
  -> managedcluster-import-controller imports
```

**Known issue:** ClusterPool CR was not in `blockDeletionResources`
for MCE uninstall, causing ClusterPool to remain orphaned after MCE
removal (ACM-27552).

---

## Cluster Operations

| Operation | Resources Created | Key API |
|-----------|-------------------|---------|
| Create cluster | ClusterDeployment, MachinePool, InstallConfig | hive.openshift.io/v1 |
| Import cluster | ManagedCluster, KlusterletAddonConfig | cluster.open-cluster-management.io/v1 |
| Destroy cluster | Deletes ClusterDeployment | hive.openshift.io/v1 |
| Transfer cluster to set | Updates ManagedCluster labels | cluster.open-cluster-management.io/v1 |
| Upgrade cluster | ClusterCurator with upgrade spec | cluster.open-cluster-management.io/v1beta1 |

---

## Namespace Model

CLC uses multiple namespaces, which is a common source of confusion:

| Namespace | Contents |
|---|---|
| `ocm` | MCH operator, GRC controllers, search, observability operator, ALC operators. Changed in ACM 5.0; previously `open-cluster-management` in ACM 2.x |
| `open-cluster-management-hub` | Registration, placement, work controllers |
| `multicluster-engine` | MCE components: import controller, cluster-manager, hive-operator, foundation, addon-manager, hypershift, cluster-proxy, discovery, ocm-controller/proxyserver/webhook |
| `hive` | Hive operator and hive-controllers |
| `<cluster-name>` | Per-cluster: ClusterDeployment, install pods, kubeconfig secrets, curator Jobs |
| `open-cluster-management-agent` | Klusterlet agent on spoke |
| `open-cluster-management-agent-addon` | Addon agents on spoke (search-collector, governance-framework, etc.) |
| `<hosted-ns>` | HyperShift: HostedCluster, NodePool, control plane pods |

---

## Console Integration

CLC pages: `/multicloud/infrastructure/clusters/managed`,
`/multicloud/infrastructure/clusters/discovered`,
`/multicloud/infrastructure/clusters/sets`

The cluster creation wizard constructs ClusterDeployment and related resources.
Key backend interaction: `frontend/src/resources/resource.ts` builds API paths.

Navigation: `cypress/views/header.js` -- `openMenu()` and `goToClusters()`
functions. The perspective switcher race condition (synchronous `$body.find()`)
affects ALL CLC tests that navigate to the clusters page.

---

## Configuration

### MCH Component Toggle

CLC is enabled by default. It cannot be fully disabled because it
provides core cluster management capabilities.

### Cloud Provider Credentials

Stored as Secrets in the cluster's namespace. Secret type varies by
provider (AWS, Azure, GCP, vSphere, bare metal). The Credentials UI
in ACM Console manages these.

### Hive Configuration

HiveConfig CR (`hive.openshift.io/v1`) controls global Hive behavior:
- `spec.targetNamespace` -- where Hive operates (default: `hive`)
- `spec.deleteProtection` -- prevents accidental ClusterDeployment deletion
- `spec.manageDNS` -- whether Hive manages cluster DNS

---

## Cross-Subsystem Dependencies

| Dependency | Why |
|---|---|
| Infrastructure (klusterlet) | Import and upgrade require klusterlet connectivity to spoke |
| Search | Fleet Virt uses search to discover VMs on CLC-managed clusters |
| Governance | PlacementBinding/Placement shared with GRC for cluster targeting |
| Console | Cluster pages, create/import wizards, upgrade UI |
| Virtualization | Cluster API Provider KubeVirt uses KubeVirt for cluster provisioning |
| AAP (external) | ClusterCurator pre/post-upgrade automation hooks |

## What Depends on CLC

| Consumer | Impact When CLC Is Down |
|---|---|
| All managed clusters | Cannot provision, import, or upgrade clusters |
| ClusterPool | Cannot create or claim pre-provisioned clusters |
| HyperShift | Cannot create or manage hosted control planes |
| Fleet Virt KubeVirt provider | Cannot provision KubeVirt-based clusters |
| RBAC (ClusterPermission) | Cannot propagate RBAC rules to managed clusters |
| GRC/App/Search | Cannot add new clusters for policy/app/search management |
