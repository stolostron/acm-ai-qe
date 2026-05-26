<div align="center">

# AI Systems Suite

**AI-powered quality engineering tools for ACM, built on Claude Code.**


</div>

---

## Get Started

```bash
git clone https://github.com/stolostron/acm-ai-qe.git ai_systems_v2
cd ai_systems_v2
claude
```

```
/onboard
```

The onboarding skill detects your environment, walks you through MCP server setup and credentials, and gets you ready to run any workflow.

> [!TIP]
> `/onboard` is idempotent -- run it again anytime to check what's configured and what's missing.

## Skills

19 portable skills available from the repo root -- just launch `claude` and ask in natural language.

### Primary Workflows

| Skill | What It Does | Try It |
|-------|-------------|--------|
| **Test Case Generator** | Generates Polarion-ready test cases from JIRA tickets. 9-phase pipeline: JIRA investigation, PR analysis, UI discovery, synthesis, optional live validation, writing, and mandatory quality review. | `"Generate a test case for ACM-30459"` |
| **Z-Stream Analyzer** | Classifies Jenkins pipeline test failures as PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or NO_BUG. 4-stage pipeline with data gathering, cluster diagnostics, 12-layer AI classification, and report generation. | `"Analyze this run: <JENKINS_URL>"` |
| **Hub Health Check** | Diagnoses ACM hub cluster health using a 6-phase pipeline with 4 depth modes. Checks operators, pods, addons, subsystems, dependency chains, and known failure patterns. | `"How's my hub health?"` (after `oc login`) |
| **Bug Hunter** | Proactively hunts for bugs in ACM feature implementations using test cases as a starting point. 10-dimension investigation with adversarial subagents. | `"Hunt bugs using RHACM4K-61733"` |
| **Bug Fix Verifier** | Verifies whether a known bug fix has landed on a target environment. Checks branch reachability, build dates, code presence, and UI behavior. | `"Verify ACM-29818 is fixed on this cluster"` |

### Supporting Skills

These are called by the primary workflows or used standalone for focused tasks.

| Skill | Purpose |
|-------|---------|
| **Failure Classifier** | Classify individual test failures with 12-layer diagnostics and counterfactual validation. |
| **Cluster Health** | Cluster health diagnostic toolkit (12-layer model, 14 trap patterns, dependency chains). |
| **Cluster Investigator** | Deep-dive investigation of individual test failures tracing from symptom to root cause. |
| **Cluster Remediation** | Remediate hub cluster issues with structured approval workflow. Proposes fixes, executes approved mutations, verifies results. |
| **Data Enricher** | Enrich test failure data with page object resolution, selector verification, and change history analysis. |
| **QE Code Analyzer** | PR diff analysis for test impact -- what changed and what to test. |
| **Test Case Writer** | Writes test case markdown from pre-gathered context. Called by the generator pipeline or standalone with context already in hand. |
| **Test Case Reviewer** | Quality review gate for test case files (conventions, UI verification, AC consistency). |
| **Knowledge Base** | Read-only ACM Console domain reference: per-area architecture, Polarion conventions, naming patterns. |
| **Knowledge Learner** | Builds and updates ACM knowledge by comparing live cluster state to the knowledge base. |
| **Jenkins Client** | Interface to Jenkins CI for build status, test results, pipeline stages, console logs, and downstream trees. |

### Utility Skills

| Skill | Purpose |
|-------|---------|
| **Onboard** | Interactive setup -- detects environment, configures MCP servers, prompts for credentials. |
| **YouTube Digest** | Extracts YouTube transcripts and produces structured digests with key takeaways and timestamps. |
| **Grill Me** | Interview-style stress testing of plans and designs until reaching shared understanding. |

## Apps

The primary workflows above are backed by full applications in `apps/` with their own agents, knowledge bases, tests, and slash commands.

| App | Skills It Powers | Slash Commands |
|-----|-----------------|----------------|
| **[Z-Stream Analysis](apps/z-stream-analysis/)** | z-stream-analyzer, failure-classifier, data-enricher, cluster-investigator | `/analyze`, `/gather`, `/quick` |
| **[Hub Health](apps/acm-hub-health/)** | hub-health-check, cluster-health, cluster-remediation, knowledge-learner | `/health-check`, `/deep`, `/sanity`, `/investigate`, `/learn` |
| **[Test Case Generator](apps/test-case-generator/)** | test-case-generator, test-case-writer, test-case-reviewer, qe-code-analyzer | `/generate`, `/review`, `/batch` |

Each app has its own `CLAUDE.md` with architecture details, data contracts, and development conventions.

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/getting-started)
- Python 3.10+
- GitHub CLI ([`gh`](https://cli.github.com/))

> [!NOTE]
> Some workflows need additional tools (`oc`, `jq`, `podman`, Node.js). The `/onboard` skill checks for everything and tells you exactly what's missing.

## How It Works

Each workflow combines **deterministic Python scripts** (data gathering, report generation) with **AI agents** (investigation, classification, test writing) orchestrated by Claude Code. Agents access external systems through [MCP servers](https://modelcontextprotocol.io/) -- JIRA, Jenkins, Polarion, ACM cluster APIs, and a Neo4j knowledge graph.

```
You ──> Claude Code ──> Skill ──> Pipeline
                          │
                 ┌────────┼────────┐
                 v        v        v
            Python     AI Agent   MCP Servers
            Scripts    (Claude)   (JIRA, Jenkins,
                                   Polarion, oc, ...)
```

## Project Layout

```
ai_systems_v2/
├── .claude/
│   ├── skills/                # 19 portable skills (usable from repo root)
│   ├── knowledge/             # Shared knowledge database (11 categories, 14 subsystems)
│   ├── commands/pre-push.md   # /pre-push quality gate
│   ├── settings.json          # Root-level Claude Code settings
│   └── statusline.sh          # Status line (model, branch, context %)
├── apps/
│   ├── z-stream-analysis/     # Pipeline failure classifier
│   ├── acm-hub-health/        # Cluster diagnostic agent
│   └── test-case-generator/   # JIRA-to-Polarion test cases
├── mcp/                       # MCP server code + setup
│   ├── setup.sh               # Automated MCP setup (also used by /onboard)
│   ├── deploy-acm-search.sh   # ACM Search MCP deploy
│   ├── verify.py              # Standalone health checker
│   ├── acm-source-mcp-server/ # ACM Console source search
│   └── polarion/              # Polarion test case access
├── .mcp.json                  # Root MCP config for skills (generated by /onboard, gitignored)
├── docs/
│   ├── skill-architecture.md  # Skill inventory, blast radius, contributing
│   └── skill-authoring-guide.md # Skill authoring standards
├── AGENTS.md                  # Agent reference for external AI tools
├── CLAUDE.md                  # Claude Code instructions
└── README.md                  # You are here
```

## License & Attribution

This project is licensed under the **Apache License 2.0** (SPDX: `Apache-2.0`). See [LICENSE](LICENSE).

This repo integrates with MCP servers maintained by other teams (JIRA, Jenkins, Knowledge Graph, ACM Search). All external code usage, fork provenance, upstream PRs, and design inspirations are documented in **[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)**.

## Contributing

```bash
cd apps/z-stream-analysis
python -m pytest tests/unit/ tests/regression/ -q    # 753 tests, no external deps
```

See each app's `CLAUDE.md` for architecture details and development conventions. For skill authoring standards, see [`docs/skill-authoring-guide.md`](docs/skill-authoring-guide.md). For the skill inventory and blast radius map, see [`docs/skill-architecture.md`](docs/skill-architecture.md).
