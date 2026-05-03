# CCLM (Cross-Cluster Live Migration) Area Knowledge

## Overview

CCLM enables live migration of virtual machines between managed clusters in an ACM fleet. The feature is implemented in the kubevirt-plugin (not stolostron/console) and depends on Fleet Virtualization infrastructure, Search subsystem for VM discovery, and RBAC/MCRA for access control.

## Key Components

| Component | Source | Role |
|-----------|--------|------|
| `CrossClusterMigration` | `kubevirt-ui/kubevirt-plugin` repo | Wizard for initiating cross-cluster VM migration |
| `CrossClusterMigrationWizard` | `kubevirt-plugin` `src/multicluster/components/` | Multi-step migration wizard (source → target → review) |
| `TargetStep` | `kubevirt-plugin` `src/multicluster/components/CrossClusterMigration/components/` | Target cluster/namespace selection step |
| `useCrossClusterMigrationSubmit` | `kubevirt-plugin` `src/multicluster/hooks/` | Hook for submitting migration requests |
| `CrossClusterMigrationPlansWidget` | `kubevirt-plugin` overview tab | Widget showing migration plan status |
| `MultiClusterMigrationStatusSection` | `kubevirt-plugin` overview tab | Migration status display in VM list |
| `useACMExtensionActions` | `kubevirt-plugin` `src/multicluster/hooks/` | Registers CCLM as a VM action in ACM context |
| `multicluster-sdk` | Shared lib | Queries search-api for VM and cluster data |

## CRDs / Resources

| CRD | API Group | Purpose |
|-----|-----------|---------|
| VirtualMachine | `kubevirt.io/v1` | VM definition being migrated |
| VirtualMachineInstance | `kubevirt.io/v1` | Running VM instance on source cluster |
| ManagedCluster | `cluster.open-cluster-management.io/v1` | Source and target clusters |
| HyperConverged | `hco.kubevirt.io/v1beta1` | CNV operator config (must exist on both clusters) |

## Navigation Routes

CCLM is accessed via the Fleet Virtualization VM actions menu, not as a standalone page:

| Access Point | Path | Context |
|-------------|------|---------|
| VM Actions Menu | (within Fleet Virt VM list or details) | "Migrate to another cluster" action |
| Migration Wizard | Modal overlay | Multi-step wizard launched from action |
| Migration Status | Overview tab widgets | Status of active/completed migrations |

CCLM pages are part of the kubevirt-plugin ConsolePlugin, not stolostron/console routes.

## Migration Workflow

```
Select VM(s) → Choose Target Cluster → Choose Target Namespace → Review → Submit
  ↓
Migration Plan Created → VM Live Migration → Status Monitoring → Complete/Failed
```

Steps:
1. User selects one or more VMs from the Fleet Virt VM list
2. Triggers "Migrate to another cluster" from the actions menu
3. Wizard opens: select target cluster (must have CNV installed)
4. Select target namespace on the target cluster
5. Review migration configuration
6. Submit — migration plan is created
7. Monitor migration status via Overview tab widgets

## Prerequisites

- **Hub**: `cnv-mtv-integrations` MCH component enabled
- **Source spoke**: CNV/KubeVirt installed, VM(s) running
- **Target spoke**: CNV/KubeVirt installed, compatible storage, network connectivity to source
- **Both spokes**: Matching or compatible CNV versions (CNV 4.16+ required for CCLM)
- **RBAC**: User needs VM migration permissions on both source and target clusters

## Translation Keys

CCLM UI strings are in the kubevirt-plugin, not in stolostron/console translations. Use `set_cnv_version()` in acm-ui MCP and search in `repo="kubevirt"`.

| Context | Search Strategy |
|---------|----------------|
| Migration wizard labels | `search_code("CrossClusterMigration", repo="kubevirt")` |
| Action menu items | `search_code("useACMExtensionActions", repo="kubevirt")` |
| Status labels | `search_code("MigrationStatusSection", repo="kubevirt")` |

## Setup Prerequisites

- **MCP**: Call `set_acm_version()` AND `set_cnv_version()` before any acm-ui search
- **MCP repo**: Use `repo="kubevirt"` for CCLM component searches (not `repo="acm"`)
- At least two spoke clusters with CNV 4.16+ installed
- At least one running VM on the source spoke cluster
- Network connectivity between source and target spokes

## Testing Considerations

- CCLM is a kubevirt-plugin feature — search in `repo="kubevirt"`, not `repo="acm"`
- Set BOTH `set_acm_version()` AND `set_cnv_version()` in acm-ui MCP
- Migration requires TWO spoke clusters with CNV — setup is more complex than single-cluster features
- Migration is a state-changing operation — test cases should verify both success and rollback scenarios
- Target cluster selection depends on which managed clusters have CNV installed
- Migration status monitoring uses the Overview tab widgets (same page as Fleet Virt VM list)
- If `cnv-mtv-integrations` is not enabled on the hub, the CCLM action is not available
- Bulk migration (multiple VMs) is supported via the `BulkVirtualMachineActionFactory`
