# Governance (GRC) -- Architecture

## What Governance Does

Provides a policy framework for defining, distributing, enforcing, and reporting
on security/compliance policies across managed clusters. Handles:

- **Policy creation:** On hub via YAML, console UI, or PolicyGenerator
- **Policy propagation:** Distribute to target clusters via Placement
- **Policy enforcement:** Enforce desired state (ConfigurationPolicy with enforce)
- **Compliance reporting:** Aggregate per-cluster status back to hub

---

## Hub-Side Components

### grc-policy-propagator

- **Pod label:** `app=grc-policy-propagator`
- **Namespace:** MCH namespace

Central hub controller. It:
1. Watches `Policy`, `Placement`, `PlacementBinding` resources
2. Generates **replicated policies** in each target cluster's namespace on hub
   (named `namespaceName.policyName`, must not exceed 63 chars)
3. Resolves **hub templates** (`{{hub ... hub}}`) before propagation
4. Aggregates compliance status from all replicated policies via Status
   Aggregation Engine and Root Compliance Calculator
5. Triggers PolicyAutomation (Ansible jobs) on violations

Internal sub-components:
- Resource Version Tracker
- Template Resolvers (with encryption support)
- PlacementBinding/PlacementRule/Placement Decision handlers
- Status Aggregation Engine with Root Compliance Calculator

### grc-policy-addon-controller

- **Namespace:** MCH namespace

Manages governance addon lifecycle on managed clusters via addon framework.
Deploys: governance-policy-framework, config-policy-controller,
cert-policy-controller, iam-policy-controller.

Configuration via ManagedClusterAddon annotations:
- `policy-evaluation-concurrency` (default: 2)
- `client-qps` and `client-burst`
- `log-level` (-1 errors, 0 info, 1 debug, 2 verbose)

---

## Spoke-Side Components (Addons)

### governance-policy-framework-addon

Contains **5 sync controllers**:

1. **Spec Sync:** Pulls replicated policies from hub to managed cluster
2. **Template Sync:** Creates/updates/deletes policy objects
   (ConfigurationPolicy, CertificatePolicy, etc.) from policy-templates
3. **Status Sync:** Reports compliance events back to hub
4. **Secret Sync:** Handles encrypted hub template value decryption
5. **Gatekeeper Sync:** Translates Gatekeeper constraint audit results into
   ACM compliance events

### config-policy-controller

Enforces `ConfigurationPolicy` on managed clusters:
- Compares managed cluster objects against `objectDefinition`
- Supports `musthave`, `mustonlyhave`, `mustnothave`
- When `enforce`: creates or patches objects to match desired state
- Default evaluation uses Kubernetes API watches (not polling)
- Resolves managed cluster templates (`{{ ... }}`) at runtime
- Concurrency controlled by `policy-evaluation-concurrency`

Key parameters:
- **namespaceSelector:** Which namespaces to check (include/exclude, matchExpressions)
- **evaluationInterval:** `watch` (default), duration, or `never`
- **pruneObjectBehavior:** Cleanup on removal: None, DeleteIfCreated, DeleteAll
- **recreateOption:** None, IfRequired, Always

### cert-policy-controller

Monitors certificates in secrets. Detects expiring certs, excessive duration,
DNS SAN mismatches. Inform-only (no enforce support).

### OperatorPolicy

Manages OLM operator lifecycle through policy:
- Installs operators (creates Subscription + OperatorGroup)
- Approves InstallPlans matching `versions` spec
- Removes operators per `removalBehavior` settings
- Health monitoring via `complianceConfig`

---

## Template Resolution

### Hub Templates (`{{hub ... hub}}`)
Processed on hub during propagation. Context: `.ManagedClusterName`,
`.ManagedClusterLabels`, `.PolicyMetadata`. Functions: `lookup`, `fromSecret`
(auto-encrypts), `fromConfigMap`, `protect`.

### Managed Cluster Templates (`{{ ... }}`)
Processed on spoke at evaluation time. Context: `.ObjectName`,
`.ObjectNamespace`, `.Object`. Can reference any spoke resource.

### Template Functions
`lookup`, `fromSecret`, `copySecretData`, `fromConfigMap`, `base64enc/dec`,
`toRawJson`, `toLiteral`, `protect`, `skipObject`, `hasNodesWithExactRoles`

Advanced: `object-templates-raw` supports if/else, range, Go template control.

---

## Gatekeeper Integration

ACM integrates with OPA Gatekeeper for admission-webhook policy enforcement:
- ConstraintTemplates define policy logic in Rego
- Constraints are instances with parameters and match criteria
- Gatekeeper Sync Controller translates audit results into ACM compliance events
- PolicyGenerator supports `informGatekeeperPolicies: true` (default)

---

## Reconciliation Patterns

### What Triggers Re-evaluation
- **Watches (default):** Informer watches on resources matching objectDefinition.
  Any change triggers re-evaluation.
- **Polling:** When evaluationInterval set to duration (e.g., `10s`)
- **Hub template changes:** Referenced resource changes or trigger-update annotation
- **Placement changes:** New cluster selections update policy distribution

### How Watchers Work
config-policy-controller sets up informer-based watches. When watched object
changes, controller re-evaluates. The `evaluationInterval` determines fallback:
- `watch`: Relies on watches, no polling
- Duration: Falls back to polling at specified interval
- `never`: No re-evaluation after initial check

---

## Cross-Subsystem Dependencies

- **Infrastructure:** If klusterlet disconnected, compliance status stops updating
- **Console:** Resource Proxy proxies GRC resources for governance UI
- **Search:** Discovered policies table requires Search to index policy resources
- **PlacementBinding/PlacementRule:** Shared with CLC and Application subsystems
