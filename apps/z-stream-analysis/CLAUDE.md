# Z-Stream Pipeline Analysis (v3.1)

Enterprise Jenkins pipeline failure analysis with definitive PRODUCT BUG | AUTOMATION BUG | INFRASTRUCTURE classification. v3.1 adds feature investigation playbooks, tiered cluster investigation, MCH component extraction, cluster credential persistence, and classification feedback.

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

Before writing analysis-results.json, ALWAYS read `src/schemas/analysis_results_schema.json` and the output example in `.claude/agents/z-stream-analysis.md` (search for "Output Schema"). The report generator (`report.py`) will reject the file if required fields are missing or named incorrectly. Key fields that must be exact:
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

## Decision Quick Reference (3-Path Routing with Feature Knowledge Override)

See `docs/00-OVERVIEW.md` for the full decision routing table. Summary:
- **D-1** Check feature knowledge override FIRST — if tiered investigation confirmed a playbook failure path, use playbook classification (v3.1)
- **D0** Check backend cross-check — if backend caused UI failure, route to Path B2
- **Path A** (selector mismatch, no backend issue) → AUTOMATION_BUG
- **Path B1** (non-selector timeout) → INFRASTRUCTURE
- **Path B2** (everything else OR backend cross-check override) → JIRA-informed investigation → PRODUCT_BUG or AUTOMATION_BUG

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

## New in v3.1

- **Feature investigation playbooks** (`src/data/feature_playbooks/`) — YAML playbooks with architecture, prerequisites, and known failure paths per feature area
- **FeatureKnowledgeService** — loads playbooks, checks MCH prerequisites, matches error symptoms to known failure paths
- **Tiered cluster investigation** (Tiers 0-4) — SRE debugging methodology from health snapshot to deep investigation
- **MCH component extraction** — `mch_enabled_components` and `mch_version` in `cluster_landscape`
- **Cluster credential persistence** — `cluster_access` in core-data.json for Stage 2 re-authentication
- **Feature knowledge in core-data** — `feature_knowledge` section with readiness, playbooks, KG status

### From v3.0

- **Cluster landscape** (`cluster_landscape` in core-data.json) — managed clusters, operator statuses, resource pressure
- **Feature grounding** (`feature_grounding` in core-data.json) — tests grouped by feature area with subsystem/component context
- **Backend cross-check** (Phase B7) — detects UI failures caused by backend problems, overrides Path A routing
- **Targeted pod investigation** (Phase B5b) — on-demand pod diagnostics for feature area components
- **Earlier Knowledge Graph** (Phase A3b) — subsystem context built before per-test analysis
- **Feedback CLI** (`python -m src.scripts.feedback`) — rate classifications for accuracy tracking

## Extracted Context

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

**KG label mapping:** The Knowledge Graph uses descriptive labels (e.g., `"API Gateway Controller"`), not pod names (e.g., `"search-api"`). The AI instructions include a `pod_to_kg_label` map and a `query_strategy` that directs the AI to use `get_subsystem_components` first to discover actual KG labels before querying by component.

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
| Stage 1: Data gathering (Steps 1-10) | `docs/01-STAGE1-DATA-GATHERING.md` |
| Stage 2: AI analysis (Phases A-E) | `docs/02-STAGE2-AI-ANALYSIS.md` |
| Stage 3: Report generation | `docs/03-STAGE3-REPORT-GENERATION.md` |
| All services reference | `docs/04-SERVICES-REFERENCE.md` |
| MCP integration guide | `docs/05-MCP-INTEGRATION.md` |
| v2.5 vs v3.0 comparison | `docs/V2.5-VS-V3.0-COMPARISON.md` |

## CLI Options

```bash
python -m src.scripts.gather <url> --skip-env    # Skip cluster validation
python -m src.scripts.gather <url> --skip-repo   # Skip repository cloning
python -m src.scripts.report <dir> --keep-repos  # Don't cleanup repos/
python -m src.scripts.feedback <dir> --test "name" --correct    # Rate classification
python -m src.scripts.feedback <dir> --test "name" --incorrect --should-be PRODUCT_BUG
python -m src.scripts.feedback --stats           # View accuracy stats
```

## Tests

```bash
# Regression tests (fast, no external deps — 40 tests):
python -m pytest tests/regression/ -v

# Unit tests (379 tests):
python -m pytest tests/unit/ -v

# Unit + regression (419 tests):
python -m pytest tests/unit/ tests/regression/ -v

# Integration tests (requires Jenkins VPN — 50 tests):
python -m pytest tests/integration/ -v --timeout=300

# All tests (469 total):
python -m pytest tests/ -v --timeout=300
```

### Test Structure

- `tests/unit/` — 379 unit tests across 13 service/script files
- `tests/regression/` — 40 regression tests for cross-module consistency, playbook quality, AI instructions, schema coverage
- `tests/integration/` — 50 integration tests for Stage 1 gather, Stage 3 report, and cross-stage data contracts
- `tests/fixtures/` — Synthetic analysis-results.json exercising all v3.1 schema fields

## File Structure

```
z-stream-analysis/
├── main.py                 # Entry point
├── pytest.ini              # Test markers (regression, integration, slow)
├── src/scripts/
│   ├── gather.py          # Stage 1: Data collection
│   ├── report.py          # Stage 3: Report generation
│   └── feedback.py        # Classification feedback CLI
├── src/services/          # 16 Python service modules
├── src/schemas/           # JSON Schema validation
├── src/data/
│   └── feature_playbooks/ # YAML investigation playbooks (base.yaml, acm-2.16.yaml)
├── tests/
│   ├── conftest.py        # Shared fixtures
│   ├── unit/              # Unit tests (379)
│   ├── regression/        # Regression tests (40)
│   ├── integration/       # Integration tests (50)
│   └── fixtures/          # Test data (synthetic analysis-results.json)
├── .claude/agents/
│   └── z-stream-analysis.md  # Agent definition
└── docs/                  # Detailed documentation
```
