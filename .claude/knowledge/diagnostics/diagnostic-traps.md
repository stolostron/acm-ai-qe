# Common Diagnostic Traps

Patterns where the obvious diagnosis is WRONG. Read this before concluding
any investigation. Each trap describes what you see, what you might conclude,
and what's actually happening.

These traps serve two purposes:
- **Hub health diagnosis** (acm-hub-health): avoiding misdiagnosis of
  cluster state -- the cluster looks healthy but isn't, or looks broken
  but the issue is elsewhere
- **Failure classification** (z-stream-analysis): avoiding misclassification
  of test failures -- the test failure looks like one category but the
  root cause belongs to another

These traps are verified against the RHACM Knowledge Graph, ACM source code,
and real cluster behavior.

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
means no component reconciliation -- any component that crashes stays down.

**Rule:** Never trust MCH/MCE `.status.phase` without first confirming the
operator pod is Running and Ready. Same applies to MCE status -- check the
`multicluster-engine` operator pod.

**Variant -- Leader Election Stuck (Trap 1b):** Both operator replicas
show Running/Ready, health probes pass, but reconciliation has stopped.
The Kubernetes leader election Lease expired (often due to etcd latency
at Layer 2), and neither replica re-acquired it. The agent checks
operator replicas (2/2 -- healthy), pod status (Running/Ready -- healthy),
MCH status (Running -- appears healthy) and concludes everything is fine.
Meanwhile, no reconciliation is happening and managed resources drift.

**How to detect:**
```bash
# Check leader election Lease renewTime
oc get lease -n <mch-ns> | grep multiclusterhub
oc get lease <lease-name> -n <mch-ns> -o jsonpath='{.spec.renewTime}'
# If renewTime is not within the last few minutes, leader election is stuck

# Check operator logs for reconciliation activity
oc logs -n <ns> -l <operator-label> --tail=30 --timestamps
# Healthy: "Reconciling <resource>" messages at regular intervals
# Stuck: only health check / probe activity, no reconcile messages

# Common root cause: etcd latency (Layer 2)
time oc get namespaces > /dev/null
# If >2 seconds, etcd latency may be causing lease expiry
```

**Applies to:** MCH operator (2 replicas), MCE operator (2 replicas),
grc-policy-propagator (2 replicas), cluster-manager (3 replicas),
cluster-curator-controller (2 replicas), any controller with
`--leader-elect`.

---

## Trap 2: Console Pod Healthy but Feature Tabs Missing

**What you see:** Console pod is Running/Ready (liveness/readiness probes pass).
But users report entire sections missing from the UI (e.g., Clusters tab,
Infrastructure tab gone). Tests report missing UI elements.

**What you might conclude:** Console is fine, user is confused. Or: tests
have stale selectors (AUTOMATION_BUG).

**What's actually happening:** ACM console uses two OCP dynamic plugins:
- `acm-console-dynamic-plugin` (ACM features: governance, applications, etc.)
- `mce-console-dynamic-plugin` (MCE features: clusters, infrastructure, bare metal)

These are registered via ConsolePlugin CRDs. The console pod serves the UI
shell, but feature content comes from plugin pods (`console-mce` in the
`multicluster-engine` namespace). If `console-mce` is in CrashLoopBackOff
(known-issues: probe timeouts under load, connection pooling exhaustion),
the MCE tabs silently disappear.

Additionally, console-api is a shared backend for 7 feature areas (GRC
Resources, Application Resources, Observability Dashboards, Cluster
Resources, Search Interface, Fleet Virtualization, console-api). A single
backend service failure cascades to multiple seemingly unrelated UI pages.

**How to detect:**
```bash
# Check BOTH console pods (ACM namespace AND MCE namespace)
oc get pods -n <mch-ns> | grep console
oc get pods -n multicluster-engine | grep console

# Check ConsolePlugin registrations
oc get consoleplugins

# Check console-mce specifically (most common failure)
oc get pods -n multicluster-engine -l app=console-mce
oc logs -n multicluster-engine -l app=console-mce --tail=20
```

