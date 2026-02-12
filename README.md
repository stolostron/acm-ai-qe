# AI Systems Suite

Multi-app repository for Jenkins pipeline analysis and test generation tools, built on Claude Code.

---

## Z-Stream Analysis

> Automated Jenkins pipeline failure analysis. Classifies each failed test as **PRODUCT_BUG**, **AUTOMATION_BUG**, **INFRASTRUCTURE**, **FLAKY**, **NO_BUG**, **MIXED**, or **UNKNOWN** — with evidence-backed reasoning and JIRA correlation.

### Quick Start

Open Claude Code in this repository (root or `apps/z-stream-analysis/`) and ask:

```
Analyze this run: https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/qe-acm-automation-poc/job/clc-e2e-pipeline/3757
```

That's it. Claude Code handles the full pipeline automatically:

1. Gathers data from Jenkins (build info, test reports, console logs)
2. Investigates each failure using a 5-phase framework with MCP tool queries
3. Classifies every failed test with multi-evidence validation
4. Generates a detailed report with prioritized action items

### Example Output

After the analysis completes, you'll find these files in `apps/z-stream-analysis/runs/<job>_<timestamp>/`:

```
runs/qe-acm-automation-poc_clc-e2e-pipeline_20260212_003849/
├── Detailed-Analysis.md        # Full report with per-test breakdown
├── SUMMARY.txt                 # Quick overview
├── per-test-breakdown.json     # Structured data for tooling
├── analysis-results.json       # Raw AI analysis output
├── core-data.json              # Gathered Jenkins data
└── console-log.txt             # Jenkins console log
```

**SUMMARY.txt** gives you the high-level picture:

```
PIPELINE FAILURE ANALYSIS SUMMARY
============================================================
Jenkins URL: https://jenkins.example.com/job/clc-e2e-pipeline/3757
Build: qe-acm-automation-poc #3757
Result: UNSTABLE

TEST SUMMARY:
  Total: 34  |  Passed: 23  |  Failed: 11  |  Pass Rate: 67.6%

FAILURE BREAKDOWN:
  [AUTOMATION BUG]: 11 test(s)
  [PRODUCT BUG]:     0 test(s)
  [INFRASTRUCTURE]:  0 test(s)

OVERALL: AUTOMATION BUG (90% confidence)

PRIORITY ACTIONS:
  1. [HIGH]   RHACM4K-3046 — Case mismatch in button selector
  2. [MEDIUM] RHACM4K-51365/51367/51368 — Unstable OUIA selectors
  3. [MEDIUM] RHACM4K-30168/3177/52891 — Test isolation failure
```

**Detailed-Analysis.md** includes per-test analysis with evidence, root cause, and recommended fixes.

### How It Works

The analysis runs in three stages:

| Stage | What | How |
|-------|------|-----|
| **1. Gather** | Fetch Jenkins data | `gather.py` pulls build info, test reports, console logs, and clones test repos |
| **2. Analyze** | Classify each failure | AI runs 5 investigation phases (A-E) using MCP tools to search product code, translations, and JIRA |
| **3. Report** | Generate deliverables | `report.py` produces markdown report, JSON breakdown, and summary |

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
| **JIRA** | 24 | Issue search, creation, and management |
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
    ├── acm-ui/                # ACM UI MCP server
    ├── jira/                  # JIRA MCP server
    ├── neo4j-rhacm/           # Knowledge graph MCP server
    └── polarion/              # Polarion MCP server
```

## Tests

```bash
cd apps/z-stream-analysis/ && python -m pytest tests/ -q
```
