# Infrastructure -- Known Issues

Based on infrastructure-related bugs from ACM 2.12-2.17 and common OCP
platform issues affecting ACM operation.

---

## 1. Node Pressure Evicts ACM Controllers

**Versions:** All | **Severity:** High | **Fix:** Cluster-fixable

Node MemoryPressure or DiskPressure on control plane nodes causes kubelet to
evict ACM hub controllers (console-api, search-api, grc-policy-propagator,
addon-manager). BestEffort QoS pods evicted first, then Burstable.

**Root cause:** ACM controllers running on control plane nodes without
sufficient resource guarantees. Under memory pressure, kubelet evicts pods
by QoS class.

**Signals:** Multiple ACM pods in Evicted state. `oc get pods -A | grep Evicted`
shows ACM namespace pods. Node conditions show MemoryPressure=True or
DiskPressure=True.

**Fix:** Ensure control plane nodes have sufficient resources. Set appropriate
resource requests/limits on ACM deployments. Consider dedicated infra nodes
for ACM workloads.

---

## 2. Certificate Rotation Not Detected in Hosted Mode

**Versions:** 2.14-2.17 | **Severity:** High | **Fix:** Code changes (multiple)

Controllers using mounted kubeconfig secrets for hosted control planes don't
detect when the secret is rotated. Controllers continue using expired
credentials until pod restart.

**Affected components:**
- config-policy-controller (hosted mode)
- HyperShift addon
- observability addon
- cluster-proxy

**Root cause:** Controllers read kubeconfig from mounted secret volume at
startup. Kubernetes updates the volume mount, but controllers don't watch
for file changes or re-read the credential.

**Signals:** Controllers start returning 401 Unauthorized after credential
rotation. Pod logs show authentication failures to spoke APIs. Pod restart
fixes the issue temporarily until next rotation.

**Workaround:** Restart affected pods after certificate rotation. Consider
setting up a sidecar or inotify-based solution to detect file changes.

---

## 3. etcd Performance Degradation at Scale

**Versions:** All | **Severity:** High | **Fix:** Cluster-fixable

Large ACM deployments (100+ managed clusters) generate thousands of CRs
(ManifestWork, replicated policies, ClusterPermissions), causing etcd
performance degradation.

**Signals:**
- API request latency increases (> 500ms for mutating requests)
- `etcd_disk_wal_fsync_duration_seconds` p99 > 50ms
- `etcd_server_leader_changes_seen_total` increasing
- etcd defragmentation needed (database size > 4GB)

**Fix:**
- Ensure etcd disks are SSD/NVMe with < 10ms fsync latency
- Run etcd defragmentation: `oc rsh -n openshift-etcd etcd-<node> etcdctl defrag`
- Monitor etcd metrics via Prometheus
- Consider reducing ManifestWork count (fewer addons, smaller scope)

---

## 4. Storage Class Missing or Misconfigured

**Versions:** All | **Severity:** Medium | **Fix:** Cluster-fixable

ACM components requiring persistent storage fail when StorageClass is missing,
default StorageClass not set, or CSI driver is unhealthy.

**Affected components:**
- search-postgres (optional PVC, defaults to emptyDir)
- thanos-store (required PVC for observability)
- thanos-receive (recommended PVC)

**Signals:** Pods stuck in Pending. Events show "no persistent volumes available"
or "storageclass not found." `oc get sc` shows no default StorageClass.

**Fix:** Ensure a default StorageClass exists. Verify CSI driver health.
For cloud providers, confirm IAM permissions for dynamic provisioning.

---

## 5. CSR Approval Failures Block Node Certificates

**Versions:** All (OCP-level) | **Severity:** High | **Fix:** Cluster-fixable

Certificate Signing Requests (CSRs) for node certificate renewal not
auto-approved. Nodes become NotReady when serving certificates expire.

**Root cause:** machine-approver controller down, or CSR doesn't match
expected node identity. Common after cluster hibernation/wake cycles.

**Signals:** `oc get csr` shows Pending CSRs. Node conditions show
NotReady. kubelet logs show TLS handshake failures.

