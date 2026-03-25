# Z-Stream Pipeline Analysis (v3.3)

Jenkins pipeline failure analysis with definitive PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE classification.

## What This Does

When Jenkins tests fail, you need to know: **Is it a PRODUCT BUG, AUTOMATION BUG, or INFRASTRUCTURE issue?**

This 3-Stage Pipeline provides:
1. **Data Gathering** (`gather.py`): Factual data collection from Jenkins, environment, repositories, and Knowledge Graph
2. **AI Analysis** (Claude Code agent): 5-phase investigation with full repo access and MCP integration
3. **Report Generation** (`report.py`): Human-readable reports from AI analysis

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

Or in Claude Code, just say:
```
Analyze this run: <JENKINS_URL>
```

## Architecture

```
STAGE 1: gather.py    -> core-data.json + repos/
STAGE 2: AI Analysis  -> analysis-results.json (5-phase investigation)
STAGE 3: report.py    -> Detailed-Analysis.md + per-test-breakdown.json + SUMMARY.txt
```

### Stage 1: Data Gathering

`gather.py` collects factual data without classification:
- Jenkins build info, console log, test report
- Environment validation (cluster connectivity, API health)
- Repository cloning (automation, console, kubevirt-plugin)
- Context extraction (test code, page objects, selector search)
- Feature grounding (tests grouped by feature area with subsystem context)
- Cluster landscape (managed clusters, operator statuses, resource pressure)
- Backend API probing (5 console endpoints validated against cluster state)
- Feature knowledge (playbook-driven prerequisites, failure paths, KG dependency context)
- Temporal evidence (git timeline comparison between product and test changes)
- Cluster credentials (persisted for Stage 2 re-authentication)

### Stage 2: AI Analysis

Claude Code agent performs 5-phase investigation:
- **Phase A**: Initial assessment (re-auth, feature grounding, environment, patterns, KG context)
- **Phase B**: Deep investigation per test (extracted context, timeline, console, MCP, backend cross-check, tiered playbook investigation)
- **Phase C**: Cross-reference validation (multi-evidence, cascading failures, pattern correlation)
- **Phase D**: Classification routing with pre-checks (blank page, hook dedup, temporal evidence, data assertion) then 3-path routing (selector -> Path A, timeout -> Path B1 with graduated health scoring, else -> Path B2 JIRA investigation) then causal link verification and counter-bias validation
- **Phase E**: Feature context and JIRA correlation (Knowledge Graph, feature stories, bug search)

### Stage 3: Report Generation

`report.py` formats AI output into reports:
- `Detailed-Analysis.md` — comprehensive markdown report
- `per-test-breakdown.json` — structured data for tooling
- `SUMMARY.txt` — brief text summary

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

## Feature Areas

| Area | Subsystem | Playbook |
|------|-----------|----------|
| GRC | Governance | Yes |
| Search | Search | Yes |
| CLC | Cluster Lifecycle | Yes |
| Observability | Observability | Yes |
| Virtualization | Virtualization | Yes |
| Application | Application Lifecycle | Yes |
| Console | Console | Yes |
| Infrastructure | Infrastructure | Yes |
| RBAC | RBAC & User Management | Yes |
| Automation | Ansible Automation Platform | Yes |

## Run Directory Structure

```
runs/<job>_<timestamp>/
├── core-data.json              <- Primary data for AI (read first)
├── run-metadata.json           <- Run metadata (timing, version)
├── manifest.json               <- File index
├── console-log.txt             <- Full Jenkins console output
├── jenkins-build-info.json     <- Build metadata
├── test-report.json            <- Per-test failure details
├── environment-status.json     <- Cluster health
├── element-inventory.json      <- MCP element locations (if available)
├── repos/
│   ├── automation/             <- Full cloned automation repo
│   ├── console/                <- Full cloned console repo
│   └── kubevirt-plugin/        <- For VM tests only
├── analysis-results.json       <- AI output (created by agent)
├── Detailed-Analysis.md        <- Report (created by report.py)
├── per-test-breakdown.json     <- Structured data (created by report.py)
├── SUMMARY.txt                 <- Brief summary (created by report.py)
└── feedback.json               <- Classification feedback (optional)
```

## Services (16 Python Modules)

