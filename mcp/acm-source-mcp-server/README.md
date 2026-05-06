# ACM Source MCP Server

An MCP server that provides knowledge about the ACM Source and Fleet Virtualization codebase by interfacing with GitHub repositories via the `gh` CLI.

## Supported Repositories

| Key | Repository | Description |
|-----|------------|-------------|
| `acm` | [stolostron/console](https://github.com/stolostron/console) | ACM Console (AcmTable, routes, ui-components) |
| `kubevirt` | [kubevirt-ui/kubevirt-plugin](https://github.com/kubevirt-ui/kubevirt-plugin) | Fleet Virtualization UI (search, tree view, migration modal) |

## Version Mapping

**Important**: The repositories use different versioning schemes:

| Repository | Version Format | Example Branches |
|------------|----------------|------------------|
| **ACM Console** | ACM version | `release-2.15`, `release-2.16` |
| **kubevirt-plugin** | CNV/OpenShift Virt version | `release-4.19`, `release-4.20` |

The MCP server can **auto-detect** the CNV version from your cluster and set the correct branch automatically.

## Features

- **Multi-Repo Support**: Search both ACM Console and KubeVirt Plugin repositories
- **Cluster Version Detection**: Auto-detect CNV version and set correct kubevirt-plugin branch
- **Version Awareness**: Switch between releases (e.g., `release-2.15`, `main`, `release-4.20`)
- **Component Lookup**: Find React components and their source code
- **Route Mapping**: Map URLs to source files
- **Test ID Discovery**: Extract `data-testid`, `data-test`, `id`, and `aria-label` attributes
- **Fleet Virt Selectors**: Quick access to common Fleet Virtualization selectors

## Prerequisites

- Python 3.10+
- GitHub CLI (`gh`) installed and authenticated (`gh auth login`)
- OpenShift CLI (`oc`) for cluster version detection (optional)

## Installation

1. Clone this repository.
2. Install dependencies:
   ```bash
   pip install -e .
   ```

## Usage with Cursor

Add the following to your `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "acm-source": {
      "command": "python",
      "args": ["-m", "acm_source_mcp_server.main"],
      "cwd": "/path/to/acm-source-mcp-server",
      "timeout": 60
    }
  }
}
```

## Available Tools

### Cluster Detection (NEW)

| Tool | Description |
|------|-------------|
| `detect_cnv_version` | Auto-detect CNV version from cluster and set correct kubevirt-plugin branch |
| `get_cluster_virt_info` | Get comprehensive virtualization info (CNV version, plugins, Fleet Virt status) |

### Repository Management

| Tool | Description |
|------|-------------|
| `list_repos` | List available repositories and their current versions |
| `get_current_version(repo)` | Get the current version for a repository |

### Code Discovery

| Tool | Description |
|------|-------------|
| `find_test_ids(path, repo)` | Find automation attributes in a file |
| `get_component_source(path, repo)` | Get raw source code for a file |
| `search_code(query, repo)` | Search code using GitHub code search |
| `search_code(query, repo, scope="components")` | Search for components by name |
| `get_route_component(url_path)` | Map URL to source files |

### Fleet Virtualization

| Tool | Description |
|------|-------------|
| `get_fleet_virt_selectors` | Get common Fleet Virt selectors from kubevirt-plugin |

## Examples

### Auto-detect CNV version (Recommended)

```
# First, detect CNV version from your cluster (requires oc login)
detect_cnv_version()
# Output: CNV Version Detected: 4.20.3, Mapped to kubevirt-plugin branch: release-4.20

# Get full cluster virt info
get_cluster_virt_info()

# Now find test IDs - will use the correct branch for your cluster
find_test_ids("src/views/search/components/SearchBar.tsx", "kubevirt")
```

### Search for Fleet Virtualization selectors

```
# List repos and current versions
list_repos()

# Manually set kubevirt-plugin branch (if needed)
set_cnv_version("4.20")

# Find test IDs in the SearchBar component
find_test_ids("src/views/search/components/SearchBar.tsx", "kubevirt")

# Get all Fleet Virt selectors
get_fleet_virt_selectors()
```

### Search ACM Console

```
# Set ACM version
set_acm_version("2.15")

# Find test IDs in AcmTable
find_test_ids("frontend/src/ui-components/AcmTable/AcmTableToolbar.tsx", "acm")

# Search for components
search_code("Credentials", "acm", scope="components")
```

### Map URL to source files

```
# Find source files for Fleet Virt VMs page
get_route_component("/k8s/all-clusters/all-namespaces/kubevirt.io~v1~VirtualMachine")
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
