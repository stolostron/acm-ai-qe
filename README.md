# AI Systems Suite

Multi-app repository for Jenkins pipeline analysis and test generation tools, built on Claude Code.

## Applications

### Z-Stream Analysis — Active

`apps/z-stream-analysis/`

Analyzes Jenkins pipeline failures and classifies them as PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, FLAKY, NO_BUG, MIXED, or UNKNOWN.

Three-stage pipeline:
1. **Data Gathering** (`gather.py`) — Fetches Jenkins build data, test reports, console logs, and clones repos
2. **AI Analysis** — 5-phase investigation framework classifies each failed test with multi-evidence validation
3. **Report Generation** (`report.py`) — Produces `Detailed-Analysis.md` with per-test breakdown

```bash
cd apps/z-stream-analysis/

# Gather data from a Jenkins build
python -m src.scripts.gather "<JENKINS_URL>"

# AI analysis writes analysis-results.json (via z-stream-analysis agent)

# Generate reports
python -m src.scripts.report runs/<run_dir>
```

See `apps/z-stream-analysis/CLAUDE.md` for the classification guide and full documentation.

### Claude Test Generator — In Progress

`apps/claude-test-generator/`

Test plan generation from JIRA tickets. Not currently functional.

## MCP Servers

Four MCP servers provide tools during analysis. Run `bash mcp/setup.sh` to configure.

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM UI | 20 | ACM Console and kubevirt-plugin source code search |
| JIRA | 23 | Issue search, creation, and management |
| Neo4j RHACM | 3 | Component dependency analysis (optional) |
| Polarion | 17 | Polarion test case access (optional) |

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- Python 3.10+
- `gh` CLI (authenticated with GitHub)
- `oc` CLI (optional, for cluster validation)
- JIRA PAT (for JIRA MCP server)

## Directory Structure

```
ai_systems_v2/
├── apps/
│   ├── z-stream-analysis/     # Pipeline failure analysis
│   └── claude-test-generator/ # Test generation (in progress)
└── mcp/
    ├── acm-ui/                # ACM UI MCP server
    ├── jira/                  # JIRA MCP server
    ├── neo4j-rhacm/           # Knowledge graph MCP server
    └── polarion/              # Polarion MCP server
```

## Tests

```bash
cd apps/z-stream-analysis/
python -m pytest tests/ -q
```
