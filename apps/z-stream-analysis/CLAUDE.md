# Z-Stream Pipeline Analysis (v3.5)

Enterprise Jenkins pipeline failure analysis with definitive PRODUCT BUG | AUTOMATION BUG | INFRASTRUCTURE classification. v3.5 adds environment oracle with feature-aware dependency health checking, Polarion test case context, KG-driven dependency learning, and oracle-informed classification routing.

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
STAGE 0: gather.py    → cluster_oracle (environment oracle + knowledge database)
STAGE 1: gather.py    → core-data.json + cluster.kubeconfig + repos/
STAGE 2: AI Analysis  → analysis-results.json (5-phase investigation)
STAGE 3: report.py    → Detailed-Analysis.md + per-test-breakdown.json + SUMMARY.txt
```

Stage 0 runs inside gather.py (Step 5) after environment data is collected. Stage 1 covers the remaining gather steps. The terminal shows distinct banners for each stage.

See `docs/00-OVERVIEW.md` for detailed diagrams.

## Run Directory

See `docs/00-OVERVIEW.md` for full run directory structure. Key files: `core-data.json` (primary AI input), `cluster.kubeconfig` (persisted cluster auth for Stage 2), `analysis-results.json` (AI output), `Detailed-Analysis.md` (final report).

## Classification Guide

4 primary classifications: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, NO_BUG. 3 edge-case classifications: MIXED, UNKNOWN, FLAKY (rarely assigned).

See `docs/00-OVERVIEW.md` for full classification definitions with owners and triggers.

## Decision Quick Reference (3-Path Routing with Pre-Checks)

See `docs/00-OVERVIEW.md` for the full decision routing table. Summary:
- **PR-1** Blank page / no-js pre-check — if page is blank due to missing prerequisite (AAP, IDP, CNV), route to INFRASTRUCTURE (v3.2)
- **PR-2** Hook failure dedup — if after-all hook cascades from prior failure, classify NO_BUG (v3.2)
- **PR-3** Temporal evidence — if `stale_test_signal=true` with refactor/rename commit, signal PRODUCT_BUG (v3.2)
- **PR-5** Data assertion pre-check — if `failure_mode_category=data_incorrect` with assertion values extracted, signal PRODUCT_BUG (v3.3)
- **PR-6** Backend probe source-of-truth — if probe has `classification_hint`, use deterministic K8s-vs-console comparison to route PRODUCT_BUG or INFRASTRUCTURE (v3.4)
- **PR-7** Environment Oracle dependency check — if oracle detects broken dependency (operator missing, addon degraded, component not running), route to INFRASTRUCTURE with Tier 1 evidence (v3.5)
- **PR-4** Check feature knowledge override FIRST — if tiered investigation confirmed a playbook failure path, use playbook classification (v3.1)
- **D0** Check backend cross-check — if backend caused UI failure, route to Path B2
- **Path A** (selector mismatch, no backend issue) → AUTOMATION_BUG
- **Path B1** (non-selector timeout, graduated per-area health scoring) → INFRASTRUCTURE (v3.3)
- **Path B2** (everything else OR backend cross-check override) → JIRA-informed investigation → PRODUCT_BUG or AUTOMATION_BUG
- **D4b** Per-test causal link verification — dominant signal must have causal mechanism to each test's failure mode (v3.3)

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

## New in v3.5

Four implementation phases (A through D) build a comprehensive environment oracle:

- **Phase A: Playbook-based dependency health checking** — resolves the `met=None` gap in FeatureKnowledgeService for addon, operator, and CRD prerequisites. Discovers dependencies from feature playbooks (base.yaml), then runs targeted read-only `oc get` commands against the live cluster to check their health. Uses strict `_validate_readonly` with `ALLOWED_COMMANDS` whitelist (get, describe, api-resources only). Graceful degradation when cluster access is unavailable (dependency targets still extracted from playbooks; cluster checks skipped, prerequisites fall back to `met=None`).
- **Phase B: Polarion test case context** — fetches Polarion test case description, setup, and steps for each failed test's Polarion ID via the Polarion REST API. Parses setup HTML for dependency keywords (operators, addons, infrastructure requirements). Discovered dependencies are merged with playbook dependencies and checked on the cluster. Polarion MCP also available during Stage 2 for deeper queries. Requires `POLARION_PAT` in `mcp/polarion/.env`.
- **Phase C: KG-driven feature and dependency learning** — queries the Knowledge Graph for each feature area's component topology (internal data flow, cross-subsystem dependencies, transitive dependency chains up to depth 3) and for each individual dependency's architecture (subsystem, what it depends on, what depends on it). Includes rhacm-docs path resolution for documentation context. Stored in `cluster_oracle.knowledge_context` for AI-driven dependency chain walking during classification. Playbook architecture summaries included as context.
- **Phase D: Agent integration** — new pre-routing check PR-7 combines all oracle data (playbook health, Polarion context, KG topology) as Tier 1 evidence in Phase D classification. If oracle detects a broken dependency (operator missing, addon degraded, CRD absent), tests in that feature area get routed to INFRASTRUCTURE.
- **Pipeline expanded to 11 steps** — new Step 5 (Environment Oracle) runs after Step 4 (environment check) and before Step 6 (repository cloning). Oracle output stored in `cluster_oracle` key of core-data.json.
- **Prerequisite resolution** — `FeatureKnowledgeService.check_prerequisites()` accepts `oracle_data` parameter, replacing previously hardcoded `met=None` results.
- **New schema fields** — `cluster_oracle` in core-data.json with `dependency_health`, `overall_feature_health`, `dependency_targets`, `feature_areas`, `knowledge_context`

## New in v3.3

- **Assertion value extraction** (Phase PR-5) — parses Cypress/Chai `expected X to equal Y` errors to extract expected vs actual values, identifying data-level failures (API returned wrong data) vs selector-level failures
- **Failure mode categorization** — each test classified as `render_failure`, `element_missing`, `data_incorrect`, `timeout_general`, `assertion_logic`, `server_error`, or `unknown` — enabling causal link verification
- **Refined failure types** — `assertion` split into `assertion_data` (value/count comparisons) and `assertion_selector` (element existence/visibility)
- **Per-feature-area health scoring** (GAP-04) — `ClusterInvestigationService.get_feature_area_health()` computes per-area health scores with graduated bands: definitive (<0.3), strong (0.3-0.5), moderate (0.5-0.7), none (>0.7)
- **Per-test causal link verification** (Phase D4b) — every test attributed to a dominant pattern must have a documented causal mechanism linking the pattern to the specific error; incompatible failure modes trigger independent re-investigation
- **Counter-bias validation strengthened** (Phase D5) — 3-test threshold rule: if 3+ tests share the same root_cause, at least 1 must be independently re-investigated
- **Backend API probing** (Step 4c) — probes 5 console backend endpoints (`/authenticated`, `/hub`, `/username`, `/ansibletower`, `/proxy/search`) via `oc exec` + curl, cross-references responses against cluster landscape to detect data anomalies (wrong hub name, reversed username, empty results)
- **New schema fields** — `failure_mode_category`, `assertion_analysis` per test; `data_assertion_failures`, `feature_area_health` in summary; `backend_probes` in core-data.json

## New in v3.2

- **Blank page / no-js pre-routing** (Phase PR-1) — detects blank pages caused by missing prerequisites (AAP not installed, IDP not configured, CNV missing) and routes to INFRASTRUCTURE instead of misclassifying as AUTOMATION_BUG
- **Hook failure deduplication** (Phase PR-2) — classifies `after all`/`after each` hook cascading failures as NO_BUG instead of counting them as independent bugs
- **Temporal evidence routing** (Phase PR-3) — uses `stale_test_signal` data to detect PRODUCT_BUG when product files changed with refactor/rename/PF6 commits
- **Automation/AAP playbook** — new feature area profile in `base.yaml` with AAP operator prerequisite checks and three failure paths
- **Knowledge Graph client fix** — replaced stub `_execute_cypher()` with real Neo4j HTTP API queries; KG now works in both Stage 1 (gather.py) and Stage 2 (AI agent)
- **New schema fields** — `is_cascading_hook_failure`, `blank_page_detected` per test; `cascading_hook_failures`, `blank_page_failures` in summary
- **Automation feature area** — added to `feature_area_service.py` with patterns, components, and namespace mappings
- **Counter-bias validation** (Phase D5) — self-check before finalizing any classification to counter routing bias
- **Path A confidence rebalanced** — requires B7 backend health confirmation; range lowered from 0.85-0.95 to 0.75-0.90
- **Regex injection fix** — `re.escape()` applied at 6 Cypher query injection points in `KnowledgeGraphClient`
- **Shared utilities** — `dataclass_to_dict()` and `validate_command_readonly()` extracted to `shared_utils.py`; 4 services deduplicated
- **11 new playbook failure paths** — 5 PRODUCT_BUG + 6 AUTOMATION_BUG paths added across Search, GRC, CLC, Application, Console profiles

### From v3.1

- **Feature investigation playbooks** (`src/data/feature_playbooks/`) — YAML playbooks with architecture, prerequisites, and known failure paths per feature area
- **FeatureKnowledgeService** — loads playbooks, checks MCH prerequisites, matches error symptoms to known failure paths
- **Tiered cluster investigation** (Tiers 0-4) — SRE debugging methodology from health snapshot to deep investigation
- **MCH component extraction** — `mch_enabled_components` and `mch_version` in `cluster_landscape`
- **Cluster kubeconfig persistence** — `cluster.kubeconfig` saved in run directory for Stage 2 re-authentication (passwords masked in core-data.json, agent uses `--kubeconfig` instead of `oc login`)
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
- `recent_selector_changes` - git diff analysis showing what replaced a removed selector (added/removed selectors from recent commits)
- `assertion_analysis` - parsed expected vs actual values from assertion errors (v3.3)
- `failure_mode_category` - categorized failure mode: `render_failure`, `element_missing`, `data_incorrect`, `timeout_general`, `assertion_logic`, `server_error`, `unknown` (v3.3)

Use extracted_context first. Only access repos/ if insufficient.

## Backend Probes

core-data.json includes `backend_probes` (v3.3) — responses from 5 console backend API endpoints probed via `oc exec` + curl during Stage 1 Step 4c. Each probe has `response_valid` (boolean) and `anomalies` (list). Used by Phase B7c as Tier 1 evidence when probe anomalies match the test's feature area.

| Probe | Endpoint | Validates | Feature Areas |
|---|---|---|---|
| `authenticated` | `/authenticated` | Response time < 5s | All |
| `hub` | `/hub` | Hub name matches MCH | CLC, Infrastructure, Observability |
| `username` | `/username` | Not reversed (`kube:admin`) | RBAC |
| `ansibletower` | `/ansibletower` | Non-empty if AAP healthy | Automation |
| `search` | `/proxy/search` | Returns Pods | Search |

Skipped when `--skip-env` is used or cluster access is unavailable.

## MCP Servers Available

Five MCP servers provide tools during Stage 2 (AI Analysis). New users: run `bash mcp/setup.sh` from the repo root to configure all servers.

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM-UI | 19 | ACM Console + kubevirt-plugin source code search via GitHub |
| JIRA | 25 | Issue search, creation, management for bug correlation (Jira Cloud) |
| Polarion | 25 | Polarion test case access + dependency discovery |
| Knowledge Graph (Neo4j RHACM) | 2 | Component dependency analysis via Cypher queries (optional) |

**JIRA Cloud:** Uses basic auth (email + API token). Create `mcp/jira-mcp-server/.env` from `.env.example` with your credentials, or run `bash mcp/setup.sh`. The config uses `load_dotenv(override=True)` so `.env` always takes precedence over shell vars. API token: https://id.atlassian.com/manage-profile/security/api-tokens

**Knowledge Graph:** The KG client (`knowledge_graph_client.py`) queries Neo4j directly via HTTP API (`http://localhost:7474`). It works in both Stage 1 (gather.py populates `kg_dependency_context` in core-data.json) and Stage 2 (AI agent uses MCP tools for ad-hoc queries). Requires `podman start neo4j-rhacm neo4j-mcp`. Connection settings configurable via `NEO4J_HTTP_URL`, `NEO4J_USER`, `NEO4J_PASSWORD` env vars (defaults: `localhost:7474`, `neo4j`, `rhacmgraph`).

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
| Stage 1: Data gathering (Steps 1-11) | `docs/01-STAGE1-DATA-GATHERING.md` |
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
# Regression tests (fast, no external deps — 47 tests):
python -m pytest tests/regression/ -v

