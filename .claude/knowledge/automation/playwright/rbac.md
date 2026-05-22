# FG-RBAC Area Knowledge Base

Domain knowledge for writing Fine-Grained RBAC automation tests in `console-e2e` (Playwright).

> **As-built (May 2026):** `presets.ts` has **2** RBAC users (`fg-rbac-admin`, `fg-rbac-view`). `rbac-test.ts` + `rbac-auth.setup.ts` exist. **`src/tests/fg-rbac/`**, **`fg-rbac-test.ts`**, **`McraService`**, and FG-RBAC page objects are **not in the repo yet** — sections below describing those files are **target design**. Verify with `ls`/`Glob` before importing.

---

## Test Users

All RBAC test users follow the `clc-e2e-*` prefix convention. Created by `build/gen-rbac.sh` in the clc-ui repo.

| User Pattern | Purpose |
|-------------|---------|
| `clc-e2e-global-61726` | Global access test user |
| `clc-e2e-managed-admin` | Managed admin (extended:admin + kubevirt:view) |
| `clc-e2e-admin-cluster` | Cluster admin |
| `clc-e2e-admin-ns` | Namespace admin |
| `clc-e2e-view` | View-only user |
| `clc-e2e-{specName}-{polarionId}` | Spec-specific users |

**Authentication:**
- IDP name: `clc-e2e-htpasswd`
- Password: `test-RBAC-4-e2e` (set via `RBAC_TEST_PASSWORD` or `RBAC_MANAGED_ADMIN_PASSWORD`)
- Login: via storageState (`.auth/{role}.json` from `rbac-auth.setup.ts`). Use `asUser(role)` from `rbac-test.ts` today. **Planned:** `fg-rbac-test.ts` / `asVirtUser` wrappers — not in repo. Users in `presets.ts`, filtered by `RBAC_DOMAIN`.

---

## Required Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `RBAC_TEST_PASSWORD` | Yes (RBAC tests) | -- | Password for clc-e2e test users |
| `RBAC_TEST_USER` | No | `clc-e2e-global-61726` | Primary test user |
| `RBAC_IDP` | No | `clc-e2e-htpasswd` | IDP name |
| `RBAC_MANAGED_ADMIN_PASSWORD` | No | Falls back to `RBAC_TEST_PASSWORD` | Managed admin user password |
| `RBAC_MANAGED_ADMIN_USER` | No | `clc-e2e-managed-admin` | Managed admin username |
| `RBAC_SPOKE_CLUSTER` | No | Falls back to `VIRT_SPOKE_CLUSTER` | Spoke cluster for RBAC tests |

---

## API Resources

### MCRA (MultiClusterRoleAssignment)

| Property | Value |
|----------|-------|
| API Group | `rbac.open-cluster-management.io` |
| API Version | `v1beta1` |
| Kind | `MultiClusterRoleAssignment` |
| Namespace | `open-cluster-management-global-set` |

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

Placement naming convention (wizard-generated):
- `clusters-{hash}` -- individual cluster selection
- `cluster-sets-{hash}` -- cluster set selection
- System placements: `global`, `default` (never modify these)

Label for wizard reuse: `open-cluster-management.io/managed-by: console`

---

## Role Assignment Wizard Structure (ACM 2.16)

### Entry Points

1. **Identity entry** (User Management > Identities > User > Role assignments tab): Scope -> Roles -> Review
2. **Role entry** (Roles page): Identities -> Scope -> Review
3. **Cluster Set entry** (Cluster Sets > Detail > Role assignments tab): Identities -> Granularity -> Roles -> Review (scope pre-selected)

### Scope Types

| Scope | Granularity Options | What Gets Created |
|-------|--------------------|--------------------|
| Global access | (none) | MCRA with global placement |
| Select cluster sets | "Cluster set role assignment" or "Project role assignment" | MCRA with cluster-set placement |
| Select clusters | "Cluster role assignment" or "Project role assignment" | MCRA with cluster placement |

---

## Console-e2e (Playwright) Implementation — TARGET DESIGN (NOT IN REPO)

> **NONE of the files below exist in the repo yet** (`fg-rbac.ts`, `fg-rbac-test.ts`, `McraService`, FG-RBAC page objects). They are the target implementation plan. Always verify with `ls`/`Glob` before importing. Create these files when FG-RBAC Playwright specs are being developed.

### Constants Structure (target)

FG-RBAC will have its own constants file (`src/constants/fg-rbac.ts`) as the **single authoritative source** for all RBAC constants -- routes, selectors, text labels, wizard metadata, and backend resource definitions. There will be no separate `routes.ts` or `SELECTORS.fgRbac` in `selectors.ts`.

Area-specific constants in `src/constants/fg-rbac.ts` are organized by UI location:

| Export | Contains | Used By |
|--------|----------|---------|
| `RBAC_ROUTES` | Navigation paths | Page objects (`goto()`) |
| `RBAC_USER_DETAIL` | User detail tabs, navigation, detail fields, empty states | `UserDetailsPage` |
| `RBAC_RA_TABLE` | Table columns, toolbar (IDs + labels), row actions, filters, empty state, defaults | `RoleAssignmentsTable`, `UserDetailsPage` |
| `RBAC_WIZARD` | Wizard description, scope info, identities tabs, projects form, pre-auth user, view examples, notifications, edit mode | `RoleAssignmentWizardPage` |
| `WIZARD_STEP_IDS` | Wizard step DOM IDs (typed) | `RoleAssignmentWizardPage` |
| `SCOPE_TYPES` / `ScopeType` | Scope type labels + union type | `RoleAssignmentWizardPage` |
| `GRANULARITY_OPTIONS` / `GranularityOption` | Granularity labels + union type | `RoleAssignmentWizardPage` |
| `MCRA_RESOURCE` | Backend resource definition (apiVersion, labels, namespace) | Test specs |

