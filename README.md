# AI Systems Suite

Claude Code-powered tools for ACM (Advanced Cluster Management) quality engineering.

## Apps

| App | What It Does | Status |
|-----|-------------|--------|
| [ACM Hub Health](apps/acm-hub-health/) | Diagnose and remediate ACM hub clusters through natural language. 6-phase pipeline with 12-layer diagnostic model: layer-organized health checks (foundational layers first), horizontal dependency chain tracing + vertical layer tracing, layer-based fallback for unknown issues. 59 knowledge files (architecture, diagnostics, baselines, webhooks, certs, addons, version constraints, 14 diagnostic traps, 12 dependency chains). Session tracing via Claude Code hooks (JSONL traces with oc command parsing, MCP tracking, phase inference, mutation detection). | Active |
| [Z-Stream Analysis](apps/z-stream-analysis/) | Classify Jenkins pipeline failures (product bug, automation bug, infra) using 12-layer diagnostic investigation (v4.0) with root-cause-first analysis. Stage 1.5 cluster-diagnostic agent produces structured health data (environment_health_score, operator_health, health_depth). v4.0 adds context signals (PR-7), Polarion expected-behavior check (PR-6b), symmetric counterfactual (D-V5c/D-V5e), and layer discrepancy detection. Environment Oracle, per-group investigation agents, and knowledge database (61 files: architecture, data-flow, failure-signatures across 12 ACM subsystems + diagnostics methodology including 12-layer model + healthy baselines + addon catalog + webhook registry + diagnostic traps + learned patterns). | Active |
| [Test Case Generator](apps/test-case-generator/) | Generate Polarion-ready test cases from JIRA tickets. 6-phase subagent pipeline: deterministic data gathering (gh CLI), parallel AI investigation (3 subagents: feature-investigator, code-change-analyzer, ui-discovery), synthesis with scope gating and AC cross-referencing, optional live validation (browser + oc + acm-search + acm-kubectl), AI-powered test case writing, mandatory quality review gate (AC vs implementation, scope alignment, numeric thresholds), and deterministic report/validation with Polarion HTML output. 6 specialized agents, 7 MCP integrations (JIRA, Polarion, ACM UI, Neo4j, ACM Search, ACM Kubectl, Playwright). Supports 9 console areas (Governance, RBAC, Fleet Virt, CCLM, MTV, Clusters, Search, Applications, Credentials). Session tracing via Claude Code hooks. | Active |

## Quick Start (Recommended)

```bash
git clone <repo-url>
cd ai_systems_v2
claude
```

Then type `/onboard` -- the interactive setup detects your environment, explains the apps, and guides MCP server configuration with credential setup.

## Prerequisites

All apps require:
- **Claude Code CLI** -- [install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started)

App-specific:
- **Hub Health**: `oc` CLI logged into an ACM hub cluster. Node.js + `mcp-remote` (`npm install -g mcp-remote`) for the acm-search MCP server. Podman for Neo4j knowledge graph container (optional but recommended). Python 3 + PyYAML only if using `knowledge/refresh.py` (optional).
- **Z-Stream**: Python 3.10+, `oc` CLI, Red Hat VPN (for Jenkins/Polarion), JIRA API token, GitHub CLI (`gh`)
- **Test Case Generator**: Python 3.10+, GitHub CLI (`gh`), JIRA API token, Red Hat VPN (for Polarion), Node.js 18+ (for acm-kubectl and playwright live validation MCPs)

## Quick Start: ACM Hub Health Agent

Diagnose your ACM hub cluster -- health checks, deep investigations, root cause analysis.
No Python scripts to run. Just Claude Code + `oc` + natural language.

```bash
# 1. Clone the repo
git clone <repo-url>
cd ai_systems_v2/apps/acm-hub-health

# 2. One-time setup (clones rhacm-docs, sets up MCP)
bash setup.sh

# 3. Log into your hub
oc login https://api.my-hub.example.com:6443 -u admin -p ...

# 4. Start the agent
claude
```

Then use slash commands or natural language:
```
/sanity                              # Quick pulse check (~30s)
/health-check                        # Standard health check (~2-3 min)
/deep                                # Full deep audit (~5-10 min)
/investigate observability           # Deep dive into a subsystem
Why are my managed clusters Unknown? # Natural language works too
```

See [apps/acm-hub-health/README.md](apps/acm-hub-health/README.md) for full documentation.

## Quick Start: Z-Stream Pipeline Analysis

Classify Jenkins test failures as PRODUCT_BUG, AUTOMATION_BUG, or INFRASTRUCTURE.

```bash
# 1. Clone the repo
git clone <repo-url>
cd ai_systems_v2

# 2. Set up MCP servers
#    Select option 2 (Z-Stream Pipeline Analysis) when prompted
#    You'll be asked for JIRA, Jenkins, and Polarion credentials
bash mcp/setup.sh

# 3. Start Claude Code
cd apps/z-stream-analysis
claude
```

Then use the slash command:
```
/analyze https://jenkins.example.com/job/pipeline/123/
```

Other commands: `/gather <URL>` (Stage 1 only), `/quick <URL>` (skip cluster diagnostic).

Or run the pipeline manually:
```bash
python -m src.scripts.gather "https://jenkins.example.com/job/pipeline/123/"
# Claude Code performs 12-layer diagnostic analysis (Stage 2)
python -m src.scripts.report runs/<run_dir>
```

See [apps/z-stream-analysis/README.md](apps/z-stream-analysis/README.md) for full documentation.

## Quick Start: Test Case Generator

