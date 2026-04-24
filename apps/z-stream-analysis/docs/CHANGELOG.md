# Changelog

Version history for Z-Stream Pipeline Analysis. For current architecture and usage, see `CLAUDE.md`.

---

## v4.0

- **Cluster health moved to Stage 1.5** — `ClusterHealthService` deprecated. All cluster health investigation handled by the `cluster-diagnostic` AI agent (Stage 1.5), producing `cluster-diagnosis.json` with structured fields consumed by Stage 2 and Stage 3.
- **Structured health fields** — `environment_health_score` (weighted penalty formula), `operator_health`, `subsystem_health` (with `health_depth` and `unchecked_layers`), `classification_guidance`, `counter_signals`, `image_integrity`.
- **Console image integrity check** — Stage 1.5 compares the running console image against `healthy-baseline.yaml` expected prefixes (`quay.io:443/acm-d/console`, `quay.io/stolostron/console`). Non-standard images flagged in `image_integrity` field, Console subsystem marked degraded, image integrity penalty (-0.10) applied to health score. Stage 2 uses this to distinguish CSS/rendering failures from dead selectors.
- **14 diagnostic traps + Trap 1b** — expanded from 10. New Trap 9 (ResourceQuota blocking pod recreation), Trap 10 (certificate rotation silent failure + shared TLS secret pattern), Trap 11 (NetworkPolicy making pods non-functional), Trap 1b (leader election stuck — pods Running/Ready but reconciliation stopped). Counter-traps: 12 (false INFRASTRUCTURE: selector doesn't exist), 13 (false INFRASTRUCTURE: backend returns wrong data), 14 (false NO_BUG: disabled prerequisite that should be enabled). Trap 3 expanded with Recreate strategy + emptyDir operational note. All traps explicitly reported in `diagnostic_traps_applied`.
- **Layer-aware Phase 3** — bottom-up investigation checks foundational layers (Compute, Control Plane, Network, Storage) BEFORE component layers (Operators, Pods). Infrastructure guards (NetworkPolicy, ResourceQuota) checked at Layer 3 before pod health at Layer 9 — pods may LOOK healthy but be non-functional.
- **Self-healing expanded** — 5 triggers (unknown operators, new failure patterns, new dependency chains, certificate issues, post-upgrade settling) with 8-source introspection framework (ownerReferences, OLM labels, CSV metadata, K8s labels, env vars, webhooks, ConsolePlugins, APIServices).
- **Data-collector agent** — new agent enriches `core-data.json` after gather.py with AI-driven tasks: page_objects (import tracing), console_search (MCP verification), recent_selector_changes + temporal_summary (git history with intent assessment).
- **Dynamic MCH namespace** — `_discover_mch_namespace()` replaces hardcoded `open-cluster-management`. Supports `ocm`, custom namespaces.
- **PR-7 changed to context signals** — diagnostic findings are ADDITIVE, not binding classifications. Per-test counterfactual verification required.
- **PR-6b Polarion check** — PRODUCT_BUG fast-path when Polarion test case describes expected behavior that contradicts actual behavior.
- **Symmetric counterfactual** — D-V5c validates AUTOMATION_BUG ("does backend confirm expectation?"), D-V5e validates PRODUCT_BUG ("is product behavior correct?").
- **Layer discrepancy detection** — Tier 1 PRODUCT_BUG evidence when lower layer is healthy but higher layer shows defect.
- **Backend probes removed** — ~780 lines of deterministic backend probing (Step 4c) removed. Stage 1.5 performs comprehensive investigation instead.
- **HTML report** — Environment tab renders `image_integrity` warnings, updated health score from `cluster-diagnosis.json`, graceful fallback for missing/partial diagnosis.
- **Knowledge base expansion** — `service-map.yaml` (15+ Service-to-pod mappings with endpoint diagnostics). Components registry expanded to 70 (Hive StatefulSets: hive-clustersync, hive-machinepool; provisioning resources: HiveConfig, ClusterProvision, Install Pod, ClusterImageSet). Version constraints expanded to 5 (olm-max-openshift-version, submariner-ocp418, clustercurator-ocp421, console-mce-crashloop). Cluster lifecycle dependency chain expanded from 4-step to 12-step with layer annotations and prerequisites. Layers 3 (endpoint verification), 4 (storage model table), 5 (OLM foundational health), 6 (multi-hop token forwarding), 9 (sub-operator CRs, scheduling investigation, StatefulSet awareness) all expanded. Data-flow files corrected for console proxy chain (5-hop), search integration path (OCP console hops), and cluster provisioning (layer-annotated). Post-upgrade patterns expanded to 9 (search re-collection, webhook cert rotation, API deprecation, Pattern 10 controller disable flags). Healthy baseline updated: hive pod count 5-8 (was 3-6), hive-clustersync and hive-machinepool StatefulSets added, --disabled-controllers note.

## v3.9

- **Provably linked grouping** (Phase A4) — replaces symptom-based grouping with 3 strict criteria: (1) same exact selector AND same calling function, (2) same before-all hook in same describe block, (3) same spec file AND same exact error message AND same line number. "Button disabled", "timed out", "same feature area" are explicitly INVALID grouping criteria. Typical group count drops from 5-15 to 3-8.
- **Per-test verification within groups** (Phase B) — after investigating the first test in a group, a mandatory 4-point check (code path, backend component, user role, error element) verifies each subsequent test. Failures split from the group and receive individual 12-layer investigation inline.
- **Expanded counterfactual verification** (D-V5) — 9 verification templates covering selector-not-found, button-disabled, timeout, data-assertion, blank-page, CSS/PF6, NetworkPolicy, operator, and ResourceQuota. Each template specifies the exact verification command and reclassification logic.
- **Evidence duplication detection** (D-V5) — 5+ tests with identical evidence text trigger a flag; at least 2 must be individually verified.
- **Per-test evidence requirement** (D-V5) — every INFRASTRUCTURE classification from a cluster-wide issue must have at least one evidence source specific to that test. Cluster-wide-only evidence caps confidence at 0.60.
- **Anti-blanket-override enforcement** (investigation-agent.md) — cluster-wide findings are explicitly labeled CONTEXT, not CONCLUSIONS. Three new anti-patterns: no verbatim evidence copying, no cluster-wide-only classification, no skipping 4-point verification.
- **Counterfactual templates in diagnostic-layers.md** — 6 templates added to the 12-layer reference so investigation agents can verify selector, button-disabled, timeout, data-assertion, blank-page, and CSS issues against cluster-wide findings.
- **Schema v3.9** — new optional `verification_status` field (enum: `verified_in_group`, `split_from_group`, `individually_investigated`) tracks per-test verification outcome.

## v3.8.1

- **Counterfactual verification** (D-V5) — new mandatory validation step for INFRASTRUCTURE classifications based on cluster-wide issues (tampered image, NetworkPolicy, operator at 0 replicas, ResourceQuota). For each test, the agent must verify "would this test pass if the cluster-wide issue were fixed?" by checking the failing selector against the OFFICIAL console source (ACM-UI MCP `search_code`). A selector missing from both the tampered and official console is AUTOMATION_BUG, not INFRASTRUCTURE. Prevents anchoring bias where one strong signal is blanket-applied to all tests.
- **Phase A1 short-circuit removed** — only `cluster_connectivity == false` (cluster completely unreachable) triggers blanket INFRASTRUCTURE classification. Previously, `environment_health_score < 0.3` with CRITICAL verdict would skip all per-test analysis. Now all scores require per-test investigation with counterfactual verification, because a cluster can have critical infrastructure issues AND tests with stale selectors that would fail regardless.
- **Investigation agent anti-anchoring** — new Section 3b in `investigation-agent.md` requires counterfactual verification when cluster-wide issues are found. Explicit warning that `console_search.found=false` was checked against the running (possibly tampered) console, not the official source. Anti-patterns updated with anchoring bias detection.
- **Tampered console warning** — when the console is running a non-official image, `console_search.found` results in core-data.json are unreliable for classification. The agent must verify selectors against the official source via ACM-UI MCP before attributing failures to the tampered image.

## v3.8

- **12-layer diagnostic investigation** (Stage 2) — restructured Phase B from monolithic per-test investigation to root-cause-first analysis using a 12-layer infrastructure model (Compute, Control Plane, Network, Storage, Configuration, Authentication, Authorization, API/CRD/Webhook, Operator, Cross-Cluster, Data Flow, UI). The parent agent groups tests by shared signals (Phase A4), then spawns focused investigation agents per group. Each agent traces from the symptom downward through applicable layers to find the broken layer, investigates WHO caused it (ownerReferences, labels, creation timestamps), then classifies. Falls back to inline v3.7 tiered investigation when agents are unavailable.
- **Phase A4: Test grouping** — new grouping step after cross-test correlation. Tests sharing the same dead selector (console_search.found=false, 3+ tests) are classified directly as AUTOMATION_BUG. After-all hooks are classified as NO_BUG via PR-2. Remaining tests are grouped by shared infrastructure signals, data/component dependencies, or feature area for investigation agents. Typical: 5-15 groups from 64 failures.
- **Phase D-V: Investigation result validation** — new validation step where the parent agent cross-checks investigation agent results against PR signals (PR-6 deterministic K8s-vs-console comparison, PR-7 oracle dependencies), verifies root cause layer consistency with classification, and checks evidence completeness. D4 final validation, D4b causal link verification, and D5 counter-bias validation are preserved unchanged.
- **New knowledge file** — `knowledge/diagnostics/diagnostic-layers.md` provides the condensed 12-layer investigation methodology reference with per-layer checklists, error-to-layer mapping, and classification-after-root-cause rules. Based on DIAGNOSTIC-LAYER-ARCHITECTURE.md validated against ACM 2.16 GA (Azure) and ACM 2.17 bugged cluster (AWS).
- **New agent** — `.claude/agents/investigation-agent.md` defines the investigation subagent persona: read-only cluster access, 12-layer methodology, structured JSON output with root_cause_layer, evidence_sources, investigation_steps_taken.
- **Schema v3.8** — 4 new optional per-test fields: `root_cause_layer` (integer 1-12), `root_cause_layer_name` (enum of 12 layer names), `investigation_steps_taken` (array of per-layer verdicts), `cause_owner` (who caused the issue at root cause layer).
- **dependencies.yaml enriched** — each dependency chain gains `layers_involved` (list of layer numbers) and `layer_note` connecting horizontal dependency chains to the vertical layer model.
- **Classification decision tree updated** — structural note explains that PR-1 through PR-7 now serve as validation checks for investigation agent results, with PR-2 (cascading hook) remaining as instant classification. 3-path routing remains as fallback for direct classification.
- **HTML report** — per-test cards show layer badge (e.g., `L3: Network / Connectivity`), cause owner, and investigation steps taken (collapsible list).

## v3.7

- **Automated cluster health audit** (Stage 1 Step 4) — new `ClusterHealthService` performs a 6-phase health audit modeled on the acm-hub-health diagnostic pipeline: DISCOVER (inventory MCH, MCE, operators, nodes, clusters), LEARN (load knowledge baselines from YAML), CHECK (pod health, infrastructure guards, image integrity, managed clusters), COMPARE (baseline deviation detection), CORRELATE (map findings to feature areas), SCORE (compute `environment_health_score` 0.0-1.0 and overall verdict). Produces `cluster-health.json` (19KB) with operator health, per-subsystem health, infrastructure issues, managed cluster status, baseline comparison, console plugins, and classification guidance.
- **Knowledge database validated against live cluster** — all YAML files validated against ACM 2.16 GA on Azure. `components.yaml` expanded from 31 to 58 components with health_check commands for every entry. `healthy-baseline.yaml` now has validated pod counts for 7 namespaces. `addon-catalog.yaml` expanded from 12 to 18 addons with `cluster_management_addons` section (17 hub-side CRs). `dependencies.yaml` gained 3 new chains (operator_management, addon_delivery, registration). New `prerequisites.yaml` with 34 machine-checkable prerequisite definitions extracted from playbooks.
- **Oracle Phase 6 skipped** — the oracle's cluster health checks (Phase 6, ~420 lines) are now handled by the ClusterHealthService in Step 4. The oracle focuses on feature context: Phase 1 (feature area identification), Phase 2 (Polarion test case context), Phases 3-4 (KG subsystem topology), Phase 5 (synthesis). Always called with `skip_cluster=True`.
- **EnvironmentValidationService deprecated** — replaced by `ClusterHealthService` for health assessment. Credential extraction and kubeconfig persistence moved to `_login_to_cluster()` in gather.py. The old service is kept for backward compatibility but no longer called in the pipeline.
- **FeatureKnowledgeService cluster_health fallback** — `check_prerequisites()` now accepts `cluster_health` parameter as fallback when oracle `dependency_health` is empty (Phase 6 skipped). Operator prerequisites resolved from health audit data.
- **core-data.json gains `cluster_health` key** — compact summary with `environment_health_score`, `overall_verdict`, `critical_issue_count`, `affected_feature_areas`, and cluster identity.
- **Agent instructions updated** — Phase A-0 now reads `cluster-health.json` first. Phase A1 routing uses `overall_verdict` + `environment_health_score` instead of old `environment_score`. PR-7a uses `infrastructure_issues` from health audit as primary evidence source.
- **KG subsystem name mismatch fixed** — `KG_SUBSYSTEM_MAP` in `knowledge_graph_client.py` maps all 12 app feature area names to their KG subsystem equivalents (e.g., CLC→Cluster, GRC→Governance). Previously, `get_subsystem_components("CLC")` returned 0 components because the KG uses `Cluster`, not `CLC`. Now returns 84 components. Multi-subsystem support for areas like RBAC (Cluster + Console). Also fixed oracle `_kg_query_internal_flow()` and `_kg_query_cross_subsystem()` to use the mapping.

## v3.6

- **Comprehensive cluster diagnostic** (Stage 1.5) — after gather.py completes, a dedicated `cluster-diagnostic` agent performs a full hub-health-style 6-phase investigation of the cluster: Discover (operator inventory, webhooks, ConsolePlugins), Learn (baseline comparison, knowledge database), Check (per-namespace pod health, log pattern scanning, infrastructure guards, addon verification, trap detection), Pattern Match (failure signatures, JIRA bugs), Correlate (dependency chain tracing, cross-subsystem impact), Output (structured `cluster-diagnosis.json`). Stage 2 reads this for dramatically improved INFRASTRUCTURE vs PRODUCT_BUG disambiguation.
- **4 new knowledge files** adapted from the ACM Hub Health agent: `healthy-baseline.yaml` (expected pod counts and deployment states), `addon-catalog.yaml` (all managed cluster addons with health checks and impact statements), `webhook-registry.yaml` (expected webhooks with criticality and failure policies), `diagnostics/diagnostic-traps.md` (10 patterns where the obvious diagnosis is wrong).
- **Diagnostic trap detection** — 8 traps verified during Stage 1.5: stale MCH status, console tabs missing despite healthy pod, search empty with all green pods, observability empty due to S3, GRC non-compliant after upgrade, managed cluster NotReady misdiagnosis, mass addon failure from single pod, console cascade from search-api. (Extended to 14 traps in v4.0.)
- **Self-healing knowledge** — diagnostic agent writes discoveries about unknown operators and components to `knowledge/learned/` for future runs. Third-party operators (AAP, GitOps, CNV, MTV, OADP) are inventoried and their ACM integration assessed.
- **Stage 2 optimization** — when diagnostic data is available, Stage 2 skips redundant Tier 2-4 cluster investigation for subsystems already covered. Pre-classified infrastructure issues and confirmed-healthy subsystems eliminate redundant root cause discovery.
- **Classification guidance** — diagnostic produces `classification_guidance` with `pre_classified_infrastructure` (Tier 1 evidence with confidence), `confirmed_healthy` (subsystems where infrastructure is ruled out), and `partial_impact` (transitive dependency effects).
- **Enhanced diagnostic output** — `cluster-diagnosis.json` includes 6 additional data sections beyond subsystem health and classification guidance: `component_log_excerpts` (key error lines from unhealthy pod logs, saves Agent #2 from re-running `oc logs`), `component_restart_counts` (catches "Running but restarted 12 times"), `managed_cluster_detail` (per-cluster conditions and unavailable addons), `ocp_operators_degraded` (degraded OCP operators like dns, monitoring, ingress), `console_plugin_status` (plugin registrations with backend health to prevent Trap 2 misclassifications).

## v3.5.1

- **External service failure detection** (Phase B3b) — console log parser extracts external service failure patterns (`failed to push to testrepo`, `SSL certificate problem`, `MTLS Test Environment setup failure`, Minio/Gogs/Tower connection errors) as a new `external_service_issues` category. Agent instructions (B3b) guide the AI to cross-reference console log evidence with Jenkins parameters (`OBJECTSTORE_PRIVATE_URL`, `TOWER_HOST`) when subscription tests timeout.
- **Version compatibility constraints** — new `knowledge/version-constraints.yaml` documents product version incompatibilities (e.g., AnsibleJob CR doesn't support AAP 2.5+ workflow jobs). Agent reads constraints when CreateContainerConfigError appears alongside healthy operator CSVs, routing to PRODUCT_BUG instead of INFRASTRUCTURE.
- **Known JIRA bugs cache** — `knowledge/failure-patterns.yaml` gains a `known_jira_bugs` section providing instant correlation for known bugs (e.g., ACM-32244 subscription timestamp issue) without requiring JIRA MCP calls.
- **External service failure signatures** — 3 new signatures in `knowledge/architecture/application-lifecycle/failure-signatures.md` for Minio unreachable, Gogs Git server down, and MTLS setup failure. 4 new `external_service` patterns in `failure-patterns.yaml`.
- **ALC repo fallback** — `KNOWN_REPOS` dict in `shared_utils.py` now includes `alc-e2e`, `alc_e2e`, `application-ui-test`, and `app-e2e` entries for robustness when console log extraction fails.
- **New failure type** — `_classify_failure_type()` returns `external_service` for errors mentioning specific external services (Minio, Gogs, Tower, MTLS setup) by name.
- **Subscription timeout disambiguation** — `failure-signatures.md` clarifies that subscription reconciliation timeouts are INFRASTRUCTURE when the controller pod is unhealthy, but PRODUCT_BUG (ACM-32244) when the controller is healthy but not reconciling.

## v3.5

Four implementation phases (A through D) build a comprehensive environment oracle:

- **Phase A: Playbook-based dependency health checking** — resolves the `met=None` gap in FeatureKnowledgeService for addon, operator, and CRD prerequisites. Discovers dependencies from feature playbooks (base.yaml), then runs targeted read-only `oc get` commands against the live cluster to check their health. Uses strict `_validate_readonly` with `ALLOWED_COMMANDS` whitelist (get, describe, api-resources only). Graceful degradation when cluster access is unavailable (dependency targets still extracted from playbooks; cluster checks skipped, prerequisites fall back to `met=None`).
- **Phase B: Polarion test case context** — fetches Polarion test case description, setup, and steps for each failed test's Polarion ID via the Polarion REST API. Parses setup HTML for dependency keywords (operators, addons, infrastructure requirements). Discovered dependencies are merged with playbook dependencies and checked on the cluster. Polarion MCP also available during Stage 2 for deeper queries. Requires `POLARION_PAT` in `mcp/polarion/.env`.
- **Phase C: KG-driven feature and dependency learning** — queries the Knowledge Graph for each feature area's component topology (internal data flow, cross-subsystem dependencies, transitive dependency chains up to depth 3) and for each individual dependency's architecture (subsystem, what it depends on, what depends on it). Includes rhacm-docs path resolution for documentation context. Stored in `cluster_oracle.knowledge_context` for AI-driven dependency chain walking during classification. Playbook architecture summaries included as context.
- **Phase D: Agent integration** — new pre-routing check PR-7 combines all oracle data (playbook health, Polarion context, KG topology) as Tier 1 evidence in Phase D classification. Oracle signals are ADDITIVE — per-test evidence (e.g., `console_search.found=false`) takes precedence. DEFINITIVE signal requires 2+ confirmed-missing dependencies. Managed clusters < 4h old are excluded from health scoring. The agent MUST read `knowledge/architecture/<area>/failure-signatures.md` before applying oracle signals.
- **Pipeline expanded to 11 steps** — new Step 5 (Environment Oracle) runs after Step 4 (environment check) and before Step 6 (repository cloning). Oracle output stored in `cluster_oracle` key of core-data.json.
- **Prerequisite resolution** — `FeatureKnowledgeService.check_prerequisites()` accepts `oracle_data` parameter, replacing previously hardcoded `met=None` results.
- **New schema fields** — `cluster_oracle` in core-data.json with `dependency_health`, `overall_feature_health`, `dependency_targets`, `feature_areas`, `knowledge_context`

## v3.4

- **Backend probe source-of-truth validation** (Phase PR-6) — when `backend_probes` includes a probe with `classification_hint` and `anomaly_source`, uses deterministic K8s-vs-console comparison. Compares cluster ground truth (`cluster_ground_truth`) against console backend response to distinguish PRODUCT_BUG (console returns wrong data despite healthy K8s) from INFRASTRUCTURE (underlying K8s resource is unhealthy). Routes with 0.85-0.90 confidence as Tier 1 evidence.
- **Cluster access confidence adjustment** (Phase PR-4b) — adjusts classification confidence by 0.15 when cluster access is unavailable during Stage 2, reflecting reduced investigation depth.

## v3.3

- **Assertion value extraction** (Phase PR-5) — parses Cypress/Chai `expected X to equal Y` errors to extract expected vs actual values, identifying data-level failures (API returned wrong data) vs selector-level failures
- **Failure mode categorization** — each test classified as `render_failure`, `element_missing`, `data_incorrect`, `timeout_general`, `assertion_logic`, `server_error`, or `unknown` — enabling causal link verification
- **Refined failure types** — `assertion` split into `assertion_data` (value/count comparisons) and `assertion_selector` (element existence/visibility)
- **Per-feature-area health scoring** (GAP-04) — `ClusterInvestigationService.get_feature_area_health()` computes per-area health scores with graduated bands: definitive (<0.3), strong (0.3-0.5), moderate (0.5-0.7), none (>0.7)
- **Per-test causal link verification** (Phase D4b) — every test attributed to a dominant pattern must have a documented causal mechanism linking the pattern to the specific error; incompatible failure modes trigger independent re-investigation
- **Counter-bias validation strengthened** (Phase D5) — 3-test threshold rule: if 3+ tests share the same root_cause, at least 1 must be independently re-investigated
- **Backend API probing** (Step 4c) — probes 5 console backend endpoints (`/authenticated`, `/hub`, `/username`, `/ansibletower`, `/proxy/search`) via `oc exec` + curl, cross-references responses against cluster landscape to detect data anomalies (wrong hub name, reversed username, empty results)
- **New schema fields** — `failure_mode_category`, `assertion_analysis` per test; `data_assertion_failures`, `feature_area_health` in summary; `backend_probes` in core-data.json

## v3.2

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

## v3.1

- **Feature investigation playbooks** (`src/data/feature_playbooks/`) — YAML playbooks with architecture, prerequisites, and known failure paths per feature area
- **FeatureKnowledgeService** — loads playbooks, checks MCH prerequisites, matches error symptoms to known failure paths
- **Tiered cluster investigation** (Tiers 0-4) — SRE debugging methodology from health snapshot to deep investigation
- **MCH component extraction** — `mch_enabled_components` and `mch_version` in `cluster_landscape`
- **Cluster kubeconfig persistence** — `cluster.kubeconfig` saved in run directory for Stage 2 re-authentication (passwords masked in core-data.json, agent uses `--kubeconfig` instead of `oc login`)
- **Feature knowledge in core-data** — `feature_knowledge` section with readiness, playbooks, KG status

## v3.0

- **Cluster landscape** (`cluster_landscape` in core-data.json) — managed clusters, operator statuses, resource pressure
- **Feature grounding** (`feature_grounding` in core-data.json) — tests grouped by feature area with subsystem/component context
- **Backend cross-check** (Phase B7) — detects UI failures caused by backend problems, overrides Path A routing
- **Targeted pod investigation** (Phase B5b) — on-demand pod diagnostics for feature area components
- **Earlier Knowledge Graph** (Phase A3b) — subsystem context built before per-test analysis
- **Feedback CLI** (`python -m src.scripts.feedback`) — rate classifications for accuracy tracking