| Service | Purpose |
|---------|---------|
| `JenkinsIntelligenceService` | Build info extraction, console log parsing, test report analysis |
| `JenkinsAPIClient` | Direct Jenkins REST API client with authentication |
| `EnvironmentValidationService` | Real oc/kubectl cluster validation (READ-ONLY) |
| `RepositoryAnalysisService` | Git clone to run directory, test file indexing |
| `TimelineComparisonService` | Git date comparison between repos |
| `StackTraceParser` | Parse JS/TS stack traces to file:line |
| `ACMConsoleKnowledge` | ACM console directory structure and feature mapping |
| `ACMUIMCPClient` | ACM UI MCP Server integration for element discovery |
| `ComponentExtractor` | Extract backend component names from test failures |
| `KnowledgeGraphClient` | Neo4j RHACM Knowledge Graph queries via HTTP API |
| `ClusterInvestigationService` | Targeted component diagnostics and cluster landscape |
| `FeatureAreaService` | Map tests to feature areas with subsystem context |
| `FeatureKnowledgeService` | Load playbooks, check prerequisites, match failure paths |
| `FeedbackService` | Classification accuracy tracking and feedback |
| `SchemaValidationService` | JSON Schema validation for analysis results |
| `shared_utils` | Common functions (subprocess, curl, masking, dataclass_to_dict, command validation) |

## MCP Servers

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM-UI | 20 | ACM Console + kubevirt-plugin source code search via GitHub |
| JIRA | 25 | Issue search, creation, management for bug correlation |
| Knowledge Graph (Neo4j) | 3 | Component dependency analysis via Cypher queries |

Run `bash mcp/setup.sh` from the repo root to configure all servers.

## Tests

```bash
# Unit + regression (515 tests, no external deps):
python -m pytest tests/unit/ tests/regression/ -q

# Integration (requires Jenkins VPN, 50 tests):
python -m pytest tests/integration/ -v --timeout=300

# All tests (565 total):
python -m pytest tests/ -q --timeout=300
```

## CLI Options

```bash
python -m src.scripts.gather <url>               # Standard gather
python -m src.scripts.gather <url> --skip-env     # Skip cluster validation
python -m src.scripts.gather <url> --skip-repo    # Skip repository cloning
python -m src.scripts.report <dir>                # Generate reports
python -m src.scripts.report <dir> --keep-repos   # Don't cleanup repos/
python -m src.scripts.feedback <dir> --test "name" --correct
python -m src.scripts.feedback <dir> --test "name" --incorrect --should-be PRODUCT_BUG
python -m src.scripts.feedback --stats
```

## Configuration

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `JENKINS_USER` | Jenkins username for API authentication |
| `JENKINS_API_TOKEN` | Jenkins API token |
| `Z_STREAM_CONSOLE_REPO_URL` | Override console repository URL |
| `Z_STREAM_KUBEVIRT_REPO_URL` | Override kubevirt-plugin repository URL |
| `NEO4J_HTTP_URL` | Neo4j HTTP API URL (default: `http://localhost:7474`) |
| `NEO4J_USER` | Neo4j username (default: `neo4j`) |
| `NEO4J_PASSWORD` | Neo4j password (default: `rhacmgraph`) |

## Documentation

| Topic | File |
|-------|------|
| Classification guide & pipeline overview | [CLAUDE.md](CLAUDE.md) |
| Pipeline overview & version history | [docs/00-OVERVIEW.md](docs/00-OVERVIEW.md) |
| Stage 1: Data gathering | [docs/01-STAGE1-DATA-GATHERING.md](docs/01-STAGE1-DATA-GATHERING.md) |
| Stage 2: AI analysis | [docs/02-STAGE2-AI-ANALYSIS.md](docs/02-STAGE2-AI-ANALYSIS.md) |
| Stage 3: Report generation | [docs/03-STAGE3-REPORT-GENERATION.md](docs/03-STAGE3-REPORT-GENERATION.md) |
| Services reference | [docs/04-SERVICES-REFERENCE.md](docs/04-SERVICES-REFERENCE.md) |
| MCP integration guide | [docs/05-MCP-INTEGRATION.md](docs/05-MCP-INTEGRATION.md) |
| Agent instructions | [.claude/agents/z-stream-analysis.md](.claude/agents/z-stream-analysis.md) |
