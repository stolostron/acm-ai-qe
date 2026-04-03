# Z-Stream Analysis Overview (v3.6)

Jenkins pipeline failure analysis with definitive classification of each test failure.

**Input:** A Jenkins URL with failed tests
**Output:** Classification of each failure as PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or other

---

## Five-Stage Pipeline

```
  STAGE 0        STAGE 1          STAGE 1.5          STAGE 2            STAGE 3
┌──────────┐  ┌──────────┐    ┌────────────┐    ┌──────────┐      ┌──────────┐
│  ORACLE  │─►│  GATHER  │───►│ DIAGNOSTIC │───►│ ANALYZE  │─────►│  REPORT  │
│(inside   │  │  (Python)│    │   (AI)     │    │   (AI)   │      │ (Python) │
│ gather)  │  │          │    │            │    │          │      │          │
└──────────┘  └──────────┘    └────────────┘    └──────────┘      └──────────┘
     │              │                │                │                  │
     ▼              ▼                ▼                ▼                  ▼
cluster_oracle  core-data.json  cluster-          analysis-         Detailed-Analysis.md
                cluster.kubeconfig  diagnosis.json  results.json    per-test-breakdown.json
                repos/          knowledge/learned/                  SUMMARY.txt
                pipeline.log.jsonl                                  pipeline.log.jsonl
```

| Stage | Command | What It Does |
|-------|---------|--------------|
| 1 | `python -m src.scripts.gather "<URL>"` | Collect data from Jenkins, cluster health audit (6-phase), feature context oracle, and repos; persist kubeconfig. Produces `core-data.json` + `cluster-health.json`. |
| 1.5 | `cluster-diagnostic` agent (optional) | Deep AI-driven cluster investigation; writes `cluster-diagnosis.json` |
| 2 | `z-stream-analysis` agent reads core-data.json + cluster-health.json | 5-phase systematic investigation per test (uses health audit + diagnostic data + kubeconfig) |
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
  │                    Steps 1-11:                │                    │
  │                    Fetch Jenkins data        │                    │
  │                    Cluster health audit      │                    │
  │                    Feature context oracle    │                    │
  │                    Clone repos               │                    │
  │                    Extract context           │                    │
  │                         │                    │                    │
  │                    core-data.json +          │                    │
  │                    cluster-health.json       │                    │
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
├── cluster.kubeconfig          ← Persisted cluster auth for Stage 2
├── pipeline.log.jsonl          ← Structured logs from all Python services (Stage 1+3)
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

Agent trace logs (Claude Code tool calls, MCP interactions, prompts) are stored
separately in .claude/traces/<session_id>.jsonl — one file per session.
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

### Decision Quick Reference (Pre-Routing + 3-Path Routing in Phase D)

**Pre-routing checks:** **PR-1** blank page / no-js detection (missing prerequisite → INFRASTRUCTURE), **PR-2** hook failure deduplication (cascading after-all hooks → NO_BUG), **PR-3** temporal evidence (stale_test_signal with refactor commit → signals PRODUCT_BUG), **PR-5** data assertion extraction (expected vs actual value mismatch → signals PRODUCT_BUG or AUTOMATION_BUG based on value source) (v3.3), **PR-6** backend probe source-of-truth — if probe has `classification_hint`, use deterministic K8s-vs-console comparison to route PRODUCT_BUG or INFRASTRUCTURE (v3.4), **PR-7** Environment Oracle dependency check — if oracle detects broken dependency (operator, addon, component), route to INFRASTRUCTURE (v3.5).

**3-path routing:** **Path A** (selector mismatch → AUTOMATION_BUG), **Path B1** (non-selector timeout → INFRASTRUCTURE, graduated health scoring with definitive/strong/moderate bands) (v3.3), **Path B2** (everything else → JIRA-informed investigation). **PR-4** checks feature knowledge override first (unmet prerequisites, playbook-confirmed failure paths). **D0** checks backend cross-check — if a backend issue caused the UI failure, routes to Path B2 regardless.

**Post-classification validation:** **D4** final validation, **D4b** per-test causal link verification (every test attributed to a dominant pattern must have a documented causal mechanism) (v3.3), **D5** counter-bias validation (3-test threshold rule: if 3+ tests share the same root_cause, at least 1 must be independently re-investigated) (v3.3).

See [02-STAGE2-AI-ANALYSIS.md](02-STAGE2-AI-ANALYSIS.md) Phase D for the full decision routing with evidence tables and confidence scores.

