# MCP Integration Guide

How the three MCP (Model Context Protocol) servers connect Z-Stream Analysis to external systems for failure investigation.

---

## What Is MCP?

Model Context Protocol (MCP) is a JSON-RPC protocol that allows AI agents to call external tools at runtime. Instead of the agent guessing or relying on pre-fetched data, MCP lets the agent query live systems during investigation.

Z-Stream Analysis uses three MCP servers:

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Z-STREAM ANALYSIS AGENT                          │
│                                                                      │
│  "Is selector '#create-btn' in the product code?"                   │
│  "Are there related bugs filed in JIRA?"                            │
│  "What depends on search-api?"                                       │
│                                                                      │
│      ┌─────────┐          ┌─────────┐          ┌─────────┐          │
│      │ ACM-UI  │          │  JIRA   │          │Knowledge│          │
│      │   MCP   │          │   MCP   │          │  Graph  │          │
│      │20 tools │          │24 tools │          │  MCP    │          │
│      └────┬────┘          └────┬────┘          └────┬────┘          │
└───────────┼────────────────────┼────────────────────┼────────────────┘
            │                    │                    │
            ▼                    ▼                    ▼
  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
  │   GitHub API    │  │    JIRA API     │  │   Neo4j DB      │
  │                 │  │                 │  │                  │
  │ stolostron/     │  │  Red Hat JIRA   │  │  RHACM component│
  │   console      │  │  (issues, bugs, │  │  dependency      │
  │ kubevirt-ui/    │  │   stories)      │  │  graph           │
  │   kubevirt-     │  │                 │  │                  │
  │   plugin        │  │                 │  │                  │
  │ QE test repos   │  │                 │  │                  │
  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

**Without MCP:** The agent can only classify based on data already in `core-data.json` (pre-extracted selectors, console log patterns, environment health).

**With MCP:** The agent can actively investigate — search product source code, read feature stories, find related bugs, trace component dependencies — making classifications more accurate and actionable.

---

## Two MCP Access Patterns

MCP tools are accessed differently depending on the stage:

```
┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 1: Python MCP Clients                                        │
│  ─────────────────────────────                                       │
│  gather.py imports ACMUIMCPClient and KnowledgeGraphClient           │
│  These are Python classes that call MCP servers via subprocess        │
│  Used for pre-computing data before AI analysis                      │
│                                                                      │
│  Files:                                                              │
│    src/services/acm_ui_mcp_client.py (293 lines)                     │
│    src/services/knowledge_graph_client.py (513 lines)                │
│                                                                      │
│  Purpose: CNV version detection, element inventory pre-computation   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  STAGE 2: Claude Code Native MCP                                     │
│  ───────────────────────────────                                     │
│  The AI agent calls MCP tools directly via Claude Code's built-in    │
│  MCP integration (no Python client needed)                           │
│                                                                      │
│  Tool call format:                                                   │
│    mcp__acm-ui__search_code(query='create-btn', repo='acm')         │
│    mcp__jira__search_issues(jql='project = ACM AND ...')             │
│    mcp__user-neo4j-rhacm__read_neo4j_cypher(query='MATCH ...')      │
│                                                                      │
│  Purpose: Active investigation during 5-phase analysis               │
└──────────────────────────────────────────────────────────────────────┘
```

| Stage | Access Method | MCP Servers Used | Purpose |
|-------|---------------|------------------|---------|
| Stage 1 | Python classes (`ACMUIMCPClient`, `KnowledgeGraphClient`) | ACM-UI | Pre-compute CNV version, element inventory |
| Stage 2 | Claude Code native (`mcp__<server>__<tool>`) | All three (ACM-UI, JIRA, Knowledge Graph) | Active investigation during analysis |
| Stage 3 | None | None | Report generation uses no MCP tools |

---

## MCP Server 1: ACM-UI (20 Tools)

### What It Is

A GitHub-backed code search and source access server for the ACM Console (`stolostron/console`) and kubevirt-plugin (`kubevirt-ui/kubevirt-plugin`) repositories. It accesses specific branch versions of these repos via the GitHub API, allowing the agent to search product source code, look up selectors, read component files, and check UI translations.

**Tool prefix:** `mcp__acm-ui__`

### Why It Matters

When a Cypress test fails because an element isn't found, the core question is: "Does this element still exist in the product code?" The ACM-UI MCP answers this by searching the actual product repository on the correct branch version.

