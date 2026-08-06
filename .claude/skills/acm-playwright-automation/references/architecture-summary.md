# Console-E2E Architecture Summary

Agent-optimized reference for `stolostron/console-e2e` (Domain-Driven Hybrid Playwright E2E).

**As-built:** June 2026, verified against live repo.
**Local clone:** `$CONSOLE_E2E_ROOT` (the user's local `stolostron/console-e2e` clone)

**IMPORTANT:** This file is a snapshot. Before assuming any file or method exists, verify with `ls`, `Glob`, or `grep` against the live repo. The repo evolves continuously.

---

## Repo Stats

- **227** TypeScript files under `src/`
- **9** Playwright projects: `setup`, `rbac-setup`, `cluster`, `governance`, `search`, `alc`, `fg-rbac`, `fleet-virt`, `unit`
- **No `chromium` project** -- the `alc` project matches testMatch `/app/` but the project name is `alc`; always pass `--project alc`
- **Tech:** `@playwright/test` ^1.58.2, TypeScript ^5.9.3, dotenv ^17.2.3, Node >=20

---

## Layer Architecture

| Layer | Directory | Purpose | Imports From | Imported By |
|-------|-----------|---------|--------------|-------------|
| Config | `src/config/` | Env vars, presets, typed getters | nothing (leaf) | fixtures, services, tests |
| Constants | `src/constants/` | Routes, selectors, text labels | nothing (leaf) | pages, components, tests, fixtures |
| Services | `src/services/` | Backend CLI ops (no Playwright) | config, constants, utils | fixtures, tests (hooks) |
| Utils | `src/utils/` | Pure functions, no side effects | nothing (leaf) | anywhere |
| Components | `src/components/` | Reusable UI widgets (tables, modals) | constants | pages |
| Pages | `src/pages/` | Full views, extend BasePage | constants, components | fixtures |
| Lib | `src/lib/` | Browser helpers (login, assertions) | config | fixtures, setup projects |
| Fixtures | `src/fixtures/` | DI wiring, extends `test` | services, pages, config | tests only |
| Tests | `src/tests/` | Specs, `test.step()`, assertions | fixtures only | nothing |

---

## File Inventory (As-Built)

### Config

| File | Exports |
|------|---------|
| `schema.ts` | `HubAuthConfig`, `RbacUser`, `RbacConfig`, `VirtConfig`, `TestConfig` interfaces |
| `presets.ts` | `hubAuthPresets` (kubeadmin), `rbacPresets` (41 users across fg-rbac domain + tiers) |
| `index.ts` | `getHubAuth()`, `getRbacUsers(domain?)`, `getTestConfig()`, `getRbacConfig()`, `getVirtConfig()`, `loadAlcLocalEnvFile()` -- loads dotenv |
| `e2e-spec-loader` system | Data-driven test scenario system -- YAML scenario files for domains: argo-push, placement, policy, policySet, subscription. Unit-tested via `e2e-spec-data.unit.spec.ts`. |

### Constants (11 files)

| File | Contains |
|------|----------|
| `selectors.ts` | `PF_MASTHEAD`, `PF_SPINNER`, `PF_SKELETON`, `SELECTORS.cluster.*` |
| `app.ts` | `APP_ROUTES`, `APP_PAGE`, `APP_TABLE`, `APP_FILTER`, `APP_ADVANCED_CONFIG`, `APP_CREATE_MENU` |
| `cluster.ts` | `CLUSTER_ROUTES`, `CLUSTER_TABLE_COLUMNS`, `GPU_COLUMN` |
| `fg-rbac.ts` | FG-RBAC routes, selectors, user role constants |
| `fleet-virt.ts` | Fleet Virt routes, VM table selectors, tab selectors |
| `governance.ts` | GRC routes, policy selectors, labels |
| `placement.ts` | Placement routes, wizard selectors |
| `placement-tolerations.ts` | Toleration-specific selectors |
| `placement-preview.ts` | Preview modal selectors |
| `search.ts` | Search page routes, selectors |
| `sampleRepos.ts` | Git repository URLs for ALC test data |

### Services

| File | Key Methods | Status |
|------|-------------|--------|
| `OcCliService.ts` | **37 methods.** Generic: `run(cmd)`, `applyYaml(path)`, `deleteYaml(path)`, `getConsoleUrl()`, `hasResourcesInCluster()`. Domain: `mcra*` (RBAC), `vm*` (Fleet Virt), `policy*` (GRC), `application*` (ALC), `cluster*`/`labelManagedCluster` (CLC), `placement*`, `subscription*`, `deleteNamespace`, `deleteSecret` | Implemented |
| `domains/ObservabilityService.ts` | `isInstalled()`, `getManagedClusters()`, `getGrafanaAnnotation()`, `restoreGrafanaAnnotation()`, `removeGrafanaAnnotation()` | Implemented |

### Utils

| File | Exports |
|------|---------|
| `kube-helper.ts` | `generateSafeName(prefix)` |

### Components (10 files)

| File | Pattern |
|------|---------|
| `patternfly/AcmTable.ts` | `search()`, `clearSearch()`, `getRow(ouiaId)`, `verifyRowVisible()`, `verifyRowNotVisible()`, `verifyEmpty()`, `clickRow()`, `verifyColumnHeaderVisible()`, `verifyColumnHeaderNotVisible()`, `verifyColumnOrder()` |
| `patternfly/AcmSearchInput.ts` | Search input with typeahead |
| `patternfly/ManageColumnsDialog.ts` | Column visibility management |
| `app/ApplicationsTable.ts` | Extends `AcmTable` -- filters, create menu, pagination, row actions |
| `cluster/ClusterTable.ts` | Composed (NOT extending AcmTable) -- column headers via `data-label`, GPU popover |
| `fg-rbac/RoleAssignmentsTable.ts` | Role assignment list with user/cluster filtering |
| `fleet-virt/AdvancedSearchModal.ts` | Advanced search dialog for VM list |
| `fleet-virt/SavedSearches.ts` | Saved search management |
| `fleet-virt/StatusFilter.ts` | VM status filter |
| `fleet-virt/TreeView.ts` | Hierarchical cluster/VM tree view |

### Pages (30 files across 6 area subdirectories + BasePage)

| Area | Files | Key Classes |
|------|-------|-------------|
| root | 1 | `BasePage` -- abstract, `waitForLoad()` checks PF_SPINNER + PF_SKELETON. No `goto()`. |
| app/ | 5 | `ApplicationListPage`, `ApplicationDetailsPage`, `ArgoPullApplicationCreateWizardPage`, `ArgoPushApplicationCreateWizardPage`, `SubscriptionApplicationCreateWizardPage` |
| cluster/ | 6 | `ClusterListPage`, `ClusterNodesPage`, `ClusterSetsPage`, `PlacementsListPage`, `CreatePlacementWizardPage`, `PlacementDetailsPage` |
| fg-rbac/ | 4 | `RolesListPage`, `RoleDetailsPage`, `UserDetailsPage`, `RoleAssignmentWizardPage` |
| fleet-virt/ | 2 | `FleetVirtPage`, `VmDetailsPage` |
| governance/ | 10 | `GovernancePage`, `PoliciesListPage`, `PolicyDetailsPage`, `CreatePolicyWizardPage`, `PolicySetsListPage`, `PolicySetDetailsPage`, `CreatePolicySetWizardPage`, `PlacementsListPage` (separate from cluster), `PlacementDetailsPage`, `DiscoveredPolicyDetailsPage`, `PolicyTemplateDetailsPage` |
| infrastructure/ | 2 | `ClusterDetailsPage`, `ClusterSetDetailsPage` |

### Lib (5 subdirectories + root files)

| Path | Purpose |
|------|---------|
| `openshift-login.ts` | `openshiftLogin(page, LoginOptions)` -- handles single + multi-IdP broker |
| `app/` | Application setup helpers (argo, subscription, placement) |
| `assertions/` | Shared assertion helpers across areas |
| `cluster/` | Cluster setup and management helpers |
| `governance/` | Policy, placement, and policy set setup helpers |
| `placement/` | Placement wizard and preview helpers |
| `utils.ts` | Shared utility functions |

### Fixtures (7 files)

| File | Provides | Used By |
|------|----------|---------|
| `acm-test.ts` | `oc`, `observabilityService`, `uniqueName`, `clusterListPage`, `clusterNodesPage`, `placementsListPage`, `createPlacementWizardPage`, `policiesListPage`, `createPolicyWizardPage`, `policySetsListPage`, `createPolicySetWizardPage` | `src/tests/cluster/*.spec.ts`, some governance specs |
| `app-test.ts` | `oc`, `applicationListPage`, argo wizard pages, subscription wizard page | `src/tests/app/*.spec.ts` |
| `governance-test.ts` | `oc`, governance page objects (policies, placements, policy sets) | `src/tests/governance/*.spec.ts` |
| `rbac-test.ts` | `oc`, `asUser(role)` -> `{ page }` from `.auth/{role}.json` | Base for `fg-rbac-test` and `fleet-virt-test` |
| `fg-rbac-test.ts` | Extends `rbac-test` -- `oc`, `rbacConfig`, FG-RBAC page objects | `src/tests/fg-rbac/*.spec.ts` |
| `fleet-virt-test.ts` | Extends base -- `oc`, fleet-virt page objects | `src/tests/fleet-virt/*.spec.ts` |
| `search-test.ts` | `oc`, search page objects | `src/tests/search/*.spec.ts` |

### Tests (51 files: 40 integration + 9 unit + 2 setup)

| Area | Count | Example Specs |
|------|-------|---------------|
| setup | 2 | `auth.setup.ts`, `rbac-auth.setup.ts` |
| app/ | 13 | `applications-list`, `push-applications`, `git-applications`, `argo-push-*`, `subscription-wizard-*`, `manage-columns`, `advanced-config-*`, `applications-label-filter` |
| cluster/ | 6 | `cluster-list`, `gpu-count-column`, `gpu-count-nodes`, `manage-columns`, `placement-create-preview`, `placement-create-tolerations` |
| fg-rbac/ | 8 | `role-assignment-*` (cluster, clusterset, global, edge-cases, entry-points), `managed-admin-full-access`, `roles-page-validation`, `cross-page-integration` |
| fleet-virt/ | 7 | `advanced-search`, `saved-search-basic`, `vm-actions`, `tree-view`, `status-filter`, `hub-view-role`, `role-visibility` |
| governance/ | 5 | `policy-labels`, `discovered-policy-labels`, `governance-placement-*`, `placement-references` |
| search/ | 1 | `search-page` |
| unit/ | 9 | `e2e-spec-data`, `placement-*`, `private-git`, `topology-*`, `appset-graph-ids`, `applications-label-filter`, `subscription-details`, `managed-cluster-context` |

### Templates (10 YAML files across 4 area subdirs)

| Area | Files |
|------|-------|
| `app/` | `argo-helm-appset-setup.yaml`, `gitops-placement-preview-setup.yaml`, `subscription/existing-placement-wizard-setup.yaml` |
| `cluster/` | `placement-preview-test-setup.yaml` |
| `fg-rbac/` | `empty-clusterset.yaml`, `test-clusterset.yaml` |
| `governance/` | `discovered-policy-resources.yaml`, `policy-preview-test-setup.yaml`, `placement-policy-resources.yaml`, `policy-set-preview-test-setup.yaml` |

---

## Playwright Projects

| Project | testMatch | dependencies | storageState | Specs |
|---------|-----------|--------------|--------------|-------|
| `setup` | `auth.setup.ts` | -- | -- | always |
| `rbac-setup` | `rbac-auth.setup.ts` | -- | -- | when RBAC runs |
| `cluster` | `/cluster/` | `['setup']` | `.auth/admin.json` | 6 specs |
| `governance` | `/governance/` | `['setup']` | `.auth/admin.json` | 5 specs |
| `search` | `/search/` | `['setup']` | `.auth/admin.json` | 1 spec |
| `alc` | `/app/` | `['setup']` | `.auth/admin.json` | 13 specs |
| `fg-rbac` | `/fg-rbac/` | `['setup', 'rbac-setup']` | `.auth/admin.json` | 8 specs |
| `fleet-virt` | `/fleet-virt/` | `['setup']` | `.auth/admin.json` | 7 specs |
| `unit` | `/unit/` | -- | -- | 9 specs |

**There is no `chromium` project.** The project named `alc` matches `/app/` paths. Always pass `--project alc`.

---

## Authentication Flow

1. `global-setup.ts` -- multi-stage setup:
   - Wipes `.auth/` directory and recreates it
   - `projectArgv`: detects requested projects (unit-only skip, ALC-specific env loading via `loadAlcLocalEnvFile()`)
   - `clusterPrep`: conditional managed cluster preparation (skippable via `E2E_SKIP_MANAGED_KUBECONFIG_MERGE`)
   - `ansiblePrep`: Ansible preparation (skippable via `E2E_SKIP_ANSIBLE_PREP`)
   - `gitOpsPrep`: GitOps preparation when ALC projects run
   - `operatorPreflight`: verifies required operators are installed
   - Helper modules: `logPrefix`, `envTruthy`, `repoRoot`
2. `auth.setup.ts` -- `openshiftLogin(admin)` -> saves `.auth/admin.json`
3. `rbac-auth.setup.ts` -- loops `getRbacUsers(RBAC_DOMAIN)` -> saves `.auth/{role}.json` per user (skips if `RBAC_TEST_PASSWORD` unset)
4. Test projects load `storageState` from saved JSON -- tests start pre-authenticated
5. `rbac-test.ts` `asUser(role)` -- creates `BrowserContext` from `.auth/{role}.json` (~50ms, no OAuth)

**Auth file is `admin.json`** (not `user.json`).

---

## Data Flow (test execution order)

1. `playwright.config.ts` selects project
2. `global-setup.ts` runs multi-stage setup (auth cleanup, cluster prep, operator checks)
3. Setup project runs login -> saves cookies
4. Test project loads `storageState` (pre-authenticated)
5. Test imports area fixture (`@fixtures/acm-test`, `@fixtures/app-test`, `@fixtures/governance-test`, etc.)
6. Fixture creates services + pages (lazy DI)
7. `test.beforeAll` creates prerequisites via OcCliService methods or lib helpers
8. Test destructures only needed fixtures
9. `test.step()` calls page object methods
10. Page object handles `page.goto()` + locators
11. Test asserts with `expect()`
12. `test.afterAll` cleans up resources (`--ignore-not-found`)

---

## File Placement Decision Tree

| Code Type | Destination | Pattern |
|-----------|-------------|---------|
| Navigation, page-level locators | `src/pages/{area}/` | Extend `BasePage`, `goto()` uses constants |
| CLI / backend operations | `src/services/OcCliService.ts` | Domain methods added directly, no Playwright |
| Reusable UI widgets (tables, modals) | `src/components/{area}/` | May extend `AcmTable` or standalone |
| Static strings (routes, selectors, labels) | `src/constants/{area}.ts` (20+) or `selectors.ts` (<20) | One authoritative location per selector |
| Configuration | `src/config/` | Interfaces in schema, getters in index |
| Pure functions | `src/utils/` | No Playwright, no Config imports |
| DI wiring | `src/fixtures/{area}-test.ts` | Extend `@playwright/test` |
| Test specs | `src/tests/{area}/` | Import from area fixture |
| Browser helpers (login, assertions) | `src/lib/` or `src/lib/{area}/` | OK to import Playwright |
| YAML templates | `src/templates/{area}/` | Referenced by services and lib helpers |

---

## Must-Do Rules

1. **Extend BasePage** -- all page objects; `super(page)` only (oc on subclass)
2. **Navigation in PO methods** -- `page.goto()` only inside page objects
3. **Constants in files** -- no inline routes/selectors/labels in specs
4. **Domain services for CLI** -- extract when 2+ tests share same `oc.run()` pattern
5. **Column by header** -- `getCellByColumnHeader(row, 'Name')`, never `td.nth(N)`
6. **Fixtures for DI** -- import `test` from area fixture, not `@playwright/test`
7. **Cleanup in afterAll** -- idempotent (`--ignore-not-found`)
8. **Path aliases** -- `@pages/`, `@services/`, `@fixtures/`, never relative `../../`
9. **Locator hierarchy** -- getByRole > getByLabel > getByPlaceholder > getByText > getByTestId > locator > CSS
10. **Table verify helpers** -- `AcmTable.verifyRowVisible/NotVisible/Empty` allowed (ESLint whitelist)

---

## Anti-Patterns (Forbidden)

| Pattern | Why | Instead |
|---------|-----|---------|
| `page.goto()` in specs | Centralizing in POs = one update | PO `goto()` or `navigateTo*()` method |
| Raw `oc.run()` in spec body | Wrap in named OcCliService methods | `oc.mcra*()`, `oc.vm*()` etc. |
| Inline constants in specs | Fragile, duplicated | `constants/{area}.ts` |
| `td.nth(N)` | Columns reorder | Header-based resolution |
| `page.waitForTimeout(N)` | Forbidden; causes flakes | `expect().toPass()`, `waitFor()`, `toBeVisible()` |
| `page.reload()` in retry | Tab crash = hard failure | `page.goto(url).catch(() => {})` in PO |
| CSS class selectors for assertions | Internal PF/OCP classes break | Role-based locators |
| `not.toBeVisible()` | Use `toBeHidden()` (ESLint enforced) | `await expect(loc).toBeHidden()` |
| Duplicate PO methods | Extract to component or BasePage | Shared component |
| Selectors/locators in test files | Locators in POs as `private readonly` | Page object accessor methods |
| `test.only` | Breaks CI | Remove before commit |
| `new PageObject(page)` in tests | Use fixtures for DI | Destructure from fixture |
| Browser interaction in services | Services = backend only | Put browser code in `lib/` |
| Separate service class files | Add methods to OcCliService directly | Prefix by resource: `mcra*`, `vm*` |
| Duplicated selectors across files | One authoritative location | Large domain -> own `{area}.ts` file |
| `process.env` in tests | Use config layer | `getHubAuth()`, `getRbacUsers()`, `getRbacConfig()`, `getVirtConfig()` |
| Relative imports | Breaks refactoring | Path aliases always |

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `HUB_URL` | Yes | Hub console URL (auto-derived from `oc get route`) |
| `HUB_PASSWORD` | Yes | Hub login password |
| `CONSOLE_USERNAME` | No | Override admin username (default: kubeadmin) |
| `CONSOLE_IDP` | No | Override IDP (default: kube:admin) |
| `RBAC_TEST_PASSWORD` | For RBAC | Password for clc-e2e-* test users |
| `RBAC_IDP` | No | Override RBAC IDP (default: clc-e2e-htpasswd) |
| `RBAC_DOMAIN` | No | Filter users by domain in getRbacUsers() |
| `E2E_SKIP_MANAGED_KUBECONFIG_MERGE` | No | Skip managed cluster kubeconfig merge in global-setup |
| `E2E_SKIP_ANSIBLE_PREP` | No | Skip Ansible preparation in global-setup |

---

## Path Aliases (tsconfig.json)

| Alias | Maps To |
|-------|---------|
| `@config` / `@config/*` | `src/config/` |
| `@constants/*` | `src/constants/*` |
| `@services/*` | `src/services/*` |
| `@components/*` | `src/components/*` |
| `@pages/*` | `src/pages/*` |
| `@utils/*` | `src/utils/*` |
| `@fixtures/*` | `src/fixtures/*` |
| `@lib/*` | `src/lib/*` |
| `@tests/*` | `src/tests/*` |

---

## Playwright Config (key settings)

```
timeout: 60_000
expect.timeout: 15_000
fullyParallel: true
retries: CI ? 2 : 0
workers: CI ? 1 : undefined
globalSetup: src/global-setup.ts
reporter: html
trace: on-first-retry
```

---

## Linting

Run `npm run lint:check` before Phase 4. Covers Prettier (all file types) + ESLint + TypeScript.

ESLint `playwright/expect-expect` allows: `verifyRowVisible`, `verifyRowNotVisible`, `verifyEmpty`.
`toBeHidden()` preferred over `not.toBeVisible()`.

---

## Keeping This File Current

This file is the **agent-facing architecture reference** for the Playwright automation skill. Update it when the repo structure changes (new areas, new services, new patterns). Source of truth: the live repo (`Glob`/`ls` before assuming files exist).

Source of truth: the live repo at `$CONSOLE_E2E_ROOT`. Run `Glob`/`ls` before assuming files exist.
