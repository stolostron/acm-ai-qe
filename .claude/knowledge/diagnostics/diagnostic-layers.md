# 12-Layer Diagnostic Model

Systematic investigation framework for finding root causes in ACM clusters.
Each layer is a distinct failure domain. A failure at a lower layer cascades
upward and manifests as symptoms at higher layers.

This model serves two purposes:
- **Hub health diagnosis** (acm-hub-health): determining cluster state
  (HEALTHY, DEGRADED, CRITICAL) by tracing through infrastructure layers
- **Failure classification** (z-stream-analysis): finding the root cause
  of test failures and determining WHO caused the breakage to classify as
  PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or NO_BUG

Reference: DIAGNOSTIC-LAYER-ARCHITECTURE.md (validated against ACM 2.16
GA on Azure and ACM 2.17 bugged cluster on AWS with 5 injected issues).

## The 12 Layers (bottom to top)

```
    SYMPTOM APPEARS HERE (top)
    ─────────────────────────
    Layer 12: UI / Plugin / Rendering
    Layer 11: Data Flow / Content Integrity
    Layer 10: Cross-Cluster / Hub-Spoke
    Layer  9: Operator / Reconciliation
    Layer  8: API / CRD / Webhook
    Layer  7: Authorization / RBAC
    Layer  6: Authentication / Identity
    Layer  5: Configuration / Desired State
    Layer  4: Storage / Data Persistence
    Layer  3: Network / Connectivity
    Layer  2: Control Plane / State Store
    Layer  1: Compute / Scheduling
    ─────────────────────────
    ROOT CAUSE LIVES HERE (bottom)
```

Each layer depends on all layers below it. A failure at a lower layer
cascades upward and manifests as symptoms at higher layers. A network
issue (Layer 3) looks like a data issue (Layer 11) which looks like a
UI issue (Layer 12). The diagnostic challenge is tracing downward to
the actual broken layer.

**Layers are failure domains to check or eliminate, NOT mandatory steps.**
Skip layers that don't apply to the current investigation.

## Diagnostic Workflows

### Hub Health: When to Go Bottom-Up vs Top-Down

**Bottom-up (Layers 1->12):** Full health audit (`/deep`). Check
foundational layers first to find root causes before symptoms.

**Top-down (Layers 12->1):** Targeted investigation (`/investigate`).
Start at the symptom layer and trace downward.

**Hybrid approach (recommended for standard checks):**

```
+---------------------------------------------------------------+
|                    DIAGNOSTIC WORKFLOW                          |
+----------------------------------------------------------------+
|                                                                 |
|  Step 1: QUICK SWEEP (10 seconds)                              |
|  +-- Layer 1: Nodes Ready? Pods scheduling?                    |
|  +-- Layer 2: API server responding? etcd healthy?             |
|  +-- Layer 3: NetworkPolicies in ACM namespaces?               |
|       +-- If ANY broken -> ROOT CAUSE FOUND (stop here)        |
|                                                                 |
|  Step 2: CHECK BY LAYER (bottom-up for /deep)                  |
|  +-- Layer 4:  Storage accessible? PVCs Bound?                 |
|  +-- Layer 5:  Configuration correct? Components enabled?      |
|  +-- Layer 6:  Auth working? (skip if admin-only)              |
|  +-- Layer 7:  RBAC correct? (skip if admin-only)              |
|  +-- Layer 8:  CRDs exist? Webhooks responsive?                |
|  +-- Layer 9:  Operators reconciling? Replicas correct?        |
|  +-- Layer 10: Managed clusters Available? Addons deployed?    |
|  +-- Layer 11: Data flowing correctly?                         |
|  +-- Layer 12: Plugins registered? Console rendering?          |
|       +-- At each layer: APPLICABLE? -> check. Skip if not.   |
|       +-- HEALTHY? -> move up. BROKEN? -> investigate deeper.  |
|                                                                 |
|  Step 3: CONFIRM ROOT CAUSE                                    |
|  +-- Verify with 2+ evidence sources (evidence-tiers.md)       |
|  +-- Rule out adjacent layers                                  |
|  +-- Check against diagnostic traps (diagnostic-traps.md)      |
|  +-- Trace upstream impact (what else does this break?)        |
|                                                                 |
+----------------------------------------------------------------+
```

### Failure Classification: Map Symptom, Trace, Classify

For test failure investigation (z-stream analysis), use a 3-step process:

**Step B0: Map Symptom to Starting Layer**

| Error pattern | Start at layer |
|---|---|
| "element not found", selector missing | Layer 12 (UI) |
| "timed out waiting for" | Layer 12, trace down |
| "Expected X but got Y" (data mismatch) | Layer 11 (Data Flow) |
| "Expected to find content" (empty data) | Layer 11 (Data Flow) |
| "500 Internal Server Error" | Layer 9 (Operator) |
| "403 Forbidden" | Layer 7 (RBAC) |
| "401 Unauthorized" | Layer 6 (Auth) |
| "connection refused" / "connection timed out" | Layer 3 (Network) |
| blank page / `class="no-js"` / empty body | Could be 3, 6, 9, or 12 |
| "button disabled" / `aria-disabled` | Layer 7, 11, or 12 |
| `cy.exec()` failed / shell error | Layer 1 (Compute/CI) |
| pod OOMKilled / CrashLoopBackOff | Layer 1 or 9 |

