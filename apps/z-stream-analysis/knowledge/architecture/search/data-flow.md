# Search Data Flow

How data moves from spoke clusters through the search pipeline to the UI.

---

## Collection Phase (Spoke -> Hub)

```
Spoke Cluster
  search-collector addon
    -> watches all resources on the spoke
    -> indexes: kind, apigroup, name, namespace, labels, status
    -> sends resource data to hub search-indexer

Hub Cluster
  search-indexer
    -> receives data from all spoke collectors
    -> processes and writes to search-postgres
    -> maintains schema: search.resources (uid, cluster, data JSONB)
                          search.edges (sourceId, destId, edgeType, cluster)
```

## Query Phase (UI -> API -> Database)

```
User types search query in console UI
  -> frontend constructs GraphQL query
  -> POST /api/proxy/search (console backend, backend/src/lib/search.ts)
    -> backend proxies to search-api pod (HTTP)
      -> search-api executes SQL against search-postgres
      -> returns matching resources with pagination
    -> backend returns results to frontend
  -> frontend renders results in accordion groups by resource type
```

## Database Schema

```sql
search.resources (uid TEXT PRIMARY KEY, cluster TEXT, data JSONB)
search.edges (sourceId TEXT, sourceKind TEXT, destId TEXT, destKind TEXT, edgeType TEXT, cluster TEXT)

Indexes:
  data_kind_idx (GIN on data->'kind')
  data_namespace_idx (GIN on data->'namespace')
  data_name_idx (GIN on data->'name')
  data_cluster_idx (btree on cluster)
  data_composite_idx (GIN on hubClusterResource, namespace, apigroup, kind_plural)
```

## Failure Points

| Point | What breaks | Symptom |
|-------|------------|---------|
| search-collector addon missing on spoke | Resources from that spoke absent | Silent empty results -- no error |
| search-postgres down | All queries fail | SQL connection error in search-api logs |
| search.resources table dropped | Queries return "relation does not exist" | Search page shows error or empty |
| NetworkPolicy blocks postgres | search-api can't connect to DB | Connection timeout, empty results |
| search-api down | Console can't query search | /api/proxy/search returns 502/503 |
| Backend proxy injects limit | Results artificially limited | Pagination shows wrong total count |
| Backend proxy modifies query | Wrong results returned | Namespace/name swapped in detail links |

## Console Backend Modifications (Bug Injection Points)

The search data flow passes through `backend/src/lib/search.ts` on the console.
This is where code-level bugs can intercept and modify queries or responses:
- Injecting `input.limit = 5` limits all results to 5
- Swapping namespace/name in URL construction sends detail links to wrong resources
- Stripping the `!=` operator silently changes negation to equality
