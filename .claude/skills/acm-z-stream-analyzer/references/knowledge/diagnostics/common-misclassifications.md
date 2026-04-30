# Common Misclassifications

Known cases where the classification pipeline gets confused and why.

---

## 1. Intentional Product Rename -> Classified as PRODUCT_BUG

**What happens:** Product intentionally changes a UI label (e.g., "Pre-upgrade" to "Pre-update"). The app sees the product text changed and automation expects the old text.

**App says:** PRODUCT_BUG (product changed something that broke tests)
**Correct:** AUTOMATION_BUG (the change was intentional, automation needs to update)

**Why it's wrong:** The app can't distinguish "intentional rename" from "accidental breakage" using git diffs alone. Both look the same in code changes.

**How to detect:** If the commit message says "rename", "update text", "rebrand", or the PR is labeled as a planned change -> AUTOMATION_BUG. If the change was unintentional and breaks expected behavior -> PRODUCT_BUG.

**Mitigation:** PR-3 (stale test signal) partially addresses this by looking at commit message patterns, but it's not perfect for label-only changes.

---

## 2. SSE Event Dropping -> Classified as AUTOMATION_BUG

**What happens:** The SSE pipeline silently drops events for a resource type. The UI table doesn't update. The error is "expected element not found in table."

**App says:** AUTOMATION_BUG (selector stale or element missing)
**Correct:** PRODUCT_BUG (data delivery layer is broken)

**Why it's wrong:** "Element not found in table" looks identical whether the selector is wrong OR the data never arrived. `console_search.found` doesn't help because the selector IS correct -- the element should exist but the data didn't arrive to populate it.

**How to detect:** If `console_search.found = true` AND the element is a table row that should contain dynamic data AND manually refreshing the page shows the data -> suspect SSE issue.

**Mitigation:** Source-of-truth validation (PR-6) helps if the backend probe can verify the data exists in the API but not in the UI. SSE-level inspection is not yet implemented.

---

## 3. Degraded Clusters + Functional Test -> Classified as PRODUCT_BUG

**What happens:** Managed clusters are NotReady, causing cluster operations (transfer, destroy) to fail. The UI elements exist, the selectors are correct, but the operation times out.

**App says:** PRODUCT_BUG (selector exists, env looks OK at the broad level)
**Correct:** INFRASTRUCTURE (managed clusters are degraded, operation can't complete)

**Why it's wrong:** The global `environment_score` can be high (0.90+) because the hub itself is healthy. The degraded managed clusters only affect specific operations.

**How to detect:** The Environment Oracle (v3.5) checks managed cluster health per-feature. If `managed_clusters.not_ready > 0` -> INFRASTRUCTURE signal for tests that depend on spoke operations.

**Mitigation:** PR-7 (oracle dependency check) now catches this.

---

## 4. Backend Data Corruption -> Classified as INFRASTRUCTURE

**What happens:** The console backend modifies API responses (wrong status, inflated counts, reversed username). The test sees wrong data but no HTTP errors.

**App says:** INFRASTRUCTURE (probe finds discrepancy between console and cluster)
**Correct:** PRODUCT_BUG (console code is corrupting the data, not the cluster)

**Why it's wrong:** The source-of-truth validation detects the mismatch but historically over-classified as INFRASTRUCTURE because "data doesn't match cluster" sounded like an infra issue.

**How to detect:** PR-6 now explicitly routes console-vs-cluster mismatches to PRODUCT_BUG. If the cluster returns correct data but the console returns different data -> the console code is wrong, not the infrastructure.

**Mitigation:** PR-6 (backend probe cross-reference) addresses this.

---

## 5. Test Assumes Fresh State -> Classified as AUTOMATION_BUG (correct but could be clearer)

**What happens:** Test runs `oc create ns X` but namespace already exists from a previous test run. Or test expects "Create" but cluster has existing config showing "Configure".

**App says:** AUTOMATION_BUG (test doesn't handle existing state)
**Correct:** AUTOMATION_BUG (this IS correct, but the root cause is test isolation)

**Why it matters:** These are correctly classified, but the fix recommendation should specifically call out the idempotency pattern: use `--dry-run=client -o yaml | oc apply -f -` or `{failOnNonZeroExit: false}`.

---

## 6. No Cluster Access -> Reduced Confidence Across the Board

**What happens:** The app can't authenticate to the cluster (re-auth returns 500). All cluster-dependent evidence is missing. The oracle can't run. Backend probes can't execute.

**App says:** Classifications are assigned but with confidence reduced by 0.15 across all tests.
**Impact:** The app falls back to Jenkins-only analysis (error messages, stack traces, selector search). This is still ~85-91% accurate but misses infrastructure issues that require cluster inspection.

**Mitigation:** The app explicitly reports when cluster access is degraded so the user knows the analysis has limitations.
