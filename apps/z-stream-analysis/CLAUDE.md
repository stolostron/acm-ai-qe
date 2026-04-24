# Z-Stream Pipeline Analysis (v4.0)

Jenkins pipeline failure analysis with PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE | NO_BUG classification. v4.0 moves cluster health entirely to Stage 1.5 cluster-diagnostic agent (deprecates ClusterHealthService), adds structured health fields (environment_health_score, operator_health, health_depth, image_integrity), changes PR-7 from binding classifications to context signals, adds PR-6b Polarion expected-behavior check, symmetric counterfactual (D-V5c for AUTOMATION_BUG, D-V5e for PRODUCT_BUG), and layer discrepancy detection as Tier 1 evidence. Builds on v3.9's provably linked grouping, v3.8's 12-layer diagnostic investigation, and v3.7's comprehensive environment oracle. See `docs/CHANGELOG.md` for version history.

## Pipeline Execution UX (MANDATORY)

When a user asks to analyze a Jenkins run, **do NOT delegate the entire pipeline to a single agent**. The user must see stage-by-stage progress in their terminal. Run each stage yourself in the main conversation with visible status updates between them.

**Required behavior:**

1. **Stage 1** — Run `gather.py` yourself. Before running, output:
   ```
   Stage 1: Gathering pipeline data from Jenkins...
   ```
   After it completes, summarize what was collected (e.g., "Extracted 64 failed tests across 8 feature areas, 3 managed clusters").

2. **Stage 1.5** — Spawn the `cluster-diagnostic` agent. Before launching, output:
   ```
   Stage 1.5: Running comprehensive cluster diagnostic...
   ```
   Pass the run directory path as the prompt. After it completes, show the verdict and key findings (e.g., "Verdict: DEGRADED — search-postgres OOM, 2 subsystems affected"). Skip this stage if `--skip-env` was used or cluster access is unavailable.

   After Stage 1.5 (or after Stage 1 if 1.5 is skipped), spawn the `data-collector` agent with the run directory path. It enriches `core-data.json` with data that requires AI code analysis (resolving `page_objects` by tracing imports, verifying `console_search` selector existence via MCP, analyzing `recent_selector_changes` with git history and intent assessment, and building selector-level `temporal_summary`). No stage banner needed — it runs quietly before Stage 2.

3. **Stage 2** — Use the `analysis` agent for AI analysis. Before launching, output:
   ```
   Stage 2: Analyzing <N> failed tests (12-layer diagnostic investigation)...
   ```
   After it completes, show the classification breakdown (e.g., "44 AUTOMATION_BUG, 12 INFRASTRUCTURE, 7 NO_BUG, 1 PRODUCT_BUG").

4. **Stage 3** — Run `report.py` yourself. Before running, output:
   ```
   Stage 3: Generating report...
   ```
   After it completes, confirm the output files.

**Why:** When everything runs inside a single agent, the user only sees collapsed tool calls with no sense of progress. Stage-by-stage updates keep the user informed.

## Quick Start

```bash
# Step 1: Gather data from Jenkins
python -m src.scripts.gather "<JENKINS_URL>"

# Step 2: AI analyzes using 12-layer diagnostic model (creates analysis-results.json)
# Read core-data.json + cluster-diagnosis.json, classify each test

# Step 3: Generate reports
python -m src.scripts.report runs/<dir>
```

## MANDATORY: Read Schema Before Writing analysis-results.json

Before writing analysis-results.json, ALWAYS read `src/schemas/analysis_results_schema.json` and the output example in `.claude/agents/analysis.md` (search for "Output Schema"). The report generator (`report.py`) will reject the file if required fields are missing or named incorrectly. Key fields that must be exact:
- `per_test_analysis` (NOT `failed_tests`)
- `summary.by_classification` (NOT `classification_breakdown`)
- `investigation_phases_completed` (required array)

## Architecture

```
STAGE 1: gather.py      → core-data.json + cluster.kubeconfig + repos/
  Step 1: Jenkins build info (build result, params, branch, SHA)
  Step 2: Console log download + error pattern extraction
  Step 3: Test report extraction
  Step 4: Cluster login + kubeconfig persist + MCH namespace discovery (4a), landscape (4b)
  Step 5: Feature context oracle (Polarion, KG topology, targeted dependency verification)
  Step 6-9: Repo cloning, context extraction, feature grounding, knowledge
STAGE 1.5: cluster-diagnostic agent → cluster-diagnosis.json (comprehensive health + structured data)
STAGE 2: AI Analysis    → analysis-results.json (12-layer diagnostic investigation, per-group investigation agents)
STAGE 3: report.py      → Detailed-Analysis.md + analysis-report.html + per-test-breakdown.json + SUMMARY.txt
```

