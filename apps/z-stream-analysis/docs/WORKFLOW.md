# Z-Stream Analysis - Complete Workflow Documentation

## Overview

This document outlines the complete workflow of the z-stream-analysis application, detailing every stage, function, input, output, and data transformation.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           JENKINS URL INPUT                              │
│              https://jenkins.example.com/job/pipeline/123/               │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        STAGE 1: DATA GATHERING                           │
│                         (src/scripts/gather.py)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Jenkins    │  │  Console     │  │ Environment  │  │  Repository  │ │
│  │   Service    │  │  Log         │  │  Validation  │  │  Analysis    │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         └──────────────────┼─────────────────┼─────────────────┘         │
│                            ▼                 ▼                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    EVIDENCE PACKAGE BUILDER                          ││
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  ││
│  │  │ Stack Trace     │  │ Classification  │  │ Cross-Reference     │  ││
│  │  │ Parser          │  │ Decision Matrix │  │ Validator           │  ││
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
                        Multi-File Output:
                    manifest.json, core-data.json,
                  repository-*.json, evidence-package.json
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        STAGE 2: AI ANALYSIS                              │
│                             (main.py)                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │              TWO-AGENT INTELLIGENCE FRAMEWORK                        ││
│  │  ┌─────────────────────────┐  ┌─────────────────────────────────┐   ││
│  │  │ PHASE 1: Investigation  │  │ PHASE 2: Solution               │   ││
│  │  │ Intelligence Agent      │─▶│ Intelligence Agent              │   ││
│  │  │ - Evidence gathering    │  │ - Bug classification            │   ││
│  │  │ - Pattern detection     │  │ - Fix recommendations           │   ││
│  │  │ - Source correlation    │  │ - Implementation guidance       │   ││
│  │  └─────────────────────────┘  └─────────────────────────────────┘   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │              EVIDENCE VALIDATION ENGINE                              ││
│  │  - Verify technical claims                                           ││
│  │  - Detect false positives                                            ││
│  │  - Cross-source consistency                                          ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
                       analysis-results.json
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        STAGE 3: REPORT GENERATION                        │
│                        (src/scripts/report.py)                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                      REPORT GENERATOR                                ││
│  │  Output Files:                                                       ││
│  │  - Detailed-Analysis.md (human-readable)                            ││
│  │  - SUMMARY.txt (console-friendly)                                   ││
│  │  - analysis-metadata.json (machine-readable)                        ││
│  │  - full-analysis-results.json (complete data)                       ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## STAGE 1: DATA GATHERING

### Entry Point: `src/scripts/gather.py`

#### Main Function: `DataGatherer.gather_all()`

```python
def gather_all(jenkins_url: str, skip_environment: bool, skip_repository: bool) -> Tuple[Path, Dict]
```

**Inputs:**
- `jenkins_url`: Full Jenkins build URL (e.g., `https://jenkins.example.com/job/pipeline/123/`)
- `skip_environment`: Skip cluster validation (default: False)
- `skip_repository`: Skip repo analysis (default: False)

**Outputs:**
- `run_dir`: Path to created run directory (e.g., `runs/pipeline_20260116_143000/`)
- `gathered_data`: Dictionary with all collected data

**Sub-steps:**

---

### Step 1.1: Create Run Directory

```python
def _create_run_directory(jenkins_url: str) -> Path
```

**Creates:**
```
runs/<job_name>_<timestamp>/
├── run-metadata.json    # Initial status
```

**Output Example:**
```json
{
  "jenkins_url": "https://jenkins.example.com/job/pipeline/123/",
  "created_at": "2026-01-16T14:30:00",
  "status": "gathering"
}
```

---

### Step 1.2: Gather Jenkins Build Info

```python
def _gather_jenkins_build_info(jenkins_url: str, run_dir: Path)
```

**Service Used:** `JenkinsIntelligenceService.analyze_jenkins_url()`

**Flow:**
1. Check if MCP is available (`is_mcp_available()`)
2. Fetch build info via MCP or curl fallback
3. Extract metadata (job_name, build_number, result, branch, commit)
4. Extract build parameters (including cluster credentials)
5. Mask sensitive data before saving

**Output File:** `jenkins-build-info.json`

