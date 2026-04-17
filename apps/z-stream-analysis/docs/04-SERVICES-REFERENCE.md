# Services Reference

One-stop reference for all Python services and the `ReportFormatter` class.

---

## Overview

Z-Stream Analysis uses 17 active service modules in `src/services/`, plus `ReportFormatter` in `src/scripts/report.py` and `DataGatherer` in `src/scripts/gather.py`. Services provide **factual data only** — all classification is performed by the AI agent in Stage 2. ClusterHealthService and EnvironmentValidationService exist but are deprecated and not called from the pipeline (health audit moved to Stage 1.5 cluster-diagnostic agent in v4.0).

```
gather.py ──┬── JenkinsAPIClient ──────────── Jenkins REST API
            ├── JenkinsIntelligenceService ── Build info, console log, test report
            ├── RepositoryAnalysisService ──── Git clone, file indexing
            ├── StackTraceParser ───────────── JS/TS stack trace → file:line
            ├── TimelineComparisonService ──── Git date comparison
            ├── ComponentExtractor ─────────── Error → component names
            ├── ACMConsoleKnowledge ─────────── Directory structure mapping
            ├── ACMUIMCPClient ─────────────── MCP fallback for Stage 1
            ├── ClusterInvestigationService ── Cluster landscape + pod diagnostics (v3.0)
            ├── FeatureAreaService ────────── Test-to-feature-area mapping (v3.0)
            ├── FeatureKnowledgeService ──── Playbook loading + symptom matching (v3.1)
            ├── EnvironmentOracleService ── Feature context oracle (v3.5, Phase 6 skipped in v3.7)
            └── shared_utils ──────────────── Config, subprocess, credentials

report.py ── ReportFormatter ─────────────── Markdown/JSON/text output

feedback.py  FeedbackService ─────────────── Classification accuracy tracking (v3.0)

Stage 1+2 ─── KnowledgeGraphClient ─────────── Neo4j RHACM queries via HTTP API
              SchemaValidationService ─────── JSON Schema validation
```

---

## Service Details

### 1. JenkinsIntelligenceService

| Property | Value |
|----------|-------|
| **File** | `src/services/jenkins_intelligence_service.py` (894 lines) |
| **Purpose** | Extracts build info, console log patterns, and test report from Jenkins |
| **Used by** | Stage 1, Steps 1-3 |

**Key exports:** `JenkinsIntelligenceService`, `JenkinsIntelligence`, `JenkinsMetadata`, `TestCaseFailure`, `TestReport`

**Key methods:**

| Method | Description |
|--------|-------------|
| `analyze_jenkins_url(url)` | Full analysis: build info + console log + test report |
| `_analyze_failure_patterns(console_log)` | Regex pattern matching for error categories |
| `_classify_failure_type(error_text)` | Returns factual error type (timeout, element_not_found, network, assertion_data, assertion_selector, etc.) |
| `_is_data_assertion(error_text)` | Static method. Returns True if assertion error involves data values rather than selectors (v3.3) |
| `to_dict(intelligence)` | Convert result to serializable dictionary |

---

### 2. JenkinsAPIClient

| Property | Value |
|----------|-------|
| **File** | `src/services/jenkins_api_client.py` (391 lines) |
| **Purpose** | Authenticated Jenkins REST API access via curl |
| **Used by** | Stage 1, Steps 1-3 (via JenkinsIntelligenceService) |

**Key exports:** `JenkinsAPIClient`, `get_jenkins_api_client`, `is_jenkins_available`

**Key methods:**

| Method | Description |
|--------|-------------|
| `get_build_info(url)` | GET `<url>/api/json` |
| `get_console_output(url)` | GET `<url>/consoleText` |
| `get_test_report(url)` | GET `<url>/testReport/api/json` |
| `parse_build_url(url)` | Parse Jenkins URL into components |

**Credential priority:** constructor args > environment variables > config file

---

### 3. EnvironmentValidationService

| Property | Value |
|----------|-------|
| **File** | `src/services/environment_validation_service.py` (616 lines) |
| **Purpose** | Cluster health checks using READ-ONLY oc/kubectl commands |
| **Used by** | Stage 1, Step 4 |

