# ACM Hub Health Agent Overview

AI-powered diagnostic agent for Red Hat Advanced Cluster Management (ACM) hub clusters.
Uses Claude Code with embedded ACM domain knowledge to perform read-only health
checks at any depth -- from quick sanity checks to deep component-level investigations.

**Input:** An `oc` session logged into an ACM hub cluster
**Output:** Structured health report with verdicts, findings, and recommended actions

---

## Architecture

```
                           ┌──────────────────────────────────┐
                           │          Claude Code CLI         │
                           │  ┌────────────────────────────┐  │
                           │  │       CLAUDE.md            │  │
                           │  │  (Agent Methodology)       │  │
                           │  │  - Safety constraints      │  │
                           │  │  - 6-phase pipeline        │  │
                           │  │  - Depth router            │  │
                           │  │  - Output format           │  │
                           │  │  - Self-healing rules      │  │
                           │  └────────────────────────────┘  │
                           │                                  │
  User ────────────────────►  Slash Commands                  │
  "check my hub"           │  /sanity, /health-check,         │
  "/investigate search"    │  /investigate, /learn             │
  "/learn"                 │                                  │
                           └──────────┬───────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
          │   oc CLI     │  │  Knowledge   │  │  External Sources│
          │ (read-only)  │  │    System    │  │                  │
          │              │  │              │  │  ACM-UI MCP      │
          │  oc get      │  │  architecture│  │  (source code)   │
          │  oc describe │  │  diagnostics │  │                  │
          │  oc logs     │  │  cross-cut   │  │  rhacm-docs/     │
          │  oc adm top  │  │  learned     │  │  (AsciiDoc)      │
          └──────────────┘  └──────────────┘  └──────────────────┘
                    │                 │                 │
                    └─────────────────┼─────────────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │    Health Report      │
                           │                       │
                           │  Verdict: HEALTHY /   │
                           │    DEGRADED / CRITICAL │
                           │  Component table      │
                           │  Issue details        │
                           │  Recommended actions  │
                           └──────────────────────┘
```

---

## How It Works

The agent operates through a 6-phase diagnostic pipeline, with a depth router
that selects which phases to run based on the user's intent:

```
  DEPTH ROUTER              PHASE 1            PHASE 2             PHASE 3
┌──────────────┐        ┌──────────┐        ┌──────────┐        ┌──────────┐
│  Interpret   │  ───►  │ DISCOVER │  ───►  │  LEARN   │  ───►  │  CHECK   │
│  user intent │        │          │        │          │        │          │
│              │        │ Inventory│        │ Consult  │        │ Verify   │
│  sanity      │        │ the hub  │        │ knowledge│        │ health   │
│  standard    │        │          │        │ + self-  │        │ of each  │
│  deep        │        │          │        │ heal gaps│        │ component│
│  targeted    │        │          │        │          │        │          │
└──────────────┘        └──────────┘        └──────────┘        └──────────┘
                                                                      │
                            ┌──────────────────────────────────────────┘
                            │
                       PHASE 4             PHASE 5             PHASE 6
                    ┌──────────┐        ┌──────────┐        ┌──────────┐
                    │ PATTERN  │  ───►  │CORRELATE │  ───►  │  DEEP    │
                    │ MATCH    │        │          │        │INVESTIGATE│
                    │          │        │ Cross-   │        │          │
                    │ Known    │        │ component│        │ Logs,    │
                    │ bug?     │        │ root     │        │ events,  │
                    │          │        │ cause    │        │ storage, │
                    │          │        │          │        │ network  │
                    └──────────┘        └──────────┘        └──────────┘
```

| Depth | Trigger Phrases | Phases Run | Time |
|-------|----------------|------------|------|
| Quick pulse | "sanity check", "quick look", "is my hub alive" | Phase 1 only | ~30s |
| Standard | "health check", "how's my hub" (default) | Phases 1-4 | ~2-3 min |
| Deep audit | "deep dive", "full audit", "thorough check" | All 6 phases | ~5-10 min |
| Targeted | "check search", "investigate observability" | All 6 phases on target area | varies |

---

## Knowledge System

