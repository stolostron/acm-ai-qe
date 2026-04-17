# Z-Stream Pipeline Analysis (v4.0)

Jenkins pipeline failure analysis with definitive PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE classification.

## What This Does

When Jenkins tests fail, you need to know: **Is it a PRODUCT BUG, AUTOMATION BUG, or INFRASTRUCTURE issue?**

This 5-Stage Pipeline provides:
0. **Environment Oracle** (inside gather.py): Feature-aware dependency health & knowledge database
1. **Data Gathering** (`gather.py`): Factual data collection from Jenkins, environment, repositories, and Knowledge Graph
1.5. **Cluster Diagnostic** (`cluster-diagnostic` agent): Comprehensive 6-phase hub-health-style cluster investigation producing `cluster-diagnosis.json`
2. **AI Analysis** (`analysis` agent): 5-phase investigation with diagnostic data, full repo access, and MCP integration
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
STAGE 0:   gather.py              -> cluster_oracle (environment oracle + knowledge database)
STAGE 1:   gather.py              -> core-data.json + cluster.kubeconfig + repos/
STAGE 1.5: cluster-diagnostic     -> cluster-diagnosis.json (6-phase investigation + structured health data)
STAGE 2:   AI Analysis            -> analysis-results.json (12-layer diagnostic investigation)
STAGE 3:   report.py              -> Detailed-Analysis.md + analysis-report.html + per-test-breakdown.json + SUMMARY.txt
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
- Cluster kubeconfig (persisted `cluster.kubeconfig` for Stage 1.5 and Stage 2)

### Stage 1.5: Cluster Diagnostic (v3.6)

Dedicated `cluster-diagnostic` agent performs a comprehensive 6-phase investigation:
- **Phase 1: Discover** — Full cluster inventory (MCH/MCE, ALL CSVs, webhooks, ConsolePlugins, nodes, managed clusters)
- **Phase 2: Learn** — Compare against healthy-baseline.yaml, addon-catalog.yaml, webhook-registry.yaml, diagnostic traps
- **Phase 3: Check** — Per-namespace pod health with baseline comparison, log pattern scanning, restart counts, OCP operator health, infrastructure guards, addon/webhook verification, trap detection
- **Phase 4: Pattern Match** — Cross-reference against failure-patterns.yaml and failure-signatures.md
- **Phase 5: Correlate** — Dependency chain tracing, cross-subsystem impact, env var dependency discovery
- **Phase 6: Output** — Write `cluster-diagnosis.json` + self-healing discoveries to `knowledge/learned/`

Output includes: environment health score (weighted 0.0-1.0), cluster identity, operator health (with replica counts), subsystem health, operator inventory, addon health, webhook status, component log excerpts, restart counts, managed cluster detail, OCP operators, console plugin status, infrastructure issues, dependency chains, baseline comparison, classification guidance, and self-healing discoveries.

### Stage 2: AI Analysis (v4.0 — Structured Diagnostics + Context Signals + 12-Layer Investigation)

Claude Code agent uses the 12-layer diagnostic model to find root causes:
- **Phase A**: Initial assessment (re-auth, feature grounding, environment, patterns, KG context) + **A4: provably linked grouping** — groups by strict code-path criteria only (same selector+function, same before-all hook, same spec+error+line). Dead selectors classified directly, hook cascades as NO_BUG.
- **Phase B**: 12-layer root cause investigation — traces from symptom through infrastructure layers (Compute, Control Plane, Network, Storage, Config, Auth, RBAC, API, Operator, Cross-Cluster, Data Flow, UI) to find broken layer, investigates WHO caused it, then classifies. **Per-test verification** (v3.9): 4-point check (code path, backend, role, element) on each subsequent test in a group; failures split to individual investigation.
- **Phase C**: Cross-reference validation (multi-evidence, cascading failures, pattern correlation)
- **Phase D**: Validation of investigation results against PR signals (PR-6 backend health via cluster-diagnosis.json, PR-6b Polarion expected behavior, PR-7 context signals), **symmetric counterfactual** (D-V5c for AUTOMATION_BUG, D-V5e for PRODUCT_BUG, v4.0), **layer discrepancy detection** (v4.0), expanded counterfactual (D-V5, v3.9: 9 templates), causal link verification (D4b), counter-bias validation (D5). Fallback: 3-path routing when investigation agents unavailable.
- **Phase E**: Feature context and JIRA correlation (Knowledge Graph, feature stories, bug search)

Every test in the output includes `root_cause_layer` (1-12), `root_cause_layer_name`, `investigation_steps_taken`, and `cause_owner`.

### Stage 3: Report Generation

`report.py` formats AI output into reports:
- `analysis-report.html` — interactive HTML report with filters and per-test cards
- `Detailed-Analysis.md` — comprehensive markdown report
- `per-test-breakdown.json` — structured data for tooling
- `SUMMARY.txt` — brief text summary

## Classification Types

**Primary classifications (actively assigned):**

| Classification | Owner | Description |
|----------------|-------|-------------|
| **PRODUCT_BUG** | Product Team | Backend 500 errors, API broken, feature not working, wrong data returned |
| **AUTOMATION_BUG** | Automation Team | Stale selector, wrong assertion, test logic issue, missing wait condition |
| **INFRASTRUCTURE** | Platform Team | Cluster down, VM scheduling failure, pod crashes, resource pressure |
| **NO_BUG** | N/A | Cascading hook failure from a prior test failure -- not an independent issue |

**Edge case classifications (rarely assigned):**

