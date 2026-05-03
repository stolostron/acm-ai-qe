# Kubernetes Fundamentals for ACM Hub Diagnosis

This document covers the Kubernetes internals an AI agent must understand to
diagnose issues on an ACM hub cluster. It prioritizes mechanisms over
definitions -- HOW things work, not just what they are.

---

## 1. The Operator Pattern

### Controllers and Reconciliation

A Kubernetes controller is a control loop that watches cluster state through
the API server and makes changes to move current state toward desired state.
Every controller follows:

```
Observe (read current state) -> Compare (diff against desired) -> Act (make changes) -> Repeat
```

The core function is the **Reconcile loop**. When called, it receives a
namespace/name pair identifying the changed object. The controller then:

1. Fetches the current object from the API server (or its local cache)
2. Reads `.spec` (desired state)
3. Reads `.status` (current state)
4. Computes the diff
5. Takes action (create/update/delete child resources)
6. Updates `.status` to reflect what it did
7. Returns (with or without a requeue)

If Reconcile returns an error, the controller runtime requeues with
**exponential backoff** (starting ~5ms, capping at ~16 minutes). If it returns
success with a `RequeueAfter` duration, it schedules the next reconciliation
after that interval.

**Critical ACM failure mode:** A controller that updates `.status` and triggers
its own watch will reconcile again immediately, creating a hot loop. This is a
common ACM bug -- the config-policy-controller re-evaluates every 10 seconds
because lookup watchers trigger on status-only changes (ACM-25694).

### Informers and Watches

Controllers don't poll the API server. They use **informers** -- client-side
caching mechanisms that maintain a local copy of watched resources.

How an informer works:

1. On startup, the informer does a **List** call to get all existing objects
2. It populates a local **cache** (in-memory indexed store)
3. It opens a **Watch** connection -- a long-lived HTTP stream that receives
   change notifications in real-time
4. Each change event (ADDED, MODIFIED, DELETED) updates the local cache and
   is placed on the **work queue**

The work queue deduplicates entries. If the same object changes 10 times
before the controller processes it, the controller sees only one reconciliation
request. Reconciliation should be level-triggered (based on current state),
not edge-triggered (based on individual changes).

**What "failed to wait for caches to sync" means:** On startup, each informer
must complete its initial List and populate its cache before the controller can
begin processing. If this times out (API server load, large resource counts,
memory pressure), the controller cannot start. Common in ACM when hive-operator
or cluster-permission controllers are under memory pressure.

### Watch Scoping

Controllers can watch resources at different scopes:
- **Cluster-scoped:** All instances across all namespaces
- **Namespace-scoped:** Only within specific namespaces
- **Filtered:** With label or field selectors to reduce event volume

A controller that uses `Owns()` watches all resources with an owner reference
pointing to its primary resource. Convenient but expensive at scale. The
cluster-permission controller OOM (ACM-24032) was caused by `Owns(ManifestWork)`
caching all ManifestWorks in memory.

---

## 2. Custom Resource Definitions (CRDs)

### What CRDs Are

A CRD extends the Kubernetes API with a new resource type. A CRD defines:
- **Group:** API group (e.g., `cluster.open-cluster-management.io`)
- **Versions:** One or more API versions (e.g., `v1`, `v1beta1`, `v1alpha1`)
- **Schema:** OpenAPI v3 validation
- **Scope:** Namespaced or Cluster-scoped
- **Subresources:** Optional `/status` and `/scale`

### Versions and Stored Versions

A CRD can serve multiple API versions simultaneously. The **storage version**
is used when persisting to etcd. `.status.storedVersions` lists all versions
with data in etcd.

If an upgrade removes a version that still has data in etcd, the upgrade
breaks. This is what happened with the MCRA CRD breaking change (ACM-28211):
v1alpha1 was removed without a conversion webhook, blocking ACM upgrades.

### Conversion Webhooks

When a CRD serves multiple versions with different schemas, a conversion
webhook transforms objects between versions. Without one, the API server can
only do trivial conversion. If the webhook is unavailable, ALL reads of
non-storage versions fail.

---

## 3. Pod Lifecycle

### Phases

- **Pending:** Accepted but not scheduled or images not pulled
- **Running:** At least one container running
- **Succeeded:** All containers exited 0 (Jobs/batch)
- **Failed:** At least one container exited non-zero
- **Unknown:** Cannot determine state (node communication lost)

### CrashLoopBackOff Mechanics

When a container crashes repeatedly with `restartPolicy: Always`, kubelet
applies exponential backoff:

```
Attempt 1: restart immediately (0s)
Attempt 2: 10s delay
Attempt 3: 20s delay
Attempt 4: 40s delay
Attempt 5: 80s delay
Attempt 6+: 300s (5 min) cap
```

Status shows `CrashLoopBackOff` when kubelet is in the backoff period.
The container IS NOT running during this time.

**Backoff reset:** If the container runs successfully for 10 minutes, the
backoff counter resets. A container crashing every 9 minutes never exits
CrashLoopBackOff; one crashing every 11 minutes appears stable.

**ACM diagnostic pattern:** When an ACM controller shows CrashLoopBackOff:
1. `oc describe pod` -- Events section for exit codes
2. `oc logs <pod> --previous` -- logs from the crashed container
3. Exit code 137 = OOMKilled
4. Exit code 1 = application error (nil pointer, missing config)

---

## 4. Resource Management

### Requests and Limits

- **requests:** Guaranteed minimum. Scheduler uses this for placement.
- **limits:** Maximum allowed. Enforced at runtime.

CPU limits: CFS throttling (throttled, not killed).
Memory limits: OOM killer. If RSS exceeds limit, kernel kills immediately.
Exit code 137 (128 + SIGKILL=9).