**Classification impact:** Without this trap, Stage 2 sees "element not found"
errors and classifies as AUTOMATION_BUG (selector changed). The actual cause
is INFRASTRUCTURE -- the console plugin pod is down, so the elements were
never rendered.

**Rule:** Console pod healthy does NOT mean console is fully functional.
Always check: (1) console-mce pod, (2) ConsolePlugin CRDs, (3) backend
services (search-api, console-api).

**Version note:** In ACM 2.16+, console-api is integrated into the console
chart. The separate console-api deployment may not exist. Check what's
actually deployed rather than assuming specific pod names.

---

## Trap 3: Search Returns Empty but All Pods Are Green

**What you see:** `oc get pods | grep search` shows all search pods Running.
Search-collector addon is Available on spokes. But search UI returns 0 results
or tests fail with "expected results > 0".

**What you might conclude:** Search is healthy, maybe a UI bug or test
assertion issue (PRODUCT_BUG or AUTOMATION_BUG).

**What's actually happening:** search-postgres uses `emptyDir` (not a PVC).
If the postgres pod restarts for ANY reason (OOMKill, node drain, eviction,
rolling update), all indexed data is lost. The schema itself may be dropped.

When this happens:
- search-api is Running (stateless API, doesn't know data is gone)
- search-collector is Available (collecting on spokes, doesn't know hub lost data)
- search-indexer is Running (waiting for data to arrive)
- search-postgres is Running (but with empty tables)

Re-collection from all spokes takes 10-30 minutes depending on fleet size.

**How to detect:**
```bash
# Check postgres data directly
oc exec deploy/search-postgres -n <mch-ns> -- \
  psql -U searchuser -d search -c "SELECT count(*) FROM search.resources" 2>&1

# If "relation does not exist" -> schema was dropped, restart postgres
# If count = 0 but table exists -> data lost, wait for collectors (10-30 min)

# Check postgres pod age vs other search pods
oc get pods -n <mch-ns> -l app=search-postgres \
  -o jsonpath='{.items[0].metadata.creationTimestamp}'
# If much younger than other search pods -> recent restart = likely data loss
```

**Classification impact:** This is the most common misclassification trap.
Without it, search tests with "0 results" get classified as PRODUCT_BUG
(search returns wrong data) when it's actually INFRASTRUCTURE (data lost
due to pod restart, will self-recover).

**Rule:** Search "all green" + "empty results" = always check postgres
schema and data count before investigating anything else.

**Operational note -- Recreate strategy + emptyDir:** search-postgres uses
Deployment strategy `Recreate` (not `RollingUpdate`). Combined with
emptyDir, ANY deployment update (including ACM upgrades, operator
reconciliation, resource limit changes) terminates the old pod before
starting the new one. This causes both a data loss AND a downtime window
on every restart. Post-upgrade empty search results for 10-30 minutes is
expected behavior, similar to Trap 5 (GRC settling). See
post-upgrade-patterns.md #6.

**Playbook reference:** diagnostic-playbooks.md, Search section, Step 6.

---

## Trap 4: Observability Dashboards Empty -- Looks Like Operator, Actually S3

**What you see:** Grafana dashboards show no data. MCO CR status may show
conditions. Observability tests fail.

**What you might conclude:** Observability operator is broken (PRODUCT_BUG).

**What's actually happening:** The most common cause of observability failure
is S3/object storage misconfiguration, NOT operator issues. The operator is
healthy -- it deployed everything correctly. But thanos-store, thanos-compactor,
and thanos-receive can't access the object storage.

**How to detect:**
```bash
# Check thanos pods FIRST (not the operator)
oc get pods -n open-cluster-management-observability | grep thanos

# If thanos-store or thanos-compactor are in CrashLoopBackOff:
oc logs -n open-cluster-management-observability <thanos-store-pod> --tail=20
# Look for: "bucket operation failed", "Access Denied", "NoSuchBucket"

# Verify the S3 secret
oc get secret thanos-object-storage -n open-cluster-management-observability -o yaml
```

**Classification impact:** Without this trap, observability test failures get
classified as PRODUCT_BUG (operator not working). The actual cause is
INFRASTRUCTURE (S3 credentials rotated or bucket misconfigured).

**Rule:** Observability failures -> check thanos pods and S3 secret before
investigating the operator.

**Reference:** observability/known-issues.md, Issue #4.

---

## Trap 5: GRC Policies Non-Compliant After Upgrade (Normal Behavior)

**What you see:** After ACM upgrade, governance dashboard shows multiple
policies as non-compliant or Unknown. Governance tests fail.

**What you might conclude:** Upgrade broke something in GRC (PRODUCT_BUG).

**What's actually happening:** This is NORMAL post-upgrade behavior:

1. Upgrade restarts governance-policy-framework addon on every spoke
2. While restarting, compliance status resets to Unknown
3. After restart, controllers re-evaluate all policies
4. Re-evaluation takes time (especially with `evaluationInterval` settings)
5. During this window (5-15 minutes), dashboard shows non-compliant/Unknown

**How to detect (is it settling or a real issue?):**
```bash
# Check if governance addons are still restarting
oc get managedclusteraddons -A | grep governance
# If "Progressing" or "Unknown" -> still settling, wait

# Check propagator for errors vs normal re-evaluation
oc logs -n <mch-ns> -l app=grc-policy-propagator --tail=30
# Normal: "Evaluating policy..." messages
# Problem: Error messages, panic, OOM
```

**Classification impact:** Without this trap, post-upgrade GRC test failures
are classified as PRODUCT_BUG or INFRASTRUCTURE. They should be NO_BUG
(expected transient behavior, tests ran during the settling window).

**Rule:** Post-upgrade GRC non-compliance for 5-15 minutes is expected.
Only investigate if (a) it persists beyond 20 minutes, OR (b) governance
addon pods are in CrashLoopBackOff, OR (c) propagator logs show errors.

**Cross-reference:** architecture/infrastructure/post-upgrade-patterns.md

---

## Trap 6: ManagedCluster NotReady -- Don't Assume Klusterlet Crashed

**What you see:** `oc get managedclusters` shows one or more clusters with
AVAILABLE=False or Unknown.

**What you might conclude:** Klusterlet on the spoke crashed, need to restart
it. Or: INFRASTRUCTURE on spoke.

**What's actually happening:** AVAILABLE=False has multiple causes, most of
which are NOT klusterlet crashes:

| Cause | Frequency | Klusterlet crashed? |
|-------|-----------|:---:|
| Network/firewall between spoke and hub | Common | No |
| Proxy configuration wrong on spoke | Common | No |
| Hub API server overloaded | Occasional | No |
| Lease renewal failure (transient) | Common | No |
| Klusterlet pod OOMKilled | Rare | Yes |
| Klusterlet pod evicted | Rare | Sort of |

**How to detect the ACTUAL cause:**
```bash
# Step 1: Check lease (hub-side, no spoke access needed)
oc get lease -n <cluster-namespace> --sort-by=.spec.renewTime
# If lease was renewed recently (last 5 min) -> NOT a connectivity issue
# If lease is stale -> spoke can't reach hub

# Step 2: Check conditions for specific messages
oc get managedcluster <name> -o jsonpath='{.status.conditions[*].message}'
# "the client is rate limited" -> hub API overloaded
# "failed to send lease update" -> spoke can't reach hub API
# "cluster has no agent" -> klusterlet not deployed

# Step 3: If all addons are also Unavailable -> it's connectivity
oc get managedclusteraddons -n <cluster-namespace>
# All unavailable = network issue (single addon unavailable = addon issue)
```

**Classification impact:** Without this trap, managed cluster connectivity
issues get classified as INFRASTRUCTURE (correct) but with wrong root cause
(klusterlet crash vs network issue). The root cause matters for
whether it's a test environment issue vs a product issue.

**Rule:** Check lease and conditions before concluding klusterlet crash.
If ALL addons are Unavailable for that cluster, it's connectivity, not
individual addon failures.

**Cross-reference:** cluster-lifecycle/health-patterns.md

---

## Trap 7: ALL Spoke Addons Unavailable -- Single Pod Failure

**What you see:** `oc get managedclusteraddons -A` shows ALL addons
(governance, search-collector, observability, etc.) as Unavailable across
multiple or all managed clusters.

**What you might conclude:** Widespread spoke failure. Each addon needs
individual investigation.

**What's actually happening:** Addon deployment to spokes is managed by
`addon-manager` (in the hub's MCE namespace). If addon-manager is down,
NO addons get deployed or updated on ANY spoke.

**How to detect:**
```bash
# Check addon-manager pod FIRST
oc get pods -n multicluster-engine | grep addon-manager
# If CrashLoopBackOff or not Running -> this is your root cause

# Don't investigate individual addons until addon-manager is healthy
```

**Classification impact:** Without this trap, tests across multiple feature
areas get classified independently (search INFRASTRUCTURE, governance
INFRASTRUCTURE, etc.) when there's ONE root cause. The diagnostic should
identify "addon-manager down" as the single infrastructure issue affecting
all addon-dependent tests.

**Rule:** Mass addon failure across multiple clusters -> check addon-manager
before anything else.

---

## Trap 8: Console Multiple Pages Failing -- Check Search First

**What you see:** Multiple seemingly unrelated console pages fail:
- Search page shows errors
- Fleet Virt VM list is empty
- Fleet Virt tree view is empty
- RBAC resource views show nothing
- Some policy status views are stale

**What you might conclude:** Console has a widespread bug (PRODUCT_BUG).
Or multiple backend services failed simultaneously.

**What's actually happening:** All these features share a single dependency:
`search-api`. Console proxies search queries for multiple features through
its Resource Proxy backend component. When search-api is down or slow,
all dependent features fail.

| Feature | Dependency on search-api |
|---------|------------------------|
| Search UI | Direct (GraphQL) |
| Fleet Virt VM list | Via multicluster-sdk |
| Fleet Virt tree view | Via multicluster-sdk |
| RBAC resource views | Via aggregate API |
| Policy status (some) | Via resource proxy |

**How to detect:**
```bash
# Check search-api FIRST
oc get pods -n <mch-ns> | grep search-api
oc logs -n <mch-ns> -l app=search-api --tail=20

# If search-api is down, fixing it resolves all dependent features
# Don't investigate console, fleet-virt, or RBAC individually
```

**Classification impact:** Without this trap, tests in Console, Virtualization,
RBAC, and GRC get classified independently -- some as AUTOMATION_BUG (selector
not found because page didn't render), some as PRODUCT_BUG (wrong data).
They should ALL be INFRASTRUCTURE with a single root cause: search-api down.

**Rule:** 3+ console features broken simultaneously -> check search-api
before investigating individual features.

**Reference:** console/known-issues.md #9 documents this cascade.

---

## Trap 9: ResourceQuota Blocking Pod Restarts

**What you see:** Pods gradually disappear from ACM namespaces. Services
degrade one by one over time. `oc get pods` shows fewer pods than expected.
Pod restart counts don't increase because the pod isn't restarting -- it's
not being recreated. Some deployments have fewer replicas than expected
with no error events visible.

**What you might conclude:** Individual component failures. Each missing
pod is a separate issue. Or: the operator is healthy but scaled down
intentionally.

**What's actually happening:** A ResourceQuota in the ACM namespace limits
the total pod count or resource consumption. When a pod crashes or is
evicted, the replacement pod can't be created because creating it would
exceed the quota. The Deployment shows `desiredReplicas=2` but
`availableReplicas=0`.

ACM does not create ResourceQuotas by default. Any ResourceQuota in an ACM
namespace was added externally (by an admin, policy, or cluster operator).

**How to detect:**
```bash
# Check for ResourceQuotas in ACM namespaces
oc get resourcequota -n <mch-ns> --no-headers
oc get resourcequota -n multicluster-engine --no-headers

# If found, check what's being limited
oc describe resourcequota -n <mch-ns>
# Look at Used vs Hard limits for pods, cpu, memory

# Compare pod counts against healthy-baseline.yaml
```

**Rule:** If pods are missing but not restarting, check for ResourceQuotas
before investigating individual component failures. ResourceQuota in ACM
namespaces is always suspicious.

---

## Trap 10: Hive Webhook Misconfigured Blocks ALL Cluster Operations

**What you see:** Cluster creation fails. Cluster import fails. Cluster
deletion fails. All operations on ClusterDeployment CRs return errors
like `failed calling webhook "clusterdeploymentvalidators"`.

**What you might conclude:** Hive operator is broken or needs restart.

**What's actually happening:** Hive registers a ValidatingWebhookConfiguration
with `failurePolicy: Fail`. If the webhook service pod (`hiveadmission`)
is down, crashed, or its TLS cert is expired, the API server rejects
ALL create/update/delete operations on Hive CRDs. The Hive operator itself
may be perfectly healthy -- it's the admission webhook that's blocking.

**How to detect:**
```bash
# Check the webhook configuration
oc get validatingwebhookconfiguration | grep hive

# Check the webhook service endpoint
oc get pods -n hive | grep hiveadmission
oc logs -n hive -l app=hiveadmission --tail=20

# Test if the webhook is actually blocking
oc get events -n <any-cluster-ns> --sort-by=.lastTimestamp | grep webhook
```

**Rule:** When ALL cluster lifecycle operations fail, check Hive webhook
before investigating the Hive operator or controllers.

---

## Trap 11: NetworkPolicy Silently Blocking Pod Communication

**What you see:** All pods are Running and Ready (probes pass). But
specific inter-service communication fails. For example, search-api
can't reach search-postgres, or console can't reach search-api.
Services that depend on the blocked path return errors or empty results.
Features don't work -- search returns empty, governance policies don't
propagate, etc.

**What you might conclude:** The service itself is broken or has a bug
(PRODUCT_BUG). All infrastructure looks healthy.

**What's actually happening:** A NetworkPolicy in the ACM namespace is
blocking ingress or egress traffic between pods. ACM does NOT create
NetworkPolicies by default. Any NetworkPolicy in an ACM namespace was
added externally (test artifact or external security constraint) and
may silently break pod-to-pod communication that ACM expects to work.

The insidious aspect: pods are Running (health probes use localhost, not
cross-pod connections), but cross-pod communication fails. The failure
is invisible until a feature that requires the blocked communication
path is used.

**How to detect:**
```bash
# Check for NetworkPolicies in ACM namespaces
oc get networkpolicy -n <mch-ns> --no-headers
oc get networkpolicy -n multicluster-engine --no-headers
oc get networkpolicy -n open-cluster-management-hub --no-headers

# If found, check what traffic is blocked
oc describe networkpolicy -n <mch-ns>
# Look at Ingress/Egress rules and which pods they affect
```

**Rule:** When pods are Running but cross-service communication fails,
check for NetworkPolicies before concluding the service has a bug.
Any NetworkPolicy in an ACM namespace is suspicious. This MUST be
checked BEFORE pod health (Layer 3 before Layer 9).

---

## Trap 12: TLS Cert Corrupted but service-CA Doesn't Auto-Repair

**What you see:** A service returns TLS handshake errors. The pod may be
CrashLooping with TLS-related errors in logs. service-ca-operator is
healthy and running. All pods Running, no restarts, but connections
between services fail intermittently.

**What you might conclude:** service-ca-operator is broken and not
rotating certificates properly. Or: network issue or PRODUCT_BUG in
service communication.

**What's actually happening:** The TLS secret for the service exists but
contains corrupted or manually modified certificate data. service-ca-operator
only creates secrets -- it does NOT overwrite existing secrets. If someone
(or a process) modified the secret content, service-ca-operator sees the
secret already exists and skips it.

This is common when:
- A secret was manually edited for debugging and not reverted
- A backup/restore process corrupted the secret
- An operator patched the wrong secret
- A certificate expired or rotated incorrectly

**How to detect:**
```bash
# Check cert validity
oc get secret <secret-name> -n <ns> -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -dates -issuer 2>&1
# If "unable to load certificate" -> cert data is corrupted
# If expired -> rotation didn't happen because secret exists

# Check if service-ca annotations are intact
oc get secret <secret-name> -n <ns> -o yaml | grep -i service
# Should have service.beta.openshift.io annotations

# Check TLS secret ages against certificate-inventory.yaml
# Look for x509: certificate has expired in pod logs

# Check for pending CSRs
oc get csr | grep Pending
```

**Shared TLS secret pattern:** Some ACM services share a TLS secret
across components. If a shared secret is corrupted, ALL services that
mount it fail simultaneously. When multiple services show TLS errors
at the same time, check whether they reference the same secret:
```bash
# Find which secrets are mounted by a failing pod
oc get deploy <name> -n <ns> -o jsonpath='{.spec.template.spec.volumes[*].secret.secretName}'
# Check if other deployments mount the same secret
oc get deploy -n <ns> -o json | jq -r '.items[] | .metadata.name as $n | .spec.template.spec.volumes[]? | select(.secret?) | "\($n): \(.secret.secretName)"' | sort -t: -k2
```
A single corrupted secret can manifest as failures in seemingly
unrelated subsystems.

**Fix:** Delete the corrupted secret. service-ca-operator will detect
the missing secret and recreate it with a fresh certificate. Restart
the affected pod to pick up the new cert.

**Rule:** service-ca-operator creates but doesn't overwrite. If a cert
is broken, check the secret contents before blaming the operator.

---

## Trap 13: ConsolePlugin Registered but Plugin Service Unreachable

**What you see:** ConsolePlugin CRs exist and are registered in the
OCP console config. The main console pod is healthy. But specific
feature tabs render with loading errors, blank content, or JavaScript
errors -- not entirely missing, but broken.

**What you might conclude:** The console has a UI rendering bug (PRODUCT_BUG).

**What's actually happening:** The ConsolePlugin CR references a backend
Service that serves the plugin's JavaScript bundle and API. If the
plugin's backend pod is unhealthy (crashed, image pull failure, resource
limits), the OCP console successfully loads the plugin shell but fails
to fetch the plugin's content at runtime. The tab appears in navigation
(because the plugin is registered) but renders errors (because the
content can't be loaded).

This is different from Trap 2:
- **Trap 2:** Tabs entirely missing (ConsolePlugin not registered or
  console-mce pod is down)
- **Trap 13:** Tabs present but render errors (plugin registered but
  its backend is unhealthy)

**How to detect:**
```bash
# Check ConsolePlugin CRs
oc get consoleplugins -o yaml
# Note the .spec.backend.service for each plugin

# Check the plugin backend pods
oc get pods -n <mch-ns> -l app=console-chart-console-v2
oc get pods -n multicluster-engine -l app=console-mce-console

# Check if the plugin service endpoint has ready addresses
oc get endpoints -n <ns> <service-name>
# If no ready addresses -> backend pod is down
```

**Rule:** Feature tabs present but broken -> check plugin backend pod
health. Feature tabs missing entirely -> check ConsolePlugin CRDs
and console-mce pod (Trap 2).

---

## Trap 14: Both Operator Replicas Running but Reconciliation Stopped

**What you see:** An operator Deployment shows 2/2 (or 3/3) replicas
Running and Ready. Pod logs show no errors. But the operator is not
reconciling -- CRs are not being processed, status fields are not
updating, managed resources are drifting.

**What you might conclude:** Everything is healthy. Or: the CR is
correct and nothing needs reconciling.

**What's actually happening:** Kubernetes controllers with HA (multiple
replicas) use leader election to ensure only one replica actively
reconciles. The standby replicas idle until the leader's lease expires.
If leader election is stuck -- the leader's lease expired but no replica
re-acquires it (clock skew, etcd latency, Lease/ConfigMap lock
contention) -- NEITHER replica reconciles. Health probes still pass
because they check the process, not the reconcile loop.

This applies to any HA operator using `--leader-elect`, including:
- multiclusterhub-operator (2 replicas)
- multicluster-engine-operator (2 replicas)
- grc-policy-propagator (2 replicas)
- cluster-manager (3 replicas)
- cluster-curator-controller (2 replicas)
- Any controller with leader election enabled

**How to detect:**
```bash
# Check leader election lease for the operator
oc get lease -n <operator-ns> --no-headers | grep <operator-name>
oc get lease <lease-name> -n <operator-ns> -o jsonpath='{.spec.renewTime}'
# If renewTime is stale (>2x leaseDurationSeconds ago), leader election
# is stuck. Default leaseDuration is typically 15-30s.

# Check operator logs for reconciliation activity
oc logs -n <ns> -l <operator-label> --tail=30 --timestamps
# Healthy: "Reconciling <resource>" messages at regular intervals
# Stuck: only health check / probe activity, no reconcile messages

# Common root cause: etcd latency (Layer 2)
time oc get namespaces > /dev/null
# If >2 seconds, etcd latency may be causing lease expiry
```

**Rule:** When an HA operator shows all replicas Running but nothing is
being reconciled, check the leader election lease before concluding the
CRs are correct. A stale lease `renewTime` indicates stuck leader
election. This is a variant of Trap 1 (stale status) but with a
different root cause -- the operator process is alive but not active.

---

## Counter-Traps: Protecting Against FALSE Classification

Traps 1-11 protect against wrongly classifying as PRODUCT_BUG or
AUTOMATION_BUG when the real cause is INFRASTRUCTURE. The following
counter-traps protect in the OPPOSITE direction -- preventing
over-classification as INFRASTRUCTURE when per-test evidence points
elsewhere.

---

## Counter-Trap A: Degraded Cluster but Selector Doesn't Exist (False INFRASTRUCTURE)

**What you see:** Oracle or diagnostic reports "search-collector degraded
on 2/5 clusters" or "search-postgres recently restarted." Multiple tests
in the Search feature area fail.

**What you might conclude:** All Search test failures are INFRASTRUCTURE
because the cluster is degraded.

**What's actually happening:** Some tests fail because of the degraded
infrastructure (timeouts, empty results). But OTHER tests in the same
feature area fail because of stale selectors -- the test code references
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
  without test update) -- but it's still NOT INFRASTRUCTURE.

**Classification impact:** Without this trap, ALL tests in a degraded
feature area get swept into INFRASTRUCTURE. The pipeline should classify
each test independently based on its specific error, using infrastructure
data as context -- not as a blanket override.

**Rule:** A degraded cluster does NOT explain a missing selector. Always
check `console_search.found` before accepting an INFRASTRUCTURE
classification from the oracle or diagnostic.

---

## Counter-Trap B: Backend Returns Wrong Data Despite All Pods Healthy (False INFRASTRUCTURE)

**What you see:** Tests fail with "expected 5 items, got 3" or "expected
hub name 'my-hub', got 'other-hub'." Backend probes detect anomalies.
Oracle shows some components as degraded.

**What you might conclude:** INFRASTRUCTURE -- the backend components
are broken.

**What's actually happening:** The console backend code has a data
transformation bug. The Kubernetes API returns correct data, but the
console's backend proxy (Node.js) corrupts it during transformation.
All pods are healthy -- the code is running correctly, it just produces
wrong output.

**How to detect:**
- Check `cluster-diagnosis.json` -> `subsystem_health` for the feature area.
  If subsystem is healthy but test shows wrong data values, the issue is
  in the console code, not the cluster.
- Check `assertion_analysis` -- if `has_data_assertion=true` and values
  don't match, investigate whether the backend API returns correct data
  via targeted `oc exec + curl` during Stage 2.
- If Kubernetes API returns correct values but the console UI shows
  different values, that's data corruption in the proxy layer.

**Classification impact:** Without this trap, data assertion failures
in a degraded cluster get classified as INFRASTRUCTURE ("the cluster
returned wrong data"). The real cause is PRODUCT_BUG -- the console's
data transformation has a bug.

**Rule:** When the cluster returns correct data but the console shows
wrong data, it's PRODUCT_BUG regardless of cluster health.

---

## Counter-Trap C: Disabled Prerequisite That Should Be Enabled (False NO_BUG)

**What you see:** Tests for a feature area fail with blank pages or
"element not found." The feature's operator/addon is not installed.
Classification as NO_BUG ("prerequisite not met, feature disabled").

**What you might conclude:** NO_BUG -- the feature is intentionally
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
be notified that their setup failed. This is INFRASTRUCTURE -- the test
environment was not correctly provisioned.

**Rule:** Before classifying NO_BUG for a missing prerequisite, verify
the prerequisite was not supposed to be present for this pipeline run.

---

## Quick Reference: Trap Index

| Trap | Symptom | Check First | Wrong -> Correct Classification |
|------|---------|-------------|-------------------------------|
| 1 | MCH says Running but things break | Operator pod replicas | Healthy -> INFRASTRUCTURE |
| 1b | Operator pods Running but nothing reconciling | Leader election Lease renewTime | Healthy -> INFRASTRUCTURE |
| 2 | Console pod healthy, tabs missing | console-mce + ConsolePlugin CRDs | AUTOMATION_BUG -> INFRASTRUCTURE |
| 3 | Search all green, empty results | Postgres pod age + data count | PRODUCT_BUG -> INFRASTRUCTURE |
| 4 | Observability dashboards empty | Thanos pods + S3 secret | PRODUCT_BUG -> INFRASTRUCTURE |
| 5 | GRC non-compliant after upgrade | Addon pod age (wait 15 min) | PRODUCT_BUG -> NO_BUG |
| 6 | ManagedCluster NotReady | Lease + conditions (not klusterlet) | Wrong root cause |
| 7 | ALL addons Unavailable everywhere | addon-manager pod | Multiple issues -> single root cause |
| 8 | Multiple console pages broken | search-api pod | Multiple PRODUCT_BUG -> single INFRASTRUCTURE |
| 9 | Pods gradually disappearing | ResourceQuota in ACM namespace | Hidden INFRASTRUCTURE |
| 10 | ALL cluster ops fail | Hive webhook service | Operator blame -> webhook blame |
| 11 | Pods Running, cross-service fails | NetworkPolicy in ACM namespace | PRODUCT_BUG -> INFRASTRUCTURE |
| 12 | TLS errors, service-ca healthy | Corrupted cert secret (delete to fix) | Operator blame -> secret blame |
| 13 | Feature tabs present but broken | Plugin backend pod health | PRODUCT_BUG -> INFRASTRUCTURE |
| 14 | Both replicas Running, nothing reconciling | Leader election lease (renewTime) | Healthy -> INFRASTRUCTURE |
| A | Degraded cluster + selector error | console_search.found per test | INFRASTRUCTURE -> AUTOMATION_BUG |
| B | Backend data wrong despite healthy pods | subsystem_health + data assertions | INFRASTRUCTURE -> PRODUCT_BUG |
| C | Missing prerequisite that should exist | Jenkins params + MCH components | NO_BUG -> INFRASTRUCTURE |
