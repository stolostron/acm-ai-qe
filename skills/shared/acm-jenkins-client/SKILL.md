---
name: acm-jenkins-client
description: >-
  Interface to Jenkins CI for reading build status, test results, pipeline stages,
  console logs, downstream trees, and (with approval) triggering builds. Use when
  you need Jenkins pipeline data, logs, JUnit results, or to monitor or trigger jobs.
  Prefer the jenkins MCP in Cursor and Claude Code when configured (same MCP set in both
  places). Bundled REST docs and scripts/jenkins_api.py cover portability,
  stdlib-only scripts, and any host without the MCP.
compatibility: >-
  Requires VPN for Red Hat Jenkins and API credentials in ~/.jenkins/config.json
  (jenkins_url, jenkins_user, jenkins_token). In a typical dual setup, the jenkins MCP is
  configured and is the primary path; references/jenkins-remote-api.md and scripts/jenkins_api.py
  are the REST fallback and script parity layer (not a substitute for lack of MCP in your env).
metadata:
  author: acm-qe
  version: "1.1.1"
---

# Jenkins CI Client

**Primary path:** use the **jenkins** MCP tools below (expected when Cursor and Claude Code are onboarded with the same MCP stack). That is not a bottleneck for normal QE use.

**Also documented:** Jenkins **Remote API** and **`jenkins_api.py`** — for stdlib-only automation (e.g. inventory refresh), `curl`/CI jobs, or any context where the agent does not expose the MCP. See [references/jenkins-remote-api.md](references/jenkins-remote-api.md) and `python3 "${CLAUDE_SKILL_DIR}/scripts/jenkins_api.py" --help`.

This skill exposes **how** to call Jenkins; the calling skill decides **what** to extract and analyze.

## Prerequisites

- VPN when Jenkins is internal
- Credentials file: `~/.jenkins/config.json` (or pass `--config` to the bundled script) with `jenkins_url`, `jenkins_user`, `jenkins_token` (aliases `url`, `user`, `token` supported)
- **Jenkins MCP:** use it by default in Cursor and Claude Code when configured; for a few capabilities (rich downstream tree, packaged analyzers) the MCP is still the best interface even though REST covers most reads

## Progressive disclosure

- **REST / curl / polling / triggers:** [references/jenkins-remote-api.md](references/jenkins-remote-api.md)
- **MCP response field shapes:** [references/tool-reference.md](references/tool-reference.md)

## Bundled script (no extra pip packages)

| Command | Purpose |
|---------|---------|
| `jenkins_api.py api /job/.../api/json` | GET JSON (pretty-printed) |
| `jenkins_api.py console CI-Jobs/foo 123 --tail 500` | Last lines of console |
| `jenkins_api.py crumb` | Print crumb header for manual `curl` POST |
| `jenkins_api.py poll CI-Jobs/foo 123` | Wait until `building` is false |

Example:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/jenkins_api.py" api "/job/CI-Jobs/job/ocp_deploy_and_acm_install/lastSuccessfulBuild/api/json?tree=number,url,result"
```

## MCP Tools

### Build Information
| Tool | Purpose |
|------|---------|
| `get_build(job_name, build_number)` | Get full build details (result, parameters, duration, timestamp) |
| `get_build_status(job_name, build_number)` | Quick build result check (SUCCESS, FAILURE, UNSTABLE, ABORTED) |
| `get_build_log(job_name, build_number, start, max_lines)` | Download console log (supports pagination) |
| `get_job(job_name)` | Get job configuration and recent builds |
| `get_all_jobs(folder)` | List all jobs in a folder |

### Pipeline Analysis
| Tool | Purpose |
|------|---------|
| `get_pipeline_stages(job_name, build_number)` | Get pipeline stage breakdown with status and duration |
| `get_downstream_tree(job_name, build_number)` | Get downstream build tree (parent -> child relationships) |
| `analyze_pipeline(job_name, build_number)` | AI-assisted pipeline analysis with failure identification |

### Test Results
| Tool | Purpose |
|------|---------|
| `get_test_results(job_name, build_number)` | Get JUnit test results (pass/fail/skip counts, per-test details) |
| `analyze_test_results(job_name, build_number)` | AI-assisted test result analysis with failure categorization |

### Build Triggering
| Tool | Purpose |
|------|------|
| `trigger_build(job_name, parameters)` | Trigger a new build with parameters (use with caution) |

## Gotchas

1. **Job names include folder paths.** Use the full path: `folder/subfolder/job-name`, not just `job-name`. Same rule for `jenkins_api.py console` / `poll`.
2. **Build logs can be very large.** Use MCP pagination or `jenkins_api.py console ... --tail 500`.
3. **Pipeline stages may be nested.** `get_pipeline_stages` returns a flat list -- parent-child relationships are in the `id` and `parentId` fields. REST: try `wfapi/describe` (see remote API doc).
4. **Test results follow JUnit format.** `failedTests` array contains `name`, `className`, `errorDetails`, `errorStackTrace`. REST: `testReport/api/json` when the job publishes JUnit.
5. **VPN required** for typical Red Hat Jenkins hosts.
6. **No universal REST substitute** for `get_downstream_tree` / packaged analyzers — use MCP in your normal Cursor + Claude Code setup; REST is for scripts and edge hosts.

## Common Patterns

### Get a build's test failures (MCP)
```
get_build(job_name, build_number)          -- build metadata
get_test_results(job_name, build_number)   -- JUnit results with per-test details
```

### Get console log errors (MCP or script)
```
get_build_log(job_name, build_number, start=-500)  -- last 500 lines
```
```
python3 "${CLAUDE_SKILL_DIR}/scripts/jenkins_api.py" console CI-Jobs/your_job 42 --tail 500
```

### Trace downstream builds
```
get_downstream_tree(job_name, build_number)  -- full downstream tree (MCP preferred)
```

## Rules

- NEVER trigger builds without explicit user approval.
- If the MCP is unavailable **or** you need a headless/scripted call, use [references/jenkins-remote-api.md](references/jenkins-remote-api.md) and `jenkins_api.py` for reads and polling; for triggers without MCP, print parameters and use UI or documented POST + crumb.