**Step B1: Check cluster-diagnosis.json First**

Before running oc commands, cross-reference the test's feature area
against pre-computed health data:

- Read `cluster-diagnosis.json` for this test's feature area
- Check subsystem_health, operator_health, and classification_guidance
- Is the relevant subsystem OK, DEGRADED, or CRITICAL?
- Are there `infrastructure_issues` affecting this feature?
- Check `health_depth` -- does it cover only pod-level or deeper?

If cluster-diagnosis shows CRITICAL issues in this feature area:
  Strong INFRASTRUCTURE signal, but STILL verify the connection
  between the infrastructure issue and THIS test's specific error.

If cluster-health shows all layers OK for this feature area:
  Root cause is likely Layer 11 (data) or Layer 12 (UI/test).

If cluster-diagnosis.json has `pre_classified_infrastructure` for
this feature area: use as Tier 1 evidence. Do NOT re-run the same
oc commands Stage 1.5 already ran.

**Step B2: Trace Downward (if needed)**

Starting from the symptom layer (Step B0), check each applicable
layer. Use ALL available tools (oc commands, MCP queries, knowledge
DB files). Investigate as deep as needed until you have evidence.

At each layer, answer:
a) Is this layer healthy FOR THE SPECIFIC COMPONENT this test uses?
b) If unhealthy: is this the ROOT CAUSE, or a symptom of a deeper
   issue? If symptom, continue downward. If root cause, go to Step B3.
c) If healthy: move to the next lower applicable layer.

Skip layers that don't apply:
- No managed clusters involved? Skip Layer 10.
- Admin user test? Skip Layers 6-7.
- No persistent storage? Skip Layer 4.
- No resource creation in test? Skip Layer 8.

**Step B3: Investigate WHO/WHY at Root Cause Layer**

Once the broken layer is found, determine the CAUSE:

a) WHO owns the broken resource?
   ```
   oc get <resource> -n <ns> -o jsonpath='{.metadata.ownerReferences}'
   oc get <resource> -n <ns> -o jsonpath='{.metadata.labels}'
   ```
   - ownerReferences point to ACM operator? product-created
   - No owner, no ACM labels? external/manual
   - Test namespace/labels? test-created

b) WHEN was it created/modified?
   ```
   oc get <resource> -o jsonpath='{.metadata.creationTimestamp}'
   ```
   Compare against operator deployment times, test start time.

c) WHY is it in this state?
   ```
   oc logs <related-pod> --tail=100
   oc get events -n <ns> --sort-by=.lastTimestamp
   ```
   - ACM Source MCP: search_code("<component>") for intended behavior
   - JIRA MCP: search_issues() for related bugs
   - Knowledge DB: read failure-signatures.md for known patterns

## Per-Layer Reference

### Layer 1: Compute / Scheduling

**What breaks:** Node NotReady, OOMKilled (exit 137), pod evicted,
ImagePullBackOff, Pending pods (insufficient resources or taints).

```
Check: oc get nodes
       oc adm top nodes
       oc get pods -n <acm-ns> --field-selector=status.phase!=Running,status.phase!=Succeeded
       oc get events -A --field-selector reason=OOMKilling --sort-by=.lastTimestamp | tail -5
Healthy: All nodes Ready, no resource pressure, pods scheduling
Broken:  Node NotReady, OOMKilled, Evicted, ImagePullBackOff, Pending
```

**Impact:** If a node is NotReady, ALL pods on that node are affected.
Check this before investigating specific component failures.

**Knowledge:** kubernetes-fundamentals.md, healthy-baseline.yaml

---

### Layer 2: Control Plane / State Store

**What breaks:** etcd slow (>50ms disk latency), etcd leader stuck,
etcd database too large (>8GB), API server overloaded, scheduler stuck.

```
Check: oc get co etcd kube-apiserver kube-scheduler
       oc get pods -n openshift-etcd --no-headers | grep -v guard
       time oc get namespaces > /dev/null  (should be < 1 second)
Healthy: All control plane operators Available, API responsive
Broken:  etcd slow, API server overloaded, scheduler not scheduling
Signal:  Multiple unrelated operators fail simultaneously? Suspect Layer 2.
```

**Impact:** When etcd is slow, EVERY operator appears to fail. The
root cause is not in any operator -- it's the state store below them.
~51% of cluster-wide K8s failures trace to state store issues (DSN 2024).

**Knowledge:** kubernetes-fundamentals.md

---

### Layer 3: Network / Connectivity

**What breaks:** NetworkPolicy blocking traffic (silent -- no error,
just timeout), service has no endpoints, DNS failure, route
misconfiguration, proxy blocking outbound traffic.

