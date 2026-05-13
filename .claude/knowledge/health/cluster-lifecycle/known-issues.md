# Cluster Lifecycle (CLC) -- Known Issues

Based on 233 CLC bugs from ACM 2.12-2.17.

---

## 1. Detach Destroys Hosted Clusters (ACM-15018)

**Versions:** MCE 2.5-2.8 | **Severity:** Critical | **Fix:** Code change (import-controller/pull/408)

Detaching a hosted cluster deletes the hosting namespace, which contains
the HostedCluster control plane pods. The cluster is destroyed instead
of just being removed from ACM management.

**Root cause:** managedcluster-import-controller deletes the cluster
namespace on detach without checking whether a HostedCluster resource
exists in that namespace. For standard clusters, the namespace only
contains import artifacts. For hosted clusters, the namespace IS the
control plane.

**Signals:** After detach operation, HostedCluster disappears. Control
plane pods deleted. Data plane nodes lose connectivity to control plane.
Check: `oc get hostedcluster -n <ns>` returns NotFound after detach.

**Fix pattern:** Guard namespace deletion with a check for HostedCluster
resources. If a HostedCluster exists, skip namespace deletion and only
remove ACM-specific resources (ManagedCluster, import secrets, addons).

**Scope:** 5 bugs across MCE 2.5-2.8 reported this same pattern.

---

## 2. ClusterDeployment Finalizer Broken (ACM-26271)

**Versions:** ACM 2.16 | **Severity:** Blocker | **Fix:** Code change (hive/pull/2729)

ClusterDeployment finalizer doesn't work when Hive metadata passthrough
is missing. Clusters can't be deprovisioned -- cloud resources are
orphaned.

**Root cause:** Hive webhook validates ClusterDeployment on creation
and stores metadata needed for deprovisioning. When metadata passthrough
was missing (due to a webhook regression), the CD was accepted but the
deprovisioning controller couldn't find the metadata needed to delete
cloud resources.

**Signals:** `oc delete clusterdeployment <name>` hangs. CD stuck in
`Deprovisioning` state. Deprovision pod logs show metadata-related errors.
Check: `oc get clusterdeployment <name> -o jsonpath='{.metadata.finalizers}'`
shows Hive finalizer present but CD can't be removed.

**Workaround:** Manually delete cloud resources, then remove finalizer
from CD: `oc patch cd <name> -p '{"metadata":{"finalizers":null}}' --type merge`

---

## 3. ClusterPermission Controller OOM at Scale (ACM-24032)

**Versions:** ACM 2.15 | **Severity:** Important | **Fix:** Code change (cluster-permission/pull/69)

cluster-permission controller OOM-kills in large environments (1000+
managed clusters) during performance testing.

**Root cause:** Controller used `Owns(ManifestWork)` watch, which cached
ALL ManifestWorks across all managed clusters -- not just the ones
created by cluster-permission. At scale, this consumed gigabytes of
memory. ManifestWorks are created by many controllers (GRC, App, addons),
so the cache grew far beyond what cluster-permission needed.

**Signals:** `oc get pods -n open-cluster-management -l app=cluster-permission`
shows OOMKilled. Pod restart count climbing. Check events:
`oc get events -n open-cluster-management --field-selector reason=OOMKilling`

**Fix pattern:** Removed `Owns` watch on ManifestWork. Controller now
uses label-filtered watches to only cache ManifestWorks it created.
Memory dropped from GBs to MBs.

---

## 4. ClusterPermission Hot-Loop Reconciliation (ACM-25572)

**Versions:** ACM 2.15 | **Severity:** Important | **Fix:** Code change (cluster-permission/pull/77)

cluster-permission controller reconciles continuously even when nothing
changed, causing elevated CPU and API server load.

**Root cause:** Informer resync interval too aggressive. Controller
reconciled on every ManifestWork status update (which happens frequently
as work-agent reports status). The pattern: reconcile -> update
ClusterPermission status -> trigger own watch -> reconcile again.

**Signals:** Frequent reconciliation in controller logs. Elevated CPU
on the controller pod. High API server request rate from the
cluster-permission service account.

**Fix pattern:** Throttled resync interval. Added spec-change detection
to skip reconciliation when only status fields changed. Combined with
ACM-24032 fix to dramatically reduce controller resource usage.

---

## 5. ManagedCluster Remains After HostedCluster Destroy (ACM-20695)

**Versions:** ACM 2.14-2.15 | **Severity:** Critical | **Fix:** Code change (hypershift-addon/pull/525)

After destroying a HostedCluster, the corresponding ManagedCluster
resource is re-created automatically, preventing clean deletion.

