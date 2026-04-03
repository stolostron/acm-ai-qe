# Z-Stream Pipeline Analysis (v3.7)

Enterprise Jenkins pipeline failure analysis with definitive PRODUCT BUG | AUTOMATION BUG | INFRASTRUCTURE classification. v3.7 adds automated 6-phase cluster health audit (ClusterHealthService) that replaces the narrow EnvironmentValidationService, producing comprehensive `cluster-health.json` with operator health, subsystem health, infrastructure issues, and classification guidance. The oracle's Phase 6 (cluster health checks) is now handled by the health audit, and the oracle focuses on feature context (Polarion, KG topology).

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
   Stage 2: Analyzing <N> failed tests (5-phase investigation)...
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
STAGE 1: gather.py      → core-data.json + cluster-health.json + cluster.kubeconfig + repos/
  Step 1: Jenkins build info + cluster credential extraction
  Step 2: Console log download + parsing
  Step 3: Test report extraction
  Step 4: Cluster health audit (ClusterHealthService, 6-phase) + landscape + backend probes
  Step 5: Feature context oracle (Polarion, KG topology — Phase 6 health checks skipped)
  Step 6-11: Repo cloning, context extraction, feature grounding, knowledge, inventory, hints
STAGE 1.5: cluster-diagnostic agent → cluster-diagnosis.json (optional deep investigation)
STAGE 2: AI Analysis    → analysis-results.json (5-phase investigation, uses health + diagnostic data)
STAGE 3: report.py      → Detailed-Analysis.md + analysis-report.html + per-test-breakdown.json + SUMMARY.txt
```

Stage 1 runs gather.py with 11 steps. Step 4 performs the comprehensive cluster health audit (6 phases: DISCOVER, LEARN, CHECK, COMPARE, CORRELATE, SCORE) producing `cluster-health.json`. Step 5 runs the oracle for feature context only (Polarion test cases, KG topology). Stage 1.5 is optional — runs the cluster-diagnostic agent for deeper AI-driven investigation. Stage 2 reads `cluster-health.json` + `core-data.json` for analysis.

See `docs/00-OVERVIEW.md` for detailed diagrams.

## Run Directory

See `docs/00-OVERVIEW.md` for full run directory structure. Key files: `core-data.json` (primary AI input), `cluster-health.json` (comprehensive health audit, 19KB), `cluster.kubeconfig` (persisted cluster auth for Stage 2), `pipeline.log.jsonl` (structured service logs), `analysis-results.json` (AI output), `Detailed-Analysis.md` (final report), `analysis-report.html` (interactive HTML report).

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

## New in v3.7

- **Automated cluster health audit** (Stage 1 Step 4) — new `ClusterHealthService` performs a 6-phase health audit modeled on the acm-hub-health diagnostic pipeline: DISCOVER (inventory MCH, MCE, operators, nodes, clusters), LEARN (load knowledge baselines from YAML), CHECK (pod health, infrastructure guards, image integrity, managed clusters), COMPARE (baseline deviation detection), CORRELATE (map findings to feature areas), SCORE (compute `environment_health_score` 0.0-1.0 and overall verdict). Produces `cluster-health.json` (19KB) with operator health, per-subsystem health, infrastructure issues, managed cluster status, baseline comparison, console plugins, and classification guidance.
- **Knowledge database validated against live cluster** — all YAML files validated against ACM 2.16 GA on Azure. `components.yaml` expanded from 31 to 58 components with health_check commands for every entry. `healthy-baseline.yaml` now has validated pod counts for 7 namespaces. `addon-catalog.yaml` expanded from 12 to 18 addons with `cluster_management_addons` section (17 hub-side CRs). `dependencies.yaml` gained 3 new chains (operator_management, addon_delivery, registration). New `prerequisites.yaml` with 34 machine-checkable prerequisite definitions extracted from playbooks.
- **Oracle Phase 6 skipped** — the oracle's cluster health checks (Phase 6, ~420 lines) are now handled by the ClusterHealthService in Step 4. The oracle focuses on feature context: Phase 1 (feature area identification), Phase 2 (Polarion test case context), Phases 3-4 (KG subsystem topology), Phase 5 (synthesis). Always called with `skip_cluster=True`.
- **EnvironmentValidationService deprecated** — replaced by `ClusterHealthService` for health assessment. Credential extraction and kubeconfig persistence moved to `_login_to_cluster()` in gather.py. The old service is kept for backward compatibility but no longer called in the pipeline.
- **FeatureKnowledgeService cluster_health fallback** — `check_prerequisites()` now accepts `cluster_health` parameter as fallback when oracle `dependency_health` is empty (Phase 6 skipped). Operator prerequisites resolved from health audit data.
- **core-data.json gains `cluster_health` key** — compact summary with `environment_health_score`, `overall_verdict`, `critical_issue_count`, `affected_feature_areas`, and cluster identity.
- **Agent instructions updated** — Phase A-0 now reads `cluster-health.json` first. Phase A1 routing uses `overall_verdict` + `environment_health_score` instead of old `environment_score`. PR-7a uses `infrastructure_issues` from health audit as primary evidence source.
- **KG subsystem name mismatch fixed** — `KG_SUBSYSTEM_MAP` in `knowledge_graph_client.py` maps all 12 app feature area names to their KG subsystem equivalents (e.g., CLC→Cluster, GRC→Governance). Previously, `get_subsystem_components("CLC")` returned 0 components because the KG uses `Cluster`, not `CLC`. Now returns 84 components. Multi-subsystem support for areas like RBAC (Cluster + Console). Also fixed oracle `_kg_query_internal_flow()` and `_kg_query_cross_subsystem()` to use the mapping.

## New in v3.6

- **Comprehensive cluster diagnostic** (Stage 1.5) — after gather.py completes, a dedicated `cluster-diagnostic` agent performs a full hub-health-style 6-phase investigation of the cluster: Discover (operator inventory, webhooks, ConsolePlugins), Learn (baseline comparison, knowledge database), Check (per-namespace pod health, log pattern scanning, infrastructure guards, addon verification, trap detection), Pattern Match (failure signatures, JIRA bugs), Correlate (dependency chain tracing, cross-subsystem impact), Output (structured `cluster-diagnosis.json`). Stage 2 reads this for dramatically improved INFRASTRUCTURE vs PRODUCT_BUG disambiguation.
- **4 new knowledge files** adapted from the ACM Hub Health agent: `healthy-baseline.yaml` (expected pod counts and deployment states), `addon-catalog.yaml` (all managed cluster addons with health checks and impact statements), `webhook-registry.yaml` (expected webhooks with criticality and failure policies), `diagnostics/diagnostic-traps.md` (10 patterns where the obvious diagnosis is wrong).
- **Diagnostic trap detection** — 10 traps verified during Stage 1.5: stale MCH status, console tabs missing despite healthy pod, search empty with all green pods, observability empty due to S3, GRC non-compliant after upgrade, managed cluster NotReady misdiagnosis, mass addon failure from single pod, console cascade from search-api.
- **Self-healing knowledge** — diagnostic agent writes discoveries about unknown operators and components to `knowledge/learned/` for future runs. Third-party operators (AAP, GitOps, CNV, MTV, OADP) are inventoried and their ACM integration assessed.
- **Stage 2 optimization** — when diagnostic data is available, Stage 2 skips redundant Tier 2-4 cluster investigation for subsystems already covered. Pre-classified infrastructure issues and confirmed-healthy subsystems eliminate redundant root cause discovery.
- **Classification guidance** — diagnostic produces `classification_guidance` with `pre_classified_infrastructure` (Tier 1 evidence with confidence), `confirmed_healthy` (subsystems where infrastructure is ruled out), and `partial_impact` (transitive dependency effects).
- **Enhanced diagnostic output** — `cluster-diagnosis.json` includes 6 additional data sections beyond subsystem health and classification guidance: `component_log_excerpts` (key error lines from unhealthy pod logs, saves Agent #2 from re-running `oc logs`), `component_restart_counts` (catches "Running but restarted 12 times"), `managed_cluster_detail` (per-cluster conditions and unavailable addons), `ocp_operators_degraded` (degraded OCP operators like dns, monitoring, ingress), `console_plugin_status` (plugin registrations with backend health to prevent Trap 2 misclassifications).

## New in v3.5.1

- **External service failure detection** (Phase B3b) — console log parser extracts external service failure patterns (`failed to push to testrepo`, `SSL certificate problem`, `MTLS Test Environment setup failure`, Minio/Gogs/Tower connection errors) as a new `external_service_issues` category. Agent instructions (B3b) guide the AI to cross-reference console log evidence with Jenkins parameters (`OBJECTSTORE_PRIVATE_URL`, `TOWER_HOST`) when subscription tests timeout.
- **Version compatibility constraints** — new `knowledge/version-constraints.yaml` documents product version incompatibilities (e.g., AnsibleJob CR doesn't support AAP 2.5+ workflow jobs). Agent reads constraints when CreateContainerConfigError appears alongside healthy operator CSVs, routing to PRODUCT_BUG instead of INFRASTRUCTURE.
- **Known JIRA bugs cache** — `knowledge/failure-patterns.yaml` gains a `known_jira_bugs` section providing instant correlation for known bugs (e.g., ACM-32244 subscription timestamp issue) without requiring JIRA MCP calls.
- **External service failure signatures** — 3 new signatures in `knowledge/architecture/application-lifecycle/failure-signatures.md` for Minio unreachable, Gogs Git server down, and MTLS setup failure. 4 new `external_service` patterns in `failure-patterns.yaml`.
- **ALC repo fallback** — `KNOWN_REPOS` dict in `shared_utils.py` now includes `alc-e2e`, `alc_e2e`, `application-ui-test`, and `app-e2e` entries for robustness when console log extraction fails.
- **New failure type** — `_classify_failure_type()` returns `external_service` for errors mentioning specific external services (Minio, Gogs, Tower, MTLS setup) by name.
- **Subscription timeout disambiguation** — `failure-signatures.md` clarifies that subscription reconciliation timeouts are INFRASTRUCTURE when the controller pod is unhealthy, but PRODUCT_BUG (ACM-32244) when the controller is healthy but not reconciling.

## New in v3.5

Four implementation phases (A through D) build a comprehensive environment oracle:

- **Phase A: Playbook-based dependency health checking** — resolves the `met=None` gap in FeatureKnowledgeService for addon, operator, and CRD prerequisites. Discovers dependencies from feature playbooks (base.yaml), then runs targeted read-only `oc get` commands against the live cluster to check their health. Uses strict `_validate_readonly` with `ALLOWED_COMMANDS` whitelist (get, describe, api-resources only). Graceful degradation when cluster access is unavailable (dependency targets still extracted from playbooks; cluster checks skipped, prerequisites fall back to `met=None`).
- **Phase B: Polarion test case context** — fetches Polarion test case description, setup, and steps for each failed test's Polarion ID via the Polarion REST API. Parses setup HTML for dependency keywords (operators, addons, infrastructure requirements). Discovered dependencies are merged with playbook dependencies and checked on the cluster. Polarion MCP also available during Stage 2 for deeper queries. Requires `POLARION_PAT` in `mcp/polarion/.env`.
- **Phase C: KG-driven feature and dependency learning** — queries the Knowledge Graph for each feature area's component topology (internal data flow, cross-subsystem dependencies, transitive dependency chains up to depth 3) and for each individual dependency's architecture (subsystem, what it depends on, what depends on it). Includes rhacm-docs path resolution for documentation context. Stored in `cluster_oracle.knowledge_context` for AI-driven dependency chain walking during classification. Playbook architecture summaries included as context.
- **Phase D: Agent integration** — new pre-routing check PR-7 combines all oracle data (playbook health, Polarion context, KG topology) as Tier 1 evidence in Phase D classification. Oracle signals are ADDITIVE — per-test evidence (e.g., `console_search.found=false`) takes precedence. DEFINITIVE signal requires 2+ confirmed-missing dependencies. Managed clusters < 4h old are excluded from health scoring. The agent MUST read `knowledge/architecture/<area>/failure-signatures.md` before applying oracle signals.
- **Pipeline expanded to 11 steps** — new Step 5 (Environment Oracle) runs after Step 4 (environment check) and before Step 6 (repository cloning). Oracle output stored in `cluster_oracle` key of core-data.json.
- **Prerequisite resolution** — `FeatureKnowledgeService.check_prerequisites()` accepts `oracle_data` parameter, replacing previously hardcoded `met=None` results.
- **New schema fields** — `cluster_oracle` in core-data.json with `dependency_health`, `overall_feature_health`, `dependency_targets`, `feature_areas`, `knowledge_context`

## New in v3.4

- **Backend probe source-of-truth validation** (Phase PR-6) — when `backend_probes` includes a probe with `classification_hint` and `anomaly_source`, uses deterministic K8s-vs-console comparison. Compares cluster ground truth (`cluster_ground_truth`) against console backend response to distinguish PRODUCT_BUG (console returns wrong data despite healthy K8s) from INFRASTRUCTURE (underlying K8s resource is unhealthy). Routes with 0.85-0.90 confidence as Tier 1 evidence.
- **Cluster access confidence adjustment** (Phase PR-4b) — adjusts classification confidence by 0.15 when cluster access is unavailable during Stage 2, reflecting reduced investigation depth.

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
| ACM-UI | 20 | ACM Console + kubevirt-plugin source code search via GitHub |
| Jenkins | 7+4 | Jenkins pipeline API + ACM-specific analysis tools |
| JIRA | 25 | Issue search, creation, management for bug correlation (Jira Cloud) |
| Polarion | 25 | Polarion test case access + dependency discovery |
| Knowledge Graph (Neo4j RHACM) | 2 | Component dependency analysis via Cypher queries (optional) |

**Jenkins:** Credentials are stored in `mcp/.external/jenkins-mcp/.env` (source of truth) with `JENKINS_USER` and `JENKINS_API_TOKEN`. Run `bash mcp/setup.sh` to configure credentials and generate `.mcp.json` with them injected into the `env` field. Both the MCP server and Stage 1 gather.py read from `.mcp.json`. The `JenkinsAPIClient` checks credentials in order: constructor args > `JENKINS_USER`/`JENKINS_API_TOKEN` env vars > `.mcp.json` env section > legacy MCP configs. To update credentials, edit the `.env` file and re-run `setup.sh` to regenerate `.mcp.json`.

**JIRA Cloud:** Uses basic auth (email + API token). Run `bash mcp/setup.sh` to clone the server, configure credentials, and generate `.mcp.json` with credentials injected into the `env` field. Credentials are stored in `mcp/.external/jira-mcp-server/.env` (source of truth); re-run `setup.sh` after editing `.env` to regenerate `.mcp.json`. API token: https://id.atlassian.com/manage-profile/security/api-tokens

**Knowledge Graph:** The KG client (`knowledge_graph_client.py`) queries Neo4j directly via HTTP API (`http://localhost:7474`). It works in both Stage 1 (gather.py populates `kg_dependency_context` in core-data.json) and Stage 2 (AI agent uses MCP tools for ad-hoc queries via `uvx`). `setup.sh` handles the full Neo4j setup automatically: creates the Podman container, clones the knowledge-graph repo (base graph + extensions), and loads all data. To restart manually: `podman start neo4j-rhacm`. Connection settings configurable via `NEO4J_HTTP_URL`, `NEO4J_USER`, `NEO4J_PASSWORD` env vars (defaults: `localhost:7474`, `neo4j`, `rhacmgraph`).

