# Stage 2: AI Analysis (12-Layer Diagnostic Investigation)

The AI agent reads `core-data.json` and `cluster-diagnosis.json`, then classifies each test failure using the 12-layer diagnostic model with provably linked grouping, per-test verification, and symmetric counterfactual validation (v4.0).

---

## v3.9 Architecture: Provably Linked Grouping + Per-Test Verification

v3.9 builds on v3.8's layer-based root cause analysis with three key additions that prevent blanket override misclassification:

**Key changes from v3.8.1:**
- **Phase A4 (v3.9):** Provably linked grouping replaces symptom-based grouping. Groups require identical code paths (same selector+function, same before-all hook, same spec+error+line). "Button disabled", "same feature area", and "similar error" are NOT valid grouping criteria.
- **Phase B (v3.9):** Per-test verification within groups. After investigating the first test, a mandatory 4-point check (code path, backend component, user role, error element) verifies each subsequent test. Failures split from the group and receive individual investigation inline.
- **Phase D-V5 (v3.9, updated v4.0):** Expanded counterfactual verification with 9 templates (selector, button-disabled, timeout, data-assertion, blank-page, CSS, NetworkPolicy, operator, ResourceQuota). Symmetric validation: D-V5c validates AUTOMATION_BUG ("does backend confirm test expectation?"), D-V5e validates PRODUCT_BUG ("is product behavior actually correct?"). Plus evidence duplication detection and per-test evidence requirement.
- **Output:** Every test includes `root_cause_layer` (1-12), `root_cause_layer_name`, `investigation_steps_taken`, `cause_owner`, and optional `verification_status` (v3.9)

The 12 layers (bottom to top): Compute (1), Control Plane (2), Network (3), Storage (4), Configuration (5), Authentication (6), Authorization (7), API/CRD/Webhook (8), Operator (9), Cross-Cluster (10), Data Flow (11), UI/Plugin (12).

The 5-phase structure (A-E) is preserved. The layer-based investigation is the methodology used within Phase B. The PR-based routing (PR-1 through PR-7) becomes validation checks in Phase D rather than primary routing.

---

## Overview

**Invocation:** The analysis agent reads the run directory and applies the 12-layer investigation methodology within a 5-phase framework.

**Input:** `core-data.json` + `cluster-diagnosis.json` (from Stages 1/1.5), `repos/` (fallback), MCP servers (ACM-UI, Jenkins, JIRA, Polarion, Knowledge Graph)

**Output:** `analysis-results.json` (classification per test with root cause layer, evidence, and investigation steps)

```
core-data.json ──► AI Agent ──► analysis-results.json
                      │
     ┌────────┬───────┼───────┬──────────┐
     ▼        ▼       ▼       ▼          ▼
  ACM-UI   Jenkins   JIRA  Polarion  Knowledge
  (20)     (11)     (25)   (25)     Graph MCP
```

