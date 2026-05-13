# RBAC Data Flow

How role assignments flow from the wizard to spoke cluster enforcement.

---

## Role Assignment Creation

```
Admin navigates to role assignment wizard
  -> frontend renders wizard steps:
     1. Select user/group (subject)
     2. Select roles (e.g., acm-vm-fleet:admin, acm-vm-extended:view)
     3. Select target clusters/clustersets
     4. Review and create
  -> wizardDataToRoleAssignmentToSave() in roleAssignmentWizardHelper.ts
    -> constructs MCRA object with:
       subject: { name: <userName>, kind: User/Group }
       roles: [<role1>, <role2>]
       clusterSelector: <placement criteria>
  -> POST to Kubernetes API via console proxy
  -> MCRA CR created on hub
```

Bug injection point: roleAssignmentWizardHelper.ts can append '-system' to
the subject name, creating the MCRA for a non-existent user.

## ClusterPermission Distribution

```
MCRA CR created on hub
  -> cluster-permission controller watches MCRAs
    -> evaluates target clusters from clusterSelector
    -> for each target cluster:
       -> creates ClusterPermission CR in the cluster's namespace
       -> ClusterPermission contains RoleBindings/ClusterRoleBindings
    -> spoke klusterlet applies the bindings
  -> User now has permissions on the target clusters
```

## IDP User Authentication

```
Non-admin user navigates to ACM console
  -> OCP OAuth server handles authentication
    -> checks OAuth cluster config for IDP providers
    -> HTPasswd: validates username/password against secret
    -> LDAP: validates against LDAP server
  -> User gets OAuth token
  -> Console loads with user's identity
  -> /api/username returns the user's name
  -> UI displays username in the header menu
```

If username.ts reverses the name, RBAC tests that verify the user menu fail
with timeout ("Unable to find User menu").

## SSE Event Delivery for RBAC Resources

```
Admin creates/modifies/deletes an MCRA
  -> Kubernetes API emits watch event
  -> events.ts receives the event
  -> eventFilter() checks:
     - resource.kind == 'MulticlusterRoleAssignment'?
     - If filtered out: event silently dropped
     - If passed: SSE pushes to connected browsers
  -> UI table auto-refreshes (if event delivered)
  -> UI table stays stale (if event dropped -- manual refresh needed)
```

## Failure Points

| Point | What breaks | Symptom |
|-------|------------|---------|
| Subject name corrupted | ClusterPermission targets wrong user | Permissions don't work for intended user |
| MCRA SSE events dropped | RBAC table doesn't auto-update | Resource created but not visible until refresh |
| ManagedClusterSet SSE dropped | ClusterSet table doesn't update | Same stale UI pattern |
| Username reversed | User menu shows wrong name | RBAC tests timeout at login |
| IDP not configured | Non-admin users can't authenticate | Blank page or stuck on login form |
