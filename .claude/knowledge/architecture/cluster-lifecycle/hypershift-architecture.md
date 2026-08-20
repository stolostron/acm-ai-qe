---
type: architecture
subsystem: cluster-lifecycle
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - architecture/cluster-lifecycle/architecture.md
  - architecture/cluster-lifecycle/hive-provisioning.md
---

# HyperShift (Hosted Control Planes) -- Architecture

## What HyperShift Does

HyperShift provides hosted control planes for OpenShift clusters. Instead of running control plane components (etcd, kube-apiserver, kube-controller-manager) on dedicated master nodes, they run as pods on a management/hosting cluster. This decouples the control plane from the data plane, reducing infrastructure cost and enabling faster cluster provisioning.

In ACM, HyperShift is delivered as an MCE addon. The hub cluster (or a designated hosting cluster) runs the control planes for multiple hosted clusters, while worker nodes run on separate infrastructure (AWS, Azure, KubeVirt, or Agent-based bare metal).

---

## Key CRDs

| CRD | API Group | Purpose |
|-----|-----------|---------|
| HostedCluster | hypershift.openshift.io/v1beta1 | Defines a logical OCP cluster whose control plane runs as pods on the hosting cluster. Created by user or ACM Console. |
| HostedControlPlane | hypershift.openshift.io/v1beta1 | Auto-created by hypershift-operator from HostedCluster. Drives CP Deployments/StatefulSets. |
| NodePool | hypershift.openshift.io/v1beta1 | Worker pool for a HostedCluster. Defines replicas, release image, platform (AWS/Azure/KubeVirt/Agent). |
| HypershiftDeployment | cluster.open-cluster-management.io/v1alpha1 | ACM facade CR used by Console. Wraps hostedClusterSpec, nodePools, hostingCluster. |
| ClusterManagementAddOn | addon.open-cluster-management.io/v1alpha1 | Fleet-wide addon definition (`hypershift-addon`) registered by the addon manager. |
| ManagedClusterAddOn | addon.open-cluster-management.io/v1alpha1 | Per-cluster addon instance on the hosting ManagedCluster. |

---

## Deployment Flow

```
hypershift-addon-manager (hub, multicluster-engine namespace)
  → Registers ClusterManagementAddOn: hypershift-addon (CMAO)
  → Creates ManagedClusterAddOn on hosting cluster (MCAo)
  → Deploys hypershift-addon-agent to hosting cluster
    (open-cluster-management-agent-addon namespace, 2 containers)
  → hypershift-install-job (one-time Job)
    → Installs hypershift-operator into hypershift namespace on hosting cluster
  → hypershift-operator (2 replicas, hypershift namespace)
    → Watches HostedCluster + NodePool CRs
    → Creates HostedControlPlane in clusters-<name> namespace
    → Deploys CP pods: etcd, kube-apiserver, kube-controller-manager,
      control-plane-operator, ignition-server, OAuth, Konnectivity, CVO
  → NodePool reconciliation provisions workers (cloud Machines or KubeVirt VMs)
  → Workers bootstrap via ignition-server
  → When HostedCluster reaches Available:
    → hypershift-addon-agent creates ManagedCluster on hub
    → managedcluster-import-controller deploys hosted klusterlet
    → Annotations: hosting-cluster-name, klusterlet-deploy-mode: Hosted
```

---

## Auto-Import of Hosted Clusters

When a HostedCluster reaches `Available` status, the hypershift-addon-agent running on the hosting cluster:
1. Creates a ManagedCluster CR on the hub with annotation `klusterlet-deploy-mode: Hosted`
2. Sets `hosting-cluster-name` annotation pointing to the hosting ManagedCluster
3. managedcluster-import-controller detects the new ManagedCluster and deploys klusterlet in hosted mode

The hosted klusterlet runs on the hosting cluster (not on worker nodes), communicating with the hosted cluster's API server through the local control plane pods.

---

## Key Deployments