**Key exports:** `EnvironmentValidationService`, `EnvironmentValidationResult`, `ClusterInfo`

**Key methods:**

| Method | Description |
|--------|-------------|
| `validate_environment(cluster_name, namespaces, target_api_url, username, password)` | Full environment validation |
| `login_to_cluster(api_url, username, password)` | Authenticate to cluster |
| `check_specific_resource(resource_type, name, namespace)` | Check a specific k8s resource |
| `to_dict(result)` | Convert result to dictionary |
| `cleanup()` | Remove temporary kubeconfig |

**Kubeconfig persistence (v3.5):** After `validate_environment()`, `gather.py` calls `_persist_cluster_kubeconfig()` to create a persistent `cluster.kubeconfig` in the run directory. This kubeconfig is used by the AI agent in Stage 2 (via `--kubeconfig`) instead of re-authenticating with the masked password.

**Safety:** Only whitelisted READ-ONLY commands (`oc get`, `oc describe`, `oc whoami`, `oc version`). No write operations.

---

### 4. RepositoryAnalysisService

| Property | Value |
|----------|-------|
| **File** | `src/services/repository_analysis_service.py` (162 lines) |
| **Purpose** | Git clone and repository inference |
| **Used by** | Stage 1, Step 6 |

**Key exports:** `RepositoryAnalysisService`, `SelectorHistory`

**Key methods:**

| Method | Description |
|--------|-------------|
| `clone_to(repo_url, branch, target_path)` | Clone repository to specific path |
| `_infer_repo_from_job(job_name)` | Map job name to automation repo URL |
| `_get_head_commit(repo_path)` | Get HEAD commit hash from cloned repo |

---

### 5. StackTraceParser

| Property | Value |
|----------|-------|
| **File** | `src/services/stack_trace_parser.py` (374 lines) |
| **Purpose** | Parses JS/TS stack traces to extract file:line, error type, and failing selector |
| **Used by** | Stage 1, Steps 3 and 7 |

**Key exports:** `StackTraceParser`, `StackFrame`, `ParsedStackTrace`, `parse_stack_trace`

**Key methods:**

| Method | Description |
|--------|-------------|
| `parse(stack_trace)` | Parse full stack trace into structured frames |
| `extract_failing_selector(error_message)` | Extract CSS selector from error text |
| `extract_assertion_values(error_message)` | Extract expected vs actual values from assertion errors. Returns `{has_data_assertion, assertion_type, expected, actual, raw_assertion}` or None (v3.3) |
| `get_context_range(frame, context_lines)` | Calculate line range for context |
| `_classify_assertion_type(match, groups)` | Static method. Classifies assertion type from regex match (v3.3) |

**Class data:** `ASSERTION_PATTERNS` — 8 regex patterns for extracting assertion values from Cypress/Chai, Jest, and generic assertion formats (v3.3)

**Handles:** Webpack paths, Node.js format, async functions, Cypress error formats

---

### 6. TimelineComparisonService

| Property | Value |
|----------|-------|
| **File** | `src/services/timeline_comparison_service.py` (1027 lines) |
| **Purpose** | Compares git modification dates between automation and product repos; detects recent selector changes via git diff |
| **Used by** | Stage 1, Step 7 (timeline evidence, recent selector changes) |

**Key exports:** `TimelineComparisonService`, `TimelineComparisonResult`, `ElementTimeline`, `SelectorTimeline`, `TimeoutPatternResult`

**Key methods:**

| Method | Description |
|--------|-------------|
| `compare_timelines(selector)` | Compare automation vs product modification dates |
| `find_recent_selector_changes(lookback_commits)` | Scan git diff for selector additions/removals across last N commits (runs once, cached) |
| `cross_reference_selector(failing_selector, changes)` | Match a failing selector against cached changes to find what replaced it |
| `element_exists_in_console(element_id)` | Check if element exists in product repo |
| `get_element_last_modified(element_id)` | Get last modification date for element |
| `get_selector_last_modified(selector)` | Get last modification date for selector |
| `analyze_timeout_pattern(failed_tests, env_healthy)` | Detect mass timeout patterns |
| `clone_console_to(branch, target_path, acm_version)` | Clone console repo to target |
| `clone_kubevirt_to(branch, target_path)` | Clone kubevirt-plugin to target |

