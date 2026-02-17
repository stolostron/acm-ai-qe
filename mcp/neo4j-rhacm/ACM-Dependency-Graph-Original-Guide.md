# ACM Dependency Graph & MCP Server Guide

A comprehensive guide to understanding and using the Neo4j-based ACM dependency graph through the Model Context Protocol (MCP) integration in Cursor IDE.

---

## Table of Contents

1. [What This System Is](#what-this-system-is)
2. [What This System Is NOT](#what-this-system-is-not)
3. [Architecture Overview](#architecture-overview)
4. [Strengths](#strengths)
5. [Limitations](#limitations)
6. [How to Access](#how-to-access)
7. [Debugging ACM with the Graph](#debugging-acm-with-the-graph)
8. [Practical Examples](#practical-examples)
9. [Comprehensive Query Examples](#comprehensive-query-examples)
10. [Cypher Query Reference](#cypher-query-reference)
11. [Troubleshooting](#troubleshooting)

---

## What This System Is

### Overview

The ACM Dependency Graph is a **Neo4j property graph database** that maps the architecture and dependencies of Advanced Cluster Management (ACM) and Open Cluster Management (OCM) components. It provides:

- **Visual representation** of ACM architecture
- **Queryable relationships** between components
- **Impact analysis** capabilities
- **Architecture understanding** for debugging and development

### Components

| Component | Description |
|-----------|-------------|
| **Neo4j Database** | Graph database storing nodes (Projects, Controllers, CRDs, Components) and relationships |
| **MCP Server** | Model Context Protocol server exposing Neo4j queries via SSE (Server-Sent Events) |
| **mcp-remote** | NPM package bridging Cursor IDE to the remote MCP server |
| **Cursor Integration** | Configuration allowing AI to query the graph naturally |

### Data Model

The graph contains four main node types:

```
┌─────────────┐     HAS_CONTROLLER      ┌──────────────┐
│   Project   │ ──────────────────────► │  Controller  │
│             │     HAS_COMPONENT       │              │
│  - name     │ ──────────────────────► │  - name      │
│  - layer    │     DEFINES_CRD         │  - type      │
│  - desc     │ ──────────────────────► │  - location  │
└─────────────┘                         └──────────────┘
       │                                       │
       │ USES_CRD                              │ MANAGES/DEPLOYS
       ▼                                       ▼
┌─────────────┐                         ┌──────────────┐
│     CRD     │ ◄─────────────────────  │  Component   │
│             │      ENFORCES           │              │
│  - name     │                         │  - name      │
│  - api_group│                         │  - type      │
│  - purpose  │                         │  - desc      │
└─────────────┘                         └──────────────┘
```

### Graph Statistics (ACM)

| Node Type | Count | Examples |
|-----------|-------|----------|
| Project | 9 | Cluster Lifecycle Management, GRC, Observability |
| Controller | 28 | Hive Operator, Placement Controller, Policy Propagator |
| CRD | 22 | ManagedCluster, ClusterDeployment, Policy |
| Component | 12 | Console UI, Search API, Cloud Providers |

---

## What This System Is NOT

### Critical Clarifications

| It Is NOT | Explanation |
|-----------|-------------|
| **Real-time code analyzer** | Does NOT connect to GitHub or analyze code live |
| **Live cluster monitor** | Does NOT query running ACM clusters |
| **Auto-updating** | Does NOT refresh when stolostron repos change |
| **Complete ACM documentation** | Is a dependency graph, not full docs |
| **Runtime dependency tracker** | Shows architectural dependencies, not runtime calls |

### Data Freshness

```
┌─────────────────────────────────────────────────────────────┐
│  IMPORTANT: Static Data                                      │
│                                                              │
│  The graph was populated by manually analyzing stolostron    │
│  repositories at a point in time. It does NOT:               │
│                                                              │
│  ❌ Auto-update when new repos/components are added          │
│  ❌ Reflect renamed or deleted components automatically      │
│  ❌ Show real-time cluster state                             │
│  ❌ Include every single ACM component                       │
│                                                              │
│  The data represents ACM architecture as of when the         │
│  Cypher load scripts were last executed.                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture Overview

### End-to-End Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              YOUR MACHINE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐      ┌─────────────────┐      ┌─────────────────────────┐ │
│  │   Cursor IDE │ ───► │   mcp-remote    │ ───► │   SSE Connection        │ │
│  │   (AI Agent) │      │   (npx package) │      │   (HTTPS stream)        │ │
│  └──────────────┘      └─────────────────┘      └───────────┬─────────────┘ │
│                                                              │               │
└──────────────────────────────────────────────────────────────┼───────────────┘
                                                               │
                                                               │ Internet
                                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    OpenShift Cluster (regional-poc.dev05)                    │
│                    OCP Version: 4.18.x (Kubernetes 1.31)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────┐      ┌─────────────────────┐                       │
│  │   MCP Server Pod    │ ───► │   Neo4j Database    │                       │
│  │   (neo4j-mcp-sse)   │      │   (Graph Storage)   │                       │
│  │                     │      │                     │                       │
│  │  - Receives queries │      │  - 71 nodes         │                       │
│  │  - Executes Cypher  │      │  - 127 relationships│                       │
│  │  - Returns via SSE  │      │  - Indexed for perf │                       │
│  └─────────────────────┘      └─────────────────────┘                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Population Process

```
┌─────────────────────────────────────────────────────────────┐
│  HOW DATA GETS INTO THE GRAPH (One-Time/Manual Process)     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. STOLOSTRON REPOS (GitHub)                               │
│     ├── stolostron/multiclusterhub-operator                 │
│     ├── stolostron/governance-policy-framework              │
│     ├── stolostron/cluster-lifecycle-api                    │
│     └── 50+ repositories                                    │
│              │                                               │
│              ▼ (Manual Analysis)                             │
│  2. EXTRACT INFORMATION                                      │
│     ├── CRD YAML files → api_group, name, purpose           │
│     ├── Controller code → relationships, responsibilities   │
│     └── Documentation → descriptions, layers                │
│              │                                               │
│              ▼                                               │
│  3. WRITE CYPHER SCRIPTS                                     │
│     CREATE (p:Project {name: "Cluster Lifecycle..."})       │
│     CREATE (c:Controller {name: "Hive Operator"...})        │
│     CREATE (p)-[:HAS_CONTROLLER]->(c)                       │
│              │                                               │
│              ▼                                               │
│  4. LOAD INTO NEO4J (Run once)                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Strengths

### 1. Visual Architecture Understanding

See how ACM components connect without reading thousands of lines of code:

```cypher
-- See entire Cluster Lifecycle architecture
MATCH (p:Project {name: "Cluster Lifecycle Management"})-[r]->(target)
RETURN p, r, target
```

### 2. Impact Analysis

Quickly identify what's affected when changing a component:

```cypher
-- What depends on Placement Controller?
MATCH (source)-[r]->(target {name: "Placement Controller"})
RETURN source.name, type(r)
```

**Result:** Subscription Controller, Policy Propagator, Application Controller all USE Placement Controller.

### 3. Dependency Chain Tracing

Follow multi-hop dependency paths:

```cypher
-- Trace 3-hop dependencies from Cluster Manager Operator
MATCH path = (a {name: "Cluster Manager Operator"})-[*1..3]->(b)
RETURN path
```

### 4. CRD-to-Controller Mapping

Instantly find which controller manages a CRD:

```cypher
-- Who manages the ManagedCluster CRD?
MATCH (c:Controller)-[:MANAGES]->(crd {name: "ManagedCluster"})
RETURN c.name, c.responsibility
```

### 5. Layer-Based Architecture View

Understand ACM's layered architecture:

```cypher
-- Show all components by layer
MATCH (p:Project) RETURN p.name, p.layer, p.description ORDER BY p.layer
```

### 6. Natural Language Queries via Cursor

Ask questions naturally and the AI translates to Cypher:
- "What controllers are in the governance layer?"
- "Show me the observability stack"
- "What deploys the Work Agent?"

---

## Limitations

### 1. Static Data

| Limitation | Impact |
|------------|--------|
| Not real-time | New components won't appear until manually added |
| No auto-refresh | Must manually re-run load scripts to update |
| Point-in-time snapshot | May not reflect latest ACM version |

### 2. Incomplete Coverage

| What's Included | What's Missing |
|-----------------|----------------|
| Major controllers | Every helper function |
| Primary CRDs | Internal CRDs |
| Key relationships | All code-level dependencies |
| Main projects | Utility/helper projects |

### 3. No Runtime Information

The graph shows **architectural** dependencies, not:
- Actual API calls at runtime
- Performance metrics
- Log correlation
- Real cluster state

### 4. Query Complexity

Some complex queries may:
- Time out on large traversals
- Require Cypher knowledge
- Need bounded hops (`[*1..3]` not `[*]`)

---

## How to Access

### Option 1: Cursor IDE (MCP Integration)

**Configuration** (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "neo4j-acm": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://neo4j-mcp-sse-neo4jdb.apps.regional-poc.dev05.red-chesterfield.com/sse"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      },
      "timeout": 120
    },
    "neo4j-ocm": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://neo4j-mcp-neo4j-2.apps.regional-poc.dev05.red-chesterfield.com/sse"
      ],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      },
      "timeout": 120
    }
  }
}
```

**Usage:** Ask the AI naturally:
- "Query the ACM graph to show all controllers"
- "Use neo4j-acm to find what manages ClusterDeployment"

### Option 2: Neo4j Browser (Interactive UI)

| Graph | URL |
|-------|-----|
| **ACM** | https://neo4j-ui-acm-neo4j-acm.apps.regional-poc.dev05.red-chesterfield.com/browser |
| **OCM** | https://neo4j-ui-neo4j-2.apps.regional-poc.dev05.red-chesterfield.com/browser |

**Connection Settings:**
- **URL:** `neo4j-db-acm-neo4j-acm.apps.regional-poc.dev05.red-chesterfield.com:443`
- **Protocol:** `neo4j+s`
- **Username:** `neo4j`
- **Password:** `neoadmin`

### Option 3: Local Port Forward

```bash
# Login to cluster first
oc login https://api.regional-poc.dev05.red-chesterfield.com:6443

# Port forward
kubectl port-forward -n neo4j-acm svc/service-neo4j-acm 7474:7474 7687:7687

# Access locally
open http://localhost:7474
```

---

## Debugging ACM with the Graph

### Scenario 1: Understanding a Bug's Blast Radius

**Problem:** A bug in the Placement Controller is reported. What could be affected?

```cypher
-- Find everything that depends on Placement Controller
MATCH (source)-[r]->(target {name: "Placement Controller"})
RETURN source.name AS Component, type(r) AS Relationship, labels(source)[0] AS Type

-- Result:
-- Subscription Controller → USES
-- Policy Propagator Controller → USES  
-- MultiCluster Observability Operator → USES
-- Application Controller → USES
```

**Insight:** A Placement Controller bug could affect subscriptions, policies, observability, and applications.

---

### Scenario 2: Tracing Cluster Provisioning Flow

**Problem:** Cluster provisioning is failing. What's the flow?

```cypher
-- Trace the provisioning path
MATCH path = (p:Project {name: "Cluster Lifecycle Management"})-[:HAS_CONTROLLER]->(hive {name: "Hive Operator"})-[:DEPLOYS]->(cd)-[:MANAGES|PROVISIONS]->(target)
RETURN path
```

**Flow Discovered:**
```
Cluster Lifecycle Management
    └── HAS_CONTROLLER → Hive Operator
                              └── DEPLOYS → ClusterDeployment Controller
                                                 ├── MANAGES → ClusterDeployment (CRD)
                                                 └── PROVISIONS → Cloud Providers
```

---

### Scenario 3: Finding CRD Ownership

**Problem:** Need to know which controller to debug for a specific CRD.

```cypher
-- Find controller for any CRD
MATCH (c:Controller)-[:MANAGES]->(crd:CRD)
RETURN crd.name AS CRD, crd.api_group AS APIGroup, c.name AS ManagedBy
ORDER BY crd.name
```

---

### Scenario 4: Understanding Hub-Spoke Communication

**Problem:** Debugging communication between hub and managed cluster components.

```cypher
-- Find all communication paths
MATCH (hub:Controller)-[:COMMUNICATES_WITH]->(spoke:Controller)
RETURN hub.name AS HubController, spoke.name AS SpokeController

-- Result:
-- Work Controller → Work Agent
-- Registration Controller → Registration Agent
```

---

### Scenario 5: Policy Propagation Path

**Problem:** Policies aren't being applied to managed clusters.

```cypher
-- Trace policy flow
MATCH path = (p:Project)-[:HAS_CONTROLLER]->(c:Controller)-[r]->(target)
WHERE p.name CONTAINS "Governance"
RETURN path
```

---

### Scenario 6: Finding All Controllers in a Layer

**Problem:** Need to understand all components in observability.

```cypher
MATCH (p:Project {layer: "observability"})-[:HAS_CONTROLLER|HAS_COMPONENT]->(c)
RETURN p.name AS Project, labels(c)[0] AS Type, c.name AS Component
```

---

## Practical Examples

### Basic Queries

| Purpose | Cypher Query |
|---------|--------------|
| Count all nodes | `MATCH (n) RETURN labels(n) AS type, count(n) AS count` |
| List all projects | `MATCH (p:Project) RETURN p.name, p.layer ORDER BY p.layer` |
| List all controllers | `MATCH (c:Controller) RETURN c.name, c.type ORDER BY c.name` |
| List all CRDs | `MATCH (crd:CRD) RETURN crd.name, crd.api_group` |

### Relationship Queries

| Purpose | Cypher Query |
|---------|--------------|
| Controller → CRD mapping | `MATCH (c:Controller)-[:MANAGES]->(crd:CRD) RETURN c.name, crd.name` |
| Deployment hierarchy | `MATCH (a:Controller)-[:DEPLOYS]->(b:Controller) RETURN a.name, b.name` |
| Communication paths | `MATCH (a)-[:COMMUNICATES_WITH]->(b) RETURN a.name, b.name` |
| Project contents | `MATCH (p:Project)-[r]->(c) RETURN p.name, type(r), c.name` |

### Impact Analysis

| Purpose | Cypher Query |
|---------|--------------|
| What depends on X? | `MATCH (s)-[r]->(t {name: "X"}) RETURN s.name, type(r)` |
| What does X affect? | `MATCH (s {name: "X"})-[r]->(t) RETURN t.name, type(r)` |
| 2-hop dependencies | `MATCH path = (a {name: "X"})-[*1..2]->(b) RETURN path` |

### Path Tracing

| Purpose | Cypher Query |
|---------|--------------|
| Shortest path A to B | `MATCH p=shortestPath((a {name:"A"})-[*]-(b {name:"B"})) RETURN p` |
| All paths (bounded) | `MATCH path = (a)-[*1..3]->(b) WHERE a.name="X" RETURN path LIMIT 50` |

---

## Comprehensive Query Examples

This section provides extensive query examples organized by category, complexity, and ACM component. Use these as templates for your own investigations.

---

### Category 1: Graph Discovery & Exploration

#### 1.1 Schema Discovery (Basic)

```cypher
-- Get complete schema: all node types and their counts
MATCH (n)
RETURN labels(n)[0] AS NodeType, count(n) AS Count
ORDER BY Count DESC
```

**Expected Output:**
| NodeType | Count |
|----------|-------|
| Controller | 28 |
| CRD | 22 |
| Component | 12 |
| Project | 9 |

---

#### 1.2 Relationship Types Discovery (Basic)

```cypher
-- List all relationship types in the graph
MATCH ()-[r]->()
RETURN DISTINCT type(r) AS RelationshipType, count(r) AS Count
ORDER BY Count DESC
```

**Expected Output:**
| RelationshipType | Count |
|------------------|-------|
| HAS_CONTROLLER | 28 |
| MANAGES | 22 |
| USES | 18 |
| DEPLOYS | 12 |
| ... | ... |

---

#### 1.3 Node Properties Discovery (Basic)

```cypher
-- See all properties for a specific node type
MATCH (c:Controller)
RETURN c
LIMIT 1
```

**Use Case:** Understand what properties are available before writing targeted queries.

---

#### 1.4 Complete Graph Overview (Basic)

```cypher
-- Visualize the entire graph structure (use LIMIT for large graphs)
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 100
```

**Use Case:** Get a bird's-eye view of the ACM architecture in Neo4j Browser's visualization.

---

#### 1.5 Find Orphan Nodes (Intermediate)

```cypher
-- Find nodes with no relationships (data quality check)
MATCH (n)
WHERE NOT (n)--()
RETURN labels(n)[0] AS Type, n.name AS Name
```

**Use Case:** Identify incomplete data or isolated components.

---

### Category 2: Cluster Lifecycle (CLC) Queries

#### 2.1 CLC Project Overview (Basic)

```cypher
-- Get all components in Cluster Lifecycle Management
MATCH (p:Project {name: "Cluster Lifecycle Management"})-[r]->(target)
RETURN p.name AS Project, type(r) AS Relationship, 
       labels(target)[0] AS TargetType, target.name AS TargetName
ORDER BY TargetType, TargetName
```

---

#### 2.2 Hive Ecosystem (Basic)

```cypher
-- Show Hive Operator and everything it deploys/manages
MATCH (hive {name: "Hive Operator"})-[r]->(target)
RETURN hive.name AS Source, type(r) AS Relationship, target.name AS Target
```

---

#### 2.3 Cluster Provisioning Chain (Intermediate)

```cypher
-- Trace the full cluster provisioning flow
MATCH path = (p:Project)-[:HAS_CONTROLLER]->(c:Controller)-[:DEPLOYS|MANAGES|PROVISIONS*1..3]->(target)
WHERE p.name = "Cluster Lifecycle Management"
RETURN path
```

**Visualization:** Shows the complete path from project through controllers to cloud providers.

---

#### 2.4 ClusterDeployment Dependencies (Intermediate)

```cypher
-- What manages and uses ClusterDeployment CRD?
MATCH (source)-[r]->(crd:CRD {name: "ClusterDeployment"})
RETURN source.name AS Component, type(r) AS Relationship, 
       labels(source)[0] AS ComponentType
UNION
MATCH (crd:CRD {name: "ClusterDeployment"})-[r]->(target)
RETURN target.name AS Component, type(r) AS Relationship,
       labels(target)[0] AS ComponentType
```

---

#### 2.5 ManagedCluster Lifecycle (Intermediate)

```cypher
-- Trace everything related to ManagedCluster CRD
MATCH (n)-[r]-(crd:CRD {name: "ManagedCluster"})
RETURN n.name AS RelatedComponent, type(r) AS Relationship, 
       labels(n)[0] AS ComponentType,
       CASE WHEN startNode(r) = crd THEN "outgoing" ELSE "incoming" END AS Direction
```

---

#### 2.6 Registration Flow (Advanced)

```cypher
-- Trace the complete cluster registration flow
MATCH path = (reg {name: "Registration Controller"})-[*1..3]->(target)
RETURN path
UNION
MATCH path = (source)-[*1..2]->(reg {name: "Registration Controller"})
RETURN path
```

---

#### 2.7 Placement Decision Chain (Advanced)

```cypher
-- How does placement work across ACM?
MATCH (placement {name: "Placement Controller"})<-[r1]-(user)
MATCH (placement)-[r2]->(managed)
RETURN user.name AS UsedBy, type(r1) AS UsageType,
       managed.name AS Manages, type(r2) AS ManagesType
```

---

### Category 3: Governance, Risk & Compliance (GRC) Queries

#### 3.1 GRC Project Components (Basic)

```cypher
-- Get all components in GRC/Governance
MATCH (p:Project)-[r]->(target)
WHERE p.name CONTAINS "Governance" OR p.name CONTAINS "GRC"
RETURN p.name AS Project, type(r) AS Relationship, target.name AS Component
```

---

#### 3.2 Policy Propagation Flow (Basic)

```cypher
-- How do policies flow through the system?
MATCH (p {name: "Policy Propagator Controller"})-[r]->(target)
RETURN p.name AS Source, type(r) AS Relationship, target.name AS Target
```

---

#### 3.3 Policy CRD Ecosystem (Intermediate)

```cypher
-- All components that interact with Policy CRD
MATCH (n)-[r]-(crd:CRD {name: "Policy"})
RETURN n.name AS Component, type(r) AS Relationship,
       labels(n)[0] AS Type,
       CASE WHEN startNode(r) = crd THEN "from Policy" ELSE "to Policy" END AS Direction
```

---

#### 3.4 Configuration Policy Chain (Intermediate)

```cypher
-- Trace ConfigurationPolicy dependencies
MATCH path = (n)-[*1..2]-(crd:CRD)
WHERE crd.name CONTAINS "ConfigurationPolicy" OR crd.name CONTAINS "Policy"
RETURN path
LIMIT 50
```

---

#### 3.5 Compliance Framework Components (Advanced)

```cypher
-- Find all compliance-related controllers and their relationships
MATCH (c:Controller)
WHERE c.name CONTAINS "Policy" 
   OR c.name CONTAINS "Compliance"
   OR c.responsibility CONTAINS "policy"
MATCH (c)-[r]-(related)
RETURN c.name AS Controller, type(r) AS Relationship,
       related.name AS RelatedComponent, labels(related)[0] AS Type
ORDER BY c.name
```

---

### Category 4: Observability Queries

#### 4.1 Observability Stack Overview (Basic)

```cypher
-- Get the entire observability layer
MATCH (p:Project {layer: "observability"})-[r]->(target)
RETURN p.name AS Project, type(r) AS Relationship,
       labels(target)[0] AS Type, target.name AS Component
```

---

#### 4.2 MultiCluster Observability Dependencies (Basic)

```cypher
-- What does MultiCluster Observability Operator depend on?
MATCH (mco {name: "MultiCluster Observability Operator"})-[:USES]->(dependency)
RETURN mco.name AS Operator, dependency.name AS Dependency
```

---

#### 4.3 Search Component Relationships (Intermediate)

```cypher
-- Trace Search API and its dependencies
MATCH (search)-[r]-(related)
WHERE search.name CONTAINS "Search"
RETURN search.name AS SearchComponent, type(r) AS Relationship,
       related.name AS Related, labels(related)[0] AS Type
```

---

#### 4.4 Metrics Collection Path (Intermediate)

```cypher
-- How do metrics flow from spoke to hub?
MATCH path = (spoke:Controller)-[:SENDS_METRICS|COMMUNICATES_WITH*1..3]->(hub:Controller)
WHERE spoke.name CONTAINS "Agent" AND hub.name CONTAINS "Observability"
RETURN path
```

---

### Category 5: Application Lifecycle Queries

#### 5.1 Application Management Components (Basic)

```cypher
-- Get all application-related components
MATCH (n)
WHERE n.name CONTAINS "Application" 
   OR n.name CONTAINS "Subscription"
   OR n.name CONTAINS "Channel"
RETURN labels(n)[0] AS Type, n.name AS Name
ORDER BY Type, Name
```

---

#### 5.2 Subscription Controller Dependencies (Basic)

```cypher
-- What does Subscription Controller use?
MATCH (sub {name: "Subscription Controller"})-[r]->(target)
RETURN sub.name AS Controller, type(r) AS Relationship, target.name AS Target
```

---

#### 5.3 GitOps Integration Points (Intermediate)

```cypher
-- Find GitOps-related components and their connections
MATCH (n)-[r]-(related)
WHERE n.name CONTAINS "GitOps" 
   OR n.name CONTAINS "ArgoCD"
   OR n.name CONTAINS "Channel"
RETURN n.name AS GitOpsComponent, type(r) AS Relationship,
       related.name AS Connected, labels(related)[0] AS Type
```

---

### Category 6: Hub-Spoke Communication Queries

#### 6.1 All Hub-Spoke Communications (Basic)

```cypher
-- Find all communication paths between hub and spoke
MATCH (hub)-[:COMMUNICATES_WITH]->(spoke)
RETURN hub.name AS HubController, spoke.name AS SpokeAgent
```

---

#### 6.2 Work Distribution Flow (Basic)

```cypher
-- How does work get distributed to managed clusters?
MATCH path = (work {name: "Work Controller"})-[*1..2]->(target)
RETURN path
```

---

#### 6.3 Agent Deployment Hierarchy (Intermediate)

```cypher
-- Find all agents and what deploys them
MATCH (deployer)-[:DEPLOYS]->(agent)
WHERE agent.name CONTAINS "Agent"
RETURN deployer.name AS DeployedBy, agent.name AS Agent
```

---

#### 6.4 Complete Hub-to-Spoke Flow (Advanced)

```cypher
-- Trace a complete flow from hub to spoke and back
MATCH (hub:Controller)-[r1]->(spoke:Controller)
WHERE spoke.name CONTAINS "Agent"
OPTIONAL MATCH (spoke)-[r2]->(downstream)
RETURN hub.name AS HubController, 
       type(r1) AS HubToSpoke,
       spoke.name AS SpokeAgent,
       type(r2) AS SpokeToDownstream,
       downstream.name AS Downstream
```

---

### Category 7: CRD Analysis Queries

#### 7.1 All CRDs with API Groups (Basic)

```cypher
-- List all CRDs with their API groups
MATCH (crd:CRD)
RETURN crd.name AS CRD, crd.api_group AS APIGroup, crd.purpose AS Purpose
ORDER BY crd.api_group, crd.name
```

---

#### 7.2 CRD-to-Controller Mapping (Basic)

```cypher
-- Map every CRD to its managing controller
MATCH (c:Controller)-[:MANAGES]->(crd:CRD)
RETURN crd.name AS CRD, crd.api_group AS APIGroup, c.name AS ManagedBy
ORDER BY c.name, crd.name
```

---

#### 7.3 CRDs by API Group (Intermediate)

```cypher
-- Group CRDs by API group with counts
MATCH (crd:CRD)
RETURN crd.api_group AS APIGroup, collect(crd.name) AS CRDs, count(crd) AS Count
ORDER BY Count DESC
```

---

#### 7.4 CRD Usage Analysis (Intermediate)

```cypher
-- Find CRDs and everything that uses them
MATCH (user)-[:USES_CRD|USES]->(crd:CRD)
RETURN crd.name AS CRD, collect(DISTINCT user.name) AS UsedBy, count(user) AS UserCount
ORDER BY UserCount DESC
```

---

#### 7.5 Cross-Project CRD Dependencies (Advanced)

```cypher
-- Find CRDs used across multiple projects
MATCH (p1:Project)-[:HAS_CONTROLLER]->(c1:Controller)-[:MANAGES]->(crd:CRD)
MATCH (p2:Project)-[:HAS_CONTROLLER]->(c2:Controller)-[:USES]->(crd)
WHERE p1 <> p2
RETURN crd.name AS SharedCRD, 
       p1.name AS DefiningProject, 
       c1.name AS ManagingController,
       p2.name AS UsingProject,
       c2.name AS UsingController
```

---

### Category 8: Impact Analysis Queries

#### 8.1 Inbound Dependencies (Basic)

```cypher
-- What depends on a specific component?
MATCH (dependent)-[r]->(target {name: "Placement Controller"})
RETURN dependent.name AS Dependent, type(r) AS DependencyType,
       labels(dependent)[0] AS DependentType
ORDER BY DependentType, Dependent
```

---

#### 8.2 Outbound Dependencies (Basic)

```cypher
-- What does a component depend on?
MATCH (source {name: "Subscription Controller"})-[r]->(dependency)
RETURN dependency.name AS Dependency, type(r) AS DependencyType,
       labels(dependency)[0] AS DependencyType
ORDER BY DependencyType, Dependency
```

---

#### 8.3 Bidirectional Impact (Intermediate)

```cypher
-- Complete dependency picture for a component
MATCH (n {name: "Work Controller"})
OPTIONAL MATCH (n)-[r_out]->(outbound)
OPTIONAL MATCH (inbound)-[r_in]->(n)
RETURN 
    "Outbound" AS Direction, type(r_out) AS Relationship, outbound.name AS Component
UNION
MATCH (n {name: "Work Controller"})
OPTIONAL MATCH (inbound)-[r_in]->(n)
RETURN 
    "Inbound" AS Direction, type(r_in) AS Relationship, inbound.name AS Component
```

---

#### 8.4 Multi-Hop Impact Radius (Intermediate)

```cypher
-- Find all components within 2 hops of a change
MATCH path = (source {name: "Hive Operator"})-[*1..2]-(affected)
WHERE source <> affected
RETURN DISTINCT affected.name AS AffectedComponent,
       labels(affected)[0] AS Type,
       length(path) AS HopsAway
ORDER BY HopsAway, Type, AffectedComponent
```

---

#### 8.5 Critical Path Analysis (Advanced)

```cypher
-- Find components that appear in many dependency chains
MATCH path = (a)-[*1..3]->(b)
WITH nodes(path) AS nodeList
UNWIND nodeList AS n
WITH n
WHERE n:Controller OR n:Component
RETURN n.name AS Component, count(*) AS AppearanceCount
ORDER BY AppearanceCount DESC
LIMIT 10
```

**Use Case:** Identify the most critical components in the architecture.

---

#### 8.6 Breaking Change Impact (Advanced)

```cypher
-- What would break if a CRD schema changed?
MATCH (crd:CRD {name: "ManagedCluster"})<-[r]-(user)
MATCH (crd)-[r2]->(downstream)
RETURN 
    "Direct User" AS ImpactLevel, user.name AS Component, type(r) AS Usage
UNION
MATCH (crd:CRD {name: "ManagedCluster"})<-[:MANAGES]-(controller)
MATCH (controller)<-[r]-(upstream)
RETURN 
    "Indirect Impact" AS ImpactLevel, upstream.name AS Component, type(r) AS Usage
```

---

### Category 9: Path Finding Queries

#### 9.1 Shortest Path Between Components (Basic)

```cypher
-- Find shortest path between two components
MATCH p = shortestPath(
    (a {name: "Hive Operator"})-[*]-(b {name: "ManagedCluster"})
)
RETURN p
```

---

#### 9.2 All Paths Between Components (Intermediate)

```cypher
-- Find all paths (bounded) between two components
MATCH path = (a {name: "Cluster Manager Operator"})-[*1..4]->(b {name: "Work Agent"})
RETURN path
LIMIT 20
```

---

#### 9.3 Path Through Specific Relationship (Intermediate)

```cypher
-- Find paths that go through DEPLOYS relationships
MATCH path = (start)-[:DEPLOYS*1..3]->(end)
RETURN start.name AS Start, 
       [n IN nodes(path) | n.name] AS PathNodes,
       end.name AS End
LIMIT 20
```

---

#### 9.4 Relationship Chain Types (Intermediate)

```cypher
-- Show relationship types in paths
MATCH path = (a {name: "Policy Propagator Controller"})-[*1..3]->(b)
RETURN a.name AS Start,
       [r IN relationships(path) | type(r)] AS RelationshipChain,
       b.name AS End
LIMIT 20
```

---

#### 9.5 Cross-Layer Paths (Advanced)

```cypher
-- Find paths that cross architectural layers
MATCH (p1:Project)-[:HAS_CONTROLLER]->(c1:Controller)-[r*1..2]->(c2:Controller)<-[:HAS_CONTROLLER]-(p2:Project)
WHERE p1.layer <> p2.layer
RETURN p1.name AS SourceProject, p1.layer AS SourceLayer,
       c1.name AS SourceController,
       [rel IN r | type(rel)] AS PathTypes,
       c2.name AS TargetController,
       p2.name AS TargetProject, p2.layer AS TargetLayer
LIMIT 30
```

---

### Category 10: Aggregation & Statistics Queries

#### 10.1 Controller Statistics (Basic)

```cypher
-- Count relationships per controller
MATCH (c:Controller)-[r]-()
RETURN c.name AS Controller, count(r) AS RelationshipCount
ORDER BY RelationshipCount DESC
```

---

#### 10.2 Project Size Comparison (Basic)

```cypher
-- Compare projects by number of components
MATCH (p:Project)-[r]->(component)
RETURN p.name AS Project, p.layer AS Layer,
       count(component) AS ComponentCount
ORDER BY ComponentCount DESC
```

---

#### 10.3 Relationship Distribution (Intermediate)

```cypher
-- Analyze relationship type distribution
MATCH ()-[r]->()
WITH type(r) AS relType, count(r) AS count
RETURN relType AS RelationshipType, count AS Count,
       round(100.0 * count / sum(count) OVER (), 2) AS Percentage
ORDER BY Count DESC
```

---

#### 10.4 Component Connectivity Score (Intermediate)

```cypher
-- Rank components by connectivity (in + out relationships)
MATCH (n)
WHERE n:Controller OR n:Component
OPTIONAL MATCH (n)-[r_out]->()
OPTIONAL MATCH ()-[r_in]->(n)
WITH n, count(DISTINCT r_out) AS outgoing, count(DISTINCT r_in) AS incoming
RETURN n.name AS Component, 
       labels(n)[0] AS Type,
       outgoing AS OutgoingRelationships,
       incoming AS IncomingRelationships,
       outgoing + incoming AS TotalConnections
ORDER BY TotalConnections DESC
LIMIT 15
```

---

#### 10.5 CRD Complexity Analysis (Advanced)

```cypher
-- Analyze CRD complexity by usage
MATCH (crd:CRD)
OPTIONAL MATCH (manager:Controller)-[:MANAGES]->(crd)
OPTIONAL MATCH (user)-[:USES|USES_CRD]->(crd)
WITH crd, manager, collect(DISTINCT user.name) AS users
RETURN crd.name AS CRD,
       crd.api_group AS APIGroup,
       manager.name AS ManagedBy,
       size(users) AS UserCount,
       users AS UsedBy
ORDER BY UserCount DESC
```

---

### Category 11: Debugging Scenario Queries

#### 11.1 Why Can't I Create a Cluster? (Basic)

```cypher
-- Trace cluster creation path
MATCH path = (p:Project {name: "Cluster Lifecycle Management"})
    -[:HAS_CONTROLLER]->(hive {name: "Hive Operator"})
    -[:DEPLOYS|MANAGES*1..2]->(downstream)
RETURN path
```

---

#### 11.2 Why Aren't Policies Applying? (Intermediate)

```cypher
-- Trace policy application flow
MATCH path = (grc:Project)-[:HAS_CONTROLLER]->(prop {name: "Policy Propagator Controller"})
    -[*1..3]->(target)
WHERE grc.name CONTAINS "Governance"
RETURN path
```

---

#### 11.3 Why Is Observability Not Working? (Intermediate)

```cypher
-- Trace observability data flow
MATCH (obs:Project {layer: "observability"})-[:HAS_CONTROLLER|HAS_COMPONENT]->(comp)
MATCH (comp)-[r]->(downstream)
RETURN obs.name AS Project, comp.name AS Component,
       type(r) AS Relationship, downstream.name AS Downstream
```

---

#### 11.4 What Controllers Share This CRD? (Intermediate)

```cypher
-- Find potential conflicts/coordination needs
MATCH (c1:Controller)-[r1]->(crd:CRD)<-[r2]-(c2:Controller)
WHERE c1 <> c2
RETURN crd.name AS CRD,
       c1.name AS Controller1, type(r1) AS Relation1,
       c2.name AS Controller2, type(r2) AS Relation2
```

---

#### 11.5 Complete Stack Trace for a Component (Advanced)

```cypher
-- Get complete context for debugging a specific component
MATCH (target {name: "Work Agent"})
-- Get project
OPTIONAL MATCH (p:Project)-[:HAS_CONTROLLER|HAS_COMPONENT*1..2]->(target)
-- Get deployer
OPTIONAL MATCH (deployer)-[:DEPLOYS]->(target)
-- Get what it uses
OPTIONAL MATCH (target)-[:USES|MANAGES]->(uses)
-- Get what uses it
OPTIONAL MATCH (user)-[:USES]->(target)
-- Get communications
OPTIONAL MATCH (target)-[:COMMUNICATES_WITH]-(comm)
RETURN 
    target.name AS Component,
    p.name AS Project,
    p.layer AS Layer,
    deployer.name AS DeployedBy,
    collect(DISTINCT uses.name) AS Uses,
    collect(DISTINCT user.name) AS UsedBy,
    collect(DISTINCT comm.name) AS CommunicatesWith
```

---

### Category 12: Data Validation Queries

#### 12.1 Find Duplicate Nodes (Basic)

```cypher
-- Check for duplicate node names
MATCH (n)
WITH n.name AS name, collect(n) AS nodes, count(n) AS count
WHERE count > 1
RETURN name, count, [node IN nodes | labels(node)[0]] AS Types
```

---

#### 12.2 Controllers Without Projects (Basic)

```cypher
-- Find controllers not associated with any project
MATCH (c:Controller)
WHERE NOT ((:Project)-[:HAS_CONTROLLER]->(c))
RETURN c.name AS OrphanController
```

---

#### 12.3 CRDs Without Managers (Basic)

```cypher
-- Find CRDs with no managing controller
MATCH (crd:CRD)
WHERE NOT ((:Controller)-[:MANAGES]->(crd))
RETURN crd.name AS UnmanagedCRD, crd.api_group AS APIGroup
```

---

#### 12.4 Relationship Consistency Check (Intermediate)

```cypher
-- Verify expected relationships exist
MATCH (p:Project)
OPTIONAL MATCH (p)-[:HAS_CONTROLLER]->(c:Controller)
WITH p, count(c) AS controllerCount
WHERE controllerCount = 0
RETURN p.name AS ProjectWithNoControllers
```

---

### Category 13: Advanced Pattern Matching

#### 13.1 Find Circular Dependencies (Advanced)

```cypher
-- Detect circular dependencies (potential issues)
MATCH path = (a)-[*2..4]->(a)
WHERE a:Controller OR a:Component
RETURN DISTINCT [n IN nodes(path) | n.name] AS CircularPath
LIMIT 10
```

---

#### 13.2 Components With Only Incoming Dependencies (Intermediate)

```cypher
-- Find "leaf" components (only consumed, don't consume others)
MATCH (n)
WHERE (n:Controller OR n:Component)
  AND NOT (n)-->()
  AND ()-->(n)
RETURN n.name AS LeafComponent, labels(n)[0] AS Type
```

---

#### 13.3 Components With Only Outgoing Dependencies (Intermediate)

```cypher
-- Find "root" components (only provide, don't consume)
MATCH (n)
WHERE (n:Controller OR n:Component)
  AND (n)-->()
  AND NOT ()-->(n)
RETURN n.name AS RootComponent, labels(n)[0] AS Type
```

---

#### 13.4 Find All Deployment Chains (Advanced)

```cypher
-- Trace complete deployment hierarchies
MATCH path = (root)-[:DEPLOYS*]->(leaf)
WHERE NOT ((:Controller)-[:DEPLOYS]->(root))
  AND NOT ((leaf)-[:DEPLOYS]->(:Controller))
RETURN root.name AS RootDeployer,
       [n IN nodes(path) | n.name] AS DeploymentChain,
       leaf.name AS FinalDeployment
```

---

#### 13.5 Multi-Project Communication Patterns (Advanced)

```cypher
-- Find how projects communicate with each other
MATCH (p1:Project)-[:HAS_CONTROLLER]->(c1:Controller)
      -[:COMMUNICATES_WITH|USES*1..2]->
      (c2:Controller)<-[:HAS_CONTROLLER]-(p2:Project)
WHERE p1 <> p2
RETURN DISTINCT p1.name AS SourceProject, 
       c1.name AS SourceController,
       c2.name AS TargetController,
       p2.name AS TargetProject
ORDER BY p1.name, p2.name
```

---

### Category 14: Feature-Specific Traces

#### 14.1 AWS Credentials Flow (Intermediate)

```cypher
-- Trace how AWS credentials are managed
MATCH (n)
WHERE n.name CONTAINS "AWS" 
   OR n.name CONTAINS "Cloud"
   OR n.name CONTAINS "Credential"
MATCH (n)-[r]-(related)
RETURN n.name AS Component, type(r) AS Relationship,
       related.name AS Related, labels(related)[0] AS Type
```

---

#### 14.2 Cluster Import Process (Intermediate)

```cypher
-- Trace the cluster import/join flow
MATCH (reg {name: "Registration Controller"})-[r1]->(target)
MATCH (agent)-[r2]->(reg)
RETURN "Registration Controller" AS Step,
       collect(DISTINCT target.name) AS DeploysTo,
       collect(DISTINCT agent.name) AS ReceivesFrom
```

---

#### 14.3 Addon Deployment Flow (Intermediate)

```cypher
-- How are addons deployed to managed clusters?
MATCH (n)
WHERE n.name CONTAINS "Addon" OR n.name CONTAINS "Add-on"
MATCH (n)-[r]-(related)
RETURN n.name AS AddonComponent, type(r) AS Relationship,
       related.name AS Related, labels(related)[0] AS Type
```

---

#### 14.4 RBAC Integration Points (Intermediate)

```cypher
-- Find RBAC-related components
MATCH (n)
WHERE n.name CONTAINS "RBAC"
   OR n.name CONTAINS "Role"
   OR n.name CONTAINS "Permission"
   OR n.responsibility CONTAINS "RBAC"
   OR n.responsibility CONTAINS "authorization"
RETURN labels(n)[0] AS Type, n.name AS Component, 
       n.responsibility AS Responsibility
```

---

#### 14.5 Console UI Dependencies (Intermediate)

```cypher
-- What does the Console UI depend on?
MATCH (console)
WHERE console.name CONTAINS "Console" OR console.name CONTAINS "UI"
MATCH (console)-[r]->(dependency)
RETURN console.name AS UI, type(r) AS Relationship,
       dependency.name AS Dependency, labels(dependency)[0] AS Type
```

---

### Category 15: Cursor AI Natural Language Examples

When using the MCP integration in Cursor, you can ask questions naturally. Here are examples mapped to their Cypher equivalents:

| Natural Language Question | Translated Cypher |
|--------------------------|-------------------|
| "What is the ACM graph schema?" | `MATCH (n) RETURN labels(n), count(n)` |
| "Show me all controllers" | `MATCH (c:Controller) RETURN c.name` |
| "What depends on Hive?" | `MATCH (s)-[r]->(t {name: "Hive Operator"}) RETURN s.name, type(r)` |
| "How does policy propagation work?" | `MATCH path = (p:Project)-[:HAS_CONTROLLER]->(c)-[*1..2]->(t) WHERE p.name CONTAINS "Governance" RETURN path` |
| "What CRDs are in cluster lifecycle?" | `MATCH (p:Project {name: "Cluster Lifecycle Management"})-[*1..2]->(crd:CRD) RETURN crd.name` |
| "Find communication paths" | `MATCH (a)-[:COMMUNICATES_WITH]->(b) RETURN a.name, b.name` |
| "What would break if I changed ManagedCluster?" | `MATCH (n)-[r]->(crd:CRD {name: "ManagedCluster"}) RETURN n.name, type(r)` |
| "Show the observability stack" | `MATCH (p:Project {layer: "observability"})-[r]->(c) RETURN p, r, c` |
| "Trace cluster provisioning" | `MATCH path = ({name: "Hive Operator"})-[*1..3]->(target) RETURN path` |
| "Which controllers manage CRDs?" | `MATCH (c:Controller)-[:MANAGES]->(crd:CRD) RETURN c.name, crd.name` |

---

### Query Complexity Reference

| Complexity | Characteristics | Performance |
|------------|-----------------|-------------|
| **Basic** | Single MATCH, direct properties, simple WHERE | < 100ms |
| **Intermediate** | Multiple MATCHes, 1-2 hop paths, aggregations | 100-500ms |
| **Advanced** | Variable-length paths, UNION, complex patterns | 500ms-2s |
| **Heavy** | Unbounded paths, full graph scans | > 2s (use LIMIT) |

---

### Query Best Practices

1. **Always bound variable-length paths**: Use `[*1..3]` not `[*]`
2. **Use LIMIT on exploratory queries**: Start with `LIMIT 50`
3. **Anchor on indexed properties**: `name` is typically indexed
4. **Use DISTINCT for deduplication**: Especially in path queries
5. **Profile slow queries**: Use `PROFILE` prefix to analyze
6. **Start specific, broaden if needed**: Better than starting broad

---

## Cypher Query Reference

### Syntax Basics

```cypher
-- Match nodes
MATCH (n:Label)                    -- Match by label
MATCH (n {name: "value"})         -- Match by property
MATCH (n:Label {name: "value"})   -- Match by both

-- Match relationships
MATCH (a)-[r]->(b)                -- Any relationship
MATCH (a)-[:TYPE]->(b)            -- Specific type
MATCH (a)-[r:TYPE1|TYPE2]->(b)    -- Multiple types
MATCH (a)-[*1..3]->(b)            -- Variable length (1-3 hops)

-- Return
RETURN n                          -- Return node
RETURN n.name, n.type             -- Return properties
RETURN n, r, m                    -- Return multiple
RETURN labels(n), type(r)         -- Return metadata

-- Filtering
WHERE n.name CONTAINS "Policy"    -- String contains
WHERE n.name =~ ".*Controller.*"  -- Regex
WHERE n.layer IN ["governance", "observability"]

-- Ordering and limiting
ORDER BY n.name
LIMIT 50
```

### Common Patterns

```cypher
-- Find by partial name
MATCH (n) WHERE toLower(n.name) CONTAINS "policy" RETURN n

-- Get relationship types
MATCH ()-[r]->() RETURN DISTINCT type(r)

-- Get node labels
MATCH (n) RETURN DISTINCT labels(n)

-- Count by type
MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count ORDER BY count DESC
```

---

## Troubleshooting

### MCP Connection Issues

| Issue | Solution |
|-------|----------|
| "Error - Show Output" in Cursor | Restart Cursor, check network connectivity |
| SSL certificate errors | Ensure `NODE_TLS_REJECT_UNAUTHORIZED=0` in env |
| Timeout errors | Increase timeout in mcp.json, simplify query |
| No tools showing | Reload Cursor window after config change |

### Neo4j Browser Issues

| Issue | Solution |
|-------|----------|
| "Cannot connect to db" | Change URL format, use `neo4j+s` protocol |
| Authentication failed | Use `neo4j` / `neoadmin` credentials |
| SSL warning | Accept certificate by visiting DB URL directly first |

### Query Issues

| Issue | Solution |
|-------|----------|
| Query timeout | Add `LIMIT`, bound variable-length paths |
| No results | Check node/property names (case-sensitive) |
| Slow queries | Use indexed properties (`name`, `id`) as anchors |

---

## Related Documentation

| Document | Location |
|----------|----------|
| Setup Guide | `/documentation/troubleshooting/neo4j-dependency-graph-setup.md` |
| Query Examples | `/documentation/troubleshooting/neo4j-cypher-query-examples.md` |
| Browser Access | `/documentation/troubleshooting/neo4j-browser-access-guide.md` |
| Troubleshooting | `/documentation/troubleshooting/neo4j-troubleshooting-guide.md` |
| Graph Architecture | `/downloads/dependency-graph/docs/GRAPH-ARCHITECTURE.md` |
| MCP Guide | `/downloads/dependency-graph/docs/MCP-GUIDE.md` |

---

## Quick Reference Card

### Cursor MCP Commands

```
"Show me the ACM graph schema"
"What controllers are in the cluster lifecycle project?"
"Run this Cypher on neo4j-acm: MATCH (n) RETURN count(n)"
"What depends on the Work Controller?"
"Trace the path from Hive Operator to ClusterDeployment"
```

### Essential Cypher Queries

```cypher
-- Overview
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 100

-- Projects
MATCH (p:Project) RETURN p.name, p.layer

-- Controllers
MATCH (c:Controller) RETURN c.name, c.responsibility

-- Impact analysis
MATCH (s)-[r]->(t {name: "TARGET"}) RETURN s.name, type(r)

-- CRD ownership
MATCH (c:Controller)-[:MANAGES]->(crd:CRD) RETURN c.name, crd.name
```

### Access Points

| Resource | URL/Path |
|----------|----------|
| ACM Browser | https://neo4j-ui-acm-neo4j-acm.apps.regional-poc.dev05.red-chesterfield.com/browser |
| OCM Browser | https://neo4j-ui-neo4j-2.apps.regional-poc.dev05.red-chesterfield.com/browser |
| Credentials | `neo4j` / `neoadmin` |

---

*Last Updated: January 2026*
*Graph Data Source: stolostron repositories (manual analysis)*
*Maintainer: Joydeep's team*
