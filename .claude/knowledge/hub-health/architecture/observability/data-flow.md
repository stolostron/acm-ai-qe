# Observability Subsystem -- Data Flow

## End-to-End Data Movement

```
Spoke Cluster(s)                     Hub Cluster
Prometheus                           open-cluster-management-observability namespace
  |                                  ┌─────────────────────────────────────────────┐
  v                                  │                                             │
metrics-collector  -- remote-write ->│  thanos-receive (ingests, local TSDB)       │
(observability addon)                │       |                                     │
                                     │       v (every 2h)                          │
spoke alertmanager -- forward ------>│  S3 Object Storage (long-term persistence)  │
                                     │       |                                     │
                                     │       v                                     │
                                     │  thanos-store (serves from S3)              │
                                     │       |                                     │
                                     │  thanos-compactor (compacts, downsamples)   │
                                     │       |                                     │
                                     │       v                                     │
                                     │  thanos-query (fans out to receive + store) │
                                     │       |                                     │
                                     │       v                                     │
                                     │  thanos-query-frontend (caches via memcached)│
                                     │       |                                     │
                                     │       v                                     │
                                     │  rbac-query-proxy (RBAC enforcement)        │
                                     │       |                                     │
                                     │       v                                     │
                                     │  Grafana (dashboards)                       │
                                     │                                             │
                                     │  thanos-rule (evaluates recording/alerting) │
                                     │       |                                     │
                                     │       v                                     │
                                     │  alertmanager (routing, dedup, silencing)   │
                                     └─────────────────────────────────────────────┘
```

---

## 1. Spoke Side: Metrics Collection

### What Gets Scraped

The endpoint-observability-operator deploys a metrics-collector on each managed
cluster. The collector scrapes the local Prometheus `/federate` endpoint for a
curated set of metrics defined by the `observability-metrics-allowlist` ConfigMap.

Default metrics include:
- Cluster info: `acm_managed_cluster_info` (vendor, cloud, version, availability)
- Governance: `policy_governance_info`, `cluster_policy_governance_info`,
  `config_policies_evaluation_duration_seconds_*`
- Search: `search_api_*`, `search_indexer_*`
- Policy reports: `policyreport_info`
- Platform metrics: kube-state-metrics, node-exporter, etcd, apiserver

The allowlist is not user-modifiable (default metrics), but custom metrics can
be added via `custom-allowlist` ConfigMap.

### How It Sends Data

- **Protocol:** HTTPS remote-write to hub's thanos-receive service
- **Transport:** Prometheus remote-write protocol (protobuf over HTTP)
- **Auth:** Addon framework credentials (SA token from ManifestWork)
- **Workers:** Configurable `workers` parameter shards `/federate` requests
  for parallel remote-write (Technology Preview)
- **Alert forwarding:** Spoke alertmanager alerts forwarded to hub alertmanager
  (auto-configured by endpoint operator updating `cluster-monitoring-config` CM)

### Per-Cluster Controls

- `observability: disabled` label on ManagedCluster skips that cluster
- `enableMetrics: false` in `observabilityAddonSpec` disables all clusters
- When a managed cluster is detached, `metrics-collector` deployments are removed

---

## 2. Hub Side: thanos-receive

Ingests remote-write data from all spoke collectors:
1. Accepts incoming HTTPS remote-write requests
2. Writes to local Prometheus TSDB
3. Periodically (every 2 hours) uploads TSDB blocks to S3 object storage
4. Receive-controller manages hashring for multi-replica distribution

Handles concurrent writes from all managed clusters simultaneously.
`RetentionInLocal` parameter controls how long data stays in local TSDB before
relying solely on object storage.

---

## 3. Hub Side: Object Storage (S3)

Long-term persistence layer. Stores TSDB blocks uploaded by thanos-receive.
Contains:
- Raw metric samples (5m resolution)
- Downsampled data (5m and 1h resolutions after compaction)
- Block metadata

Object storage is the single source of truth for historical metrics.
Without it, only recent data in thanos-receive local TSDB is available.

---

## 4. Hub Side: thanos-store

Serves queries against object storage:
1. Receives query requests from thanos-query
2. Loads block metadata from S3
3. Fetches relevant TSDB blocks
4. Returns metric data

Maintains a small local cache of block metadata. Startup time is proportional
to the number of blocks in storage (more clusters and longer retention = more
blocks = slower startup).

---

## 5. Hub Side: thanos-compactor

Background maintenance of object storage:
1. Scans for uploadable blocks
2. Compacts small blocks into larger blocks
3. Applies downsampling (5m and 1h resolutions)
4. Enforces retention policy (deletes blocks older than configured retention)
5. Cleans up partial or corrupted blocks

Only one replica runs (singleton). If halted, query performance degrades over
time as uncompacted blocks accumulate.

---

## 6. Hub Side: thanos-query

Query engine that serves PromQL:
1. Receives query from thanos-query-frontend (or direct)
2. Fans out to data sources: thanos-receive (recent) and thanos-store (historical)
3. Deduplicates overlapping data from multiple sources
4. Returns merged results

This is the datasource configured in Grafana. Also serves thanos-rule for
recording and alerting rule evaluation.

---

## 7. Hub Side: thanos-query-frontend