**Root cause:** hypershift-addon-operator's auto-import logic watches
for HostedClusters and creates ManagedCluster CRs for any HC that
doesn't have a corresponding MC. When the HC is being destroyed:
1. HC deletion triggers MC deletion
2. MC deleted
3. Auto-import watch sees HC exists without MC
4. Auto-import recreates MC
5. HC finalizer runs, deletes HC
6. Orphaned MC remains

**Signals:** `oc get managedclusters` shows a ManagedCluster for a
destroyed HostedCluster. Cluster shows Available=Unknown (no control
plane to connect to). hypershift-addon-operator logs show auto-import
messages for the deleted HC.

**Fix pattern:** Auto-import logic checks HC deletion timestamp. If
HC has a `deletionTimestamp`, skip auto-import. Additionally, MC
deletion is triggered when HC deletion is detected (before HC
finalizers complete).

---

## 6. Certificate Regeneration in Hosted Mode (8 bugs)

**Versions:** MCE 2.4-2.8 | **Severity:** High | **Fix:** Ongoing across multiple controllers
**JIRAs:** ACM-17667 and related

Multiple controllers fail to detect certificate rotation when running
in hosted mode with mounted kubeconfig secrets.

**Root cause:** Hosted control plane pods mount kubeconfig secrets as
volumes. When certificates rotate, the secret is updated and the volume
mount reflects the new content. However, controllers that read the
kubeconfig into memory at startup (or cache the client) don't detect
the file change. They continue using the old certificate until it
expires, then start getting 401 errors.

**Affected controllers:**
- config-policy-controller (governance addon on hosted cluster)
- hypershift-addon-operator
- observability-addon (metrics-collector)
- Any addon controller deployed to hosted cluster data planes

**Signals:** Controller logs show authentication failures (401) to the
spoke API. Pod running fine but producing continuous auth errors. Pod
restart fixes the issue (picks up new cert).

**Pattern:** This is a systemic issue across all controllers that use
mounted kubeconfigs. Each controller needs to either:
1. Watch the kubeconfig file for changes and reload
2. Use a client builder that auto-refreshes from file
3. Use in-cluster config with CSR-based rotation (which already handles this)

**Workaround:** Restart affected controller pods after certificate
rotation. Can be automated via a CronJob or a controller that watches
for secret changes and triggers pod restarts.

---

## 7. Hive Stuck Provisioning

**Versions:** All | **Severity:** High | **Fix:** Varies by root cause

ClusterDeployment stays in `Provisioning` state without progressing.
Multiple root causes:

### 7a. Install pod never created
- **Cause:** hive-controllers down or overloaded
- **Detection:** No install pods in the cluster namespace.
  `oc get pods -n <cluster-ns> -l hive.openshift.io/install=true`
  returns no results
- **Fix:** Check hive-controllers health in `hive` namespace

### 7b. Install pod fails with cloud errors
- **Cause:** Invalid credentials, quota exceeded, networking issues
- **Detection:** Install pod in Error/Failed state.
  `oc logs -n <cluster-ns> -l hive.openshift.io/install=true`
  shows cloud-specific errors
- **Fix:** Fix credentials/quota/networking, delete failed CD, retry

### 7c. Bootstrap timeout
- **Cause:** Cluster infrastructure provisioned but OCP bootstrap fails
- **Detection:** Install pod log shows "waiting for bootstrap to complete"
  then timeout
- **Fix:** Check bootstrap machine console output via cloud provider

### 7d. Webhook denial prevents cleanup
- **Cause:** CD metadata passthrough broken (ACM-26271)
- **Detection:** CD stuck, deprovision pod can't find required metadata
- **Fix:** Apply Hive fix, or manually clean up

---

## 8. Import Failures

**Versions:** All | **Severity:** High | **Fix:** Varies by root cause

Cluster import fails at various stages. Common patterns:

### 8a. Import controller not running
- **Signals:** ManagedCluster created but no import secret generated
- **Detection:** `oc get pods -n open-cluster-management -l app=managedcluster-import-controller`
  shows CrashLoopBackOff or missing
- **Fix:** Investigate import controller crash (check logs, events)

### 8b. Auto-import secret invalid
- **Signals:** Auto-import for completed CD fails silently
- **Detection:** `oc get secret -n <cluster-ns> auto-import-secret` -- check
  kubeconfig validity
- **Fix:** Regenerate kubeconfig, delete/recreate auto-import-secret

