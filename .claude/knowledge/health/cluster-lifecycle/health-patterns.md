# Managed Cluster Health Patterns (Hub-Side)

How to diagnose managed cluster health from the hub without spoke access.
The agent only has `oc` against the hub -- all diagnostics here use hub-side
resources to infer spoke health.

---

## Hub-Side Resources Per Managed Cluster

Each managed cluster creates these resources on the hub:

| Resource | Namespace | Purpose |
|----------|-----------|---------|
| ManagedCluster CR | cluster-scoped | Cluster registration and status |
| Namespace | `<cluster-name>` | Per-cluster namespace for all resources |
| Lease | `<cluster-name>` | Heartbeat from klusterlet (renewed every ~60s) |
| ManifestWorks | `<cluster-name>` | Workloads delivered to the spoke |
| ManagedClusterAddons | `<cluster-name>` | Addon status per cluster |
| ManagedClusterInfo | `<cluster-name>` | Extended cluster metadata |

---

## ManagedCluster Conditions

The primary health signals from `oc get managedcluster <name> -o yaml`:

| Condition | True | False | Unknown |
|-----------|------|-------|---------|
| HubAccepted | Hub approved the cluster | Hub rejected | Not evaluated yet |
| ManagedClusterJoined | Spoke registered with hub | Never connected | Registration pending |
| ManagedClusterConditionAvailable | Lease is current, spoke is reachable | Spoke unreachable | Lease stale or transitioning |

**Available is the key health signal.** It reflects whether the klusterlet
on the spoke is renewing its lease with the hub.

---

## Lease-Based Health Assessment

The lease is the most reliable hub-side indicator of spoke connectivity:

```bash
# Check lease for a specific cluster
oc get lease -n <cluster-name> --sort-by=.spec.renewTime

# Check lease renewal time
oc get lease <cluster-name>-lease -n <cluster-name> \
  -o jsonpath='{.spec.renewTime}'
```

| Lease State | Meaning |
|-------------|---------|
| Renewed within last 5 min | Spoke is connected and healthy |
| Stale (5-15 min old) | Possible transient network issue |
| Stale (>15 min old) | Spoke likely unreachable |
| Missing | Spoke never connected or namespace corrupted |

---

## Diagnosing AVAILABLE=False

When a managed cluster shows AVAILABLE=False, check in this order:

### Step 1: Is it one cluster or many?

```bash
oc get managedclusters -o custom-columns=NAME:.metadata.name,AVAILABLE:.status.conditions[0].status
```

- **One cluster**: Likely spoke-specific issue (network, node, klusterlet)
- **Many clusters**: Likely hub-side issue (API server load, registration controller)
- **ALL clusters**: Check hub registration controller and API server

### Step 2: Check the condition message

```bash
oc get managedcluster <name> -o jsonpath='{.status.conditions}' | jq .
```

Common messages and what they mean:

| Message | Root Cause | Hub or Spoke? |
|---------|-----------|---------------|
| "the client is rate limited" | Hub API server overloaded | Hub |
| "failed to send lease update" | Spoke can't reach hub API | Spoke/Network |
| "cluster has no agent" | Klusterlet not deployed | Spoke |
| "cluster is not available" | Generic -- check lease | Either |

### Step 3: Check addon status for that cluster

```bash
oc get managedclusteraddons -n <cluster-name>
```

- **ALL addons Unavailable**: Connectivity issue (spoke can't reach hub)
- **Single addon Unavailable**: That specific addon has a problem
- **Addons Available but cluster NotReady**: Rare -- lease renewal issue

### Step 4: Check events in the cluster namespace

```bash
oc get events -n <cluster-name> --sort-by=.lastTimestamp | tail -10
```

Look for: certificate expiry, RBAC errors, import failures.

---

## Hub-Side vs Spoke-Side Problems

| Symptom | Points to Hub Problem | Points to Spoke Problem |
|---------|----------------------|------------------------|
| Multiple clusters NotReady simultaneously | Yes | No (unless shared infra) |
| Single cluster NotReady, others fine | No | Yes |
| Cluster was healthy, suddenly NotReady | Check hub API load first | Then check spoke |
| Cluster never became Ready after import | Check import controller | Check spoke network |
| Addons Available, cluster NotReady | Registration controller | Unlikely spoke issue |
| All addons + cluster NotReady | Connectivity | Spoke or network |

---

## Hub Controllers That Affect Managed Cluster Health

| Controller | Namespace | Impact If Down |
|-----------|-----------|---------------|
| registration-operator | open-cluster-management-hub | New clusters can't register |
| registration-controller | open-cluster-management-hub | CSR approval stops, leases not monitored |
| work-manager | open-cluster-management-hub | ManifestWork delivery stops |
| placement-controller | multicluster-engine | Placement decisions stop |
| addon-manager | multicluster-engine | Addon deployment stops |
| managedcluster-import-controller | multicluster-engine | New cluster imports fail |

```bash
# Quick check of all hub controllers
oc get pods -n open-cluster-management-hub --no-headers
oc get pods -n multicluster-engine | grep -E 'registration|work-manager|placement|addon-manager|import'
```

---

## Common Patterns

### Pattern: Gradual Cluster Disconnection

Clusters go NotReady one at a time over hours/days. Usually caused by:
- Certificate expiry on spokes (check klusterlet client cert rotation)
- Spoke node pressure causing klusterlet eviction
- Network policy changes in the environment

### Pattern: All Clusters NotReady Simultaneously

All managed clusters become NotReady at the same time. Usually caused by:
- Hub API server restart or overload
- Registration controller crash
- Network infrastructure change (firewall, proxy)

### Pattern: New Clusters Can't Join, Existing Are Fine

Import succeeds but cluster stays in Pending. Usually caused by:
- CSR approval backlog (check `oc get csr | grep Pending`)
- Registration controller healthy but can't approve (RBAC issue)
- Import controller created the ManagedCluster but klusterlet can't connect

---

## See Also

- `cluster-lifecycle/architecture.md` -- Import, detach, upgrade flows
- `cluster-lifecycle/known-issues.md` -- CLC bugs affecting managed clusters
- `infrastructure/known-issues.md` -- Klusterlet disconnection patterns
- `diagnostics/common-diagnostic-traps.md` -- Trap 6 (NotReady misdiagnosis)