### Full Investigation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE A: Initial Assessment                                        │
│                                                                     │
│  A0: Feature area grounding (read feature_grounding)                │
│  A1: Environment health check                                      │
│      └── cluster_connectivity == false? ──YES──► ALL = INFRA       │
│                │                                (skip Phases B-D)   │
│               NO (even if score < 0.3, investigate per-test)        │
│                ▼                                                    │
│  A1b: Cluster landscape check (degraded operators?)                 │
│  A2: Failure pattern detection (mass timeout? same selector?)       │
│  A3: Cross-test correlation scan                                    │
│  A3b: Batch KG subsystem context (if KG available)                  │
│  A4: Provably linked grouping (v3.9)                                │
│       ├── Instant: dead selector (3+ tests) → AUTOMATION_BUG        │
│       ├── Instant: after-all hook cascade → NO_BUG                  │
│       ├── Group: same selector+function, same hook, same spec+error │
│       └── Individual: everything else (symptom grouping PROHIBITED) │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│  PHASE B: Deep Investigation (per test/group)                       │
│                                                                     │
│  B1: Check extracted_context (test code, page objects, selectors)   │
│  B2: Check recent_selector_changes + temporal_summary (renamed?)   │
│  B3: Check console_log (500s? network errors? auth errors?)        │
│  B4: Query MCP tools (ACM-UI search, JIRA, Knowledge Graph)        │
│  B5: Backend component analysis (detected_components → KG)          │
│  B5b: Targeted pod investigation [conditional]                      │
│        └── Trigger: 500 errors OR ambiguous classification          │
│  B6: Repository deep dive [if extracted_context insufficient]       │
│  B7: Backend cross-check [conditional]                              │
│        └── UI failure + backend component crash?                    │
│            └── YES → set backend_caused_ui_failure = true           │
│  B7c: Backend health check [via cluster-diagnosis.json]              │
│        └── subsystem unhealthy → Tier 1 INFRASTRUCTURE evidence     │
│  B-V: Per-test verification within groups (v3.9, MANDATORY)         │
│        └── 4-point check: code path, backend, role, element         │
│            └── ANY fails → SPLIT, investigate individually inline   │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│  PHASE C: Cross-Reference Validation                                │
│                                                                     │
│  C1: Multi-evidence check (2+ sources per test? REQUIRED)           │
│  C2: Cascading failure detection (shared dependency via KG?)        │
│  C3: Pattern correlation with Phase A                               │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│  PHASE D: Pre-Routing + 3-Path Classification Routing               │
│                                                                     │
│  PR-1→PR-2→PR-3→PR-5→PR-4 (pre-routing checks)                     │
│  D0: Backend cross-check override                                   │
│      └── backend_caused_ui_failure? ──YES──► Path B2                │
│                │                                                    │
│               NO                                                    │
│                ▼                                                    │
│  ┌──────────────────┬──────────────────┬──────────────────┐         │
│  │    Path A        │    Path B1       │    Path B2       │         │
│  │ Selector         │ Timeout          │ Everything else  │         │
│  │ mismatch         │ (non-selector)   │ + backend        │         │
│  │                  │                  │   override       │         │
│  │ → AUTOMATION_BUG │ → INFRASTRUCTURE │ → JIRA lookup    │         │
│  │                  │                  │   → PRODUCT_BUG  │         │
│  │                  │                  │   → AUTO_BUG     │         │
│  │                  │                  │   → MIXED/FLAKY/ │         │
│  │                  │                  │     NO_BUG/      │         │
│  │                  │                  │     UNKNOWN      │         │
│  └──────────────────┴──────────────────┴──────────────────┘         │
│                                                                     │
│  D-V5: Expanded counterfactual verification (v3.9/v4.0, MANDATORY)  │
│       └── 9 templates: selector, button-disabled, timeout,          │
│           data-assertion, blank-page, CSS, NetworkPolicy,           │
│           operator, ResourceQuota                                   │
│       └── Symmetric validation (v4.0):                              │
│           D-V5c: AUTOMATION_BUG — "does backend confirm test        │
│                  expectation?" If backend disagrees, reconsider.    │
│           D-V5e: PRODUCT_BUG — "is product behavior actually        │
│                  correct?" If product works as designed, reconsider.│
│       └── Layer discrepancy (v4.0): lower layer healthy but higher  │
│           layer defective = Tier 1 PRODUCT_BUG evidence             │
│       └── Evidence duplication: 5+ identical → flag & verify 2      │
│       └── Per-test evidence: cluster-wide-only → confidence ≤ 0.60 │
│  D4: Final validation (confirm classification, calc confidence)     │
│  D4b: Causal link verification (v3.3)                               │
│       └── Every test in dominant pattern must have causal mechanism  │
│  D5: Counter-bias validation (v3.2, strengthened v3.3)              │
│       └── 3-test threshold: if 3+ tests share root_cause,           │
│           at least 1 must be independently re-investigated          │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│  PHASE E: Feature Context & JIRA Correlation                        │
│                                                                     │
│  E0: Build subsystem context (incremental from A3b)                 │
│  E1: Carry forward Path B2 findings                                 │
│  E2: Search JIRA for feature stories / PORs                         │
│  E3: Read acceptance criteria, linked PRs                           │
│  E4: Search JIRA for related bugs                                   │
│  E5: Known issue matching + feature-informed validation             │
│  E6: Create/link JIRA issues (optional)                             │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          ▼
              analysis-results.json
