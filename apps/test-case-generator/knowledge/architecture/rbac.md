# RBAC Area Knowledge

## Overview

Fine-Grained RBAC (FG-RBAC) in ACM Console enables granular role-based access control for managed clusters, cluster sets, and namespaces. Uses MulticlusterRoleAssignment (MCRA) and ClusterPermission CRDs propagated via ManifestWork to managed clusters.

## Key Components

| Component | Source File | Role |
|-----------|------------|------|
| Role Assignment Wizard | `roleAssignmentWizardHelper.ts` | Constructs MCRA from wizard input |
| Events Handler | `events.ts` | SSE event stream for MCRA updates |
| Username Resolver | `username.ts` | Resolves user/group subjects |
| console-api RBAC endpoints | — | Serves `/rbac/identities`, `/rbac/roles`, `/rbac/role-assignments` |
| MCRA Operator | Hub deployment in MCH namespace | Reconciles MCRA → ClusterPermission |
| `acm-roles` addon | Deployed to managed clusters | Provides scoped role definitions |

## CRDs / Resources

| CRD | API Group | Purpose |
|-----|-----------|---------|
| MulticlusterRoleAssignment (MCRA) | `rbac.open-cluster-management.io/v1alpha1` | Defines role assignment with subject + role + scope |
| ClusterPermission | `rbac.open-cluster-management.io/v1alpha1` | Applied to managed clusters for namespace-level access |
| ManagedClusterSet | `cluster.open-cluster-management.io/v1beta2` | Groups clusters for RBAC scoping |
| ManagedClusterSetBinding | `cluster.open-cluster-management.io/v1beta2` | Binds cluster sets to namespaces |

## Scope Types

- **Global Access** — Access to all clusters and namespaces
- **Single Cluster Set** — Full or project-level access to one cluster set
- **Multiple Cluster Sets** — Access across multiple cluster sets
- **Single Cluster** — Full or project-level access to one cluster
- **Multiple Clusters** — Access across specific clusters
- **Empty Cluster Set** — Edge case: cluster set with no bound clusters
- **Common Projects** — Edge case: overlapping namespaces across cluster sets

## Navigation Routes

| Route Key | Path | Page |
|-----------|------|------|
| `clusterRoleAssignments` | `/multicloud/infrastructure/clusters/details/:namespace/:name/role-assignments` | Cluster role assignments |
| `clusterSetRoleAssignments` | `/multicloud/infrastructure/clusters/sets/details/:id/role-assignments` | Cluster set role assignments |
| `roles` | `/multicloud/user-management/roles` | Available roles list |
| `identities` | `/multicloud/user-management/identities` | User/group identities |

## UI Flows

### Role Assignment Wizard (7 steps)
1. **Select Subject** — User or Group (requires IDP for enumeration)
2. **Select Role** — `acm-vm-fleet:admin`, `acm-vm-extended:view`, etc.
3. **Select Scope Type** — Global, Cluster Set, Cluster, Project
4. **Select Cluster Set** (if applicable)
5. **Select Clusters** (if applicable)
6. **Select Namespaces** (if project-level)
7. **Review and Create** — Shows MCRA YAML preview

### User Management Tab
- Separate from FG-RBAC wizard
- Manages ClusterRoleBindings at the cluster set level
- Uses direct IDP integration for user enumeration

## Setup Prerequisites

- `cluster-permission` enabled in MCH (enabled by default)
- `fine-grained-rbac` enabled in MCH (**disabled by default** — must be explicitly enabled)
- IDP configured for user/group enumeration (HTPasswd or LDAP)
- MCRA and ClusterPermission CRDs registered
- `acm-roles` addon deployed when fine-grained-rbac is enabled
- At least one ManagedClusterSet with bound clusters for scope testing

## Testing Considerations

- Test with both internal users and OIDC (Direct Authentication) users
- Verify MCRA creation via CLI after UI wizard action
- Check ClusterPermission propagation to managed clusters via ManifestWork
- Test scope combinations (cluster set + project level)
- Global cluster set has different role options (no admin role)
- Without IDP: user/group lists are empty but manual role assignment still works
- Known issue: wizard subject name corruption — `roleAssignmentWizardHelper.ts` may append `-system` to subject name
- Known issue: SSE event dropping — `events.ts` may silently filter out MCRA events, preventing UI auto-update
- Known issue: username reversal — `username.ts` reverses name parts (`kube:admin` → `admin:kube`)
