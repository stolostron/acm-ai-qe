# Infrastructure -- Architecture

## What Infrastructure Covers

The infrastructure foundation layer provides the base platform health upon
which all ACM and OCP features depend. This includes: node health and pressure
conditions, etcd cluster health, certificate lifecycle, storage subsystem,
OCP platform operators, cluster version management, resource quotas,
NetworkPolicies, and webhook infrastructure.

Infrastructure failures cascade -- if this layer is unhealthy, every ACM
feature built on top is affected.

---

## OCP Foundation

| Component | What It Does | Impact If Unhealthy |
|-----------|-------------|---------------------|
| etcd | Cluster state store | ALL operations fail |
| kube-apiserver | API request processing | ALL operations fail |
| OCP ClusterOperators (34) | Platform services | Specific features degrade |
| Ingress | Route/service exposure | Console inaccessible |
| service-ca | TLS certificate management | TLS failures across services |

---

## Node Management

### Node Health Model

OCP nodes report health through conditions:

| Condition | Healthy Value | Failure Meaning |
|---|---|---|
| `Ready` | `True` | kubelet healthy, can accept pods |
| `MemoryPressure` | `False` | Sufficient memory available |
| `DiskPressure` | `False` | Sufficient disk space |
| `PIDPressure` | `False` | Sufficient process IDs |
| `NetworkUnavailable` | `False` | Network correctly configured |

### Node Roles

| Role | Purpose | Impact If Unhealthy |
|---|---|---|
| `master` / `control-plane` | API server, scheduler, controller-manager, etcd | Cluster API unavailable, scheduling stops |
| `worker` | Runs workload pods | Workloads rescheduled (if capacity allows) |
| `infra` | Infrastructure workloads (router, registry, monitoring) | Ingress/monitoring disrupted |

### Node Pressure Responses

When nodes enter pressure conditions:
1. **MemoryPressure:** kubelet evicts pods by QoS class (BestEffort first).
   OOM kills possible.
2. **DiskPressure:** kubelet garbage-collects images, evicts pods.
   Pods may fail to start.
3. **PIDPressure:** kubelet rejects new pods
4. **NotReady:** scheduler stops placing new pods, existing pods rescheduled after
   `pod-eviction-timeout` (default 5 minutes). Node can't run workloads,
   pods get evicted.
5. **CPU throttled:** Pods run but extremely slowly

For ACM hub clusters, node pressure on control plane nodes can cascade to:
- console-api, search-api, grc-policy-propagator evictions
- etcd performance degradation
- addon-manager unable to process ManifestWork

### Failure Classification Context

- Multiple nodes NotReady = INFRASTRUCTURE (broad impact)
- Single node pressure = INFRASTRUCTURE (specific pods affected)
- All nodes healthy but pods failing = look at pod-level issues

---

## etcd

### Architecture

etcd is the key-value store backing the Kubernetes API. On OCP:
- Runs as static pods on control plane nodes
- Quorum-based: requires majority of members (2 of 3, 3 of 5)
- Stores all cluster state: resources, secrets, configmaps, CRDs

### Health Indicators

| Metric/Check | Healthy | Unhealthy Signal |
|---|---|---|
| `etcd_server_has_leader` | 1 | 0 = no leader, cluster partitioned |
| `etcd_server_leader_changes_seen_total` | Low/stable | Rapid increases = leader instability |
| `etcd_disk_wal_fsync_duration_seconds` | < 10ms p99 | > 100ms = disk I/O bottleneck |
| `etcd_network_peer_round_trip_time_seconds` | < 50ms | > 200ms = network latency |
| Member count | Matches expected | Fewer = member down/removed |

### etcd Failure Modes

- **Single member down:** Quorum maintained (2 of 3), reads/writes continue
  with degraded performance
- **Quorum lost:** API server becomes read-only or unavailable
- **Disk I/O slow:** Write latency increases, leader elections frequent,
  API server request timeouts
- **Defragmentation needed:** Database size grows, compaction needed

### ACM Impact of etcd Issues

etcd degradation affects ACM disproportionately because ACM creates many CRs:
- ManifestWork per addon per cluster
- Replicated policies per target cluster
- ClusterPermission per RBAC user per cluster
- Search index metadata on hub

Large ACM deployments can have 10,000+ CRs, making etcd performance critical.

---

## Certificates

### Certificate Lifecycle in OCP

OCP manages several certificate categories:

| Category | Rotation | Impact of Expiry |
|---|---|---|
| API server serving cert | Auto (annually) | API server TLS failures |
| kubelet serving certs | Auto (CSR-based) | Node communication breaks |
| etcd peer/client certs | Auto (annually) | etcd cluster communication fails |
| Ingress/router certs | Manual or auto (cert-manager) | HTTPS ingress broken |
| Service serving certs | Auto (service-ca-operator) | Inter-service TLS fails |

### TLS Certificate Infrastructure

OCP service-CA operator manages internal TLS certificates:
- Generates certs for services with `service.beta.openshift.io/serving-cert-secret-name` annotation
- Rotates on ~2 year schedule
- Does NOT auto-repair manual corruption
- MCH operator does NOT reconcile cert content