```

---

## Input Data

The agent reads `core-data.json` which contains:

| Top-Level Key | Contents | Used In |
|---------------|----------|---------|
| `metadata` | Jenkins URL, gathered timestamp, version | All phases |
| `jenkins` | Job name, build number, result, parameters | Phase A |
| `test_report.summary` | Total/passed/failed counts, pass rate | Phase A |
| `test_report.failed_tests[]` | Per-test: error, stack trace, extracted_context (incl. `assertion_analysis`, `failure_mode_category`), detected_components | Phase B, D |
| `environment` | Cluster connectivity status | Phase A |
| `cluster_landscape` | Managed clusters, operators, MCH status, `mch_enabled_components`, resource pressure | Phase A, B |
| `console_log` | Error patterns (has_500_errors, has_network_errors, etc.), key_errors | Phase A, B |
| `feature_grounding` | Tests grouped by feature area with subsystem/component context | Phase A |
| `feature_knowledge` | Playbook readiness, prerequisites, failure paths, KG dependency context, KG status | Phase A, B, D |
| `cluster_access` | API URL, username, `kubeconfig_path`, `mch_namespace` for re-authentication | Phase A (cluster login) |
| `cluster_oracle` | Feature context: dependency health, knowledge context, Polarion discovery, overall feature health | Phase A, B, D |
| `cluster_health` | Deferred to Stage 1.5 (`cluster-diagnosis.json`) | Phase A-0 |

The agent also reads `cluster-diagnosis.json` (Stage 1.5 output):

| Key | Contents | Used In |
|-----|----------|---------|
| `environment_health_score` | Float 0.0-1.0, weighted penalty formula | Phase A1 |
| `subsystem_health` | Per-subsystem status, root cause, evidence tier, traps checked | Phase A-0, B, D |
| `operator_health` | Per-operator desired/available replicas, status | Phase A-0, B |
| `infrastructure_issues` | Node pressure, NetworkPolicy, ResourceQuota, cert expiry, tampered image | Phase A-0, D |
| `classification_guidance` | Pre-classified INFRASTRUCTURE, confirmed healthy areas | Phase A-0, D |
| `counter_signals` | Potential false INFRASTRUCTURE, dead selectors, context notes | Phase D |
| `image_integrity` | Console image validation against expected registries | Phase B, D |

---

## Phase A: Initial Assessment

**Purpose:** Ground analysis in feature areas, detect global patterns, check cluster health before analyzing individual tests.

```
core-data.json + cluster-diagnosis.json
      │
      ├── A-0: Read cluster diagnostic (v4.0)
      │   Read cluster-diagnosis.json for environment_health_score,
      │   subsystem_health, operator_health, infrastructure_issues,
      │   classification_guidance, counter_signals, image_integrity
      │   Map infrastructure issues to affected feature areas
      │
      ├── A-1: Cluster re-authentication (v3.5)
      │   Read cluster_access.kubeconfig_path from core-data.json
      │   Verify: oc whoami --kubeconfig <kubeconfig_path>
      │   Use --kubeconfig on ALL oc commands throughout Stage 2
      │   If kubeconfig_path is null or oc whoami fails: proceed with snapshot data only, reduce confidence by 0.15
      │
      ├── A0: Feature area grounding (v3.0)
      │   Read feature_grounding → map tests to subsystems/components
      │
      ├── A0b: Review feature knowledge (v3.1)
      │   Read feature_knowledge → architecture, prerequisites, pre-matched failure paths
      │   Review KG dependency context per feature area
      │
      ├── A0c: Run Tier 0 health snapshot (v3.1)
      │   Live commands: oc get mch, managedclusters, clusteroperators, adm top, non-healthy pods
      │   Compare live state against cluster_landscape snapshot from Stage 1
      │
      ├── A1: Environment health check
      │   cluster_diagnosis.cluster_connectivity == false?  → ALL TESTS = INFRASTRUCTURE
      │   cluster_diagnosis.environment_health_score < 0.3? → INFRASTRUCTURE default hypothesis
      │
      ├── A1b: Cluster landscape check (v3.0)
      │   Read cluster_landscape → check degraded operators, resource pressure
      │   Degraded operator matching feature area? → backend may cause UI failures
      │
      ├── A2: Failure pattern detection
      │   console_log.has_network_errors + majority timeout? → INFRASTRUCTURE
      │   All tests fail with same selector? → single root cause
      │   Mass timeouts (>50% of failures)? → likely INFRASTRUCTURE
      │
      ├── A3: Cross-test correlation scan
      │   Shared selectors across tests? → group analysis
      │   Same component in multiple errors? → cascading failure candidate
      │
      └── A3b: Subsystem context building via KG (v3.0)
          Batch-query Knowledge Graph for all unique subsystems
          Store subsystem_context for use throughout Phases B-E
          (Replaces per-test KG queries; makes Phase E0 incremental)
