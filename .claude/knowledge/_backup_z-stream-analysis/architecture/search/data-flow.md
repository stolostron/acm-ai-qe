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

## Console Integration Path (Full Chain)

The search query path includes OCP console hops that are invisible to
the application but can fail independently:

```
Browser
  -> OCP Ingress Router (HAProxy)
    -> OCP Console Pod (openshift-console)
      -> ConsolePlugin proxy (routes to ACM plugin)
        -> console-api (plugin backend, port 3000)
          -> Resource Proxy (backend/src/lib/search.ts)
            -> search-api pod (HTTP, port 4010)
              -> search-postgres (SQL, port 5432)
              -> returns matching resources
            -> backend returns results
          -> frontend renders results
```

Each hop can fail: ingress down (L3), OCP console down (L9), plugin not
registered (L8), console-api down (L9/L12), search-api down (L9/L11),
postgres empty (L4/Trap 3).

## Query Phase (Detail: console-api onward)

```
console-api receives proxied request
  -> backend/src/lib/search.ts constructs search request
  -> proxies to search-api pod (HTTP)
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