```json
{
  "build_url": "https://jenkins.example.com/job/pipeline/123/",
  "job_name": "pipeline",
  "build_number": 123,
  "build_result": "UNSTABLE",
  "branch": "release-2.15",
  "commit_sha": "abc123def456",
  "parameters": {
    "CYPRESS_HUB_API_URL": "https://api.cluster.example.com:6443",
    "CYPRESS_OPTIONS_HUB_PASSWORD": "***MASKED***"
  }
}
```

---

### Step 1.3: Gather Console Log

```python
def _gather_console_log(jenkins_url: str, run_dir: Path)
```

**Services Used:**
- `JenkinsMCPClient.get_console_output()` (if MCP available)
- `JenkinsIntelligenceService._fetch_console_log()` (fallback)

**Flow:**
1. Fetch full console output
2. Save raw console log
3. Extract error lines (contains 'error' or 'fail')
4. Extract warning lines
5. Store first 20 error lines in `key_errors`

**Output Files:**
- `console-log.txt` (full output)
- Updates `gathered_data['console_log']`

```json
{
  "file_path": "console-log.txt",
  "total_lines": 5000,
  "error_lines_count": 25,
  "warning_lines_count": 10,
  "key_errors": [
    "Error: cy.get('#managedClusterSet') - element not found",
    "Error: Request failed with status code 500"
  ]
}
```

---

### Step 1.4: Gather Test Report

```python
def _gather_test_report(jenkins_url: str, run_dir: Path)
```

**Service Used:** `JenkinsIntelligenceService._fetch_and_analyze_test_report()`

**Flow:**
1. Fetch test report from Jenkins API (`/testReport/api/json`)
2. Parse each test case (passed, failed, skipped)
3. For each failed test:
   - Extract full error message (no truncation)
   - Extract full stack trace (no truncation)
   - Parse stack trace to get file:line
   - Extract failing selector from error message
   - Determine failure type (timeout, element_not_found, etc.)
   - Pre-classify with confidence score

**Output File:** `test-report.json`

```json
{
  "summary": {
    "total_tests": 50,
    "passed_count": 47,
    "failed_count": 3,
    "skipped_count": 0,
    "pass_rate": 94.0,
    "duration": 754.0
  },
  "failed_tests": [
    {
      "test_name": "test_create_managed_cluster",
      "class_name": "managedCluster.spec.js",
      "status": "FAILED",
      "duration_seconds": 15.5,
      "error_message": "Expected to find element: `#managedClusterSet-radio`, but never found it.",
      "stack_trace": "AssertionError: ...\n    at webpack://app/./cypress/views/clusters/managedCluster.js:181:11",
      "failure_type": "element_not_found",
      "preliminary_classification": "AUTOMATION_BUG",
      "preliminary_confidence": 0.65,
      "preliminary_reasoning": "Element not found but selector exists in codebase"
    }
  ]
}
```

---

### Step 1.5: Gather Environment Status

```python
def _gather_environment_status(run_dir: Path)
```

**Service Used:** `EnvironmentValidationService.validate_environment()`

**Flow:**
1. Extract target cluster credentials from Jenkins parameters:
   - `CYPRESS_HUB_API_URL` / `CLUSTER_API_URL` / `API_URL`
   - `CYPRESS_OPTIONS_HUB_USER` / `CLUSTER_USER` / `USERNAME`
   - `CYPRESS_OPTIONS_HUB_PASSWORD` / `CLUSTER_PASSWORD` / `PASSWORD`
2. If credentials found:
   - Create temporary kubeconfig
   - Run `oc login` to target cluster
   - Set `target_cluster_used: true`
3. Run READ-ONLY validation commands:
   - `oc cluster-info`
   - `oc whoami`
   - `oc version`
   - `oc get nodes`
   - `oc get pods -n open-cluster-management`
4. Calculate environment health score
5. Cleanup temporary kubeconfig

**Output File:** `environment-status.json`

```json
{
  "healthy": true,
  "accessible": true,
  "api_accessible": true,
  "target_cluster_used": true,
  "cluster_url": "https://api.qe6-cluster.example.com:6443",
  "environment_score": 0.85,
  "pod_status": {
    "open-cluster-management": {
      "total": 25,
      "ready": 24,
      "not_ready": 1
    }
  },
  "errors": []
}
```

---

### Step 1.6: Gather Repository Analysis

```python
def _gather_repository_analysis(jenkins_url: str, run_dir: Path)
```

**Service Used:** `RepositoryAnalysisService.analyze_repository()`

**Flow:**
1. Extract repo URL and branch from console log:
   - Pattern: `Checking out git https://github.com/org/repo.git`
   - Pattern: `Checking out Revision abc123 (origin/release-2.15)`
