# Clusters Area Knowledge

## Overview

Cluster management in ACM Console covers the full lifecycle of managed clusters: creation, import, upgrade, and destruction, plus cluster sets for grouping.

## Key Features
- Cluster creation via various providers (AWS, Azure, vSphere, bare metal, KubeVirt)
- Cluster import and detach
- Cluster upgrade management
- Cluster sets and bindings
- Placement rules and decisions
- Submariner networking

## Navigation Routes
- `clusters`: `/multicloud/infrastructure/clusters`
- `managedClusters`: `/multicloud/infrastructure/clusters/managed`
- `clusterDetails`: `/multicloud/infrastructure/clusters/details/:namespace/:name`
- `clusterSets`: `/multicloud/infrastructure/clusters/sets`
- `clusterSetDetails`: `/multicloud/infrastructure/clusters/sets/details/:id`
- `importCluster`: `/multicloud/infrastructure/clusters/import`

## Testing Considerations
- Cluster operations are state-changing -- use read-only verification in test steps
- Cluster set operations affect RBAC scope
- Import flow requires an available unmanaged cluster
