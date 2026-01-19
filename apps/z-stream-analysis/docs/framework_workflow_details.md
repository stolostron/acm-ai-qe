# Z-Stream Analysis Framework - Technical Details

This document provides technical details about the Z-Stream Analysis framework architecture and workflow.

## Architecture Overview

The framework uses a three-stage pipeline for Jenkins pipeline failure analysis:

```
Stage 1: Data Gathering (gather.py)
    │
    ▼
Stage 2: AI Analysis (Investigation → Solution)
    │
    ▼
Stage 3: Report Generation (report.py)
```

## Stage 1: Data Gathering

The `gather.py` script collects all evidence needed for analysis.

### Data Sources

| Source | What It Collects |
|--------|------------------|
| Jenkins API | Build metadata, console log, test report, parameters |
| Environment | Cluster health, API accessibility (READ-ONLY) |
| Repository | Clone automation repo, index selectors, git history |
| Console Repo | Clone stolostron/console for timeline comparison |

### Multi-File Output Structure

Data is split across multiple files to stay under Claude Code's 25,000 token limit:

```
runs/<job>_<timestamp>/
├── manifest.json              # ~150 tokens - File index
├── core-data.json             # ~5,500 tokens - Primary data
├── repository-selectors.json  # ~7,500 tokens - Selector lookup
├── repository-test-files.json # ~7,000 tokens - Test file details
├── repository-metadata.json   # ~800 tokens - Repo summary
├── raw-data.json              # ~200 tokens - Backward-compat stub
├── evidence-package.json      # Pre-calculated classification scores
├── jenkins-build-info.json    # Build metadata (credentials masked)
├── console-log.txt            # Full console output
├── test-report.json           # Per-test failure details
└── environment-status.json    # Cluster health
```

### Evidence Package

The `evidence-package.json` contains pre-calculated classification scores:

```json
{
  "test_failures": [{
    "test_name": "test_create_cluster",
    "failure_evidence": {
      "error_type": "AssertionError",
      "failure_category": "element_not_found",
      "root_cause_file": "managedCluster.js",
      "root_cause_line": 181
    },
    "repository_evidence": {
      "selector_found": true,
      "selector_recently_changed": true,
      "days_since_modified": 6
    },
    "environment_evidence": {
      "cluster_healthy": true,
      "api_accessible": true
    },
    "pre_calculated_scores": {
      "product_bug_score": 0.45,
      "automation_bug_score": 0.50,
      "infrastructure_score": 0.05
    },
    "final_classification": "PRODUCT_BUG",
    "final_confidence": 0.72
  }]
}
```

## Stage 2: AI Analysis

The AI analysis phase uses two conceptual agents:

### Investigation Agent Workflow

1. Read `core-data.json` to understand the failure
2. Check `evidence_package.test_failures` for pre-calculated scores
3. For element_not_found errors, load `repository-selectors.json`
4. Cross-reference with `console_log.key_errors`

### Solution Agent Workflow

1. Apply classification decision matrix to each test failure
2. Run cross-reference validation to catch misclassifications
3. Calculate confidence scores
4. Generate fix recommendations
5. Save `analysis-results.json`

### Classification Decision Matrix

The framework uses formal rules for classification:

```python
# From classification_decision_matrix.py
DECISION_MATRIX = {
    ('element_not_found', True, True): (0.30, 0.60, 0.10),   # Product, Auto, Infra
    ('element_not_found', True, False): (0.60, 0.30, 0.10),
    ('element_not_found', False, True): (0.20, 0.30, 0.50),
    ('server_error', True, None): (0.90, 0.05, 0.05),
    ('timeout', True, None): (0.20, 0.70, 0.10),
    ('timeout', False, None): (0.10, 0.20, 0.70),
    ('network', False, None): (0.10, 0.10, 0.80),
    ('network', True, None): (0.60, 0.10, 0.30),
}
```

### Timeline Comparison

For element_not_found errors, the `TimelineComparisonService` compares git dates:

| Console Modified | Automation Modified | Classification |
|-----------------|---------------------|----------------|
| More recently | Earlier | AUTOMATION_BUG |
| Earlier | More recently | PRODUCT_BUG |
| Never existed | N/A | AUTOMATION_BUG |
| Removed | Still used | AUTOMATION_BUG |

