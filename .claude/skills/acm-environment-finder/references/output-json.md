# `ocp_credentials/output.json` (Jenkins artifact)

Successful `ocp_deploy_and_acm_install` / `ocp_deploy_and_mce_install` builds often archive `ocp_credentials/output.json` next to `kubeconfig`. **Schema is not guaranteed stable** across CI branches -- parse defensively.

## How to fetch

Same auth as kubeconfig:

```
${BUILD_URL}artifact/ocp_credentials/output.json
```

Use `curl -sSk -u USER:TOKEN` or download via Jenkins UI.

## Parsing strategy

1. Load JSON with a single top-level object or array; handle both.
2. Walk common locations for API URL and cluster/infra identifiers:

| Likely keys / paths | Purpose |
|---------------------|---------|
| Top-level `apiURL`, `apiUrl`, `serverURL`, `host` | API endpoint string |
| `status.apiURL`, `clusterInfo.api` | Nested API URL |
| `infraId`, `infraID`, `infra_id` | InfraID for destroy job |
| `metadata.name`, `clusterName`, `cluster_name` | Friendly name |
| `installConfig.metadata.name` | Base name (may not equal InfraID) |

3. If JSON is wrapped (e.g. string field containing nested JSON), try one-level `json.loads` on string values that start with `{`.
4. If still ambiguous, fall back to kubeconfig `clusters[0].cluster.server` for API URL and ask the user for InfraID for destroy.

## Destroy workflow

`pics_cloud_destroy` expects **InfraID** in `OCP_CLUSTER_NAME`, not always the same as `OCP_CLUSTER_NAME` from the install job parameters. Prefer `infraId` from `output.json` when present; else ask the user.
