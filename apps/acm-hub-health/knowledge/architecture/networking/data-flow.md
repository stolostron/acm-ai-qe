# Networking (Submariner) -- Data Flow

## End-to-End Cross-Cluster Communication

```
Cluster A                           Broker (Hub)                    Cluster B
─────────                           ────────────                    ─────────

Pod A                                                                Pod B
  │                                                                    ▲
  ▼                                                                    │
RouteAgent                                                        RouteAgent
(routes pod traffic                                               (routes incoming
 to gateway node)                                                  to target pod)
  │                                                                    ▲
  ▼                                                                    │
Gateway Engine ──── IPsec/WireGuard/VXLAN tunnel ──────────►  Gateway Engine
  │                         │                                          ▲
  ▼                         ▼                                          │
Broker Sync ──────► Endpoint CR ◄─────── Broker Sync
                    Cluster CR
                    (exchange metadata)

Service Discovery (Lighthouse):
ServiceExport ──► Lighthouse ──► Broker ──► ServiceImport ──► CoreDNS
(source cluster)                                              (.clusterset.local)
```

---

## Flow 1: Tunnel Establishment

1. **submariner-addon deployed** -- ACM addon controller creates
   ManagedClusterAddon and ManifestWork for Submariner on target clusters
2. **Submariner operator installed on spoke** -- ManifestWork payload
   includes the Submariner operator subscription
3. **Broker created on hub** -- Broker CR in the ManagedClusterSet
   namespace provides the rendezvous point
4. **Gateway DaemonSet starts** -- Runs on nodes labeled
   `submariner.io/gateway=true` (one node per cluster typically)
5. **Endpoint exchange via Broker** -- Each gateway creates an Endpoint
   CR on the Broker; other gateways read it to discover peers
6. **Tunnel negotiation** -- Gateways establish IPsec (default),
   WireGuard, or VXLAN tunnels using discovered endpoints
7. **RouteAgent configures routing** -- Installs routes on all nodes
   to direct cross-cluster CIDR traffic through the gateway

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| 1. Addon deployment | submariner MCA not created | No Submariner on spoke | `oc get managedclusteraddon -n <cluster> submariner` |
| 2. Operator install | Image pull fails on spoke | Submariner operator pods pending | Check operator pods on spoke |
| 3. Broker creation | ManagedClusterSet not configured | No Broker CR | `oc get broker -A` |
| 4. Gateway start | No node labeled for gateway | Gateway DaemonSet 0 ready | Check nodes with `submariner.io/gateway=true` label |
| 5. Endpoint exchange | Broker unreachable from spoke | Endpoint CRs missing | Check Broker namespace for Endpoint CRs |
| 6. Tunnel negotiation | Port blocked (4500/UDP, 4490/UDP) | Gateway shows Connecting | `oc get gateways.submariner.io -A` |
| 7. Route setup | OVN-K version incompatible | Routes not installed | Check RouteAgent pods and logs |

---

## Flow 2: Service Discovery

1. **ServiceExport created** -- User exports a Service on the source
   cluster by creating a ServiceExport CR
2. **Lighthouse agent** -- Watches ServiceExport, publishes service
   metadata to the Broker
3. **Broker sync** -- Service metadata stored as Broker resources
4. **ServiceImport created** -- Lighthouse agent on remote clusters
   reads Broker, creates ServiceImport CRs locally
5. **CoreDNS plugin** -- Lighthouse CoreDNS plugin resolves
   `<svc>.<ns>.svc.clusterset.local` queries using ServiceImport data
6. **DNS resolution** -- Pods using `.clusterset.local` names reach
   cross-cluster services via the tunnel

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| ServiceExport | User doesn't create it | Service not discoverable | `oc get serviceexport -n <ns>` |
| Lighthouse agent | Pod crashed or not deployed | ServiceImport not created on remote | Check Lighthouse pods on spoke |
| Broker sync | Network partition from Broker | Stale service metadata | Check Lighthouse logs for sync errors |
| ServiceImport | Conflict with local service | Resolution returns wrong IP | `oc get serviceimport -n <ns>` |
| CoreDNS plugin | Plugin not loaded | `.clusterset.local` NXDOMAIN | `nslookup <svc>.<ns>.svc.clusterset.local` |
| DNS resolution | Tunnel down | DNS resolves but connection times out | Verify tunnel status first |

---

## Flow 3: GlobalNet (Overlapping CIDRs)

When cluster CIDRs overlap, GlobalNet provides NAT:

1. **GlobalNet enabled** -- SubmarinerConfig sets `globalCIDR` range
2. **GlobalIP allocation** -- GlobalNet controller allocates GlobalIPs
   from the CIDR range for services and pods that need cross-cluster access
3. **Ingress rules** -- GlobalNet configures iptables/nftables rules
   on the gateway for DNAT (incoming traffic)
4. **Egress rules** -- SNAT rules for outgoing cross-cluster traffic
5. **Tunnel transit** -- Traffic uses GlobalIPs through the tunnel
6. **Remote NAT** -- Destination gateway translates GlobalIP back to
   local pod/service IP

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| GlobalIP allocation | CIDR range exhausted | New services can't get GlobalIP | `oc get clusterglobalegressips -A` |
| NAT rules | nftables migration breaks rules | Existing connections fail | Check gateway logs for iptables/nftables errors |
| Tunnel transit | GlobalIP collision between clusters | Intermittent connectivity | Compare GlobalCIDR ranges across clusters |

---

## Data Freshness

- **Endpoint exchange:** Near-real-time via Broker watches
- **Service discovery:** Seconds to minutes depending on Broker sync interval
- **Gateway health:** Real-time via gateway status CRs
- **DNS resolution:** Cached per CoreDNS TTL settings