If a cert is manually corrupted:
- The affected service fails TLS handshakes
- Pod may CrashLoopBackOff or run with TLS errors
- Persists until next scheduled rotation or manual fix

### Certificate Rotation Failures

Common failure patterns:
1. **CSR not approved:** Node certificate renewal stuck, node becomes NotReady
2. **Certificate expired before rotation:** Typically happens when cluster
   has been shut down for extended periods
3. **Custom CA conflicts:** User-provided CA certificates conflicting with
   auto-generated ones
4. **Hosted mode rotation:** Mounted kubeconfig secrets don't trigger
   controller restarts on rotation (recurring theme across ACM components)

### ACM-Specific Certificate Issues

ACM components with certificate dependencies:
- **HyperShift addon:** kubeconfig secrets for hosted clusters
- **config-policy-controller:** Mounted credentials in hosted mode
- **observability addon:** TLS for metrics collection
- **cluster-proxy:** TLS termination for proxied connections

Certificate rotation in hosted mode is a recurring bug pattern (~30 bugs).
Controllers don't detect when mounted kubeconfig secrets are updated.

---

## Storage

### Storage Classes and Provisioners

OCP storage depends on:
- **StorageClass:** Defines provisioner and parameters
- **PersistentVolumeClaim (PVC):** Request for storage
- **PersistentVolume (PV):** Actual storage allocation
- **CSI drivers:** Container Storage Interface plugins

### ACM Storage Dependencies

| Component | Storage Need | Impact If Missing |
|---|---|---|
| search-postgres | PVC (recommended) or emptyDir | Search data lost on restart with emptyDir |
| thanos-store | PVC (required, S3-compatible) | Observability metrics lost |
| thanos-receive | PVC (recommended) | Metrics ingestion buffer lost |
| etcd | Local disk (must be fast) | Cluster API degradation |
| Hive | PVC for cluster install logs | Install logs lost |

### Storage Failure Modes

- **PVC pending:** StorageClass not available, provisioner down
- **PV not bound:** Insufficient capacity, zone mismatch
- **CSI driver crash:** All PVC operations fail for that provisioner
- **Disk full:** Pod evictions, etcd degradation, log loss

---

## Resource Quotas

ResourceQuotas limit namespace resource consumption. If a quota is set on
the ocm namespace with limits below current usage:
- Existing pods continue running
- Any pod that crashes can't restart (quota exceeded)
- Creates slow-motion cascading failure as pods naturally restart

This is a realistic production scenario (cluster admin applies quotas
without exempting system namespaces).

---

## NetworkPolicies

NetworkPolicies control pod-to-pod communication. A policy that blocks
ingress to a critical pod (like search-postgres) causes:
- Both pods show Running (healthy individually)
- Communication fails with connection timeout
- Very hard to diagnose (no error messages, no pod crashes)

---

## Webhook Infrastructure

Validating webhooks intercept API requests. Issues:
- Webhook service down: ALL requests to that resource type fail with 500
- CA bundle expired: TLS validation fails, webhook unreachable
- failurePolicy=Fail: requests blocked (safe but disruptive)
- failurePolicy=Ignore: requests pass without validation (unsafe)

---

## OCP Platform Health

### Cluster Operators

OCP platform health is tracked via ClusterOperator resources:

```bash
oc get clusteroperators
```

Key operators for ACM:
| Operator | Impact If Degraded |
|---|---|
| `kube-apiserver` | All API operations fail |
| `etcd` | Data store unavailable |
| `authentication` | Login/OAuth broken, console inaccessible |
| `console` | OCP console unavailable (ACM plugin host) |
| `ingress` | Routes unreachable, console/API access via routes broken |
| `network` | Pod networking broken, inter-service communication fails |
| `storage` | PVC operations fail, stateful workloads impacted |
| `machine-config` | Node configuration drift, updates blocked |

### Cluster Version Management

OCP version governs API compatibility for ACM:
- ACM version matrix defines supported OCP versions
- OCP upgrades can break Submariner (OVN changes), CAPI providers, CSI
- ClusterVersion CR tracks current and target version
- Upgrade channels: stable, fast, candidate, eus

```bash
oc get clusterversion version -o jsonpath='{.status.desired.version}'
```

---

## Infrastructure Dependencies (for ACM)

| Dependency | Why | Detection |
|---|---|---|
| Healthy control plane nodes | API server, etcd, controllers | `oc get nodes` |
| etcd quorum | All API operations | `oc get pods -n openshift-etcd` |
| Valid certificates | TLS communication | `oc get csr`, check expiry dates |
| Working storage | PVCs for stateful components | `oc get pvc -A` |
| Functioning network | Pod-to-pod, service-to-service | `oc get co network` |
| DNS resolution | Service discovery | `oc get co dns` |
| Ingress routes | External access to console | `oc get co ingress` |
| OAuth/authentication | User login, API auth | `oc get co authentication` |

## Cascade Impact

Infrastructure failures cascade to all ACM subsystems:

```
Node pressure -> Pod evictions -> ACM controllers evicted -> feature outage
etcd slow -> API latency -> ManifestWork creation slow -> addon deployment delays
Cert expired -> TLS failures -> cross-component communication broken
Storage full -> PVC failures -> search-postgres/thanos-store down
Network broken -> klusterlet disconnected -> ALL spoke features fail
```
