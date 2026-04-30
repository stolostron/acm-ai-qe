# Phase D: Validate and Route

## Pre-Routing Checks (PR-1 through PR-7)

Applied before final classification routing:

### PR-1: Blank Page Detection
If test shows blank page / `class="no-js"`: check console-api health, auth redirect chain, navigation URL. This is a prerequisite check, not a classification.

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

Mandatory for cluster-wide INFRASTRUCTURE classifications. 9 verification templates:

For each test classified INFRASTRUCTURE, ask: "Would this test PASS if the infrastructure issue were fixed?"
- YES -> infrastructure attribution confirmed
- NO -> reclassify (usually AUTOMATION_BUG)

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

Every test's classification must have a causal chain:
```
root_cause (Layer N) -> intermediate effect -> test error (Layer 12)
```

If the causal chain has gaps, the classification confidence must be reduced.

## D5: Counter-Bias Validation

Checklist to prevent systematic misclassification:

1. **Trap 9 (Anchoring):** When one strong signal found (tampered image, NetworkPolicy), verify it doesn't become the default for all tests. Each test needs independent verification.
2. **Automation vs Infrastructure:** A selector missing from BOTH tampered AND official source is AUTOMATION_BUG, not INFRASTRUCTURE.
3. **Product vs Infrastructure:** Backend returning wrong data with healthy pods is PRODUCT_BUG, not INFRASTRUCTURE.
4. **Layer discrepancy:** Lower layer healthy but higher layer defective = Tier 1 evidence for PRODUCT_BUG (product code issue, not infrastructure).
