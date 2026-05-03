---
name: acm-failure-classifier
description: Classify Jenkins pipeline test failures as PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or NO_BUG using a 5-phase AI investigation framework with 12-layer diagnostics, provably linked grouping, counterfactual validation, and multi-evidence requirements. Use when test failures need root-cause classification.
compatibility: "Uses acm-cluster-health (methodology), acm-ui-source (selector verification), acm-neo4j-explorer (dependencies), acm-jira-client (bug correlation), acm-polarion-client (test case context). Requires oc CLI for cluster access. Uses acm-cluster-investigator for per-group deep investigation."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Test Failure Classifier (v4.0)

Analyzes Jenkins pipeline test failures using a 5-phase investigation framework to produce per-test classifications with evidence chains.

**Standalone operation:** If invoked directly with a path to `core-data.json`, performs the full classification analysis. If invoked without data, asks for a Jenkins URL and guides through data gathering first.

## Classifications

| Classification | Meaning | Owner |
|---|---|---|
| **PRODUCT_BUG** | Product code defect causing the failure | Development team |
| **AUTOMATION_BUG** | Test code is stale, wrong selector, wrong assertion | QE/Automation team |
| **INFRASTRUCTURE** | Environment issue (cluster, network, storage, config) | Infrastructure team |
| **NO_BUG** | Expected behavior (after-all cascade, intentionally disabled feature) | No action needed |
| **MIXED** | Multiple root causes contributing | Both dev + QE |
| **FLAKY** | Intermittent failure with no consistent root cause | QE to stabilize |
| **UNKNOWN** | Insufficient evidence to classify | Needs manual investigation |

## Multi-Evidence Requirement

Every classification needs ALL 5 criteria:
1. **Minimum 2 evidence sources** -- single-source evidence is insufficient
2. **Ruled out alternatives** -- document why other classifications don't fit
3. **MCP tools used** -- leverage available MCPs when trigger conditions met
4. **Cross-test correlation** -- check for patterns across all failures
5. **JIRA correlation** -- search for related bugs before finalizing

## Knowledge Directory

KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/z-stream-analysis/

## 5-Phase Framework

### Phase A: Ground and Group

Read `references/phase-a-grouping.md` for full details.

**A0: Feature Grounding** -- Read `feature_grounding` from core-data.json. For each detected area, read `${KNOWLEDGE_DIR}/architecture/<area>/architecture.md` and `data-flow.md`.

**A1: Environment Health** -- Read `cluster-diagnosis.json` if available. Extract `environment_health_score`, `subsystem_health`, `classification_guidance`. When score < 0.8 (DEGRADED/CRITICAL), infrastructure is a hypothesis but NOT automatic -- per-test verification still required.

**A2: Failure Pattern Matching** -- Read `${KNOWLEDGE_DIR}/architecture/<area>/failure-signatures.md`. Match error patterns against known signatures.

**A3: Cross-Test Correlation** -- Find patterns: same selector across multiple tests? Same error message? Same feature area?

**A4: Instant Classification + Provably Linked Grouping**
- After-all hook cascading from prior failure -> **NO_BUG directly** (no investigation needed)
- Dead selector (`console_search.found=false`) shared by 3+ tests -> **AUTOMATION_BUG directly** (unless `recent_selector_changes` hints PRODUCT_BUG)
- Remaining tests: group using STRICT criteria only:
  - Same exact selector + same calling function
  - Same before-all hook failure
  - Same spec + exact error + same line
- "Same feature area", "similar error", "button disabled" are NOT valid grouping criteria

### Phase B: Investigate

Read `references/phase-b-investigation.md` for full details.

For each group (or individual test), use the acm-cluster-investigator skill to perform 12-layer investigation. The investigator:
- Maps symptom to starting layer
- Checks pre-computed data from cluster-diagnosis.json
- Runs counterfactual verification for cluster-wide issues
- Performs 4-point group verification
- Traces down through layers to root cause
- Classifies based on root cause layer + WHO/WHY

**Tiered Playbook (B8):**
- Tier 0: Extracted context only (sufficient for clear selector mismatches)
- Tier 1: + MCP selector verification (acm-ui-source)
- Tier 2: + Repo code reading (test file, page objects)
- Tier 3: + Backend verification (oc commands, cluster state)
- Tier 4: + Cross-system (JIRA bugs, Polarion test cases, knowledge graph)

**Mandatory:** Every classification must include `root_cause_layer` (1-12) and `root_cause_layer_name`.

### Phase C: Correlate