Without ACM-UI MCP, the agent relies only on the pre-computed `console_search` from Stage 1 (which uses local grep on cloned repos). ACM-UI MCP adds:
- Cross-branch search (different ACM versions)
- QE-proven selector catalogs from test repos
- UI text and translation lookup
- Wizard step extraction
- PatternFly CSS selector reference

### Version Management

ACM and CNV versions are **independent** — each maps to a separate repository branch:

```
ACM Version        Branch                  Repository
───────────────────────────────────────────────────────
2.11 - 2.15        release-2.{11-15}       stolostron/console
2.16 (latest GA)   release-2.16            stolostron/console
2.17 (dev)         main                    stolostron/console

CNV Version        Branch                  Repository
───────────────────────────────────────────────────────
4.14 - 4.20        release-4.{14-20}       kubevirt-ui/kubevirt-plugin
4.21 (latest GA)   release-4.21            kubevirt-ui/kubevirt-plugin
4.22 (dev)         main                    kubevirt-ui/kubevirt-plugin
```

**Setting the correct version is the first thing the agent does:**

```
At start of Stage 2:
mcp__acm-ui__set_acm_version(version='2.16')   ← Match target cluster ACM version

If VM tests are present:
mcp__acm-ui__detect_cnv_version()               ← Auto-detect from connected cluster
  OR
mcp__acm-ui__set_cnv_version(version='4.21')    ← Set manually
```

If the wrong version is set, selector searches may return false negatives (element exists in product but on a different branch).

### How It Is Used: Stage 1

In `gather.py`, the Python `ACMUIMCPClient` class is used for two tasks:

```
gather.py
    │
    ├── Step 5: Repository Cloning
    │   └── acm_ui_mcp_client.detect_cnv_version()
    │       → Determines which kubevirt-plugin branch to clone
    │       → Example: CNV 4.20.3 on cluster → clone release-4.20
    │
    └── Step 7: Element Inventory
        └── _gather_element_inventory()
            → Searches cloned repos for failing selectors
            → Writes element-inventory.json
```

**Example: CNV Version Detection**
```python
# In gather.py, during Step 5
cnv_info = self.acm_ui_mcp_client.detect_cnv_version()
# Returns: CNVVersionInfo(version='4.20', branch='release-4.20',
#                          detected_from='cluster')
# Used to clone: kubevirt-ui/kubevirt-plugin @ release-4.20
```

### How It Is Used: Stage 2

The AI agent calls ACM-UI tools directly during investigation. Here are the key scenarios:

#### Scenario 1: Verifying a Selector Exists in Product Code

**When:** Test fails with `element_not_found` and `console_search.found = false`

```
Agent reads core-data.json:
  console_search.found = false for '#create-btn'

Agent verifies via MCP (broader search than local grep):

  mcp__acm-ui__search_code(query='create-btn', repo='acm')
  ─────────────────────────────────────────────────────────
  Result: No matches found in stolostron/console@release-2.16

  mcp__acm-ui__search_code(query='create', repo='acm')
  ─────────────────────────────────────────────────────
  Result: Found 'cluster-create-btn' in
    frontend/src/routes/Infrastructure/Clusters/ClusterCreate.tsx:42

Conclusion: Selector was renamed from '#create-btn' to '#cluster-create-btn'
Classification: AUTOMATION_BUG (confidence: 0.92)
Recommended fix: Update selector in cypress/views/cluster.js
```

#### Scenario 2: Looking Up QE-Proven Selectors

**When:** Agent needs to verify what selectors QE teams use in their test repos

```
Agent checks QE selector catalog:

  mcp__acm-ui__get_acm_selectors(source='catalog', component='clc')
  ──────────────────────────────────────────────────────────────────
  Result: Cluster Lifecycle selectors from stolostron/clc-ui-e2e:
    createClusterButton: '[data-testid="createCluster"]'
    clusterNameInput: '#clusterName'
    ...

Comparison: Test uses '#create-btn', catalog shows '[data-testid="createCluster"]'
→ Confirms selector mismatch
```

#### Scenario 3: Understanding Wizard Flow

**When:** Test fails during a multi-step wizard and the agent needs to understand which step is affected

