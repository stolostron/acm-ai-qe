---
type: automation
subsystem: search
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - ui/search.md
  - automation/cypress/search.md
version_notes:
  - "Search pods run in MCH namespace (ocm in ACM 5.0, previously open-cluster-management)"
---

# Search Area Knowledge Base

Domain knowledge for writing Search automation tests.

---

## Test Area

| Directory | Specs |
|-----------|-------|
| `src/tests/search/` (Playwright) | 5 specs (welcome-page, search-page, search-details-page, saved-search, overview-page) |
| `cypress/tests/advancedSearch/` (Cypress, legacy) | 1 spec (advanced search) |

Note: Additional search tests may exist in `stolostron/search-e2e-test` (separate repo, selectors available via `acm-source` MCP with `repo="search-e2e"`).

---

## Key Files

| File | Purpose |
|------|---------|
| `cypress/views/common/search.js` | Search page object |
| `cypress/views/common/advancedSearch.js` | Advanced search page object |

---

## Navigation

- Path: `constants.searchPath` = `/multicloud/search`

---

## Tags

`@CLC`, `@e2e`

---

## Key Patterns

- Search uses `search-cluster-proxy` to query spoke clusters
- Advanced search supports field-based queries (kind, name, namespace, cluster, label)
- Search results render in a resource table -- use `cy.getClusterListRow()` pattern
- For Fleet Virt search testing, see fleet-virt.md knowledge base
