// RHACM Architecture Graph - Sample Analytics Queries
// 
// Prerequisites: Import rhacm_architecture_comprehensive_final.cypher first
// Usage: Copy and paste these queries into Neo4j Browser or cypher-shell
//
// These queries help analyze the RHACM dependency graph to understand:
// - Component distribution and connectivity patterns
// - Cross-subsystem dependencies and integration points
// - Hub-spoke communication flows
// - Critical components and architectural bottlenecks

// =============================================================================
// BASIC ANALYSIS QUERIES
// =============================================================================

// 1. Component Count by Subsystem
// Shows the distribution of components across RHACM subsystems
MATCH (n:RHACMComponent) 
RETURN n.subsystem as Subsystem, count(n) as ComponentCount 
ORDER BY ComponentCount DESC;

// 2. Total Graph Statistics
// Overall metrics for the complete architecture
MATCH (n:RHACMComponent)
OPTIONAL MATCH ()-[r]->()
RETURN count(DISTINCT n) as TotalComponents,
       count(DISTINCT r) as TotalRelationships,
       count(DISTINCT n.subsystem) as TotalSubsystems;

// 3. Component Types Distribution
// Breakdown by component types (Operator, Controller, etc.)
MATCH (n:RHACMComponent)
RETURN n.type as ComponentType, count(n) as Count
ORDER BY Count DESC;

// =============================================================================
// CONNECTIVITY ANALYSIS
// =============================================================================

// 4. Most Connected Components (Hub Analysis)
// Identifies the most critical components by connection count
MATCH (n:RHACMComponent)
OPTIONAL MATCH (n)-[r_out]->()
OPTIONAL MATCH ()-[r_in]->(n)
RETURN n.label as Component, 
       n.subsystem as Subsystem,
       count(DISTINCT r_out) as OutgoingDependencies,
       count(DISTINCT r_in) as IncomingDependencies,
       count(DISTINCT r_out) + count(DISTINCT r_in) as TotalConnections
ORDER BY TotalConnections DESC LIMIT 20;

// 5. Least Connected Components
// Potential orphaned or peripheral components
MATCH (n:RHACMComponent)
OPTIONAL MATCH (n)-[r_out]->()
OPTIONAL MATCH ()-[r_in]->(n)
WITH n, count(DISTINCT r_out) + count(DISTINCT r_in) as connections
WHERE connections <= 2
RETURN n.label as Component, n.subsystem as Subsystem, connections
ORDER BY connections ASC, n.subsystem;

// 6. Relationship Types Analysis
// Understanding different types of component relationships
MATCH ()-[r]->()
RETURN type(r) as RelationshipType, count(r) as Count
ORDER BY Count DESC;

// =============================================================================
// CROSS-SUBSYSTEM ANALYSIS
// =============================================================================

// 7. Cross-Subsystem Dependencies
// Shows integration patterns between major subsystems
MATCH (source:RHACMComponent)-[r]->(target:RHACMComponent)
WHERE source.subsystem <> target.subsystem
RETURN source.subsystem as SourceSubsystem, 
       target.subsystem as TargetSubsystem,
       type(r) as RelationshipType,
       count(r) as Dependencies
ORDER BY Dependencies DESC;

// 8. Subsystem Integration Matrix
// Complete view of how subsystems interact
MATCH (source:RHACMComponent)-[r]->(target:RHACMComponent)
WHERE source.subsystem <> target.subsystem
WITH source.subsystem as Source, target.subsystem as Target, count(r) as Deps
RETURN Source, 
       collect(Target + ": " + toString(Deps)) as IntegratesWithSubsystems
ORDER BY Source;

// 9. Most Integrated Subsystems
// Which subsystems have the most external connections
MATCH (source:RHACMComponent)-[r]->(target:RHACMComponent)
WHERE source.subsystem <> target.subsystem
RETURN source.subsystem as Subsystem,
       count(DISTINCT target.subsystem) as ConnectedSubsystems,
       count(r) as TotalCrossConnections
ORDER BY TotalCrossConnections DESC;

// =============================================================================
// HUB-SPOKE ARCHITECTURE ANALYSIS
// =============================================================================

