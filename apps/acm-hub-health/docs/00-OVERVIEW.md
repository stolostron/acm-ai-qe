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
                           │  │  - 5-phase pipeline        │  │
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
          │  oc get      │  │  Static:     │  │  (source code)   │
          │  oc describe │  │  component-  │  │                  │
          │  oc logs     │  │  registry.md │  │  rhacm-docs/     │
          │  oc adm top  │  │  failure-    │  │  (AsciiDoc)      │
          │              │  │  patterns.md │  │                  │
          │              │  │  diagnostic- │  │                  │
          │              │  │  playbooks.md│  │                  │
          │              │  │              │  │                  │
          │              │  │  Learned:    │  │                  │
          │              │  │  learned/*.md│  │                  │
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

The agent operates through a 5-phase diagnostic pipeline, with a depth router
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
                       PHASE 4             PHASE 5
                    ┌──────────┐        ┌──────────┐
                    │CORRELATE │  ───►  │  DEEP    │
                    │          │        │INVESTIGATE│
                    │ Cross-   │        │          │
                    │ component│        │ Logs,    │
                    │ analysis │        │ events,  │
                    │          │        │ storage, │
                    │          │        │ network  │
                    └──────────┘        └──────────┘
```

| Depth | Trigger Phrases | Phases Run | Time |
|-------|----------------|------------|------|
| Quick pulse | "sanity check", "quick look", "is my hub alive" | Phase 1 only | ~30s |
| Standard | "health check", "how's my hub" (default) | Phases 1-3 | ~2-3 min |
| Deep audit | "deep dive", "full audit", "thorough check" | All 5 phases | ~5-10 min |
| Targeted | "check search", "investigate observability" | All 5 phases on target area | varies |

---

## Self-Healing Knowledge

The agent uses a two-layer knowledge system that improves over time:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Knowledge System                            │
│                                                                 │
│  Layer 1: Static                    Layer 2: Learned            │
│  ┌─────────────────────────┐       ┌─────────────────────────┐  │
│  │  component-registry.md  │       │  learned/<topic>.md     │  │
│  │  failure-patterns.md    │       │                         │  │
│  │  diagnostic-playbooks.md│       │  Written by the agent   │  │
│  │                         │       │  during health checks   │  │
│  │  Curated reference      │       │  when it discovers      │  │
│  │  material. May become   │       │  mismatches between     │  │
│  │  outdated as ACM        │       │  knowledge and cluster  │  │
│  │  evolves.               │       │  state.                 │  │
│  └─────────────────────────┘       └─────────────────────────┘  │
│                                                                 │
│  When Layer 1 and Layer 2 conflict, Layer 2 is more recent     │
│  and likely more accurate -- but always verify against the      │
│  live cluster.                                                  │
└─────────────────────────────────────────────────────────────────┘
```

When the agent encounters a component or behavior not covered by its static
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
| `git clone` (rhacm-docs only) | |

These constraints are enforced at two levels:
1. **CLAUDE.md instructions** -- the agent methodology explicitly forbids mutation
2. **settings.json permissions** -- only read-only `oc` commands are auto-approved

If a fix requires changes, the agent tells the user what to do. It does not do it itself.

---

## Slash Commands

| Command | Purpose | Phases | Typical Time |
|---------|---------|--------|--------------|
| `/sanity` | Quick pulse check | Phase 1 | ~30s |
| `/health-check` | Standard diagnostic | Phases 1-3 | ~2-3 min |
| `/investigate <target>` | Deep targeted investigation | All 5 phases | varies |
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
├── .mcp.json                           ← MCP server configuration (acm-ui)
├── .gitignore                          ← Ignores docs/rhacm-docs/
│
├── docs/
│   ├── 00-OVERVIEW.md                  ← This file
│   ├── 01-DEPTH-ROUTER.md             ← Depth routing system
│   ├── 02-DIAGNOSTIC-PIPELINE.md      ← 5-phase pipeline details
│   ├── 03-KNOWLEDGE-SYSTEM.md         ← Knowledge layers and self-healing
│   ├── 04-MCP-AND-EXTERNAL-SOURCES.md ← MCP integration and docs
│   ├── 05-OUTPUT-AND-REPORTING.md     ← Output format and verdicts
│   ├── 06-SLASH-COMMANDS.md           ← Command reference
│   └── rhacm-docs/                     ← Official ACM docs clone (git ignored)
│
├── knowledge/
│   ├── component-registry.md           ← Static: ACM component reference
│   ├── failure-patterns.md             ← Static: cross-component failure heuristics
│   ├── diagnostic-playbooks.md         ← Static: per-subsystem investigation procedures
│   └── learned/                        ← Dynamic: agent-discovered knowledge
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
| No custom code (pure Claude Code) | Zero dependencies beyond `oc` and `claude`. No Python, no containers, no infrastructure to maintain. |
| Read-only constraint | Safety for production hubs. The agent diagnoses; humans remediate. |
| Two-layer knowledge | Static knowledge provides a baseline. Learned knowledge fills gaps. Neither is trusted blindly -- the cluster is always truth. |
| Self-healing over static docs | ACM evolves across versions. Components are renamed, restructured, or added. The agent adapts by investigating and learning, rather than requiring manual knowledge updates. |
| Depth router (not modes) | Users describe what they want in natural language. The agent maps intent to the right depth. No need to remember mode names. |
| Per-namespace discovery | MCH namespace is not always `open-cluster-management`. Can be `ocm` or custom. The agent discovers the actual namespace first, then uses it for all subsequent checks. |

---

## Detailed Documentation

| Topic | File |
|-------|------|
| Depth routing system | [01-DEPTH-ROUTER.md](01-DEPTH-ROUTER.md) |
| 5-phase diagnostic pipeline | [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) |
| Knowledge system and self-healing | [03-KNOWLEDGE-SYSTEM.md](03-KNOWLEDGE-SYSTEM.md) |
| MCP and external source integration | [04-MCP-AND-EXTERNAL-SOURCES.md](04-MCP-AND-EXTERNAL-SOURCES.md) |
| Output format and reporting | [05-OUTPUT-AND-REPORTING.md](05-OUTPUT-AND-REPORTING.md) |
| Slash command reference | [06-SLASH-COMMANDS.md](06-SLASH-COMMANDS.md) |
