# 2-Agent Pipeline Analysis Framework

This document explains how the Z-Stream Analysis framework uses a 2-agent architecture for Jenkins pipeline failure analysis.

## Overview

The framework follows a three-stage pipeline:

1. **Stage 1: Data Gathering** (`gather.py`) - Collects evidence from Jenkins, environment, and repository
2. **Stage 2: AI Analysis** - Investigation + Solution agents classify failures
3. **Stage 3: Report Generation** (`report.py`) - Generates human-readable reports

## 2-Agent Architecture

### Investigation Intelligence Agent

**Purpose**: Comprehensive evidence gathering and validation

**Responsibilities**:
- Jenkins data extraction (build metadata, console logs, test reports)
- Environment validation (cluster connectivity, health checks)
- Repository analysis (clone, selector indexing, git history)
- Evidence correlation across all sources

**Output**: Complete evidence package with pre-calculated classification scores

### Solution Intelligence Agent

**Purpose**: Analysis, classification, and solution generation

**Input**: Evidence package from Investigation phase

**Responsibilities**:
- Pattern recognition and root cause identification
- Classification decision (PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE)
- Fix recommendation generation
- Implementation guidance

**Output**: `analysis-results.json` with per-test classifications

## Context Flow

```
Jenkins URL
    │
    ▼
Investigation Agent
    ├── Jenkins API → build info, console log, test report
    ├── Environment → cluster validation (READ-ONLY)
    ├── Repository → clone, index selectors, git history
    └── Evidence Package → pre-calculated classification scores
    │
    ▼
Solution Agent
    ├── Read evidence package
    ├── Apply classification decision matrix
    ├── Cross-reference validation
    └── Generate analysis-results.json
    │
    ▼
Report Generation
    ├── Detailed-Analysis.md
    ├── SUMMARY.txt
    └── analysis-metadata.json
```

## Classification System

The framework uses a hybrid AI + script approach:

### Decision Matrix

The `ClassificationDecisionMatrix` maps (failure_type, env_healthy, selector_found) to weighted scores:

| Failure Type | Env Healthy | Selector Found | Product | Automation | Infra |
|--------------|-------------|----------------|---------|------------|-------|
| element_not_found | Yes | Yes | 30% | 60% | 10% |
| element_not_found | Yes | No | 60% | 30% | 10% |
| server_error | Yes | * | 90% | 5% | 5% |
| timeout | Yes | * | 20% | 70% | 10% |
| timeout | No | * | 10% | 20% | 70% |
| network | No | * | 10% | 10% | 80% |

### Cross-Reference Validator

Catches and corrects misclassifications:

| Rule | Condition | Action |
|------|-----------|--------|
| 500 Override | AUTOMATION_BUG + console has 500 errors | Correct to PRODUCT_BUG |
| Cluster Override | AUTOMATION_BUG + cluster unhealthy | Correct to INFRASTRUCTURE |
| Selector Change | PRODUCT_BUG + selector recently changed | Flag for review |

### Confidence Calculator

Five-factor weighted scoring:

| Factor | Weight | Description |
|--------|--------|-------------|
| Score Separation | 30% | How clearly one classification wins |
| Evidence Completeness | 25% | How much data we have |
| Source Consistency | 20% | Do all sources agree |
| Selector Certainty | 15% | Is selector status definitive |
| History Signal | 10% | Does git history support classification |

## Services Implementation

The framework is implemented with 17 Python services:

| Service | Purpose |
|---------|---------|
| `jenkins_intelligence_service.py` | Build info extraction, test report parsing |
| `two_agent_intelligence_framework.py` | 2-agent orchestration |
| `evidence_validation_engine.py` | Claim validation, false positive detection |
| `environment_validation_service.py` | Cluster validation (READ-ONLY) |
| `repository_analysis_service.py` | Git clone, selector indexing |
| `stack_trace_parser.py` | Parse stack traces to file:line |
| `classification_decision_matrix.py` | Formal classification rules |
| `confidence_calculator.py` | Multi-factor confidence scoring |
| `cross_reference_validator.py` | Misclassification correction |
| `evidence_package_builder.py` | Build structured evidence packages |
| `timeline_comparison_service.py` | Compare git dates between repos |
| `report_generator.py` | Multi-format report generation |

## Test Coverage

The framework has **220 unit tests** across 11 test files:

| Test File | Tests |
|-----------|-------|
| test_classification_decision_matrix.py | 35 |
| test_cross_reference_validator.py | 28 |
| test_evidence_package_builder.py | 28 |
| test_confidence_calculator.py | 27 |
| test_timeline_comparison_service.py | 19 |
| test_stack_trace_parser.py | 19 |
| test_data_classes.py | 16 |
| test_two_agent_intelligence_framework.py | 15 |
| test_integration_edge_cases.py | 13 |
| test_evidence_validation_engine.py | 11 |
| test_jenkins_intelligence_service.py | 9 |

## Usage

```bash
# Step 1: Gather data from Jenkins
python -m src.scripts.gather "https://jenkins.example.com/job/pipeline/123/"

# Step 2: AI analyzes core-data.json and creates analysis-results.json

# Step 3: Generate reports
python -m src.scripts.report runs/<run_dir>
```
