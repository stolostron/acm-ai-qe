---
type: architecture
subsystem: install
acm_version: "5.0"
last_verified: 2026-08-17
related:
  - failures/install/failure-signatures.md
  - versions/acm-2x-to-5x-changes.md
version_notes:
  - "MCH namespace default changed from open-cluster-management to ocm in ACM 5.0"
  - "hive-operator moved from hive namespace to multicluster-engine in ACM 5.0"
  - "CSV version format changed from v2.x.y to v5.0.0-xxx in ACM 5.0"
---

# Install -- Architecture

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
| `multiclusterhub-operator` | `ocm` (Changed in ACM 5.0; previously `open-cluster-management` in ACM 2.x) | Manages ACM installation via MultiClusterHub CR. 2 replicas. |
| `multicluster-engine-operator` | `multicluster-engine` | Core MCE operator. 2 replicas. |
| `hive-operator` | `multicluster-engine` (Changed in ACM 5.0; previously `hive` in ACM 2.x) | Cluster provisioning operator. 1 replica. |
| `assisted-service` | `assisted-installer` | Assisted installation service [NOT VERIFIED: assisted-installer namespace not checked on this cluster] |

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

---

## Upstream vs Downstream Build Pipeline (Fix Propagation)

When a PR merges to `stolostron/console` (or any ACM component), it goes through **two separate, independent build systems** before it reaches a provisioned cluster. Understanding this distinction is critical for fix verification timing.

### The Two Systems

| System | Purpose | Registry | Trigger | Completion time |
|--------|---------|----------|---------|-----------------|
| **Upstream (quay-retag)** | Tag upstream community images on quay.io | `quay.io/stolostron/<component>` | Merge to `main` or `release-X.Y` | 1-2 hours |
| **Downstream (Konflux)** | Build RHEL-based images, rebuild OLM catalog index | `quay.io:443/acm-d/<component>-rhel9` + `acm-dev-catalog:latest-X.Y` | Detected by Konflux build system | 12-24 hours |

### Upstream Pipeline (quay-retag)

1. PR merges to `stolostron/<component>` (`main` or `release-X.Y` branch)
2. CI detects the merge and builds an upstream image
3. The `stolostron/pipeline` repo (`quay-retag` branch) receives a commit: `"Stage X.Y.0 snapshot of <component>-<commit-sha>"`
4. The upstream image is tagged on `quay.io/stolostron/<component>:<version>-<sha>`
5. The `TAG` file in the pipeline repo is updated with a new timestamp

**This is what appears fast.** The `stolostron/pipeline` repo shows the commit within 1-2 hours. But this ONLY updates the upstream quay.io images -- it does NOT update the downstream catalog.

### Downstream Pipeline (Konflux → OLM Catalog)

1. Konflux detects the new commit on the component's release branch
2. Konflux builds the downstream RHEL-based image (`<component>-rhel9`)
3. The image is pushed to `quay.io:443/acm-d/<component>-rhel9`
4. The operator bundle is updated to reference the new component image digest
5. The catalog index is rebuilt (this bundles ALL component images into one index)
6. The `acm-dev-catalog:latest-X.Y` tag is updated to point to the new index

**This is what actually matters for provisioned environments.** When the Jenkins pipeline uses `RHACM_SNAPSHOT_TAG=latest-X.Y` with `ACM_REPOSITORY=konflux`, OLM pulls from step 6's output.

### Why the Lag Exists

Steps 2-6 in the downstream pipeline are sequential and each takes time:
- Component image build: ~30-60 minutes
- Bundle update: ~30 minutes
- Catalog index rebuild: ~60-120 minutes (aggregates ALL components)
- The catalog rebuild is batched, not per-component

Total: 12-24 hours from PR merge to catalog availability.

### How to Tell Which System You're Looking At

| Indicator | System |
|-----------|--------|
| `stolostron/pipeline` repo commit messages | Upstream (quay-retag) |
| `quay.io/stolostron/<component>` image tags | Upstream |
| `quay.io:443/acm-d/<component>-rhel9` image digests | Downstream |
| `acm-dev-catalog:latest-X.Y` catalog image | Downstream (what OLM uses) |
| MCH `currentVersion` (e.g., `5.0.0-215`) | Downstream version number from catalog |
| CSV `relatedImages` entries | Downstream image digests that are actually deployed |

### Practical Impact on Fix Verification

| Scenario | What works | What doesn't |
|----------|-----------|--------------|
| PR merged 2 hours ago, pipeline repo shows staging | Upstream image exists | Downstream catalog NOT updated yet — provisioning will get the OLD image |
| PR merged 24 hours ago | Both upstream and downstream should be current | Safe to provision |
| Cluster provisioned, fix not present | Use Op 2 (Refresh) to force catalog re-pull | Only works if downstream catalog has been updated since merge |

### Rule: Wait 24 hours for downstream propagation

Before provisioning a cluster specifically to verify a fix, wait at least 24 hours after the PR merge. If provisioning sooner, expect that the fix may not be in the deployed images even though the upstream pipeline repo shows the commit as "staged".