```
Check: oc get networkpolicy -n <acm-ns> --no-headers
       oc get networkpolicy -n multicluster-engine --no-headers
       oc get resourcequota -n <acm-ns> --no-headers
       oc get resourcequota -n multicluster-engine --no-headers
       oc get endpoints -n <acm-ns> <service-name>
       oc get svc -n <acm-ns> -o wide
       oc exec deploy/<pod-a> -- curl http://<service-b>:<port> --connect-timeout 3
Healthy: No NetworkPolicies in ACM namespaces, pods can reach services,
         all Services have ready endpoints
Broken:  NetworkPolicy blocking traffic, service no endpoints, DNS failure
```

**IMPORTANT:** ACM does NOT create NetworkPolicies or ResourceQuotas
by default. Any found in ACM namespaces is externally created and
suspicious. This is checked BEFORE pod health (Layer 9) because a
NetworkPolicy can make pods appear healthy (Running, 0 restarts) while
being completely non-functional.

**Service endpoint verification:** Every inter-component dependency
in ACM traverses a Kubernetes Service. A Service with zero ready
endpoints is a silent failure -- requests hang or return connection
refused, but no error appears on the Service object itself. When a
NetworkPolicy is found or connectivity failures are suspected, check
whether affected Services have ready endpoints:
```
oc get endpoints -n <acm-ns> --no-headers | awk '$2 == "<none>" {print $1}'
oc get endpoints -n multicluster-engine --no-headers | awk '$2 == "<none>" {print $1}'
oc get endpoints -n hive --no-headers | awk '$2 == "<none>" {print $1}'
```
Any Service with `<none>` endpoints means its selector does not match
any Running/Ready pods. Cross-reference with `service-map.yaml` to
identify which components are affected. This happens after label
changes during upgrades, when readiness probes fail, or when pods
restart and haven't passed readiness yet.

**Diagnostic traps:** Trap 9 (ResourceQuota blocks pod restarts),
Trap 11 (NetworkPolicy silently blocks pod communication).

**Knowledge:** infrastructure/architecture.md, infrastructure/known-issues.md,
infrastructure/failure-signatures.md, service-map.yaml

---

### Layer 4: Storage / Data Persistence

**What breaks:** PVC stuck Pending, S3 credentials expired (thanos),
emptyDir data loss on pod restart (search-postgres), disk full.

```
Check: oc get pvc -n <acm-ns>
       oc get pvc -n open-cluster-management-observability
       oc get sc | grep "(default)"
       oc exec deploy/search-postgres -n <acm-ns> -- \
         psql -U searchuser -d search -c "SELECT count(*) FROM search.resources"
Healthy: PVCs Bound, search-postgres has data, S3 credentials valid
Broken:  PVC Pending, disk full, emptyDir data lost, S3 expired
Signal:  search-postgres recently restarted? emptyDir data loss (Trap 3).
```

**Storage models vary by component.** Not all ACM components use PVCs.
Before checking PVCs, determine the component's storage model:

| Component | Storage Model | Layer 4 Concern |
|-----------|--------------|-----------------|
| search-postgres | emptyDir | Pod restart = total data loss. Check pod age + row count |
| observability (thanos-*) | PVC (StatefulSet) | PVC bound? Disk full? S3 credentials valid? |
| search-api, console, grc | stateless | No Layer 4 concern -- skip for these |
| hive-clustersync | emptyDir | Pod restart = sync state lost, re-sync needed |

```
# Determine storage model for any deployment:
# oc get deploy <name> -n <ns> -o jsonpath='{.spec.template.spec.volumes[*].name}'
#
# PVC-backed:  observability (thanos-receive, thanos-store, alertmanager,
#              compactor, rule) -- data survives pod restart
# emptyDir:    search-postgres (default) -- data lost on restart, rebuilt
#              from collectors. No PVC expected; absence is normal.
# Stateless:   search-api, console, grc-propagator, import-controller
#              -- no persistent data, no storage concern
# External:    observability (S3/object storage) -- check thanos-object-storage Secret
```
A missing PVC is only a finding if the component is expected to use one.
For emptyDir components, the diagnostic question is "did the pod restart
recently?" not "is the PVC bound?" For stateless components, skip Layer 4.

**Diagnostic traps:** Trap 3 (search empty but pods green -- emptyDir
data loss), Trap 4 (observability empty -- S3 misconfiguration).

**Knowledge:** search/architecture.md, observability/architecture.md,
observability/failure-signatures.md, healthy-baseline.yaml

---

### Layer 5: Configuration / Desired State

**What breaks:** MCH component disabled (feature silently absent), OLM
Subscription pointing to wrong channel, ConfigMap with wrong values,
feature gate not enabled, CatalogSource gRPC disconnected, CSV not
Succeeded.

