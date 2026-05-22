# RBAC Area Knowledge Base

Domain knowledge for writing RBAC automation tests in `clc-ui-e2e` (Cypress) and `console-e2e` (Playwright).

---

## Test Users

All RBAC test users follow the `clc-e2e-*` prefix convention. Created by `build/gen-rbac.sh`.

| User Pattern | Purpose |
|-------------|---------|
| `clc-e2e-admin-cluster` | Cluster admin |
| `clc-e2e-admin-ns` | Namespace admin |
| `clc-e2e-view` | View-only user |
| `clc-e2e-edit-test` | Edit test user |
| `clc-e2e-operator` | Operator (group-based) |
| `clc-e2e-edgecase-*` | Edge case test users |
| `clc-e2e-clusterset-*` | Cluster set entry tests |
| `clc-e2e-{specName}-{polarionId}` | Spec-specific users (e.g., `clc-e2e-clusterset-61863`) |

**Authentication:**
- IDP name: `clc-e2e-htpasswd`
- Password: `test-RBAC-4-e2e`
- Login: `cy.login(user, Cypress.env('CLC_RBAC_PASS'), Cypress.env('CLC_OC_IDP'))`

---

## Required Environment Variables

| Variable | Maps To | Purpose |
|----------|---------|---------|
| `CYPRESS_CLC_OC_IDP` | `Cypress.env('CLC_OC_IDP')` | IDP name for RBAC test user login |
| `CYPRESS_CLC_RBAC_PASS` | `Cypress.env('CLC_RBAC_PASS')` | Password for all clc-e2e test users |
| `CYPRESS_VIRT_SPOKE_CLUSTER` | `Cypress.env('VIRT_SPOKE_CLUSTER')` | Spoke cluster name (may be comma-separated) |
| `CYPRESS_HUB_API_URL` | `Cypress.env('HUB_API_URL')` | Hub API URL for cleanup requests |

**Guard pattern (ALWAYS add in `before` and `beforeEach`):**
```javascript
const spokeCluster = (Cypress.env('VIRT_SPOKE_CLUSTER') || '').split(',')[0].trim()

before(function () {
  if (!spokeCluster) {
    this.skip('VIRT_SPOKE_CLUSTER environment variable is not set - skipping test')
  }
})
```

---

## API Resources

### MCRA (MultiClusterRoleAssignment)

| Property | Value |
|----------|-------|
| API Group | `rbac.open-cluster-management.io` |
| API Version | `v1beta1` |
| Kind | `MultiClusterRoleAssignment` |
| Namespace | `open-cluster-management-global-set` |
| Constants path | `constants.mcra_api_path` = `/apis/rbac.open-cluster-management.io/v1beta1` |
| Constants ns | `constants.mcra_namespace` = `open-cluster-management-global-set` |

Key MCRA structure (v1beta1):
```yaml
spec:
  subject:          # singular object, NOT array
    name: "username"
    kind: "User"
    apiGroup: "rbac.authorization.k8s.io"
  roleAssignments:
    - clusterRole:
        name: "kubevirt.io:view"
      clusterSelection:
        placements:
          - name: "clusters-xxx"
```

### Placement

| Property | Value |
|----------|-------|
| API Group | `cluster.open-cluster-management.io` |
| API Version | `v1beta1` |
| Namespace | `open-cluster-management-global-set` (same as MCRA) |
| Constants path | `constants.ocm_cluster_api_v1beta1_path` |

Placement naming convention (wizard-generated):
- `clusters-{hash}` -- individual cluster selection
- `cluster-sets-{hash}` -- cluster set selection
- System placements: `global`, `default` (never modify these)

Label for wizard reuse: `open-cluster-management.io/managed-by: console`

### RBAC (ClusterRoleBinding / RoleBinding)

| Property | Value |
|----------|-------|
| API Group | `rbac.authorization.k8s.io` |
| API Version | `v1` |
| Constants path | `constants.rbac_api_path` = `/apis/rbac.authorization.k8s.io/v1` |

---

## Existing Files and Utilities

### API Files

| File | Exports | Purpose |
|------|---------|---------|
| `cypress/apis/mcra.js` | `listMCRAs`, `getMCRA`, `deleteMCRA`, `listPlacements`, `getPlacement`, `deletePlacement`, `patchPlacement`, `MCRA_API_GROUP`, `MCRA_API_VERSION`, `PLACEMENT_API_GROUP`, `PLACEMENT_API_VERSION` | MCRA + Placement CRUD |
| `cypress/apis/rbac.js` | `getUser`, `getClusterRole`, `getClusterRolebinding`, `createClusterRolebinding`, `deleteClusterRolebinding`, `getRolebinding`, `createRolebinding`, `deleteRolebinding` | K8s RBAC CRUD |

