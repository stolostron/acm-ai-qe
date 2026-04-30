# Neo4j Cypher Query Patterns for RHACM

## Node Properties

Each `RHACMComponent` node has:
- `label` -- Component name (e.g., "PolicyTemplateDetails", "Search API")
- `description` -- What the component does
- `subsystem` -- Which ACM subsystem it belongs to
- `type` -- Component type (e.g., "UI", "Operator", "CRD", "API")

## Relationship Types

- `DEPENDS_ON` -- Component A requires Component B to function
- `CONTAINS` -- Component A contains/includes Component B
- `MANAGES` -- Component A manages the lifecycle of Component B
- `USES` -- Component A uses Component B's API or data
- `INTEGRATES_WITH` -- Component A integrates with Component B

## Subsystems

7 subsystems: Cluster, RBAC, Search, Observability, Applications, Governance, Foundation

## Query Patterns by Use Case

### Component Discovery
```cypher
-- Find component by name (partial match)
MATCH (n:RHACMComponent) WHERE n.label CONTAINS 'PolicyTemplate' RETURN n.label, n.description, n.subsystem

-- Find component by exact subsystem
MATCH (n:RHACMComponent) WHERE n.subsystem = 'Governance' RETURN n.label, n.type ORDER BY n.label

-- Count components per subsystem
MATCH (n:RHACMComponent) RETURN n.subsystem, count(n) AS count ORDER BY count DESC
```

### Dependency Analysis
```cypher
-- Direct dependencies (what does X need?)
MATCH (src)-[:DEPENDS_ON]->(dep) WHERE src.label CONTAINS 'X' RETURN dep.label, dep.subsystem

-- Reverse dependencies (what breaks if X breaks?)
MATCH (consumer)-[:DEPENDS_ON]->(target) WHERE target.label CONTAINS 'X' RETURN consumer.label, consumer.subsystem

-- Full dependency chain (2 levels deep)
MATCH path = (src)-[:DEPENDS_ON*1..2]->(dep) WHERE src.label CONTAINS 'X' RETURN [n IN nodes(path) | n.label] AS chain
```

### Impact Analysis
```cypher
-- Cross-subsystem impact
MATCH (a)-[r]->(b) WHERE a.subsystem <> b.subsystem RETURN a.subsystem, type(r), b.subsystem, count(*) AS count ORDER BY count DESC

-- Components with most dependents (high-impact if broken)
MATCH (dep)-[:DEPENDS_ON]->(target) RETURN target.label, target.subsystem, count(dep) AS dependent_count ORDER BY dependent_count DESC LIMIT 10
```

### RBAC-Specific
```cypher
-- All RBAC-related components
MATCH (n:RHACMComponent) WHERE n.subsystem = 'RBAC' RETURN n.label, n.description

-- What depends on RBAC
MATCH (dep)-[:DEPENDS_ON]->(rbac) WHERE rbac.subsystem = 'RBAC' RETURN dep.label, dep.subsystem, rbac.label
```
