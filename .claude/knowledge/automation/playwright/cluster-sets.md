# Cluster Sets Area Knowledge Base

Domain knowledge for writing Cluster Sets automation tests.

---

## Test Area

| Directory | Specs |
|-----------|-------|
| `cypress/tests/clusterset/` | 6 specs (actions, RBAC, create, overview, resource assign, user manage) |

---

## Key Files

| File | Purpose |
|------|---------|
| `cypress/views/clusterset/clusterset.js` | Main page object |
| `cypress/views/clusterset/clusterset_overview.js` | Cluster set overview page |
| `cypress/views/clusterset/clusterset_usermanage.js` | User management within cluster sets |
| `cypress/views/clusterset/clusterset_resourceassign.js` | Resource assignment |
| `cypress/views/actions/clusterSetAction.js` | ClusterSet state setup/teardown |
| `cypress/apis/clusterSet.js` | ManagedClusterSet API wrappers |

---

## Navigation

- Path: `constants.clusterSetPath` = `/multicloud/infrastructure/clusters/sets`

---

## API Resources

| Resource | API Path |
|----------|----------|
| ManagedClusterSet | `constants.ocm_cluster_api_v1beta2_path` = `/apis/cluster.open-cluster-management.io/v1beta2` |
| ManagedClusterSetBinding | same API group, namespaced |

---

## Tags

`@CLC`, `@e2e`, `@clusterset`

---

## Key Patterns

- `default` and `global` cluster sets are system-managed -- never delete
- ClusterSet RBAC: users need ManagedClusterSetBinding in their namespace to see clusters in a set
- Resource assignment: clusters and cluster pools can be assigned to sets
- User management: ClusterRoleBindings scoped to cluster set
- The "Role assignments" tab on cluster set details page is the cluster set entry point for RBAC wizard (see rbac.md)
