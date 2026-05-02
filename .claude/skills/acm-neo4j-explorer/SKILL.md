---
name: acm-neo4j-explorer
description: Query the RHACM component dependency graph via Neo4j. Use when you need to understand ACM component architecture, subsystem membership, dependency chains, or impact analysis for any ACM-related investigation.
compatibility: "Requires MCP server: neo4j-rhacm (Podman/Docker with neo4j-rhacm container). Optional -- skill degrades gracefully without it."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Neo4j Architecture Explorer

Provides access to the RHACM component knowledge graph via the `neo4j-rhacm` MCP server. The graph contains ACM component nodes with their subsystem membership, descriptions, and inter-component relationships.

## Prerequisites

- Podman or Docker running with the `neo4j-rhacm` container started
- `neo4j-rhacm` MCP server configured and connected

## MCP Tools

| Tool | Purpose |
|------|---------|
| `read_neo4j_cypher(query)` | Execute a read-only Cypher query against the RHACM graph |
| `get_neo4j_schema()` | Get the graph schema (node labels, relationship types, properties) |

## Common Query Patterns

Read `references/cypher-patterns.md` for the full pattern library. Key patterns:

### Find a component and its subsystem
```cypher
MATCH (n:RHACMComponent)
WHERE n.label CONTAINS 'ComponentName'
RETURN n.label, n.description, n.subsystem
```

### What does this component depend on (downstream)?
```cypher
MATCH (src)-[r]->(tgt)
WHERE src.label CONTAINS 'ComponentName'
RETURN src.label, type(r), tgt.label, tgt.subsystem
```

### What depends on this component (upstream impact)?
```cypher
MATCH (dep)-[:DEPENDS_ON]->(t)
WHERE t.label CONTAINS 'ComponentName'
RETURN dep.label, dep.subsystem
```

### All components in a subsystem
```cypher
MATCH (n:RHACMComponent)
WHERE n.subsystem = 'SubsystemName'
RETURN n.label, n.type, n.description
```

### Find relationships between two components
```cypher
MATCH (a)-[r]->(b)
WHERE a.label CONTAINS 'CompA' AND b.label CONTAINS 'CompB'
RETURN a.label, type(r), b.label
```

## Graph Statistics

The graph contains approximately 370 component nodes across 7 subsystems (Cluster, RBAC, Search, Observability, Applications, Governance, Foundation) with 541 relationships (DEPENDS_ON, CONTAINS, MANAGES, USES, INTEGRATES_WITH).

## Rules

- All queries are **read-only** -- the MCP is configured with `--read-only`
- If the MCP is unavailable (Podman not running), note it and proceed without architecture context
- Use graph queries to **supplement**, not replace, domain knowledge from architecture files
