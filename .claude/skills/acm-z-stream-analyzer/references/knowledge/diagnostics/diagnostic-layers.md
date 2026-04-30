# 12-Layer Diagnostic Model

Investigation methodology for finding the root cause of test failures.
Trace from the symptom downward through infrastructure layers until you
find the broken layer. Then investigate WHO caused it and WHY.

Reference: DIAGNOSTIC-LAYER-ARCHITECTURE.md (validated against ACM 2.16 GA
on Azure and ACM 2.17 bugged cluster on AWS with 5 injected issues).

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
UI issue (Layer 12). The diagnostic challenge is tracing downward.

Layers are failure domains to check or eliminate, NOT mandatory steps
in every investigation. If a layer doesn't apply, skip it.

## Investigation Workflow

### Step B0: Map Symptom to Starting Layer

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

### Step B1: Check cluster-diagnosis.json First

Before running oc commands, cross-reference the test's feature area
against pre-computed health data:

- Read `cluster-diagnosis.json` for this test's feature area
- Check subsystem_health, operator_health, and classification_guidance
- Is the relevant subsystem OK, DEGRADED, or CRITICAL?
- Are there `infrastructure_issues` affecting this feature?
- Check `health_depth` — does it cover only pod-level or deeper?

If cluster-diagnosis shows CRITICAL issues in this feature area:
  Strong INFRASTRUCTURE signal, but STILL verify the connection
  between the infrastructure issue and THIS test's specific error.

If cluster-health shows all layers OK for this feature area:
  Root cause is likely Layer 11 (data) or Layer 12 (UI/test).

If cluster-diagnosis.json has `pre_classified_infrastructure` for
this feature area: use as Tier 1 evidence. Do NOT re-run the same
oc commands Stage 1.5 already ran.

### Step B2: Trace Downward (if needed)

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

### Step B3: Investigate WHO/WHY at Root Cause Layer

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
   - ACM-UI MCP: search_code("<component>") for intended behavior
   - JIRA MCP: search_issues() for related bugs
   - Knowledge DB: read failure-signatures.md for known patterns

## Per-Layer Reference

### Layer 1: Compute / Scheduling
```
Check: oc get nodes
       oc adm top nodes
       oc get pods -n <ns> --field-selector=status.phase!=Running,status.phase!=Succeeded
Healthy: All nodes Ready, no resource pressure, pods scheduling
Broken: Node NotReady, OOMKilled (exit 137), Evicted, ImagePullBackOff, Pending
Knowledge: kubernetes-fundamentals.md, healthy-baseline.yaml
```

### Layer 2: Control Plane / State Store
```
Check: oc get co etcd kube-apiserver kube-scheduler
       oc get pods -n openshift-etcd --no-headers | grep -v guard
Healthy: All control plane operators Available, API responsive
Broken: etcd slow/leader stuck, API server overloaded, scheduler not scheduling
Signal: Multiple unrelated operators fail simultaneously? Suspect Layer 2.
Knowledge: kubernetes-fundamentals.md
```

### Layer 3: Network / Connectivity
```
Check: oc get networkpolicy -n <acm-ns> --no-headers
       oc get endpoints -n <acm-ns> <service-name>
       oc get svc -n <acm-ns> -o wide
       oc exec deploy/<pod-a> -- curl http://<service-b>:<port> --connect-timeout 3
       oc get resourcequota -n <acm-ns>
Healthy: No NetworkPolicies in ACM namespaces, all Services have ready endpoints
Broken: NetworkPolicy blocking traffic, service has no endpoints, DNS failure
IMPORTANT: ACM does NOT create NetworkPolicies. Any found in ACM namespaces is suspicious.
Knowledge: infrastructure/failure-signatures.md, service-map.yaml, subsystem architecture files
```

**Service endpoint verification:** A Service with zero ready endpoints is
a silent failure — the Service object exists, the pod may be Running, but
no traffic reaches it because the selector doesn't match any Ready pods.
This happens after label changes during upgrades, when readiness probes
fail, or when pods restart and haven't passed readiness yet. Check:
```
oc get endpoints -n <acm-ns> <service-name>
# If ENDPOINTS column shows <none>, no traffic can reach the backing pods
```
Cross-reference `knowledge/service-map.yaml` for which components depend
on each Service and what breaks when endpoints are missing.

