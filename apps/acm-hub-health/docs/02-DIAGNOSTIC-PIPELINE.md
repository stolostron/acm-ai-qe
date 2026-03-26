# Diagnostic Pipeline: 5-Phase Methodology

The agent uses a 5-phase diagnostic pipeline to investigate hub health. Each
phase builds on the previous one's findings.

---

## Overview

```
  PHASE 1              PHASE 2              PHASE 3              PHASE 4              PHASE 5
┌──────────┐        ┌──────────┐        ┌──────────┐        ┌──────────┐        ┌──────────┐
│ DISCOVER │  ───►  │  LEARN   │  ───►  │  CHECK   │  ───►  │CORRELATE │  ───►  │  DEEP    │
│          │        │          │        │          │        │          │        │INVESTIGATE│
│ What's   │        │ What do  │        │ Is each  │        │ Are      │        │          │
│ deployed?│        │ I know   │        │ component│        │ issues   │        │ Dig into │
│          │        │ about it?│        │ healthy? │        │ related? │        │ specifics│
└──────────┘        └──────────┘        └──────────┘        └──────────┘        └──────────┘
     │                    │                   │                   │                    │
     ▼                    ▼                   ▼                   ▼                    ▼
  Inventory          Knowledge           Component           Root cause           Detailed
  of hub             gaps filled          status              hypotheses           findings
  components                              verdicts
```

| Phase | Run When | Purpose |
|-------|----------|---------|
| 1 - Discover | Always | Inventory what's deployed on this specific hub |
| 2 - Learn | Standard+ | Consult knowledge base, fill gaps via self-healing |
| 3 - Check | Standard+ | Systematically verify health of each component |
| 4 - Correlate | Deep / Targeted | Cross-reference findings to find root causes |
| 5 - Deep Investigate | Deep / Targeted | Dig into logs, events, storage for critical findings |

---

## Phase 1: Discover (Always Run)

**Purpose:** Build a complete inventory of what's deployed on this hub before
checking anything. Never assume what's deployed -- every hub is different.

**Key principle:** Discover the MCH namespace first. It is NOT always
`open-cluster-management` -- it can be `ocm` or any custom namespace. All
subsequent pod checks must use the discovered namespace.

### Commands (run in parallel)

```bash
oc get mch -A -o yaml                          # MCH status, version, components, NAMESPACE
oc get multiclusterengines -A -o yaml           # MCE status
oc get nodes                                    # Node health
oc get clusterversion                           # OCP version, upgrade status
oc get managedclusters                          # Fleet: managed cluster summary
oc get csv -n multicluster-engine               # MCE operator status
oc whoami --show-server                         # Cluster identity
```

### Data Extracted

| Data Point | Source | Example |
|-----------|--------|---------|
| MCH namespace | `oc get mch -A` metadata.namespace | `ocm` |
| ACM version | MCH `.status.currentVersion` | `2.16.0` |
| MCE version | MCE `.status.currentVersion` | `2.11.0` |
| OCP version | clusterversion `.status.desired.version` | `4.21.5` |
| Enabled components | MCH `.spec.overrides.components` | `[search, grc, console, ...]` |
| Component health map | MCH `.status.components` | `{search-api: {status: "True"}, ...}` |
| MCH phase | MCH `.status.phase` | `Running` |
| MCE phase | MCE `.status.phase` | `Available` |
| Node count/status | node list | `6 Ready (3 master, 3 worker)` |
| Managed cluster count | managedcluster list | `2 Available` |
| CSV status | csv list | `advanced-cluster-management.v2.16.0 Succeeded` |

### Critical First Steps

1. **Discover MCH namespace:** `oc get mch -A` returns the namespace in
   `.metadata.namespace`. Use this namespace for ALL subsequent pod checks.

2. **Identify enabled components:** MCH `.spec.overrides.components` lists
   what's enabled/disabled. This tells you what to check and what to skip.
   Every hub is different.

3. **Check component health map:** MCH `.status.components` is a map keyed
   by component name. Each entry has `status`, `type`, `reason`, `kind`.
   Any entry with `status: "False"` is a problem.

---

## Phase 2: Learn (Standard+)

**Purpose:** For each component discovered in Phase 1, consult the knowledge
base and fill any gaps.

### Process Per Component

