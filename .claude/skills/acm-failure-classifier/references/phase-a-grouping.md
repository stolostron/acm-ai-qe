# Phase A: Ground and Group

## A0: Feature Grounding

Read `feature_grounding` from core-data.json. For each detected feature area:
1. Read `knowledge/architecture/<area>/architecture.md` -- how the subsystem works
2. Read `knowledge/architecture/<area>/data-flow.md` -- data flow through the subsystem
3. Read `feature_knowledge` if present -- oracle-provided failure paths and readiness

## A1: Environment Health Assessment

If `cluster-diagnosis.json` exists:
1. Read `environment_health_score` (0.0-1.0)
2. Read `subsystem_health` for each affected area
3. Read `classification_guidance.pre_classified_infrastructure`
4. Read `counter_signals` -- tests that may NOT be infrastructure despite cluster issues

**Score interpretation:**
- >= 0.8: Healthy. Focus on automation/product bugs.
- 0.5-0.8: Degraded. Infrastructure is a hypothesis for affected areas.
- < 0.5: Critical. Many failures may be infrastructure, but STILL verify per-test.
- < 0.3: Severe. BUT do NOT blanket short-circuit to INFRASTRUCTURE. Tests with stale selectors would fail regardless.

## A1b: Cluster Landscape

Read `cluster_landscape` from core-data.json: MCH version, managed clusters, feature status.

## A2: Failure Pattern Matching

For each detected area, read `knowledge/architecture/<area>/failure-signatures.md`. Match error messages against known signatures. Record matched patterns with their classification hints.

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
