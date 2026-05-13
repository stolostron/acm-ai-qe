# Search Subsystem -- Data Flow

## End-to-End Data Movement

```
Spoke Cluster(s)          Hub Cluster                Hub Cluster
search-collector    -->   search-indexer    -->      search-postgres
(klusterlet-addon-        (processes &               (PostgreSQL DB)
 search)                   writes to DB)                  |
                                                         v
                                              search-api (GraphQL + RBAC)
                                                         |
                                                         v
                                              Console Browser (GraphQL)
```

---

## 1. Spoke Side: search-collector

### What It Watches
Watches Kubernetes API for resource changes. By default collects all resource
types. Can be restricted via `search-collector-config` ConfigMap with
`AllowedResources`/`DeniedResources`.

### What It Collects
For each resource:
- Standard metadata: name, namespace, kind, apigroup, labels, annotations, timestamps
- Resource-specific fields based on kind (e.g., VirtualMachine: status, cpu, memory, runStrategy)
- Computed relationships between resources (e.g., Pod owned by ReplicaSet)
- ~90 total resource-specific fields across 22+ resource kinds

### How It Sends Data
- **Protocol:** HTTPS to hub's search-indexer service
- **Transport:** Batched resource metadata (adds, updates, deletes)
- **Frequency:** Continuous watch-based deltas, not periodic full-sync
- **Auth:** Addon framework credentials (SA token from addon-manager)

---

## 2. Hub Side: search-indexer

Receives resource metadata from all collectors:
1. Accepts incoming HTTPS requests from collectors
2. Processes changes: adds, updates, removes
3. Writes to PostgreSQL
4. Tracks active managed clusters via hub-side watches

Handles concurrent requests from multiple collectors.

---

## 3. Hub Side: search-postgres

Stores the complete resource index. Contains:
- Resource metadata (all collected fields)
- Resource relationships
- Cluster membership

**Default:** emptyDir (data lost on restart, rebuilt from collectors).
**Recommended:** PVC-backed for persistence. ~20Gi for ~200 managed clusters.

---

## 4. Hub Side: search-api

### Query Flow
1. Console browser sends GraphQL query (proxied through console -> resource proxy)
2. search-api authenticates via user's OAuth token
3. RBAC check: evaluates user permissions to determine visible resources
4. Translates GraphQL + RBAC filter into PostgreSQL query
5. Returns filtered results as JSON

### Query Syntax
- Property-based filters: `kind:Pod namespace:default status:Running`
- Operators: `=`, `!=`/`!`, `<`, `<=`, `>`, `>=`, `*` (partial)
- Multi-value (OR): `name:a,b`
- Multi-property (AND): `kind:Pod namespace:default`
- Related resources supported
- Date comparisons with `hour`, `day`, `week`, `month`, `year`

### Console Integration Path
```
Browser -> OCP Console -> ConsolePlugin proxy -> console-api (BFF) -> Resource Proxy -> search-api (GraphQL)
```
The first two hops (OCP Console and ConsolePlugin proxy) are transparent
to the search data flow but are distinct failure domains: if the OCP
Console pod or ConsolePlugin registration is broken, search queries from
the UI fail even though search-api is healthy. Direct API access to
search-api (bypassing console) would still work.

### Fleet Virt Integration Path
```
kubevirt-plugin -> multicluster-sdk -> search-api
```
Converts search results into typed K8s resource objects for VM list, tree view.

---

## 5. Failure Modes at Each Hop

### search-collector down on spoke
- **Symptom:** Resources from that spoke don't appear in search. No error.
- **Scope:** Only that spoke. Other clusters unaffected.
- **Detection:** `oc get managedclusteraddon search-collector -n {cluster}`
- **Recovery:** Automatic. Data resynchronizes from scratch on reconnect.

### search-indexer down
- **Symptom:** Results become stale. New changes don't appear/disappear.
- **Scope:** All clusters -- no new data processed.
- **Detection:** `oc get pods -n <mch-ns> -l app=search-indexer`
- **Recovery:** Processes backlog on restart.

### search-postgres down
- **Symptom:** ALL queries fail. Console search errors. Fleet Virt VM list empty.
- **Scope:** Total search outage.
- **Detection:** `oc get pods -n <mch-ns> -l app=search-postgres`
- **Recovery:** emptyDir = full re-index (minutes-hours). PVC = data persists.

### search-api down
- **Symptom:** All queries return 500/ECONNREFUSED. Data still being indexed.
- **Scope:** Total query outage but data collection continues.
- **Detection:** `oc get pods -n <mch-ns> -l app=search-api`
- **Recovery:** Pod restart. search-api is stateless.

### Managed cluster disconnected
- **Symptom:** Spoke resources become stale, eventually disappear from search.
- **Scope:** Single cluster.
- **Detection:** `oc get managedclusters` -- check AVAILABLE column.

---

## 6. Data Freshness

- Normal operation: changes appear in search within seconds
- Indexer restart/rebuild: temporary lag (minutes)
- New cluster import: initial indexing proportional to resource count
- Collector restart: full re-sync from that cluster
