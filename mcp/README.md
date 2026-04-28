# MCP Servers -- Setup Guide

## What are MCP servers?

MCP (Model Context Protocol) servers are background processes that give AI agents
(Claude Code, Cursor) access to external tools. When an AI agent analyzes a pipeline
failure, it uses MCP servers to search GitHub for source code, look up JIRA bugs,
and query component dependency graphs -- without needing API keys embedded in prompts.

## Prerequisites

- **Python 3.10+** (required) -- `brew install python3` (macOS) or `sudo dnf install python3` (Fedora/RHEL)
- **`gh` CLI** (required for acm-ui) -- `brew install gh` (macOS)
- **`uvx`** (optional, needed for polarion + neo4j) -- `pip install uv`
- **Podman** (optional, needed for neo4j-rhacm) -- `brew install podman` (macOS)
- **Node.js 18+** (needed for acm-search, acm-kubectl, playwright) -- `brew install node` (macOS) or `sudo dnf install nodejs` (Fedora/RHEL)
- **`mcp-remote`** (needed for acm-search) -- `npm install -g mcp-remote` (stdio-to-SSE bridge)
- **`oc` CLI** (needed for acm-search, acm-kubectl) -- [OpenShift client downloads](https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/)

## Which servers do I need?

| Server | Used by | What it does | Tools | Source |
|--------|---------|--------------|-------|--------|
| **acm-ui** | Hub Health, Z-Stream, Test Case Gen | Searches ACM Console & Fleet Virt source code on GitHub | 20 | This repo |
| **jira** | Z-Stream, Test Case Gen | Searches/creates JIRA issues for bug correlation | 25 | [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server) |
| **jenkins** | Z-Stream | Jenkins pipeline analysis, build monitoring, failure investigation | 11 | [redhat-community-ai-tools/jenkins-mcp](https://github.com/redhat-community-ai-tools/jenkins-mcp) |
| **polarion** | Z-Stream, Test Case Gen | Reads/writes Polarion test cases (RHACM4K project) | 25 | This repo (wrapper around [polarion-mcp](https://pypi.org/project/polarion-mcp/)) |
| **neo4j-rhacm** | Hub Health, Z-Stream, Test Case Gen | Queries RHACM component dependency graph (370 components, 541 relationships across 7 subsystems) | 2 | [mcp-neo4j-cypher](https://pypi.org/project/mcp-neo4j-cypher/) (PyPI) + [stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph) (data) |
| **acm-search** | Hub Health, Test Case Gen | Fleet-wide resource queries across all managed clusters via search-postgres (spoke-side visibility) | 5 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) |
| **acm-kubectl** | Test Case Gen | Multicluster kubectl -- list/run commands on hub and spoke clusters | 3 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) |
| **playwright** | Test Case Gen | Browser automation for live UI validation (navigate, click, screenshot) | 24 | [@playwright/mcp](https://www.npmjs.com/package/@anthropic-ai/playwright-mcp) (npm) |

### What works without optional servers

| Server | If unavailable | Z-Stream impact | Hub Health impact | Test Case Gen impact |
|--------|---------------|-----------------|-------------------|---------------------|
| neo4j-rhacm | Dependency analysis disabled | Component KG queries skipped | Dependency chain correlation skipped | Architecture impact analysis skipped |
| acm-search | Spoke-side visibility lost | N/A | Spoke pod health checks skipped; hub-only diagnosis | Live validation cluster queries unavailable |
| acm-kubectl | Spoke kubectl disabled | N/A | N/A | Live validation spoke commands unavailable |
| playwright | Browser automation disabled | N/A | N/A | UI discovery browser verification and live validation skipped |
| jira | Bug correlation disabled | No JIRA correlation; classification still works | N/A | Feature investigation limited to PR + code |
| polarion | Test case access disabled | PR-6b expected-behavior check skipped | N/A | No existing coverage lookup; test cases still generated |

The setup script handles this automatically -- select your app and it installs only the servers that app needs.

## Quick Setup

From the repository root, run:

```bash
bash mcp/setup.sh
```

The script:
1. Checks prerequisites (Python, `gh` CLI, `uvx`)
2. Clones external MCP servers (jira, jenkins) into `mcp/.external/` (gitignored)
3. Creates Python virtual environments for each server
4. Installs dependencies into each venv
5. Prompts for credentials (API tokens, emails) -- press Enter to skip any
6. Generates `.mcp.json` for the selected app(s)

Re-running the script updates the clones and re-checks credentials.

## Architecture

This repo contains only the MCP servers we created. External servers are cloned
at setup time from their upstream repositories:

```
mcp/
|-- setup.sh                        <-- Run this to set up everything
|-- README.md                       <-- This file
|
|-- acm-ui-mcp-server/              <-- Our code: ACM Console source search (20 tools)
|   |-- acm_ui_mcp_server/          <-- Python package
|   |-- pyproject.toml
|   \-- docs/
|
|-- polarion/                        <-- Our code: Polarion wrapper (25 tools)
|   |-- polarion-mcp-wrapper.py     <-- SSL patch + 11 enhanced tools
|   \-- README.md
|
|-- jenkins-acm-tools.py            <-- Our code: 4 ACM-specific Jenkins analysis tools
|                                       (wraps upstream jenkins-mcp + adds analyze_pipeline,
|                                        get_downstream_tree, get_test_results, analyze_test_results)
|
|-- verify.py                        <-- Standalone health checker (run anytime)
|
\-- .external/                       <-- Cloned at setup time (gitignored)
    |-- jira-mcp-server/             <-- From stolostron/jira-mcp-server
    |-- jenkins-mcp/                 <-- From redhat-community-ai-tools/jenkins-mcp
    \-- acm-mcp-server/              <-- From stolostron/acm-mcp-server (acm-search + acm-kubectl)
```

### External MCP Sources

External MCPs are cloned from forks with pending upstream PRs. Once merged,
`setup.sh` will be updated to point to upstream `main`.

| MCP | Fork (current) | Upstream PR |
|-----|----------------|-------------|
| JIRA | [atifshafi/jira-mcp-server@feat/redhat-fields](https://github.com/atifshafi/jira-mcp-server/tree/feat/redhat-fields) | [stolostron/jira-mcp-server#24](https://github.com/stolostron/jira-mcp-server/pull/24) |
| Jenkins | [atifshafi/jenkins-mcp@fix/auth-logs-paths](https://github.com/atifshafi/jenkins-mcp/tree/fix/auth-logs-paths) | [redhat-community-ai-tools/jenkins-mcp#13](https://github.com/redhat-community-ai-tools/jenkins-mcp/pull/13) |

### Credential storage

| Server | Credential file | Gitignored? |
|--------|----------------|-------------|
| acm-ui | `gh auth` (system) | N/A |
| jira | `mcp/.external/jira-mcp-server/.env` | Yes (entire `.external/` dir) |
| jenkins | `~/.jenkins/config.json` | N/A (home dir) |
| polarion | `mcp/polarion/.env` | Yes (`*.env`) |
| neo4j-rhacm | None (local container) | N/A |
| acm-search | None (reads from cluster secret) | N/A |
| acm-kubectl | None (uses `oc login`) | N/A |
| playwright | None (browser automation) | N/A |

## Verifying Setup

Run the standalone health checker anytime:

```bash
python3 mcp/verify.py              # All apps, prerequisites + artifacts
python3 mcp/verify.py --app 2      # Z-Stream only
python3 mcp/verify.py --live       # Include connectivity checks
python3 mcp/verify.py --json       # Machine-readable output
```

Or check MCP registration in Claude Code:

```bash
claude mcp list
```

To test individual servers, ask the AI agent:
- "List the MCP repos" -- tests acm-ui
- "Search JIRA for project=ACM" -- tests jira
- "Get all Jenkins jobs" -- tests jenkins
- "Query the knowledge graph: MATCH (n) RETURN count(n)" -- tests neo4j-rhacm
- "Get search database stats" -- tests acm-search

## After a reboot

```bash
# If you set up neo4j-rhacm, restart the containers:
podman machine start && podman start neo4j-rhacm
```

The other servers start automatically when the AI agent launches.