Generate Polarion-ready test cases from JIRA tickets.

```bash
# 1. Clone the repo
git clone <repo-url>
cd ai_systems_v2

# 2. Set up MCP servers
#    Select option 3 (Test Case Generator) when prompted
#    You'll be asked for JIRA and Polarion credentials
bash mcp/setup.sh

# 3. Start Claude Code
cd apps/test-case-generator
claude
```

Then use the slash command:
```
/generate ACM-30459
```

Or run the pipeline manually:
```bash
python -m src.scripts.gather ACM-30459 --version 2.17
# Claude Code performs Phases 1-4.5: investigation + generation + quality review
python -m src.scripts.report runs/ACM-30459/<run-dir>
```

See [apps/test-case-generator/README.md](apps/test-case-generator/README.md) for setup and usage, [docs/](apps/test-case-generator/docs/) for detailed documentation.

## MCP Setup

All three apps use MCP (Model Context Protocol) servers to give Claude Code access to
external tools. The setup script handles everything:

```bash
bash mcp/setup.sh
```

It asks which app you want to configure and only installs the servers that app needs:

| App | MCP Servers Installed |
|-----|----------------------|
| Hub Health | acm-ui, neo4j-rhacm, acm-search |
| Z-Stream | acm-ui, jira, jenkins, polarion, neo4j-rhacm |
| Test Case Generator | acm-ui, jira, polarion, neo4j-rhacm, acm-search, acm-kubectl, playwright |

Credentials are prompted only for the servers being installed. Press Enter to skip
any you don't have yet -- placeholder files are created that you can fill in later.

### MCP Server Reference

| Server | Tools | Source | Purpose |
|--------|-------|--------|---------|
| ACM UI | 20 | This repo | ACM Console + kubevirt-plugin source code search via GitHub |
| Jenkins | 11 | [redhat-community-ai-tools/jenkins-mcp](https://github.com/redhat-community-ai-tools/jenkins-mcp) | Jenkins pipeline API access for build data extraction |
| JIRA | 25 | [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server) | Issue search, creation, management for bug correlation |
| Polarion | 25 | This repo | Polarion test case access (Red Hat VPN required) |
| Neo4j RHACM (KG) | 2 | [stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph) | ACM component dependency analysis via Cypher queries |
| ACM Search | 5 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | Fleet-wide resource queries via search-postgres (spoke-side visibility) |
| ACM Kubectl | 3 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | Multicluster kubectl (list clusters, run commands on hub/spokes) |
| Playwright | 24 | [@playwright/mcp](https://www.npmjs.com/package/@playwright/mcp) (npm) | Browser automation for live UI validation |

External MCP servers (JIRA, Jenkins, Knowledge Graph, ACM Search) are cloned
automatically by `setup.sh` into `mcp/.external/` (gitignored). Most use forks with
ACM-specific fixes on top of the upstream sources:

| Server | Upstream | Fork used by setup.sh | Changes |
|--------|----------|----------------------|---------|
| JIRA | [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server) | [atifshafi/jira-mcp-server](https://github.com/atifshafi/jira-mcp-server) `feat/redhat-fields` | Red Hat field support ([PR#24](https://github.com/stolostron/jira-mcp-server/pull/24)) |
| Jenkins | [redhat-community-ai-tools/jenkins-mcp](https://github.com/redhat-community-ai-tools/jenkins-mcp) | [atifshafi/jenkins-mcp](https://github.com/atifshafi/jenkins-mcp) `fix/auth-logs-paths` | Auth + log path fixes ([PR#13](https://github.com/redhat-community-ai-tools/jenkins-mcp/pull/13)) |
| Neo4j RHACM (KG) | [stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph) | [atifshafi/knowledge-graph](https://github.com/atifshafi/knowledge-graph) `atif-depth-improvements` | Virtualization, Hive, Klusterlet, Addon Framework, HyperShift + depth improvements |
| ACM Search | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | upstream `main` (no fork needed) | PostgreSQL search database access for fleet-wide resource queries |

This repo contains the MCP servers we created (ACM UI, Polarion wrapper,
Jenkins ACM analysis tools).

## Directory Structure

```
ai_systems_v2/
├── apps/
│   ├── acm-hub-health/        # Hub health diagnostic agent
│   ├── z-stream-analysis/     # Pipeline failure analysis
│   └── test-case-generator/   # Polarion-ready test case generation from JIRA
├── mcp/
│   ├── setup.sh               # Interactive setup (clones external MCPs, creates venvs)
│   ├── acm-ui-mcp-server/     # Our code: ACM Console source search
│   ├── polarion/              # Our code: Polarion wrapper
│   ├── jenkins-acm-tools.py   # Our code: 4 ACM-specific Jenkins analysis tools
│   └── .external/             # Cloned at setup time (gitignored)
│       ├── jira-mcp-server/   #   from stolostron/jira-mcp-server
│       ├── jenkins-mcp/       #   from redhat-community-ai-tools/jenkins-mcp
│       ├── knowledge-graph/   #   from stolostron/knowledge-graph
│       └── acm-mcp-server/    #   from stolostron/acm-mcp-server
├── AGENTS.md                  # Agent reference (tool-agnostic, for external AI tools)
├── CLAUDE.md                  # Claude Code agent instructions
└── README.md                  # This file
```

## Tests

```bash
cd apps/z-stream-analysis/

# Fast -- unit + regression (719 tests, no external deps)
python -m pytest tests/unit/ tests/regression/ -q

# Full suite (769+ tests, requires Jenkins VPN for integration)
python -m pytest tests/ -q --timeout=300
```
