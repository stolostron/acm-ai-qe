---
name: acm-environment-finder
description: >-
  Finds, provisions, or destroys ACM QE test environments using Jenkins provisioning job
  history (ocp_deploy_and_acm_install), local cache at ~/.acm-env-inventory, optional
  team Google Sheet, and hub validation via the in-repo sibling acm-hub-health-check skill.
  Use when the user asks to find an environment, usable cluster, ACM hub for a version
  (e.g. 2.15.2, 2.17), Azure/AWS/GCP/VMware platform, spokes or freshness, refresh
  environment inventory, provision or create a new ACM/OCP environment, destroy or
  tear down a cluster by URL name or Jenkins build, or match CI sheet rows to live hubs.
compatibility: >-
  Requires Python 3, VPN for Red Hat Jenkins, Jenkins API credentials at ~/.jenkins/config.json
  (see references/jenkins-without-mcp.md), and oc CLI for kubeconfig-based checks.
  Google Sheet: optional (MCP or API). Jenkins: when the host exposes the jenkins MCP, use it for
  interactive reads and triggers; otherwise REST/UI per references. refresh-inventory.py uses REST only
  (no MCP inside the process) — see ../acm-jenkins-client/SKILL.md and references/jenkins-without-mcp.md.
  Hub diagnostics: ../acm-hub-health-check/SKILL.md.
metadata:
  author: acm-qe
  version: "1.2.0"
---

# ACM Environment Finder

Orchestrates **find**, **provision**, and **destroy** flows for ACM QE environments. **Everything in this folder plus sibling `.claude/skills/*` in the same repository is authoritative** — do not rely on skills or MCP packs that are not part of the clone. See [references/agent-skills-primer.md](references/agent-skills-primer.md).

**Secrets in chat:** Never paste `jenkins_token`, kubeconfig contents, or other credentials into the transcript. Use file paths on disk and redacted summaries (server host, build number, cluster name only).

## How this skill fits

1. **Inventory:** Run the bundled `scripts/refresh-inventory.py` (stdlib + Jenkins REST inside the script — no MCP inside the process). See [references/jenkins-without-mcp.md](references/jenkins-without-mcp.md).
2. **Optional sheet:** If the runtime has Google Sheets access, use it; otherwise skip and use cache + Jenkins only.
3. **Hub validation:** After kubeconfig is downloaded and **`KUBECONFIG`** is exported, run the **preflight gate** (`scripts/hub_validation_gate.py`) then follow **`../acm-hub-health-check/SKILL.md`** (Quick depth by default). **No substitutes:** do not replace that procedure with ad-hoc `oc` checklists or unrelated skills; only that sibling file (deeper depth only if the user asks within that skill). See [references/sibling-skills.md](references/sibling-skills.md) and [references/hub-validation-gate.md](references/hub-validation-gate.md).
4. **Jenkins reads/triggers (interactive):** When the host exposes the **jenkins** MCP, use it for reads and approved triggers (`get_job`, `get_build`, `trigger_build`, etc.) per **`../acm-jenkins-client/SKILL.md`**. If the MCP is not available, use Jenkins REST, `jenkins_api.py`, or the UI per [references/jenkins-without-mcp.md](references/jenkins-without-mcp.md). The refresh script uses REST only (no MCP inside the process).

## Prerequisites

| Need | Detail |
|------|--------|
| VPN | Jenkins and many clusters are internal |
| Jenkins API | `~/.jenkins/config.json` or `--config` (see [references/jenkins-without-mcp.md](references/jenkins-without-mcp.md)) |
| Google Sheet | Optional; team spreadsheet ID is in [references/google-sheet.md](references/google-sheet.md) |
| `oc` CLI | Kubeconfig download + login for hub checks |
| Hub methodology | In-repo: `../acm-hub-health-check/SKILL.md` |

## Progressive disclosure

- Repo-local siblings and portability rules: [references/sibling-skills.md](references/sibling-skills.md)
- Jenkins without MCP: [references/jenkins-without-mcp.md](references/jenkins-without-mcp.md)
- Design primer: [references/agent-skills-primer.md](references/agent-skills-primer.md)
- Testing checklist: [references/testing-and-metrics.md](references/testing-and-metrics.md)
- Sheet parsing: [references/google-sheet.md](references/google-sheet.md)
- Jenkins parameters: [references/pipeline-parameters.md](references/pipeline-parameters.md)
- Job routing: [references/provisioning-pipelines.md](references/provisioning-pipelines.md)
- Hub preflight gate (machine-readable handoff): [references/hub-validation-gate.md](references/hub-validation-gate.md)
- `output.json` parsing: [references/output-json.md](references/output-json.md)

