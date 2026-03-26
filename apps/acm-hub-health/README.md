# ACM Hub Health Agent

AI-powered diagnostic agent for Red Hat Advanced Cluster Management (ACM) hub clusters.
Uses Claude Code to systematically investigate hub health, diagnose issues, and provide
actionable findings -- all through natural language.

The agent maintains a self-healing knowledge base: when it encounters components or
behaviors not covered by its reference knowledge, it investigates using official ACM
documentation and source code, learns, and records findings for future runs.

## Prerequisites

- **`oc` CLI** -- logged into your ACM hub cluster
- **Claude Code CLI** -- [install guide](https://docs.anthropic.com/en/docs/claude-code/getting-started)
- **Python 3.10+** -- for the MCP server venv
- **GitHub CLI (`gh`)** -- `brew install gh` (macOS) or `sudo dnf install gh` (RHEL/Fedora), then `gh auth login`

## Setup

```bash
# 1. Set up MCP servers (from repo root)
#    Select option 1 (ACM Hub Health Agent) when prompted
bash mcp/setup.sh

# 2. Clone the official ACM documentation (optional, improves self-healing)
cd apps/acm-hub-health
git clone --depth 1 https://github.com/stolostron/rhacm-docs.git docs/rhacm-docs

# 3. Log into your hub
oc login https://api.my-hub.example.com:6443 -u admin -p ...

# 4. Start the agent
claude
```

## Usage

```
# Quick pulse check (~30 seconds)
/sanity

# Standard health check (~2-3 minutes)
/health-check

# Deep audit (~5-10 minutes)
Do a thorough deep dive of my hub

# Targeted investigation
Why are my managed clusters showing Unknown?
Check if search is working properly
Investigate observability

# Proactive knowledge refresh (after ACM upgrade)
/learn
/learn observability
```

## How It Works

### Diagnostic Pipeline

1. **Discover** -- Inventories what's deployed on your specific hub
2. **Learn** -- Consults reference knowledge + previous discoveries
3. **Check** -- Systematically verifies health of each component
4. **Correlate** -- Cross-references findings to find root causes
5. **Deep Investigate** -- Digs into specific issues

### Self-Healing Knowledge

When the agent finds something not covered by its knowledge base:
1. Collects more evidence from the live cluster
2. Searches official ACM documentation (`docs/rhacm-docs/`)
3. Searches ACM Console source code via the `acm-ui` MCP server
4. Synthesizes an understanding and writes it to `knowledge/learned/`
5. Future runs read these discoveries alongside the static knowledge

All cluster operations are **read-only**. The agent never modifies your cluster.

## Updating Knowledge After ACM Upgrades

After upgrading ACM, run `/learn` to let the agent discover what changed:
```
oc login <upgraded-hub> ...
claude
/learn
```
The agent will compare the cluster against its knowledge, investigate any
differences, and update `knowledge/learned/` with the new information.

## Directory Structure

```
acm-hub-health/
├── CLAUDE.md                           # Agent methodology and instructions
├── README.md                           # This file
├── .mcp.json                           # MCP server configuration (acm-ui)
├── .gitignore                          # Ignores docs/rhacm-docs/
├── docs/
│   ├── 00-OVERVIEW.md                  # Architecture, components, design decisions
│   ├── 01-DEPTH-ROUTER.md             # Depth routing system
│   ├── 02-DIAGNOSTIC-PIPELINE.md      # 5-phase pipeline details
│   ├── 03-KNOWLEDGE-SYSTEM.md         # Knowledge layers and self-healing
│   ├── 04-MCP-AND-EXTERNAL-SOURCES.md # MCP integration and docs
│   ├── 05-OUTPUT-AND-REPORTING.md     # Output format and verdicts
│   ├── 06-SLASH-COMMANDS.md           # Command reference
│   └── rhacm-docs/                     # Official ACM docs clone (git ignored)
├── knowledge/
│   ├── component-registry.md           # Static: ACM component reference
│   ├── failure-patterns.md             # Static: known failure patterns
│   ├── diagnostic-playbooks.md         # Static: investigation procedures
│   └── learned/                        # Dynamic: agent-discovered knowledge
│       └── <topic>.md                  # Written by agent during self-healing
└── .claude/
    ├── settings.json                   # Auto-approved read-only commands
    ├── settings.local.json             # Local overrides (not committed)
    └── commands/
        ├── sanity.md                   # /sanity
        ├── health-check.md             # /health-check
        ├── investigate.md              # /investigate <topic>
        └── learn.md                    # /learn [area]
```
