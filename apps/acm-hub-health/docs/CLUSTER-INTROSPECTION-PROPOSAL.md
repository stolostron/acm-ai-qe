# Cluster Introspection for Dependency Discovery

Proposal for reverse-engineering operator dependencies from live cluster
metadata when the knowledge graph and static knowledge don't cover a
component.

Based on investigation of ACM 2.16 GA hub (Azure) with 9 installed
operators: ACM, MCE, AAP, Flux, OpenShift GitOps, CNV, MTV, OADP,
Submariner.

---

## Problem

The static knowledge database covers core ACM subsystems. The knowledge
graph covers 300+ ACM components. But a real hub can have any combination
of operators from the OperatorHub marketplace -- AAP, Compliance Operator,
ACS, Quay, custom operators -- creating dependency relationships that
neither source models. When the agent encounters a component it doesn't
know, it needs to understand its dependencies from the cluster itself.

---

## Data Sources Available on Every OpenShift Cluster

Investigation found 8 metadata sources that reveal dependency information.
They vary in reliability and what they tell you.

### Source 1: Owner References (Tier 1 -- Definitive)

Every Kubernetes resource can have `.metadata.ownerReferences` pointing to
the resource that created it. This is the controller hierarchy -- following
owner refs traces the chain from a pod back to its operator.

**What it reveals:** Who created/manages this resource (the controller chain).

**Observed patterns on live cluster:**

```
MCE namespace (strong owner refs):
  cluster-curator-controller     -> owner: MultiClusterEngine/multiclusterengine
  hive-operator                  -> owner: MultiClusterEngine/multiclusterengine
  console-mce-console            -> owner: MultiClusterEngine/multiclusterengine
  cluster-proxy                  -> owner: ManagedProxyConfiguration/cluster-proxy

AAP namespace (full chain):
  aap-gateway                    -> owner: AnsibleAutomationPlatform/aap
  auto-con-task                  -> owner: AutomationController/auto-con
  *-operator-controller-manager  -> owner: ClusterServiceVersion/aap-operator.v2.6.0

ACM namespace (almost no owner refs):
  console-chart-console-v2       -> NO owner reference
  grc-policy-propagator          -> NO owner reference
  search-api                     -> NO owner reference
```

**Key finding:** Owner refs are reliable where they exist (MCE, AAP, CNV),
but ACM's own deployments in the MCH namespace have almost no owner refs.
This is a gap in ACM's operator implementation -- the MCH operator creates
deployments without setting owner references.

**Reliability:** Tier 1 where present, but coverage varies by operator.

**Query:**
```bash
oc get deploy -n <namespace> -o json | jq '.items[] | {name: .metadata.name, owners: .metadata.ownerReferences}'
```

### Source 2: OLM Labels (Tier 1 -- Definitive)

OLM (Operator Lifecycle Manager) labels resources it manages. The
`olm.owner` label on ClusterRoles and ClusterRoleBindings identifies which
CSV (operator version) owns each RBAC resource.

**What it reveals:** Which operator owns which RBAC rules, and through
those rules, which API groups and resources the operator accesses.

**Observed patterns:**

```
AAP operator's ClusterRoles reveal it accesses:
  - automationcontroller.ansible.com (its own CRDs)
  - monitoring.coreos.com (Prometheus integration)
  - route.openshift.io (creates routes)
  - networking.k8s.io (network policies)

ACM operator's ClusterRole reveals it accesses:
  - 74 API groups, 228 resources (broad cluster-wide access)
  - action.open-cluster-management.io, addon.open-cluster-management.io
  - agent-install.openshift.io (assisted installer integration)
```

**Key finding:** The API groups an operator's RBAC can access tells you
what other operators/resources it interacts with. If operator A has RBAC
to read `monitoring.coreos.com`, it depends on the monitoring stack. This
is an implicit dependency declaration.

**Reliability:** Tier 1 -- OLM always sets these labels.

**Query:**
```bash
oc get clusterroles -l olm.owner=<csv-name> -o json | jq '.items[].rules[] | {apiGroups, resources}'
```