**Fix:** Approve pending CSRs manually:
```bash
oc get csr -o name | xargs oc adm certificate approve
```
For recurring issues, check machine-approver pod health.

---

## 6. Ingress/Router Issues Break Console Access

**Versions:** All | **Severity:** High | **Fix:** Cluster-fixable

When the OCP Ingress operator or router pods are unhealthy, ACM console
becomes inaccessible via Route. All browser-based ACM operations stop.

**Signals:** Console URL returns 503 or connection refused. `oc get co ingress`
shows Degraded. Router pods not Running in `openshift-ingress` namespace.

**Fix:** Check and restart ingress operator and router pods. Verify
DNS resolution for wildcard domain.

---

## 7. MCH Uninstall Hangs (Various Causes)

**Versions:** 2.13-2.16 | **Severity:** Critical | **Fix:** Various

MCH deletion can hang for multiple infrastructure reasons:
- Submariner ManifestWork deletion race (ACM-15538)
- search-pause annotation preventing cleanup
- MCE CSV deletion ordering (ACM-15851)
- ClusterPool resources blocking MCE deletion (ACM-27552)

**Signals:** MCH stuck in Terminating. `oc get mch -o yaml` shows finalizers
present. MCH operator logs show blocked resources.

**Workarounds by cause:**
- Submariner: Remove ManifestWork finalizers manually
- search-pause: `oc annotate mch multiclusterhub -n <ns> search-pause-`
- MCE CSV: Delete MCE CSV manually
- ClusterPool: Delete ClusterPool CRs before MCE uninstall

---

## 8. klusterlet Disconnection

**Versions:** All | **Severity:** High | **Fix:** Investigation needed

klusterlet on spoke loses connectivity to hub. ALL spoke-dependent features
fail for that cluster: search results stale, policy compliance unknown,
app status missing, VM operations fail.

**Common causes:**
- Network connectivity loss between spoke and hub
- Hub API server overloaded (etcd issues)
- klusterlet pod OOMKilled or evicted
- Lease renewal failure

**Signals:** `oc get managedclusters` shows AVAILABLE=False. ManagedCluster
conditions show `ManagedClusterConditionAvailable=Unknown` with lease expiry
message.

**Fix:** Check spoke-to-hub network. Verify klusterlet pods on spoke.
Check hub API server health. Look for lease renewal failures in klusterlet logs.

---

## Bug Pattern Distribution

| Category | Estimated Count | Top Issues |
|---|---|---|
| Certificate lifecycle | ~30 | Hosted mode rotation, CSR approval, expiry |
| Node health | ~15 | Memory pressure, disk pressure, evictions |
| etcd health | ~10 | Performance degradation, leader changes |
| Storage | ~8 | PVC pending, CSI driver, capacity |
| Uninstall hangs | ~10 | Finalizer races, annotation blockers |
| klusterlet connectivity | ~15 | Lease expiry, network, OOM |

## Root Cause Themes

1. **Scale amplification:** ACM's CRD footprint (ManifestWorks, replicated policies)
   amplifies base platform issues like etcd latency
2. **Certificate blind spots:** Mounted secret rotation not detected by controllers
3. **Resource guarantee gaps:** ACM controllers without explicit resource requests
   are vulnerable to eviction
4. **Cleanup ordering:** MCH uninstallation has multiple potential deadlocks from
   circular dependencies between operators and ManifestWorks
5. **Single point of failure:** klusterlet disconnect immediately impacts all spoke features

## Summary

| # | Issue | Cluster-Fixable? | Severity |
|---|-------|:---:|---|
| 1 | Node pressure evicts controllers | Yes | High |
| 2 | Cert rotation not detected (hosted) | Restart pods | High |
| 3 | etcd degradation at scale | Yes (disk, defrag) | High |
| 4 | StorageClass missing | Yes | Medium |
| 5 | CSR approval failures | Yes (manual approve) | High |
| 6 | Ingress/router broken | Yes | High |
| 7 | MCH uninstall hangs | Manual workarounds | Critical |
| 8 | klusterlet disconnection | Investigation needed | High |
