# Z-Stream Analysis Knowledge Database

Domain reference data for the AI agent during Stage 2 failure classification.
The agent reads these files to understand ACM architecture, known failure
patterns, and classification methodology.

---

## Structure

### Architecture (`architecture/`)

Per-subsystem deep knowledge organized as:
- `architecture.md` -- components, CRDs, namespaces, prerequisites
- `data-flow.md` -- how data moves through the subsystem (where failures occur)
- `failure-signatures.md` -- known failure patterns with classification guidance

| Subsystem | Files | Coverage |
|-----------|-------|----------|
| Platform foundation | `acm-platform.md`, `kubernetes-fundamentals.md` | ACM operator hierarchy, K8s concepts |
| Search | 3 files | search-api/indexer/postgres/collector, GraphQL flow, DB corruption |
| Console | 3 files | Frontend React, backend Node.js, SSE events, proxy routes |
| Governance (GRC) | 3 files | Policy propagator, spoke addons, compliance flow |
| Cluster Lifecycle (CLC) | 3 files | Hive, import controller, webhooks, cluster operations |
| Virtualization | 3 files | CNV, MTV, VM actions, CCLM, KVM nodes |
| Application Lifecycle (ALC) | 3 files | Subscriptions, channels, ArgoCD, app status |
| RBAC | 3 files | FG-RBAC, MCRA, ClusterPermission, IDP auth |
| Automation | 3 files | ClusterCurator, Ansible Tower integration |
| Observability | 2 files | MCO, Thanos, Grafana, metrics collection |
| Infrastructure | 2 files | Nodes, etcd, quotas, NetworkPolicies, webhooks, certs |

### Diagnostics (`diagnostics/`)

Classification methodology and investigation reference:

| File | Content |
|------|---------|
| `classification-decision-tree.md` | PR-1 through PR-7 decision tree with 3-path routing (v3.8: serves as validation checks for layer-based investigation) |
| `diagnostic-layers.md` | 12-layer diagnostic investigation methodology (v3.8): per-layer checklists, error-to-layer mapping, WHO/WHY investigation, classification-after-root-cause rules |
| `diagnostic-traps.md` | 10 patterns where the obvious diagnosis is WRONG (8 from hub health + 2 counter-traps) |
| `evidence-tiers.md` | How Tier 1 and Tier 2 evidence is weighted |
| `common-misclassifications.md` | 6 known cases where the pipeline gets confused and why |

### Structured Data (12 root YAML files)

| File | Content | Used For |
|------|---------|----------|
| `addon-catalog.yaml` | All managed cluster addons with health checks and impact | Addon health verification |
| `api-endpoints.yaml` | Backend API endpoints with probe commands | Backend cross-check |
| `components.yaml` | ACM component registry (name, namespace, labels, health checks) | Component health context |
| `dependencies.yaml` | Dependency chains with cascade failure paths and `layers_involved` (v3.8) | Root cause tracing |
| `failure-patterns.yaml` | Known failure signatures for short-circuit classification | Fast pattern matching |
| `feature-areas.yaml` | Feature area index (test patterns, components, routes) | Test-to-feature mapping |
| `healthy-baseline.yaml` | Expected pod counts and deployment states per namespace | Baseline comparison |
| `prerequisites.yaml` | Machine-checkable prerequisite definitions per feature | Prerequisite validation |
| `selectors.yaml` | UI selector ground truth per feature area | Stale selector detection |
| `test-mapping.yaml` | Test suite to feature area mapping with known issues | Investigation scoping |
| `version-constraints.yaml` | Product version incompatibilities | Version-specific routing |
| `webhook-registry.yaml` | Expected webhooks with criticality and failure policies | Webhook verification |

### Learned Knowledge (`learned/`)

Agent-contributed corrections and discoveries across runs:

| File | Content |
|------|---------|
| `corrections.yaml` | "I classified X as Y but it was Z because..." |
| `new-patterns.yaml` | "I found a new failure pattern: ..." |
| `selector-changes.yaml` | "Selector X was renamed to Y in commit Z" |

### Refresh Script

`refresh.py` updates knowledge from live sources:
- ACM Source MCP (selectors, components)
- Neo4j Knowledge Graph (dependencies)
- GitHub (PR diffs, selector renames)
- JIRA (known bugs per component)
- Live cluster (pod states, webhooks, certs)

Usage:
```bash
python knowledge/refresh.py              # Refresh all
python knowledge/refresh.py --selectors  # Refresh selectors only
python knowledge/refresh.py --promote    # Promote learned/ entries to main files
```