## Inventory cache

This is **not** a documentation or knowledge database. **`inventory.json`** is a **local machine cache**: JSON written by `scripts/refresh-inventory.py` after querying Jenkins provisioning jobs. Each `entries[]` item summarizes a build (parameters, timestamp, whether `kubeconfig` artifacts exist, etc.) so find-mode can rank candidates without hitting Jenkins for every row on every request.

| Path | Role |
|------|------|
| `~/.acm-env-inventory/inventory.json` | Last successful refresh output (`entries` array) |
| `~/.acm-env-inventory/last-refresh.txt` | Unix epoch seconds of last refresh |

**First run or empty cache:** If `inventory.json` is missing, unreadable, or `entries` is empty/missing, run a refresh **before** Mode 1 Step C (same commands below). Success: exit code **0** and stdout ending with JSON that includes a non-empty `entries` (or an explicit empty list if Jenkins truly has no matching history yet).

**Lazy refresh:** If `last-refresh.txt` is older than **2 hours**, run a refresh.

Use one of (same pattern for `refresh-inventory.py` and `hub_validation_gate.py`):

```bash
# Recommended: from the repository clone root (portable across agent hosts and CI)
python3 "$(git rev-parse --show-toplevel)/.claude/skills/acm-environment-finder/scripts/refresh-inventory.py"
```

```bash
# Alternative: set SKILL_DIR to the absolute path of this skill folder (acm-environment-finder), then:
python3 "${SKILL_DIR}/scripts/refresh-inventory.py"
```

Pass `--dry-run` to print JSON without writing `inventory.json`.

**Expected output (refresh script):** Exit code 0; stdout ends with JSON containing `entries` (build metadata, `has_kubeconfig_artifact`, etc.). On failure, stderr explains auth or network.

## MANDATORY: Gate enforcement

| Action | Gate |
|--------|------|
| Read sheet, read Jenkins, read cache, download artifacts | No user approval |
| Remote Jenkins trigger (API, MCP, or any automation) | **Explicit user approval** after showing full job path + parameters |
| `oc` against a cluster | Session-specific kubeconfig; read-only for find |

Todo pattern for provision/destroy:

```
discover-candidates | pending
prepare-jenkins-params | pending
GATE: user-approval | pending
trigger-build | pending
monitor-or-handoff | pending
```

Do not mark `GATE: user-approval` completed without user confirmation.

**CRITICAL:** Never trigger a Jenkins build until the user has explicitly approved the exact job path and parameter map shown in the session.

---

## Instructions

### Mode 1: Find

### Step A -- Parse user criteria

Capture when provided: ACM version or snapshot (`2.15.2`, `latest-2.17`, DOWNSTREAM tag), OCP version, `CLOUD_PROVIDER` / platform, need for **spokes**, **freshness** (prefer newer `build_timestamp` / Running sheet rows).

### Step B -- Sheet first (optional)

If the agent has **Google Sheet** access (same API your runtime uses for `read_sheet_values`), load the sheet in [references/google-sheet.md](references/google-sheet.md). Prefer rows with Status **Running** that match version/platform. If there is no Sheet access, **skip** this step and rely on cache + Jenkins.

### Step C -- Local cache

