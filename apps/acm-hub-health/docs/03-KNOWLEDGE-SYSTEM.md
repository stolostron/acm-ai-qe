# Knowledge System and Self-Healing

The agent uses a two-layer knowledge system that combines curated reference
material with discoveries made during previous health checks. When the agent
encounters something not covered by its knowledge base, it triggers a
self-healing process to investigate, learn, and record findings.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Knowledge System                                  │
│                                                                            │
│  ┌────────────────────────────┐       ┌──────────────────────────────────┐ │
│  │ LAYER 1: Static Knowledge  │       │ LAYER 2: Learned Knowledge       │ │
│  │                            │       │                                  │ │
│  │ knowledge/                 │       │ knowledge/learned/               │ │
│  │ ├── component-registry.md  │       │ └── <topic>.md                   │ │
│  │ ├── failure-patterns.md    │       │                                  │ │
│  │ └── diagnostic-playbooks.md│       │ Written by the agent during      │ │
│  │                            │       │ health checks when mismatches    │ │
│  │ Manually curated.          │       │ are detected between knowledge   │ │
│  │ Covers common components,  │       │ and cluster state.               │ │
│  │ patterns, and procedures.  │       │                                  │ │
│  │ May become outdated as     │       │ Supplements static knowledge.    │ │
│  │ ACM evolves.               │       │ More recent and version-specific.│ │
│  └────────────────────────────┘       └──────────────────────────────────┘ │
│                                                                            │
│  Priority: Cluster > Layer 2 > Layer 1                                     │
│  The live cluster is always the source of truth.                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Static Knowledge

Three curated reference files provide the baseline knowledge:

### component-registry.md

Reference guide for ACM hub components. Covers:

| Section | What It Documents |
|---------|-------------------|
| Top-Level Control Plane | MCH, MCE, OCP ClusterVersion |
| Cluster Management | Managed clusters, klusterlet, lifecycle controllers, add-on manager |
| Search | Search-api, indexer, collector, postgres, v2 operator |
| Governance / Policy (GRC) | Policy propagator, spoke-side controllers |
| Observability | Thanos stack, Grafana, alertmanager, metrics collectors, Minio/S3 |
| Application Lifecycle | Subscription controller, channel controller, GitOps path |
| Console | Console frontend, CLI downloads, console plugins |
| RBAC / User Management | Fine-grained RBAC, cluster permissions |
| Virtualization (Fleet Virt) | CNV integration, kubevirt-plugin |
| Infrastructure Foundation | Nodes, certificates, storage |

For each component, the registry documents:
- **Namespace** -- where it lives (noting that MCH namespace varies)
- **Resource** -- the CRD or API resource
- **Check command** -- how to inspect it
- **Healthy state** -- what healthy looks like
- **Key pods** -- pod names and labels
- **Impact when degraded** -- what breaks when this component fails
- **Common issues** -- frequently observed failure modes

### failure-patterns.md

Cross-component failure correlation heuristics. Organized by category:

| Category | Example Patterns |
|----------|-----------------|
| Platform-Level | MCH stuck progressing, CSVs not succeeded, nodes NotReady |
| Managed Cluster | Multiple clusters Unknown, single cluster Unknown, Joined=False |
| Cross-Component | Search + Observability both broken, console 500 across features |
| Storage-Related | PVC full, Thanos store CrashLoop |
| Upgrade-Related | Components degraded after OCP upgrade, ACM upgrade stuck |
| Certificate | Intermittent TLS failures, webhook failures after rotation |
| Resource Pressure | OOMKilled pods |
| Anti-Patterns | Things that look related but aren't |

Each pattern includes:
- **Symptoms** -- what you observe
- **Heuristic** -- what it likely means
- **Investigate** -- how to verify

### diagnostic-playbooks.md

Per-subsystem investigation procedures for deep dives. Each playbook provides
ordered investigation steps with specific commands:

| Playbook | Steps | Focus |
|----------|-------|-------|
| MCH / MCE Lifecycle | 6 steps | MCH status, operator pods, operator logs, events, install plans |
| Managed Cluster Connectivity | 6 steps | Cluster status, lease renewal, events, addon status, registration, klusterlet |
| Search Subsystem | 5 steps | Search pods, search-api, storage/PVCs, collector addon, MCH config |
| Observability Stack | 7 steps | MCO CR, pods, Thanos components, PVCs/S3, store logs, addons, Grafana |
| Governance / Policy | 5 steps | Propagator, policy summary, addons, work-manager, specific policies |
| Application Lifecycle | 6 steps | Subscription controller, subscriptions, channels, placement, GitOps, addons |
| Console & UI | 5 steps | Console pods, ConsolePlugin CRs, plugin pods, routes, OAuth |
| Node & Infrastructure | 6 steps | Node status, conditions, resource usage, unschedulable, clusterversion, etcd |
| Certificates | 4 steps | TLS secrets, cert expiration, webhook configs, service verification |
| Add-ons (General) | 4 steps | Addon list, status, addon-manager, ClusterManagementAddon |

---

## Layer 2: Learned Knowledge

Discoveries made by the agent during health checks. Stored in
`knowledge/learned/` as individual markdown files.

### When Learned Knowledge Is Created

The agent writes to `knowledge/learned/` when it encounters a mismatch between
static knowledge and cluster state during Phase 2 (Learn):

```
  Phase 2: Learn
       │
       ├── Component X in component-registry.md?
       │        │
       │        ├── Yes ── Details match cluster? ── Yes ── Continue
       │        │                    │
       │        │                    └── No ─── MISMATCH ─── Self-Healing
       │        │
       │        └── No ─── MISMATCH ─── Self-Healing
       │
       ▼
  Continue to Phase 3
```

### Learned Knowledge File Format

```markdown
# <Component/Topic Name>

**Discovered**: <date>
**ACM Version**: <version from MCH>
**Trigger**: <what mismatch was detected>

## What Was Found
<description of what was observed on the cluster>

## Evidence
- **Cluster**: <what oc commands revealed>
- **Docs**: <what rhacm-docs said, with file references>
- **Source**: <what acm-ui MCP revealed, if applicable>

## Understanding
<synthesized explanation of the component/behavior>

## Health Signals
- **Healthy**: <what healthy looks like>
- **Degraded**: <warning signs>
- **Critical**: <failure indicators>

## Relationship to Static Knowledge
<how this relates to or updates existing knowledge>
```

### Conflict Resolution

When static and learned knowledge conflict:

| Scenario | Resolution |
|----------|------------|
| Learned knowledge contradicts static | Learned is more recent, likely more accurate |
| Both contradict the cluster | The cluster is always truth |
| Learned knowledge is stale (old ACM version) | Verify against current cluster before trusting |

---

## Self-Healing Process

When a mismatch is detected, the agent runs a 6-step self-healing process:

```
  MISMATCH DETECTED
         │
         ▼
  ┌──────────────────┐
  │ Step 1: Collect   │     oc describe, labels, annotations,
  │ cluster evidence  │     owner refs, events, namespace check
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 2: Search    │     grep -r "<keyword>" docs/rhacm-docs/
  │ official docs     │     --include="*.adoc" -l
  │ (if available)    │     Read relevant AsciiDoc files
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 3: Search    │     acm-ui MCP: search_code, search_component,
  │ ACM source code   │     get_component_source, get_routes
  │ via MCP           │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 4: Synthesize│     Combine cluster + docs + source evidence.
  │ and resolve       │     Classify as: knowledge gap, knowledge drift,
  │                   │     version-specific change, or actual issue
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 5: Write     │     Write to knowledge/learned/<topic>.md
  │ learned knowledge │     using the standard format
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 6: Continue  │     Use new knowledge for remaining
  │ health check      │     health check phases
  └──────────────────┘
```

### Step 1: Collect Cluster Evidence

```bash
oc describe <resource> -n <namespace>          # Full resource details
oc get <resource> -o yaml                      # Labels, annotations, owner refs
oc get events -n <namespace>                   # Recent events
oc get pods -n <namespace> -l <label>          # Related pods
```

The agent checks:
- Labels and annotations (reveal purpose and owner)
- Owner references (what controller manages this)
- Events in the namespace (recent activity)
- Related resources in the same namespace

### Step 2: Search Official Documentation

If `docs/rhacm-docs/` is cloned (optional):

