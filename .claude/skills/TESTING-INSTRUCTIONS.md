# Skill Pack Testing Instructions

**Branch:** `skill-implementation` (in `ai_systems_v2` repo)
**Date:** 2026-04-29
**Status:** Implementation complete, not committed, needs end-to-end testing

## What Was Built

18 portable ACM skills under `.claude/skills/acm-*/` converting the test-case-generator, acm-hub-health, and z-stream-analysis apps into Anthropic-compliant skill packs.

### Shared Skills (6)
- `acm-knowledge-base` -- Domain knowledge (9 area files, 4 convention files)
- `acm-neo4j-explorer` -- Neo4j architecture queries
- `acm-ui-source` -- ACM UI MCP interface (routes, translations, selectors)
- `acm-jira-client` -- JIRA MCP interface (vanilla, no app-specific logic)
- `acm-polarion-client` -- Polarion MCP interface
- `acm-cluster-health` -- 12-layer diagnostic methodology

### TC-Gen Skills (4)
- `acm-test-case-generator` -- Orchestrator (10-phase pipeline)
- `acm-code-analyzer` -- PR diff analysis
- `acm-test-case-writer` -- Test case writing (with graceful degradation)
- `acm-test-case-reviewer` -- Quality gate + programmatic enforcement

### Hub-Health Skills (3)
- `acm-hub-health-check` -- Orchestrator (6-phase, 4 depth modes, 59 knowledge files)
- `acm-cluster-remediation` -- Mutation execution with approval gates (graceful degradation)
- `acm-knowledge-learner` -- Cluster discovery and knowledge building (graceful degradation)

## Test 1: Test Case Generator (ACM-30459)

**JIRA:** https://redhat.atlassian.net/browse/ACM-30459
**PR:** stolostron/console#5790
**Area:** Governance (labels on PolicyTemplateDetails page)
**Cluster for live validation:** https://console-openshift-console.apps.ashafi-test-az-217.az.dev09.red-chesterfield.com
**Cluster login:** `oc login https://api.ashafi-test-az-217.az.dev09.red-chesterfield.com:6443 -u kubeadmin -p 'WXHWj-C25aT-fQ9cF-FQFUB' --insecure-skip-tls-verify`

### What to Test

Run the full pipeline by saying: "Generate a test case for ACM-30459 with live validation on https://console-openshift-console.apps.ashafi-test-az-217.az.dev09.red-chesterfield.com"

Verify each phase executes:
1. **Phase 0** -- Resolves inputs (JIRA ID, version 2.17, area governance, PR 5790)
2. **Phase 1** -- Runs `scripts/gather.py` (produces gather-output.json + pr-diff.txt)
3. **Phase 2** -- JIRA investigation using acm-jira-client (reads story, ACs, ALL comments, linked tickets)
4. **Phase 3** -- Code analysis using acm-code-analyzer (reads PR diff, reads full source of PolicyTemplateDetails.tsx via MCP, identifies filtering logic in label-utils.ts)
5. **Phase 4** -- UI discovery using acm-ui-source (routes, translations for "Labels", component source)
6. **Phase 5** -- Synthesis (merges findings, resolves conflicts, plans test steps)
7. **Phase 6** -- Live validation on the Azure cluster (if cluster accessible)
8. **Phase 7** -- Test case writing using acm-test-case-writer (conventions, knowledge constraints, self-review)
9. **Phase 8** -- Quality review using acm-test-case-reviewer (3+ MCP verifications, AC check) + scripts/review_enforcement.py
10. **Phase 9** -- Report generation using scripts/report.py (HTML, validation, summary)

### Known Correct Answers (from prior analysis)

The generated test case MUST correctly state:
- **Label filtering:** `isUserDefinedPolicyLabel()` filters `cluster-name` (exact), `cluster-namespace` (exact), `policy.open-cluster-management.io/*` (prefix). NOT `cluster.open-cluster-management.io/` or `velero.io/`.
- **Field order:** Name, [Namespace if namespaced], Engine, Cluster, Kind, API version, Labels, [type-specific]
- **Empty state:** Labels field IS always present, shows "-" when no user-defined labels (NOT hidden)
- **Component:** Uses `<AcmLabels labels={labels} />` (NOT `renderLabelsAsList`)
- **Route:** `/multicloud/governance/policies/details/:namespace/:name/template/:clusterName/:apiGroup?/:apiVersion/:kind/:templateName`
- **Translation key:** `table.labels` -> "Labels"

### Approved Reference

Compare output against the approved Polarion test case:
`documentation/acm-components/virt/test-cases/2.17/RHACM4K-63381-GRC-Policy-Details-Labels.md`

And Polarion: `get_polarion_test_case_summary(project_id="RHACM4K", work_item_id="RHACM4K-63381")`

## Test 2: Hub Health Diagnostic

**Cluster:** https://api.ashafi-test-az-217.az.dev09.red-chesterfield.com:6443
**Login:** `oc login https://api.ashafi-test-az-217.az.dev09.red-chesterfield.com:6443 -u kubeadmin -p 'WXHWj-C25aT-fQ9cF-FQFUB' --insecure-skip-tls-verify`

