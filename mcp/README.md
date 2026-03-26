# MCP Servers -- Setup Guide

## What are MCP servers?

MCP (Model Context Protocol) servers are background processes that give AI agents
(Claude Code, Cursor) access to external tools. When an AI agent analyzes a pipeline
failure, it uses MCP servers to search GitHub for source code, look up JIRA bugs,
and query component dependency graphs -- without needing API keys embedded in prompts.

Without MCP servers configured, the z-stream-analysis AI agent cannot investigate
failures beyond what's in the gathered data files.

## Prerequisites

- **Python 3.10+** (required) -- `brew install python3` (macOS) or `sudo dnf install python3` (Fedora/RHEL)
- **`gh` CLI** (optional, needed for acm-ui) -- `brew install gh` (macOS) or `sudo dnf install gh` (Fedora/RHEL)
- **`uvx`** (optional, needed for polarion + neo4j) -- `pip install uv`
- **Podman** (optional, needed for neo4j-rhacm) -- `brew install podman` (macOS)

## Which servers do I need?

| Server | Required? | What it does | Tools | Credentials |
|--------|-----------|--------------|-------|-------------|
| **acm-ui** | Yes | Searches ACM Console & Fleet Virt source code on GitHub | 20 | `gh auth login` |
| **jira** | Yes | Searches/creates JIRA issues for bug correlation | 25 | Jira Cloud API token + email |
| **jenkins** | No | Jenkins pipeline analysis, build monitoring, failure investigation | 11 | Jenkins API token + VPN |
| **polarion** | No | Reads Polarion test cases (RHACM4K project) | 17+ | Red Hat VPN + Polarion JWT token |
| **neo4j-rhacm** | No | Queries RHACM component dependency graph (291 components) | 3 | Podman containers |

## Quick Setup

From the repository root, run:

```bash
bash mcp/setup.sh
```

The script:
1. Checks prerequisites (Python 3.10+, optionally `gh` CLI)
2. Creates a Python virtual environment for each server (in `mcp/<server>/.venv/`)
3. Installs dependencies into each venv
4. Prompts for credentials (API tokens, emails) -- press Enter to skip any
5. Writes credential `.env` files (gitignored, never committed)
6. Generates `apps/z-stream-analysis/.mcp.json` pointing to each venv

Credentials can be skipped during setup and filled in later by editing the `.env`
files. Re-running the script will re-prompt for any missing credentials.

After the script finishes, restart Claude Code or Cursor to pick up the new config.

## Manual Setup

If you prefer to set things up individually:

| Server | Setup instructions |
|--------|--------------------|
| acm-ui | [mcp/acm-ui-mcp-server/README.md](acm-ui-mcp-server/README.md) |
| jira | [mcp/jira-mcp-server/README.md](jira-mcp-server/README.md) |
| jenkins | [mcp/jenkins-mcp/README.md](jenkins-mcp/README.md) |
| neo4j-rhacm | [mcp/neo4j-rhacm/README.md](neo4j-rhacm/README.md) |
| polarion | [mcp/polarion/README.md](polarion/README.md) |

### Manual JIRA Setup

1. Create a venv and install:
   ```bash
   python3 -m venv mcp/jira-mcp-server/.venv
   mcp/jira-mcp-server/.venv/bin/pip install -e mcp/jira-mcp-server/
   ```
2. Copy the example env: `cp mcp/jira-mcp-server/.env.example mcp/jira-mcp-server/.env`
3. Edit `mcp/jira-mcp-server/.env` with your credentials:
   ```
   JIRA_SERVER_URL=https://your-company.atlassian.net
   JIRA_ACCESS_TOKEN=<your-api-token>
   JIRA_EMAIL=<your-email>@company.com
   ```
4. Get an API token at https://id.atlassian.com/manage-profile/security/api-tokens

The `.env` file uses `override=True` so it always takes precedence over any
pre-existing shell environment variables (e.g., from `jira-cli`).

### Manual Polarion Setup

1. Copy the example env: `cp mcp/polarion/.env.example mcp/polarion/.env`
2. Edit `mcp/polarion/.env` with your JWT token:
   ```
   POLARION_PAT=<your-jwt-token>
   ```
3. Get a token at: Polarion > My Account > Personal Access Tokens (requires VPN)

## Verifying Setup

After restarting your MCP client:

```bash
# Claude Code
claude mcp list
# Should show: acm-ui (Connected), jira (Connected), etc.
```

Or ask the AI agent directly:
- "List the MCP repos" -- tests acm-ui
- "Search JIRA for project=ACM" -- tests jira
- "Get all Jenkins jobs" -- tests jenkins
- "Query the knowledge graph: MATCH (n) RETURN count(n)" -- tests neo4j-rhacm

## How it works

The z-stream analysis app has a `.mcp.json` file that tells Claude Code which
MCP servers to start. Each server uses a local `.venv/` for isolation:

```
apps/z-stream-analysis/.mcp.json
  -> acm-ui:      .venv/bin/python -m acm_ui_mcp_server.main   (cwd: mcp/acm-ui-mcp-server)
  -> jira:         .venv/bin/python -m jira_mcp_server.main      (cwd: mcp/jira-mcp-server)
  -> jenkins:      .venv/bin/python jenkins_mcp_server.py        (cwd: mcp/jenkins-mcp)
  -> polarion:     uvx --with polarion-mcp python wrapper.py     (cwd: mcp/polarion)
  -> neo4j-rhacm:  uvx mcp-neo4j-cypher bolt://localhost:7687
```