```
  mcp__acm-ui__get_wizard_steps(
    path='frontend/src/wizards/ClusterCreation/CreateClusterWizard.tsx',
    repo='acm'
  )
  ──────────────────────────────────────────────────────────────────
  Result: Wizard steps:
    Step 1: "Infrastructure Provider" (always visible)
    Step 2: "Cluster Details" (always visible)
    Step 3: "Node Pools" (visible when: provider !== 'existing')
    Step 4: "Review" (always visible)

Test fails at Step 3 but test expects Step 3 to always be visible.
Product change added a condition (provider !== 'existing').
→ AUTOMATION_BUG: Test doesn't account for conditional step visibility
```

#### Scenario 4: Checking UI Text Changes

**When:** Test asserts on button text or error messages that may have changed

```
  mcp__acm-ui__search_translations(query='Create cluster')
  ──────────────────────────────────────────────────────────
  Result:
    key: "cluster.create.button" → "Create cluster"
    key: "cluster.create.title" → "Create a cluster"

Test asserts: cy.contains('Create Cluster')  ← Capital C
Product text: 'Create cluster'                ← lowercase c
→ AUTOMATION_BUG: Case mismatch in assertion
```

#### Scenario 5: VM Test Investigation

**When:** Test involves virtualization features (Fleet Virt / kubevirt)

```
  mcp__acm-ui__detect_cnv_version()
  ──────────────────────────────────
  Result: CNV 4.20.3, branch release-4.20

  mcp__acm-ui__get_fleet_virt_selectors()
  ────────────────────────────────────────
  Result: Fleet Virt UI selectors from kubevirt-plugin@release-4.20:
    vmListTable: '[data-test-id="virtual-machine-list"]'
    vmNameColumn: '[data-test-col="name"]'
    ...

  mcp__acm-ui__search_code(query='vm-action-btn', repo='kubevirt')
  ──────────────────────────────────────────────────────────────────
  Result: Found in src/views/virtualmachines/actions/VmActions.tsx:89
```

### Full Tool Reference

| Category | Tool | Purpose | Typical Phase |
|----------|------|---------|---------------|
| **Version** | `set_acm_version` | Set ACM Console branch (2.11-2.17) | Start of Stage 2 |
| | `set_cnv_version` | Set kubevirt-plugin branch (4.14-4.22) | Start of Stage 2 |
| | `detect_cnv_version` | Auto-detect CNV from cluster | Start of Stage 2 |
| | `list_versions` | Show version-to-branch mappings | As needed |
| | `get_current_version` | Get active version | As needed |
| | `list_repos` | List repos with settings | As needed |
| | `get_cluster_virt_info` | Cluster virt details | Phase B |
| **Search** | `search_code` | GitHub code search across repos | Phase B4 |
| | `find_test_ids` | Find data-testid/aria-label in a file | Phase B4 |
| | `get_component_source` | Read raw source code | Phase B4, B6 |
| | `search_component` | Find component files by name | Phase B4 |
| | `get_route_component` | Map URL path to source files | Phase B4 |
| **Selectors** | `get_acm_selectors` | QE-proven selectors from test repos | Phase B4 |
| | `get_fleet_virt_selectors` | Fleet Virt UI selectors | Phase B4 |
| | `get_patternfly_selectors` | PatternFly v6 CSS fallbacks | Phase B4 |
| **Context** | `search_translations` | Find exact UI text (i18n strings) | Phase B4 |
| | `get_wizard_steps` | Extract wizard step structure | Phase B4 |
| | `get_component_types` | TypeScript type/interface defs | Phase B4 |
| | `get_routes` | All ACM Console navigation paths | Phase B4 |

---

## MCP Server 2: JIRA (24 Tools)

### What It Is

A full-featured JIRA integration server providing authenticated access to Red Hat JIRA. The agent can search for issues, read feature stories, create bugs, link related failures, add comments, and manage watchers.

**Tool prefix:** `mcp__jira__`

### Why It Matters

JIRA provides two types of context that fundamentally improve classification accuracy:

1. **Feature intent** — What should the code do? If a feature story says "users can create clusters with digest references" and the product returns a 500 error when doing this, that's a PRODUCT_BUG regardless of what the test code looks like.

2. **Known issues** — Has this bug already been filed? If ACM-12345 says "search-api returns 500 on large result sets" and the failing test hits search-api with a large query, that's a confirmed PRODUCT_BUG with a JIRA reference.

Without JIRA MCP, the agent classifies based on symptoms alone. With JIRA, the agent classifies based on symptoms + product intent + existing bug knowledge.

### How It Is Used: Stage 1

Not used in Stage 1. JIRA MCP is exclusively a Stage 2 tool.

