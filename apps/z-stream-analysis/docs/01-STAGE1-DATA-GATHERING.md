# Stage 1: Data Gathering (gather.py)

Collects all raw data needed for AI analysis from Jenkins, the target cluster, and source repositories.

---

## Overview

Stage 1 data collection combines a deterministic Python script (`gather.py`)
with an AI-powered data-collector agent. The user initiates the pipeline from
a Claude Code session by providing a Jenkins URL. The orchestrating agent runs
gather.py, then spawns the data-collector agent to enrich the output.

**How it runs:**

1. **gather.py** (deterministic, ~80s) — Runs Steps 1-9: fetches Jenkins data,
   logs into the cluster, clones repos, extracts test context, builds feature
   knowledge. Produces `core-data.json` with all 13 top-level keys. Fields
   `page_objects`, `console_search`, `recent_selector_changes`, and
   `temporal_summary` are initialized as empty/null.

2. **data-collector agent** (AI, ~3-5 min) — Enriches `core-data.json` with
   fields that require intelligent code analysis:
   - Task 1: Resolves `page_objects` by tracing imports in `repos/automation/`
   - Task 2: Verifies `console_search` via MCP tools (ACM-UI)
   - Task 3: Analyzes `recent_selector_changes` and `temporal_summary` using
     git history with intent assessment

**Input:** Jenkins build URL (e.g., `https://jenkins.example.com/job/acm-e2e/123/`)

**Output:** A run directory containing `core-data.json`, `cluster.kubeconfig`,
`repos/`, and supporting files. All data needed for Stage 1.5 and Stage 2.

---

## Step 1: Fetch Jenkins Build Info

**Service:** `JenkinsIntelligenceService.analyze_jenkins_url()` (via `_fetch_build_info()`)

**API:** `GET <jenkins_url>/api/json` (authenticated)

**Extracted fields:**

| Field | Example |
|-------|---------|
| `job_name` | `acm-qe-e2e-nightly` |
| `build_number` | `123` |
| `result` | `UNSTABLE`, `FAILURE`, `SUCCESS` |
| `timestamp` | `1706880000000` |
| `duration` | `3600000` (ms) |
| `parameters` | List of build parameters |

**Key parameters extracted:**

| Parameter | Purpose |
|-----------|---------|
| `CYPRESS_HUB_API_URL` | Target cluster API URL |
| `CYPRESS_OPTIONS_HUB_USER` | Cluster username |
| `CYPRESS_OPTIONS_HUB_PASSWORD` | Cluster password (masked in output) |
| `GIT_BRANCH` | Test branch |
| `CLUSTER_NAME` | Cluster identifier |

**Output file:** `jenkins-build-info.json`

---

## Step 2: Fetch and Parse Console Log

**Service:** `JenkinsAPIClient.get_console_output()` (primary), `JenkinsIntelligenceService._fetch_console_log()` (fallback)

**API:** `GET <jenkins_url>/consoleText` (authenticated)

The raw console output (can be 10MB+) is saved to `console-log.txt` and parsed for error patterns using regex.

### Regex Patterns (in JenkinsIntelligenceService, used during Step 3 test report analysis)

**Timeout patterns:**
```python
timeout_patterns = [
    r'timeout.*waiting.*for.*element',   # "Timeout waiting for element"
    r'TimeoutError',                      # "TimeoutError: ..."
    r'timed out after \d+',              # "timed out after 30000"
    r'cypress.*timed.*out'               # "Cypress timed out..."
]
```

**Element not found patterns:**
```python
element_patterns = [
    r'element.*not.*found',              # "Element not found"
    r'selector.*not.*found',             # "Selector not found"
    r'NoSuchElementException',           # Selenium-style error
    r'ElementNotInteractableException'   # Element exists but not clickable
]
```

**Network error patterns:**
```python
network_patterns = [
    r'connection.*refused',              # "Connection refused"
    r'network.*error',                   # "Network error"
    r'failed.*to.*connect',             # "Failed to connect"
    r'DNS.*resolution.*failed'           # "DNS resolution failed"
]
```

### Failure Type Classification (Step 3)

`_classify_failure_type()` in `JenkinsIntelligenceService` returns a factual error type (not a bug classification). This runs during Step 3 test report processing, not Step 2:

```python
def _classify_failure_type(self, error_text: str) -> str:
    error_lower = error_text.lower()
    if any(p in error_lower for p in ['timeout', 'timed out', 'exceeded']):
        return 'timeout'
    elif any(p in error_lower for p in ['element not found', 'element: not found',
                                         'expected to find element', 'nosuchelementexception',
                                         'elementnotinteractableexception', 'selector not found']):
        return 'element_not_found'
    elif any(p in error_lower for p in ['connection', 'network', 'refused', 'dns']):
        return 'network'
    elif any(p in error_lower for p in ['assert', 'expect', 'should', 'equal', 'match']):
        # v3.3: further split into assertion_data or assertion_selector
        if has_data_assertion(error_text):
            return 'assertion_data'
        elif has_selector_assertion(error_text):
            return 'assertion_selector'
        return 'assertion'
    elif any(p in error_lower for p in ['500', '502', '503', 'internal server', 'bad gateway']):
        return 'server_error'
    elif any(p in error_lower for p in ['401', '403', 'unauthorized', 'forbidden', 'permission']):
        return 'auth_error'
    elif any(p in error_lower for p in ['404', 'not found', 'no such']):
        return 'not_found'
    else:
        return 'unknown'
```

### Output Structure

