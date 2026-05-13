# Foundation Subsystem Architecture

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
| `registration-controller` | `open-cluster-management-hub` | Manages ManagedCluster registration and CSR approval |
| `work-agent` | `open-cluster-management-agent` | Executes ManifestWork on spoke clusters |
| `work-manager` | `open-cluster-management-hub` | Creates and tracks ManifestWork from hub |
| `cluster-proxy` | `open-cluster-management` | Provides kube-apiserver proxy to spoke clusters |
| `managed-serviceaccount` | `open-cluster-management` | Creates ServiceAccount tokens on spoke clusters |
| `addon-manager` | `open-cluster-management` | Lifecycle management for ManagedClusterAddons |

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
