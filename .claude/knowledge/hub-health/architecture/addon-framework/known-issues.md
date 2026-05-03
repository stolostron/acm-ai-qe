# Addon Framework -- Known Issues

Based on addon-framework-related bugs from ACM 2.12-2.17, cross-referenced
with cluster diagnostic data and z-stream failure analysis.

---

## 1. addon-manager OOMKilled at Scale

**Versions:** ACM 2.14+
**Severity:** Critical (all addons affected)
**Fix:** Cluster-fixable (increase memory limits)

addon-manager-controller memory spikes during reconciliation on large
fleets (200+ managed clusters). Each cluster's ManifestWork generation
loads configuration and templates into memory. OOMKilled addon-manager
stops all addon operations across all clusters.

**Signals:**
- addon-manager pod restart count increasing
- Pod events show `OOMKilled` or exit code 137
- Multiple ManagedClusterAddons stuck in `Progressing` simultaneously
- No new addon deployments or upgrades proceeding

**Detection:**
```bash
oc get pods -n open-cluster-management-hub -l app=clustermanager-addon-manager-controller
# Check for restarts and OOMKilled
oc describe pod -n open-cluster-management-hub -l app=clustermanager-addon-manager-controller | grep -A3 "Last State"
```

**Cluster-fixable:** Yes -- increase memory limits on the addon-manager
deployment. Typical production clusters need 512Mi-1Gi for 200+ clusters.

---

## 2. ManifestWork Rejected Due to Resource Conflicts

**Versions:** All
**Severity:** Medium (single addon on single cluster)
**Fix:** Cluster-fixable (resolve conflicts on spoke)

When the spoke cluster already has user-created resources in the addon's
target namespace with the same name as ManifestWork-managed resources,
the work-agent reports Apply errors. The ManifestWork status shows the
conflict, and the ManagedClusterAddon shows `ManifestApplied=False`.

**Signals:**
- ManagedClusterAddon condition `ManifestApplied=False`
- ManifestWork status shows `Apply` error with conflict message
- Other addons on the same cluster work fine

**Detection:**
```bash
# Check ManifestWork status
oc get manifestwork addon-<addon-name>-deploy-0 -n <cluster> -o jsonpath='{.status.conditions}'
# Look for resource conflict messages
oc get manifestwork addon-<addon-name>-deploy-0 -n <cluster> -o yaml | grep -A5 "status:"
```

**Cluster-fixable:** Yes -- remove or rename conflicting resources on
the spoke cluster.

---

## 3. Pre-Delete Task Crash Blocks Addon Removal (ACM-22679)

**Versions:** ACM 2.13-2.16
**Severity:** High (addon stuck, blocks MCH uninstall)
**Fix:** Code change needed + cluster workaround
**JIRA:** ACM-22679

config-policy-controller pre-delete task crashes with a nil pointer
dereference during uninstall when the cluster is in a specific state.
The ManagedClusterAddon gets stuck in Terminating because the finalizer
can't complete. This can block MCH uninstall if the uninstall process
tries to remove all addons.

**Signals:**
- ManagedClusterAddon stuck in `Terminating` state
- `oc get managedclusteraddon -n <cluster> config-policy-controller` shows
  age growing but resource not deleted
- Pre-delete Job logs show nil pointer panic
- MCH uninstall hangs waiting for addon cleanup

**Detection:**
```bash
# Check for stuck addons
oc get managedclusteraddons -A | grep -v "Available"
# Check finalizers
oc get managedclusteraddon -n <cluster> <addon> -o jsonpath='{.metadata.finalizers}'
# Check pre-delete Job
oc get jobs -n <cluster> | grep pre-delete
```

**Cluster-fixable:** Workaround -- manually remove the finalizer from
the stuck ManagedClusterAddon: `oc patch managedclusteraddon -n <cluster>
<addon> --type=merge -p '{"metadata":{"finalizers":null}}'`. Permanent
fix requires code change in config-policy-controller.

---

## 4. Addon Stuck in Progressing After Upgrade

