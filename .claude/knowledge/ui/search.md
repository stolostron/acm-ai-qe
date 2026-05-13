# Search Area Knowledge

## Overview

ACM Search provides a unified search experience across all managed clusters, with RBAC-scoped results based on user permissions. Uses a PostgreSQL database to index resources collected from hub and spoke clusters.

## Key Components

| Component | Namespace | Role |
|-----------|-----------|------|
| `search-api` | ocm (app=search-api) | GraphQL query server |
| `search-indexer` | ocm (app=search-indexer) | Processes collected data |
| `search-postgres` | ocm (app=search-postgres) | PostgreSQL database (**uses emptyDir, not PVC**) |
| `search-collector` | ocm (app=search-collector) | Collects hub resources |
| `search-v2-operator` | ocm | Manages search lifecycle |
| `search-collector` addon | open-cluster-management-agent-addon (spoke) | Collects spoke resources |

## CRDs / Resources

Search indexes ~22 Kubernetes resource types with ~90 fields. No custom CRDs — it queries existing resources via the Kubernetes API.

## Console Integration

| Element | Detail |
|---------|--------|
| Backend proxy | `/api/proxy/search` |
| Backend code | `backend/src/lib/search.ts` |
| Query format | GraphQL |
| Test selectors | `data-test="search-query-input"`, `data-test="search-results"` |
| PF6 selectors | `.pf-v6-c-menu__list-item` (result type accordion items) |

## Navigation Routes

| Route Key | Path | Page |
|-----------|------|------|
| `search` | `/multicloud/search` | Main search page |
| `resources` | `/multicloud/search/resources` | Resource details |
| `resourceYAML` | `/multicloud/search/resources/yaml` | Resource YAML view |
| `resourceRelated` | `/multicloud/search/resources/related` | Related resources |
| `resourceLogs` | `/multicloud/search/resources/logs` | Resource logs |

## Storage Model

- **search-postgres uses emptyDir** (not PVC) — data is lost on pod restart
- Index is rebuilt from collectors after restart
- No persistent storage dependency
- Corruption persists until pod restart if data directory is corrupted while running

## RBAC Filtering

- Search results are filtered by user permissions
- `search-api` evaluates access per resource based on the requesting user's roles
- FG-RBAC (MCRA) permissions are respected — users only see resources on clusters they have access to
- Fleet Virt VM list is entirely sourced from Search — if search is down, VM list is empty

## Translation Keys

| Key | English Text | Context |
|-----|-------------|---------|
| `Search` | "Search" | Navigation tab |
| `Search resources` | "Search resources" | Placeholder text |
| `Saved searches` | "Saved searches" | Saved filter section |
| `Related resources` | "Related resources" | Related resources tab |
| `Suggested search templates` | "Suggested search templates" | Quick filters |

## Query Syntax

Search queries use `key:value` pairs with operators:
- Equality: `kind:Pod` or `cluster:spoke-1`
- Inequality: `kind:!=Secret`
- Multiple values: `namespace:default,kube-system`
- Wildcard: `name:search-*`
- Multiple criteria: `kind:Pod namespace:default status:Running`

## Setup Prerequisites

- `search` component enabled in MCH (enabled by default)
- `search-collector` addon deployed to spokes
- PostgreSQL database healthy with correct schema
- Network policies must allow `search-api` → `search-postgres` communication

## Testing Considerations

- Search results depend on user RBAC permissions — test with different roles
- Search API uses GraphQL (not REST)
- Resource details link to external Search resource views
- search-collector missing on a spoke means empty results for that cluster's resources
- Known issue: count off-by-one — frontend adds 1 to `items.length` in accordion header
- Known issue: wrong detail links — namespace/name parameters swapped in `searchDefinitions.tsx`
- Known issue: results artificially limited — backend injects `limit: 5`
- Known issue: `!=` operator broken — `search-helper.tsx` strips `!`, turning `!=` into `=`
