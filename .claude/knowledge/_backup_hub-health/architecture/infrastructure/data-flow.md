# Infrastructure -- Data Flow

## Flow 1: Certificate Rotation

```
service-ca-operator              Serving Cert Secrets           Pods
────────────────────             ────────────────────           ────
Generates signing CA       →     Creates TLS secrets      →    Mounted as volumes
(openshift-service-ca)           with serving-cert annotation  Pods use for TLS
                                       │
                            Auto-rotation before expiry
                            (service-ca recreates secret)
                                       │
                            Pod detects volume change     →    Pod restarts or
                            (kubelet projected volume)         reloads cert
```

### Step-by-step

1. **service-ca-operator** runs in `openshift-service-ca` namespace.
   Generates a self-signed CA and watches for Services annotated with
   `service.beta.openshift.io/serving-cert-secret-name`.
2. **Secret creation** -- For each annotated Service, creates a TLS
   secret containing a serving certificate signed by the cluster CA.
3. **Secret mounting** -- Deployments mount TLS secrets as volumes.
   Pod containers use the cert/key for TLS termination.
4. **Auto-rotation** -- service-ca-operator monitors certificate
   expiry and recreates the secret before expiration.
5. **Pod restart** -- When the secret content changes, kubelet
   updates the projected volume. Some pods detect the change and
   reload; others require a restart.

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| service-ca-operator down | No new certs created, no rotation | New services get no cert; existing certs expire | `oc get deploy -n openshift-service-ca` |
| Secret corrupted | TLS handshake failures | Pods log TLS errors, clients get connection refused | `oc get secret <name> -n <ns> -o jsonpath='{.data.tls\.crt}' \| base64 -d \| openssl x509 -text` |
| Secret manually modified | service-ca won't overwrite existing secrets | Cert expires without rotation | Check if secret has `service.beta.openshift.io/` annotations intact |
| Pod doesn't reload | Pod uses stale cert after rotation | Intermittent TLS errors (old cert expired) | Compare cert expiry with pod start time |
| Hosted mode | Kubeconfig-based certs not managed by service-ca | Auth failures to spoke cluster | Check kubeconfig secret age and cert validity |

### ACM-specific certificates

Key TLS secrets in ACM namespaces (see `certificate-inventory.yaml`
for the full list):
- `search-api-certs`, `search-indexer-certs`, `search-postgres-certs` --
  Search internal TLS
- `console-chart-console-certs`, `console-mce-console-certs` -- Console
  serving certs
- `propagator-webhook-server-cert` -- GRC webhook serving cert
- `multiclusterhub-operator-webhook` -- MCH webhook cert
- `multicluster-engine-operator-webhook` -- MCE webhook cert

---

## Flow 2: etcd Health and Performance

```
etcd cluster (3 members)
  │
  ├── Leader election (Raft consensus)
  │     └── Heartbeat interval: 100ms default
  │
  ├── WAL (Write-Ahead Log)
  │     └── fsync to disk on every write
  │     └── Slow disk = slow writes = slow API
  │
  ├── Compaction
  │     └── Periodic removal of old revisions
  │     └── Prevents unbounded DB growth
  │
  ├── Defragmentation
  │     └── Reclaims space from compacted revisions
  │     └── Must be triggered manually or by operator
  │
  └── API server connection
        └── All K8s API requests go through etcd
        └── etcd latency = API latency
```

### Step-by-step

1. **Writes** -- API server sends writes to etcd leader. Leader
   replicates to followers via Raft. Write acknowledged when majority
   confirms.
2. **WAL fsync** -- Every write fsyncs to WAL on disk. Disk I/O is
   the critical bottleneck. Slow disk = slow etcd = slow everything.
3. **Compaction** -- etcd auto-compacts old revisions to prevent DB
   growth. If compaction falls behind, DB size grows and performance
   degrades.
