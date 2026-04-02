# AI Systems Suite

Claude Code-powered tools for ACM (Advanced Cluster Management) quality engineering.

## Apps

| App | What It Does | Status |
|-----|-------------|--------|
| [ACM Hub Health](apps/acm-hub-health/) | Diagnose and remediate ACM hub clusters through natural language. Checks operator health, image integrity, NetworkPolicies, ResourceQuotas, service connectivity, and data integrity. Knowledge database with per-subsystem architecture docs, baselines, webhooks, certs, addons. | Active |
| [Z-Stream Analysis](apps/z-stream-analysis/) | Classify Jenkins pipeline failures (product bug, automation bug, infra) with Environment Oracle and per-subsystem knowledge database (53 files: architecture, data-flow, failure-signatures across 12 ACM subsystems + diagnostics methodology). | Active |
| [Claude Test Generator](apps/claude-test-generator/) | Generate test plans from JIRA tickets | In progress -- not functional |

## Prerequisites

All apps require:
- **Claude Code CLI** -- [install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started)

App-specific:
- **Hub Health**: `oc` CLI logged into an ACM hub cluster. Python 3 + PyYAML only if using `knowledge/refresh.py` (optional).
- **Z-Stream**: Python 3.10+, `oc` CLI, Red Hat VPN (for Jenkins/Polarion), JIRA API token, GitHub CLI (`gh`)

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

Then paste a Jenkins URL:
```
Analyze this run: https://jenkins.example.com/job/pipeline/123/
```

Or run the pipeline manually:
```bash
python -m src.scripts.gather "https://jenkins.example.com/job/pipeline/123/"
# Claude Code performs AI analysis (Stage 2)
python -m src.scripts.report runs/<run_dir>
```

See [apps/z-stream-analysis/README.md](apps/z-stream-analysis/README.md) for full documentation.

## MCP Setup

Both apps use MCP (Model Context Protocol) servers to give Claude Code access to
external tools. The setup script handles everything:

```bash
bash mcp/setup.sh
```

It asks which app you want to configure and only installs the servers that app needs:

| App | MCP Servers Installed |
|-----|----------------------|
| Hub Health | acm-ui |
| Z-Stream | acm-ui, jira, jenkins, polarion, neo4j-rhacm |

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

External MCP servers (JIRA, Jenkins, Knowledge Graph) are cloned automatically by
`setup.sh` into `mcp/.external/` (gitignored). The apps use forks with ACM-specific
fixes on top of the upstream sources:

| Server | Upstream | Fork used by setup.sh | Changes |
|--------|----------|----------------------|---------|
| JIRA | [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server) | [atifshafi/jira-mcp-server](https://github.com/atifshafi/jira-mcp-server) `feat/redhat-fields` | Red Hat field support ([PR#24](https://github.com/stolostron/jira-mcp-server/pull/24)) |
| Jenkins | [redhat-community-ai-tools/jenkins-mcp](https://github.com/redhat-community-ai-tools/jenkins-mcp) | [atifshafi/jenkins-mcp](https://github.com/atifshafi/jenkins-mcp) `fix/auth-logs-paths` | Auth + log path fixes ([PR#13](https://github.com/redhat-community-ai-tools/jenkins-mcp/pull/13)) |
| Neo4j RHACM (KG) | [stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph) | [atifshafi/knowledge-graph](https://github.com/atifshafi/knowledge-graph) `atif-virt-extension` | Virtualization subsystem extension |

This repo contains the MCP servers we created (ACM UI, Polarion wrapper,
Jenkins ACM analysis tools).

## Directory Structure

```
ai_systems_v2/
├── apps/
│   ├── acm-hub-health/        # Hub health diagnostic agent
│   ├── z-stream-analysis/     # Pipeline failure analysis
│   └── claude-test-generator/ # Test plan generation (WIP)
├── mcp/
│   ├── setup.sh               # Interactive setup (clones external MCPs, creates venvs)
│   ├── acm-ui-mcp-server/     # Our code: ACM Console source search
│   ├── polarion/              # Our code: Polarion wrapper
│   ├── jenkins-acm-tools.py   # Our code: 4 ACM-specific Jenkins analysis tools
│   └── .external/             # Cloned at setup time (gitignored)
│       ├── jira-mcp-server/   #   from stolostron/jira-mcp-server
│       ├── jenkins-mcp/       #   from redhat-community-ai-tools/jenkins-mcp
│       └── knowledge-graph/   #   from stolostron/knowledge-graph
├── CLAUDE.md                  # Claude Code agent instructions
└── README.md                  # This file
```

## Tests

```bash
cd apps/z-stream-analysis/

# Fast -- unit + regression (667+ tests, no external deps)
python -m pytest tests/unit/ tests/regression/ -q

# Full suite (717+ tests, requires Jenkins VPN for integration)
python -m pytest tests/ -q --timeout=300
```
