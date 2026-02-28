# Stage 1: Data Gathering (gather.py)

Collects all raw data needed for AI analysis from Jenkins, the target cluster, and source repositories.

---

## Overview

**Command:**
```bash
python -m src.scripts.gather "<JENKINS_URL>"
```

**Input:** Jenkins build URL (e.g., `https://jenkins.example.com/job/acm-e2e/123/`)

**Output:** A run directory with all collected data

```
                          Jenkins URL
                               │
    ┌──────────────────────────┼──────────────────────────┐
    │                          ▼                          │
    │   Step 1: Jenkins Info ──► Step 2: Console Log      │
    │                              │                      │
    │                              ▼                      │
    │                          Step 3: Test Report         │
    │                              │                      │
    │               ┌──────────────┼──────────────┐       │
    │               ▼                             ▼       │
    │   ┌───────────────────┐        ┌────────────────┐   │
    │   │ Step 4: Env Check │        │ Step 4b: (v3.0)│   │
    │   │ (skip: --skip-env)│        │ Cluster        │   │
    │   │                   │        │ Landscape      │   │
    │   └───────────────────┘        │ (skip:         │   │
    │               │                │  --skip-env)   │   │
    │               │                └────────────────┘   │
    │               ▼                                     │
    │   ┌───────────────────┐                             │
    │   │ Step 5: Clone     │                             │
    │   │ Repos             │                             │
    │   │ (skip: --skip-repo│                             │
    │   └─────────┬─────────┘                             │
    │             │                                       │
    │   ┌─────────┼──────────────────────┐                │
    │   ▼         ▼                      ▼                │
    │ Step 6:   Step 6b: (v3.0)  Step 6c: (v3.1)  Step 7: │
    │ Extract   Feature         Feature          Element │
    │ Context   Grounding       Knowledge        Inv.   │
    │ (skip:    (always)        + KG Context     (skip: │
    │  --skip-                  (always)          --skip-│
    │  repo)                                      repo) │
    │   └─────────┬──────────────────────────────┘       │
    │             ▼                                       │
    │   ┌───────────────────┐                             │
    │   │ Step 8: Hints     │ ◄── always runs             │
    │   │ + Step 8b:        │                             │
    │   │ Temporal Summaries│                             │
    │   └───────────────────┘                             │
    │             │                                       │
    └─────────────┼───────────────────────────────────────┘
                  ▼
        runs/<job>_<timestamp>/core-data.json
```

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

**Service:** `JenkinsIntelligenceService.analyze_jenkins_url()` (via `_fetch_console_log()` + `_analyze_failure_patterns()`)

**API:** `GET <jenkins_url>/consoleText` (authenticated)

The raw console output (can be 10MB+) is saved to `console-log.txt` and parsed for error patterns using regex.

### Regex Patterns

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

### Failure Type Classification

`_classify_failure_type()` returns a factual error type (not a bug classification):

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
    'patterns': {
        'timeout_errors': ['timed out after 30000', ...],
        'element_not_found': ['Expected to find element: #create-btn'],
        'network_errors': [],
        'assertion_failures': ['expected 3 to equal 5'],
        'build_failures': [],
        'environment_issues': []
    },
    'total_failures': 4,
    'primary_failure_type': 'timeout_errors'
}
```

**Output files:** `console-log.txt` (raw), error patterns embedded in `core-data.json`

---

## Step 3: Fetch Test Report

**Service:** `JenkinsIntelligenceService.analyze_jenkins_url()` (via `_fetch_and_analyze_test_report()`)

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

## Step 4: Environment Validation

**Service:** `EnvironmentValidationService.validate_environment()`

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

### Environment Score Calculation

Score is calculated additively from four weighted components (max 1.0):

| Component | Weight | Calculation |
|-----------|--------|-------------|
| Cluster connected | 20% | +0.2 if `connected` |
| API accessible | 20% | +0.2 if `api_accessible` |
| Service health | 40% | +0.4 × (healthy services / total services) |
| Namespace access | 20% | +0.2 × (accessible namespaces / total namespaces) |

If no namespaces are available to check, partial credit of 0.1 is given.

**Score interpretation:**

| Range | Status |
|-------|--------|
| 0.90 - 1.00 | Healthy |
| 0.70 - 0.89 | Minor issues |
| 0.50 - 0.69 | Degraded |
| 0.30 - 0.49 | Unhealthy |
| 0.00 - 0.29 | Critical → ALL TESTS = INFRASTRUCTURE |

### READ-ONLY Safety

| Allowed | NOT Allowed |
|---------|-------------|
| `oc get`, `oc describe` | `oc delete`, `oc apply` |
| `oc whoami`, `oc version` | `oc patch`, `oc edit` |
| `oc api-resources` | `oc scale`, `oc rollout` |
| `kubectl get`, `kubectl describe` | Any write operation |

**Output file:** `environment-status.json`

---

## Step 4b: Cluster Landscape (v3.0)

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

## Step 5: Repository Cloning

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

## Step 6: Context Extraction

**Method:** `DataGatherer._extract_complete_test_context()`

For each failed test, extracts three categories of context and additional metadata. This is the key v2.4 feature — providing AI with complete context upfront rather than requiring file reads during analysis.

```
For each failed test:
     │
     ├── Sub-step 6a: Read test file content
     ├── Sub-step 6b: Extract page objects
     ├── Sub-step 6c: Search console repository
     ├── Timeline evidence
     ├── Component extraction
     └── Temporal summary injection