2. Clone repository at specified branch (full clone, not shallow)
3. Index all test files by framework:
   - Cypress: `*.cy.js`, `*.cy.ts`, `cypress/**/*.js`
   - Jest: `*.test.js`, `*.test.ts`, `__tests__/**/*.js`
   - Pytest: `test_*.py`, `*_test.py`
4. Extract selectors from test files:
   - `#id`, `.class`, `[data-cy=...]`, `[data-test=...]`
5. Build selector lookup: `selector → [file1.js, file2.js]`
6. Get git history for selectors (when they were last changed)
7. Cleanup cloned repository

**Output:** Updates `gathered_data['repository']` (saved to multi-file structure)

```json
{
  "repository_url": "https://github.com/stolostron/console.git",
  "branch": "release-2.15",
  "commit_sha": "abc123def456",
  "repository_cloned": true,
  "test_files": [
    {
      "path": "cypress/tests/managedCluster.spec.js",
      "test_framework": "cypress",
      "test_count": 12,
      "selectors": ["#managedClusterSet-radio", "#create-cluster-btn", ".cluster-name"]
    }
  ],
  "selector_lookup": {
    "#managedClusterSet-radio": [
      "cypress/views/clusters/managedCluster.js",
      "cypress/tests/managedCluster.spec.js"
    ]
  },
  "selector_history": {
    "#managedClusterSet-radio": {
      "date": "2026-01-10",
      "sha": "xyz789abc",
      "message": "feat: Update cluster set radio button for PatternFly v6",
      "days_ago": 6
    }
  }
}
```

---

### Step 1.7: Build Evidence Packages

```python
def _build_evidence_packages(jenkins_url: str, run_dir: Path)
```

**Service Used:** `EvidencePackageBuilder.build_package()`

**Sub-services:**
- `StackTraceParser` - Parse stack traces to file:line
- `ClassificationDecisionMatrix` - Apply formal classification rules
- `ConfidenceCalculator` - Calculate multi-factor confidence
- `CrossReferenceValidator` - Catch misclassifications

**Flow:**
1. For each failed test:
   a. Parse stack trace to extract frames
   b. Extract failing selector from error message
   c. Look up selector in repository data
   d. Check if selector was recently changed
   e. Apply decision matrix based on:
      - `failure_type` (timeout, element_not_found, server_error, network)
      - `env_healthy` (true/false)
      - `selector_found` (true/false/null)
   f. Apply additional factors (console_500_error, selector_recently_changed)
   g. Calculate confidence using 5-factor model
   h. Run cross-reference validation (may correct classification)
2. Aggregate all test failures into evidence package
3. Calculate overall classification and confidence

**Output File:** `evidence-package.json`

