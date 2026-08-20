---
type: architecture
subsystem: cluster-lifecycle
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - architecture/cluster-lifecycle/architecture.md
  - data-flow/cluster-lifecycle/data-flow.md
---

# Hive Provisioning -- Architecture

## What Hive Does

Hive provides IPI (Installer-Provisioned Infrastructure) cluster provisioning and lifecycle management for ACM. It automates the creation of OCP clusters on cloud providers (AWS, Azure, GCP, vSphere, bare metal) using the `openshift-install` binary, and manages their ongoing lifecycle including hibernation, scaling, and deprovisioning.

Hive operates in its own namespace (`hive`) and is deployed by the MCE operator via the HiveConfig CR. It is the primary provisioning backend for ACM cluster creation -- the Console cluster creation wizard ultimately produces a ClusterDeployment CR that Hive processes.

---

## Key CRDs

| CRD | API Group | Purpose |
|-----|-----------|---------|
| ClusterDeployment | hive.openshift.io/v1 | Primary CR for provisioning a new cluster. Specifies platform, version (via ClusterImageSet), networking, compute. |
| ClusterProvision | hive.openshift.io/v1 | Auto-created per provisioning attempt. Tracks install log, status, retry metadata. |
| ClusterPool | hive.openshift.io/v1 | Maintains a pool of pre-provisioned hibernated clusters for on-demand claiming. |
| ClusterClaim | hive.openshift.io/v1 | Claims a cluster from a ClusterPool. Supports lifetime-based auto-cleanup. |
| ClusterImageSet | hive.openshift.io/v1 | Defines available OCP versions (release image references). ~200+ entries per hub. |
| HiveConfig | hive.openshift.io/v1 | Cluster-scoped configuration for the Hive subsystem. Created by MCE operator. |
| MachinePool | hive.openshift.io/v1 | Worker node scaling on provisioned clusters. |
| SyncSet / SelectorSyncSet | hive.openshift.io/v1 | Resources to apply/sync to Hive-provisioned clusters. |

---

## Provisioning Chain

```
ClusterDeployment (user/console creates)
  → hive-controllers watches, validates
  → ClusterProvision (auto-created per attempt)
  → Install Job (runs openshift-install create cluster)
    → Calls cloud provider API: VMs, networking, LBs, DNS, bootstrap
    → 30-60 minutes typical duration
  → Provisioned OCP Cluster (kubeconfig + admin creds stored as Secrets)
  → managedcluster-import-controller detects new cluster
  → ManagedCluster CR auto-created on hub
  → klusterlet deployed to spoke via ManifestWork
  → Cluster becomes Available in ACM
```

Each ClusterDeployment gets its own namespace (matching the cluster name) where install pods, secrets, kubeconfig, and logs reside. If provisioning fails, Hive may create additional ClusterProvision resources for retry attempts.

---

## ClusterPool / ClusterClaim Pattern

ClusterPool pre-provisions clusters and keeps them hibernated for near-instant claiming:

```
ClusterPool (spec.size: N, spec.runningCount: M)
  → hive-controllers provisions N ClusterDeployments
  → (N - M) clusters hibernated, M kept running
  → User creates ClusterClaim (spec.clusterPoolName: pool-name)
  → clusterclaims-controller assigns available cluster
  → Cluster resumes from hibernation
  → managedcluster-import-controller auto-imports
  → On ClusterClaim deletion: cluster returned to pool or destroyed
```

Key fields:
- `spec.size` -- total pool capacity
- `spec.runningCount` -- clusters kept in running state (rest hibernated)
- `spec.lifetime` (on ClusterClaim) -- auto-cleanup duration (e.g., `8h`)

---

## Key Deployments

| Deployment | Namespace | Replicas | Purpose |
|------------|-----------|----------|---------|
| hive-operator | multicluster-engine | 1 | Watches HiveConfig, deploys hive-controllers and hiveadmission in `hive` namespace |
| hive-controllers | hive | 1 | Main reconciler. Watches ClusterDeployment, ClusterPool, ClusterClaim, MachinePool. Orchestrates provisioning. |
| hiveadmission | hive | 2 | Validating/mutating webhook for Hive CRs. Enforces naming, required fields. |
| hive-clustersync | hive | 1 (StatefulSet) | Syncs SelectorSyncSet/SyncSet resources to Hive-provisioned clusters. |
| hive-machinepool | hive | 1 (StatefulSet) | Manages MachinePool scaling on provisioned clusters. |

---

## Webhooks

Hive registers validating webhooks with `failurePolicy: Fail`:
- `clusterdeploymentvalidators.admission.hive.openshift.io`
- `clusterimagesetvalidators.admission.hive.openshift.io`
- `machinepoolvalidators.admission.hive.openshift.io`

If the `hiveadmission` service (port 443, ClusterIP) is unreachable, ALL operations on those resource types return 500 errors. The webhook configuration is managed by hive-operator, NOT the MCH operator.

---

## Namespace Model

| Namespace | Contents |
|-----------|----------|
| `multicluster-engine` | hive-operator deployment |
| `hive` | hive-controllers, hiveadmission, hive-clustersync, hive-machinepool |
| `<cluster-name>` | Per-cluster: ClusterDeployment, install pods, kubeconfig/admin Secrets, logs |

---

## Cross-Subsystem Dependencies

| Depends On | Why |
|------------|-----|
| MCE operator | Creates HiveConfig CR that triggers hive-operator deployment |
| Cloud provider APIs | Install Jobs call AWS/Azure/GCP/vSphere APIs for infrastructure |
| managedcluster-import-controller | Auto-imports provisioned clusters as ManagedClusters |
| klusterlet (Infrastructure) | Deployed to provisioned clusters for hub registration |
| ClusterImageSet controller | Populates available OCP versions for provisioning |
| Console | Cluster creation wizard produces ClusterDeployment CRs |

| Consumed By | Impact When Hive Is Down |
|-------------|--------------------------|
| Console cluster creation | Cannot provision new clusters |
| ClusterPool/ClusterClaim | Cannot claim pre-provisioned clusters |
| HyperShift (KubeVirt provider) | Cannot provision KubeVirt-based hosted clusters |
| ClusterCurator | Cannot trigger upgrades on Hive-provisioned clusters |