### How It Is Used: Stage 2

JIRA MCP is used in three investigation phases:

```
Phase D (Path B2) ──────────────────────────────────────────
│  When failure doesn't match selector mismatch or timeout
│  Agent searches JIRA for the feature story behind the test
│
│  1. Extract Polarion ID from test name (e.g., RHACM4K-3046)
│  2. Search JIRA: mcp__jira__search_issues(jql="summary ~ 'RHACM4K-3046'")
│  3. Read story: mcp__jira__get_issue(issue_key='ACM-22079')
│  4. Compare acceptance criteria vs actual failure
│  5. Classify based on feature intent
│
Phase E (E2-E6) ────────────────────────────────────────────
│  Feature context and bug correlation for ALL classifications
│
│  E2: Search for feature stories  → mcp__jira__search_issues
│  E3: Read acceptance criteria    → mcp__jira__get_issue
│  E4: Search for related bugs     → mcp__jira__search_issues
│  E5: Read matching bug details   → mcp__jira__get_issue
│  E6: Create/link issues          → mcp__jira__create_issue / link_issue
│
Phase D (D4: Final Validation) ─────────────────────────────
│  For ANY classification
│  Search for existing bugs that match the failure
│  Adjust confidence if known issue found
```

#### Scenario 1: Feature Story Informs Classification (Path B2)

**When:** Test fails with assertion error — product returns unexpected response

```
Test name: "RHACM4K-3046 - Verify cluster upgrade with digest"
Error: "Expected status 200 but got 500"

Agent extracts Polarion ID: RHACM4K-3046

  mcp__jira__search_issues(
    jql="summary ~ 'RHACM4K-3046' OR description ~ 'RHACM4K-3046'",
    max_results=5
  )
  ──────────────────────────────────────────────────────────────────
  Result: ACM-22079 "ClusterCurator: Support digest-based upgrades"

  mcp__jira__get_issue(issue_key='ACM-22079')
  ─────────────────────────────────────────────
  Result:
    Summary: "ClusterCurator: Support digest-based upgrades"
    Acceptance Criteria:
      - "Cluster upgrades using digest references must succeed"
      - "ClusterCurator should resolve digest to tag before upgrade"
    Linked PRs: github.com/stolostron/cluster-curator/pull/456
    Fix Version: ACM 2.16

Analysis:
  Feature story says digest upgrades must work.
  Product returns 500 on digest upgrade attempt.
  Linked PR recently merged → possible regression.
→ Classification: PRODUCT_BUG (confidence: 0.90)
→ Recommended fix: "Investigate regression from PR #456 in cluster-curator"
```

#### Scenario 2: Known Bug Correlation (Phase E4-E5)

**When:** Agent finds a related bug already filed in JIRA

```
Test fails with 500 from search-api.
Agent already classified as PRODUCT_BUG in Phase D.

Phase E4:
  mcp__jira__search_issues(
    jql="project = ACM AND type = Bug AND status != Closed
         AND (summary ~ 'search-api' OR summary ~ 'search 500')",
    max_results=10
  )
  ──────────────────────────────────────────────────────────────────
  Result: ACM-12345 "search-api returns 500 on queries with > 1000 results"

Phase E5:
  mcp__jira__get_issue(issue_key='ACM-12345')
  ─────────────────────────────────────────────
  Result:
    Status: Open
    Priority: Major
    Description: "When search query returns > 1000 results,
                  search-api returns HTTP 500 instead of paginated response"
    Affected versions: ACM 2.16.0, 2.16.1

Match: Test queries search-api and gets 500. Known issue ACM-12345.
→ Classification: PRODUCT_BUG confirmed
→ JIRA correlation: ACM-12345
→ Recommended fix: "Known issue ACM-12345 — track fix in ACM 2.16.2"
→ Confidence: +0.05 (JIRA correlation found)
```

#### Scenario 3: Bug Filing (Phase E6)

**When:** Agent identifies a definitive new PRODUCT_BUG with no existing JIRA

