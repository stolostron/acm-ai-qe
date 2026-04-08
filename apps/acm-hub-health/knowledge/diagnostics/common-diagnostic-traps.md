# Common Diagnostic Traps

Patterns where the obvious diagnosis is WRONG. Read this before concluding
any investigation. Each trap describes what you see, what you might conclude,
and what's actually happening.

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

**Rule:** Never trust MCH/MCE `.status.phase` without first confirming the
operator pod is Running and Ready. Same applies to MCE status -- check the
`multicluster-engine` operator pod.

---

## Trap 2: Console Pod Healthy but Feature Tabs Missing

**What you see:** Console pod is Running/Ready (liveness/readiness probes pass).
But users report entire sections missing from the UI (e.g., Clusters tab,
Infrastructure tab gone).

**What you might conclude:** Console is fine, user is confused.

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

**Rule:** Console pod healthy does NOT mean console is fully functional.
Always check: (1) console-mce pod, (2) ConsolePlugin CRDs, (3) backend
services (search-api, console-api).

**Version note:** In ACM 2.16+, console-api is integrated into the console
chart. The separate console-api deployment may not exist. Check what's
actually deployed rather than assuming specific pod names.

---

## Trap 3: Search Returns Empty but All Pods Are Green

**What you see:** `oc get pods | grep search` shows all search pods Running.
Search-collector addon is Available on spokes. But search UI returns 0 results.

**What you might conclude:** Search is healthy, maybe a UI bug.

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

# If "relation does not exist" → schema was dropped, restart postgres
# If count = 0 but table exists → data lost, wait for collectors (10-30 min)

# Check postgres pod age vs other search pods
oc get pods -n <mch-ns> -l app=search-postgres \
  -o jsonpath='{.items[0].metadata.creationTimestamp}'
# If much younger than other search pods → recent restart = likely data loss
```

**Rule:** Search "all green" + "empty results" = always check postgres
schema and data count before investigating anything else.

**Playbook reference:** diagnostic-playbooks.md, Search section, Step 6.

---

## Trap 4: Observability Dashboards Empty -- Looks Like Operator, Actually S3

**What you see:** Grafana dashboards show no data. MCO CR status may show conditions.

**What you might conclude:** Observability operator is broken.

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

**Rule:** Observability failures -> check thanos pods and S3 secret before
investigating the operator.

**Reference:** observability/known-issues.md, Issue #4.

---

## Trap 5: GRC Policies Non-Compliant After Upgrade (Normal Behavior)

**What you see:** After ACM upgrade, governance dashboard shows multiple
policies as non-compliant or Unknown.

**What you might conclude:** Upgrade broke something in GRC.

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

**Rule:** Post-upgrade GRC non-compliance for 5-15 minutes is expected.
Only investigate if (a) it persists beyond 20 minutes, OR (b) governance
addon pods are in CrashLoopBackOff, OR (c) propagator logs show errors.

**Cross-reference:** architecture/infrastructure/post-upgrade-patterns.md

---

## Trap 6: ManagedCluster NotReady -- Don't Assume Klusterlet Crashed

**What you see:** `oc get managedclusters` shows one or more clusters with
AVAILABLE=False or Unknown.

**What you might conclude:** Klusterlet on the spoke crashed, need to restart it.

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

**What you might conclude:** Console has a widespread bug. Or multiple
backend services failed simultaneously.

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

**Rule:** 3+ console features broken simultaneously -> check search-api
before investigating individual features.

**Reference:** console/known-issues.md #9 documents this cascade.

---

## Trap 9: ResourceQuota Blocking Pod Restarts

**What you see:** Pods gradually disappear from ACM namespaces. Services
degrade one by one over time. `oc get pods` shows fewer pods than expected.
Pod restart counts don't increase because the pod isn't restarting -- it's
not being recreated.

**What you might conclude:** Individual component failures. Each missing
pod is a separate issue.

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
```

**Rule:** If pods are missing but not restarting, check for ResourceQuotas
before investigating individual component failures.

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

**What you might conclude:** The service itself is broken or has a bug.

**What's actually happening:** A NetworkPolicy in the ACM namespace is
blocking ingress or egress traffic between pods. ACM does NOT create
NetworkPolicies by default. Any NetworkPolicy in an ACM namespace was
added externally and may silently break pod-to-pod communication that
ACM expects to work.

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
Any NetworkPolicy in an ACM namespace is suspicious.

---

## Trap 12: TLS Cert Corrupted but service-CA Doesn't Auto-Repair

**What you see:** A service returns TLS handshake errors. The pod may be
CrashLooping with TLS-related errors in logs. service-ca-operator is
healthy and running.

**What you might conclude:** service-ca-operator is broken and not
rotating certificates properly.

**What's actually happening:** The TLS secret for the service exists but
contains corrupted or manually modified certificate data. service-ca-operator
only creates secrets -- it does NOT overwrite existing secrets. If someone
(or a process) modified the secret content, service-ca-operator sees the
secret already exists and skips it.

This is common when:
- A secret was manually edited for debugging and not reverted
- A backup/restore process corrupted the secret
- An operator patched the wrong secret

**How to detect:**
```bash
# Check cert validity
oc get secret <secret-name> -n <ns> -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -dates -issuer 2>&1
# If "unable to load certificate" -> cert data is corrupted
# If expired -> rotation didn't happen because secret exists

# Check if service-ca annotations are intact
oc get secret <secret-name> -n <ns> -o yaml | grep -i service
# Should have service.beta.openshift.io annotations
```

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

**What you might conclude:** The console has a UI rendering bug.

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

## Quick Reference: Trap Index

| Trap | Symptom | Check First |
|------|---------|-------------|
| 1 | MCH says Running but things are broken | Operator pod replicas |
| 2 | Console pod healthy, tabs missing | console-mce pod + ConsolePlugin CRDs |
| 3 | Search all green, empty results | Postgres schema + data count |
| 4 | Observability dashboards empty | Thanos pods + S3 secret |
| 5 | GRC non-compliant after upgrade | Addon pod age (wait 15 min) |
| 6 | ManagedCluster NotReady | Lease + conditions (not klusterlet) |
| 7 | ALL addons Unavailable everywhere | addon-manager pod |
| 8 | Multiple console pages broken | search-api pod |
| 9 | Pods gradually disappearing | ResourceQuota in ACM namespace |
| 10 | ALL cluster operations fail | Hive webhook service |
| 11 | Pods Running but cross-service fails | NetworkPolicy in ACM namespace |
| 12 | TLS errors, service-ca healthy | Corrupted cert secret (delete to fix) |
| 13 | Feature tabs present but broken | Plugin backend pod health |
