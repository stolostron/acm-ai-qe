---
name: acm-z-stream-analyzer
description: Analyze Jenkins pipeline test failures and classify each as PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or NO_BUG. Runs a 4-stage pipeline with data gathering, cluster diagnostics, AI classification, and report generation. Use when asked to analyze a Jenkins run, classify test failures, or investigate pipeline results.
compatibility: "Required MCPs: acm-source, jira, polarion. Recommended: neo4j-rhacm, jenkins. Requires oc CLI and gh CLI. Run /onboard to configure all MCPs."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Z-Stream Pipeline Failure Analyzer

Analyzes Jenkins pipeline test failures using a 4-stage pipeline with AI-driven 12-layer diagnostic investigation. Produces per-test classifications with evidence chains.

**Standalone operation:** Works independently. Give it a Jenkins URL and it runs the full pipeline. If invoked without a URL, asks for one.

## Skills Used

This skill orchestrates the following skills:

| Skill | Stage | How This Skill Uses It |
|-------|-------|----------------------|
| **acm-jenkins-client** | Pre-flight | Verify Jenkins connectivity, get build metadata |
| **acm-cluster-health** | Stage 1.5 | 12-layer diagnostic methodology for cluster health assessment |
| **acm-data-enricher** | Post-Stage 1 | Enrich core-data.json with selector verification, timeline analysis, page object resolution |
| **acm-failure-classifier** | Stage 2 | Full 5-phase classification analysis (A through E) |
| **acm-cluster-investigator** | Stage 2 | Per-group deep investigation dispatched by the classifier |
| **acm-source** (MCP) | Stages 1.5-2 | Selector verification, source code search |
| **neo4j-rhacm** (MCP) | Stages 1.5-2 | Component dependency analysis |
| **jira** (MCP) | Stage 2 | Bug correlation and story context |
| **polarion** (MCP) | Stage 2 | Test case expected behavior |
| **acm-knowledge-base** | All stages | Shared area architecture context |

## Pipeline Stages

Read `references/pipeline-stages.md` for full details.

### Stage 1: Gather Data (deterministic)

```
Stage 1: Gathering pipeline data from Jenkins...
```

Run the gather script from the app directory:
```bash
cd apps/z-stream-analysis && python -m src.scripts.gather "<JENKINS_URL>" [--skip-env] [--skip-repo]
```

This produces:
- `core-data.json` -- all test data, cluster landscape, feature grounding, extracted context
- `cluster.kubeconfig` -- persisted cluster auth
- `repos/` -- cloned automation and product repos

Options:
- `--skip-env` -- skip cluster login and landscape collection
- `--skip-repo` -- skip repository cloning

Show summary: "Extracted N failed tests across M feature areas, K managed clusters."

## Knowledge Directory

KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/

### Stage 1.5: Cluster Diagnostic (AI)

```
Stage 1.5: Running comprehensive cluster diagnostic...
```

Using the acm-cluster-health skill methodology, perform a comprehensive cluster health assessment. Read the `cluster.kubeconfig` from the run directory.

Follow the 6-phase diagnostic process:
1. **Discover:** MCH namespace, version, operators, nodes, managed clusters, CSVs, webhooks
2. **Learn:** Read knowledge baselines (`${KNOWLEDGE_DIR}/baselines/healthy-baseline.yaml`, `baselines/components.yaml`, `baselines/addon-catalog.yaml`, `diagnostics/diagnostic-traps.md`)
3. **Check:** 12-layer bottom-up verification (compute, network guards, storage, config, pods, addons)
4. **Pattern Match:** Cross-reference against `${KNOWLEDGE_DIR}/failures/failure-patterns.yaml` and per-area `failures/<area>/failure-signatures.md`
5. **Correlate:** Trace dependency chains, identify root causes across subsystems
6. **Output:** Write `cluster-diagnosis.json` with structured health data

The `cluster-diagnosis.json` **must** include these fields (required by the HTML report):
- `cluster_connectivity` (boolean) — true if cluster API is reachable
- `environment_health_score` (float 0.0-1.0) — weighted health score with penalty breakdown
- `cluster_identity` (object) — `api_url`, `ocp_version`, `acm_version`, `mce_version`, `mch_namespace`, `mch_phase`, `node_count`, `node_ready_count`, `managed_cluster_count`, `managed_cluster_ready_count`
- `operator_health` (object keyed by name) — each with `namespace`, `desired_replicas`, `available_replicas`, `status` (OK/DEGRADED/CRITICAL), `detail`
- `console_plugins` (array) — each with `name`, `service`, `namespace`
- `critical_issue_count` (integer) — count of critical infrastructure issues