The agent uses a layered knowledge system that combines curated architecture
documentation with diagnostics methodology and discoveries from previous runs:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Knowledge System                                  │
│                                                                            │
│  ┌──────────────────────────┐  ┌──────────────────────────────────────────┐│
│  │ Architecture Knowledge   │  │ Diagnostic Knowledge                     ││
│  │ knowledge/architecture/  │  │ knowledge/diagnostics/                   ││
│  │                          │  │                                          ││
│  │ Per-component:           │  │ dependency-chains.md (6 cascade paths)   ││
│  │   architecture.md        │  │ evidence-tiers.md (Tier 1/2/3 rules)    ││
│  │   data-flow.md           │  │ diagnostic-playbooks.md (procedures)    ││
│  │   known-issues.md        │  │                                          ││
│  └──────────────────────────┘  └──────────────────────────────────────────┘│
│                                                                            │
│  ┌──────────────────────────┐  ┌──────────────────────────────────────────┐│
│  │ Cross-Cutting Knowledge  │  │ Learned Knowledge                        ││
│  │ knowledge/               │  │ knowledge/learned/                       ││
│  │                          │  │                                          ││
│  │ component-registry.md    │  │ Written by the agent during health       ││
│  │ failure-patterns.md      │  │ checks when it discovers things not      ││
│  │                          │  │ covered by the static knowledge.         ││
│  └──────────────────────────┘  └──────────────────────────────────────────┘│
│                                                                            │
│  Priority: Cluster > Learned > Static                                     │
│  The live cluster is always the source of truth.                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

When the agent encounters a component or behavior not covered by its
knowledge, it triggers a self-healing process:

1. Collects more evidence from the live cluster (`oc describe`, labels, events)
2. Searches official ACM documentation (`docs/rhacm-docs/`)
3. Searches ACM Console source code via the `acm-ui` MCP server
4. Synthesizes findings and resolves the mismatch
5. Writes discoveries to `knowledge/learned/<topic>.md`
6. Future runs read these discoveries alongside the static knowledge

---

## Safety Model

All cluster operations are **read-only**. The agent never modifies cluster state.

| Allowed | Blocked |
|---------|---------|
| `oc get`, `oc describe`, `oc logs` | `oc apply`, `oc create`, `oc delete` |
| `oc api-resources`, `oc version` | `oc patch`, `oc edit`, `oc scale` |
| `oc whoami`, `oc cluster-info` | `oc rollout restart`, `oc adm drain` |
| `oc adm top`, `kubectl get/describe` | Any command that modifies state |
| `jq`, `grep`, `wc`, `sort`, `head`, `tail`, `awk`, `cut` | |
| `cat`, `ls`, `find` | |

These constraints are enforced at two levels:
1. **CLAUDE.md instructions** -- the agent methodology explicitly forbids mutation
2. **settings.json permissions** -- only read-only `oc` commands are auto-approved

If a fix requires changes, the agent tells the user what to do. It does not do it itself.

---

## Slash Commands

| Command | Purpose | Phases | Typical Time |
|---------|---------|--------|--------------|
| `/sanity` | Quick pulse check | Phase 1 | ~30s |
| `/health-check` | Standard diagnostic | Phases 1-4 | ~2-3 min |
| `/investigate <target>` | Deep targeted investigation | All 6 phases | varies |
| `/learn [area]` | Knowledge-building session | Discovery + learning | varies |

Users can also interact naturally:
```
Is my hub healthy?
Check if search is working
Why are my managed clusters showing Unknown?
Do a thorough deep dive of my hub
```

---

## Directory Structure

