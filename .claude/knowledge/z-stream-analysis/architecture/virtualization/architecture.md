# Fleet Virtualization Architecture

Fleet Virtualization enables VM management across managed clusters through the
ACM console. It integrates CNV (Container-native Virtualization) and MTV
(Migration Toolkit for Virtualization) with the ACM hub.

---

## Components

### Hub-side (ACM Console)
| Component | Type | Namespace | Role |
|-----------|------|-----------|------|
| console-chart-console-v2 | Hub deployment | ocm | Proxies VM actions via virtualMachineProxy.ts |
| kubevirt ConsolePlugin | OCP plugin | N/A | Fleet Virt UI (tree view, VM list, actions) |

### Spoke-side (CNV)
| Component | Type | Namespace | Role |
|-----------|------|-----------|------|
| kubevirt-operator | Spoke operator | openshift-cnv | Manages CNV components |
| virt-api | Spoke deployment | openshift-cnv | VM lifecycle API |
| virt-controller | Spoke deployment | openshift-cnv | VM reconciliation |
| virt-handler | Spoke daemonset | openshift-cnv | Per-node VM management |
| hyperconverged-cluster-operator | Spoke operator | openshift-cnv | HyperConverged CR management |

### Spoke-side (MTV)
| Component | Type | Namespace | Role |
|-----------|------|-----------|------|
| forklift-operator | Spoke operator | openshift-mtv | Manages MTV components |
| ForkliftController | Spoke CR | openshift-mtv | MTV controller lifecycle |
| Provider CRs | Spoke CRDs | openshift-mtv | Source/target for migrations |

## Prerequisites

- `cnv-mtv-integrations` enabled in MCH (disabled by default -- must be explicitly enabled)
- CNV operator installed on spoke cluster (CSV phase: Succeeded)
- HyperConverged CR in Available state
- KVM-capable worker nodes on spoke (check `devices.kubevirt.io/kvm` in node allocatable)
- For migrations: MTV operator installed, Provider CRs configured with valid credentials

## Key CRDs

| CRD | API Group | Purpose |
|-----|-----------|---------|
| VirtualMachine | kubevirt.io/v1 | VM definition and lifecycle |
| VirtualMachineInstance | kubevirt.io/v1 | Running VM instance |
| DataVolume | cdi.kubevirt.io/v1beta1 | VM disk storage |
| MigrationPolicy | migrations.kubevirt.io/v1alpha1 | Migration configuration |
| Provider | forklift.konveyor.io/v1beta1 | Migration source/target provider |
| ForkliftController | forklift.konveyor.io/v1beta1 | MTV controller management |

## Console Integration

Fleet Virt pages: `/k8s/all-clusters/all-namespaces/kubevirt.io~v1~VirtualMachine`

The console's kubevirt plugin provides the VM list, tree view, and action menus.
VM actions (start, stop, migrate, clone, delete) are proxied through the console
backend via `backend/src/routes/virtualMachineProxy.ts`.

VM search uses the search infrastructure -- if search-collector is missing on a
spoke, VMs from that spoke won't appear in the Fleet Virt VM list.

## CCLM (Cross-Cluster Live Migration)

CCLM requires:
1. CNV on both source and target spokes
2. MTV operator with ForkliftController Available
3. Provider CRs with valid credentials for source and target
4. Network connectivity between source and target clusters
5. KVM-capable nodes on the target cluster

If ANY of these prerequisites is missing, migration fails. The failure mode
depends on which prerequisite is broken:
- No KVM nodes: VM scheduling failure (FailedScheduling)
- Provider token expired: migration starts but never completes (silent failure)
- No network: migration fails with timeout
