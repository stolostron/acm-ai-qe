# Classification Guide

## 7 Classifications

### PRODUCT_BUG
Product code defect causing the test failure. The product is behaving incorrectly.
- **Owner:** Development team
- **Triggers:** Wrong data returned, broken rendering, nil pointer panic, incorrect API response, component crash from code bug, webhook rejects valid requests
- **Evidence needed:** Backend returns wrong data (Tier 1), or layer discrepancy (lower layer healthy, higher layer defective)

### AUTOMATION_BUG
Test code is stale or incorrect. The product is working correctly but the test expects old behavior.
- **Owner:** QE/Automation team
- **Triggers:** Selector renamed in product (test not updated), assertion expects old value, test setup incomplete, PatternFly migration broke selectors
- **Evidence needed:** Selector not in official source (Tier 1) + intentional product rename confirmed

### INFRASTRUCTURE
Environment or infrastructure issue causing the failure. Neither product nor test code is at fault.
- **Owner:** Infrastructure team
- **Triggers:** Operator at 0 replicas, NetworkPolicy blocking, ResourceQuota preventing pod scheduling, node pressure, IDP not configured, spoke cluster down
- **Evidence needed:** Component unhealthy (Tier 1) + test depends on that component

### NO_BUG
Expected behavior or test artifact. No action needed.
- **Owner:** None
- **Triggers:** After-all hook cascade from prior failure, feature intentionally disabled, post-upgrade settling (transient)

### MIXED
Multiple independent root causes contributing to the failure.
- **Owner:** Both development + QE
- **Triggers:** Infrastructure issue AND stale selector in same test, product bug AND test setup issue

### FLAKY
Intermittent failure with no consistent root cause. Passes on retry.
- **Owner:** QE to stabilize
- **Triggers:** Timing-dependent test, race condition, inconsistent element rendering

### UNKNOWN
Insufficient evidence to classify with confidence.
- **Owner:** Needs manual investigation
- **Triggers:** Evidence points in multiple directions, no clear root cause layer, confidence < 0.70

## Multi-Evidence Requirement

Every classification needs ALL 5 criteria:
1. **2+ evidence sources** (single-source insufficient)
2. **Ruled out alternatives** (why NOT other classifications)
3. **MCP tools used** (leverage available servers)
4. **Cross-test correlation** (patterns across failures)
5. **JIRA correlation** (search for related bugs)
