---
description: |
  Run a targeted deep investigation on a specific ACM component, symptom,
  or area. Runs all 6 diagnostic phases focused on the target, tracing
  dependency chains and correlating cross-component issues with evidence.
when_to_use: |
  When the user wants to investigate a specific problem, asks "why are
  clusters Unknown", "what's wrong with search", "investigate governance",
  "dig into observability", or provides a specific target to analyze.
argument-hint: "target-component-or-symptom"
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
  - mcp__acm-ui__*
  - mcp__neo4j-rhacm__*
  - mcp__acm-search__*
---

# ACM Targeted Investigation

Runs all 6 diagnostic phases focused on a specific component, symptom, or
area. Uses the `acm-hub-health-check` portable skill for phase methodology
and the `acm-cluster-health` portable skill for the 12-layer diagnostic
model. Optionally uses `acm-neo4j-explorer` for dependency analysis.

ALL cluster operations are strictly **read-only**.

## Step 1: Parse the Target

Identify the target from the user's request. Map to an ACM subsystem:

| User Says | Target Subsystem | Knowledge Path |
|-----------|-----------------|----------------|
| "search", "empty results" | Search | `knowledge/architecture/search/` |
| "governance", "policies", "GRC" | Governance | `knowledge/architecture/governance/` |
| "clusters Unknown", "managed clusters" | Cluster Lifecycle | `knowledge/architecture/cluster-lifecycle/` |
| "console", "UI broken", "tabs missing" | Console | `knowledge/architecture/console/` |
| "observability", "dashboards empty" | Observability | `knowledge/architecture/observability/` |
| "addons", "addon unavailable" | Addon Framework | `knowledge/architecture/addon-framework/` |
| "applications", "subscriptions" | Application Lifecycle | `knowledge/architecture/application-lifecycle/` |
| "virtualization", "VMs" | Virtualization | `knowledge/architecture/virtualization/` |
| "RBAC", "permissions" | RBAC | `knowledge/architecture/rbac/` |
| "certificates", "TLS errors" | Infrastructure | `knowledge/architecture/infrastructure/` |

If the target doesn't map to a subsystem, treat it as a symptom and
investigate using the 12-layer model to find the affected subsystem.

## Step 2: Run the Pipeline (Focused)

Run all 6 phases from the `acm-hub-health-check` methodology, but focused
on the target and its dependencies:

**Phase 1 (Discover):** Full hub inventory (same as diagnose -- needed for
context). Identify the MCH namespace.

**Phase 2 (Learn):** Read the target subsystem's knowledge files:
- `knowledge/architecture/<subsystem>/architecture.md` -- how it works
- `knowledge/architecture/<subsystem>/data-flow.md` -- where data flows
- `knowledge/architecture/<subsystem>/known-issues.md` -- known bugs
- `knowledge/diagnostics/diagnostic-layers.md` -- 12-layer framework
- `knowledge/diagnostics/common-diagnostic-traps.md` -- 14 traps

**Phase 3 (Check):** Check the target's health bottom-up through the 12
layers. Also check dependencies of the target (e.g., search depends on
search-postgres, which depends on storage).

**Phase 4 (Pattern Match):** Match against the target's `known-issues.md`
and `knowledge/failure-patterns.md`.

**Phase 5 (Correlate):** Trace dependency chains involving the target.
Read `knowledge/diagnostics/dependency-chains.md` (12 chains). Use
`acm-neo4j-explorer` for broader dependency coverage if available.

**Phase 6 (Deep Investigate):** Deep dive into the target. Pod logs,
events, data flow tracing. Follow the target's playbook from
`knowledge/diagnostics/diagnostic-playbooks.md`.

## Step 3: Report Findings

Use **narrative format** (not the tabular health report):

```
# Investigation: <target>

## Summary
<what was found, root cause, confidence>

## Evidence Chain
1. <observation> -> <inference>
2. <observation> -> <inference>
3. ...

## Root Cause
<root cause with layer identification and evidence tier>

## Known Issue Match
<JIRA reference or "No match">

## Recommended Action
<what to do -- fix, upgrade, workaround>

## Dependency Impact
<what else is affected by this root cause>
```

## Step 4: Offer Next Steps

Based on findings, suggest:
- `remediate` skill if cluster-fixable issues found
- `learn` skill if unknown components were discovered
- Full `diagnose` skill at Deep depth if broader investigation needed