### Layer 4: Storage / Data Persistence
```
Check: oc get pvc -n <acm-ns>
       oc get pvc -n open-cluster-management-observability
       oc exec deploy/search-postgres -- psql -U searchuser -d search -c "SELECT count(*) FROM search.resources"
Healthy: All PVCs Bound, search-postgres has data, S3 credentials valid
Broken: PVC Pending, disk full, emptyDir data lost on restart, S3 expired
Signal: search-postgres recently restarted? emptyDir data loss (Trap 3).
Knowledge: search/architecture.md, observability/failure-signatures.md
```

**Storage model reference:** Determine the storage model BEFORE checking
PVCs. Different components use different storage and need different checks:

| Component | Storage Model | Layer 4 Concern |
|-----------|--------------|-----------------|
| search-postgres | emptyDir | Pod restart = total data loss. Check pod age + row count |
| observability (thanos-*) | PVC (StatefulSet) | PVC bound? Disk full? S3 credentials valid? |
| search-api, console, grc | stateless | No Layer 4 concern — skip for these |
| hive-clustersync | emptyDir | Pod restart = sync state lost, re-sync needed |

For emptyDir components, the diagnostic question is "did the pod restart
recently?" not "is the PVC bound?" For stateless components, skip Layer 4.

### Layer 5: Configuration / Desired State
```
Check: oc get mch -n <acm-ns> -o jsonpath='{range .spec.overrides.components[*]}{.name}={.enabled}{"\n"}{end}'
       oc get sub -A | grep -E "acm|mce|multicluster"
       oc get catsrc -n openshift-marketplace
       oc get installplan -n <acm-ns>
       oc get csv -n <acm-ns>
Healthy: All MCH components enabled, correct OLM subscriptions, CSVs Succeeded
Broken: Component disabled (silently absent), wrong subscription channel
Signal: Feature completely absent (no pods, no CRDs, no errors)? Check Layer 5 first.
Knowledge: acm-platform.md, subsystem architecture files, version-constraints.yaml
```

**OLM foundational health:** OLM is the foundation for all operator
installations. Three failure scenarios are invisible to basic pod checks:

1. **CatalogSource with stale gRPC connection:** `oc get catsrc -n
   openshift-marketplace` — if `LAST OBSERVED` is stale, OLM can't
   resolve new operator versions. Self-healing is broken.
2. **olm.maxOpenShiftVersion ceiling:** After OCP upgrade, check if the
   cluster's OCP version exceeds the operator bundle's ceiling annotation.
   CSV stays in Replacing/Pending state. See `version-constraints.yaml`.
3. **Corrupted CSV with bad OPERAND_IMAGE refs:** The MCH operator CSV
   contains 40+ image references as `OPERAND_IMAGE_*` env vars. A
   corrupted CSV propagates bad image refs to all managed component
   deployments. Multiple unrelated pods with ImagePullBackOff
   simultaneously is a signal to check the CSV — one root cause at
   Layer 5 explains all the Layer 1 symptoms.

```
# Check CatalogSource health
oc get catsrc -n openshift-marketplace -o jsonpath='{range .items[*]}{.metadata.name}: {.status.connectionState.lastObservedState}{"\n"}{end}'

# Check CSV phase
oc get csv -n <acm-ns> -o jsonpath='{range .items[*]}{.metadata.name}: {.status.phase}{"\n"}{end}'
```

### Layer 6: Authentication / Identity
```
Check: oc get oauth cluster -o jsonpath='{range .spec.identityProviders[*]}{.name} ({.type}){"\n"}{end}'
       oc login -u <test-user> -p <password> --insecure-skip-tls-verify (if applicable)
       oc get csr | grep Pending
Healthy: IDPs configured, non-admin login works, no pending CSRs
Broken: IDP not configured, certificate expired, ServiceAccount token not mounted
Signal: Admin works but non-admin fails? This is Layer 6, not Layer 12.
Skip: If test uses admin user or ServiceAccount-based auth (auto-managed).
Knowledge: rbac/architecture.md
```

**Multi-hop token forwarding:** Console-proxied features involve a 5-hop
token forwarding chain:
```
Browser → OCP Ingress Router (HAProxy) → OCP Console Pod
  → ConsolePlugin proxy → plugin backend (console-api)
    → target service (search-api, grc-propagator, etc.)
```
When a user gets 403 on a console-proxied feature (search, governance,
applications, Fleet Virt, observability dashboards), the token may have
been dropped at any hop. Check logs at each hop before concluding the
issue is Layer 7 (RBAC). The ConsolePlugin proxy must have
`authorization: UserToken` configured, and the console backend's
`getAuthenticatedToken()` must succeed at each proxy stage.

