# Z-Stream Pipeline Analysis (v2.5)

> **Enterprise Jenkins Pipeline Failure Analysis with 5-Phase Investigation Framework and 286 Unit Tests**

## What This Does

When Jenkins tests fail, you need to know: **Is it a PRODUCT BUG, AUTOMATION BUG, or INFRASTRUCTURE issue?**

This **3-Stage Pipeline** provides:
1. **Data Gathering** (gather.py): Factual data collection from Jenkins, environment, and repositories
2. **AI Analysis** (Claude Code agent): 5-phase investigation with full repo access and MCP integration
3. **Report Generation** (report.py): Human-readable reports from AI analysis

**Result:** Definitive verdicts with evidence-based classification in < 5 minutes.

## Quick Start

```bash
cd apps/z-stream-analysis

# Step 1: Gather data from Jenkins
python -m src.scripts.gather "https://jenkins.example.com/job/pipeline/123/"

# Step 2: AI Analysis (Claude Code agent reads core-data.json, investigates repos/)
# The agent creates analysis-results.json with classifications

# Step 3: Generate reports
python -m src.scripts.report runs/<run_dir>
```

## Architecture Overview (v2.5)

```
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 1: DATA GATHERING (gather.py)                                │
│  Script collects FACTUAL DATA + clones FULL REPOS for AI access     │
│  ├── Jenkins: build info, parameters, result                        │
│  ├── Console Log: error lines, patterns                             │
│  ├── Test Report: test name, error, stack trace, duration           │
│  ├── Environment: cluster accessible? API responding?               │
│  ├── Repositories: FULL CLONE to runs/<dir>/repos/                  │
│  ├── Context Extraction: test code, page objects, console search    │
│  ├── MCP Integration (optional): element-inventory.json             │
│  └── Investigation Hints: pointers to failed test files, selectors  │
│                                                                     │
│  Output: core-data.json + element-inventory.json (if MCP available) │
│          + repos/automation/ + repos/console/ + repos/kubevirt/     │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 2: AI ANALYSIS (Claude Code Agent)                           │
│  5-Phase Investigation with repo access and MCP tools               │
│  ├── Phase A: Initial Assessment (environment, patterns)            │
│  ├── Phase B: Deep Investigation (per-test, 6 steps)                │
│  ├── Phase C: Cross-Reference Validation (2+ evidence sources)      │
│  ├── Phase D: Classification (3-path routing)                       │
│  └── Phase E: Feature Context & JIRA Correlation (7 steps)          │
│                                                                     │
│  Output: analysis-results.json (classifications + reasoning)        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  STAGE 3: REPORT GENERATION (report.py)                             │
│  Script formats AI output into human-readable reports               │
│  ├── Parse analysis-results.json                                    │
│  ├── Generate Detailed-Analysis.md                                  │
│  └── Generate SUMMARY.txt                                           │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Design Principle:** Services provide FACTUAL DATA only. All classification is performed by AI during the analysis phase.

## Classification Types

| Classification | Owner | Description |
|----------------|-------|-------------|
| **PRODUCT_BUG** | Product Team | Backend 500 errors, API broken, feature not working |
| **AUTOMATION_BUG** | Automation Team | Selector not found, timeout on wait, test logic wrong |
| **INFRASTRUCTURE** | Platform Team | Cluster down, network errors, provisioning failed |
| **MIXED** | Multiple | Multiple distinct root causes in same run |
| **UNKNOWN** | TBD | Insufficient evidence, needs manual investigation |
| **FLAKY** | Automation Team | Passes on retry, intermittent timing failure |
| **NO_BUG** | N/A | Expected failure from intentional product change |

## Run Directory Structure

```
runs/<job>_<timestamp>/
├── core-data.json              ← Primary data for AI (read first)
├── element-inventory.json      ← MCP element locations (if available)
├── repos/
│   ├── automation/             ← Full cloned automation repo
│   ├── console/                ← Full cloned console repo
│   └── kubevirt-plugin/        ← For VM tests only
├── analysis-results.json       ← AI output (created by agent)
├── Detailed-Analysis.md        ← Report (created by report.py)
└── SUMMARY.txt                 ← Report (created by report.py)
```

## Services Layer (12 Python Services)

| Service | Purpose |
|---------|---------|
| `JenkinsIntelligenceService` | Build info extraction, console log parsing, test report analysis |
| `JenkinsAPIClient` | Direct Jenkins REST API client with authentication |
| `ACMUIMCPClient` | ACM UI MCP Server integration for element discovery |
| `EnvironmentValidationService` | Real oc/kubectl cluster validation (READ-ONLY) |
| `RepositoryAnalysisService` | Git clone to run directory, test file indexing |
| `TimelineComparisonService` | Git date comparison between repos |
| `StackTraceParser` | Parse JS/TS stack traces to file:line |
| `ACMConsoleKnowledge` | ACM console directory structure and feature mapping |
| `ComponentExtractor` | Extract backend component names from test failures |
| `KnowledgeGraphClient` | Neo4j RHACM Knowledge Graph integration |
| `SchemaValidationService` | JSON Schema validation for analysis results |
| `SharedUtils` | Common functions (subprocess, curl, masking) |

## Test Coverage

- **286 unit tests** across 9 test files
- **100% pass rate** with comprehensive edge case coverage

```bash
# Run all tests
python -m pytest tests/unit/ -v

# Run specific test file
python -m pytest tests/unit/services/test_acm_ui_mcp_client.py -v
```

## Configuration

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `JENKINS_USER` | Jenkins username for API authentication |
| `JENKINS_API_TOKEN` | Jenkins API token |
| `Z_STREAM_CONSOLE_REPO_URL` | Override console repository URL |
| `Z_STREAM_KUBEVIRT_REPO_URL` | Override kubevirt-plugin repository URL |

### MCP Integration (Optional)

When ACM UI MCP Server is configured, additional capabilities are available:
- CNV version detection from cluster
- Fleet Virtualization selector inventory
- Pre-computed element locations

## Key Principle

**Don't guess. Investigate.**

The AI has full repo access - use it to understand exactly what went wrong before classifying. Read the actual test code, trace the imports, search for elements, check git history.

A thorough investigation beats a quick guess every time.

## Documentation

See [CLAUDE.md](CLAUDE.md) for comprehensive documentation including:
- Detailed workflow instructions
- Classification guide
- MCP integration details
- ACM console directory structure
- KubeVirt plugin integration