```python
{
    'file_path': 'console-log.txt',
    'total_lines': 12500,
    'error_lines_count': 42,
    'key_errors': ['first 20 lines containing error or fail...'],
    'error_patterns': {
        'has_500_errors': False,
        'has_network_errors': False,
        'has_timeout_mentions': True
    }
}
```

**Output files:** `console-log.txt` (raw), error patterns embedded in `core-data.json` under `console_log`

---

## Step 3: Fetch Test Report

**Service:** `JenkinsIntelligenceService._fetch_and_analyze_test_report()`

**API:** `GET <jenkins_url>/testReport/api/json` (JUnit format)

**Extracted summary:**

| Field | Example |
|-------|---------|
| `total` | `150` |
| `passed` | `142` |
| `failed` | `8` |
| `skipped` | `0` |
| `pass_rate` | `94.67%` |

**Per failed test:**

| Field | Example |
|-------|---------|
| `test_name` | `should create cluster successfully` |
| `class_name` | `Cluster.Create` |
| `duration` | `45.23` (seconds) |
| `error_message` | `Timed out: Expected to find '#create-btn'` |
| `stack_trace` | `at Context.<anonymous> (create.cy.ts:45:12)...` |
| `status` | `FAILED` |

### Stack Trace Parsing

`StackTraceParser.parse_stack_trace()` extracts structured information from JS/TS stack traces:

```
INPUT:
  AssertionError: Timed out retrying after 30000ms: Expected to find
  element: '#create-btn', but never found it.
      at Context.<anonymous> (cypress/e2e/cluster/create.cy.ts:45:12)
      at runnable.run (cypress/support/commands.js:123:5)

OUTPUT:
  {
    "error_type": "element_not_found",
    "root_cause_file": "cypress/e2e/cluster/create.cy.ts",
    "root_cause_line": 45,
    "failing_selector": "#create-btn",
    "frames": [
      { "file": "create.cy.ts", "line": 45, "function": "anonymous" },
      { "file": "commands.js", "line": 123, "function": "run" }
    ]
  }
```

**Output file:** `test-report.json`

---

## Step 4: Cluster Login + Landscape

**Services:** `EnvironmentValidationService` (login + kubeconfig persist), `ClusterInvestigationService` (landscape)

Step 4 establishes cluster access and collects landscape data. It does two things: (4a) login (two-tier credential lookup: Jenkins parameters, then console log fallback), kubeconfig persistence, and MCH namespace discovery, (4b) cluster landscape snapshot. The comprehensive health audit is handled by Stage 1.5 (cluster-diagnostic agent), which produces `cluster-diagnosis.json`.

**MCH namespace discovery (Step 4a):** After login, gather.py runs `oc get mch -A` to discover the actual MCH namespace. This can be `open-cluster-management`, `ocm`, or a custom namespace depending on the ACM installation. The discovered namespace is used for all subsequent `oc` commands and propagated to all services (`ClusterInvestigationService`, `FeatureAreaService`). Derived namespaces (`-hub`, `-observability`, `-agent`) are computed from the discovered base namespace.

**Output:** `cluster.kubeconfig` + `cluster_landscape` and `cluster_access.mch_namespace` keys in core-data.json

**Commands:** `oc` / `kubectl` (READ-ONLY operations only)

```
Extract cluster URL from Jenkins parameters
(CYPRESS_HUB_API_URL)
        │
        ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ oc login     │  │ oc get nodes │  │ oc get pods  │
│ (authenticate│  │ (check nodes)│  │ -n open-     │
│  to cluster) │  │              │  │ cluster-...  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
  Cluster           Node status        ACM pods
  accessible?       (Ready/NotReady)   (Running?)
```

**Note:** Environment health scoring (`environment_health_score`) is handled entirely by Stage 1.5 (cluster-diagnostic agent) in `cluster-diagnosis.json`. Step 4 does not compute any health score — it only establishes access and collects landscape data. Stage 1.5 also validates console image integrity against `healthy-baseline.yaml` expected prefixes and reports findings in the `image_integrity` field.

### READ-ONLY Safety

| Allowed | NOT Allowed |
|---------|-------------|
| `oc get`, `oc describe` | `oc delete`, `oc apply` |
| `oc whoami`, `oc version` | `oc patch`, `oc edit` |
| `oc api-resources` | `oc scale`, `oc rollout` |
| `kubectl get`, `kubectl describe` | Any write operation |

### Cluster Access Persistence (v3.1, updated v4.0)

Part of `_login_to_cluster()` (Step 4a). Extracts cluster credentials with two-tier lookup: Jenkins build parameters first, then console log fallback (for pipelines that use Jenkins Password Parameter types concealed from the REST API). After login, creates a persistent `cluster.kubeconfig` in the run directory. The `credential_source` field records which method succeeded (`jenkins_parameters` or `console_log_fallback`). Passwords are masked in `core-data.json` — the kubeconfig provides authentication without needing the raw password.

```json
{
  "cluster_access": {
    "api_url": "https://api.cluster.example.com:6443",
    "username": "kubeadmin",
    "has_credentials": true,
    "password": "****masked****",
    "kubeconfig_path": "runs/<dir>/cluster.kubeconfig",
    "credential_source": "jenkins_parameters",
    "mch_namespace": "open-cluster-management"
  }
}
```

The `kubeconfig_path` is also set on `env_service.kubeconfig` so subsequent gather steps (cluster landscape, oracle) use the same authenticated kubeconfig.

**Output files:** `cluster.kubeconfig`, `cluster_access` and `cluster_landscape` keys in `core-data.json`

---

## Step 4 (continued): Cluster Landscape (v3.0)

**Service:** `ClusterInvestigationService.get_cluster_landscape()`