**Key outputs:** `stale_test_signal`, `product_commit_type`, `element_removed`, `element_never_existed`, `recent_selector_changes`

---

### 7. ACMConsoleKnowledge

| Property | Value |
|----------|-------|
| **File** | `src/services/acm_console_knowledge.py` (701 lines) |
| **Purpose** | Structured knowledge about ACM console directory layout for test-to-feature mapping |
| **Used by** | Stage 1, Step 7 (directory mapping); Stage 2 (investigation paths) |

**Key exports:** `ACMConsoleKnowledge`

**Key methods:**

| Method | Description |
|--------|-------------|
| `map_test_to_feature(test_name)` | Map test name to feature area |
| `get_relevant_directories(test_name, error_message)` | Get product directories to search |
| `get_investigation_paths(feature_area, failure_type)` | Suggested investigation file paths |
| `extract_selector_from_error(error_message)` | Extract selector from error text |
| `suggest_search_patterns(selector)` | Generate grep patterns for selector |
| `requires_kubevirt_repo(test_name)` | Check if test needs kubevirt-plugin |
| `find_element_with_mcp(selector, search_all_repos)` | Search via MCP integration |
---

### 8. ACMUIMCPClient

| Property | Value |
|----------|-------|
| **File** | `src/services/acm_ui_mcp_client.py` (295 lines) |
| **Purpose** | Python MCP client for Stage 1 data gathering; Stage 2 uses Claude Code's native MCP |
| **Used by** | Stage 1 (CNV detection) |

**Key exports:** `ACMUIMCPClient`, `ElementInfo`, `SearchResult`, `CNVVersionInfo`, `FleetVirtSelectors`

**Key methods:**

| Method | Description |
|--------|-------------|
| `detect_cnv_version()` | Detect CNV version from connected cluster |
| `find_test_ids(file_path, repository)` | Find data-testid/aria-label in a file |
| `search_code(query, repository)` | Search code across repos |
| `find_element_definition(selector, search_all_repos)` | Find element definitions |

---

### 9. ComponentExtractor

| Property | Value |
|----------|-------|
| **File** | `src/services/component_extractor.py` (381 lines) |
| **Purpose** | Extracts ACM component names from error messages for Knowledge Graph queries |
| **Used by** | Stage 1, Step 7 (detected_components) |

**Key exports:** `ComponentExtractor`, `ExtractedComponent`

**Key methods:**

| Method | Description |
|--------|-------------|
| `extract_from_error(error_message)` | Extract component names from error text |
| `extract_from_stack_trace(stack_trace)` | Extract from stack trace |
| `extract_from_console_log(console_log)` | Extract from console output |
| `extract_with_context(text, source)` | Extract with surrounding context |
| `extract_all_from_test_failure(error, stack, console)` | Combined extraction |
| `get_subsystem(component_name)` | Map component to subsystem |
| `get_components_by_subsystem(subsystem)` | List components in a subsystem |

**Known subsystems:** Governance, Search, Cluster, Provisioning, Observability, Application, Console, Virtualization, Infrastructure

---

### 10. KnowledgeGraphClient

| Property | Value |
|----------|-------|
| **File** | `src/services/knowledge_graph_client.py` (533 lines) |
| **Purpose** | Neo4j client for RHACM component dependency analysis via HTTP API |
| **Used by** | Stage 1 (gather.py for kg_dependency_context) and Stage 2 (Phases B5/C2/E0 via MCP) |
| **Connection** | Direct HTTP to Neo4j query API (`http://localhost:7474/db/neo4j/query/v2`). Configurable via `NEO4J_HTTP_URL`, `NEO4J_USER`, `NEO4J_PASSWORD` env vars. |

**Key exports:** `KnowledgeGraphClient`, `ComponentInfo`, `DependencyChain`, `get_knowledge_graph_client`, `is_knowledge_graph_available`

**Key methods:**

