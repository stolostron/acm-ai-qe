# MCP Server Sample Questions for RHACM Architecture Graph

This file contains sample questions to demonstrate the capabilities of the RHACM architecture MCP server. These questions showcase different types of analysis possible with the Neo4j knowledge graph.

## Basic Architecture Questions

### Component Discovery
- "How many components are in each RHACM subsystem?"
- "What are the main types of components in RHACM?"
- "List all operators in the RHACM architecture"
- "Show me all controllers in the Governance subsystem"
- "What components are part of the Application Lifecycle?"

### Component Details
- "Tell me about the governance-policy-propagator component"
- "What does the multicluster-observability-operator do?"
- "Explain the role of the search-indexer component"
- "What is the purpose of the cluster-curator-controller?"
- "How does the console-api component work?"

## Relationship and Dependency Analysis

### Direct Dependencies
- "What components does Red Hat Advanced Cluster Management depend on?"
- "What are the dependencies of the Governance subsystem?"
- "Show me what the multicluster-observability-operator contains"
- "What components does the policy propagator manage?"
- "Which components authenticate with Hive?"

### Dependency Chains
- "What is the complete dependency chain from ACM to policy enforcement?"
- "How does a policy flow from creation to enforcement on managed clusters?"
- "Trace the path from application deployment to cluster execution"
- "Show the observability data flow from managed clusters to dashboards"
- "What's the dependency path for cluster provisioning?"

### Reverse Dependencies
- "What components depend on the Kubernetes API Server?"
- "Which components use the Open Cluster Management API?"
- "What relies on the governance-policy-framework?"
- "Show me everything that depends on etcd"
- "What components connect to the search-collector?"

## Cross-Subsystem Integration

### Integration Patterns
- "How does the Governance subsystem integrate with Application Lifecycle?"
- "What are the connections between Observability and other subsystems?"
- "Show me all cross-subsystem relationships for the Console"
- "How does Search integrate with the rest of RHACM?"
- "What components bridge the Cluster and Application subsystems?"

### Communication Flows
- "Which components communicate across clusters?"
- "Show me the hub-spoke communication patterns"
- "What components deploy addons to managed clusters?"
- "How do subsystems exchange data with each other?"
- "What are the cross-cluster deployment relationships?"

## Hub-Spoke Architecture

### Hub Components
- "What components run on the ACM hub cluster?"
- "Which hub components manage spoke clusters?"
- "Show me all components that deploy to managed clusters"
- "What hub operators control spoke cluster addons?"
- "Which components orchestrate cross-cluster operations?"

### Spoke Components
- "What addons are deployed to managed clusters?"
- "How do spoke clusters report back to the hub?"
- "What components run on managed clusters for each subsystem?"
- "Show me the klusterlet architecture on spoke clusters"
- "Which spoke components collect and forward data to the hub?"

## Enterprise Features

### Global Hub
- "How does the Multicluster Global Hub work?"
- "What components are involved in multi-hub federation?"
- "Show me the Global Hub data flow architecture"
- "How does the Global Hub Agent communicate with the Manager?"
- "What storage does Global Hub use?"

### Submariner Networking
- "Explain the Submariner network architecture"
- "What components provide cross-cluster connectivity?"
- "How does service discovery work across clusters with Submariner?"
- "Show me the Lighthouse DNS architecture"
- "What is the role of the Submariner Gateway?"

### Backup and Recovery
- "How does RHACM handle backup and disaster recovery?"
- "What components are involved in cluster backup?"
- "Show me the OADP integration architecture"
- "How does Velero work with RHACM?"
- "What gets backed up in an RHACM cluster?"

### Insights Integration
- "How does Red Hat Insights integrate with RHACM?"
- "What components collect cluster health data?"
- "Show me the insights remediation flow"
- "How does cluster advisor provide recommendations?"
- "What compliance insights are available?"

## Operational Analysis

### Critical Components
- "What are the most connected components in RHACM?"
- "Which components are critical for RHACM operation?"
- "Show me components that have no dependencies"
- "What components would cause the most impact if they failed?"
- "Which components are central to multiple subsystems?"

