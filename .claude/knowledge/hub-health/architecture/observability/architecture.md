# Observability Subsystem -- Architecture

## What Observability Does

Observability provides multicluster metrics collection, storage, querying, alerting,
and visualization for ACM. It deploys a Thanos-based metrics stack on the hub cluster
and metrics-collector addons on managed clusters. Prometheus scrapes metrics on spokes,
the collector sends them to Thanos on the hub, and Grafana dashboards visualize the
aggregated data. Alertmanager handles alert routing and deduplication across all
managed clusters.

---

## Architecture Overview

The `multicluster-observability-operator` is the root component. It deploys the
entire observability stack on the hub cluster and generates `ManifestWorks` to deploy
metrics collection addons on managed clusters. The operator is managed by the
`multiclusterhub-operator` (enabled by default but requires explicit configuration of
the `MultiClusterObservability` CR to activate).

The architecture follows a collector-receiver-query pattern:

- **Spoke side:** observability-addon (metrics-collector) scrapes Prometheus on the
  managed cluster and remote-writes metrics to the hub's thanos-receive endpoint
- **Hub side:** thanos-receive ingests metrics, thanos-store persists to S3-compatible
  object storage, thanos-query serves queries, Grafana renders dashboards,
  alertmanager handles alerts, thanos-compactor compacts historical data

The `MultiClusterObservability` CR (`observability.open-cluster-management.io/v1beta2`)
controls all configuration: storage, retention, replicas, resource limits, node
placement, and addon settings.

---

## Key Components

### multicluster-observability-operator (hub)

- **Namespace:** `open-cluster-management`
- **Pod label:** `app=multicluster-observability-operator`
- **CR Kind:** `MultiClusterObservability` (`observability.open-cluster-management.io/v1beta2`)

Root operator. Watches the MCO CR and reconciles the full observability stack:
thanos-receive, thanos-query, thanos-store, thanos-compactor, thanos-rule,
grafana, alertmanager, rbac-query-proxy, observatorium-api/operator, and
memcached instances. Also manages addon deployment to managed clusters via
ManifestWorks.

### observability-addon / metrics-collector (spoke)

- **Addon name:** `observability-controller`
- **Spoke namespace:** `open-cluster-management-addon-observability`
- **Hub addon label:** `app=endpoint-observability-operator`
- **Default:** Enabled (when MCO CR exists)

Runs on each managed cluster. The endpoint-observability-operator deploys
metrics-collector which scrapes the local Prometheus `/federate` endpoint
and remote-writes selected metrics to thanos-receive on the hub. Also
forwards spoke alertmanager alerts to the hub alertmanager.

Configurable via the `observabilityAddonSpec` in the MCO CR:
- `enableMetrics`: Toggle metrics collection (default: true)
- `workers`: Number of internal workers in the metric collector process
  (shards `/federate` requests for parallel remote-write)

Disable per-cluster via label: `observability: disabled` on ManagedCluster.

### thanos-receive (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app.kubernetes.io/name=thanos-receive`
- **Type:** StatefulSet (3 replicas default)

Accepts incoming remote-write requests from spoke collectors. Writes to
local Prometheus TSDB. Periodically (every 2 hours) uploads TSDB blocks to
object storage for long-term retention.

Retention configurable via `RetentionInLocal` (MCO v1beta2).

### thanos-query (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app.kubernetes.io/name=thanos-query`
- **Type:** Deployment (2 replicas default)

Query engine. Serves PromQL queries by fanning out to thanos-store (object
storage) and thanos-receive (recent data). Frontend for Grafana dashboards.

### thanos-query-frontend (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app.kubernetes.io/name=thanos-query-frontend`
- **Type:** Deployment (2 replicas default)

Caching proxy in front of thanos-query. Uses memcached for query result
caching. Splits long-range queries into smaller intervals.

### thanos-store-shard (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app.kubernetes.io/name=thanos-store`
- **Type:** StatefulSet (3 replicas default)

API gateway for object storage. Serves historical metric data from S3-compatible
storage. Keeps a small local cache of remote block metadata. Local data is
safe to delete across restarts (at the cost of longer startup).

### thanos-compactor (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app.kubernetes.io/name=thanos-compact`
- **Type:** StatefulSet (1 replica)

Compacts and downsamples TSDB blocks in object storage. Applies retention
policy. Needs local disk space for intermediate processing.

Four built-in alerts monitor compactor health:
- `ACMThanosCompactHalted` (critical): compactor stopped
- `ACMThanosCompactHighCompactionFailures` (warning): >5% failure rate
- `ACMThanosCompactBucketHighOperationFailures` (warning): >5% bucket op failures
- `ACMThanosCompactHasNotRun` (warning): no upload in 24 hours

### thanos-rule (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app.kubernetes.io/name=thanos-rule`
- **Type:** StatefulSet (3 replicas default)

Evaluates Prometheus recording and alerting rules against thanos-query. Writes
rule results back to local Prometheus TSDB format. Retention configurable via
`RetentionInLocal`.

### grafana (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app=grafana`
- **Type:** Deployment (2 replicas default)
- **Version:** Grafana 11.6.1

Visualization layer. Renders pre-built dashboards using thanos-query as
datasource. Dashboards are static (loaded by grafana-dashboard-loader sidecar).
Accessible from ACM console header link.

