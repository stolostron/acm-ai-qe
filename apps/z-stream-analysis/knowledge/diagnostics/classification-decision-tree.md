# Classification Decision Tree

The complete decision tree for classifying test failures. Each pre-routing
check runs in order; the first match short-circuits to a classification.

---

## Pre-Routing Checks (run in order, first match wins)

### PR-1: Blank Page?
- **Data source:** Step 2 (console log parser) -- `blank_page_detected`
- **Trigger:** HTML contains `class="no-js"` or `about:blank`
- **If YES:** Page never loaded. Check MCH prerequisites:
  - Prereqs missing -> INFRASTRUCTURE (feature not enabled)
  - Prereqs met -> AUTOMATION_BUG (navigation timing issue)
- **If NO:** Proceed to PR-2

### PR-2: Cascading Hook Failure?
- **Data source:** Step 3 (JUnit parser) -- test name prefix
- **How it works:** Cypress reports hook failures as synthetic testcases:
  `"after all" hook for "RHACM4K-XXXXX"` or `"before all" hook for "..."`
- **Critical distinction:**
  - `"after all"` + prior test in same spec failed = **NO_BUG** (cascading cleanup)
  - `"before all"` = NOT cascading -- investigate normally as its own failure
- **If after-all cascade:** NO_BUG (95% confidence)
- **If not a hook:** Proceed to PR-3

### PR-3: Recent Product Change?
- **Data source:** Step 8 (timeline comparison) -- git log last 2 weeks
- **Trigger:** Product file was refactored recently AND automation not updated
- **If YES:** AUTOMATION_BUG (product changed, test needs update)
- **If NO:** Proceed to PR-5

### PR-5: Selector Drift? (v3.3)
- **Data source:** Step 8b (200-commit git diff)
- **Trigger:** The specific failing selector was renamed/removed in a recent product commit
- **If YES:** AUTOMATION_BUG (selector was renamed, test needs new selector name)
- **If NO:** Proceed to PR-6

### PR-6: Backend Probe Mismatch? (v3.3)
- **Data source:** Steps 9+10 (console API response vs oc CLI ground truth)
- **Trigger:** Console backend returns different data than Kubernetes API
- **If YES:** PRODUCT_BUG (console code is corrupting data)
- **If NO:** Proceed to PR-7

### PR-7: Environment Oracle Dependency Check (v3.5)
- **Data source:** cluster_oracle.dependency_health
- **Trigger:** Feature dependency is unhealthy (operator down, addon missing, CRD absent)
- **If YES:** INFRASTRUCTURE with specific root cause
- **If NO:** Proceed to D0

### D0: Backend Caused UI Failure?
- **Data source:** Steps 4+6+7 (pod health, console log 500s, KG dependencies)
- **How it works:** Cross-references console log for 500 errors, checks component health via KG dependency chain, verifies with ACM-UI MCP
- **If YES:** Forces Path B2 (overrides selector-based Path A)
- **If NO:** Proceed to 3-path routing

## 3-Path Routing

### Path A: Selector Not in Product -> AUTOMATION_BUG
- **Trigger:** `failure_type` is timeout/element_not_found AND `console_search.found == false` AND `backend_caused_ui_failure == false`
- **Evidence:** The selector the test uses doesn't exist in the product source code
- **Confidence:** 0.85-0.95 depending on corroborating evidence (timeline, MCP verification)

### Path B1: Environment Degraded -> INFRASTRUCTURE
- **Trigger:** Mass timeouts across multiple tests AND `feature_health < 0.7` AND resource pressure/pod crashes
- **Evidence:** Cluster-wide or feature-specific infrastructure issue
- **Confidence:** 0.80-0.95

### Path B2: Feature Broken -> PRODUCT_BUG (JIRA-informed)
- **Trigger:** Selector exists in product (`console_search.found == true`) AND environment healthy AND backend healthy
- **Evidence:** Product code has a defect, feature doesn't work despite everything being deployed
- **Investigation:** Uses JIRA MCP to search for known bugs, KG for dependency analysis
- **Confidence:** 0.60-0.85

## Confidence Scoring

Confidence is computed from evidence tier weights:
- **Tier 1 evidence** (console_search, timeline, backend probes): 1.0 weight each
- **Tier 2 evidence** (MCP verification, JIRA correlation): 0.5 weight each
- **Minimum threshold:** Combined weight >= 1.8 to classify with high confidence
- **Below threshold:** Classification still assigned but with lower confidence + UNKNOWN flag