| Method | Description |
|--------|-------------|
| `get_dependencies(component)` | Direct dependencies of a component |
| `get_dependents(component)` | Components that depend on this one |
| `get_transitive_dependents(component, max_depth)` | Full dependency chain |
| `get_component_info(component)` | Detailed component information |
| `find_common_dependency(components)` | Find shared dependency root |
| `get_subsystem_components(subsystem)` | All components in a subsystem |
| `analyze_failure_impact(components)` | Cascading failure analysis |

---

### 11. SchemaValidationService

| Property | Value |
|----------|-------|
| **File** | `src/services/schema_validation_service.py` (448 lines) |
| **Purpose** | Validates analysis-results.json against JSON Schema |
| **Used by** | Stage 3 (report.py validates input) |

**Key exports:** `SchemaValidationService`, `ValidationResult`, `ValidationIssue`, `ValidationSeverity`

**Key methods:**

| Method | Description |
|--------|-------------|
| `validate(data)` | Validate dictionary against schema |
| `validate_file(file_path)` | Validate a JSON file |
| `format_issues(result)` | Format validation issues as readable text |
| `to_dict(result)` | Convert result to dictionary |

**Schema location:** `src/schemas/analysis_results_schema.json`

---

### 12. shared_utils

| Property | Value |
|----------|-------|
| **File** | `src/services/shared_utils.py` (513 lines) |
| **Purpose** | Common configuration, subprocess wrappers, credential handling, file detection |
| **Used by** | All services |

**Key exports:**

| Category | Exports |
|----------|---------|
| **Config** | `TimeoutConfig`, `RepositoryConfig`, `ThresholdConfig`, `TIMEOUTS`, `REPOS`, `THRESHOLDS` (includes `INFRA_DEFINITIVE=0.3`, `INFRA_STRONG=0.5`, `INFRA_MODERATE=0.7` — v3.3) |
| **Subprocess** | `run_subprocess`, `build_curl_command`, `execute_curl` |
| **JSON** | `parse_json_response`, `safe_json_loads` |
| **Credentials** | `get_jenkins_credentials`, `encode_basic_auth`, `get_auth_header`, `mask_sensitive_value`, `mask_sensitive_dict` |
| **File detection** | `is_test_file`, `is_framework_file`, `is_support_file` |

---

### 13. ReportFormatter

| Property | Value |
|----------|-------|
| **File** | `src/scripts/report.py` (1,049 lines) |
| **Purpose** | Formats AI analysis results into Markdown, JSON, and text reports |
| **Used by** | Stage 3 |

**Key exports:** `ReportFormatter`, `format_reports`

**Key methods:**

| Method | Description |
|--------|-------------|
| `format_all()` | Generate all three report formats |
| `format_markdown()` | Generate Detailed-Analysis.md |
| `format_json()` | Generate per-test-breakdown.json |
| `format_summary()` | Generate SUMMARY.txt |

See [03-STAGE3-REPORT-GENERATION.md](03-STAGE3-REPORT-GENERATION.md) for details.

---

### 14. ClusterInvestigationService (v3.0)

| Property | Value |
|----------|-------|
| **File** | `src/services/cluster_investigation_service.py` (543 lines) |
| **Purpose** | Cluster landscape snapshot + targeted pod-level diagnostics |
| **Used by** | Stage 1, Step 4 (landscape); Stage 2, Phase B5b (pod investigation) |

**Key exports:** `ClusterInvestigationService`, `ClusterLandscape`, `PodDiagnostics`, `ComponentDiagnostics`, `FeatureAreaHealth` (v3.3)

**Key methods:**

| Method | Description |
|--------|-------------|
| `get_cluster_landscape()` | Managed clusters, operators, resource pressure, MCH status |
| `diagnose_component(component, namespace)` | Pod status, restart counts, events, log tails |
| `diagnose_subsystem(subsystem)` | Diagnose all components in a subsystem |
| `get_resource_pressure()` | Check CPU/memory/disk/PID pressure on nodes |
| `get_feature_area_health(feature_area, landscape)` | Calculate health score for a feature area based on its components. Returns `FeatureAreaHealth` (v3.3) |
| `get_all_feature_area_health(feature_areas)` | Calculate health scores for multiple feature areas. Returns `Dict[str, FeatureAreaHealth]` (v3.3) |
| `_score_to_signal(score)` | Static method. Converts health score to signal strength using `THRESHOLDS.INFRA_*` constants (v3.3) |
| `to_dict(obj)` | Convert result to dictionary |