```
Check: oc get mch -n <acm-ns> -o jsonpath='{range .spec.overrides.components[*]}{.name}={.enabled}{"\n"}{end}'
       oc get sub -A | grep -E "acm|mce|multicluster"
       oc get catsrc -n openshift-marketplace -o 'custom-columns=NAME:.metadata.name,STATE:.status.connectionState.lastObservedState'
       oc get csv -n <acm-ns> -o 'custom-columns=NAME:.metadata.name,PHASE:.status.phase'
       oc get csv -n multicluster-engine -o 'custom-columns=NAME:.metadata.name,PHASE:.status.phase'
       oc get installplan -n <acm-ns>
Healthy: All expected MCH components enabled, correct OLM subscriptions,
         CatalogSources READY, CSVs Succeeded
Broken:  Component disabled (silently absent), wrong subscription channel,
         CatalogSource disconnected, CSV stuck (Pending/Replacing/Failed)
Signal:  Feature completely absent (no pods, no CRDs, no errors)?
         Check Layer 5 -- a disabled component produces zero evidence.
```

**OLM is the foundation for ALL operators.** Three failure scenarios
are invisible to basic pod checks:

1. **CatalogSource with stale gRPC connection:** `oc get catsrc -n
   openshift-marketplace` -- if `LAST OBSERVED` is stale, OLM can't
   resolve new operator versions. Self-healing is broken.
2. **olm.maxOpenShiftVersion ceiling:** After OCP upgrade, check if the
   cluster's OCP version exceeds the operator bundle's ceiling annotation.
   CSV stays in Replacing/Pending state. See `version-constraints.yaml`.
3. **Corrupted CSV with bad OPERAND_IMAGE refs:** The MCH operator CSV
   contains 40+ image references as `OPERAND_IMAGE_*` env vars. A
   corrupted CSV propagates bad image refs to all managed component
   deployments. Multiple unrelated pods with ImagePullBackOff
   simultaneously is a signal to check the CSV -- one root cause at
   Layer 5 explains all the Layer 1 symptoms.

```
# Check CatalogSource health
oc get catsrc -n openshift-marketplace -o jsonpath='{range .items[*]}{.metadata.name}: {.status.connectionState.lastObservedState}{"\n"}{end}'

# Check CSV phase
oc get csv -n <acm-ns> -o jsonpath='{range .items[*]}{.metadata.name}: {.status.phase}{"\n"}{end}'

# Check max OCP version ceiling
oc get csv -n <acm-ns> -o jsonpath='{.items[0].metadata.annotations.olm\.maxOpenShiftVersion}'

# Check OPERAND_IMAGE env vars
oc get csv -n <acm-ns> -o yaml | grep OPERAND_IMAGE | head -5
```

**Knowledge:** acm-platform.md, per-subsystem architecture files,
version-constraints.yaml

---

### Layer 6: Authentication / Identity

**When relevant:** External identity is involved (OAuth, IDP, mounted
kubeconfig) or certificates have expired. Skip if only ServiceAccount-
based auth (auto-managed by Kubernetes).

**What breaks:** Certificate expired (401 Unauthorized), IDP not
configured, ServiceAccount token not mounted, OAuth server down.

```
Check: oc get oauth cluster -o jsonpath='{range .spec.identityProviders[*]}{.name} ({.type}){"\n"}{end}'
       oc get csr | grep Pending
       oc get secret -n <acm-ns> -o json | jq -r '.items[] | select(.type=="kubernetes.io/tls") | .metadata.name'
       oc login -u <test-user> -p <password> --insecure-skip-tls-verify (if applicable)
Healthy: IDPs configured, no pending CSRs, certs valid, non-admin login works
Broken:  IDP unreachable, certs expired, SA tokens missing
Signal:  Admin works but non-admin fails? This is Layer 6, not Layer 12.
Skip:    If test uses admin user or ServiceAccount-based auth (auto-managed).
```

**Multi-hop token forwarding:** For features accessed through the OCP
Console, the user's OAuth token is forwarded across multiple hops:
```
Browser -> OCP Ingress Router (HAProxy) -> OCP Console Pod
  -> ConsolePlugin proxy -> plugin backend (console-api)
    -> target service (search-api, grc-propagator, etc.)
```
A 401/403 at any hop breaks the chain. When diagnosing auth failures
for console-proxied features, check logs at each hop to identify WHERE
the token is rejected. This applies to ALL features accessed through
the console UI (search, governance, applications, observability,
fleet virtualization). The ConsolePlugin proxy must have
`authorization: UserToken` configured, and the console backend's
`getAuthenticatedToken()` must succeed at each proxy stage.

