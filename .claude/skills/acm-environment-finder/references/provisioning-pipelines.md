# Which Jenkins job for which outcome

## Find candidates (read-only)

1. **Google Sheet** (fast, possibly stale) -- see `google-sheet.md`.
2. **Local cache** `~/.acm-env-inventory/inventory.json` -- from `scripts/refresh-inventory.py`.
3. **Jenkins** -- scan recent successful builds on provisioning jobs (primary).

## Provision OCP + ACM

| Job path | When |
|----------|------|
| `CI-Jobs/ocp_deploy_and_acm_install` | Default: new hub with ACM on cloud / vSphere / ROSA-class providers per parameter choices |

After trigger, monitor the build until it completes: when the **jenkins** MCP is available, use MCP tools for status and polling per **`../acm-jenkins-client/SKILL.md`**. If the MCP is unavailable, poll Jenkins `.../api/json` for `building` / `result` or use the Jenkins UI. If you have a local `jenkins-run` binary on your machine, you may use it; this repo does not ship that binary.

Typical runtime: on the order of 1--2 hours (varies by platform).

## Provision OCP + MCE only

| Job path | When |
|----------|------|
| `CI-Jobs/ocp_deploy_and_mce_install` | User wants MCE without ACM hub |

## Provision bare OCP

| Job path | When |
|----------|------|
| `CI-Jobs/pics_cloud_deploy` | OCP only; user will install ACM separately |

## Destroy

| CLOUD_PROVIDER / platform | Job path |
|---------------------------|----------|
| aws, azure, gcp, vsphere, eks, aks, gke | `CI-Jobs/pics_cloud_destroy` |
| ROSA | `openshift/destroy/cloud/rosa-destroy` (under Jenkins root `openshift` folder) |
| ARO | `openshift/destroy/cloud/aro-destroy` |
| OSD | `openshift/destroy/cloud/osd-destroy` |

Always resolve **InfraID** for `OCP_CLUSTER_NAME` on `pics_cloud_destroy`. If only kubeconfig or API URL is known, parse InfraID from `output.json` artifact or from cluster metadata; if impossible, ask the user.

## Credentials

| File | Content |
|------|---------|
| `~/.jenkins/config.json` | `jenkins_url`, `jenkins_user`, `jenkins_token` |

VPN: Jenkins host is internal (`jenkins-csb-rhacm-tests.dno.corp.redhat.com`).
