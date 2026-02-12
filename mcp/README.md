# MCP Servers — Setup Guide

## What are MCP servers?

MCP (Model Context Protocol) servers are background processes that give AI agents
(Claude Code, Cursor) access to external tools. When an AI agent analyzes a pipeline
failure, it uses MCP servers to search GitHub for source code, look up JIRA bugs,
and query component dependency graphs — without needing API keys embedded in prompts.

Without MCP servers configured, the z-stream-analysis AI agent cannot investigate
failures beyond what's in the gathered data files.

## Which servers do I need?

| Server | Required? | What it does | Needs |
|--------|-----------|--------------|-------|
| **acm-ui** | Yes | Searches ACM Console & Fleet Virt source code on GitHub | `gh` CLI authenticated |
| **jira** | Yes | Searches/creates JIRA issues for bug correlation | JIRA Personal Access Token |
| **neo4j-rhacm** | No | Queries RHACM component dependency graph (291 components) | Podman + Node.js |
| **polarion** | No | Reads Polarion test cases (RHACM4K project) | Red Hat VPN + Polarion JWT token |

## Quick Setup

From the repository root, run:

```bash
bash mcp/setup.sh
```

The script will:
1. Check prerequisites (Python, `gh` CLI)
2. Install the ACM UI MCP server
3. Clone and install the JIRA MCP server, prompt for your JIRA token
4. Optionally set up the Neo4j knowledge graph (Podman containers)
5. Optionally set up the Polarion MCP server
6. Update `apps/z-stream-analysis/.mcp.json` with correct paths

After the script finishes, restart Claude Code or Cursor to pick up the new config.

## Manual Setup

If you prefer to set things up individually, or if the setup script doesn't cover
your environment, see the README in each server's directory:

| Server | Setup instructions |
|--------|--------------------|
| acm-ui | [mcp/acm-ui/README.md](acm-ui/README.md) |
| jira | [mcp/jira/README.md](jira/README.md) |
| neo4j-rhacm | [mcp/neo4j-rhacm/README.md](neo4j-rhacm/README.md) |
| polarion | [mcp/polarion/README.md](polarion/README.md) |

## Verifying Setup

After restarting your MCP client:

```bash
# Claude Code
claude mcp list
# Should show: acm-ui (Connected), jira (Connected), etc.
```

Or ask the AI agent directly:
- "List the MCP repos" → tests acm-ui
- "Search JIRA for project=ACM" → tests jira
- "Query the knowledge graph: MATCH (n) RETURN count(n)" → tests neo4j-rhacm

## How it works

The z-stream analysis app has a `.mcp.json` file that tells Claude Code which
MCP servers to start:

```
apps/z-stream-analysis/.mcp.json
  → acm-ui:      ../../mcp/acm-ui           (Python package, in this repo)
  → jira:         ../../mcp/jira/jira-mcp-server  (cloned by setup.sh, gitignored)
  → neo4j-rhacm:  npx mcp-remote localhost:8000   (Podman container, if set up)
  → polarion:     uvx polarion-mcp wrapper         (PyPI package + wrapper, if set up)
```

Each server runs as a subprocess that communicates with the AI agent via JSON-RPC
over stdin/stdout (or SSE for neo4j-rhacm).

## After a reboot

```bash
# If you set up neo4j-rhacm, restart the containers:
podman machine start && podman start neo4j-rhacm neo4j-mcp
```

The other servers (acm-ui, jira, polarion) start automatically when the AI agent
launches — no manual restart needed.

---

## Server Details

### acm-ui (`mcp/acm-ui/`)

Source code included in this repo. 20 tools for searching 6 GitHub repositories:
stolostron/console, kubevirt-ui/kubevirt-plugin, and 4 QE automation repos.

Supports independent ACM (2.11–2.17) and CNV (4.14–4.22) version switching.
Can auto-detect CNV version from a connected OpenShift cluster.

**Detailed docs:** [mcp/acm-ui/README.md](acm-ui/README.md)

### jira (`mcp/jira/`)

External repo ([stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server)),
cloned by setup.sh into `mcp/jira/jira-mcp-server/` (gitignored). 24 tools for JIRA
issue search, creation, team management, and component aliases.

**Detailed docs:** [mcp/jira/README.md](jira/README.md)

### neo4j-rhacm (`mcp/neo4j-rhacm/`)

Container-based. Two Podman containers run a Neo4j database with 291 RHACM components
and an MCP SSE server. Based on
[stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph/tree/main/acm/agentic-docs/dependency-analysis),
forked and extended with additional queries and MCP integration docs.

3 tools: `read_neo4j_cypher`, `write_neo4j_cypher`, `get_neo4j_schema`

**Setup script:** `bash mcp/neo4j-rhacm/setup.sh`
**Detailed docs:** [mcp/neo4j-rhacm/README.md](neo4j-rhacm/README.md)

### polarion (`mcp/polarion/`)

Custom wrapper (`polarion-mcp-wrapper.py`) around the `polarion-mcp` PyPI package.
Patches SSL for Red Hat internal Polarion and adds 3 enhanced tools for test case
content retrieval. 17 tools total.

**Detailed docs:** [mcp/polarion/README.md](polarion/README.md)

---

## Directory Structure

```
mcp/
├── README.md                     ← This file (setup guide)
├── setup.sh                      ← Run this to set up everything
├── acm-ui/                       ← ACM Console source code search (20 tools)
│   ├── README.md
│   ├── pyproject.toml
│   ├── acm_ui_mcp_server/       ← Python package (4 modules, ~1,670 lines)
│   └── docs/                     ← Full reference documentation
├── jira/                         ← JIRA integration (24 tools)
│   ├── README.md
│   └── jira-mcp-server/         ← Cloned by setup.sh (gitignored)
├── neo4j-rhacm/                  ← RHACM dependency graph (3 tools)
│   ├── README.md
│   ├── setup.sh                  ← Container setup script
│   ├── QUICK-REFERENCE.md
│   ├── sample_queries.cypher     ← 30+ Cypher queries
│   ├── mcp_sample_questions.md   ← 100+ example questions
│   └── ...                       ← Additional reference docs
└── polarion/                     ← Polarion test cases (17 tools)
    ├── README.md
    └── polarion-mcp-wrapper.py   ← SSL patch + 3 enhanced tools
```
