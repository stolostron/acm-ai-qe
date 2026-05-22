# Fleet Virtualization Area Knowledge Base

> **Playwright as-built:** No `src/tests/fleet-virt/`, `fleet-virt-test.ts`, or `VmService` in `console-e2e` yet. Content below is domain + Cypress reference until Fleet Virt Playwright specs land.

Domain knowledge for writing Fleet Virtualization (VM management) automation tests in `console-e2e` (Playwright).

---

## Prerequisites

- ACM hub cluster with Fleet Virtualization enabled
- Spoke cluster with CNV (OpenShift Virtualization) installed and VMs running
- Spoke cluster imported as ManagedCluster in ACM

---

## Required Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `VIRT_SPOKE_CLUSTER` | No | `local-cluster` | Spoke cluster name |
| `HUB_PASSWORD` | Yes | -- | Hub console login password |

**Guard pattern (in test specs):**
```typescript
test.skip(!virtConfig.spokeCluster, 'VIRT_SPOKE_CLUSTER not set');
```

---

## Navigation

Fleet Virtualization VM list page:
- Route: `/k8s/all-clusters/all-namespaces/kubevirt.io~v1~VirtualMachine` (in `fleet-virt.ts` as `FLEET_VIRT_ROUTES.vmList`)
- URL must contain `all-clusters` for CCLM (cross-cluster live migration) to be available
- Use `FleetVirtPage.goto()` which calls `oc.getConsoleUrl()` + `shouldLoad()` with retry

---

## Console-e2e (Playwright) Implementation — TARGET DESIGN (NOT IN REPO)

> **NONE of the files below exist in the repo yet.** They are the target implementation plan. Always verify with `ls`/`Glob` before importing. Create these files when Fleet Virt Playwright specs are being developed.

### Constants Structure (target)

Fleet Virt will have its own constants file (`src/constants/fleet-virt.ts`) as the **single authoritative source** for all Fleet Virt constants -- routes, selectors, page text, search labels, saved search text, and VM table selectors. There will be no separate `routes.ts` or `SELECTORS.fleetVirt` in `selectors.ts`.

### Page Object and Component Inventory (target)

| File | Purpose |
|------|---------|
| `src/pages/fleet-virt/FleetVirtPage.ts` | VM list page: goto, shouldLoad (retry+reload), searchVM, openAdvancedSearch, getVmRow, getNoVMsEmptyState |
| `src/pages/fleet-virt/VmDetailsPage.ts` | VM details page: clickTab, getPageHeading, getActionsDropdown, getActionMenuItem, Console/Events/Snapshots/Configuration tab locators |
| `src/components/fleet-virt/AdvancedSearchModal.ts` | Side panel (NOT dialog): selectCluster, selectProject (uses toggle button), clickSearch, clickClearAll, close |
| `src/components/fleet-virt/SavedSearches.ts` | Save/load/remove: saveSearch, openSavedSearches, triggerSavedSearch, removeSavedSearch, getSavedSearchItem |

### Fixture Wiring (target)

Fleet Virt tests will use `src/fixtures/fleet-virt-test.ts`:

```typescript
type FleetVirtFixtures = {
  oc: OcCliService;
  virtConfig: VirtConfig;
  fleetVirtPage: FleetVirtPage;
  advancedSearchModal: AdvancedSearchModal;
  savedSearches: SavedSearches;
};
```

---

## Selectors Reference (from kubevirt-plugin source)

All selectors verified via acm-source MCP against `kubevirt-ui/kubevirt-plugin` release-4.21.
Centralized in `src/constants/selectors.ts` under `SELECTORS.fleetVirt`.

**VM Search:**
- Search input: `[data-test="vm-search-input"] input`
- Search results: `[data-test="search-bar-results"]`

**Advanced Search:**
- Open button: `[data-test="vm-advanced-search"]`
- Name input: `[data-test="adv-search-vm-name"]`
- Cluster wrapper: `[data-test="adv-search-vm-cluster"]`
- Project wrapper: `[data-test="adv-search-vm-project"]`

**VM Table:**
- Resource row: `[data-test-rows="resource-row"]`
- Status cell: `[data-label="status"]`

**Saved Searches:**
- Save form: `[data-test-id="save-search-name"]`, `[data-test-id="save-search-description"]`
- Save button: `[data-test="save-button"]`
- Saved search item: `[data-test="saved-search-item-{name}"]`

**Tree View:**
- Container: `.pf-v6-c-tree-view`
- Cluster node: `li#clusterSelector\/{clusterName}`
- Project node: `li#projectSelector\/{cluster}\/{project}`
- VM node: `li#${cluster}\/${project}\/${vmName}`

**VM Details Page (implemented -- VmDetailsPage.ts):**
- Page heading: `getByRole('heading', { name: /^VM /, level: 1 })` (avoids matching "VirtualMachines" page title)
- Actions dropdown: `getByRole('button', { name: 'Actions' })`
- Status: `getByRole('button', { name: /Running|Stopped|Starting|Paused/ })`
- Console tab: `getByRole('button', { name: 'VNC console' })`, `getByRole('heading', { name: 'Guest login credentials' })`
- Events tab: `getByRole('heading', { name: 'Events', level: 2 })`, `getByRole('button', { name: 'Pause event streaming' })`
- Snapshots tab: `getByRole('heading', { name: 'Snapshots', level: 1 })`, `getByRole('button', { name: 'Take snapshot' })`
- Configuration tab: `getByRole('link', { name: 'Configuration' })`
- Tab navigation: `getByRole('link', { name: tabName, exact: true })` (all tabs are link role elements)

