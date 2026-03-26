# Neo4j RHACM Dependency Graph MCP Server

## Complete Documentation and Setup Guide

---

## Table of Contents

1. [What This Is](#what-this-is)
2. [Why You Need This](#why-you-need-this)
3. [Architecture Overview](#architecture-overview)
4. [Component Details](#component-details)
5. [Data Model](#data-model)
6. [Complete Setup Instructions](#complete-setup-instructions)
7. [Usage Guide](#usage-guide)
8. [Query Examples](#query-examples)
9. [QE Use Cases](#qe-use-cases)
10. [Maintenance](#maintenance)
11. [Troubleshooting](#troubleshooting)

---

## What This Is

### Overview

The **Neo4j RHACM Dependency Graph MCP Server** is a Model Context Protocol (MCP) integration that gives Cursor IDE direct access to a Neo4j graph database containing the complete architecture of Red Hat Advanced Cluster Management (RHACM).

### Key Facts

| Attribute | Value |
|-----------|-------|
| **Components** | 291 verified RHACM components |
| **Relationships** | 419 semantic relationships |
| **Subsystems** | 7 major areas (Governance, Cluster, App, Obs, Search, Console, Overview) |
| **Data Source** | [stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph) |
| **Verification** | 100% GitHub-verified against official repositories |

### What It Provides

1. **Natural Language Queries** - Ask questions about RHACM architecture in plain English
2. **Impact Analysis** - Understand what breaks when a component fails
3. **Dependency Tracing** - Follow relationships between controllers, CRDs, and operators
4. **Architecture Understanding** - Visualize how ACM components connect
5. **Debugging Aid** - Find which controller manages a specific CRD

---

## Why You Need This

### The Problem

RHACM is a complex product with:
- 100+ repositories in the stolostron organization
- Multiple interacting controllers and operators
- Cross-cluster communication patterns (hub-spoke)
- Complex policy propagation flows
- Many CRDs managed by different controllers

Understanding these relationships requires:
- Reading thousands of lines of code
- Tracing through multiple repositories
- Expert knowledge of the architecture
- Manual documentation that gets outdated

### The Solution

This dependency graph:
- **Externalizes knowledge** - Architecture is queryable, not in someone's head
- **Enables impact analysis** - "What breaks if X fails?"
- **Speeds debugging** - "Which controller manages this CRD?"
- **Supports QE testing** - Understand component dependencies for test design
- **Reduces escalations** - Self-service architecture exploration

### Benefits for QE Work

| QE Task | How Dependency Graph Helps |
|---------|---------------------------|
| RBAC Testing | Trace MCRA → ClusterPermission → RoleBinding flow |
| CNV/MTV Testing | Understand addon deployment dependencies |
| CCLM Debugging | Find controller interactions and race conditions |
| Policy Testing | Trace policy propagation from hub to spoke |
| Bug Root Cause | Identify which controller to investigate |
| Test Case Design | Understand component relationships |

---

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR MACHINE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐      ┌─────────────────┐      ┌─────────────────────────┐ │
│  │  Cursor IDE  │ ───► │   mcp-remote    │ ───► │   MCP Server            │ │
│  │              │      │   (npx)         │      │   (Port 8000)           │ │
│  │  - AI Agent  │      │                 │      │   - SSE Transport       │ │
│  │  - Queries   │      │   Bridges to    │      │   - Cypher Translation  │ │
│  └──────────────┘      │   local server  │      └───────────┬─────────────┘ │
│                        └─────────────────┘                  │               │
│                                                             │ Bolt Protocol │
│                                                             ▼               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    Neo4j Database (Podman Container)                  │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │                    RHACM Architecture Graph                      │ │  │
│  │  │                                                                  │ │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │  │
│  │  │  │ Overview │  │Governance│  │  Cluster │  │   App    │        │ │  │
│  │  │  │   110    │  │    81    │  │    13    │  │    23    │        │ │  │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │ │  │
│  │  │                                                                  │ │  │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │ │  │
│  │  │  │   Obs    │  │  Search  │  │ Console  │  = 291 components     │ │  │
│  │  │  │    20    │  │    16    │  │    28    │  = 287+ relationships │ │  │
│  │  │  └──────────┘  └──────────┘  └──────────┘                       │ │  │
│  │  │                                                                  │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  Ports: 7474 (Browser), 7687 (Bolt)                                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  stolostron/knowledge-graph (Cloned Repository)                       │  │
│  │  <knowledge-graph-clone>/                  │  │
│  │                                                                        │  │
│  │  - rhacm_architecture_comprehensive_final.cypher (main data)          │  │
│  │  - sample_queries.cypher (30+ analytics queries)                      │  │
│  │  - mcp_sample_questions.md (100+ curated questions)                   │  │
│  │  - mermaid/*.mmd (visual architecture diagrams)                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow

```
1. User asks: "What depends on Hive Operator?"
                    │
                    ▼
2. Cursor AI receives the question
                    │
                    ▼
3. AI recognizes this as a graph query
                    │
                    ▼
4. MCP tool call via mcp-remote to http://localhost:8000/sse
                    │
                    ▼
5. MCP Server translates to Cypher:
   MATCH (source)-[r]->(target {label: 'Hive Operator'})
   RETURN source.label, type(r)
                    │
                    ▼
6. Neo4j executes query and returns results
                    │
                    ▼
7. MCP Server streams results back via SSE
                    │
                    ▼
8. AI formats and presents to user
```

---

## Component Details

### 1. Neo4j Database

**What**: Graph database optimized for connected data

**Container**: `neo4j-rhacm`
- **Image**: `neo4j:2025.01.0`
- **Ports**: 
  - `7474` - Browser UI (HTTP)
  - `7687` - Bolt protocol (database connections)
- **Credentials**: `neo4j` / `rhacmgraph`
- **Plugins**: APOC (Awesome Procedures On Cypher)

**Access Points**:
- **Browser UI**: http://localhost:7474
- **Bolt URL**: `bolt://localhost:7687`

**Why Neo4j**:
- Native graph storage (not relational tables)
- Cypher query language (pattern-based)
- Excellent for dependency/relationship analysis
- Visual graph exploration in browser

### 2. MCP Server

**What**: Model Context Protocol server that exposes Neo4j to AI agents

**Container**: `neo4j-mcp`
- **Image**: `quay.io/bjoydeep/neo4j-cypher:fixed`
- **Port**: `8000`
- **Transport**: SSE (Server-Sent Events)

**Access Point**: http://localhost:8000/sse

**Tools Exposed**:

| Tool | Purpose |
|------|---------|
| `read_neo4j_cypher` | Execute read-only Cypher queries |
| `write_neo4j_cypher` | Execute write Cypher queries |
| `get_neo4j_schema` | Get database schema information |

**Why MCP**:
- Standard protocol for AI tool integration
- Cursor IDE native support
- Safe, controlled database access
- Streaming responses via SSE

### 3. mcp-remote (NPX Package)

**What**: Bridge between Cursor and local MCP server

**Configuration** in `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "neo4j-rhacm": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8000/sse"
      ],
      "timeout": 120
    }
  }
}
```

**Why mcp-remote**:
- Connects Cursor to any SSE-based MCP server
- No local installation required (npx downloads on demand)
- Works with localhost endpoints

### 4. knowledge-graph Repository

**What**: Source data for the RHACM architecture graph

**Location**: `<knowledge-graph-clone>/`

**Key Files**:

| File | Purpose |
|------|---------|
| `acm/agentic-docs/dependency-analysis/knowledge-graph/rhacm_architecture_comprehensive_final.cypher` | Main Neo4j import script (291 components) |
| `acm/agentic-docs/dependency-analysis/knowledge-graph/sample_queries.cypher` | 30+ ready-to-use analytics queries |
| `acm/agentic-docs/dependency-analysis/mcp_sample_questions.md` | 100+ curated questions for AI |
| `acm/agentic-docs/dependency-analysis/mermaid/*.mmd` | Visual architecture diagrams |
| `acm/agentic-docs/dependency-analysis/rhacm_architecture_implementation_guide.md` | How the graph was built |

**Data Quality**:
- Every component verified against GitHub repositories
- No fictional components
- Semantic relationship labels (not generic arrows)
- Complete enterprise features coverage

---

## Data Model

### Node Types

All nodes have the label `RHACMComponent` plus additional labels:

| Node Type | Count | Examples |
|-----------|-------|----------|
| **Controller** | 40+ | `config-policy-controller`, `governance-policy-addon-controller` |
| **Operator** | 25+ | `Hive Operator`, `multicluster-observability-operator` |
| **Component** | 80+ | `Web Console`, `Klusterlet`, `Submariner Gateway` |
| **Cluster** | 15+ | `ACM Hub Cluster`, `Managed Clusters`, `Cluster Manager` |
| **API** | 10+ | `Kubernetes API Server`, `Open Cluster Management API` |
| **Policy** | 20+ | `governance-policy-propagator`, `policy-collection` |
| **Observability** | 10+ | `Prometheus Stack`, `Grafana`, `Thanos` |
| **Search** | 10+ | `search-indexer`, `search-collector`, `search-v2-api` |

### Subsystems

| Subsystem | Components | Description |
|-----------|------------|-------------|
| **Overview** | 110 | Core ACM components, MCE, Global Hub, Submariner |
| **Governance** | 81 | Policy propagation, compliance, GRC framework |
| **Console** | 28 | Web UI, console API, integrations |
| **Application** | 23 | App lifecycle, GitOps, ArgoCD, subscriptions |
| **Observability** | 20 | Metrics, Thanos, Prometheus, Grafana |
| **Search** | 16 | Search indexer, collector, API |
| **Cluster** | 13 | Cluster lifecycle, Hive, provisioning |

### Relationship Types

| Relationship | Count | Meaning |
|--------------|-------|---------|
| `CONTAINS` | 108 | Parent contains child component |
| `DEPENDS_ON` | 88 | Component depends on another |
| `USES` | 33 | Component uses another's functionality |
| `MANAGES` | 21 | Controller/operator manages CRD/resource |
| `INTEGRATES_WITH` | 10 | Cross-system integration |
| `ORCHESTRATES` | 6 | Component orchestrates others |
| `PROVIDES_UI_FOR` | 6 | UI component for backend |
| `DEPLOYS` | 5 | Component deploys another |
| `ENABLES` | 5 | Component enables functionality |
| `PROVIDES` | 5 | Component provides service |

### Node Properties

Each `RHACMComponent` node has:

| Property | Description | Example |
|----------|-------------|---------|
| `id` | Unique identifier | `GOV_POLICY_PROP` |
| `label` | Human-readable name | `governance-policy-propagator` |
| `subsystem` | Which subsystem | `Governance` |
| `type` | Component type | `Policy`, `Controller`, `Operator` |
| `description` | Brief description | `Governance component: governance-policy-propagator` |

---

## Complete Setup Instructions

### Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| **Podman** | 5.x | `podman --version` |
| **Node.js** | 18+ | `node --version` |
| **npx** | (comes with npm) | `which npx` |

### Step 1: Start Podman Machine (if not running)

```bash
# Check if Podman machine exists
podman machine list

# Start the machine
podman machine start

# Verify it's running
podman machine list
# Should show "Running" status
```

### Step 2: Clone the Knowledge Graph Repository

```bash
# Navigate to tools directory
cd <parent-directory>

# Clone the repository
git clone https://github.com/stolostron/knowledge-graph.git

# Verify
ls knowledge-graph/acm/agentic-docs/dependency-analysis/knowledge-graph/
# Should show: rhacm_architecture_comprehensive_final.cypher, sample_queries.cypher
```

### Step 3: Start Neo4j Database Container

```bash
podman run -d \
    --name neo4j-rhacm \
    --restart always \
    -p 7474:7474 \
    -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/rhacmgraph \
    -e 'NEO4J_PLUGINS=["apoc"]' \
    neo4j:2025.01.0
```

**Explanation**:
- `-d`: Run in background (detached)
- `--name neo4j-rhacm`: Container name for easy reference
- `--restart always`: Auto-restart on failure or reboot
- `-p 7474:7474`: Browser UI port
- `-p 7687:7687`: Bolt protocol port
- `-e NEO4J_AUTH`: Set username/password
- `-e NEO4J_PLUGINS`: Enable APOC procedures
- `neo4j:2025.01.0`: Latest Neo4j version

### Step 4: Wait for Neo4j to Start

```bash
# Wait 30 seconds for startup
sleep 30

# Check logs to confirm it's ready
podman logs neo4j-rhacm 2>&1 | tail -5
# Should show: "Started."
```

### Step 5: Load RHACM Architecture Data

```bash
# Copy the Cypher file into the container
podman cp <knowledge-graph-clone>/acm/agentic-docs/dependency-analysis/knowledge-graph/rhacm_architecture_comprehensive_final.cypher neo4j-rhacm:/tmp/

# Execute the Cypher script
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph -f /tmp/rhacm_architecture_comprehensive_final.cypher

# Verify data loaded
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph \
    "MATCH (n:RHACMComponent) RETURN n.subsystem as Subsystem, count(n) as Count ORDER BY Count DESC"
```

**Expected Output**:
```
Subsystem, Count
"Overview", 110
"Governance", 81
"Console", 28
"Application", 23
"Observability", 20
"Search", 16
"Cluster", 13
```

### Step 6: Start MCP Server Container

First, get the Neo4j container's IP address:
```bash
NEO4J_IP=$(podman inspect neo4j-rhacm --format '{{.NetworkSettings.IPAddress}}')
echo "Neo4j IP: $NEO4J_IP"
```

Then start the MCP server with the correct IP:
```bash
podman run -d \
    --name neo4j-mcp \
    -p 8000:8000 \
    quay.io/bjoydeep/neo4j-cypher:fixed \
    mcp-neo4j-cypher \
    --db-url bolt://${NEO4J_IP}:7687 \
    --username neo4j \
    --password rhacmgraph \
    --transport sse
```

**Note**: Using the actual container IP (e.g., `10.88.0.2`) is more reliable than `host.containers.internal` on macOS with Podman.

**Explanation**:
- `--db-url bolt://<IP>:7687`: Connect to Neo4j container using its actual IP
- `--transport sse`: Use Server-Sent Events for streaming
- Port 8000 for MCP SSE endpoint

### Step 7: Verify MCP Server

```bash
# Check it's running
podman ps --filter name=neo4j-mcp

# Check logs
podman logs neo4j-mcp 2>&1 | tail -5
# Should show: "Uvicorn running on http://0.0.0.0:8000"

# Test the endpoint
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/sse
# Should return: 200
```

### Step 8: Update Cursor MCP Configuration

Edit `~/.cursor/mcp.json` and add the `neo4j-rhacm` entry:

```json
{
  "mcpServers": {
    "neo4j-rhacm": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://localhost:8000/sse"
      ],
      "timeout": 120
    }
  }
}
```

### Step 9: Create Tool Descriptors for Cursor

Cursor requires tool descriptor files to recognize MCP tools. Create the folder and files:

```bash
# Create the MCP tools directory
mkdir -p ~/.cursor/projects/Users-ashafi-Documents-work-automation/mcps/user-neo4j-rhacm/tools

# Create read_neo4j_cypher.json
cat > ~/.cursor/projects/Users-ashafi-Documents-work-automation/mcps/user-neo4j-rhacm/tools/read_neo4j_cypher.json << 'EOF'
{
  "name": "read_neo4j_cypher",
  "description": "Execute a read-only Cypher query against the RHACM dependency graph in Neo4j. Returns results as JSON array of objects.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The Cypher query to execute"
      },
      "params": {
        "type": "object",
        "description": "Optional parameters for the query",
        "default": {}
      }
    },
    "required": ["query"]
  }
}
EOF

# Create write_neo4j_cypher.json
cat > ~/.cursor/projects/Users-ashafi-Documents-work-automation/mcps/user-neo4j-rhacm/tools/write_neo4j_cypher.json << 'EOF'
{
  "name": "write_neo4j_cypher",
  "description": "Execute an updating Cypher query against Neo4j. Returns a result summary.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "The Cypher query to execute"
      },
      "params": {
        "type": "object",
        "description": "Optional parameters",
        "default": {}
      }
    },
    "required": ["query"]
  }
}
EOF

# Create get_neo4j_schema.json
cat > ~/.cursor/projects/Users-ashafi-Documents-work-automation/mcps/user-neo4j-rhacm/tools/get_neo4j_schema.json << 'EOF'
{
  "name": "get_neo4j_schema",
  "description": "Get the Neo4j database schema including node labels, properties, and relationships.",
  "inputSchema": {
    "type": "object",
    "properties": {},
    "required": []
  }
}
EOF

# Create SERVER_METADATA.json
cat > ~/.cursor/projects/Users-ashafi-Documents-work-automation/mcps/user-neo4j-rhacm/SERVER_METADATA.json << 'EOF'
{
  "name": "neo4j-rhacm",
  "description": "RHACM Dependency Graph - Neo4j MCP Server",
  "version": "0.2.2"
}
EOF
```

### Step 10: Restart Cursor

1. **Quit Cursor completely** (Cmd+Q on Mac)
2. **Reopen Cursor**
3. **Verify MCP is loaded**: Settings > Features > MCP
4. **Should show**: `neo4j-rhacm` with `3 tools enabled`

---

## Usage Guide

### Natural Language Queries

After setup, you can ask questions naturally in Cursor:

#### Basic Architecture Questions
```
"How many components are in each RHACM subsystem?"
"What are the main types of components in RHACM?"
"List all operators in the RHACM architecture"
```

#### Dependency Analysis
```
"What components depend on governance-policy-propagator?"
"Show me what Hive Operator manages"
"What are the dependencies of the Governance subsystem?"
```

#### Impact Analysis
```
"If config-policy-controller fails, what would be affected?"
"What is the blast radius of a Placement Controller failure?"
"Which components are critical for RHACM operation?"
```

#### Cross-Subsystem Analysis
```
"How does Governance integrate with Cluster Management?"
"Show cross-subsystem dependencies"
"What components bridge Application and Cluster subsystems?"
```

#### Hub-Spoke Architecture
```
"What components run on managed clusters?"
"Show hub-spoke communication patterns"
"How do spoke clusters report back to the hub?"
```

### Direct Cypher Queries

You can also request specific Cypher queries:

```
"Run this Cypher: MATCH (n:RHACMComponent) WHERE n.subsystem = 'Governance' RETURN n.label, n.type"
```

---

## Query Examples

### 1. Component Discovery

**List all components by subsystem:**
```cypher
MATCH (n:RHACMComponent) 
RETURN n.subsystem as Subsystem, count(n) as ComponentCount 
ORDER BY ComponentCount DESC
```

**Find components by name pattern:**
```cypher
MATCH (n:RHACMComponent) 
WHERE n.label CONTAINS 'policy' 
RETURN n.label, n.subsystem, n.type
```

**List all controllers:**
```cypher
MATCH (n:RHACMComponent) 
WHERE n.type = 'Controller' 
RETURN n.label, n.subsystem 
ORDER BY n.subsystem
```

### 2. Dependency Analysis

**What depends on a component:**
```cypher
MATCH (source)-[r]->(target {label: 'governance-policy-propagator'})
RETURN source.label as DependsOn, type(r) as RelationType
```

**What a component depends on:**
```cypher
MATCH (source {label: 'governance-policy-propagator'})-[r]->(target)
RETURN target.label as Dependency, type(r) as RelationType
```

**Multi-hop dependencies:**
```cypher
MATCH path = (source {label: 'Hive Operator'})-[*1..3]->(target)
RETURN [n in nodes(path) | n.label] as DependencyChain
LIMIT 20
```

### 3. Impact Analysis

**Most connected components (critical):**
```cypher
MATCH (n:RHACMComponent)
OPTIONAL MATCH (n)-[r_out]->()
OPTIONAL MATCH ()-[r_in]->(n)
RETURN n.label, n.subsystem, 
       count(DISTINCT r_out) + count(DISTINCT r_in) as Connections
ORDER BY Connections DESC LIMIT 15
```

**Cross-subsystem dependencies:**
```cypher
MATCH (source:RHACMComponent)-[r]->(target:RHACMComponent)
WHERE source.subsystem <> target.subsystem
RETURN source.subsystem as From, target.subsystem as To, count(r) as Dependencies
ORDER BY Dependencies DESC
```

### 4. Enterprise Features

**Global Hub components:**
```cypher
MATCH (n:RHACMComponent) 
WHERE n.label CONTAINS 'Global Hub' 
RETURN n.label, n.type
```

**Submariner networking:**
```cypher
MATCH (n:RHACMComponent) 
WHERE n.label CONTAINS 'Submariner' 
RETURN n.label, n.type
```

**Backup & Recovery:**
```cypher
MATCH (n:RHACMComponent) 
WHERE n.label CONTAINS 'Backup' OR n.label CONTAINS 'OADP' OR n.label CONTAINS 'Velero'
RETURN n.label, n.type
```

---

## QE Use Cases

### RBAC Testing

**Find all RBAC-related components:**
```cypher
MATCH (n:RHACMComponent) 
WHERE n.label CONTAINS 'Role' OR n.label CONTAINS 'Permission' OR n.label CONTAINS 'RBAC'
RETURN n.label, n.subsystem, n.type
```

**Trace policy flow:**
```
"Show me the policy propagation path from hub to managed clusters"
```

### CNV/MTV/CCLM Testing

**Find addon deployment patterns:**
```cypher
MATCH (n:RHACMComponent) 
WHERE n.label CONTAINS 'Addon' 
RETURN n.label, n.subsystem, n.type
```

**Understand controller interactions:**
```
"What controllers are involved in cluster registration?"
```

### Debugging Scenarios

**Component failure impact:**
```
"If governance-policy-propagator fails, what would be affected?"
```

**CRD ownership:**
```
"Which controller manages the ManagedCluster CRD?"
```

**Controller dependencies:**
```
"What does config-policy-controller depend on?"
```

---

## Maintenance

### Daily Operations

**Start services (after reboot):**
```bash
podman machine start
podman start neo4j-rhacm neo4j-mcp
```

**Stop services:**
```bash
podman stop neo4j-rhacm neo4j-mcp
```

**Check status:**
```bash
podman ps --filter name=neo4j
```

### Viewing Logs

```bash
# Neo4j logs
podman logs neo4j-rhacm

# MCP server logs
podman logs neo4j-mcp

# Follow logs in real-time
podman logs -f neo4j-mcp
```

### Updating Data

To refresh the data from the latest repository:

```bash
# Pull latest changes
cd <knowledge-graph-clone>
git pull

# Clear existing data
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph \
    "MATCH (n) DETACH DELETE n"

# Reload data
podman cp acm/agentic-docs/dependency-analysis/knowledge-graph/rhacm_architecture_comprehensive_final.cypher neo4j-rhacm:/tmp/
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph -f /tmp/rhacm_architecture_comprehensive_final.cypher
```

### Recreating Containers

If you need to start fresh:

```bash
# Remove containers
podman rm -f neo4j-rhacm neo4j-mcp

# Recreate Neo4j
podman run -d \
    --name neo4j-rhacm \
    --restart always \
    -p 7474:7474 \
    -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/rhacmgraph \
    -e 'NEO4J_PLUGINS=["apoc"]' \
    neo4j:2025.01.0

# Wait for startup
sleep 30

# Load data
podman cp <knowledge-graph-clone>/acm/agentic-docs/dependency-analysis/knowledge-graph/rhacm_architecture_comprehensive_final.cypher neo4j-rhacm:/tmp/
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph -f /tmp/rhacm_architecture_comprehensive_final.cypher

# Get Neo4j IP
NEO4J_IP=$(podman inspect neo4j-rhacm --format '{{.NetworkSettings.IPAddress}}')
echo "Neo4j IP: $NEO4J_IP"

# Recreate MCP server with correct IP
podman run -d \
    --name neo4j-mcp \
    -p 8000:8000 \
    quay.io/bjoydeep/neo4j-cypher:fixed \
    mcp-neo4j-cypher \
    --db-url bolt://${NEO4J_IP}:7687 \
    --username neo4j \
    --password rhacmgraph \
    --transport sse
```

---

## Troubleshooting

### Podman Issues

**"Cannot connect to Podman":**
```bash
# Start Podman machine
podman machine start
```

**Container won't start:**
```bash
# Check for port conflicts
lsof -i :7474
lsof -i :7687
lsof -i :8000

# Remove conflicting containers
podman rm -f neo4j-rhacm neo4j-mcp
```

### Neo4j Issues

**"Connection refused":**
- Wait 30 seconds after starting the container
- Check logs: `podman logs neo4j-rhacm`

**"Authentication failed":**
- Credentials are: `neo4j` / `rhacmgraph`
- If you need to reset, recreate the container

### MCP Issues

**MCP not showing in Cursor:**
1. Verify `~/.cursor/mcp.json` is valid JSON
2. Restart Cursor completely (Cmd+Q)
3. Check MCP server is running: `podman ps --filter name=neo4j-mcp`

**"No tools, prompts, or resources" in Cursor:**

This happens when Cursor can't find the tool descriptor files. Fix:

```bash
# Create tool descriptors (see Step 9 above)
mkdir -p ~/.cursor/projects/Users-ashafi-Documents-work-automation/mcps/user-neo4j-rhacm/tools

# Verify files exist
ls ~/.cursor/projects/Users-ashafi-Documents-work-automation/mcps/user-neo4j-rhacm/tools/
# Should show: read_neo4j_cypher.json, write_neo4j_cypher.json, get_neo4j_schema.json

# Restart Cursor
```

**"Error - Show Output" in Cursor:**
1. Check MCP server logs: `podman logs neo4j-mcp`
2. Verify endpoint: `curl http://localhost:8000/sse`
3. Restart MCP container: `podman restart neo4j-mcp`

**MCP container can't connect to Neo4j:**

This usually happens because `host.containers.internal` doesn't resolve properly on macOS. Fix:

```bash
# Get Neo4j container IP
NEO4J_IP=$(podman inspect neo4j-rhacm --format '{{.NetworkSettings.IPAddress}}')

# Recreate MCP with correct IP
podman rm -f neo4j-mcp
podman run -d --name neo4j-mcp -p 8000:8000 \
    quay.io/bjoydeep/neo4j-cypher:fixed \
    mcp-neo4j-cypher \
    --db-url bolt://${NEO4J_IP}:7687 \
    --username neo4j --password rhacmgraph --transport sse
```

**Query timeout:**
- Increase timeout in `~/.cursor/mcp.json` to 180
- Simplify complex queries (add LIMIT)

### Query Issues

**No results:**
- Check component names are correct (case-sensitive)
- Use `CONTAINS` for partial matching
- Verify data is loaded: `MATCH (n) RETURN count(n)`

**Slow queries:**
- Add `LIMIT` clause
- Bound variable-length paths (`[*1..3]` not `[*]`)

---

## Additional Resources

### Repository Structure

```
<knowledge-graph-clone>/
├── acm/
│   └── agentic-docs/
│       └── dependency-analysis/
│           ├── knowledge-graph/
│           │   ├── rhacm_architecture_comprehensive_final.cypher  # Main data
│           │   └── sample_queries.cypher                          # 30+ queries
│           ├── mermaid/                                           # Visual diagrams
│           ├── mcp_sample_questions.md                            # 100+ questions
│           ├── rhacm_architecture_implementation_guide.md         # How it was built
│           └── README.md                                          # Overview
└── README.md
```

### Useful Links

- **stolostron/knowledge-graph**: https://github.com/stolostron/knowledge-graph
- **Neo4j Cypher Manual**: https://neo4j.com/docs/cypher-manual/current/
- **MCP Specification**: https://modelcontextprotocol.io/
- **RHACM Documentation**: https://access.redhat.com/documentation/en-us/red_hat_advanced_cluster_management_for_kubernetes

### Access Points

| Resource | URL |
|----------|-----|
| Neo4j Browser | http://localhost:7474 |
| MCP SSE Endpoint | http://localhost:8000/sse |
| Credentials | neo4j / rhacmgraph |

---

## Summary

The Neo4j RHACM Dependency Graph MCP provides:

1. **291 verified components** from the RHACM architecture
2. **287+ semantic relationships** between components
3. **Natural language access** via Cursor AI
4. **Impact analysis** for debugging and testing
5. **Architecture understanding** for QE work

Use it to:
- Understand component dependencies
- Analyze blast radius of failures
- Trace policy and cluster provisioning flows
- Debug RBAC, CNV, MTV, and CCLM issues
- Design better test cases

---

*Last Updated: January 30, 2026*
*Data Source: stolostron/knowledge-graph*
*Components: 291 | Relationships: 419 | Subsystems: 7*
