# Jenkins Remote API (REST fallback)

**Typical setup:** Jenkins (and other) MCPs are configured in **both** Cursor and Claude Code — use the MCP tools first; that is not a bottleneck.

Use this document when you need **HTTP/REST** anyway: stdlib-only scripts (same auth as MCP), `curl`, CI pipelines, or a host without the jenkins MCP. Same credentials and VPN expectations as MCP flows.

Official reference: [Jenkins Remote API](https://www.jenkins.io/doc/book/using/remote-access-api/).

## Configuration (local, not in git)

JSON file (default `~/.jenkins/config.json`):

| Key | Alternate key | Purpose |
|-----|----------------|---------|
| `jenkins_url` | `url` | Base URL, e.g. `https://jenkins.example.com/` |
| `jenkins_user` | `user` | Username |
| `jenkins_token` | `token` | API token (not password) |

HTTP **Basic** auth: `Authorization: Basic base64(user:token)`.

Many internal Jenkins instances use a corporate TLS chain; scripts in this repo may disable TLS verification for automation (same pattern as `../acm-environment-finder/scripts/refresh-inventory.py`). Prefer fixing trust store when you can.

## Job path → URL segment

Folder job `CI-Jobs/ocp_deploy_and_acm_install` maps to:

```
/job/CI-Jobs/job/ocp_deploy_and_acm_install
```

Each path segment after the first is `job/<segment>`, URL-encoded. This matches Python:

```python
from urllib.parse import quote
parts = job_path.strip("/").split("/")
"/" + "/".join(f"job/{quote(p, safe='')}" for p in parts)
```

## Reads (replace MCP `get_job` / `get_build`)

| Goal | HTTP |
|------|------|
| Job + recent builds | `GET {base}/job/.../api/json` — optional `?tree=builds[number,url,result,timestamp]` to shrink payload |
| Single build | `GET {base}/job/.../{n}/api/json` |
| Last good build | `GET {base}/job/.../lastSuccessfulBuild/api/json` (404 if none) |
| Build in progress | `building` field `true`, `result` often `null` |
| Queue | `GET {base}/queue/api/json` |

**Parameters** on a build live under `actions[]` where `_class` is `hudson.model.ParametersAction` → `parameters[{name,value}]`.

**Artifacts:** `artifacts[]` with `relativePath`. Download:

```
GET {build_url}artifact/{relativePath}
```

(`build_url` ends with `/`; strip duplicate slashes if concatenating.)

## Console log (replace MCP `get_build_log`)

Plain text (entire log can be huge):

```
GET {build_url}consoleText
```

Tail locally: `curl ... | tail -n 500` or request only if your Jenkins supports progressive log APIs (varies by plugin).

## Pipeline stages (replace MCP `get_pipeline_stages` when it works)

For **Pipeline** jobs, Workflow REST is often available:

```
GET {build_url}wfapi/describe
```

or stage detail:

```
GET {build_url}execution/wfapi/describe
```

Exact paths differ by Jenkins version and `workflow-job` plugin. If `wfapi` 404s, use **console log** parsing or MCP when present.

## JUnit / test results (replace MCP `get_test_results` when present)

If the job publishes JUnit via the standard action:

```
GET {build_url}testReport/api/json
```

If this 404s, tests may only exist as **artifacts** (e.g. `**/junit.xml`) — list `artifacts` and download the XML.

## Folder listing (replace MCP `get_all_jobs` for one folder)

```
GET {base}/job/CI-Jobs/api/json?tree=jobs[name,url,_class]
```

Adjust folder (`CI-Jobs`) to the folder you need.

## Downstream tree (replace MCP `get_downstream_tree`)

There is no single portable JSON as rich as the MCP wrapper. Practical options:

1. Inspect build `actions` for fingerprints / downstream triggers (structure varies).
2. Use job `downstreamProjects` / `upstreamProjects` on **job** JSON (declarative links, not per-build).
3. Prefer MCP `get_downstream_tree` when the host provides it.

## Crumb (CSRF) for POST

Many Jenkins instances require a crumb header for state-changing POSTs:

```
GET {base}/crumbIssuer/api/json
```

Response includes `crumbRequestField` (usually `Jenkins-Crumb`) and `crumb` (token). Send both as headers on POST, e.g.:

```bash
CRUMB=$(curl -sSk -u "$JENKINS_USER:$JENKINS_TOKEN" "$JENKINS_URL/crumbIssuer/api/json" | jq -r '.crumb')
FIELD=$(curl -sSk -u "$JENKINS_USER:$JENKINS_TOKEN" "$JENKINS_URL/crumbIssuer/api/json" | jq -r '.crumbRequestField')
```

If `crumbIssuer` 404s, crumbs may be disabled — try POST without crumb.

## Trigger parameterized build (replace MCP `trigger_build`)

**Only after explicit user approval.** Two common patterns:

### A. Jenkins UI

User opens **Build with Parameters**, pastes values you printed.

### B. HTTP `buildWithParameters`

```
POST {base}/job/.../buildWithParameters?PARAM1=value1&PARAM2=value2
```

Query string must be URL-encoded (`urllib.parse.urlencode` in Python, `--data-urlencode` in curl). Empty string parameters sometimes required — match UI defaults.

Headers: Basic auth + crumb headers if required.

### C. `curl` sketch

```bash
curl -sSk -X POST -u "$JENKINS_USER:$JENKINS_TOKEN" \
  -H "$FIELD: $CRUMB" \
  "$JENKINS_URL/job/CI-Jobs/job/ocp_deploy_and_acm_install/buildWithParameters?RHACM_SNAPSHOT_TAG=latest-2.17&CLOUD_PROVIDER=AZURE"
```

### D. Dry run

There is no universal Jenkins “dry run” flag. Options: (1) Jenkins UI “preview” if available; (2) a dedicated dry-run job in your org; (3) **do not POST** — print parameters and wait for user to confirm.

## Poll until build finishes

Loop on:

```
GET {build_url}api/json?tree=building,result,number
```

- `building: true` → still running.
- `building: false` and `result` set → terminal state.

Sleep 15–30s between polls for long installs; respect server load.

## Bundled helper script

From this skill directory:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/jenkins_api.py" --help
```

Implements authenticated GET (JSON or `consoleText`) without extra dependencies.

## MCP ↔ REST quick map

When the **jenkins** MCP is available (normal in dual Cursor + Claude Code setups), **prefer the MCP tool** in the left column. Use the right column for scripts, `curl`, or CI.

| MCP tool | REST / notes |
|----------|----------------|
| `get_job` | `GET .../job/.../api/json` |
| `get_build` | `GET .../job/.../{n}/api/json` |
| `get_build_status` | Same build JSON → `result`, `building` |
| `get_build_log` | `GET .../consoleText` (tail locally) |
| `get_pipeline_stages` | `GET .../wfapi/describe` or `execution/wfapi/describe` (when supported) |
| `get_test_results` | `GET .../testReport/api/json` or artifact XML |
| `get_all_jobs` | `GET .../job/{folder}/api/json?tree=jobs[name,url]` |
| `get_downstream_tree` | No single REST equivalent; use MCP when available |
| `analyze_pipeline` / `analyze_test_results` | Agent reasoning over JSON/logs from above |
| `trigger_build` | `POST .../build` or `.../buildWithParameters?...` + crumb |