Stage 1 runs gather.py with 9 steps. Step 4 handles cluster login (with MCH namespace discovery) and landscape collection. Step 5 runs the oracle for feature context only (Polarion test cases, KG topology). Stage 1.5 runs the cluster-diagnostic agent for comprehensive health investigation, producing `cluster-diagnosis.json` with structured health data (environment_health_score, operator_health, subsystem_health, image_integrity, classification_guidance, counter_signals). The diagnostic checks 14 traps, validates console image integrity against expected registries, and reports all findings with health_depth and unchecked_layers per subsystem. Stage 2 uses the 12-layer diagnostic model with provably linked grouping (v3.9): Phase A4 groups tests using strict code-path criteria only, investigation agents trace from symptom through infrastructure layers, per-test verification checks each test within a group, and expanded counterfactual verification (9 templates) validates INFRASTRUCTURE classifications. Falls back to inline tiered investigation (v3.7) when agents are unavailable.

See `docs/00-OVERVIEW.md` for detailed diagrams.

## Run Directory

See `docs/00-OVERVIEW.md` for full run directory structure. Key files: `core-data.json` (primary AI input), `cluster.kubeconfig` (persisted cluster auth for Stage 1.5 and Stage 2), `cluster-diagnosis.json` (comprehensive cluster health diagnostic from Stage 1.5), `pipeline.log.jsonl` (structured service logs), `analysis-results.json` (AI output), `Detailed-Analysis.md` (final report), `analysis-report.html` (interactive HTML report).

## Classification Guide

4 primary classifications: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, NO_BUG. 3 edge-case classifications: MIXED, UNKNOWN, FLAKY (rarely assigned).

See `docs/00-OVERVIEW.md` for full classification definitions with owners and triggers.

## Decision Quick Reference (v4.0: Structured Diagnostics + Context Signals + Provably Linked Grouping)

**v3.9 primary flow:** Phase A4 groups tests using provably linked criteria only → investigation agents use 12-layer diagnostic model → per-test verification within groups (4-point check) → Phase D-V validates with expanded counterfactual.

**Phase A4 instant classification (no investigation needed):**
- Dead selector shared by 3+ tests (`console_search.found=false`) → AUTOMATION_BUG directly
- After-all hook cascading from prior failure (PR-2) → NO_BUG directly

**Phase A4 provably linked grouping (v3.9):** Groups use strict criteria only — same exact selector+function, same before-all hook, same spec+error+line. "Button disabled", "same feature area", "similar error" are NOT valid grouping criteria.

**Investigation agents (Phase B):** Trace from symptom through 12 infrastructure layers (Compute → Control Plane → Network → Storage → Config → Auth → RBAC → API → Operator → Cross-Cluster → Data Flow → UI) to find root cause layer, then classify based on WHO caused it.

**Per-test verification (Phase B, v3.9):** After group investigation, 4-point check (code path, backend, role, element) on each subsequent test. Failures split to individual investigation.

**Phase D-V validation checks (cross-check investigation results):**
- **PR-6** Backend health check — investigated by Stage 1.5 cluster diagnostic and Stage 2 analysis agent
- **PR-6b** Polarion expected behavior check — PRODUCT_BUG fast-path without JIRA (v4.0)
- **PR-7** Environment/Diagnostic context signals — ADDITIVE, not binding classifications (v4.0)
- **D-V5** Expanded counterfactual — 9 templates + symmetric validation: D-V5c for AUTOMATION_BUG ("does backend confirm expectation?"), D-V5e for PRODUCT_BUG ("is product behavior correct?") (v4.0)
- **Layer discrepancy** — Tier 1 PRODUCT_BUG evidence when lower layer healthy but higher layer defective (v4.0)
- **D4b** Per-test causal link verification (v3.3)
- **D5** Counter-bias validation (v3.3)

**Fallback (v3.7 routing, used when investigation agents unavailable):**
- **PR-1** through **PR-7** pre-routing checks → **Path A** (selector mismatch → AUTOMATION_BUG), **Path B1** (timeout → INFRASTRUCTURE), **Path B2** (JIRA-informed → PRODUCT_BUG)

