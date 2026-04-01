# Depth Router

The depth router interprets the user's natural language request and selects which
phases of the diagnostic pipeline to run. Users never need to think about "modes"
or "phases" -- they describe what they want, and the router maps that to the
appropriate depth.

---

## Overview

```
                        User Input
                            │
                            ▼
                   ┌─────────────────┐
                   │  Depth Router   │
                   │                 │
                   │  Analyzes user  │
                   │  language to    │
                   │  determine      │
                   │  intent         │
                   └────────┬────────┘
                            │
              ┌─────────────┼─────────────┬──────────────┐
              │             │             │              │
              ▼             ▼             ▼              ▼
       ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
       │   Quick   │ │ Standard  │ │   Deep    │ │ Targeted  │
       │   Pulse   │ │   Check   │ │   Audit   │ │   Invest. │
       │           │ │           │ │           │ │           │
       │ Phase 1   │ │ Phases    │ │ All 6     │ │ All 6     │
       │ only      │ │ 1-4       │ │ Phases    │ │ Phases    │
       │           │ │           │ │           │ │ (scoped)  │
       │ ~30s      │ │ ~2-3 min  │ │ ~5-10 min │ │ varies    │
       └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

---

## Depth Levels

### Quick Pulse

**Phases:** Phase 1 (Discover) only
**Time:** ~30 seconds
**Slash command:** `/sanity`

Runs the minimum checks to determine if the hub is fundamentally alive. Checks
MCH status, MCE status, node health, managed cluster connectivity, and operator
CSVs. Reports only immediate red flags.

**Trigger phrases:**
- "sanity check"
- "quick look"
- "is my hub alive"
- "pulse check"

**What it checks:**

| Check | Command | Looking For |
|-------|---------|-------------|
| MCH status | `oc get mch -A -o yaml` | `phase: Running`, all components `status: "True"` |
| MCE status | `oc get multiclusterengines -A -o yaml` | `phase: Available` |
| Node health | `oc get nodes` | All nodes Ready |
| OCP version | `oc get clusterversion` | Available=True, Progressing=False |
| Managed clusters | `oc get managedclusters` | All Available=True, Joined=True |
| Operator CSVs | `oc get csv -n <mch-ns>` and `oc get csv -n multicluster-engine` | All Succeeded |
| Cluster identity | `oc whoami --show-server` | Confirms connectivity |

**What it does NOT check:**
- Individual pod health
- Logs or events
- Storage (PVCs)
- Add-on status on spokes
- Known issue matching
- Cross-component correlation

**Output:** Compact component status table with overall verdict.

---

### Standard Check

**Phases:** Phases 1-4 (Discover, Learn, Check, Pattern Match)
**Time:** ~2-3 minutes
**Slash command:** `/health-check`

The default depth. Discovers what's deployed, consults the architecture
knowledge, systematically verifies each component's health, then matches
any findings against known bug patterns with JIRA references.

**Trigger phrases:**
- "health check"
- "how's my hub"
- "check my cluster"
- No specific depth indicator (default)

**What it adds over Quick Pulse:**

| Addition | Details |
|----------|---------|
| Component discovery | Identifies all enabled MCH components from `.spec.overrides.components` |
| Architecture knowledge | Reads `knowledge/architecture/<component>/` for each component |
| Self-healing | Investigates any components not in the knowledge base |
| Pod-level checks | Checks pods in MCH namespace, MCE namespace, observability namespace, hive namespace |
| Non-Running pod detection | `--field-selector=status.phase!=Running,status.phase!=Succeeded` |
| Operator log scanning | Checks for known error patterns in controller logs |
| Add-on status | `oc get managedclusteraddons -A` |
| Restart count analysis | Flags pods with high restart counts |
| Known issue matching | Compares findings against `known-issues.md` per component |
| Version-aware diagnosis | Checks exact ACM/MCE version and matches to fix versions |

**Output:** Full health report with component status table, any issues found
(with JIRA references when matched), and cluster overview.

---

### Deep Audit

**Phases:** All 6 (Discover, Learn, Check, Pattern Match, Correlate, Deep Investigate)
**Time:** ~5-10 minutes
**Slash command:** `/deep`

Runs the complete pipeline. After checking all components and matching known
issues, traces dependency chains to identify root causes across components,
then performs deep investigation of any critical findings including log
analysis, event review, and storage checks.

**Trigger phrases:**
- "deep dive"
- "thorough check"
- "full audit"
- "investigate everything"
- "comprehensive"

**What it adds over Standard Check:**

| Addition | Details |
|----------|---------|
| Dependency chain tracing | Uses `knowledge/diagnostics/dependency-chains.md` to trace root causes |
| Evidence-tier weighting | Applies `knowledge/diagnostics/evidence-tiers.md` rules |
| Cross-component correlation | Identifies shared dependencies causing multiple symptoms |
| Log analysis | `oc logs` for any degraded components |
| Event review | `oc get events -n <namespace>` for affected namespaces |
| Storage verification | `oc get pvc` across all relevant namespaces |
| Resource usage | `oc adm top pods` / `oc adm top nodes` |
| Previous crash logs | `oc logs --previous` for pods with high restart counts |
| Data flow tracing | Reads component `data-flow.md` to identify where flow is broken |

**Output:** Full health report with evidence-based findings, confidence levels,
and cross-component correlation.

---

### Targeted Investigation

**Phases:** All 6, scoped to the target area and its dependencies
**Time:** Varies by target complexity
**Slash command:** `/investigate <target>`

Focuses on a specific component, symptom, or area. Runs all 6 phases but scoped
to the target. Includes the target's dependencies and related components.

**Trigger phrases:**
- "check search"
- "why are managed clusters Unknown"
- "is observability working"
- "investigate governance"
- "what's wrong with <component>"

**How scoping works:**

```
User: "investigate observability"
                │
                ▼
    ┌───────────────────────┐
    │  Target: Observability │
    ├───────────────────────┤
    │  Primary scope:        │
    │  - MCO CR              │
    │  - All pods in obs ns  │
    │  - Thanos components   │
    │  - Grafana, Alertmgr   │
    │  - Metrics collectors  │
    │  - Minio/S3 storage    │
    │                        │
    │  Dependencies:         │
    │  - MCH (parent)        │
    │  - Spoke addons        │
    │  - PVCs / storage      │
    │  - Routes / networking │
    ├───────────────────────┤
    │  Knowledge consulted:  │
    │  architecture/         │
    │    observability/      │
    │  diagnostics/          │
    │    diagnostic-playbooks│
    │    dependency-chains   │
    └───────────────────────┘