### Layer 7: Authorization / RBAC
```
Check: oc auth can-i <verb> <resource> --as=<user>
       oc get clusterrolebinding | grep <role>
       oc get clusterpermissions -A
Healthy: ServiceAccount has required permissions, RBAC bindings correct
Broken: ClusterRoleBinding missing, RBAC aggregation incomplete, SCC too restrictive
Signal: User sees some resources but not others? Button disabled? Check Layer 7.
Skip: If test uses cluster-admin.
Knowledge: rbac/architecture.md, rbac/data-flow.md, rbac/failure-signatures.md
```

### Layer 8: API / CRD / Webhook
```
Check: oc api-resources | grep <resource>
       oc get validatingwebhookconfigurations | wc -l
       oc get apiservices | grep -v Local | grep "open-cluster-management\|hive"
Healthy: All CRDs present, webhooks responsive, APIServices available
Broken: CRD missing, webhook down with failurePolicy:Fail, APIService 503
Signal: Resource creation rejected? "admission webhook denied"? This is Layer 8.
Skip: If failure is timeout or empty data (more likely Layer 3 or 11).
Knowledge: webhook-registry.yaml, kubernetes-fundamentals.md
```

### Layer 9: Operator / Reconciliation
```
Check: oc get deploy <operator> -n <ns>
       oc get statefulset -n hive
       oc get statefulset -n open-cluster-management-observability
       oc logs -n <ns> -l name=<operator> --tail=50
       oc logs -n <ns> <pod> --previous (if CrashLoopBackOff)
Healthy: Operator replicas match desired, reconciling normally
Broken: 0 replicas (Trap 1 -- status is stale!), CrashLoopBackOff, hot-loop
Signal: MCH says "Running" but things break? Check if MCH operator is at 0 replicas.
       Also check leader election Lease -- pods may be Running but not reconciling (Trap 1b).
Knowledge: acm-platform.md, components.yaml, per-subsystem architecture.md
```

**Sub-operator CR status checks:** ACM uses a recursive operator pattern.
When MCH says "Running" but a subsystem is broken, check the intermediate
CR to bridge the gap between MCH status (too coarse) and pod logs (too
granular):
```
# Search CR conditions
oc get search -n <acm-ns> -o jsonpath='{range .items[0].status.conditions[*]}{.type}: {.status} ({.message}){"\n"}{end}'

# HiveConfig status
oc get hiveconfig hive -o jsonpath='{.status.conditions}'

# MultiClusterObservability CR conditions
oc get multiclusterobservability observability -o jsonpath='{.status.conditions}'
```

**Deployment scheduling investigation:** When a deployment has 0
available replicas, check scheduling BEFORE checking container logs —
if the pod never started, there are no logs:
```
oc describe deploy <name> -n <ns> | grep -A5 Conditions
oc get events -n <ns> --sort-by=.lastTimestamp | grep -E "Unschedulable|FailedCreate|FailedScheduling"
```
Root cause is often Layer 1 (compute) or Layer 3 (ResourceQuota).

**StatefulSet awareness:** The hive namespace has 2 StatefulSets
(hive-clustersync, hive-machinepool) and the observability namespace
has 5+ (thanos-receive, thanos-store, compactor, rule, alertmanager).
`oc get deploy` misses these entirely — always check StatefulSets too.
If hive-clustersync is down, SyncSets won't be applied to provisioned
clusters, but `oc get deploy -n hive` would show "all healthy."

**Leader election stuck (Trap 1b):** Both operator replicas may be
Running/Ready, health probes pass, but reconciliation has stopped
because the leader election Lease expired (often due to etcd latency
at Layer 2). Check:
```
oc get lease -n <acm-ns> | grep <operator>
oc get lease <lease-name> -n <acm-ns> -o jsonpath='{.spec.renewTime}'
```
A stale `renewTime` (not renewed in the last few minutes) means no
replica holds the leader lock — reconciliation has stopped despite
healthy-looking pods. Applies to all HA operators: MCH operator (2
replicas), MCE operator (2), grc-policy-propagator (2), cluster-manager
(3).

### Layer 10: Cross-Cluster / Hub-Spoke
```
Check: oc get managedclusters
       oc get lease -n <cluster-ns> --sort-by=.spec.renewTime
       oc get managedclusteraddons -n <cluster-ns>
Healthy: All managed clusters Available, addons deployed, leases fresh
Broken: Cluster NotReady, ManifestWork not delivered, addon Unavailable
Signal: ALL addons Unavailable on ALL clusters? Check addon-manager at Layer 9 first.
Skip: If test is hub-only (no managed clusters involved).
Knowledge: addon-catalog.yaml, dependencies.yaml, cluster-lifecycle/, foundation/
```