```

### A0: Feature Area Grounding (v3.0)

Read `feature_grounding` from core-data.json. This tells you WHAT feature each test validates before analyzing WHY it failed. Use this to focus investigation on relevant subsystem components, know which namespaces to check for pod health, and understand investigation focus per feature area.

### A1b: Cluster Landscape Check (v3.0)

Read `cluster_landscape` from core-data.json. Check for degraded operators overlapping with feature area components, resource pressure (CPU/memory), MCH status, and managed cluster readiness. A degraded operator matching a feature area component signals that backend issues may be causing UI failures.

### A3b: Subsystem Context Building (v3.0)

If Knowledge Graph is available AND `feature_grounding` identifies components, batch-query subsystem context for all unique subsystems. This stores context for use throughout Phases B-E and makes Phase E0 incremental rather than building context from scratch.

**Example:** If `cluster_diagnosis.cluster_connectivity = false`, Phase A short-circuits: all tests classified as INFRASTRUCTURE with confidence 0.95. If `environment_health_score < 0.3`, INFRASTRUCTURE is the default hypothesis but per-test analysis still runs.

---

## Phase B: Deep Investigation (Per Test)

**Purpose:** Investigate each failed test individually. All sub-steps are mandatory (B5b and B7 are conditional).

```
For each test in test_report.failed_tests[]:

  B1: Check extracted_context
      ├── test_file.content — actual test code
      ├── page_objects — selector definitions
      └── console_search.found — is selector in product?

  B2: Check recent_selector_changes + temporal_summary
      ├── change_detected + intent_assessment → intentional rename or accidental removal
      ├── stale_test_signal → product changed after automation
      ├── classification_hint → AUTOMATION_BUG or PRODUCT_BUG
      └── temporal_summary.days_difference → how long since product/automation changed

  B3: Check console_log evidence
      ├── 500/502/503 errors → PRODUCT_BUG signal
      ├── Network errors → INFRASTRUCTURE signal
      └── Auth errors → PRODUCT_BUG signal

  B4: Query MCP tools (if needed)
      ├── ACM-UI: search_code, find_test_ids, get_component_source
      ├── JIRA: search_issues (for related bugs)
      └── Knowledge Graph: read_neo4j_cypher (component dependencies)

  B5: Backend component analysis
      ├── detected_components → Knowledge Graph query
      ├── Cascading failure detection
      └── Subsystem context building

  B5b: Targeted pod investigation (v3.0, conditional)
      ├── Trigger: 500 errors detected OR ambiguous classification
      ├── Check pod status for feature area's key_components
      ├── CrashLoopBackOff → PRODUCT_BUG signal
      └── Pod Pending (resource issues) → INFRASTRUCTURE signal

  B6: Repository deep dive (when extracted_context insufficient)
      ├── Read additional files from repos/
      ├── Check git history
      └── Trace import chains

  B7: Backend cross-check (v3.0)
      ├── For element_not_found / timeout failures:
      │   Check console log for 500s from feature area components
      │   Check cluster_landscape for non-Ready components
      │   Check B5b pod diagnostics for crashes
      ├── If backend caused UI failure:
      │   Set backend_caused_ui_failure = true
      ├── → Overrides Path A routing in Phase D (routes to Path B2)
      │
      └── B7c: Backend health check (via cluster-diagnosis.json)
          ├── Check subsystem_health for test's feature area
          ├── Subsystem degraded/critical → Tier 1 INFRASTRUCTURE evidence
          └── Subsystem healthy → backend ruled out, focus on selectors/JIRA

  B8: Tiered playbook investigation (v3.1)
      ├── Check prerequisites with live oc commands
      ├── Execute failure path investigation steps from matched playbook paths
      └── Compare results against expected outcomes

  B8b: If Tier 2 confirms a failure path (v3.1)
      └── Query KG for upstream dependencies of confirmed failing component
          └── If upstream also failing → root cause is upstream

  B8c: If Tier 1-2 don't explain → run Tier 3 data flow tracing (v3.1)
      └── Use KG dependency context + playbook architecture.data_flow

  B8d: If Tier 1-3 don't explain OR multiple areas failing → run Tier 4 (v3.1)
      └── Cross-namespace event scan, network checks, KG cascading analysis
```

**Example:** Test `should create cluster` has `extracted_context.console_search.found = false` and `recent_selector_changes.change_detected = true, direction = removed_from_product`. Two Tier 1 evidence sources pointing to AUTOMATION_BUG.

---

## Phase C: Cross-Reference Validation

**Purpose:** Verify every classification has 2+ evidence sources before proceeding.

```
C1: Multi-evidence requirement check
    └── Does each test have 2+ evidence sources? (REQUIRED)
        Minimum: 1 Tier 1 + 1 Tier 2, OR 2 Tier 1, OR 3 Tier 2

