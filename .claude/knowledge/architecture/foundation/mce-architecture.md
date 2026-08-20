---
type: architecture
subsystem: foundation
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - architecture/foundation/architecture.md
  - architecture/install/olm-install-chain.md
  - architecture/cluster-lifecycle/architecture.md
  - versions/acm-2x-to-5x-changes.md
version_notes:
  - "MCE operator increased to 2 replicas (HA) in ACM 5.0"
  - "cluster-manager deployment has 3 replicas in ACM 5.0"
  - "MCE version aligned with ACM at 5.0 (previously MCE 2.x with ACM 2.x)"
---

# MCE Internal Architecture -- Architecture

MultiCluster Engine (MCE) is the platform layer of ACM. It manages cluster
lifecycle, registration, work distribution, proxy connectivity, Hive-based
provisioning, HyperShift hosted control planes, and cluster discovery. MCE
can be installed standalone or as part of ACM (where the MCH operator creates
the MCE chain automatically).

---

## MCE Operator

The `multicluster-engine-operator` (2 replicas, leader-elected) watches the
`MultiClusterEngine` CR and reconciles all MCE-level components. Created by
OLM from the MCE CSV. The MCE CR is created by the MCH operator (not the user)
when installed as part of ACM.

| Field | Value |
|-------|-------|
| CRD | `multiclusterengines.multicluster.openshift.io` |
| CR name | `multiclusterengine` |
| CR scope | Cluster-scoped |
| Phase when healthy | `Available` |

---

## Deployments in `multicluster-engine` Namespace (21 total)

| Deployment | Replicas | Role |
|------------|----------|------|
| `multicluster-engine-operator` | 2 | MCE operator. Watches MultiClusterEngine CR, reconciles all MCE components. |
| `cluster-manager` | 3 | Deploys the registration-operator (OCM hub). Creates the ClusterManager CR which spawns the 6 hub controllers in `open-cluster-management-hub`. |
| `ocm-controller` | 2 | Core OCM controller. Manages ManagedCluster lifecycle, cluster status aggregation, and coordination between MCE subsystems. |
| `ocm-proxyserver` | 2 | Aggregated API server extending the Kubernetes API with OCM resources. Provides the `clusterview` API group used by the ACM console for cluster listing and RBAC-scoped views (e.g., `kubevirtprojects`, `userpermissions`). |
| `ocm-webhook` | 2 | Admission webhook for OCM resources. Validates and mutates ManagedCluster, Placement, and other OCM CRs before they are persisted. |
| `managedcluster-import-controller-v2` | 2 | Import controller. When a new ManagedCluster is created (imported or provisioned), creates ManifestWork containing klusterlet operator, CRDs, and configuration for the spoke. |
| `cluster-curator-controller` | 2 | Orchestrates pre/post-hook Ansible jobs during cluster provisioning and upgrade workflows. Watches ClusterCurator CRs. |
| `cluster-image-set-controller` | 1 | Manages ClusterImageSet resources that catalog available OCP versions for provisioning. The console uses these to populate the version dropdown during cluster creation. |
| `cluster-permission` | 1 | Watches ClusterPermission CRs (created by the MRA controller) and generates ManifestWork to deliver RoleBindings/ClusterRoleBindings to managed clusters. |
| `cluster-proxy` | 2 | Hub-side proxy server accepting tunneled connections from spoke clusters. Enables the hub to route API requests, VNC console connections, and kubectl commands to managed clusters without direct network access. |
| `cluster-proxy-addon-manager` | 2 | Manages the cluster-proxy addon deployment to spoke clusters via the addon framework. Ensures each spoke has a proxy agent that establishes a reverse tunnel to the hub. |
| `cluster-proxy-addon-user` | 2 | User-facing proxy endpoint. Controllers and users route requests through this service to reach managed cluster API servers via the cluster-proxy tunnels. Used by Fleet Virtualization for VNC console access. |
| `clusterclaims-controller` | 2 | Manages ClusterClaim CRs for ClusterPool. Assigns hibernated clusters from a pool, resumes them, and returns them when the claim is deleted. |
| `clusterlifecycle-state-metrics-v2` | 1 | Exposes Prometheus metrics for cluster lifecycle state (import status, addon health, provisioning progress). |
| `console-mce-console` | 2 | MCE console backend. Provides the base platform UI functionality (clusters, infrastructure) as an OCP ConsolePlugin. Works alongside the ACM console plugin. |
| `discovery-operator` | 1 | Discovers existing OpenShift clusters from Red Hat OCM or other sources. Watches DiscoveryConfig CRs and creates DiscoveredCluster resources that can be imported into ACM. |
| `hive-operator` | 1 | Manages the Hive cluster provisioning system. Watches HiveConfig CR and deploys hive-controllers and hiveadmission in the `hive` namespace. Hive handles OCP cluster provisioning via ClusterDeployment CRs using cloud provider APIs. |
| `hypershift-addon-manager` | 1 | Manages HyperShift hosted control plane addon deployment to management clusters. Enables provisioning of hosted clusters where the control plane runs as pods on a hosting cluster. |
| `infrastructure-operator` | 1 | Manages the Assisted Installer service for bare-metal and on-premise cluster provisioning. Watches AgentServiceConfig CR. Deploys assisted-service, assisted-image-service, and related components for host discovery and installation. |
| `hcp-cli-download` | 1 | Serves the `hypershift` CLI binary for download. Provides the tool needed to create and manage hosted control plane clusters from the command line. |
| `provider-credential-controller` | 1 | Manages cloud provider credentials used for cluster provisioning. Validates credential secrets and ensures they contain the required fields for the target platform (AWS, Azure, GCP, vSphere). |