### Layer 11: Data Flow / Content Integrity
```
Check: Compare API response vs what UI shows
       oc exec deploy/search-postgres -- psql -c "SELECT count(*) FROM search.resources"
       oc exec deploy/console-chart-console-v2 -- curl -s http://localhost:3000/api/hub -k
Healthy: Data counts match expected, API responses correct
Broken: Wrong count, fields swapped, stale cache, data transformation bug
Signal: Everything looks healthy (pods Running, network fine) but data is WRONG.
This is where product bugs (code logic errors) live.
Knowledge: per-subsystem data-flow.md files (8 subsystems have these)
```

### Layer 12: UI / Plugin / Rendering
```
Check: oc get consoleplugins
       oc get pods -n <acm-ns> | grep console
       ACM-UI MCP: search_code("<failing-selector>")
Healthy: Plugins registered, console pods Running, selectors in product source
Broken: Plugin not registered, PatternFly regression, React error boundary
Signal: Selector not in product source? Could be Layer 12 (stale test selector).
        But verify the feature backend isn't down first (Layer 9/11).
Knowledge: console/architecture.md, selectors.yaml, console/failure-signatures.md
```

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

## Layer Quick-Reference Card

```
Layer  Check                         Key Command
─────  ───────────────────────────── ─────────────────────────────
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

---

## Counterfactual Verification Templates (v3.9)

When a cluster-wide issue is found (tampered image, NetworkPolicy, operator
down, ResourceQuota, degraded operator), apply these templates to verify
whether each individual test is actually affected.

The key question: **"Would this test PASS if the cluster-wide issue were fixed?"**

### Template 1: Selector Not Found + Cluster-Wide Issue

```
Check:  ACM-UI MCP search_code("<selector>")
If selector NOT FOUND in official console → AUTOMATION_BUG (dead selector)
If selector FOUND in official but not in tampered → INFRASTRUCTURE
The cluster-wide issue matters ONLY if the selector exists in the official
source but was removed/broken by the issue.
```

### Template 2: Button Disabled + Cluster-Wide Issue

```
Check:  oc auth can-i <verb> <resource> --as=<test-user>
If backend GRANTS permission but UI shows disabled → PRODUCT_BUG
  (UI does not reflect backend RBAC state — console code issue)
If backend DENIES permission → check if denial is from cluster-wide
  issue or from correct RBAC configuration
Fallback (kubeconfig expired): check test role against RBAC architecture
  in knowledge/architecture/rbac/
```

### Template 3: Timeout + Cluster-Wide Issue

```
Check:  oc get deploy <component> -n <ns> (is the backend healthy?)
        oc logs <component-pod> --tail=50 (any errors?)
        ACM-UI MCP search_code("<selector>") (does element exist?)
If component healthy AND selector exists → AUTOMATION_BUG (timing issue)
If component unhealthy → verify THIS test depends on that component
If selector doesn't exist → AUTOMATION_BUG regardless of component health
```

### Template 4: Data Assertion + Cluster-Wide Issue

```
Check:  oc get <resource> or oc exec curl to API endpoint
        Compare API response vs test's expected value
If API returns correct data but UI shows wrong → PRODUCT_BUG (transformation)
If API returns wrong data → trace upstream through data flow layers (11→9→3)
If API returns empty data → check Layer 4 (storage) and Layer 9 (operator)
```

### Template 5: Blank Page + Cluster-Wide Issue

```
Check:  console-api pod health, auth redirect chain, navigation URL
If console-api healthy + auth working + URL correct → AUTOMATION_BUG
If console-api unhealthy → INFRASTRUCTURE (but verify console-api is
  affected by the specific cluster-wide issue)
If auth redirect fails → Layer 6 issue, may or may not be cluster-wide
```

### Template 6: CSS visibility:hidden + Cluster-Wide Issue

```
Check:  Is this standard PatternFly 6 behavior?
  PF6 menus, dropdowns, and popovers use visibility:hidden until
  triggered. This is by design, not caused by tampered images.
  If the element uses PF6 transition classes (pf-v6-*, pf-m-expanded,
  etc.) → AUTOMATION_BUG (test needs cy.waitForVisible or
  .should('be.visible') with appropriate wait)
If NOT PF6 standard behavior → investigate further
```
