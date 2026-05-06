# MCP Integration

Seven MCP servers provide external data access for the pipeline. Four are used during investigation (Phases 1-3), three are used during live validation (Phase 5). Setup is handled by `mcp/setup.sh` from the repository root.

## Server Summary

| Server | Tools | Source | Phase | Setup |
|--------|-------|--------|-------|-------|
| acm-source | 18 | This repo (`mcp/acm-source-mcp-server/`) | 2, 3, 6, 7 | Local venv |
| jira | 3 | [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server) | 1 | Clone + venv + .env |
| polarion | 7 | This repo (`mcp/polarion/`) | 1 | uvx + .env |
| neo4j-rhacm | 2 | [mcp-neo4j-cypher](https://pypi.org/project/mcp-neo4j-cypher/) (PyPI) | 1-3 | Podman container |
| acm-search | 5 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | 5 | On-cluster SSE + mcp-remote |
| acm-kubectl | 3 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | 5 | npx |
| playwright | 24 | [@playwright/mcp](https://www.npmjs.com/package/@playwright/mcp) (npm) | 3 (conditional), 5 | npx |

## Setup

```bash
cd ai_systems_v2/
bash mcp/setup.sh
# Select: 3) Test Case Generator
```

The setup script:
1. Checks prerequisites (Python, gh CLI, Node.js, npx, uvx, Podman)
2. Clones external repos into `mcp/.external/`
3. Creates virtual environments and installs dependencies
4. Prompts for credentials (JIRA email + API token, Polarion JWT)
5. Deploys acm-search on-cluster (if oc logged in)
6. Generates `.mcp.json` for the test-case-generator app

---

## ACM Source MCP Server

**Tools:** 20
**Source:** `mcp/acm-source-mcp-server/` (our code)
**Used by:** Code Analyzer (Phase 2), UI Discoverer (Phase 3), Test Case Writer (Phase 6), Quality Reviewer (Phase 7)

Searches ACM Console and kubevirt-plugin source code on GitHub. Provides selectors, translations, routes, wizard steps, component source, and test IDs.

### Key Tools

| Tool | Purpose |
|------|---------|
| `set_acm_version(version)` | Set target ACM version (MUST call first) |
| `set_cnv_version(version)` | Set CNV version (Fleet Virt only) |
| `search_code(query, repo)` | Search source code by keyword |
| `get_component_source(path, repo)` | Read full component source file |
| `search_translations(searchTerm)` | Find UI label strings by keyword |
| `get_routes(area)` | Get navigation paths for a console area |
| `get_wizard_steps(path, repo)` | Analyze wizard step structure |
| `get_acm_selectors(area)` | Get QE selectors for area |
| `get_fleet_virt_selectors()` | Get Fleet Virt selectors |
| `find_test_ids(path, repo)` | Find `data-test` attributes |
| `get_patternfly_selectors()` | Get PatternFly component selectors |
| `get_component_types(path, repo)` | Get TypeScript types/interfaces |
| `list_repos()` | List available repositories |
| `get_current_version()` | Get currently set version |

### Usage Rule

Always call `set_acm_version` before any other tool. For Fleet Virt features, also call `set_cnv_version`.

---

## JIRA MCP Server

**Tools:** 3
**Source:** `mcp/.external/jira-mcp-server/` (cloned from stolostron)
**Used by:** Data Gatherer (Phase 1)

Connects to Jira Cloud (Red Hat Atlassian) for ticket investigation.

### Tools

| Tool | Purpose |
|------|---------|
| `get_issue(issue_key)` | Fetch full ticket details (does NOT return issue links) |
| `search_issues(jql, fields, max_results)` | Search via JQL (use for linked tickets) |
| `get_project_components(project_key)` | List project components |

### Credentials

Stored in `mcp/.external/jira-mcp-server/.env`:

```
JIRA_SERVER_URL=https://redhat.atlassian.net
JIRA_ACCESS_TOKEN=<your-api-token>
JIRA_EMAIL=<your-email>
```

Get API token at: https://id.atlassian.com/manage-profile/security/api-tokens

---

## Polarion MCP

**Tools:** 7
**Source:** `mcp/polarion/` (our wrapper)
**Used by:** Data Gatherer (Phase 1)

Read-only access to Polarion test cases in the RHACM4K project. Runs via `uvx` from PyPI.

### Tools

| Tool | Purpose |
|------|---------|
| `get_polarion_work_items(project_id, query)` | Search test cases (Lucene query syntax, NOT JQL) |
| `get_polarion_work_item(project_id, work_item_id, fields)` | Fetch single test case |
| `get_polarion_test_case_summary(project_id, work_item_id)` | Quick summary |
| `get_polarion_test_steps(project_id, work_item_id)` | Get test steps |
| `get_polarion_setup_html(project_id, work_item_id)` | Get setup HTML |
| `get_polarion_work_item_text(project_id, work_item_id)` | Get description text |
| `check_polarion_status()` | Verify Polarion connectivity |

### Credentials

Stored in `mcp/polarion/.env`:

```
POLARION_BASE_URL=https://polarion.engineering.redhat.com/polarion
POLARION_PAT=<your-jwt-token>
```

Requires Red Hat VPN. Project ID is always `RHACM4K`.

---

## Neo4j RHACM Knowledge Graph

**Tools:** 2
**Source:** [mcp-neo4j-cypher](https://pypi.org/project/mcp-neo4j-cypher/) (PyPI via uvx)
**Used by:** Data Gatherer (Phase 1), Code Analyzer (Phase 2), UI Discoverer (Phase 3)

RHACM component dependency graph. Runs as a Podman container. Component and relationship counts depend on the loaded graph extensions (base graph has ~291 nodes).

### Tools

| Tool | Purpose |
|------|---------|
| `get_neo4j_schema()` | List available node types, relationship types |
| `read_neo4j_cypher(query)` | Execute Cypher query (read-only) |

### Example Queries

```cypher
-- What depends on a component?
MATCH (dep)-[:DEPENDS_ON]->(t) WHERE t.label CONTAINS 'GovernanceUI' RETURN dep.label, dep.subsystem

-- All components in a subsystem
MATCH (n:RHACMComponent) WHERE n.subsystem = 'Governance' RETURN n.label, n.type
```

### Setup

Requires Podman with `neo4j-rhacm` container. The setup script creates the container, loads the base graph (~291 nodes), and loads extensions.

---

## ACM Search MCP Server

**Tools:** 5
**Source:** `mcp/.external/acm-mcp-server/servers/postgresql/` (cloned from stolostron)
**Used by:** Live Validator (Phase 5 only)

Fleet-wide resource queries across all managed clusters via the ACM search-postgres database. Runs as a pod on the ACM hub, accessed via SSE over an OpenShift route.

### Tools

| Tool | Purpose |
|------|---------|
| `find_resources(kind, namespace, cluster, labels)` | Search K8s resources across clusters |
| `query_database(sql)` | Raw SQL queries on search DB |
| `list_tables()` | List all search DB tables |
| `get_database_stats()` | Database size and connection info |
| `search_tables(keyword)` | Search table names |

### Setup

Requires:
- Node.js + `mcp-remote` (npm package, stdio-to-SSE bridge)
- ACM hub cluster with search enabled
- On-cluster deployment via `make deploy-prebuilt`

---

## ACM Kubectl MCP Server

**Tools:** 3
**Source:** `mcp/.external/acm-mcp-server/servers/multicluster-kubectl/` (cloned from stolostron)
**Used by:** Live Validator (Phase 5 only)

Multicluster kubectl operations: list managed clusters, run kubectl on hub or spoke clusters, generate kubeconfig for managed clusters.

### Tools

| Tool | Purpose |
|------|---------|
| `clusters()` | List all managed clusters with status |
| `kubectl(command, cluster)` | Run kubectl on hub or specified cluster |
| `connect_cluster(cluster, clusterRole)` | Generate kubeconfig + RBAC for managed cluster |

### Setup

Runs via `npx -y acm-mcp-server@latest`. Requires Node.js 18+ and KUBECONFIG pointing to an ACM hub.

---

## Playwright MCP Server

**Tools:** 24
**Source:** [@playwright/mcp](https://www.npmjs.com/package/@playwright/mcp) (npm)
**Used by:** UI Discoverer (Phase 3, conditional — only when cluster URL provided), Live Validator (Phase 5)

Browser automation for live UI validation. Opens a real browser, navigates pages, takes snapshots of the accessibility tree, clicks elements, fills forms, and takes screenshots.

### Tools (all 24)

| Tool | Purpose |
|------|---------|
| `browser_navigate(url)` | Navigate to URL |
| `browser_navigate_back()` | Go back in history |
| `browser_snapshot()` | Get accessibility tree (elements, roles, refs) |
| `browser_click(ref)` | Click element by ref |
| `browser_type(ref, value)` | Type into field |
| `browser_fill_form(ref, value)` | Fill input field |
| `browser_take_screenshot()` | Capture current state |
| `browser_console_messages()` | Check for JS errors |
| `browser_network_requests()` | Inspect API calls |
| `browser_tabs(action)` | List, open, close, or select tabs |
| `browser_wait_for(ms)` | Wait for page changes |
| `browser_hover(ref)` | Hover element |
| `browser_press_key(key)` | Press keyboard key |
| `browser_select_option(ref, values)` | Select dropdown option |
| `browser_handle_dialog(accept)` | Accept or dismiss dialog |
| `browser_resize(width, height)` | Resize browser window |
| `browser_close()` | Close the page |
| `browser_evaluate(function)` | Evaluate JavaScript on page |
| `browser_generate_locator(ref)` | Generate a Playwright locator |
| `browser_verify_text_visible(text)` | Verify text on page |
| `browser_verify_element_visible(selector)` | Verify element exists |
| `browser_drag(start, end)` | Drag and drop between elements |
| `browser_file_upload(paths)` | Upload files |
| `browser_run_code(code)` | Run Playwright code snippet |

### Usage Pattern

```
browser_navigate(url)     # Go to page
browser_snapshot()         # Get element refs
browser_click(ref)         # Interact
browser_snapshot()         # Verify state changed
browser_take_screenshot()  # Capture evidence
```

### Setup

Runs via `npx @playwright/mcp@latest`. Requires Node.js 18+ and Chromium browser (installed by `npx playwright install chromium`).

---

## Agent-to-MCP Matrix

```
Data Gatherer (Phase 1):
  bash      -> python gather.py, gh pr view, gh pr diff (GitHub CLI via bash)
  jira      -> get_issue, search_issues, get_project_components
  polarion  -> get_polarion_work_items, get_polarion_test_case_summary
  neo4j     -> read_neo4j_cypher (architecture context)

Code Analyzer (Phase 2):
  bash      -> gh pr view, gh pr diff (GitHub CLI via bash)
  acm-source    -> set_acm_version, search_code, get_component_source,
               get_component_types, search_translations, get_routes
  neo4j     -> read_neo4j_cypher (component dependencies)

UI Discoverer (Phase 3):
  acm-source    -> set_acm_version, set_cnv_version, search_code, get_component_source,
               search_translations, get_wizard_steps, get_routes, get_acm_selectors,
               get_fleet_virt_selectors, find_test_ids, get_patternfly_selectors
  playwright -> browser_navigate, browser_snapshot, browser_take_screenshot
               (conditional: only when cluster URL provided, for live element verification)
  bash       -> oc login, oc whoami, oc get mch -A (cluster auth for browser verification)

Live Validator (Phase 5):
  playwright -> browser_navigate, browser_snapshot, browser_click, browser_fill_form,
                browser_take_screenshot, browser_console_messages, browser_network_requests
  bash       -> oc get pods/csv/mch/managedcluster (oc CLI via bash)
  acm-search -> find_resources, query_database
  acm-kubectl -> clusters, kubectl, connect_cluster

Test Case Writer (Phase 6, spot-check only):
  acm-source    -> set_acm_version, get_routes, search_translations

Quality Reviewer (Phase 7):
  acm-source    -> set_acm_version, search_translations, get_routes, get_wizard_steps
```