```
  mcp__jira__create_issue(
    project_key='ACM',
    summary='search-api: 500 error on digest-based cluster upgrade query',
    description='Found during z-stream analysis of pipeline acm-e2e #123.\n\n'
                'Error: search-api returns HTTP 500 when querying clusters '
                'with digest-based upgrade references.\n\n'
                'Evidence:\n'
                '- Console log shows 500 Internal Server Error\n'
                '- Environment healthy (score 0.95)\n'
                '- Test logic verified correct via RHACM4K-3046 acceptance criteria\n'
                '- Regression likely from PR #456 in cluster-curator',
    issue_type='Bug',
    priority='Major',
    components=['Search'],
    work_type='46653',
    due_date='2026-03-01'
  )
  ──────────────────────────────────────────────────────────────────
  Result: ACM-99999 created

  mcp__jira__link_issue(
    link_type='Relates',
    inward_issue='ACM-99999',
    outward_issue='ACM-22079'
  )
  → Links new bug to the feature story
```

### Full Tool Reference

| Category | Tool | Purpose | Typical Phase |
|----------|------|---------|---------------|
| **Search** | `search_issues` | JQL search for bugs, stories, epics | D (B2), E2, E4 |
| | `search_issues_by_team` | Find issues by team members | E4 |
| | `search_users` | Search JIRA users by name, email, or username | As needed |
| **Read** | `get_issue` | Full issue details (story, acceptance criteria, PRs) | D (B2), E3, E5 |
| | `debug_issue_fields` | Raw field dump for debugging | As needed |
| **Create** | `create_issue` | File new bug with evidence | E6 |
| | `update_issue` | Update priority, components, etc. | E6 |
| | `transition_issue` | Change issue status | E6 |
| **Link** | `link_issue` | Link related issues (Relates, Blocks, Duplicates) | E6 |
| | `add_comment` | Add analysis findings as comment | E6 |
| | `log_time` | Log investigation time | E6 |
| **Project** | `get_projects` | List accessible projects | As needed |
| | `get_project_components` | List components in a project | E2 |
| | `get_link_types` | Available link types | E6 |
| **Teams** | `list_teams` / `add_team` / `remove_team` | Manage team configs | Setup |
| | `assign_team_to_issue` | Add team as watchers | E6 |
| | `add_watcher_to_issue` / `remove_watcher_from_issue` | Manage watchers | E6 |
| | `get_issue_watchers` | List watchers | As needed |
| **Aliases** | `list_component_aliases` / `add_component_alias` / `remove_component_alias` | Component shortcuts | Setup |

---

## MCP Server 3: Knowledge Graph (Neo4j RHACM)

### What It Is