**KG label mapping:** The Knowledge Graph uses descriptive labels (e.g., `"API Gateway Controller"`), not pod names (e.g., `"search-api"`). The AI instructions include a `pod_to_kg_label` map and a `query_strategy` that directs the AI to use `get_subsystem_components` first to discover actual KG labels before querying by component.

**KG subsystem mapping (v3.7):** The KG uses 7 broad subsystem names (Overview, Cluster, Governance, Console, Application, Observability, Search) while the app uses 12+ feature area names. `KG_SUBSYSTEM_MAP` in `knowledge_graph_client.py` translates automatically (e.g., CLC→Cluster, GRC→Governance, RBAC→Cluster+Console). The `resolve_kg_subsystems()` static method is available for custom queries.

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
| Knowledge database reference | `docs/06-KNOWLEDGE-DATABASE.md` |
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

## Logging & Observability

Two-layer structured logging captures every operation across all pipeline stages.

### Layer 1: Python Service Logs (`pipeline.log.jsonl`)

Written to the run directory by `src/logging_config.py`. Captures all `logging.getLogger()` calls from 18 Python service modules with `run_id` and `stage` context on every entry. Console output shows colored human-readable format; the JSONL file captures DEBUG-level detail.

```bash
# View all warnings/errors from a run
grep '"level": "warning"\|"level": "error"' runs/<dir>/pipeline.log.jsonl

# Filter by stage
grep '"stage": "oracle"' runs/<dir>/pipeline.log.jsonl

# Filter by service
grep '"logger": "src.services.jenkins_api_client"' runs/<dir>/pipeline.log.jsonl
```

