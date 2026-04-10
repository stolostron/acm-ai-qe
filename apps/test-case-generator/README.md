# ACM Console Test Case Generator

Generates Polarion-ready test cases for ACM Console UI features from JIRA tickets. Built as a standalone Claude Code application using a 3-stage pipeline (gather / analyze / report) with MCP integration for JIRA, Polarion, ACM UI source discovery, and architecture knowledge graph.

## Prerequisites

- Python 3.10+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI
- `gh` CLI ([GitHub CLI](https://cli.github.com/)) authenticated (`gh auth login`)
- Access to Red Hat JIRA (Atlassian Cloud)
- Access to Polarion (VPN required)
- Optional: Podman (for Neo4j architecture knowledge graph)

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

| File | Stage | Description |
|------|-------|-------------|
| `gather-output.json` | 1 | All gathered data (PR, conventions, knowledge) |
| `pr-diff.txt` | 1 | Full PR diff |
| `test-case.md` | 2 | Primary deliverable: Polarion test case |
| `analysis-results.json` | 2 | Investigation metadata |
| `test-case-setup.html` | 3 | Polarion setup section HTML |
| `test-case-steps.html` | 3 | Polarion steps table HTML |
| `review-results.json` | 3 | Structural validation results |
| `SUMMARY.txt` | 3 | Human-readable summary |
| `pipeline.log.jsonl` | All | Pipeline telemetry |

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