```json
{
  "metadata": {
    "jenkins_url": "https://jenkins.example.com/job/pipeline/123/",
    "build_number": 123,
    "analyzed_at": "2026-01-16T14:35:00Z"
  },
  "test_failures": [
    {
      "test_name": "test_create_managed_cluster",
      "failure_evidence": {
        "error_type": "AssertionError",
        "error_message": "Expected to find element: `#managedClusterSet-radio`",
        "failure_category": "element_not_found",
        "root_cause_file": "cypress/views/clusters/managedCluster.js",
        "root_cause_line": 181,
        "failing_selector": "#managedClusterSet-radio"
      },
      "repository_evidence": {
        "repository_cloned": true,
        "branch": "release-2.15",
        "selector_evidence": {
          "selector": "#managedClusterSet-radio",
          "found_in_codebase": true,
          "file_paths": ["managedCluster.js", "managedCluster.spec.js"],
          "recently_changed": true,
          "days_since_modified": 6
        }
      },
      "environment_evidence": {
        "cluster_healthy": true,
        "cluster_accessible": true,
        "api_accessible": true,
        "target_cluster_used": true
      },
      "console_evidence": {
        "has_500_errors": true,
        "has_network_errors": false,
        "has_api_errors": true
      },
      "classification_result": {
        "classification": "AUTOMATION_BUG",
        "confidence": 0.65,
        "scores": {
          "product_bug": 0.30,
          "automation_bug": 0.60,
          "infrastructure": 0.10
        }
      },
      "validation_report": {
        "was_corrected": true,
        "needs_review": true,
        "original_classification": "AUTOMATION_BUG",
        "final_classification": "PRODUCT_BUG"
      },
      "pre_calculated_scores": {
        "product_bug_score": 0.45,
        "automation_bug_score": 0.50,
        "infrastructure_score": 0.05
      },
      "final_classification": "PRODUCT_BUG",
      "final_confidence": 0.72,
      "reasoning": "Element not found but console shows 500 errors - cross-validation overrode to PRODUCT_BUG"
    }
  ],
  "summary": {
    "total_failures": 3,
    "by_classification": {
      "PRODUCT_BUG": 3
    },
    "overall_classification": "PRODUCT_BUG",
    "overall_confidence": 0.78
  }
}
```

---

### Step 1.8: Save Multi-File Data

```python
def _save_multi_file_data(run_dir: Path)
```

Data is split across multiple files to stay under Claude Code's 25,000 token limit:

**Output Files:**

| File | Tokens | Purpose |
|------|--------|---------|
| `manifest.json` | ~150 | File index and workflow instructions |
| `core-data.json` | ~5,500 | Primary data for AI (read first) |
| `repository-selectors.json` | ~7,500 | Selector lookup (on-demand) |
| `repository-test-files.json` | ~7,000 | Test file details (on-demand) |
| `repository-metadata.json` | ~800 | Repo summary (on-demand) |
| `raw-data.json` | ~200 | Backward compatibility stub |

**core-data.json Structure:**

```json
{
  "metadata": {
    "jenkins_url": "...",
    "gathered_at": "2026-01-16T14:30:00",
    "gathering_time_seconds": 45.2,
    "status": "complete"
  },
  "jenkins": { /* from step 1.2 */ },
  "test_report": { /* from step 1.4 */ },
  "console_log": { /* from step 1.3 */ },
  "environment": { /* from step 1.5 */ },
  "evidence_package": { /* from step 1.7 */ },
  "ai_instructions": {
    "version": "2.0.0",
    "file_structure": "multi-file",
    "workflow": [
      "1. This file contains all primary analysis data",
      "2. Check evidence_package.test_failures for pre-calculated scores",
      "3. For element_not_found errors, load repository-selectors.json",
      "4. For stack trace analysis, load repository-test-files.json",
      "5. Classify each test as PRODUCT_BUG, AUTOMATION_BUG, or INFRASTRUCTURE",
      "6. Save analysis-results.json following the schema"
    ]
  }
}
```

**manifest.json Structure:**

```json
{
  "version": "2.0.0",
  "file_structure": "multi-file",
  "files": {
    "core-data.json": { "description": "Primary data", "load_first": true },
    "repository-selectors.json": { "description": "Selector lookup", "load_on_demand": true },
    "repository-test-files.json": { "description": "Test files", "load_on_demand": true }
  },
  "workflow": ["Read core-data.json first", "Load selectors on-demand"]
}
```

---

## STAGE 2: AI ANALYSIS

### Entry Point: `main.py`

#### Main Function: `run_analysis()`

```python
def run_analysis(jenkins_url: str, output_dir: str, logger: Logger) -> dict
```

**Flow:**
1. Create output directory
2. Initialize `TwoAgentIntelligenceFramework`
3. Run Phase 1: Investigation Intelligence
4. Run Phase 2: Solution Intelligence
5. Run Evidence Validation
6. Save results via `ReportGenerator`

---

### Phase 1: Investigation Intelligence Agent

**Service:** `TwoAgentIntelligenceFramework.investigate_pipeline_failure()`

**Purpose:** Gather and correlate evidence from all sources

**Inputs:**
- Jenkins URL
- Raw data from gather phase

**Outputs:**
- `InvestigationResult` with:
  - `jenkins_intelligence`: Build info, test failures
  - `environment_validation`: Cluster health
  - `repository_analysis`: Test files, selectors
  - `evidence_correlation`: Cross-source patterns
  - `confidence_score`: 0.0-1.0

---

### Phase 2: Solution Intelligence Agent

**Service:** `TwoAgentIntelligenceFramework.generate_solution()`

**Purpose:** Analyze evidence and generate classifications + fixes

**Inputs:**
- `InvestigationResult` from Phase 1

**Outputs:**
- `SolutionResult` with:
  - `evidence_analysis`: Per-test analysis, multi-failure summary
  - `bug_classification`: Primary + per-test classifications
  - `fix_recommendations`: Per-test and overall fixes
  - `implementation_guidance`: Prerequisites, validation, rollback
  - `confidence_score`: 0.0-1.0

---

### Evidence Validation

**Service:** `EvidenceValidationEngine.validate_technical_claims()`

**Purpose:** Verify all technical claims are accurate

**Validation Types:**
- `FILE_EXISTENCE` - Verify mentioned files exist
- `DEPENDENCY_VERIFICATION` - Check package.json dependencies
- `EXTENSION_VERIFICATION` - Verify file extensions
- `TECHNICAL_CLAIM_VERIFICATION` - Check technical assertions
- `CROSS_SOURCE_CONSISTENCY` - Verify consistency

**Output:**
- `ValidationSummary` with `false_positive_risk` score

---

## STAGE 3: REPORT GENERATION

### Entry Point: `src/scripts/report.py`

**Service:** `ReportGenerator.generate_all_reports()`

**Inputs:**
- `analysis_result`: Complete analysis from Stage 2
- `jenkins_url`: Original URL
- `run_dir`: Output directory

**Outputs:**

### Detailed-Analysis.md

Human-readable markdown report with:
- Classification banner (PRODUCT_BUG / AUTOMATION_BUG / INFRASTRUCTURE)
- Executive summary
- Per-test failure breakdown
- Classification breakdown table
- Environment assessment
- Repository analysis
- Recommended actions
- Evidence sources

### SUMMARY.txt

Console-friendly text summary:
```
================================================================================
Z-STREAM ANALYSIS SUMMARY
================================================================================

