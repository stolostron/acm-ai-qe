---
description: |
  Run a knowledge-building session against the current cluster. Discovers
  new components, compares against the knowledge base, investigates gaps,
  and writes findings to knowledge/learned/. Use after ACM upgrades or
  to refresh the knowledge base.
when_to_use: |
  When the user asks to learn from the cluster, update knowledge, discover
  new components, refresh baselines, or says "learn", "discover", "what's
  new on this cluster", "refresh knowledge".
argument-hint: "[specific-area-to-learn]"
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
  - Bash(oc api-resources:*)
  - Bash(oc exec:*)
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

# ACM Knowledge Learner

Builds and updates the ACM knowledge base by comparing live cluster state
against curated knowledge. Uses the `acm-knowledge-learner` portable skill
methodology. Discoveries are written to `knowledge/learned/`.

ALL cluster operations are strictly **read-only** -- never modify the
cluster during learning.

## Step 1: Discover Cluster State

If diagnosis findings are available in the conversation, use them.
Otherwise, run discovery:

```bash
oc get mch -A -o yaml
oc get csv -A -o json
oc get consoleplugins -o json
oc get managedclusters
oc get managedclusteraddons -A --no-headers
```

If a specific area argument is provided, focus discovery on that area.

## Step 2: Compare Against Knowledge Base

Read `knowledge/component-registry.md`. For each discovered component:
- **In the registry?** If NO: unknown component -- trigger learning
- **Knowledge matches cluster?** If NO: knowledge drift -- update needed

## Step 3: Investigate Unknowns

For each unknown component, reverse-engineer its role using 8 cluster
metadata sources:

1. **ownerReferences** -- Pod -> Deployment -> CSV -> Operator chain
2. **OLM labels** -- `olm.owner` maps resources to CSV
3. **CSV metadata** -- owned CRDs and managed deployments
4. **K8s labels** -- `app.kubernetes.io/managed-by`, `part-of`, `component`
5. **Environment variables** -- `*.svc`, `*_HOST`, `*_URL` reveal dependencies
6. **Webhooks** -- validation/mutation service targets
7. **ConsolePlugins** -- UI integration and backend proxy targets
8. **APIServices** -- non-local API aggregation dependencies

See `knowledge/diagnostics/cluster-introspection.md` for the detailed
introspection procedure.

## Step 4: Enrich with MCPs (optional)

If **neo4j-rhacm MCP** is available:
```
read_neo4j_cypher("MATCH (n:RHACMComponent) WHERE n.label CONTAINS '<component>' RETURN n.label, n.description, n.subsystem")
```

If **acm-source** MCP is available:
```
search_code("<component>", repo="acm")
```

If **acm-search** MCP is available:
- `get_database_stats()` first to verify connectivity
- `find_resources(kind=..., outputMode="list")` for spoke-side footprint

## Step 5: Write Discoveries

Write each discovery to `knowledge/learned/`:

- Unknown operator: `knowledge/learned/<operator-name>.md`
- New failure pattern: `knowledge/learned/new-patterns.yaml`
- New dependency chain: `knowledge/learned/new-chains.yaml`
- Certificate issue: `knowledge/learned/cert-issues.yaml`
- Post-upgrade observation: `knowledge/learned/upgrade-observations.yaml`

Discoveries are additive -- never delete existing learned entries.

## Baseline Refresh

To refresh YAML baselines from the current cluster state:

```bash
python knowledge/refresh.py --baseline --webhooks --certs --addons
```

Use `--dry-run` to preview changes. Use `--promote` to copy entries from
`learned/` to the main knowledge directory after review.

## Rules

- ALL cluster operations are strictly **read-only**
- Write ONLY to `knowledge/learned/` -- never modify curated knowledge directly
- Discoveries are additive -- never delete existing learned entries
- When introspection is insufficient, note the gap rather than guessing
