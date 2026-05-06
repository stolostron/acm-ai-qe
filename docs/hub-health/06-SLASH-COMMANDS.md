# Slash Command Reference

The agent provides five slash commands that map to specific diagnostic workflows.
These are implemented as Claude Code custom commands in `.claude/commands/`.

---

## Overview

```
  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌────────────────┐   ┌──────────────┐
  │   /sanity    │   │ /health-check│   │    /deep     │   │  /investigate  │   │   /learn     │
  │              │   │              │   │              │   │  <target>      │   │   [area]     │
  │  Quick pulse │   │  Standard    │   │  Full audit  │   │                │   │              │
  │  Phase 1     │   │  Phases 1-4  │   │  All 6       │   │  Targeted deep │   │  Knowledge   │
  │  ~30s        │   │  ~2-3 min    │   │  phases      │   │  All 6 phases  │   │  building    │
  │              │   │              │   │  ~5-10 min   │   │  scoped        │   │              │
  └──────────────┘   └──────────────┘   └──────────────┘   └────────────────┘   └──────────────┘
```

Users can also interact with natural language without slash commands. The depth
router interprets intent automatically (see [01-DEPTH-ROUTER.md](01-DEPTH-ROUTER.md)).

---

## /sanity

**File:** `.claude/commands/sanity.md`
**Depth:** Quick pulse (Phase 1 only)
**Time:** ~30 seconds

### What It Does

Runs the minimum checks to determine if the hub is fundamentally alive:
- MCH status and phase
- MCE status and phase
- Node health (all Ready?)
- Managed cluster connectivity (all Available?)
- Operator CSVs (all Succeeded?)
- Cluster identity (connectivity confirmed)

### When to Use

- Morning pulse check
- After a maintenance window to verify recovery
- Quick verification before starting other work
- When you just need a yes/no on hub health

### Usage

```
/sanity
/sanity focus on managed clusters
```

The optional argument can provide additional context or focus, but the check
remains Phase 1 only.

### Output

Compact component status table with overall verdict. See
[05-OUTPUT-AND-REPORTING.md](05-OUTPUT-AND-REPORTING.md) "Quick Pulse Output" section.

### Example

```
/sanity
```

Produces:

```markdown
# Hub Health Report: ashafi-acm-216-ga
## Overall Verdict: HEALTHY

## Component Status
| Component | Status | Details |
|-----------|--------|---------|
| MCH | OK | Phase: Running, v2.16.0 -- "All hub components ready" |
| MCE | OK | Phase: Available, v2.11.0 |
| OCP | OK | v4.21.5, Available, not progressing |
| Nodes | OK | 6/6 Ready (3 master, 3 worker) |
| Managed Clusters | OK | 2/2 Available |
| ACM CSV | OK | Succeeded |
| MCE CSV | OK | Succeeded |

## Cluster Overview
- **ACM Version**: 2.16.0
- **MCE Version**: 2.11.0
- **OCP Version**: 4.21.5
- **MCH Namespace**: `ocm`
- **Nodes**: 6 Ready
- **Managed Clusters**: 2 Available
```

---

## /health-check

**File:** `.claude/commands/health-check.md`
**Depth:** Standard (Phases 1-4)
**Time:** ~2-3 minutes

### What It Does

Full standard diagnostic following the 6-phase methodology (Phases 1-4):

1. **Discover** -- Inventory the hub (MCH, MCE, nodes, clusters, CSVs)
2. **Learn** -- Consult architecture knowledge, self-heal any gaps
3. **Check** -- Verify health of each discovered component (pods, conditions,
   add-ons, restart counts, operator log patterns)
4. **Pattern Match** -- Match findings against known bugs with JIRA references

### When to Use

- Regular health checks
- After deploying changes to the hub
- When investigating general hub stability
- Default depth when unsure what to check

### Usage

```
/health-check
/health-check pay attention to observability
```

The optional argument can provide focus areas that receive extra attention,
but all components are still checked.

**CLI wrapper:** The `acm-hub` CLI accepts both `check` and `health-check`
as command names -- both invoke this slash command.

### Output

Full health report with component status table, any issues found, and cluster
overview. See [05-OUTPUT-AND-REPORTING.md](05-OUTPUT-AND-REPORTING.md) "Standard
Health Report Format" section.

---

## /deep

**File:** `.claude/commands/deep.md`
**Depth:** Full audit (All 6 phases)
**Time:** ~5-10 minutes

### What It Does

Runs a thorough deep audit of the entire hub using all 6 phases:

1. **Discover** -- Full hub inventory
2. **Learn** -- Architecture knowledge for every deployed component
3. **Check** -- Health of every component (pods, logs, operator patterns)
4. **Pattern Match** -- Match all findings against known bugs with JIRA references
5. **Correlate** -- Trace dependency chains, find root causes across components
6. **Deep Investigate** -- Logs, events, storage, networking for critical findings

### When to Use

- When you want a comprehensive audit of the entire hub
- After major upgrades or configuration changes
- When multiple components may be affected
- When you need a complete picture before planning remediation

### Usage

```
/deep
/deep focus on storage and certificates
```

The optional argument can provide additional context or focus areas, but
all components are checked at full depth.

### Output

Full health report with all findings correlated. See
[05-OUTPUT-AND-REPORTING.md](05-OUTPUT-AND-REPORTING.md).

---

## /investigate

**File:** `.claude/commands/investigate.md`
**Depth:** Targeted (All 6 phases, scoped)
**Time:** Varies by target complexity

### What It Does

Deep targeted investigation of a specific component, symptom, or area. Runs
all 6 phases scoped to the target:

