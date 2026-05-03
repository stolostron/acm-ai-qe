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

- **hypershift-addon-operator:** Manages the HyperShift addon on the
  hub. Watches HostedCluster resources and triggers auto-import.
- **HyperShift Operator:** Manages HostedCluster and NodePool lifecycle.
- **external-managed-kubeconfig:** Secret generated for existing HCPs
  that need to be imported (ACM-22317 fixed the backfill case).

---

## Key Components

### managedcluster-import-controller

- **Pod label:** `app=managedcluster-import-controller`
- **Namespace:** MCH namespace (`open-cluster-management`)

Watches ManagedCluster CRs and deploys klusterlet to spoke clusters.
Generates import manifests (klusterlet deployment, bootstrap kubeconfig
secret, CRDs). For auto-import, detects completed ClusterDeployments
and HostedClusters.

**Critical behavior:** On ManagedCluster deletion, it cleans up klusterlet
from the spoke. On detach (removing the ManagedCluster without destroying
the cluster), it must NOT delete the namespace if a HostedCluster exists
in it (ACM-15018 fix).

### cluster-curator-controller

- **Pod label:** `app=cluster-curator`
- **Namespace:** MCH namespace

Watches ClusterCurator CRs and orchestrates cluster upgrades. Creates
Job pods that drive the upgrade workflow. Supports pre/post-upgrade
hooks via AnsibleJob CRDs referencing AAP templates.

**Known issue:** Curator logic incompatible with OCP 4.21 upgrade API
changes (ACM-30314). Curator pods run in the cluster's namespace.

### cluster-manager

- **Pod label:** `app=cluster-manager`
- **Namespace:** MCH namespace

Core cluster management controller from the registration-operator.
Deploys hub-side components (registration, placement, work controllers)
in `open-cluster-management-hub` namespace. The ClusterManager CR
(`operator.open-cluster-management.io/v1`) controls the deployment mode.

### hive-controllers

- **Pod label:** `app=hive-controllers`
- **Namespace:** `hive`

Provisions cloud infrastructure for new clusters. Watches ClusterDeployment,
ClusterPool, ClusterClaim CRDs. Runs install pods with `openshift-install`
binary. Manages cloud credentials, DNS, and networking.

Separate namespace (`hive`) from the rest of ACM. Hive operator manages
its own lifecycle independently. ClusterDeployment webhooks validate
configurations.

### registration-operator

- **Pod label:** `app=registration-operator`
- **Namespace:** MCH namespace

Manages hub-side registration of managed clusters. Deploys and manages
the registration controller, work controller, and placement controller
in `open-cluster-management-hub`. Also deploys klusterlet on spoke
clusters (via the klusterlet CR).

### placement-controller

- **Pod label:** `app=placement-controller`
- **Namespace:** `open-cluster-management-hub`

Evaluates Placement resources to determine which managed clusters
match placement criteria. Produces PlacementDecision resources listing
selected clusters. Used by GRC (policy distribution), Application
(subscription/AppSet targeting), and CLC itself (ClusterPool claims).

### cluster-permission-controller

- **Pod label:** `app=cluster-permission`
- **Namespace:** MCH namespace

Propagates RBAC rules to managed clusters via ManifestWork. Watches
ClusterPermission CRs and creates ManifestWork resources containing
Roles, RoleBindings, ClusterRoles, and ClusterRoleBindings.

**Known issue:** Prior to fixes (ACM-24032, ACM-25572), this controller
used `Owns` watch on ManifestWork, caching all ManifestWorks across
all clusters. At scale (1000+ clusters), this caused OOM. Also had
aggressive informer resync causing hot-loop reconciliation.

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

## Namespace Model

CLC uses multiple namespaces, which is a common source of confusion:

| Namespace | Contents |
|---|---|
| `open-cluster-management` | Hub controllers (import-controller, curator, cluster-permission), MCH operator |
| `open-cluster-management-hub` | Registration, placement, work controllers |
| `hive` | Hive operator and hive-controllers |
| `<cluster-name>` | Per-cluster: ClusterDeployment, install pods, kubeconfig secrets, curator Jobs |
| `open-cluster-management-agent` | Klusterlet agent on spoke |
| `open-cluster-management-agent-addon` | Addon agents on spoke (search-collector, governance-framework, etc.) |
| `<hosted-ns>` | HyperShift: HostedCluster, NodePool, control plane pods |

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
