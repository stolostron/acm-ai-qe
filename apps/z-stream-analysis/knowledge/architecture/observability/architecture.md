# Observability Architecture

ACM Observability collects metrics from managed clusters and provides
dashboards via Grafana on the hub. Powered by Thanos for federated metrics.

---

## Components

| Component | Type | Namespace | Role |
|-----------|------|-----------|------|
| multicluster-observability-operator | Hub deployment | ocm | Manages the observability stack |
| Thanos (if MCO CR created) | Hub statefulset | open-cluster-management-observability | Federated metrics storage |
| Grafana (if MCO CR created) | Hub deployment | open-cluster-management-observability | Dashboard visualization |
| metrics-collector | Spoke addon | open-cluster-management-addon-observability | Collects Prometheus metrics from spoke |

## Prerequisites

- `multicluster-observability` enabled in MCH (enabled by default, but operator only)
- MultiClusterObservability (MCO) CR created with objectStorage config (S3-compatible)
- S3-compatible storage available (Minio, AWS S3, etc.)

**Important:** Enabling the MCH component only deploys the operator pod.
The full Thanos/Grafana stack requires the user to create the MCO CR with
storage configuration. Without the MCO CR, the operator sits idle.

## Console Integration

Observability dashboards are accessed through the Grafana route. The hub
metadata endpoint (`/api/hub`) reports `isObservabilityInstalled` which
controls conditional rendering of observability-related UI elements.

## Known Failure Modes

- MCO CR not created: Operator running but no observability stack deployed
- S3 storage missing: MCO CR exists but Thanos can't store metrics
- metrics-collector addon missing on spoke: No metrics from that spoke
- Hub metadata wrong: `isObservabilityInstalled` inverted, causing wrong UI rendering