### Layer 2: Agent Trace Logs (`.claude/traces/<session_id>.jsonl`)

Written by Claude Code hooks (`.claude/hooks/agent_trace.py`). Captures every tool call, MCP interaction, shell command, subagent spawn, and user prompt during Stage 2 AI analysis. Hooks are configured in `.claude/settings.json`.

```bash
# View all MCP calls from a session
grep '"mcp_server"' .claude/traces/<session_id>.jsonl

# View prompts
grep '"event": "prompt"' .claude/traces/<session_id>.jsonl

# View tool errors
grep '"event": "tool_error"' .claude/traces/<session_id>.jsonl
```

## Tests

```bash
# Regression tests (fast, no external deps — 47 tests):
python -m pytest tests/regression/ -v

# Unit tests (660+ tests):
python -m pytest tests/unit/ -v

# Unit + regression (707+ tests):
python -m pytest tests/unit/ tests/regression/ -v

# Integration tests (requires Jenkins VPN — 50 tests):
python -m pytest tests/integration/ -v --timeout=300

# All tests (717+ total):
python -m pytest tests/ -v --timeout=300
```

### Test Structure

- `tests/unit/` — 660+ unit tests across 19 service/script files (includes 77 oracle + 40 health service tests)
- `tests/regression/` — 47 regression tests for cross-module consistency, playbook quality, AI instructions, schema coverage
- `tests/integration/` — 50 integration tests for Stage 1 gather, Stage 3 report, and cross-stage data contracts
- `tests/fixtures/` — Synthetic analysis-results.json exercising v3.2+ schema fields