### alertmanager (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app=alertmanager`
- **Type:** StatefulSet (3 replicas default)
- **Version:** Prometheus Alertmanager 0.28.1

Receives alerts from thanos-rule and forwarded spoke alertmanager alerts.
Handles deduplication, grouping, routing, silencing, and inhibition.
Stores `nflog` data and silenced alerts in persistent storage.

### rbac-query-proxy (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app=rbac-query-proxy`
- **Type:** Deployment (2 replicas default)

RBAC-aware proxy in front of thanos-query. Enforces user permissions for
Grafana dashboard access. Uses OAuth proxy sidecar for authentication.

### observatorium-api (hub)

- **Namespace:** `open-cluster-management-observability`
- **Pod label:** `app.kubernetes.io/name=observatorium-api`
- **Type:** Deployment (2 replicas default)

API gateway for the observability stack. Routes requests to appropriate
backend components.

---

## Component Versions (ACM 2.17)

| Component | Version |
|---|---|
| Grafana | 11.6.1 |
| Thanos | 0.37.2 |
| Prometheus Alertmanager | 0.28.1 |
| Prometheus | 2.55.1 |
| Prometheus Operator | 0.81.0 |
| Kube State Metrics | 2.15.0 |
| Node Exporter | 1.9.1 |
| Memcached Exporter | 0.15.2 |

---

## Resource Requirements

The full observability stack requires approximately **2701 mCPU** and **11972 Mi memory**
for a deployment with 5 managed clusters. The heaviest components are:

| Component | CPU (total) | Memory (total) |
|---|---|---|
| thanos-receive (3 replicas) | 900 mCPU | 1536 Mi |
| thanos-store-shard (3 replicas) | 300 mCPU | 3072 Mi |
| thanos-query (2 replicas) | 600 mCPU | 2048 Mi |
| thanos-compactor (1 replica) | 100 mCPU | 512 Mi |
| thanos-rule (3 replicas) | 150 mCPU | 1536 Mi |
| alertmanager (3 replicas) | 27 mCPU | 735 Mi |

---

## Object Storage (External Dependency)

Observability is the only ACM feature that requires external storage.
Thanos needs S3-compatible object storage for metrics persistence. The
`thanos-object-storage` secret in `open-cluster-management-observability`
namespace holds the storage credentials.

Supported providers:
- Amazon Web Services S3
- Red Hat Ceph (S3-compatible)
- Google Cloud Storage
- Azure Blob Storage
- Red Hat OpenShift Data Foundation
- Red Hat OpenShift on IBM Cloud (ROKS)

Missing or misconfigured storage causes thanos-store and thanos-compactor to
crash. This is the most common deployment issue.

---

## Persistent Volumes

Multiple PVs are required (each replica gets its own PV):

| Component | Purpose |
|---|---|
| alertmanager | Stores nflog and silenced alerts |
| thanos-compactor | Intermediate data for compaction, bucket state cache |
| thanos-rule | Recording/alerting rule evaluation results |
| thanos-receive-default | Local TSDB cache before upload to object storage |
| thanos-store-shard | Remote block metadata cache |

Do not use local storage operator or local volumes -- data loss occurs if pod
reschedules to a different node. Block storage recommended (similar to Prometheus).

---

## Configuration

### MCH Component Toggle

The `multicluster-observability-operator` is enabled by default in MCH, but
the operator itself requires the `MultiClusterObservability` CR to be created
in the `open-cluster-management-observability` namespace before it deploys
anything.

Minimum viable CR:

```yaml
apiVersion: observability.open-cluster-management.io/v1beta2
kind: MultiClusterObservability
metadata:
  name: observability
spec:
  observabilityAddonSpec: {}
  storageConfig:
    metricObjectStorage:
      name: thanos-object-storage
      key: thanos.yaml
```

### Hub Self-Management

When `disableHubSelfManagement` is `false` (default), the hub cluster is always
configured to collect and send its own metrics regardless of the setting.
Hub metrics appear in the `local-cluster` namespace in Grafana.

### Per-Cluster Disable

Add `observability: disabled` label to a ManagedCluster to exclude it from
metrics collection.

### STS Token Support

For AWS STS-based S3 access, annotate service accounts in the `advanced`
section of the MCO CR with `eks.amazonaws.com/role-arn`.

---

## Cross-Subsystem Dependencies

| Dependency | Why |
|---|---|
| S3-compatible object storage | Long-term metrics persistence; if misconfigured, thanos-store crashes |
| Managed cluster connectivity | metrics-collector needs klusterlet for spoke communication |
| addon-manager | Deploys observability-addon to spokes via ManifestWorks |
| MCH/MCE operators | Lifecycle management of the observability operator |
| Console | Proxies Grafana dashboard access from browser, provides Grafana link |
| Prometheus (spoke) | Source of metrics on managed clusters; collector scrapes `/federate` |

## What Depends on Observability

| Consumer | Impact When Observability Is Down |
|---|---|
| Grafana dashboards | Dashboards empty, no data visualization |
| Console overview widgets | Observability widgets on overview page show no data |
| Alertmanager integrations | No alert forwarding from managed clusters |
| Compliance monitoring | Governance metrics (`policy_governance_info`) not aggregated |
| Capacity planning | Cluster resource utilization data unavailable |
