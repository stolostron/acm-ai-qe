# MCP Integration and External Sources

The agent augments its cluster observations with two external information sources:
the ACM UI MCP server (source code search) and the official ACM documentation
(AsciiDoc reference). These are used primarily during the self-healing process
(Phase 2) to understand components not covered by static knowledge.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Agent Investigation                             │
│                                                                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐ │
│  │  Live Cluster   │    │  ACM-UI MCP     │    │  rhacm-docs/        │ │
│  │  (oc CLI)       │    │  Server         │    │  (AsciiDoc)         │ │
│  │                 │    │                 │    │                     │ │
│  │  Primary source │    │  Source code    │    │  Official docs      │ │
│  │  of truth.      │    │  from GitHub.   │    │  from GitHub.       │ │
│  │  Always used.   │    │  Used during    │    │  Used during        │ │
│  │                 │    │  self-healing.  │    │  self-healing.      │ │
│  │                 │    │                 │    │  Optional.          │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────┘ │
│         │                      │                        │              │
│         └──────────────────────┼────────────────────────┘              │
│                                │                                       │
│                                ▼                                       │
│                     Synthesized Understanding                          │
│                     (written to learned/*.md)                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ACM-UI MCP Server

The `acm-ui` MCP server provides access to the stolostron/console and
kubevirt-plugin source code via GitHub. It is configured in `.mcp.json` at
the app root.

### Configuration

`.mcp.json`:
```json
{
  "mcpServers": {
    "acm-ui": {
      "command": "<venv>/bin/python",
      "args": ["-m", "acm_ui_mcp_server.main"],
      "timeout": 30
    }
  }
}
```

The MCP server runs as a Python process using the virtual environment created
by `mcp/setup.sh` from the repo root.

### Setup

```bash
# From the repo root (ai_systems_v2/)
# Select option 1 (ACM Hub Health Agent) when prompted
bash mcp/setup.sh
```

The setup script presents an interactive menu. Selecting option 1 installs
only the `acm-ui` MCP server and writes the `.mcp.json` config to this app's
directory. No other MCP servers are installed unless you also select the
z-stream analysis app.

### Available Tools

| Tool | Purpose | When Used |
|------|---------|-----------|
| `search_code` | Search for keywords across console + kubevirt-plugin codebase | Understanding how a component integrates |
| `search_component` | Find a specific React component by name | Finding UI component architecture |
| `get_component_source` | Get the full source code of a component | Understanding component behavior |
| `get_component_types` | Get TypeScript type definitions for a component | Understanding data contracts |
| `get_routes` | Find route definitions and navigation paths | Understanding UI navigation |
| `get_route_component` | Get the component rendered at a specific route | Mapping URL to component |
| `get_acm_selectors` | Find data-testid attributes in ACM components | Selector discovery |
| `get_patternfly_selectors` | Find PatternFly component selectors | UI element identification |
| `get_fleet_virt_selectors` | Find fleet virtualization selectors | VM management UI elements |
| `find_test_ids` | Find test IDs in component source | Test coverage discovery |
| `search_translations` | Search i18n translation strings | Finding user-visible text |
| `get_wizard_steps` | Get wizard step definitions | Multi-step flow analysis |
| `get_current_version` | Get the currently selected ACM version | Version context |
| `set_version` / `set_acm_version` / `set_cnv_version` | Set version context for searches | Version-scoped queries |
| `list_versions` | List available ACM/CNV versions | Version discovery |
| `list_repos` | List available repositories | Repo discovery |
| `detect_cnv_version` | Detect CNV version from context | Auto-detection |
| `get_cluster_virt_info` | Get virtualization info for a cluster | VM capability check |

### Version-Scoped Searches

The MCP server supports version-scoped searches to match the cluster's ACM
version. Set the version context before searching:

```
1. Get ACM version from MCH: oc get mch -A -o jsonpath='{.items[0].status.currentVersion}'
2. Set MCP version context: set_acm_version("2.16")
3. Search: search_code("observability", version="2.16")
```

This ensures search results match the code that's actually running on the cluster.

### When to Use MCP

| Scenario | MCP Tool(s) |
|----------|-------------|
| New component not in knowledge base | `search_code`, `search_component` |
| Understanding console integration | `get_routes`, `get_route_component` |
| Verifying component architecture | `get_component_source`, `get_component_types` |
| Finding UI navigation paths | `get_routes` |
| Understanding data flow | `search_code` with API/endpoint keywords |

---

## Official ACM Documentation (rhacm-docs)

The `docs/rhacm-docs/` directory can contain a clone of the official Red Hat ACM
documentation from the stolostron/rhacm-docs GitHub repository. This is optional
but improves the self-healing process.

### Setup

```bash
# From the acm-hub-health/ directory
git clone --depth 1 https://github.com/stolostron/rhacm-docs.git docs/rhacm-docs
```

The `docs/rhacm-docs/` directory is git-ignored (listed in `.gitignore`).

### How to Search

```bash
# Find files mentioning a component
grep -r "<component-name>" docs/rhacm-docs/ --include="*.adoc" -l

# Find files mentioning a keyword
grep -r "<keyword>" docs/rhacm-docs/ --include="*.adoc" -l

# Read a specific doc file
cat docs/rhacm-docs/troubleshooting/<file>.adoc
```

### Key Documentation Areas

| Directory | Content |
|-----------|---------|
| `troubleshooting/` | Symptom-based troubleshooting guides |
| `observability/` | Observability stack architecture, alerts, configuration |
| `install/` | Installation, sizing, upgrade procedures |
| `clusters/` | Cluster lifecycle management |
| `governance/` | Policy framework, compliance |
| `search/` | Search subsystem architecture |
| `virtualization/` | Fleet virtualization |
| `health_metrics/` | Metrics and monitoring |

### When rhacm-docs Is Not Present

If `docs/rhacm-docs/` has not been cloned, the agent skips documentation
searches during self-healing. It relies on cluster evidence and the acm-ui
MCP server instead. The agent operates correctly without the docs -- they
provide additional context but are not required.

---

## Integration with Self-Healing

During the self-healing process (see [03-KNOWLEDGE-SYSTEM.md](03-KNOWLEDGE-SYSTEM.md)),
the external sources are consulted in sequence:

```
  MISMATCH DETECTED
         │
         ▼
  Step 1: Cluster evidence (oc CLI)         ← Always available
         │
         ▼
  Step 2: Official docs (rhacm-docs/)       ← Optional (skipped if not cloned)
         │
         ▼
  Step 3: Source code (acm-ui MCP)          ← Available if MCP server is set up
         │
         ▼
  Step 4: Synthesize all evidence
         │
         ▼
  Step 5: Write learned knowledge
```

Each source provides different context:

| Source | What It Provides |
|--------|-----------------|
| Cluster (oc CLI) | Current state: what's deployed, its status, its configuration |
| rhacm-docs | Intent: what the component is designed to do, how it should be configured |
| acm-ui MCP | Implementation: how it integrates with the console, its API surface, data flow |

The combination of all three gives the agent a complete picture: current state
(cluster), intended behavior (docs), and implementation details (source code).

---

## Permission Model

The `.claude/settings.json` file auto-approves specific tool categories:

| Permission | What It Allows |
|-----------|----------------|
| `Bash(oc get:*)` | All `oc get` commands |
| `Bash(oc describe:*)` | All `oc describe` commands |
| `Bash(oc logs:*)` | All `oc logs` commands |
| `Bash(oc version:*)` | Version checks |
| `Bash(oc whoami:*)` | Identity checks |
| `Bash(oc cluster-info:*)` | Cluster info |
| `Bash(oc api-resources:*)` | API resource discovery |
| `Bash(oc adm top:*)` | Resource usage |
| `Bash(kubectl get:*)` | kubectl get commands |
| `Bash(kubectl describe:*)` | kubectl describe commands |
| `Bash(grep:*)`, `Bash(jq:*)`, `Bash(wc:*)`, `Bash(sort:*)`, `Bash(head:*)`, `Bash(tail:*)`, `Bash(awk:*)`, `Bash(cut:*)` | Text processing utilities |
| `Bash(cat:*)`, `Bash(ls:*)`, `Bash(find:*)` | File system inspection |
| `Bash(git clone:*)` | Cloning rhacm-docs |
| `Read` | Reading any file |
| `Write(knowledge/learned/*)` | Writing learned knowledge files only |
| `mcp__acm-ui__*` | All acm-ui MCP server tools |

The agent's write access is limited to `knowledge/learned/` (via the Write
permission) and `docs/rhacm-docs/` (via `git clone`). It cannot modify cluster
state. It cannot execute arbitrary commands.

---

## See Also

- [03-KNOWLEDGE-SYSTEM.md](03-KNOWLEDGE-SYSTEM.md) -- self-healing process that uses these sources
- [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) -- Phase 2 (Learn) where sources are consulted
- [00-OVERVIEW.md](00-OVERVIEW.md) -- top-level overview
