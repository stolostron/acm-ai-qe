---
name: acm-ui-source
description: Query ACM Console and kubevirt-plugin source code for components, routes, translations, selectors, wizard steps, and TypeScript types. Use when you need to discover or verify UI elements, navigation paths, button labels, data-test attributes, or component source code in the ACM Console.
compatibility: "Requires MCP server: acm-ui (acm-ui-mcp-server). Needs GitHub CLI auth (gh auth login) for source access. Run /onboard to configure."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM UI Source Code Explorer

Provides version-scoped access to ACM Console (`stolostron/console`) and kubevirt-plugin (`kubevirt-ui/kubevirt-plugin`) source code via the `acm-ui` MCP server. Supports discovery of routes, translations, selectors, component source, wizard structures, and TypeScript types.

## Critical: Always Set Version First

Before ANY search or get operation, you MUST set the ACM version:

```
set_acm_version('2.17')         -- Target a specific ACM version
set_acm_version('latest')       -- Latest GA version
set_acm_version('main')         -- Development/next release
```

For Fleet Virt, CCLM, or MTV features, ALSO set the CNV version (independent of ACM version):
```
set_cnv_version('4.21')
```

Verify versions are set:
```
list_repos()                    -- Shows configured repos and branches
```

## MCP Tools

### Version Management
| Tool | Purpose |
|------|---------|
| `set_acm_version(version)` | Set ACM Console branch by version |
| `set_cnv_version(version)` | Set kubevirt-plugin branch by CNV version |
| `list_repos()` | Show configured repos and branches |
| `list_versions()` | List available ACM versions |
| `get_current_version()` | Show current version setting |

### Source Code Search
| Tool | Purpose |
|------|---------|
| `search_code(query, repo)` | Find files containing a string. `repo`: `acm`, `kubevirt`, `acm-e2e`, `search-e2e`, `app-e2e`, `grc-e2e` |
| `search_component(query, repo)` | Find React components by name |
| `get_component_source(path, repo)` | Read the full source of a file |
| `get_component_types(path, repo)` | Read TypeScript types/interfaces from a file |

### UI Element Discovery
| Tool | Purpose |
|------|---------|
| `search_translations(query, exact)` | Find UI label strings (button text, messages, column headers) |
| `get_routes(repo)` | Get all ACM Console navigation paths (117 routes) |
| `get_route_component(route_key)` | Get the component that renders a specific route |
| `get_wizard_steps(path, repo)` | Analyze wizard step structure |
| `find_test_ids(path, repo)` | Extract `data-test` and `data-testid` attributes |

### QE Selectors
| Tool | Purpose |
|------|---------|
| `get_acm_selectors(source, component)` | Get existing QE selectors from automation repos |
| `get_fleet_virt_selectors()` | Get Fleet Virt Cypress selectors |
| `get_patternfly_selectors(component)` | Get PatternFly 6 CSS class-based selectors |

### Cluster/Virt Info
| Tool | Purpose |
|------|---------|
| `get_cluster_virt_info()` | Get cluster virtualization configuration info |
| `detect_cnv_version()` | Auto-detect CNV version from cluster |

## Repository Keys

| Key | Repository | Notes |
|-----|-----------|-------|
| `acm` | `stolostron/console` | Main ACM Console. Branch follows `set_acm_version`. |
| `kubevirt` | `kubevirt-ui/kubevirt-plugin` | Fleet Virt/CCLM/MTV UI. Branch follows `set_cnv_version`. |
| `acm-e2e` | `stolostron/clc-ui-e2e` | Cypress E2E tests. Always `main` branch. |
| `search-e2e` | Search E2E tests | Always `main` branch. |
| `app-e2e` | Application E2E tests | Always `main` branch. |
| `grc-e2e` | Governance E2E tests | Always `main` branch. |

QE repos always use `main` branch regardless of the ACM version setting.

## Gotchas

- **Version MUST be set first** -- calls without `set_acm_version` return results from whatever branch was last configured
- **QE repos ignore version** -- always `main`, even after `set_acm_version('2.16')`
- **Fleet Virt needs BOTH versions** -- `set_acm_version` and `set_cnv_version` are independent
- **`search_translations` is partial match by default** -- set `exact=true` for exact matches
- **`get_routes` returns 117 routes** -- filter by section (Governance, Infrastructure, etc.) in the output

## Rules

- NEVER call search/get tools without setting the version first
- NEVER assume UI labels -- always verify via `search_translations`
- NEVER assume navigation paths -- always verify via `get_routes`
- If the MCP is unavailable, note it and proceed with available data
