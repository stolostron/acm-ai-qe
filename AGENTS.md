# AI Systems Suite — Agent Reference

Multi-app repository for ACM quality engineering tools built on Claude Code.

## Build and Test

```bash
# Z-stream analysis (fast suite, 703 tests, no external deps)
cd apps/z-stream-analysis
python -m pytest tests/unit/ tests/regression/ -q

# Full suite (748 tests, requires Jenkins VPN for integration)
python -m pytest tests/ -q --timeout=300
```

## Setup

From the repo root, launch Claude Code and run the onboarding skill:

```bash
claude
```

```
/onboard
```

This detects your environment, configures MCP servers, prompts for credentials, and generates `.mcp.json` for each app.

## Architecture

Three applications, each with its own CLAUDE.md, knowledge base, and agent definitions.

### Z-Stream Analysis (`apps/z-stream-analysis/`)

Jenkins pipeline failure analysis. 5-stage pipeline:

1. **Stage 1** `gather.py` — Extracts test data from Jenkins, produces `core-data.json`
2. **Stage 1.5** `cluster-diagnostic` agent — Cluster health investigation, produces `cluster-diagnosis.json`
3. **Stage 1.5** `data-collector` agent — Enriches `core-data.json` with selector verification
4. **Stage 2** `analysis` agent — 12-layer diagnostic investigation, produces `analysis-results.json`
5. **Stage 3** `report.py` — Generates `Detailed-Analysis.md` + HTML report

4 agents in `.claude/agents/`: `analysis.md`, `cluster-diagnostic.md`, `data-collector.md`, `investigation-agent.md`

3 slash commands in `.claude/commands/`: `/analyze`, `/gather`, `/quick`

Classifications: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, NO_BUG, MIXED, UNKNOWN, FLAKY

### ACM Hub Health (`apps/acm-hub-health/`)

Diagnostic agent for ACM hub clusters. Single-agent architecture with 6 diagnostic phases (Discover, Learn, Check, Pattern Match, Correlate, Deep Investigate). Read-only diagnosis; remediation only after explicit approval.

5 slash commands: `/sanity`, `/health-check`, `/deep`, `/investigate`, `/learn`

### Test Case Generator (`apps/test-case-generator/`)

Generates Polarion-ready test cases from JIRA tickets. 6-phase subagent pipeline with 6 specialized agents: feature-investigator, code-change-analyzer, ui-discovery, live-validator, test-case-generator, quality-reviewer.

3 slash commands: `/generate`, `/review`, `/batch`

## MCP Servers (`mcp/`)

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM UI | 20 | Console + kubevirt-plugin source code search |
| Jenkins | 11 | Pipeline API + ACM analysis tools |
| JIRA | 25 | Issue search, creation, management |
| Polarion | 25 | Test case access |
| Neo4j RHACM | 2 | Component dependency graph (optional) |
| ACM Search | 5 | Fleet-wide spoke resource queries |
| ACM Kubectl | 3 | Multicluster kubectl for hub and spoke clusters |
| Playwright | 24 | Browser automation for live UI validation |

Run `bash mcp/setup.sh` to configure. External MCPs are cloned into `mcp/.external/` (gitignored).

## Code Conventions

- **Python services**: `src/services/` — one module per concern, dataclass models
- **Knowledge files**: `knowledge/` — YAML for structured data, markdown for architecture docs
- **Agent definitions**: `.claude/agents/*.md` — YAML frontmatter (`name`, `description`, `tools`) + markdown instructions
- **Feature playbooks**: `src/data/feature_playbooks/` — `base.yaml` + version overlays (`acm-{version}.yaml`), deep-merged at load time
- **Session tracing**: `.claude/hooks/agent_trace.py` — JSONL traces in `.claude/traces/`

## Known Gotchas

- **VPN required** for integration tests (Jenkins access)
- **MCP setup required** before first run (run `/onboard` in Claude Code from the repo root)
- **Neo4j optional** — Podman container `neo4j-rhacm` auto-starts if available
- **Cluster access** — z-stream Stage 1.5 and hub-health require `oc login` to a hub cluster
- **Version overlays** — playbook overlays deep-merge by `id` field; new IDs append, matching IDs replace

## Directory Structure

```
ai_systems_v2/
├── apps/
│   ├── z-stream-analysis/     # Pipeline failure analysis
│   ├── acm-hub-health/        # Hub health diagnostic
│   └── test-case-generator/   # Test case generation
├── mcp/
│   ├── setup.sh               # Interactive MCP setup
│   ├── verify.py              # Standalone health checker
│   ├── acm-ui-mcp-server/     # ACM Console source search
│   ├── polarion/              # Polarion wrapper
│   └── jenkins-acm-tools.py   # ACM-specific Jenkins tools
├── CLAUDE.md                  # Claude Code instructions
├── AGENTS.md                  # This file
└── .coderabbit.yaml           # CodeRabbit review config
```