See `docs/00-OVERVIEW.md` for the full decision routing table.

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
  {"source": "recent_selector_changes", "finding": "change_detected, direction=removed_from_product", "tier": 1}
]
```

## Extracted Context

Each failed test includes pre-extracted context in core-data.json:

- `test_file.content` - actual test code (up to 200 lines)
- `page_objects` - imported selector definitions (populated by data-collector agent after gather.py)
- `console_search.found` - whether selector exists in product source (verified by data-collector agent using MCP tools, includes `verification` context)
- `detected_components` - backend components for Knowledge Graph
- `recent_selector_changes` - selector timeline analysis with intent assessment and classification hints (populated by data-collector agent)
- `assertion_analysis` - parsed expected vs actual values from assertion errors (v3.3)
- `failure_mode_category` - categorized failure mode: `render_failure`, `element_missing`, `data_incorrect`, `timeout_general`, `assertion_logic`, `server_error`, `unknown` (v3.3)

Use extracted_context first. Only access repos/ if insufficient.

## MCP Servers Available

Five MCP servers provide tools during Stage 2 (AI Analysis). Run `bash mcp/setup.sh` from the repo root to configure. See `docs/05-MCP-INTEGRATION.md` for setup details, credential configuration, and full tool reference.

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM-UI | 20 | ACM Console + kubevirt-plugin source code search via GitHub |
| Jenkins | 7+4 | Jenkins pipeline API + ACM-specific analysis tools |
| JIRA | 25 | Issue search, creation, management for bug correlation (Jira Cloud) |
| Polarion | 25 | Polarion test case access + dependency discovery |
| Knowledge Graph (Neo4j RHACM) | 2 | Component dependency analysis via Cypher queries (optional) |

**KG label mapping:** The Knowledge Graph uses descriptive labels (e.g., `"API Gateway Controller"`), not pod names (e.g., `"search-api"`). The AI instructions include a `pod_to_kg_label` map and a `query_strategy` that directs the AI to use `get_subsystem_components` first to discover actual KG labels before querying by component.

**KG subsystem mapping:** The KG uses 7 broad subsystem names (Overview, Cluster, Governance, Console, Application, Observability, Search) while the app uses 12+ feature area names. `KG_SUBSYSTEM_MAP` in `knowledge_graph_client.py` translates automatically (e.g., CLC→Cluster, GRC→Governance, RBAC→Cluster+Console). The `resolve_kg_subsystems()` static method is available for custom queries.

See `.claude/agents/analysis.md` for the trigger matrix specifying when to use each MCP tool.

## Key Principle

**Don't guess. Investigate.**

AI has full repo access - use it to understand exactly what went wrong before classifying. Read actual test code, trace imports, search for elements, check git history.

For non-obvious failures (not simple selector mismatches or timeouts), use Knowledge Graph
to understand the subsystem context and JIRA to read feature stories before classifying.
Understanding what a feature SHOULD do is key to classifying what went WRONG.

## Pre-flight Checks

gather.py runs automatic pre-flight checks before Step 1. If the Neo4j Knowledge Graph container (`neo4j-rhacm`) is not running, it attempts to start the Podman machine and the container automatically. If it can't start them, the pipeline continues without KG — dependency analysis is degraded but all other features work normally.

## Change Impact Checklist (MANDATORY)

After ANY code change, trace the feature's data flow and update ALL touchpoints. The regression tests in `tests/regression/test_consistency_enforcement.py` enforce version, step count, key count, data contract, and removed-field consistency automatically — run them after every change.

**If you change a core-data.json key** (add, remove, rename):
- `src/scripts/gather.py` → `_save_combined_data()` dict, `gathered_data` init, docstring step list
- `.claude/agents/analysis.md` → Phase A-0 reading instructions, data table
- `.claude/agents/data-collector.md` → Task references
- `docs/01-STAGE1-DATA-GATHERING.md` → schema tree, per-key documentation
- `.coderabbit.yaml` → data contracts section, key count
- `CLAUDE.md` → architecture block
- `tests/integration/test_pipeline_contracts.py` → `EXPECTED_SECTIONS`
- `tests/regression/test_consistency_enforcement.py` → `EXPECTED_KEYS`, `EXPECTED_KEY_COUNT`

**If you change the step count** (add, remove a pipeline step):
- `src/scripts/gather.py` → `total_steps`, docstring, class docstring, CLI help
- `CLAUDE.md` → architecture block, Stage 1 paragraph
- `docs/00-OVERVIEW.md` → sequence diagram, docs table
- `docs/01-STAGE1-DATA-GATHERING.md` → overview, step sections
- `docs/architecture-diagrams.html` → diagram nodes, detail panels, NODE_MAP
- `.coderabbit.yaml` → step list
- `tests/regression/test_consistency_enforcement.py` → `EXPECTED_STEPS`

**If you change the version**:
- `src/scripts/gather.py` → `gatherer_version`, `data_version`, manifest `version`, CLI help, docstring
- `src/scripts/report.py` → footer version string
- `src/services/__init__.py` → module docstring
- `tests/regression/test_consistency_enforcement.py` → `CURRENT_VERSION`
- `tests/unit/scripts/test_gather_enhancements.py` → version assertion
- `tests/integration/test_pipeline_stage1.py` → version assertion

**If you remove a field or method**:
- Add to `.coderabbit.yaml` → "Methods that were REMOVED" list
- Add to `tests/regression/test_consistency_enforcement.py` → `REMOVED_FIELDS`
- Grep ALL `.md`, `.yaml`, `.html`, `.py` files for references
- Update `docs/` workflow documentation and HTML diagrams

## CLI Options

```bash
python -m src.scripts.gather <url> --skip-env    # Skip cluster validation
python -m src.scripts.gather <url> --skip-repo   # Skip repository cloning
python -m src.scripts.report <dir> --keep-repos  # Don't cleanup repos/
python -m src.scripts.feedback <dir> --test "name" --correct    # Rate classification
python -m src.scripts.feedback <dir> --test "name" --incorrect --should-be PRODUCT_BUG
python -m src.scripts.feedback --stats           # View accuracy stats
```

## Logging & Observability

Two-layer structured logging captures every operation across all pipeline stages.

**Layer 1: Python Service Logs (`pipeline.log.jsonl`)** — Written to the run directory by `src/logging_config.py`. Captures all `logging.getLogger()` calls from Python service modules with `run_id` and `stage` context. Console output shows colored human-readable format; the JSONL file captures DEBUG-level detail.

**Layer 2: Agent Trace Logs (`.claude/traces/<session_id>.jsonl`)** — Written by Claude Code hooks (`.claude/hooks/agent_trace.py`). Captures ALL tool calls (Bash, Read, Edit, Write, Grep, Glob, MCP, Agent spawn/complete) and user prompts across the parent session and subagents. Hooks use catch-all matchers on PreToolUse, PostToolUse, and PostToolUseFailure events. Hooks are configured in `.claude/settings.json`.

## Tests

```bash
# Fast — unit + regression (703 tests, no external deps):
python -m pytest tests/unit/ tests/regression/ -q