C2: Cascading failure detection
    └── Multiple tests failing from same component?
        → Query Knowledge Graph for dependency chain
        → Group under single root cause if confirmed

C3: Pattern correlation with Phase A
    └── Do individual findings match Phase A patterns?
        → Strengthen or weaken initial hypotheses
```

**Evidence tiers:**

| Tier | Weight | Examples |
|------|--------|----------|
| 1 (Definitive) | 1.0 | 500 errors in log, element_removed=true, env_score<0.3, probe response_valid=false |
| 2 (Strong) | 0.8 | Selector mismatch, multiple tests same selector |
| 3 (Supportive) | 0.5 | Similar selectors exist, timing issues |

**Example:** Test has `console_search.found=false` (Tier 1) + `element_removed=true` (Tier 1) = 2 Tier 1 sources. Requirement met.

---

## Phase D: Pre-Routing + 3-Path Classification Routing

**Purpose:** Apply pre-routing checks that can short-circuit classification, then route remaining tests through the 3-path routing based on evidence.

### PR-1: Blank Page / No-JS Pre-Check (v3.2)

**Check FIRST.** If a test's error shows a blank page (`class="no-js"`, empty body, zero interactive elements), the page failed to render — not a selector mismatch. Check the feature area's prerequisites (AAP operator for Automation, IDP for RBAC, CNV for Virtualization). If prerequisite missing → INFRASTRUCTURE (0.90). If all prerequisites met → AUTOMATION_BUG (0.80). **Short-circuits standard routing.**

### PR-2: Hook Failure Deduplication (v3.2)

If a test name starts with `"after all" hook` or `"after each" hook` AND a prior test in the same spec already failed AND the error is a DOM/jQuery error → classify as NO_BUG (0.90) with reasoning "cascading cleanup failure." **Short-circuits standard routing.** Does NOT apply to `before all` hooks (those are setup failures).

### PR-3: Temporal Evidence Check (v3.2)

If `extracted_context.temporal_summary.stale_test_signal == true` AND `product_commit_message` mentions refactor/rename/PF6/migration → strong signal for PRODUCT_BUG (0.85). This sets a hypothesis validated through Path B2 investigation. **Does NOT short-circuit** — adds evidence for standard routing.

### PR-5: Data Assertion Pre-Check (v3.3)

If `extracted_context.assertion_analysis.has_data_assertion == true` AND `extracted_context.failure_mode_category == "data_incorrect"`, the test failed because returned data did not match expected values — not because of a missing element or infrastructure issue. Sets a PRODUCT_BUG hypothesis with 0.80-0.85 confidence. **Does NOT short-circuit** — adds evidence for standard routing, validated through Path B2 investigation.

### PR-6: Backend Health Check (via cluster-diagnosis.json)

Checks `subsystem_health` from `cluster-diagnosis.json` for the test's feature area. If the subsystem is degraded/critical and the root cause explains the test's error, this is Tier 1 INFRASTRUCTURE evidence. If the subsystem is healthy, backend is ruled out. Backend health investigation is handled by Stage 1.5 (cluster-diagnostic agent) with comprehensive pod health, operator status, console image integrity validation, and dependency chain analysis. Also checks `image_integrity` — if the console image is non-standard, CSS/rendering failures should be investigated as potential PRODUCT_BUG rather than AUTOMATION_BUG.

### PR-6b: Polarion Expected Behavior Check (v4.0)

If Polarion test case setup describes expected behavior AND the subsystem is healthy AND the behavior is not delivered, signals PRODUCT_BUG (0.80). Also detects layer discrepancies (lower layer healthy, higher layer defect) as Tier 1 PRODUCT_BUG evidence. See `knowledge/diagnostics/diagnostic-layers.md` "Layer Discrepancy Detection".

### PR-7: Environment/Diagnostic Context Signals (v4.0)

**v4.0 change:** PR-7 produces CONTEXT SIGNALS, not binding classifications. Infrastructure findings from `cluster-diagnosis.json` are inputs to the per-test layer investigation, not pre-determined classifications. The layer investigation determines whether each test's specific error is caused by the infrastructure signal. Key behaviors:

- **Context, not classification:** Degraded dependencies are STRONG signals but do NOT produce binding INFRASTRUCTURE classifications. The classification comes from the layer investigation.
- **Additive, not override:** Per-test evidence takes precedence. If `console_search.found=false`, classify as AUTOMATION_BUG regardless of infrastructure signals.
- **Mandatory reads:** Agent MUST read `knowledge/architecture/<area>/failure-signatures.md` before applying signals; pattern matches take precedence.
- **Full per-test analysis required:** Every test entry must include error message, specific element/selector, evidence sources, and recommended fix.

### PR-4: Feature Knowledge Override (v3.1)

**Check feature knowledge.** If a prerequisite is unmet AND Tier 2 playbook investigation confirmed it with live `oc` commands, use the playbook's suggested classification at 0.95 confidence. If a failure path was confirmed, use the path's classification and confidence. If cluster login failed (`cluster_access_available=false`), reduce confidence by 0.15 on all classifications.

### D0: Backend Cross-Check Override (v3.0)

**Check backend cross-check before 3-path routing.** If Phase B7 determined `backend_caused_ui_failure == true`, route directly to Path B2 regardless of whether the failure looks like a selector mismatch. This prevents misclassifying UI failures caused by backend component crashes (e.g., element not found BECAUSE the backend broke, not because the selector changed).

```
                    Start Classification
                           │
                    ┌──────┴──────┐
                    │ PR-1: Blank │
                    │ page check  │◄── Short-circuits if blank page + missing prereq
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ PR-2: Hook  │
                    │ dedup check │◄── Short-circuits if cascading after-all hook
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │PR-3:Temporal│
                    │  evidence   │◄── Sets hypothesis, does NOT short-circuit
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │PR-5: Data   │
                    │ assertion   │◄── Sets PRODUCT_BUG hypothesis if data assertion
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │PR-6:Backend│
                    │health check│◄── Via cluster-diagnosis.json (v4.0)
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │PR-6b:Polar- │
                    │ion expected │◄── PRODUCT_BUG fast-path (v4.0)
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │PR-7:Context │
                    │  signals   │◄── ADDITIVE, not binding (v4.0)
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │PR-4:Feature │
                    │ knowledge   │◄── Playbook override if confirmed
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ D0: Backend │
                    │ cross-check │
                    └──────┬──────┘
                           │
              ┌── YES ─────┴───── NO ──┐
              │                        │
              │           ┌────────────┼────────────┐
              │           ▼            ▼            ▼
              │      ┌─────────┐ ┌──────────┐ ┌──────────┐
              │      │ PATH A  │ │ PATH B1  │ │ PATH B2  │
              │      │Selector │ │ Timeout  │ │Everything│
              │      │mismatch │ │(non-sel) │ │  else    │
              │      └────┬────┘ └────┬─────┘ └────┬─────┘
              │           │           │            │
              ▼           ▼           ▼            ▼
           PATH B2   AUTOMATION   INFRA-       JIRA
           (backend  _BUG         STRUCTURE    Investigation
            caused)                                │
                                          ┌────────┼────────┐
                                          ▼        ▼        ▼
                                     PRODUCT   AUTOMATION  OTHER
                                     _BUG      _BUG        (MIXED,
                                                           FLAKY,
                                                           NO_BUG,
                                                           UNKNOWN)