**Method:** `DataGatherer._gather_cluster_landscape()`

Collects a cluster-wide health snapshot beyond what Step 4's environment score provides. This data feeds Phase A1b (cluster landscape check) and Phase B5b (targeted pod investigation) during Stage 2 analysis.

Shares the kubeconfig and CLI from `EnvironmentValidationService` so both services query the same cluster. Skipped when `--skip-env` is used (sets `cluster_landscape: {skipped: true}`).

**Commands:** Same READ-ONLY `oc`/`kubectl` commands as Step 4.

### Data Collected

| Field | Command | Example |
|-------|---------|---------|
| `managed_cluster_count` | `oc get managedclusters -o json` | `3` |
| `managed_cluster_statuses` | (parsed from above) | `{"Ready": 3}` |
| `operator_statuses` | `oc get clusterserviceversions -A -o json` | `{"all_available": true}` |
| `degraded_operators` | (filtered from above) | `[]` or `["search-operator"]` |
| `resource_pressure` | `oc get nodes -o json` (conditions) | `{"cpu": false, "memory": false, "disk": false, "pid": false}` |
| `policy_count` | `oc get policies -A --no-headers` | `9` |
| `multiclusterhub_status` | `oc get multiclusterhub -A -o json` | `"Running"` |
| `mch_enabled_components` | (from MCH spec.overrides.components) | `{"search": true, "grc": true}` |
| `mch_version` | (from MCH status.currentVersion) | `"2.16.1"` |

### How It's Used in Stage 2

- **Phase A1b:** Degraded operator overlapping a feature area component signals backend may cause UI failures
- **Phase B5b:** When 500 errors or ambiguous classification detected, targeted pod investigation queries pods in the namespaces identified here
- **Phase B7:** Backend cross-check uses landscape data to determine if backend issues caused UI failures

**Output:** Stored in `core-data.json` under `cluster_landscape` key.

---

**Note:** Backend API probing (Step 4c) was removed. Backend health investigation
is now handled comprehensively by Stage 1.5 (cluster-diagnostic agent) which checks
pod health, operator status, console plugins, addon verification, and dependency chains.
Stage 2 (analysis agent) performs targeted investigation during per-test analysis with
full context about what feature area and component to check.

---

## Step 5: Environment Oracle (v3.5)

**Service:** `EnvironmentOracleService`

**Method:** `DataGatherer._run_environment_oracle()`

Feature-aware dependency health checking. Runs three phases of the Environment Oracle to build a targeted dependency model for the detected feature areas, then validates those dependencies against the live cluster.

### Skip Condition

Skipped entirely (with `cluster_oracle: {}`) when `--skip-env` is used or cluster access is unavailable. If the oracle fails at any phase, gather continues with empty oracle data — it does not block the pipeline.

### Phase 1: Feature Identification

Identifies the feature area from the Jenkins pipeline name and test names. Extracts Polarion test case IDs (e.g., `RHACM4K-12345`) from test names for traceability.

**Inputs:**
- `jenkins.job_name` — pipeline name for feature area inference
- `test_report.failed_tests[].test_name` — test names for Polarion ID extraction and feature confirmation

**Outputs:**
- Detected feature area(s)
- Extracted Polarion IDs per test

### Phase 5: Dependency Model Synthesis

Synthesizes a dependency model from the feature playbooks (`src/data/feature_playbooks/base.yaml`). For each detected feature area, extracts the operators, addons, and CRDs that the feature depends on.

**Inputs:**
- Feature area(s) from Phase 1
- Feature playbook definitions (prerequisites, dependencies, components)

**Outputs:**
- List of operators to check (e.g., `multicluster-engine`, `advanced-cluster-management`)
- List of addons to check (e.g., `search-collector`, `governance-policy-framework`)
- List of CRDs to validate (e.g., `managedclusters.cluster.open-cluster-management.io`)

### Phase 6: Targeted Cluster Validation

Runs targeted read-only `oc` commands against the live cluster to validate the dependencies identified in Phase 5.

**Commands (all read-only):**

| Check | Command | Purpose |
|-------|---------|---------|
| Operator CSV | `oc get csv -n <namespace> -o json` | Verify operator is installed and phase is `Succeeded` |
| Addon check | `oc get managedclusteraddon -A -o json` | Verify addon is deployed and available |
| CRD check | `oc get crd <name>` | Verify CRD exists on cluster |

Each check records pass/fail status and any error details. Failed checks indicate a missing or degraded dependency that may explain test failures.

### Output Structure

Stored in `core-data.json` under `cluster_oracle`:

```json
{
  "cluster_oracle": {
    "version": "1.0.0",
    "oracle_phase": "C",
    "snapshot_time": "2026-03-30T17:49:01Z",
    "feature_areas": ["Application"],
    "failed_test_count": 25,
    "polarion_ids": ["RHACM4K-6784", "RHACM4K-16936"],
    "polarion_discovery": {},
    "knowledge_context": {
      "feature_components": {"Application": ["application-manager", "subscription-controller"]},
      "cross_subsystem_dependencies": {},
      "dependency_details": {}
    },
    "dependency_targets": [
      {
        "id": "application-manager-addon",
        "type": "addon",
        "name": "application-manager-addon",
        "source": "playbook"
      }
    ],
    "dependency_health": {},
    "overall_feature_health": {
      "score": null,
      "signal": "unknown",
      "blocking_issues": [],
      "summary": "No dependency health data available"
    },
    "cluster_access_status": "authenticated",
    "errors": []
  }
}
```

### Key Fields

