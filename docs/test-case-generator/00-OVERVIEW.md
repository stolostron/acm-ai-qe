# ACM Console Test Case Generator Overview

Generates Polarion-ready test cases for ACM Console UI features from JIRA tickets. The pipeline uses 6 specialized Claude Code subagents, 7 MCP integrations, deterministic Python scripts for data gathering and report generation, and mandatory quality gating before output.

## Architecture

```
                 ┌─────────────────────────────────────┐
                 │         Claude Code (main)           │
                 │     Orchestrator: /generate cmd      │
                 └────────────┬────────────────────────┘
                              │
           ┌──────────────────┼──────────────────────┐
           │                  │                      │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌───────────▼──────────┐
    │  Phase 0    │   │  Stage 1    │   │     Phase 1          │
    │  Ask Qs     │   │  gather.py  │   │  3 parallel agents   │
    │  (if needed)│   │  (Python)   │   │  JIRA + Code + UI    │
    └──────┬──────┘   └──────┬──────┘   └───────────┬──────────┘
           │                  │                      │
           └──────────────────┼──────────────────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 2      │
                     │   Synthesize    │
                     │  (orchestrator) │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 3      │
                     │  Live Validate  │
                     │  (optional)     │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 4      │
                     │  Write Test     │
                     │  Case (agent)   │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │   Phase 4.5     │
                     │  Quality Gate   │
                     │  (agent, loop)  │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Stage 3      │
                     │   report.py     │
                     │   (Python)      │
                     └─────────────────┘
```

## Pipeline Stages

The pipeline has 8 steps: 2 deterministic stages + 6 AI phases. "6-phase" in the tagline counts the AI phases only. The portable skill pack uses a 10-phase model that breaks investigation into 3 sequential phases; the app consolidates them into 1 parallel phase. See the README "Concepts" section for the full mapping.

| Phase/Stage | Type | Agent/Script | Duration | Input | Output |
|------------|------|-------------|----------|-------|--------|
| Phase 0 | Interactive | Orchestrator | ~10 sec | User args | Resolved inputs |
| Stage 1 | Deterministic | `gather.py` | ~2-5 sec | JIRA ID, options | `gather-output.json`, `pr-diff.txt` |
| Phase 1 | AI (parallel) | 3 subagents | ~30-60 sec | gather-output | FEATURE INVESTIGATION, CODE CHANGE ANALYSIS, UI DISCOVERY RESULTS |
| Phase 2 | AI (orchestrator) | Main context | ~10 sec | 3 agent outputs | SYNTHESIZED CONTEXT with TEST PLAN |
| Phase 3 | AI (optional) | live-validator | ~2-5 min | Console URL, steps | LIVE VALIDATION RESULTS |
| Phase 4 | AI | test-case-generator | ~30-60 sec | Synthesized context | `test-case.md`, `analysis-results.json` |
| Phase 4.5 | AI (gate) | quality-reviewer | ~30-60 sec | test-case.md | PASS or NEEDS_FIXES (3-tier escalation) |
| Stage 3 | Deterministic | `report.py` | ~1 sec | test-case.md | HTML, `review-results.json`, `SUMMARY.txt` |

## Agents

| Agent | Phase | MCP Tools | Role |
|-------|-------|-----------|------|
| Feature Investigator | 1 (parallel) | jira, polarion, neo4j-rhacm, bash | JIRA deep dive: ACs, comments, linked tickets, Polarion coverage |
| Code Change Analyzer | 1 (parallel) | acm-ui, neo4j-rhacm, bash | PR diff analysis: changed components, UI elements, interaction models |
| UI Discovery | 1 (parallel) | acm-ui, neo4j-rhacm, playwright (conditional), bash | ACM Console source: selectors, translations, routes, wizard steps + optional live verification |
| Live Validator | 3 | playwright, acm-search, acm-kubectl, bash | Browser + oc CLI + fleet queries on real cluster |
| Test Case Generator | 4 | acm-ui | Write test case markdown from synthesized context |
| Quality Reviewer | 4.5 | acm-ui, polarion | Convention compliance, discovered vs assumed, AC vs implementation |

## MCP Servers