1. **Discover** -- Full hub inventory (context)
2. **Learn** -- Architecture knowledge about the target and its dependencies
3. **Check** -- Health of the target component (pods, logs, operator patterns)
4. **Pattern Match** -- Match against known bugs with JIRA references
5. **Correlate** -- Trace dependency chains to find root cause
6. **Deep Investigate** -- Logs, events, storage, data flow tracing

### When to Use

- When a specific component is suspected to be broken
- When a symptom needs root cause analysis
- When you need detailed information about a specific area
- After `/health-check` identifies an issue worth investigating

### Usage

```
/investigate observability
/investigate search
/investigate why managed clusters are Unknown
/investigate governance policy propagation
```

The argument specifies the target. It can be:
- A component name: `observability`, `search`, `governance`, `console`
- A symptom: `why managed clusters are Unknown`, `search returns no results`
- A subsystem: `storage`, `certificates`, `networking`

### Output

Narrative format focused on the target. See [05-OUTPUT-AND-REPORTING.md](05-OUTPUT-AND-REPORTING.md)
"Targeted Investigation Output" section.

### Investigation Scoping

The target determines what gets checked:

| Target | Primary Scope | Dependencies Checked |
|--------|--------------|---------------------|
| `observability` | MCO CR, all obs pods, Thanos components, Grafana, collectors, S3/Minio | MCH, PVCs, spoke addons, routes |
| `search` | Search pods (api, indexer, collector, postgres, operator) | MCH, PVCs, spoke collector addons |
| `governance` | Policy propagator, policy summary, compliance status | MCH, spoke addons, work-manager |
| `managed clusters` | Per-cluster status, conditions, leases | Registration controller, addons per cluster |
| `console` | Console pods, ConsolePlugin CRs, routes | MCH, OAuth, plugin pods |
| `certificates` | TLS secrets, expiration dates | Webhook configurations, services |

---

## /learn

**File:** `.claude/commands/learn.md`
**Depth:** Discovery + Learning (not a health check)
**Time:** Varies

### What It Does

Runs a knowledge-building session against the current cluster. Instead of
checking health, focuses on discovering and documenting what's deployed:

1. For every component found on the cluster:
   - Check if it exists in static knowledge (`knowledge/component-registry.md`)
   - If not, or if details differ, investigate it:
     - Collect detailed info from the cluster (`oc describe`, labels, owner refs)
     - Reverse-engineer dependencies from cluster metadata (owner refs, OLM
       labels, CSV metadata, env vars, webhooks, ConsolePlugins, APIServices)
     - Cross-reference with `neo4j-rhacm` MCP for broader dependency coverage
     - Search `docs/rhacm-docs/` for documentation
     - Use `acm-source` MCP to search source code
   - Write findings to `knowledge/learned/`

### When to Use

- After upgrading ACM to a new version
- When deploying the agent against a new hub for the first time
- When you want to ensure the knowledge base matches the current cluster
- After enabling/disabling MCH components

### Usage

```
/learn                    # Full knowledge refresh (all components)
/learn observability      # Focused on observability subsystem
/learn search             # Focused on search subsystem
/learn console            # Focused on console architecture
```

The optional argument scopes the learning to a specific area.

### Output

Summary of what was discovered and what was written to `knowledge/learned/`.
Lists any mismatches found between knowledge and cluster state, and what
was learned to resolve them.

### Knowledge Files Written

Files are written to `knowledge/learned/<topic>.md` using the standard format
documented in [03-KNOWLEDGE-SYSTEM.md](03-KNOWLEDGE-SYSTEM.md).

---

## Command Implementation

Slash commands are implemented as markdown files in `.claude/commands/`:

```
.claude/commands/
├── sanity.md               # /sanity
├── health-check.md         # /health-check
├── deep.md                 # /deep
├── investigate.md          # /investigate <target>
└── learn.md                # /learn [area]
```

Each file contains a brief prompt that instructs the agent on what to do.
The `$ARGUMENTS` placeholder captures any additional text the user provides
after the command.

### Command File Structure

Each command file ends with a `$ARGUMENTS` line that captures user input. The
wording varies per command:

| Command | Arguments Line |
|---------|---------------|
| `/sanity` | `If additional context is provided: $ARGUMENTS` |
| `/health-check` | `If additional context or focus area is provided: $ARGUMENTS` |
| `/deep` | `If additional context is provided: $ARGUMENTS` |
| `/investigate` | `Target to investigate: $ARGUMENTS` |
| `/learn` | `If a specific area to learn about is provided: $ARGUMENTS` |

The agent reads the command prompt and executes the appropriate diagnostic
workflow according to the methodology defined in `CLAUDE.md`.

---

## Natural Language Alternatives

Users don't need to use slash commands. The depth router handles natural
language:

| Slash Command | Natural Language Equivalents |
|--------------|----------------------------|
| `/sanity` | "quick check", "is my hub alive", "sanity check" |
| `/health-check` | "health check", "how's my hub", "check my cluster" |
| `/deep` | "deep dive", "full audit", "thorough check" |
| `/investigate observability` | "investigate observability", "check observability in depth" |
| `/learn` | "learn about what's deployed", "refresh your knowledge" |

See [01-DEPTH-ROUTER.md](01-DEPTH-ROUTER.md) for the full routing logic.

---

## See Also

- [01-DEPTH-ROUTER.md](01-DEPTH-ROUTER.md) -- depth routing from natural language
- [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) -- pipeline phases each command invokes
- [05-OUTPUT-AND-REPORTING.md](05-OUTPUT-AND-REPORTING.md) -- output format for each depth
- [00-OVERVIEW.md](00-OVERVIEW.md) -- top-level overview
