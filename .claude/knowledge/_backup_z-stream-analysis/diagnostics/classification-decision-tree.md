# Classification Decision Tree

The complete decision tree for classifying test failures.

## Role in the v3.8 Architecture (Layer-Based Investigation)

In v3.8, the primary investigation methodology is the 12-layer diagnostic
model (see `diagnostic-layers.md`). Investigation agents trace from the
symptom downward through infrastructure layers to find the root cause,
then classify based on WHO caused the breakage.

The pre-routing checks below (PR-1 through PR-7) now serve as:

- **PR-2 (cascading hook):** Instant classification. After-all hook + prior
  test failed = NO_BUG. Always correct, runs before any investigation agent
  is spawned.
- **All other PRs:** VALIDATION checks applied by the parent agent AFTER
  receiving investigation results. If an investigation agent's finding
  conflicts with a PR signal, the parent investigates the discrepancy
  rather than blindly following either one.

The 3-path routing (Path A/B1/B2) remains as the fallback classification
path when investigation agents are not available or when tests are
classified directly by the parent agent (e.g., obvious shared dead
selector patterns).

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

### PR-6b: Polarion Expected Behavior Check (v4.0)
- **Data source:** cluster_oracle.polarion_discovery + cluster-diagnosis.json
- **Trigger:** Polarion describes expected behavior AND subsystem is healthy AND behavior not delivered
- **If expected behavior not met AND subsystem healthy:** PRODUCT_BUG signal (0.80)
- **Also:** Layer discrepancy (lower layer healthy, higher layer defect) = Tier 1 PRODUCT_BUG evidence
- **If no Polarion data:** Proceed to PR-7

### PR-7: Environment/Diagnostic Context Signals (v4.0)
- **Data source:** cluster-diagnosis.json, cluster_oracle.knowledge_context
- **CRITICAL CHANGE (v4.0):** PR-7 produces CONTEXT SIGNALS, not binding classifications
- **Dependency signals (missing/degraded):** STRONG or MODERATE signals that are INPUTS to the layer investigation, not classifications
- **The layer investigation determines classification**, not PR-7
- **Signals are ADDITIVE, not blanket overrides:**
  - `console_search.found=false` → AUTOMATION_BUG regardless of signals
  - Known failure-signatures pattern → use pattern classification
  - Layer discrepancy → PRODUCT_BUG
- **MANDATORY:** Read `architecture/<area>/failure-signatures.md` before applying signals. Pattern matches take precedence.
- **If NO dependency broken:** Proceed to PR-4

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
- **How it works:** Cross-references console log for 500 errors, checks component health via KG dependency chain, verifies with ACM Source MCP
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
