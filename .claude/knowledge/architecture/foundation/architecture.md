---
type: architecture
subsystem: foundation
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - failures/foundation/failure-signatures.md
  - versions/acm-2x-to-5x-changes.md
version_notes:
  - "cluster-proxy moved from open-cluster-management to multicluster-engine namespace in ACM 5.0"
  - "addon-manager referenced as cluster-manager-addon-manager-controller in open-cluster-management-hub"
  - "work-manager removed as standalone hub deployment; spoke-side klusterlet-addon-workmgr still exists"
  - "registration-operator renamed to cluster-manager-registration-controller"
---

# Foundation -- Architecture

The Foundation subsystem covers the OCM (Open Cluster Management) core
framework: addon management, managed cluster registration, work distribution,
cluster-proxy connectivity, and managed service accounts.

---

## Test Repository

- **Repo:** `stolostron/acmqe-autotest`
- **Framework:** Ginkgo (Go)
- **Test directory:** `pkg/tests/`
- **Branch pattern:** `main`
- **Ginkgo labels:** `[ServerFoundation]`, `[addon-framework]`, `[registration]`, `[work-agent]`

## Key Components

| Component | Namespace | Purpose |
|-----------|-----------|---------|
| `cluster-manager-registration-controller` | `open-cluster-management-hub` (3 replicas) | Manages ManagedCluster registration and CSR approval |
| `work-agent` | `open-cluster-management-agent` (spoke-side) | Executes ManifestWork on spoke clusters |
| `klusterlet-addon-workmgr` | `open-cluster-management-agent-addon` (spoke-side) | Spoke-side work manager addon. No standalone hub-side deployment in ACM 5.0. |
| `cluster-proxy` | `multicluster-engine` (2 replicas) | Provides kube-apiserver proxy to spoke clusters. Changed in ACM 5.0; previously in `open-cluster-management` in ACM 2.x. |
| `managed-serviceaccount-addon-agent` | `open-cluster-management-agent-addon` (spoke-side) | Creates ServiceAccount tokens on spoke clusters. No hub-side deployment; managed via addon framework. |
| `cluster-manager-addon-manager-controller` | `open-cluster-management-hub` (3 replicas) | Lifecycle management for ManagedClusterAddons. Changed in ACM 5.0; previously referenced as `addon-manager` in `open-cluster-management` in ACM 2.x. |

## CRDs

- `managedclusters.cluster.open-cluster-management.io`
- `managedclusteraddons.addon.open-cluster-management.io`
- `manifestworks.work.open-cluster-management.io`
- `managedclustersets.cluster.open-cluster-management.io`
- `managedserviceaccounts.authentication.open-cluster-management.io`
- `clustermanagers.operator.open-cluster-management.io`
- `managedclusters.clusterview.open-cluster-management.io` (may not exist in all versions)

## Test Structure (Ginkgo)

Tests use Go's Ginkgo framework, not Cypress. Test names follow this format:

```
[ServerFoundation] [P1][Sev1][addon-framework] Addon should reach Available status
```

- Labels in brackets (`[ServerFoundation]`, `[addon-framework]`) indicate subsystem
- Priority (`[P1]`) and severity (`[Sev1]`) are embedded in the name
- Polarion IDs appear as `RHACM4K-XXXXX` in the test description

Ginkgo assertion format:
```
Expected
    <bool>: true
to equal
    <bool>: false
```

JUnit XML output has the same schema as Cypress, but error messages and test names differ.

## Multi-Cloud Spoke Clusters

Foundation tests exercise managed cluster operations across multiple cloud providers:
- ROSA (AWS)
- Azure (AKS)
- GKE (Google)
- IKS (IBM)

All spoke clusters must be healthy, imported, and their addons in `Available` state.
