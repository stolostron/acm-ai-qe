# Install Subsystem Architecture

The Install subsystem covers ACM and MCE installation, upgrade, and operator
lifecycle tests. Tests validate CSV phase progression, component enablement,
CRD availability, and downstream operator health.

---

## Test Repository

- **Repo:** `stolostron/acmqe-autotest`
- **Framework:** Ginkgo (Go)
- **Test directory:** `pkg/tests/`
- **Branch pattern:** `main`
- **Ginkgo labels:** `[Install]`, `[install]`
- **Sub-jobs:** `install_mce_e2e_tests`, `install_acm_e2e_tests`

## Key Components

| Component | Namespace | Purpose |
|-----------|-----------|---------|
| `multiclusterhub-operator` | `open-cluster-management` | Manages ACM installation via MultiClusterHub CR |
| `multicluster-engine` | `multicluster-engine` | Core MCE operator |
| `hive-operator` | `hive` | Cluster provisioning operator |
| `assisted-service` | `assisted-installer` | Assisted installation service |

## Installation Sequence

1. MCE operator installed via OLM (ClusterServiceVersion)
2. MCE CSV reaches `Succeeded` phase
3. ACM operator installed, creates MultiClusterHub CR
4. MCH operator reconciles, enables components based on spec
5. All sub-operators reach healthy state

## Jenkins Pipeline Structure

The `install_e2e_tests` pipeline has downstream sub-jobs:
- `install_mce_e2e_tests` -- MCE-specific install validation
- `install_acm_e2e_tests` -- ACM-specific install validation

Both run on the same cluster. If MCE install fails, ACM install tests cascade-fail.

## Key Parameters

| Parameter | Purpose |
|-----------|---------|
| `ACM_DS_TAG` | Downstream image tag for ACM operator |
| `ROSA_CLUSTER_NAME` | ROSA HCP cluster used for install tests |
| `OCP_VERSION` | Target OpenShift version |