| Server | Tools | Source | Purpose |
|--------|-------|--------|---------|
| acm-ui | 20 | This repo (`mcp/acm-ui-mcp-server/`) | ACM Console source code search via GitHub |
| jira | 3 | [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server) | JIRA ticket investigation |
| polarion | 7 | This repo (`mcp/polarion/`) | Existing Polarion test case coverage |
| neo4j-rhacm | 2 | [mcp-neo4j-cypher](https://pypi.org/project/mcp-neo4j-cypher/) (PyPI) | Component dependency analysis |
| acm-search | 5 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | Fleet-wide resource queries (live validation) |
| acm-kubectl | 3 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | Multicluster kubectl (live validation) |
| playwright | 24 | [@playwright/mcp](https://www.npmjs.com/package/@playwright/mcp) (npm) | Browser automation (live validation) |

## Run Directory Layout

Each pipeline run produces artifacts under `runs/<JIRA_ID>/<JIRA_ID>-<timestamp>/`:

```
runs/ACM-30459/ACM-30459-2026-04-18T02-00-46/
  gather-output.json                 # Stage 1: all gathered data
  pr-diff.txt                        # Stage 1: full PR diff
  phase1-feature-investigation.md    # Phase 1: feature investigator output (app pipeline)
  phase1-code-change-analysis.md     # Phase 1: code change analyzer output (app pipeline)
  phase1-ui-discovery.md             # Phase 1: UI discovery output (app pipeline)
  phase2-jira.json                   # Phase 2: JIRA findings (portable skill alternate)
  phase3-code.json                   # Phase 3: code analysis (portable skill alternate)
  phase4-ui.json                     # Phase 4: UI discovery (portable skill alternate)
  phase2-synthesized-context.md      # Phase 2: merged investigation + test plan (app pipeline)
  synthesized-context.md             # Phase 5: merged context (portable skill alternate)
  phase3-live-validation.md          # Phase 3: live validation output (app pipeline)
  phase6-live-validation.md          # Phase 6: live validation (portable skill alternate)
  test-case.md                       # Phase 4/7: primary deliverable
  analysis-results.json              # Phase 4/7: investigation metadata
  phase4.5-quality-review.md         # Phase 4.5: quality review output (app pipeline)
  phase8-review.md                   # Phase 8: quality review (portable skill alternate)
  test-case-setup.html               # Stage 3: Polarion setup HTML
  test-case-steps.html               # Stage 3: Polarion steps table HTML
  review-results.json                # Stage 3: structural validation
  SUMMARY.txt                        # Stage 3: human-readable summary
  pipeline.log.jsonl                 # All stages + phases: telemetry
```

## Supported Console Areas

| Area | Tag Pattern | Knowledge File |
|------|------------|----------------|
| Governance | `[GRC-X.XX]` | `architecture/governance.md` |
| RBAC | `[FG-RBAC-X.XX]` | `architecture/rbac.md` |
| Fleet Virtualization | `[FG-RBAC-X.XX] Fleet Virtualization UI` | `architecture/fleet-virt.md` |
| CCLM | `[FG-RBAC-X.XX] CCLM` | `architecture/cclm.md` |
| MTV | `[MTV-X.XX]` | `architecture/mtv.md` |
| Clusters | `[Clusters-X.XX]` | `architecture/clusters.md` |
| Search | `[FG-RBAC-X.XX] Search` | `architecture/search.md` |
| Applications | `[Apps-X.XX]` | `architecture/applications.md` |
| Credentials | `[Credentials-X.XX]` | `architecture/credentials.md` |

All 9 areas have architecture knowledge files providing domain context for agents.

## Directory Structure

```
test-case-generator/
├── src/
│   ├── models/              # Pydantic data models (3 files)
│   ├── services/            # Business logic services (5 files)
│   ├── scripts/             # CLI scripts (gather.py, log_phase.py, report.py)
│   └── templates/           # Markdown skeleton template
├── tests/
│   └── unit/                # Unit tests (4 files, 45 tests)
├── .claude/
│   ├── agents/              # 6 agent definitions
│   ├── skills/              # 3 skill definitions (generate, review, batch)
│   ├── hooks/               # Session tracing hook
│   ├── traces/              # Session trace JSONL files (gitignored)
│   └── settings.json        # Permissions + hooks config
├── knowledge/
│   ├── conventions/         # Test case format rules (4 files)
│   ├── architecture/        # Per-area domain knowledge (9 files)
│   ├── examples/            # Sample test case (1 file)
│   └── patterns/            # Learned patterns from runs (planned)
├── runs/                    # Pipeline output (gitignored)
├── docs/                    # This documentation
├── CLAUDE.md                # App constitution
└── README.md                # Setup and usage guide
```

## Detailed Documentation

| Document | Description |
|----------|-------------|
| [01-PIPELINE-PHASES.md](01-PIPELINE-PHASES.md) | Phase-by-phase pipeline execution |
| [02-AGENTS.md](02-AGENTS.md) | Agent definitions, inputs, outputs, MCP tools |
| [03-MCP-INTEGRATION.md](03-MCP-INTEGRATION.md) | MCP server setup, tools, usage patterns |
| [04-KNOWLEDGE-SYSTEM.md](04-KNOWLEDGE-SYSTEM.md) | Conventions, architecture knowledge, patterns |
| [05-QUALITY-GATES.md](05-QUALITY-GATES.md) | Phase 4.5 reviewer + Stage 3 validator |
| [06-SESSION-TRACING.md](06-SESSION-TRACING.md) | Claude Code hooks, JSONL traces, session summaries |
| [architecture-diagrams.html](architecture-diagrams.html) | Interactive pipeline workflow visualization |
