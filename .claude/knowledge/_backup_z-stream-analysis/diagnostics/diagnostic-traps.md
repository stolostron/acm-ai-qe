# Diagnostic Traps for Failure Classification

Patterns where the obvious diagnosis is WRONG. The cluster diagnostic agent
(Stage 1.5) MUST check each of these before concluding its investigation.
Each trap describes what you see, what you might conclude, what's actually
happening, and how it affects failure classification.

Origin: Adapted from acm-hub-health diagnostic traps with z-stream
classification context added.

---

## Trap 1: Stale MCH/MCE CR Status (Operator Not Running)

**What you see:** `oc get mch` shows `phase: Running`. Everything looks healthy.

**What you might conclude:** Hub is healthy, move on.

**What's actually happening:** The MCH operator reconciles the MCH CR and
updates `.status.phase`. If the operator pod is scaled to 0 or crashed, the
status field FREEZES at its last-known value. The CR says "Running" because
nobody is updating it to say otherwise.

**How to detect:**
```bash
# ALWAYS check operator pod health before trusting MCH status
oc get deploy multiclusterhub-operator -n <mch-ns> -o jsonpath='{.spec.replicas}/{.status.availableReplicas}'
# If 0/0 or replicas mismatch, the MCH status is STALE
```

**Classification impact:** If this trap is missed, the diagnostic reports
"healthy" and Stage 2 classifies test failures as PRODUCT_BUG or
AUTOMATION_BUG when they should be INFRASTRUCTURE. The operator being down
means no component reconciliation — any component that crashes stays down.

**Rule:** Never trust MCH/MCE `.status.phase` without first confirming the
operator pod is Running and Ready.

**Variant — Leader Election Stuck (Trap 1b):** Both operator replicas
show Running/Ready, health probes pass, but reconciliation has stopped.
The Kubernetes leader election Lease expired (often due to etcd latency
at Layer 2), and neither replica re-acquired it. The agent checks
operator replicas (2/2 — healthy), pod status (Running/Ready — healthy),
MCH status (Running — appears healthy) and concludes everything is fine.
Meanwhile, no reconciliation is happening and managed resources drift.

**How to detect:**
```bash
# Check leader election Lease renewTime
oc get lease -n <mch-ns> | grep multiclusterhub
oc get lease <lease-name> -n <mch-ns> -o jsonpath='{.spec.renewTime}'
# If renewTime is not within the last few minutes, leader election is stuck
```

**Applies to:** MCH operator (2 replicas), MCE operator (2 replicas),
grc-policy-propagator (2 replicas), cluster-manager (3 replicas).

---

## Trap 2: Console Pod Healthy but Feature Tabs Missing

**What you see:** Console pod is Running/Ready (liveness/readiness probes pass).
But tests report missing UI elements — entire sections gone from the UI.

**What you might conclude:** Console is fine, tests have stale selectors
(AUTOMATION_BUG).

**What's actually happening:** ACM console uses OCP dynamic plugins:
- `acm-console-dynamic-plugin` (ACM features: governance, applications)
- `mce-console-dynamic-plugin` (MCE features: clusters, infrastructure)

These are registered via ConsolePlugin CRDs. The console pod serves the UI
shell, but feature content comes from plugin pods (`console-mce` in
`multicluster-engine` namespace). If `console-mce` is in CrashLoopBackOff,
the MCE tabs silently disappear.

Additionally, console-api is a shared backend for 7 feature areas. A single
backend service failure cascades to multiple seemingly unrelated UI pages.

**How to detect:**
```bash
oc get pods -n <mch-ns> | grep console
oc get pods -n multicluster-engine | grep console
oc get consoleplugins
oc get pods -n multicluster-engine -l app=console-mce
oc logs -n multicluster-engine -l app=console-mce --tail=20
```

**Classification impact:** Without this trap, Stage 2 sees "element not found"
errors and classifies as AUTOMATION_BUG (selector changed). The actual cause
is INFRASTRUCTURE — the console plugin pod is down, so the elements were
never rendered.

**Rule:** Console pod healthy does NOT mean console is fully functional.
Always check: (1) console-mce pod, (2) ConsolePlugin CRDs, (3) backend
services (search-api, console-api).

---

## Trap 3: Search Returns Empty but All Pods Are Green

**What you see:** All search pods Running. Search-collector addon is
Available on spokes. But search tests fail with "expected results > 0".

**What you might conclude:** Search is healthy, this is a product bug or
test assertion issue (PRODUCT_BUG or AUTOMATION_BUG).

