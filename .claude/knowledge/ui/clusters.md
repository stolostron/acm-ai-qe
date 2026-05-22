# Clusters Area Knowledge

## Overview

Cluster management in ACM Console covers the full lifecycle of managed clusters: creation (provisioning), import, upgrade, and destruction, plus cluster sets for grouping and placement for scheduling.

## Key Components

| Component | Namespace | Role |
|-----------|-----------|------|
| `hive-operator` | hive | Manages Hive controllers |
| `hive-controllers` | hive | Provisions infrastructure via cloud APIs |
| `hive-clustersync` | hive | Syncs cluster state |
| `managedcluster-import-controller-v2` | multicluster-engine | Handles import and klusterlet deployment |
| `cluster-curator-controller` | ocm | Manages upgrade workflows |
| `cluster-manager` | open-cluster-management-hub | Registration and work distribution |
| `placement-controller` | open-cluster-management-hub | Evaluates Placement resources |
| klusterlet | open-cluster-management-agent (spoke) | Spoke agent for registration |

## CRDs / Resources

| CRD | API Group | Purpose |
|-----|-----------|---------|
| ManagedCluster | `cluster.open-cluster-management.io/v1` | Represents a managed cluster |
| ManagedClusterSet | `cluster.open-cluster-management.io/v1beta2` | Groups clusters |
| ManagedClusterSetBinding | `cluster.open-cluster-management.io/v1beta2` | Binds cluster sets to namespaces |
| ClusterDeployment | `hive.openshift.io/v1` | Cluster provisioning specification |
| ClusterPool | `hive.openshift.io/v1` | Pre-provisioned cluster pool |
| ClusterClaim | `hive.openshift.io/v1` | Claims a cluster from a pool |
| ClusterCurator | `cluster.open-cluster-management.io/v1beta1` | Upgrade workflow orchestration |
| ClusterImageSet | `hive.openshift.io/v1` | Available OCP versions for provisioning |
| HostedCluster/NodePool | `hypershift.openshift.io/v1beta1` | HyperShift hosted control planes |

## Navigation Routes

| Route Key | Path | Page |
|-----------|------|------|
| `clusters` | `/multicloud/infrastructure/clusters` | Clusters overview |
| `managedClusters` | `/multicloud/infrastructure/clusters/managed` | Managed clusters list |
| `clusterDetails` | `/multicloud/infrastructure/clusters/details/:namespace/:name` | Cluster details |
| `clusterSets` | `/multicloud/infrastructure/clusters/sets` | Cluster sets |
| `clusterSetDetails` | `/multicloud/infrastructure/clusters/sets/details/:id` | Cluster set details |
| `importCluster` | `/multicloud/infrastructure/clusters/import` | Import cluster flow |
| `discoveredClusters` | `/multicloud/infrastructure/clusters/discovered` | Discovered clusters |

## Three Core Flows

### 1. Create (Provisioning)
ClusterDeployment → hive-controllers → cloud API provisioning → install pod → auto-import → klusterlet → ManagedCluster Available

### 2. Import
ManagedCluster CR → import-controller → klusterlet manifests → spoke registration
- Manual: user applies klusterlet YAML to target cluster
- Auto: import controller generates and applies manifests

### 3. Upgrade
ClusterCurator → optional Ansible hooks (AAP) → OCP ClusterVersion update
- Curator tracks upgrade progress and reports status

## Provider-Specific Flows

| Provider | Key Fields | Notes |
|----------|-----------|-------|
| AWS | Region, Base Domain, Credentials Secret | Most common test target |
| Azure | Resource Group, Base Domain, Credentials Secret | Requires subscription ID |
| vSphere | vCenter URL, Datacenter, Credentials | Requires network config |
| Bare Metal | BMH resources, bootstrap ISO | Longest provisioning time |
| KubeVirt | Namespace, Memory, CPUs | Nested virtualization |

## Hive Webhooks (Critical)

Hive registers validating webhooks with `failurePolicy=Fail`:
- `clusterdeploymentvalidators.admission.hive.openshift.io`
- `clusterimagesetvalidators.admission.hive.openshift.io`

If webhook service is unreachable, ALL ClusterDeployment and ClusterImageSet operations fail with 500 errors.

## Translation Keys

| Key | English Text | Context |
|-----|-------------|---------|
| `Clusters` | "Clusters" | Navigation tab |
| `Managed clusters` | "Managed clusters" | Tab header |
| `Cluster sets` | "Cluster sets" | Tab header |
| `Create cluster` | "Create cluster" | Button |
| `Import cluster` | "Import cluster" | Button |
| `Destroy cluster` | "Destroy cluster" | Action |
| `Detach cluster` | "Detach cluster" | Action |
| `Upgrade available` | "Upgrade available" | Status badge |
| `Hibernate cluster` | "Hibernate cluster" | Action (Hive-provisioned only) |

## Setup Prerequisites

- Hive enabled and webhook configured
- Cloud credentials stored as Secrets in the cluster namespace
- HiveConfig CR for global behavior settings
- For upgrades: ClusterCurator requires ClusterVersion API access
- For HyperShift: hypershift-addon-operator and HyperShift Operator installed
- At least one managed cluster with AVAILABLE=True for testing

## Testing Considerations

- Cluster operations are state-changing — use read-only verification in test steps where possible
- Cluster set operations affect RBAC scope (ManagedClusterSetBinding)
- Import flow requires an available unmanaged cluster
- Detach semantics: must NOT delete hosting namespace for hosted clusters
- Known issue: perspective switcher race condition in OCP 4.20+ (use `perspective-switcher-toggle` instead of `cluster-dropdown-toggle`)
- Known issue: ClusterCurator incompatible with OCP 4.21 upgrade API
- Provisioning tests are long-running (30+ minutes) — design test cases with verification checkpoints
