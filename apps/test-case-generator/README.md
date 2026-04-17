# ACM Console Test Case Generator

Generates Polarion-ready test cases for ACM Console UI features from JIRA tickets. Built as a standalone Claude Code application using a 6-phase subagent pipeline with 6 specialized agents, 7 MCP integrations, parallel investigation, live cluster validation, and mandatory quality review gating.

## Prerequisites

- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- `gh` CLI ([GitHub CLI](https://cli.github.com/)) authenticated (`gh auth login`)
- Access to Red Hat JIRA (Atlassian Cloud)
- Access to Polarion (VPN required)
- Optional: Podman (for Neo4j architecture knowledge graph)
- Optional: Live ACM cluster with console access (for Phase 3 live validation)

## Setup

From the repository root (`ai_systems_v2/`):

```bash
bash mcp/setup.sh
# Select: Test Case Generator
# Follow prompts for JIRA credentials, Polarion PAT, etc.
```

This configures all MCP servers and generates `.mcp.json` for the app.

Then start Claude Code:

```bash
cd apps/test-case-generator
claude
```

## Usage

### Generate a test case

```
/generate ACM-30459
```

Options:
- `--version 2.17` -- Override ACM version (default: from JIRA fix_versions)
- `--pr 5790` -- Specify PR number (default: auto-detected from JIRA)
- `--area governance` -- Override area detection
- `--skip-live` -- Skip live cluster validation
- `--cluster-url https://console...` -- Console URL for live validation
- `--repo stolostron/console` -- Override repository (default: stolostron/console)

### Review an existing test case

```
/review path/to/test-case.md
```

### Batch generation

```
/batch ACM-30459,ACM-30460,ACM-30461
```

### Manual stage-by-stage

```bash
# Stage 1: Gather data
python -m src.scripts.gather ACM-30459 --version 2.17

# Stage 2: AI investigation + generation (interactive in Claude Code)

# Stage 3: Generate reports
python -m src.scripts.report runs/ACM-30459/<run-dir>
```

## Output

Each run produces artifacts under `runs/<JIRA_ID>/<timestamp>/`:

| File | Phase | Description |
|------|-------|-------------|
| `gather-output.json` | Stage 1 | All gathered data (PR, conventions, knowledge) |
| `pr-diff.txt` | Stage 1 | Full PR diff |
| `test-case.md` | Phase 4 | Primary deliverable: Polarion test case |
| `analysis-results.json` | Phase 4 | Investigation metadata |
| `test-case-setup.html` | Stage 3 | Polarion setup section HTML |
| `test-case-steps.html` | Stage 3 | Polarion steps table HTML |
| `review-results.json` | Stage 3 | Structural validation results |
| `SUMMARY.txt` | Stage 3 | Human-readable summary |
| `pipeline.log.jsonl` | All | Pipeline telemetry |

## Pipeline Architecture

```
Stage 1: gather.py (deterministic)     -> gather-output.json + pr-diff.txt
Phase 1: 3 parallel investigation agents -> feature + code + UI context
Phase 2: Synthesize test plan            -> merged investigation
Phase 3: Live validation (optional)      -> confirmed behavior
Phase 4: Test case generator agent       -> test-case.md
Phase 4.5: Quality reviewer agent        -> PASS / NEEDS_FIXES loop
Stage 3: report.py (deterministic)       -> HTML + validation + summary
```

## Agents

| Agent | Phase | Role |
|-------|-------|------|
| Feature Investigator | 1 (parallel) | JIRA deep dive, linked tickets, Polarion coverage |
| Code Change Analyzer | 1 (parallel) | PR diff analysis, UI elements, Neo4j impact |
| UI Discovery | 1 (parallel) | Source code selectors, translations, routes |
| Live Validator | 3 | Browser + oc CLI + acm-search + acm-kubectl |
| Test Case Generator | 4 | Write test case from synthesized context |
| Quality Reviewer | 4.5 | Conventions, discovered vs assumed, PASS/NEEDS_FIXES |

## Knowledge Database

The `knowledge/` directory contains curated domain knowledge:

- **`conventions/`** -- Test case format rules (from 85+ existing test cases)
- **`architecture/`** -- Per-area domain knowledge (governance, RBAC, fleet-virt, etc.)
- **`patterns/`** -- Learned patterns from successful runs (agent-written)
- **`diagnostics/`** -- Known quality issues and common mistakes

## MCP Servers

| Server | Purpose |
|--------|---------|
| acm-ui | ACM Console source code discovery (selectors, routes, translations) |
| jira | JIRA ticket investigation (stories, bugs, comments, links) |
| polarion | Existing test case coverage (Polarion work items) |
| neo4j-rhacm | Architecture dependency graph (component relationships) |
| acm-search | Live cluster resource queries across managed clusters |
| acm-kubectl | Multicluster kubectl (list clusters, run commands on hub/spokes) |
| playwright | Browser automation for live UI validation |