### Actions Layer

| File | Exports | Key Methods |
|------|---------|-------------|
| `cypress/views/actions/rbac.js` | `rbacActions` | `shouldHaveClusterRolebindingForUser(name, role, user)` -- idempotent create; `deleteClusterRolebinding(name)`; `shouldHaveRolebindingForUser(binding, ns, role, user)` -- namespaced; `deleteRolebinding(binding, ns)` |
| `cypress/views/actions/roleAssignment.js` | `roleAssignmentActions` | `deleteMCRAForUser(userName)` -- delete all MCRAs for user; `cleanupOrphanedPlacements()` -- delete orphaned + label unlabeled; `deleteAllMCRAsAndPlacements()` -- nuclear cleanup |

### View Files (Page Objects)

| File | Key Exports |
|------|-------------|
| `cypress/views/virtualization/roleAssignmentWizard.js` | `WIZARD_SELECTORS`, `SCOPE_TYPES`, `CLUSTER_SET_ACCESS_LEVELS`, `CLUSTER_ACCESS_LEVELS`, `navigateToUserRoleAssignmentsTab()`, `navigateToClusterSetRoleAssignmentsTab()`, `openCreateRoleAssignmentWizard()`, `selectScopeType()`, `selectClusterSets()`, `selectClusters()`, `selectClusterSetAccessLevel()`, `selectClusterAccessLevel()`, `selectProjects()`, `selectRole()`, `selectIdentity()`, `clickNext()`, `clickBack()`, `verifyReviewStep()`, `clickCreateAndVerifySuccess()`, `dismissWizardIfOpen()`, `verifyRoleAssignmentStatus()`, `verifyCommonProjectsShown()`, `createCommonProject()` |

### Test Helpers

| File | Purpose |
|------|---------|
| `cypress/tests/rbac/virtualization/helpers/roleAssignment.js` | Shared test data and helper functions for role assignment specs |
| `cypress/tests/rbac/virtualization/helpers/fleetVirtualization.js` | Fleet Virt RBAC helper functions |

---

## Spec File Patterns

### Standard Structure

```javascript
describe('RBAC UI - Feature Name', {
  tags: ['@CLC', '@e2e-virt', '@rbac', '@virtualization', '@roleassignment'],
  retries: { runMode: 1, openMode: 0 },
}, () => {
  const testUser = 'clc-e2e-{purpose}-{polarionId}'
  const spokeCluster = (Cypress.env('VIRT_SPOKE_CLUSTER') || '').split(',')[0].trim()

  before(function () {
    if (!spokeCluster) this.skip('VIRT_SPOKE_CLUSTER not set')
  })

  beforeEach(function () {
    if (!spokeCluster) this.skip('VIRT_SPOKE_CLUSTER not set')
    cy.loginViaAPI()
    cy.setAPIToken()
    roleAssignmentActions.deleteMCRAForUser(testUser)
    roleAssignmentActions.cleanupOrphanedPlacements()
    dismissWizardIfOpen()
  })

  after(function () {
    if (!spokeCluster) return
    cy.loginViaAPI()
    cy.setAPIToken()
    roleAssignmentActions.deleteMCRAForUser(testUser)
    roleAssignmentActions.cleanupOrphanedPlacements()
  })

  it('RHACM4K-XXXXX: Test description', { tags: ['@RHACM4K-XXXXX'] }, function () {
    // Steps using view helpers
  })
})
```

### Tags

| Tag | When |
|-----|------|
| `@CLC` | Always |
| `@e2e-virt` | Virt RBAC tests (run in e2e-virt stage) |
| `@rbac` | RBAC tests |
| `@virtualization` | Virtualization feature |
| `@roleassignment` | Role assignment wizard tests |
| `@RHACM4K-XXXXX` | Polarion ID on `it()` |

---

## Existing Spec Coverage (26 specs)

