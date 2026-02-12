# Services Reference

One-stop reference for all 13 Python services and the `ReportFormatter` class.

---

## Overview

Z-Stream Analysis uses 13 service modules (12 in `src/services/`, plus `ReportFormatter` in `src/scripts/report.py`). Services provide **factual data only** — all classification is performed by the AI agent in Stage 2.

```
gather.py ──┬── JenkinsAPIClient ──────────── Jenkins REST API
            ├── JenkinsIntelligenceService ── Build info, console log, test report
            ├── EnvironmentValidationService  Cluster health (oc/kubectl)
            ├── RepositoryAnalysisService ──── Git clone, file indexing
            ├── StackTraceParser ───────────── JS/TS stack trace → file:line
            ├── TimelineComparisonService ──── Git date comparison
            ├── ComponentExtractor ─────────── Error → component names
            ├── ACMConsoleKnowledge ─────────── Directory structure mapping
            ├── ACMUIMCPClient ─────────────── MCP fallback for Stage 1
            └── shared_utils ──────────────── Config, subprocess, credentials

report.py ── ReportFormatter ─────────────── Markdown/JSON/text output

Stage 2 ───── SchemaValidationService ─────── JSON Schema validation
              KnowledgeGraphClient ─────────── Neo4j RHACM queries (optional)
```

---

## Service Details

### 1. JenkinsIntelligenceService

| Property | Value |
|----------|-------|
| **File** | `src/services/jenkins_intelligence_service.py` (900 lines) |
| **Purpose** | Extracts build info, console log patterns, and test report from Jenkins |
| **Used by** | Stage 1, Steps 1-3 |

**Key exports:** `JenkinsIntelligenceService`, `JenkinsIntelligence`, `JenkinsMetadata`, `TestCaseFailure`, `TestReport`

**Key methods:**

| Method | Description |
|--------|-------------|
| `analyze_jenkins_url(url)` | Full analysis: build info + console log + test report |
| `_analyze_failure_patterns(console_log)` | Regex pattern matching for error categories |
| `_classify_failure_type(error_text)` | Returns factual error type (timeout, element_not_found, network, etc.) |
| `to_dict(intelligence)` | Convert result to serializable dictionary |

---

### 2. JenkinsAPIClient

| Property | Value |
|----------|-------|
| **File** | `src/services/jenkins_api_client.py` (449 lines) |
| **Purpose** | Authenticated Jenkins REST API access via curl |
| **Used by** | Stage 1, Steps 1-3 (via JenkinsIntelligenceService) |

**Key exports:** `JenkinsAPIClient`, `get_jenkins_api_client`, `is_jenkins_available`

**Key methods:**

| Method | Description |
|--------|-------------|
| `get_build_info(url)` | GET `<url>/api/json` |
| `get_console_output(url)` | GET `<url>/consoleText` |
| `get_test_report(url)` | GET `<url>/testReport/api/json` |
| `get_build_parameters(url)` | Extract build parameters |
| `parse_build_url(url)` | Parse Jenkins URL into components |
| `verify_connection()` | Test Jenkins connectivity |

**Credential priority:** constructor args > environment variables > config file

---

### 3. EnvironmentValidationService

| Property | Value |
|----------|-------|
| **File** | `src/services/environment_validation_service.py` (615 lines) |
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

**Safety:** Only whitelisted READ-ONLY commands (`oc get`, `oc describe`, `oc whoami`, `oc version`). No write operations.

---

### 4. RepositoryAnalysisService

| Property | Value |
|----------|-------|
| **File** | `src/services/repository_analysis_service.py` (437 lines) |
| **Purpose** | Git clone and repository file analysis |
| **Used by** | Stage 1, Steps 5-7 |

**Key exports:** `RepositoryAnalysisService`, `RepositoryAnalysisResult`, `TestFileInfo`, `DependencyInfo`, `SelectorHistory`

**Key methods:**

| Method | Description |
|--------|-------------|
| `clone_to(repo_url, branch, target_path)` | Clone repository to specific path |
| `get_selector_history(repo_path, selector, file_path)` | Git history for a selector |
| `get_file_content_around_line(repo_path, file_path, line, context)` | Read file with context lines |
| `resolve_imports(repo_path, file_path)` | Resolve import paths in test files |
| `get_targeted_evidence(repo_path, file, line, selector)` | Gather evidence for a failure |

---

### 5. StackTraceParser

| Property | Value |
|----------|-------|
| **File** | `src/services/stack_trace_parser.py` (378 lines) |
| **Purpose** | Parses JS/TS stack traces to extract file:line, error type, and failing selector |
| **Used by** | Stage 1, Step 3 |

**Key exports:** `StackTraceParser`, `StackFrame`, `ParsedStackTrace`, `parse_stack_trace`

**Key methods:**

| Method | Description |
|--------|-------------|
| `parse(stack_trace)` | Parse full stack trace into structured frames |
| `extract_failing_selector(error_message)` | Extract CSS selector from error text |
| `get_context_range(frame, context_lines)` | Calculate line range for context |

**Handles:** Webpack paths, Node.js format, async functions, Cypress error formats

---

### 6. TimelineComparisonService