### Source 3: CSV Metadata (Tier 1 -- Definitive)

Each operator's ClusterServiceVersion contains structured metadata about
what the operator provides and requires.

**What it reveals:**
- **Owned CRDs**: What custom resources this operator manages
- **Required CRDs**: What CRDs must exist for this operator to work
- **Managed deployments**: What pods the operator runs
- **Related images**: All container images the operator uses
- **OLM properties**: Version constraints (e.g., max OpenShift version)

**Observed patterns:**

```
ACM CSV:
  Owned: 1 CRD (MultiClusterHub)
  Required: 0 (does NOT formally declare MCE dependency!)
  Managed deployments: 1 (multiclusterhub-operator)
  Related images: 64

AAP CSV:
  Owned: 24 CRDs
  Required: 0
  Managed deployments: 6

CNV CSV:
  Owned: 9 CRDs
  Required: 0
  Managed deployments: 10
```

**Key finding:** The `required` CRDs field is empty for ALL operators on
this cluster. Operators don't formally declare OLM dependencies. This makes
CSV metadata useful for understanding what an operator PROVIDES (owned CRDs,
deployments) but not what it REQUIRES.

**Reliability:** Tier 1 for "what does this operator provide." Unreliable
for "what does it depend on" since `required` is typically empty.

**Query:**
```bash
oc get csv <name> -n <ns> -o json | jq '{owned: .spec.customresourcedefinitions.owned, required: .spec.customresourcedefinitions.required, deployments: .spec.install.spec.deployments[].name}'
```

### Source 4: Kubernetes Labels and Annotations (Tier 2 -- Strong)

Standard Kubernetes labels provide grouping and ownership metadata. Not
all operators use them consistently, but when present they're reliable.

**What it reveals:** Logical grouping (part-of, managed-by, component).

**Observed patterns:**

```
AAP (rich labeling):
  app.kubernetes.io/managed-by: aap-operator
  app.kubernetes.io/part-of: aap
  app.kubernetes.io/component: aap-gateway

MCE (no standard labels but has owner refs instead):
  (relies on ownerReferences rather than labels)

ACM (partial):
  app.kubernetes.io/instance: grc
  app.kubernetes.io/name: grc
  (no managed-by or part-of)
```

**Key finding:** `app.kubernetes.io/managed-by` and `part-of` labels
are the most useful, but their presence depends on the operator's
implementation. When present, they're authoritative.

**Reliability:** Tier 2 -- not all operators set them, but reliable when
present.

**Query:**
```bash
oc get deploy -n <ns> -o json | jq '.items[] | {name: .metadata.name, managedBy: .metadata.labels["app.kubernetes.io/managed-by"], partOf: .metadata.labels["app.kubernetes.io/part-of"]}'
```

### Source 5: Environment Variables and Volume Mounts (Tier 1 -- Definitive)

Container environment variables and volume mounts reveal runtime
dependencies -- what services, secrets, and configmaps a component
connects to.

**What it reveals:** Runtime connectivity between components.

**Observed patterns:**

```
search-api:
  DB_HOST = search-postgres.ocm.svc          -> depends on search-postgres

search-collector:
  AGGREGATOR_URL = https://search-indexer.ocm.svc:3010  -> depends on search-indexer

search-indexer:
  DB_HOST = search-postgres.ocm.svc          -> depends on search-postgres

console:
  CLUSTER_API_URL = https://kubernetes.default.svc:443  -> depends on kube API

multicluster-observability-operator:
  SPOKE_NAMESPACE = open-cluster-management-addon-observability  -> manages spoke namespace

klusterlet-addon-controller:
  DEFAULT_IMAGE_PULL_SECRET = multiclusterhub-operator-pull-secret  -> depends on MCH operator
  ADDON_CLUSTERROLE_PREFIX = open-cluster-management:addons:       -> manages addon RBAC

MCH operator:
  OPERAND_IMAGE_* env vars list ALL images it manages             -> maps operator to its operands
```