// 10. Hub-Spoke Communication Patterns
// Cross-cluster deployment and communication flows
MATCH (hub:RHACMComponent)-[r {cross_cluster: true}]->(spoke:RHACMComponent)
RETURN hub.label as HubComponent, 
       hub.subsystem as HubSubsystem,
       type(r) as CommunicationType,
       collect(DISTINCT spoke.label)[0..5] as SpokeComponents,
       count(spoke) as SpokeCount
ORDER BY SpokeCount DESC;

// 11. Cross-Cluster Relationship Analysis
// Understanding hub-spoke deployment patterns
MATCH ()-[r {cross_cluster: true}]->()
RETURN type(r) as CrossClusterRelationType, count(r) as Count
ORDER BY Count DESC;

// 12. Hub Cluster Components
// Components that manage spoke clusters
MATCH (hub:RHACMComponent)-[r {cross_cluster: true}]->()
RETURN DISTINCT hub.label as HubComponent, 
       hub.subsystem as Subsystem,
       hub.type as ComponentType
ORDER BY hub.subsystem, hub.label;

// =============================================================================
// CRITICAL PATH ANALYSIS
// =============================================================================

// 13. Root Components (No Dependencies)
// Foundation components that other components depend on
MATCH (n:RHACMComponent)
WHERE NOT ()-[:DEPENDS_ON]->(n)
RETURN n.subsystem as Subsystem, 
       n.label as RootComponent, 
       n.type as Type
ORDER BY Subsystem, RootComponent;

// 14. Leaf Components (No Dependents)
// End-point components that nothing depends on
MATCH (n:RHACMComponent)
WHERE NOT (n)-[:DEPENDS_ON]->()
RETURN n.subsystem as Subsystem,
       n.label as LeafComponent,
       n.type as Type
ORDER BY Subsystem, LeafComponent;

// 15. Dependency Chain Length
// Longest dependency paths in the architecture
MATCH path = (start:RHACMComponent)-[:DEPENDS_ON*]->(end:RHACMComponent)
WHERE NOT ()-[:DEPENDS_ON]->(start) AND NOT (end)-[:DEPENDS_ON]->()
RETURN start.label as StartComponent,
       end.label as EndComponent,
       length(path) as ChainLength,
       [node in nodes(path) | node.label] as DependencyChain
ORDER BY ChainLength DESC LIMIT 10;

// =============================================================================
// SUBSYSTEM-SPECIFIC ANALYSIS
// =============================================================================

// 16. Governance Subsystem Deep Dive
// Internal structure of the largest subsystem
MATCH (n:RHACMComponent {subsystem: 'Governance'})
OPTIONAL MATCH (n)-[r]->(m:RHACMComponent {subsystem: 'Governance'})
RETURN n.label as Component,
       n.type as Type,
       count(r) as InternalConnections,
       collect(DISTINCT type(r)) as RelationshipTypes
ORDER BY InternalConnections DESC;

// 17. Application Lifecycle Models
// Understanding the three application deployment patterns
MATCH (n:RHACMComponent {subsystem: 'Application'})
RETURN n.label as Component,
       n.type as Type,
       n.description as Description
ORDER BY n.label;

// 18. Observability Data Flow
// How metrics and monitoring data flows through the system
MATCH (obs:RHACMComponent {subsystem: 'Observability'})-[r]->(target)
RETURN obs.label as ObservabilityComponent,
       type(r) as FlowType,
       target.label as Target,
       target.subsystem as TargetSubsystem
ORDER BY obs.label;

// =============================================================================
// ENTERPRISE FEATURES ANALYSIS
// =============================================================================

// 19. Addon Components
// All RHACM addons and their deployment patterns
MATCH (n:RHACMComponent)
WHERE n.label CONTAINS "Addon" OR n.label CONTAINS "addon"
RETURN n.label as AddonComponent,
       n.subsystem as Subsystem,
       n.type as Type
ORDER BY n.subsystem, n.label;

// 20. Global Hub Federation
// Multi-hub management components
MATCH (n:RHACMComponent)
WHERE n.label CONTAINS "Global Hub" OR n.label CONTAINS "global-hub"
OPTIONAL MATCH (n)-[r]->(m)
RETURN n.label as GlobalHubComponent,
       count(r) as Connections,
       collect(DISTINCT m.label)[0..5] as ConnectedComponents
ORDER BY n.label;

