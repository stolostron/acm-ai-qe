# Z-Stream Pipeline Analysis (v3.9)

Jenkins pipeline failure analysis with PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE | NO_BUG classification. v3.9 adds provably linked grouping (Phase A4), per-test verification within groups (4-point check), and expanded counterfactual verification (D-V5) with 9 templates covering selector, button-disabled, timeout, data-assertion, blank-page, CSS, NetworkPolicy, operator, and ResourceQuota failures. Builds on v3.8's 12-layer diagnostic investigation, v3.7's automated cluster health audit, comprehensive environment oracle, and knowledge-graph-driven dependency analysis. See `docs/CHANGELOG.md` for version history.

## Pipeline Execution UX (MANDATORY)

When a user asks to analyze a Jenkins run, **do NOT delegate the entire pipeline to a single agent**. The user must see stage-by-stage progress in their terminal. Run each stage yourself in the main conversation with visible status updates between them.

**Required behavior:**

1. **Stage 1** — Run `gather.py` yourself. Before running, output:
   ```
   Stage 1: Gathering pipeline data from Jenkins...
   ```
   After it completes, summarize what was collected (e.g., "Extracted 64 failed tests across 8 feature areas, health audit: 24% CRITICAL (4 issues)").

2. **Stage 1.5** — Spawn the `cluster-diagnostic` agent. Before launching, output:
   ```
   Stage 1.5: Running comprehensive cluster diagnostic...
   ```
   Pass the run directory path as the prompt. After it completes, show the verdict and key findings (e.g., "Verdict: DEGRADED — search-postgres OOM, 2 subsystems affected"). Skip this stage if `--skip-env` was used or cluster access is unavailable.

3. **Stage 2** — Use the `z-stream-analysis` agent for AI analysis. Before launching, output:
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
# Read core-data.json + cluster-health.json + cluster-diagnosis.json, classify each test

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
STAGE 1: gather.py      → core-data.json + cluster-health.json + cluster.kubeconfig + repos/
  Step 1: Jenkins build info + cluster credential extraction
  Step 2: Console log download + parsing
  Step 3: Test report extraction
  Step 4: Cluster health audit (ClusterHealthService, 6-phase) + landscape + backend probes
  Step 5: Feature context oracle (Polarion, KG topology — Phase 6 health checks skipped)
  Step 6-11: Repo cloning, context extraction, feature grounding, knowledge, inventory, hints
STAGE 1.5: cluster-diagnostic agent → cluster-diagnosis.json (optional deep investigation)
STAGE 2: AI Analysis    → analysis-results.json (12-layer diagnostic investigation, per-group investigation agents)
STAGE 3: report.py      → Detailed-Analysis.md + analysis-report.html + per-test-breakdown.json + SUMMARY.txt
```

Stage 1 runs gather.py with 11 steps. Step 4 performs the comprehensive cluster health audit (6 phases: DISCOVER, LEARN, CHECK, COMPARE, CORRELATE, SCORE) producing `cluster-health.json`. Step 5 runs the oracle for feature context only (Polarion test cases, KG topology). Stage 1.5 is optional — runs the cluster-diagnostic agent for deeper AI-driven investigation. Stage 2 uses the 12-layer diagnostic model with provably linked grouping (v3.9): Phase A4 groups tests using strict code-path criteria only, investigation agents trace from symptom through infrastructure layers, per-test verification checks each test within a group, and expanded counterfactual verification (9 templates) validates INFRASTRUCTURE classifications. Falls back to inline tiered investigation (v3.7) when agents are unavailable.

See `docs/00-OVERVIEW.md` for detailed diagrams.

## Run Directory

See `docs/00-OVERVIEW.md` for full run directory structure. Key files: `core-data.json` (primary AI input), `cluster-health.json` (comprehensive health audit, 19KB), `cluster.kubeconfig` (persisted cluster auth for Stage 2), `pipeline.log.jsonl` (structured service logs), `analysis-results.json` (AI output), `Detailed-Analysis.md` (final report), `analysis-report.html` (interactive HTML report).

## Classification Guide

4 primary classifications: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, NO_BUG. 3 edge-case classifications: MIXED, UNKNOWN, FLAKY (rarely assigned).

See `docs/00-OVERVIEW.md` for full classification definitions with owners and triggers.

## Decision Quick Reference (v3.9: Provably Linked Grouping + Layer-Based + Verification)

**v3.9 primary flow:** Phase A4 groups tests using provably linked criteria only → investigation agents use 12-layer diagnostic model → per-test verification within groups (4-point check) → Phase D-V validates with expanded counterfactual.

**Phase A4 instant classification (no investigation needed):**
- Dead selector shared by 3+ tests (`console_search.found=false`) → AUTOMATION_BUG directly
- After-all hook cascading from prior failure (PR-2) → NO_BUG directly

**Phase A4 provably linked grouping (v3.9):** Groups use strict criteria only — same exact selector+function, same before-all hook, same spec+error+line. "Button disabled", "same feature area", "similar error" are NOT valid grouping criteria.

**Investigation agents (Phase B):** Trace from symptom through 12 infrastructure layers (Compute → Control Plane → Network → Storage → Config → Auth → RBAC → API → Operator → Cross-Cluster → Data Flow → UI) to find root cause layer, then classify based on WHO caused it.

**Per-test verification (Phase B, v3.9):** After group investigation, 4-point check (code path, backend, role, element) on each subsequent test. Failures split to individual investigation.

**Phase D-V validation checks (cross-check investigation results):**
- **PR-6** Backend probe source-of-truth — deterministic K8s-vs-console comparison (v3.4)
- **PR-7** Environment Oracle — broken dependency check (v3.5)
- **D-V5** Expanded counterfactual — 9 verification templates (selector, button-disabled, timeout, data-assertion, blank-page, CSS, NetworkPolicy, operator, ResourceQuota) + evidence duplication detection + per-test evidence requirement (v3.9)
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
  {"source": "timeline_evidence", "finding": "element_removed", "tier": 1}
]
```

