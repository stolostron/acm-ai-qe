# 12-Layer Diagnostic Model

Systematic investigation framework for finding root causes of cluster
health issues. Each layer is a distinct failure domain. A failure at a
lower layer cascades upward and manifests as symptoms at higher layers.

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

Each layer depends on all layers below it. A network issue (Layer 3)
looks like a data issue (Layer 11) which looks like a UI issue (Layer 12).
The diagnostic challenge is tracing downward to the actual broken layer.

**Layers are failure domains to check or eliminate, NOT mandatory steps.**
Skip layers that don't apply to the current investigation.

## Diagnostic Workflow

### When to Go Bottom-Up vs Top-Down

**Bottom-up (Layers 1→12):** Full health audit (`/deep`). Check
foundational layers first to find root causes before symptoms.

**Top-down (Layers 12→1):** Targeted investigation (`/investigate`).
Start at the symptom layer and trace downward.

**Hybrid approach (recommended for standard checks):**

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIAGNOSTIC WORKFLOW                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: QUICK SWEEP (10 seconds)                              │
│  ├── Layer 1: Nodes Ready? Pods scheduling?                    │
│  ├── Layer 2: API server responding? etcd healthy?             │
│  └── Layer 3: NetworkPolicies in ACM namespaces?               │
│       └── If ANY broken → ROOT CAUSE FOUND (stop here)         │
│                                                                 │
│  Step 2: CHECK BY LAYER (bottom-up for /deep)                  │
│  ├── Layer 4:  Storage accessible? PVCs Bound?                 │
│  ├── Layer 5:  Configuration correct? Components enabled?      │
│  ├── Layer 6:  Auth working? (skip if admin-only)              │
│  ├── Layer 7:  RBAC correct? (skip if admin-only)              │
│  ├── Layer 8:  CRDs exist? Webhooks responsive?                │
│  ├── Layer 9:  Operators reconciling? Replicas correct?        │
│  ├── Layer 10: Managed clusters Available? Addons deployed?    │
│  ├── Layer 11: Data flowing correctly?                         │
│  └── Layer 12: Plugins registered? Console rendering?          │
│       └── At each layer: APPLICABLE? → check. Skip if not.    │
│       └── HEALTHY? → move up. BROKEN? → investigate deeper.   │
│                                                                 │
│  Step 3: CONFIRM ROOT CAUSE                                    │
│  ├── Verify with 2+ evidence sources (evidence-tiers.md)       │
│  ├── Rule out adjacent layers                                  │
│  ├── Check against diagnostic traps (common-diagnostic-traps)  │
│  └── Trace upstream impact (what else does this break?)        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

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
Healthy: No NetworkPolicies in ACM namespaces, pods can reach services
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
identify which components are affected.

**Diagnostic traps:** Trap 9 (ResourceQuota blocks pod restarts),
Trap 11 (NetworkPolicy silently blocks pod communication).

**Knowledge:** infrastructure/architecture.md, infrastructure/known-issues.md,
service-map.yaml

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

**Diagnostic traps:** Trap 3 (search empty but pods green -- emptyDir
data loss), Trap 4 (observability empty -- S3 misconfiguration).

**Knowledge:** search/architecture.md, observability/architecture.md,
healthy-baseline.yaml

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
Healthy: All expected MCH components enabled, correct OLM subscriptions,
         CatalogSources READY, CSVs Succeeded
Broken:  Component disabled (silently absent), wrong subscription channel,
         CatalogSource disconnected, CSV stuck (Pending/Replacing/Failed)
Signal:  Feature completely absent (no pods, no CRDs, no errors)?
         Check Layer 5 -- a disabled component produces zero evidence.
```

**OLM is the foundation for ALL operators.** A CatalogSource with
stale gRPC connectivity prevents OLM from resolving operator updates.
A CSV not in `Succeeded` phase means the operator deployment may be
partially rolled out. OLM also enforces a hard OCP version ceiling
via `olm.maxOpenShiftVersion` -- check this when upgrades fail:
```
oc get csv -n <acm-ns> -o jsonpath='{.items[0].metadata.annotations.olm\.maxOpenShiftVersion}'
```
If this annotation exists and the OCP version exceeds it, OLM blocks
operator upgrade until a newer bundle is published.

**Cross-layer note (L1 symptom, L5 root cause):** If multiple unrelated
pods show ImagePullBackOff simultaneously, check the CSV for corrupted
`OPERAND_IMAGE_*` env vars. The MCH operator CSV contains 40+ image
references. A corrupted CSV propagates bad image refs to all managed
component deployments:
```
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
Healthy: IDPs configured, no pending CSRs, certs valid
Broken:  IDP unreachable, certs expired, SA tokens missing
Signal:  Admin works but non-admin fails? This is Layer 6, not Layer 12.
```

**Multi-hop token forwarding:** For features accessed through the OCP
Console, the user's OAuth token is forwarded across multiple hops:
Browser → OCP Console → ConsolePlugin proxy → plugin backend
(console-api) → target service (search-api, grc-propagator, etc.).
A 401/403 at any hop breaks the chain. When diagnosing auth failures
for console-proxied features, check logs at each hop to identify WHERE
the token is rejected. This applies to ALL features accessed through
the console UI (search, governance, applications, observability,
fleet virtualization).

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
```

