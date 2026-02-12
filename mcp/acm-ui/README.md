# ACM UI MCP Server

An MCP server that provides knowledge about the ACM UI and Fleet Virtualization codebase by interfacing with GitHub repositories via the `gh` CLI.

Part of the [AI Systems Suite](../../README.md). Used by the [Z-Stream Analysis](../../apps/z-stream-analysis/) application for UI component investigation during pipeline failure analysis.

## Supported Repositories

| Key | Repository | Description |
|-----|------------|-------------|
| `acm` | [stolostron/console](https://github.com/stolostron/console) | ACM Console (AcmTable, routes, ui-components) |
| `kubevirt` | [kubevirt-ui/kubevirt-plugin](https://github.com/kubevirt-ui/kubevirt-plugin) | Fleet Virtualization UI (search, tree view, migration modal) |
| `acm-e2e` | [stolostron/clc-ui-e2e](https://github.com/stolostron/clc-ui-e2e) | Cluster Lifecycle + RBAC UI automation |
| `search-e2e` | [stolostron/search-e2e-test](https://github.com/stolostron/search-e2e-test) | Search component E2E automation |
| `app-e2e` | [stolostron/application-ui-test](https://github.com/stolostron/application-ui-test) | Applications (ALC) UI automation |
| `grc-e2e` | [stolostron/acmqe-grc-test](https://github.com/stolostron/acmqe-grc-test) | Governance (GRC) E2E automation |

## Version Mapping

**Important**: The repositories use different versioning schemes:

| Repository | Version Format | Example Branches |
|------------|----------------|------------------|
| **ACM Console** | ACM version | `release-2.15`, `release-2.16` |
| **kubevirt-plugin** | CNV/OpenShift Virt version | `release-4.19`, `release-4.20` |

The MCP server can **auto-detect** the CNV version from your cluster and set the correct branch automatically.

## Features

- **Multi-Repo Support**: Search 6 repositories (2 source + 4 QE automation)
- **Cluster Version Detection**: Auto-detect CNV version and set correct kubevirt-plugin branch
- **Version Awareness**: Switch between releases (e.g., ACM 2.16, CNV 4.20)
- **Component Lookup**: Find React components and their source code
- **Route Mapping**: Map URLs to source files
- **Test ID Discovery**: Extract `data-testid`, `data-test`, `id`, and `aria-label` attributes
- **Fleet Virt Selectors**: Quick access to common Fleet Virtualization selectors
- **Translation Search**: Find exact UI text from ACM Console translation files
- **Type Analysis**: Extract TypeScript interfaces and type definitions
- **Wizard Analysis**: Extract wizard step structure and visibility conditions
- **PatternFly Reference**: PatternFly v6 CSS selector catalog

## Prerequisites

- Python 3.10+
- GitHub CLI (`gh`) installed and authenticated
- OpenShift CLI (`oc`) for cluster version detection (optional)

## New User Setup

### Step 1: Install GitHub CLI

The ACM UI MCP server uses `gh` to access GitHub repositories. Install it if you don't have it:

```bash
# macOS
brew install gh

# Linux (Fedora/RHEL)
sudo dnf install gh

# Verify
gh --version
```

### Step 2: Authenticate with GitHub

```bash
gh auth login
```

Follow the prompts:
- Select **GitHub.com**
- Select **HTTPS** as the preferred protocol
- Authenticate via **browser** or **paste a token**
- Verify: `gh auth status` should show "Logged in to github.com"

You need read access to the `stolostron` and `kubevirt-ui` GitHub organizations. If you can view https://github.com/stolostron/console in a browser, you have access.

### Step 3: Install the MCP server

From the repository root:

```bash
pip install -e mcp/acm-ui/
```

Or from within this directory:

```bash
pip install -e .
```

### Step 4: Verify installation

```bash
python -c "import acm_ui_mcp_server; print('OK')"
```

### Step 5 (Optional): Install OpenShift CLI

If you want auto-detection of CNV version from a connected cluster:

```bash
# Download from https://console.redhat.com/openshift/downloads
# Or on macOS:
brew install openshift-cli

# Log in to your cluster
oc login https://api.your-cluster.example.com:6443

# Verify
oc whoami
```

## MCP Configuration

### For apps in this repository

Apps use `.mcp.json` at their root. Example from `apps/z-stream-analysis/.mcp.json`:

```json
{
  "mcpServers": {
    "acm-ui": {
      "command": "python",
      "args": ["-m", "acm_ui_mcp_server.main"],
      "cwd": "../../mcp/acm-ui"
    }
  }
}
```

### For Cursor IDE

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "acm-ui": {
      "command": "python",
      "args": ["-m", "acm_ui_mcp_server.main"],
      "cwd": "/path/to/ai_systems_v2/mcp/acm-ui",
      "timeout": 60
    }
  }
}
```

### For Claude Code

Add to your project's `.mcp.json` or use `claude mcp add`.

## Available Tools (20)

### Version Management

| Tool | Description |
|------|-------------|
| `set_acm_version(version)` | Set ACM Console branch by version (e.g., '2.16', 'latest') |
| `set_cnv_version(version)` | Set kubevirt-plugin branch by CNV version (e.g., '4.20') |
| `list_versions()` | List all supported ACM and CNV versions |
| `get_current_version(repo)` | Get current version for a repository |
| `set_version(version, repo)` | Set branch directly (low-level) |
| `list_repos()` | List repositories and current settings |

### Cluster Detection

| Tool | Description |
|------|-------------|
| `detect_cnv_version()` | Auto-detect CNV version from cluster |
| `get_cluster_virt_info()` | Get cluster virtualization status |

### Code Discovery

| Tool | Description |
|------|-------------|
| `find_test_ids(path, repo)` | Find automation attributes in a file |
| `get_component_source(path, repo)` | Get raw source code for a file |
| `search_component(query, repo)` | Search for components by name |
| `search_code(query, repo)` | GitHub code search |
| `get_route_component(url_path)` | Map URL to source files |

### Selectors and UI Text

| Tool | Description |
|------|-------------|
| `get_fleet_virt_selectors()` | Fleet Virt selectors from kubevirt-plugin |
| `get_acm_selectors(source, component)` | ACM Console selectors (catalog + source) |
| `search_translations(query, exact)` | Search UI text from translation files |
| `get_patternfly_selectors(component)` | PatternFly v6 CSS selector reference |

### Structure Analysis

| Tool | Description |
|------|-------------|
| `get_component_types(path, repo)` | Extract TypeScript interfaces and types |
| `get_wizard_steps(path, repo)` | Analyze wizard step structure |
| `get_routes(repo)` | Get all ACM Console navigation paths |

## Quick Start

```python
# Set versions (ACM and CNV are independent)
set_acm_version('2.16')
set_cnv_version('4.20')

# Or auto-detect CNV from connected cluster
detect_cnv_version()

# Find selectors
find_test_ids("src/views/search/components/SearchBar.tsx", "kubevirt")

# Search code
search_code("vm-search-input", "kubevirt")

# Get ACM selectors
get_acm_selectors('catalog', 'search')
```

## Key File Paths

### ACM Console (repo='acm')
- `frontend/src/ui-components/` - Reusable UI components (AcmTable, AcmButton, etc.)
- `frontend/src/routes/` - Page components
- `frontend/packages/multicluster-sdk/` - Multi-cluster SDK

### KubeVirt Plugin (repo='kubevirt')
- `src/views/virtualmachines/` - VM list, details, tree view
- `src/views/search/` - Search bar, advanced search
- `src/multicluster/components/CrossClusterMigration/` - CCLM modal
- `cypress/views/` - Selector definitions for testing

## Full Documentation

See [docs/ACM-UI-MCP-Server-Documentation.md](docs/ACM-UI-MCP-Server-Documentation.md) for the complete reference including:
- All tool parameters and example outputs
- Recommended workflows for AI assistants
- Version mapping details and maintenance instructions
- Technical implementation details
- Troubleshooting guide
