# MCP Integration and External Sources

The agent augments its cluster observations with three external information
sources: the ACM UI MCP server (source code search), the Neo4j RHACM knowledge
graph (component dependency analysis), and the official ACM documentation
(AsciiDoc reference). These are used during self-healing (Phase 2), dependency
correlation (Phase 5), and whenever the static knowledge doesn't cover a
component or dependency path.

---

## Overview

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                              Agent Investigation                                     │
│                                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │
│  │ Live Cluster │  │ ACM-UI MCP   │  │ neo4j-rhacm MCP  │  │ rhacm-docs/         │  │
│  │ (oc CLI)     │  │ Server       │  │ (Knowledge Graph)│  │ (AsciiDoc)          │  │
│  │              │  │              │  │                  │  │                     │  │
│  │ Primary      │  │ Source code  │  │ 370 component    │  │ Official docs       │  │
│  │ source of    │  │ from GitHub. │  │ dependency graph.│  │ from GitHub.        │  │
│  │ truth.       │  │ Used during  │  │ Fallback when    │  │ Used during         │  │
│  │ Always used. │  │ self-healing.│  │ curated chains   │  │ self-healing.       │  │
│  │              │  │              │  │ don't cover it.  │  │ Optional.           │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  └─────────────────────┘  │
│         │                 │                   │                       │               │
│         └─────────────────┼───────────────────┼───────────────────────┘               │
│                           │                   │                                       │
│                           ▼                   ▼                                       │
│                       Synthesized Understanding                                      │
│                       (written to learned/*.md)                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ACM-UI MCP Server

The `acm-ui` MCP server provides access to the stolostron/console and
kubevirt-plugin source code via GitHub. It is configured in `.mcp.json` at
the app root.

### Configuration

`.mcp.json` (acm-ui entry shown; see neo4j-rhacm section for its config):
```json
{
  "mcpServers": {
    "acm-ui": {
      "command": "<venv>/bin/python",
      "args": ["-m", "acm_ui_mcp_server.main"],
      "timeout": 30
    },
    "neo4j-rhacm": { "..." : "see Knowledge Graph section below" }
  }
}
```

The MCP server runs as a Python process using the virtual environment created
by `mcp/setup.sh` from the repo root.

### Setup

```bash
# Option A: App-level setup (from acm-hub-health/)
bash setup.sh

# Option B: Repo-level setup (from ai_systems_v2/)
# Select option 1 (ACM Hub Health Agent) when prompted
bash mcp/setup.sh
```

Either script creates the virtual environment, generates the `.mcp.json`
config (with acm-ui and neo4j-rhacm), and checks prerequisites. The
app-level `setup.sh` also clones rhacm-docs.

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
| `set_version` | Set version context for searches | Version-scoped queries |
| `set_acm_version` | Set ACM version context | Version-scoped queries |
| `set_cnv_version` | Set CNV version context | Version-scoped queries |
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

## Neo4j RHACM Knowledge Graph (neo4j-rhacm)

The `neo4j-rhacm` MCP server provides read-only Cypher query access to a
Neo4j graph database containing 370 ACM components and 541 dependency
relationships (incl. Hive, Klusterlet, HyperShift, Virtualization, RBAC).
It supplements the 8 curated dependency chains in
`knowledge/dependency-chains.yaml` with a broader, dynamic component graph.

### Configuration

`.mcp.json` (generated by setup.sh):
```json
{
  "mcpServers": {
    "neo4j-rhacm": {
      "command": "uvx",
      "args": ["--with", "fastmcp<3", "mcp-neo4j-cypher",
               "--db-url", "bolt://localhost:7687",
               "--username", "neo4j", "--password", "rhacmgraph",
               "--read-only"],
      "timeout": 60
    }
  }
}
```

The MCP server connects to a local Neo4j container via the Bolt protocol.
The container is created and loaded with graph data by `mcp/setup.sh`.

### Setup

```bash
# Repo-level setup (creates container, loads graph data)
bash mcp/setup.sh     # Select option 1 or 3

# App-level setup (configures .mcp.json; container must exist)
bash setup.sh
```

The repo-level `mcp/setup.sh` handles the full lifecycle: installing Podman
if needed, creating the Neo4j container, loading the base graph (~291 base
components) and extensions (Hive, Klusterlet, Addon Framework, HyperShift,
Virtualization, RBAC, depth connections), and generating `.mcp.json`.
The app-level `setup.sh` only writes the MCP config -- use `mcp/setup.sh`
if the container doesn't exist yet.

### Available Tools

The MCP server exposes two Cypher query tools:

| Tool | Purpose | When Used |
|------|---------|-----------|
| `read_query` | Execute a read-only Cypher query | Dependency tracing, impact analysis, common root cause detection |
| `get_schema` | Get the graph schema (node types, relationships) | Understanding what's queryable |

### When to Use

| Scenario | Query Pattern |
|----------|---------------|
| Component not in the 8 curated chains | Query direct dependencies and dependents |
| Multiple failures with no obvious link | Find common upstream dependencies |
| Unknown component during self-healing | Query subsystem membership and dependencies |
| Tracing transitive failure impact | Query dependents up to 3 hops deep |

### When NOT to Use

- **Curated chains cover it** -- prefer `dependency-chains.yaml` (it includes
  impact descriptions and investigation procedures the raw graph doesn't)
- **Quick sanity checks** (Phase 1 only) -- adds latency, not needed for pulse
- **Health definitions** -- the graph shows structural relationships, not
  what "healthy" looks like (use `healthy-baseline.yaml` for that)

### Example Queries

```cypher
-- What does a component depend on?
MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent)
WHERE c.label =~ '(?i).*search-api.*'
RETURN dep.label, dep.subsystem

-- What breaks if a component fails? (transitive, up to 3 hops)
MATCH path = (dep:RHACMComponent)-[:DEPENDS_ON*1..3]->(c:RHACMComponent)
WHERE c.label =~ '(?i).*search-api.*'
RETURN DISTINCT dep.label, dep.subsystem

-- Find shared root cause for multiple failing components
MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent)
WHERE c.label =~ '(?i).*(search|console).*'
WITH common, collect(DISTINCT c.label) AS dependents, count(DISTINCT c) AS cnt
WHERE cnt > 1
RETURN common.label, common.subsystem, dependents

-- All components in a subsystem
MATCH (c:RHACMComponent)
WHERE c.subsystem =~ '(?i).*governance.*'
RETURN c.label, c.type
```

### Availability

The knowledge graph requires a local Neo4j container (`neo4j-rhacm`). If
the MCP is unavailable (container not running, Podman not installed), the
agent skips graph queries silently and relies on the curated knowledge files.
The agent operates correctly without it -- the graph provides broader
coverage but is not required.

To check status: `podman ps | grep neo4j-rhacm`
To start a stopped container: `podman start neo4j-rhacm`

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
  Step 2: Cluster introspection             ← Reverse-engineer deps from
         (live metadata)                       owner refs, OLM labels, CSVs,
         │                                     env vars, webhooks, ConsolePlugins,
         ▼                                     APIServices (always available)
  Step 3: Knowledge graph                   ← neo4j-rhacm MCP
         (cross-reference)                     Supplement cluster-derived map
         │                                     with broader ACM relationships
         ▼
  Step 4: Understand dependencies           ← acm-ui MCP + rhacm-docs
         (source code + docs)                  For each dep from steps 2-3:
         │                                     HOW does it work?
         ▼
  Step 5: Synthesize all evidence
         │
         ▼
  Step 6: Write learned knowledge
```

The self-healing process uses a **layered discovery flow**: cluster
introspection builds a dependency map from live metadata (always
available, no external tools), the knowledge graph supplements it with
broader ACM relationships, then acm-ui MCP and rhacm-docs fill in the
implementation details. Each step is informed by the previous step's output.

Each source provides different context:

| Source | What It Provides | Role |
|--------|-----------------|------|
| Cluster (oc CLI) | Current state: what's deployed, its status, its configuration | What IS |
| Cluster introspection | Dependencies from owner refs, OLM labels, CSVs, env vars, webhooks | The map (always available) |
| neo4j-rhacm MCP | Broader ACM component relationships, subsystem membership | Supplements the map |
| acm-ui MCP | Implementation: source code, data flow, integration points | How it works |
| rhacm-docs | Intent: what the component is designed to do, how it should be configured | Why it exists |

Cluster introspection provides the map from live metadata. The knowledge
graph supplements it. The acm-ui MCP provides implementation details.
Together they let the agent understand any component's full context --
including third-party operators not in the knowledge database.

---

## Permission Model

The `.claude/settings.json` file auto-approves two categories of commands:

- **Diagnostic** (always available): read-only `oc`/`kubectl` commands,
  text processing utilities, file inspection, `git clone`, all acm-ui
  MCP tools, and all neo4j-rhacm MCP tools (read-only Cypher queries).
  File writes limited to `knowledge/learned/` only.
- **Remediation** (double-gated): `oc patch`, `oc scale`,
  `oc rollout restart`, `oc delete pod`, `oc annotate`, `oc label`,
  `oc apply`. These are NOT auto-approved in settings.json -- Claude Code
  prompts the user for permission on each mutation command. Additionally,
  the CLAUDE.md Remediation Protocol requires completing all diagnosis and
  presenting a structured plan before offering any fixes.

Destructive commands (`oc delete` on non-pod resources, `oc adm drain`)
are never allowed.

See [CLAUDE.md](../CLAUDE.md) for the Safety and Remediation Protocol
sections and `.claude/settings.json` for the exact permission entries.

---

## See Also

- [03-KNOWLEDGE-SYSTEM.md](03-KNOWLEDGE-SYSTEM.md) -- self-healing process that uses these sources
- [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) -- Phase 2 (Learn) where sources are consulted
- [00-OVERVIEW.md](00-OVERVIEW.md) -- top-level overview
