# Phase C: Correlate

Phase C looks across ALL failures in the run (not one test at a time) to find shared root
causes, so that N failures with one cause are reported as one bug — not N bugs. It runs after
Phase B investigation and before Phase D validation.

## C1: Multi-Evidence Check

Verify each classification carries at least 2 evidence sources satisfying the combination rule
(1 Tier 1 + 1 Tier 2, OR 2 Tier 1, OR 3 Tier 2). The tier weights and the rule are the single
source of truth in `../../acm-z-stream-analyzer/references/evidence-requirements.md`. A test that
cannot clear this bar is flagged for re-investigation in Phase D (D-V1), not finalized.

## C2: Cascading Analysis

Two DISTINCT cascade types. Keep them separate — they collapse failures for different reasons.

### C2a: Component-dependency cascade (-> single PRODUCT_BUG)

When several failing components share an **upstream dependency**, the upstream component is the
root cause and the downstream failures are symptoms, not independent bugs.

**Detection (neo4j-rhacm available):** run the common-dependency query — find dependencies that
2+ failing components share:

```cypher
MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent)
WHERE c.label IN [<failing component labels>]
WITH common, count(DISTINCT c) AS component_count
WHERE component_count >= 2
RETURN common.label, component_count
ORDER BY component_count DESC
```

**On a cascade:**
1. Identify the **root-cause component** (`common.label` with the highest `component_count`).
2. Mark every dependent component's failures as **symptoms** of that root cause.
3. Collapse the group into a **single PRODUCT_BUG** for the root-cause component (the dependents
   do NOT each get their own bug). Set the dependents' `verification_status` to reflect they were
   attributed to the cascade root, and record the cascade in the
   `cascading_failure_analysis` output object (see `output-schema.md`).

**Detection (KG unavailable — fallback):** derive dependency chains from
`${KNOWLEDGE_DIR}/baselines/dependency-chains.yaml` (the shared-DB analogue of the graph). Look up
each failing component's upstream chain and apply the same common-dependency test: if 2+ failing
components resolve to the same upstream root, treat it as the cascade root exactly as above. Note
in the evidence that the dependency link came from the knowledge file (Tier 2), not the live KG.

`knowledge_graph_query` in the output records the Cypher query used, or the
`dependency-chains.yaml` lookup when the fallback path was taken.

### C2b: Infrastructure cascade (distinct case)

When ONE infrastructure issue (e.g. an OOMKilled backend, a NetworkPolicy, a degraded operator)
explains multiple failures, document the cascade so the affected tests share the INFRASTRUCTURE
root cause. This is a separate case from C2a: the shared cause is an infrastructure fault, not a
product component's upstream dependency. Per-test causal-link verification (Phase D-V5 / D4b)
still applies — a degraded subsystem does NOT automatically make every test INFRASTRUCTURE.

## C3: Pattern Correlation

Look for systemic patterns across the run:
- All CLC tests fail -> check hive; all Search tests fail -> check search-postgres; all
  Observability tests fail -> check the observability operator.
- **Bulk selector rule:** if **80% of failures share the same selector** that Phase A/B already
  confirmed dead (`console_search.found=false` in official source), treat it as a bulk
  **AUTOMATION_BUG** with a single root cause (the stale/renamed selector) — **unless
  `recent_selector_changes` hints the selector was removed by a product change**, in which case
  those tests stay on the normal investigation path as PRODUCT_BUG candidates. This
  cross-references already-investigated Phase A/B findings; it does NOT skip per-test
  investigation. It mirrors Phase A4's "dead selector shared by 3+ tests -> AUTOMATION_BUG
  (unless recent_selector_changes hints PRODUCT_BUG)" guard — A4 handles the clear multi-test
  dead selector; C3 catches the near-uniform (>=80%) case across the run's failures.
- Tests across DIFFERENT feature areas with the same error pattern -> suspect infrastructure or
  a shared platform dependency (route back to C2).

## Output

Record cascade findings in the `cascading_failure_analysis` object of `analysis-results.json`
(`analysis_performed`, `root_cause_component`, `root_cause_subsystem`, `dependent_components`,
`tests_affected_by_cascade`, `knowledge_graph_query`). See `output-schema.md` for the field
definitions.