**What's actually happening:** search-postgres uses `emptyDir` (not a PVC).
If the postgres pod restarts for ANY reason (OOMKill, node drain, eviction,
rolling update), all indexed data is lost. The schema itself may be dropped.

When this happens:
- search-api is Running (stateless, doesn't know data is gone)
- search-collector is Available (collecting on spokes, unaware hub lost data)
- search-indexer is Running (waiting for data to arrive)
- search-postgres is Running (but with empty tables)

Re-collection takes 10-30 minutes depending on fleet size.

**How to detect:**
```bash
# Check postgres pod age vs other search pods
oc get pods -n <mch-ns> -l app=search-postgres \
  -o jsonpath='{.items[0].metadata.creationTimestamp}'
# If much younger than other search pods -> recent restart = data loss

# Check postgres data directly (if exec is available)
oc exec deploy/search-postgres -n <mch-ns> -- \
  psql -U searchuser -d search -c "SELECT count(*) FROM search.resources" 2>&1
```

**Classification impact:** This is the most common misclassification trap.
Without it, search tests with "0 results" get classified as PRODUCT_BUG
(search returns wrong data) when it's actually INFRASTRUCTURE (data lost
due to pod restart, will self-recover).

**Rule:** Search "all green" + "empty results" = always check postgres pod
age and data count before classifying.

**Operational note — Recreate strategy + emptyDir:** search-postgres uses
Deployment strategy `Recreate` (not `RollingUpdate`). Combined with
`emptyDir`, every deployment update terminates the old pod BEFORE starting
the new one, guaranteeing data loss and a downtime window. Any MCH
operator reconciliation that touches the search-postgres deployment spec
(image update during upgrade, resource limit change, env var modification)
causes the pod to be killed before the new one starts. Post-upgrade empty
search results for 10-30 minutes is expected behavior (similar to Trap 5
for GRC), not a finding.

---

## Trap 4: Observability Dashboards Empty — Looks Like Operator, Actually S3

**What you see:** Observability tests fail. MCO CR may show conditions.

**What you might conclude:** Observability operator is broken (PRODUCT_BUG).

**What's actually happening:** The most common cause of observability failure
is S3/object storage misconfiguration, NOT operator issues. The operator is
healthy — it deployed everything. But thanos-store, thanos-compactor, and
thanos-receive can't access the object storage.

**How to detect:**
```bash
oc get pods -n open-cluster-management-observability | grep thanos
# If thanos-store or thanos-compactor are CrashLoopBackOff:
oc logs -n open-cluster-management-observability <thanos-store-pod> --tail=20
# Look for: "bucket operation failed", "Access Denied", "NoSuchBucket"
```

**Classification impact:** Without this trap, observability test failures get
classified as PRODUCT_BUG (operator not working). The actual cause is
INFRASTRUCTURE (S3 credentials rotated or bucket misconfigured).

**Rule:** Observability failures -> check thanos pods and S3 secret before
investigating the operator.

---

## Trap 5: GRC Policies Non-Compliant After Upgrade (Normal Behavior)

**What you see:** After ACM upgrade, governance tests show policies as
non-compliant or Unknown.

**What you might conclude:** Upgrade broke GRC (PRODUCT_BUG).

**What's actually happening:** Normal post-upgrade behavior:
1. Upgrade restarts governance-policy-framework addon on every spoke
2. While restarting, compliance status resets to Unknown
3. After restart, controllers re-evaluate all policies
4. Re-evaluation takes 5-15 minutes

**How to detect:**
```bash
oc get managedclusteraddons -A | grep governance
# If "Progressing" or "Unknown" -> still settling, wait
oc logs -n <mch-ns> -l app=grc-policy-propagator --tail=30
# Normal: "Evaluating policy..." messages
# Problem: Error messages, panic, OOM
```

**Classification impact:** Without this trap, post-upgrade GRC test failures
are classified as PRODUCT_BUG or INFRASTRUCTURE. They should be NO_BUG
(expected transient behavior, tests ran during the settling window).

**Rule:** Post-upgrade GRC non-compliance for 5-15 minutes is expected.
Only classify as a real issue if it persists beyond 20 minutes.

---

## Trap 6: ManagedCluster NotReady — Don't Assume Klusterlet Crashed

**What you see:** `oc get managedclusters` shows AVAILABLE=False or Unknown.

**What you might conclude:** Klusterlet crashed (INFRASTRUCTURE on spoke).

