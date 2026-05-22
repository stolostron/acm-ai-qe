# Fleet Virtualization Area Knowledge Base

Domain knowledge for writing Fleet Virtualization (VM management) automation tests.

---

## Prerequisites

- ACM hub cluster with Fleet Virtualization enabled
- Spoke cluster with CNV (OpenShift Virtualization) installed and VMs running
- Spoke cluster imported as ManagedCluster in ACM

---

## Required Environment Variables

| Variable | Purpose |
|----------|---------|
| `CYPRESS_VIRT_SPOKE_CLUSTER` | Spoke cluster name (may be comma-separated) |
| `CYPRESS_HUB_API_URL` | Hub API URL for cleanup |
| `CYPRESS_BASE_URL` | Console URL |

**Guard pattern:**
```javascript
const spokeCluster = (Cypress.env('VIRT_SPOKE_CLUSTER') || '').split(',')[0].trim()
before(function () {
  if (!spokeCluster) this.skip('VIRT_SPOKE_CLUSTER not set')
})
```

---

## Navigation

Fleet Virtualization VM list page:
- Path: `/k8s/all-clusters/all-namespaces/kubevirt.io~v1~VirtualMachine`
- Constants: `constants.fleetVirtVMsPath`
- URL must contain `all-clusters` for CCLM (cross-cluster live migration) to be available

Use `fleetVirtMethods.goToFleetVirtualization()` -- handles perspective switcher (OCP 4.20+) and navigation.

---

## Existing Files and Utilities

### View Files (Page Objects)

| File | Key Exports |
|------|-------------|
| `cypress/views/virtualization/fleetVirtualization.js` | `fleetVirtSelectors` (navigation, vmSearch, advancedSearch, vmTable, treeView, vmDetails, bulkSelection), `fleetVirtMethods` (goToFleetVirtualization, shouldLoad, searchVM, clickVMInTreeView, verifyVMStatus, selectVMsForBulkAction, performBulkAction) |
| `cypress/views/virtualization/virtualization.js` | General virt helpers (non-fleet) |
| `cypress/views/virtualization/searchClusterProxy.js` | Search cluster proxy helpers for spoke resource discovery |
| `cypress/views/virtualization/roleAssignmentWizard.js` | RBAC wizard (see rbac.md knowledge base) |

### Selectors Reference (`fleetVirtSelectors`)

**Navigation:**
- Perspective switcher: `[data-test-id="perspective-switcher-toggle"]`
- Fleet Management option: text `'Fleet Management'`

**VM Search:**
- Search input: `[data-test="vm-search-input"] input`
- Search results: `[data-test="search-bar-results"]`
- Reset button: `button[aria-label="Reset"]`

**Advanced Search Modal:**
- Open button: `[data-test="vm-advanced-search"]`
- Name input: `[data-test="adv-search-vm-name"]`
- Cluster toggle: `[data-test="adv-search-vm-cluster-toggle"]`
- Project toggle: `[data-test="adv-search-vm-project-toggle"]`

**Tree View (left sidebar):**
- Container: `.pf-v6-c-tree-view`
- List item: `.pf-v6-c-tree-view__list-item`
- Node text: `.pf-v6-c-tree-view__node-text`
- Cluster node (dynamic): `li#clusterSelector\/{clusterName}`
- Project node (dynamic): `li#projectSelector\/{cluster}\/{project}`
- VM node (dynamic): `li#{cluster}\/{project}\/{vmName}`

**VM Details Page:**
- Actions dropdown: `[data-test="actions-dropdown"] button`
- Status field: `[data-test-id="virtual-machine-overview-details-status"]`
- Cluster field: `[data-test-id="virtual-machine-overview-details-cluster"]`
- Name field: `[data-test-id="virtual-machine-overview-details-name"]`

**Bulk Selection:**
- VM row checkbox: `tr[data-test-rows="resource-row"]:has(a[data-test="{vmName}"]) input.pf-v6-c-check__input`
- Bulk actions dropdown: `.list-managment-group .kv-actions-dropdown button.pf-v6-c-menu-toggle.pf-m-secondary`
- Migrate menu item: `li[data-test-id="bulk-migration-actions"] button`
- Cross-cluster migration: `li[data-test-id="cross-cluster-migration"] button`
- Start/Stop/Restart/Pause/Unpause: `li[data-test-id="selected-vms-action-{action}"] button`
- Selection count: `[data-ouia-component-id="BulkSelect-text"]`
- VM row (by name): `tr[data-test-rows="resource-row"]:has(a[data-test="{vmName}"])`

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

## Test Area Structure

| Directory | Specs |
|-----------|-------|
| `cypress/tests/virtualization/` | Non-RBAC Fleet Virt tests (3 specs) |
| `cypress/tests/rbac/virtualization/` | RBAC + Fleet Virt tests (26 specs) |
| `cypress/tests/hostedClusters/virtualization/` | Hosted cluster virt tests (1 spec) |

---

## Tags

| Tag | When |
|-----|------|
| `@CLC` | Always |
| `@e2e-virt` | Fleet Virt tests (run in e2e-virt stage) |
| `@virtualization` | Virtualization feature |
| `@rbac` | If test involves RBAC |
| `@roleassignment` | If test involves RA wizard |

---

## Gotchas

- `VIRT_SPOKE_CLUSTER` may be comma-separated -- always `.split(',')[0].trim()`
- Fleet Virt page uses `shouldLoad()` with retry-and-reload pattern (up to 5 retries) because the page can take time to initialize search-cluster-proxy connections
- Tree view selectors use escaped forward slashes (`\\/`) in dynamic IDs (CSS escaping requirement)
- VM status checks need `cy.waitUntil()` with polling -- VM state transitions are async
- `data-test` attributes are the primary selector strategy for Fleet Virt (from kubevirt-plugin source)
- PF version: Fleet Virt uses PF6 components (`pf-v6-c-*` classes)
- The perspective switcher is only visible on OCP 4.20+ and only when ACM provides Fleet Management perspective
