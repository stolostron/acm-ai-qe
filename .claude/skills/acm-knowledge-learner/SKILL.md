---
name: acm-knowledge-learner
description: Build and update ACM knowledge by comparing live cluster state to the knowledge base. Discovers unknown operators, new failure patterns, dependency chains, and certificate issues. Use when asked to learn from a cluster, update knowledge, discover new components, or refresh baselines.
compatibility: "Requires oc CLI logged into an ACM hub. Optional MCPs: neo4j-rhacm (dependency discovery), acm-source (component understanding), acm-search (fleet discovery). Works with reduced depth without optional MCPs."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Knowledge Learner

## Knowledge Directory

KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/

Builds and updates the ACM knowledge base by comparing live cluster state against curated knowledge. Discovers unknown components, new failure patterns, dependency chains, and infrastructure changes.

**Standalone operation:** This skill works independently. Give it cluster access and it will:
1. Discover what's deployed on the hub
2. Compare against the knowledge base
3. Identify gaps (unknown operators, undocumented dependencies, new patterns)
4. Write discoveries directly to the appropriate knowledge file

When used after a diagnostic (acm-hub-health-check), it receives richer context about what was found and can focus learning on the gaps discovered during diagnosis. Without prior diagnosis, it performs its own discovery phase.

## Process

### Step 1: Discover Cluster State

If diagnosis findings are available in the conversation, use them. Otherwise, run discovery:

```bash
oc get mch -A -o yaml
oc get csv -A -o json
oc get consoleplugins -o json
oc get managedclusters
oc get managedclusteraddons -A --no-headers
```

### Step 2: Compare Against Knowledge Base

Read `${KNOWLEDGE_DIR}/baselines/component-registry.md`. For each discovered component:
- Is it in the component registry? If NO: **unknown component** -- trigger learning
- Does the knowledge match what's deployed? If NO: **knowledge drift** -- update needed

### Step 3: Investigate Unknowns (8-Source Introspection)

For each unknown component, reverse-engineer its role using these 8 sources:

1. **ownerReferences** -- Pod -> Deployment -> CSV -> Operator chain
   ```bash
   oc get deploy <name> -n <ns> -o jsonpath='{.metadata.ownerReferences}'
   ```

2. **OLM labels** -- `olm.owner` maps resources to CSV
   ```bash
   oc get deploy <name> -n <ns> -o jsonpath='{.metadata.labels}'
   ```

3. **CSV metadata** -- owned CRDs and managed deployments
   ```bash
   oc get csv <csv-name> -n <ns> -o jsonpath='{.spec.customresourcedefinitions.owned}'
   ```

4. **K8s labels** -- `app.kubernetes.io/managed-by`, `part-of`, `component`

5. **Environment variables** -- `*.svc`, `*_HOST`, `*_URL` reveal runtime dependencies
   ```bash
   oc get deploy <name> -n <ns> -o jsonpath='{.spec.template.spec.containers[*].env}'
   ```

6. **Webhooks** -- validation/mutation service targets
   ```bash
   oc get validatingwebhookconfigurations -o json | jq '.items[] | select(.webhooks[].clientConfig.service.namespace == "<ns>")'
   ```

7. **ConsolePlugins** -- UI integration and backend proxy targets

8. **APIServices** -- non-local API aggregation dependencies

### Step 4: Cross-Reference with MCPs (optional, enriches results)

If **neo4j-rhacm MCP** is available:
```
read_neo4j_cypher("MATCH (n:RHACMComponent) WHERE n.label CONTAINS '<component>' RETURN n.label, n.description, n.subsystem")
```

If **acm-source MCP** is available:
```
search_code("<component>", repo="acm")
```

If **acm-search** MCP is available:
- Call `get_database_stats()` first to verify connectivity
- Use `find_resources(kind=..., outputMode="list")` for the component's resources across managed clusters
- Identify spoke-side footprint

If acm-search is unavailable (stub, connection error), skip fleet queries
and tell the user: "acm-search is not configured. To enable fleet
discovery, run `oc login <hub> && bash mcp/deploy-acm-search.sh` from
your terminal, then restart Claude Code."

### Step 5: Write Discoveries

Write each discovery directly to the appropriate knowledge file. Read the target first, check for duplicates, append in the existing format.

**Unknown operator discovered:**
Write to `${KNOWLEDGE_DIR}/architecture/<subsystem>/architecture.md` (append a new component section).

**New failure pattern:**
Write to `${KNOWLEDGE_DIR}/failures/<subsystem>/failure-signatures.md` (append under the matching classification heading).

**New dependency chain:**
Write to `${KNOWLEDGE_DIR}/baselines/dependency-chains.yaml` (append a new chain entry).

**Certificate issue:**
Write to `${KNOWLEDGE_DIR}/health/<subsystem>/known-issues.md` (append as a new numbered issue).

**Post-upgrade observation:**
Write to `${KNOWLEDGE_DIR}/health/<subsystem>/known-issues.md` (append with version context).

## Discovery Triggers

Automatically investigate when ANY of these are observed:

| Trigger | What to Investigate |
|---------|-------------------|
| CSV in ACM namespace not in component-registry | Unknown operator -- full 8-source introspection |
| Pod failing with unrecognized error pattern | New failure pattern -- check logs, compare to failure-patterns.md |
| Two subsystems failing with no known chain between them | New dependency chain -- trace env vars, owner refs |
| TLS errors in pod logs | Certificate issue -- check secret ages, CSR status |
| Pod restarts settling after upgrade | Post-upgrade settling -- compare pod ages to MCH upgrade time |

## Baseline Refresh

Baseline refresh is done by the agent directly -- read the baseline file, query the cluster with `oc`, and update the file in place.

## Rules

- ALL cluster operations are strictly **read-only** -- never modify the cluster during learning
- Write directly to the appropriate target file (see directory map in root CLAUDE.md)
- Discoveries are **additive** -- never delete existing content, only append
- Read the target file first and check for duplicates before writing
- When introspection is insufficient, note the gap rather than guessing