# Unit tests (555+ tests):
python -m pytest tests/unit/ -v

# Unit + regression (602+ tests):
python -m pytest tests/unit/ tests/regression/ -v

# Integration tests (requires Jenkins VPN — 50 tests):
python -m pytest tests/integration/ -v --timeout=300

# All tests (652+ total):
python -m pytest tests/ -v --timeout=300
```

### Test Structure

- `tests/unit/` — 555+ unit tests across 18 service/script files (includes 77 oracle tests)
- `tests/regression/` — 47 regression tests for cross-module consistency, playbook quality, AI instructions, schema coverage
- `tests/integration/` — 50 integration tests for Stage 1 gather, Stage 3 report, and cross-stage data contracts
- `tests/fixtures/` — Synthetic analysis-results.json exercising v3.2+ schema fields

## File Structure

```
z-stream-analysis/
├── main.py                 # Entry point
├── pytest.ini              # Test markers (regression, integration, slow)
├── src/scripts/
│   ├── gather.py          # Stage 1: Data collection
│   ├── report.py          # Stage 3: Report generation
│   └── feedback.py        # Classification feedback CLI
├── src/services/          # 18 Python service modules
├── src/schemas/           # JSON Schema validation
├── src/data/
│   └── feature_playbooks/ # YAML investigation playbooks (base.yaml, acm-2.16.yaml)
├── tests/
│   ├── conftest.py        # Shared fixtures
│   ├── unit/              # Unit tests (555+)
│   ├── regression/        # Regression tests (47)
│   ├── integration/       # Integration tests (50)
│   └── fixtures/          # Test data (synthetic analysis-results.json)
├── .claude/agents/
│   └── z-stream-analysis.md  # Agent definition
└── docs/                  # Detailed documentation
```