Read `~/.acm-env-inventory/inventory.json` (see [Inventory cache](#inventory-cache)). If the file is missing or `entries` is absent/empty, run `refresh-inventory.py` per that section, then re-read the file.

Filter `entries` where `build_result == "SUCCESS"` (and `skip_acm_install` is false unless user wants OCP-only). Sort by `build_timestamp` descending.

### Step D -- Jenkins live (fill gaps)

When the **jenkins** MCP is available on the host, use **`get_job` / `get_build`** (and related MCP tools) for live job and build data — same JSON shapes as REST. If the MCP is **not** available, use Jenkins REST (same endpoints as `refresh-inventory.py`) or the Jenkins UI. Jobs listed in [references/provisioning-pipelines.md](references/provisioning-pipelines.md). Merge with cache; prefer artifacts present (`has_kubeconfig_artifact`).

### Step E -- Rank candidates

1. Successful install with matching **RHACM_SNAPSHOT_TAG** / **ACM_CHANNEL** / user version substring.
2. Matching **CLOUD_PROVIDER** / region.
3. Newer timestamp.
4. **No newer overwrite:** For each candidate, scan builds *after* it on the same `OCP_CLUSTER_NAME`. If a later build targets the same cluster with a different snapshot, the candidate is stale -- discard it.

### Step E.5 -- Reachability gate (mandatory, before Step F)

**NEVER present a candidate without verifying it is alive first.** The sheet is frequently stale (clusters destroyed but still listed as "Running"). For every candidate that passes Step E ranking:

```bash
curl -sk --max-time 10 -o /dev/null -w "%{http_code}" "https://console-openshift-console.apps.<cluster>.<domain>"
```

- **HTTP 200**: Proceed to Step F (full health check).
- **Any other result** (000, ERR_NAME_NOT_RESOLVED, timeout): Discard. Mark as dead in working notes and move to next candidate.

This is a fast (~1s) pre-filter. Do not skip it.

### Step F -- Health check (mandatory before recommending)

1. Build artifact URL: `{jenkins_build_url}artifact/ocp_credentials/kubeconfig`
2. `curl -sSk -u "$JENKINS_USER:$JENKINS_TOKEN" -o "$UNIQUE_KUBECONFIG" "$URL"` (credentials from `~/.jenkins/config.json` or your `--config` file)
3. `export KUBECONFIG=$UNIQUE_KUBECONFIG`
4. **Preflight gate (required):** run `scripts/hub_validation_gate.py` — same path patterns as `refresh-inventory.py` ([Inventory cache](#inventory-cache)). **Require exit code 0.** Parse the single JSON object on stdout: use `hub_skill_abspath` for the next step; on failure use `exit_reason` / `hint` and retry or pick another candidate. This script checks clone integrity + `oc` + cluster reachability; it is **not** a hub health diagnosis.

   ```bash
   python3 "$(git rev-parse --show-toplevel)/.claude/skills/acm-environment-finder/scripts/hub_validation_gate.py"
   ```

   ```bash
   python3 "${SKILL_DIR}/scripts/hub_validation_gate.py"
   ```
5. **Hub validation:** open **`../acm-hub-health-check/SKILL.md`** (path from step 4 JSON matches this relative target) and run **Quick** depth (user may request Standard/Deep from that skill). Do not skip this file in favor of improvised checks.
6. If user asked for **spokes**, after hub Quick check run `oc get managedclusters --no-headers | wc -l` and compare to expectation.
7. On failure: set `health_status` to `FAILED` in notes; try next candidate; delete temp kubeconfig.

### Step G -- Deliver

Return: cluster name, platform, snapshot/channel, Jenkins build URL, kubeconfig path or download command, console hint from sheet if present, and whether spokes matched.

---

### Mode 2: Provision (gated)

Default job: `CI-Jobs/ocp_deploy_and_acm_install`

### Parameter mapping (plain language to Jenkins)

| User intent | Parameters |
|-------------|--------------|
| ACM 2.17 nightly | `RHACM_SNAPSHOT_TAG=latest-2.17`, `ACM_CHANNEL=2.17` (if channel needed) |
| Azure | `CLOUD_PROVIDER=AZURE` |
| OCP 4.18 | `OCP_VERSION=4.18.x`, `OCP_RELEASE=stable-4.18` or user value |
| Defaults | Document chosen defaults in the approval summary |

### ACM_REPOSITORY default

**Always use `konflux`** (team standard as of May 2026). Do not use `production` or `acm-d` unless the user explicitly requests it. This applies to all ACM versions including older z-streams (2.15, 2.16).

### Cluster naming convention

**NEVER use the `ci-` prefix** in `OCP_CLUSTER_NAME`. The `ci-` prefix is reserved for the automated CI process. Use descriptive names like `atif-215-hub`, `atif-az-50`, `test-217-virt`, etc. Pattern: `<user>-<version/purpose>-<optional-qualifier>`.

### MCE snapshot tag mapping

When provisioning, match the MCE version to the ACM version:

| ACM version | MCE snapshot |
|-------------|-------------|
| latest-2.15 | latest-2.10 |
| latest-2.16 | latest-2.11 |
| latest-2.17 | latest-2.17 |
| latest-5.0 | latest-5.0 |

When the **jenkins** MCP is available, use **`get_job` / `get_build`** for configuration and recent builds before any trigger. If the MCP is unavailable, use REST per [references/jenkins-without-mcp.md](references/jenkins-without-mcp.md) and **`../acm-jenkins-client/references/jenkins-remote-api.md`**.

### Trigger

1. When the **jenkins** MCP is available, use `trigger_build` after approval per **`../acm-jenkins-client/SKILL.md`**. If the MCP is unavailable, use Jenkins UI or documented REST (crumb) from that skill’s references.
2. Show user **all** parameters.
3. On explicit **yes**: trigger via approved channel only.
4. Monitor build until complete: when the **jenkins** MCP is available, use MCP status and polling per **`../acm-jenkins-client/SKILL.md`**; otherwise `jenkins_api.py` poll, REST polling, or the Jenkins UI.

### After success

Download `ocp_credentials/kubeconfig` and `output.json`, then `export KUBECONFIG`, run **`scripts/hub_validation_gate.py`** (exit 0 required), then run hub checks **only** per **`../acm-hub-health-check/SKILL.md`** (Quick), then deliver URLs and build link.

---

### Mode 3: Destroy (gated)

### Resolve target

Accept: API URL, cluster display name, or `job/path #build`.

1. Search `inventory.json` / in-memory candidates for match.
2. If missing InfraID: download `output.json` from the matching build and parse defensively (see [references/output-json.md](references/output-json.md)).
3. If still unknown: ask user for **InfraID** and **PLATFORM** for `pics_cloud_destroy`.

### Map to destroy job

Default: `CI-Jobs/pics_cloud_destroy` with `PLATFORM` (lowercase aws/azure/gcp/vsphere/eks/aks/gke), `OCP_CLUSTER_NAME` = InfraID, `REGION` from source build.

For ROSA / ARO / OSD use destroy jobs under `openshift/destroy/cloud/` per [references/provisioning-pipelines.md](references/provisioning-pipelines.md).

### Trigger

Show infra id, platform, region, and job URL; require explicit approval; then trigger via the same rules as Mode 2.

---

## Related content in this repository

| Path | Use |
|------|-----|
| `../acm-hub-health-check/SKILL.md` | Hub health validation after kubeconfig is available |
| `../acm-jenkins-client/SKILL.md` | Jenkins MCP when the host exposes it; REST + `jenkins_api.py` when not |

Do not reference skills that are not present under `.claude/skills/` in this repo.

---

## Examples

**Example 1 -- Find**

- **User says:** "Find me a Running ACM 2.17 hub on VMware for a quick sanity test."
- **Actions:** Optional sheet + cache + Jenkins; rank VMware + 2.17; download kubeconfig; **`hub_validation_gate.py`** then **Quick** hub checks from `../acm-hub-health-check/SKILL.md`.
- **Result:** One recommended hub with Jenkins build URL, temp kubeconfig path, health summary, and spoke count if requested.

**Example 2 -- Provision**

- **User says:** "Provision ACM latest-2.17 on Azure eastus."
- **Actions:** List parameters; show full map; wait for explicit approval; trigger build (UI/REST/MCP per environment); monitor; download artifacts; **`hub_validation_gate.py`** then **Quick** hub checks from `../acm-hub-health-check/SKILL.md`.
- **Result:** New build URL, kubeconfig location, and hub health status after install completes.

**Example 3 -- Destroy**

- **User says:** "Destroy https://api.foo.dev09.red-chesterfield.com:6443"
- **Actions:** Locate inventory row or build; resolve InfraID (use [references/output-json.md](references/output-json.md) when needed); map platform; show summary; wait for approval; trigger `CI-Jobs/pics_cloud_destroy` with approval.
- **Result:** Destroy build queued or completed; user informed that inventory cache may be stale until next refresh.

---

## Troubleshooting

| Symptom | Cause | What to do |
|---------|-------|------------|
| Jenkins errors | VPN / token | Confirm VPN; verify `~/.jenkins/config.json`; run refresh script with `--dry-run` |
| No candidates / empty `entries` | Never refreshed or stale jobs | Run `refresh-inventory.py`; confirm success JSON on stdout; see [Inventory cache](#inventory-cache) |
| Empty sheet rows | Range too small or no Sheet access | Widen range if using Sheets; else rely on `inventory.json` |
| curl artifact 404 | Wrong path or build failed | Confirm artifacts from build JSON; path is usually `ocp_credentials/kubeconfig` |
| Gate script exits non-zero | Missing hub sibling, bad kube, oc missing | Read JSON `exit_reason` on stdout; fix clone or kube; see [references/hub-validation-gate.md](references/hub-validation-gate.md) |
| Health check fails immediately | Expired kube or wrong cluster | Retry next candidate; refresh inventory |
| destroy parameter rejected | Wrong PLATFORM or InfraID | [references/pipeline-parameters.md](references/pipeline-parameters.md) and [references/output-json.md](references/output-json.md) |
| `refresh-inventory.py` fails SSL | Corporate CA | Script disables TLS verify intentionally (same pattern as many internal Jenkins clients) |

---

## Negative triggers (scope)

Do **not** use this skill as primary for: Jenkins-only test failure triage (use **`../acm-jenkins-client/SKILL.md`**), build-tag lookup on an already-logged-in hub without environment discovery, or standalone deep hub diagnosis without find/provision/destroy context (use **`../acm-hub-health-check/SKILL.md`** alone).