| Spec File | Area |
|-----------|------|
| `virt_roleAssignment.spec.js` | Core RA wizard (identity entry) |
| `virt_creation.spec.js` | RA creation flows (all scope types) |
| `virt_clusterSetEntry.spec.js` | RA from cluster set details page |
| `virt_clusterScope.spec.js` | Cluster-scoped RA |
| `virt_editRoleAssignment.spec.js` | Edit existing RA |
| `virt_deleteRoleAssignment.spec.js` | Delete RA |
| `virt_commonProjects.spec.js` | Common projects in cluster scope |
| `virt_edgeCases.spec.js` | Edge cases (empty set, no clusters) |
| `virt_treeView.spec.js` | Fleet Virt tree view with RBAC |
| `virt_search.spec.js` | VM search with RBAC |
| `virt_searchClusterProxy.spec.js` | Search cluster proxy access |
| `virt_actions.spec.js` | VM actions with RBAC |
| `virt_fullFleetAdmin.spec.js` | Full fleet admin validation |
| `virt_hubViewRole.spec.js` | Hub view role validation |
| `virt_managedAdminRole.spec.js` | Managed cluster admin role |
| `virt_managedViewRole.spec.js` | Managed cluster view role |
| `virt_readOnlyFleetViewer.spec.js` | Read-only fleet viewer |
| `virt_roleVisibility.spec.js` | Role visibility based on RBAC |
| `virt_standardRoles.spec.js` | Standard K8s/KubeVirt roles |
| `virt_status.spec.js` | RA status verification |
| `virt_reviewStepDiff.spec.js` | Review step content validation |
| `virt_clusterSetColumn.spec.js` | Cluster set column in RA table |
| `virt_spokeClusterNamespace.spec.js` | Spoke cluster namespace access |
| `virt_subjectContent.spec.js` | Subject content validation |
| `virt_idpLogin.spec.js` | IDP login flow |
| `virt_miscRbac.spec.js` | Miscellaneous RBAC checks |

---

## Role Assignment Wizard Structure (ACM 2.16)

### Entry Points

1. **Identity entry** (User Management > Identities > User > Role assignments tab): Scope -> Roles -> Review
2. **Role entry** (Roles page): Identities -> Scope -> Review
3. **Cluster Set entry** (Cluster Sets > Detail > Role assignments tab): Identities -> Granularity -> Roles -> Review (scope pre-selected, "Select scope" hidden)

### Scope Types

| Scope | Granularity Options | What Gets Created |
|-------|--------------------|--------------------|
| Global access | (none) | MCRA with global placement |
| Select cluster sets | "Cluster set role assignment" or "Project role assignment" | MCRA with cluster-set placement |
| Select clusters | "Cluster role assignment" or "Project role assignment" | MCRA with cluster placement |

### Key Selectors (from `WIZARD_SELECTORS`)

| Selector | ID/Class |
|----------|----------|
| Wizard container | `.pf-v6-c-wizard` |
| Scope type dropdown | `#scope-type` |
| Cluster set access level | `#clusters-set-access-level` |
| Cluster access level | `#clusters-access-level` |
| Wizard footer | `.pf-v6-c-wizard__footer` |
| Primary button | `button.pf-m-primary` |
| Wizard nav | `.pf-v6-c-wizard__nav` |

---

## Gotchas

- MCRA v1beta1 uses `spec.subject` (singular object), NOT `spec.subjects` (array) -- API mismatch with RBAC v1 conventions
- Placements are SHARED across MCRAs -- deterministic names based on cluster selection hash. Always clean up orphaned placements.
- `cy.login()` for RBAC users requires IDP: `cy.login(user, password, idp)` -- not `cy.loginViaAPI()` which uses kubeadmin
- `VIRT_SPOKE_CLUSTER` may be comma-separated (`spoke1,spoke2`). Always split and take first: `.split(',')[0].trim()`
- PF6 enabled/disabled: custom Chai overrides in `e2e.js` handle `pf-m-aria-disabled` and `aria-disabled`
- `beforeEach` MUST run cleanup before every attempt (including retries) for retry safety
- `build/` changes (user setup, IDP config) go on separate branch -- never modify in test branches
- **OIDC/Keycloak clusters:** `cy.login()` and `cy.loginViaAPI()` do NOT work. Use `loginViaKeycloak()` from `cypress/views/common/keycloakAuth.js` which detects Keycloak (`#username`) vs OCP (`#inputUsername`) login forms automatically. Sets `DIRECT_AUTH_DETECTED` flag for environment guards. API cleanup uses the console proxy (`/api/proxy/plugin/mce/console/multicloud/apis/...`) since bearer tokens from Keycloak `admin-cli` don't authenticate to the K8s API server. The `start-tests.sh` script has OIDC fallback: if `oc login` fails, it derives `CYPRESS_BASE_URL` from the API URL and skips oc-dependent setup.