| Field | Type | Purpose |
|-------|------|---------|
| `feature_areas` | list | Feature areas identified from pipeline name and test names |
| `polarion_ids` | list | Polarion test case IDs extracted from test names |
| `dependency_targets` | list | Dependencies discovered from playbooks and Polarion |
| `dependency_health` | dict | Health check results per dependency (when cluster is accessible) |
| `overall_feature_health` | dict | Aggregate health score with signal (healthy/degraded/unhealthy/unknown) |
| `cluster_access_status` | string | `authenticated`, `no_credentials`, `login_failed`, `skipped`, `error` |
| `knowledge_context` | dict | KG topology data (feature components, cross-subsystem deps) |

### How It's Used in Stage 2

- **Phase A0:** Oracle `feature_areas` and `overall_feature_health` provide early signal about missing dependencies before per-test analysis begins
- **Phase PR-7:** If `dependency_health` shows a broken dependency, routes tests in that feature area to INFRASTRUCTURE
- **Phase PR-4:** Failed oracle checks can confirm playbook prerequisite failures, strengthening INFRASTRUCTURE classification
- **Phase B7:** Oracle dependency status used for comprehensive health assessment

**Output:** Stored in `core-data.json` under `cluster_oracle` key.

---

## Step 6: Repository Cloning

**Service:** `RepositoryAnalysisService.clone_to()`

### Automation Repo Detection

Job name determines the automation repository via substring matching (`_infer_repo_from_job()` checks `if key in job_name.lower()`):

| Job Name Contains | Repository |
|---|---|
| `clc-e2e` | `stolostron/clc-ui-e2e` |
| `clc-ui-e2e` | `stolostron/clc-ui-e2e` |
| `console-e2e` | `stolostron/console-e2e` |
| `acm-e2e` | `stolostron/acm-e2e` |
| `grc-ui-e2e` | `stolostron/grc-ui-e2e` |
| `search-e2e` | `stolostron/search-e2e-test` |
| (no match) | Attempts to extract from console log; returns None if both fail |

No glob/regex patterns are used. Can be overridden with `Z_STREAM_AUTOMATION_REPOS` environment variable (JSON).

### Console and Kubevirt Repos

The product repo (`stolostron/console`) is always cloned.

If VM/kubevirt tests are detected in the job name, `kubevirt-ui/kubevirt-plugin` is also cloned on the matching branch:

```
1. Query cluster: oc get csv -n openshift-cnv
2. Extract version: kubevirt-hyperconverged.v4.20.3
3. Map to branch: release-4.20
4. Clone kubevirt-plugin on that branch
```

### Directory Structure

```
repos/
├── automation/              ← Test repository
│   ├── cypress/
│   │   ├── e2e/             ← Test specs
│   │   ├── support/         ← Cypress commands
│   │   └── views/           ← Page objects & selectors
│   └── ...
├── console/                 ← Product repository
│   ├── frontend/src/
│   │   ├── routes/          ← Feature components
│   │   ├── components/      ← Shared components
│   │   └── ui-components/   ← UI library
│   └── ...
└── kubevirt-plugin/         ← Only for VM tests
    └── src/
```

---

## Step 7: Context Extraction

**Method:** `DataGatherer._extract_complete_test_context()`

For each failed test, extracts test code and failure metadata. Fields that require AI code analysis (`page_objects`, `console_search`, `recent_selector_changes`, `temporal_summary`) are initialized as empty/null and populated later by the data-collector agent.

```
For each failed test:
     │
     ├── Sub-step 7a: Read test file content
     ├── Sub-step 7b: Initialize page_objects placeholder (populated by agent)
     ├── Sub-step 7c: Initialize console_search placeholder (populated by agent)
     ├── Sub-step 7d: Parse assertion analysis (v3.3)
     └── Sub-step 7e: Categorize failure mode (v3.3)
```

Note: `detected_components` extraction happens in Step 3 (test report parsing), not Step 7. Timeline evidence (`recent_selector_changes`, `temporal_summary`) is populated by the data-collector agent after gather.py completes.

### Sub-step 7a: Read Test File

**Method:** `_read_test_file(automation_path, test_file_path, max_lines=200)`

1. Normalize path (remove leading `/`)
2. Try direct path: `repos/automation/<test_file_path>`
3. If not found, try alternatives: `cypress/<path>`, `cypress/e2e/<path>`
4. Read file content, truncate at 200 lines if needed

```python
def _read_test_file(self, automation_path, test_file_path, max_lines=200):
    if test_file_path.startswith('/'):
        test_file_path = test_file_path[1:]

    full_path = automation_path / test_file_path

    if not full_path.exists():
        for path in [
            automation_path / test_file_path,
            automation_path / 'cypress' / test_file_path,
            automation_path / 'cypress' / 'e2e' / test_file_path,
        ]:
            if path.exists():
                full_path = path
                break

    content = full_path.read_text()
    lines = content.split('\n')

    return {
        'path': str(full_path.relative_to(automation_path)),
        'content': '\n'.join(lines[:max_lines]) if len(lines) > max_lines else content,
        'line_count': len(lines),
        'truncated': len(lines) > max_lines
    }
```

### Sub-step 7b: Page Objects (data-collector agent)

Page object resolution is handled by the **data-collector agent** after gather.py completes. The agent uses AI code analysis to trace imports and resolve selector definitions across any test framework (Cypress, Playwright, etc.). gather.py initializes the field as `[]`.

**Output:**
```json
[
  {
    "path": "cypress/views/cluster.js",
    "content": "export const clusterSelectors = {\n  createButton: '#create-btn'\n};",
    "contains_failing_selector": true
  }
]
```

