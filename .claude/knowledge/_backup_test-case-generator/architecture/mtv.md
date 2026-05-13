# MTV (Migration Toolkit for Virtualization) Area Knowledge

## Overview

MTV (Migration Toolkit for Virtualization, also known as Forklift) enables migration of virtual machines from external virtualization platforms (VMware, RHV, OpenStack, OVA) to OpenShift Virtualization. In the ACM context, MTV integrations provide fleet-level visibility of migration plans and status across managed clusters.

## Key Components

| Component | Source | Role |
|-----------|--------|------|
| `ForkliftController` | Spoke deployment | MTV operator managing migrations on spoke clusters |
| `MigrationsWidget` | `kubevirt-plugin` `src/views/virtualmachines/list/components/OverviewTab/widgets/` | Overview widget showing MTV migration plan status |
| `useMTVPlans` | `kubevirt-plugin` hook | Fetches MTV plan data for status display |
| `mtvPlanStatus` | `kubevirt-plugin` utils | Parses MTV plan status for UI display |
| `mtv-integrations-controller` | Hub deployment | Hub-side controller for MTV fleet integration |
| `multicluster-sdk` | Shared lib | Queries search-api for migration data across clusters |

## CRDs / Resources

| CRD | API Group | Purpose |
|-----|-----------|---------|
| ForkliftController | `forklift.konveyor.io/v1beta1` | MTV operator lifecycle |
| Plan | `forklift.konveyor.io/v1beta1` | Migration plan definition |
| Migration | `forklift.konveyor.io/v1beta1` | Active migration execution |
| Provider | `forklift.konveyor.io/v1beta1` | Source virtualization provider (VMware, RHV, etc.) |
| NetworkMap | `forklift.konveyor.io/v1beta1` | Network mapping from source to target |
| StorageMap | `forklift.konveyor.io/v1beta1` | Storage mapping from source to target |
| Host | `forklift.konveyor.io/v1beta1` | Source host representation |

## Navigation Routes

MTV features in ACM are accessed via the Fleet Virtualization Overview tab, not as standalone pages:

| Access Point | Path | Context |
|-------------|------|---------|
| Migrations Widget | Overview tab in Fleet Virt VM list | Shows MTV plan status across fleet |
| MTV Plan Details | (links to spoke OCP console) | Individual plan details on spoke cluster |

MTV migration plan management (create, edit, delete) is done on the spoke cluster's OCP console, not through the ACM hub console. ACM provides fleet-level visibility only.

## Migration Workflow (Spoke-Level)

```
Create Provider → Create NetworkMap → Create StorageMap → Create Plan → Run Migration
  ↓
Migration Running → VM Conversion → VM Import → Complete/Failed
```

## MCH Component

- `cnv-mtv-integrations` — **disabled by default**
- Must be explicitly enabled in MCH for MTV integration features
- Same flag controls both Fleet Virt and MTV integration visibility

## Provider Types

| Provider | Source Platform | Key Configuration |
|----------|---------------|-------------------|
| VMware (vSphere) | vCenter Server | URL, credentials, TLS fingerprint |
| Red Hat Virtualization | RHV/oVirt | URL, credentials, CA cert |
| OpenStack | OpenStack | URL, credentials, project |
| OVA | Open Virtual Appliance | NFS share path |

## Translation Keys

MTV UI strings are primarily in the kubevirt-plugin, not stolostron/console. Use `repo="kubevirt"` in acm-source MCP.

| Context | Search Strategy |
|---------|----------------|
| Migration widget labels | `search_code("MigrationsWidget", repo="kubevirt")` |
| Plan status strings | `search_code("mtvPlanStatus", repo="kubevirt")` |
| Migration status | `search_code("useMTVPlans", repo="kubevirt")` |

## Setup Prerequisites

- **Hub**: `cnv-mtv-integrations` MCH component enabled
- **Spokes**: MTV (Forklift) operator installed
- **Spokes**: CNV/KubeVirt installed (target for migrated VMs)
- **MCP**: Call `set_acm_version()` AND `set_cnv_version()` before acm-source searches
- **MCP repo**: Use `repo="kubevirt"` for MTV component searches
- At least one spoke with an active MTV migration plan for status testing

## Testing Considerations

- MTV is primarily a kubevirt-plugin feature — search in `repo="kubevirt"`, not `repo="acm"`
- Set BOTH `set_acm_version()` AND `set_cnv_version()` in acm-source MCP
- ACM provides fleet-level MTV visibility, not plan management — test cases should focus on viewing/monitoring, not creating migration plans
- MTV plan creation and management is done on the spoke OCP console — if testing plan creation, that's a spoke-level test, not an ACM hub test
- Migration plan status values: Created, Ready, Running, Succeeded, Failed, Canceled
- Provider credential management may overlap with the Credentials area — scope carefully
- If `cnv-mtv-integrations` is not enabled on the hub, MTV widgets are not visible
- MTV plan data is sourced from Search subsystem — if search is down, migration data is empty