### 8c. Klusterlet can't reach hub
- **Signals:** ManagedCluster stuck in `ManagedClusterConditionAvailable=Unknown`
- **Detection:** Check klusterlet pods on spoke:
  `oc get pods -n open-cluster-management-agent` (on spoke cluster)
- **Fix:** Verify network connectivity from spoke to hub API.
  Check firewall rules, proxy settings.

### 8d. external-managed-kubeconfig missing for HCPs (ACM-22317)
- **Signals:** Pre-existing HostedClusters not importable after ACM install
- **Detection:** No `external-managed-kubeconfig` secret in the HC namespace
- **Fix:** Fixed in later versions to backfill kubeconfig generation for
  pre-existing HCPs

### 8e. Klusterlet overwrites server URL (ACM-21891)
- **Signals:** Import fails for non-OpenShift clusters (EKS, GKE, AKS)
- **Detection:** Bootstrap kubeconfig has empty server URL after klusterlet
  processes it
- **Fix:** Code fix in klusterlet agent for non-OpenShift cluster detection

---

## 9. ClusterPermission RoleBinding Namespace Wrong (ACM-22985)

**Versions:** ACM 2.14-2.15 | **Severity:** Normal | **Fix:** Code change (cluster-permission/pull/68)

ClusterPermission creates RoleBindings in the wrong namespace on the
managed cluster after the managed-serviceaccount addon namespace changed.

**Root cause:** Controller hardcoded the old MSA addon namespace instead
of dynamically resolving it. When MSA addon moved to a different
namespace, RoleBindings were created in a namespace that no longer had
the service account.

**Signals:** ClusterPermission status shows RoleBinding created but RBAC
rules not effective. Service account can't access resources despite
ClusterPermission granting access.

---

## 10. ClusterPool Remains After MCE Uninstall (ACM-27552)

**Versions:** ACM 2.16 | **Severity:** Normal | **Fix:** Code change (backplane-operator/pull/2352)

ClusterPool CR is not cleaned up when MCE is uninstalled, leaving
orphaned pre-provisioned clusters running.

**Root cause:** ClusterPool was not included in the `blockDeletionResources`
list in the backplane-operator. MCE uninstall skipped ClusterPool cleanup.

**Signals:** After MCE uninstall, `oc get clusterpool -A` still returns
results. Orphaned clusters continue running and incurring cloud costs.

**Fix:** Added ClusterPool to `blockDeletionResources` so MCE uninstall
blocks until ClusterPools are cleaned up.

---

## 11. Curator Fails to Upgrade OCP 4.21 (ACM-30314)

**Versions:** ACM 2.17 | **Severity:** Normal | **Fix:** Code change (curator-controller/pull/524)

ClusterCurator upgrade logic incompatible with OCP 4.21 ClusterVersion
API changes.

**Root cause:** OCP 4.21 changed how upgrade channels and versions are
represented in the ClusterVersion resource. Curator's version matching
logic failed on the new format.

**Signals:** ClusterCurator upgrade Job fails immediately with version
parsing errors. Curator pod logs show version comparison failures.

---

## Bug Pattern Distribution

| Category | Count | Top Issues |
|---|---|---|
| Konflux/EC compliance | ~80 | Stale Tekton bundles, EC policy violations (recurring per z-stream) |
| HyperShift import/detach | ~15 | MC re-creation, detach destroying HC, cert rotation |
| Hive provisioning | ~12 | Stuck provisioning, finalizer race, webhook denial |
| ClusterPermission scale | ~6 | OOM, hot-loop, RoleBinding namespace |
| Certificate lifecycle | ~8 | Mounted kubeconfig not triggering restart |
| Curator/upgrade | ~5 | OCP version compatibility, AAP integration |
| Image/build failures | ~12 | Stale images, failed builds |
| ClusterPool | ~3 | Orphaned pools, cleanup |

## Root Cause Themes

1. **Cross-namespace complexity:** CLC operates across 4+ namespaces per
   cluster. Bugs often involve wrong namespace references or missing
   namespace checks (detach, RoleBinding, cleanup).
2. **Watch scope too broad:** Controllers watching all ManifestWorks or
   all resources when they only need a subset. Causes OOM and hot-loops.
3. **Hosted mode certificate lifecycle:** Mounted secrets don't trigger
   pod restarts, requiring each controller to implement its own file
   watching -- most don't.
4. **Auto-import race conditions:** Auto-import logic conflicts with
   deletion logic, causing resources to be recreated during cleanup.
5. **Hive metadata assumptions:** Webhook and finalizer logic assumes
   metadata set at creation time will be available at deprovision time.
   Any gap in the creation-time metadata causes deprovision failures.
