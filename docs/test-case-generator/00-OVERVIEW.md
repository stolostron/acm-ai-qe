# ACM Console Test Case Generator Overview

Generates Polarion-ready test cases for ACM Console UI features from JIRA tickets. The pipeline uses 7 specialized Claude Code subagents (Phases 2-8), 7 MCP integrations, deterministic Python scripts for data gathering and report generation, and mandatory quality gating before output. Runs as a portable skill pack from `.claude/skills/acm-test-case-generator/`.

## Architecture

```
                 ┌─────────────────────────────────────┐
                 │         Claude Code (main)           │
                 │  Orchestrator: /generate skill       │
                 └────────────┬────────────────────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 0      │
                     │  Parse Inputs   │
                     │  (orchestrator) │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 1      │
                     │   gather.py     │
                     │   (Python)      │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 2      │
                     │  JIRA Story     │
                     │  (subagent)     │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 3      │
                     │  Code Analysis  │
                     │  (subagent)     │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 4      │
                     │  UI Discovery   │
                     │  (subagent)     │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 5      │
                     │   Synthesize    │
                     │  (subagent)     │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 6      │
                     │  Live Validate  │
                     │  (optional)     │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 7      │
                     │  Write Test     │
                     │  Case (subagent)│
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 8      │
                     │  Quality Gate   │
                     │  (subagent)     │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 9      │
                     │   report.py     │
                     │   (Python)      │
                     └─────────────────┘
```

## Pipeline Phases

10 phases (0-9): 2 deterministic Python scripts (Phases 1 and 9), 7 AI-driven subagents (Phases 2-8), and 1 interactive orchestrator step (Phase 0). Each subagent runs in an isolated context, writes structured output to disk, and terminates.

| Phase | Type | Agent/Script | Duration | Input | Output |
|:-----:|------|-------------|----------|-------|--------|
| 0 | Interactive | Orchestrator | ~10 sec | User args | Resolved inputs |
| 1 | Deterministic | `scripts/gather.py` | ~2-5 sec | JIRA ID, options | `gather-output.json`, `pr-diff.txt` |
| 2 | AI (subagent) | jira-investigator | ~15-30 sec | JIRA ID | `phase2-jira.json` |
| 3 | AI (subagent) | code-analyzer | ~15-30 sec | PR number, repo | `phase3-code.json` |
| 4 | AI (subagent) | ui-discoverer | ~15-30 sec | ACM version, area | `phase4-ui.json` |
| 5 | AI (subagent) | synthesizer | ~10 sec | Phase 2-4 outputs | `synthesized-context.md` |
| 6 | AI (subagent, optional) | live-validator | ~2-5 min | Console URL | `phase6-live-validation.md` |
| 7 | AI (subagent) | test-case-writer | ~30-60 sec | Synthesized context | `test-case.md`, `analysis-results.json` |
| 8 | AI (subagent, gate) | quality-reviewer | ~30-60 sec | test-case.md | PASS or NEEDS_FIXES (3-tier escalation) |
| 9 | Deterministic | `scripts/report.py` | ~1 sec | test-case.md | HTML, `review-results.json`, `SUMMARY.txt` |

## Subagents

