# AI Systems Suite

Multi-app repository for Jenkins pipeline analysis and test generation tools.

## Applications

### Z-Stream Analysis (`apps/z-stream-analysis/`) — Active

Jenkins pipeline failure analysis with classification: PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE | FLAKY | NO_BUG | MIXED | UNKNOWN.

Three-stage pipeline:
1. **gather.py** — Extracts test data from Jenkins (builds `core-data.json`)
2. **AI Analysis** — 5-phase investigation producing `analysis-results.json`
3. **report.py** — Generates `Detailed-Analysis.md` from analysis results

See `apps/z-stream-analysis/CLAUDE.md` for schema requirements, classification guide, and MCP tool reference.

### Claude Test Generator (`apps/claude-test-generator/`) — In Progress

Test plan generation from JIRA tickets. Not currently functional — do not use.

## Running Z-Stream Analysis

Z-stream can be run from this root directory. All commands must execute from the app directory:

```bash
cd apps/z-stream-analysis/

# Stage 1: Gather data
python -m src.scripts.gather "<JENKINS_URL>"
python -m src.scripts.gather "<JENKINS_URL>" --skip-env    # Skip cluster validation
python -m src.scripts.gather "<JENKINS_URL>" --skip-repo   # Skip repo cloning

# Stage 2: AI Analysis
# Use the z-stream-analysis agent, or manually read core-data.json and write analysis-results.json
# MUST read src/schemas/analysis_results_schema.json before writing analysis-results.json

# Stage 3: Generate reports
python -m src.scripts.report runs/<run_dir>
```

The `z-stream-analysis` agent (`.claude/agents/z-stream-analysis.md`) handles the full pipeline when given a Jenkins URL.

## MCP Servers (`mcp/`)

Run `bash mcp/setup.sh` from repo root to configure all servers.

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM UI (`mcp/acm-ui/`) | 20 | ACM Console + kubevirt-plugin source code search via GitHub |
| JIRA (`mcp/jira/`) | 23 | Issue search, creation, management for bug correlation |
| Neo4j RHACM (`mcp/neo4j-rhacm/`) | 3 | Component dependency analysis via Cypher queries (optional) |
| Polarion (`mcp/polarion/`) | 17 | Polarion test case access (optional) |

## Directory Structure

```
ai_systems_v2/
├── apps/
│   ├── z-stream-analysis/     # Active — pipeline failure analysis
│   └── claude-test-generator/ # In progress — not functional
└── mcp/
    ├── acm-ui/                # ACM UI MCP server
    ├── jira/                  # JIRA MCP server
    ├── neo4j-rhacm/           # Knowledge graph MCP server
    └── polarion/              # Polarion MCP server
```

## Tests

```bash
# Z-stream analysis tests (from app directory)
cd apps/z-stream-analysis/ && python -m pytest tests/ -q
```
