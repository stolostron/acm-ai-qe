# Governance (GRC) -- Data Flow

## End-to-End Policy Lifecycle

```
Hub: Policy + PlacementBinding + Placement
  |
  v
Hub: grc-policy-propagator evaluates Placement decisions
  |
  v
Hub: Replicated policy in each target cluster's namespace
  |
  v (hub template resolution with encryption)
Hub -> Spoke: Spec Sync Controller pulls replicated policy
  |
  v
Spoke: Template Sync creates ConfigurationPolicy / CertificatePolicy / OperatorPolicy
  |
  v
Spoke: config-policy-controller evaluates and optionally enforces
  |
  v
Spoke -> Hub: Status Sync Controller reports compliance events
  |
  v
Hub: Status Aggregation Engine -> Root Compliance Calculator
```

### Console-Originated Policy Lifecycle

```
User creates Policy via console UI or oc apply
  -> Policy CR created in hub namespace
  -> grc-policy-propagator watches for new/changed policies
    -> evaluates PlacementBinding + PlacementRule
    -> determines target managed clusters
    -> creates replicated Policy in each target cluster's namespace
  -> governance-policy-framework addon on spoke
    -> detects replicated Policy
    -> instantiates policy template (ConfigurationPolicy, CertificatePolicy, etc.)
    -> controller evaluates compliance
  -> compliance status flows back to hub
    -> spoke addon updates Policy status
    -> propagator aggregates compliance across clusters
  -> console UI displays compliance status in policy table
```

---

## Step 1: Policy Creation on Hub

User creates Policy + Placement + PlacementBinding in same namespace.

**Failure:** Missing PlacementBinding or Placement -> policy exists but is NOT
propagated. No error -- just no propagation. Policy name + namespace exceeding
63 chars -> replicated policy label exceeds K8s limit.

---

## Step 2: Propagator Distributes

grc-policy-propagator watches Policy/Placement/PlacementBinding. For each
matched cluster, creates replicated policy in that cluster's namespace on hub.
Named `<policy-namespace>.<policy-name>`.

**Failure:** Propagator pod down -> policies not distributed. Placement matches
no clusters -> no replicated policies created. ManagedClusterSetBinding missing ->
Placement can't evaluate.

---

## Step 3: Hub Template Resolution

Propagator resolves `{{hub ... hub}}` templates before creating replicated policy.
`fromSecret`/`copySecretData` auto-encrypt values. `protect` encrypts arbitrary values.

**Failure:** Template syntax error -> policy marked as violation. Referenced
resource not found -> empty/nil value, possibly invalid YAML. Permission
denied -> template resolution fails.

---

## Step 4: Delivery to Spoke (Spec Sync)

governance-policy-framework-addon's Spec Sync Controller pulls replicated
policies from hub to spoke. Unlike other addon flows that use ManifestWork,
governance uses its own sync controllers.

**Failure:** Framework addon not running -> policies never reach spoke,
compliance unknown. Klusterlet disconnected -> spec sync can't communicate,
policies on spoke become stale.

---

## Step 5: Template Sync Creates Policy Objects

Template Sync Controller reads `spec.policy-templates[]` from replicated policy,
creates/updates/deletes corresponding policy objects (ConfigurationPolicy, etc.).
Secret Sync handles decryption of encrypted values.

**Failure:** Invalid policy template -> policy object not created, stays pending.
CRD not installed on spoke -> creation fails.

---

## Step 6: config-policy-controller Evaluates and Enforces

For each ConfigurationPolicy:
1. Resolves managed cluster templates (`{{ ... }}`)
2. Evaluates namespaceSelector for target namespaces
3. Compares objectDefinition against cluster state
4. If enforce: creates/patches/deletes objects
5. Default: uses watches (not polling) for re-evaluation

**Failure:** Controller not running -> policies never evaluated, compliance
unknown. Template resolution failure -> non-compliant with template error.
**Hot-loop:** Lookup watchers trigger on status-only changes, causing
re-evaluation every 10s even on compliant policies (ACM-25694).

---

## Step 7: Status Flows Back to Hub

Status Sync Controller reads compliance from policy controllers, writes to
replicated policy on spoke AND hub. Status only contains current policy version
updates -- no historical preservation.

**Failure:** Klusterlet disconnected -> status can't reach hub, shows stale.
work-manager backlog -> compliance updates delayed.

---

## Step 8: Root Compliance Aggregation

Status Aggregation Engine reads all replicated policy statuses. Root Compliance
Calculator aggregates:
- ALL clusters Compliant -> root Compliant
- ANY cluster NonCompliant -> root NonCompliant
- Pending clusters -> depends on ignorePending setting

Metrics updated: `policy_governance_info` (0=compliant, 1=non-compliant, -1=pending).
PolicyAutomation triggered on non-compliance if configured.

**Failure:** Propagator down -> aggregation stops, root status stale.
History calculation bugs -> excessive status updates overloading framework
(ACM-28668).

---

## Compliance Reporting Flow (Spoke Detail)

```
Spoke cluster
  config-policy-controller evaluates ConfigurationPolicy
    -> compares desired state vs actual state
    -> sets compliance status (Compliant / NonCompliant)
  governance-policy-framework reports status to hub
    -> updates replicated Policy status in cluster namespace

Hub cluster
  grc-policy-propagator
    -> reads compliance from all cluster namespaces
    -> aggregates into root Policy status
    -> status appears in console UI policy table
```

---

## Gatekeeper-Specific Flow

Template Sync deploys ConstraintTemplate + constraints to spoke. Gatekeeper
webhook evaluates API requests real-time. Gatekeeper audit controller
periodically audits existing resources. Gatekeeper Sync Controller translates
audit violations into ACM compliance events. Standard status flow back to hub.

---

## OperatorPolicy Flow

Template Sync deploys OperatorPolicy to spoke. Operator policy controller
checks OLM state (Subscription, CSV, OperatorGroup, InstallPlan). When enforce:
creates Subscription/OperatorGroup, approves InstallPlans matching versions spec.
Standard status flow back to hub.

---

## Failure Modes at Each Hop

### propagator down
- **Symptom:** Policies not distributed to spokes. New policies created but never enforced.
- **Scope:** All policy propagation blocked.
- **Detection:** `oc get pods -n <mch-ns> -l app=grc-policy-propagator`

### propagator cert corrupted
- **Symptom:** Webhook fails TLS. Policy creation/modification returns 500.
- **Scope:** All policy mutations blocked.
- **Detection:** Check propagator webhook serving cert validity.

### spoke addon missing
- **Symptom:** No compliance reporting from that spoke. Policy shows "no status" for that cluster.
- **Scope:** Single spoke.
- **Detection:** `oc get managedclusteraddon governance-policy-framework -n {cluster}`

### ResourceQuota blocks propagator restart
- **Symptom:** Propagator stays down after crash. Policies stale, no new distribution.
- **Scope:** All policy operations.
- **Detection:** Check pod events for ResourceQuota denial.

### PlacementBinding wrong
- **Symptom:** Policy targets wrong clusters. Compliance reports don't match expectations.
- **Scope:** Affected policies.
- **Detection:** `oc get placementbinding -n <policy-ns>` -- verify references.