### Sub-step 7c: Console Search (data-collector agent)

Selector verification in product source is handled by the **data-collector agent** after gather.py completes. The agent uses MCP tools (ACM-UI `search_code`, `search_component`) to verify selector existence with full context — understanding PatternFly components, runtime-generated selectors, and correct route/page context. gather.py initializes the field as `null`.

**Output:**
```json
{
  "selector": "#create-btn",
  "found": false,
  "verification": {
    "verified_by": "data-collector",
    "method": "mcp_literal_search",
    "result": "not_found",
    "detail": "Selector not found in ACM console source"
  }
}
```

### Sub-step 7d: Parse Assertion Analysis (v3.3)

**Method:** `StackTraceParser.extract_assertion_values(error_message)`

Parses Cypress/Chai assertion errors to extract expected vs actual values. Only populated when the error contains a data assertion (not selector assertions like `expected to find element`).

**Output:**
```json
{
  "has_data_assertion": true,
  "assertion_type": "count_mismatch",
  "expected": "5",
  "actual": "3",
  "raw_assertion": "expected 3 to equal 5"
}
```

| `assertion_type` | Meaning |
|---|---|
| `count_mismatch` | Expected N items, got M |
| `value_mismatch` | Expected value X, got Y |
| `content_missing` | Expected text/content not present |
| `state_mismatch` | Expected state (enabled, visible, checked) differs |
| `property_missing` | Expected property/attribute absent |

### Sub-step 7e: Categorize Failure Mode (v3.3)

**Method:** `DataGatherer._classify_failure_mode(failure_type, error_message, console_search, assertion_analysis)`

Assigns a high-level failure mode category to each test based on its `failure_type`, error content, and assertion analysis. Used by Phase PR-5 and Phase D4b in Stage 2.

| `failure_mode_category` | Trigger |
|---|---|
| `render_failure` | Blank page, no-js, page failed to load |
| `element_missing` | `element_not_found` failure type |
| `data_incorrect` | `assertion_data` with `has_data_assertion=true` |
| `timeout_general` | Timeout without element reference |
| `assertion_logic` | `assertion_selector` or assertion without data component |
| `server_error` | 500/502/503 in error message |
| `unknown` | No pattern matched |

### Recent Selector Changes (data-collector agent)

Selector timeline analysis is handled by the **data-collector agent** after gather.py completes. The agent uses git history analysis (`git log -S`) on both the product and automation repos to determine whether a selector was recently changed, whether the change was intentional (planned refactor) or accidental (side effect), and what the replacement selector is.

gather.py initializes the field as `null`. The agent produces enriched output:

| Output Field | Meaning |
|---|---|
| `change_detected` | Whether any git commits touched this selector |
| `direction` | `removed_from_product`, `automation_ahead_of_product`, or `null` |
| `commit.sha`, `commit.message`, `commit.date` | The commit that changed the selector |
| `replacement_selector` | What was added in the same area (if any) |
| `intent_assessment` | `intentional_rename`, `likely_unintentional`, `automation_premature`, `no_recent_change` |
| `classification_hint` | `AUTOMATION_BUG`, `PRODUCT_BUG`, or `null` |
| `reasoning` | Human-readable explanation for Stage 2 |

### Component Extraction (Step 3, not Step 7)

**Service:** `ComponentExtractor.extract_all_from_test_failure(error_message, stack_trace)`

Component extraction runs during Step 3 (test report parsing) via `_extract_components_from_failure()`, not during Step 7. Each failed test's `detected_components` list is populated at that point. Each component includes:
- `name`: Component identifier (e.g., `search-api`)
- `subsystem`: Parent subsystem (e.g., `Search`)
- `source`: Where it was found (error_message, stack_trace)
- `context`: Snippet of surrounding text (truncated to 100 chars)

### Temporal Summary (data-collector agent)

The `temporal_summary` field is populated by the **data-collector agent** (Task 3) at selector level using git log analysis. It provides selector-level timeline data (when the product and automation last modified the selector, not just the file), `stale_test_signal`, and `product_commit_type`. gather.py initializes the field as `null`.

---

## Step 8: Feature Area Grounding (v3.0)

**Service:** `FeatureAreaService.group_tests_by_feature()`

**Method:** `DataGatherer._ground_feature_areas()`

Groups all failed tests by feature area (CLC, Search, GRC, etc.) and attaches subsystem context. This runs **always** — it does not require cloned repos (unlike Step 7) because it uses test names, file paths, and detected components rather than file content.

### Identification Priority

`FeatureAreaService.identify_feature_area()` maps each test using these signals (in order of reliability):

1. **Test file path** — e.g., `cypress/e2e/cluster/` → CLC
2. **Test name patterns** — e.g., `RHACM4K-*` prefix, keyword matching
3. **Detected components** — from error messages (e.g., `search-api` → Search)
4. **Error message content** — fallback keyword matching

Tests that don't match any pattern are grouped under `Unknown`.

### Output Structure

Stored in `core-data.json` under `feature_grounding`:

```json
{
  "feature_grounding": {
    "groups": {
      "CLC": {
        "subsystem": "Cluster Lifecycle",
        "key_components": ["cluster-curator", "managedcluster-import-controller"],
        "key_namespaces": ["open-cluster-management"],
        "investigation_focus": "Cluster creation, import, upgrade workflows",
        "tests": ["RHACM4K-51364", "RHACM4K-3046"],
        "test_count": 2
      },
      "Search": {
        "subsystem": "Search",
        "key_components": ["search-api", "search-collector"],
        "key_namespaces": ["open-cluster-management"],
        "investigation_focus": "Search indexing, query, and result display",
        "tests": ["RHACM4K-52779"],
        "test_count": 1
      }
    },
    "feature_areas_found": ["CLC", "Search"],
    "total_groups": 2
  }
}
```

