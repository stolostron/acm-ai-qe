# Neo4j Knowledge Graph Reference (neo4j-rhacm)

Read-only Cypher query access to a Neo4j graph database containing 370
ACM components and 541 dependency relationships across 7 subsystems
(Hive, Klusterlet, Addon Framework, HyperShift, Virtualization, MTV,
CCLM, Fine-Grained RBAC).

## Role in the Discovery Chain

```
  Static knowledge doesn't cover it
           |
           v
  Cluster introspection: reverse-engineer dependencies
  from live metadata (owner refs, OLM labels, CSVs,
  env vars, webhooks, ConsolePlugins, APIServices)
           |
           v
  neo4j-rhacm MCP: cross-reference and supplement
  with broader ACM component relationships
           |
           v
  acm-ui MCP: understand each discovered dependency
  (source code, data flow, implementation details)
           |
           v
  Write synthesized understanding to learned/
```

## Example Cypher Queries

```cypher
-- What does component X depend on?
MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent)
WHERE c.label =~ '(?i).*search-api.*'
RETURN dep.label, dep.subsystem

-- What breaks if component X fails? (up to 3 hops)
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

## Availability

The knowledge graph requires a local Neo4j container (`neo4j-rhacm`).
Before querying, check if the container is running:

```bash
# Check if running
podman ps --format '{{.Names}}' | grep neo4j-rhacm

# If not running, start it (container exists from setup)
podman start neo4j-rhacm
```

If the container does not exist at all (never set up), skip graph queries
and rely on the curated knowledge files. Advise the user to run
`bash mcp/setup.sh` from the repo root to create the container.
