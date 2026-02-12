# Z-Stream Analysis Overview (v2.5)

Jenkins pipeline failure analysis with definitive classification of each test failure.

**Input:** A Jenkins URL with failed tests
**Output:** Classification of each failure as PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or other

---

## Three-Stage Pipeline

```
     STAGE 1                 STAGE 2                  STAGE 3
  ┌──────────┐           ┌──────────┐            ┌──────────┐
  │  GATHER  │    ───►   │ ANALYZE  │    ───►    │  REPORT  │
  │  (Python)│           │   (AI)   │            │ (Python) │
  └──────────┘           └──────────┘            └──────────┘
       │                      │                       │
       ▼                      ▼                       ▼
  core-data.json      analysis-results.json    Detailed-Analysis.md
  repos/                                       per-test-breakdown.json
                                               SUMMARY.txt
```

| Stage | Command | What It Does |
|-------|---------|--------------|
| 1 | `python -m src.scripts.gather "<URL>"` | Collect data from Jenkins, cluster, and repos |
| 2 | AI agent reads core-data.json | 5-phase systematic investigation per test |
| 3 | `python -m src.scripts.report runs/<dir>` | Generate human-readable reports |

---

## End-to-End Sequence

```
USER                     STAGE 1                STAGE 2              STAGE 3
  │                    (gather.py)           (AI Agent)          (report.py)
  │                         │                    │                    │
  │  Jenkins URL            │                    │                    │
  │─────────────────────────►                    │                    │
  │                         │                    │                    │
  │                    Steps 1-8:                │                    │
  │                    Fetch Jenkins data        │                    │
  │                    Check cluster health      │                    │
  │                    Clone repos               │                    │
  │                    Extract context           │                    │
  │                         │                    │                    │
  │                    core-data.json            │                    │
  │                         │────────────────────►                    │
  │                         │                    │                    │
  │                         │              Phase A: Assess            │
  │                         │              Phase B: Investigate       │
  │                         │              Phase C: Validate          │
  │                         │              Phase D: Classify          │
  │                         │              Phase E: JIRA Context      │
  │                         │                    │                    │
  │                         │            analysis-results.json        │
  │                         │                    │────────────────────►
  │                         │                    │                    │
  │                         │                    │              Format reports
  │                         │                    │                    │
  │◄─────────────────────────────────────────────── Detailed-Analysis.md
  │◄─────────────────────────────────────────────── SUMMARY.txt
```

---

## Run Directory Structure

```
runs/<job>_<timestamp>/
│
│  Created by Stage 1 (gather.py):
├── core-data.json              ← Primary data for AI
├── run-metadata.json           ← Run metadata (timing, version)
├── manifest.json               ← File index with workflow
├── console-log.txt             ← Full Jenkins console output
├── jenkins-build-info.json     ← Build metadata (credentials masked)
├── test-report.json            ← Per-test failure details
├── environment-status.json     ← Cluster health
├── element-inventory.json      ← MCP element locations (if available)
├── repos/                      ← Cloned repositories
│   ├── automation/             ← Test code
│   ├── console/                ← Product code
│   └── kubevirt-plugin/        ← For VM tests only
│
│  Created by Stage 2 (AI agent):
├── analysis-results.json       ← AI classifications
│
│  Created by Stage 3 (report.py):
├── Detailed-Analysis.md        ← Human-readable report
├── per-test-breakdown.json     ← Structured data for tooling
└── SUMMARY.txt                 ← Brief summary
```

---

## Classification Types

| Classification | Owner | Triggers |
|----------------|-------|----------|
| **PRODUCT_BUG** | Product Team | 500/502/503 errors; backend API failure; UI feature broken; feature story contradicts behavior |
| **AUTOMATION_BUG** | Automation Team | Selector not in product code; element removed from product; test expects outdated format; acceptance criteria changed, test unchanged |
| **INFRASTRUCTURE** | Platform Team | Cluster not accessible; network/DNS failures; multiple unrelated tests timing out |
| **MIXED** | Multiple | Multiple distinct root causes identified |
| **UNKNOWN** | — | Insufficient evidence (confidence < 0.50) |
| **FLAKY** | — | Passes on retry without code changes; intermittent timing failure |
| **NO_BUG** | — | Failure expected given intentional product changes |

### Decision Quick Reference (3-Path Routing in Phase D)

| Evidence | Path | Classification |
|----------|------|----------------|
| `console_search.found = false` | A | AUTOMATION_BUG |
| `element_removed = true` in timeline | A | AUTOMATION_BUG |
| `failure_type = element_not_found` | A | AUTOMATION_BUG |
| Timeout waiting for missing selector | A | AUTOMATION_BUG |
| Timeout (non-selector) | B1 | INFRASTRUCTURE |
| `environment.cluster_accessible = false` | B1 | INFRASTRUCTURE |
| Multiple unrelated tests timeout | B1 | INFRASTRUCTURE |
| 500 errors in console log | B2 | PRODUCT_BUG |
| Feature story contradicts product behavior | B2/E | PRODUCT_BUG |
| Assertion failure + test logic wrong | B2 | AUTOMATION_BUG |
| Test passes on retry, no code changes | Any | FLAKY |
| Failure matches intentional product change | E | NO_BUG |

