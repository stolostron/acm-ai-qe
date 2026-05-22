# Networking -- Architecture

## What Multicluster Networking Does

Submariner provides direct networking connectivity between managed clusters,
enabling pod-to-pod and service-to-service communication across cluster
boundaries. ACM deploys and manages Submariner via the submariner-addon on
managed clusters.

---

## Submariner Architecture

Submariner establishes encrypted tunnels between clusters. Three core components
run on each participating cluster:

### Gateway

- **Type:** DaemonSet (on designated gateway nodes)
- **Namespace:** `submariner-operator`

Establishes and maintains encrypted IPsec/WireGuard tunnels to gateways on
other clusters. Each cluster designates one or more gateway nodes. Gateway
election uses leader-based selection.

Key responsibilities:
- Tunnel establishment and maintenance
- Endpoint advertisement via Broker
- Health monitoring of remote endpoints
- Cable driver management (IPsec, WireGuard, VXLAN)

### RouteAgent

- **Type:** DaemonSet (on all nodes)
- **Namespace:** `submariner-operator`

Programs host networking rules to route cross-cluster traffic to the gateway
node. Handles:
- iptables/nftables rule programming for inter-cluster routing
- VXLAN tunnel to gateway node within the cluster
- Endpoint event handling for remote cluster changes

### GlobalNet

- **Namespace:** `submariner-operator`
- **Optional component** (enabled when clusters have overlapping CIDRs)

Provides global virtual IP addresses when cluster pod/service CIDRs overlap:
- Allocates GlobalIPs from a non-overlapping CIDR range
- NATs between cluster-local IPs and GlobalIPs
- Manages GlobalIngressIP and GlobalEgressIP resources
- Programs iptables/nftables rules for address translation

---

## Broker

The Broker is a lightweight API aggregation layer that runs on the hub cluster
(or a designated broker cluster). It provides:
- Endpoint exchange between clusters
- Service discovery synchronization
- Cluster connectivity metadata sharing

Clusters join the Broker by creating a BrokerJoin resource. The Broker
exchanges Endpoint CRDs between participating clusters.

---

## Submariner Addon (ACM Integration)

### submariner-addon

- **MCH component:** `submariner-addon`
- **Hub controller:** `submariner-addon-controller`
- **Namespace:** MCH namespace

ACM manages Submariner lifecycle through the addon framework:
1. ClusterManagementAddon registered for Submariner
2. ManagedClusterAddon created in target cluster namespaces
3. addon-manager generates ManifestWork with Submariner operator and config
4. Submariner operator on spoke deploys Gateway, RouteAgent, GlobalNet

Configuration via `SubmarinerConfig` CR:
- Cable driver selection (IPsec, WireGuard, VXLAN)
- Gateway node selection (labels, count)
- IPsec configuration (NAT traversal, ports)
- GlobalNet CIDR and allocation
- Air-gapped deployment settings

### ManagedClusterSet Integration

Submariner connectivity is scoped to ManagedClusterSets:
- Clusters must be in the same ManagedClusterSet
- Submariner creates a ServiceImport/ServiceExport mesh within the set
- Broker scoped to the cluster set

---

## Service Discovery

Submariner enables cross-cluster service discovery via Lighthouse:
- **ServiceExport:** Marks a service for cross-cluster visibility
- **ServiceImport:** Auto-created on remote clusters for exported services
- DNS-based service resolution across clusters
- CoreDNS plugin integration for `.clusterset.local` domain

---

## Network Requirements

| Requirement | Details |
|---|---|
| Gateway ports | UDP 4500 (IPsec NAT-T), UDP 4800 (VXLAN), TCP 8080 (metrics) |
| Non-overlapping CIDRs | Required unless GlobalNet is enabled |
| Gateway node labeling | `submariner.io/gateway: true` on designated nodes |
| Cloud provider support | AWS, GCP, Azure, bare metal, VMware |
| OVN-Kubernetes compatibility | Specific version requirements per OCP version |

---

## Cross-Subsystem Dependencies

| Dependency | Why |
|---|---|
| Infrastructure (klusterlet) | Submariner addon deployed via addon framework |
| addon-manager | Manages submariner-addon lifecycle |
| MCH operator | Lifecycle management, component toggle |
| ManagedClusterSet | Scopes Submariner connectivity |
| OVN-Kubernetes / OpenShiftSDN | Cluster network plugin compatibility |

## What Depends on Networking

| Consumer | Impact When Submariner Is Down |
|---|---|
| Cross-cluster service communication | Services unreachable across clusters |
| Multi-cluster applications | Applications using cross-cluster services fail |
| Disaster recovery (OADP) | Cross-cluster backup/restore connectivity lost |
| GlobalNet users | Global IP addressing broken |
