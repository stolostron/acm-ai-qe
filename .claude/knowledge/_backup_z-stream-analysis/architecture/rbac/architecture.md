# RBAC Architecture

Fine-Grained RBAC (FG-RBAC) enables granular access control for ACM resources
using MulticlusterRoleAssignment (MCRA) and ClusterPermission CRDs.

---

## Components

| Component | Type | Namespace | Role |
|-----------|------|-----------|------|
| cluster-permission | Hub deployment | ocm | Creates ClusterPermission resources on spokes based on MCRA |
| rbac-query-proxy | Hub deployment | ocm | Proxies RBAC-filtered queries to the console |

## Key CRDs

| CRD | API Group | Purpose |
|-----|-----------|---------|
| MulticlusterRoleAssignment | rbac.open-cluster-management.io/v1alpha1 | Defines who gets what access where |
| ClusterPermission | rbac.open-cluster-management.io/v1alpha1 | Applied on spoke clusters by cluster-permission controller |

## Prerequisites

- `cluster-permission` enabled in MCH (enabled by default)
- `fine-grained-rbac` enabled in MCH (disabled by default)
- MCRA and ClusterPermission CRDs registered
- IDP users configured (HTPasswd, LDAP) via OAuth cluster config

## RBAC Flow

```
Admin creates MCRA via role assignment wizard
  -> wizard in roleAssignmentWizardHelper.ts
    -> constructs subject name, roles, target clusters
  -> ClusterPermission CR created on hub
  -> cluster-permission controller
    -> evaluates MCRA definition
    -> creates ClusterPermission resources on target spoke clusters
    -> spoke kubelets enforce the permissions
```

## Console Integration

RBAC pages: role assignment wizard at `/multicloud/infrastructure/clusters/managed`
(RBAC tab), permissions page.

IDP user login: non-admin users authenticate via OAuth providers (HTPasswd, LDAP).
The console resolves the current user via `/api/username` endpoint.

SSE events: MCRA create/update/delete events are delivered to the UI via the SSE
endpoint in `events.ts`. If events for `MulticlusterRoleAssignment` kind are
dropped, the RBAC table doesn't auto-update.

## Known Failure Modes

- Subject name corruption: wizardHelper appends `-system` to the subject name
- SSE event dropping: events.ts filters out MCRA events silently
- Username reversal: username.ts reverses the name parts (kube:admin -> admin:kube)
- IDP authentication failure: non-admin users stuck on login form