### What to Test

#### Quick Check
Say: "Quick sanity check on my hub"
- Should run Phase 1 only (~30s)
- Must discover MCH namespace as `ocm` (NOT hardcode `open-cluster-management`)
- Must check operator replicas
- Must produce verdict

#### Standard Health Check
Say: "How's my hub health?"
- Should run Phases 1-4 (~2-3 min)
- Phase 1: Discover (MCH in `ocm` namespace, version 2.17.0-176, MCE 2.17.0-195, OCP 4.21.9, 6 nodes, 2 managed clusters)
- Phase 2: Learn (read component-registry, healthy-baseline, diagnostic-traps)
- Phase 3: Check (12-layer bottom-up, compare pods to baseline, check traps)
- Phase 4: Pattern Match (cross-ref failure-patterns.md, known-issues.md)
- Must produce report with verdict (expected: HEALTHY for this cluster)
- Must include 9-field format for any issues found

#### Verify Knowledge Files Load
- Must read from `references/knowledge/` (the skill's bundled knowledge, not the app's)
- Must reference diagnostic-traps (14 traps)
- Must reference healthy-baseline.yaml for pod count comparison

### Known Cluster State (from earlier testing)

- MCH namespace: `ocm` (non-default!)
- ACM version: 2.17.0-176
- MCE version: 2.17.0-195
- OCP version: 4.21.9
- Nodes: 6
- Managed clusters: 2 (local-cluster + ashafi-test-az-217-7a13e), both Available
- Operators: multiclusterhub-operator 2/2, multicluster-engine-operator 2/2
- NetworkPolicies: 0, ResourceQuotas: 0
- Non-Running pods: 0 in ACM namespaces
- Search-postgres: 16,886 resources (healthy)
- Console image: quay.io:443/acm-d/console (official)
- All addons Available
- Expected verdict: **HEALTHY**

## Test 3: Z-Stream Pipeline Analysis

**Jenkins URL:** https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/qe-acm-automation-poc/job/alc_e2e_tests/2745/
**VPN required:** Yes (Jenkins is internal)

### What to Test

Run the full pipeline by saying: "Analyze this Jenkins run: https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/qe-acm-automation-poc/job/alc_e2e_tests/2745/"

Verify each stage executes:

1. **Stage 1 (Gather):** `gather.py` runs, produces `core-data.json` with failed tests, cluster landscape, feature grounding. Check that repos are cloned and test context extracted.

2. **Stage 1.5 (Cluster Diagnostic):** Using acm-cluster-health methodology:
   - Discovers MCH namespace dynamically (NOT hardcoded)
   - Checks operator health (replicas)
   - Checks infrastructure guards (NetworkPolicies, ResourceQuotas)
   - Checks pod health against baseline
   - Checks addon health
   - Detects traps (14 traps checked)
   - Produces `cluster-diagnosis.json` with structured health data

3. **Data Enrichment:** Using acm-data-enricher:
   - Task 1: Page objects resolved (import tracing)
   - Task 2: Selector existence verified via acm-ui-source MCP
   - Task 3: Selector timeline analyzed (git history)
   - core-data.json enriched with results

4. **Stage 2 (AI Analysis):** Using acm-failure-classifier:
   - Phase A: Feature grounding, environment health, pattern matching, provably linked grouping
   - Phase B: 12-layer investigation (via acm-cluster-investigator for groups)
   - Phase C: Multi-evidence correlation
   - Phase D: Validation and routing (counterfactual, causal links)
   - Phase E: JIRA correlation
   - Produces `analysis-results.json` with per-test classifications
   - Classifications use correct field names (`per_test_analysis`, NOT `failed_tests`)

5. **Stage 3 (Report):** `report.py` produces:
   - `Detailed-Analysis.md`
   - `analysis-report.html`
   - `per-test-breakdown.json`
   - `SUMMARY.txt`

### Verification Criteria

- Every test has a classification (PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or NO_BUG)
- Every classification has 2+ evidence sources
- Every classification has ruled_out_alternatives
- Every classification has root_cause_layer (1-12) and root_cause_layer_name
- After-all hook cascades are classified NO_BUG (not investigated)
- Dead selectors (3+ tests, console_search.found=false) are classified AUTOMATION_BUG
- No blanket INFRASTRUCTURE without per-test counterfactual verification
- Provably linked grouping uses strict criteria only (same selector+function, same hook, same spec+error+line)

### Report Location

Reports are written to `apps/z-stream-analysis/runs/<timestamp>_<pipeline-name>/` because gather.py and report.py run from the app directory.

---

## Design Principles to Verify

1. **Graceful degradation:** If any MCP is unavailable, skills should note it and proceed with reduced depth, not fail
2. **Vanilla shared skills:** acm-jira-client, acm-ui-source etc. should contain NO app-specific logic -- all workflow intelligence comes from the orchestrator
3. **Standalone operation:** Every skill should work when invoked directly (some with reduced functionality)
4. **No angle brackets in frontmatter:** All SKILL.md files comply
5. **All skills have `name` and `description` in frontmatter**
6. **All skills have `compatibility` field declaring MCP requirements**
