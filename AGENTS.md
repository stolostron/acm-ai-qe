# AI Systems Suite — Agent Reference

<!-- This is the tool-agnostic agent reference. For Claude Code-specific instructions,
     see CLAUDE.md. Both files are maintained separately: AGENTS.md omits Claude-specific
     details (settings, slash commands, CodeRabbit) to stay portable across AI tools.
     Per agentic-sdlc convention, some squads symlink AGENTS.md -> CLAUDE.md; this repo
     keeps them separate because CLAUDE.md contains tool-specific configuration. -->

Multi-app repository for ACM quality engineering tools built on Claude Code. **GitHub:** [stolostron/acm-ai-qe](https://github.com/stolostron/acm-ai-qe).

## Build and Test

```bash
# Z-stream analysis (fast suite, 753 tests, no external deps)
cd apps/z-stream-analysis
python -m pytest tests/unit/ tests/regression/ -q

# Full suite (798 tests, requires Jenkins VPN for integration)
python -m pytest tests/ -q --timeout=300

# Hub health (22 regression tests, no external deps)
cd apps/acm-hub-health
python -m pytest tests/regression/ -q

# Test case generator (119 tests, no external deps)
cd apps/test-case-generator
python -m pytest tests/unit/ tests/integration/ -q

# Portable skill eval harness (from repo root)
cd ai_systems_v2
python .claude/skills/acm-test-case-generator/evals/run_evals.py
```

## Setup

From the repo root, launch Claude Code and run the onboarding skill:

```bash
claude
```

```
/onboard
```

This detects your environment, configures MCP servers, prompts for credentials, generates `.mcp.json` for each app, and creates a root `.mcp.json` so portable skills have MCP access from the repo root.

## Architecture

Three applications, each with its own CLAUDE.md, knowledge base, and agent definitions.

### Z-Stream Analysis (`apps/z-stream-analysis/`)

Jenkins pipeline failure analysis. 5-stage pipeline:

1. **Stage 1** `gather.py` — Extracts test data from Jenkins, produces `core-data.json`
2. **Post-Stage 1** `data-collector` agent — Enriches `core-data.json` with selector verification, page objects, timeline analysis
3. **Stage 1.5** `cluster-diagnostic` agent — Cluster health investigation, produces `cluster-diagnosis.json`
4. **Stage 2** `analysis` agent — 12-layer diagnostic investigation, produces `analysis-results.json`
5. **Stage 3** `report.py` — Generates `Detailed-Analysis.md` + HTML report

4 agents in `.claude/agents/`: `analysis.md`, `cluster-diagnostic.md`, `data-collector.md`, `investigation-agent.md`

3 slash commands in `.claude/commands/`: `/analyze`, `/gather`, `/quick`

Classifications: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, NO_BUG, MIXED, UNKNOWN, FLAKY

### ACM Hub Health (`apps/acm-hub-health/`)

Diagnostic agent for ACM hub clusters. Single-agent architecture with 6 diagnostic phases (Discover, Learn, Check, Pattern Match, Correlate, Deep Investigate). Read-only diagnosis; remediation only after explicit approval.

5 slash commands: `/sanity`, `/health-check`, `/deep`, `/investigate`, `/learn`

### Test Case Generator (`apps/test-case-generator/`)

Generates Polarion-ready test cases from JIRA tickets. 6-phase subagent pipeline with 6 specialized agents (each with structured anomaly reporting): feature-investigator, code-change-analyzer (with coverage gap analysis), ui-discovery, live-validator (with environment verification and form-based OAuth browser authentication), test-case-generator, quality-reviewer (with design efficiency and coverage gap verification). report.py includes artifact completeness check (9 expected files). Portable standalone scripts for repo-root execution.

3 skills in `.claude/skills/`: `/generate`, `/review`, `/batch`

## Skills (`.claude/skills/`)

19 portable skills, flat layout. Each has a `SKILL.md` entry point (YAML frontmatter + instructions). Shared skills are stateless tools; orchestrators compose them into pipelines.

| Domain | Skills | Orchestrators |
|--------|--------|---------------|
| Shared | `acm-knowledge-base`, `acm-cluster-health`, `acm-jenkins-client` | — |
| Test Case Gen | `acm-test-case-generator`, `acm-qe-code-analyzer`, `acm-test-case-writer`, `acm-test-case-reviewer` | `/generate`, `/review`, `/batch` |
| Hub Health | `acm-hub-health-check`, `acm-cluster-remediation`, `acm-knowledge-learner` | `/acm-hub-health-check` |
| Z-Stream | `acm-z-stream-analyzer`, `acm-failure-classifier`, `acm-cluster-investigator`, `acm-data-enricher` | `/analyze`, `/gather`, `/quick` |
| Bug Investigation | `acm-bug-hunter`, `acm-bug-fix-verifier` | `/acm-bug-hunter` |
| Utility | `onboard`, `youtube-digest`, `grill-me` | `/onboard` |

See `docs/skill-architecture.md` for blast radius map and `docs/skill-authoring-guide.md` for authoring standards.

## MCP Servers (`mcp/`)

| Server | Tools | Purpose |
|--------|-------|---------|
| ACM Source | 18 | Console + kubevirt-plugin source code search |
| Jenkins | 11 | Pipeline API + ACM analysis tools |
| JIRA | 29 | Issue search, creation, attachments, list/download attachments, inline comment images ([atifshafi/jira-mcp-server@feat/redhat-fields](https://github.com/atifshafi/jira-mcp-server/tree/feat/redhat-fields)) |
| Polarion | 25 | Test case access |
| Neo4j RHACM | 2 | Component dependency graph (optional) |
| ACM Search | 5 | Fleet-wide spoke resource queries |
| ACM Kubectl | 3 | Multicluster kubectl for hub and spoke clusters |
| Playwright | 24 | Browser automation for live UI validation |

Run `/onboard` from Claude Code to configure, or `bash mcp/setup.sh` manually. Use `bash mcp/deploy-acm-search.sh` after `oc login` for ACM Search. External MCPs are cloned into `mcp/.external/` (gitignored).

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
├── .mcp.json                  # Root MCP config for skills (generated by /onboard, gitignored)
├── .claude/
│   ├── skills/                # 19 portable skills (usable from repo root)
│   ├── knowledge/             # Shared knowledge database for skills (3 domains: tc-gen, z-stream, hub-health)
│   ├── commands/pre-push.md   # /pre-push quality gate
│   ├── settings.json          # Root-level Claude Code settings
│   └── statusline.sh          # Status line script (model, branch, context %)
├── apps/
│   ├── z-stream-analysis/     # Pipeline failure analysis
│   ├── acm-hub-health/        # Hub health diagnostic
│   └── test-case-generator/   # Test case generation
├── docs/                      # Cross-app documentation
│   ├── skill-architecture.md  # Skill inventory, blast radius, contributing guide
│   ├── skill-authoring-guide.md # Anthropic-based skill authoring standards
│   ├── acm-bug-hunter/        # Bug hunter implementation spec
│   ├── hub-health/            # Hub health detailed docs
│   ├── test-case-generator/   # TC gen detailed docs (pipeline, agents, quality gates)
│   └── z-stream-analysis/     # Z-stream detailed docs
├── workflows/                 # Named multi-phase processes (user/cron triggered)
├── solutions/                 # Battle-tested SOPs for known problems (agent self-help)
├── repos/
│   └── repos.yaml             # QE repo registry
├── team-members/
│   └── team-members.md        # Console QE squad roster
├── mcp/
│   ├── setup.sh               # Interactive MCP setup
│   ├── deploy-acm-search.sh   # ACM Search MCP deploy (oc login → deploy → .mcp.json)
│   ├── verify.py              # Standalone health checker
│   ├── acm-source-mcp-server/     # ACM Console source search
│   ├── polarion/              # Polarion wrapper
│   └── jenkins-acm-tools.py   # ACM-specific Jenkins tools
├── CLAUDE.md                  # Claude Code instructions (tool-specific; see also this file)
├── AGENTS.md                  # This file (tool-agnostic agent reference)
├── context.md                 # Ubiquitous language glossary + repo design summary (read first for shared terms)
├── README.md                  # User-facing setup and onboarding guide
└── .coderabbit.yaml           # CodeRabbit review config
```