### Page Object Inventory

| Page Object | File | Purpose |
|-------------|------|---------|
| `UserDetailsPage` | `src/pages/fg-rbac/UserDetailsPage.ts` | User detail page (4 tabs, exposes locators for detail fields) |
| `RoleAssignmentWizardPage` | `src/pages/fg-rbac/RoleAssignmentWizardPage.ts` | 7-step wizard modal with composite flows |
| `RolesPage` | `src/pages/fg-rbac/RolesPage.ts` | Roles list and role detail navigation |
| `RoleAssignmentsTable` | `src/components/fg-rbac/RoleAssignmentsTable.ts` | Standalone table component (role-name-based row access) |

### RoleAssignmentsTable: Why Standalone

The RBAC Role Assignments table is a **standalone component** (not extending `AcmTable`) because:
- The dev source `RoleAssignments.tsx` passes a composite `keyFn` to `<AcmTable>` that generates OUIA IDs like `mcra-name-assignment-name-user-role` -- these contain internal resource metadata NOT visible in the UI
- Row identification uses role-name links (`getByRole('link', { name: roleName })`) which is more natural than OUIA IDs
- Per architecture doc: components expose locators, tests assert. Methods like `getRowByRole()`, `getEmptyState()`, `getAllNamespacesCell()` return Locators.

### Fixture Wiring

FG-RBAC uses a two-layer fixture pattern:

**`src/fixtures/rbac-test.ts`** -- universal RBAC fixture (any area extends this):
```typescript
type RbacFixtures = {
  oc: OcCliService;
  asUser: (role: string) => Promise<UserSession>;
};
// asUser loads pre-saved .auth/{role}.json via browser.newContext({ storageState })
// Context lifecycle (creation + teardown) managed here
```

**`src/fixtures/fg-rbac-test.ts`** -- extends rbac-test with FG-RBAC + Fleet Virt specifics:
```typescript
type FgRbacFixtures = {
  mcra: McraService;
  rbacConfig: RbacConfig;
  userDetailsPage: UserDetailsPage;
  roleAssignmentWizardPage: RoleAssignmentWizardPage;
  rolesPage: RolesPage;
  asVirtUser: (role: string) => Promise<VirtUserSession>;
};
// asVirtUser calls base asUser(role), then attaches vmDetailsPage + fleetVirtPage
```

New areas needing RBAC testing extend `rbac-test.ts` and add their own typed wrapper (e.g., `asGrcUser`) that calls `asUser` and attaches area page objects. Add users to `presets.ts` with `domains: ['your-domain']`.

### Wizard Composite Flows

The `RoleAssignmentWizardPage` provides one-liner methods for standard wizard paths:

| Method | Wizard Path |
|--------|-------------|
| `createGlobalAccess(role)` | Scope(Global) -> Roles -> Review -> Create |
| `createClusterSetFullAccess(sets, role)` | Scope(Sets) -> Select -> Granularity(Full) -> Roles -> Review -> Create |
| `createClusterFullAccess(clusters, role)` | Scope(Clusters) -> Select -> Granularity(Full) -> Roles -> Review -> Create |

Use composite flows when the test doesn't need to verify intermediate wizard states. Use step-by-step methods when the test verifies individual wizard steps.

### RBAC User Login

Use `asUser(role)` or an area wrapper to get a session for a non-admin user:

```typescript
// Direct (from rbac-test.ts) -- returns UserSession with just page
const session = await asUser('fg-rbac-admin');

// Area wrapper (from fg-rbac-test.ts) -- returns VirtUserSession with page objects
const rbacSession = await asVirtUser('fg-rbac-admin');
// No live OAuth -- loads pre-saved .auth/fg-rbac-admin.json cookies (~50ms)
// rbacSession.page -- authenticated page with RBAC user cookies
// rbacSession.vmDetailsPage -- pre-wired VmDetailsPage
// rbacSession.fleetVirtPage -- pre-wired FleetVirtPage
// Both admin (page) and RBAC user (rbacSession.page) are active simultaneously
// Context lifecycle managed by rbac-test fixture -- automatic teardown
```

---

## Gotchas

- MCRA v1beta1 uses `spec.subject` (singular object), NOT `spec.subjects` (array)
- Placements are SHARED across MCRAs -- deterministic names based on cluster selection hash. Always clean up orphaned placements.
- `RBAC_SPOKE_CLUSTER` or `VIRT_SPOKE_CLUSTER` must be set for tests that need a spoke cluster
- **AcmTable OUIA IDs** -- the RBAC RA table's `data-ouia-component-id` values are composite keys, NOT simple resource names. Do NOT use OUIA-based row lookup. Use role-name links instead.
- **Search placeholder** -- the RBAC RA table overrides the default search placeholder. Use `getByPlaceholder('Search for role assignments...')` not `[aria-label="Search input"]`.
- **Granularity dropdown** -- rendered as a PF6 combobox with `name: "Access level for selected clusters"`, not an element with `id="clusters-access-level"`. The page object handles this with an `.or()` fallback.
- **asUser** (rbac-test fixture) loads pre-saved `.auth/{role}.json` storageState -- no live OAuth at test time (~50ms). Login happens once in `rbac-auth.setup.ts`. Use `asUser` directly today; `asVirtUser` / `fg-rbac-test` are planned (see banner above).
- Per architecture doc: no `waitForTimeout`, no assertions in page objects/components. Use `expect().toPass()` for polling, expose locators for tests to assert.