### How It's Used in Stage 2

- **Phase A0:** Read feature grounding to know WHAT each test validates before analyzing WHY it failed
- **Phase A1b:** Cross-reference feature areas with degraded operators from `cluster_landscape`
- **Phase A3b:** Batch-query Knowledge Graph for all unique subsystems identified here
- **Phase B5b:** Use `key_components` and `key_namespaces` to target pod investigation

---

## Step 9: Feature Knowledge Playbooks (v3.1)

**Service:** `FeatureKnowledgeService.load_playbooks()`, `FeatureKnowledgeService.get_feature_readiness()`

**Method:** `DataGatherer._check_feature_knowledge()`

Loads YAML investigation playbooks from `src/data/feature_playbooks/`, checks MCH prerequisites against cluster state, pre-matches test error messages against known failure paths, and queries the Knowledge Graph for per-area dependency context. Runs after Step 8 (requires detected feature areas).

### Data Sources

- `src/data/feature_playbooks/base.yaml` — stable profiles (Search, GRC, CLC, Application, Console, Infrastructure, Automation, RBAC, Observability)
- `src/data/feature_playbooks/acm-{version}.yaml` — version-specific profiles (Virtualization, CrossClusterMigration)
- `cluster_landscape.mch_enabled_components` — for MCH prerequisite checks
- Knowledge Graph (via direct HTTP API to Neo4j) — for dependency context

### ACM Version Detection

The ACM version is detected in this priority:
1. Jenkins parameter `DOWNSTREAM_RELEASE`
2. MCH `status.currentVersion` (major.minor from `cluster_landscape.mch_version`)

### Output Structure

Stored in `core-data.json` under `feature_knowledge`:

```json
{
  "feature_knowledge": {
    "acm_version": "2.16",
    "profiles_loaded": ["CLC", "Search", "Infrastructure", "Automation"],
    "feature_readiness": {
      "CLC": {
        "feature_area": "CLC",
        "architecture_summary": "Three flows: Create, Import, Upgrade...",
        "key_insight": "CLC spans multiple operators...",
        "all_prerequisites_met": true,
        "prerequisite_checks": [
          {"id": "clc-mch-component", "type": "mch_component", "met": true, "detail": "cluster-lifecycle=enabled in MCH"}
        ],
        "unmet_prerequisites": [],
        "failure_paths": [...],
        "pre_matched_paths": []
      }
    },
    "investigation_playbooks": {
      "CLC": {
        "display_name": "Cluster Lifecycle",
        "architecture": {...},
        "prerequisites": [...],
        "dependencies": ["Infrastructure"],
        "failure_paths": [...]
      }
    },
    "kg_dependency_context": {
      "CLC": {
        "internal_data_flow": ["cluster-curator --DEPENDS_ON--> cluster-manager"],
        "cross_subsystem_dependencies": [...],
        "components_in_subsystem": [...]
      }
    },
    "kg_status": {
      "available": true
    },
    "gap_detection": {
      "stale_components": [],
      "hardcoded_namespaces": [],
      "missing_overlay": "acm-2.17.yaml",
      "overall_match_rate": 0.05,
      "gap_areas": ["RBAC", "Console", "CLC"],
      "match_rates": {
        "CLC": {"total_errors": 16, "matched_count": 0, "unmatched_count": 16, "match_rate": 0.0}
      }
    }
  }
}
```

### How It's Used in Stage 2

- **Phase A0b:** Review feature knowledge — architecture summaries, key insights, prerequisite status
- **Phase B8:** Tiered playbook investigation — check prerequisites with live `oc` commands, execute failure path investigation steps
- **Phase B8b-d:** If playbook confirms a failure path, query KG for upstream dependencies; escalate to Tier 3-4 if needed
- **Phase PR-4:** Feature knowledge override — if prerequisite unmet AND confirmed with live commands, use playbook classification at 0.95 confidence

**Output:** Stored in `core-data.json` under `feature_knowledge` key.

---

## Output Files

All collected data is written to the run directory.

**Files created:**

| File | Contents | Created By |
|------|----------|------------|
| `core-data.json` | All gathered data (primary file for AI) | gather.py |
| `cluster.kubeconfig` | Persisted cluster auth for Stage 2 | gather.py |
| `run-metadata.json` | Run metadata (timing, version) | gather.py |
| `manifest.json` | File index with workflow metadata | gather.py |
| `console-log.txt` | Full Jenkins console output | gather.py |
| `jenkins-build-info.json` | Build metadata (credentials masked) | gather.py |
| `test-report.json` | Per-test failure details | gather.py |
| `pipeline.log.jsonl` | Structured service logs (DEBUG-level) | gather.py (via logging_config) |
| `repos/` | Cloned repositories | gather.py |

### core-data.json Complete Schema

All 13 top-level keys are always present. Source column indicates who populates each field — **Script** (gather.py, deterministic), **Agent** (data-collector, AI-powered), or **Both** (initialized by script, enriched by agent).

```
core-data.json
├── metadata                    [Script, Step 1]
├── jenkins                     [Script, Step 1]
├── test_report                 [Script, Step 3 + Agent]
│   ├── summary
│   └── failed_tests[]          ← per-test entries (schema below)
├── console_log                 [Script, Step 2]
├── environment                 [Script, Step 4a]
├── cluster_health              [Script, stub — actual data in cluster-diagnosis.json]
├── cluster_access              [Script, Step 4a]
├── cluster_landscape           [Script, Step 4b]
├── cluster_oracle              [Script, Step 5]
├── repositories                [Script, Step 6]
├── feature_grounding           [Script, Step 8]
├── feature_knowledge           [Script, Step 9]
└── errors                      [Script, throughout]
```

