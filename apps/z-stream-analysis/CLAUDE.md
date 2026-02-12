# Z-Stream Pipeline Analysis (v2.5)

Enterprise Jenkins pipeline failure analysis with definitive PRODUCT BUG | AUTOMATION BUG | INFRASTRUCTURE classification.

## Quick Start

```bash
# Step 1: Gather data from Jenkins
python -m src.scripts.gather "<JENKINS_URL>"

# Step 2: AI analyzes core-data.json (creates analysis-results.json)
# Read core-data.json, use extracted_context, classify each test

# Step 3: Generate reports
python -m src.scripts.report runs/<dir>
```

## MANDATORY: Read Schema Before Writing analysis-results.json

Before writing analysis-results.json, ALWAYS read `src/schemas/analysis_results_schema.json` and the output example in `.claude/agents/z-stream-analysis.md` (lines 984-1096). The report generator (`report.py`) will reject the file if required fields are missing or named incorrectly. Key fields that must be exact:
- `per_test_analysis` (NOT `failed_tests`)
- `summary.by_classification` (NOT `classification_breakdown`)
- `investigation_phases_completed` (required array)

## Architecture

```
STAGE 1: gather.py    → core-data.json + repos/
STAGE 2: AI Analysis  → analysis-results.json (5-phase investigation)
STAGE 3: report.py    → Detailed-Analysis.md + per-test-breakdown.json + SUMMARY.txt
```

See `docs/00-OVERVIEW.md` for detailed diagrams.

## Run Directory

See `docs/00-OVERVIEW.md` for full run directory structure. Key files: `core-data.json` (primary AI input), `analysis-results.json` (AI output), `Detailed-Analysis.md` (final report).

## Classification Guide

7 classification categories: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, MIXED, UNKNOWN, FLAKY, NO_BUG.

See `docs/00-OVERVIEW.md` for full classification definitions with owners and triggers.

## Decision Quick Reference (3-Path Routing)

See `docs/00-OVERVIEW.md` for the full decision routing table. Summary:
- **Path A** (selector mismatch) → AUTOMATION_BUG
- **Path B1** (non-selector timeout) → INFRASTRUCTURE
- **Path B2** (everything else) → JIRA-informed investigation → PRODUCT_BUG or AUTOMATION_BUG

## Multi-Evidence Requirement

**Every classification needs all 5 criteria:**

1. **Minimum 2 evidence sources** — single-source evidence is insufficient
2. **Ruled out alternatives** — document why other classifications don't fit
3. **MCP tools used** — leverage available MCP servers when trigger conditions met
4. **Cross-test correlation** — check for patterns across all failures
5. **JIRA correlation** — search for related bugs before finalizing

```json
"evidence_sources": [
  {"source": "console_search", "finding": "found=false", "tier": 1},
  {"source": "timeline_evidence", "finding": "element_removed", "tier": 1}
]
```

## Extracted Context (v2.4+)

Each failed test includes pre-extracted context in core-data.json:

- `test_file.content` - actual test code (up to 200 lines)
- `page_objects` - imported selector definitions
- `console_search.found` - whether selector exists in product
- `detected_components` - backend components for Knowledge Graph

Use extracted_context first. Only access repos/ if insufficient.

## MCP Servers Available

Three MCP servers provide tools during Stage 2 (AI Analysis). New users: run `bash mcp/setup.sh` from the repo root to configure all servers.

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM-UI | 20 | ACM Console + kubevirt-plugin source code search via GitHub |
| JIRA | 24 | Issue search, creation, management for bug correlation |
| Knowledge Graph (Neo4j RHACM) | 3 | Component dependency analysis via Cypher queries (optional) |

See `docs/05-MCP-INTEGRATION.md` for full tool reference, or `.claude/agents/z-stream-analysis.md` for the trigger matrix specifying when to use each tool.

## Key Principle

**Don't guess. Investigate.**

AI has full repo access - use it to understand exactly what went wrong before classifying. Read actual test code, trace imports, search for elements, check git history.

For non-obvious failures (not simple selector mismatches or timeouts), use Knowledge Graph
to understand the subsystem context and JIRA to read feature stories before classifying.
Understanding what a feature SHOULD do is key to classifying what went WRONG.

## Detailed Documentation

| Topic | File |
|-------|------|
| Pipeline overview & classification guide | `docs/00-OVERVIEW.md` |
| Stage 1: Data gathering (Steps 1-8) | `docs/01-STAGE1-DATA-GATHERING.md` |
| Stage 2: AI analysis (Phases A-E) | `docs/02-STAGE2-AI-ANALYSIS.md` |
| Stage 3: Report generation | `docs/03-STAGE3-REPORT-GENERATION.md` |
| All services reference | `docs/04-SERVICES-REFERENCE.md` |
| MCP integration guide | `docs/05-MCP-INTEGRATION.md` |

## CLI Options

```bash
python -m src.scripts.gather <url> --skip-env    # Skip cluster validation
python -m src.scripts.gather <url> --skip-repo   # Skip repository cloning
python -m src.scripts.report <dir> --keep-repos  # Don't cleanup repos/
```

## File Structure

```
z-stream-analysis/
├── main.py                 # Entry point
├── src/scripts/
│   ├── gather.py          # Stage 1: Data collection
│   └── report.py          # Stage 3: Report generation
├── src/services/          # 13 Python service modules
├── src/schemas/           # JSON Schema validation
├── .claude/agents/
│   └── z-stream-analysis.md  # Agent definition
└── docs/                  # Detailed documentation
```
