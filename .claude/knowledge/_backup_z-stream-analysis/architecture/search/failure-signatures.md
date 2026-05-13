# Search Failure Signatures

Known failure patterns for Search-related test failures and their classifications.

---

## AUTOMATION_BUG Patterns

### Carbon Design System Selector
- **Error:** `Timed out retrying: Expected to find element: .tf--list-box__menu-item`
- **Pattern:** Any selector starting with `.tf--` (Carbon Design System)
- **Classification:** AUTOMATION_BUG (95% confidence)
- **Explanation:** Console migrated from Carbon to PatternFly in 2023. Selectors like `.tf--list-box__menu-item`, `.tf--dropdown`, `.tf--combo-box` are from the pre-PatternFly era.
- **Fix:** Replace with PatternFly equivalent (`.pf-v6-c-menu__list-item`, `.pf-v6-c-select`, etc.)
- **Evidence:** `console_search.found = false`, automation file last modified 2022

### Stale cluster-dropdown-toggle
- **Error:** `Expected to find element: [data-test-id="cluster-dropdown-toggle"]`
- **Pattern:** Navigation function tries old OCP cluster switcher
- **Classification:** AUTOMATION_BUG (95% confidence)
- **Explanation:** OCP 4.20+ replaced cluster-dropdown-toggle with perspective-switcher-toggle
- **Fix:** Update header.js to use `[data-test-id="perspective-switcher-toggle"]` with retry

### PF6 Portal Visibility
- **Error:** `cy.click() failed because element has visibility:hidden`
- **Pattern:** `pf-v6-c-menu__item-main` has `visibility:hidden`
- **Classification:** AUTOMATION_BUG (90% confidence)
- **Explanation:** PF6 renders menu flyout items in a DOM portal outside the parent container. Cypress `.within()` scope can't reach them.
- **Fix:** Use `{ withinSubject: null }` to break out of `.within()` scope

## INFRASTRUCTURE Patterns

### Search Database Corruption
- **Error:** `ERROR: relation "search.resources" does not exist`
- **Pattern:** SQL query fails because the resources table was dropped
- **Classification:** INFRASTRUCTURE (95% confidence)
- **Explanation:** The search-postgres database schema is corrupted. Since postgres uses emptyDir, restarting the pod would rebuild the index, but while running the corruption persists.
- **Fix:** Restart search-postgres pod or manually recreate the schema

### NetworkPolicy Blocking Search
- **Error:** Search page shows empty results or connection timeout
- **Pattern:** search-api can reach the API but search-postgres is unreachable
- **Classification:** INFRASTRUCTURE (90% confidence)
- **Explanation:** A NetworkPolicy is blocking ingress to search-postgres. All search pods show Running but can't communicate.
- **Fix:** Remove the blocking NetworkPolicy: `oc delete networkpolicy block-search-db -n ocm`

### Search Component Disabled in MCH
- **Error:** Search page/tab not found, search-related elements missing
- **Pattern:** Multiple search tests fail with "element not found"
- **Classification:** INFRASTRUCTURE (95% confidence) -- specifically NO_BUG if intentionally disabled
- **Explanation:** The search component is disabled in MCH spec.overrides.components
- **Fix:** Enable search in MCH or mark tests as expected-to-skip

### search-collector Missing on Spoke
- **Error:** Search returns empty results for resources that exist on a spoke
- **Pattern:** Resources from one specific spoke are absent; other spokes show results
- **Classification:** INFRASTRUCTURE (85% confidence)
- **Explanation:** The search-collector addon is not deployed or is degraded on that spoke
- **Fix:** Check `oc get managedclusteraddon search-collector -n <spoke>`

## PRODUCT_BUG Patterns

### Search Count Off-by-One
- **Error:** Accordion shows count +1 higher than actual results
- **Pattern:** "Pod v1 (6)" but table shows 5 rows
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** Frontend code in SearchResults.tsx adds 1 to items.length in the accordion header
- **File:** `frontend/src/routes/Search/SearchResults/SearchResults.tsx`

### Search Detail Links Wrong Resource
- **Error:** Clicking search result navigates to wrong resource (404 or different resource)
- **Pattern:** URL has namespace and name swapped
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** searchDefinitions.tsx swaps namespace and name parameters in URL construction
- **File:** `frontend/src/routes/Search/searchDefinitions.tsx`

### Search Results Artificially Limited
- **Error:** Only 5 results shown regardless of actual count
- **Pattern:** "1-5 of 5" when hundreds of resources exist
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** Backend injects `limit: 5` into the GraphQL query variables
- **File:** `backend/src/lib/search.ts`

### Search != Operator Broken
- **Error:** Negation query returns opposite results
- **Pattern:** `kind:Pod status:!=Running` returns only Running pods
- **Classification:** PRODUCT_BUG (90% confidence)
- **Explanation:** search-helper.tsx strips the `!` from `!=`, turning it into `=`
- **File:** `frontend/src/routes/Search/search-helper.tsx`
