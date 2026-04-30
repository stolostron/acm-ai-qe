# Knowledge System

The agent's knowledge about ACM -- 59 files organized in 5 layers. The
knowledge defines what correct, healthy behavior looks like (ground truth).
The cluster shows current state. The gap between the two is what the agent
diagnoses and reports.

## Structure

### `architecture/` -- How ACM Works (40 files)

Engineering-level knowledge about each ACM subsystem. Each component
directory contains up to 4 files:

- `architecture.md` -- How the component works: controllers, CRDs,
  reconciliation, watches, health reporting, dependencies
- `data-flow.md` -- End-to-end data movement with protocol-level detail
- `known-issues.md` -- Bug patterns, diagnostic signals, version-specific issues
- Special files: `health-patterns.md`, `post-upgrade-patterns.md`

Foundation files (apply to all components):
- `kubernetes-fundamentals.md` -- K8s primitives ACM is built on
- `acm-platform.md` -- MCH/MCE hierarchy, operator lifecycle, addon framework

Component directories:

| Directory | Files | Notes |
|-----------|-------|-------|
| `search/` | architecture, data-flow, known-issues | search-v2, postgres, RBAC filtering |
| `governance/` | architecture, data-flow, known-issues | GRC, propagator, sync controllers |
| `observability/` | architecture, data-flow, known-issues | Thanos stack, Grafana, S3 storage |
| `cluster-lifecycle/` | architecture, data-flow, known-issues, **health-patterns** | Hive, import, upgrade, HyperShift |
| `console/` | architecture, data-flow, known-issues | Plugin model, console-api, fleet virt |
| `application-lifecycle/` | architecture, data-flow, known-issues | Subscriptions, AppSets, GitOps |
| `virtualization/` | architecture, data-flow, known-issues | Fleet virt, KubeVirt, MTV |
| `rbac/` | architecture, data-flow, known-issues | MCRA, ClusterPermission, roles |
| `automation/` | architecture, data-flow, known-issues | ClusterCurator, AAP hooks, upgrades |
| `addon-framework/` | architecture, data-flow, known-issues | Addon manager, ManifestWork delivery |
| `networking/` | architecture, data-flow, known-issues | Submariner, tunnels, service discovery |
| `infrastructure/` | architecture, data-flow, known-issues, **post-upgrade-patterns** | Node/cert/etcd/storage flows |

### `diagnostics/` -- Investigation Methodology (8 files)

- `diagnostic-layers.md` -- 12-layer investigation framework for systematic
  root cause tracing (vertical layer tracing complements horizontal chains)
- `dependency-chains.md` -- 12 critical cascade paths with tracing procedures
- `common-diagnostic-traps.md` -- 14 patterns where the obvious diagnosis is wrong
- `evidence-tiers.md` -- Tier 1/2/3 evidence weighting rules + confidence levels
- `diagnostic-playbooks.md` -- 14 per-subsystem investigation procedures
- `cluster-introspection.md` -- 8 metadata sources for reverse-engineering
  component dependencies from live cluster state (self-healing fallback)
- `neo4j-reference.md` -- Knowledge graph Cypher queries, availability, and
  discovery chain (neo4j-rhacm MCP reference)
- `acm-search-reference.md` -- Search MCP tool parameters, query patterns,
  capabilities and limitations (acm-search MCP reference)

### Structured Operational Data (7 YAML files)

Quantitative baselines for comparing cluster state against known-good values:

- `healthy-baseline.yaml` -- Expected pod counts, deployment states, conditions
- `dependency-chains.yaml` -- 12 cascade paths in machine-readable format
- `service-map.yaml` -- Critical Service-to-Pod mappings for connectivity diagnosis
- `webhook-registry.yaml` -- Validating/mutating webhooks, owners, failure policies
- `certificate-inventory.yaml` -- TLS secrets, rotation owners, impact when corrupted
- `addon-catalog.yaml` -- Managed cluster addons, health checks, dependencies
- `version-constraints.yaml` -- Known version incompatibilities for version-aware diagnosis

### Cross-Cutting Knowledge (2 markdown files)

- `component-registry.md` -- Master inventory of ACM components, CRDs, and namespaces
- `failure-patterns.md` -- Symptom-to-root-cause correlation heuristics

### `learned/` -- Agent-Discovered Knowledge

Written by the agent during health checks when it encounters something not
in the static knowledge. Grows over time. Version- and cluster-specific.

## How Knowledge is Used

When investigating a component, the agent follows this priority order:

1. Read `architecture/<component>/architecture.md` -- understand how it should work
2. Check `known-issues.md` -- match symptoms against documented bug patterns
3. Consult structured YAML -- compare cluster state against quantitative baselines
4. Use `diagnostics/` -- follow investigation methodology and evidence rules
5. Check `learned/` -- look for previous discoveries on this cluster
6. If nothing matches -- trigger self-healing:
   - Reverse-engineer dependencies from live cluster metadata
     (owner refs, OLM labels, CSVs, env vars, webhooks, ConsolePlugins, APIServices)
   - Cross-reference with neo4j-rhacm knowledge graph MCP
   - Use acm-ui MCP to understand dependency implementation (source code)
   - Write findings to `learned/` for future runs

## Refreshing Knowledge

Update YAML baselines from a live cluster:

```bash
python -m knowledge.refresh                 # Refresh all YAML files
python -m knowledge.refresh --baseline      # Update healthy-baseline.yaml
python -m knowledge.refresh --webhooks      # Update webhook-registry.yaml
python -m knowledge.refresh --certs         # Update certificate-inventory.yaml
python -m knowledge.refresh --addons        # Update addon-catalog.yaml
python -m knowledge.refresh --promote       # Review learned/ entries for promotion
python -m knowledge.refresh --dry-run       # Show what would change without writing
```

Smart merge behavior: curated content (impact descriptions, dependencies,
diagnostic guidance) is preserved. New items found on the cluster get
placeholder descriptions. Items no longer on the cluster are flagged but
kept. Version drift between YAML metadata and the cluster's ACM version
is detected and reported.

Requires: `oc` CLI logged into an ACM hub cluster, `pyyaml` package.