A Neo4j graph database containing the dependency relationships between all RHACM (Red Hat Advanced Cluster Management) components. The agent queries it using Cypher (Neo4j's query language) to understand which components depend on which, enabling cascading failure detection.

**Tool:** `mcp__user-neo4j-rhacm__read_neo4j_cypher`

**Status:** Optional — may not be connected in all environments. The agent degrades gracefully when unavailable.

### Why It Matters

When `search-api` returns a 500 error, is it a bug in `search-api` itself, or did one of its dependencies (`search-collector`, `search-indexer`) fail and cause a cascade? Without the Knowledge Graph, the agent can only guess based on the error message. With it, the agent can trace the dependency chain:

```
Without Knowledge Graph:
  "500 from search-api" → PRODUCT_BUG in search-api (maybe wrong)

With Knowledge Graph:
  search-api ──depends on──► search-collector ──depends on──► search-indexer
  search-indexer is down → search-collector fails → search-api returns 500
  → PRODUCT_BUG in search-indexer (actual root cause)
```

### How It Is Used: Stage 1

In `gather.py`, the Python `KnowledgeGraphClient` checks if the Knowledge Graph is available and flags it in `core-data.json`. No queries are executed during Stage 1 — the client just records availability for the AI agent.

```python
# In gather.py initialization
if is_knowledge_graph_available():
    self.knowledge_graph_client = get_knowledge_graph_client()
```

### How It Is Used: Stage 2

The Knowledge Graph is queried in three phases:

```
Phase B5: Backend Component Analysis
│  "Test error mentions 'search-api'. What depends on search-api?"
│
│  mcp__user-neo4j-rhacm__read_neo4j_cypher(
│    query="MATCH (dep)-[:DEPENDS_ON]->(c:RHACMComponent)
│           WHERE c.label =~ '(?i).*search-api.*'
│           RETURN DISTINCT dep.label as dependent"
│  )
│  → Result: console, observability-dashboard
│  → "If search-api is down, console and observability are also affected"
│
Phase C2: Cascading Failure Detection
│  "3 tests fail in different areas. Do they share a dependency?"
│
│  mcp__user-neo4j-rhacm__read_neo4j_cypher(
│    query="MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent)
│           WHERE c.label IN ['search-api', 'console', 'observability-dashboard']
│           WITH common, count(DISTINCT c) as cnt
│           WHERE cnt >= 2
│           RETURN common.label as shared_dependency"
│  )
│  → Result: search-collector
│  → "All 3 components depend on search-collector — cascading failure"
│
Phase E0: Subsystem Context Building
│  "search-api failed. What subsystem is it in? What else is in that subsystem?"
│
│  mcp__user-neo4j-rhacm__read_neo4j_cypher(
│    query="MATCH (c:RHACMComponent)
│           WHERE c.label =~ '(?i).*search-api.*'
│           RETURN c.label, c.subsystem, c.type"
│  )
│  → Result: subsystem='Search'
│
│  mcp__user-neo4j-rhacm__read_neo4j_cypher(
│    query="MATCH (c:RHACMComponent)
│           WHERE c.subsystem = 'Search'
│           RETURN c.label, c.type"
│  )
│  → Result: search-api, search-collector, search-indexer, search-operator
│  → "These are all the components in the Search subsystem"
│  → Used in Phase E2 to build better JIRA search queries
```

#### Scenario: Cascading Failure Detection

**When:** Multiple tests fail across different feature areas but share an underlying dependency

```
Failed tests:
  1. "search results should display" → search-api 500
  2. "observability dashboard loads" → observability-api timeout
  3. "cluster details show metrics" → metrics-collector error

Without Knowledge Graph:
  → 3 separate PRODUCT_BUGs filed (wrong)

With Knowledge Graph:

  Phase B5 (per test):
  ┌────────────────────────────────────────────────────┐
  │  Test 1: search-api                                │
  │  → deps: search-collector, search-indexer          │
  │                                                    │
  │  Test 2: observability-api                         │
  │  → deps: search-collector, thanos-query            │
  │                                                    │
  │  Test 3: metrics-collector                         │
  │  → deps: search-collector                          │
  └────────────────────────────────────────────────────┘

  Phase C2 (cross-test):
  ┌────────────────────────────────────────────────────┐
  │  Common dependency query:                          │
  │  Components: [search-api, observability-api,       │
  │               metrics-collector]                   │
  │  Shared dependency: search-collector               │
  │  Affected count: 3 out of 3                        │
  └────────────────────────────────────────────────────┘

  → Root cause: search-collector failure
  → 1 PRODUCT_BUG in search-collector (not 3 separate bugs)
  → Tests 1, 2, 3 are all symptoms of the same root cause
```

### Known Subsystems

| Subsystem | Key Components |
|-----------|----------------|
| Governance | grc-policy-propagator, config-policy-controller, governance-policy-framework |
| Search | search-api, search-collector, search-indexer, search-operator |
| Cluster | cluster-curator, managedcluster-import-controller, registration |
| Provisioning | hive, hypershift, assisted-service, capi-provider |
| Observability | thanos-query, thanos-receive, metrics-collector, grafana |
| Virtualization | kubevirt-operator, virt-api, virt-controller, virt-handler |
| Console | console, console-api, acm-console |
| Infrastructure | klusterlet, multicluster-engine, foundation |
| Application | application-manager, subscription, channel |

### Common Cypher Query Templates

```cypher
-- Direct dependencies of a component
MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent)
WHERE c.label =~ '(?i).*{component}.*'
RETURN dep.label as dependency, dep.subsystem

-- What depends on a component (reverse lookup)
MATCH (dep:RHACMComponent)-[:DEPENDS_ON]->(c:RHACMComponent)
WHERE c.label =~ '(?i).*{component}.*'
RETURN dep.label as dependent, dep.subsystem

-- Common dependency across multiple components
MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent)
WHERE c.label IN ['{comp1}', '{comp2}', '{comp3}']
WITH common, count(DISTINCT c) as cnt
WHERE cnt >= 2
RETURN common.label as shared_dependency, cnt as shared_by_count

-- All components in a subsystem
MATCH (c:RHACMComponent)
WHERE c.subsystem = '{subsystem}'
RETURN c.label, c.type

-- Transitive dependencies (2 levels deep)
MATCH path = (c:RHACMComponent)-[:DEPENDS_ON*1..2]->(dep:RHACMComponent)
WHERE c.label =~ '(?i).*{component}.*'
RETURN [n in nodes(path) | n.label] as chain
```

---

## MCP Trigger Matrix

When should the agent call which MCP tool? This matrix maps investigation triggers to tool calls:

### Always (Start of Stage 2)

| Trigger | Tool | Call |
|---------|------|------|
| Start of investigation | `set_acm_version` | `mcp__acm-ui__set_acm_version(version='2.16')` |
| VM test detected in job name | `detect_cnv_version` | `mcp__acm-ui__detect_cnv_version()` |

### Phase B4 (Per Test)

| Trigger | Tool | Call |
|---------|------|------|
| `console_search.found = false` | `search_code` | `mcp__acm-ui__search_code(query='{selector}', repo='acm')` |
| Need QE-proven selectors | `get_acm_selectors` | `mcp__acm-ui__get_acm_selectors(source='catalog', component='{area}')` |
| Need to read product source | `get_component_source` | `mcp__acm-ui__get_component_source(path='{file}', repo='acm')` |
| UI text assertion failure | `search_translations` | `mcp__acm-ui__search_translations(query='{text}')` |
| Wizard step failure | `get_wizard_steps` | `mcp__acm-ui__get_wizard_steps(path='{file}', repo='acm')` |

### Phase B5 (Per Test)

| Trigger | Tool | Call |
|---------|------|------|
| `detected_components` has entries | `read_neo4j_cypher` | Dependency query for each component |

### Phase C2

| Trigger | Tool | Call |
|---------|------|------|
| Multiple tests share components | `read_neo4j_cypher` | Common dependency query |

### Phase D (Path B2)

| Trigger | Tool | Call |
|---------|------|------|
| Polarion ID in test name | `search_issues` | `mcp__jira__search_issues(jql="summary ~ 'RHACM4K-XXXX'")` |
| Feature story found | `get_issue` | `mcp__jira__get_issue(issue_key='ACM-XXXXX')` |

### Phase E

| Trigger | Tool | Call |
|---------|------|------|
| Need subsystem context | `read_neo4j_cypher` | Component + subsystem query |
| Search for feature stories | `search_issues` | JQL by component/subsystem/keywords |
| Read story details | `get_issue` | Full story with acceptance criteria |
| Search for related bugs | `search_issues` | JQL for open bugs matching failure |
| Read bug details | `get_issue` | Full bug details for matching |
| File new bug | `create_issue` | Create with classification evidence |
| Link related issues | `link_issue` | Link failures to root cause |

---

## Graceful Degradation

Each MCP server can be unavailable. The system is designed to work without any MCP server connected, with progressively better results as more servers are available:

```
                        Classification Accuracy
                        ──────────────────────►

┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ No MCP        │  │ ACM-UI Only   │  │ ACM-UI +      │  │ All Three     │
│               │  │               │  │ JIRA          │  │               │
│ Uses only     │  │ + Cross-repo  │  │ + Feature     │  │ + Dependency  │
│ core-data.json│  │   search      │  │   intent      │  │   chains      │
│ (pre-computed │  │ + Selector    │  │ + Known bug   │  │ + Cascading   │
│  grep, env,   │  │   catalogs    │  │   matching    │  │   failure     │
│  timeline)    │  │ + Translations│  │ + Bug filing  │  │   detection   │
│               │  │               │  │               │  │ + Subsystem   │
│ Works but     │  │ Better for    │  │ Much better   │  │   context     │
│ limited       │  │ selector bugs │  │ for all types │  │ Full picture  │
└───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘
```

### Specific Fallbacks

| Unavailable Server | Fallback | Impact |
|--------------------|----------|--------|
| **ACM-UI MCP** | Use `console_search` from core-data.json (pre-computed grep), cloned repos in `repos/` directory | Loses cross-branch search, QE selector catalogs, translations |
| **JIRA MCP** | Skip Phases D-B2 and E2-E6; classify on error evidence alone | Loses feature intent, known bug correlation, bug filing |
| **Knowledge Graph** | Use `subsystem` field from `ComponentExtractor.detected_components`; skip cascading failure detection | Loses dependency chains, cascading failure grouping, subsystem peer lists |
| **All three down** | Full classification still works using core-data.json (extracted_context, timeline_evidence, console_log, environment) | Selector mismatches and infrastructure failures still classified accurately; Path B2 cases may get UNKNOWN |

---

## End-to-End MCP Flow Example

A complete example showing all three MCP servers working together on a single test failure:

```
Test: "RHACM4K-3046 - Verify search results display"
Error: "TypeError: Cannot read properties of undefined (reading 'items')"
failure_type: assertion
console_log: has_500_errors = true (search-api 500 Internal Server Error)
detected_components: [{name: "search-api", subsystem: "Search"}]

─── Phase B4: ACM-UI MCP ────────────────────────────────────

  1. Set version:
     mcp__acm-ui__set_acm_version(version='2.16')

  2. Check if test's data-testid exists in product:
     mcp__acm-ui__search_code(query='search-result-table', repo='acm')
     → Found: frontend/src/routes/Search/SearchResults.tsx:156
     → Selector EXISTS in product (not a selector mismatch)

─── Phase B5: Knowledge Graph MCP ───────────────────────────

  3. What depends on search-api?
     mcp__user-neo4j-rhacm__read_neo4j_cypher(
       query="MATCH (dep)-[:DEPENDS_ON]->(c:RHACMComponent)
              WHERE c.label =~ '(?i).*search-api.*'
              RETURN dep.label"
     )
     → console, observability-dashboard depend on search-api

  4. What does search-api depend on?
     mcp__user-neo4j-rhacm__read_neo4j_cypher(
       query="MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep)
              WHERE c.label =~ '(?i).*search-api.*'
              RETURN dep.label"
     )
     → search-collector, search-indexer

─── Phase D: Path B2 (JIRA-informed) ───────────────────────

  5. Search for feature story:
     mcp__jira__search_issues(
       jql="summary ~ 'RHACM4K-3046' OR description ~ 'RHACM4K-3046'"
     )
     → ACM-22079 "Search: Display filtered results with pagination"

  6. Read story details:
     mcp__jira__get_issue(issue_key='ACM-22079')
     → Acceptance: "Search results must display with pagination"
     → Fix Version: ACM 2.16.0
     → Linked PR: stolostron/console#1234 (merged 3 days ago)

  Analysis: Product should paginate results.
            500 error means backend can't handle the query.
            Linked PR merged recently → possible regression.
  → Classification: PRODUCT_BUG (Path B2, confidence: 0.88)

─── Phase E: JIRA Correlation ──────────────────────────────

  7. Search for related bugs:
     mcp__jira__search_issues(
       jql="project = ACM AND type = Bug AND status != Closed
            AND (summary ~ 'search-api' OR summary ~ 'search 500')"
     )
     → ACM-12345 "search-api 500 on large result sets" (Open, Major)

  8. Read bug details:
     mcp__jira__get_issue(issue_key='ACM-12345')
     → Matches exact symptom
     → Affected: ACM 2.16.0, 2.16.1

  → PRODUCT_BUG confirmed with JIRA correlation
  → Confidence: 0.88 + 0.05 (JIRA match) + 0.05 (feature story) = 0.95
  → Recommended fix: "Known issue ACM-12345. Track fix in ACM 2.16.2."
  → No new bug filed (existing issue found)

─── Final Output ───────────────────────────────────────────

  {
    "classification": "PRODUCT_BUG",
    "confidence": 0.95,
    "classification_path": "B2",
    "evidence_sources": [
      {"source": "console_log", "finding": "search-api 500", "tier": 1},
      {"source": "acm_ui_mcp", "finding": "selector exists in product", "tier": 2},
      {"source": "jira_correlation", "finding": "ACM-12345 matches", "tier": 1},
      {"source": "knowledge_graph", "finding": "search-api dependency chain verified", "tier": 2}
    ],
    "jira_correlation": {
      "related_issues": ["ACM-12345"],
      "feature_story": "ACM-22079"
    },
    "feature_context": {
      "subsystem": "Search",
      "components_involved": ["search-api", "search-collector", "search-indexer"],
      "knowledge_graph_context": {
        "subsystem_queried": true,
        "failure_in_dependency": false
      }
    }
  }
```

---

## Configuration

MCP servers are configured in Claude Code's MCP settings. No application-level configuration is needed.

The `core-data.json` output from Stage 1 includes an `mcp_integration` section that documents which tools are available, their call format, and trigger conditions. This embedded reference ensures the AI agent knows how to use MCP tools regardless of whether it has access to documentation files.

```json
// In core-data.json → ai_instructions → mcp_integration
{
  "servers_available": {
    "acm_ui": true,
    "knowledge_graph": true,
    "jira": true
  },
  "how_to_call": "Use native MCP tool calls. Example: mcp__jira__search_issues(jql='...')"
}
```
