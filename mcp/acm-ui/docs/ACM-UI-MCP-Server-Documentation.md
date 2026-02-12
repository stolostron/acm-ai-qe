# ACM UI MCP Server - Complete Documentation

## Overview

The ACM UI MCP Server is a Model Context Protocol (MCP) server designed to provide AI coding assistants (like those in Cursor IDE or Claude Code) with deep, real-time knowledge of the Advanced Cluster Management (ACM) and Fleet Virtualization user interface codebases. It bridges the gap between AI assistants and the complex, multi-repository UI source code that powers Red Hat's ACM and OpenShift Virtualization console experiences.

---

## The Problem It Solves

When working on ACM UI automation (e.g., Cypress tests), developers and AI assistants face several challenges:

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
|                        AI Assistant                                |
|  +------------------------------------------------------------+  |
|  |                    Claude Code / Cursor                      |  |
|  |  "Find the selector for the VM search bar"                  |  |
|  +----------------------------+-------------------------------+  |
|                               | MCP Protocol                      |
|  +----------------------------v-------------------------------+  |
|  |              ACM UI MCP Server                              |  |
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
- **ACM Console** (`acm`): The base ACM UI framework, including cluster management, RBAC, and infrastructure pages
- **KubeVirt Plugin** (`kubevirt`): OpenShift Console plugin for virtualization - Fleet Virtualization UI lives here

**QE Automation Repositories (for selector catalogs):**
- **CLC UI E2E** (`acm-e2e`): Cluster Lifecycle + RBAC UI automation (ACM 2.15+)
- **Search E2E** (`search-e2e`): Search component E2E automation
- **Application UI Test** (`app-e2e`): Applications/ALC UI automation
- **GRC Test** (`grc-e2e`): Governance/GRC E2E automation

When a user navigates to Fleet Virtualization in ACM, they're using components from `kubevirt-plugin` rendered within the ACM/OpenShift Console framework. The QE automation repos provide curated, tested selectors that can be more reliable than extracting raw selectors from source.

---

## Available Tools (20 Total)

### 1. Version Management Tools

**Key Concept**: ACM and CNV versions are **INDEPENDENT**:
- **ACM version** -> which `stolostron/console` branch to use
- **CNV version** -> which `kubevirt-ui/kubevirt-plugin` branch to use

ACM 2.16 can manage clusters running CNV 4.18, 4.19, 4.20, or 4.21.

#### `list_repos()`

**Purpose**: Shows current version status for both repositories.

**Example output**:
```
=== ACM UI MCP Server ===

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

---

#### `set_version(version, repo)` (Legacy)

**Purpose**: Manually sets the active branch for a repository (low-level).

**Note**: Prefer using `set_acm_version()` or `set_cnv_version()` for semantic version switching.

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
3. Maps to branch: `4.20.3` -> `release-4.20`
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

---

#### `search_component(query, repo)`

**Purpose**: Searches for component files by name within common directories.

**Search paths for each repo**:

| Repo | Directories Searched |
|------|---------------------|
| `acm` | `frontend/src/components`, `frontend/src/routes`, `frontend/src/ui-components`, `frontend/packages/multicluster-sdk/src/components` |
| `kubevirt` | `src/views/virtualmachines`, `src/views/search`, `src/multicluster/components`, `src/utils/components`, `cypress/views` |

---

#### `search_code(query, repo)`

**Purpose**: Uses GitHub code search to find any code containing the query.

**Use case**: Finding where a specific selector, function, or pattern is used.

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

---

### 4. Fleet Virtualization Tools

#### `get_fleet_virt_selectors()`

**Purpose**: Returns common Fleet Virtualization UI selectors from the kubevirt-plugin's Cypress test files.

**Files parsed**:
- `cypress/views/selector.ts`
- `cypress/views/selector-common.ts`
- `cypress/views/actions.ts`

---

### 5. Translation & UI Text Tools

#### `search_translations(query, exact)`

**Purpose**: Searches ACM Console translation strings for matching text. Essential for finding exact UI text (button labels, messages, etc.) for test cases.

**Parameters**:
- `query`: Text to search for (e.g., `'Create role assignment'`, `'error'`)
- `exact`: If `True`, only return exact matches. Default `False` for partial matches.

---

#### `get_acm_selectors(source, component)`

**Purpose**: Returns ACM Console UI selectors for test automation. Supports multiple QE repos organized by component.

**Parameters**:
- `source`: `'catalog'` | `'source'` | `'both'` (default)
- `component`: `'all'` | `'clc'` | `'search'` | `'app'` | `'grc'`

---

### 6. Type & Structure Analysis Tools

#### `get_component_types(path, repo)`

**Purpose**: Extracts TypeScript type and interface definitions from a source file.

#### `get_wizard_steps(path, repo)`

**Purpose**: Analyzes a wizard component to extract step structure and visibility conditions.

#### `get_routes(repo)`

**Purpose**: Extracts navigation paths and route definitions from ACM Console.

#### `get_patternfly_selectors(component)`

**Purpose**: Returns common PatternFly v6 CSS selectors for test automation. Useful as fallback when data-testid attributes are not available.

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
AI calls: search_component("AcmTable", "acm")
Result: frontend/src/ui-components/AcmTable/AcmTableToolbar.tsx

Step 3: Extract selectors
-----------------------------------------
AI calls: find_test_ids("frontend/src/ui-components/AcmTable/AcmTableToolbar.tsx", "acm")
Result: data-testid="bulk-select", id="acm-table-toolbar", etc.
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

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_ACM_VERSION` | `2.16` | Default ACM version (semantic, e.g., `2.16`) |
| `DEFAULT_CNV_VERSION` | `4.21` | Default CNV version (semantic, e.g., `4.21`) |

**Note**: These are semantic versions, not branch names. The server automatically maps to the correct branch.

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
# From the repository root
pip install -e mcp/acm-ui/

# Or from within the mcp/acm-ui/ directory
pip install -e .

# Verify installation
python -c "from acm_ui_mcp_server.server import list_repos; print(list_repos())"
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
  - Now supports 6 repositories total (2 source + 4 QE automation)

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
