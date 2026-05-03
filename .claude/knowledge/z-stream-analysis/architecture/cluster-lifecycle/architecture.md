# Cluster Lifecycle (CLC) Architecture

Cluster Lifecycle covers cluster creation, import, upgrade, destruction, and
pool management. It's the largest test area in the CLC E2E pipeline.

---

## Components

| Component | Type | Namespace | Pod Label | Role |
|-----------|------|-----------|-----------|------|
| hive-operator | Hub deployment | hive | app=hive-operator | Manages Hive controllers and CRDs |
| hive-controllers | Hub deployment | hive | app=hive-controllers | Provisions and manages clusters via ClusterDeployment |
| hive-clustersync | Hub deployment | hive | app=hive-clustersync | Syncs cluster state between Hive and managed clusters |
| managedcluster-import-controller-v2 | Hub deployment | multicluster-engine | app=managedcluster-import-controller-v2 | Handles cluster import and klusterlet deployment |
| cluster-curator-controller | Hub deployment | ocm | app=cluster-curator-controller | Manages automation workflows (Ansible pre/post hooks) |
| cluster-manager | Hub deployment | open-cluster-management-hub | app=cluster-manager-registration-controller | Registration and work distribution |

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

## Webhooks (Critical)

Hive registers several validating webhooks with `failurePolicy=Fail`:
- `clusterdeploymentvalidators.admission.hive.openshift.io`
- `clusterimagesetvalidators.admission.hive.openshift.io`
- `machinepoolvalidators.admission.hive.openshift.io`

If ANY of these webhook services are unreachable, ALL operations on those
resource types fail with 500 "failed calling webhook" errors. The webhook
configuration is managed by the Hive operator, NOT the MCH operator.

## Console Integration

CLC pages: `/multicloud/infrastructure/clusters/managed`,
`/multicloud/infrastructure/clusters/discovered`,
`/multicloud/infrastructure/clusters/sets`

The cluster creation wizard constructs ClusterDeployment and related resources.
Key backend interaction: `frontend/src/resources/resource.ts` builds API paths.

Navigation: `cypress/views/header.js` -- `openMenu()` and `goToClusters()`
functions. The perspective switcher race condition (synchronous `$body.find()`)
affects ALL CLC tests that navigate to the clusters page.

## Cluster Operations

| Operation | Resources Created | Key API |
|-----------|-------------------|---------|
| Create cluster | ClusterDeployment, MachinePool, InstallConfig | hive.openshift.io/v1 |
| Import cluster | ManagedCluster, KlusterletAddonConfig | cluster.open-cluster-management.io/v1 |
| Destroy cluster | Deletes ClusterDeployment | hive.openshift.io/v1 |
| Transfer cluster to set | Updates ManagedCluster labels | cluster.open-cluster-management.io/v1 |
| Upgrade cluster | ClusterCurator with upgrade spec | cluster.open-cluster-management.io/v1beta1 |