## Extracted Context

Each failed test includes pre-extracted context in core-data.json:

- `test_file.content` - actual test code (up to 200 lines)
- `page_objects` - imported selector definitions
- `console_search.found` - whether selector exists in product (checked against the RUNNING console image — if console is tampered, verify against official source via ACM-UI MCP)
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

See `.claude/agents/z-stream-analysis.md` for the trigger matrix specifying when to use each MCP tool.

## Key Principle

**Don't guess. Investigate.**

AI has full repo access - use it to understand exactly what went wrong before classifying. Read actual test code, trace imports, search for elements, check git history.

For non-obvious failures (not simple selector mismatches or timeouts), use Knowledge Graph
to understand the subsystem context and JIRA to read feature stories before classifying.
Understanding what a feature SHOULD do is key to classifying what went WRONG.

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

**Layer 1: Python Service Logs (`pipeline.log.jsonl`)** — Written to the run directory by `src/logging_config.py`. Captures all `logging.getLogger()` calls from 18 Python service modules with `run_id` and `stage` context. Console output shows colored human-readable format; the JSONL file captures DEBUG-level detail.

**Layer 2: Agent Trace Logs (`.claude/traces/<session_id>.jsonl`)** — Written by Claude Code hooks (`.claude/hooks/agent_trace.py`). Captures ALL tool calls (Bash, Read, Edit, Write, Grep, Glob, MCP, Agent spawn/complete) and user prompts across the parent session and subagents. Hooks use catch-all matchers on PreToolUse, PostToolUse, and PostToolUseFailure events. Hooks are configured in `.claude/settings.json`.

## Tests

```bash
# Fast — unit + regression (719 tests, no external deps):
python -m pytest tests/unit/ tests/regression/ -q

# Full suite (765+ tests, requires Jenkins VPN for integration):
python -m pytest tests/ -q --timeout=300
```

Test structure: `tests/unit/` (660 tests across 19 service/script files), `tests/regression/` (59 cross-module consistency + schema coverage tests), `tests/integration/` (50 tests requiring Jenkins VPN), `tests/fixtures/` (synthetic analysis-results.json).

## Knowledge Database (`knowledge/`)

Domain reference data for the AI agent during Stage 2 analysis. Includes per-subsystem architecture docs (14 areas), diagnostics methodology (5 files), structured YAML data (12 files), and self-healing learned patterns. See `docs/06-KNOWLEDGE-DATABASE.md` for the complete file reference, YAML schemas, and maintenance procedures.

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
| Stage 1: Data gathering (Steps 1-11) | `docs/01-STAGE1-DATA-GATHERING.md` |
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
├── src/services/          # 18 Python service modules + shared_utils
├── src/reports/           # HTML report generator
├── src/schemas/           # JSON Schema validation
├── src/data/              # Feature playbooks (YAML)
├── knowledge/             # Knowledge database (see docs/06)
│   ├── architecture/      # Per-subsystem docs (14 areas, 37 files)
│   ├── diagnostics/       # Classification methodology + 12-layer model (5 files)
│   └── *.yaml             # Structured data files (12 files)
├── tests/                 # Unit (660), regression (59), integration (50)
├── .claude/agents/        # z-stream-analysis.md, cluster-diagnostic.md, investigation-agent.md
├── .claude/hooks/         # agent_trace.py (trace logging)
└── docs/                  # Detailed documentation (10 files)
```
