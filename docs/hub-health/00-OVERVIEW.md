# ACM Hub Health Agent Overview

AI-powered diagnostic and remediation agent for Red Hat Advanced Cluster Management
(ACM) hub clusters. Uses Claude Code with embedded ACM domain knowledge to perform
health checks at any depth -- from quick sanity checks to deep component-level
investigations. Diagnosis is read-only; fixes are executed only after presenting
a structured remediation plan and getting explicit user approval.

**Input:** An `oc` session logged into an ACM hub cluster
**Output:** Structured health report with verdicts, findings, and remediation plan

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
  "/investigate search"    │  /deep, /investigate, /learn     │
  "/learn"                 │                                  │
                           └──────────┬───────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
          │   oc CLI     │  │  Knowledge   │  │  External Sources│
          │              │  │    System    │  │                  │
          │  Diagnosis:  │  │              │  │  ACM-UI MCP      │
          │  oc get      │  │  architecture│  │  (source code)   │
          │  oc describe │  │  diagnostics │  │                  │
          │  oc logs     │  │  cross-cut   │  │  neo4j-rhacm MCP │
          │  Remediation:│  │  learned     │  │  (dependency     │
          │  oc patch    │  │              │  │   graph)         │
          │  (w/approval)│  │              │  │                  │
          │              │  │              │  │  acm-search MCP  │
          │              │  │              │  │  (fleet queries) │
          │              │  │              │  │                  │
          │              │  │              │  │  rhacm-docs/     │
          │              │  │              │  │  (AsciiDoc)      │
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

              ┌──────────────────────────────────────────────┐
              │           Session Tracing                    │
              │  (Claude Code hooks → .claude/traces/)      │
              │                                              │
              │  Every tool call, MCP interaction, prompt,   │
              │  and error → structured JSONL trace file     │
              │  + session index with aggregate stats        │
              └──────────────────────────────────────────────┘
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
│              │        │ Inventory│        │ Consult  │        │ Layer-   │
│  sanity      │        │ the hub  │        │ knowledge│        │ organized│
│  standard    │        │          │        │ + self-  │        │ health   │
│  deep        │        │          │        │ heal gaps│        │ checks   │
│  targeted    │        │          │        │          │        │ (L1→L12) │
└──────────────┘        └──────────┘        └──────────┘        └──────────┘
                                                                      │
                            ┌──────────────────────────────────────────┘
                            │
                       PHASE 4             PHASE 5             PHASE 6
                    ┌──────────┐        ┌──────────┐        ┌──────────┐
                    │ PATTERN  │  ───►  │CORRELATE │  ───►  │  DEEP    │
                    │ MATCH    │        │          │        │INVESTIGATE│
                    │          │        │ Horiz +  │        │          │
                    │ Known    │        │ vertical │        │ Logs,    │
                    │ bug?     │        │ root     │        │ events + │
                    │          │        │ cause    │        │ layer    │
                    │          │        │ tracing  │        │ fallback │
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

The agent uses a layered knowledge system: architecture docs, structured YAML
baselines, diagnostic methodology, cross-cutting references, and learned
knowledge from previous runs. When the agent encounters something not in its
knowledge, it triggers a self-healing process to investigate and record findings.

See [03-KNOWLEDGE-SYSTEM.md](03-KNOWLEDGE-SYSTEM.md) for the full architecture,
trust model, and self-healing process.

---

## Safety Model

The agent operates in two modes:

- **Diagnostic mode** (Phases 1-6): Strictly read-only, fully auto-approved.
  The user is NEVER prompted for permission during diagnosis. All read-only
  `oc` commands, file tools (Read, Glob, Grep), data processing (`python3`),
  subagent spawning (Agent), and MCP tools are auto-approved.
- **Remediation mode** (post-diagnosis): The agent may fix cluster-fixable
  issues, but ONLY after completing all diagnosis, presenting a structured
  remediation plan with root causes and exact commands, and receiving
  explicit user approval. Mutation commands (`oc patch`, `oc scale`, etc.)
  are NOT auto-approved -- Claude Code prompts for permission on each one,
  providing a second safety layer on top of the plan-approval flow.

Enforced at two levels: CLAUDE.md Remediation Protocol (methodology requires
structured approval flow) and `.claude/settings.json` (auto-approved
diagnostic commands, mutation commands require permission). Destructive
commands (`oc delete` on non-pod resources,
`oc adm drain`) are never allowed.

See the "Safety" and "Remediation Protocol" sections in
[CLAUDE.md](../CLAUDE.md) for the full details.

---

## Slash Commands

| Command | Purpose | Phases | Typical Time |
|---------|---------|--------|--------------|
| `/sanity` | Quick pulse check | Phase 1 | ~30s |
| `/health-check` | Standard diagnostic | Phases 1-4 | ~2-3 min |
| `/deep` | Full deep audit | All 6 phases | ~5-10 min |
| `/investigate <target>` | Deep targeted investigation | All 6 phases | varies |
| `/learn [area]` | Knowledge-building session | Discovery + learning | varies |

Users can also interact naturally:
```
Is my hub healthy?
Check if search is working
Why are my managed clusters showing Unknown?
/deep
```

---

## Directory Structure