```

### Sub-step 6a: Read Test File

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

### Sub-step 6b: Extract Page Objects

**Method:** `_extract_page_objects(test_content, failing_selector, automation_path)`

1. Parse import statements using regex: `r"import\s+.*?from\s+['\"]([^'\"]+)['\"]"`
2. Filter to view/selector imports (paths containing `views`, `selectors`, or `page`)
3. Resolve import paths (try `.js`, `.ts` extensions)
4. Read files, extract lines around failing selector (5 lines context) or first 50 lines

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

### Sub-step 6c: Search Console Repository

**Method:** `_search_console_for_selector(console_path, selector)`

1. Normalize selector: strip `#` or `.` prefix
2. Run grep: `grep -rn --include=*.tsx --include=*.ts --include=*.jsx --include=*.js "<selector>" repos/console/frontend/src/`
3. If found: return locations with file, line, content
4. If not found: search for partial match (first half of selector name) to find similar selectors

**Output:**
```json
{
  "selector": "#create-btn",
  "found": false,
  "locations": [],
  "similar_selectors": ["#cluster-create-btn", "#create-cluster-button"]
}
```

### Timeline Evidence

**Service:** `TimelineComparisonService.compare_timelines(selector)`

Compares git modification dates between automation and product repos:

| Output Field | Meaning |
|---|---|
| `element_never_existed` | Selector was never in product code |
| `element_removed` | Selector existed but was deleted |
| `stale_test_signal` | Product changed after automation last touched selector |
| `product_commit_type` | Type of last product change (rename, refactor, etc.) |

### Component Extraction

**Service:** `ComponentExtractor.extract_all_from_test_failure(error, stack, console)`

Extracts ACM component names from error messages. Each component includes:
- `name`: Component identifier (e.g., `search-api`)
- `subsystem`: Parent subsystem (e.g., `Search`)
- `source`: Where it was found (error_message, stack_trace, console_log)

### Temporal Summary Injection

**Method:** `_inject_temporal_summaries()`

Adds human-readable temporal summaries to each test's timeline evidence for AI consumption.

---

## Step 6b: Feature Area Grounding (v3.0)

**Service:** `FeatureAreaService.group_tests_by_feature()`

**Method:** `DataGatherer._ground_feature_areas()`

Groups all failed tests by feature area (CLC, Search, GRC, etc.) and attaches subsystem context. This runs **always** — it does not require cloned repos (unlike Step 6) because it uses test names, file paths, and detected components rather than file content.

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

## Step 6c: Feature Knowledge Playbooks (v3.1)

**Service:** `FeatureKnowledgeService.load_playbooks()`, `FeatureKnowledgeService.get_feature_readiness()`

**Method:** `DataGatherer._check_feature_knowledge()`

Loads YAML investigation playbooks from `src/data/feature_playbooks/`, checks MCH prerequisites against cluster state, pre-matches test error messages against known failure paths, and queries the Knowledge Graph for per-area dependency context. Runs after Step 6b (requires detected feature areas).

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

## Step 6d: Cluster Access Persistence (v3.1)

**Method:** Part of `DataGatherer._gather_environment_status()`

Persists cluster credentials (API URL, username, masked password) in `core-data.json` under `cluster_access` so the AI agent can re-authenticate to the cluster during Stage 2 for live investigation.

### Output Structure

```json
{
  "cluster_access": {
    "api_url": "https://api.cluster.example.com:6443",
    "username": "kubeadmin",
    "has_credentials": true,
    "password": "****masked****",
    "note": "Re-authenticate in Stage 2: oc login <api_url> --username <user> --password <password>"
  }
}
```

**Output:** Stored in `core-data.json` under `cluster_access` key.

---

## Step 7: Build Element Inventory

**Method:** `DataGatherer._gather_element_inventory()`

Builds an element inventory from the cloned repos and MCP data. Uses `ACMConsoleKnowledge.build_element_inventory()` and `ACMUIMCPClient` to locate data-testid and aria-label attributes in product source code.

Skipped when `--skip-repo` is used (requires cloned repos).

**Output file:** `element-inventory.json`

---

## Step 8: Build Investigation Hints

**Method:** `DataGatherer._build_investigation_hints()` + `_inject_temporal_summaries()`

