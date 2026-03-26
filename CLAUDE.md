# AI Systems Suite

Multi-app repository for Jenkins pipeline analysis and test generation tools.

## Applications

### Z-Stream Analysis (`apps/z-stream-analysis/`) — Active

Jenkins pipeline failure analysis (v3.5) with classification: PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE | FLAKY | NO_BUG | MIXED | UNKNOWN. Includes assertion value extraction, per-feature-area graduated infrastructure scoring, per-test causal link verification, failure mode categorization, blank page pre-routing, hook failure deduplication, temporal evidence routing, feature investigation playbooks, tiered cluster investigation, and classification feedback.

Four-stage pipeline:
0. **Environment Oracle** (inside gather.py) — Feature-aware dependency health & knowledge database (`cluster_oracle`)
1. **gather.py** — Extracts test data from Jenkins (builds `core-data.json` with cluster landscape, backend API probes, and feature grounding; persists `cluster.kubeconfig` for Stage 2)
2. **AI Analysis** — 5-phase investigation with backend cross-check producing `analysis-results.json`
3. **report.py** — Generates `Detailed-Analysis.md` from analysis results

See `apps/z-stream-analysis/CLAUDE.md` for schema requirements, classification guide, and MCP tool reference.

### Claude Test Generator (`apps/claude-test-generator/`) — In Progress

Test plan generation from JIRA tickets. Not currently functional — do not use.

## Running Z-Stream Analysis

Open Claude Code in this repository (root or `apps/z-stream-analysis/`) and ask:

```
Analyze this run: <JENKINS_URL>
```

Claude Code handles the full pipeline automatically — gather, analyze, report.

### Manual Pipeline (Advanced)

```bash
cd apps/z-stream-analysis/

# Stage 1: Gather data
python -m src.scripts.gather "<JENKINS_URL>"
python -m src.scripts.gather "<JENKINS_URL>" --skip-env    # Skip cluster validation
python -m src.scripts.gather "<JENKINS_URL>" --skip-repo   # Skip repo cloning

# Stage 2: AI Analysis
# Read core-data.json, classify each failure using MCP tools
# MUST read src/schemas/analysis_results_schema.json before writing analysis-results.json

# Stage 3: Generate reports
python -m src.scripts.report runs/<run_dir>
```

## MCP Servers (`mcp/`)

Run `bash mcp/setup.sh` from repo root to configure all servers.

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM UI (`mcp/acm-ui-mcp-server/`) | 19 | ACM Console + kubevirt-plugin source code search via GitHub |
| Jenkins (`mcp/jenkins-mcp/`) | 11 | Jenkins pipeline API access for build data extraction |
| JIRA (`mcp/jira-mcp-server/`) | 25 | Issue search, creation, management for bug correlation (Jira Cloud) |
| Neo4j RHACM (`mcp/neo4j-rhacm/`) | 2 | Component dependency analysis via Cypher queries (optional) |
| Polarion (`mcp/polarion/`) | 25 | Polarion test case access (optional) |

**JIRA Cloud Setup:** Create `mcp/jira-mcp-server/.env` from `.env.example` with your Jira Cloud credentials (email + API token). Or run `bash mcp/setup.sh`. Get a token at https://id.atlassian.com/manage-profile/security/api-tokens. See `apps/z-stream-analysis/docs/05-MCP-INTEGRATION.md` for details.

## Directory Structure

```
ai_systems_v2/
├── apps/
│   ├── z-stream-analysis/     # Active — pipeline failure analysis
│   └── claude-test-generator/ # In progress — not functional
└── mcp/
    ├── acm-ui-mcp-server/     # ACM UI MCP server
    ├── jenkins-mcp/           # Jenkins pipeline MCP server
    ├── jira-mcp-server/       # JIRA MCP server
    ├── neo4j-rhacm/           # Knowledge graph MCP server
    └── polarion/              # Polarion MCP server
```

## Tests

```bash
# Z-stream analysis tests (from app directory)
cd apps/z-stream-analysis/

# Fast — unit + regression (602+ tests, no external deps):
python -m pytest tests/unit/ tests/regression/ -q

# Full suite (652+ tests, requires Jenkins VPN for integration):
python -m pytest tests/ -q --timeout=300
```
