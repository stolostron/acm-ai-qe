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

### PR-3: Temporal Evidence? (v3.2)
- **Data source:** Step 7 (temporal_summary in extracted_context)
- **Trigger:** `stale_test_signal=true` with refactor/rename/PF6 commit in product
- **If YES:** Signal PRODUCT_BUG hypothesis (product changed, automation may be stale)
- **If NO:** Proceed to PR-5

### PR-5: Data Assertion Pre-Check? (v3.3)
- **Data source:** Step 7 (assertion_analysis in extracted_context)
- **Trigger:** `failure_mode_category=data_incorrect` with assertion values extracted (expected vs actual mismatch)
- **If YES:** Signal PRODUCT_BUG (API or backend returned wrong data values)
- **If NO:** Proceed to PR-6

### PR-6: Backend Probe Source-of-Truth? (v3.4)
- **Data source:** Step 4 (backend probes with source-of-truth validation)
- **Trigger:** Probe has `classification_hint` and `anomaly_source`; deterministic K8s-vs-console comparison
- **If console returns wrong data despite healthy K8s:** PRODUCT_BUG (0.85-0.90 confidence)
- **If underlying K8s resource is unhealthy:** INFRASTRUCTURE (0.85-0.90 confidence)
- **If no probe mismatch:** Proceed to PR-7

### PR-7: Environment Oracle Dependency Check (v3.5)
- **Data source:** cluster_oracle.dependency_health
- **Trigger:** Feature dependency is unhealthy (operator down, addon missing, CRD absent)
- **If YES:** INFRASTRUCTURE with specific root cause
- **If NO:** Proceed to PR-4

### PR-4: Feature Knowledge Override (v3.1)
- **Data source:** Feature playbooks (`src/data/feature_playbooks/`)
- **Trigger:** Tiered investigation confirmed a playbook failure path matching the test's error symptoms
- **If YES:** Use playbook classification (playbook specifies PRODUCT_BUG or AUTOMATION_BUG per path)
- **If NO:** Proceed to PR-4b

### PR-4b: Cluster Access Confidence Adjustment (v3.4)
- **Data source:** Cluster authentication status during Stage 2
- **Trigger:** Cluster access is unavailable (re-auth returns 500 or kubeconfig missing)
- **Effect:** Adjusts confidence by -0.15 across all classifications (reduced investigation depth)
- **Note:** Not a routing decision -- always proceeds to D0

### D0: Backend Caused UI Failure?
- **Data source:** Steps 2+4+9 (console log 500s, pod health + backend probes, KG dependencies)
- **How it works:** Cross-references console log for 500 errors, checks component health via KG dependency chain, verifies with ACM-UI MCP
- **If YES:** Forces Path B2 (overrides selector-based Path A)
- **If NO:** Proceed to 3-path routing

## 3-Path Routing

### Path A: Selector Not in Product -> AUTOMATION_BUG
- **Trigger:** `failure_type` is timeout/element_not_found AND `console_search.found == false` AND `backend_caused_ui_failure == false`
- **Evidence:** The selector the test uses doesn't exist in the product source code
- **Confidence:** 0.75-0.90 depending on corroborating evidence (timeline, MCP verification, B7 backend health)

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
- **Tier 1 evidence** (console_search, timeline, backend probes, oracle): 1.0 weight each
- **Tier 2 evidence** (MCP verification, JIRA correlation): 0.5 weight each
- **Minimum threshold:** Combined weight >= 1.8 to classify with high confidence
- **Below threshold:** Classification still assigned but with lower confidence + UNKNOWN flag
