# Phase A: Ground and Group

## A0: Feature Grounding

Read `feature_grounding` from core-data.json. For each detected feature area:
1. Read `${KNOWLEDGE_DIR}/architecture/<area>/architecture.md` -- how the subsystem works
2. Read `${KNOWLEDGE_DIR}/architecture/<area>/data-flow.md` -- data flow through the subsystem
3. Read `feature_knowledge` if present -- oracle-provided failure paths and readiness

## A1: Environment Health Assessment

If `cluster-diagnosis.json` exists, read ALL of these sections:

1. **`overall_verdict` + `environment_health_score`**: If CRITICAL with score < 0.3, many tests may be INFRASTRUCTURE — but per-test verification is still required.

2. **`infrastructure_issues`**: Each entry is Tier 1 evidence (direct cluster state observation) with severity, category, component, namespace, impact, and trap reference. Cross-reference against `classification_guidance.affected_feature_areas`.

3. **`operator_health`**: MCH/MCE operator status and replica counts. MCH at 0 replicas = stale MCH CR status (Trap 1).

4. **`operator_inventory`**: Third-party operator health (AAP, CNV, MTV, GitOps). Check `acm_integration` field for operators with console plugins or addons.

5. **`subsystem_health`**: Per-subsystem status. Use `root_cause` and `evidence_detail` as Tier 1 evidence. Check `traps_triggered` — if a trap was triggered, the obvious diagnosis is WRONG. Check `health_depth` — `pod_level` means only pods were checked; `data_verified` means data integrity was confirmed.

6. **`classification_guidance.pre_classified_infrastructure`**: Confirmed infrastructure issues per feature area (Tier 1 evidence). Does NOT mean all tests in that area are INFRASTRUCTURE — verify each test's specific error is caused by the identified issue.

7. **`classification_guidance.confirmed_healthy`**: Feature areas where infrastructure is ruled out. Skip cluster investigation for these — focus on selectors, JIRA, code changes.

8. **`managed_cluster_detail`**: Per-cluster availability, join status, addon health. Tests requiring spoke data fail if the target cluster is unavailable.

9. **`baseline_comparison`**: Under-replicated deployments and unexpected resources (NetworkPolicies, ResourceQuotas). Strong INFRASTRUCTURE evidence.

10. **`console_plugins`**: Registered ConsolePlugin CRs. Missing plugins = missing UI tabs.

11. **`image_integrity`**: Whether console image matches expected registries. Non-standard image = tampered environment. Tests with CSS/rendering issues should be investigated as potential PRODUCT_BUG (image defective), not AUTOMATION_BUG. Use acm-ui-source to verify selectors against OFFICIAL source.

12. **`component_log_excerpts`**: Pre-extracted error lines from unhealthy pods. Use instead of running `oc logs` — saves context.

13. **`component_restart_counts`**: Pods with >3 restarts are unstable even if currently Running. Catches "all green but recently crashed" signals.

14. **`counter_signals`**: `potential_false_infrastructure` lists tests with `console_search.found=false` that should be AUTOMATION_BUG regardless of infrastructure state. `infrastructure_context_notes` explains whether issues are test artifacts or product-created.

**Score interpretation:**
- >= 0.8: Healthy. Focus on automation/product bugs.
- 0.5-0.8: Degraded. Infrastructure is a hypothesis for affected areas.
- < 0.5: Critical. Many failures may be infrastructure, but STILL verify per-test.
- < 0.3: Severe. BUT do NOT blanket short-circuit to INFRASTRUCTURE. Tests with stale selectors would fail regardless.

**ANTI-ANCHORING RULE:** The cluster diagnostic provides CONTEXT, not pre-determined classification. Start from each test's actual error, then check whether cluster-wide findings explain THAT SPECIFIC error. Do NOT start from "the cluster is broken" and work backward.

**Tampered Console Warning:** When console runs a non-official image, check `console_search.verification.verified_by`. If `"data-collector"`, the selector was already verified against the OFFICIAL source — trust the result. If `verification` is absent, use acm-ui-source `search_code` to verify manually. A selector missing from BOTH tampered AND official source is AUTOMATION_BUG (dead selector), not INFRASTRUCTURE.

## A1b: Cluster Landscape

Read `cluster_landscape` from core-data.json: MCH version, managed clusters, feature status.

## A2: Failure Pattern Matching

For each detected area, read `${KNOWLEDGE_DIR}/architecture/<area>/failure-signatures.md`. Match error messages against known signatures. Record matched patterns with their classification hints.

## A3: Cross-Test Correlation

Scan all failed tests for patterns:
- Same failing_selector across multiple tests -> potential shared root cause
- Same error message across different feature areas -> potential infrastructure cause
- Same `root_cause_file` across tests -> shared code issue

## A3b: Knowledge Graph Context (optional)

If acm-neo4j-explorer available, query subsystem dependencies for affected areas.

## A4: Instant Classification + Provably Linked Grouping

### Instant Classification (no investigation needed)

**After-all hook cascade (PR-2):**
If `hooks.afterAll.failed=true` AND the test was NOT the first failure in its spec -> NO_BUG. The prior test's failure corrupted the after-all hook which then fails all subsequent tests.

**Dead selector (bulk):**
If `console_search.found=false` AND 3+ tests share the same dead selector -> AUTOMATION_BUG directly. Exception: if `recent_selector_changes.intent_assessment = "likely_unintentional"` -> may be PRODUCT_BUG instead.

### Provably Linked Grouping

Remaining tests are grouped using STRICT criteria ONLY:

| Criterion | Valid Group? |
|---|---|
| Same exact selector + same calling function | YES |
| Same before-all hook failure | YES |
| Same spec + exact same error message + same line number | YES |
| Same feature area | NO -- too broad |
| Similar error message | NO -- different root causes |
| "Button disabled" on same page | NO -- different RBAC paths |

Each group is sent to the acm-cluster-investigator skill for 12-layer investigation. Individual tests that don't match any group criteria are investigated individually.
