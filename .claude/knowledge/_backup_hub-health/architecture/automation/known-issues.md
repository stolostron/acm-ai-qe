# Automation (ClusterCurator) -- Known Issues

Based on automation-related bugs from ACM 2.12-2.17 and cross-referenced
with z-stream failure analysis data.

---

## 1. AnsibleJob CR Incompatible with AAP 2.5+ Workflow Templates

**Versions:** ACM ≤2.13 with AAP ≥2.5
**Severity:** High (all automation hooks broken)
**Fix:** ACM 2.14+ (AnsibleJob CR updated for new AAP API)

AnsibleJob CR attempts to mount AAP 2.4-style secrets that do not exist
in AAP 2.5+. The pod enters CreateContainerConfigError. The AAP operator
CSV shows Succeeded, and the AAP instance is healthy -- the CRD simply
does not support the new workflow API.

**Signals:**
- `CreateContainerConfigError` on AnsibleJob pods
- `Ansible posthook is not triggered within time limit` in curator Job logs
- AAP operator healthy but automation hooks fail

**Detection:**
```bash
# Check AAP version
oc get csv -A | grep aap
# If AAP >= 2.5 and ACM <= 2.13, this is the cause
```

**Cluster-fixable:** No -- requires ACM upgrade to 2.14+.

---

## 2. ansibletower.ts Proxy Returns Empty Results

**Versions:** ACM 2.15+
**Severity:** Medium (template selection broken, hooks still work if
configured via CR directly)
**Fix:** Code change needed

Console backend proxy intercepts AAP API requests and returns
`{count:0, results:[]}` without contacting the AAP instance. Template
dropdown appears empty even though AAP is healthy and has templates
configured.

**Signals:**
- Template dropdown empty in console automation configuration
- AAP operator CSV phase=Succeeded
- Direct AAP API call returns templates (curl to AAP endpoint works)
- Console backend logs show the proxy handled the request

**Detection:**
```bash
# Verify AAP is healthy
oc get csv -A | grep aap
# Check console backend logs for ansibletower proxy errors
oc logs -n <mch-ns> -l app=console-chart-console-v2 --tail=50 | grep -i tower
```

**Cluster-fixable:** No -- code change needed. Workaround: configure
ClusterCurator CR directly via YAML instead of console UI.

---

## 3. ClusterCurator SSE Events Dropped

**Versions:** ACM 2.15+
**Severity:** Low (cosmetic -- curation still executes, only UI display
is affected)
**Fix:** Code change needed

The console backend's `events.ts` event filter drops ClusterCurator
events. Automation status does not update in the console UI in real-time.
The curation executes correctly; only the UI display is stale until
manual page refresh.

**Signals:**
- Automation shows "In Progress" indefinitely in console UI
- Manual page refresh shows the correct completed/failed status
- ClusterCurator CR conditions show correct status when checked via CLI

**Detection:**
```bash
# Compare UI status with actual CR status
oc get clustercurator -n <cluster-ns> <cluster-name> -o jsonpath='{.status.conditions}'
```

**Cluster-fixable:** No -- code change in events.ts needed.

---

## 4. ClusterCurator Incompatible with OCP 4.21 Upgrade API (ACM-30314)

**Versions:** ACM ≤2.15, spoke cluster OCP ≥4.21
**Severity:** High (upgrades to OCP 4.21+ fail)
**Fix:** ACM 2.16+ (curator updated for new OCP upgrade API)
**JIRA:** ACM-30314

The ClusterCurator upgrade logic uses the pre-4.21 ClusterVersion API
to patch the desired update. OCP 4.21 changed the upgrade API,
causing the curator upgrade Job to fail immediately when attempting
to patch the spoke's ClusterVersion.

**Signals:**
- Curator upgrade Job fails at the ClusterVersion patch step
- ClusterCurator condition shows `Job_failed`
- Curator Job logs show API error or patch rejection
- Spoke is OCP 4.21+ and ACM is ≤2.15

**Detection:**
```bash
# Check spoke OCP version
oc get clusterversion version -o jsonpath='{.status.desired.version}'
# Check ACM version
oc get mch -A -o jsonpath='{.items[0].status.currentVersion}'
# Check curator Job logs
oc logs job/<curator-job-name> -n <cluster-ns> --tail=50
```

**Cluster-fixable:** No -- requires ACM upgrade to 2.16+. Workaround:
trigger spoke upgrade directly via spoke's ClusterVersion CR.

**Cross-ref:** cluster-lifecycle/known-issues.md

---

## 5. Curator Job Timeout on Long-Running Ansible Playbooks

**Versions:** All
**Severity:** Medium
**Fix:** Cluster-fixable (increase timeout)

Default `jobMonitorTimeout` (5 minutes for hooks) may be insufficient
for complex Ansible playbooks. The curator Job marks the curation as
failed when the timeout is exceeded, even though the Ansible playbook
may still be running successfully on AAP.

**Signals:**
- ClusterCurator condition message contains "not triggered within time limit"
- AnsibleJob CR on hub shows the job is still running
- AAP shows the playbook executing successfully

**Detection:**
```bash
# Check current timeout setting
oc get clustercurator -n <cluster-ns> <name> -o jsonpath='{.spec.upgrade.jobMonitorTimeout}'
# Check if AnsibleJob is still running
oc get ansiblejob -n <cluster-ns> --no-headers
```

**Cluster-fixable:** Yes -- increase `jobMonitorTimeout` in the
ClusterCurator spec.

---

## 6. Curator Job Fails with Expired Kubeconfig (Hosted Mode)

**Versions:** ACM 2.14-2.17 (hosted clusters)
**Severity:** High (upgrade operations fail)
**Fix:** Ongoing code changes

In hosted mode, the kubeconfig secret for the managed cluster may
expire if certificate rotation is not detected. The curator Job
retrieves the kubeconfig but authentication to the spoke fails because
the credentials are stale.

**Signals:**
- Curator Job logs show authentication errors connecting to spoke
- Kubeconfig secret exists but contains expired credentials
- Other operations using the same kubeconfig also fail

**Detection:**
```bash
# Check kubeconfig secret age and content
oc get secret -n <cluster-ns> | grep admin-kubeconfig
# Verify credentials are valid
oc --kubeconfig=<extracted-kubeconfig> get nodes
```

**Cluster-fixable:** Partial -- regenerating the kubeconfig secret
resolves the immediate issue, but the underlying rotation detection
problem needs a code fix.

**Cross-ref:** infrastructure/known-issues.md #2 (certificate rotation
not detected in hosted mode)

---

## Summary

| # | Issue | Versions | Severity | Cluster-Fixable |
|---|---|---|---|---|
| 1 | AnsibleJob/AAP 2.5+ incompatibility | ACM ≤2.13 | High | No (upgrade ACM) |
| 2 | ansibletower.ts returns empty | 2.15+ | Medium | No (code change) |
| 3 | SSE events dropped | 2.15+ | Low | No (code change) |
| 4 | OCP 4.21 upgrade API incompatibility | ACM ≤2.15 | High | No (upgrade ACM) |
| 5 | Hook timeout too short | All | Medium | Yes (increase timeout) |
| 6 | Expired kubeconfig in hosted mode | 2.14-2.17 | High | Partial |