#### 1. `metadata` — Run metadata (Script, Step 1)

```json
{
  "jenkins_url": "",
  "gathered_at": "",
  "gatherer_version": "4.0.0",
  "jenkins_api_available": true,
  "acm_ui_mcp_available": true,
  "knowledge_graph_available": false,
  "run_directory": "runs/<dir>",
  "gathering_time_seconds": 0.0,
  "status": "complete",
  "data_version": "4.0.0"
}
```

#### 2. `jenkins` — Build metadata (Script, Step 1)

```json
{
  "build_url": "",
  "job_name": "",
  "build_number": 0,
  "build_result": "UNSTABLE",
  "timestamp": 0,
  "parameters": { "CYPRESS_HUB_API_URL": "", "GIT_BRANCH": "", "..." : "..." },
  "branch": "main",
  "commit_sha": null,
  "artifacts": ["junit_cypress-*.xml", "..."],
  "environment_info": { "cluster_name": null, "target_branch": "main" }
}
```

#### 3. `test_report` — Test results + per-test context (Script, Step 3 + Agent)

```json
{
  "summary": {
    "total_tests": 0, "passed_count": 0, "failed_count": 0,
    "skipped_count": 0, "pass_rate": 0.0, "duration": 0.0
  },
  "failed_tests": [
    {
      "test_name": "",
      "class_name": "",
      "status": "FAILED",
      "duration_seconds": 0.0,
      "error_message": "",
      "stack_trace": "",
      "failure_type": "",
      "parsed_stack_trace": {
        "root_cause_file": null, "root_cause_line": null,
        "test_file": null, "test_line": null,
        "failing_selector": null, "error_type": "",
        "frames_count": 0, "user_code_frames": 0
      },
      "detected_components": [],
      "extracted_context": {
        "test_file": null,
        "page_objects": [],
        "console_search": null,
        "recent_selector_changes": null,
        "assertion_analysis": null,
        "failure_mode_category": "",
        "temporal_summary": null
      }
    }
  ]
}
```

**Per-test field sources:**

| Field | Source | Populated by |
|-------|--------|-------------|
| test_name, class_name, status, duration_seconds, error_message, stack_trace, failure_type | JUnit XML | Script (Step 3) |
| parsed_stack_trace | Stack trace parser | Script (Step 3) |
| detected_components | Component extraction | Script (Step 3) |
| test_file | Read from repos/automation/ | Script (Step 7) |
| page_objects | Trace imports, find selector definitions | **Agent** (Task 1) |
| console_search | Verify selector in product source via MCP | **Agent** (Task 2) |
| recent_selector_changes | Git log analysis with intent assessment | **Agent** (Task 3) |
| assertion_analysis | Parse assertion values from error | Script (Step 7) |
| failure_mode_category | Classify error type | Script (Step 7) |
| temporal_summary | Selector-level timeline from git log | **Agent** (Task 3) |

#### 4. `console_log` — Jenkins console output analysis (Script, Step 2)

```json
{
  "file_path": "console-log.txt",
  "total_lines": 0,
  "error_lines_count": 0,
  "key_errors": ["first 20 error lines..."],
  "error_patterns": {
    "has_500_errors": false,
    "has_network_errors": false,
    "has_timeout_mentions": false
  }
}
```

#### 5. `environment` — Cluster connectivity status (Script, Step 4a)

```json
{
  "cluster_connectivity": true,
  "source": "cluster-login"
}
```

#### 6. `cluster_health` — Stub (Script, Step 4)

Health data is in `cluster-diagnosis.json` from Stage 1.5, not here.

```json
{
  "deferred_to_stage_1_5": true,
  "note": "Cluster health data provided by cluster-diagnosis.json from Stage 1.5"
}
```

#### 7. `cluster_access` — Cluster credentials (Script, Step 4a)

```json
{
  "api_url": "",
  "username": "",
  "has_credentials": true,
  "password": "***MASKED***",
  "credential_source": "jenkins_parameters",
  "kubeconfig_path": "runs/<dir>/cluster.kubeconfig",
  "mch_namespace": "ocm"
}
```

The `mch_namespace` is discovered via `oc get mch -A`. All downstream `oc` commands
and service lookups use this namespace instead of hardcoding `open-cluster-management`.

#### 8. `cluster_landscape` — Cluster state snapshot (Script, Step 4b)

```json
{
  "managed_cluster_count": 0,
  "managed_cluster_statuses": { "Ready": 0, "NotReady": 0 },
  "operator_statuses": { "authentication": "Available", "...": "..." },
  "degraded_operators": [],
  "resource_pressure": { "cpu": false, "memory": false, "disk": false, "pid": false },
  "policy_count": 0,
  "multiclusterhub_status": "Running",
  "mch_enabled_components": { "console": true, "search": true, "...": true },
  "mch_version": ""
}
```

#### 9. `cluster_oracle` — Feature context from oracle (Script, Step 5)

The 6-phase Environment Oracle builds a knowledge database about the feature
being tested, its dependencies, and their health state.