| Property | Value |
|----------|-------|
| **File** | `src/services/timeline_comparison_service.py` (881 lines) |
| **Purpose** | Compares git modification dates between automation and product repos |
| **Used by** | Stage 1, Step 6 (timeline evidence) |

**Key exports:** `TimelineComparisonService`, `TimelineComparisonResult`, `ElementTimeline`, `SelectorTimeline`, `TimeoutPatternResult`

**Key methods:**

| Method | Description |
|--------|-------------|
| `compare_timelines(selector)` | Compare automation vs product modification dates |
| `element_exists_in_console(element_id)` | Check if element exists in product repo |
| `get_element_last_modified(element_id)` | Get last modification date for element |
| `get_selector_last_modified(selector)` | Get last modification date for selector |
| `analyze_timeout_pattern(failed_tests, env_healthy)` | Detect mass timeout patterns |
| `clone_console_to(branch, target_path, acm_version)` | Clone console repo to target |
| `clone_kubevirt_to(branch, target_path)` | Clone kubevirt-plugin to target |

**Key outputs:** `stale_test_signal`, `product_commit_type`, `element_removed`, `element_never_existed`

---

### 7. ACMConsoleKnowledge

| Property | Value |
|----------|-------|
| **File** | `src/services/acm_console_knowledge.py` (701 lines) |
| **Purpose** | Structured knowledge about ACM console directory layout for test-to-feature mapping |
| **Used by** | Stage 1, Step 6 (directory mapping); Stage 2 (investigation paths) |

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
| `build_element_inventory(repository, component_paths)` | Build element inventory |

---

### 8. ACMUIMCPClient

| Property | Value |
|----------|-------|
| **File** | `src/services/acm_ui_mcp_client.py` (293 lines) |
| **Purpose** | Python MCP client for Stage 1 data gathering; Stage 2 uses Claude Code's native MCP |
| **Used by** | Stage 1 (element inventory, CNV detection) |

**Key exports:** `ACMUIMCPClient`, `ElementInfo`, `SearchResult`, `CNVVersionInfo`, `FleetVirtSelectors`

**Key methods:**

| Method | Description |
|--------|-------------|
| `detect_cnv_version()` | Detect CNV version from connected cluster |
| `find_test_ids(file_path, repository)` | Find data-testid/aria-label in a file |
| `search_code(query, repository)` | Search code across repos |
| `find_element_definition(selector, search_all_repos)` | Find element definitions |
| `get_element_inventory(component_paths, repository)` | Build element inventory |

---

### 9. ComponentExtractor

| Property | Value |
|----------|-------|
| **File** | `src/services/component_extractor.py` (381 lines) |
| **Purpose** | Extracts ACM component names from error messages for Knowledge Graph queries |
| **Used by** | Stage 1, Step 6 (detected_components) |

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
| **File** | `src/services/knowledge_graph_client.py` (513 lines) |
| **Purpose** | Optional Neo4j client for RHACM component dependency analysis |
| **Used by** | Stage 2, Phases B5/C2/E0 (via MCP or direct) |

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
| `build_query_for_phase2(components)` | Generate Cypher queries for Stage 2 |

---

### 11. SchemaValidationService

| Property | Value |
|----------|-------|
| **File** | `src/services/schema_validation_service.py` (461 lines) |
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
| **File** | `src/services/shared_utils.py` (645 lines) |
| **Purpose** | Common configuration, subprocess wrappers, credential handling, file detection |
| **Used by** | All services |

**Key exports:**

| Category | Exports |
|----------|---------|
| **Config** | `TimeoutConfig`, `RepositoryConfig`, `ThresholdConfig`, `TIMEOUTS`, `REPOS`, `THRESHOLDS` |
| **Subprocess** | `run_subprocess`, `build_curl_command`, `execute_curl` |
| **JSON** | `parse_json_response`, `safe_json_loads` |
| **Credentials** | `get_jenkins_credentials`, `encode_basic_auth`, `get_auth_header`, `mask_sensitive_value`, `mask_sensitive_dict` |
| **File detection** | `is_test_file`, `is_framework_file`, `is_support_file`, `detect_test_framework` |
| **Base class** | `ServiceBase` |

---

### 13. ReportFormatter

| Property | Value |
|----------|-------|
| **File** | `src/scripts/report.py` (752 lines) |
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

## Service-to-Stage Mapping

| Service | Stage 1 | Stage 2 | Stage 3 |
|---------|---------|---------|---------|
| JenkinsAPIClient | Steps 1-3 | | |
| JenkinsIntelligenceService | Steps 1-3 | | |
| EnvironmentValidationService | Step 4 | | |
| RepositoryAnalysisService | Steps 5-7 | | |
| StackTraceParser | Step 3 | | |
| TimelineComparisonService | Step 6 | | |
| ACMConsoleKnowledge | Step 6 | Phase B | |
| ACMUIMCPClient | Steps 5, 7 | | |
| ComponentExtractor | Step 6 | | |
| KnowledgeGraphClient | | Phases B5, C2, E0 | |
| SchemaValidationService | | | Input validation |
| shared_utils | All steps | | |
| ReportFormatter | | | All output |

---

## Statistics

| Metric | Value |
|--------|-------|
| Total service lines | ~6,900 |
| Service files | 12 |
| Data classes | 24+ |
| Public methods | ~150 |
| Configuration | Centralized in shared_utils |
