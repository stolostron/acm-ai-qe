---
name: acm-hub-health-check
description: Diagnose ACM hub cluster health using a 6-phase pipeline with 4 depth modes. Checks operators, pods, addons, subsystems, dependency chains, and known failure patterns. Use when asked to check hub health, run diagnostics, troubleshoot ACM issues, or verify cluster state.
compatibility: "Requires oc CLI logged into an ACM hub. Uses acm-cluster-health skill (methodology). Optional MCPs: neo4j-rhacm (dependency analysis), acm-search (fleet queries). Run /onboard to configure."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Hub Health Diagnostic

Diagnoses ACM hub cluster health using a 6-phase pipeline. Works at 4 depth levels from a 30-second sanity check to a 10-minute deep investigation. Produces a structured health report with evidence-based findings.

**Standalone operation:** This skill works independently. Give it cluster access (`oc` logged in) and it runs the full diagnostic. When used with the acm-cluster-health skill, it follows the 12-layer methodology. When used with the neo4j-rhacm MCP, it gets richer dependency analysis. Without those, it still works -- just with less depth.

## Knowledge Directory

KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/hub-health/

## Depth Router

| User Intent | Depth | Phases | Duration |
|-------------|-------|--------|----------|
| "Is my hub alive?", "quick check", "sanity" | Quick | Phase 1 only | ~30s |
| "How's my hub?", "health check", "check my cluster" | Standard | Phases 1-4 | ~2-3 min |
| "Thorough check", "deep audit", "full diagnostic" | Deep | All 6 phases | ~5-10 min |
| "Why are clusters Unknown?", "investigate search" | Targeted | Full depth on specific area | ~3-5 min |

Default to Standard when intent is unclear.

## Phase 1: Discover (all depths)

Inventory what's deployed on the hub. Run these commands:

```bash
oc get mch -A -o yaml
oc get multiclusterengines -A -o yaml
oc get nodes
oc get clusterversion
oc get managedclusters
oc get csv -A -o json
oc whoami --show-server
```

**Critical: Discover MCH namespace first.** From the MCH resource, identify the namespace (NOT always `open-cluster-management` -- can be `ocm` or custom). All subsequent commands use this namespace.

**Operator health (do this immediately after MCH discovery):**
```bash
oc get deploy multiclusterhub-operator -n <mch-ns> --no-headers
oc get deploy multicluster-engine-operator -n multicluster-engine --no-headers
```

If multiclusterhub-operator has 0 replicas: **CRITICAL immediately**. MCH status is stale. ACM is unmanaged. This takes priority over all other findings.

**For Quick depth: STOP HERE.** Report MCH/MCE status, node count, managed cluster count, operator health. Verdict: HEALTHY/DEGRADED/CRITICAL.

### Also discover in Phase 1
```bash
oc get validatingwebhookconfigurations --no-headers
oc get mutatingwebhookconfigurations --no-headers
oc get consoleplugins --no-headers 2>/dev/null
oc get statefulsets -n <mch-ns> --no-headers
oc get statefulsets -n hive --no-headers
```

**If running in z-stream pipeline context:** Read `core-data.json` from the run directory to identify which feature areas have failing tests. Prioritize investigation of those subsystems.

## Phase 2: Learn (Standard+)

Build understanding of healthy vs actual state. Read these knowledge files in order:

1. `${KNOWLEDGE_DIR}/component-registry.md` -- master component inventory
2. `${KNOWLEDGE_DIR}/architecture/acm-platform.md` -- MCH/MCE hierarchy
3. For each affected subsystem: `${KNOWLEDGE_DIR}/architecture/<subsystem>/architecture.md` AND `failure-signatures.md`
4. `${KNOWLEDGE_DIR}/healthy-baseline.yaml` -- expected pod counts, deployment states
5. `${KNOWLEDGE_DIR}/diagnostics/common-diagnostic-traps.md` -- 14 traps
6. `${KNOWLEDGE_DIR}/service-map.yaml` -- service-to-pod endpoint mapping
7. `${KNOWLEDGE_DIR}/webhook-registry.yaml` -- expected webhooks with criticality
8. If managed clusters present: `${KNOWLEDGE_DIR}/architecture/cluster-lifecycle/health-patterns.md`
9. `${KNOWLEDGE_DIR}/diagnostics/diagnostic-layers.md` -- 12-layer framework

**Unknown operator protocol:** For CSVs not in the component registry: (1) note CSV metadata and owned CRDs, (2) check if it has ConsolePlugins registered, (3) check MCH/MCE namespace for related deployments.

