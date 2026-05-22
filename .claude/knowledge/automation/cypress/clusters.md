# Clusters Area Knowledge Base

Domain knowledge for writing Cluster Lifecycle automation tests.

---

## Test Areas

| Directory | Scope |
|-----------|-------|
| `cypress/tests/clusters/managedClusters/create/` | Cluster creation (AWS, Azure, GCP, vSphere, BMC) |
| `cypress/tests/clusters/managedClusters/destroy/` | Cluster teardown (detach, destroy) |
| `cypress/tests/clusters/managedClusters/` | Cluster actions, addons, CSV export, machine pools |

---

## Key Files

| File | Purpose |
|------|---------|
| `cypress/views/clusters/managedCluster.js` | Main page object (~2500 lines). Exports: `managedClustersSelectors`, `clustersMethods`, `managedClusterDetailMethods`, `managedClustersMethods`, `managedClustersUIValidations` |
| `cypress/views/clusters/centrallyManagedClusters.js` | CIM/AI-assisted install page object |
| `cypress/views/clusters/clusterPools.js` | Cluster pools page object |
| `cypress/views/actions/clusterAction.js` | Cluster state setup/teardown actions |
| `cypress/apis/cluster.js` | ManagedCluster CRUD API wrappers |
| `cypress/apis/hive.js` | Hive ClusterDeployment API wrappers |

---

## Navigation Paths

| Path | Constant |
|------|----------|
| Cluster list | `constants.managedclustersPath` = `/multicloud/infrastructure/clusters/managed` |
| Cluster detail | `constants.managedclusterOverviewPath` = `/multicloud/infrastructure/clusters/details` |
| Create cluster | `constants.createClustersPath` = `/multicloud/infrastructure/clusters/create` |
| Import cluster | `constants.importClustersPath` = `/multicloud/infrastructure/clusters/import` |

---

## API Resources

| Resource | API Path Constant |
|----------|-------------------|
| ManagedCluster | `constants.ocm_cluster_api_v1_path` = `/apis/cluster.open-cluster-management.io/v1` |
| ClusterDeployment | `constants.hive_api_path` = `/apis/hive.openshift.io/v1` |
| ManagedClusterAddOn | `constants.ocm_addon_api_path` = `/apis/addon.open-cluster-management.io/v1alpha1` |

---

## Tags

`@CLC`, `@e2e`, `@create` (creation), `@destroy` (teardown), `@clusteractions`

---

## Key Patterns

- `cy.getClusterListRow(name)` -- always use for table row lookup (uses `data-ouia-component-id`)
- Creation wizard is multi-step -- use `managedClustersMethods.clickCreate()`, `fillClusterDetails()`
- Cluster lifecycle: create -> ready -> detach -> destroy
- Credential must exist before cluster creation (see credentials.md)
- `testIsolation: false` in cypress config -- tests share state within a spec
