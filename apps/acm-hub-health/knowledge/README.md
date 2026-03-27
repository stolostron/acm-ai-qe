# Knowledge System

This directory contains the agent's knowledge about ACM, organized in layers.

## How to Use

At the start of every health check, read the relevant knowledge files to build
context before investigating. The knowledge is organized so you can quickly find
what you need based on the component or subsystem you're investigating.

## Structure

### `architecture/` -- How ACM Works (per-component)

Deep engineering-level knowledge about each ACM subsystem. Each component
directory contains:

- `architecture.md` -- How the component works from the ground up: controllers,
  CRDs, reconciliation, watches, health reporting, dependencies
- `data-flow.md` -- End-to-end data movement with protocol-level detail
- `known-issues.md` -- Bug patterns, diagnostic signals, version-specific issues

Foundation files at the architecture root:
- `kubernetes-fundamentals.md` -- K8s primitives ACM is built on
- `acm-platform.md` -- MCH/MCE hierarchy, operator lifecycle, addon framework

### `diagnostics/` -- Health Check Methodology

- `dependency-chains.md` -- 6 critical cascade paths with tracing procedures
- `diagnostic-playbooks.md` -- Per-subsystem investigation procedures
- `evidence-tiers.md` -- What counts as strong vs weak evidence

### Structured Operational Data (YAML)

Quantitative reference data for comparing cluster state against known-good values:

- `healthy-baseline.yaml` -- Expected pod counts, deployment states, conditions
  for a healthy ACM hub. Compare actual cluster state against this baseline.
- `dependency-chains.yaml` -- Structured YAML complement to
  `diagnostics/dependency-chains.md`. Same 6 chains in machine-readable format
  for correlation lookups.
- `webhook-registry.yaml` -- All validating and mutating webhooks expected on
  an ACM hub, their owners, failure policies, and impact when broken.
- `certificate-inventory.yaml` -- TLS secrets per namespace, what uses them,
  who manages rotation, and impact when corrupted.
- `addon-catalog.yaml` -- All managed cluster addons, deployment expectations,
  health checks, and dependencies.

### Cross-Cutting Knowledge (markdown)

Top-level references spanning all components:
- `component-registry.md` -- Master inventory of ACM components, CRDs, and namespaces
- `failure-patterns.md` -- Common failure signatures mapped to root causes

### `learned/` -- Agent-Discovered Knowledge

Written by the agent during health checks when it discovers something not
in the static knowledge. Grows over time.

- Component discoveries: `<component>.md`

## Priority Order

When investigating a component:
1. Read its `architecture/` files first (understand how it should work)
2. Check `known-issues.md` for matching bug patterns
3. Consult structured YAML data (`healthy-baseline.yaml`, `dependency-chains.yaml`,
   `addon-catalog.yaml`, `webhook-registry.yaml`, `certificate-inventory.yaml`)
   for quantitative expectations
4. Use `diagnostics/` for investigation methodology
5. Check `learned/` for previous discoveries on this cluster
6. If nothing matches, use self-healing (rhacm-docs + acm-ui MCP)

## Refreshing Knowledge

Run the refresh script to update knowledge from a live cluster:

```bash
# From the acm-hub-health directory:
python -m knowledge.refresh                 # Refresh all YAML files from connected cluster
python -m knowledge.refresh --baseline      # Update healthy-baseline.yaml
python -m knowledge.refresh --webhooks      # Update webhook-registry.yaml
python -m knowledge.refresh --certs         # Update certificate-inventory.yaml
python -m knowledge.refresh --addons        # Update addon-catalog.yaml
python -m knowledge.refresh --promote       # Review learned/ entries for promotion
python -m knowledge.refresh --dry-run       # Show what would change without writing
```

All refresh flags use smart merge: new items found on the cluster are added with
placeholder descriptions, existing curated content (impact descriptions,
dependencies, diagnostic guidance) is preserved, and items no longer on the
cluster are flagged but kept. The script also detects version drift between
YAML metadata and the cluster's actual ACM version.

Requires: `oc` CLI logged into an ACM hub cluster, `pyyaml` package.
