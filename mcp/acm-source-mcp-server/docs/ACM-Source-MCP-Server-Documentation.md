# ACM Source MCP Server - Complete Documentation

## Overview

The ACM Source MCP Server is a Model Context Protocol (MCP) server designed to provide AI coding assistants (like those in Cursor IDE) with deep, real-time knowledge of the Advanced Cluster Management (ACM) and Fleet Virtualization user interface codebases. It bridges the gap between AI assistants and the complex, multi-repository UI source code that powers Red Hat's ACM and OpenShift Virtualization console experiences.

---

## The Problem It Solves

When working on ACM Source automation (e.g., Cypress tests), developers and AI assistants face several challenges:

1. **Selector Discovery**: Finding the correct `data-testid`, `data-test`, `id`, or `aria-label` attributes for UI elements requires manually searching through thousands of files across multiple repositories.

2. **Version Fragmentation**: The UI code is split across repositories with different versioning schemes:
   - **ACM Console** (`stolostron/console`) uses ACM versions like `2.15`, `2.16`
   - **KubeVirt Plugin** (`kubevirt-ui/kubevirt-plugin`) uses CNV/OpenShift Virtualization versions like `4.19`, `4.20`

3. **Dynamic Environments**: The correct branch to reference depends on what's actually deployed in your cluster, not a static assumption.

4. **Multi-Repository Complexity**: Fleet Virtualization UI components live in a separate repository from the main ACM console, but appear as an integrated experience to users.

---

## Architecture

```
+------------------------------------------------------------------+
|                        Cursor IDE                                 |
|  +------------------------------------------------------------+  |
|  |                    AI Assistant                             |  |
|  |  "Find the selector for the VM search bar"                  |  |
|  +----------------------------+-------------------------------+  |
|                               | MCP Protocol                      |
|  +----------------------------v-------------------------------+  |
|  |              ACM Source MCP Server                              |  |
|  |  +--------------+  +--------------+  +--------------+       |  |
|  |  | GitHub       |  | UI           |  | Cluster      |       |  |
|  |  | Client       |  | Analyzer     |  | Detector     |       |  |
|  |  | (gh CLI)     |  | (Regex)      |  | (oc CLI)     |       |  |
|  |  +------+-------+  +------+-------+  +------+-------+       |  |
|  +---------+-----------------+-----------------+---------------+  |
+-------------+-----------------+-----------------+-----------------+
              |                 |                 |
              v                 v                 v
     +----------------+  +------------+  +------------------+
     | GitHub Repos   |  | Source     |  | OpenShift        |
     | - stolostron/  |  | Code       |  | Cluster          |
     |   console      |  | Analysis   |  | (CNV version)    |
     | - kubevirt-ui/ |  |            |  |                  |
     |   kubevirt-    |  |            |  |                  |
     |   plugin       |  |            |  |                  |
     +----------------+  +------------+  +------------------+
```

### Components

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| GitHub Client | Fetches source code from repositories | Wraps `gh` CLI (not direct API) |
| UI Analyzer | Extracts test IDs and automation attributes | Regex pattern matching |
| Cluster Detector | Detects CNV version from live cluster | Wraps `oc` CLI commands |
| MCP Server | Exposes tools to AI via MCP protocol | FastMCP Python framework |

---

## Supported Repositories