```
acm-hub-health/
├── CLAUDE.md                           ← Agent methodology and instructions
├── README.md                           ← Quick start guide
├── setup.sh                            ← One-time setup (rhacm-docs, MCP venv, .mcp.json)
├── .mcp.json                           ← MCP server configuration (acm-ui) [generated by setup.sh]
├── .gitignore                          ← Ignores docs/rhacm-docs/
│
├── docs/
│   ├── 00-OVERVIEW.md                  ← This file
│   ├── 01-DEPTH-ROUTER.md             ← Depth routing system
│   ├── 02-DIAGNOSTIC-PIPELINE.md      ← 6-phase pipeline details
│   ├── 03-KNOWLEDGE-SYSTEM.md         ← Knowledge layers and self-healing
│   ├── 04-MCP-AND-EXTERNAL-SOURCES.md ← MCP integration and docs
│   ├── 05-OUTPUT-AND-REPORTING.md     ← Output format and verdicts
│   ├── 06-SLASH-COMMANDS.md           ← Command reference
│   └── rhacm-docs/                     ← Official ACM docs clone (gitignored)
│
├── knowledge/
│   ├── component-registry.md           ← Master inventory of ACM components, CRDs, namespaces
│   ├── failure-patterns.md             ← Cross-component failure signatures
│   ├── healthy-baseline.yaml           ← Expected pod counts, deployment states, conditions
│   ├── dependency-chains.yaml          ← Structured YAML complement to diagnostics/ chains
│   ├── webhook-registry.yaml           ← Validating/mutating webhooks and their impact
│   ├── certificate-inventory.yaml      ← TLS secrets, rotation, and corruption impact
│   ├── addon-catalog.yaml              ← Addon health checks, dependencies, expectations
│   ├── refresh.py                      ← Updates YAML files from live cluster
│   ├── architecture/                   ← Per-component architecture, data-flow, known-issues
│   │   ├── kubernetes-fundamentals.md
│   │   ├── acm-platform.md
│   │   ├── search/                     ← architecture.md, data-flow.md, known-issues.md
│   │   ├── governance/                 ← "
│   │   ├── observability/              ← "
│   │   ├── cluster-lifecycle/          ← "
│   │   ├── console/                    ← "
│   │   ├── application-lifecycle/      ← "
│   │   ├── virtualization/             ← "
│   │   ├── rbac/                       ← "
│   │   ├── addon-framework/            ← architecture.md
│   │   ├── networking/                 ← architecture.md, known-issues.md
│   │   └── infrastructure/             ← architecture.md, known-issues.md
│   ├── diagnostics/                    ← Health check methodology
│   │   ├── dependency-chains.md        ← 6 critical cascade paths (narrative)
│   │   ├── evidence-tiers.md           ← Evidence weighting rules
│   │   └── diagnostic-playbooks.md     ← Per-subsystem investigation procedures
│   └── learned/                        ← Agent-discovered knowledge (grows over time)
│       └── <topic>.md                  ← Written by agent during self-healing
│
└── .claude/
    ├── settings.json                   ← Auto-approved read-only commands
    ├── settings.local.json             ← Local overrides (not committed)
    └── commands/
        ├── sanity.md                   ← /sanity slash command
        ├── health-check.md             ← /health-check slash command
        ├── investigate.md              ← /investigate slash command
        └── learn.md                    ← /learn slash command
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Minimal custom code | Core agent is pure Claude Code with no runtime dependencies beyond `oc` and `claude`. The only custom code is `knowledge/refresh.py` (optional, for updating YAML baselines from a live cluster; requires Python 3 + PyYAML). |
| Read-only constraint | Safety for production hubs. The agent diagnoses; humans remediate. |
| Layered knowledge (architecture + diagnostics + structured YAML + learned) | Architecture knowledge explains how things work. Structured YAML provides quantitative baselines. Diagnostics knowledge guides methodology. Learned knowledge fills version-specific gaps. |
| File-based knowledge database (not SQL) | No database server dependency. YAML/markdown files are human-readable, git-tracked, and diffable. Claude reads them directly into context. |
| Self-healing over static docs | ACM evolves across versions. Components are renamed, restructured, or added. The agent adapts by investigating and learning, rather than requiring manual knowledge updates. |
| Evidence-based diagnosis | Every conclusion requires 2+ evidence sources with confidence levels. Prevents false positives and builds trust. |
| Pattern matching before reasoning | Check known-issues.md for documented bugs before reasoning from scratch. Many issues are known bugs with JIRA references and fix versions. |
| Depth router (not modes) | Users describe what they want in natural language. The agent maps intent to the right depth. No need to remember mode names. |
| Per-namespace discovery | MCH namespace is not always `open-cluster-management`. Can be `ocm` or custom. The agent discovers the actual namespace first, then uses it for all subsequent checks. |

---

## Detailed Documentation

| Topic | File |
|-------|------|
| Depth routing system | [01-DEPTH-ROUTER.md](01-DEPTH-ROUTER.md) |
| 6-phase diagnostic pipeline | [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) |
| Knowledge system and self-healing | [03-KNOWLEDGE-SYSTEM.md](03-KNOWLEDGE-SYSTEM.md) |
| MCP and external source integration | [04-MCP-AND-EXTERNAL-SOURCES.md](04-MCP-AND-EXTERNAL-SOURCES.md) |
| Output format and reporting | [05-OUTPUT-AND-REPORTING.md](05-OUTPUT-AND-REPORTING.md) |
| Slash command reference | [06-SLASH-COMMANDS.md](06-SLASH-COMMANDS.md) |