Compare cluster topology to knowledge. If knowledge doesn't cover a discovered component, note it for the acm-knowledge-learner skill (if available) or proceed with best-effort analysis.

## Phase 3: Check (Standard+)

Systematic health verification, **bottom-up**. Use the acm-cluster-health skill methodology (12-layer model) if available. If not, follow this layer order:

### Foundational Layers (check FIRST)

**Layers 1-2 (Compute + Control Plane):** Already covered in Phase 1. Verify: all nodes Ready? OCP operators Available? MCH/MCE operators have replicas?

**Layer 3 (Network + Infrastructure Guards):** Check BEFORE pod health.
```bash
oc get networkpolicy -n <mch-ns> --no-headers 2>/dev/null
oc get resourcequota -n <mch-ns> --no-headers 2>/dev/null
oc get endpoints -n <mch-ns> --no-headers 2>/dev/null | awk '$2 == "<none>" {print $1}'
```
ACM does NOT create NetworkPolicies or ResourceQuotas. Any presence is suspicious (Trap 9, Trap 11).

**Layer 4 (Storage):** PVCs Bound? Search-postgres data integrity?
```bash
oc get pvc -n <mch-ns> 2>/dev/null
oc exec deploy/search-postgres -n <mch-ns> -- psql -U searchuser -d search -c "SELECT count(*) FROM search.resources" 2>&1
```
If search pods Running but 0 rows: data lost (Trap 3).

**Layer 5 (Configuration):** MCH component toggles, OLM subscriptions, CatalogSource health.

### Component Layers

**Layers 6-8 (Auth/RBAC/Webhooks):** Check only if relevant errors surfaced in logs.

**Layer 9 (Operators + Pods):**
```bash
oc get pods -n <mch-ns> --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers
oc get pods -n multicluster-engine --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers
oc get pods -n hive --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers
```

Compare pod counts against `${KNOWLEDGE_DIR}/healthy-baseline.yaml`. Check restart counts (flag pods with >3 restarts). Check StatefulSets in hive and observability namespaces.

**Sub-operator CR status checks:**
```bash
oc get search -A -o jsonpath='{range .items[*]}{.metadata.name}: {.status.conditions[*].type}={.status.conditions[*].status}{"\n"}{end}' 2>/dev/null
oc get hiveconfig -o jsonpath='{.items[0].status.conditions}' 2>/dev/null
oc get multiclusterobservability -o jsonpath='{.items[0].status.conditions}' 2>/dev/null
```

**Console image integrity check:**
```bash
oc get deploy console-chart-console-v2 -n <mch-ns> -o jsonpath='{.spec.template.spec.containers[0].image}'
```
Compare against expected prefixes from `healthy-baseline.yaml` (registry.redhat.io/, quay.io/stolostron/). Non-standard image = tampered environment. Apply -0.10 penalty to health score.

**Leader election check (Trap 1b):**
```bash
oc get lease -n <mch-ns> --no-headers
```
Verify lease holders are current. Pods can be Running/Ready but reconciliation stopped if lease is stuck.

For unhealthy pods: `oc logs <pod> --tail=50`, `oc logs <pod> --previous`, `oc get events`. Scan for: OOMKilled, nil pointer, context deadline exceeded, cache sync failures.

**Layer 10 (Cross-Cluster):**
```bash
oc get managedclusteraddons -A --no-headers
```
Compare against `${KNOWLEDGE_DIR}/addon-catalog.yaml`. If ALL addons unavailable: check addon-manager pod first (Trap 7).

**Spoke-side verification (conditional):** If acm-search MCP available AND search-postgres healthy, use `find_resources` for fleet-wide checks. See `${KNOWLEDGE_DIR}/diagnostics/acm-search-reference.md`.

### Application Layers

**Layers 11-12 (Data Flow + UI):** Only check if lower layers healthy but features broken.

### Trap Detection

Walk through ALL 14 traps from `${KNOWLEDGE_DIR}/diagnostics/common-diagnostic-traps.md`. Record each as TRIGGERED, NOT triggered, or N/A.

## Phase 4: Pattern Match (Standard+)

Cross-reference findings against known issues:

1. Read `${KNOWLEDGE_DIR}/failure-patterns.md`
2. Read `${KNOWLEDGE_DIR}/architecture/<subsystem>/known-issues.md` for each affected subsystem
3. Check `${KNOWLEDGE_DIR}/version-constraints.yaml` for version incompatibilities
4. Check `${KNOWLEDGE_DIR}/architecture/infrastructure/post-upgrade-patterns.md` before reporting post-upgrade issues (may be normal settling)