**Bulk Selection (for future tests):**
- VM row checkbox: `tr[data-test-rows="resource-row"]:has(a[data-test="{vmName}"]) input`
- Bulk actions: `.list-managment-group .kv-actions-dropdown button`
- Action items: `li[data-test-id="selected-vms-action-{action}"] button`

---

## VM Lifecycle Actions

| Action | Menu Item Test ID |
|--------|-------------------|
| Start | `selected-vms-action-start` |
| Stop | `selected-vms-action-stop` |
| Restart | `selected-vms-action-restart` |
| Pause | `selected-vms-action-pause` |
| Unpause | `selected-vms-action-unpause` |
| Migrate (in-cluster) | `bulk-migration-actions` |
| Cross-Cluster Live Migration | `cross-cluster-migration` |

---

## Table Component Architecture

Fleet Virt VM tables are **NOT** `AcmTable` instances. They use `VirtualizedTable` from `@openshift-console/dynamic-plugin-sdk`.

| Aspect | ACM Tables (`AcmTable`) | Fleet Virt VM Tables (`VirtualizedTable`) |
|--------|------------------------|------------------------------------------|
| Source | `stolostron/console` | `kubevirt-ui/kubevirt-plugin` |
| Row ID | `data-ouia-component-id` | `data-test-rows="resource-row"` |
| Search | `aria-label="Search input"` | `data-test="vm-search-input"` |

Fleet Virt components are standalone (not extending AcmTable). Per architecture doc: components expose locators, tests assert.

---

## CCLM (Cross-Cluster Live Migration)

Requires `all-clusters` in URL path. The CCLM wizard allows migrating VMs between spoke clusters.

Key source components:
- `kubevirt-ui/kubevirt-plugin`: `src/multicluster/components/` -- CCLM modal
- `stolostron/console`: wrapper integration

---

## Search Cluster Proxy

Fleet Virtualization uses `search-cluster-proxy` to discover resources on spoke clusters. When search-cluster-proxy is down or spoke is disconnected, VM data will not appear in the console.

**Debugging tip:** If VMs don't appear in the Fleet Virt page, check:
1. `oc get managedcluster` -- spoke status should be `True`
2. `oc get pods -n open-cluster-management | grep search` -- search pods running
3. `search-cluster-proxy` pod logs for connectivity errors

---

## Gotchas

- `VIRT_SPOKE_CLUSTER` defaults to `local-cluster` -- set explicitly for spoke-specific tests
- `FleetVirtPage.shouldLoad()` uses `expect().toPass()` with retry-and-reload because search-cluster-proxy connections are slow
- Tree view selectors use escaped forward slashes (`\\/`) in dynamic IDs (CSS escaping requirement)
- VM status transitions are async -- use `expect().toPass()` polling, not `waitForTimeout`
- `data-test` attributes are the primary selector strategy (from kubevirt-plugin source)
- PF version: Fleet Virt uses PF6 components (`pf-v6-c-*` classes)
- The perspective switcher is only visible on OCP 4.20+ and only when ACM provides Fleet Management perspective
- **Advanced search is a side panel, NOT a dialog** -- `getByRole('dialog')` won't work
- **Clicking Search in advanced search navigates to `/search?rowFilter-...`** -- URL changes, panel closes
- **PF6 MultiSelectTypeahead placeholder changes** from "All clusters" to "Select cluster" after selection -- both placeholders must be handled
- **PF6 MultiSelectTypeahead dropdown open** -- clicking the combobox `<input>` is unreliable after other interactions. Click the adjacent toggle button (`button[aria-label="Multi select Typeahead menu toggle"]`) instead
- **RBAC users see a flat table, not tree view** -- admin sees tree (clusters → namespaces → VMs), RBAC users see flat table with columns (Name, Cluster, Namespace, Status). VM names in the flat table are plain text, NOT links. The Cluster column has links to ManagedCluster. To navigate to VM details, construct the URL directly: `/k8s/cluster/${spoke}/ns/${namespace}/kubevirt.io~v1~VirtualMachine/${vmName}`
- **Actions menu differs by role** -- `kubevirt.io:view` shows: Open Console, Clone (disabled), Take snapshot (disabled), Copy SSH (disabled), Edit labels (disabled), Delete (disabled). No Start/Stop/Restart/Migrate. Always verify menu items with browser MCP before writing assertions
- **`textContent()` concatenates without spaces** -- gridcell `textContent()` returns `"VirtualMachineVMcclm-min-roles-vm-2"`. Parse with regex: `cellText.replace(/^VirtualMachineVM/i, '')`
- **VM details heading strict mode** -- Fleet Virt page has two `h1` elements: "VirtualMachines" (page) and "VM \<name\> Running" (details). Use `getByRole('heading', { name: /^VM /, level: 1 })` to match by accessible name
- **`page.reload()` crashes on dead tabs** -- use `page.goto(url).catch(() => {})` in retry loops instead
- Per architecture doc: no `waitForTimeout`, no assertions in page objects/components. Expose locators for tests to assert.