The cluster-permission controller OOM (ACM-24032) was caused by informer
caches growing unbounded from watching all ManifestWorks.

### QoS Classes

- **Guaranteed:** requests = limits for both CPU and memory. Last evicted.
- **Burstable:** requests < limits. Middle priority.
- **BestEffort:** No requests/limits. First evicted.

Most ACM operator pods are Burstable.

---

## 5. Admission Controllers

After authentication and authorization, requests pass through admission:

```
Request -> Authentication -> Authorization (RBAC) -> Mutating Admission ->
Schema Validation -> Validating Admission -> etcd
```

Webhooks can accept/reject (validating) or modify (mutating) requests.
`failurePolicy: Fail` (default) rejects requests if the webhook is
unreachable. `failurePolicy: Ignore` proceeds without the check.

**ACM pattern:** Hive uses webhooks for ClusterDeployment validation. If the
webhook service is down with `failurePolicy: Fail`, all ClusterDeployment
operations are blocked (ACM-26271).

---

## 6. Leader Election

Controllers run with multiple replicas for HA. Only ONE reconciles at a time.
Leader election uses a Lease object as a distributed lock.

During failover: leader dies -> lease expires (typically 15s) -> new leader
acquires lease -> starts reconciling. Gap of at least `leaseDuration` where
no reconciliation occurs.

Most ACM controllers run as single replicas, so leader election primarily
prevents split-brain during rolling updates.

---

## 7. etcd

Stores ALL Kubernetes API objects as key-value pairs. Keys:
`/registry/<api-group>/<resource-type>/<namespace>/<name>`

If etcd's database exceeds its space quota (default 2GB), it enters alarm mode
and rejects ALL writes. Reads still work. Manifests as "etcdserver: mvcc:
database space exceeded" on every create/update/delete.

If etcd is slow (high fsync latency, >10ms), all API operations slow down.
Controllers see "context deadline exceeded". Looks like individual component
failures but is platform-wide.

---

## 8. API Server Request Flow

```
Client -> TLS -> Authentication (certs/tokens/OIDC) -> Authorization (RBAC) ->
  Mutating Admission -> Schema Validation -> Validating Admission -> etcd ->
  Watch notifications to all watchers
```

### RBAC

Four resource types: Role, ClusterRole, RoleBinding, ClusterRoleBinding.
RBAC is additive -- no deny rules. If no rule grants permission, implicitly denied.

ACM's fine-grained RBAC (MCRA) extends Kubernetes RBAC. MCRA operator creates
ClusterPermission resources which become ManifestWorks that deploy Roles and
RoleBindings to spoke clusters. Failure at any point means the user doesn't
get expected permissions.

---

## 9. Finalizers

Strings in `metadata.finalizers` that prevent deletion until removed:

1. User deletes resource -> API server sets `metadata.deletionTimestamp`
2. Resource NOT deleted from etcd yet
3. Controller does cleanup work
4. Controller removes its finalizer
5. When all finalizers removed, API server deletes from etcd

If the responsible controller is down or buggy, the resource gets stuck in
`Terminating` forever. Common in ACM:
- Hive ClusterDeployment finalizers (ACM-26271)
- Submariner ManifestWork finalizers blocking MCH uninstall (ACM-15538)
- MTV integrations adding finalizers to already-deleting ManagedClusters (ACM-29920)

---

## 10. Secrets and Certificate Rotation

Secrets store sensitive data. Type `kubernetes.io/tls` stores certificates.

When a ConfigMap/Secret mounted as a file is updated, kubelet eventually updates
the file (~1 minute). But the application may cache the old value.

**ACM issue pattern:** Certificate rotation in hosted mode doesn't trigger
controller restarts. Controllers continue using cached connections with old
certificates. Affects config-policy-controller, HyperShift addon, observability
addon (~30 bugs).

---

## 11. PersistentVolumeClaims

PVCs request persistent storage. Lifecycle: Pending (waiting for PV) -> Bound.

If a pod references a PVC that's Pending, the pod stays in Pending. Common
with search-postgres -- if the PVC isn't bound, postgres can't start and
search is unavailable.

Observability's Thanos stack requires S3-compatible storage -- the only ACM
feature requiring external storage.

---

## 12. Events

Events record what happened to resources. Generated by kubelet, scheduler,
controllers, webhooks. Default retention: 1 hour.

Key events for ACM diagnosis:

| Event Reason | Meaning | ACM Context |
|---|---|---|
| `FailedScheduling` | No node with enough resources | Controller memory requests too high |
| `BackOff` | CrashLoopBackOff | Controller crash -- check logs --previous |
| `Unhealthy` | Failed probe | console-mce probe timeout (ACM-24965) |
| `OOMKilled` | Exceeded memory limit | cluster-permission at scale (ACM-24032) |
| `FailedMount` | Volume mount failed | PVC not bound, Secret missing |

---

## 13. OLM (Operator Lifecycle Manager)

OLM manages operator lifecycle on OpenShift: installation, upgrades,
dependency resolution, RBAC provisioning.

Key resources:
- **CatalogSource:** Operator catalog image
- **Subscription:** Declares intent to install an operator and track a channel
- **InstallPlan:** Resources to create/update for a new version
- **CSV (ClusterServiceVersion):** Operator manifest

CSV phases: `Succeeded` (healthy), `Installing`, `Pending`, `Failed`, `Replacing`, `Deleting`.

ACM uses two CSVs:
- `advanced-cluster-management.v2.X.Y` in the MCH namespace
- `multicluster-engine.v2.X.Y` in `multicluster-engine`

CRD changes during upgrade can break existing CRs. If a new CRD removes a
version with data in etcd, objects stored in that version become inaccessible
(ACM-28211).
