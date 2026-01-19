# Z-Stream Analysis Implementation Status

## Current Status: Production Ready

The Z-Stream Analysis framework is implemented with 17 Python services, a hybrid AI + script classification system, multi-file data architecture, and 220 unit tests.

## Services (17 Total)

### Core Services

| Service | File | Purpose |
|---------|------|---------|
| Jenkins Intelligence | `jenkins_intelligence_service.py` | Build info extraction, test report parsing |
| Two-Agent Framework | `two_agent_intelligence_framework.py` | Agent orchestration |
| Evidence Validation | `evidence_validation_engine.py` | Claim validation, false positive detection |
| Environment Validation | `environment_validation_service.py` | Cluster validation (READ-ONLY) |
| Repository Analysis | `repository_analysis_service.py` | Git clone, selector indexing |

### Classification Services

| Service | File | Purpose |
|---------|------|---------|
| Stack Trace Parser | `stack_trace_parser.py` | Parse stack traces to file:line |
| Classification Matrix | `classification_decision_matrix.py` | Formal classification rules |
| Confidence Calculator | `confidence_calculator.py` | 5-factor weighted scoring |
| Cross-Reference Validator | `cross_reference_validator.py` | Misclassification correction |
| Evidence Package Builder | `evidence_package_builder.py` | Build evidence packages |
| Timeline Comparison | `timeline_comparison_service.py` | Git date comparison |
| AST Integration | `ast_integration_service.py` | Optional Node.js AST helper |

### Utility Services

| Service | File | Purpose |
|---------|------|---------|
| Report Generator | `report_generator.py` | Multi-format reports |
| Jenkins MCP Client | `jenkins_mcp_client.py` | MCP integration |
| Schema Validation | `schema_validation_service.py` | JSON schema validation |
| Shared Utils | `shared_utils.py` | Common functions |

## Scripts

| Script | File | Purpose |
|--------|------|---------|
| Data Gathering | `src/scripts/gather.py` | Jenkins data collection, evidence package building |
| Report Generation | `src/scripts/report.py` | Generate Markdown/Text/JSON reports |

## Schemas

| Schema | File | Purpose |
|--------|------|---------|
| Analysis Results | `analysis_results_schema.json` | JSON Schema for analysis output |
| Analysis Template | `analysis_results_template.json` | Template for AI-generated results |
| Evidence Package | `evidence_package_schema.json` | Schema for evidence packages |
| Manifest | `manifest_schema.json` | Schema for multi-file structure |

## Test Coverage (220 Tests)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_classification_decision_matrix.py | 35 | Classification rules |
| test_cross_reference_validator.py | 28 | Misclassification correction |
| test_evidence_package_builder.py | 28 | Evidence package building |
| test_confidence_calculator.py | 27 | Confidence scoring |
| test_timeline_comparison_service.py | 19 | Git date comparison |
| test_stack_trace_parser.py | 19 | Stack trace parsing |
| test_data_classes.py | 16 | Data structures, enums |
| test_two_agent_intelligence_framework.py | 15 | Agent coordination |
| test_integration_edge_cases.py | 13 | Edge cases |
| test_evidence_validation_engine.py | 11 | False positive prevention |
| test_jenkins_intelligence_service.py | 9 | Build info, console analysis |

## File Structure

```
z-stream-analysis/
├── main.py                                    # Full pipeline orchestration
├── CLAUDE.md                                  # Primary documentation
├── .claude/
│   ├── settings.json
│   ├── settings.local.json
│   └── agents/
│       ├── z-stream-analysis.md
│       ├── investigation-intelligence.md
│       └── solution-intelligence.md
├── src/
│   ├── schemas/
│   │   ├── analysis_results_schema.json
│   │   ├── analysis_results_template.json
│   │   ├── evidence_package_schema.json
│   │   └── manifest_schema.json
│   ├── scripts/
│   │   ├── gather.py
│   │   └── report.py
│   └── services/
│       ├── jenkins_intelligence_service.py
│       ├── jenkins_mcp_client.py
│       ├── two_agent_intelligence_framework.py
│       ├── evidence_validation_engine.py
│       ├── environment_validation_service.py
│       ├── repository_analysis_service.py
│       ├── report_generator.py
│       ├── schema_validation_service.py
│       ├── shared_utils.py
│       ├── stack_trace_parser.py
│       ├── classification_decision_matrix.py
│       ├── confidence_calculator.py
│       ├── cross_reference_validator.py
│       ├── evidence_package_builder.py
│       ├── ast_integration_service.py
│       └── timeline_comparison_service.py
├── tests/
│   ├── deep_dive_validation.py
│   ├── e2e_workflow_simulation.py
│   └── unit/
│       └── services/
│           ├── test_jenkins_intelligence_service.py
│           ├── test_two_agent_intelligence_framework.py
│           ├── test_evidence_validation_engine.py
│           ├── test_data_classes.py
│           ├── test_integration_edge_cases.py
│           ├── test_stack_trace_parser.py
│           ├── test_classification_decision_matrix.py
│           ├── test_confidence_calculator.py
│           ├── test_cross_reference_validator.py
│           ├── test_evidence_package_builder.py
│           └── test_timeline_comparison_service.py
├── docs/
│   ├── implementation-status.md
│   ├── agents_concepts_workflow.md
│   ├── documentation-status.md
│   ├── framework_workflow_details.md
│   └── WORKFLOW.md
└── runs/
    └── <job>_<timestamp>/
        ├── manifest.json
        ├── core-data.json
        ├── repository-selectors.json
        ├── repository-test-files.json
        ├── repository-metadata.json
        ├── raw-data.json
        ├── evidence-package.json
        ├── jenkins-build-info.json
        ├── console-log.txt
        ├── test-report.json
        ├── environment-status.json
        ├── analysis-results.json
        ├── Detailed-Analysis.md
        └── SUMMARY.txt
```

## Multi-File Data Architecture

Data is split across multiple files to stay under Claude Code's 25,000 token limit:

| File | Tokens | Purpose |
|------|--------|---------|
| manifest.json | ~150 | File index and workflow instructions |
| core-data.json | ~5,500 | Primary data (read first) |
| repository-selectors.json | ~7,500 | Selector lookup (on-demand) |
| repository-test-files.json | ~7,000 | Test file details (on-demand) |
| repository-metadata.json | ~800 | Repo summary (on-demand) |
| raw-data.json | ~200 | Backward compatibility stub |

## Hybrid Classification System

Classification uses a formal decision matrix with cross-reference validation:

1. **Stack Trace Parser** - Extract file:line from error stack traces
2. **Classification Decision Matrix** - Formal rules based on failure_type, env_healthy, selector_found
3. **Confidence Calculator** - 5-factor weighted scoring
4. **Cross-Reference Validator** - Catch and correct misclassifications
5. **Timeline Comparison Service** - Compare git dates between automation and console repos

## Security Features

- **Credential Masking**: PASSWORD, TOKEN, SECRET, KEY patterns masked
- **READ-ONLY Cluster Operations**: Only whitelisted oc/kubectl commands
- **Target Cluster Authentication**: Credentials from Jenkins parameters

## Usage

```bash
# Data gathering
python -m src.scripts.gather "https://jenkins.example.com/job/pipeline/123/"

# Report generation
python -m src.scripts.report runs/<run_dir>

# Full pipeline
python main.py "https://jenkins.example.com/job/pipeline/123/"

# Run tests
python3 -m pytest tests/unit/services/ -v
```