BUILD: pipeline #123 (UNSTABLE)
BRANCH: release-2.15

CLASSIFICATION: PRODUCT_BUG
CONFIDENCE: 78%

FAILURES: 3 total
  - PRODUCT_BUG: 3

TOP ACTION: Fix backend 500 error in cluster API endpoint
================================================================================
```

### JSON Files

- `analysis-metadata.json` - Timing, confidence, classification
- `full-analysis-results.json` - Complete analysis data

---

## CLASSIFICATION DECISION MATRIX

The `ClassificationDecisionMatrix` applies formal rules:

| Failure Type | Env Healthy | Selector Found | → Product | → Automation | → Infra |
|--------------|-------------|----------------|-----------|--------------|---------|
| element_not_found | true | true | 30% | 60% | 10% |
| element_not_found | true | false | 60% | 30% | 10% |
| element_not_found | false | * | 20% | 30% | 50% |
| server_error | true | * | 90% | 5% | 5% |
| server_error | false | * | 60% | 10% | 30% |
| timeout | true | * | 20% | 70% | 10% |
| timeout | false | * | 10% | 20% | 70% |
| network | true | * | 60% | 10% | 30% |
| network | false | * | 10% | 10% | 80% |
| assertion | true | * | 50% | 45% | 5% |
| auth_error | true | * | 40% | 50% | 10% |
| auth_error | false | * | 30% | 20% | 50% |

**Additional Factors:**
- `console_500_error` → +15% PRODUCT_BUG
- `selector_recently_changed` → +20% AUTOMATION_BUG
- `cluster_inaccessible` → +25% INFRASTRUCTURE

---

## CONFIDENCE CALCULATION

Five-factor weighted model:

| Factor | Weight | Description |
|--------|--------|-------------|
| Score Separation | 30% | How clearly one classification wins |
| Evidence Completeness | 25% | How much data we have |
| Source Consistency | 20% | Do all sources agree |
| Selector Certainty | 15% | Is selector status definitive |
| History Signal | 10% | Does git history support classification |

---

## CROSS-REFERENCE VALIDATION RULES

| Rule | Condition | Action |
|------|-----------|--------|
| 500 Override | AUTOMATION_BUG + console has 500 errors | Correct → PRODUCT_BUG |
| Cluster Override | AUTOMATION_BUG + cluster unhealthy | Correct → INFRASTRUCTURE |
| Selector Change | PRODUCT_BUG + selector recently changed | Flag for review |
| Network Mismatch | AUTOMATION_BUG + network errors in console | Flag for review |
| Infra Healthy | INFRASTRUCTURE + env healthy | Flag for review, reduce confidence |

---

## FILE OUTPUTS

After running the complete pipeline:

```
runs/<job>_<timestamp>/
├── manifest.json              # File index (multi-file structure)
├── core-data.json             # Primary data for AI (~5,500 tokens)
├── repository-selectors.json  # Selector lookup (~7,500 tokens)
├── repository-test-files.json # Test files (~7,000 tokens)
├── repository-metadata.json   # Repo summary (~800 tokens)
├── raw-data.json              # Backward-compat stub (~200 tokens)
├── evidence-package.json      # Pre-calculated scores (from gather)
├── jenkins-build-info.json    # Build metadata (masked)
├── console-log.txt            # Full console output
├── test-report.json           # Per-test failure details
├── environment-status.json    # Cluster health
├── analysis-results.json      # AI analysis output
├── Detailed-Analysis.md       # Human-readable report
├── SUMMARY.txt                # Brief summary
├── analysis-metadata.json     # Timing + confidence
└── full-analysis-results.json # Complete data
```

### Multi-File Data Architecture

Data is split to stay under Claude Code's 25,000 token limit:

| File | Tokens | When to Load |
|------|--------|--------------|
| `core-data.json` | ~5,500 | Always (read first) |
| `repository-selectors.json` | ~7,500 | For element_not_found errors |
| `repository-test-files.json` | ~7,000 | For stack trace analysis |
| `repository-metadata.json` | ~800 | For repo details |
| `manifest.json` | ~150 | File index |
| `raw-data.json` | ~200 | Backward compatibility only |

---

## SERVICE DEPENDENCIES

```
gather.py
├── JenkinsIntelligenceService
│   └── JenkinsMCPClient (optional)
├── EnvironmentValidationService
├── RepositoryAnalysisService
└── EvidencePackageBuilder
    ├── StackTraceParser
    ├── ClassificationDecisionMatrix
    ├── ConfidenceCalculator
    └── CrossReferenceValidator