Note JIRA references, fix versions, and cluster-fixability for matched patterns.

## Phase 5: Correlate (Deep)

Trace dependency chains when multiple issues found:

1. Read `${KNOWLEDGE_DIR}/diagnostics/dependency-chains.md` (12 chains)
2. For each chain: check each link against Phase 3 findings. Record broken links and root causes.
3. Use neo4j-rhacm MCP for dependencies not in curated chains (if available)
4. If acm-search MCP available: spoke-side chain verification
5. Weight evidence per `${KNOWLEDGE_DIR}/diagnostics/evidence-tiers.md`: minimum 2 sources per conclusion, at least 1 Tier 1
6. Verify conclusions against trap list -- is this a diagnostic trap?

## Phase 6: Deep Investigate (Deep/Targeted)

For CRITICAL findings or targeted investigations:

- `oc logs <pod> --tail=100` and `--previous`
- `oc get events -n <ns> --sort-by=.lastTimestamp`
- Resource details: `oc describe`, YAML dumps
- Follow `${KNOWLEDGE_DIR}/diagnostics/diagnostic-playbooks.md`
- Read component `data-flow.md` to trace where flow breaks
- Use acm-search MCP for spoke triage when available

## Structured Output (Pipeline Mode)

When used by the acm-z-stream-analyzer (Stage 1.5), produce `cluster-diagnosis.json` instead of a markdown report. Read `references/diagnostic-output-schema.md` for the full JSON schema including:
- `environment_health_score` (weighted penalty formula)
- `health_depth` per subsystem (pod_level/connectivity_verified/data_verified/full)
- `counter_signals` (tests that should NOT be classified as INFRASTRUCTURE)
- `classification_guidance` (pre-classified infrastructure + confirmed healthy areas)
- `attribution_rule` per infrastructure issue (when to attribute + what NOT to attribute)

Write self-healing discoveries to `${KNOWLEDGE_DIR}/learned/` for future runs.

## Report Format (Standalone Mode)

### Verdict (mechanical, no qualifiers)

- **HEALTHY:** All components OK
- **DEGRADED:** Any component WARN, no CRIT
- **CRITICAL:** Any component CRIT

### Per Issue (9 required fields)

Each issue under `### [SEVERITY] <title>` must include:

1. **What** -- problem description
2. **Evidence** -- Tier 1/2 evidence
3. **Root Cause** -- best assessment + confidence level
4. **Layer** -- diagnostic layer identification
5. **Known Issue** -- JIRA ref or "No match"
6. **Fix Version** -- ACM version with fix or "N/A"
7. **Cluster-Fixable** -- Yes / Workaround / No
8. **Impact** -- what is affected
9. **Recommended Action** -- what to do

Use "N/A" or "No match" for fields that don't apply. Never omit fields.

## Safety Rules

**Diagnostic mode is STRICTLY read-only. NEVER modify the cluster during diagnosis.**

Allowed: `oc get`, `oc describe`, `oc logs`, `oc exec` (read-only), `oc adm top`, `oc whoami`, `oc auth can-i`, `oc api-resources`, `oc version`

Forbidden: `oc apply`, `oc create`, `oc delete`, `oc patch`, `oc scale`, `oc edit`, `oc annotate`, `oc label`, `oc rollout restart`

If remediation is needed, use the acm-cluster-remediation skill AFTER diagnosis is complete.

## Gotchas

1. **Stale MCH status (Trap 1)** -- MCH operator at 0 replicas makes MCH status stale. "Running" in MCH status is a lie when the operator that reconciles it is not running. Check operator replicas before trusting MCH.
2. **Search pods running but empty database (Trap 3)** -- All search pods can be Running/Ready while search-postgres has 0 rows. Data was lost (migration failure, PVC issue). Always verify row count, not just pod status.
3. **All addons unavailable (Trap 7)** -- If ALL managed cluster addons show unavailable, check the addon-manager pod first. A single addon-manager failure cascades to every addon across every cluster.
4. **ResourceQuota blocking scheduling (Trap 9)** -- ACM does NOT create ResourceQuotas. If one exists in the MCH namespace, it was added externally and may silently block pod scheduling. Pods stuck in Pending with no events is the symptom.
5. **NetworkPolicy hiding failures (Trap 11)** -- Pods show Running with 0 restarts but cannot communicate. ACM does NOT create NetworkPolicies. External policies can silently break inter-pod traffic while health checks pass.

See `${KNOWLEDGE_DIR}/diagnostics/common-diagnostic-traps.md` for all 14 traps.