# Full suite (748 tests, requires Jenkins VPN for integration):
python -m pytest tests/ -q --timeout=300
```

Test structure: `tests/unit/` (642 tests across 21 service/script files), `tests/regression/` (61 cross-module consistency + schema coverage tests), `tests/integration/` (45 tests requiring Jenkins VPN), `tests/fixtures/` (synthetic analysis-results.json).

## Knowledge Database (`knowledge/`)

Domain reference data for the AI agent during Stage 2 analysis. Includes per-subsystem architecture docs (12 areas), diagnostics methodology (5 files), structured YAML data (14 files), and self-healing learned patterns. See `docs/06-KNOWLEDGE-DATABASE.md` for the complete file reference, YAML schemas, and maintenance procedures.

**How the agent uses it:**
1. **Phase A0:** Read `architecture/<area>/architecture.md` and `data-flow.md` for each detected feature area
2. **Phase B:** Check `architecture/<area>/failure-signatures.md` for known patterns before full investigation
3. **Phase B (v3.8):** Investigation agents read `diagnostics/diagnostic-layers.md` for the 12-layer investigation methodology
4. **Phase D:** Reference `diagnostics/classification-decision-tree.md` for routing logic and validation
5. **After classification:** Write new discoveries to `learned/` for future runs

## Detailed Documentation

| Topic | File |
|-------|------|
| Pipeline overview & classification guide | `docs/00-OVERVIEW.md` |
| Stage 1: Data gathering (Steps 1-9) | `docs/01-STAGE1-DATA-GATHERING.md` |
| Stage 2: AI analysis (Phases A-E) | `docs/02-STAGE2-AI-ANALYSIS.md` |
| Stage 3: Report generation | `docs/03-STAGE3-REPORT-GENERATION.md` |
| All services reference | `docs/04-SERVICES-REFERENCE.md` |
| MCP integration guide | `docs/05-MCP-INTEGRATION.md` |
| Knowledge database reference | `docs/06-KNOWLEDGE-DATABASE.md` |
| Version history | `docs/CHANGELOG.md` |
| v2.5 vs v3.0 comparison | `docs/V2.5-VS-V3.0-COMPARISON.md` |

## File Structure

```
z-stream-analysis/
├── src/scripts/           # gather.py, report.py, feedback.py
├── src/services/          # 17 active Python service modules + shared_utils
├── src/reports/           # HTML report generator
├── src/schemas/           # JSON Schema validation
├── src/data/              # Feature playbooks (YAML)
├── knowledge/             # Knowledge database (see docs/06)
│   ├── architecture/      # Per-subsystem docs (12 areas, 37 files)
│   ├── diagnostics/       # Classification methodology + 12-layer model (5 files)
│   └── *.yaml             # Structured data files (14 files)
├── tests/                 # Unit (642), regression (61), integration (45)
├── .claude/agents/        # analysis.md, cluster-diagnostic.md, investigation-agent.md, data-collector.md
├── .claude/hooks/         # agent_trace.py (trace logging)
└── docs/                  # Detailed documentation (10 files)
```