4. **Defragmentation** -- After compaction, space is fragmented.
   Defrag reclaims it. Large ACM deployments (10,000+ CRs) can cause
   significant fragmentation.

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| Leader election | Network partition between masters | API timeouts, "etcdserver: leader changed" | `oc get pods -n openshift-etcd` |
| WAL fsync | Slow disk (cloud IOPS limit) | `took too long` warnings, API latency >500ms | `oc logs -n openshift-etcd <pod> --tail=100 \| grep "took too long"` |
| DB size | Exceeded quota (default 8GB) | "mvcc: database space exceeded" | `oc exec -n openshift-etcd <pod> -- etcdctl endpoint status --write-out=table` |
| Compaction | Falls behind at scale | Growing DB size, slow list operations | Monitor DB size over time |
| Quorum loss | 2+ members down | Complete API unavailability | `oc get pods -n openshift-etcd --no-headers` |

### ACM impact

ACM creates thousands of CRs (ManifestWorks, ManagedClusterAddons,
policy status, etc.). At scale (100+ managed clusters), ACM can
contribute 10,000+ objects to etcd. This amplifies all etcd performance
issues: slow watches, slow list operations, increased compaction load.

---

## Flow 3: Node Lifecycle and Pressure Response

```
kubelet (per node)
  │
  ├── Condition reporting
  │     └── Ready, MemoryPressure, DiskPressure, PIDPressure
  │     └── Reported to API server every nodeStatusUpdateFrequency
  │
  ├── Pressure response (when thresholds exceeded)
  │     └── Soft eviction: grace period before evicting pods
  │     └── Hard eviction: immediate pod termination
  │     └── Priority: BestEffort → Burstable → Guaranteed
  │
  └── Pod scheduling
        └── Scheduler avoids nodes with pressure conditions
        └── Pods pending if all nodes pressured
```

### Failure modes

| Condition | Trigger | Impact on ACM | Detection |
|-----------|---------|---------------|-----------|
| MemoryPressure | Available memory below threshold | ACM controller pods evicted (typically BestEffort/Burstable) | `oc get nodes -o jsonpath='{range .items[*]}{.metadata.name} {.status.conditions[?(@.type=="MemoryPressure")].status}{"\n"}{end}'` |
| DiskPressure | Node disk usage above threshold | Pod eviction, image garbage collection | Same pattern with `DiskPressure` |
| PIDPressure | Too many processes | New pods can't start | Same pattern with `PIDPressure` |
| NotReady | kubelet unresponsive | All pods on node marked Unknown, rescheduled after timeout | `oc get nodes` |

### ACM-specific impact

ACM controllers typically run on control plane nodes (via tolerations
or node selectors). If control plane nodes experience pressure:
- MCH/MCE operators may be evicted → all ACM reconciliation stops
- Search-postgres eviction → data loss (emptyDir) requiring full
  re-collection from all spokes
- Webhook server eviction → resource creation blocked cluster-wide

---

## Flow 4: Storage Provisioning

```
StorageClass
  │
  ▼
PVC created ──► CSI driver ──► Cloud API ──► PV provisioned
                                                  │
                                           PVC bound to PV
                                                  │
                                           Pod mounts volume
```

### Step-by-step

1. **StorageClass** defines provisioner (CSI driver), parameters,
   reclaim policy, volume binding mode
2. **PVC created** by ACM component (e.g., search-postgres, Thanos)
3. **CSI driver** provisions volume via cloud provider API
4. **PV created** and bound to PVC
5. **Pod mounts** the volume

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| StorageClass | Missing or misconfigured | PVC stuck in Pending | `oc get storageclass` |
| CSI driver | Driver pod not running | PVC creation times out | `oc get pods -n openshift-cluster-csi-drivers` |
| Cloud API | IAM permissions, quota exhaustion | PV not created | Check CSI driver logs |
| PVC binding | Volume binding mode WaitForFirstConsumer | PVC Pending until pod scheduled | Check volumeBindingMode in StorageClass |
| Capacity | PVC full | Pod crashes (write failures) | `oc get pvc -n <ns>` -- check capacity vs usage |

### ACM storage dependencies

- **search-postgres:** Uses emptyDir by default (no PVC, data lost on
  restart). Some deployments use PVC for persistence.
- **Thanos (observability):** Requires PVC for long-term metric storage
  via thanos-store. Also requires S3-compatible object storage.
- **Hive:** Creates PVCs for cluster provisioning jobs.
