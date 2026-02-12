# Knowledge Graph MCP - Quick Reference Card

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Neo4j Browser | http://localhost:7474 | neo4j / rhacmgraph |
| MCP SSE | http://localhost:8000/sse | - |

---

## Start/Stop Commands

```bash
# Start (after reboot)
podman machine start && podman start neo4j-rhacm neo4j-mcp

# Stop
podman stop neo4j-rhacm neo4j-mcp

# Status
podman ps --filter name=neo4j

# Logs
podman logs neo4j-rhacm
podman logs neo4j-mcp
```

---

## Natural Language Queries

### Architecture Discovery
- "How many components are in each RHACM subsystem?"
- "List all operators in RHACM"
- "What components are in the Governance subsystem?"

### Dependency Analysis
- "What depends on governance-policy-propagator?"
- "What does Hive Operator manage?"
- "Show me policy propagation flow"

### Impact Analysis
- "If config-policy-controller fails, what breaks?"
- "What are the most connected components?"
- "Show cross-subsystem dependencies"

### Enterprise Features
- "How does Global Hub work?"
- "Show Submariner components"
- "What handles backup and disaster recovery?"

---

## Cypher Quick Reference

### Basic Queries

```cypher
-- Count by subsystem
MATCH (n:RHACMComponent)
RETURN n.subsystem, count(n) ORDER BY count(n) DESC;

-- Find by name
MATCH (n:RHACMComponent)
WHERE n.label CONTAINS 'policy'
RETURN n.label, n.type;

-- List controllers
MATCH (n:RHACMComponent {type: 'Controller'})
RETURN n.label, n.subsystem;
```

### Dependency Queries

```cypher
-- What depends on X
MATCH (s)-[r]->(t {label: 'governance-policy-propagator'})
RETURN s.label, type(r);

-- What X depends on
MATCH (s {label: 'Hive Operator'})-[r]->(t)
RETURN t.label, type(r);

-- Most connected
MATCH (n:RHACMComponent)
OPTIONAL MATCH (n)-[r]->()
RETURN n.label, count(r) as connections
ORDER BY connections DESC LIMIT 10;
```

### Cross-Subsystem

```cypher
-- Integration matrix
MATCH (s:RHACMComponent)-[r]->(t:RHACMComponent)
WHERE s.subsystem <> t.subsystem
RETURN s.subsystem, t.subsystem, count(r)
ORDER BY count(r) DESC;
```

---

## Data Summary

| Subsystem | Components |
|-----------|------------|
| Overview | 110 |
| Governance | 81 |
| Console | 28 |
| Application | 23 |
| Observability | 20 |
| Search | 16 |
| Cluster | 13 |
| **Total** | **291** |

---

## Relationship Types

| Type | Count | Meaning |
|------|-------|---------|
| CONTAINS | 108 | Parent -> Child |
| DEPENDS_ON | 88 | Dependency |
| USES | 33 | Uses functionality |
| MANAGES | 21 | Controller -> CRD |
| INTEGRATES_WITH | 10 | Integration |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to Podman" | `podman machine start` |
| MCP not connecting | Check `podman ps --filter name=neo4j-mcp` |
| MCP can't connect to Neo4j | Use actual container IP: `podman inspect neo4j-rhacm --format '{{.NetworkSettings.IPAddress}}'` |
| Neo4j connection refused | Wait 30s after start |
| Query timeout | Add `LIMIT` clause |

---

## MCP Tools Available

| Tool | Description |
|------|-------------|
| `read_neo4j_cypher` | Execute read-only Cypher queries |
| `write_neo4j_cypher` | Execute write/update queries |
| `get_neo4j_schema` | Get database schema |