**C1: Multi-Evidence Check** -- Verify each classification has 2+ evidence sources.
**C2: Cascading Analysis** -- If one infrastructure issue explains multiple failures, document the cascade.
**C3: Pattern Correlation** -- Look for systemic patterns (all CLC tests fail -> check hive; all search tests fail -> check search-postgres).

### Phase D: Validate and Route

Read `references/phase-d-validation.md` for full details.

**Pre-routing checks (PR-1 through PR-7):**
- PR-1: Blank page -> check console-api, auth, navigation
- PR-2: After-all hooks -> cascade classification
- PR-3: Temporal signal -> stale_test_signal from data-collector
- PR-4: Feature knowledge -> failure path matching
- PR-5: Data assertion -> has_data_assertion checks
- PR-6: Backend health -> subsystem health from cluster-diagnosis
- PR-6b: Polarion expected behavior -> verify expected vs actual via test case
- PR-7: Oracle + diagnostic signals -> ADDITIVE context, NOT binding classification

**Three-path routing (D0):**
- **Path A:** Selector mismatch confirmed -> AUTOMATION_BUG (with timeline context)
- **Path B1:** Timeout with unhealthy subsystem -> INFRASTRUCTURE (graduated by health score)
- **Path B2:** JIRA-informed or complex -> detailed investigation result

**Counterfactual validation (D-V5):**
- 9 templates for verifying INFRASTRUCTURE claims
- **D-V5c (symmetric):** For AUTOMATION_BUG -- "does backend confirm the test's expectation?"
- **D-V5e (symmetric):** For PRODUCT_BUG -- "is product behavior actually correct?"

**D4b:** Per-test causal link verification -- every test's classification must have a causal chain from root cause to the specific test error.

**D5:** Counter-bias validation -- check for anchoring bias, automation-vs-infra confusion, product-vs-infra confusion.

### Phase E: JIRA Correlation

Read `references/phase-e-jira.md` for full details.

- Search for existing bugs matching the failure pattern
- Optionally create new bug tickets (with user approval)
- Link test failures to JIRA tickets
- Record JIRA correlation in output

## Input

- `core-data.json` -- primary input with failed tests, feature grounding, extracted context, cluster landscape
- `cluster-diagnosis.json` -- optional cluster health findings from Stage 1.5
- `cluster.kubeconfig` -- for oc commands (read-only)
- `${KNOWLEDGE_DIR}/` -- architecture, diagnostics, failure patterns

## Output

Write `analysis-results.json` to the run directory. Read `references/output-schema.md` for the required fields.

Key output sections:
- `per_test_analysis[]` -- per-test classification with evidence
- `summary.by_classification` -- counts by classification type
- `investigation_phases_completed` -- which phases ran
- `cluster_investigation_summary` -- cluster health digest
- `jira_correlation` -- linked bugs

## Schema Compliance

**MANDATORY:** Before writing analysis-results.json, read the output schema reference. The report generator (`report.py`) rejects the file if required fields are missing or named incorrectly. Critical exact field names:
- `per_test_analysis` (NOT `failed_tests`)
- `summary.by_classification` (NOT `classification_breakdown`)
- `investigation_phases_completed` (required array)

## Safety

- Read-only cluster operations only
- Credentials masked in output
- Audit trail maintained in run directory

## Gotchas

1. **Anchoring bias on cluster health** -- A degraded cluster does NOT mean all failures are INFRASTRUCTURE. Each test still needs per-test causal link verification. A single cluster issue can coexist with automation bugs and product bugs.
2. **Selector missing + backend broken is not always INFRASTRUCTURE** -- When a selector is not found AND a subsystem is unhealthy, verify the causal chain. The selector may have been removed by a PR (AUTOMATION_BUG) while the subsystem issue is unrelated.
3. **`console_search.found=false` is not automatic AUTOMATION_BUG** -- Check `recent_selector_changes` first. If the selector was recently removed or renamed in the product repo, it may be PRODUCT_BUG (breaking change without migration).
4. **"Same feature area" is not a valid grouping criterion** -- Two tests in the same area can fail for completely different reasons. Group only by exact shared signals: same selector + same calling function, same hook failure, or same spec + exact error + same line.
5. **Dead selectors need timeline context** -- A selector not found in product source could be (a) never existed (AUTOMATION_BUG), (b) recently removed by a PR (PRODUCT_BUG), or (c) behind a feature flag (check MCH toggles). The timeline determines the classification.
6. **Layer discrepancy detection** -- If the `root_cause_layer` is 9 (operators) but the evidence points to layer 4 (storage), the classification may be wrong. The layer must match the actual root cause, not the symptom layer.
7. **Test file mock data is not cluster state** -- Automation repos contain fixture data and mock objects. Never use test-file content as evidence of what the cluster or product actually does.