---

## Evidence Requirements

Every classification requires 2+ evidence sources.

### Evidence Tiers

| Tier | Weight | Examples |
|------|--------|----------|
| 1 (Definitive) | 1.0 | 500 errors in log, element_removed=true, feature_area_health<0.3 |
| 2 (Strong) | 0.8 | Selector mismatch, multiple tests same selector, cascading failure, feature_area_health 0.3-0.5 |
| 3 (Supportive) | 0.5 | Similar selectors exist, timing issues, single timeout, feature_area_health 0.5-0.7 |

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

Five MCP servers provide tools during Stage 2 (AI Analysis). The Knowledge Graph is also queried directly via HTTP API during Stage 1 (gather.py) for dependency context.

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   ACM-UI MCP (20)   │  │  Knowledge Graph    │  │   JIRA MCP (25)     │
│  ─────────────────  │  │  ─────────────────  │  │  ─────────────────  │
│  Code search        │  │  Component deps     │  │  Search issues      │
│  Find selectors     │  │  Cascading failure  │  │  Get/create/update  │
│  Get source code    │  │  Subsystem context  │  │  Comments & time    │
│  Version control    │  │  Feature workflow   │  │  Link issues        │
│  Translations       │  │  Neo4j Cypher       │  │  Team management    │
│  Wizard steps       │  │  HTTP API + MCP     │  │  Watchers           │
│                     │  │                     │  │  Transitions        │
│  ACM: 2.11-2.17     │  │                     │  │                     │
│  CNV: 4.14-4.22     │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘

┌─────────────────────┐  ┌─────────────────────┐
│  Polarion MCP (25)  │  │  Jenkins MCP (11)   │
│  ─────────────────  │  │  ─────────────────  │
│  Test case access   │  │  Build info         │
│  Test run info      │  │  Console logs       │
│  Work items         │  │  Test reports        │
│  Test steps         │  │  Job management     │
│  Requirements       │  │  Build parameters   │
│  Document access    │  │  Pipeline status    │
│  Test results       │  │                     │
└─────────────────────┘  └─────────────────────┘
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
| `cluster.kubeconfig` | Stage 1 | Persisted cluster auth for Stage 2 |
| `analysis-results.json` | Stage 2 | AI classifications |
| `Detailed-Analysis.md` | Stage 3 | Human-readable report |
| `per-test-breakdown.json` | Stage 3 | Structured data for tooling |
| `SUMMARY.txt` | Stage 3 | Quick overview |

### The 5 Phases (Stage 2)

| Phase | Purpose | Key Question |
|-------|---------|--------------|
| A | Initial Assessment + Feature Knowledge | What's the big picture? What do playbooks say? |
| B | Deep Investigation + Tiered Cluster Checks | What went wrong in each test? What do pods show? |
| C | Cross-Reference Validation | Do I have enough evidence? |
| D | Pre-Routing + Classification (Blank Page → Hook Dedup → Temporal → Data Assertion → Backend Probe → Oracle Dependency → Feature Override → Backend → 3-Path → Causal Link → Counter-Bias) | Blank page? Cascading hook? Stale test? Data assertion? Backend probe mismatch? Oracle dependency broken? Prerequisite unmet? Backend caused it? Selector (A), timeout (B1), or JIRA-informed (B2)? Causal link verified? Counter-bias checked? |
| E | Feature Context & JIRA Correlation | What should this feature do? Are there known issues? |

---

## Detailed Documentation

| Topic | File |
|-------|------|
| Stage 1: Data gathering (Steps 1-11) | [01-STAGE1-DATA-GATHERING.md](01-STAGE1-DATA-GATHERING.md) |
| Stage 2: AI analysis (Phases A-E) | [02-STAGE2-AI-ANALYSIS.md](02-STAGE2-AI-ANALYSIS.md) |
| Stage 3: Report generation | [03-STAGE3-REPORT-GENERATION.md](03-STAGE3-REPORT-GENERATION.md) |
| All services reference | [04-SERVICES-REFERENCE.md](04-SERVICES-REFERENCE.md) |
| MCP integration (ACM-UI, Jenkins, JIRA, Polarion, Knowledge Graph) | [05-MCP-INTEGRATION.md](05-MCP-INTEGRATION.md) |
| Knowledge database reference | [06-KNOWLEDGE-DATABASE.md](06-KNOWLEDGE-DATABASE.md) |

---

## Version History