**Key finding:** This is the richest source for runtime dependencies.
Env vars like `DB_HOST`, `AGGREGATOR_URL`, service references in `.svc`
format, and secret/configmap references directly reveal which components
talk to each other. The MCH operator's `OPERAND_IMAGE_*` env vars
effectively declare its entire component inventory.

**Reliability:** Tier 1 -- if a container env var references a service,
the dependency is real and active.

**Query:**
```bash
oc get deploy -n <ns> -o json | jq '.items[] | {name: .metadata.name, env: [.spec.template.spec.containers[].env[]? | select(.value | test("\\.svc|open-cluster|multicluster")) | {name, value}]}'
```

### Source 6: Webhooks (Tier 1 -- Definitive)

ValidatingWebhookConfigurations and MutatingWebhookConfigurations show
which operators intercept which resources. This reveals cross-operator
dependencies: if operator A validates resources owned by operator B,
they have a dependency.

**What it reveals:** Which operator validates/mutates which resources,
and the service that handles the webhook (cross-namespace references).

**Observed patterns:**

```
application-webhook-validator:
  service: ocm/multicluster-operators-application-svc
  intercepts: app.k8s.io/applications
  owner: Deployment/multicluster-operators-application

CDI webhooks:
  service: openshift-cnv/cdi-api
  intercepts: cdi.kubevirt.io/datavolumes
  owner: CDI/cdi-kubevirt-hyperconverged

Hive webhooks:
  service: default/kubernetes (aggregated API)
  intercepts: hive.openshift.io/clusterdeployments
  owner: HiveConfig/hive
```

**Key finding:** Webhooks create hard dependencies. If the webhook
service is down, the resources it validates can't be created or updated.
This is a critical dependency path that can cause cascading failures.

**Reliability:** Tier 1 -- webhook configurations are declarative and
always present when active.

**Query:**
```bash
oc get validatingwebhookconfigurations -o json | jq '.items[] | {name: .metadata.name, service: .webhooks[0].clientConfig.service, resources: [.webhooks[].rules[].resources[]]}'
```

### Source 7: ConsolePlugins (Tier 1 -- Definitive)

ConsolePlugin CRs declare UI integration dependencies. Each plugin
specifies the service it proxies to and any additional backend services
it needs.

**What it reveals:** UI integration topology -- which operators extend
the OpenShift console and what backend services they depend on.

**Observed patterns:**

```
acm:
  service: ocm/console-chart-console-v2:3000
  proxy -> ocm/console-chart-console-v2

forklift-console-plugin (MTV):
  service: openshift-mtv/forklift-ui-plugin:9443
  proxy -> openshift-mtv/forklift-inventory
  proxy -> openshift-mtv/forklift-services
  proxy -> openshift-mtv/forklift-ova-proxy

kubevirt-plugin (CNV):
  service: openshift-cnv/kubevirt-console-plugin-service:9443
  proxy -> openshift-cnv/kubevirt-apiserver-proxy-service

mce:
  service: multicluster-engine/console-mce-console:3000
  owner: MultiClusterEngine/multiclusterengine

gitops-plugin:
  service: openshift-gitops/gitops-plugin:9001
  owner: GitopsService/cluster
```

**Key finding:** ConsolePlugins reveal which operators add UI tabs to
the console and what backend services the UI calls. This is critical
for understanding "why is this console tab broken" questions.

**Reliability:** Tier 1 -- declarative, always accurate when present.

**Query:**
```bash
oc get consoleplugins -o json | jq '.items[] | {name: .metadata.name, service: .spec.backend.service, proxies: [.spec.proxy[]?.endpoint.service]}'
```

### Source 8: APIServices (Tier 1 -- Definitive)

Non-local APIService resources identify which operators serve custom API
endpoints via aggregated API servers.

**What it reveals:** Which operators extend the Kubernetes API and what
service handles each API group.

**Observed patterns:**

