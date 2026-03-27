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

### `remediation/` -- Fix Procedures (Phase 2)

- `remediation-playbooks.md` -- Per-fix-type procedures with safety levels
- `risk-classification.md` -- SAFE / MODERATE / RISKY criteria

### `learned/` -- Agent-Discovered Knowledge

Written by the agent during health checks when it discovers something not
in the static knowledge. Grows over time.

- Component discoveries: `<component>.md`
- Fix history: `fixes/<fix-YYYY-MM-DD>.md`

## Priority Order

When investigating a component:
1. Read its `architecture/` files first (understand how it should work)
2. Check `known-issues.md` for matching bug patterns
3. Use `diagnostics/` for investigation methodology
4. Check `learned/` for previous discoveries on this cluster
5. If nothing matches, use self-healing (rhacm-docs + acm-ui MCP)
