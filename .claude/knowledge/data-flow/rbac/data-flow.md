# RBAC -- Data Flow

## End-to-End MCRA Propagation

```
Hub: MCRA created (via console wizard or YAML)
  |
  v
Hub: MCRA Operator reconciles
  |   - evaluates scope (global / cluster-set / cluster / project)
  |   - resolves target clusters from scope
  v
Hub: ClusterPermission created in each target cluster's namespace
  |
  v
Hub: ManifestWork generated from ClusterPermission spec
  |
  v
Hub -> Spoke: work-agent applies ManifestWork payload
  |
  v
Spoke: Role/RoleBinding/ClusterRole/ClusterRoleBinding created
  |
  v
Spoke: Kubernetes RBAC enforces permissions
```

---

## Step 1: MCRA Creation

User creates MCRA via console RBAC wizard or `oc apply`:
- Selects subject (user, group, service account)
- Selects scope type (global, cluster set, cluster)
- Selects roles to assign
- Optionally scopes to specific projects within clusters

**Failure:** Console wizard state bugs -> MCRA spec doesn't match UI selections
(ACM-29966, cluster selection saves all instead of selected). YAML creation ->
validation webhook rejects invalid spec.

### Console Wizard Detail

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

---

## Step 2: MCRA Operator Reconciliation

MCRA operator watches MCRA resources and generates ClusterPermission:

1. Reads MCRA spec
2. Resolves target clusters:
   - **Global:** All managed clusters
   - **ClusterSet:** Clusters in specified ManagedClusterSets
   - **Cluster:** Specific named clusters
3. For each target cluster, creates/updates ClusterPermission in that cluster's
   namespace on hub
4. ClusterPermission contains role definitions and subject bindings

**Failure:** Concurrent PATCH -> controller panic (ACM-24737). Operator down ->
ClusterPermission not created, permissions not propagated. Stale in-memory
state -> partial updates.

---

## Step 3: ClusterPermission to ManifestWork

ClusterPermission triggers ManifestWork generation:
1. Controller reads ClusterPermission spec
2. Generates ManifestWork with RBAC resource payloads:
   - ClusterRoleBinding for cluster-scoped roles
   - RoleBinding for project-scoped roles in each target namespace
   - Custom ClusterRole definitions if needed
3. ManifestWork created in target cluster's namespace on hub

**Failure:** ClusterPermission controller OOM at scale (ACM-24032) -> ManifestWork
not generated. Too many ManifestWorks cached -> memory pressure.

### ClusterPermission Distribution (Console Perspective)

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

---

## Step 4: ManifestWork Delivery to Spoke

work-agent (part of klusterlet) on spoke picks up ManifestWork:
1. Pulls ManifestWork from hub
2. Applies RBAC resources to spoke cluster
3. Reports applied status back to hub

**Failure:** klusterlet disconnected -> ManifestWork pending, RBAC not applied.
Admission controller rejects -> ManifestWork applied=false.

---

## Step 5: Spoke-Side Enforcement

Standard Kubernetes RBAC enforces the propagated permissions:
- ClusterRoleBindings grant cluster-scoped access
- RoleBindings in specific namespaces grant project-scoped access
- Subject can now access resources per assigned roles

**Failure:** Role doesn't exist on spoke (acm-roles addon not deployed) ->
RoleBinding references missing ClusterRole. kubevirt roles missing labels ->
aggregate API doesn't pick them up for search integration.

---

## Console RBAC Query Flow

```
Console Browser
  |
  v
console-api (/rbac/identities, /rbac/roles, /rbac/role-assignments)
  |
  v
Hub API Server
  |   - queries MCRA resources
  |   - queries OAuth IDP for users/groups
  |   - queries ClusterPermission for status
  v
Console Browser (renders User Management tab)
```

### Identity Enumeration

console-api queries the hub's OAuth configuration to enumerate users and groups.
IDP must be configured for this to return results.

**Failure:** No IDP -> empty user/group lists. IDP connectivity issue -> timeout
on identity pages. Large user base -> slow response, intermittent rendering
(ACM-26185).

### Role Assignment Display

console-api reads MCRAs and their status to display current assignments:
1. Lists all MCRA resources
2. Resolves each MCRA's effective scope
3. Shows per-cluster/per-project breakdown

**Failure:** console-api down -> all RBAC pages return 500. MCRA status
conditions stale -> display shows outdated state.

---

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

---

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

---

## Search RBAC Integration Flow

```
RBAC User -> Console -> kubevirt-plugin -> search-api
                                              |
                                              v
                                         RBAC Filter
                                              |
                                              v
                                    Check user's MCRA scope
                                              |
                                              v
                                    Filter search results
                                    to permitted clusters/
                                    namespaces/resource kinds
                                              |
                                              v
                                    Return filtered results
```

Search-api evaluates the requesting user's permissions:
1. Checks standard Kubernetes RBAC for `list` verb access
2. If fine-grained RBAC enabled, checks MCRA-defined scope
3. Filters search results to only include resources within scope
4. Aggregate API picks up roles from ClusterPermission fields

**Failure:** Aggregate API misses kubevirt roles (ACM-24887) -> VM resources
filtered out despite valid ClusterPermission. Search checks `list` but not `*` ->
wildcard verb users see empty results.

---

## Failure Modes at Each Layer

### MCRA creation fails
- **Symptom:** Wizard shows success but no MCRA created. Or MCRA created with wrong spec.
- **Detection:** `oc get mcra -A` -- check if MCRA exists with correct spec.

### MCRA operator not reconciling
- **Symptom:** MCRA exists but no ClusterPermission created.
- **Detection:** `oc get clusterpermission -n {cluster}` -- empty.
  Check MCRA operator pod logs.

### ClusterPermission not propagated
- **Symptom:** ClusterPermission exists on hub but no ManifestWork.
- **Detection:** `oc get manifestwork -n {cluster} | grep permission`

### ManifestWork not applied on spoke
- **Symptom:** ManifestWork exists but spoke has no Role/RoleBindings.
- **Detection:** On spoke: `oc get rolebindings,clusterrolebindings | grep {user}`

### Roles missing on spoke
- **Symptom:** RoleBinding exists but references non-existent ClusterRole.
- **Detection:** `oc get clusterrole | grep open-cluster-management`
  Check if acm-roles addon is deployed.

### Search not honoring RBAC
- **Symptom:** RBAC user sees wrong resources in search/VM views.
- **Detection:** Compare `oc auth can-i` results with search results for same user.

### Console-Specific Failure Points

| Point | What Breaks | Symptom |
|-------|------------|---------|
| Subject name corrupted | ClusterPermission targets wrong user | Permissions don't work for intended user |
| MCRA SSE events dropped | RBAC table doesn't auto-update | Resource created but not visible until refresh |
| ManagedClusterSet SSE dropped | ClusterSet table doesn't update | Same stale UI pattern |
| Username reversed | User menu shows wrong name | RBAC tests timeout at login |
| IDP not configured | Non-admin users can't authenticate | Blank page or stuck on login form |