Builds investigation hints for AI analysis, including timeline evidence and failed test locations. Then injects per-test temporal summaries into each test's `extracted_context` for AI consumption.

This step always runs (not gated by `--skip-repo`).

---

## Output Files

All collected data is written to the run directory.

**Files created:**

| File | Contents | Created By |
|------|----------|------------|
| `core-data.json` | All gathered data (primary file for AI) | gather.py |
| `run-metadata.json` | Run metadata (timing, version) | gather.py |
| `manifest.json` | File index with workflow metadata | gather.py |
| `console-log.txt` | Full Jenkins console output | gather.py |
| `jenkins-build-info.json` | Build metadata (credentials masked) | gather.py |
| `test-report.json` | Per-test failure details | gather.py |
| `environment-status.json` | Cluster health data | gather.py |
| `element-inventory.json` | MCP element locations (if available) | gather.py |
| `repos/` | Cloned repositories | gather.py |

### core-data.json Structure

```json
{
  "metadata": {
    "jenkins_url": "https://jenkins.../job/acm-e2e/123/",
    "gathered_at": "2026-02-04T15:30:00Z",
    "gatherer_version": "3.1.0"
  },
  "jenkins": {
    "job_name": "acm-qe-e2e-nightly",
    "build_number": 123,
    "result": "UNSTABLE",
    "parameters": [...]
  },
  "test_report": {
    "summary": { "total": 150, "failed": 8 },
    "failed_tests": [
      {
        "test_name": "should create cluster",
        "error_message": "Expected to find...",
        "failure_type": "element_not_found",
        "parsed_stack_trace": { ... },
        "extracted_context": {
          "test_file": { "content": "...", "line_count": 150 },
          "page_objects": [...],
          "console_search": { "found": false, ... }
        },
        "detected_components": [...]
      }
    ]
  },
  "environment": {
    "cluster_connectivity": true,
    "environment_score": 0.95
  },
  "cluster_landscape": {
    "managed_clusters": [...],
    "operators": [...],
    "resource_pressure": {...},
    "mch_status": "Running"
  },
  "console_log": {
    "error_patterns": { ... },
    "key_errors": [...]
  },
  "investigation_hints": {
    "timeline_evidence": { ... },
    "failed_test_locations": [...]
  },
  "feature_grounding": {
    "groups": {
      "CLC": { "subsystem": "Cluster", "test_count": 3, "key_components": [...] },
      "Search": { "subsystem": "Search", "test_count": 2, "key_components": [...] }
    }
  },
  "feature_knowledge": {
    "acm_version": "2.16",
    "profiles_loaded": ["CLC", "Search", "Automation"],
    "feature_readiness": { ... },
    "investigation_playbooks": { ... },
    "kg_dependency_context": { ... },
    "kg_status": { "available": true }
  },
  "cluster_access": {
    "api_url": "https://api.cluster.example.com:6443",
    "username": "kubeadmin",
    "has_credentials": true,
    "password": "****masked****"
  },
  "ai_instructions": { ... }
}
```

---

## Services Used

| Service | Step | Purpose |
|---------|------|---------|
| `JenkinsAPIClient` | 1-3 | Jenkins REST API calls |
| `JenkinsIntelligenceService` | 1-3 | Build info, console parsing, test report |
| `StackTraceParser` | 3 | JS/TS stack trace → file:line |
| `EnvironmentValidationService` | 4 | Cluster health checks |
| `ClusterInvestigationService` | 4b | Cluster landscape snapshot (v3.0) |
| `RepositoryAnalysisService` | 5 | Git clone, repo inference |
| `TimelineComparisonService` | 6 | Git date comparison |
| `ComponentExtractor` | 6 | Error → component names |
| `ACMConsoleKnowledge` | 6-7 | Directory structure mapping |
| `FeatureAreaService` | 6b | Test-to-feature-area mapping (v3.0) |
| `FeatureKnowledgeService` | 6c | Playbook loading, prerequisite checks, symptom matching (v3.1) |
| `KnowledgeGraphClient` | 6c | Neo4j dependency queries for kg_dependency_context (v3.2) |
| `ACMUIMCPClient` | 5, 7 | CNV detection (Step 5), element inventory (Step 7) |
| `shared_utils` | All | Config, subprocess, credentials |

See [04-SERVICES-REFERENCE.md](04-SERVICES-REFERENCE.md) for detailed method signatures.

---

## CLI Options

```bash
# Basic usage
python -m src.scripts.gather "https://jenkins.example.com/job/test/123/"

# Options
python -m src.scripts.gather <url> --verbose       # Verbose logging
python -m src.scripts.gather <url> --skip-env      # Skip environment validation (Step 4)
python -m src.scripts.gather <url> --skip-repo     # Skip repository cloning (Steps 5-7)
python -m src.scripts.gather <url> -o ./my-runs    # Custom output directory
```
