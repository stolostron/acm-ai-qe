# Virtualization -- Architecture

## What Virtualization Does

Fleet Virtualization provides centralized management of virtual machines across
multiple OpenShift clusters from the ACM hub. It bridges CNV (OpenShift
Virtualization) on spoke clusters with the ACM console, enabling cross-cluster
VM discovery, lifecycle operations, migration, and RBAC-scoped access control.

---

## Architectural Layers

Three distinct layers work together:

1. **Hub UI layer:** kubevirt-plugin console extension renders VM views in ACM console
2. **Hub integration layer:** cnv-mtv-integrations MCH component, mtv-integrations-controller,
   search integration for cross-cluster VM discovery
3. **Spoke infrastructure layer:** CNV (OpenShift Virtualization) operator runs VMs,
   MTV (Migration Toolkit for Virtualization) handles migrations

---

## Hub-Side Components

### kubevirt-plugin (console extension)

- **Type:** OpenShift ConsolePlugin (dynamic plugin)
- **Registration:** `consoleplugins.console.openshift.io/kubevirt-plugin`

Fleet Virtualization UI is a console extension that renders:
- **VM Tree View:** Hierarchical cluster > project > VM navigation
- **VM Actions:** Start, stop, pause, restart, migrate operations
- **VM Details:** Resource details fetched via search-cluster-proxy

Uses `multicluster-sdk` to query search-api for VM resources across clusters.
VM discovery depends entirely on Search subsystem -- if search is down, VM list
is empty.

### cnv-mtv-integrations (MCH component)

- **MCH component name:** `cnv-mtv-integrations`
- **Default:** Disabled (must be explicitly enabled)

When enabled, deploys:
- CNV Addon to managed clusters (enables VM management)
- MTV Addon to managed clusters (enables migration)
- mtv-integrations-controller on hub

### mtv-integrations-controller

- **Namespace:** MCH namespace
- **Pod label:** `app=mtv-integrations-controller`

Hub-side controller that:
- Manages MTV provider lifecycle for managed clusters
- Creates ManagedServiceAccount (MSA) for spoke access
- Handles ForkliftController CRD reconciliation
- Manages finalizers on ManagedCluster resources for cleanup

### MCRA Integration

Fleet Virtualization integrates with the MCRA (MultiClusterRoleAssignment)
operator for VM-level RBAC:
- MCRA creates ClusterPermission with kubevirt-scoped roles
- ClusterPermission propagated to spokes via ManifestWork
- Search API filters VM results based on MCRA-granted permissions
- Console RBAC UI provides wizard for VM role assignments

---

## Spoke-Side Components

### CNV / OpenShift Virtualization

- **Operator:** `kubevirt-hyperconverged` CSV
- **Namespace:** `openshift-cnv`

HyperConverged Cluster Operator (HCO) manages six sub-operators:
1. **KubeVirt Operator** -- core VM lifecycle (virt-api, virt-controller, virt-handler)
2. **CDI Operator** -- Containerized Data Importer for disk management
3. **SSP Operator** -- Scheduling, Scale, Performance
4. **Cluster Network Addons Operator** -- VM networking (bridges, SR-IOV)
5. **Node Maintenance Operator** -- node drain for VM migration
6. **HostPath Provisioner Operator** -- local storage for VMs

Key spoke pods:
- `virt-api` -- VM API server, admission webhooks
- `virt-controller` -- VM lifecycle state machine
- `virt-handler` -- per-node DaemonSet, manages QEMU/KVM

### MTV / Migration Toolkit for Virtualization

- **Operator:** Forklift operator
- **Namespace:** `openshift-mtv` (or `konveyor-forklift`)

Handles VM migration from external sources (VMware, RHV, OpenStack) and
cross-cluster live migration (CCLM):
- **Migration Controller** -- orchestrates migration plans
- **Provider Controller** -- manages source/target provider connections
- **Plan Controller** -- executes migration plans step-by-step
- **StorageMap/NetworkMap Controllers** -- maps source to target storage/network

### CCLM (Cross-Cluster Live Migration)

Uses KubeVirt Migration Operator (depends on KubeVirt Operator) for live VM
migration between OpenShift clusters. Requires:
- Source and target clusters both running CNV
- Network connectivity between clusters
- Compatible storage backends
- RBAC user needs both source and target cluster permissions

---

## MCH Component Toggle

cnv-mtv-integrations is **disabled by default**. Two independent prerequisites:

1. **Hub:** cnv-mtv-integrations MCH component enabled
2. **Spoke:** CNV operator installed on spoke clusters

Missing hub flag -> Fleet Virt UI tab absent (no error, just missing nav item).
Missing spoke CNV -> VMs can't exist on that cluster, but UI tab still renders.

---

## Cross-Subsystem Dependencies

| Dependency | Why |
|---|---|
| Search | VM discovery uses search-api via multicluster-sdk; search down = empty VM list |
| Console | kubevirt-plugin is a ConsolePlugin; console down = no VM UI |
| RBAC / MCRA | VM access control uses MCRA -> ClusterPermission -> spoke roles |
| Infrastructure (klusterlet) | VM operations proxied through spoke connectivity |
| search-cluster-proxy | Direct spoke resource queries for VM details/actions |

## What Depends on Virtualization

| Consumer | Impact When Virt Is Down |
|---|---|
| Fleet Virt UI (VM Tree View) | VM list empty, tree view empty |
| VM Actions (start/stop/migrate) | Operations fail or timeout |
| CCLM (Cross-Cluster Live Migration) | Live migration unavailable |
| MTV migration plans | VM migration from external sources fails |
| RBAC UI VM role assignments | Cannot assign VM-scoped roles |
