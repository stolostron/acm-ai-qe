# Jenkins without MCP (clone-friendly)

**When MCP is available:** If the host exposes the **jenkins** MCP, interactive agents should use it for reads and approved triggers — see `../acm-jenkins-client/SKILL.md`. That is the default path whenever the tool is present.

The bundled `scripts/refresh-inventory.py` uses **only Python 3 stdlib** and the Jenkins REST API (`urllib`), so **no MCP is required inside that script** to refresh `inventory.json`. This file still describes REST for that reason and for fresh clones that only run scripts.

## Read builds and artifacts

Same JSON as the script: `GET {jenkins_url}/job/.../job/{name}/{build_number}/api/json` with Basic auth (`user:apiToken`). Artifact relative paths appear under `artifacts[]`.

## Provision or destroy (no MCP)

1. Print the full parameter map for the user (job URL + table).
2. User triggers **Build with Parameters** in the Jenkins UI, **or** uses their own automation (e.g. `curl` to `/buildWithParameters` with a crumb — see [Jenkins Remote API](https://www.jenkins.io/doc/book/using/remote-access-api/)).
3. When an agent has the jenkins MCP, use `trigger_build` after approval; otherwise use UI or REST as documented in `../acm-jenkins-client/references/jenkins-remote-api.md`.

## Credentials

Default config path is `~/.jenkins/config.json` (override with `--config`). Keys: `jenkins_url`, `jenkins_user`, `jenkins_token`. This file is **local** to each machine, not committed to git.

**Transcripts:** Never paste `jenkins_token`, kubeconfig bodies, or other secrets into chat logs. Refer to paths on disk (`$UNIQUE_KUBECONFIG`, config file location) and redacted summaries only.