// 21. Submariner Network Components
// Cross-cluster networking architecture
MATCH (n:RHACMComponent)
WHERE n.label CONTAINS "Submariner" OR n.label CONTAINS "submariner"
RETURN n.label as SubmarinerComponent,
       n.type as Type,
       n.description as Description
ORDER BY n.label;

// =============================================================================
// OPERATIONAL QUERIES
// =============================================================================

// 22. Operator Components
// All operators in the RHACM ecosystem
MATCH (n:RHACMComponent)
WHERE n.type = "Operator" OR n.label CONTAINS "operator"
RETURN n.label as OperatorName,
       n.subsystem as Subsystem,
       n.description as Description
ORDER BY n.subsystem, n.label;

// 23. Controller Components
// All controllers and their management responsibilities
MATCH (n:RHACMComponent)
WHERE n.type = "Controller" OR n.label CONTAINS "controller"
RETURN n.label as ControllerName,
       n.subsystem as Subsystem,
       n.type as Type
ORDER BY n.subsystem, n.label;

// 24. API Components
// All API endpoints and services
MATCH (n:RHACMComponent)
WHERE n.type = "API" OR n.label CONTAINS "API" OR n.label CONTAINS "api"
RETURN n.label as APIComponent,
       n.subsystem as Subsystem,
       n.description as Description
ORDER BY n.subsystem, n.label;

// =============================================================================
// TROUBLESHOOTING QUERIES
// =============================================================================

// 25. Find Component by Name Pattern
// Useful for locating specific components
// Usage: Replace 'search_pattern' with your search term
MATCH (n:RHACMComponent)
WHERE n.label CONTAINS 'policy' // Change 'policy' to your search term
RETURN n.label as Component,
       n.subsystem as Subsystem,
       n.type as Type,
       n.description as Description
ORDER BY n.subsystem, n.label;

// 26. Component Neighborhood
// Find all directly connected components to a specific component
// Usage: Replace 'Component Name' with the actual component you want to explore
MATCH (center:RHACMComponent {label: 'Red Hat Advanced Cluster Management'})
OPTIONAL MATCH (center)-[r_out]->(connected_out)
OPTIONAL MATCH (connected_in)-[r_in]->(center)
RETURN center.label as CenterComponent,
       'OUTGOING' as Direction,
       type(r_out) as RelationType,
       connected_out.label as ConnectedComponent,
       connected_out.subsystem as ConnectedSubsystem
UNION
MATCH (center:RHACMComponent {label: 'Red Hat Advanced Cluster Management'})
OPTIONAL MATCH (connected_in)-[r_in]->(center)
RETURN center.label as CenterComponent,
       'INCOMING' as Direction,
       type(r_in) as RelationType,
       connected_in.label as ConnectedComponent,
       connected_in.subsystem as ConnectedSubsystem
ORDER BY Direction, RelationType;

// 27. Subsystem Component List
// List all components in a specific subsystem
// Usage: Replace 'Governance' with desired subsystem
MATCH (n:RHACMComponent {subsystem: 'Governance'})
RETURN n.label as Component,
       n.type as Type,
       n.description as Description
ORDER BY n.type, n.label;

// =============================================================================
// PERFORMANCE QUERIES
// =============================================================================

// 28. Verify Import Completeness
// Ensure all components were imported successfully
MATCH (n:RHACMComponent)
RETURN count(n) as TotalComponents,
       count(DISTINCT n.subsystem) as UniqueSubsystems,
       collect(DISTINCT n.subsystem) as SubsystemList;

// 29. Relationship Completeness Check
// Verify relationships were created properly
MATCH ()-[r]->()
RETURN count(r) as TotalRelationships,
       count(DISTINCT type(r)) as UniqueRelationshipTypes,
       collect(DISTINCT type(r)) as RelationshipTypes;

// 30. Data Quality Check
// Find any components with missing properties
MATCH (n:RHACMComponent)
WHERE n.label IS NULL OR n.subsystem IS NULL OR n.type IS NULL
RETURN count(n) as ComponentsWithMissingProperties,
       collect(n) as ProblematicComponents;

// =============================================================================
// END OF SAMPLE QUERIES
// =============================================================================

// Note: These queries provide comprehensive analysis capabilities for the RHACM
// architecture graph. Modify the WHERE clauses and component names as needed
// to explore specific aspects of your RHACM deployment.
//
// For best performance with large result sets, consider adding LIMIT clauses
// to queries that might return many results.