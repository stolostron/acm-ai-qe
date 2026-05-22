# Search Area Knowledge Base

Domain knowledge for writing Search automation tests.

---

## Test Area

| Directory | Specs |
|-----------|-------|
| `cypress/tests/advancedSearch/` | 1 spec (advanced search) |

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
