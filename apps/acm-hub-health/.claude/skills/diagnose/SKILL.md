---
description: |
  Run ACM hub health diagnostics at configurable depth. Quick pulse check
  (~30s), standard health check (~2-3 min), or full deep audit (~5-10 min).
  Produces a structured health report with evidence-based findings.
when_to_use: |
  When the user wants to check hub health, run a diagnostic, see if the
  hub is alive, do a sanity check, health check, or deep audit. Also
  triggers on "is my hub OK", "how's my hub", "thorough check",
  "full diagnostic", "check my cluster".
argument-hint: "[--depth quick|standard|deep] [additional context]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write(knowledge/learned/*)
  - Edit(knowledge/learned/*)
  - Bash(oc get:*)
  - Bash(oc describe:*)
  - Bash(oc logs:*)
  - Bash(oc version:*)
  - Bash(oc whoami:*)
  - Bash(oc cluster-info:*)
  - Bash(oc api-resources:*)
  - Bash(oc adm top:*)
  - Bash(oc exec:*)
  - Bash(oc auth:*)
  - Bash(kubectl get:*)
  - Bash(kubectl describe:*)
  - Bash(grep:*)
  - Bash(jq:*)
  - Bash(wc:*)
  - Bash(sort:*)
  - Bash(head:*)
  - Bash(tail:*)
  - Bash(awk:*)
  - Bash(cut:*)
  - Bash(cat:*)
  - Bash(ls:*)
  - Bash(find:*)
  - Bash(python3:*)
  - Bash(python:*)
  - mcp__acm-source__*
  - mcp__neo4j-rhacm__*
  - mcp__acm-search__*
---

# ACM Hub Health Diagnostic

Runs the 6-phase diagnostic pipeline at the requested depth. Uses the
`acm-hub-health-check` portable skill for the phase methodology and the
`acm-cluster-health` portable skill for the 12-layer diagnostic model.

ALL cluster operations are strictly **read-only** during diagnosis. If
cluster-fixable issues are found, offer the `remediate` skill AFTER
presenting the full health report.

## Step 1: Determine Depth

Parse the user's request or `--depth` flag:

| Depth | Phases | Duration | Triggers |
|-------|--------|----------|----------|
| Quick | Phase 1 only | ~30s | "sanity", "quick check", "is my hub alive", `--depth quick` |
| Standard | Phases 1-4 | ~2-3 min | "health check", "how's my hub", `--depth standard` |
| Deep | All 6 phases | ~5-10 min | "deep audit", "thorough check", "full diagnostic", `--depth deep` |

Default to **Standard** when intent is unclear.

Tell the user which depth was selected before starting.

## Step 2: Run the Pipeline

Execute phases sequentially. Show a status update before each phase starts.

### Phase 1: Discover (all depths)

Inventory what's deployed. Run these commands (in parallel where possible):

```bash
oc get mch -A -o yaml
oc get multiclusterengines -A -o yaml
oc get nodes
oc get clusterversion
oc get managedclusters
oc get csv -A -o json
oc whoami --show-server
```

**Critical: Discover MCH namespace first.** From the MCH resource, identify the
namespace (NOT always `open-cluster-management`). All subsequent commands use
this namespace.

**Operator health** (immediately after MCH discovery):
```bash
oc get deploy multiclusterhub-operator -n <mch-ns> --no-headers
oc get deploy multicluster-engine-operator -n multicluster-engine --no-headers
```

If multiclusterhub-operator has 0 replicas: **CRITICAL immediately**. MCH
`.status.phase: Running` is a snapshot from the last reconciliation -- it does
NOT update when the operator stops. This takes priority over all other findings.

**For Quick depth: STOP HERE.** Report MCH/MCE status, node count, managed
cluster count, operator health. Use the verdict rules from
[report-format.md](report-format.md).

### Phase 2: Learn (Standard+)

Build understanding of healthy vs actual state:

1. Read `knowledge/component-registry.md`
2. Read `knowledge/architecture/acm-platform.md`
3. For components with issues: read `knowledge/architecture/<subsystem>/architecture.md`
4. Read `knowledge/healthy-baseline.yaml`
5. Read `knowledge/diagnostics/common-diagnostic-traps.md` (14 traps)
6. If managed clusters present: read `knowledge/architecture/cluster-lifecycle/health-patterns.md`
7. Read `knowledge/diagnostics/diagnostic-layers.md` (12-layer framework)

If the knowledge doesn't cover a discovered component, note the gap and
continue with best-effort analysis. Suggest the `learn` skill after diagnosis.

### Phase 3: Check (Standard+)

Systematic bottom-up health verification using the 12-layer model from the
`acm-cluster-health` portable skill. Check foundational layers (1-3) BEFORE
component layers (4-10) BEFORE application layers (11-12).

Key checks per layer group:

**Foundational (Layers 1-3):** Nodes Ready? OCP operators Available?
NetworkPolicies or ResourceQuotas in ACM namespaces? (ACM does NOT create
these -- presence is suspicious: Trap 9, Trap 11)

**Component (Layers 4-10):** PVCs Bound? Search-postgres data integrity?
MCH component toggles? Pod health across ACM namespaces vs
`knowledge/healthy-baseline.yaml`? Addon status vs `knowledge/addon-catalog.yaml`?

**Application (Layers 11-12):** Only if lower layers healthy. Data flow,
ConsolePlugin status, console image integrity.

**Spoke-side verification:** If `acm-search` MCP available AND search-postgres
healthy, use `find_resources` for fleet-wide checks. See
`knowledge/diagnostics/acm-search-reference.md`.

Walk through ALL 14 traps from `knowledge/diagnostics/common-diagnostic-traps.md`.

### Phase 4: Pattern Match (Standard+)

Cross-reference findings against known issues:

1. Read `knowledge/failure-patterns.md`
2. Read `knowledge/architecture/<subsystem>/known-issues.md` for each affected subsystem
3. Check `knowledge/version-constraints.yaml`
4. Check `knowledge/architecture/infrastructure/post-upgrade-patterns.md`

Note JIRA references, fix versions, and cluster-fixability for matched patterns.

### Phase 5: Correlate (Deep only)

Trace dependency chains when multiple issues found:

1. Read `knowledge/diagnostics/dependency-chains.md` (12 chains)
2. Check each chain link against Phase 3 findings
3. Use `neo4j-rhacm MCP` for dependencies not in curated chains (if available)
4. If `acm-search` MCP available: spoke-side chain verification
5. Weight evidence per `knowledge/diagnostics/evidence-tiers.md`
6. Verify conclusions against trap list

### Phase 6: Deep Investigate (Deep only)

For CRITICAL findings:

- `oc logs <pod> --tail=100` and `--previous`
- `oc get events -n <ns> --sort-by=.lastTimestamp`
- Resource details: `oc describe`, YAML dumps
- Follow `knowledge/diagnostics/diagnostic-playbooks.md`
- Read component `data-flow.md` to trace where flow breaks
- Use `acm-search` MCP for spoke triage when available

## Step 3: Generate Report

Use the format in [report-format.md](report-format.md). Key rules:

- Verdict is mechanical: HEALTHY / DEGRADED / CRITICAL
- Each issue has 9 required fields
- Use "N/A" or "No match" for fields that don't apply -- never omit fields
- For targeted investigations, use narrative format with evidence chain

## Step 4: Offer Remediation (if applicable)

If cluster-fixable issues are found, offer to run the `remediate` skill.
Do NOT attempt fixes during the diagnostic pipeline.

## Shell Compatibility

Always single-quote `oc` output format arguments containing brackets to
prevent zsh glob expansion:
```bash
oc get pods -o 'custom-columns=NAME:.metadata.name,RESTARTS:.status.containerStatuses[0].restartCount'
```