## Knowledge Database (`knowledge/`)

Standalone knowledge database providing domain reference data for the AI agent
during Stage 2 analysis. Complements the feature playbooks at
`src/data/feature_playbooks/` which are programmatically consumed during Stage 1.

### Architecture Docs (`knowledge/architecture/`)

Per-subsystem deep knowledge: architecture, data flow, and failure signatures.
The AI agent reads the relevant subsystem docs at the start of Phase A0 based
on the detected feature area.

| Subsystem | Files | Key content |
|-----------|-------|-------------|
| Platform | `acm-platform.md`, `kubernetes-fundamentals.md` | Operator hierarchy, MCH, namespaces, K8s concepts |
| Search | `search/{architecture,data-flow,failure-signatures}.md` | search-api/postgres/collector, GraphQL flow, DB corruption |
| Console | `console/{architecture,data-flow,failure-signatures}.md` | React frontend, Node.js backend, SSE events, proxy routes |
| Governance | `governance/{architecture,data-flow,failure-signatures}.md` | Policy propagator, spoke addons, compliance flow |
| Cluster Lifecycle | `cluster-lifecycle/{architecture,data-flow,failure-signatures}.md` | Hive, webhooks, import controller, cluster ops |
| Virtualization | `virtualization/{architecture,data-flow,failure-signatures}.md` | CNV, MTV, VM actions, CCLM, KVM nodes |
| App Lifecycle | `application-lifecycle/{architecture,data-flow,failure-signatures}.md` | Subscriptions, channels, ArgoCD, app status |
| RBAC | `rbac/{architecture,data-flow,failure-signatures}.md` | FG-RBAC, MCRA, ClusterPermission, IDP auth |
| Automation | `automation/{architecture,data-flow,failure-signatures}.md` | ClusterCurator, Ansible Tower integration |
| Observability | `observability/{architecture,failure-signatures}.md` | MCO, Thanos, Grafana |
| Foundation | `foundation/{architecture,test-dependencies,failure-signatures}.md` | Addon framework, registration, cluster-proxy, multi-cloud spokes |
| Install | `install/{architecture,test-dependencies,failure-signatures}.md` | ACM/MCE install, CSV phases, operator lifecycle |
| Infrastructure | `infrastructure/{architecture,failure-signatures,post-upgrade-patterns}.md` | Nodes, quotas, NetworkPolicies, certs, post-upgrade |