```
  Component from Phase 1
          │
          ▼
  ┌───────────────────┐
  │ Check static      │
  │ knowledge          │     knowledge/component-registry.md
  │ (component-        │
  │  registry.md)      │
  └────────┬──────────┘
           │
           ▼
  ┌───────────────────┐
  │ Check learned     │
  │ knowledge          │     knowledge/learned/*.md
  │ (learned/*.md)     │
  └────────┬──────────┘
           │
           ▼
  ┌───────────────────┐     ┌──────────────────┐
  │ Mismatch?         │────►│ Self-Healing      │
  │                   │ yes │ Process            │
  │ - Not in registry │     │ (see 03-KNOWLEDGE │
  │ - Different NS    │     │  -SYSTEM.md)       │
  │ - Different pods  │     │                    │
  │ - New behavior    │     │ Write to           │
  └────────┬──────────┘     │ learned/<topic>.md │
           │ no             └──────────────────┘
           ▼
  Continue with known
  reference information
```

### What Triggers Self-Healing

- A component is deployed that isn't in `component-registry.md`
- A namespace is different from what the knowledge says
- Pod naming or labeling doesn't match the reference
- A new CRD, addon, or operator is discovered
- Health signals or status conditions are unfamiliar
- Behavior differs from what the knowledge describes

See [03-KNOWLEDGE-SYSTEM.md](03-KNOWLEDGE-SYSTEM.md) for the full self-healing process.

---

## Phase 3: Check (Standard+)

**Purpose:** Systematically verify the health of each discovered component.

### Checks Per Component

For each component identified in Phase 1:

| Check | Method | What It Reveals |
|-------|--------|-----------------|
| Pod status | `oc get pods -n <ns> --field-selector=status.phase!=Running,status.phase!=Succeeded` | Pods not in expected state |
| Restart count | Pod `.status.containerStatuses[].restartCount` | CrashLoop indicators |
| Resource conditions | `oc get <resource> -o yaml` conditions array | Available, Degraded, Progressing |
| Recent events | `oc get events -n <ns> --sort-by=.lastTimestamp` | Scheduling failures, OOM, image pull errors |
| Anomalies | Comparison with knowledge reference | Unexpected state vs documented behavior |

### Batch Check Strategy

The agent checks efficiently -- batching related commands rather than running
them one pod at a time:

```bash
# Check all non-running pods across key namespaces (use MCH namespace from Phase 1)
oc get pods -n <mch-namespace> --field-selector=status.phase!=Running,status.phase!=Succeeded
oc get pods -n multicluster-engine --field-selector=status.phase!=Running,status.phase!=Succeeded
oc get pods -n open-cluster-management-hub --field-selector=status.phase!=Running,status.phase!=Succeeded
oc get pods -n open-cluster-management-observability 2>/dev/null
oc get pods -n hive --no-headers

# Check all add-on status across all managed clusters in one command
oc get managedclusteraddons -A
```

### Namespace Discovery

The agent uses the MCH namespace discovered in Phase 1 rather than hardcoding
namespace names. Common namespace mappings:

| Namespace | What Lives There |
|-----------|-----------------|
| MCH namespace (varies: `ocm`, `open-cluster-management`, or custom) | Most ACM hub components, operators, MCH operator |
| `open-cluster-management-hub` | Hub-specific controllers (placement, work-manager, registration) |
| `multicluster-engine` | MCE operator and components |
| `open-cluster-management-observability` | Observability stack (Thanos, Grafana, ~30+ pods) |
| `hive` | Hive cluster provisioning |

### Health Verdict Per Component

Each component gets a verdict:

| Verdict | Criteria |
|---------|----------|
| **OK** | All pods Running, zero or low restart count, conditions healthy |
| **WARN** | Minor issues: high restart count but currently stable, non-critical condition degraded |
| **CRIT** | Pods CrashLooping, critical conditions False, core functionality impaired |

---

## Phase 4: Correlate (Deep / Targeted)

**Purpose:** When multiple issues are found, look for connections between them.
Identify root causes rather than treating each symptom independently.

### Correlation Process

```
  Phase 3 Findings
  (multiple issues)
          │
          ▼
  ┌───────────────────┐
  │ Check failure-    │     knowledge/failure-patterns.md
  │ patterns.md for   │
  │ known patterns    │
  └────────┬──────────┘
           │
           ▼
  ┌───────────────────┐
  │ Check shared      │     Same storage class? Same node?
  │ dependencies      │     Same network path?
  └────────┬──────────┘
           │
           ▼
  ┌───────────────────┐
  │ Check timeline    │     Did failures happen at the same time?
  │ correlation       │     Is there a cascade pattern?
  └────────┬──────────┘
           │
           ▼
  Root cause hypothesis
```

### Common Correlation Patterns

These patterns are documented in `knowledge/failure-patterns.md`:

| Pattern | Symptoms | Likely Root Cause |
|---------|----------|-------------------|
| Search + Observability both broken | Multiple storage-backed components failing | Shared storage/CSI driver issue |
| Search empty + Managed clusters Unknown | Missing results AND spoke disconnected | Spoke connectivity (same clusters affected) |
| Multiple addons unavailable on same spoke | Several independent addons fail together | Klusterlet or addon-manager issue, not individual addons |
| Console 500 across all features | All UI features broken simultaneously | Console-api pod down (single backend) |
| Components degraded after OCP upgrade | Multiple pods restarting post-upgrade | OCP upgrade disruption (may self-resolve) |

### Anti-Patterns

Things that look related but usually aren't:

- Different components failing for different reasons (e.g., search OOMKilled + governance webhook error) -- investigate independently
- Spoke addon failure vs hub component failure -- if hub is fine, the problem is spoke-side
- Pod restart count > 0 -- restarts during upgrades and maintenance are normal

---

## Phase 5: Deep Investigate (Deep / Targeted)

**Purpose:** For critical findings or targeted investigations, dig into the
details -- logs, events, storage, networking.

### Investigation Toolkit

| Tool | Command Pattern | What It Reveals |
|------|-----------------|-----------------|
| Pod logs | `oc logs -n <ns> <pod> --tail=50` | Error messages, stack traces |
| Previous crash logs | `oc logs -n <ns> <pod> --previous --tail=30` | Why the pod crashed last time |
| Namespace events | `oc get events -n <ns> --sort-by=.lastTimestamp` | Scheduling, OOM, image pull |
| Resource details | `oc describe <resource> -n <ns>` | Conditions, events, owner refs |
| PVC status | `oc get pvc -n <ns>` | Storage binding, capacity |
| Resource usage | `oc adm top pods -n <ns>` | CPU/memory consumption |
| Network verification | `oc get routes -n <ns>`, `oc get svc -n <ns>` | Route/service availability |
| Node conditions | `oc get nodes -o json \| jq ...` | MemoryPressure, DiskPressure |

### Per-Subsystem Playbooks

The agent follows investigation procedures from `knowledge/diagnostic-playbooks.md`.
Each subsystem has a documented procedure:

| Subsystem | Playbook Section | Key Investigation Steps |
|-----------|-----------------|------------------------|
| MCH / MCE Lifecycle | "MCH / MCE Lifecycle" | Check `.status.components`, operator logs, install plans |
| Managed Cluster Connectivity | "Managed Cluster Connectivity" | Check lease renewal, cluster events, registration controller |
| Search | "Search Subsystem" | Check search pods, postgres PVC, search-collector addon |
| Observability | "Observability Stack" | Check MCO CR, Thanos components, S3 config, PVCs, store logs |
| Governance / Policy | "Governance / Policy Framework" | Check propagator, policy compliance, work-manager |
| Application Lifecycle | "Application Lifecycle" | Check subscription controller, channels, placement decisions |
| Console & UI | "Console & UI" | Check console pods, ConsolePlugin CRs, routes, OAuth |
| Node & Infrastructure | "Node & Infrastructure" | Check node conditions, resource usage, etcd |
| Certificates | "Certificates" | Check TLS secrets, expiration dates, webhook configs |
| Add-ons | "Add-ons (General)" | Check addon status, ClusterManagementAddon, addon-manager |

### Investigation Output

Phase 5 findings are presented in narrative format:

1. **What was checked** -- the specific commands and resources examined
2. **What was found** -- the actual state observed on the cluster
3. **What it means** -- interpretation of the findings with uncertainty noted
4. **What to do** -- recommended remediation actions (never executed by the agent)

---

## Phase Execution by Depth

```
              Phase 1    Phase 2    Phase 3    Phase 4    Phase 5
              Discover   Learn      Check      Correlate  Investigate
  ───────────────────────────────────────────────────────────────────
  Quick       ████████
  Pulse

  Standard    ████████   ████████   ████████
  Check

  Deep        ████████   ████████   ████████   ████████   ████████
  Audit

  Targeted    ████████   ████████   ████████   ████████   ████████
  Invest.     (full)     (scoped)   (scoped)   (w/ deps)  (focused)
```

---

## See Also

- [01-DEPTH-ROUTER.md](01-DEPTH-ROUTER.md) -- how depth level is selected
- [03-KNOWLEDGE-SYSTEM.md](03-KNOWLEDGE-SYSTEM.md) -- knowledge and self-healing (Phase 2 detail)
- [05-OUTPUT-AND-REPORTING.md](05-OUTPUT-AND-REPORTING.md) -- how findings are reported
- [00-OVERVIEW.md](00-OVERVIEW.md) -- top-level overview
