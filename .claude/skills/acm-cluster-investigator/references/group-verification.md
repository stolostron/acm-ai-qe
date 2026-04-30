# Per-Test Group Verification (v3.9)

## 4-Point Check

When investigating a GROUP of tests, do NOT apply one result to all tests.

**Step 1:** Investigate the FIRST test fully using the 12-layer model.

**Step 2:** For each SUBSEQUENT test, run the 4-point check:

### 1. SAME CODE PATH?
Does this test call the same function/method that produces the error? Compare `test_file.content`. If the test navigates to a different page, uses a different `cy.get`/`cy.contains` chain, or calls a different API endpoint -> NOT the same code path.

### 2. SAME BACKEND COMPONENT?
Does this test interact with the same backend service? Check `detected_components` and `feature_grounding.component`. A Cluster test and a Search test on the same page use different backends.

### 3. SAME USER ROLE?
Does this test authenticate as the same user type? An admin test and an RBAC test may see the same button but through different RBAC paths. "Button disabled" for admin = likely PRODUCT_BUG. "Button disabled" for restricted user = may be correct behavior.

### 4. SAME ERROR ELEMENT?
Does the error reference the same DOM element (same selector, same `data-testid`, same `aria-label`)? If the first test fails on `#create-btn` and this test fails on `#import-btn`, they are not the same error even if both say "button disabled."

## Decision

- **ALL 4 checks pass** -> Apply group result. Add verification note: `"verified_in_group: code_path=same, backend=same, role=same, element=same"`
- **ANY check fails** -> SPLIT from group. Investigate this test individually using the full 12-layer model INLINE. Record: `"split_from_group: [check] failed -- [detail]"`

## Evidence Requirements

Every test MUST have evidence specific to THAT test. Evidence that only references cluster-wide state without connecting it to THIS test's specific error is insufficient. Per-test evidence must reference:
- The specific selector/element/assertion that failed in THIS test
- The specific verification performed for THIS test
- The specific counterfactual result for THIS test

## Grouping Criteria (what qualifies as a "group")

Only these strict criteria create valid groups:
- Same exact selector + same calling function
- Same before-all hook failure
- Same spec file + exact same error message + same line number

The following are NOT valid grouping criteria:
- "Same feature area" (too broad)
- "Similar error message" (different root causes)
- "Button disabled on same page" (different RBAC paths)
