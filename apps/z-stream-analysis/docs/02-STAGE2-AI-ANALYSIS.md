# Stage 2: AI Analysis (5-Phase Investigation)

The AI agent reads `core-data.json` and produces `analysis-results.json` using a systematic 5-phase investigation framework.

---

## Overview

**Invocation:** The z-stream-analysis agent reads the run directory and applies the 5-phase framework.

**Input:** `core-data.json` (from Stage 1), `repos/` (fallback), MCP servers (ACM-UI, JIRA, Knowledge Graph)

**Output:** `analysis-results.json` (classification per test with evidence)

```
core-data.json ──► AI Agent ──► analysis-results.json
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
      ACM-UI MCP   JIRA MCP   Knowledge
      (20 tools)   (24 tools)  Graph MCP
```

### Full Investigation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE A: Initial Assessment                                        │
│                                                                     │
│  A0: Feature area grounding (read feature_grounding)                │
│  A1: Environment health check                                      │
│      └── env_score < 0.3? ──YES──► ALL TESTS = INFRASTRUCTURE      │
│                │                   (skip Phases B-D)                │
│               NO                                                    │
│                ▼                                                    │
│  A1b: Cluster landscape check (degraded operators?)                 │
│  A2: Failure pattern detection (mass timeout? same selector?)       │
│  A3: Cross-test correlation scan                                    │
│  A3b: Batch KG subsystem context (if KG available)                  │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────────┐
│  PHASE B: Deep Investigation (per test)                             │
│                                                                     │
│  B1: Check extracted_context (test code, page objects, selectors)   │
│  B2: Check timeline_evidence (element_removed? stale_test_signal?) │
│  B3: Check console_log (500s? network errors? auth errors?)        │
│  B4: Query MCP tools (ACM-UI search, JIRA, Knowledge Graph)        │
│  B5: Backend component analysis (detected_components → KG)          │
│  B5b: Targeted pod investigation [conditional]                      │
│        └── Trigger: 500 errors OR ambiguous classification          │
│  B6: Repository deep dive [if extracted_context insufficient]       │
│  B7: Backend cross-check [conditional]                              │
│        └── UI failure + backend component crash?                    │
│            └── YES → set backend_caused_ui_failure = true           │
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
│  PHASE D: 3-Path Classification Routing                             │
│                                                                     │
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
│  D4: Final validation (confirm classification, calc confidence)     │
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
| `test_report.failed_tests[]` | Per-test: error, stack trace, extracted_context, detected_components | Phase B |
| `environment` | Cluster health, environment_score, API status | Phase A |
| `cluster_landscape` | Managed clusters, operators, MCH status, `mch_enabled_components`, resource pressure | Phase A, B |
| `console_log` | Error patterns (has_500_errors, has_network_errors, etc.), key_errors | Phase A, B |
| `feature_grounding` | Tests grouped by feature area with subsystem/component context | Phase A |
| `feature_knowledge` | Playbook readiness, prerequisites, failure paths, KG dependency context, KG status | Phase A, B, D |
| `cluster_access` | API URL, username, password for re-authentication | Phase A (cluster login) |
| `investigation_hints.timeline_evidence` | Element history, modification dates | Phase B |
| `investigation_hints.failed_test_locations` | File paths for failed tests | Phase B |

---

## Phase A: Initial Assessment

**Purpose:** Ground analysis in feature areas, detect global patterns, check cluster health before analyzing individual tests.

```
core-data.json
      │
      ├── A-1: Cluster re-authentication (v3.1)
      │   Read cluster_access from core-data.json
      │   Run: oc login <api_url> --username <user> --password <password>
      │   Verify: oc whoami
      │   If fails: proceed with snapshot data only, reduce confidence by 0.15
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
      │   environment.cluster_connectivity == false?  → ALL TESTS = INFRASTRUCTURE
      │   environment.environment_score < 0.3?      → ALL TESTS = INFRASTRUCTURE
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

**Example:** If `environment.environment_score = 0.15` and `cluster_connectivity = false`, Phase A short-circuits: all tests classified as INFRASTRUCTURE with confidence 0.95.

---

## Phase B: Deep Investigation (Per Test)

**Purpose:** Investigate each failed test individually. All sub-steps are mandatory (B5b and B7 are conditional).

```
For each test in test_report.failed_tests[]:

  B1: Check extracted_context
      ├── test_file.content — actual test code
      ├── page_objects — selector definitions
      └── console_search.found — is selector in product?

  B2: Check timeline_evidence
      ├── element_never_existed → AUTOMATION_BUG signal
      ├── element_removed → AUTOMATION_BUG signal
      └── console_changed_after_automation → stale test signal

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
      └── → Overrides Path A routing in Phase D (routes to Path B2)

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

**Example:** Test `should create cluster` has `extracted_context.console_search.found = false` and `timeline_evidence.element_removed = true`. Two Tier 1 evidence sources pointing to AUTOMATION_BUG.

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
| 1 (Definitive) | 1.0 | 500 errors in log, element_removed=true, env_score<0.3 |
| 2 (Strong) | 0.8 | Selector mismatch, multiple tests same selector |
| 3 (Supportive) | 0.5 | Similar selectors exist, timing issues |

**Example:** Test has `console_search.found=false` (Tier 1) + `element_removed=true` (Tier 1) = 2 Tier 1 sources. Requirement met.

---

## Phase D: 3-Path Classification Routing

**Purpose:** Route each test to the correct classification path based on evidence.

### D-1: Feature Knowledge Override (v3.1)

**Check feature knowledge FIRST.** If a prerequisite is unmet AND Tier 2 playbook investigation confirmed it with live `oc` commands, use the playbook's suggested classification at 0.95 confidence. If a failure path was confirmed, use the path's classification and confidence. If cluster login failed (`cluster_access_available=false`), reduce confidence by 0.15 on all classifications.

### D0: Backend Cross-Check Override (v3.0)

**Check backend cross-check SECOND before 3-path routing.** If Phase B7 determined `backend_caused_ui_failure == true`, route directly to Path B2 regardless of whether the failure looks like a selector mismatch. This prevents misclassifying UI failures caused by backend component crashes (e.g., element not found BECAUSE the backend broke, not because the selector changed).

```
                    Start Classification
                           │
                    ┌──────┴──────┐
                    │ D0: Backend │
                    │ cross-check │
                    │ override?   │
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

| Evidence | Classification | Confidence |
|----------|---------------|------------|
| >50% tests timeout + env unhealthy | INFRASTRUCTURE | 0.80 |
| `cluster_connectivity=false` | INFRASTRUCTURE | 0.95 |
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
    "analyzer_version": "3.1.0"
  },
  "investigation_phases_completed": ["A", "B", "C", "D", "E"],
  "per_test_analysis": [
    {
      "test_name": "should create cluster successfully",
      "test_file": "cypress/e2e/cluster/create.cy.ts",
      "classification": "AUTOMATION_BUG",
      "classification_path": "A",
      "confidence": 0.92,
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
        {"source": "timeline_evidence", "finding": "element_removed=true", "tier": 1}
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

**Known subsystems:** Governance, Search, Cluster, Provisioning, Observability, Virtualization, Console, Infrastructure, Application