```bash
grep -r "<component-name>" docs/rhacm-docs/ --include="*.adoc" -l
grep -r "<keyword>" docs/rhacm-docs/ --include="*.adoc" -l
```

Key documentation areas:
- `troubleshooting/` -- symptom-based troubleshooting
- `observability/` -- observability architecture and alerts
- `install/` -- installation, sizing, upgrade procedures
- `clusters/` -- cluster lifecycle management
- `governance/` -- policy framework
- `search/` -- search subsystem
- `virtualization/` -- fleet virtualization
- `health_metrics/` -- metrics and monitoring

If `docs/rhacm-docs/` is not present, this step is skipped.

### Step 3: Search ACM Source Code via MCP

The `acm-ui` MCP server provides access to the stolostron/console and
kubevirt-plugin source code:

Key tools used during self-healing (subset -- see
[04-MCP-AND-EXTERNAL-SOURCES.md](04-MCP-AND-EXTERNAL-SOURCES.md) for the full
19-tool inventory):

| MCP Tool | Purpose |
|----------|---------|
| `search_code` | Search for keywords across the codebase |
| `search_component` | Find a specific React component |
| `get_component_source` | Get the source code of a component |
| `get_routes` | Find route definitions and navigation paths |
| `get_acm_selectors` | Find data-testid attributes |

This reveals how the component integrates with the console, its API endpoints,
and its data flow.

### Step 4: Synthesize and Resolve

The agent combines evidence from all three sources to classify the mismatch:

| Classification | Meaning | Action |
|---------------|---------|--------|
| Knowledge gap | New feature/component not in static knowledge | Document the new component |
| Knowledge drift | Renamed/restructured component | Update with current names |
| Version-specific change | Behavior changed in this ACM version | Document with version annotation |
| Actual issue | Unexpected state that indicates a problem | Report as a finding |

### Step 5: Write Learned Knowledge

Findings are written to `knowledge/learned/<topic>.md` using the standard format
(see "Learned Knowledge File Format" above). The file name reflects the topic
(e.g., `search-postgres-migration.md`, `console-v2-plugin-architecture.md`).

### Step 6: Continue Health Check

The agent uses the newly learned information to complete the remaining phases
with accurate understanding of the component.

---

## Knowledge Refresh: The /learn Command

The `/learn` slash command runs a dedicated knowledge-building session. Instead
of checking health, it focuses on discovering and documenting what's deployed.

```
/learn                    # Full knowledge refresh
/learn observability      # Focused on observability
/learn search             # Focused on search
```

### When to Run /learn

- After upgrading ACM to a new version
- When deploying the agent against a new hub for the first time
- When you want to ensure the knowledge base matches the current cluster state
- After enabling/disabling MCH components

### /learn Process Per Component

1. Check if it exists in `knowledge/component-registry.md`
2. If not, or if details differ, investigate it:
   - Collect detailed info from the cluster
   - Search `docs/rhacm-docs/` for documentation
   - Use `acm-ui` MCP to search source code
3. Write findings to `knowledge/learned/`

---

## Trust Hierarchy

```
  Most trusted                               Least trusted
  ┌──────────┐    ┌───────────────┐    ┌─────────────────────┐
  │  Live    │ >  │   Learned     │ >  │  Static Knowledge   │
  │  Cluster │    │   Knowledge   │    │  (component-registry │
  │          │    │   (learned/)  │    │   failure-patterns    │
  │          │    │               │    │   playbooks)          │
  └──────────┘    └───────────────┘    └─────────────────────┘
```

1. **The cluster is always truth.** If what you see contradicts the knowledge
   files, the cluster wins.
2. **Learned knowledge is more recent.** It was written by the agent during a
   previous run against a specific cluster and ACM version.
3. **Static knowledge is the baseline.** Curated but may be outdated. Use it
   as a starting point, not as gospel.

---

## See Also

- [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) -- Phase 2 (Learn) in the pipeline context
- [04-MCP-AND-EXTERNAL-SOURCES.md](04-MCP-AND-EXTERNAL-SOURCES.md) -- MCP tools used during self-healing
- [00-OVERVIEW.md](00-OVERVIEW.md) -- top-level overview