**Class data:** `FEATURE_AREA_SUBSYSTEM_MAP` — maps 10 feature areas (GRC, Search, CLC, etc.) to subsystem names for health scoring (v3.3)

**Safety:** READ-ONLY operations only (same as EnvironmentValidationService). Validates all commands against a whitelist.

---

### 15. FeatureAreaService (v3.0)

| Property | Value |
|----------|-------|
| **File** | `src/services/feature_area_service.py` (386 lines) |
| **Purpose** | Maps failed tests to feature areas (CLC, Search, GRC, etc.) with subsystem context |
| **Used by** | Stage 1, Step 8 (feature grounding in core-data.json) |

**Key exports:** `FeatureAreaService`, `FeatureGrounding`, `FeatureMapping`

**Key methods:**

| Method | Description |
|--------|-------------|
| `identify_feature_area(test_name)` | Map test name to feature area |
| `group_tests_by_feature(failed_tests)` | Group all failed tests by feature area |
| `get_grounding(feature_area)` | Get subsystem, key components, namespaces, investigation focus |
| `to_dict(obj)` | Convert result to dictionary |

---

### 16. FeatureKnowledgeService (v3.1)

| Property | Value |
|----------|-------|
| **File** | `src/services/feature_knowledge_service.py` (354 lines) |
| **Purpose** | Loads feature investigation playbooks (YAML), checks prerequisites against cluster state, matches error symptoms to known failure paths |
| **Used by** | Stage 1, Step 9 (feature knowledge in core-data.json) |

**Key exports:** `FeatureKnowledgeService`, `FeatureReadiness`, `PrerequisiteCheck`, `MatchedFailurePath`

**Key methods:**

| Method | Description |
|--------|-------------|
| `load_playbooks(acm_version, feature_areas)` | Load base.yaml + version overlay, filter to requested feature areas |
| `check_prerequisites(feature_area, mch_components, cluster_landscape)` | Check each prerequisite against cluster state (MCH components auto-checked, others flagged for AI) |
| `match_symptoms(feature_area, error_messages)` | Match error messages against failure path symptom regexes |
| `get_feature_readiness(feature_area, mch_components, cluster_landscape, error_messages)` | Combined prerequisite check + symptom matching into a readiness assessment |
| `get_investigation_playbook(feature_area)` | Return full playbook (architecture + failure_paths) for core-data.json injection |

**Playbook location:** `src/data/feature_playbooks/` (base.yaml, acm-2.16.yaml)

---

### 17. EnvironmentOracleService (v3.5)

| Property | Value |
|----------|-------|
| **File** | `src/services/environment_oracle_service.py` |
| **Purpose** | Feature-aware dependency health checking via a 6-phase pipeline: identify feature areas, discover Polarion test case context, learn feature architecture from KG + docs, learn dependency architecture, synthesize collection plan, collect cluster state |
| **Used by** | Stage 1, Step 5 (oracle output stored in `cluster_oracle` key of core-data.json) |

**Key exports:** `EnvironmentOracleService`, `DependencyTarget`, `DependencyHealth`, `PolarionDiscovery`

**Key methods:**

| Method | Description |
|--------|-------------|
| `run_oracle(jenkins_data, test_report, cluster_landscape, ...)` | Execute full 6-phase pipeline, returns `cluster_oracle` dict |
| `_phase1_identify(test_report, jenkins_data)` | Extract feature areas, failed test names, Polarion IDs |
| `_phase2_discover_from_polarion(polarion_ids)` | Fetch Polarion test case setup/steps, extract dependency keywords |
| `_phase3_learn_feature(identification, kg_client)` | Query KG for component topology + search rhacm-docs for architecture context |
| `_phase4_learn_dependencies_comprehensive(identification, knowledge_context, kg_client)` | Query KG for each dependency's architecture (subsystem, what depends on it) |
| `_phase5_synthesize_collection_plan(identification, polarion_discovery, knowledge_context)` | Merge playbook prereqs + KG components + Polarion deps into dependency targets |
| `_phase6_collect_cluster_state(targets, cluster_credentials, skip_cluster)` | Run read-only `oc get` commands against live cluster for each target |
| `_load_polarion_token()` | Load Polarion PAT from `mcp/polarion/.env` (repo root or app root fallback) |

