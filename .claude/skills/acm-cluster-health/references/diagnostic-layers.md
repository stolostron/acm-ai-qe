# 12-Layer Diagnostic Model

## Investigation Order

Check bottom-up. A broken lower layer explains symptoms at all higher layers.

### Foundational Layers (check FIRST)

**Layer 1 -- Compute:** Node status, CPU/memory/disk pressure, scheduling capacity.
**Layer 2 -- Control Plane:** OCP cluster operators, API server health, etcd.
**Layer 3 -- Network:** NetworkPolicies in ACM namespaces (should not exist), service endpoints (zero endpoints = silent failure), DNS resolution.
**Layer 4 -- Storage:** PVC bound status, emptyDir data integrity (search-postgres row count), StatefulSet volume claims.
**Layer 5 -- Configuration:** MCH/MCE component toggles, OLM subscription health, CatalogSource gRPC state, CSV phase, InstallPlan completion.

### Conditional Layers (check if symptoms suggest)

**Layer 6 -- Auth/TLS:** Certificate expiry, pending CSRs, service-ca secret ages. Check if TLS errors surfaced in logs.
**Layer 7 -- RBAC:** Role bindings, service account permissions. Check if permission errors surfaced.
**Layer 8 -- Webhooks:** Validating/mutating configurations. Compare against expected webhooks. Check failure policies.

### Component Layers (check after foundational)

**Layer 9 -- Operators:** Pod status, replica counts vs baseline, restart counts, StatefulSet health, sub-operator CR conditions, leader election leases, console image integrity.
**Layer 10 -- Cross-Cluster:** Managed cluster availability, addon health, klusterlet status, lease freshness.

### Application Layers (check last)

**Layer 11 -- Data Flow:** API response correctness, data propagation between components, search index freshness.
**Layer 12 -- UI:** Console pod health, plugin registration, rendering correctness.
