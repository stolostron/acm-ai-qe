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
│  │   architecture.md          │  │   11 critical cascade paths           │ │
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
│  Topology (what exists): Cluster observation > Learned > Static            │
│  Health (what's correct): Knowledge defines ground truth; cluster shows    │
│  current state; the gap between them = findings to diagnose               │
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
| `cluster-lifecycle/` | Managed clusters, provisioning, import, klusterlet, hub-side health patterns |
| `console/` | Console frontend, plugins, API integration |
| `application-lifecycle/` | Subscriptions, channels, GitOps, placement |
| `virtualization/` | Fleet virtualization, CNV integration, MTV |
| `rbac/` | Fine-grained RBAC, cluster permissions |

All components have full coverage (`architecture.md`, `data-flow.md`, `known-issues.md`):

| Component | What It Covers |
|-----------|---------------|
| `automation/` | ClusterCurator, AAP integration, cluster upgrade hooks |
| `addon-framework/` | Addon manager, ManifestWork delivery, addon health |
| `networking/` | Submariner, tunnels, service discovery, GlobalNet |
| `infrastructure/` | Nodes, storage, certificates, etcd + `post-upgrade-patterns.md` |

### How Knowledge Is Used Across Phases

1. **Phase 2 (Learn):** Read `architecture.md` to understand how a component
   should work. Read `diagnostic-layers.md` + `common-diagnostic-traps.md`
   to prepare for layer-organized checking and avoid misdiagnoses.
2. **Phase 3 (Check):** Use `diagnostic-layers.md` for layer-organized
   health checks — foundational layers (network, storage) before component
   layers (operators, pods).
3. **Phase 4 (Pattern Match):** Read `known-issues.md` to match symptoms
   against documented bugs with JIRA references
4. **Phase 5 (Correlate):** Use `dependency-chains.md` for horizontal
   tracing and `diagnostic-layers.md` for vertical layer tracing.
5. **Phase 6 (Deep Investigate):** Read `data-flow.md` to trace where the
   data flow is broken. Use `diagnostic-layers.md` as fallback when no
   playbook matches.

---

## Diagnostic Knowledge

Health-check-specific methodology in `knowledge/diagnostics/`:

### diagnostic-layers.md

The 12-layer diagnostic model provides a systematic investigation framework
for finding root causes. Each layer is a distinct failure domain -- a failure
at a lower layer cascades upward and manifests as symptoms at higher layers.
The layers (bottom to top): Compute, Control Plane, Network, Storage,
Configuration, Auth, RBAC, API/CRD/Webhook, Operator, Cross-Cluster, Data
Flow, UI/Plugin. Used in Phase 3 (layer-organized health checking), Phase 5
(vertical tracing), and Phase 6 (fallback for unknown issues).

### dependency-chains.md

Documents 11 critical cascade paths with tracing procedures:

1. **Console → Search → Managed Clusters** -- search-collector down = resources missing
2. **Governance → Framework Addon → Config Policy → Clusters** -- policy propagation chain
3. **MCH Operator → Backplane → Component Operators** -- operator hierarchy
4. **HyperShift Addon → Import Controller → Klusterlet** -- hosted cluster import
5. **MCRA → ClusterPermission → ManifestWork → RBAC** -- fine-grained RBAC propagation
6. **Observability Operator → Addon → Thanos** -- metrics pipeline
7. **Addon Manager → Addon Framework → Spoke Addon Pods** -- single point of failure for all addons
8. **StorageClass → CSI Driver → PV → PVC → Pod** -- persistent storage for stateful components
9. **Channel → Subscription → ManifestWork → Spoke Application** -- app deployment via subscription model
10. **CNV → Search Collector → Search API → kubevirt-plugin → Console** -- cross-cluster VM discovery
11. **SubmarinerConfig → Addon → Gateway → Tunnel → Service Discovery** -- cross-cluster networking

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
| Networking / Submariner | 8 steps | Addon deployed, operator, broker, gateway, tunnels, OCP compat, DNS |
| RBAC / User Management | 6 steps | FG-RBAC enabled, MCRA controller, ClusterPermission, acm-roles addon |
| Addon Framework Deep | 6 steps | addon-manager health, CMA registrations, ManifestWork, work-agent, finalizers |
| Hive / Cluster Provisioning | 6 steps | Hive operator, ClusterDeployment, provision jobs, cloud creds, webhook |

### common-diagnostic-traps.md

13 patterns where the obvious diagnosis is WRONG. Each trap describes what you
see, what you might conclude, and what's actually happening:

| Trap | Symptom | What to Check First |
|------|---------|---------------------|
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

Loaded in Phase 2 (Learn). Verified against in Phase 5 (Correlate) before
finalizing any diagnosis.

---

## Structured Operational Data

Quantitative YAML files for comparing cluster state against known-good values.
These complement the narrative documentation with machine-readable reference data.

| File | Content | Used In |
|------|---------|---------|
| `healthy-baseline.yaml` | Expected pod counts, deployment states, node thresholds | Phase 3 (Check) -- compare actual vs expected |
| `dependency-chains.yaml` | 11 cascade paths in structured YAML | Phase 5 (Correlate) -- structured lookups |
| `webhook-registry.yaml` | Validating/mutating webhooks, failure policies | Phase 3 (Check) -- detect missing webhooks |
| `certificate-inventory.yaml` | TLS secrets, rotation, impact when corrupted | Phase 6 (Deep) -- cert investigation |
| `addon-catalog.yaml` | All addons, health checks, dependencies | Phase 3 (Check) -- addon health audit |
| `version-constraints.yaml` | Known version incompatibilities | Phase 4 (Pattern Match) -- version-aware diagnosis |

### healthy-baseline.yaml

Defines what "normal" looks like for a healthy ACM hub:
- MCH/MCE expected phases and conditions
- Pod count ranges per namespace
- Critical deployments with minimum replicas
- Node thresholds (CPU, memory, disk)
- Expected managed cluster conditions
- Required addons per feature

### dependency-chains.yaml

Structured YAML complement to `diagnostics/dependency-chains.md`. Same 11 chains
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

Run `python -m knowledge.refresh` to update YAML files from a live cluster
(requires Python 3 + PyYAML). See
[knowledge/README.md](../knowledge/README.md) for all flags (--baseline,
--webhooks, --certs, --addons, --promote, --dry-run) and smart merge behavior.

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
| Learned knowledge contradicts static (topology) | Learned is more recent, use it for structural facts |
| Learned knowledge contradicts static (health definition) | Learned may reflect version-specific changes; verify against cluster + docs |
| Cluster state differs from knowledge-defined healthy state | The deviation IS the finding. Knowledge defines what correct looks like; diagnose and report the gap |
| Cluster topology differs from knowledge (namespace, pod names) | Trust the cluster observation. Trigger self-healing to update knowledge |
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
  │ Step 2: CLUSTER   │     Reverse-engineer dependencies from
  │ INTROSPECTION     │     live metadata: owner refs, OLM labels,
  │ (live metadata)   │     CSV owned CRDs, env vars with .svc
  │                   │     refs, webhooks, ConsolePlugins,
  │                   │     APIServices (always available)
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 3: CROSS-    │     neo4j-rhacm MCP: supplement the
  │ REFERENCE WITH    │     cluster-derived map with broader
  │ KNOWLEDGE GRAPH   │     ACM component relationships
  │                   │     (skipped if container unavailable)
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 4: UNDERSTAND│     For each dependency from steps 2-3:
  │ DEPENDENCIES      │     acm-ui MCP: search source code for
  │ (acm-ui MCP +     │     implementation details, data flow
  │  rhacm-docs)      │     rhacm-docs: search for intended behavior
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 5: Synthesize│     Combine cluster evidence + introspection
  │ and resolve       │     + graph + source + docs. Classify as:
  │                   │     knowledge gap, knowledge drift,
  │                   │     version-specific change, or actual issue
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 6: Write     │     Write to knowledge/learned/<topic>.md
  │ learned knowledge │     using the standard format
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Step 7: Continue  │     Use new knowledge for remaining
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

## Knowledge Roles and Trust Model

The knowledge database serves the agent in two distinct roles, each with a
different relationship to the live cluster:

### Role 1: Structural Observation (Topology)

What exists on this cluster: namespaces, pod names, which components are
deployed, CRD schemas. These vary per cluster and per ACM version.

```
  Trust for topology:  Cluster observation > Learned > Static
```

If the knowledge says search-api runs in `open-cluster-management` but the
agent observes it in `ocm`, the agent uses `ocm`. The knowledge was wrong
about the structural fact. This triggers self-healing -- the agent writes to
`knowledge/learned/` to update its topology understanding.

### Role 2: Health Assessment (Correctness)

What correct, healthy behavior looks like: expected phases, pod states,
data flows, component interactions, known bug signatures.

```
  Trust for correctness:  Knowledge (ground truth) defines what SHOULD BE
                          Cluster observation shows what IS
                          The gap between the two = findings to diagnose
```

The knowledge defines the ground truth for health:
- `healthy-baseline.yaml` says `expected_phase: Running` -- if the cluster
  shows `Progressing`, that gap IS the finding
- `architecture.md` describes how data should flow -- a deviation is a
  problem to diagnose, not a new truth to accept
- `known-issues.md` defines bug signatures -- the agent matches cluster
  symptoms against them to identify known bugs
- `evidence-tiers.md` defines how to weight evidence for conclusions

The cluster is NOT "right" when it shows CrashLoopBackOff. The knowledge
says pods should be Running. The agent reports the deviation as an issue.

### Between Knowledge Layers

When knowledge layers disagree about topology or health definitions:

1. **Learned knowledge is more recent.** Written during a previous run
   against a specific cluster and ACM version. Preferred over static.
2. **Static knowledge is the curated baseline.** May be outdated for newer
   ACM versions. Use as a starting point, verify against the cluster.
3. **When learned knowledge is stale** (written for an older ACM version),
   verify against the current cluster before trusting.

---

## See Also

- [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) -- Phase 2 (Learn) and Phase 4 (Pattern Match) in the pipeline context
- [04-MCP-AND-EXTERNAL-SOURCES.md](04-MCP-AND-EXTERNAL-SOURCES.md) -- MCP tools used during self-healing
- [00-OVERVIEW.md](00-OVERVIEW.md) -- top-level overview
