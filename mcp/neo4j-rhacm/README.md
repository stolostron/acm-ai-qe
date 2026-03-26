# Knowledge Graph MCP Documentation

This folder contains all documentation related to the Neo4j RHACM Knowledge Graph MCP integration.

## Quick Start

**Services are running on:**
- Neo4j Browser: http://localhost:7474 (neo4j / rhacmgraph)
- MCP SSE Endpoint: http://localhost:8000/sse

**Start services after reboot:**
```bash
podman machine start
podman start neo4j-rhacm neo4j-mcp
```

---

## Documentation Index

### Primary Documentation

| File | Description |
|------|-------------|
| [Neo4j-RHACM-MCP-Complete-Guide.md](./Neo4j-RHACM-MCP-Complete-Guide.md) | **Main Guide** - Complete setup, usage, and troubleshooting (885 lines) |
| [mcp_sample_questions.md](./mcp_sample_questions.md) | 100+ curated questions for AI interaction |
| [sample_queries.cypher](./sample_queries.cypher) | 30+ ready-to-use Cypher analytics queries |

### Reference Documentation

| File | Description |
|------|-------------|
| [MCP-Architecture-Guide.md](./MCP-Architecture-Guide.md) | MCP protocol architecture and usage patterns |
| [Graph-Architecture-Reference.md](./Graph-Architecture-Reference.md) | Neo4j graph data model and query patterns |
| [ACM-Dependency-Graph-Original-Guide.md](./ACM-Dependency-Graph-Original-Guide.md) | Original ACM dependency graph documentation |
| [stolostron-knowledge-graph-README.md](./stolostron-knowledge-graph-README.md) | Original README from stolostron/knowledge-graph repo |

---

## Data Summary

| Metric | Value |
|--------|-------|
| Total Components | 291 |
| Total Relationships | 419 |
| Subsystems | 7 |

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

### Natural Language (in Cursor)

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

## Related Locations

| Resource | Path |
|----------|------|
| Knowledge Graph Repo | Clone from `https://github.com/stolostron/knowledge-graph` |
| MCP Config | `apps/z-stream-analysis/.mcp.json` |

---

## Maintenance

### Update Data from Repository

```bash
cd <path-to-knowledge-graph-clone>
git pull

# Reload data
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph "MATCH (n) DETACH DELETE n"
podman cp acm/agentic-docs/dependency-analysis/knowledge-graph/rhacm_architecture_comprehensive_final.cypher neo4j-rhacm:/tmp/
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph -f /tmp/rhacm_architecture_comprehensive_final.cypher
```

### Recreate Containers

See [Neo4j-RHACM-MCP-Complete-Guide.md](./Neo4j-RHACM-MCP-Complete-Guide.md#recreating-containers) for full instructions.

---

*Last Updated: January 30, 2026*