```json
{
  "version": "1.0.0",
  "oracle_phase": "C",
  "snapshot_time": "",
  "feature_areas": ["CLC"],
  "failed_test_count": 0,
  "polarion_ids": ["RHACM4K-XXXXX", "..."],
  "polarion_discovery": {
    "polarion_available": true,
    "tests_queried": 0,
    "tests_with_content": 0,
    "test_case_context": { "RHACM4K-XXXXX": { "title": "", "description": "", "setup": "" } }
  },
  "knowledge_context": {
    "kg_available": false,
    "subsystems_investigated": [],
    "docs_context": { "docs_path": "", "available_directories": [] },
    "playbook_architecture": {}
  },
  "dependency_targets": [{ "id": "", "type": "", "name": "", "description": "" }],
  "dependency_health": {},
  "overall_feature_health": {
    "score": null,
    "signal": "unknown",
    "blocking_issues": [],
    "summary": ""
  },
  "cluster_access_status": "skipped",
  "errors": []
}
```

#### 10. `repositories` — Cloned repo metadata (Script, Step 6)

```json
{
  "automation": {
    "path": "repos/automation",
    "url": "",
    "branch": "main",
    "commit": "",
    "cloned": true
  },
  "console": {
    "path": "repos/console",
    "url": "https://github.com/stolostron/console.git",
    "branch": "main",
    "cloned": true,
    "patternfly_version": { "@patternfly/react-core": "^6.4.1" },
    "structure_valid": { "ui_components": true, "routes": true, "..." : true }
  },
  "kubevirt_plugin": {
    "path": "repos/kubevirt-plugin",
    "url": "",
    "branch": "main",
    "cloned": true,
    "structure_valid": { "src": true, "views": true }
  }
}
```

Automation repo URL is detected dynamically from the Jenkins pipeline.
kubevirt-plugin is only cloned when VM/virt tests are detected.

#### 11. `feature_grounding` — Test-to-subsystem mapping (Script, Step 8)

```json
{
  "groups": {
    "CLC": {
      "subsystem": "Cluster Lifecycle",
      "key_components": ["cluster-curator", "hive-controllers"],
      "key_namespaces": ["open-cluster-management", "hive"],
      "investigation_focus": "Cluster creation, import, upgrade...",
      "tests": ["RHACM4K-1588: ...", "RHACM4K-8322: ..."],
      "test_count": 16
    }
  },
  "feature_areas_found": ["CLC", "Virtualization", "RBAC", "..."],
  "total_groups": 8
}
```

#### 12. `feature_knowledge` — Playbooks and KG context (Script, Step 9)

```json
{
  "acm_version": "2.17",
  "profiles_loaded": ["CLC", "Search", "Virtualization", "..."],
  "feature_readiness": {
    "CLC": {
      "all_prerequisites_met": true,
      "prerequisite_checks": [{ "id": "", "type": "", "met": true }],
      "unmet_prerequisites": [],
      "failure_paths": [{ "id": "", "symptoms": [], "classification": "", "confidence": 0.0 }],
      "pre_matched_paths": []
    }
  },
  "investigation_playbooks": {
    "CLC": {
      "display_name": "Cluster Lifecycle",
      "architecture": { "summary": "", "data_flow": [], "key_insight": "" },
      "prerequisites": [],
      "dependencies": [],
      "failure_paths": []
    }
  },
  "kg_dependency_context": {},
  "kg_status": { "available": false, "error": "", "impact": "", "remediation": "" },
  "gap_detection": {
    "stale_components": [],
    "hardcoded_namespaces": [],
    "missing_overlay": "",
    "overall_match_rate": 0.0,
    "gap_areas": [],
    "match_rates": {}
  }
}
```

#### 13. `errors` — Errors encountered during gathering (Script, throughout)

```json
["Knowledge Graph unavailable: ...", "..."]
```

---

## Services Used

| Service | Step | Purpose |
|---------|------|---------|
| `JenkinsAPIClient` | 1-3 | Jenkins REST API calls |
| `JenkinsIntelligenceService` | 1-3 | Build info, console parsing, test report |
| `StackTraceParser` | 3, 7 | Stack trace parsing (Step 3), assertion value extraction (Step 7) |
| `EnvironmentValidationService` | 4 | Cluster health checks + kubeconfig persistence |
| `ClusterInvestigationService` | 4 | Cluster landscape snapshot (v3.0) |
| `EnvironmentOracleService` | 5 | Feature-aware dependency health checking (v3.5) |
| `RepositoryAnalysisService` | 6 | Git clone, repo inference |
| `TimelineComparisonService` | 6 | Console + kubevirt repo cloning |
| `ACMConsoleKnowledge` | 6 | PatternFly version, structure validation, kubevirt repo detection |
| `ComponentExtractor` | 3 | Error → component names (detected_components) |
| `FeatureAreaService` | 8 | Test-to-feature-area mapping (v3.0) |
| `FeatureKnowledgeService` | 9 | Playbook loading, prerequisite checks, symptom matching (v3.1) |
| `KnowledgeGraphClient` | 9 | Neo4j dependency queries for kg_dependency_context (v3.2) |
| `ACMUIMCPClient` | 6 | CNV detection (Step 6) |
| `shared_utils` | All | Config, subprocess, credentials |

See [04-SERVICES-REFERENCE.md](04-SERVICES-REFERENCE.md) for detailed method signatures.

---

## CLI Options

```bash
# Basic usage
python -m src.scripts.gather "https://jenkins.example.com/job/test/123/"

# Options
python -m src.scripts.gather <url> --verbose       # Verbose logging
python -m src.scripts.gather <url> --skip-env      # Skip environment + cluster landscape + oracle (Steps 4-5)
python -m src.scripts.gather <url> --skip-repo     # Skip repository cloning (Steps 6-7)
python -m src.scripts.gather <url> -o ./my-runs    # Custom output directory
```
