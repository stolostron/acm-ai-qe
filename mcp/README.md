# MCP Servers -- Setup Guide

> **MIRROR NOTICE:** This directory is a **git-tracked mirror** of the canonical
> MCP source code at `ai/tools/mcp/`. All development and modifications happen
> in the canonical location. This mirror is synced periodically for version
> tracking in the stolostron/ai-test-gen repository.
>
> **Canonical location:** `/Users/ashafi/Documents/work/ai/tools/mcp/`
> **Sync script:** `ai/tools/mcp/sync-to-git.sh`
>
> **NEVER** run `pip install -e .` from this directory. Use the canonical path.

---

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
| **jira** | Yes | Searches/creates JIRA issues for bug correlation | 27 | JIRA Personal Access Token |
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
3. Install JIRA MCP server dependencies, prompt for your JIRA token
4. Optionally set up the Neo4j knowledge graph (Podman containers)
5. Update `apps/z-stream-analysis/.mcp.json` with correct paths

After the script finishes, restart Claude Code or Cursor to pick up the new config.

## Manual Setup

If you prefer to set things up individually, or if the setup script doesn't cover
your environment, see the README in each server's directory:

| Server | Setup instructions |
|--------|--------------------|
| acm-ui | [mcp/acm-ui-mcp-server/README.md](acm-ui-mcp-server/README.md) |
| jira | [mcp/jira-mcp-server/README.md](jira-mcp-server/README.md) |
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
- "List the MCP repos" -- tests acm-ui
- "Search JIRA for project=ACM" -- tests jira
- "Query the knowledge graph: MATCH (n) RETURN count(n)" -- tests neo4j-rhacm

## How it works

The z-stream analysis app has a `.mcp.json` file that tells Claude Code which
MCP servers to start:

```
apps/z-stream-analysis/.mcp.json
  -> acm-ui:      ../../mcp/acm-ui-mcp-server     (Python package, in this repo)
  -> jira:         ../../mcp/jira-mcp-server        (Python package, in this repo)
  -> neo4j-rhacm:  npx mcp-remote localhost:8000    (Podman container, if set up)
  -> polarion:     uvx polarion-mcp wrapper          (PyPI package + wrapper, if set up)
```

Each server runs as a subprocess that communicates with the AI agent via JSON-RPC
over stdin/stdout (or SSE for neo4j-rhacm).

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

Based on [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server),
with local modifications for sprint management and field coverage.

27 tools for JIRA issue search, creation, team management, component aliases,
sprint assignment, and user search.

**Local modifications (not in upstream):**
- Sprint management: `list_boards`, `list_sprints`, `assign_sprint`
- Fields: qa_contact, epic_link, severity, affects_versions, acceptance_criteria, reviewers
- Read: issue_links, attachments, sprint info in issue responses
- Bug fixes: story_points=0 and original_estimate="" handling

**Detailed docs:** [mcp/jira-mcp-server/README.md](jira-mcp-server/README.md)

### neo4j-rhacm (`mcp/neo4j-rhacm/`)

Container-based. Two Podman containers run a Neo4j database with 291 RHACM components
and an MCP SSE server. Based on
[stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph/tree/main/acm/agentic-docs/dependency-analysis),
forked and extended with additional queries and MCP integration docs.

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
+-- README.md                        <-- This file (setup guide + mirror docs)
+-- setup.sh                         <-- Run this to set up everything
+-- acm-ui-mcp-server/               <-- ACM Console source code search (20 tools)
|   +-- README.md
|   +-- pyproject.toml
|   +-- acm_ui_mcp_server/           <-- Python package (4 modules)
|   \-- docs/                        <-- Full reference documentation
+-- jira-mcp-server/                 <-- JIRA integration (27 tools)
|   +-- README.md
|   +-- pyproject.toml
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

---

## Mirror Sync Process

This directory mirrors `ai/tools/mcp/` (the canonical development location).
To update this mirror after making changes to MCP code:

```bash
# From the canonical location:
bash ai/tools/mcp/sync-to-git.sh
```

The sync script uses rsync to copy code while excluding secrets (.env), build
artifacts (__pycache__), and nested git directories (.git/).