Caching and query optimization layer:
1. Receives queries from rbac-query-proxy
2. Checks memcached for cached results
3. Splits long-range queries into smaller intervals
4. Forwards cache misses to thanos-query
5. Caches results in memcached for future queries

---

## 8. Hub Side: rbac-query-proxy

RBAC enforcement layer:
1. Receives authenticated requests (OAuth proxy sidecar handles auth)
2. Evaluates user RBAC permissions
3. Filters accessible managed clusters
4. Proxies authorized queries to thanos-query-frontend

---

## 9. Hub Side: Grafana

Visualization:
1. Loads pre-built dashboards from grafana-dashboard-loader sidecar
2. User accesses via Grafana link in ACM console header
3. Queries thanos (through rbac-query-proxy -> query-frontend -> query)
4. Renders time-series visualizations

Dashboards are static (shipped with the product). Custom dashboards can be
designed but are not persisted across upgrades.

---

## 10. Hub Side: thanos-rule

Recording and alerting rule evaluation:
1. Periodically evaluates Prometheus recording rules against thanos-query
2. Writes recording rule results to local TSDB
3. Evaluates alerting rules
4. Fires alerts to alertmanager

Built-in ACM alerts include compactor health alerts and can be extended with
custom recording and alerting rules.

---

## 11. Hub Side: alertmanager

Alert management:
1. Receives alerts from thanos-rule (hub-side rules)
2. Receives forwarded alerts from spoke alertmanagers
3. Deduplicates, groups, and routes alerts
4. Sends notifications to configured integrations (email, Slack, PagerDuty, OpsGenie)
5. Handles silencing and inhibition
6. Stores state (nflog, silences) in persistent storage

---

## Failure Modes at Each Hop

### metrics-collector down on spoke
- **Symptom:** No new metrics from that spoke. Grafana dashboards show gaps.
- **Scope:** Only that spoke. Other clusters unaffected.
- **Detection:** `oc get managedclusteraddon observability-controller -n {cluster}`
- **Recovery:** Automatic on addon restart. Spoke data gap during downtime.

### thanos-receive down
- **Symptom:** All incoming metrics rejected. Spoke collectors log remote-write errors.
- **Scope:** All clusters -- no new data ingested.
- **Detection:** `oc get pods -n open-cluster-management-observability -l app.kubernetes.io/name=thanos-receive`
- **Recovery:** Pod restart. Local TSDB data persists on PVC. Collectors retry.

### Object storage unreachable
- **Symptom:** thanos-store and thanos-compactor crash or error. Historical queries fail.
  Recent data (in thanos-receive TSDB) still queryable.
- **Scope:** Historical data unavailable. Recent data (last 2h window) still works.
- **Detection:** Check thanos-store and thanos-compactor logs for S3 connection errors.
- **Recovery:** Fix storage credentials or network. Components auto-recover on reconnect.

### thanos-store down
- **Symptom:** Historical queries fail. Recent data from thanos-receive still available.
- **Scope:** Long-range queries return incomplete data.
- **Detection:** `oc get pods -n open-cluster-management-observability -l app.kubernetes.io/name=thanos-store`
- **Recovery:** Pod restart. Block metadata re-cached from S3 (slower startup).

### thanos-compactor halted
- **Symptom:** No immediate visible impact. Over time: query performance degrades,
  storage usage grows, retention not enforced.
- **Scope:** Background maintenance stops. Data accumulates.
- **Detection:** `ACMThanosCompactHalted` alert fires. Check compactor pod status.
- **Recovery:** Fix root cause (often disk space), restart compactor.

### thanos-query down
- **Symptom:** ALL Grafana dashboards empty. All metric queries fail.
- **Scope:** Total query outage. Data still being ingested and stored.
- **Detection:** `oc get pods -n open-cluster-management-observability -l app.kubernetes.io/name=thanos-query`
- **Recovery:** Pod restart. thanos-query is stateless.

### grafana down
- **Symptom:** Dashboard UI unavailable. Data still being collected and queryable via API.
- **Scope:** Visualization only.
- **Detection:** `oc get pods -n open-cluster-management-observability -l app=grafana`
- **Recovery:** Pod restart. Grafana is stateless (dashboards loaded from sidecar).

### alertmanager down
- **Symptom:** No alert notifications sent. Alerts still evaluated by thanos-rule.
- **Scope:** Alert routing only.
- **Detection:** `oc get pods -n open-cluster-management-observability -l app=alertmanager`
- **Recovery:** Pod restart. State (nflog, silences) restored from PVC.

### Managed cluster disconnected
- **Symptom:** Metrics from that spoke become stale. Last data point before disconnect.
- **Scope:** Single cluster.
- **Detection:** `oc get managedclusters` -- check AVAILABLE column.

---

## Data Freshness and Retention

- Normal operation: spoke metrics appear on hub within seconds to minutes
  (depends on scrape interval and remote-write batching)
- thanos-receive TSDB: data available immediately after ingestion
- Object storage upload: every 2 hours from thanos-receive
- Compaction: background process, may lag hours behind ingestion
- Default retention: configurable via `retentionConfig` in MCO CR
  (Thanos downsampling resolution: raw, 5m, 1h)
- Historical data requires object storage; without it only local TSDB window
  is available (configured by `RetentionInLocal`)
