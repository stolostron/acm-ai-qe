# Virtualization Data Flow

How VM operations flow from the console through the hub to spoke clusters.

---

## VM Action Flow (Start, Stop, Migrate)

```
User clicks VM action in Fleet Virt UI
  -> frontend sends action request
  -> POST /api/proxy/vm
    -> backend/src/routes/virtualMachineProxy.ts
      -> determines action type (start, stop, migrate, clone, delete)
      -> constructs target URL for spoke cluster's kubevirt API
      -> proxies request to managed cluster
        -> kubevirt API executes the action
        -> returns result
      -> backend returns response to frontend
  -> frontend shows success/failure toast
  -> SSE event updates VM status in real-time
```

## VM GET (Status Query) Flow

```
UI needs VM current status
  -> GET /api/proxy/vm/<name>
    -> virtualMachineProxy.ts virtualMachineGETProxy()
      -> fetches VM from spoke cluster
      -> returns status (Running, Scheduling, Stopped, etc.)
  -> UI displays printableStatus
```

Bug injection point: the response can be modified before returning to the
frontend (e.g., Running -> Scheduling), causing the UI to show wrong status.

## VM Resource Usage Flow

```
UI shows VM resource usage (CPU, memory)
  -> GET /api/proxy/vm/<name>/usage
    -> virtualMachineProxy.ts vmResourceUsageProxy()
      -> fetches usage metrics from spoke
      -> returns { cpu: <value>, memory: <value> }
  -> UI renders usage charts
```

Bug injection point: usage values can be multiplied/divided before returning.

## VM Discovery via Search

```
Fleet Virt VM list page loads
  -> queries search for kind:VirtualMachine across all clusters
  -> search-api queries search-postgres
  -> returns VM list from all spokes where search-collector runs
  -> UI renders VM table with cluster column
```

If search-collector is missing on a spoke, VMs from that spoke silently
disappear from the list. No error -- just fewer VMs shown.

## CCLM Migration Flow

```
User initiates cross-cluster migration
  -> UI collects source VM, target cluster, migration policy
  -> creates Migration CR on source spoke via MTV
    -> ForkliftController orchestrates migration
    -> Provider credentials used to access source/target
    -> VM data transferred between clusters
    -> Target cluster creates VirtualMachine from migrated data
  -> Migration status updates via SSE
```

## Failure Points

| Point | What breaks | Symptom |
|-------|------------|---------|
| virtualMachineProxy returns fake success | VM action appears to succeed but VM state unchanged | "VM stopped" toast but VM keeps running |
| VM GET response modified | UI shows wrong VM status | Running VMs appear as "Scheduling" |
| Usage values falsified | Resource charts show wrong data | CPU 2.5x too high, memory 70% too low |
| No KVM nodes | VM scheduling failure | FailedScheduling error, VM stuck in Scheduling |
| Provider token expired | Migration silently fails | UI shows "migration started" but never completes |
| search-collector missing | VMs from spoke absent | VM list shows fewer VMs than expected |
