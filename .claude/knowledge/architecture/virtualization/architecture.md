---
type: architecture
subsystem: virtualization
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - data-flow/virtualization/data-flow.md
  - health/virtualization/known-issues.md
  - failures/virtualization/failure-signatures.md
  - ui/fleet-virt.md
  - automation/playwright/fleet-virt.md
---

# Virtualization (Fleet Virtualization) -- Architecture

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

### Console Backend VM Proxy

- **Component:** `console-chart-console-v2`
- **Namespace:** MCH namespace (ocm)
- **Route file:** `backend/src/routes/virtualMachineProxy.ts`

Proxies VM actions (start, stop, migrate) through the console backend.

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

---

## Key CRDs

| CRD | API Group | Purpose |
|-----|-----------|---------|
| VirtualMachine | kubevirt.io/v1 | VM definition and lifecycle |
| VirtualMachineInstance | kubevirt.io/v1 | Running VM instance |
| DataVolume | cdi.kubevirt.io/v1beta1 | VM disk storage |
| MigrationPolicy | migrations.kubevirt.io/v1alpha1 | Migration configuration |
| Provider | forklift.konveyor.io/v1beta1 | Migration source/target provider |
| ForkliftController | forklift.konveyor.io/v1beta1 | MTV controller management |

---

## CCLM (Cross-Cluster Live Migration)

Live VM migration between OpenShift clusters using CNV's decentralized
migration API and Submariner for cross-cluster pod-to-pod connectivity.

### virt-synchronization-controller

| Field | Value |
|-------|-------|
| Namespace | `openshift-cnv` |
| Replicas | 2 |
| Port | 9185/TCP |
| Label | `kubevirt.io=virt-synchronization-controller` |

Handles live memory state transfer during cross-cluster migration. The source
cluster's controller streams VM memory pages to the destination cluster's
controller over port 9185 via the Submariner tunnel. Must be running on both
source and target clusters.

### ServiceExport for Cross-Cluster Discovery

The virt-synchronization-controller Service must be exported via a
`ServiceExport` (`multicluster.x-k8s.io/v1alpha1`) on both hub and spoke.
Submariner's Lighthouse agent syncs this to other clusters as a `ServiceImport`,
enabling DNS resolution at:

```
virt-synchronization-controller.openshift-cnv.svc.clusterset.local
```

Without the ServiceExport, the sync controllers on different clusters cannot
discover each other, and migration silently fails to start.

### Feature Gates

The `decentralizedLiveMigration` feature gate must be enabled on the
HyperConverged CR on **both** hub and spoke clusters:

```bash
oc patch hyperconverged kubevirt-hyperconverged -n openshift-cnv \
  --type=merge -p '{"spec":{"featureGates":{"decentralizedLiveMigration":true}}}'
```

This enables the virt-synchronization-controller deployment and the
cross-cluster migration API.

### UI Visibility ConfigMap

The `kubevirt-ui-features` ConfigMap in `openshift-cnv` controls whether the
"Cross cluster migration" option appears in the Fleet Virt console
(VM Actions > Migration submenu):

```bash
oc patch configmap kubevirt-ui-features -n openshift-cnv \
  --type=merge -p '{"data":{"kubevirtCrossClusterMigration":"true"}}'
```

Without this patch, the CCLM action is hidden in the UI even if all backend
prerequisites are met.

### Prerequisites (complete list)

1. CNV installed on **both** clusters (HyperConverged CR in Available state)
2. Submariner tunnel connected between clusters (gateway active, connection established)
3. `decentralizedLiveMigration` feature gate enabled on both clusters' HyperConverged CR
4. `ServiceExport` created for virt-synchronization-controller on both clusters
5. `kubevirt-ui-features` ConfigMap patched with `kubevirtCrossClusterMigration: "true"`
6. MTV operator installed, ForkliftController Available
7. Provider CRs with valid credentials for source and target
8. KVM-capable worker nodes on target cluster (`devices.kubevirt.io/kvm` in node allocatable)
9. RBAC user needs permissions on both source and target clusters
10. Compatible storage backends on both clusters

### Migration Flow

```
1. User selects "Cross cluster migration" from VM Actions menu
2. UI reads kubevirt-ui-features ConfigMap to confirm CCLM is enabled
3. User selects target cluster and target namespace
4. MTV creates a Migration Plan (Forklift) with source/target providers
5. Source virt-synchronization-controller begins streaming VM memory pages
   to target controller over port 9185 via Submariner tunnel
6. Target controller writes memory pages to a new VMI on the target cluster
7. Final memory delta is transferred (convergence phase)
8. Source VM is stopped, target VM is started
9. Migration Plan status transitions to Succeeded
```

### Failure Modes

| Missing Prerequisite | Failure Behavior |
|---|---|
| No KVM nodes on target | VM scheduling failure (FailedScheduling) |
| Provider token expired | Migration starts but never completes (silent failure) |
| No Submariner tunnel | Migration fails with timeout |
| No ServiceExport | Sync controllers cannot discover each other, migration hangs |
| Feature gate disabled | Migration API returns 404, UI action hidden |
| Incompatible storage | DataVolume creation fails on target cluster |

---

## Prerequisites

- `cnv-mtv-integrations` enabled in MCH (disabled by default -- must be explicitly enabled)
- CNV operator installed on spoke cluster (CSV phase: Succeeded)
- HyperConverged CR in Available state
- KVM-capable worker nodes on spoke (check `devices.kubevirt.io/kvm` in node allocatable)
- For migrations: MTV operator installed, Provider CRs configured with valid credentials

---

## MCH Component Toggle

cnv-mtv-integrations is **disabled by default**. Two independent prerequisites:

1. **Hub:** cnv-mtv-integrations MCH component enabled
2. **Spoke:** CNV operator installed on spoke clusters

Missing hub flag -> Fleet Virt UI tab absent (no error, just missing nav item).
Missing spoke CNV -> VMs can't exist on that cluster, but UI tab still renders.

---

## Console Integration

Fleet Virt pages: `/k8s/all-clusters/all-namespaces/kubevirt.io~v1~VirtualMachine`

The console's kubevirt plugin provides the VM list, tree view, and action menus.
VM actions (start, stop, migrate, clone, delete) are proxied through the console
backend via `backend/src/routes/virtualMachineProxy.ts`.

VM search uses the search infrastructure -- if search-collector is missing on a
spoke, VMs from that spoke won't appear in the Fleet Virt VM list.

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