**What's actually happening:** AVAILABLE=False has multiple causes:

| Cause | Frequency | Klusterlet crashed? |
|-------|-----------|:---:|
| Network/firewall between spoke and hub | Common | No |
| Proxy configuration wrong on spoke | Common | No |
| Hub API server overloaded | Occasional | No |
| Lease renewal failure (transient) | Common | No |
| Klusterlet pod OOMKilled | Rare | Yes |

**How to detect:**
```bash
oc get lease -n <cluster-namespace> --sort-by=.spec.renewTime
oc get managedcluster <name> -o jsonpath='{.status.conditions[*].message}'
oc get managedclusteraddons -n <cluster-namespace>
# ALL addons unavailable = network issue, not individual addon failures
```

**Classification impact:** Without this trap, managed cluster connectivity
issues get classified as INFRASTRUCTURE (correct) but with wrong root cause
(klusterlet crash vs network issue). The root cause matters for
whether it's a test environment issue vs a product issue.

**Rule:** Check lease and conditions before concluding klusterlet crash.

---

## Trap 7: ALL Spoke Addons Unavailable — Single Pod Failure

**What you see:** ALL addons (governance, search-collector, observability)
show Unavailable across multiple or all managed clusters.

**What you might conclude:** Widespread spoke failure. Each addon needs
individual investigation.

**What's actually happening:** Addon deployment is managed by `addon-manager`
(hub MCE namespace). If addon-manager is down, NO addons get deployed or
updated on ANY spoke.

**How to detect:**
```bash
oc get pods -n multicluster-engine | grep addon-manager
# If CrashLoopBackOff or not Running -> this is your root cause
```

**Classification impact:** Without this trap, tests across multiple feature
areas get classified independently (search INFRASTRUCTURE, governance
INFRASTRUCTURE, etc.) when there's ONE root cause. The diagnostic should
identify "addon-manager down" as the single infrastructure issue affecting
all addon-dependent tests.

**Rule:** Mass addon failure across multiple clusters -> check addon-manager
before anything else.

---

## Trap 8: Console Multiple Pages Failing — Check Search First

**What you see:** Multiple console pages fail in tests:
- Search page shows errors
- Fleet Virt VM list is empty
- Fleet Virt tree view is empty
- RBAC resource views show nothing
- Some policy status views are stale

**What you might conclude:** Console has a widespread bug (PRODUCT_BUG).
Or multiple backend services failed simultaneously.

**What's actually happening:** All these features share search-api as a
dependency. Console proxies search queries for multiple features through
its Resource Proxy backend. When search-api is down or slow, all dependent
features fail.

| Feature | Dependency on search-api |
|---------|------------------------|
| Search UI | Direct (GraphQL) |
| Fleet Virt VM list | Via multicluster-sdk |
| Fleet Virt tree view | Via multicluster-sdk |
| RBAC resource views | Via aggregate API |
| Policy status (some) | Via resource proxy |

**How to detect:**
```bash
oc get pods -n <mch-ns> | grep search-api
oc logs -n <mch-ns> -l app=search-api --tail=20
```