All paths in `.mcp.json` are relative -- no machine-specific paths. Each server
runs as a subprocess communicating via JSON-RPC over stdin/stdout.

### Credential storage

| Server | Credential file | Gitignored? |
|--------|----------------|-------------|
| acm-ui | `gh auth` (system) | N/A |
| jira | `mcp/jira-mcp-server/.env` | Yes (`*.env`) |
| jenkins | `~/.jenkins/config.json` | N/A (home dir) |
| polarion | `mcp/polarion/.env` | Yes (`*.env`) |
| neo4j-rhacm | None (local container) | N/A |

## After a reboot

```bash
# If you set up neo4j-rhacm, restart the containers:
podman machine start && podman start neo4j-rhacm neo4j-mcp
```

The other servers (acm-ui, jira, jenkins, polarion) start automatically when the
AI agent launches -- no manual restart needed.

---

## Server Details

### acm-ui (`mcp/acm-ui-mcp-server/`)

20 tools for searching 6 GitHub repositories:
stolostron/console, kubevirt-ui/kubevirt-plugin, and 4 QE automation repos.

Supports independent ACM (2.11-2.17) and CNV (4.14-4.22) version switching.
Can auto-detect CNV version from a connected OpenShift cluster.

**Detailed docs:** [mcp/acm-ui-mcp-server/README.md](acm-ui-mcp-server/README.md)

### jira (`mcp/jira-mcp-server/`)

Based on [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server).

**Jira Cloud:** Uses basic auth (email + API token). Custom field IDs and work type
IDs are configured for Jira Cloud. User references require `accountId` (use
`search_users` to resolve names to IDs).

**Setup:** Run `bash mcp/setup.sh` or manually create `mcp/jira-mcp-server/.env`
from the `.env.example` template.

25 tools for JIRA issue search, creation, team management, component aliases,
watcher management, field clearing, and user search.

**Detailed docs:** [mcp/jira-mcp-server/README.md](jira-mcp-server/README.md)

### jenkins (`mcp/jenkins-mcp/`)

Forked from [redhat-community-ai-tools/jenkins-mcp](https://github.com/redhat-community-ai-tools/jenkins-mcp)
with upstream bug fixes (auth, log parsing, nested paths, trigger params) and
specialized ACM CI/CD analysis tools.

**Core tools (7):** `get_all_jobs`, `get_job`, `get_build`, `trigger_build`,
`get_build_log`, `get_build_status`, `get_pipeline_stages`

**Specialized tools (4):** `analyze_pipeline`, `get_downstream_tree`,
`get_test_results`, `analyze_test_results` (wrap existing `jenkins-tools` scripts)

**Credentials:** `~/.jenkins/config.json` with `jenkins_url`, `jenkins_user`,
`jenkins_token`. Requires Red Hat VPN for internal Jenkins.

**Detailed docs:** [mcp/jenkins-mcp/README.md](jenkins-mcp/README.md)

### neo4j-rhacm (`mcp/neo4j-rhacm/`)

Container-based. Two Podman containers run a Neo4j database with 291 RHACM components
and an MCP SSE server. Based on
[stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph/tree/main/acm/agentic-docs/dependency-analysis).

3 tools: `read_neo4j_cypher`, `write_neo4j_cypher`, `get_neo4j_schema`

**Detailed docs:** [mcp/neo4j-rhacm/README.md](neo4j-rhacm/README.md)

### polarion (`mcp/polarion/`)

Custom wrapper (`polarion-mcp-wrapper.py`) around the `polarion-mcp` PyPI package.
Patches SSL for Red Hat internal Polarion and adds enhanced tools for test case
content retrieval. 17+ tools total.

**Setup:** Run `bash mcp/setup.sh` or manually create `mcp/polarion/.env` with your
Polarion Personal Access Token:
```
POLARION_PAT=<your-polarion-pat>
```

**Detailed docs:** [mcp/polarion/README.md](polarion/README.md)

---

## Directory Structure

```
mcp/
+-- README.md                        <-- This file (setup guide)
+-- setup.sh                         <-- Run this to set up everything
+-- acm-ui-mcp-server/               <-- ACM Console source code search (20 tools)
|   +-- README.md
|   +-- pyproject.toml
|   +-- acm_ui_mcp_server/           <-- Python package (4 modules)
|   \-- docs/                        <-- Full reference documentation
+-- jira-mcp-server/                 <-- JIRA integration (25 tools)
|   +-- README.md
|   +-- pyproject.toml
|   +-- .env.example                 <-- Template for credentials
|   +-- jira_mcp_server/             <-- Python package (4 modules)
|   +-- tests/                       <-- Unit tests
|   +-- doc/                         <-- Feature documentation
|   \-- examples/                    <-- Usage examples
+-- jenkins-mcp/                     <-- Jenkins CI/CD analysis (11 tools)
|   +-- README.md
|   +-- jenkins_mcp_server.py        <-- Single-file FastMCP server
|   \-- requirements.txt             <-- Python dependencies
+-- neo4j-rhacm/                     <-- RHACM dependency graph (3 tools)
|   +-- README.md
|   +-- QUICK-REFERENCE.md
|   +-- sample_queries.cypher        <-- 30+ Cypher queries
|   \-- mcp_sample_questions.md      <-- 100+ example questions
\-- polarion/                        <-- Polarion test cases (17+ tools)
    +-- README.md
    \-- polarion-mcp-wrapper.py      <-- SSL patch + enhanced tools
```
