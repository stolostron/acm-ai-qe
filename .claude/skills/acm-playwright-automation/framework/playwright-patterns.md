# Playwright Framework Patterns

Framework-specific patterns, conventions, and gotchas for writing Playwright tests in `stolostron/console-e2e`.

**Local clone:** `$CONSOLE_E2E_ROOT` (the user's local `stolostron/console-e2e` clone)

**Architecture reference (AUTHORITATIVE -- verify before coding):**
- **Architecture summary:** `${CLAUDE_SKILL_DIR}/references/architecture-summary.md`

**Target / migration reference (aspirational -- many paths not in repo yet):**
- `docs/architecture-overview.md` in the repo clone

---

## Repo Structure

```
console-e2e/
  playwright.config.ts       # 9 projects: setup, rbac-setup, cluster, governance, search, alc, fg-rbac, fleet-virt, unit
  package.json               # @playwright/test ^1.58.2
  tsconfig.json              # Path aliases (@pages, @fixtures, @lib, ...)
  eslint.config.mjs          # verifyRow* whitelisted for expect-expect
  start.sh                   # Hub oc login; dispatches to 6 areas: alc, clc, grc, search, fg-rbac, fleet-virt
  src/
    global-setup.ts          # Multi-stage: wipe .auth/, clusterPrep, ansiblePrep, gitOpsPrep, operatorPreflight
    global-setup/            # 8 modules: ansiblePrep, clusterPrep, envTruthy, gitOpsPrep, logPrefix, operatorPreflight, projectArgv, repoRoot
    config/
      schema.ts              # HubAuthConfig, RbacUser, RbacConfig, VirtConfig, TestConfig
      presets.ts             # hubAuthPresets; 41 RBAC users (fg-rbac domain + tiers)
      index.ts               # getHubAuth(), getRbacUsers(), getTestConfig(), getRbacConfig(), getVirtConfig(), loadAlcLocalEnvFile(); dotenv
    constants/               # 11 files
      selectors.ts           # PF_MASTHEAD, PF_SPINNER, PF_SKELETON, SELECTORS.*
      app.ts                 # ALC routes, table, filters, advanced config
      cluster.ts             # Routes, GPU columns, manage columns
      fg-rbac.ts             # FG-RBAC routes, selectors, user role constants
      fleet-virt.ts          # Fleet Virt routes, VM table selectors, tab selectors
      governance.ts          # GRC routes, policy selectors, labels
      placement.ts           # Placement routes, wizard selectors
      placement-tolerations.ts  # Toleration-specific selectors
      placement-preview.ts   # Preview modal selectors
      search.ts              # Search page routes, selectors
      sampleRepos.ts         # Git repository URLs for ALC test data
    services/
      OcCliService.ts        # 37 methods: generic + domain (mcra*, vm*, policy*, application*, cluster*, placement*, subscription*)
      domains/
        ObservabilityService.ts   # MCO install, clusters, Grafana annotation (5 methods)
    utils/
      kube-helper.ts         # generateSafeName(prefix) only
    lib/                     # 5 subdirs + root files
      openshift-login.ts     # openshiftLogin(page, LoginOptions)
      utils.ts               # Shared utility functions
      app/                   # Application setup helpers
      assertions/            # Shared assertion helpers
      cluster/               # Cluster setup helpers
      governance/            # Policy, placement, policy set setup helpers
      placement/             # Placement wizard and preview helpers
    components/              # 10 files across 5 area subdirs
      patternfly/AcmTable.ts       # search, clearSearch, getRow, verifyRow*, verifyEmpty, clickRow, verifyColumnHeader*, verifyColumnOrder
      patternfly/AcmSearchInput.ts, ManageColumnsDialog.ts
      app/ApplicationsTable.ts     # extends AcmTable
      cluster/ClusterTable.ts      # composed (not extending AcmTable)
      fg-rbac/RoleAssignmentsTable.ts
      fleet-virt/AdvancedSearchModal.ts, SavedSearches.ts, StatusFilter.ts, TreeView.ts
    pages/                   # 30 files across 6 area subdirs + BasePage
      BasePage.ts            # (page) only; waitForLoad() -> toHaveCount(0) on PF loaders
      app/                   # 5: ApplicationListPage, ApplicationDetailsPage, Argo*WizardPage, SubscriptionApplicationCreateWizardPage
      cluster/               # 6: ClusterListPage, ClusterNodesPage, ClusterSetsPage, PlacementsListPage, CreatePlacementWizardPage, PlacementDetailsPage
      fg-rbac/               # 4: RolesListPage, RoleDetailsPage, UserDetailsPage, RoleAssignmentWizardPage
      fleet-virt/            # 2: FleetVirtPage, VmDetailsPage
      governance/            # 10: GovernancePage, PoliciesListPage, PolicyDetailsPage, CreatePolicyWizardPage, PolicySets*, Placements*, DiscoveredPolicyDetailsPage, PolicyTemplateDetailsPage
      infrastructure/        # 2: ClusterDetailsPage, ClusterSetDetailsPage
    fixtures/                # 7 files
      acm-test.ts            # cluster + governance shared: oc, observabilityService, uniqueName, cluster + placement + policy pages
      app-test.ts            # ALC: oc, applicationListPage, argo wizards, subscription wizard
      governance-test.ts     # GRC: oc, governance page objects
      rbac-test.ts           # Base: oc, asUser(role) -> { page }
      fg-rbac-test.ts        # Extends rbac-test: oc, rbacConfig, FG-RBAC pages
      fleet-virt-test.ts     # Fleet Virt: oc, fleet-virt pages
      search-test.ts         # Search: oc, search pages
    templates/               # 10 YAML files across 4 area subdirs
      app/, cluster/, fg-rbac/, governance/
    tests/                   # 51 files: 40 integration + 9 unit + 2 setup
      auth.setup.ts          # project setup -> .auth/admin.json
      rbac-auth.setup.ts     # project rbac-setup -> .auth/{role}.json
      app/                   # 13 specs
      cluster/               # 6 specs
      fg-rbac/               # 8 specs
      fleet-virt/            # 7 specs
      governance/            # 5 specs
      search/                # 1 spec
      unit/                  # 9 unit specs
```

### Playwright projects (use these in CLI)

| Project | testMatch | dependencies | storageState | Specs |
|---------|-----------|--------------|--------------|-------|
| `setup` | `auth.setup.ts` | -- | -- | always |
| `rbac-setup` | `rbac-auth.setup.ts` | -- | -- | when RBAC runs |
| `cluster` | `/cluster/` | `setup` | `.auth/admin.json` | 6 specs |
| `governance` | `/governance/` | `setup` | `.auth/admin.json` | 5 specs |
| `search` | `/search/` | `setup` | `.auth/admin.json` | 1 spec |
| `alc` | `/app/` | `setup` | `.auth/admin.json` | 13 specs |
| `fg-rbac` | `/fg-rbac/` | `setup`, `rbac-setup` | `.auth/admin.json` | 8 specs |
| `fleet-virt` | `/fleet-virt/` | `setup` | `.auth/admin.json` | 7 specs |
| `unit` | `/unit/` | -- | -- | 9 specs |

**There is no `chromium` project.** The project named `alc` matches `/app/` paths. Pass `--project alc`.

---

## Architecture Rules

### Constants: Split by scope

| File | Contains |
|------|----------|
| `selectors.ts` | PatternFly globals + small domain blocks in `SELECTORS` |
| `{area}.ts` | Routes, selectors, labels when 20+ or large ALC/cluster domains |

**All 11 constants files implemented:** `selectors.ts`, `app.ts`, `cluster.ts`, `fg-rbac.ts`, `fleet-virt.ts`, `governance.ts`, `placement.ts`, `placement-tolerations.ts`, `placement-preview.ts`, `search.ts`, `sampleRepos.ts`.

Do NOT duplicate selectors between `selectors.ts` and area files.

### Config

| File | Purpose |
|------|---------|
| `schema.ts` | `HubAuthConfig`, `RbacUser`, `RbacConfig`, `VirtConfig`, `TestConfig` |
| `presets.ts` | `hubAuthPresets`, `rbacPresets` |
| `index.ts` | `getHubAuth()`, `getRbacUsers(domain?)`, `getTestConfig()`, `getRbacConfig()`, `getVirtConfig()`, `loadAlcLocalEnvFile()` |

Specs must not read `process.env` directly.

**Env:** `HUB_URL`, `HUB_PASSWORD` (required for UI auth), optional `CONSOLE_USERNAME`, `CONSOLE_IDP`, `RBAC_TEST_PASSWORD`, `RBAC_DOMAIN`.

### Services: Backend only

| Service | Status |
|---------|--------|
| `OcCliService` | 37 methods -- generic CLI + domain methods (mcra*, vm*, policy*, application*, cluster*, placement*, subscription*). No Playwright. |
| `ObservabilityService` | **Implemented** -- 5 methods: isInstalled, getManagedClusters, get/restore/removeGrafanaAnnotation |

Domain-specific methods are added directly to OcCliService (prefixed by resource type). Separate service classes only when the domain needs constructor-injected state (like ObservabilityService).

**Hooks:** Instantiate `new ObservabilityService(new OcCliService())` in `beforeAll`/`afterAll`. Avoid raw `oc.run()` in specs; in hooks prefer named OcCliService methods, use `oc.run()` only for one-off YAML until a named method is added.

### Components

- **Extend `AcmTable`** when console uses `<AcmTable>` with usable OUIA row IDs.
- **Compose standalone** when table DOM differs (GPU columns, `data-label` headers).
- **`verifyRowVisible` / `verifyRowNotVisible` / `verifyEmpty`** are ESLint-whitelisted.

### Pages

- Extend `BasePage` with `super(page)` -- **not** `super(page, oc)`.
- Domain pages: `constructor(page: Page, private readonly oc: OcCliService)`.
- `BasePage` has **no** `goto()` -- each page implements its own.
- Expose locators and interaction methods; keep business `expect` in specs.

### Fixtures

| Fixture | Import in | Provides |
|---------|-----------|----------|
| `acm-test` | `src/tests/cluster/*.spec.ts`, some governance specs | `oc`, `observabilityService`, `uniqueName`, cluster pages, placement pages, policy pages |
| `app-test` | `src/tests/app/*.spec.ts` | `oc`, `applicationListPage`, argo wizards, subscription wizard |
| `governance-test` | `src/tests/governance/*.spec.ts` | `oc`, governance page objects |
| `rbac-test` | Base for fg-rbac-test, fleet-virt-test | `oc`, `asUser(role)` |
| `fg-rbac-test` | `src/tests/fg-rbac/*.spec.ts` | Extends `rbac-test` -- `oc`, `rbacConfig`, FG-RBAC pages |
| `fleet-virt-test` | `src/tests/fleet-virt/*.spec.ts` | `oc`, fleet-virt pages |
| `search-test` | `src/tests/search/*.spec.ts` | `oc`, search pages |
| `@playwright/test` | setup projects only | setup projects |

### Tests

- No `page.goto`, selectors, or `oc.run` in spec files.
- **Polarion-driven specs:** one `test()` per Polarion ID; one `test.step()` per Polarion step.
- **Sanity suites** (e.g. `applications-list.spec.ts`): multiple `test()` blocks without Polarion IDs is valid.
- Cleanup: `afterAll` for hub mutations; `afterEach` for per-test resources.

---

## Path Aliases (tsconfig.json)

```typescript
import { OcCliService } from '@services/OcCliService';
import { ObservabilityService } from '@services/domains/ObservabilityService';
import { ClusterListPage } from '@pages/cluster/ClusterListPage';
import { CLUSTER_ROUTES } from '@constants/cluster';
import { test, expect } from '@fixtures/acm-test';
import { openshiftLogin } from '@lib/openshift-login';
```

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

## Playwright Config (as-built)

```typescript
import './src/config/index';  // dotenv

defineConfig({
  testDir: './src/tests',
  globalSetup: require.resolve('./src/global-setup'),
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  projects: [
    { name: 'setup', testMatch: /\/auth\.setup\.ts/ },
    { name: 'rbac-setup', testMatch: /rbac-auth\.setup\.ts/ },
    { name: 'cluster', dependencies: ['setup'], testMatch: /cluster/, storageState: '.auth/admin.json' },
    { name: 'governance', dependencies: ['setup'], testMatch: /governance/, storageState: '.auth/admin.json' },
    { name: 'search', dependencies: ['setup'], testMatch: /search/, storageState: '.auth/admin.json' },
    { name: 'alc', dependencies: ['setup'], testMatch: /app/, storageState: '.auth/admin.json' },
    { name: 'fg-rbac', dependencies: ['setup', 'rbac-setup'], testMatch: /fg-rbac/, storageState: '.auth/admin.json' },
    { name: 'fleet-virt', dependencies: ['setup'], testMatch: /fleet-virt/, storageState: '.auth/admin.json' },
    { name: 'unit', testMatch: /unit/ },
  ],
});
```

---

## Authentication

### Admin

`auth.setup.ts` (project `setup`): `getHubAuth()` + `OcCliService.getConsoleUrl()` + `openshiftLogin(page, LoginOptions)` -> `.auth/admin.json`.

**Code uses `admin.json`.** Some README text still says `user.json` -- follow the code.

### RBAC users

`rbac-auth.setup.ts`: `getRbacUsers(RBAC_DOMAIN)` -- users from `presets.ts`. Skips if `RBAC_TEST_PASSWORD` unset. Saves `.auth/{role}.json`.

### In tests

`rbac-test.ts`: `asUser(role)` -> new context with `storageState: .auth/{role}.json`, returns `{ page }`. Closes contexts after test.

---

## Locator Strategy

| Priority | Locator |
|----------|---------|
| 1 | `getByRole` |
| 2 | `getByLabel` |
| 3 | `getByPlaceholder` |
| 4 | `getByText` |
| 5 | `getByTestId` |
| 6 | `locator('[data-ouia-component-id=...]')` |
| 7 | CSS (last resort) |

Never `page.waitForTimeout(N)`.

### Live DOM learnings

(See prior skill content for PF6 MultiSelect toggle, `page.goto().catch()` in PO retry methods, RBAC flat VM table, `toBeHidden()` vs `not.toBeVisible()`, etc.)

---

## AcmTable vs Standalone / Composed Tables

| Pattern | Example in repo |
|---------|-----------------|
| Extend `AcmTable` | `ApplicationsTable` |
| Compose helper | `ClusterListPage` uses `AcmTable` + `ClusterTable` |
| Column by header | `ClusterTable.getColumnHeader(name)` -- never `td.nth(N)` |

---

## Constants Design Pattern

**All 11 constants files implemented.** Each area has its own `{area}.ts` with routes + selectors + labels in one file. Do not duplicate selectors between `selectors.ts` and area files.

---

## Test Structure Examples

### Polarion-mapped (GPU)

```typescript
import { test, expect } from '@fixtures/acm-test';
import { ObservabilityService } from '@services/domains/ObservabilityService';
import { OcCliService } from '@services/OcCliService';

test.describe('GPU ...', { tag: ['@clusters'] }, () => {
  test.beforeAll(async () => {
    const svc = new ObservabilityService(new OcCliService());
    // probe hub state
  });

  test('RHACM4K-63953: ...', async ({ clusterListPage }) => {
    await test.step('Verify GPU count column is visible', async () => {
      await clusterListPage.goto();
      // ...
    });
  });
});
```

### ALC sanity (multi-test, no Polarion step mapping)

```typescript
import { test, expect } from '@fixtures/app-test';

test.describe('Applications list', { tag: ['@app', '@alc'] }, () => {
  test('displays Applications page...', async ({ applicationListPage }) => {
    await applicationListPage.goto();
    await expect(applicationListPage.getPageTitle()).toBeVisible();
  });
});
```

---

## Linting & Formatting

Run `npm run lint:check` before Phase 4.

**ESLint** (`eslint.config.mjs`): `playwright/expect-expect` allows `verifyRowVisible`, `verifyRowNotVisible`, `verifyEmpty`.

| Pattern | Correct |
|---------|---------|
| Hidden check | `toBeHidden()` |
| Auth file | `.auth/admin.json` |
| Setup test name | `test('authenticate admin', ...)` in `auth.setup.ts` |

---

## Potential Future Extensions (do not assume present -- verify with `ls`)

- `src/services/domains/McraService.ts`, `VmService.ts`, `PolicyService.ts` -- only when domain needs constructor-injected state (currently all domain methods live in OcCliService)

All other previously planned items (constants, pages, fixtures, tests, lib/assertions, templates for fg-rbac, fleet-virt, governance, search) now exist in the repo. Always verify with `ls`/`Glob` before assuming any file exists.

---

## Dependencies (package.json)

`@playwright/test` ^1.58.2, `typescript` ^5.9.3, `dotenv` ^17.2.3, Node >=20. `@faker-js/faker` is listed but **unused in src/**.