| Agent | Phase | MCP Tools | Role |
|-------|:-----:|-----------|------|
| JIRA Investigator | 2 | jira, polarion, neo4j-rhacm, bash | JIRA deep dive: ACs, comments, linked tickets, Polarion coverage |
| Code Analyzer | 3 | acm-ui, neo4j-rhacm, bash | PR diff analysis: changed components, UI elements, interaction models |
| UI Discoverer | 4 | acm-ui, neo4j-rhacm, playwright (conditional), bash | ACM Console source: selectors, translations, routes, wizard steps |
| Synthesizer | 5 | — | Merge investigation outputs, scope gate, AC cross-reference, test plan |
| Live Validator | 6 | playwright, acm-search, acm-kubectl, bash | Browser + oc CLI + fleet queries on real cluster |
| Test Case Writer | 7 | acm-ui | Write test case markdown from synthesized context |
| Quality Reviewer | 8 | acm-ui, polarion | Convention compliance, discovered vs assumed, AC vs implementation |

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
  gather-output.json                 # Phase 1: all gathered data
  pr-diff.txt                        # Phase 1: full PR diff
  phase2-jira.json                   # Phase 2: JIRA investigation findings
  phase3-code.json                   # Phase 3: code change analysis
  phase4-ui.json                     # Phase 4: UI element discovery
  synthesized-context.md             # Phase 5: merged context + test plan
  phase6-live-validation.md          # Phase 6: live validation (optional)
  test-case.md                       # Phase 7: PRIMARY DELIVERABLE
  analysis-results.json              # Phase 7: investigation metadata
  phase8-review.md                   # Phase 8: quality review output
  test-case-setup.html               # Phase 9: Polarion setup section HTML
  test-case-steps.html               # Phase 9: Polarion steps table HTML
  review-results.json                # Phase 9: structural validation + artifact completeness
  SUMMARY.txt                        # Phase 9: human-readable summary + artifact completeness
  pipeline.log.jsonl                 # All phases: telemetry log
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

All 9 areas have architecture knowledge files providing domain context for subagents.

## Skill Pack Structure

```
.claude/skills/acm-test-case-generator/
├── SKILL.md                         # Orchestrator: sequences phases 0-9
├── scripts/
│   ├── gather.py                    # Phase 1: deterministic data gathering
│   ├── report.py                    # Phase 9: validation + HTML + summary
│   ├── review_enforcement.py        # Phase 8: programmatic enforcement layer
│   └── generate_html.py             # Phase 9: Polarion HTML generation
├── references/
│   ├── agents/                      # 7 subagent definitions
│   │   ├── jira-investigator.md     # Phase 2
│   │   ├── code-analyzer.md         # Phase 3
│   │   ├── ui-discoverer.md         # Phase 4
│   │   ├── synthesizer.md           # Phase 5
│   │   ├── live-validator.md        # Phase 6
│   │   ├── test-case-writer.md      # Phase 7
│   │   └── quality-reviewer.md      # Phase 8
│   ├── synthesis-template.md        # Phase 5: conflict resolution + optimization passes
│   ├── phase-gates.md               # Gate rules and progress indicators
│   └── pipeline-workflow.md         # Context flow and subagent spawning
└── knowledge → .claude/knowledge/test-case-generator/  # Shared knowledge database
    ├── conventions/                 # Test case format rules (4 files)
    ├── architecture/                # Per-area domain knowledge (9 files)
    └── examples/                    # Sample test case (1 file)
```

## Detailed Documentation

| Document | Description |
|----------|-------------|
| [01-PIPELINE-PHASES.md](01-PIPELINE-PHASES.md) | Phase-by-phase pipeline execution (Phases 0-9) |
| [02-AGENTS.md](02-AGENTS.md) | Subagent definitions, inputs, outputs, MCP tools |
| [03-MCP-INTEGRATION.md](03-MCP-INTEGRATION.md) | MCP server setup, tools, usage patterns |
| [04-KNOWLEDGE-SYSTEM.md](04-KNOWLEDGE-SYSTEM.md) | Conventions, architecture knowledge, patterns |
| [05-QUALITY-GATES.md](05-QUALITY-GATES.md) | Phase 8 reviewer + Phase 9 validator |
| [06-SESSION-TRACING.md](06-SESSION-TRACING.md) | Claude Code hooks, JSONL traces, session summaries |
| [07-SKILL-ARCHITECTURE.md](07-SKILL-ARCHITECTURE.md) | Skill decomposition, data flow, context isolation |
| [architecture-diagrams.html](architecture-diagrams.html) | Interactive pipeline workflow visualization |