**Classification impact:** Without this trap, tests in Console, Virtualization,
RBAC, and GRC get classified independently — some as AUTOMATION_BUG (selector
not found because page didn't render), some as PRODUCT_BUG (wrong data).
They should ALL be INFRASTRUCTURE with a single root cause: search-api down.

**Rule:** 3+ console features broken simultaneously -> check search-api
before investigating individual features.

---

## Quick Reference: Trap Index

| Trap | Symptom | Check First | Wrong Classification → Correct |
|------|---------|-------------|-------------------------------|
| 1 | MCH says Running but things break | Operator pod replicas | PRODUCT_BUG → INFRASTRUCTURE |
| 1b | Operator pods Running but nothing reconciling | Leader election Lease renewTime | Healthy → INFRASTRUCTURE |
| 2 | Console pod healthy, tabs missing | console-mce + ConsolePlugin CRDs | AUTOMATION_BUG → INFRASTRUCTURE |
| 3 | Search all green, empty results | Postgres pod age + data count | PRODUCT_BUG → INFRASTRUCTURE |
| 4 | Observability dashboards empty | Thanos pods + S3 secret | PRODUCT_BUG → INFRASTRUCTURE |
| 5 | GRC non-compliant after upgrade | Addon pod age (wait 15 min) | PRODUCT_BUG → NO_BUG |
| 6 | ManagedCluster NotReady | Lease + conditions | Wrong root cause |
| 7 | ALL addons Unavailable everywhere | addon-manager pod | Multiple issues → single root cause |
| 8 | Multiple console pages broken | search-api pod | Multiple PRODUCT_BUG → single INFRASTRUCTURE |
| 9 | ResourceQuota blocking pod recreation | ResourceQuota in ACM namespace | Hidden INFRASTRUCTURE |
| 10 | Cert rotation silent failure | TLS secret ages + CSR status | Hidden INFRASTRUCTURE |
| 11 | NetworkPolicy making pods non-functional | NetworkPolicy in ACM namespace | PRODUCT_BUG → INFRASTRUCTURE |
| 12 | Degraded cluster + selector error | Per-test console_search.found | INFRASTRUCTURE → AUTOMATION_BUG |
| 13 | Backend data wrong despite healthy pods | subsystem_health + data assertions | INFRASTRUCTURE → PRODUCT_BUG |
| 14 | Missing prerequisite that should exist | Jenkins params + MCH components | NO_BUG → INFRASTRUCTURE |

---

## Trap 9: ResourceQuota Blocking Pod Recreation

**What you see:** Pods are Running but some deployments have fewer replicas
than expected. No error events visible. Pods that crash don't restart.

**What you might conclude:** The operator is healthy but scaled down intentionally.

**What's actually happening:** A ResourceQuota in the ACM namespace silently
prevents pod creation. ACM does NOT create ResourceQuotas — any found is a
test artifact or external constraint.

**How to detect:**
- `oc get resourcequota -n $MCH_NS` — if ANY exists, check its limits
- Compare pod counts against `healthy-baseline.yaml`
- Check if the quota's CPU/memory limits are below actual usage

**Rule:** ResourceQuota in ACM namespaces is always suspicious. Check
before accepting "healthy but under-replicated" as normal.

---

## Trap 10: Certificate Rotation Silent Failure

**What you see:** All pods Running, no restarts, but connections between
services fail intermittently. TLS handshake errors in logs.

**What you might conclude:** Network issue or PRODUCT_BUG in service
communication.

**What's actually happening:** A TLS certificate expired or rotated
incorrectly. Pods continue running but can't establish TLS connections.
This is invisible to basic pod health checks.

**How to detect:**
- Check `oc get csr` for pending CSRs
- Check TLS secret ages against `certificate-inventory.yaml`
- Look for `x509: certificate has expired` in pod logs

**Rule:** If services can't communicate but pods are healthy, check
certificates before investigating code.

**Shared TLS secret pattern:** Some ACM services share TLS secrets
across components. When multiple services show TLS errors simultaneously,
check whether they share a common TLS secret — one corrupted secret
explains all the failures:
```bash
# Find which deployments mount the same secret
oc get deploy -n <acm-ns> -o json | jq -r '.items[] | .metadata.name as $d | .spec.template.spec.volumes[]? | select(.secret) | "\($d) -> \(.secret.secretName)"' | sort -t'>' -k2
```
If multiple deployments reference the same TLS secret and that secret is
corrupted or expired, the root cause is ONE secret, not multiple
independent certificate failures.

---

## Trap 11: NetworkPolicy Making Pods Non-Functional

**What you see:** All pods Running with 0 restarts. But features don't
work — search returns empty, governance policies don't propagate, etc.

**What you might conclude:** PRODUCT_BUG — the code must be broken since
all infrastructure looks healthy.

**What's actually happening:** A NetworkPolicy in the ACM namespace blocks
traffic between pods. ACM does NOT create NetworkPolicies — any found
is a test artifact or external security constraint. Pods appear healthy
because they're running, but they can't communicate.

**How to detect:**
- `oc get networkpolicy -n $MCH_NS` — if ANY exists, check its rules
- Check if the policy blocks ingress to critical pods (search-postgres,
  console-api, grc-policy-propagator)
- This MUST be checked BEFORE pod health (Layer 3 before Layer 9)

**Rule:** A NetworkPolicy can make pods appear healthy while being
completely non-functional. Always check Layer 3 before concluding
"all green" from pod health checks.

---

## Counter-Traps: Protecting Against FALSE INFRASTRUCTURE

Traps 1-11 protect against wrongly classifying as PRODUCT_BUG or
AUTOMATION_BUG when the real cause is INFRASTRUCTURE. Traps 12-13
protect in the OPPOSITE direction — preventing the pipeline from
over-classifying as INFRASTRUCTURE when per-test evidence points
elsewhere.

---

## Trap 12: Degraded Cluster but Selector Doesn't Exist (False INFRASTRUCTURE)

**What you see:** Oracle or diagnostic reports "search-collector degraded
on 2/5 clusters" or "search-postgres recently restarted." Multiple tests
in the Search feature area fail.

**What you might conclude:** All Search test failures are INFRASTRUCTURE
because the cluster is degraded.

**What's actually happening:** Some tests fail because of the degraded
infrastructure (timeouts, empty results). But OTHER tests in the same
feature area fail because of stale selectors — the test code references
CSS classes or data-testid values that were removed from the product
months ago. The degraded cluster is a coincidence, not the cause.

**How to detect:**
- Check `console_search.found` for each test. If `found=false`, the
  selector doesn't exist in the product source code at ALL. No amount
  of healthy infrastructure will make it work.
- Check `failure_mode_category`. If it's `element_missing` and the
  element never existed in the current product version, it's AUTOMATION_BUG.
- Check `recent_selector_changes`. If the selector was removed in a
  recent product commit, it might be PRODUCT_BUG (intentional change
  without test update) — but it's still NOT INFRASTRUCTURE.

**Classification impact:** Without this trap, ALL tests in a degraded
feature area get swept into INFRASTRUCTURE. The pipeline should classify
each test independently based on its specific error, using infrastructure
data as context — not as a blanket override.

**Rule:** A degraded cluster does NOT explain a missing selector. Always
check `console_search.found` before accepting an INFRASTRUCTURE
classification from the oracle or diagnostic.

---

## Trap 13: Backend Returns Wrong Data Despite All Pods Healthy (False INFRASTRUCTURE)

**What you see:** Tests fail with "expected 5 items, got 3" or "expected
hub name 'my-hub', got 'other-hub'." Backend probes detect anomalies.
Oracle shows some components as degraded.

**What you might conclude:** INFRASTRUCTURE — the backend components
are broken.

**What's actually happening:** The console backend code has a data
transformation bug. The Kubernetes API returns correct data, but the
console's backend proxy (Node.js) corrupts it during transformation.
All pods are healthy — the code is running correctly, it just produces
wrong output.

**How to detect:**
- Check `cluster-diagnosis.json` → `subsystem_health` for the feature area.
  If subsystem is healthy but test shows wrong data values, the issue is
  in the console code, not the cluster.
- Check `assertion_analysis` — if `has_data_assertion=true` and values
  don't match, investigate whether the backend API returns correct data
  via targeted `oc exec + curl` during Stage 2.
- If Kubernetes API returns correct values but the console UI shows
  different values, that's data corruption in the proxy layer.

**Classification impact:** Without this trap, data assertion failures
in a degraded cluster get classified as INFRASTRUCTURE ("the cluster
returned wrong data"). The real cause is PRODUCT_BUG — the console's
data transformation has a bug.

**Rule:** When the cluster returns correct data but the console shows
wrong data, it's PRODUCT_BUG regardless of cluster health.

---

## Trap 14: Disabled Prerequisite That Should Be Enabled (False NO_BUG)

**What you see:** Tests for a feature area fail with blank pages or
"element not found." The feature's operator/addon is not installed.
PR-4 classifies as NO_BUG ("prerequisite not met, feature disabled").

**What you might conclude:** NO_BUG — the feature is intentionally
disabled, tests should not have run.

**What's actually happening:** The operator/addon SHOULD be installed
for this pipeline run but is missing due to an environment setup failure.
The Jenkins pipeline parameters or the test suite configuration indicate
this feature should be tested, but the prerequisite wasn't provisioned.

**How to detect:**
- Check Jenkins parameters for feature flags (e.g., `INSTALL_AAP=true`,
  `ENABLE_OBSERVABILITY=true`). If the parameter says "install" but the
  operator is absent, the prerequisite failure is INFRASTRUCTURE.
- Check `cluster_landscape.mch_enabled_components`. If the MCH spec
  enables a component but it's not running, that's INFRASTRUCTURE.
- Check if other tests in the same pipeline successfully used the feature
  earlier (the operator was present but crashed mid-run).

**Classification impact:** Without this trap, missing prerequisites get
classified as NO_BUG ("not our problem") when the environment team should
be notified that their setup failed. This is INFRASTRUCTURE — the test
environment was not correctly provisioned.

**Rule:** Before classifying NO_BUG for a missing prerequisite, verify
the prerequisite was not supposed to be present for this pipeline run.
