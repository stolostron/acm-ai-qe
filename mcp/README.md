# MCP Servers -- Setup Guide

## What are MCP servers?

MCP (Model Context Protocol) servers are background processes that give AI agents
(Claude Code, Cursor) access to external tools. When an AI agent analyzes a pipeline
failure, it uses MCP servers to search GitHub for source code, look up JIRA bugs,
and query component dependency graphs -- without needing API keys embedded in prompts.

Without MCP servers configured, the z-stream-analysis AI agent cannot investigate
failures beyond what's in the gathered data files.

## Which servers do I need?

| Server | Required? | What it does | Tools | Needs |
|--------|-----------|--------------|-------|-------|
| **acm-ui** | Yes | Searches ACM Console & Fleet Virt source code on GitHub | 20 | `gh` CLI authenticated |
| **jira** | Yes | Searches/creates JIRA issues for bug correlation | 25 | Jira Cloud API token + email |
| **neo4j-rhacm** | No | Queries RHACM component dependency graph (291 components) | 3 | Podman + Node.js |
| **polarion** | No | Reads Polarion test cases (RHACM4K project) | 17+ | Red Hat VPN + Polarion JWT token |

## Quick Setup

From the repository root, run:

```bash
bash mcp/setup.sh
```

The script will:
1. Check prerequisites (Python, `gh` CLI)
2. Install ACM UI MCP server dependencies
3. Install JIRA MCP server dependencies, prompt for your credentials
4. Optionally set up the Neo4j knowledge graph (Podman containers)
5. Generate `apps/z-stream-analysis/.mcp.json` with correct relative paths

After the script finishes, restart Claude Code or Cursor to pick up the new config.

## Manual Setup

If you prefer to set things up individually:

| Server | Setup instructions |
|--------|--------------------|
| acm-ui | [mcp/acm-ui-mcp-server/README.md](acm-ui-mcp-server/README.md) |
| jira | [mcp/jira-mcp-server/README.md](jira-mcp-server/README.md) |
| neo4j-rhacm | [mcp/neo4j-rhacm/README.md](neo4j-rhacm/README.md) |
| polarion | [mcp/polarion/README.md](polarion/README.md) |

### Manual JIRA Setup

1. Install dependencies: `pip install -e mcp/jira-mcp-server/`
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
- "Query the knowledge graph: MATCH (n) RETURN count(n)" -- tests neo4j-rhacm

## How it works

The z-stream analysis app has a `.mcp.json` file that tells Claude Code which
MCP servers to start. All paths are relative to the app directory:

```
apps/z-stream-analysis/.mcp.json
  -> acm-ui:      ../../mcp/acm-ui-mcp-server     (Python package)
  -> jira:         ../../mcp/jira-mcp-server        (Python package)
  -> neo4j-rhacm:  uvx mcp-neo4j-cypher             (bolt://localhost:7687)
```

Each server runs as a subprocess that communicates with the AI agent via JSON-RPC
over stdin/stdout.

## After a reboot

```bash
# If you set up neo4j-rhacm, restart the containers:
podman machine start && podman start neo4j-rhacm neo4j-mcp
```

The other servers (acm-ui, jira, polarion) start automatically when the AI agent
launches -- no manual restart needed.

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
+-- neo4j-rhacm/                     <-- RHACM dependency graph (3 tools)
|   +-- README.md
|   +-- QUICK-REFERENCE.md
|   +-- sample_queries.cypher        <-- 30+ Cypher queries
|   \-- mcp_sample_questions.md      <-- 100+ example questions
\-- polarion/                        <-- Polarion test cases (17+ tools)
    +-- README.md
    \-- polarion-mcp-wrapper.py      <-- SSL patch + enhanced tools
```