```
admission.hive.openshift.io/v1 -> hive/hiveadmission
clusterview.open-cluster-management.io/v1 -> multicluster-engine/ocm-proxyserver
subresources.kubevirt.io/v1 -> openshift-cnv/virt-api
upload.cdi.kubevirt.io/v1beta1 -> openshift-cnv/cdi-api
proxy.open-cluster-management.io/v1beta1 -> multicluster-engine/ocm-proxyserver
```

**Key finding:** If an APIService points to a pod and that pod is down,
the entire API group becomes unavailable. This can break other operators
that depend on those APIs.

**Reliability:** Tier 1 -- always accurate, system-maintained.

**Query:**
```bash
oc get apiservices -o json | jq '.items[] | select(.spec.service != null) | {name: .metadata.name, service: .spec.service}'
```

---

## Proposed Discovery Workflow

### Step 1: Identify the Unknown Component

Determine what kind of thing we're looking at:

```
Is it a deployment/pod?
  -> Check owner references (trace up to CSV or CR)
  -> Check labels (managed-by, part-of, instance)
  -> Check the namespace (maps to subscription)

Is it a CRD?
  -> Check labels (olm.owner, managed-by)
  -> Cross-reference with CSV owned CRDs

Is it an operator (CSV)?
  -> Read its owned CRDs, managed deployments
  -> Read its RBAC (ClusterRoles with olm.owner label)
```

### Step 2: Map the Operator's Footprint

For the identified operator, collect everything it owns/manages:

```
a. What CRDs does it own?       (CSV .spec.customresourcedefinitions.owned)
b. What deployments does it run? (CSV .spec.install.spec.deployments)
c. What RBAC does it have?       (ClusterRoles with olm.owner=<csv>)
d. What API groups does it access?(from RBAC rules)
e. What webhooks does it run?    (validating/mutating webhook configs)
f. What console plugins?         (ConsolePlugin CRs)
g. What API services?            (non-local APIServices)
```

### Step 3: Infer Dependencies from RBAC

The operator's ClusterRole rules reveal its dependencies through the
API groups it accesses:

```
API group in RBAC rules          -> Depends on
──────────────────────────────────────────────
monitoring.coreos.com            -> Prometheus/monitoring stack
route.openshift.io               -> OpenShift router
storage.k8s.io                   -> CSI/storage subsystem
cdi.kubevirt.io                  -> CDI (CNV)
kubevirt.io                      -> KubeVirt (CNV)
hive.openshift.io                -> Hive (cluster provisioning)
addon.open-cluster-management.io -> ACM addon framework
cluster.open-cluster-management.io -> ACM managed clusters
config.openshift.io              -> OpenShift cluster config
machine.openshift.io             -> Machine API
```

If the API group belongs to a CRD, trace the CRD back to its owning CSV
to identify the operator dependency.

### Step 4: Infer Dependencies from Environment Variables

Parse container env vars for cross-component references:

```
Pattern                          -> Dependency
──────────────────────────────────────────────
*.svc, *.svc.cluster.local       -> Service dependency (namespace/name)
DB_HOST, DATABASE_URL            -> Database dependency
*_URL, *_ENDPOINT                -> Service endpoint dependency
*_SECRET, SECRET_NAME            -> Secret dependency
*_NAMESPACE                      -> Cross-namespace relationship
OPERAND_IMAGE_*                  -> Managed operand (operator->child)
```

### Step 5: Build Dependency Graph

Combine all sources into a dependency map:

```
Component: search-api
  Namespace: ocm
  Owner: Search/search-v2-operator (owner ref)
  Part-of: ACM (subscription in ocm namespace)
  Depends on:
    - search-postgres (env: DB_HOST=search-postgres.ocm.svc)
    - kubernetes API (env: CLUSTER_API_URL)
  Depended on by:
    - console (env var / route reference)
  Webhooks: none
  Console plugins: none
  API services: none
```

### Step 6: Cross-Reference with MCH/MCE Component Maps

Both MCH and MCE maintain component status maps in their CR status.
Cross-reference the discovered component against these maps:

```
MCH .status.components:
  search-api: True (Deployment) MinimumReplicasAvailable
  -> Confirms search-api is MCH-managed

MCE .status.components:
  cluster-proxy (Deployment): True MinimumReplicasAvailable
  -> Confirms cluster-proxy is MCE-managed
```

Any component NOT in these maps but running in ACM namespaces is likely
from another operator or a manual deployment.

---

## Evidence Confidence by Source

| Source | Tier | Coverage | What It Tells You |
|--------|------|----------|-------------------|
| Owner references | 1 | 60-70% of resources | Controller hierarchy (who created this) |
| OLM labels | 1 | All OLM-managed RBAC | Operator-to-RBAC mapping |
| CSV metadata | 1 | All operators | What operator provides (CRDs, pods) |
| Env vars / volumes | 1 | All pods | Runtime service dependencies |
| Webhooks | 1 | All webhook-using operators | Cross-operator validation deps |
| ConsolePlugins | 1 | All UI-extending operators | UI integration topology |
| APIServices | 1 | All API-extending operators | API aggregation dependencies |
| Labels (app.k8s.io) | 2 | 40-50% of resources | Logical grouping |

---

## What This Cannot Discover

1. **Implicit runtime dependencies** -- If component A calls component B's
   API but the URL is hardcoded in the binary (not in env vars), we can't
   see it from metadata alone.

2. **Ordering dependencies** -- We can see that A depends on B, but not
   whether A needs B to start first or just needs it available eventually.

3. **Feature-level dependencies** -- "Search only works if managed clusters
   have search-collector addon deployed" is a feature-level dependency, not
   a metadata-level one.

4. **Performance dependencies** -- "Observability requires S3-compatible
   storage with specific IOPS" can't be inferred from metadata.

These gaps are where web search (for operator documentation) and the
static knowledge database (for ACM-specific behavior) remain necessary.

---

## Implementation Approach

The cluster introspection would be a new step in the self-healing flow,
between "collect cluster evidence" and "query knowledge graph":

```
  Static knowledge doesn't cover it
           |
           v
  Step 1: Cluster evidence (oc describe, labels, events)
           |
           v
  Step 2: Cluster introspection (NEW)
           - Trace owner refs up to CSV
           - Read CSV owned CRDs and deployments
           - Parse RBAC for API group dependencies
           - Parse env vars for service dependencies
           - Check webhooks, console plugins, API services
           - Cross-ref with MCH/MCE component maps
           - Build dependency map
           |
           v
  Step 3: Knowledge graph (if available, for ACM components)
           |
           v
  Step 4: acm-ui MCP + rhacm-docs (understand discovered deps)
           |
           v
  Step 5: Web search (for third-party operator docs, if needed)
           |
           v
  Synthesize + write to learned/
```

The cluster introspection step runs 6-8 `oc get` commands (all read-only,
auto-approved) and processes the JSON output to build a dependency map.
No new tools or MCPs needed -- it uses the existing `oc` CLI.

---

## Example: Discovering AAP Dependencies from Scratch

If the agent encountered AAP on a cluster with no static knowledge:

1. **Owner refs**: `aap-gateway` -> `AnsibleAutomationPlatform/aap` ->
   `ClusterServiceVersion/aap-operator.v2.6.0`
2. **CSV**: Owns 24 CRDs, manages 6 deployments, catalog: redhat-operators
3. **RBAC**: Accesses `monitoring.coreos.com` (Prometheus integration),
   `route.openshift.io` (creates routes), `networking.k8s.io`
4. **Labels**: `managed-by: aap-operator`, `part-of: aap`
5. **Subscription**: channel `stable-2.6-cluster-scoped`, automatic updates
6. **No webhooks, no console plugins, no API services**

Result: AAP is a self-contained operator that optionally integrates with
Prometheus monitoring and creates OpenShift routes. It doesn't depend on
ACM components. If it fails, no ACM components are directly affected.

This is exactly the kind of assessment the agent needs for health checks --
understanding whether a failing component affects ACM or is independent.
