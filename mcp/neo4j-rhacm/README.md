# Neo4j RHACM Knowledge Graph MCP

RHACM architecture dependency graph in Neo4j, accessible via the Model Context Protocol (MCP).

Part of the [AI Systems Suite](../../README.md). Used by the [Z-Stream Analysis](../../apps/z-stream-analysis/) application for component dependency analysis during pipeline failure investigation.

**Origin:** Based on [stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph/tree/main/acm/agentic-docs/dependency-analysis), forked and extended with additional sample queries, MCP integration documentation, and curated AI interaction questions.

This is a **container-based** MCP server. No custom source code is maintained here — this directory contains setup documentation, sample queries, and reference materials.

---

## Quick Start (Existing Setup)

If containers are already set up, start them after a reboot:

```bash
podman machine start
podman start neo4j-rhacm neo4j-mcp
```

**Services:**
- Neo4j Browser: http://localhost:7474 (neo4j / rhacmgraph)
- MCP SSE Endpoint: http://localhost:8000/sse

---

## New User Setup (First-Time)

### Step 1: Install Podman

```bash
# macOS
brew install podman
podman machine init
podman machine start

# Linux (Fedora/RHEL)
sudo dnf install podman
```

Verify: `podman --version`

### Step 2: Install Node.js (for mcp-remote)

```bash
# macOS
brew install node

# Linux
sudo dnf install nodejs
```

Verify: `node --version` (18+ required), `which npx`

### Step 3: Start the Neo4j database container

```bash
podman run -d \
  --name neo4j-rhacm \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/rhacmgraph \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:2025.01.0
```

Wait ~30 seconds for Neo4j to initialize, then verify:

```bash
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph "RETURN 1"
```

### Step 4: Load the RHACM knowledge graph data

```bash
# Clone the data source
git clone https://github.com/stolostron/knowledge-graph.git /tmp/knowledge-graph

# Copy the Cypher import script into the container
podman cp /tmp/knowledge-graph/acm/agentic-docs/dependency-analysis/knowledge-graph/rhacm_architecture_comprehensive_final.cypher neo4j-rhacm:/tmp/

# Load data
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph -f /tmp/rhacm_architecture_comprehensive_final.cypher

# Verify (should return 291)
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph "MATCH (n) RETURN count(n)"
```

### Step 5: Start the MCP SSE server container

```bash
podman run -d \
  --name neo4j-mcp \
  -p 8000:8000 \
  quay.io/bjoydeep/neo4j-cypher:fixed \
  mcp-neo4j-cypher \
    --db-url bolt://host.containers.internal:7687 \
    --username neo4j \
    --password rhacmgraph \
    --transport sse
```

Verify MCP endpoint:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/sse
# Should return 200
```

### Step 6: Configure MCP in your project

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "neo4j-rhacm": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8000/sse"],
      "timeout": 120
    }
  }
}
```

### Step 7: Test the connection

In Claude Code or Cursor, ask: "Query the knowledge graph: MATCH (n) RETURN count(n)"

Expected result: 291 components.

---

## Data Summary

| Metric | Value |
|--------|-------|
| Total Components | 291 |
| Total Relationships | 419 |
| Subsystems | 7 |
| Data Source | [stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph) |

### Components by Subsystem

| Subsystem | Count |
|-----------|-------|
| Overview | 110 |
| Governance | 81 |
| Console | 28 |
| Application | 23 |
| Observability | 20 |
| Search | 16 |
| Cluster | 13 |

---

## Architecture

```
AI Agent (Claude Code / Cursor)
  └─ MCP protocol (via npx mcp-remote or direct SSE)
       └─ MCP Server container (Port 8000, SSE transport)
            └─ Neo4j Database container (Port 7474/7687, Bolt protocol)
                 └─ RHACM Architecture Graph (291 components, 419 relationships)
```

### Containers

| Container | Image | Port | Purpose |
|-----------|-------|------|---------|
| `neo4j-rhacm` | `neo4j:2025.01.0` | 7474, 7687 | Graph database |
| `neo4j-mcp` | `quay.io/bjoydeep/neo4j-cypher:fixed` | 8000 | MCP SSE server |

### MCP Tools

| Tool | Purpose |
|------|---------|
| `read_neo4j_cypher` | Execute read-only Cypher queries |
| `write_neo4j_cypher` | Execute write Cypher queries |
| `get_neo4j_schema` | Get database schema information |

---

## Documentation Index

| File | Description |
|------|-------------|
| [QUICK-REFERENCE.md](./QUICK-REFERENCE.md) | Quick lookup card for commands and queries |
| [MCP-Architecture-Guide.md](./MCP-Architecture-Guide.md) | MCP protocol architecture and usage patterns |
| [mcp_sample_questions.md](./mcp_sample_questions.md) | 100+ curated questions for AI interaction |
| [sample_queries.cypher](./sample_queries.cypher) | 30+ ready-to-use Cypher analytics queries |

---

## Common Commands

### Start/Stop Services

```bash
# Start
podman machine start
podman start neo4j-rhacm neo4j-mcp

# Stop
podman stop neo4j-rhacm neo4j-mcp

# Check status
podman ps --filter name=neo4j
```

### View Logs

```bash
podman logs neo4j-rhacm
podman logs neo4j-mcp
```

### Test Connection

```bash
# Test Neo4j
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph "MATCH (n) RETURN count(n)"

# Test MCP endpoint
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/sse
```

---

## Example Queries

### Natural Language (via AI agent)

```
"What components are in the Governance subsystem?"
"What depends on governance-policy-propagator?"
"Show me hub-spoke communication patterns"
"If Hive Operator fails, what would be affected?"
```

### Direct Cypher

```cypher
-- List all subsystems with counts
MATCH (n:RHACMComponent)
RETURN n.subsystem as Subsystem, count(n) as Count
ORDER BY Count DESC;

-- Find policy-related components
MATCH (n:RHACMComponent)
WHERE n.label CONTAINS 'policy'
RETURN n.label, n.subsystem, n.type;

-- Cross-subsystem dependencies
MATCH (s:RHACMComponent)-[r]->(t:RHACMComponent)
WHERE s.subsystem <> t.subsystem
RETURN s.subsystem as From, t.subsystem as To, count(r) as Dependencies
ORDER BY Dependencies DESC;
```

---

## Usage in Z-Stream Analysis

During Stage 2 (AI Analysis), the Knowledge Graph is used in:

- **Phase B5**: Component dependency analysis, cascading failure detection
- **Phase C2**: Cascading failure validation
- **Phase E0**: Subsystem context building and feature workflow understanding

The `knowledge_graph_client.py` service provides a Python interface, but actual Cypher queries are executed via MCP tool calls during AI analysis.

---

## Updating Data

```bash
# Pull latest from stolostron/knowledge-graph
cd /path/to/knowledge-graph
git pull

# Clear and reload
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph "MATCH (n) DETACH DELETE n"
podman cp acm/agentic-docs/dependency-analysis/knowledge-graph/rhacm_architecture_comprehensive_final.cypher neo4j-rhacm:/tmp/
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph -f /tmp/rhacm_architecture_comprehensive_final.cypher
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to Podman" | `podman machine start` |
| MCP not connecting | Check `podman ps --filter name=neo4j-mcp` |
| MCP can't reach Neo4j | Use container IP: `podman inspect neo4j-rhacm --format '{{.NetworkSettings.IPAddress}}'` |
| Neo4j connection refused | Wait 30s after container start |
| Query timeout | Add `LIMIT` clause, bound variable-length paths |

See the troubleshooting table above for common fixes.