**Knowledge:** rbac/architecture.md, rbac/data-flow.md, rbac/known-issues.md

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
```

**CRITICAL:** If MCH operator is at 0 replicas, MCH CR status
"Running" is STALE. All ACM components are unmanaged and will not
recover from failures. This takes priority over all other findings.

**StatefulSets alongside Deployments:** Some namespaces have both.
The `hive` namespace has Deployments (hive-controllers, hiveadmission)
AND StatefulSets (hive-clustersync, hive-machinepool). Observability
uses StatefulSets for thanos-receive, thanos-store, compactor, rule,
and alertmanager. Always check `oc get statefulset` in addition to
Deployments for these namespaces.

**Sub-operator CR status:** Many ACM subsystems use an intermediate
Custom Resource between the top-level MCH/MCE status and individual
pods. These CRs report subsystem-level health:
```
oc get search -n <acm-ns> -o yaml 2>/dev/null | grep -A3 'type: Ready'
oc get hiveconfig -o yaml 2>/dev/null | grep -A5 'status:'
oc get mco observability -o yaml 2>/dev/null | grep -A5 'conditions:'
```
When MCH says "Running" but a subsystem is broken, check its
intermediate CR before diving into individual pod logs. The general
pattern is: operator → intermediate CR → component deployments.

**Replica mismatch investigation:** When `desiredReplicas !=
availableReplicas`, trace the Deployment → ReplicaSet → Pod chain
before checking container logs. The pod may never have started:
```
oc describe deploy <name> -n <ns> | grep -A5 'Conditions\|Events'
oc get events -n <ns> --sort-by=.lastTimestamp --field-selector involvedObject.kind=Pod | tail -10
```
Common findings: `Unschedulable` (Layer 1: node resources, taints),
`FailedCreate` (Layer 3: ResourceQuota), `FailedScheduling` (Layer 1:
affinity/anti-affinity). Do not check container logs when the
container never started.

**Diagnostic traps:** Trap 1 (stale MCH/MCE status when operator not
running), Trap 7 (ALL addons Unavailable -- check addon-manager first),
Trap 14 (both operator replicas Running but leader election stuck).

**Knowledge:** acm-platform.md, healthy-baseline.yaml, per-subsystem
architecture files

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
Signal:  ALL addons Unavailable on ALL clusters? → check addon-manager
         at Layer 9 (Trap 7), NOT individual addons.
```

**Diagnostic traps:** Trap 6 (ManagedCluster NotReady -- check lease
and conditions, not klusterlet), Trap 7 (mass addon failure --
addon-manager single point of failure).

**Knowledge:** addon-catalog.yaml, dependency-chains.yaml,
cluster-lifecycle/architecture.md, cluster-lifecycle/health-patterns.md

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
       Compare API response vs expected values
       Compare data counts against fleet size (~200 resources per cluster)
Healthy: Data counts match expected, API responses correct
Broken:  Wrong count, fields swapped, stale cache, data transformation bug
Signal:  Everything looks healthy but data is WRONG → Layer 11.
```

**Knowledge:** per-subsystem data-flow.md files

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
Healthy: Plugins registered, console pods Running, images match baseline
Broken:  Plugin not registered, backend pod down, tampered image
Signal:  Tabs missing entirely → Trap 2 (console-mce pod or ConsolePlugin CRDs)
         Tabs present but broken → Trap 13 (plugin backend pod health)
```

**Diagnostic traps:** Trap 2 (console pod healthy, tabs missing --
check console-mce), Trap 8 (multiple console pages broken -- check
search-api first), Trap 13 (tabs present but render errors -- plugin
backend unhealthy).

**Knowledge:** console/architecture.md, console/known-issues.md,
healthy-baseline.yaml (image patterns)

---

## Layers and Diagnostic Traps

Each trap in `common-diagnostic-traps.md` maps to a layer where the
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

### Vertical Tracing Procedure (Phase 5)

When multiple issues are found across different subsystems:

1. List each finding with its layer number
2. Identify the LOWEST affected layer across all findings
3. Check: does a single issue at that layer explain all higher findings?
   - Yes → that's the root cause; higher findings are symptoms
   - No → there are multiple independent root causes
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
independently, check Layer 3 first → NetworkPolicy blocking traffic
in ACM namespace → one root cause explains both symptoms.

## Layer Quick-Reference Card

```
Layer  Check                         Key Command
─────  ───────────────────────────── ─────────────────────────────
  1    Nodes Ready? Pods schedule?   oc get nodes
  2    API server + etcd healthy?    oc get co etcd
  3    NetworkPolicy? ResourceQuota? oc get netpol -n <ns>
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