---

## ClusterManager CR and Hub Controllers

The `cluster-manager` deployment (3 replicas) in `multicluster-engine` runs the
registration-operator. It creates a `ClusterManager` CR which triggers the
deployment of 6 hub controllers in the `open-cluster-management-hub` namespace.
These controllers form the OCM control plane for managed cluster communication.

### Hub Controllers in `open-cluster-management-hub` (6 deployments)

| Deployment | Replicas | Role |
|------------|----------|------|
| `cluster-manager-addon-manager-controller` | 3 | Lifecycle manager for ManagedClusterAddons. Creates ManifestWork to deploy addon agents (search-collector, governance-framework, application-manager, etc.) on spoke clusters. |
| `cluster-manager-addon-webhook` | 3 | Admission webhook for addon-related resources. Validates ManagedClusterAddon and ClusterManagementAddon CRs. |
| `cluster-manager-placement-controller` | 3 | Evaluates Placement CRs against ManagedCluster labels, ClusterSets, and predicates. Writes PlacementDecision CRs listing selected clusters. Used by GRC, application lifecycle, FG-RBAC, and ArgoCD integration. |
| `cluster-manager-registration-controller` | 3 | Manages ManagedCluster registration lifecycle: CSR approval, cluster acceptance, lease-based heartbeat monitoring, and cluster status updates. |
| `cluster-manager-registration-webhook` | 3 | Admission webhook for registration resources. Validates ManagedCluster, ManagedClusterSet, and ManagedClusterSetBinding CRs. |
| `cluster-manager-work-webhook` | 3 | Admission webhook for ManifestWork resources. Validates work payloads before they are delivered to spoke clusters. |

---

## Hive Subsystem (Provisioned by hive-operator)

The hive-operator deploys the Hive stack in a separate `hive` namespace. Hive
handles IPI-based cluster provisioning using cloud provider APIs.

| Resource | Type | Replicas | Role |
|----------|------|----------|------|
| `hive-controllers` | Deployment | 1 | Main reconciler for ClusterDeployment, ClusterPool, and provisioning Jobs |
| `hiveadmission` | Deployment | 2 | Admission webhook for Hive CRs (ClusterDeployment, ClusterPool validation) |
| `hive-clustersync` | StatefulSet | 1 | Syncs SelectorSyncSet and SyncSet resources to Hive-provisioned clusters |
| `hive-machinepool` | StatefulSet | 1 | Manages MachinePool CRs for scaling worker nodes on provisioned clusters |

### Hive CRDs

| CRD | Purpose |
|-----|---------|
| `ClusterDeployment` | Declares a cluster to provision (platform, version, networking, credentials) |
| `ClusterPool` | Pre-provisions hibernated clusters for fast claiming |
| `ClusterClaim` | Claims a cluster from a ClusterPool |
| `ClusterImageSet` | Catalogs available OCP versions (typically 200+ entries) |
| `HiveConfig` | Cluster-scoped config for the Hive subsystem |

---

## Cluster-Proxy Architecture

The cluster-proxy trio provides API server connectivity to managed clusters
that may not be directly reachable from the hub (e.g., behind NAT or firewall).

```
Console / Controller
  → cluster-proxy-addon-user (port 9092)
    → cluster-proxy (port 8090)
      → [reverse tunnel]
        → cluster-proxy agent on spoke
          → spoke kube-apiserver
```

The addon-manager deploys the proxy agent to each spoke via ManifestWork.
The agent establishes a reverse tunnel to the hub's cluster-proxy server.
Fleet Virtualization uses this path for VNC console access to VMs on managed
clusters.

---

## MCE Relationship to ACM Components

MCE provides the platform layer that other ACM components depend on:

| ACM Component | MCE Dependency |
|---------------|----------------|
| GRC (policy propagation) | Placement controller for cluster targeting; ManifestWork for policy delivery |
| Application Lifecycle | Placement controller for cluster targeting; ManifestWork for app delivery |
| Fine-Grained RBAC | Placement controller for cluster targeting; cluster-permission for ManifestWork creation |
| Search | ManagedCluster registration for cluster inventory |
| Console | ocm-proxyserver for clusterview API; cluster-proxy for VNC access |
| Submariner | ManagedCluster registration; addon framework for agent deployment |
| Observability | Addon framework for metrics-collector deployment to spokes |

---

## Diagnostic Commands

```bash
# MCE operator and CR
oc get multiclusterengine
oc get pods -n multicluster-engine

# All 21 MCE deployments
oc get deployments -n multicluster-engine

# Hub controllers
oc get deployments -n open-cluster-management-hub

# ClusterManager CR
oc get clustermanager

# Hive
oc get pods -n hive
oc get hiveconfig -o yaml

# Cluster-proxy connectivity
oc get pods -n multicluster-engine -l app=cluster-proxy
oc get managedclusteraddons -A | grep cluster-proxy
```