**Versions:** All
**Severity:** Medium (addon deployment delayed)
**Fix:** Cluster-fixable (resolve spoke resource issue)

After ACM upgrade, addon-manager regenerates ManifestWork with new
image references. If the spoke cluster has insufficient resources (CPU,
memory, or node capacity), the new addon pods can't schedule. The
ManagedClusterAddon shows `Progressing=True` indefinitely while the
old pods are terminated but new pods are Pending.

**Signals:**
- ManagedClusterAddon condition `Progressing=True` for extended period
  (beyond the 5-10 minute normal settling window)
- ManifestWork shows `Applied=True` but addon pod is Pending
- Spoke cluster has resource pressure (check node capacity)

**Detection:**
```bash
# Check addon status
oc get managedclusteraddon -n <cluster> <addon> -o yaml
# Check if this is post-upgrade settling (normal) or stuck
# Normal settling: < 10 minutes after upgrade
# Stuck: > 15 minutes, or spoke resource issues
```

**Cluster-fixable:** Yes -- free up resources on spoke cluster, or
increase resource quotas.

**Cross-ref:** infrastructure/post-upgrade-patterns.md #2 (addon
re-registration delay)

---

## 5. Addon Health False Positive (Lease Renewed but Pod CrashLooping)

**Versions:** All
**Severity:** Medium (misleading health status)
**Fix:** Known limitation of lease-based health

With lease-based health checking, the addon's Lease object can be
renewed by a pod that starts, renews the Lease, then crashes. If the
crash-restart cycle is fast enough that the Lease is renewed within the
threshold, ManagedClusterAddon shows `Available=True` even though the
addon is functionally non-operational (CrashLoopBackOff).

**Signals:**
- ManagedClusterAddon shows `Available=True`
- Addon pod on spoke has high restart count (CrashLoopBackOff)
- Addon functionality not working (e.g., search-collector not sending
  data despite being "Available")

**Detection:**
```bash
# Compare hub status with actual spoke pod status
oc get managedclusteraddon -n <cluster> <addon> -o jsonpath='{.status.conditions[?(@.type=="Available")].status}'
# Then check actual pod on spoke
# oc get pods -n open-cluster-management-agent-addon -l <addon-label>
```

**Cluster-fixable:** Investigate why the addon pod is crashing. The
false positive resolves once the underlying crash is fixed.

---

## 6. ClusterManagementAddon Missing After MCE Upgrade

**Versions:** ACM 2.14-2.15
**Severity:** High (new clusters don't get addon)
**Fix:** Code change in 2.16+

During MCE upgrade, some ClusterManagementAddon registrations are
deleted and recreated. A race condition can cause the recreation to
fail silently, leaving the CMA missing. Existing ManagedClusterAddons
and ManifestWorks continue to function, but new clusters won't get
the addon deployed.

**Signals:**
- New managed clusters don't have the addon deployed
- Existing clusters still have the addon running
- `oc get clustermanagementaddons` shows fewer entries than expected
  (compare against `addon-catalog.yaml` for expected count)

**Detection:**
```bash
# List all registered CMAs
oc get clustermanagementaddons --no-headers | wc -l
# Compare with expected count (17 on ACM 2.16)
# Check for specific missing addons
oc get clustermanagementaddon <addon-name>
```

**Cluster-fixable:** Workaround -- restart the operator that owns the
missing CMA. The operator reconciliation re-creates the CMA.

---

## Summary

| # | Issue | Versions | Severity | Cluster-Fixable |
|---|---|---|---|---|
| 1 | addon-manager OOMKilled at scale | 2.14+ | Critical | Yes (increase memory) |
| 2 | ManifestWork resource conflicts | All | Medium | Yes (resolve conflicts) |
| 3 | Pre-delete crash blocks removal | 2.13-2.16 | High | Workaround (remove finalizer) |
| 4 | Addon stuck Progressing after upgrade | All | Medium | Yes (free spoke resources) |
| 5 | Lease-based health false positive | All | Medium | Investigate crash cause |
| 6 | CMA missing after MCE upgrade | 2.14-2.15 | High | Workaround (restart operator) |
