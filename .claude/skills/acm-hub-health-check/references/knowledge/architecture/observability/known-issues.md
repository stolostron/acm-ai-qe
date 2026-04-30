# Observability Subsystem -- Known Issues

Based on 101 Observability bugs from ACM 2.12-2.17.

---

## 1. RCE Vulnerability via Endpoint Operator SA (ACM-29127)

**Versions:** ACM 2.15, 2.16
**Severity:** Major
**Fix:** Code change (obs-operator PR#2342)

The `hub-endpoint-observability-operator-sa` service account had `nodes/proxy`
RBAC permissions, enabling Remote Code Execution on any node in the cluster.
An attacker with access to this SA could execute arbitrary commands via the
kubelet API.

**Root cause:** Overly broad RBAC grant on the endpoint operator service account.
The operator only needs metrics scraping access, not node proxy access.

**Fix:** Removed `nodes/proxy` from RBAC. Changed to direct kubelet access pattern
for metrics collection.

**Signals:** Audit `hub-endpoint-observability-operator-sa` ClusterRoleBinding.
Check for `nodes/proxy` in ClusterRole rules. Run:
`oc get clusterrole -o yaml | grep -A5 "nodes/proxy"`

---

## 2. Grafana Status Variable Broken (ACM-21975)

**Versions:** ACM 2.15, 2.16
**Severity:** Critical
**Fix:** Code change

Grafana dashboard JSON model corruption breaks the `Status` variable in
Virtualization dashboards and other dashboards using variable references.
Variable definitions become malformed, causing empty dropdown selectors
and missing data on dashboards.

**Root cause:** Dashboard JSON model corruption during variable definition
serialization. The grafana-dashboard-loader writes variable definitions
that reference other variables, and the reference chain breaks.

**Signals:** Grafana dashboard shows empty variable dropdowns. Dashboard
renders but panels show "No data". Check Grafana dashboard JSON for
variable definition integrity:
- Dashboard variables show `$__all` instead of actual values
- Variable query returns empty results
- Panel queries using `$Status` return no data

---

## 3. ETCD Metrics Not Collected for Hosted Control Planes (ACM-31063)

**Versions:** ACM 2.16, 2.17
**Severity:** Normal
**Fix:** Code change

The observability addon relabel configuration filters out ETCD metrics for
Hosted Control Plane (HCP) clusters. ETCD runs differently in HCP mode
(in the management cluster namespace rather than on spoke nodes), and the
relabel config doesn't account for this topology.

**Root cause:** Addon relabel config was written for traditional cluster topology
where ETCD runs on control plane nodes. HCP ETCD pods run in the management
cluster with different labels and namespace.

**Signals:** ETCD-related Grafana panels show no data for HCP clusters.
`etcd_*` metrics missing from HCP cluster namespace in thanos-query.
Other metrics from the same HCP cluster are present.

---

## 4. S3 Storage Misconfiguration Crashes thanos-store

**Versions:** All
**Severity:** High (total historical query outage)
**Fix:** Cluster-fixable

Missing, incorrect, or expired S3 credentials in the `thanos-object-storage`
secret cause thanos-store, thanos-compactor, and thanos-receive (on upload)
to crash or enter error loops. This is the most common deployment issue.

**Signals:** `oc get pods -n open-cluster-management-observability` -- thanos-store
and thanos-compactor pods in CrashLoopBackOff. Logs show S3 connection errors:
`msg="bucket operation failed"`, `err="Access Denied"`, `err="NoSuchBucket"`.

**Fix:** Verify and fix the `thanos-object-storage` secret:
```bash
oc get secret thanos-object-storage -n open-cluster-management-observability -o yaml
```
Ensure bucket exists, endpoint is correct (without protocol), and credentials
are valid and not expired.

---

## 5. Metrics Collection Endpoint Scraping Failures (19 bugs)

**Versions:** ACM 2.15, 2.16, 2.17
**Severity:** Varies (Normal to Major)
**Fix:** Varies per bug

Broad category of issues where the metrics-collector on spokes fails to scrape
or transmit metrics. Sub-patterns:

1. **Relabel config issues:** Metrics filtered out by incorrect relabel rules
   (e.g., ETCD metrics for HCPs, custom metrics not matching allowlist)
2. **Endpoint discovery failures:** Prometheus endpoint not discoverable on
   non-standard cluster configurations
3. **Remote-write failures:** TLS errors, certificate expiry, network partitions
   between spoke and hub
4. **Resource exhaustion:** Collector OOM on clusters with many resources

**Signals:** No metrics from specific spokes. `oc logs` on metrics-collector
pod shows scrape errors or remote-write failures. Grafana shows gaps for
specific clusters.

---

## 6. Alerting Rule Regressions (18 bugs)

**Versions:** ACM 2.15, 2.16, 2.17
**Severity:** Varies (Normal to Critical)
**Fix:** Code changes

Alert rule definitions regress across versions. Common sub-patterns:

1. **Alert rule YAML errors:** Invalid PromQL in recording or alerting rules
2. **Thanos query path changes:** Backend query API changes break rule evaluation
3. **Alertmanager integration failures:** Route configuration changes, webhook
   endpoints becoming unreachable
4. **Duplicate alerts:** Same alert firing from multiple rule evaluations

**Signals:** Expected alerts not firing. `ACMThanosRule*` meta-alerts. Check
thanos-rule logs for evaluation errors. Verify alertmanager routes:
`oc get secret alertmanager-config -n open-cluster-management-observability -o yaml`

---

## 7. Certificate and TLS Chain Issues (15 bugs)

**Versions:** ACM 2.15, 2.16
**Severity:** Varies (Normal to Major)
**Fix:** Code changes + cluster-fixable workarounds

TLS certificate management issues in the observability stack. Sub-patterns:

1. **Certificate expiry:** Auto-generated certs not rotated before expiry
2. **CA chain incomplete:** Missing intermediate CA certificates
3. **Service account token rotation:** Addon SA tokens expire, breaking
   remote-write authentication

**Signals:** Remote-write errors with TLS handshake failures. `x509: certificate
has expired` in metrics-collector logs. thanos-receive rejecting connections.

**Workaround:** Restart the endpoint-observability-operator to trigger cert
regeneration. For SA token issues, restart the addon.

---

## 8. Addon Lifecycle Issues During Install/Upgrade (10 bugs)

**Versions:** ACM 2.15, 2.16
**Severity:** Varies (Normal to Major)
**Fix:** Code changes

The observability addon has timing issues during installation and upgrade:

1. **Deployment ordering:** Addon deployed before thanos-receive is ready,
   causing initial remote-write failures (self-recovers)
2. **Upgrade race conditions:** Old and new addon versions running simultaneously
   during rolling upgrade
3. **ManifestWork conflicts:** Multiple operators trying to update the same
   ManifestWork for the addon
4. **Configuration reconciler drift:** Addon configuration drifts from MCO CR
   spec after manual edits

**Signals:** Addon pods in CrashLoopBackOff after install/upgrade. Multiple
addon versions visible. `oc get managedclusteraddon observability-controller -A`
shows degraded status.

---

## 9. Grafana Dashboard Rendering Issues (10 bugs)

**Versions:** ACM 2.15, 2.16, 2.17
**Severity:** Varies (Normal to Critical)
**Fix:** Code changes

Dashboard-specific rendering problems beyond the Status variable issue:

1. **Panel query failures:** PromQL queries reference metrics that changed names
   across Prometheus/Thanos versions
2. **Dashboard loader failures:** grafana-dashboard-loader sidecar fails to
   load dashboard JSON, resulting in missing dashboards
3. **Variable cascade failures:** Dashboard variables that depend on other
   variables fail to resolve
4. **Time range handling:** Some panels don't respect the global time range
   selector

**Signals:** Individual panels show "No data" or error icons. Missing dashboards
in Grafana UI. Dashboard loader pod logs show JSON parse errors.

---

## 10. Observability Namespace Resource Conflicts

**Versions:** ACM 2.15+
**Severity:** Medium
**Fix:** Cluster-fixable

Resources left behind in `open-cluster-management-observability` namespace
after failed uninstall or partial upgrade. Prevents clean reinstallation.

**Signals:** MCO CR creation fails with resource conflict errors. Orphaned
PVCs, secrets, or configmaps in the observability namespace.

**Fix:** Manual cleanup:
```bash
oc delete mco observability
oc delete ns open-cluster-management-observability --wait=false
# Wait for termination, then force-remove finalizers if stuck
```

---

## Bug Pattern Distribution

| Category | Count | Top Issues |
|---|---|---|
| Metrics collection | 19 | Endpoint scraping, relabel configs, HCP metrics |
| Alerting | 18 | Rule regressions, alertmanager integration |
| Certificate/security | 15 | TLS chain, SA permissions, RCE exposure |
| Grafana dashboards | 10 | Variable references, panel queries, loader failures |
| Addon lifecycle | 10 | Deployment timing, upgrade races, config drift |
| Thanos stack | ~15 | Compactor issues, query path changes, receive errors |
| Object storage | ~8 | S3 config, credentials, bucket operations |
| Other | ~6 | RBAC, resource conflicts, namespace cleanup |

## Root Cause Themes

1. **Overly broad RBAC grants:** Service account permissions exceeding what the
   component actually needs (nodes/proxy RCE being the most severe)
2. **Relabel config assumptions:** Metrics filtering rules written for standard
   cluster topology, failing for non-standard (HCP, SNO, etc.)
3. **Dashboard JSON fragility:** Grafana dashboard variable references break when
   upstream Grafana version changes or metric names change
4. **Addon deployment timing:** Race conditions during install/upgrade when
   components start in different order than expected
5. **Thanos version migration:** Query path and API changes across Thanos versions
   break metric queries and rule evaluation

## Diagnostic Signals Summary

| Symptom | First Check |
|---|---|
| No metrics from spokes | `oc get managedclusteraddon observability-controller -A` |
| Dashboard variables empty | Grafana dashboard JSON variable definitions |
| thanos-store CrashLoopBackOff | `thanos-object-storage` secret validity |
| Alerts not firing | thanos-rule logs, alertmanager configuration |
| RCE exposure | endpoint-observability-operator-sa ClusterRole |
| HCP metrics missing | Addon relabel config, HCP namespace labels |
| Grafana panels "No data" | thanos-query health, datasource configuration |