```
acm-hub-health/
├── CLAUDE.md                           ← Agent methodology and instructions
├── README.md                           ← Quick start guide
├── acm-hub                             ← CLI wrapper (run from any terminal)
├── setup.sh                            ← One-time setup (rhacm-docs, MCP venv, .mcp.json)
├── .mcp.json                           ← MCP server configuration (acm-ui, neo4j-rhacm, acm-search) [generated by setup.sh]
├── .gitignore                          ← Ignores docs/rhacm-docs/, .claude/traces/
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
│   ├── service-map.yaml                ← Critical Service-to-Pod mappings for connectivity diagnosis
│   ├── webhook-registry.yaml           ← Validating/mutating webhooks and their impact
│   ├── certificate-inventory.yaml      ← TLS secrets, rotation, and corruption impact
│   ├── addon-catalog.yaml              ← Addon health checks, dependencies, expectations
│   ├── version-constraints.yaml        ← Known product version incompatibilities
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
│   │   ├── automation/                 ← architecture.md, data-flow.md, known-issues.md
│   │   ├── addon-framework/            ← architecture.md, data-flow.md, known-issues.md
│   │   ├── networking/                 ← architecture.md, data-flow.md, known-issues.md
│   │   └── infrastructure/             ← architecture.md, data-flow.md, known-issues.md, post-upgrade-patterns.md
│   ├── diagnostics/                    ← Health check methodology (8 files)
│   │   ├── diagnostic-layers.md        ← 12-layer investigation framework
│   │   ├── dependency-chains.md        ← 12 critical cascade paths (narrative)
│   │   ├── common-diagnostic-traps.md  ← 14 patterns where obvious diagnosis is wrong
│   │   ├── evidence-tiers.md           ← Evidence weighting rules
│   │   ├── diagnostic-playbooks.md     ← Per-subsystem investigation procedures
│   │   ├── cluster-introspection.md    ← 8 metadata sources for reverse-engineering deps
│   │   ├── neo4j-reference.md          ← Knowledge graph Cypher queries reference
│   │   └── acm-search-reference.md     ← Search MCP tool parameters and query patterns
│   └── learned/                        ← Agent-discovered knowledge (grows over time)
│       └── <topic>.md                  ← Written by agent during self-healing
│
└── .claude/
    ├── settings.json                   ← Auto-approved commands, hook configuration
    ├── settings.local.json             ← Local overrides (not committed)
    ├── commands/
    │   ├── sanity.md                   ← /sanity slash command
    │   ├── health-check.md             ← /health-check slash command
    │   ├── deep.md                     ← /deep slash command
    │   ├── investigate.md              ← /investigate slash command
    │   └── learn.md                    ← /learn slash command
    ├── hooks/
    │   └── agent_trace.py              ← Session tracing hook (JSONL trace per session)
    └── traces/                         ← Trace output (gitignored)
        ├── <session-id>.jsonl          ← Per-session detailed trace
        └── sessions.jsonl              ← Session index with aggregate stats
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Minimal custom code | Core agent is pure Claude Code with no runtime dependencies beyond `oc` and `claude`. Uses cluster introspection (8 live metadata sources via `oc` commands) and three MCP servers (acm-ui for source code search, neo4j-rhacm for dependency graph queries, acm-search for fleet-wide resource queries via the search database). Custom code: `.claude/hooks/agent_trace.py` (session tracing hook, stdlib only, runs automatically) and `knowledge/refresh.py` (optional, for updating YAML baselines from a live cluster; requires Python 3 + PyYAML). |
| Diagnose-first, fix-with-approval | Diagnosis is always read-only. Fixes are only attempted after all findings are presented and the user explicitly approves the remediation plan. No per-command prompts -- one structured approval for the full plan. |
| Layered knowledge (architecture + diagnostics + structured YAML + learned) | Architecture knowledge explains how things work. Structured YAML provides quantitative baselines. Diagnostics knowledge guides methodology. Learned knowledge fills version-specific gaps. |
| File-based knowledge database (not SQL) | No database server dependency. YAML/markdown files are human-readable, git-tracked, and diffable. Claude reads them directly into context. |
| Self-healing over static docs | ACM evolves across versions. Components are renamed, restructured, or added. The agent adapts by investigating and learning, rather than requiring manual knowledge updates. |
| Evidence-based diagnosis | Every conclusion requires 2+ evidence sources with confidence levels. Prevents false positives and builds trust. |
| Pattern matching before reasoning | Check known-issues.md for documented bugs before reasoning from scratch. Many issues are known bugs with JIRA references and fix versions. |
| Depth router (not modes) | Users describe what they want in natural language. The agent maps intent to the right depth. No need to remember mode names. |
| Per-namespace discovery | MCH namespace is not always `open-cluster-management`. Can be `ocm` or custom. The agent discovers the actual namespace first, then uses it for all subsequent checks. |
| Session tracing via hooks | All tool calls, MCP interactions, prompts, and errors are traced to structured JSONL files via Claude Code hooks. Enriched with diagnostic-specific metadata: `oc` verb/resource/namespace parsing, mutation detection, knowledge file phase inference, and session-level aggregate stats. No runtime dependencies -- the hook is a standalone Python script invoked by Claude Code's hook system. |

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