**Dependency target types:** `operator`, `addon`, `crd`, `component`, `managed_clusters`

**Health statuses:** `healthy`, `degraded`, `missing`, `unknown`

**Operator check behavior:**
- CSV-based detection with prefix matching (`hive-operator` matches `hive-operator.v1.2.3`)
- Pod fallback: when no CSV match found AND target has a namespace, checks for running pods (operators deployed without OLM, e.g., Hive via MCH)

**Managed cluster health:**
- Filters out clusters created < 4 hours ago (likely test artifacts still provisioning)
- `local-cluster` is always counted regardless of age
- Health based on ManagedClusterConditionAvailable status

**Overall health scoring:**
- DEFINITIVE signal requires `confirmed_missing >= 2` AND `score < 0.3` (prevents single false positive from cascading)
- Single missing dependency produces at most `strong` signal
- Signal is additive Tier 1 evidence, not a blanket classification override

---

### 18. FeedbackService (v3.0)

| Property | Value |
|----------|-------|
| **File** | `src/services/feedback_service.py` (328 lines) |
| **Purpose** | Collects tester feedback on classification accuracy for tracking and improvement |
| **Used by** | `feedback.py` CLI (post-analysis feedback loop) |

**Key exports:** `FeedbackService`, `ClassificationFeedback`, `RunFeedback`

**Key methods:**

| Method | Description |
|--------|-------------|
| `submit_feedback(run_id, test_name, is_correct, correct_classification)` | Submit feedback for a single test |
| `submit_run_feedback(run_id, feedbacks)` | Submit feedback for multiple tests in a run |
| `get_accuracy_stats()` | Global accuracy statistics across all runs |
| `get_misclassification_patterns()` | Identify common misclassification patterns |

**Storage:** Per-run feedback in `<run_dir>/feedback.json`, global index in `runs/feedback-index.json`.

---

### 19. DataGatherer (gather.py)

| Property | Value |
|----------|-------|
| **File** | `src/scripts/gather.py` (3,649 lines) |
| **Purpose** | Stage 1 orchestrator: extracts test data from Jenkins, validates environment, gathers context |
| **Used by** | Stage 1 (all steps) |

**Note:** Backend API probing methods were removed. Backend health investigation
is handled by Stage 1.5 (cluster-diagnostic agent) and Stage 2 (analysis agent).

---

## Service-to-Stage Mapping

| Service | Stage 1 | Stage 2 | Stage 3 |
|---------|---------|---------|---------|
| JenkinsAPIClient | Steps 1-3 | | |
| JenkinsIntelligenceService | Steps 1-3 | | |
| EnvironmentValidationService | Step 4 | | |
| RepositoryAnalysisService | Step 6 | | |
| StackTraceParser | Steps 3, 7 | | |
| TimelineComparisonService | Step 7 | | |
| ACMConsoleKnowledge | Step 7 | Phase B | |
| ACMUIMCPClient | Steps 6, 10 | | |
| ComponentExtractor | Step 7 | | |
| KnowledgeGraphClient | Step 9 | Phases B5, C2, E0 | |
| ClusterInvestigationService | Step 4 | Phase B5b | |
| FeatureAreaService | Step 8 | | |
| FeatureKnowledgeService | Step 9 | | |
| EnvironmentOracleService | Step 5 | Phase PR-7 | Dependency health |
| SchemaValidationService | | | Input validation |
| shared_utils | All steps | | |
| ReportFormatter | | | All output |
| FeedbackService | | | Feedback CLI |

---

## Statistics

| Metric | Value |
|--------|-------|
| Total service lines | ~7,740 (services only, excl. `__init__.py`) |
| Service files | 16 (+ReportFormatter, +DataGatherer) |
| Data classes | 36 |
| Configuration | Centralized in shared_utils |
