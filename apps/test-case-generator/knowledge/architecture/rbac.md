# RBAC Area Knowledge

## Overview

Fine-Grained RBAC (FG-RBAC) in ACM Console enables granular role-based access control for managed clusters, cluster sets, and namespaces. Uses MulticlusterRoleAssignment (MCRA) and ClusterPermission CRDs.

## Key Concepts

### Scope Types
- **Global Access** -- Access to all clusters and namespaces
- **Single Cluster Set** -- Full or project-level access to one cluster set
- **Multiple Cluster Sets** -- Access across multiple cluster sets
- **Single Cluster** -- Full or project-level access to one cluster
- **Multiple Clusters** -- Access across specific clusters
- **Empty Cluster Set** -- Edge case: cluster set with no bound clusters
- **Common Projects** -- Edge case: overlapping namespaces across cluster sets

### CRDs
- **MulticlusterRoleAssignment (MCRA)** -- Defines role assignments with subject, role, and scope
- **ClusterPermission** -- Applied to managed clusters for namespace-level access
- **ManagedClusterSet** -- Groups clusters for RBAC scoping
- **ManagedClusterSetBinding** -- Binds cluster sets to namespaces

### UI Components
- Role Assignment Wizard -- 7-step wizard for creating MCRAs
- Roles Page -- Lists available roles and their permissions
- User Management Tab -- Cluster set CRB management (separate from FG-RBAC)

## Navigation Routes
- `clusterRoleAssignments`: `/multicloud/infrastructure/clusters/details/:namespace/:name/role-assignments`
- `clusterSetRoleAssignments`: `/multicloud/infrastructure/clusters/sets/details/:id/role-assignments`
- `roles`: `/multicloud/user-management/roles`
- `identities`: `/multicloud/user-management/identities`

## Testing Considerations
- Test with both internal users and OIDC (Direct Authentication) users
- Verify MCRA creation via CLI after UI action
- Check ClusterPermission propagation to managed clusters
- Test scope combinations (cluster set + project level)
- Global cluster set has different role options (no admin)