### Diagnostics Docs (`knowledge/diagnostics/`)

Classification methodology documentation for the AI agent:

| File | Content |
|------|---------|
| `classification-decision-tree.md` | Complete PR-1 through PR-7 decision tree with 3-path routing |
| `evidence-tiers.md` | How Tier 1 and Tier 2 evidence is weighted for confidence scoring |
| `common-misclassifications.md` | 6 documented cases where the pipeline gets confused and why |
| `diagnostic-traps.md` | 10 patterns where the obvious diagnosis is WRONG (8 from hub health + 2 counter-traps) |

### Structured Data (YAML files)

| File | Content | Used For |
|------|---------|----------|
| `components.yaml` | ACM component registry (name, namespace, labels, health checks) | Component health context |
| `dependencies.yaml` | Dependency chains with cascade failure paths | Root cause tracing |
| `selectors.yaml` | UI selector ground truth per feature area | Stale selector detection |
| `api-endpoints.yaml` | Backend API endpoints with probe commands | Backend cross-check context |
| `feature-areas.yaml` | Feature area index (test patterns, components, routes) | Test-to-feature mapping |
| `failure-patterns.yaml` | Known failure signatures + known JIRA bugs cache + external service patterns | Fast pattern matching + JIRA correlation |
| `version-constraints.yaml` | Product version incompatibility matrix (e.g., AAP 2.5+ workflow jobs) | Version-aware classification |
| `test-mapping.yaml` | Test suite to feature area mapping with known issues | Investigation scoping |
| `healthy-baseline.yaml` | Expected pod counts, deployment states, node thresholds per namespace (validated against live cluster) | Baseline comparison in Step 4 health audit + Stage 1.5 diagnostic |
| `addon-catalog.yaml` | 18 managed cluster addons with health checks, dependencies, impact + 17 ClusterManagementAddon CRs | Addon health verification in Step 4 + Stage 1.5 |
| `webhook-registry.yaml` | 19 expected webhooks with criticality, failure policies, impact | Webhook verification in Stage 1.5 |
| `prerequisites.yaml` | 34 machine-checkable prerequisites per feature area (mch_component, addon, operator, crd, informational) | Feature readiness in Step 9, prerequisite validation |
| `learned/` | Agent-contributed corrections, patterns, selector changes, operator discoveries | Accumulated knowledge (self-healing) |
| `refresh.py` | Updates knowledge from ACM-UI MCP, KG, cluster | Self-healing |