main.py
├── TwoAgentIntelligenceFramework
│   ├── InvestigationIntelligenceAgent
│   │   ├── JenkinsIntelligenceService
│   │   ├── EnvironmentValidationService
│   │   └── RepositoryAnalysisService
│   └── SolutionIntelligenceAgent
│       ├── ClassificationDecisionMatrix
│       ├── ConfidenceCalculator
│       └── CrossReferenceValidator
├── EvidenceValidationEngine
└── ReportGenerator
```

---

## SHARED UTILITIES

`src/services/shared_utils.py` provides:

| Utility | Purpose |
|---------|---------|
| `run_subprocess()` | Standardized subprocess execution |
| `build_curl_command()` | Curl command construction |
| `execute_curl()` | Combined curl execution |
| `parse_json_response()` | JSON parsing with HTML detection |
| `get_jenkins_credentials()` | Env var credential extraction |
| `get_auth_header()` | Basic auth header generation |
| `encode_basic_auth()` | Auth encoding |
| `decode_basic_auth()` | Auth decoding |
| `is_test_file()` | File type detection |
| `is_framework_file()` | Framework file detection |
| `detect_test_framework()` | Framework detection |
| `dataclass_to_dict()` | Dataclass conversion |
| `ServiceBase` | Base class with logging |
| `mask_sensitive_value()` | Credential masking |
| `mask_sensitive_dict()` | Recursive dict masking |

---

## CLI USAGE

```bash
# Step 1: Gather data
python -m src.scripts.gather "https://jenkins.example.com/job/pipeline/123/"

# Step 2: AI analyzes the data
# Read core-data.json first (primary data, ~5,500 tokens)
# Load repository-selectors.json on-demand for element_not_found errors
# Save analysis-results.json

# Step 3: Generate reports
python -m src.scripts.report runs/<run_dir>

# Or run full pipeline
python main.py "https://jenkins.example.com/job/pipeline/123/"
```

---

## TESTS

```bash
# Unit tests (220 tests total)
python3 -m pytest tests/unit/services/ -v

# E2E workflow simulation
python3 tests/e2e_workflow_simulation.py
```
