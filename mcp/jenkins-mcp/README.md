# Jenkins MCP Server

MCP server for Jenkins pipeline analysis, build monitoring, and failure investigation.

Forked from [redhat-community-ai-tools/jenkins-mcp](https://github.com/redhat-community-ai-tools/jenkins-mcp)
with upstream bug fixes and specialized ACM CI/CD tools.

## Upstream Fixes

- **Auth**: Bearer token -> HTTP Basic (username:token)
- **Build log**: JSON parse crash -> returns plain text
- **Job paths**: Flat paths -> nested folder support (`folder/sub/job` -> `job/folder/job/sub/job/job`)
- **Trigger**: Added build parameter support
- **Credentials**: Reads from `~/.jenkins/config.json` (matches existing `jenkins-run` CLI tool)

## Available Tools

### Core (7)

| Tool | Description |
|------|-------------|
| `get_all_jobs` | List all Jenkins jobs at root level with name, URL, status |
| `get_job` | Get details for a job by slash-separated path |
| `get_build` | Get build info (specific number or last build) |
| `trigger_build` | Trigger a build, optionally with parameters |
| `get_build_log` | Get console output (plain text, paginated, truncated) |
| `get_build_status` | Quick status check from a full build URL |
| `get_pipeline_stages` | Get pipeline stage names, statuses, durations via Workflow API |

### Specialized (4)

These tools wrap existing `jenkins-tools` scripts for deeper analysis.

| Tool | Description |
|------|-------------|
| `analyze_pipeline` | Deep failure analysis: root cause, failed stages, fix recommendations |
| `get_downstream_tree` | Visualize downstream job tree (ASCII, markdown, or JSON) |
| `get_test_results` | Fetch test results (summary, full, or failures only) |
| `analyze_test_results` | Test results grouped by component/squad with failure breakdown |

**Note:** Specialized tools require the `jenkins-tools` scripts directory.
Set `JENKINS_TOOLS_DIR` env var or place scripts at `~/Documents/work/ai/tools/jenkins-tools`.

## Prerequisites

- Python 3.10+
- Red Hat VPN (for internal Jenkins)

## Installation

```bash
pip install -r requirements.txt
```

Or install dependencies directly:

```bash
pip install "mcp[cli]" httpx urllib3 python-dotenv
```

## Credentials

Create `~/.jenkins/config.json`:

```json
{
  "jenkins_url": "https://jenkins-csb-rhacm-tests.dno.corp.redhat.com",
  "jenkins_user": "<your-username>",
  "jenkins_token": "<your-api-token>"
}
```

To get your API token:
1. Log into Jenkins
2. Click your username (top right) -> Configure
3. Under "API Token", click "Add new Token"
4. Copy the generated token

Alternatively, set environment variables: `JENKINS_URL`, `JENKINS_USER`, `JENKINS_TOKEN`.

## Usage with Claude Code / Cursor

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "python",
      "args": ["jenkins_mcp_server.py"],
      "cwd": "/path/to/jenkins-mcp",
      "timeout": 60
    }
  }
}
```

## Examples

```
# List all jobs
get_all_jobs()

# Get a specific job
get_job("qe-acm-automation-poc/clc-e2e-pipeline")

# Get the last build
get_build("qe-acm-automation-poc/clc-e2e-pipeline")

# Get build log (last 500 lines)
get_build_log("qe-acm-automation-poc/clc-e2e-pipeline", build_number=3913)

# Deep failure analysis
analyze_pipeline("https://jenkins.example.com/job/CI/job/main/42/")

# Downstream job tree
get_downstream_tree("https://jenkins.example.com/job/CI/job/main/42/")

# Test results summary
get_test_results("qe-acm-automation-poc/clc-e2e-pipeline", mode="failures")
```
