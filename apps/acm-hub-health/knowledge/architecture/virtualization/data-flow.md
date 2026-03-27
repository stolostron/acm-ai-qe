# Virtualization -- Data Flow

## VM Discovery Flow

```
Spoke Cluster(s)               Hub Cluster                 Hub Cluster
CNV (KubeVirt)                search-collector    -->     search-postgres
VirtualMachine CRs    -->     (indexes VM                      |
VirtualMachineInstance        resources)                       v
                                                       search-api (GraphQL)
                                                              |
                                                              v
                                                    kubevirt-plugin
                                                    (multicluster-sdk)
                                                              |
                                                              v
                                                    Console Browser
                                                    (VM Tree View,
                                                     VM List, Details)
```

---

## Step 1: VM Resources on Spoke

CNV operator manages VMs on spoke clusters. Key resources:
- `VirtualMachine` -- VM definition (spec, runStrategy)
- `VirtualMachineInstance` -- running VM instance
- `DataVolume` -- VM disk (managed by CDI)
- `VirtualMachineSnapshot` -- point-in-time snapshots

These are standard Kubernetes CRs in the spoke cluster's namespaces.

**Failure:** CNV operator not installed -> no VM CRDs exist, resources can't be
created. HCO degraded -> virt-api/virt-controller unhealthy, VM operations fail.

---

## Step 2: Search Collector Indexes VM Resources

search-collector addon on spoke watches VM resources and indexes them into hub's
search-postgres. Collects ~22 resource kinds with ~90 exposed fields for
virtualization.

Key indexed VM fields:
- name, namespace, cluster, kind
- status (Running, Stopped, Paused, Migrating)
- cpu, memory, runStrategy
- labels, annotations, timestamps

**Failure:** search-collector not running on spoke -> VMs from that cluster
don't appear in search. No error -- just missing results. Collector restart ->
full re-index of all VM resources.

---

## Step 3: Search API Serves VM Queries

kubevirt-plugin uses `multicluster-sdk` to query search-api:
1. Browser requests VM list/tree from kubevirt-plugin
2. Plugin translates to GraphQL query against search-api
3. search-api applies RBAC filtering:
   - Cluster-admin: sees all VMs across all clusters
   - RBAC user: sees only VMs within MCRA-granted scope
4. Returns filtered VM resources as typed objects

**Failure:** search-api down -> all VM queries return 500/ECONNREFUSED, VM list
empty. RBAC filtering incorrect -> user sees too many or too few VMs.

---

## Step 4: Console Renders VM UI

kubevirt-plugin renders three main views:
1. **Tree View:** cluster > project > VM hierarchy from search results
2. **VM List:** Flat list with filters (status, cluster, project)
3. **VM Details:** Individual VM info fetched via search-cluster-proxy

**Failure:** kubevirt-plugin not registered -> VM tab absent from console.
Tree view empty -> usually means search returns no namespace-level resources
for the user's scope (requires full namespace access within permitted clusters).

---

## VM Operations Flow

```
Console Browser
  |
  v
kubevirt-plugin (VM Action button: Start/Stop/Pause/Restart)
  |
  v
search-cluster-proxy (proxies request to spoke)
  |
  v
Spoke: virt-api (admission + API server)
  |
  v
Spoke: virt-controller (state machine transition)
  |
  v
Spoke: virt-handler (QEMU/KVM operation on node)
  |
  v
VM state changes on spoke
  |
  v (status update propagates back)
search-collector re-indexes -> search-api -> console updates
```

**Failure at proxy:** search-cluster-proxy can't reach spoke -> 503/timeout.
**Failure at virt-api:** Admission webhook rejects -> operation fails with error.
**Failure at virt-controller:** State transition stuck -> VM stays in transitioning state.

---

## Migration Flow

### MTV Migration (External Source -> OpenShift)

```
Hub: MTV Provider (VMware/RHV/OpenStack credentials)
  |
  v
Hub: mtv-integrations-controller creates ManagedServiceAccount
  |
  v
Hub: Migration Plan created (source, target, VMs, mappings)
  |
  v
Spoke: Forklift controller executes migration
  |   - connects to source provider
  |   - copies disks (warm/cold)
  |   - creates target VM resources
  v
Spoke: VM running on target OpenShift cluster
```

**Failure:** ManagedServiceAccount token expired -> provider goes to staging mode
(ACM-22762). Forklift controller error loop -> migration stuck.

### CCLM (Cross-Cluster Live Migration)

```
Hub: CCLM migration request
  |
  v
Hub: Preflight checks (CNV version, storage, network, RBAC)
  |
  v
Source Spoke: KubeVirt Migration Operator prepares VM
  |
  v
Source -> Target: Live memory + disk transfer
  |
  v
Target Spoke: VM starts on target cluster
  |
  v
Source Spoke: Original VM removed
```

**Failure:** Preflight fails for RBAC users -> CCLM blocked (user lacks
permissions on both clusters). Webhook blocking migration plans (ACM-29920
related race conditions).

---

## Failure Modes at Each Layer

### CNV not on spoke
- **Symptom:** No VMs exist on that cluster. Search has nothing to index.
- **Scope:** That spoke only.
- **Detection:** `oc get csv -n openshift-cnv` on spoke

### cnv-mtv-integrations disabled on hub
- **Symptom:** Fleet Virt tab absent from console. No VM UI at all.
- **Scope:** Entire fleet virt feature.
- **Detection:** `oc get mch -A -o yaml | grep cnv-mtv`

### search-collector missing on spoke
- **Symptom:** VMs exist on spoke but don't appear in hub UI. No error.
- **Scope:** That spoke's VMs.
- **Detection:** `oc get managedclusteraddon search-collector -n {cluster}`

### MCRA permissions incorrect
- **Symptom:** RBAC user sees wrong VMs or no VMs. Cluster-admin sees all.
- **Scope:** Specific RBAC users.
- **Detection:** Check ClusterPermission on spoke, verify kubevirt role labels.

### mtv-integrations-controller down
- **Symptom:** MTV providers not created, migration plans can't execute.
- **Scope:** All MTV migrations.
- **Detection:** `oc get pods -n <mch-ns> -l app=mtv-integrations-controller`