**Diagnostic traps:** Trap 12 (TLS cert corrupted -- service-ca
doesn't auto-repair existing secrets).

**Knowledge:** rbac/architecture.md, certificate-inventory.yaml

---

### Layer 7: Authorization / RBAC

**When relevant:** Users see some resources but not others, buttons
disabled when they should be enabled, or fine-grained RBAC enabled.

**What breaks:** ClusterRoleBinding missing after upgrade, RBAC
aggregation incomplete, ClusterPermission in wrong namespace, SCC too
restrictive.

```
Check: oc auth can-i <verb> <resource> --as=<user>
       oc get clusterrolebinding | grep <role>
       oc get clusterpermissions -A
       oc get managedclusterroleassignments -A
Healthy: ServiceAccounts have required permissions, RBAC bindings correct
Broken:  Binding missing, aggregation incomplete, SCC too restrictive
Signal:  User sees some resources but not others? Button disabled?
Skip:    If test uses cluster-admin.
```

**Knowledge:** rbac/architecture.md, rbac/data-flow.md,
rbac/known-issues.md, rbac/failure-signatures.md

---

### Layer 8: API / CRD / Webhook

**When relevant:** Resource creation/updates are being rejected or
modified unexpectedly. If the failure is a timeout or empty data, more
likely Layer 3 (network) or Layer 11 (data flow).

**What breaks:** CRD missing (404), validating webhook down with
failurePolicy: Fail (blocks ALL resource creation), APIService
unavailable (entire API group returns 503).

```
Check: oc api-resources | grep <resource>
       oc get validatingwebhookconfigurations | wc -l
       oc get mutatingwebhookconfigurations | wc -l
       oc get apiservices | grep -v Local | grep "open-cluster-management\|hive"
Healthy: All CRDs present, webhooks responsive, APIServices available
Broken:  CRD missing, webhook down (failurePolicy: Fail), APIService 503
Signal:  "admission webhook denied"? Resource creation rejected? Layer 8.
Skip:    If failure is timeout or empty data (more likely Layer 3 or 11).
```

**Diagnostic traps:** Trap 10 (Hive webhook blocks ALL cluster
operations when hiveadmission is down).

**Knowledge:** webhook-registry.yaml, kubernetes-fundamentals.md

---

### Layer 9: Operator / Reconciliation

**What breaks:** Operator scaled to 0 (status fields freeze -- Trap 1),
CrashLoopBackOff (nil pointer, missing config, OOM), reconciliation
hot-loop, informer cache sync failure.

```
Check: oc get deploy multiclusterhub-operator -n <acm-ns>
       oc get deploy multicluster-engine-operator -n multicluster-engine
       oc get pods -n <acm-ns> --field-selector=status.phase!=Running,status.phase!=Succeeded
       oc get pods -n multicluster-engine --field-selector=status.phase!=Running,status.phase!=Succeeded
       oc get pods -n open-cluster-management-hub --field-selector=status.phase!=Running,status.phase!=Succeeded
       oc get pods -n hive --no-headers
       oc get statefulset -n hive --no-headers
       oc get statefulset -n open-cluster-management-observability --no-headers 2>/dev/null
       oc logs -n <acm-ns> -l name=multiclusterhub-operator --tail=50
Healthy: Operator replicas match desired, reconciling normally
Broken:  0 replicas (CRITICAL -- Trap 1), CrashLoopBackOff, hot-loop
Signal:  MCH says "Running" but things break? Check operator replicas.
         Also check leader election Lease -- pods may be Running but not
         reconciling (Trap 1b).
```

**CRITICAL:** If MCH operator is at 0 replicas, MCH CR status
"Running" is STALE. All ACM components are unmanaged and will not
recover from failures. This takes priority over all other findings.

**Sub-operator CR status:** Many ACM subsystems use an intermediate
Custom Resource between the top-level MCH/MCE status and individual
pods. These CRs report subsystem-level health:
```
# Search CR conditions
oc get search -n <acm-ns> -o jsonpath='{range .items[0].status.conditions[*]}{.type}: {.status} ({.message}){"\n"}{end}'

# HiveConfig status
oc get hiveconfig hive -o jsonpath='{.status.conditions}'

# MultiClusterObservability CR conditions
oc get multiclusterobservability observability -o jsonpath='{.status.conditions}'
```
When MCH says "Running" but a subsystem is broken, check its
intermediate CR before diving into individual pod logs. The general
pattern is: operator -> intermediate CR -> component deployments.

**Deployment scheduling investigation:** When a deployment has 0
available replicas, check scheduling BEFORE checking container logs --
if the pod never started, there are no logs:
```
oc describe deploy <name> -n <ns> | grep -A5 'Conditions\|Events'
oc get events -n <ns> --sort-by=.lastTimestamp --field-selector involvedObject.kind=Pod | tail -10
oc get events -n <ns> --sort-by=.lastTimestamp | grep -E "Unschedulable|FailedCreate|FailedScheduling"
```
Common findings: `Unschedulable` (Layer 1: node resources, taints),
`FailedCreate` (Layer 3: ResourceQuota), `FailedScheduling` (Layer 1:
affinity/anti-affinity). Do not check container logs when the
container never started.

**StatefulSets alongside Deployments:** Some namespaces have both.
The `hive` namespace has Deployments (hive-controllers, hiveadmission)
AND StatefulSets (hive-clustersync, hive-machinepool). Observability
uses StatefulSets for thanos-receive, thanos-store, compactor, rule,
and alertmanager. Always check `oc get statefulset` in addition to
Deployments for these namespaces. `oc get deploy` misses these
entirely -- always check StatefulSets too. If hive-clustersync is
down, SyncSets won't be applied to provisioned clusters, but
`oc get deploy -n hive` would show "all healthy."

**Leader election stuck (Trap 1b):** Both operator replicas may be
Running/Ready, health probes pass, but reconciliation has stopped
because the leader election Lease expired (often due to etcd latency
at Layer 2). Check:
```
oc get lease -n <acm-ns> | grep <operator>
oc get lease <lease-name> -n <acm-ns> -o jsonpath='{.spec.renewTime}'
```
A stale `renewTime` (not renewed in the last few minutes) means no
replica holds the leader lock -- reconciliation has stopped despite
healthy-looking pods. Applies to all HA operators: MCH operator (2
replicas), MCE operator (2), grc-policy-propagator (2), cluster-manager
(3), cluster-curator-controller (2).

**Diagnostic traps:** Trap 1 (stale MCH/MCE status when operator not
running), Trap 7 (ALL addons Unavailable -- check addon-manager first),
Trap 14 (both operator replicas Running but leader election stuck).

**Knowledge:** acm-platform.md, healthy-baseline.yaml, components.yaml,
per-subsystem architecture files

---

### Layer 10: Cross-Cluster / Hub-Spoke

**When relevant:** Issue involves managed clusters or spoke-delivered
data. Hub-only features (credential management, cluster creation wizard,
MCH configuration) work without cross-cluster involvement. Skip if the
issue is purely hub-local.

**What breaks:** Klusterlet disconnected (firewall, proxy, cert expiry),
ManifestWork not delivered, lease renewal failure, addon not deployed.

```
Check: oc get managedclusters
       oc get lease -n <cluster-ns> --sort-by=.spec.renewTime
       oc get managedclusteraddons -A
Healthy: All managed clusters Available, addons deployed, leases fresh
Broken:  Cluster NotReady, ManifestWork stuck, addon Unavailable
Signal:  ALL addons Unavailable on ALL clusters? -> check addon-manager
         at Layer 9 (Trap 7), NOT individual addons.
Skip:    If test is hub-only (no managed clusters involved).
```

**Diagnostic traps:** Trap 6 (ManagedCluster NotReady -- check lease
and conditions, not klusterlet), Trap 7 (mass addon failure --
addon-manager single point of failure).

**Knowledge:** addon-catalog.yaml, dependency-chains.yaml,
cluster-lifecycle/architecture.md, cluster-lifecycle/health-patterns.md,
foundation/

---

### Layer 11: Data Flow / Content Integrity

**When relevant:** Pods are Running, network is fine, operators are
reconciling, but the data is WRONG. This is where product bugs (code
logic errors) live -- hardest to detect because everything looks healthy.

**What breaks:** Search results show wrong count, fields swapped,
application health status inverted, SSE events dropped, policy
compliance status wrong, CSV export incomplete.

```
Check: oc exec deploy/search-postgres -n <acm-ns> -- \
         psql -U searchuser -d search -c "SELECT count(*) FROM search.resources"
       Compare API response vs expected values / vs what UI shows
       Compare data counts against fleet size (~200 resources per cluster)
       oc exec deploy/console-chart-console-v2 -- curl -s http://localhost:3000/api/hub -k
Healthy: Data counts match expected, API responses correct
Broken:  Wrong count, fields swapped, stale cache, data transformation bug
Signal:  Everything looks healthy but data is WRONG -> Layer 11.
         This is where product bugs (code logic errors) live.
```

**Knowledge:** per-subsystem data-flow.md files (8 subsystems have these)

---

### Layer 12: UI / Plugin / Rendering

**When relevant:** ALL lower layers are healthy and data is correct,
but the rendering or user-facing behavior is wrong.

**What breaks:** ConsolePlugin not registered (tabs missing), plugin
backend pod unhealthy (tabs present but broken), PatternFly regression,
React error boundary.

```
Check: oc get consoleplugins
       oc get pods -n <acm-ns> | grep console
       oc get pods -n multicluster-engine | grep console
       oc get deploy console-chart-console-v2 -n <acm-ns> \
         -o jsonpath='{.spec.template.spec.containers[0].image}'
       ACM Source MCP: search_code("<failing-selector>")
Healthy: Plugins registered, console pods Running, images match baseline,
         selectors exist in product source
Broken:  Plugin not registered, backend pod down, tampered image,
         PatternFly regression, React error boundary
Signal:  Tabs missing entirely -> Trap 2 (console-mce pod or ConsolePlugin CRDs)
         Tabs present but broken -> Trap 13 (plugin backend pod health)
         Selector not in product source? Could be Layer 12 (stale test selector).
         But verify the feature backend isn't down first (Layer 9/11).
```

**Diagnostic traps:** Trap 2 (console pod healthy, tabs missing --
check console-mce), Trap 8 (multiple console pages broken -- check
search-api first), Trap 13 (tabs present but render errors -- plugin
backend unhealthy).

**Knowledge:** console/architecture.md, console/known-issues.md,
console/failure-signatures.md, selectors.yaml,
healthy-baseline.yaml (image patterns)

---

## Layers and Diagnostic Traps

Each trap in `diagnostic-traps.md` maps to a layer where the
obvious diagnosis is wrong:

| Trap | Symptom | Obvious (wrong) layer | Actual layer |
|------|---------|----------------------|--------------|
| 1 | MCH says Running | OK (no issue) | Layer 9 (operator at 0 replicas) |
| 2 | Console pod healthy, tabs missing | Layer 12 | Layer 9/12 (console-mce pod) |
| 3 | Search all green, empty results | Layer 9 (pods fine) | Layer 4 (emptyDir data loss) |
| 4 | Observability dashboards empty | Layer 9 (operator) | Layer 4 (S3 storage) |
| 5 | GRC non-compliant after upgrade | Layer 9 (operator) | Normal settling (wait) |
| 6 | ManagedCluster NotReady | Layer 10 (klusterlet) | Layer 3/6 (network/auth) |
| 7 | ALL addons Unavailable | Layer 10 (per-addon) | Layer 9 (addon-manager) |
| 8 | Multiple console pages broken | Layer 12 (console UI) | Layer 9 (search-api) |
| 9 | Pods gradually disappearing | Layer 9 (per-pod) | Layer 3 (ResourceQuota) |
| 10 | ALL cluster ops fail | Layer 9 (Hive operator) | Layer 8 (Hive webhook) |
| 11 | Pods Running, cross-service fails | Layer 9 (per-service) | Layer 3 (NetworkPolicy) |
| 12 | TLS errors, service-ca healthy | Layer 9 (service-ca) | Layer 6 (corrupted secret) |
| 13 | Feature tabs present but broken | Layer 12 (UI rendering) | Layer 9 (plugin backend) |
| 14 | Both replicas Running, nothing reconciling | OK (pods healthy) | Layer 9 (leader election stuck) |

## Using Layers with Dependency Chains

The 12 dependency chains in `dependency-chains.md` trace HORIZONTALLY
within and across subsystems. The layer model traces VERTICALLY through
infrastructure layers. Use both:

- **Horizontal:** "console depends on search which depends on postgres"
- **Vertical:** "but WHY is postgres not responding? Layer 3: NetworkPolicy"

When a dependency chain shows a broken link, use the layer model to
determine WHY that link is broken. Each chain has a "Layers spanned"
annotation showing which layers it crosses.

### Vertical Tracing Procedure (Hub Health Phase 5)

When multiple issues are found across different subsystems:

1. List each finding with its layer number
2. Identify the LOWEST affected layer across all findings
3. Check: does a single issue at that layer explain all higher findings?
   - Yes -> that's the root cause; higher findings are symptoms
   - No -> there are multiple independent root causes
4. For each potential root cause, verify with evidence-tiers.md rules
5. Trace resource ownership to confirm the causal chain:
   `oc get <resource> -n <ns> -o jsonpath='{.metadata.ownerReferences}'`
   Owner references confirm which controller created the resource.
   If multiple unhealthy resources share a common owner, investigate
   that owner rather than each resource individually. This works for
   any Kubernetes resource and is especially useful when the component
   is not covered by curated dependency chains. See
   `cluster-introspection.md` source #1 for the full technique.

Example: Search shows empty results (Layer 11 symptom), AND GRC shows
stale compliance (Layer 11 symptom). Instead of investigating each
independently, check Layer 3 first -> NetworkPolicy blocking traffic
in ACM namespace -> one root cause explains both symptoms.

## Classification After Root Cause Found

The root cause layer does NOT directly determine the classification.
You must investigate WHO created/caused the broken resource:

| Root cause scenario | Classification |
|---|---|
| Product operator created a broken resource | PRODUCT_BUG |
| Product code has a logic error (wrong data, wrong rendering) | PRODUCT_BUG |
| Operator crashes from code bug (nil pointer, panic) | PRODUCT_BUG |
| Webhook created by product rejects valid requests | PRODUCT_BUG |
| External action broke infrastructure (NetworkPolicy, quota, scaling) | INFRASTRUCTURE |
| Environment not configured for test (IDP missing, spoke down) | INFRASTRUCTURE |
| Compute/storage/network infrastructure issue | INFRASTRUCTURE |
| Operator scaled to 0 by external action | INFRASTRUCTURE |
| Test selector stale (product renamed, test not updated) | AUTOMATION_BUG |
| Test assertion wrong (expects old behavior) | AUTOMATION_BUG |
| Test setup incomplete (missing credentials, wrong parameters) | AUTOMATION_BUG |
| Feature intentionally disabled or post-upgrade settling | NO_BUG |
| After-all hook cascading from prior failure | NO_BUG |

## Layer Discrepancy Detection

During the layer-by-layer investigation, when you verify a lower layer
is healthy but the higher layer shows a problem, record this as a
`layer_discrepancy` evidence source. This is Tier 1 evidence for
PRODUCT_BUG because the lower layer is verified by oc commands (factual),
the higher layer is observed in the test failure (factual), and the
discrepancy proves the product code at the higher layer is wrong.

| Lower Layer says | Higher Layer shows | Classification |
|---|---|---|
| L7: User HAS permission (`oc auth can-i` = yes) | L12: Button disabled | PRODUCT_BUG (UI permission logic) |
| L11: Backend returns correct data | L12: UI shows wrong data | PRODUCT_BUG (rendering bug) |
| L9: Operator healthy, reconciling | L11: Data not flowing | PRODUCT_BUG (data pipeline bug) |
| L3: Network OK, endpoints reachable | L11: Service returns empty | PRODUCT_BUG (service logic bug) |
| L6: Auth working, token valid | L12: Login redirect fails | PRODUCT_BUG (auth flow bug) |

Record in evidence_sources as:
```json
{
  "source": "layer_discrepancy",
  "finding": "Layer 7 (oc auth can-i) confirms permission, Layer 12 shows button disabled",
  "tier": 1,
  "lower_layer": 7,
  "higher_layer": 12
}
```

A layer discrepancy OVERRIDES subsystem health status. Even if
cluster-diagnosis.json says the subsystem is healthy, a discrepancy
between verified layers proves a product code defect exists.

## Counterfactual Verification Templates (v3.9)

When a cluster-wide issue is found (tampered image, NetworkPolicy, operator
down, ResourceQuota, degraded operator), apply these templates to verify
whether each individual test is actually affected.

The key question: **"Would this test PASS if the cluster-wide issue were fixed?"**

### Template 1: Selector Not Found + Cluster-Wide Issue

```
Check:  ACM Source MCP search_code("<selector>")
If selector NOT FOUND in official console -> AUTOMATION_BUG (dead selector)
If selector FOUND in official but not in tampered -> INFRASTRUCTURE
The cluster-wide issue matters ONLY if the selector exists in the official
source but was removed/broken by the issue.
```

### Template 2: Button Disabled + Cluster-Wide Issue

```
Check:  oc auth can-i <verb> <resource> --as=<test-user>
If backend GRANTS permission but UI shows disabled -> PRODUCT_BUG
  (UI does not reflect backend RBAC state -- console code issue)
If backend DENIES permission -> check if denial is from cluster-wide
  issue or from correct RBAC configuration
Fallback (kubeconfig expired): check test role against RBAC architecture
  in architecture/rbac/
```

### Template 3: Timeout + Cluster-Wide Issue

```
Check:  oc get deploy <component> -n <ns> (is the backend healthy?)
        oc logs <component-pod> --tail=50 (any errors?)
        ACM Source MCP search_code("<selector>") (does element exist?)
If component healthy AND selector exists -> AUTOMATION_BUG (timing issue)
If component unhealthy -> verify THIS test depends on that component
If selector doesn't exist -> AUTOMATION_BUG regardless of component health
```

### Template 4: Data Assertion + Cluster-Wide Issue

```
Check:  oc get <resource> or oc exec curl to API endpoint
        Compare API response vs test's expected value
If API returns correct data but UI shows wrong -> PRODUCT_BUG (transformation)
If API returns wrong data -> trace upstream through data flow layers (11->9->3)
If API returns empty data -> check Layer 4 (storage) and Layer 9 (operator)
```

### Template 5: Blank Page + Cluster-Wide Issue

```
Check:  console-api pod health, auth redirect chain, navigation URL
If console-api healthy + auth working + URL correct -> AUTOMATION_BUG
If console-api unhealthy -> INFRASTRUCTURE (but verify console-api is
  affected by the specific cluster-wide issue)
If auth redirect fails -> Layer 6 issue, may or may not be cluster-wide
```

### Template 6: CSS visibility:hidden + Cluster-Wide Issue

```
Check:  Is this standard PatternFly 6 behavior?
  PF6 menus, dropdowns, and popovers use visibility:hidden until
  triggered. This is by design, not caused by tampered images.
  If the element uses PF6 transition classes (pf-v6-*, pf-m-expanded,
  etc.) -> AUTOMATION_BUG (test needs cy.waitForVisible or
  .should('be.visible') with appropriate wait)
If NOT PF6 standard behavior -> investigate further
```

## Layer Quick-Reference Card

```
Layer  Check                         Key Command
-----  ----------------------------- -----------------------------
  1    Nodes Ready? Pods schedule?   oc get nodes
  2    API server + etcd healthy?    oc get co etcd
  3    NetworkPolicy? DNS? Service?  oc get netpol -n <ns>
  4    PVCs Bound? Disk space?       oc get pvc -n <ns>
  5    MCH toggles? ConfigMaps?      oc get mch -o yaml
  6    Certs valid? IDP working?     oc get oauth cluster
  7    RBAC bindings correct?        oc auth can-i <verb> <res>
  8    CRDs exist? Webhooks up?      oc get crd | wc -l
  9    Operators reconciling?        oc get deploy <op> -n <ns>
 10    Clusters Available? Addons?   oc get managedclusters
 11    Data correct? Counts right?   psql SELECT count(*)
 12    Plugins registered? UI ok?    oc get consoleplugins
```