| Deployment | Namespace | Cluster | Replicas | Purpose |
|------------|-----------|---------|----------|---------|
| hypershift-addon-manager | multicluster-engine | Hub | 1 | Registers CMAO, deploys addon agent to hosting clusters |
| hcp-cli-download | multicluster-engine | Hub | 1 | Serves `hcp` CLI binary for command-line cluster management |
| hypershift-addon-agent | open-cluster-management-agent-addon | Hosting | 1 (2 containers) | Watches HostedCluster lifecycle, triggers auto-import |
| hypershift-operator | hypershift | Hosting | 2 | Reconciles HostedCluster/NodePool, manages control plane pods |

---

## Control Plane Pod Inventory (per hosted cluster)

All run in `clusters-<hostedClusterName>` namespace on the hosting cluster:

| Component | Kind | Purpose |
|-----------|------|---------|
| etcd | StatefulSet | Datastore for the hosted cluster |
| kube-apiserver | Deployment | API server exposed via LoadBalancer/Route |
| kube-controller-manager | Deployment | Standard KCM for the hosted cluster |
| control-plane-operator | Deployment | Manages OpenShift CP operators (CVO, etc.) |
| ignition-server | Deployment | Serves Ignition config to NodePool workers during bootstrap |
| OAuth server | Deployment | Authentication for the hosted cluster |
| Konnectivity | Deployment | Network tunnel between CP and workers |

---

## Differences from Hive-Based Provisioning

| Aspect | Hive (IPI) | HyperShift (Hosted) |
|--------|------------|---------------------|
| Control plane location | Dedicated master nodes on target cluster | Pods on hosting cluster |
| Provisioning time | 30-60 minutes | ~10-15 minutes (CP pods only) |
| Namespace model | `<cluster-name>` for install artifacts | `clusters-<name>` for CP pods |
| Primary CRD | ClusterDeployment | HostedCluster + NodePool |
| Worker provisioning | openshift-install creates all nodes | NodePool creates workers separately |
| Resource efficiency | 3+ master nodes per cluster | Shared hosting cluster for many CPs |
| Supported platforms | AWS, Azure, GCP, vSphere, bare metal | AWS, Azure, KubeVirt, Agent |
| Upgrade path | ClusterCurator + ClusterVersion API | HostedCluster release image update |
| Detach semantics | Safe (namespace contains only install artifacts) | Dangerous (namespace contains live CP; ACM-15018) |
| Certificate rotation | Standard OCP rotation on master nodes | Mounted secrets in CP pods; stale creds until pod restart |

---

## Known Architectural Concerns

- **Certificate staleness:** Kubeconfig secrets mounted into CP pods don't trigger pod restarts on rotation. Controllers reading stale credentials fail silently until the pod restarts (8 bugs across MCE 2.4-2.8).
- **Detach safety:** Detaching a hosted cluster must NOT delete the hosting namespace (`clusters-<name>`), because it contains the live control plane. Root cause of ACM-15018.
- **external-managed-kubeconfig:** Secret required for importing existing HCPs. ACM-22317 fixed the backfill case where this Secret was missing.

---

## Cross-Subsystem Dependencies

| Depends On | Why |
|------------|-----|
| MCE operator | Deploys hypershift-addon-manager |
| Addon framework (CMAO/MCAo) | Addon lifecycle manages agent deployment to hosting clusters |
| managedcluster-import-controller | Auto-imports hosted clusters as ManagedClusters |
| klusterlet (Infrastructure) | Hosted klusterlet registers the hosted cluster with the hub |
| Cloud provider APIs / KubeVirt | NodePool provisions workers on target infrastructure |
| Console | HypershiftDeployment CR facade for UI-driven cluster creation |

| Consumed By | Impact When HyperShift Is Down |
|-------------|--------------------------------|
| Console hosted cluster creation | Cannot create hosted control plane clusters |
| Hosted cluster workloads | Existing CPs continue running but cannot be managed/scaled |
| NodePool scaling | Cannot add/remove workers from hosted clusters |
