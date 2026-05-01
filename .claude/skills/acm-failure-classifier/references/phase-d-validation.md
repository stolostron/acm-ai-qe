# Phase D: Validate and Route

## Pre-Routing Checks (PR-1 through PR-7)

Applied before final classification routing:

### PR-1: Blank Page Detection
If test shows blank page / `class="no-js"` / empty page body / zero interactive elements: check console-api health, auth redirect chain, navigation URL.

**Routing logic:**

| Condition | Classification | Confidence |
|---|---|---|
| Blank page + non-admin user (RBAC test) + IDP not configured | INFRASTRUCTURE | 0.90 |
| Blank page + Automation page + AAP operator not installed | INFRASTRUCTURE | 0.90 |
| Blank page + Automation page + AAP installed but degraded | INFRASTRUCTURE | 0.85 |
| Blank page + Automation page + AAP installed and healthy | AUTOMATION_BUG | 0.85 |
| Blank page + Fleet Virt page + CNV operator not installed | INFRASTRUCTURE | 0.90 |
| Blank page + feature prerequisite unmet (from playbook) | INFRASTRUCTURE | 0.90 |
| Blank page + console-api healthy + auth OK | AUTOMATION_BUG | 0.80 |

### PR-2: After-All Hook Deduplication
If `hooks.afterAll.failed=true` AND test was not the first failure in its spec: NO_BUG (cascade from prior failure). Already handled in Phase A4.

### PR-3: Temporal Signal
Read `recent_selector_changes.stale_test_signal` from data-collector output. If true: product changed the selector AFTER automation last touched it -> AUTOMATION_BUG hypothesis (but still verify).

### PR-4: Feature Knowledge
Match error against `feature_knowledge.failure_paths`. Known failure paths provide classification hints and confidence levels.

### PR-5: Data Assertion
If `assertion_analysis.has_data_assertion=true` AND `assertion_analysis.data_incorrect=true`: the product returned wrong data -> PRODUCT_BUG signal (if subsystem is healthy).

### PR-6: Backend Health (from cluster-diagnosis.json)
Read subsystem health status. If subsystem is `critical` or `degraded`: INFRASTRUCTURE is a strong hypothesis for tests in that area.

### PR-6b: Polarion Expected Behavior (v4.0)
For PRODUCT_BUG candidates: read the Polarion test case to verify what behavior is EXPECTED. If actual behavior matches Polarion's expected behavior, it's NOT a product bug. Fast-path PRODUCT_BUG identification without needing a JIRA ticket.

### PR-7: Oracle + Diagnostic Context Signals (v4.0)
Read environment health and diagnostic findings. These are **ADDITIVE context** -- they inform but do NOT bind classification. Per-test causal chain is still mandatory.

## Three-Path Routing (D0)

Based on investigation results:

### Path A: Selector Mismatch
`console_search.found=false` in OFFICIAL source (not just test environment). Classification: **AUTOMATION_BUG**. Add timeline context from `recent_selector_changes` if available.

### Path B1: Timeout with Infrastructure Issue
Test timed out AND subsystem is degraded/critical. Classification: **INFRASTRUCTURE**, graduated by environment_health_score. Lower scores = higher confidence in infrastructure attribution.

### Path B2: JIRA-Informed / Complex
Tests that don't clearly match Path A or B1. Use full investigation results, JIRA correlation, and evidence chain. Can result in any classification.

## Counterfactual Validation (D-V5)

Mandatory for ALL cluster-wide INFRASTRUCTURE classifications. 4-step process:

**STEP 1:** Ask "Would this test PASS if the infrastructure issue were fixed?"
- YES -> infrastructure attribution confirmed
- NO -> reclassify (usually AUTOMATION_BUG)

**STEP 2:** Apply the appropriate verification template (see 9 templates below).

**STEP 3: Evidence duplication detection** -- If 5+ tests share IDENTICAL evidence text (same evidence_sources entries, word for word), flag as suspicious blanket attribution. For each duplicated group, verify at least 2 tests individually have test-specific evidence, not cluster-wide-only evidence.