| Key | Repository | Description | Version Format |
|-----|------------|-------------|----------------|
| `acm` | [stolostron/console](https://github.com/stolostron/console) | Main ACM Console UI - clusters, credentials, governance, infrastructure | `release-2.15`, `release-2.16`, `main` |
| `kubevirt` | [kubevirt-ui/kubevirt-plugin](https://github.com/kubevirt-ui/kubevirt-plugin) | Fleet Virtualization UI - VM search, tree view, migration modal, actions | `release-4.19`, `release-4.20`, `main` |
| `acm-e2e` | [stolostron/clc-ui-e2e](https://github.com/stolostron/clc-ui-e2e) | Cluster Lifecycle + Virt/RBAC UI automation (ACM 2.15+) | `main` |
| `search-e2e` | [stolostron/search-e2e-test](https://github.com/stolostron/search-e2e-test) | Search component E2E automation (selectors in views/) | `main` |
| `app-e2e` | [stolostron/application-ui-test](https://github.com/stolostron/application-ui-test) | Applications (ALC) UI automation | `main` |
| `grc-e2e` | [stolostron/acmqe-grc-test](https://github.com/stolostron/acmqe-grc-test) | Governance (GRC) E2E automation | `main` |

### Repository Organization

**Source Code Repositories:**
- **ACM Console** (`acm`): The base ACM Source framework, including cluster management, RBAC, and infrastructure pages
- **KubeVirt Plugin** (`kubevirt`): OpenShift Console plugin for virtualization - Fleet Virtualization UI lives here

**QE Automation Repositories (for selector catalogs):**
- **CLC UI E2E** (`acm-e2e`): Cluster Lifecycle + RBAC UI automation (ACM 2.15+)
- **Search E2E** (`search-e2e`): Search component E2E automation
- **Application UI Test** (`app-e2e`): Applications/ALC UI automation
- **GRC Test** (`grc-e2e`): Governance/GRC E2E automation

When a user navigates to Fleet Virtualization in ACM, they're using components from `kubevirt-plugin` rendered within the ACM/OpenShift Console framework. The QE automation repos provide curated, tested selectors that can be more reliable than extracting raw selectors from source.

### Other ACM Repos (Reference - Not Integrated)

| Component | Repository | Description |
|-----------|------------|-------------|
| Server Foundation | [stolostron/acmqe-foundation-test](https://github.com/stolostron/acmqe-foundation-test) | Foundation/core functionality tests (backend-focused) |
| Observability | [stolostron/multicluster-observability-operator](https://github.com/stolostron/multicluster-observability-operator) | Observability operator and tests |
| Install | [stolostron/acmqe-autotest](https://github.com/stolostron/acmqe-autotest) | Installation automation tests |

---

## Available Tools (20 Total)

### 1. Version Management Tools (NEW - v2.0)

**Key Concept**: ACM and CNV versions are **INDEPENDENT**:
- **ACM version** → which `stolostron/console` branch to use
- **CNV version** → which `kubevirt-ui/kubevirt-plugin` branch to use

ACM 2.16 can manage clusters running CNV 4.18, 4.19, 4.20, or 4.21.

#### `list_repos()`

**Purpose**: Shows current version status for both repositories.

**Example output**:
```
=== ACM Source MCP Server ===

Active Versions:
  ACM:  2.16 (Latest GA) -> stolostron/console @ release-2.16
  CNV:  4.20             -> kubevirt-ui/kubevirt-plugin @ release-4.20

Note: ACM and CNV versions are INDEPENDENT.
      - ACM version = which ACM Console features to look up
      - CNV version = Fleet Virt UI on your target managed cluster

Commands:
  set_acm_version('2.16')    # Set ACM Console version
  set_cnv_version('4.20')    # Set Fleet Virt UI version
  detect_cnv_version()       # Auto-detect CNV from cluster
  list_versions()            # Show all supported versions
```

---

#### `list_versions()`

**Purpose**: Lists ALL supported ACM and CNV versions with their branch mappings.

**Example output**:
```
=== Supported Versions ===

ACM Console (stolostron/console):
  2.11  -> release-2.11
  2.12  -> release-2.12
  2.13  -> release-2.13
  2.14  -> release-2.14
  2.15  -> release-2.15
  2.16  -> release-2.16  [ACTIVE, LATEST GA]
  2.17  -> main          [DEV]

Fleet Virt UI (kubevirt-ui/kubevirt-plugin):
  4.14  -> release-4.14
  4.15  -> release-4.15
  4.16  -> release-4.16
  4.17  -> release-4.17
  4.18  -> release-4.18
  4.19  -> release-4.19
  4.20  -> release-4.20  [ACTIVE]
  4.21  -> release-4.21  [LATEST GA]
  4.22  -> main          [DEV]

Commands:
  set_acm_version('2.16')   # Set ACM Console version
  set_cnv_version('4.20')   # Set Fleet Virt UI version
  detect_cnv_version()      # Auto-detect CNV from cluster
```

---

#### `set_acm_version(version)`

**Purpose**: Sets the ACM Console (stolostron/console) branch by ACM version number. Does NOT affect kubevirt-plugin.

**Parameters**:
- `version`: ACM version (e.g., `'2.16'`, `'2.15'`, `'latest'`, `'main'`)
  - `'latest'` = latest GA version (currently 2.16)
  - `'main'` = next unreleased version (currently 2.17)

**Example**:
```python
set_acm_version('2.16')   # Use ACM 2.16 console features
set_acm_version('main')   # Use development/next release
set_acm_version('latest') # Use latest GA version
```

**Example output**:
```
ACM Console set to 2.16 (Latest GA)
  -> stolostron/console @ release-2.16

Note: kubevirt-plugin unchanged (CNV 4.20).
      Use set_cnv_version() or detect_cnv_version() to change Fleet Virt UI version.
```

---

#### `set_cnv_version(version)`

**Purpose**: Sets the kubevirt-plugin branch by CNV version number. Does NOT affect stolostron/console.

**Parameters**:
- `version`: CNV version (e.g., `'4.20'`, `'4.21'`, `'latest'`, `'main'`)
  - `'latest'` = latest GA version (currently 4.21)
  - `'main'` = next unreleased version

**Alternative**: Use `detect_cnv_version()` to auto-detect from connected cluster.

**Example**:
```python
set_cnv_version('4.20')   # Match CNV 4.20 on your spoke cluster
set_cnv_version('latest') # Use latest GA CNV version
```

**Example output**:
```
Fleet Virt UI set to CNV 4.20
  -> kubevirt-ui/kubevirt-plugin @ release-4.20

Note: ACM Console unchanged (2.16).
      Use set_acm_version() to change ACM Console version.
```

---

#### `set_version(version, repo)` (REMOVED)

**Status**: This tool has been removed. Use `set_acm_version()` or `set_cnv_version()` instead.

**Parameters**:
- `version`: Branch name (e.g., `release-2.15`, `main`, `release-4.20`)
- `repo`: Repository key - `acm` or `kubevirt`

**Validation**: Verifies the branch exists in GitHub before setting.

---

#### `get_current_version(repo)`

**Purpose**: Returns the currently active version for a repository.

**Example output**:
```
ACM: 2.16 -> release-2.16
CNV: 4.20 -> release-4.20
```

---

### 2. Cluster Detection Tools

#### `detect_cnv_version()`

**Purpose**: Auto-detects the CNV/OpenShift Virtualization version from the currently logged-in cluster and sets the correct `kubevirt-plugin` branch.

**How it works**:
1. Runs: `oc get hyperconverged kubevirt-hyperconverged -n openshift-cnv`
2. Extracts the operator version (e.g., `4.20.3`)
3. Maps to branch: `4.20.3` → `release-4.20`
4. Validates branch exists in GitHub
5. Sets the kubevirt repo to that branch

**Example output**:
```
CNV Version Detected: 4.20.3
Mapped to kubevirt-plugin branch: release-4.20

Fleet Virt UI now set to: CNV 4.20 -> release-4.20
You can now use find_test_ids(), get_component_source() with repo='kubevirt' 
to get selectors matching your cluster's CNV version.

Note: ACM Console unchanged (2.16). Use set_acm_version() to change.
```

**Why it matters**: Selectors like `data-test="vm-search-input"` may differ between CNV 4.19 and 4.20. Using the wrong branch means your Cypress tests will fail.

---

#### `get_cluster_virt_info()`

**Purpose**: Gets comprehensive virtualization status from the cluster.

**Returns**:
- CNV/OpenShift Virtualization version
- Recommended kubevirt-plugin branch
- List of console plugins (highlights virt and ACM plugins)
- Fleet Virtualization availability status
- ACM Hub installation status

**Example output**:
```
=== Cluster Virtualization Info ===

CNV/OpenShift Virtualization: 4.20.3
  -> kubevirt-plugin branch: release-4.20

Console Plugins: 7
  - acm (ACM)
  - kubevirt-plugin (virtualization)

Fleet Virtualization: ENABLED (kubevirt-plugin console plugin found)
ACM Hub: INSTALLED
```

---

### 3. Code Discovery Tools

#### `find_test_ids(component_path, repo)`

**Purpose**: Extracts all automation-relevant attributes from a specific file.

**Attributes extracted**:
- `data-testid="..."`
- `data-test="..."`
- `data-test-id="..."`
- `id="..."`
- `aria-label="..."`

**Parameters**:
- `component_path`: Path to file in the repository
- `repo`: `acm` or `kubevirt`

**Example**:
```python
find_test_ids("src/views/search/components/SearchBar.tsx", "kubevirt")
```

**Example output**:
```
Found 5 attributes in kubevirt-ui/kubevirt-plugin/src/views/search/components/SearchBar.tsx:
- data-test='vm-search-input' (Line 45)
  Context: <TextInput data-test="vm-search-input" ...
---
- data-test='vm-advanced-search' (Line 67)
  Context: <Button data-test="vm-advanced-search" ...
---
```

---

#### `get_component_source(path, repo)`

**Purpose**: Retrieves the raw source code of any file.

**Use case**: When you need to understand component structure beyond just selectors.

**Example**:
```python
get_component_source("src/multicluster/components/CrossClusterMigration/CrossClusterMigration.tsx", "kubevirt")
```

---

#### `search_component(query, repo)` (REMOVED — use `search_code(query, repo, scope="components")`)

**Status**: This tool has been merged into `search_code` with `scope="components"`. The behavior is identical.

**Search paths for each repo**:

| Repo | Directories Searched |
|------|---------------------|
| `acm` | `frontend/src/components`, `frontend/src/routes`, `frontend/src/ui-components`, `frontend/packages/multicluster-sdk/src/components` |
| `kubevirt` | `src/views/virtualmachines`, `src/views/search`, `src/multicluster/components`, `src/utils/components`, `cypress/views` |

**Example**:
```python
search_code("Migration", "kubevirt", scope="components")
```

**Example output**:
```
Found components in kubevirt-ui/kubevirt-plugin:
src/multicluster/components/CrossClusterMigration/CrossClusterMigration.tsx
src/multicluster/components/CrossClusterMigration/CrossClusterMigrationWizard.tsx
src/views/virtualmachines/actions/MigrateAction.tsx
```

---

#### `search_code(query, repo)`

**Purpose**: Uses GitHub code search to find any code containing the query.

**Use case**: Finding where a specific selector, function, or pattern is used.

**Example**:
```python
search_code("vm-search-input", "kubevirt")
```

**Example output**:
```
Found 3 files matching 'vm-search-input' in kubevirt-ui/kubevirt-plugin:
  - src/views/search/components/SearchBar.tsx
    URL: https://github.com/kubevirt-ui/kubevirt-plugin/blob/main/src/views/search/components/SearchBar.tsx
  - cypress/views/selector.ts
    URL: https://github.com/kubevirt-ui/kubevirt-plugin/blob/main/cypress/views/selector.ts
```

---

#### `get_route_component(url_path)`

**Purpose**: Maps a URL path to likely source files in both repositories.

**Heuristic mappings**:

| URL Pattern | Likely Source Files |
|-------------|-------------------|
| `/infrastructure/clusters` | ACM: `frontend/src/routes/Infrastructure/Clusters/Clusters.tsx` |
| `/infrastructure/virtualmachines` | ACM: `frontend/src/routes/Infrastructure/VirtualMachines/VirtualMachines.tsx` |
| `/k8s/all-clusters/.../VirtualMachine` | KubeVirt: `src/views/virtualmachines/navigator/VirtualMachineNavigator.tsx` |
| `/search` | KubeVirt: `src/views/search/VirtualMachineSearchResults.tsx` |

**Example**:
```python
get_route_component("/k8s/all-clusters/all-namespaces/kubevirt.io~v1~VirtualMachine")
```

---

### 4. Fleet Virtualization Tools

#### `get_fleet_virt_selectors()`

**Purpose**: Returns common Fleet Virtualization UI selectors from the kubevirt-plugin's Cypress test files.

**Files parsed**:
- `cypress/views/selector.ts`
- `cypress/views/selector-common.ts`
- `cypress/views/actions.ts`

**Example output**:
```
Fleet Virtualization UI Selectors (kubevirt-plugin):

=== cypress/views/selector.ts ===
export const vmSearchInput = '[data-test="vm-search-input"]';
export const vmAdvancedSearch = '[data-test="vm-advanced-search"]';
export const searchResults = '[data-test="search-results"]';
export const vmTreeView = '[data-test="vm-tree-view"]';
...

Source: https://github.com/kubevirt-ui/kubevirt-plugin/tree/release-4.20/cypress/views
```

---

### 5. Translation & UI Text Tools (NEW - v2.1)

#### `search_translations(query, exact)`

**Purpose**: Searches ACM Console translation strings for matching text. Essential for finding exact UI text (button labels, messages, etc.) for test cases.

**Parameters**:
- `query`: Text to search for (e.g., `'Create role assignment'`, `'error'`)
- `exact`: If `True`, only return exact matches. Default `False` for partial matches.

**Example**:
```python
search_translations('Create role assignment')  # Find button text
search_translations('validate')                # Find all validation messages
search_translations('error')                   # Find all error-related strings
```

**Example output**:
```
Found 2 translation(s) matching 'Create role assignment':

Key: Create role assignment
Value: Create role assignment
---
Key: Create role assignment for {{preselected}}
Value: Create role assignment for {{preselected}}
---

Source: stolostron/console @ release-2.16
File: frontend/public/locales/en/translation.json
```

---

#### `get_acm_selectors(source, component)`

**Purpose**: Returns ACM Console UI selectors for test automation. Supports multiple QE repos organized by component.

**Parameters**:
- `source`: Where to get selectors from:
  - `'catalog'`: Curated selectors from QE repos (organized, proven)
  - `'source'`: Extract from stolostron/console source files (complete, raw)
  - `'both'`: Return both (default)
- `component`: Filter by ACM component (default `'all'`):
  - `'all'`: All components
  - `'clc'`: Cluster Lifecycle + RBAC (clc-ui-e2e)
  - `'search'`: Search component (search-e2e-test)
  - `'app'`: Applications/ALC (application-ui-test)
  - `'grc'`: Governance/GRC (acmqe-grc-test)

**Examples**:
```python
get_acm_selectors()                    # Get all selectors from all components
get_acm_selectors('catalog')           # Get curated selectors only (all components)
get_acm_selectors('catalog', 'search') # Get Search component selectors only
get_acm_selectors('catalog', 'grc')    # Get GRC selectors only
get_acm_selectors('catalog', 'app')    # Get Applications selectors only
```

**Example output**:
```
=== ACM Console Selectors ===

## Curated Selectors (from QE automation repos)
Proven selectors used in ACM component automation:

### Cluster Lifecycle + RBAC (acm-e2e)

#### cypress/views/common/commonSelectors.js
  actionHostButton: '.pf-v6-c-table__action > button[aria-label="Kebab toggle"]'
  hostClusterTdId: 'td[data-testid="cluster"]'
  pageSearch: 'input[aria-label="Search input"]'

Source: stolostron/clc-ui-e2e @ main

### Search (search-e2e)

#### tests/cypress/views/search.js
  '.pf-v5-c-text-input-group__text-input'
  '#run-search-button'

Source: stolostron/search-e2e-test @ main

---
Available components: all, clc, search, app, grc
```

---

### 6. Type & Structure Analysis Tools (NEW - v2.1)

#### `get_component_types(path, repo)`

**Purpose**: Extracts TypeScript type and interface definitions from a source file. Useful for understanding data models, props, and state structures.

**Parameters**:
- `path`: Path to the TypeScript file in the repository
- `repo`: `'acm'` or `'kubevirt'`

**Example**:
```python
get_component_types('frontend/src/routes/UserManagement/RoleAssignments/model/role-assignment-preselected.ts', 'acm')
```

**Example output**:
```
Found 1 type/interface definition(s):

### RoleAssignmentPreselected (Line 4)
type RoleAssignmentPreselected = {
  subject?: { kind: UserKindType | GroupKindType | ServiceAccountKindType; value?: string }
  roles?: string[]
  clusterNames?: string[]
  clusterSetNames?: string[]
  namespaces?: string[]
  context?: 'role' | 'cluster' | 'clusterSets' | 'identity'
}
Fields:
  - subject?: { kind: UserKindType | GroupKindType | ServiceAccountKindType
  - roles?: string[]
  - clusterNames?: string[]
  ...
```

---

#### `get_wizard_steps(path, repo)`

**Purpose**: Analyzes a wizard component to extract step structure and visibility conditions. Essential for understanding wizard flow and writing test cases for wizard-based features.

**Parameters**:
- `path`: Path to the wizard component file
- `repo`: `'acm'` or `'kubevirt'`

**Example**:
```python
get_wizard_steps('frontend/src/wizards/RoleAssignment/RoleAssignmentWizardModal.tsx', 'acm')
```

**Example output**:
```
Found 7 wizard step(s):

## Wizard Flow
Step 1: Select scope (id: scope-selection)
  └─ isHidden: (['cluster', 'clusterSets'] as ...).includes(preselected?.context)
Step 2: Define cluster set granularity (id: scope-cluster-set-granularity)
  └─ isHidden: formData.scopeType !== 'Select cluster sets' || hasNoClusterSets
Step 3: Define cluster granularity (id: scope-cluster-granularity)
  └─ isHidden: formData.scopeType !== 'Select clusters' || hasNoClusters
Step 4: Identities (id: identities)
Step 5: Scope (id: scope)
Step 6: Roles (id: role)
Step 7: Review (id: review)

## Visibility Conditions
- **Select scope**: Hidden when entering from Clusters or Cluster Sets page
- **Define cluster set granularity**: Hidden unless cluster sets scope selected
- **Define cluster granularity**: Hidden unless clusters scope selected
```

---

#### `get_routes(repo)`

**Purpose**: Extracts navigation paths and route definitions from ACM Console. Useful for understanding the full navigation structure of the UI.

**Parameters**:
- `repo`: Currently only `'acm'` is supported

**Example**:
```python
get_routes()  # Get all ACM Console navigation paths
```

**Example output**:
```
Found 112 navigation path(s) in ACM Console:

## Applications
  applications: /multicloud/applications
  createApplicationArgo: /multicloud/applications/create/argo
  applicationDetails: /multicloud/applications/details/:namespace/:name
  ...

## Infrastructure
  clusters: /multicloud/infrastructure/clusters
  clusterDetails: /multicloud/infrastructure/clusters/details/:namespace/:name
  clusterRoleAssignments: /multicloud/infrastructure/clusters/details/:namespace/:name/role-assignments
  ...

## User-Management
  identities: /multicloud/user-management/identities
  roles: /multicloud/user-management/roles
  ...

Source: stolostron/console @ release-2.16
```

---

#### `get_patternfly_selectors(component)`

**Purpose**: Returns common PatternFly v6 CSS selectors for test automation. Useful as fallback when data-testid attributes are not available.

**Parameters**:
- `component`: Optional - filter by component type (e.g., `'button'`, `'modal'`, `'table'`, `'wizard'`)
  - Leave empty to get all selectors

**Example**:
```python
get_patternfly_selectors()          # Get all PatternFly selectors
get_patternfly_selectors('button')  # Get button selectors only
get_patternfly_selectors('wizard')  # Get wizard selectors only
```

**Example output**:
```
=== PatternFly v6 Selector Reference ===

## Button
  primary: .pf-v6-c-button.pf-m-primary
  secondary: .pf-v6-c-button.pf-m-secondary
  link: .pf-v6-c-button.pf-m-link
  danger: .pf-v6-c-button.pf-m-danger

## Modal
  modal: .pf-v6-c-modal-box
  header: .pf-v6-c-modal-box__header
  body: .pf-v6-c-modal-box__body
  footer: .pf-v6-c-modal-box__footer

## Wizard
  wizard: .pf-v6-c-wizard
  nav: .pf-v6-c-wizard__nav
  navItem: .pf-v6-c-wizard__nav-item

Usage in Cypress:
  cy.get('.pf-v6-c-button.pf-m-primary').click()
  cy.get('.pf-v6-c-modal-box').should('be.visible')

Note: Prefer data-testid selectors when available for stability.
```

---

## Recommended Workflow for AI Assistants

### Scenario: Writing Cypress tests for Fleet Virtualization

```
Step 1: Set versions (ACM and CNV independently)
-----------------------------------------
AI calls: set_acm_version('2.16')    # For ACM Console features
AI calls: set_cnv_version('4.20')    # Match spoke cluster CNV

OR auto-detect CNV:
AI calls: detect_cnv_version()
Result: CNV 4.20.3 detected, kubevirt branch set to release-4.20

Step 2: Verify versions
-----------------------------------------
AI calls: list_repos()
Result: ACM: 2.16 (Latest GA) -> release-2.16
        CNV: 4.20 -> release-4.20

Step 3: Get available selectors
-----------------------------------------
AI calls: get_fleet_virt_selectors()
Result: List of all selectors from cypress/views/*.ts

Step 4: Find specific component selectors
-----------------------------------------
AI calls: find_test_ids("src/views/search/components/SearchBar.tsx", "kubevirt")
Result: data-test="vm-search-input", data-test="vm-advanced-search", etc.

Step 5: Write accurate Cypress test
-----------------------------------------
AI generates:
  cy.get('[data-test="vm-search-input"]').type('my-vm');
  cy.get('[data-test="vm-advanced-search"]').click();
```

### Scenario: Finding selectors for ACM table

```
Step 1: Set ACM version (semantic, not branch)
-----------------------------------------
AI calls: set_acm_version('2.16')   # Use semantic version

Step 2: Find table component
-----------------------------------------
AI calls: search_code("AcmTable", "acm", scope="components")
Result: frontend/src/ui-components/AcmTable/AcmTableToolbar.tsx

Step 3: Extract selectors
-----------------------------------------
AI calls: find_test_ids("frontend/src/ui-components/AcmTable/AcmTableToolbar.tsx", "acm")
Result: data-testid="bulk-select", id="acm-table-toolbar", etc.
```

### Scenario: Cross-version comparison

```
Step 1: Check feature in ACM 2.15
-----------------------------------------
AI calls: set_acm_version('2.15')
AI calls: search_code("FeatureName", "acm")
Result: File paths in release-2.15

Step 2: Check same feature in ACM 2.16
-----------------------------------------
AI calls: set_acm_version('2.16')
AI calls: search_code("FeatureName", "acm")
Result: File paths in release-2.16 (may differ)
```

---

## Technical Implementation

### GitHub Client (`gh_client.py`)

Uses `gh` CLI exclusively (no direct API calls) for:
- Repository access without API tokens in code
- Leveraging existing `gh auth` session
- Multi-repo support via repo key mapping

```python
REPOS = {
    "acm": "stolostron/console",
    "kubevirt": "kubevirt-ui/kubevirt-plugin",
}
```

### UI Analyzer (`analyzer.py`)

Regex-based extraction of automation attributes:

```python
PATTERN = r'(data-testid|data-test-id|data-test|id|aria-label)\s*=\s*["\']([^\'"]+)["\']'
```

Returns structured data with line numbers and context.

### Cluster Detector (in `server.py`)

Uses `oc` CLI to query cluster resources:

```bash
# Primary: HyperConverged CR
oc get hyperconverged kubevirt-hyperconverged -n openshift-cnv \
  -o jsonpath='{.status.versions[?(@.name=="operator")].version}'

# Fallback: CSV
oc get csv -n openshift-cnv -o jsonpath='{...}'
```

### Version Mapping

The server maintains independent version constants for ACM and CNV:

```python
# ACM Version to Console Branch Mapping (INDEPENDENT)
ACM_VERSIONS = {
    "2.11": "release-2.11",
    "2.12": "release-2.12",
    "2.13": "release-2.13",
    "2.14": "release-2.14",
    "2.15": "release-2.15",
    "2.16": "release-2.16",
    "2.17": "main",  # Next unreleased
}

# CNV Version to KubeVirt-Plugin Branch Mapping (INDEPENDENT)
CNV_VERSIONS = {
    "4.14": "release-4.14",
    "4.15": "release-4.15",
    "4.16": "release-4.16",
    "4.17": "release-4.17",
    "4.18": "release-4.18",
    "4.19": "release-4.19",
    "4.20": "release-4.20",
    "4.21": "release-4.21",
    "4.22": "main",  # Next unreleased
}

# Current state markers
MAIN_ACM_VERSION = "2.17"    # Version that maps to main
LATEST_ACM_GA = "2.16"       # Latest GA version
MAIN_CNV_VERSION = "4.22"    # Version that maps to main
LATEST_CNV_GA = "4.21"       # Latest GA version
```

**Maintenance**: When a new version is GA'd:
1. Update `LATEST_*_GA` constant
2. Update `MAIN_*_VERSION` constant
3. Add new version entry to the mapping

---

## Configuration

### Cursor MCP Settings

Add to your Cursor MCP configuration:

```json
{
  "mcpServers": {
    "acm-source": {
      "command": "/path/to/python",
      "args": ["-m", "acm_source_mcp_server.main"]
    }
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_ACM_VERSION` | `2.16` | Default ACM version (semantic, e.g., `2.16`) |
| `DEFAULT_CNV_VERSION` | `4.21` | Default CNV version (semantic, e.g., `4.21`) |

**Note**: These are now semantic versions, not branch names. The server automatically maps to the correct branch.

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| Python 3.10+ | Runtime |
| `gh` CLI | GitHub access (must be authenticated via `gh auth login`) |
| `oc` CLI | Cluster version detection (optional, for `detect_cnv_version`) |

---

## Key File Paths Reference

### ACM Console (stolostron/console)

| Path | Contains |
|------|----------|
| `frontend/src/routes/` | Page-level components |
| `frontend/src/ui-components/` | Reusable UI components (AcmTable, etc.) |
| `frontend/src/components/` | Common components |
| `frontend/packages/multicluster-sdk/` | Multi-cluster SDK components |

### KubeVirt Plugin (kubevirt-ui/kubevirt-plugin)

| Path | Contains |
|------|----------|
| `src/views/virtualmachines/` | VM list, details, tree view |
| `src/views/search/` | Fleet Virt search bar and results |
| `src/multicluster/components/` | Cross-cluster migration modal |
| `cypress/views/` | Test selectors (selector.ts, selector-common.ts) |

---

## Installation

```bash
# Clone or navigate to the MCP server directory
cd /path/to/acm-source-mcp-server

# Install in development mode
pip install -e .

# Verify installation
python -c "from acm_source_mcp_server.server import list_repos; print(list_repos())"
```

---

## Troubleshooting

### "oc CLI not found"

The cluster detection tools require the OpenShift CLI. Install it:
```bash
# macOS
brew install openshift-cli

# Or download from Red Hat
```

### "gh CLI not found"

Install the GitHub CLI:
```bash
# macOS
brew install gh

# Authenticate
gh auth login
```

### "Branch not found"

If a specific branch doesn't exist (e.g., `release-4.21`), the server falls back to `main`. Check available branches:
```bash
gh api repos/kubevirt-ui/kubevirt-plugin/branches --jq '.[].name'
```

---

## Version History

- **v1.0**: Initial release with ACM Console support
- **v1.1**: Added kubevirt-ui/kubevirt-plugin repository support
- **v1.2**: Added cluster CNV version detection and auto-branch selection
- **v2.0**: Independent version management for ACM and CNV
  - New tools: `set_acm_version()`, `set_cnv_version()`, `list_versions()`
  - Semantic version support: Use `'2.16'` instead of `'release-2.16'`
  - Special keywords: `'latest'`, `'main'` for both repos
  - ACM supports: 2.11-2.17 (2.17 = main/dev)
  - CNV supports: 4.14-4.22 (4.22 = main/dev)
  - Updated `list_repos()` with clear version status
  - Enhanced `get_current_version()` with semantic info
- **v2.1**: Translation, Selectors, Types, Wizard, and Routes tools (6 new tools, total 20)
  - `search_translations()`: Search UI text from translation files
  - `get_acm_selectors()`: Hybrid catalog+source ACM Console selectors
  - `get_component_types()`: Extract TypeScript interfaces and types
  - `get_wizard_steps()`: Analyze wizard step structure and visibility
  - `get_routes()`: Get all ACM navigation paths (112 routes)
  - `get_patternfly_selectors()`: PatternFly v6 CSS selector reference
  - Added `acm-e2e` repo (`stolostron/clc-ui-e2e`) for QE automation selectors
- **v2.2**: Multi-component QE repo integration
  - Added `search-e2e` repo (`stolostron/search-e2e-test`) for Search selectors
  - Added `app-e2e` repo (`stolostron/application-ui-test`) for Applications selectors
  - Added `grc-e2e` repo (`stolostron/acmqe-grc-test`) for Governance/GRC selectors
  - Enhanced `get_acm_selectors()` with `component` parameter for filtered queries
  - Refactored selector catalog to support scalable multi-repo architecture
  - Now supports 6 repositories total (2 source + 4 QE automation)
  - Fixed: QE repos now correctly use `main` branch (not ACM release branch)
  - All tools (`search_code`, `get_component_source`, `find_test_ids`) work with QE repos

---

## Contributing

To add support for additional repositories:

**For Source Code Repos (acm, kubevirt):**
1. Add entry to `REPOS` in `gh_client.py`
2. Add search paths to `SEARCH_PATHS` in `server.py`
3. Add version mappings to `ACM_VERSIONS` or `CNV_VERSIONS` in `gh_client.py`
4. Update `get_version()` in `server.py` if custom branch logic needed

**For QE Automation Repos (selectors):**
1. Add entry to `REPOS` in `gh_client.py`
2. Add entry to `QE_SELECTOR_CATALOG` in `server.py` with:
   - `name`: Display name (e.g., "Search")
   - `short`: Component filter key (e.g., "search")
   - `files`: List of selector file paths
3. Add search paths to `SEARCH_PATHS` in `server.py`
4. Add repo key to `get_version()` QE branch check (returns `main`)
5. Test with `pip install -e .` and verify all tools work

---

## License

Internal Red Hat / ACM QE tooling.
