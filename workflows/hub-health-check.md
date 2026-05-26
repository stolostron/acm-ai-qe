# Hub Health Check

Diagnose ACM hub cluster health using a 6-phase diagnostic methodology with 12-layer model, 14 diagnostic traps, and dependency chain tracing.

## Trigger

- `/health-check` -- standard 6-phase diagnosis
- `/deep` -- deep investigation with full dependency chain analysis
- `/sanity` -- quick sanity check (operator + pod status only)
- `/investigate <component>` -- focused investigation on a specific subsystem
- `/learn` -- update knowledge database with findings from the current cluster

## Prerequisites

- `oc login` to an ACM hub cluster
- Optional: Neo4j RHACM graph (`neo4j-rhacm` Podman container) for dependency analysis
- Optional: ACM Search MCP for fleet-wide spoke queries

## Phases

1. **Discover** -- identify hub topology (MCH, MCE, operators, namespaces)
2. **Learn** -- load relevant knowledge base entries for detected components
3. **Check** -- run health checks across the 12-layer diagnostic model
4. **Pattern Match** -- compare findings against 14 known diagnostic traps
5. **Correlate** -- trace dependency chains to find root causes
6. **Deep Investigate** -- focused investigation on identified problem areas

## Diagnostic Model

12 layers from infrastructure up: etcd, API server, operators, CRDs, pods, addons, webhooks, certificates, network policies, search, observability, console.

14 diagnostic traps documented in `.claude/knowledge/diagnostics/diagnostic-traps.md`.

## Output

Health verdict with severity classification, per-layer status, identified issues with evidence, and recommended remediation steps. Remediation only executed after explicit user approval.

## References

- App: [`apps/acm-hub-health/CLAUDE.md`](../apps/acm-hub-health/CLAUDE.md)
- Skills: `acm-hub-health-check`, `acm-cluster-remediation`, `acm-knowledge-learner`
- Knowledge: `.claude/knowledge/diagnostics/`, `.claude/knowledge/health/`
- Docs: [`docs/hub-health/`](../docs/hub-health/)
