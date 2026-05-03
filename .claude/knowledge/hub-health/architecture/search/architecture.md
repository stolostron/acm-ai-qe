# Search Subsystem -- Architecture

## What Search Does

Search provides cross-cluster resource discovery and querying for ACM. It
indexes Kubernetes resources and their relationships across all managed
clusters and makes them queryable through a GraphQL API. The ACM console,
Fleet Virtualization UI, and RBAC-filtered resource views all depend on Search.

---

## Search v2 Architecture

Search v2 replaced the original redisgraph-based storage with PostgreSQL.
The search-v2-operator manages the lifecycle of all search components.
Architecture follows a collector-indexer-API pattern:

- **Spoke side:** search-collector addon watches Kubernetes API resources,
  collects metadata, sends to hub
- **Hub side:** search-indexer receives metadata, writes to PostgreSQL.
  search-api serves queries via GraphQL with RBAC enforcement at query time

The search-v2-operator CR (`Search` kind, `search.open-cluster-management.io/v1alpha1`)
controls all configuration: storage, resource limits, replica counts, log
levels, node placement.

---

## Key Components

### search-collector (spoke addon)

- **Addon name:** `search-collector`
- **Spoke pod:** `klusterlet-addon-search` in `open-cluster-management-agent-addon`
- **Hub pod label:** `app=search-collector`
- **Default:** Enabled

Watches Kubernetes resources on the managed cluster, collects metadata,
computes relationships, sends to search-indexer on hub. Runs on every managed
cluster where search is enabled.

Resource collection configurable via `search-collector-config` ConfigMap
with `AllowedResources`/`DeniedResources` lists. Without a ConfigMap, all
resources are collected by default.

Memory overrides per-cluster via ManagedClusterAddOn annotations:
- `addon.open-cluster-management.io/search_memory_limit`
- `addon.open-cluster-management.io/search_memory_request`

### search-indexer (hub)

- **Namespace:** MCH namespace
- **Pod label:** `app=search-indexer`

Receives resource metadata from collectors, writes to PostgreSQL. Also
watches hub resources to track active managed clusters.

Metrics:
- `search_indexer_request_duration` -- time to process a request
- `search_indexer_request_size` -- total changes per request
- `search_indexer_request_count` -- total requests received
- `search_indexer_requests_in_flight` -- concurrent requests

### search-api (hub)

- **Namespace:** MCH namespace
- **Pod label:** `app=search-api`

Serves queries via GraphQL with RBAC enforcement. Serves the console UI and
Fleet Virtualization UI (via multicluster-sdk).

Metrics:
- `search_api_requests` -- HTTP request duration
- `search_dbquery_duration_seconds` -- database query latency
- `search_api_db_connection_failed_total` -- failed DB connections

### search-postgres (hub)

- **Namespace:** MCH namespace
- **Pod label:** `app=search-postgres`

PostgreSQL database storing all collected resource data. Default: emptyDir
volume (non-persistent). Configurable to PVC via search-v2-operator CR:

```yaml
spec:
  dbStorage:
    size: 10Gi          # 20Gi sufficient for ~200 managed clusters
    storageClassName: gp2
```

### search-v2-operator (hub)

- **CR Kind:** `Search` (`search.open-cluster-management.io/v1alpha1`)
- **Namespace:** MCH namespace

Watches the Search CR and reconciles all search component deployments.
Manages four deployments: collector, indexer, database, queryapi. Each
individually configurable for resources, replicas, log verbosity.

---

## RBAC Filtering in Search

### Standard RBAC
- search-api checks the requesting user's Kubernetes RBAC for `list` verb
  access on requested resource types
- Users with cluster-admin see all indexed resources
- Non-admin users see only resources they have `list` access to

### Fine-Grained RBAC
- When enabled, search integrates with MCRA permissions
- User's MCRA-defined scope determines which clusters' resources appear
- ClusterPermission resources propagate RBAC rules via ManifestWork
- Search aggregate API picks up kubevirt roles from ClusterPermission fields

### Fleet Virtualization Integration
- Fleet Virt UI uses search (via multicluster-sdk) to discover VMs
- search-cluster-proxy enables direct spoke resource queries
- Fine-grained RBAC users can search ~22 resource kinds with ~90 exposed fields
- Tree view (cluster > project > VM) depends on search having full namespace
  access for the user's permitted scope

---

## Configuration

### MCH Component Toggle
Search is enabled by default. When disabled, the search UI tab disappears --
no error, just a missing navigation item.

### Search API Settings (console-mce-config)
```yaml
SEARCH_RESULT_LIMIT: "1000"         # Max results displayed
SEARCH_AUTOCOMPLETE_LIMIT: "10000"  # Max typeahead suggestions
SAVED_SEARCH_LIMIT: "10"            # Max saved searches per user
```

---

## Dependencies

| Dependency | Why |
|---|---|
| PostgreSQL (search-postgres) | Stores all indexed data; if down, all queries fail |
| Managed cluster connectivity | search-collector needs klusterlet to send data |
| addon-manager | Deploys search-collector to spokes |
| MCH/MCE operators | Lifecycle management |
| console | Proxies search requests from browser to search-api |

## What Depends on Search

| Consumer | Impact When Search Is Down |
|---|---|
| Console Search UI | Search page shows errors or no results |
| Fleet Virtualization UI | VM list empty, tree view empty |
| RBAC-filtered resource views | RBAC users see no resources |
| Console resource proxy | Resource details pages may fail |
| VM search (search-cluster-proxy) | VM details, actions unavailable |