### How the Agent Uses the Knowledge Database

1. **Phase A0:** Read `architecture/<area>/architecture.md` and `data-flow.md` for each detected feature area
2. **Phase B:** Check `architecture/<area>/failure-signatures.md` for known patterns before full investigation
3. **Phase D:** Reference `diagnostics/classification-decision-tree.md` for routing logic
4. **After classification:** Write new discoveries to `learned/` for future runs

## File Structure

```
z-stream-analysis/
├── main.py                 # Entry point
├── pytest.ini              # Test markers (regression, integration, slow)
├── src/logging_config.py   # Structured logging (console + JSONL dual output)
├── src/scripts/
│   ├── gather.py          # Stage 1: Data collection
│   ├── report.py          # Stage 3: Report generation
│   └── feedback.py        # Classification feedback CLI
├── src/services/          # 18 Python service modules
├── src/reports/
│   └── html_report.py     # Interactive HTML report generator (schema: src/schemas/html_report_schema.json)
├── src/schemas/           # JSON Schema validation
├── src/data/
│   └── feature_playbooks/ # YAML investigation playbooks (base.yaml, acm-2.16.yaml)
├── knowledge/             # Knowledge database (AI reads during Stage 2)
│   ├── architecture/      # Per-subsystem deep knowledge (37 files)
│   │   ├── acm-platform.md          # Platform: operator hierarchy, MCH, namespaces
│   │   ├── kubernetes-fundamentals.md # K8s concepts for failure analysis
│   │   ├── search/                  # Search subsystem (3 files)
│   │   ├── console/                 # Console subsystem (3 files)
│   │   ├── governance/              # GRC subsystem (3 files)
│   │   ├── cluster-lifecycle/       # CLC subsystem (3 files)
│   │   ├── virtualization/          # Fleet Virt subsystem (3 files)
│   │   ├── application-lifecycle/   # ALC subsystem (3 files)
│   │   ├── rbac/                    # RBAC subsystem (3 files)
│   │   ├── automation/              # Ansible subsystem (3 files)
│   │   ├── observability/           # Observability (2 files)
│   │   ├── foundation/             # Foundation subsystem (3 files)
│   │   ├── install/                # Install subsystem (3 files)
│   │   └── infrastructure/          # Infrastructure (3 files)
│   ├── diagnostics/       # Classification methodology + diagnostic traps
│   │   ├── classification-decision-tree.md
│   │   ├── evidence-tiers.md
│   │   ├── common-misclassifications.md
│   │   └── diagnostic-traps.md        # 10 traps where obvious diagnosis is wrong (v3.6)
│   ├── components.yaml    # Component registry
│   ├── dependencies.yaml  # Dependency chains
│   ├── selectors.yaml     # UI selector ground truth
│   ├── api-endpoints.yaml # Backend API endpoints
│   ├── feature-areas.yaml # Feature area index
│   ├── failure-patterns.yaml # Known failure patterns + JIRA bugs cache
│   ├── version-constraints.yaml # Product version compatibility matrix
│   ├── test-mapping.yaml  # Test suite mapping
│   ├── healthy-baseline.yaml  # Expected pod counts, deployments (Step 4 + Stage 1.5)
│   ├── addon-catalog.yaml     # 18 addons + 17 ClusterManagementAddon CRs (Step 4 + Stage 1.5)
│   ├── webhook-registry.yaml  # 19 expected webhooks + criticality (Stage 1.5)
│   ├── prerequisites.yaml     # 34 feature prerequisites (Step 9 readiness)
│   ├── learned/           # Agent-contributed knowledge (self-healing)
│   └── refresh.py         # Knowledge refresh script
├── tests/
│   ├── conftest.py        # Shared fixtures
│   ├── unit/              # Unit tests (660+)
│   ├── regression/        # Regression tests (47)
│   ├── integration/       # Integration tests (50)
│   └── fixtures/          # Test data (synthetic analysis-results.json)
├── .claude/
│   ├── agents/
│   │   ├── z-stream-analysis.md  # Stage 2 analysis agent
│   │   └── cluster-diagnostic.md # Stage 1.5 cluster diagnostic agent
│   ├── hooks/
│   │   └── agent_trace.py        # Hook: logs tool calls, MCP, prompts to JSONL
│   ├── traces/                   # Agent trace logs (per-session JSONL, gitignored)
│   └── settings.json             # Permissions + hook configuration
└── docs/                  # Detailed documentation
```