See `.claude/agents/cluster-diagnostic.md` Step 6.2 for the full schema with examples.

Show summary: "Verdict: HEALTHY/DEGRADED/CRITICAL -- N subsystems checked, M issues found."

Skip if `--skip-env` was used or cluster access is unavailable.

### Data Enrichment (AI, runs after Stage 1.5)

Using the acm-data-enricher skill, enrich `core-data.json`:
- Task 1: Resolve page objects (trace imports) -- **requires repos/**
- Task 2: Verify selector existence (via acm-source MCP) -- **no repos needed**
- Task 3: Selector timeline analysis (git history + intent) -- **requires repos/**
- Task 4: Feature knowledge gap filling (conditional) -- **no repos needed**

**Always run data enrichment when there are failed tests.** When `--skip-repo` was used, the agent runs Tasks 2 and 4 only (Tasks 1 and 3 are skipped with documented markers). Only skip data enrichment entirely when there are zero failed tests.

No stage banner needed -- runs quietly before Stage 2.

### Stage 2: AI Analysis (AI)

```
Stage 2: Analyzing <N> failed tests (12-layer diagnostic investigation)...
```

Using the acm-failure-classifier skill, analyze all failed tests:
- Phase A: Ground and group (feature context, environment health, pattern matching, provably linked grouping)
- Phase B: 12-layer investigation per group (dispatches to acm-cluster-investigator)
- Phase C: Multi-evidence correlation
- Phase D: Validation and routing (counterfactual, causal links, counter-bias)
- Phase E: JIRA correlation

Output: `analysis-results.json` with per-test classifications.

Show summary: "N AUTOMATION_BUG, M INFRASTRUCTURE, K PRODUCT_BUG, J NO_BUG"

### Stage 3: Report Generation (deterministic)

```
Stage 3: Generating report...
```

Run the report script:
```bash
cd apps/z-stream-analysis && python -m src.scripts.report <run-directory>
```

This produces:
- `Detailed-Analysis.md` -- full markdown report
- `analysis-report.html` -- interactive HTML report
- `per-test-breakdown.json` -- per-test summary
- `SUMMARY.txt` -- human-readable summary

Show summary with output file paths.

## Classification Quick Reference

Read `references/classification-guide.md` for full definitions. Summary:

| Classification | Trigger |
|---|---|
| PRODUCT_BUG | Product code defect, wrong data, broken rendering |
| AUTOMATION_BUG | Stale selector, wrong assertion, test setup issue |
| INFRASTRUCTURE | Cluster issue, network, storage, operator down |
| NO_BUG | Expected behavior, hook cascade, disabled feature |
| MIXED | Multiple independent root causes |
| FLAKY | Inconsistent reproduction |
| UNKNOWN | Insufficient evidence |

## MCP Availability

If an MCP server is unavailable (not configured or connection refused), degrade gracefully:

| MCP | Impact if Missing | Fallback |
|-----|------------------|----------|
| acm-source | No selector verification in enrichment/classification | Skip Task 2 enrichment, classify with extracted context only |
| jira | No bug correlation in Phase E | Skip Phase E, note "JIRA unavailable" in output |
| polarion | No test case expected behavior lookup | Skip PR-6b check, rely on other evidence |
| neo4j-rhacm | No dependency chain analysis | Use knowledge file dependency chains instead |
| jenkins | No pre-flight connectivity check | Proceed if Jenkins URL is directly accessible via gather.py |

Do NOT abort the pipeline for a missing optional MCP. Report which MCPs were unavailable in the pipeline summary.

## Pre-Flight Checks

Before Stage 1, verify:
1. `gh` CLI authenticated (`gh auth status`)
2. Jenkins accessible (via acm-jenkins-client or curl)
3. Neo4j container running (attempt auto-start via Podman if not)

## Safety

- ALL cluster operations are read-only during analysis
- NEVER modify the cluster, JIRA tickets, or Polarion without explicit user approval
- Credentials are masked in all output files

## Run Directory

Each analysis produces artifacts under `runs/<timestamp>_<pipeline-name>/`:
```
core-data.json            -- Stage 1: all gathered data
cluster.kubeconfig        -- Stage 1: cluster auth
cluster-diagnosis.json    -- Stage 1.5: cluster health
repos/                    -- Stage 1: cloned repos
analysis-results.json     -- Stage 2: per-test classifications
Detailed-Analysis.md      -- Stage 3: full report
analysis-report.html      -- Stage 3: interactive HTML
per-test-breakdown.json   -- Stage 3: per-test summary
SUMMARY.txt               -- Stage 3: human-readable summary
pipeline.log.jsonl         -- All stages: structured logs
```
