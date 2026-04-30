---
name: acm-cluster-investigator
description: Deep-dive investigation of individual test failures using the 12-layer diagnostic model. Traces from symptom through infrastructure layers to find root cause with evidence. Use when test failures need root-cause analysis with classification.
compatibility: "Requires oc CLI logged into the test cluster. Uses acm-ui-source (acm-ui MCP) for selector verification. Optional: acm-neo4j-explorer, acm-jira-client, acm-polarion-client. Uses acm-cluster-health for methodology."
---

# ACM Test Failure Investigator

Investigates individual test failures (or groups of related failures) using the 12-layer diagnostic model to find root causes and classify them.

**Standalone operation:** Works independently when given test failure data (test name, error message, selector, feature area) and cluster access. When invoked via the acm-failure-classifier skill, receives richer context (cluster-diagnosis.json findings, extracted_context, pre-computed data).

## Safety

ALL cluster operations are strictly **read-only**.

**Allowed:** oc get, oc describe, oc logs, oc exec (read-only), oc auth can-i, oc adm top, oc api-resources, oc whoami, oc get events

**Forbidden:** oc patch, oc delete, oc apply, oc scale, oc annotate, oc label, oc create, oc edit, oc rollout restart

## Input

You receive:
- Test failure(s): name, error message, selector, assertion values, feature area, extracted_context
- cluster-diagnosis.json excerpt (if available): pre-computed health findings
- Paths: kubeconfig, knowledge directory, core-data.json, repos/
- Feature area: which ACM subsystem

**Pre-filtering by caller:** Tests with after-all hook cascades (NO_BUG) and bulk dead selectors (AUTOMATION_BUG with 3+ tests) are already classified and NOT sent to this skill.

## Methodology

### Step 1: Read Knowledge Files

Before investigating, read (from acm-cluster-health or acm-z-stream-analyzer references):
- diagnostic-layers.md -- 12-layer investigation methodology
- architecture/<area>/architecture.md -- how the subsystem works
- architecture/<area>/failure-signatures.md -- known failure patterns
- diagnostic-traps.md -- where obvious diagnosis is wrong

### Step 2: Map Symptom to Starting Layer

Read `references/symptom-layer-map.md` for the full mapping. Key patterns:

| Error Pattern | Start Layer |
|---|---|
| "element not found", selector missing | 12 (UI) |
| "timed out waiting for" | 12, trace down |
| "Expected X but got Y" (data mismatch) | 11 (Data Flow) |
| "500 Internal Server Error" | 9 (Operator) |
| "403 Forbidden" | 7 (RBAC) |
| "401 Unauthorized" | 6 (Auth) |
| "connection refused/timed out" | 3 (Network) |
| blank page / `class="no-js"` | Could be 3, 6, 9, or 12 |
| `cy.exec()` failed | 1 (Compute/CI) |

### Step 3: Check Pre-Computed Data First

If cluster-diagnosis.json is available, use its findings as Tier 1 evidence. Do NOT re-run oc commands that Stage 1.5 already ran.

### Step 3b: Counterfactual Verification (MANDATORY for cluster-wide issues)

When a cluster-wide issue is found, verify for EACH test: "Would this test PASS if the cluster-wide issue were fixed?"

Read `references/symptom-layer-map.md` for the full verification template table (selector not found, button disabled, timeout, data assertion, blank page, CSS visibility, NetworkPolicy, operator down, ResourceQuota).

**Critical:** When console runs a non-official image, `console_search.found` was checked against the TAMPERED console. Use acm-ui-source `search_code` to check the OFFICIAL source.

### Step 3c: Per-Test Verification Within Groups (MANDATORY)

Read `references/group-verification.md` for the 4-point check:
1. **SAME CODE PATH?** -- same function/method producing the error?
2. **SAME BACKEND COMPONENT?** -- same backend service?
3. **SAME USER ROLE?** -- same authentication/RBAC path?
4. **SAME ERROR ELEMENT?** -- same DOM element (selector, data-testid)?

ALL 4 pass -> apply group result. ANY fails -> split from group, investigate individually.

### Step 4: Trace Down Through Layers

Starting from symptom layer, check each applicable layer. At each:
a) Is this layer healthy FOR THE SPECIFIC COMPONENT this test uses?
b) If unhealthy: root cause or symptom of deeper issue?
c) If healthy: move to next lower layer.

Skip inapplicable layers (no managed clusters -> skip L10, admin test -> skip L6-7).

### Step 5: Investigate WHO/WHY at Root Cause Layer

```bash
oc get <resource> -n <ns> -o jsonpath='{.metadata.ownerReferences}'
oc get <resource> -n <ns> -o jsonpath='{.metadata.labels}'
oc logs <related-pod> --tail=100
oc get events -n <ns> --sort-by=.lastTimestamp
```

Use acm-ui-source `search_code` for intended behavior. Use acm-jira-client `search_issues` for known bugs.

### Step 6: Classify

| Root Cause Scenario | Classification |
|---|---|
| Product operator created broken resource | PRODUCT_BUG |
| Product code logic error | PRODUCT_BUG |
| External action broke infrastructure | INFRASTRUCTURE |
| Environment not configured for test | INFRASTRUCTURE |
| Test selector stale (product renamed) | AUTOMATION_BUG |
| Test assertion expects old behavior | AUTOMATION_BUG |
| Feature intentionally disabled | NO_BUG |
| After-all hook cascading | NO_BUG |

## Evidence Requirements

- Minimum 2 evidence sources per classification
- Tier 1 (weight 1.0): oc output, MCP result, cluster-diagnosis finding
- Tier 2 (weight 0.5): KG analysis, JIRA correlation, knowledge pattern match
- Combined weight >= 1.8 for high confidence (0.85+)

## Output Format

Return JSON with: test_name, root_cause_layer, root_cause_layer_name, root_cause, cause_owner, classification, confidence, evidence_sources (tiered), ruled_out_alternatives, reasoning, recommended_fix, investigation_steps_taken, affected_tests.

## Anti-Patterns

- Do NOT classify based on error message alone -- trace to root cause
- Do NOT assume INFRASTRUCTURE because cluster has issues -- verify each test's error is CAUSED by the issue
- Do NOT blanket-attribute tests to a cluster-wide issue (ANCHORING BIAS)
- Do NOT assume "selectors may be valid in official console" without verifying via acm-ui-source
- Do NOT copy evidence verbatim across tests in a group -- each test needs specific evidence
- Do NOT skip the 4-point verification for subsequent tests in a group
