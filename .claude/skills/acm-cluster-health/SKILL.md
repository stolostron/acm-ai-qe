---
name: acm-cluster-health
description: Cluster health diagnostic toolkit using a 12-layer model with 14 trap patterns, dependency chain verification, and evidence-tier framework. Use when you need to assess ACM hub cluster health, verify infrastructure state, check operator health, or diagnose subsystem issues.
compatibility: "Requires oc CLI logged into an ACM hub cluster. Optional MCPs: acm-search (fleet queries), acm-kubectl (spoke access), neo4j-rhacm (dependency graph). Degrades gracefully without optional MCPs."
---

# ACM Cluster Health Diagnostic Toolkit

Provides a systematic methodology for diagnosing ACM hub cluster health. This skill exposes the 12-layer diagnostic model, 14 trap detection patterns, dependency chain verification, and evidence tier framework. It contains no app-specific output format or analytical conclusions. The calling skill decides what to investigate, how deep to go, and what output to produce.

## Diagnostic Model: 12 Layers

The layers are checked bottom-up. Lower layers affect everything above them -- a Layer 1 issue explains failures at Layers 2-12.

| Layer | Name | What It Covers | Key Commands |
|-------|------|---------------|--------------|
| 1 | Compute | Node health, CPU, memory, disk pressure | `oc adm top nodes`, `oc get nodes` |
| 2 | Control Plane | OCP operators, API server, etcd | `oc get clusteroperators`, `oc get clusterversion` |
| 3 | Network | NetworkPolicies, service endpoints, DNS | `oc get networkpolicy -n $NS`, `oc get endpoints -n $NS` |
| 4 | Storage | PVCs, persistent data integrity | `oc get pvc -n $NS`, data count queries |
| 5 | Configuration | MCH toggles, OLM subscriptions, CatalogSources | `oc get mch -A -o yaml`, `oc get csv -A` |
| 6 | Auth/TLS | Certificates, CSRs, token expiry | `oc get csr`, `oc get secrets -n $NS | grep tls` |
| 7 | RBAC | Role bindings, service account permissions | `oc auth can-i`, `oc get clusterrolebinding` |
| 8 | Webhooks | Validating/mutating webhook configurations | `oc get validatingwebhookconfigurations` |
| 9 | Operators | Pod health, replica counts, restart counts, StatefulSets | `oc get pods -n $NS`, `oc get deploy -n $NS` |
| 10 | Cross-Cluster | Managed clusters, addons, spoke connectivity | `oc get managedclusters`, `oc get managedclusteraddons -A` |
| 11 | Data Flow | API responses, data propagation, search indexing | `oc exec` curl to APIs, psql queries |
| 12 | UI | Console pods, plugins, rendering | `oc get consoleplugins`, console pod health |

Read `references/diagnostic-layers.md` for detailed per-layer investigation procedures.

## Trap Detection: 14 Patterns

Traps are common diagnostic pitfalls where the obvious conclusion is wrong. Read `references/diagnostic-traps.md` for the full reference.

| Trap | Name | What It Catches |
|------|------|----------------|
| 1 | Stale MCH/MCE | Operator at 0 replicas makes status stale -- "Running" is a lie |
| 1b | Leader Election | Pods Running/Ready but no leader holds the lock -- reconciliation stopped |
| 2 | Console Tabs | Plugin backend pod crash makes console tabs silently disappear |
| 3 | Search Empty | All search pods Running but database has 0 rows -- data lost |
| 4 | Observability S3 | Thanos pods healthy but S3 credentials expired -- no data flowing |
| 5 | GRC Post-Upgrade | Governance addon pods restarting after upgrade -- transient, not broken |
| 6 | Cluster NotReady | Lease not renewed -- klusterlet may be healthy but lease is stale |
| 7 | All Addons Down | If ALL addons are unavailable, check addon-manager pod first |
| 8 | Console Cascade | Multiple console features broken? Check search-api first (shared dependency) |
| 9 | ResourceQuota | Blocks pod scheduling silently -- pods can't be (re)created |
| 10 | Cert Rotation | Pods run, APIs respond, but TLS handshakes fail -- silent failure |
| 11 | NetworkPolicy Hidden | Pods look healthy (Running, 0 restarts) but can't communicate |
| 12 | Selector Doesn't Exist | Test references a CSS selector that was never in official source -- AUTOMATION_BUG regardless of infra state |
| 13 | Backend Wrong Data | Backend returns incorrect data -- PRODUCT_BUG, not INFRASTRUCTURE |
| 14 | Disabled Prerequisite | Feature disabled but Jenkins params say it should be enabled -- INFRASTRUCTURE setup failure |

## Dependency Chain Verification

Read `references/dependency-chains.md` for the chain definitions. Key principle: trace from symptom to root cause by following dependency chains. If Component A depends on Component B and B is broken, A's failures are CAUSED BY B.

## Evidence Tier Framework

Read `references/evidence-tiers.md` for the full framework.

| Tier | Weight | Examples |
|------|--------|---------|
| Tier 1 (definitive, 1.0) | Direct observation | `oc` command output, pod status, MCP search result, log error |
| Tier 2 (strong, 0.5) | Indirect evidence | Knowledge graph dependency, JIRA correlation, pattern match |
| Tier 3 (suggestive, 0.25) | Contextual | Similar past incidents, version-known issues |

Minimum 2 evidence sources per conclusion. Combined weight must be >= 1.8 for high confidence (0.85+).

## MCP Tools Available

When performing cluster diagnostics, these MCPs may be available:

| MCP | Tools | Purpose |
|-----|-------|---------|
| `acm-search` | `find_resources`, `query_database`, `list_tables` | Query K8s resources across all managed clusters |
| `acm-kubectl` | `clusters`, `kubectl`, `connect_cluster` | List managed clusters, run kubectl on hub or spokes |
| `neo4j-rhacm` | `read_neo4j_cypher` | Query component dependency graph |

## Key Investigation Patterns

### Discover MCH Namespace (never hardcode)
```bash
oc get mch -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.status.currentVersion}{"\n"}{end}'
```

### Check foundational health before trusting MCH status
```bash
oc get deploy multiclusterhub-operator -n $MCH_NS --no-headers
oc get deploy multicluster-engine-operator -n multicluster-engine --no-headers
```

### Infrastructure guards (check before pod health)
```bash
oc get networkpolicy -n $MCH_NS --no-headers 2>/dev/null
oc get resourcequota -n $MCH_NS --no-headers 2>/dev/null
oc get endpoints -n $MCH_NS --no-headers 2>/dev/null | awk '$2 == "<none>" {print $1}'
```

### Console image integrity
```bash
oc get deploy console-chart-console-v2 -n $MCH_NS -o jsonpath='{.spec.template.spec.containers[0].image}'
```

## Rules

- ALL cluster operations are strictly **read-only**
- **Allowed:** `oc get`, `oc describe`, `oc logs`, `oc exec` (read-only), `oc adm top`, `oc whoami`, `oc auth can-i`
- **Forbidden:** `oc apply`, `oc create`, `oc delete`, `oc patch`, `oc scale`, `oc edit`, `oc label`, `oc annotate`
- **Discover, don't assume** -- never hardcode MCH namespace, operator names, or pod counts
- **Bottom-up investigation** -- check lower layers before higher layers
- **Evidence-based conclusions** -- minimum 2 sources per finding
- If cluster access fails, note it and proceed with available data