| Version | Changes |
|---------|---------|
| v3.7 | Automated cluster health audit via `ClusterHealthService` (6-phase: DISCOVER, LEARN, CHECK, COMPARE, CORRELATE, SCORE). Produces `cluster-health.json` with operator health, subsystem health, infrastructure issues, managed cluster status, baseline comparison, and classification guidance. Replaces `EnvironmentValidationService` for Step 4. Oracle Phase 6 skipped (health checks handled by health audit). Knowledge database validated against live ACM 2.16 GA cluster (58 components, 18 addons, 10 dependency chains, 19 webhooks, 34 prerequisites). New `prerequisites.yaml`. Agent instructions updated to read `cluster-health.json` in Phase A-0. |
| v3.6 | Comprehensive AI-driven cluster diagnostic (Stage 1.5) adapted from ACM Hub Health agent. 6-phase investigation producing `cluster-diagnosis.json`. Knowledge files adapted from hub-health (healthy-baseline, addon-catalog, webhook-registry, diagnostic-traps). |
| v3.5.1 | External service failure detection, version compatibility constraints, known JIRA bugs cache, ALC repo fallback. |
| v3.5 | Environment Oracle (Step 5) — feature-aware dependency health checking via `EnvironmentOracleService`. Phase 1 identifies feature areas from pipeline/test names and extracts Polarion IDs, Phase 5 synthesizes dependency model from feature playbooks, Phase 6 runs targeted read-only `oc` commands (operator CSV, addon, CRD checks). Output stored in `cluster_oracle` key in core-data.json. Skipped with `--skip-env`. |
| v3.4 | Backend probe source-of-truth validation (PR-6) — deterministic routing when probe has `classification_hint` and `anomaly_source`, K8s-vs-console comparison to distinguish PRODUCT_BUG from INFRASTRUCTURE. Cluster access confidence adjustment (PR-4b) — adjusts confidence based on cluster accessibility during analysis. |
| v3.3 | Backend API probing (Step 4c) with 5 endpoint checks (`/authenticated`, `/hub`, `/username`, `/ansibletower`, `/proxy/search`) stored in `backend_probes`, `FEATURE_AREA_PROBE_MAP` linking feature areas to relevant probes, assertion value extraction (PR-5) with `assertion_analysis` per test, failure mode categorization (`failure_mode_category`: render_failure/element_missing/data_incorrect/timeout_general/assertion_logic/server_error/unknown), refined failure types (`assertion_data`/`assertion_selector`), per-feature-area health scoring (GAP-04) with graduated bands (definitive <0.3, strong 0.3-0.5, moderate 0.5-0.7, none >=0.7), per-test causal link verification (D4b), counter-bias 3-test threshold rule (D5 strengthened), new schema fields (`failure_mode_category`, `assertion_analysis`, `data_assertion_failures`, `feature_area_health`, `backend_probes`), graduated infrastructure thresholds (`INFRA_DEFINITIVE`/`INFRA_STRONG`/`INFRA_MODERATE`), schema version 3.3.0 |
| v3.2 | Blank page / no-js pre-routing (PR-1), hook failure deduplication (PR-2), temporal evidence routing (PR-3), Automation/AAP playbook and feature area, KnowledgeGraphClient rewritten with direct Neo4j HTTP API (fixes always-unavailable bug), new schema fields (`is_cascading_hook_failure`, `blank_page_detected`, `cascading_hook_failures`, `blank_page_failures`), counter-bias validation (D5) |
| v3.1 | Feature investigation playbooks (YAML), FeatureKnowledgeService, MCH component extraction (`mch_enabled_components`, `mch_version`), cluster kubeconfig persistence (`cluster.kubeconfig` for Stage 2 re-authentication), tiered investigation (Tiers 0-4), `feature_knowledge` in core-data.json, new schema fields (`prerequisite_analysis`, `playbook_investigation`, `cluster_investigation_detail`, `cluster_investigation_summary`), feedback CLI |
| v3.0 | Cluster investigation, feature area grounding, backend cross-check (B7/D0), targeted pod investigation (B5b) |
| v2.5 | 5-Phase Systematic Investigation Framework, multi-evidence requirement |
| v2.4 | Complete Context Upfront, extracted_context per test |
| v2.3 | Knowledge Graph integration, component extraction |
| v2.2 | ACM-UI MCP integration, JenkinsAPIClient |
| v2.0 | AI-driven classification, repos cloned to run directory |