**STEP 4: Per-test evidence requirement** -- Every INFRASTRUCTURE classification from a cluster-wide issue MUST have at least one evidence source specific to THAT test (not just cluster-wide findings). Evidence that only references cluster-wide state (e.g., "tampered console image detected") without per-test verification is INSUFFICIENT. Lower confidence to <= 0.60.

9 verification templates:

For each test classified INFRASTRUCTURE, ask: "Would this test PASS if the infrastructure issue were fixed?"

### D-V5c: Symmetric Validation for AUTOMATION_BUG (v4.0)
Ask: "Does the backend confirm the test's expectation is correct?"
- If backend says the expected value IS correct but product renders differently -> PRODUCT_BUG, not AUTOMATION_BUG
- If backend says the expected value is OUTDATED -> AUTOMATION_BUG confirmed

### D-V5e: Symmetric Validation for PRODUCT_BUG (v4.0)
Ask: "Is the product behavior actually correct (and the test expectation is wrong)?"
- Check recent product changes, feature redesigns, intentional behavior changes
- If product intentionally changed -> AUTOMATION_BUG (test needs updating)
- If product behavior is incorrect -> PRODUCT_BUG confirmed

## D4b: Causal Link Verification

Every test attributed to a shared pattern MUST have a direct causal mechanism linking the pattern to its specific error.

1. **State the causal mechanism:** How does [dominant signal] cause [this test's specific error]?

2. **Check failure_mode_category compatibility:**

| Dominant Signal | Compatible Failure Modes | Incompatible Failure Modes |
|---|---|---|
| Pod restarts / instability | `render_failure`, `timeout_general` | `data_incorrect`, `assertion_logic` |
| Network errors | `render_failure`, `timeout_general`, `server_error` | `data_incorrect`, `element_missing` |
| Backend 500 errors | `server_error`, `render_failure`, `element_missing` | `data_incorrect` |
| Selector removed | `element_missing` | `data_incorrect`, `timeout_general`, `render_failure` |

3. **If incompatible:** Re-classify independently, ignoring the dominant pattern. Example: pod restart (dominant signal) + "expected 5 items, got 0" (`data_incorrect`) = the page rendered (pod was running), so this is a data issue -> likely PRODUCT_BUG.

4. **3-test threshold rule:** If more than 3 tests share the same classification AND the same `root_cause`, independently re-investigate at least 1 test from that group. If re-investigation reveals a different root cause, flag the entire group for review.

Include a `causal_link` field in the reasoning for each test.

## D5: Counter-Bias Validation

Before finalizing any classification, perform ALL applicable checks:

- **If AUTOMATION_BUG:** Was B7 (backend cross-check) performed? Could a backend failure explain the missing element?
- **If PRODUCT_BUG:** Does the selector exist in console source? Is the test logic correct?
- **If INFRASTRUCTURE:** ALL of these:
  1. Is only one test affected? (suggests PRODUCT_BUG or AUTOMATION_BUG instead)
  2. **Trap 9 (Anchoring):** Does this test's specific error REQUIRE the broken component? A degraded search-collector does NOT explain `console_search.found=false`. Each test needs independent evidence.
  3. **Oracle primary source check:** Is the classification coming primarily from oracle/diagnostic data? If yes, verify per-test evidence independently supports INFRASTRUCTURE. Ask: "Would I classify this as INFRASTRUCTURE with only the test's error and extracted context?"
  4. **failure_mode_category match:** `element_missing` and `assertion_logic` are rarely infrastructure. `timeout_general`, `server_error`, and `render_failure` are more likely infrastructure-related.
  5. **Trap 10:** Wrong data values + healthy pods = PRODUCT_BUG (data transformation bug), not INFRASTRUCTURE.
- **If `failure_mode_category == 'data_incorrect'`:** Have you verified the backend API response path? Data mismatch almost never results from infrastructure or selector issues.
- **Dominant signal check:** If a signal (e.g., pod restarts) is cited in more than 5 test classifications, verify at least 2 have a direct `causal_link`. If not, the signal may be over-attributed.
- **Layer discrepancy:** Lower layer healthy but higher layer defective = Tier 1 evidence for PRODUCT_BUG (product code issue, not infrastructure).