| Classification | Description |
|----------------|-------------|
| **FLAKY** | Passes on retry, intermittent timing failure (requires historical data) |
| **MIXED** | Multiple distinct root causes in same test |
| **UNKNOWN** | Insufficient evidence, confidence below 0.50 |

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
| Foundation | Foundation (addon framework, registration) | — |
| Install | Installation (ACM/MCE operator lifecycle) | — |
| Infrastructure | Infrastructure | Yes |
| RBAC | RBAC & User Management | Yes |
| Automation | Ansible Automation Platform | Yes |

## Knowledge Database

Standalone knowledge database at `knowledge/` with 60 files providing domain
reference data for the diagnostic agent (Stage 1.5) and the AI analysis agent (Stage 2).

| Directory | Content | Files |
|-----------|---------|-------|
| `architecture/` | Per-subsystem architecture, data flow, failure signatures | 37 files across 12 subsystems + 2 platform docs |
| `diagnostics/` | Classification decision tree, evidence tiers, known misclassifications, diagnostic traps, 12-layer diagnostic model | 5 files |
| Root YAML | Components, dependencies, selectors, API endpoints, feature areas, failure patterns, test mapping, healthy baseline, addon catalog, webhook registry, version constraints, prerequisites | 12 files |
| `learned/` | Agent-contributed corrections, patterns, selector changes, operator discoveries | 3+ files (grows via self-healing) |
| `refresh.py` | Updates knowledge from cluster, MCP, KG | 1 script |

Subsystems covered: Search, Console, Governance, Cluster Lifecycle, Virtualization,
Application Lifecycle, RBAC, Automation, Observability, Foundation, Install, Infrastructure.

Each subsystem has `architecture.md` (how it works), `data-flow.md` (where data moves),
and `failure-signatures.md` (known failure patterns with classification guidance).

## Run Directory Structure

```
runs/<job>_<timestamp>/
├── core-data.json              <- Primary data from gather.py (Stage 1)
├── cluster-diagnosis.json      <- Cluster diagnostic output (Stage 1.5)
├── cluster.kubeconfig          <- Persisted cluster auth for Stages 1.5 + 2
├── pipeline.log.jsonl          <- Structured logs from all Python services (Stage 1+3)
├── run-metadata.json           <- Run metadata (timing, version)
├── manifest.json               <- File index
├── console-log.txt             <- Full Jenkins console output
├── jenkins-build-info.json     <- Build metadata
├── test-report.json            <- Per-test failure details
├── environment-status.json     <- Legacy cluster connectivity (deprecated, may not exist)
├── repos/
│   ├── automation/             <- Full cloned automation repo
│   ├── console/                <- Full cloned console repo
│   └── kubevirt-plugin/        <- For VM tests only
├── analysis-results.json       <- AI output (created by agent)
├── Detailed-Analysis.md        <- Report (created by report.py)
├── per-test-breakdown.json     <- Structured data (created by report.py)
├── SUMMARY.txt                 <- Brief summary (created by report.py)
└── feedback.json               <- Classification feedback (optional)

Agent trace logs: .claude/traces/<session_id>.jsonl (MCP calls, prompts, tool use)
```

## Services (17 Active Python Modules)

| Service | Purpose |
|---------|---------|
| `EnvironmentOracleService` | 6-phase feature-aware dependency health & knowledge database (v3.6) |
| `JenkinsIntelligenceService` | Build info extraction, console log parsing, test report analysis |
| `JenkinsAPIClient` | Direct Jenkins REST API client with authentication |
| `EnvironmentValidationService` | Real oc/kubectl cluster validation (READ-ONLY) |
| `RepositoryAnalysisService` | Git clone to run directory, test file indexing |
| `TimelineComparisonService` | Git date comparison between repos, 200-commit selector drift detection |
| `StackTraceParser` | Parse JS/TS stack traces to file:line |
| `ACMConsoleKnowledge` | ACM console directory structure and feature mapping |
| `ACMUIMCPClient` | ACM UI MCP Server integration for element discovery |
| `ComponentExtractor` | Extract backend component names from test failures |
| `KnowledgeGraphClient` | Neo4j RHACM Knowledge Graph queries via HTTP API |
| `ClusterInvestigationService` | Targeted component diagnostics and cluster landscape |
| `FeatureAreaService` | Map tests to feature areas with subsystem context |
| `FeatureKnowledgeService` | Load playbooks, check prerequisites (oracle-aware), match failure paths |
| `FeedbackService` | Classification accuracy tracking and feedback |
| `SchemaValidationService` | JSON Schema validation for analysis results |
| `shared_utils` | Common functions (subprocess, curl, masking, dataclass_to_dict, command validation) |

## MCP Servers

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM-UI | 20 | ACM Console + kubevirt-plugin source code search via GitHub |
| JIRA | 25 | Issue search, creation, management for bug correlation |
| Jenkins | 11 | Pipeline analysis, build monitoring, test results |
| Polarion | 25 | Test case content, setup sections, dependency discovery |
| Knowledge Graph (Neo4j) | 2 | Component dependency analysis via Cypher queries |

Run `bash mcp/setup.sh` from the repo root to configure all servers.

## Tests

```bash
# Unit + regression (664 tests, no external deps):
python -m pytest tests/unit/ tests/regression/ -q

# Integration (requires Jenkins VPN):
python -m pytest tests/integration/ -v --timeout=300

# All tests:
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
| Knowledge database reference | [docs/06-KNOWLEDGE-DATABASE.md](docs/06-KNOWLEDGE-DATABASE.md) |
| Stage 2 agent instructions | [.claude/agents/analysis.md](.claude/agents/analysis.md) |
| Stage 2 investigation agent | [.claude/agents/investigation-agent.md](.claude/agents/investigation-agent.md) |
| Stage 1.5 diagnostic agent | [.claude/agents/cluster-diagnostic.md](.claude/agents/cluster-diagnostic.md) |