### Addon Management
- "List all RHACM addons and their purposes"
- "How does the addon framework deploy components to clusters?"
- "Show me the addon lifecycle management"
- "What addons are available for each subsystem?"
- "How do addons communicate with their hub controllers?"

### Policy Management
- "Explain the complete policy lifecycle in RHACM"
- "How are policies distributed to managed clusters?"
- "What components handle policy templating?"
- "Show me the policy compliance reporting flow"
- "How does Gatekeeper integrate with RHACM policies?"

## Troubleshooting Scenarios

### Component Issues
- "If the governance-policy-propagator fails, what would be affected?"
- "What components would stop working if etcd goes down?"
- "How would a search-indexer failure impact the system?"
- "What happens if the cluster-manager becomes unavailable?"
- "Which components depend on the console-api?"

### Subsystem Failures
- "What would happen if the entire Observability subsystem fails?"
- "How would Governance subsystem failure affect other areas?"
- "What's the blast radius of Application Lifecycle failure?"
- "Which components could continue working if Search goes down?"
- "How does Console failure impact user operations?"

### Network and Connectivity
- "What components require cross-cluster network connectivity?"
- "How would network segmentation affect RHACM operations?"
- "What happens if hub-spoke communication is interrupted?"
- "Which components need internet access to function?"
- "How does certificate rotation affect component communication?"

## Advanced Analysis

### Architecture Evolution
- "How has the RHACM architecture evolved in recent versions?"
- "What new enterprise features have been added?"
- "Show me the latest governance architecture updates"
- "How has the observability pipeline changed?"
- "What HyperShift components have been integrated?"

### Performance Analysis
- "Which components are likely performance bottlenecks?"
- "How does the architecture scale with more managed clusters?"
- "What components handle the highest data volumes?"
- "Show me potential scalability constraints"
- "Which relationships indicate heavy data flow?"

### Security Analysis
- "What components handle authentication and authorization?"
- "Show me the security boundaries in RHACM"
- "Which components manage secrets and credentials?"
- "How is encryption handled across the architecture?"
- "What are the trust relationships between components?"

## Comparison Questions

### Technology Stack
- "Compare the ArgoCD Push vs Pull models in Application Lifecycle"
- "What's the difference between Hive and CAPI for cluster provisioning?"
- "How do Prometheus and Thanos work together in Observability?"
- "Compare the different channel types in Application Lifecycle"
- "What's the relationship between OCM and MCE?"

### Deployment Models
- "How do hosted control planes differ from standard clusters?"
- "Compare addon deployment patterns across subsystems"
- "What's the difference between hub and spoke component responsibilities?"
- "How do management clusters differ from managed clusters?"
- "Compare on-premises vs cloud deployment architectures"

## Integration Questions

### Third-Party Integrations
- "How does RHACM integrate with OpenShift GitOps?"
- "Show me the AWX Automation Platform integration"
- "What's the relationship with OpenShift Container Platform?"
- "How does Ansible integration work in cluster management?"
- "What external systems does RHACM connect to?"

### API Integrations
- "What APIs does RHACM provide for external integration?"
- "How do external tools query the RHACM graph?"
- "Show me the webhook integrations available"
- "What REST APIs are exposed by each subsystem?"
- "How can external monitoring systems integrate with RHACM?"

---

## Usage Tips for MCP Server

### Query Patterns
When asking questions, you can:
- Request specific component information
- Ask for relationship mappings
- Explore dependency chains
- Analyze cross-subsystem interactions
- Investigate failure scenarios
- Compare architectural approaches

### Response Types
The MCP server can provide:
- Component lists and details
- Relationship diagrams
- Dependency trees
- Data flow explanations
- Architecture recommendations
- Troubleshooting guidance

### Best Practices
- Start with broad questions, then drill down
- Ask about both technical and operational aspects
- Explore both current state and potential scenarios
- Consider security and performance implications
- Think about scalability and evolution