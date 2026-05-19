# Common Misclassifications

Known cases where the classification pipeline gets confused and why.

---

## 1. Intentional Product Rename -> Classified as PRODUCT_BUG

**What happens:** Product intentionally changes a UI label (e.g., "Pre-upgrade" to "Pre-update"). The app sees the product text changed and automation expects the old text.

**App says:** PRODUCT_BUG (product changed something that broke tests)
**Correct:** AUTOMATION_BUG (the change was intentional, automation needs to update)

**Why it's wrong:** The app can't distinguish "intentional rename" from "accidental breakage" using git diffs alone. Both look the same in code changes.

**How to detect:** If the commit message says "rename", "update text", "rebrand", or the PR is labeled as a planned change -> AUTOMATION_BUG. If the change was unintentional and breaks expected behavior -> PRODUCT_BUG.

**Mitigation:** D-V5e mandatory gate (v4.0) requires ACM-Source MCP verification before PRODUCT_BUG. If product source confirms the new text exists and the old text was intentionally replaced, classification must be AUTOMATION_BUG. PR-3 (stale test signal) provides supporting evidence via commit message patterns.

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

---

## 7. Missing Environment Resource -> Classified as PRODUCT_BUG

**What happens:** Test expects a specific resource (e.g., `open-cluster-management-backup` ManagedClusterSet) that requires an operator to be deployed. The operator is enabled in MCH config but not fully deployed. The CSV export or page correctly shows only what exists.

**App says:** PRODUCT_BUG (expected data missing from export/page)
**Correct:** AUTOMATION_BUG (test hardcodes assumption about environment state)

**Why it's wrong:** The product correctly exports/renders whatever resources exist. The test assertion assumes specific resources exist without verifying.

**How to detect:** D-V5e check #3 requires cross-referencing cluster oracle and cluster-diagnosis.json. If the expected resource's operator/components show `status=missing`, the environment doesn't have the prerequisite.

**Mitigation:** D-V5e mandatory gate (v4.0) requires environment prerequisite cross-reference before PRODUCT_BUG.

---

## 8. PF6 DOM Structure Change -> Classified as PRODUCT_BUG

**What happens:** PF5→PF6 migration changes the DOM structure (e.g., `Text` → `Content`, `ListItem` renders differently). Product source has the correct content unchanged, but test selectors can't find it in the new DOM structure.

**App says:** PRODUCT_BUG (content not found on page)
**Correct:** AUTOMATION_BUG (PF6 DOM structure change, test selector needs update)

**Why it's wrong:** The agent assumes content removal without verifying the product source. The text exists — the DOM traversal path changed.

**How to detect:** D-V5e check #1 requires ACM-Source MCP verification. If `search_translations()` or `search_code()` finds the text in the product source, the content exists — the test selector is wrong.

**Mitigation:** D-V5e mandatory gate (v4.0) requires product source verification. Phase A4 Rule 1c detects PF6 migration patterns (3+ element-not-found with healthy infrastructure).

---

## 9. RBAC Assumption Without Source Check -> Classified as PRODUCT_BUG

**What happens:** A UI element is disabled for a restricted user. The agent assumes RBAC is intentionally disabling the element and classifies as PRODUCT_BUG ("access control blocks user").

**App says:** PRODUCT_BUG (UI restricts user incorrectly)
**Correct:** AUTOMATION_BUG (product has no RBAC logic in that component — disabled state is a PF6/DOM issue)

**Why it's wrong:** The agent infers RBAC logic without checking if the component actually has permission checks. Many UI components have zero RBAC awareness.

**How to detect:** D-V5e check #1 requires searching the product source for permission/access hooks (useAccess, useClusterPermissions, etc.) in the relevant component.

**Mitigation:** D-V5e mandatory gate (v4.0) requires ACM-Source MCP verification of actual product behavior.
