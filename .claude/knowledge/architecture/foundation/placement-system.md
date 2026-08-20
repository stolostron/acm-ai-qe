---
type: architecture
subsystem: foundation
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - architecture/foundation/architecture.md
  - architecture/governance/architecture.md
  - architecture/rbac/architecture.md
---

# Placement System -- ACM's Cluster Selection Engine

## What Placement Does

The Placement system is the universal targeting engine for ACM. It answers one
question: **which managed clusters should this operation target?** Every
subsystem that needs to distribute work across clusters -- policies, apps, RBAC
bindings, addon deployment, GitOps -- goes through Placement rather than
implementing its own cluster selection logic.

The `cluster-manager-placement-controller` (3 replicas, leader-elected, in
`open-cluster-management-hub`) evaluates `Placement` CRs against the set of
registered `ManagedCluster` resources. It filters clusters using label-based
predicates, cluster set membership, and tolerations, then writes the results
to `PlacementDecision` CRs. Consumers never evaluate Placements directly --
they only read the pre-computed decisions.

---

## Key CRDs

| CRD | API Group | Scope | Purpose |
|-----|-----------|-------|---------|
| Placement | `cluster.open-cluster-management.io/v1beta1` | Namespaced | Defines cluster selection criteria (labels, cluster sets, predicates) |
| PlacementDecision | `cluster.open-cluster-management.io/v1beta1` | Namespaced | Auto-created by controller; lists clusters matching a Placement |
| ManagedClusterSet | `cluster.open-cluster-management.io/v1beta2` | Cluster | Groups managed clusters into a logical set |
| ManagedClusterSetBinding | `cluster.open-cluster-management.io/v1beta2` | Namespaced | Binds a ManagedClusterSet to a namespace, allowing Placements in that namespace to reference the set |
| PlacementRule | `apps.open-cluster-management.io/v1` | Namespaced | **DEPRECATED** (ACM 2.15+). Legacy cluster targeting; use Placement instead |

---

## Placement Evaluation Flow

```
1. User or controller creates a Placement CR with criteria
2. Placement Controller evaluates criteria against all ManagedClusters
3. Controller filters by: ManagedClusterSet membership, label selectors, predicates
4. Controller writes matching clusters to PlacementDecision CR(s)
5. Consumers watch PlacementDecision for changes
6. When clusters join, leave, or labels change, controller re-evaluates and updates decisions
```

PlacementDecisions are **live** -- they update automatically as the cluster
fleet changes. Each PlacementDecision holds up to 100 clusters; if more match,
the controller creates additional decision CRs (e.g., `<name>-decision-2`).

### How Consumers Find PlacementDecisions

PlacementDecisions are labeled with:

```
cluster.open-cluster-management.io/placement: <placement-name>
```

ACM-native consumers (MRA controller, policy propagator) use owner references
or direct API watches. The ArgoCD ApplicationSet controller uses this label as
a `labelSelector` in its `clusterDecisionResource` generator.

---

## ManagedClusterSet and Bindings

A `ManagedClusterSet` groups clusters into a logical boundary. Placements
can only select clusters from sets that are bound to the Placement's namespace
via a `ManagedClusterSetBinding`.

The `global` ManagedClusterSet is built-in and contains all clusters. It is
bound to `open-cluster-management-global-set` by default.

**Namespace scoping matters:** A Placement in `openshift-gitops` needs a
`ManagedClusterSetBinding` in that namespace to reference any cluster set.
Without the binding, the Placement selects zero clusters -- silently.

### Common Built-in Placements

| Placement Name | Namespace | Selects |
|---|---|---|
| `global` | `open-cluster-management-global-set` | All clusters |
| `rbac-hub-placement` | `open-cluster-management-global-set` | Hub only (local-cluster) |
| `rbac-spoke-placement` | `open-cluster-management-global-set` | Spoke clusters only |
| `rbac-hub-spoke-placement` | `open-cluster-management-global-set` | Both hub and spokes |
| `openshift-cnv` | varies | Clusters with CNV installed |
| `openshift-mtv` | varies | Clusters with MTV installed |

---

## The 5 Consumers

Every consumer reads `PlacementDecision` CRs to determine target clusters.
None of them evaluate the Placement directly.

