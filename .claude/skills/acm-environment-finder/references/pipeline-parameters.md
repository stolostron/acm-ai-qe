# Jenkins pipeline parameters and artifacts

**Reading builds and jobs:** When the host exposes the **jenkins** MCP, use **`get_job`**, **`get_build`**, and related tools (see `../acm-jenkins-client/SKILL.md`) — responses use the same JSON shapes as Jenkins REST. If the MCP is **not** available, use REST or the Jenkins UI per [jenkins-without-mcp.md](jenkins-without-mcp.md) and `../acm-jenkins-client/references/jenkins-remote-api.md`.

## Primary: `CI-Jobs/ocp_deploy_and_acm_install`

Description: Install OCP and ACM on a cloud provider.

### Parameters (filter / inventory fields)

| Parameter | Use |
|-----------|-----|
| `CLOUD_PROVIDER` | Platform (AWS, AZURE, GCP, VMWARE-*, ROSA-*, ARO, OSD, BAREMETAL, etc.) |
| `OCP_CLUSTER_NAME` | Cluster base name (not always full InfraID) |
| `OCP_VERSION` | Z-stream or empty for latest in channel |
| `OCP_RELEASE` | e.g. `stable`, `stable-4.18` |
| `REGION` | Cloud region or empty for default |
| `RHACM_SNAPSHOT_TAG` | ACM snapshot (`latest-2.17`, DOWNSTREAM tag, etc.) |
| `ACM_CHANNEL` | e.g. `2.16`, `2.17` |
| `MCE_SNAPSHOT_TAG` | MCE snapshot |
| `MCE_CHANNEL` | MCE channel |
| `SKIP_ACM_INSTALL` | `true` / `false` -- if `true`, hub may be OCP-only |
| `FIPS_ENABLED` | `true` / `false` |
| `ACM_NAMESPACE` | Usually `ocm` |
| `ACM_REPOSITORY` | konflux, acm-d, brew, production, ce |

### Artifacts (successful installs)

| Relative path | Purpose |
|---------------|---------|
| `ocp_credentials/kubeconfig` | Hub kubeconfig |
| `ocp_credentials/output.json` | Metadata (API URL, infra ID -- schema may vary; parse defensively). Details: [output-json.md](output-json.md) |

### Artifact download URL pattern

```
${BUILD_URL}artifact/ocp_credentials/kubeconfig
${BUILD_URL}artifact/ocp_credentials/output.json
```

Use HTTP Basic auth: user + API token from `~/.jenkins/config.json`.

## `CI-Jobs/ocp_deploy_and_mce_install`

Same artifact layout is typical for OCP+MCE flows; confirm per build using the `artifacts` array: when the **jenkins** MCP is available use `get_build`; otherwise use Jenkins REST (same shape as `refresh-inventory.py`) or the Jenkins UI.

## `CI-Jobs/pics_cloud_deploy`

Bare OCP; parameters differ (see Jenkins job config via `get_job` when MCP is available, or UI / `.../api/json` for the job). Use for OCP-only needs.

## Destroy: `CI-Jobs/pics_cloud_destroy`

| Parameter | Values / notes |
|-----------|----------------|
| `PLATFORM` | `aws`, `azure`, `gcp`, `vsphere`, `eks`, `aks`, `gke` |
| `OCP_CLUSTER_NAME` | **InfraID** (comma-separated for multiple). Not the same as short cluster name in all cases. |
| `REGION` | Optional |
| `CI_GIT_BRANCH` | Default `main` |

### Map `CLOUD_PROVIDER` (install job) to `PLATFORM` (destroy job)

| CLOUD_PROVIDER prefix / value | PLATFORM |
|------------------------------|------------|
| AWS, AWS-ARM, AWS-BM | aws |
| AZURE, ARO | azure (ARO may need `openshift/destroy/cloud/aro-destroy` instead -- see provisioning-pipelines.md) |
| GCP | gcp |
| VMWARE-* | vsphere |
| ROSA-CLASSIC, ROSA-HOSTED | Use ROSA destroy job, not pics_cloud_destroy |
| OSD | Use OSD destroy job |
| EKS / AKS / GKE (managed) | eks / aks / gke |
| BAREMETAL | No pics_cloud mapping -- ask user or use documented BM teardown |

## Secondary (testing) jobs

Use for "leftover env from test run" only if primary pipelines yield nothing:

- `CI-Jobs/e2e_ui_test_pipeline`
- `CI-Jobs/virt_console_e2e_tests`

Parameter names differ; always read `actions` → `ParametersAction`: use **`get_job` / `get_build`** when the **jenkins** MCP is available; otherwise from each build’s JSON via REST or the UI (see **`../acm-jenkins-client/SKILL.md`**).
