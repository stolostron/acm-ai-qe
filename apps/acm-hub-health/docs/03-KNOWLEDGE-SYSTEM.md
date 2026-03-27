# Knowledge System and Self-Healing

The agent uses a layered knowledge system that combines curated architecture
documentation with diagnostic methodology and discoveries from previous health
checks. When the agent encounters something not covered by its knowledge base,
it triggers a self-healing process to investigate, learn, and record findings.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Knowledge System                                  │
│                                                                            │
│  ┌────────────────────────────┐  ┌───────────────────────────────────────┐ │
│  │ Architecture Knowledge     │  │ Diagnostic Knowledge                  │ │
│  │ knowledge/architecture/    │  │ knowledge/diagnostics/                │ │
│  │                            │  │                                       │ │
│  │ Per-component directories: │  │ dependency-chains.md                  │ │
│  │   architecture.md          │  │   6 critical cascade paths            │ │
│  │   data-flow.md             │  │ evidence-tiers.md                     │ │
│  │   known-issues.md          │  │   How to weight evidence (Tier 1/2/3) │ │
│  │                            │  │ diagnostic-playbooks.md               │ │
│  │ + kubernetes-fundamentals  │  │   Per-subsystem investigation steps   │ │
│  │ + acm-platform.md          │  │                                       │ │
│  └────────────────────────────┘  └───────────────────────────────────────┘ │
│                                                                            │
│  ┌────────────────────────────┐  ┌───────────────────────────────────────┐ │
│  │ Cross-Cutting Knowledge    │  │ Structured Operational Data (YAML)    │ │
│  │ knowledge/                 │  │ knowledge/*.yaml                      │ │
│  │                            │  │                                       │ │
│  │ component-registry.md      │  │ healthy-baseline.yaml                 │ │
│  │   Master inventory of ACM  │  │ dependency-chains.yaml                │ │
│  │   components, CRDs, NS     │  │ webhook-registry.yaml                 │ │
│  │ failure-patterns.md        │  │ certificate-inventory.yaml            │ │
│  │   Common failure signatures│  │ addon-catalog.yaml                    │ │
│  │   mapped to root causes    │  │                                       │ │
│  └────────────────────────────┘  └───────────────────────────────────────┘ │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Learned Knowledge                                                      │ │
│  │ knowledge/learned/                                                     │ │
│  │                                                                        │ │
│  │ Written by the agent during health checks when mismatches are detected │ │
│  │ between knowledge and cluster state. Version- and cluster-specific.    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│  Priority: Cluster > Learned > Static                                     │
│  The live cluster is always the source of truth.                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Knowledge

Deep engineering-level documentation about each ACM subsystem, organized in
per-component directories under `knowledge/architecture/`.

### Top-Level Architecture

| File | Content |
|------|---------|
| `kubernetes-fundamentals.md` | K8s primitives that ACM is built on |
| `acm-platform.md` | MCH/MCE hierarchy, operator lifecycle, addon framework |

### Per-Component Directories

Components with full coverage (`architecture.md`, `data-flow.md`, `known-issues.md`):

| Component | What It Covers |
|-----------|---------------|
| `search/` | Search API, indexer, collector, postgres, federated search |
| `governance/` | Policy framework, propagator, spoke controllers, compliance |
| `observability/` | Thanos stack, Grafana, alertmanager, metrics pipeline |
| `cluster-lifecycle/` | Managed clusters, provisioning, import, klusterlet |
| `console/` | Console frontend, plugins, API integration |
| `application-lifecycle/` | Subscriptions, channels, GitOps, placement |
| `virtualization/` | Fleet virtualization, CNV integration, MTV |
| `rbac/` | Fine-grained RBAC, cluster permissions |

Components with partial coverage:

| Component | Files | What It Covers |
|-----------|-------|---------------|
| `addon-framework/` | `architecture.md` | Addon manager, ClusterManagementAddon lifecycle |
| `networking/` | `architecture.md`, `known-issues.md` | Submariner, service discovery |
| `infrastructure/` | `architecture.md`, `known-issues.md` | Nodes, storage, certificates |

### How Architecture Knowledge Is Used

1. **Phase 2 (Learn):** Read `architecture.md` to understand how a component
   should work before checking if it's broken
2. **Phase 4 (Pattern Match):** Read `known-issues.md` to match symptoms
   against documented bugs with JIRA references
3. **Phase 6 (Deep Investigate):** Read `data-flow.md` to trace where the
   data flow is broken

---

## Diagnostic Knowledge

Health-check-specific methodology in `knowledge/diagnostics/`:

### dependency-chains.md

Documents 6 critical cascade paths with tracing procedures:

1. **Console → Search → Managed Clusters** -- search-collector down = resources missing
2. **Governance → Framework Addon → Config Policy → Clusters** -- policy propagation chain
3. **MCH Operator → Backplane → Component Operators** -- operator hierarchy
4. **HyperShift Addon → Import Controller → Klusterlet** -- hosted cluster import
5. **MCRA → ClusterPermission → ManifestWork → RBAC** -- fine-grained RBAC propagation
6. **Observability Operator → Addon → Thanos** -- metrics pipeline

Used in Phase 5 (Correlate) to trace upstream from symptoms to root causes.

### evidence-tiers.md

Rules for weighting evidence:

| Tier | Type | Example |
|------|------|---------|
| **Tier 1** | Definitive | Error message in logs, pod status, resource condition |
| **Tier 2** | Strong | Event history, restart pattern, timing correlation |
| **Tier 3** | Circumstantial | Version match, similar past behavior, documentation |

Evidence combination rules:
- Every conclusion needs 2+ evidence sources
- At least one should be Tier 1
- State confidence level based on evidence combination
- Rule out alternatives before concluding

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

## Structured Operational Data

Quantitative YAML files for comparing cluster state against known-good values.
These complement the narrative documentation with machine-readable reference data.

| File | Content | Used In |
|------|---------|---------|
| `healthy-baseline.yaml` | Expected pod counts, deployment states, node thresholds | Phase 3 (Check) -- compare actual vs expected |
| `dependency-chains.yaml` | 6 cascade paths in structured YAML | Phase 5 (Correlate) -- structured lookups |
| `webhook-registry.yaml` | Validating/mutating webhooks, failure policies | Phase 3 (Check) -- detect missing webhooks |
| `certificate-inventory.yaml` | TLS secrets, rotation, impact when corrupted | Phase 6 (Deep) -- cert investigation |
| `addon-catalog.yaml` | All addons, health checks, dependencies | Phase 3 (Check) -- addon health audit |

### healthy-baseline.yaml

Defines what "normal" looks like for a healthy ACM hub:
- MCH/MCE expected phases and conditions
- Pod count ranges per namespace
- Critical deployments with minimum replicas
- Node thresholds (CPU, memory, disk)
- Expected managed cluster conditions
- Required addons per feature

### dependency-chains.yaml

Structured YAML complement to `diagnostics/dependency-chains.md`. Same 6 chains
in a format suitable for programmatic lookups:
- Each chain has components with roles and dependencies
- Impact descriptions per failure point
- Cross-chain patterns linking shared causes

### webhook-registry.yaml

All validating and mutating webhook configurations expected on an ACM hub:
- Owner, namespace, failure policy
- What each webhook is critical for
- Impact when broken
- Common webhook issues and resolutions

### certificate-inventory.yaml

TLS secrets per namespace:
- What component uses each secret
- Who manages rotation (service-ca vs manual)
- Impact when corrupted
- Check commands for expiry and issuer

### addon-catalog.yaml

All managed cluster addons with operational details:
- Required vs optional, default enabled state
- Health check commands
- Dependencies between addons
- Impact when unhealthy

### Refreshing Structured Data

Run the refresh script to update knowledge from a live cluster:

```bash
python -m knowledge.refresh                 # Refresh all YAML files from connected cluster
python -m knowledge.refresh --baseline      # Update healthy-baseline.yaml
python -m knowledge.refresh --webhooks      # Update webhook-registry.yaml
python -m knowledge.refresh --certs         # Update certificate-inventory.yaml
python -m knowledge.refresh --addons        # Update addon-catalog.yaml
python -m knowledge.refresh --promote       # Review learned/ entries for promotion
python -m knowledge.refresh --dry-run       # Show what would change without writing
```

All refresh flags use smart merge: new items found on the cluster are added
with placeholder descriptions, existing curated content (impact descriptions,
dependencies, diagnostic guidance) is preserved, and items no longer on the
cluster are flagged but kept. The script also detects version drift between
YAML metadata and the cluster's actual ACM version.

---

## Cross-Cutting Knowledge

Top-level reference files spanning all components:

### component-registry.md

Master inventory of ACM hub components. For each component, documents:
- **Namespace** -- where it lives (noting that MCH namespace varies)
- **Resource** -- the CRD or API resource
- **Check command** -- how to inspect it
- **Healthy state** -- what healthy looks like
- **Key pods** -- pod names and labels
- **Impact when degraded** -- what breaks when this component fails
- **Common issues** -- frequently observed failure modes

### failure-patterns.md

Cross-component failure correlation heuristics:

| Category | Example Patterns |
|----------|-----------------|
| Platform-Level | MCH stuck progressing, CSVs not succeeded, nodes NotReady |
| Managed Cluster | Multiple clusters Unknown, single cluster Unknown, Joined=False |
| Cross-Component | Search + Observability both broken, console 500 across features |
| Storage-Related | PVC full, Thanos store CrashLoop |
| Upgrade-Related | Components degraded after OCP upgrade, ACM upgrade stuck |
| Certificate | Intermittent TLS failures, webhook failures after rotation |
| Resource Pressure | OOMKilled pods |

---

## Learned Knowledge

Discoveries made by the agent during health checks. Stored in
`knowledge/learned/` as individual markdown files.

### When Learned Knowledge Is Created

The agent writes to `knowledge/learned/` when it encounters a mismatch between
static knowledge and cluster state during Phase 2 (Learn):

```
  Phase 2: Learn
       │
       ├── Component X in knowledge base?
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

| Scenario | Resolution |
|----------|------------|
| Learned knowledge contradicts static | Learned is more recent, likely more accurate |
| Both contradict the cluster | The cluster is always truth |
| Learned knowledge is stale (old ACM version) | Verify against current cluster before trusting |

---

## Self-Healing Process

When a mismatch is detected, the agent runs a self-healing process:

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

### Mismatch Classification

| Classification | Meaning | Action |
|---------------|---------|--------|
| Knowledge gap | New feature/component not in static knowledge | Document the new component |
| Knowledge drift | Renamed/restructured component | Update with current names |
| Version-specific change | Behavior changed in this ACM version | Document with version annotation |
| Actual issue | Unexpected state that indicates a problem | Report as a finding |

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

---

## Trust Hierarchy

```
  Most trusted                               Least trusted
  ┌──────────┐    ┌───────────────┐    ┌─────────────────────┐
  │  Live    │ >  │   Learned     │ >  │  Static Knowledge   │
  │  Cluster │    │   Knowledge   │    │  (architecture/     │
  │          │    │   (learned/)  │    │   diagnostics/       │
  │          │    │               │    │   cross-cutting)     │
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

- [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) -- Phase 2 (Learn) and Phase 4 (Pattern Match) in the pipeline context
- [04-MCP-AND-EXTERNAL-SOURCES.md](04-MCP-AND-EXTERNAL-SOURCES.md) -- MCP tools used during self-healing
- [00-OVERVIEW.md](00-OVERVIEW.md) -- top-level overview