---

## Evidence Requirements

Every classification requires 2+ evidence sources.

### Evidence Tiers

| Tier | Weight | Examples |
|------|--------|----------|
| 1 (Definitive) | 1.0 | 500 errors in log, element_removed=true, env_score<0.3 |
| 2 (Strong) | 0.8 | Selector mismatch, multiple tests same selector, cascading failure |
| 3 (Supportive) | 0.5 | Similar selectors exist, timing issues, single timeout |

### Minimum Requirement

1 Tier 1 + 1 Tier 2, **OR** 2 Tier 1, **OR** 3 Tier 2

### Required Evidence by Classification

| Classification | Required Sources |
|----------------|-----------------|
| PRODUCT_BUG | Console 500 + environment healthy + test selector correct |
| AUTOMATION_BUG | Timeline mismatch + console_search.found=false + no 500 errors |
| INFRASTRUCTURE | Environment unhealthy + multiple tests + network errors |

---

## MCP Servers

Three MCP servers provide tools during Stage 2 (AI Analysis):

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   ACM-UI MCP (20)   │  │  Knowledge Graph    │  │   JIRA MCP (24)     │
│  ─────────────────  │  │  ─────────────────  │  │  ─────────────────  │
│  Code search        │  │  Component deps     │  │  Search issues      │
│  Find selectors     │  │  Cascading failure  │  │  Get/create/update  │
│  Get source code    │  │  Subsystem context  │  │  Comments & time    │
│  Version control    │  │  Feature workflow   │  │  Link issues        │
│  Translations       │  │  Neo4j Cypher       │  │  Team management    │
│  Wizard steps       │  │  (Optional)         │  │  Watchers           │
│                     │  │                     │  │  Transitions        │
│  ACM: 2.11-2.17     │  │                     │  │                     │
│  CNV: 4.14-4.22     │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

See [05-MCP-INTEGRATION.md](05-MCP-INTEGRATION.md) for detailed tool usage and [04-SERVICES-REFERENCE.md](04-SERVICES-REFERENCE.md) for method signatures.

---

## Quick Reference

### Commands

```bash
# Stage 1: Gather data
python -m src.scripts.gather "https://jenkins.example.com/job/test/123/"

# Stage 2: AI analyzes (automatic when using agent)
# Reads core-data.json, creates analysis-results.json

# Stage 3: Generate reports
python -m src.scripts.report runs/<dir>

# Options
python -m src.scripts.gather <url> --skip-env      # Skip cluster check
python -m src.scripts.gather <url> --skip-repo     # Skip repo cloning
python -m src.scripts.report <dir> --keep-repos    # Don't delete repos/
```

### Key Files

| File | Created By | Purpose |
|------|------------|---------|
| `core-data.json` | Stage 1 | All gathered data (read first) |
| `analysis-results.json` | Stage 2 | AI classifications |
| `Detailed-Analysis.md` | Stage 3 | Human-readable report |
| `per-test-breakdown.json` | Stage 3 | Structured data for tooling |
| `SUMMARY.txt` | Stage 3 | Quick overview |

### The 5 Phases (Stage 2)

| Phase | Purpose | Key Question |
|-------|---------|--------------|
| A | Initial Assessment | What's the big picture? |
| B | Deep Investigation | What went wrong in each test? |
| C | Cross-Reference Validation | Do I have enough evidence? |
| D | 3-Path Classification Routing | Selector (A), timeout (B1), or JIRA-informed (B2)? |
| E | Feature Context & JIRA Correlation | What should this feature do? Are there known issues? |

---

## Detailed Documentation

| Topic | File |
|-------|------|
| Stage 1: Data gathering (Steps 1-8) | [01-STAGE1-DATA-GATHERING.md](01-STAGE1-DATA-GATHERING.md) |
| Stage 2: AI analysis (Phases A-E) | [02-STAGE2-AI-ANALYSIS.md](02-STAGE2-AI-ANALYSIS.md) |
| Stage 3: Report generation | [03-STAGE3-REPORT-GENERATION.md](03-STAGE3-REPORT-GENERATION.md) |
| All services reference | [04-SERVICES-REFERENCE.md](04-SERVICES-REFERENCE.md) |
| MCP integration (ACM-UI, JIRA, Knowledge Graph) | [05-MCP-INTEGRATION.md](05-MCP-INTEGRATION.md) |

---

## Version History

| Version | Changes |
|---------|---------|
| v2.5 | 5-Phase Systematic Investigation Framework, multi-evidence requirement |
| v2.4 | Complete Context Upfront, extracted_context per test |
| v2.3 | Knowledge Graph integration, component extraction |
| v2.2 | ACM-UI MCP integration, JenkinsAPIClient |
| v2.0 | AI-driven classification, repos cloned to run directory |