| Consumer | Controller | Namespace | Binding Mechanism | What It Creates Per Cluster |
|---|---|---|---|---|
| Governance (Policy) | `grc-policy-propagator` | `ocm` | PlacementBinding -> Placement -> PlacementDecision | Replicated Policy in cluster namespace |
| Applications (Subscription) | `multicluster-operators-hub-subscription` | `ocm` | Placement ref on Subscription -> PlacementDecision | ManifestWork with app manifests |
| ArgoCD (GitOps) | ApplicationSet controller | `openshift-gitops` | `clusterDecisionResource` generator + `acm-placement` ConfigMap bridge | ArgoCD Application CR |
| RBAC (MRA) | `multicluster-role-assignment-controller` | `ocm` | Placement ref on MRA -> PlacementDecision | ClusterPermission -> ManifestWork -> RoleBinding |
| Addon Framework | `cluster-manager-addon-manager-controller` | `open-cluster-management-hub` | `installStrategy: Placements` on ManagedClusterAddOn | ManifestWork with addon agent |

### Consumer Details

**Governance:** The `PlacementBinding` CR is unique to governance. It binds a
Policy (or PolicySet) to a Placement. The propagator reads the binding, finds
the referenced Placement's decisions, and replicates the policy to each target
cluster's namespace on the hub.

**ArgoCD:** Uses a duck-typing bridge pattern. The `acm-placement` ConfigMap
(in `openshift-gitops`) teaches ArgoCD's `clusterDecisionResource` generator
how to read PlacementDecisions by defining the API group
(`cluster.open-cluster-management.io/v1beta1`), resource kind
(`placementdecisions`), status list key (`decisions`), and match key
(`clusterName`). The generator then matches each cluster name against ArgoCD
cluster secrets to get connection parameters.

**RBAC (MRA):** The MRA controller reads PlacementDecision, creates one
`ClusterPermission` per target cluster namespace on the hub, which the
`cluster-permission` controller converts to ManifestWork containing
RoleBindings/ClusterRoleBindings for the spoke.

---

## Label-Based Discovery

Managed clusters advertise their capabilities via labels on the `ManagedCluster`
resource. Addons and operators set labels when they install, and Placements use
these labels as selection criteria.

### How Labels Are Set

| Label | Set By | Meaning |
|---|---|---|
| `addons.open-cluster-management.io/mtv=true` | mtv-integrations-controller | MTV is installed; used to auto-create Forklift Provider CRs |
| `vendor=OpenShift` | registration-controller | Cluster is an OpenShift cluster |
| `cloud=Amazon` / `cloud=Azure` / etc. | registration-controller | Cloud provider detected at import time |
| `name=<cluster-name>` | registration-controller | Cluster identity label |
| `local-cluster=true` | registration-controller | This is the hub cluster |

Placements query these labels to select clusters. For example, a Placement
targeting CNV clusters uses a `matchExpressions` on the CNV addon label.

### The Discovery Pattern

```
1. Addon installs on spoke cluster
2. Addon controller sets label on ManagedCluster resource (hub-side)
3. Placement Controller detects label change
4. Re-evaluates Placements that match the new label
5. Updates PlacementDecisions to include the newly-labeled cluster
6. Consumers pick up updated decisions and act
```

---

## Cross-Subsystem Dependencies

| Dependency | Direction | Detail |
|---|---|---|
| Foundation -> All consumers | Placement produces decisions consumed by governance, apps, RBAC, GitOps, addon framework |
| Governance -> Placement | PlacementBinding references a Placement for policy targeting |
| RBAC -> Placement | MRA references a Placement for role assignment scoping |
| Apps -> Placement | Subscription references a Placement for app deployment targeting |
| GitOps -> Placement | ApplicationSet reads PlacementDecision via ConfigMap bridge |
| Addon Framework -> Placement | Uses Placement for addon install scoping |
| Registration -> Placement | Registration controller sets labels on ManagedCluster that Placements evaluate |
| OCM Webhook -> Placement | Validates Placement, ManagedClusterSet, and binding resources |

### What Breaks When Placement Is Down

If `cluster-manager-placement-controller` is unavailable:

- No new PlacementDecision updates (existing decisions remain, but stale)
- New policies are not propagated to any cluster
- New MRA role assignments are not created
- New app deployments have no target clusters
- ArgoCD ApplicationSets stop generating new Application CRs
- Addon install scoping stops working

Existing operations continue based on stale decisions until the controller recovers.