```

### Path A — Selector Mismatch

| Evidence | Classification | Confidence |
|----------|---------------|------------|
| `element_not_found` + `console_search.found=false` | AUTOMATION_BUG | 0.92 |
| `element_removed=true` in timeline | AUTOMATION_BUG | 0.88 |
| `failure_type=element_not_found` + no 500 errors | AUTOMATION_BUG | 0.85 |
| Timeout waiting for missing selector | AUTOMATION_BUG | 0.80 |

### Path B1 — Timeout (Non-Selector)

Uses per-feature-area health from `cluster-diagnosis.json` subsystem_health for graduated confidence (v4.0). Replaces the binary 0.5 infrastructure threshold.

| Evidence | Classification | Confidence |
|----------|---------------|------------|
| `cluster_connectivity=false` | INFRASTRUCTURE | 0.95 |
| Feature area health < 0.3 (definitive) | INFRASTRUCTURE | 0.90 |
| Feature area health 0.3-0.5 (strong) | INFRASTRUCTURE | 0.80 |
| Feature area health 0.5-0.7 (moderate) | INFRASTRUCTURE | 0.70 |
| Feature area health >= 0.7 (none) | Route to Path B2 | — |
| >50% tests timeout + env unhealthy | INFRASTRUCTURE | 0.80 |
| Multiple unrelated tests timeout | INFRASTRUCTURE | 0.75 |

### Path B2 — Everything Else (JIRA Investigation)

| Evidence | Classification | Confidence |
|----------|---------------|------------|
| 500/5xx errors in console_log | PRODUCT_BUG | 0.90 |
| Backend component error | PRODUCT_BUG | 0.85 |
| Feature story contradicts behavior | PRODUCT_BUG | 0.85 |
| Assertion failed + test logic wrong | AUTOMATION_BUG | 0.75 |
| Multiple distinct causes | MIXED | varies |
| Passes on retry, no code changes | FLAKY | 0.80 |
| Expected given intentional changes | NO_BUG | 0.85 |
| Insufficient evidence | UNKNOWN | <0.50 |

### D4: Final Validation

For each test, the agent:
1. Confirms classification against evidence
2. Calculates final confidence score
3. Rules out alternative classifications with reasoning
4. Documents why alternatives don't fit

### D4b: Per-Test Causal Link Verification (v3.3)

Every test attributed to a dominant pattern must have a documented causal mechanism linking the pattern to that specific test's failure. If a test's `failure_mode_category` is incompatible with the proposed root cause, it must be independently re-investigated rather than grouped.

**Compatibility matrix (examples):**

| Root Cause Pattern | Compatible `failure_mode_category` | Incompatible |
|---|---|---|
| Pod restarts / CrashLoopBackOff | `render_failure`, `timeout_general`, `server_error` | `data_incorrect` |
| Selector removal | `element_missing`, `assertion_logic` | `data_incorrect`, `server_error` |
| API data regression | `data_incorrect`, `assertion_logic` | `element_missing`, `render_failure` |
| Network partition | `timeout_general`, `render_failure`, `server_error` | `data_incorrect` |

### D5: Counter-Bias Validation (v3.2, strengthened v3.3)

Self-check before finalizing any classification to counter routing bias. **3-test threshold rule (v3.3):** if 3 or more tests share the same `root_cause`, at least 1 must be independently re-investigated from scratch (ignoring the dominant pattern) to confirm the grouping is justified.

---

## Phase E: Feature Context & JIRA Correlation

**Purpose:** Understand what the feature should do, find related issues, validate classification against feature intent.

```
E0: Build subsystem context (Knowledge Graph) — incremental in v3.0
    Uses pre-built context from Phase A3b; only queries for new components
    detected_components → Knowledge Graph → subsystem + related components

