# AI Systems Suite (v3.3)

Multi-app repository for Jenkins pipeline analysis and test generation tools, built on Claude Code.

---

## Z-Stream Analysis

> Automated Jenkins pipeline failure analysis. Classifies each failed test as **PRODUCT_BUG**, **AUTOMATION_BUG**, **INFRASTRUCTURE**, **FLAKY**, **NO_BUG**, **MIXED**, or **UNKNOWN** — with evidence-backed reasoning and JIRA correlation.

### Quick Start

Open Claude Code in this repository (root or `apps/z-stream-analysis/`) and ask:

```
Analyze this run: <JENKINS_BUILD_URL>
```

That's it. Claude Code handles the full pipeline automatically:

1. **Gather** -- Collects facts from Jenkins, validates cluster health, clones repos, searches product source for failing selectors, scans 200 commits for selector renames, probes backend API endpoints
2. **Analyze** -- 5-phase AI investigation per test: assess environment, deep-dive with MCP tools (source code, JIRA, Knowledge Graph), validate with 2+ evidence sources, classify via decision tree, correlate with JIRA
3. **Report** -- Generates per-test markdown report, JSON breakdown, and summary

### How It Works

| Stage | What | How |
|-------|------|-----|
| **1. Gather** (Python, ~3 min) | Collect evidence | Jenkins data, cluster validation via `oc`, repo cloning, selector search in product source, 200-commit git diff for renames, backend API probing with cluster ground truth cross-reference |
| **2. Analyze** (AI, ~20-30 min) | Classify each failure | 5-phase investigation using ACM-UI MCP (selectors), JIRA MCP (known bugs), Neo4j KG (dependencies). Per-test causal verification, graduated infrastructure scoring |
| **3. Report** (Python) | Generate deliverables | `Detailed-Analysis.md`, `per-test-breakdown.json`, `SUMMARY.txt` |

### Classification Guide

| Classification | Meaning | Example |
|---------------|---------|---------|
| **PRODUCT_BUG** | Product code is broken | 500 errors, feature doesn't render, API returns wrong data |
| **AUTOMATION_BUG** | Test code is broken | Stale selector, wrong text case, missing fixture data |
| **INFRASTRUCTURE** | Environment issue | Cluster unreachable, DNS failure, network timeout |
| **FLAKY** | Intermittent failure | Passes on retry, timing-dependent |
| **MIXED** | Multiple root causes | Product bug + automation bug in same test |
| **NO_BUG** | Expected behavior | Test validates deprecated feature removed by design |
| **UNKNOWN** | Insufficient evidence | Needs manual investigation |

### Manual Pipeline (Advanced)

You can also run each stage individually:

```bash
cd apps/z-stream-analysis/

# Stage 1: Gather data
python -m src.scripts.gather "<JENKINS_URL>"
python -m src.scripts.gather "<JENKINS_URL>" --skip-env    # Skip cluster validation
python -m src.scripts.gather "<JENKINS_URL>" --skip-repo   # Skip repo cloning

# Stage 2: AI analysis (read core-data.json, write analysis-results.json)

# Stage 3: Generate reports
python -m src.scripts.report runs/<run_dir>
```

See `apps/z-stream-analysis/CLAUDE.md` for the full classification guide, schema reference, and MCP tool documentation.

---

## Claude Test Generator (In Progress)

`apps/claude-test-generator/` — Test plan generation from JIRA tickets. Not currently functional.

---

## MCP Servers

Four MCP servers provide tools during analysis. Run `bash mcp/setup.sh` to configure.

| Server | Tools | Purpose |
|--------|-------|---------|
| **ACM UI** | 20 | ACM Console + kubevirt-plugin source code search via GitHub |
| **JIRA** | 25 | Issue search, creation, and management |
| **Neo4j RHACM** | 3 | Component dependency analysis (optional) |
| **Polarion** | 17 | Polarion test case access (optional) |

---

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
│   ├── z-stream-analysis/     # Pipeline failure analysis (active)
│   └── claude-test-generator/ # Test generation (in progress)
└── mcp/
    ├── acm-ui-mcp-server/     # ACM UI MCP server
    ├── jira-mcp-server/       # JIRA MCP server
    ├── neo4j-rhacm/           # Knowledge graph MCP server
    └── polarion/              # Polarion MCP server
```

## Tests

```bash
cd apps/z-stream-analysis/ && python -m pytest tests/ -q
```
