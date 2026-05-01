# Symptom to Layer Mapping

## Starting Layer by Error Pattern

| Error Pattern | Start Layer | Notes |
|---|---|---|
| "element not found", selector missing | 12 (UI) | Check if selector exists in official source first |
| "timed out waiting for" | 12 (UI), trace down | Could be slow render (12) or backend down (9) |
| "Expected X but got Y" (data mismatch) | 11 (Data Flow) | Compare API response vs UI display |
| "500 Internal Server Error" | 9 (Operator) | Check operator pod health, logs |
| "403 Forbidden" | 7 (RBAC) | Check RBAC bindings for test user |
| "401 Unauthorized" | 6 (Auth) | Check token validity, IDP config |
| "connection refused" / "connection timed out" | 3 (Network) | Check NetworkPolicies, service endpoints |
| blank page / `class="no-js"` | Multiple (3, 6, 9, 12) | Check console-api, auth redirect, navigation URL |
| `cy.exec()` failed | 1 (Compute/CI) | CI infrastructure issue |
| CSS `visibility:hidden` / `opacity:0` | 12 (UI) | PF6 uses hidden until triggered -- may be AUTOMATION_BUG |
| Button disabled / `aria-disabled` | 7 or 9 | Check RBAC vs component health |

## Counterfactual Verification Templates

For each cluster-wide issue, verify per-test:

| Error Type | Verification Method | If Fails |
|---|---|---|
| Selector not found | ACM-UI MCP `search_code`. NOT FOUND in official source -> dead selector | Reclassify AUTOMATION_BUG |
| Button disabled | `oc auth can-i`. Backend GRANTS but UI disables -> UI logic bug | Reclassify PRODUCT_BUG |
| Timeout | Check component health. Component healthy AND selector exists -> timing | Reclassify AUTOMATION_BUG |
| Data assertion (X != Y) | Check backend data via API. API correct but UI wrong -> transform bug | Reclassify PRODUCT_BUG |
| Blank page | Check console-api, auth, URL. All OK -> navigation timing | Reclassify AUTOMATION_BUG |
| CSS visibility:hidden / opacity:0 | Check if standard PF6 behavior. PF6 menus use visibility:hidden until triggered | Reclassify AUTOMATION_BUG |
| NetworkPolicy blocking | Verify THIS test's data path uses the blocked service | Reclassify if irrelevant |
| Operator at 0 replicas | Verify THIS test depends on the scaled-down operator | Reclassify if independent |
| ResourceQuota exceeded | Verify THIS test creates new pods/resources | Reclassify if read-only |