## Stage 3: Report Generation

The `report.py` script generates reports from `analysis-results.json`:

| Output | Description |
|--------|-------------|
| `Detailed-Analysis.md` | Human-readable analysis with full details |
| `SUMMARY.txt` | Brief console-friendly summary |
| `analysis-metadata.json` | Machine-readable metadata |

### Analysis Results Schema

```json
{
  "analysis_metadata": {
    "jenkins_url": "https://...",
    "analyzed_at": "2026-01-15T15:00:00Z",
    "build_result": "UNSTABLE"
  },
  "per_test_analysis": [
    {
      "test_name": "...",
      "classification": "PRODUCT_BUG|AUTOMATION_BUG|INFRASTRUCTURE",
      "confidence": 0.85,
      "reasoning": "...",
      "evidence": ["..."],
      "recommended_fix": "..."
    }
  ],
  "summary": {
    "total_failures": 2,
    "by_classification": {
      "PRODUCT_BUG": 0,
      "AUTOMATION_BUG": 1,
      "INFRASTRUCTURE": 1
    }
  }
}
```

## Services Layer

### Core Services

| Service | File | Lines | Purpose |
|---------|------|-------|---------|
| Jenkins Intelligence | `jenkins_intelligence_service.py` | 950+ | Build info, test reports |
| Two-Agent Framework | `two_agent_intelligence_framework.py` | 1000+ | Agent orchestration |
| Evidence Validation | `evidence_validation_engine.py` | 600+ | False positive prevention |
| Environment Validation | `environment_validation_service.py` | 550+ | Cluster validation |
| Repository Analysis | `repository_analysis_service.py` | 750+ | Git clone, selector indexing |

### Classification Services

| Service | File | Purpose |
|---------|------|---------|
| Stack Trace Parser | `stack_trace_parser.py` | Parse stack traces to file:line |
| Classification Matrix | `classification_decision_matrix.py` | Formal classification rules |
| Confidence Calculator | `confidence_calculator.py` | 5-factor weighted scoring |
| Cross-Reference Validator | `cross_reference_validator.py` | Misclassification correction |
| Evidence Package Builder | `evidence_package_builder.py` | Build evidence packages |
| Timeline Comparison | `timeline_comparison_service.py` | Git date comparison |

### Utility Services

| Service | File | Purpose |
|---------|------|---------|
| Report Generator | `report_generator.py` | Multi-format reports |
| Jenkins MCP Client | `jenkins_mcp_client.py` | MCP integration |
| Schema Validation | `schema_validation_service.py` | JSON schema validation |
| Shared Utils | `shared_utils.py` | Common functions |

## Security Features

### Credential Masking

All sensitive data is masked before saving:

| Pattern | Example Masked |
|---------|----------------|
| `*PASSWORD*` | `QIE***MASKED***` |
| `*TOKEN*` | `kYu***MASKED***` |
| `*SECRET*` | `my-***MASKED***` |
| `*KEY*` | `api***MASKED***` |

### READ-ONLY Cluster Operations

Only whitelisted commands are allowed:

- `login`, `logout`, `whoami`, `cluster-info`, `version`
- `get`, `describe`, `api-resources`
- `auth can-i` (permission checks)
- `config current-context`, `config get-contexts`, `config view`

## Test Coverage

The framework has 220 unit tests across 11 test files:

```bash
# Run all tests
python3 -m pytest tests/unit/services/ -v
```

| Category | Tests |
|----------|-------|
| Classification services | 129 |
| Framework services | 35 |
| Integration and edge cases | 56 |

## Usage

### Basic Usage

```bash
# Gather data
python -m src.scripts.gather "https://jenkins.example.com/job/pipeline/123/"

# Generate reports (after AI analysis creates analysis-results.json)
python -m src.scripts.report runs/<run_dir>
```

### Full Pipeline

```bash
python main.py "https://jenkins.example.com/job/pipeline/123/"
```

### Options

```bash
python -m src.scripts.gather <url> --skip-env    # Skip cluster validation
python -m src.scripts.gather <url> --skip-repo   # Skip repository analysis
python -m src.scripts.gather <url> --verbose     # Verbose output
```