E1: Carry forward Path B2 findings
    If Path B2 was used → skip duplicate JIRA queries

E2: Search for feature stories and PORs (JIRA)
    Search strategies (in order):
    1. Polarion ID from test name
    2. Component name + "story" or "feature"
    3. Subsystem + keywords

E3: Read acceptance criteria, linked PRs
    Feature story details inform expected behavior

E4: Search JIRA for related bugs
    JQL: project=ACM AND type=Bug AND component IN (...)
    Match against current failure signature

E5: Known issue matching + feature-informed validation
    Does classification match feature intent?
    Is this a known bug already filed?

E6: Create/link issues (optional)
    If confirmed new bug → offer to create JIRA issue
```

**Graceful degradation:**

| Unavailable Service | Fallback |
|---------------------|----------|
| Knowledge Graph | Use ComponentExtractor's `subsystem` field |
| JIRA MCP | Skip E2-E5, retain Phase D classification |
| No detected_components | Use test name + feature area keywords |
| No Polarion ID | Fall through to component/subsystem search |

**Example:** Test fails with 500 error from `search-api`. Knowledge Graph shows `search-api` depends on `search-collector`. JIRA search finds ACM-12345 "Search API 500 on large result sets" — matches the failure. Classification: PRODUCT_BUG confirmed with JIRA correlation.

---

## MCP Tool Usage Matrix

> For comprehensive MCP documentation with flow diagrams, scenarios, and degradation behavior, see [05-MCP-INTEGRATION.md](05-MCP-INTEGRATION.md).

| Trigger | Tool | Purpose |
|---------|------|---------|
| Start of investigation | `set_acm_version('2.16')` | Set correct ACM Console branch |
| VM test failure | `detect_cnv_version` | Auto-set kubevirt-plugin branch |
| Selector not found | `get_acm_selectors('catalog', 'clc')` | Check QE-proven selectors |
| Cross-repo search | `search_code('selector', 'acm')` | GitHub code search |
| Verify UI text | `search_translations('Create cluster')` | i18n lookup |
| Component error | `read_neo4j_cypher` | Dependency query |
| Any classification | `search_issues` (JIRA) | Related bug lookup |
| Feature context | `get_issue` (JIRA) | Read feature story details |

---

## Output Schema: analysis-results.json

```json
{
  "analysis_metadata": {
    "jenkins_url": "https://jenkins.example.com/job/acm-e2e/123/",
    "analyzed_at": "2026-02-05T12:30:00Z",
    "analyzer_version": "4.0.0"
  },
  "investigation_phases_completed": ["A", "B", "C", "D", "E"],
  "per_test_analysis": [
    {
      "test_name": "should create cluster successfully",
      "test_file": "cypress/e2e/cluster/create.cy.ts",
      "classification": "AUTOMATION_BUG",
      "classification_path": "A",
      "confidence": 0.92,
      "failure_mode_category": "element_missing",
      "assertion_analysis": { "has_data_assertion": false },
      "error": {
        "message": "Timed out: Expected to find '#create-btn'",
        "type": "element_not_found"
      },
      "reasoning": {
        "summary": "Selector '#create-btn' not found in product code",
        "evidence": [
          "console_search.found=false for '#create-btn'",
          "Timeline shows element was removed 2 weeks ago"
        ],
        "conclusion": "Test references a selector removed from product"
      },
      "evidence_sources": [
        {"source": "console_search", "finding": "found=false", "tier": 1},
        {"source": "recent_selector_changes", "finding": "change_detected, direction=removed_from_product", "tier": 1}
      ],
      "ruled_out_alternatives": [
        {
          "classification": "PRODUCT_BUG",
          "reason": "No 500 errors in console log, element intentionally removed"
        },
        {
          "classification": "INFRASTRUCTURE",
          "reason": "Environment score 0.95, cluster fully healthy"
        }
      ],
      "root_cause_layer": 12,
      "root_cause_layer_name": "UI / Plugin / Rendering",
      "investigation_steps_taken": [
        "Layer 12: Selector '#create-btn' not in product source (console_search.found=false) -> ROOT CAUSE (stale test selector)"
      ],
      "cause_owner": "test code",
      "verification_status": "individually_investigated",
      "recommended_fix": {
        "action": "Update selector to '#cluster-create-btn'",
        "steps": [
          "Update cypress/views/cluster.js: createButton → '#cluster-create-btn'",
          "Verify new selector exists in product code"
        ],
        "owner": "Automation Team"
      },
      "jira_correlation": {
        "search_performed": true,
        "related_issues": [],
        "match_confidence": "none"
      }
    }
  ],
  "common_patterns": [
    "2 tests share the same removed selector '#create-btn'"
  ],
  "summary": {
    "total_failures": 3,
    "overall_classification": "AUTOMATION_BUG",
    "overall_confidence": 0.90,
    "by_classification": {
      "AUTOMATION_BUG": 2,
      "PRODUCT_BUG": 1
    },
    "data_assertion_failures": 0,
    "feature_area_health": {
      "CLC": 0.85,
      "Search": 0.92
    },
    "priority_order": [
      {
        "test": "should create cluster successfully",
        "priority": "HIGH",
        "classification": "AUTOMATION_BUG",
        "reason": "Blocks cluster creation test suite"
      }
    ]
  }
}
```

---

## ACM Console Directory Mapping

When investigating UI failures, these patterns map test areas to product source locations:

| Test Pattern | Console Directory |
|--------------|-------------------|
| `*cluster*` | `frontend/src/routes/Infrastructure/Clusters/` |
| `*policy*`, `*governance*` | `frontend/src/routes/Governance/` |
| `*application*` | `frontend/src/routes/Applications/` |
| `*vm*`, `*kubevirt*` | `repos/kubevirt-plugin/src/` |
| `*credential*` | `frontend/src/routes/Credentials/` |
| `*search*` | `frontend/src/routes/Search/` |

---

## Knowledge Graph Queries

For backend component errors, query RHACM component dependencies:

```cypher
-- Find what depends on a failing component
MATCH (dep)-[:DEPENDS_ON]->(c:RHACMComponent)
WHERE c.label =~ '(?i).*search-api.*'
RETURN dep.label as dependent

-- Find what a component depends on
MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep)
WHERE c.label =~ '(?i).*search-api.*'
RETURN dep.label as dependency
```

**Known ComponentExtractor subsystems:** Governance, Search, Cluster, Provisioning, Observability, Virtualization, Console, Infrastructure, Application

**Known FeatureAreaService feature areas:** GRC, Search, CLC, Observability, Virtualization, Application, Console, Infrastructure, RBAC, Automation