```

**Output:** Narrative format focused on what was checked, what was found, what
it means, and what to do about it.

---

## Routing Decision Flow

```
                          User Input
                              │
                              ▼
                    ┌─────────────────┐
                    │ Contains depth  │──── "sanity", "quick", ──── Quick Pulse
                    │ keyword?        │     "alive", "pulse"
                    └────────┬────────┘
                             │ no
                             ▼
                    ┌─────────────────┐
                    │ Names specific  │──── "search", "observ", ──── Targeted
                    │ component or    │     "governance", "why",     Investigation
                    │ symptom?        │     "check <X>"
                    └────────┬────────┘
                             │ no
                             ▼
                    ┌─────────────────┐
                    │ Contains deep   │──── "deep", "thorough", ──── Deep Audit
                    │ keyword?        │     "full", "comprehensive"
                    └────────┬────────┘
                             │ no
                             ▼
                      Standard Check
                       (default)
```

The router is not a strict keyword matcher. It uses natural language understanding
to interpret intent. "My search isn't returning results" triggers a targeted
investigation of search even though it doesn't say "investigate."

---

## Depth Comparison Matrix

| Capability | Quick | Standard | Deep | Targeted |
|-----------|-------|----------|------|----------|
| MCH/MCE status | Yes | Yes | Yes | Yes |
| Node health | Yes | Yes | Yes | If relevant |
| Managed cluster status | Yes | Yes | Yes | If relevant |
| CSV status | Yes | Yes | Yes | If relevant |
| Component discovery | No | Yes | Yes | Target area |
| Architecture knowledge | No | Yes | Yes | Yes |
| Self-healing | No | Yes | Yes | Yes |
| Pod-level checks | No | Yes | Yes | Yes (focused) |
| Operator log scanning | No | Yes | Yes | Yes (focused) |
| Add-on status | No | Yes | Yes | If relevant |
| Known issue matching | No | Yes | Yes | Yes |
| Version-aware diagnosis | No | Yes | Yes | Yes |
| Diagnostic trap verification | No | Yes | Yes | Yes |
| Post-upgrade pattern check | No | Yes | Yes | Yes |
| Dependency chain tracing | No | No | Yes | With dependencies |
| Evidence-tier weighting | No | No | Yes | Yes |
| Log analysis | No | No | Yes | Yes |
| Event review | No | No | Yes | Yes |
| Storage checks | No | No | Yes | Yes |
| Resource usage | No | No | Yes | If relevant |
| Previous crash logs | No | No | Yes | Yes |
| Diagnostic playbooks | No | No | Yes | Yes |
| Data flow tracing | No | No | Yes | Yes |

---

## See Also

- [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) -- detailed Phase 1-6 procedures
- [06-SLASH-COMMANDS.md](06-SLASH-COMMANDS.md) -- slash command reference
- [00-OVERVIEW.md](00-OVERVIEW.md) -- top-level overview
