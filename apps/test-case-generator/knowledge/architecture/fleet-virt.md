# Fleet Virtualization Area Knowledge

## Overview

Fleet Virtualization in ACM Console provides centralized management of virtual machines across managed clusters running OpenShift Virtualization (CNV/KubeVirt). Depends on Search subsystem for VM discovery and RBAC/MCRA for access control.

## Key Components

| Component | Source | Role |
|-----------|--------|------|
| `kubevirt-plugin` | `kubevirt-ui/kubevirt-plugin` repo | ConsolePlugin providing VM UI (`consoleplugins.console.openshift.io/kubevirt-plugin`) |
| `mtv-integrations-controller` | Hub deployment (ocm namespace) | Hub-side controller for MTV integration |
| Tree View | Plugin component | Hierarchical cluster > project > VM navigation |
| VM Actions Menu | Plugin component | Start, stop, restart, pause, migrate actions |
| Saved Searches | Plugin component | Persistent VM filter configurations |
| `multicluster-sdk` | Shared lib | Queries search-api for VM data |

## CRDs / Resources

| CRD | API Group | Purpose |
|-----|-----------|---------|
| VirtualMachine | `kubevirt.io/v1` | VM definition and lifecycle |
| VirtualMachineInstance | `kubevirt.io/v1` | Running VM instance |
| HyperConverged | `hco.kubevirt.io/v1beta1` | CNV operator configuration |
| ForkliftController | `forklift.konveyor.io/v1beta1` | MTV migration controller |

## MCH Component

- `cnv-mtv-integrations` — **disabled by default**
- Must be explicitly enabled in MCH for Fleet Virt UI tab to appear
- If not enabled: the UI tab is simply absent (no error, just missing navigation)

## Navigation Routes

Fleet Virtualization pages are part of the Infrastructure section. Routes are provided by the kubevirt-plugin ConsolePlugin.

## VM State Machine

```
Stopped → Starting → Running → Pausing → Paused
Running → Migrating → Running (on different node)
Running → Stopping → Stopped
Any → Error
```

Actions available depend on current state:
- **Stopped**: Start, Clone, Delete
- **Running**: Stop, Restart, Pause, Migrate, Console
- **Paused**: Unpause, Stop

## CNV Spoke Stack (Sub-operators)

1. KubeVirt Operator — core VM lifecycle (`virt-api`, `virt-controller`, `virt-handler`)
2. CDI Operator — Containerized Data Importer (disk images)
3. SSP Operator — Scheduling, Scale, Performance
4. Cluster Network Addons Operator — VM networking
5. Node Maintenance Operator — node drain for live migration
6. HostPath Provisioner Operator — local storage

## RBAC Integration

- MCRA creates ClusterPermission with kubevirt-scoped roles
- ClusterPermission propagated to spokes via ManifestWork
- search-api filters VM results by MCRA permissions
- Console RBAC wizard provides VM-specific role assignments

## Setup Prerequisites

- **Hub**: `cnv-mtv-integrations` MCH component enabled (disabled by default)
- **Spokes**: CNV/KubeVirt operator installed with HyperConverged CR
- **MCP**: Call `set_acm_version()` AND `set_cnv_version()` before any acm-ui search
- At least one running VM on a spoke cluster for action testing
- For CCLM (cross-cluster live migration): network connectivity, compatible storage, matching CNV versions

## Testing Considerations

- Set BOTH `set_acm_version()` AND `set_cnv_version()` in acm-ui MCP — they are independent settings
- VM actions depend on VM state (running vs stopped) — verify state before testing actions
- Tree view toggle persists across page navigations — test persistence
- VM list is entirely sourced from Search subsystem — if search is down, VM list is empty
- Missing hub flag (`cnv-mtv-integrations` disabled) causes the Fleet Virt tab to be absent, not an error
- Missing spoke CNV means VMs can't exist but the UI tab still renders
- QE repos (e2e test selectors) always use `main` branch regardless of version setting
- For Gatekeeper mutation policies, the Clusters tab table uses a reduced column set
