# Search Architecture

Search enables cross-cluster resource discovery. Users search for any Kubernetes
resource across all managed clusters from the ACM console.

---

## Components

| Component | Type | Namespace | Pod Label | Role |
|-----------|------|-----------|-----------|------|
| search-api | Hub deployment | ocm | app=search-api | Serves GraphQL queries from the console UI |
| search-indexer | Hub deployment | ocm | app=search-indexer | Processes collected data into the database |
| search-postgres | Hub deployment | ocm | app=search-postgres | PostgreSQL database storing the search index |
| search-collector | Hub deployment | ocm | app=search-collector | Collects resources from the hub cluster |
| search-v2-operator | Hub deployment | ocm | app=search-v2-operator-controller-manager | Manages search component lifecycle |
| search-collector (addon) | Spoke addon | open-cluster-management-agent-addon | app=search-collector | Indexes resources on each spoke cluster |

## Storage

search-postgres uses an **emptyDir** volume (not a PVC). This means:
- Data is lost when the pod restarts
- The index is rebuilt from collectors after restart
- No persistent storage dependency
- BUT: if the data directory is corrupted or tables are dropped while the pod
  is running, the corruption persists until the pod restarts

## Prerequisites

- `search` component enabled in MCH (enabled by default)
- `search-collector` addon deployed to spoke clusters
- PostgreSQL database healthy with correct schema

## Console Integration

The console's Search page lives at `/multicloud/search`. The frontend sends
GraphQL queries to the backend, which proxies them to the search-api via
`/api/proxy/search`. The backend code is in `backend/src/lib/search.ts`.

Key selectors:
- `data-test="search-query-input"` -- main search input
- `data-test="search-results"` -- results container
- `.pf-v6-c-menu__list-item` -- result type accordion items

## Cross-Subsystem Dependencies

- **Fleet Virtualization** depends on Search for VM discovery across clusters
- **RBAC** uses search integration for fine-grained permission filtering
- **Console** proxies resource requests through the Search interface
- If Search is down, VM list is empty and resource lookup fails silently
