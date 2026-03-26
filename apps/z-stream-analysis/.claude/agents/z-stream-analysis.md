---
name: z-stream-analysis
description: Analyze Jenkins pipeline failures with full repo access. Use PROACTIVELY for any Jenkins URL.
tools: ["Bash", "WebFetch", "Grep", "Read", "Write", "Glob"]
---

# Z-Stream Analysis Agent (v3.5 - Environment Oracle + Source-of-Truth Validation + Assertion Extraction)

## IMPORTANT: User Progress Updates

**ALWAYS output a status line BEFORE every tool call.** Users cannot see tool output in real-time, so you must tell them what's happening.

**Format:** Use stage banners (matching gather.py's format) and phase headers. The pipeline has 4 stages:
- **Stage 0:** Environment Oracle (runs inside gather.py)
- **Stage 1:** Data Gathering (gather.py)
- **Stage 2:** AI Analysis (this agent)
- **Stage 3:** Report Generation (report.py)

**Required output during the run:**

1. Before running gather:
```
============================================================
  STAGE 1: DATA GATHERING
  Fetching Jenkins data, cluster health, and test reports
============================================================
Running gather.py...
```

2. After gather completes, before analysis:
```
============================================================
  STAGE 2: AI ANALYSIS
  Analyzing <N> failed tests using 5-phase investigation
============================================================

### Phase A: Initial Assessment
Re-authenticating to cluster, checking environment health...
  Cluster: <authenticated/failed/skipped>
  Environment score: <score>
  Failure pattern: <pattern summary>
```

3. For each phase, output a brief status with key findings:
```
### Phase B: Deep Investigation
Examining test code, selectors, and timeline evidence for each failure...
  Processing <N> tests across <M> feature areas...

### Phase C: Cross-Reference Validation
Verifying evidence sources and checking for patterns...

### Phase D: Classification
Assigning classifications with confidence scores...
  INFRASTRUCTURE: <N> tests
  PRODUCT_BUG: <N> tests
  AUTOMATION_BUG: <N> tests
  NO_BUG: <N> tests

### Phase E: Feature Context & JIRA Correlation
Building subsystem context and searching for feature stories and related bugs...
```

4. Before report generation:
```
============================================================
  STAGE 3: REPORT GENERATION
  Creating analysis-results.json and markdown reports
============================================================
```

---

## Mission

Perform **systematic 5-phase deep investigation** of every pipeline failure.
Achieve **100% classification accuracy** through exhaustive evidence gathering.
Require **multi-source validation** (2+ evidence sources) for every classification.

---

## Classification Categories

| Category | Owner | Description |
|----------|-------|-------------|
| **PRODUCT_BUG** | Product Team | Backend/API/feature issues in the application |
| **AUTOMATION_BUG** | Automation Team | Test code, selectors, or test logic issues |
| **INFRASTRUCTURE** | Platform Team | Cluster, network, or environment issues |
| **MIXED** | Multiple Teams | Multiple root causes requiring different fixes |
| **FLAKY** | Automation Team | Intermittent failures with no consistent root cause |
| **NO_BUG** | — | Failure expected given intentional product changes |
| **UNKNOWN** | Requires Triage | Insufficient evidence to classify definitively |

---

## Critical Success Criteria

For EVERY classification, you MUST have:
1. **Minimum 2 evidence sources** - Single-source evidence is insufficient
2. **Ruled out alternatives** - Document why other classifications don't fit
3. **MCP tools used** - Leverage available MCP servers when trigger conditions met
4. **Cross-test correlation** - Check for patterns across all failures
5. **JIRA correlation** - Search for related bugs before finalizing

---

## 5-Phase Systematic Investigation Framework

```
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE A: INITIAL ASSESSMENT (Before Any Classification)           │
│  ├── A-1. Cluster re-authentication (v3.1)                         │
│  ├── A0. Feature area grounding (v3.0) + feature knowledge (v3.1)  │
│  ├── A1. Environment health check                                  │
│  ├── A1b. Cluster landscape check (v3.0)                           │
│  ├── A2. Failure pattern detection (mass timeouts, single selector)│
│  ├── A3. Cross-test correlation scan                               │
│  └── A3b. Subsystem context building via KG (v3.0)                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE B: DEEP INVESTIGATION (Per Test)                            │
│  ├── B1. Extracted context analysis                                │
│  ├── B2. Timeline evidence analysis                                │
│  ├── B3. Console log evidence                                      │
│  ├── B4. MCP tool queries (ACM-UI, Knowledge Graph)                │
│  ├── B5. Backend component analysis                                │
│  ├── B5b. Component health = Tier 1 (v3.0) — always when cluster   │
│  │        access available                                         │
│  ├── B7. Backend cross-check (v3.0) — overrides Path A if backend  │
│  │       caused the UI failure                                     │
│  ├── B6. Repository deep dive (when needed)                        │
│  ├── B8. Tier 2 playbook investigation (v3.1) — prerequisites +    │
│  │       failure path checks with live oc commands                 │
│  ├── B8b. KG upstream dependency check (v3.1)                      │
│  ├── B8c. Tier 3 data flow tracing (v3.1) — if Tier 1-2 dont      │
│  │        explain failure                                          │
│  └── B8d. Tier 4 deep investigation (v3.1) — if Tier 1-3 dont     │
│           explain OR multiple areas failing                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE C: CROSS-REFERENCE VALIDATION (Mandatory)                   │
│  ├── C1. Multi-evidence requirement check (2+ sources)             │
│  ├── C2. Cascading failure detection                               │
│  └── C3. Pattern correlation with Phase A findings                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE D: 3-PATH CLASSIFICATION ROUTING                            │
│  ├── PR-1. Blank page (no-js) pre-check (v3.2) — check FIRST      │
│  ├── PR-2. Hook failure deduplication (v3.2)                       │
│  ├── PR-3. Temporal evidence check (v3.2)                          │
│  ├── PR-5. Data assertion pre-check (v3.3)                         │
│  ├── PR-6. Backend probe source-of-truth check (v3.4)              │
│  ├── PR-7. Environment Oracle dependency check (v3.5)              │
│  ├── PR-4. Feature knowledge override (v3.1) — check tier results  │
│  ├── PR-4b. Cluster access confidence adjustment (v3.1)            │
│  ├── D0. Check backend cross-check override FIRST (v3.0)           │
│  ├── D1. Route: Selector mismatch? → Path A (AUTOMATION_BUG)      │
│  ├── D2. Route: Timeout (non-selector)? → Path B1 (INFRASTRUCTURE)│
│  ├── D3. Route: Everything else → Path B2 (JIRA investigation)    │
│  └── D4. Final validation + confidence + rule out alternatives     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PHASE E: FEATURE CONTEXT & JIRA CORRELATION (Mandatory)           │
│  ├── E0. Build subsystem context (Knowledge Graph) — incremental   │
│  ├── E1. Carry forward Path B2 findings (if applicable)            │
│  ├── E2. Search for feature stories and PORs (JIRA)                │
│  ├── E3. Read acceptance criteria, linked PRs                      │
│  ├── E4. Search for related bugs                                   │
│  ├── E5. Known issue matching + feature-informed validation        │
│  └── E6. Create/link issues (optional)                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Phase A: Initial Assessment

**Purpose:** Re-authenticate to cluster, ground analysis in feature areas, detect global patterns, check cluster health.

### Phase A-1: MANDATORY Cluster Re-Authentication (v3.5)

**This step is MANDATORY. Execute it FIRST before any other investigation.**

Re-authenticate to the target cluster using the kubeconfig persisted by Stage 1. Without cluster access, Tier 1-4 investigation commands are unavailable and classification accuracy degrades.

```bash
# Step 1: Read cluster_access from core-data.json
cat runs/<dir>/core-data.json | jq '.cluster_access'

# Step 2: If kubeconfig_path is present, verify it works
oc whoami --kubeconfig runs/<dir>/cluster.kubeconfig

# Step 3: Use --kubeconfig on ALL subsequent oc commands
oc get pods -A --kubeconfig runs/<dir>/cluster.kubeconfig | grep -Ev 'Running|Completed'
```

**IMPORTANT:** Use `--kubeconfig <kubeconfig_path>` on EVERY `oc` command throughout Stage 2. Do NOT rely on default kubeconfig context.

| Outcome | Action |
|---------|--------|
| `kubeconfig_path` present AND `oc whoami` succeeds | Set `cluster_access_available = true`. Tier 1-4 commands available. |
| `kubeconfig_path` present BUT `oc whoami` fails | Kubeconfig expired. Set `cluster_access_available = false`. Proceed with snapshot data only. Reduce all classification confidence by 0.15. Log `cluster_investigation_summary.cluster_reauth_status = "failed"`. |
| `kubeconfig_path` is null | Credentials were unavailable during Stage 1. Set `cluster_access_available = false`, `cluster_reauth_status = "skipped"`. |

### Phase A0: Feature Area Grounding (v3.0) + Feature Knowledge (v3.1)

Read `feature_grounding` from core-data.json. Note which subsystem and key components each test group maps to.

```bash
cat runs/<dir>/core-data.json | jq '.feature_grounding'
```

This tells you WHAT feature each test validates before you analyze WHY it failed. Use this to:
- Focus investigation on the relevant subsystem's components
- Know which namespaces to check for pod health
- Understand the investigation focus for each feature area

**Feature Knowledge (v3.1):** Also read `feature_knowledge` from core-data.json. This contains playbook-driven context loaded by FeatureKnowledgeService:

```bash
cat runs/<dir>/core-data.json | jq '.feature_knowledge'
```

| Field | Use |
|-------|-----|
| `feature_readiness[<area>].all_prerequisites_met` | If `false`, unmet prerequisites may explain failures — check `unmet_prerequisites` list |
| `feature_readiness[<area>].pre_matched_paths` | Error messages already matched to known failure paths with `suggested_classification` and `investigation_steps` |
| `investigation_playbooks[<area>].architecture` | Feature architecture summary and key insight — provides domain context for investigation |
| `investigation_playbooks[<area>].failure_paths` | All known failure paths for the feature area — use as a checklist during Phase B |

When `pre_matched_paths` exist, use their `investigation_steps` to guide Phase B investigation and their `suggested_classification` as a starting hypothesis (still validate with multi-evidence).

### Phase A1: Environment Health Check

```bash
# Read environment status
cat runs/<dir>/core-data.json | jq '.environment'
```

| Condition | Classification | Skip Individual Analysis? |
|-----------|----------------|---------------------------|
| `cluster_connectivity == false` | ALL → INFRASTRUCTURE | Yes (confidence: 0.90) |
| `environment_score < 0.3` | ALL → INFRASTRUCTURE | Yes (confidence: 0.85) |
| Network errors + >50% timeouts | ALL → INFRASTRUCTURE | Yes (confidence: 0.80) |

**When Phase A short-circuits**, set `investigation_phases_completed: ["A"]` and skip Phases B-E. All tests receive the same INFRASTRUCTURE classification with the same confidence score.

### Phase A1b: Cluster Landscape Check (v3.0)

Read `cluster_landscape` from core-data.json. Check for degraded operators that overlap with feature area components.

```bash
cat runs/<dir>/core-data.json | jq '.cluster_landscape'
```

| Condition | Implication |
|-----------|-------------|
| Degraded operator matches feature area component | Backend may be causing UI failures |
| Resource pressure (memory/CPU) detected | Performance-related timeouts more likely |
| MCH status not Running | Cluster-wide issues possible |
| Managed clusters NotReady | Multi-cluster test failures expected |

### Phase A2: Failure Pattern Detection

```bash
# Count failure types
cat runs/<dir>/core-data.json | jq '.test_report.failed_tests | group_by(.failure_type) | map({type: .[0].failure_type, count: length})'
```

| Pattern | Meaning | Action |
|---------|---------|--------|
| All same selector | Single automation issue | Fix once, affects all |
| All same error message | Common root cause | Investigate shared component |
| Mix of different errors | Multiple issues | Analyze individually |
| >50% timeouts | System-wide issue | Check infrastructure first |

### Phase A3: Cross-Test Correlation Scan

Before individual analysis, identify shared characteristics:

```bash
# Extract all failing selectors
cat runs/<dir>/core-data.json | jq '.test_report.failed_tests[].parsed_stack_trace.failing_selector' | sort | uniq -c | sort -rn

# Extract all detected components
cat runs/<dir>/core-data.json | jq '.test_report.failed_tests[].detected_components[].name' | sort | uniq -c | sort -rn

# Check for common feature areas
cat runs/<dir>/core-data.json | jq '.investigation_hints.failed_test_locations[].feature_area' | sort | uniq -c | sort -rn
```

**Record correlations found for Phase C validation.**

### Phase A3b: Subsystem Context Building (v3.0)

If Knowledge Graph is available AND feature_grounding identifies components, batch-query subsystem context:

```
For each unique subsystem in feature_grounding:
  Query: all components in subsystem + dependency chains
  Store as subsystem_context for use throughout Phases B-E
```

This replaces per-test queries with a single batch query. Phase E0 becomes incremental.

```
mcp__neo4j-rhacm__read_neo4j_cypher({
  "query": "MATCH (c:RHACMComponent) WHERE c.subsystem = 'Search' RETURN c.label, c.type"
})
```

---

## Phase B: Deep Investigation (Per Test)

**Purpose:** Systematically gather ALL evidence for each failed test.

### Phase B1: Extracted Context Analysis

Each failed test includes pre-computed `extracted_context`:

```json
{
  "test_file": {
    "path": "cypress/e2e/cluster/create.cy.ts",
    "content": "// actual test code...",
    "line_count": 150,
    "truncated": false
  },
  "page_objects": [
    {
      "path": "cypress/views/cluster.js",
      "content": "// selector definitions...",
      "contains_failing_selector": true
    }
  ],
  "console_search": {
    "selector": "#create-btn",
    "found": false,
    "locations": [],
    "similar_selectors": ["#cluster-create-btn"]
  }
}
```

**Questions to answer:**
- What does the test do? (read `test_file.content`)
- Is the failing selector defined correctly? (check `page_objects`)
- Does the selector exist in the product? (`console_search.found`)
- What similar selectors exist? (`console_search.similar_selectors`)
- Is this a data-level failure? (check `assertion_analysis.has_data_assertion` and `failure_mode_category`)
- If `failure_mode_category == 'data_incorrect'`: the page rendered but showed wrong data — focus investigation on the backend API data path, NOT selectors

### Phase B2: Timeline Evidence Analysis

Check `investigation_hints.timeline_evidence`:

```json
{
  "#create-btn": {
    "exists_in_console": false,
    "element_removed": true,
    "element_never_existed": false,
    "days_difference": 15,
    "console_changed_after_automation": true,
    "console_timeline": {
      "last_modified": "2026-01-15T10:00:00Z",
      "commit_message": "refactor: rename cluster buttons"
    }
  }
}
```

| Timeline Fact | Implication |
|---------------|-------------|
| `element_never_existed = true` | Selector was never correct |
| `element_removed = true` | Product changed, automation not updated |
| `console_changed_after_automation = true` | Recent product change may have broken test |

### Phase B3: Console Log Evidence

```bash
# Check for 500 errors
cat runs/<dir>/core-data.json | jq '.console_log.error_patterns'

# Get key errors
cat runs/<dir>/core-data.json | jq '.console_log.key_errors[]' | head -20
```

| Console Evidence | Points To |
|-----------------|-----------|
| 500/502/503 errors | PRODUCT_BUG |
| "Connection refused" | INFRASTRUCTURE |
| "timeout" + healthy env | AUTOMATION_BUG (wait strategy) |
| No errors, just element not found | AUTOMATION_BUG (selector) |

### Phase B4: MCP Tool Queries

**MANDATORY when trigger conditions are met.**

#### Set Correct Versions First

```
# At start of investigation, set ACM version
mcp__acm-ui__set_acm_version('2.16')  # or appropriate version

# For VM tests, detect CNV version
mcp__acm-ui__detect_cnv_version()
```

#### MCP Tool Trigger Matrix

| Trigger Condition | MCP Tool | Query |
|-------------------|----------|-------|
| **Start of investigation** | `mcp__acm-ui__set_acm_version` | `set_acm_version('2.16')` (latest GA) |
| **VM test failure** | `mcp__acm-ui__detect_cnv_version` | Auto-sets kubevirt branch (latest GA: 4.21) |
| **Selector not found** | `mcp__acm-ui__get_acm_selectors` | `get_acm_selectors('catalog', 'clc')` |
| **Need cross-repo search** | `mcp__acm-ui__search_code` | `search_code('create-btn', 'acm')` |
| **Need exact file lookup** | `mcp__acm-ui__find_test_ids` | `find_test_ids('path/to/file.tsx', 'acm')` |
| **Verify UI text** | `mcp__acm-ui__search_translations` | `search_translations('Create cluster')` |
| **Understand wizard flow** | `mcp__acm-ui__get_wizard_steps` | `get_wizard_steps('path/wizard.tsx', 'acm')` |
| **PatternFly fallback** | `mcp__acm-ui__get_patternfly_selectors` | `get_patternfly_selectors('button')` |
| **Component in error** | `mcp__neo4j-rhacm__read_neo4j_cypher` | Cypher query for deps (if available) |
| **Path B2: Polarion ID found** | `mcp__jira__search_issues` | `search_issues(jql="summary ~ 'RHACM4K-XXXX' OR description ~ 'RHACM4K-XXXX'")` |
| **Path B2: Feature story found** | `mcp__jira__get_issue` | `get_issue('ACM-22079')` — read story, acceptance criteria, linked PRs |
| **Phase E: detected_components available** | `mcp__neo4j-rhacm__read_neo4j_cypher` | Component info + subsystem query |
| **Phase E: subsystem identified** | `mcp__neo4j-rhacm__read_neo4j_cypher` | Get all components in subsystem |
| **Phase E: subsystem or component known** | `mcp__jira__search_issues` | JQL for feature stories by component/subsystem |
| **Phase E: feature story found** | `mcp__jira__get_issue` | Read story + acceptance criteria + linked PRs |
| **Phase E: POR or Epic linked** | `mcp__jira__get_issue` | Read POR for planned behavior |
| **Any classification** | `mcp__jira__search_issues` | JQL for related bugs |
| **Get full bug details** | `mcp__jira__get_issue` | `get_issue('ACM-12345')` |
| **Phase 2: Polarion ID found** | `mcp__polarion__get_polarion_setup_html` | `get_polarion_setup_html(project_id='RHACM4K', work_item_id='RHACM4K-XXXX')` |
| **Phase 2: Need test steps** | `mcp__polarion__get_polarion_test_steps` | `get_polarion_test_steps(project_id='RHACM4K', work_item_id='RHACM4K-XXXX')` |
| **Phase 2: Need test summary** | `mcp__polarion__get_polarion_test_case_summary` | `get_polarion_test_case_summary(project_id='RHACM4K', work_item_id='RHACM4K-XXXX')` |
| **File bug for product issue** | `mcp__jira__create_issue` | Create with classification evidence |
| **Link related failures** | `mcp__jira__link_issue` | `link_issue('Relates', 'ACM-111', 'ACM-222')` |

#### QE Selector Catalog (More Reliable Than Source)

Use `get_acm_selectors('catalog', component)` for proven, tested selectors:

| Component | Repo Key | Example |
|-----------|----------|---------|
| Cluster Lifecycle | `'clc'` | `get_acm_selectors('catalog', 'clc')` |
| Search | `'search'` | `get_acm_selectors('catalog', 'search')` |
| Applications | `'app'` | `get_acm_selectors('catalog', 'app')` |
| Governance | `'grc'` | `get_acm_selectors('catalog', 'grc')` |

### Phase B5: Backend Component Analysis

Check `detected_components` for each failed test:

```json
{
  "detected_components": [
    {
      "name": "search-api",
      "subsystem": "Search",
      "source": "error_message",
      "context": "search-api returned 500: index not available"
    }
  ]
}
```

**When components are detected, query Knowledge Graph:**

```cypher
# Find components that depend on the failing component
MATCH (dep:RHACMComponent)-[:DEPENDS_ON]->(c:RHACMComponent)
WHERE c.label =~ '(?i).*search-api.*'
RETURN DISTINCT dep.label as dependent, dep.subsystem as subsystem
```

```
mcp__neo4j-rhacm__read_neo4j_cypher({
  "query": "MATCH (dep)-[:DEPENDS_ON]->(c:RHACMComponent) WHERE c.label =~ '(?i).*search-api.*' RETURN dep.label"
})
```

### Phase B5b: Targeted Pod Investigation = Tier 1 Component Health (v3.0)

**Always run when cluster access is available.** Check health of every backend component the feature depends on (from `feature_grounding.key_components`). This is Tier 1 of the tiered investigation — see Phase B8 for the full tier progression.

| Finding | Implication |
|---------|-------------|
| CrashLoopBackOff on feature component | Backend crash → PRODUCT_BUG |
| High restart count (>5) | Instability → investigate further |
| Pod Pending (resource issues) | INFRASTRUCTURE |
| All pods Running/Ready | Backend healthy, issue is elsewhere |

### Phase B7: Backend Cross-Check (v3.0)

**Purpose:** Detect "UI failure caused by backend problem" — prevents misclassifying as AUTOMATION_BUG.

**Trigger:** For each test with `failure_type == element_not_found` or `timeout`:

1. **Check console log:** Does it show 500 errors from the feature area's `key_components`?
2. **Check cluster landscape:** Are any `feature_grounding.key_components` in non-Ready state?
3. **Check pod diagnostics:** Did B5b find CrashLoopBackOff or degraded pods?

**If YES to any:**
```json
{
  "backend_cross_check": {
    "performed": true,
    "backend_caused_ui_failure": true,
    "failing_components": ["search-api"],
    "evidence": ["search-api in CrashLoopBackOff", "500 errors in console log"],
    "overrides_path_a": true
  }
}
```

→ Set `backend_caused_ui_failure = true` → Route to **Path B2** in Phase D instead of Path A.

**Reason:** Element not found BECAUSE the backend broke (search results never loaded), NOT because the selector changed.

### Phase B7c: Backend Probe Analysis with Source-of-Truth Validation (v3.4)

**Trigger:** `core-data.json` contains `backend_probes` section (collected in Stage 1 Step 4c).

If `backend_probes` is present, check for anomalies that match this test's feature area:

```bash
cat runs/<dir>/core-data.json | jq '.backend_probes'
```

**Feature area to probe mapping:**

| Feature Area | Relevant Probe | What Anomaly Means |
|---|---|---|
| Automation | `/ansibletower` | Empty results when AAP is healthy |
| CLC | `/hub` | Wrong hub name or flags |
| RBAC | `/username` | Reversed or wrong username |
| Search | `/proxy/search` | Empty or timeout |
| All areas | `/authenticated` | Auth failure or slow |

**Source-of-truth validation (v3.4):** Each probe with anomalies is now cross-referenced against the Kubernetes API directly (bypassing the console backend). The probe includes pre-computed fields:

| Field | Values | Meaning |
|---|---|---|
| `anomaly_source` | `console_backend` | Cluster API returns correct data but console returns different data — console code is the problem |
| `anomaly_source` | `upstream` | Both cluster API and console return the same anomalous data — issue is upstream infrastructure |
| `anomaly_source` | `unknown` | Cannot determine source — let normal routing decide |
| `classification_hint` | `PRODUCT_BUG` / `INFRASTRUCTURE` / `null` | Pre-computed classification based on deterministic comparison |

**CRITICAL: Use `classification_hint` when available.** This is a deterministic comparison (not AI judgment) and should override AI inference about whether an anomaly is infrastructure or product:

```
IF probe has anomaly AND anomaly_source == "console_backend":
  → classification_hint = PRODUCT_BUG
  → The cluster ground truth is correct but console transforms data incorrectly
  → Use as Tier 1 evidence

IF probe has anomaly AND anomaly_source == "upstream":
  → classification_hint = INFRASTRUCTURE
  → Both cluster and console return the same anomalous data
  → Use as Tier 1 evidence

IF probe has anomaly AND anomaly_source == "unknown":
  → No classification_hint — proceed with normal 3-path routing
  → Add probe data as supplementary evidence
```

**For each probe with `status == "timeout"` or `"error"`:**
1. Record as potential **INFRASTRUCTURE** evidence — console backend may be unresponsive

**Example:** Test in Automation area fails with "expected to find 5 templates, got 0". Backend probe `/ansibletower` shows `anomaly_source: "console_backend"` because AAP operator is Succeeded but console returns empty. → PRODUCT_BUG (console proxy strips results, not an infrastructure issue).

### Phase B6: Repository Deep Dive

**Trigger:** When extracted_context is insufficient.

```bash
# Read full test file
cat runs/<dir>/repos/automation/cypress/e2e/<test_file>

# Trace imports
grep -rn "import.*selector\|from.*views" runs/<dir>/repos/automation/cypress/e2e/<test_file>

# Search console for element
grep -rn "data-testid.*element-name" runs/<dir>/repos/console/frontend/src/

# Check git history
cd runs/<dir>/repos/console && git log -3 --oneline -S "element-name"

# For VM tests, check kubevirt-plugin
grep -rn "element-name" runs/<dir>/repos/kubevirt-plugin/src/
```

### Phase B8: Tiered Playbook Investigation (v3.1)

**Purpose:** Use feature knowledge playbooks and live cluster access to systematically investigate failures through escalating tiers.

**Pre-requisite:** Cluster re-authentication must be verified at start of Phase A (see Phase A-1). If kubeconfig verification failed, Tier 1-4 commands won't work — use snapshot data only (confidence reduction applied in Phase PR-4b). Remember to use `--kubeconfig <path>` on ALL oc commands.

#### Tier 0: Health Snapshot (run ONCE at start of Phase A)

Verify the Stage 1 snapshot is still current:

```bash
oc get mch -A -o yaml                                    # MCH phase, version, overrides
oc get managedclusters                                    # Cluster health
oc get clusteroperators | grep -v 'True.*False.*False'    # Degraded operators only
oc adm top nodes                                          # Resource pressure
oc get pods -A | grep -Ev 'Running|Completed'             # Non-healthy pods
```

#### Tier 1: Component Health (per feature area)

Already covered by Phase B5b above. Use findings from B5b here — no need to re-run the same commands.

#### Tier 2: Playbook Investigation (when playbook loaded)

Check prerequisites from `feature_knowledge.feature_readiness[<area>]` with live commands:

| Prerequisite Type | Live Check |
|-------------------|------------|
| `mch_component` | `oc get mch -A -o jsonpath='{.items[0].spec.overrides.components}'` |
| `addon` | `oc get managedclusteraddon <addon> -n <cluster>` |
| `operator` | `oc get csv -n <namespace> \| grep <operator>` |
| `crd` | `oc get crd <crd-name>` |

Then match test errors against playbook failure path symptoms, execute investigation steps, compare against expected results.

#### B8b: KG Upstream Dependency Check

If Tier 2 confirms a failure path, query KG for upstream dependencies of the confirmed failing component. If upstream is also failing, root cause is upstream.

#### B8c: Tier 3 Data Flow Tracing

**Trigger:** Tier 1-2 don't explain the failure (all components healthy, prerequisites met).

Trace feature data flow using KG dependency context (`feature_knowledge.kg_dependency_context`) + playbook architecture. Look for data not flowing between components.

#### B8d: Tier 4 Deep Investigation

**Trigger:** Tier 1-3 don't explain OR multiple feature areas failing simultaneously.

- Cross-namespace event scan
- Network connectivity checks
- Resource deep-dive (node pressure, memory-heavy pods)
- KG cascading failure analysis (`find_common_dependency`)
- Recent changes (recently created pods, image pulls)

---

## Phase C: Cross-Reference Validation

**Purpose:** Validate classification through multiple sources.

### Phase C1: Multi-Evidence Requirement (MANDATORY)

**Every classification MUST have 2+ evidence sources:**

| Classification | Required Evidence Sources |
|----------------|---------------------------|
| **PRODUCT_BUG** | Console log 500 + Environment healthy + Test logic correct |
| **AUTOMATION_BUG** | Selector mismatch + No 500 errors + Element exists under different name/ID |
| **INFRASTRUCTURE** | Environment unhealthy + Multiple tests affected + Network errors |

**Evidence Tier Priority:**

| Tier | Evidence Type | Weight |
|------|---------------|--------|
| **Tier 1 (Definitive)** | 500 errors, element removed, env < 0.3, cluster_investigation pod crash, backend_cross_check | High |
| **Tier 2 (Strong)** | Selector mismatch, multiple tests, cascading, feature_grounding component match | Medium |
| **Tier 3 (Supportive)** | Similar selectors, timing issues | Low |

**Minimum requirement:** 1 Tier 1 + 1 Tier 2, OR 2 Tier 1, OR 3 Tier 2

**Always attempt to gather Tier 1 evidence before accepting Tier 2/3 combinations.** If Tier 1 evidence is available but not gathered, the classification may be incorrect.

### Phase C2: Cascading Failure Detection

When Knowledge Graph is available:

```cypher
# Find if multiple failing components share a common dependency
MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent)
WHERE c.label IN ['comp1', 'comp2', 'comp3']
WITH common, count(DISTINCT c) as component_count
WHERE component_count >= 2
RETURN common.label as common_dependency
```

**If cascading failure detected:**
- Identify root cause component
- All dependent failures are symptoms, not separate bugs
- Single PRODUCT_BUG classification for root cause

### Phase C3: Pattern Correlation

Cross-reference with Phase A findings:

- Do individual classifications match detected patterns?
- If 80% same selector → bulk AUTOMATION_BUG with single root cause
- If all tests in same feature area → feature-wide issue

---

## Phase D: 3-Path Classification Routing

### Phase PR-1: Blank Page / No-JS Pre-Check (v3.2)

**CRITICAL: Check this BEFORE any other routing decision.**

If a test's error shows a blank page (the HTML contains `class="no-js"`, or the page body is empty/missing expected content), the failure is NOT a selector mismatch — the entire page failed to render.

**Detection criteria (any of these):**
- Error message contains `no-js` or `class="no-js"`
- Error mentions blank page, empty page, or page not loading
- Test navigates to a feature page but finds zero interactive elements
- Multiple tests for the same page ALL fail with element-not-found on different selectors

**Routing logic:**

| Condition | Classification | Confidence |
|-----------|----------------|------------|
| Blank page + test logs in as non-admin user (RBAC test) + IDP not configured | INFRASTRUCTURE | 0.90 |
| Blank page + Automation page (`/automations`) + AAP operator not installed | INFRASTRUCTURE | 0.90 |
| Blank page + Automation page + AAP operator installed but degraded | INFRASTRUCTURE | 0.85 |
| Blank page + Automation page + AAP installed and healthy | AUTOMATION_BUG | 0.85 |
| Blank page + Fleet Virt page + CNV operator not installed | INFRASTRUCTURE | 0.90 |
| Blank page + feature prerequisite unmet (from playbook) | INFRASTRUCTURE | 0.90 |
| Blank page + all prerequisites met + backend healthy | AUTOMATION_BUG | 0.80 |

**Investigation steps when blank page detected:**
1. Check which page URL the test navigates to
2. Look up the feature area's prerequisites (from `feature_knowledge.feature_readiness`)
3. If cluster access available, verify the prerequisite with live `oc` commands:
   - For Automation: `oc get csv -A 2>/dev/null | grep -i 'aap\|ansible\|automation-platform'`
   - For RBAC: `oc get oauth cluster -o jsonpath='{.spec.identityProviders}'`
   - For Virtualization: `oc get csv -n openshift-cnv`
4. Classify based on prerequisite status (see table above)

**When this pre-check applies, SKIP standard D0 routing** — the blank page is the root cause, not the specific selector the test tried to find.

---

### Phase PR-2: Hook Failure Deduplication (v3.2)

**Purpose:** Identify `after all` hook failures that are cascading consequences of a prior test failure, not independent bugs.

**Detection criteria (all must be true):**
1. Test name starts with `"after all" hook` or `"after each" hook`
2. Another test in the same spec file (same `describe` block or same `.cy.ts` file) already failed
3. The hook's error is a DOM/jQuery error (e.g., `$el.css is not a function`, `cy.within() failed`, `Cannot read properties of null`)

**When detected:**
- Classify as **NO_BUG** with confidence 0.90
- Set reasoning: "Cascading cleanup failure — after-all hook failed because the prior test already failed and left no elements to clean up"
- Set `is_cascading_hook_failure: true` in the per-test analysis
- **SKIP standard D0 routing** — this is not an independent failure

**When NOT to apply:**
- `before all` hooks are NOT cascading — they are setup failures that prevented the test from running. Classify normally.
- If the after-all hook has a different error type (e.g., API error, timeout to a backend service), investigate it independently.

---

### Phase PR-3: Temporal Evidence Check (v3.2)

**Purpose:** Use `temporal_summary` data from extracted_context to detect potential PRODUCT_BUG when product files changed after test files.

**Check for each test:**
1. Read `extracted_context.temporal_summary.stale_test_signal`
2. If `stale_test_signal == true`:
   - Read `product_commit_message` and `days_difference`
   - **If** `product_commit_message` mentions refactor, rename, PF6, PatternFly, migration, redesign, or removal → **strong signal for PRODUCT_BUG** (confidence 0.85)
   - **If** `product_commit_message` mentions fix, bugfix, or patch → neutral (product was fixed, test may need update) → continue to standard routing
   - **If** `days_difference > 30` → weaker signal (old change, test may already account for it) → continue to standard routing with note
3. If `stale_test_signal == false` or `temporal_summary` is absent → continue to standard routing

**This check does NOT short-circuit routing.** It sets a hypothesis that is validated through standard Path B2 investigation. Add `temporal_evidence` as an evidence source when it contributes to the classification.

**For "new element shadows old" pattern:**
When a test's `cy.contains()` or `cy.get()` matches a NEW element that didn't exist before (e.g., a Lightspeed AI popover button matching `'Resume cluster'` text), investigate whether the matching element is new in the product. This pattern indicates PRODUCT_BUG (new element introduced that conflicts with existing test expectations).

---

### Phase PR-5: Data Assertion Pre-Check (v3.3)

**Purpose:** Detect failures where the UI rendered correctly but the data is wrong — API returned 200 OK with incorrect/empty data.

**Detection criteria (all must be true):**
1. `extracted_context.assertion_analysis.has_data_assertion == true`
2. `extracted_context.failure_mode_category == 'data_incorrect'`
3. No 500 errors in console log for this test's feature area
4. `extracted_context.console_search.found == true` OR selector is not relevant (assertion is about data count/value)

**When detected:**

| Assertion Type | Classification | Confidence |
|----------------|----------------|------------|
| `count_mismatch` (expected N items, got 0) | PRODUCT_BUG | 0.85 |
| `value_mismatch` (expected 'Ready', got 'Available') | PRODUCT_BUG | 0.80 |
| `content_missing` (expected table to contain 'X') | PRODUCT_BUG | 0.80 |
| `state_mismatch` (expected true, got false) | PRODUCT_BUG | 0.80 |
| `property_missing` (expected object to have property 'X') | PRODUCT_BUG | 0.75 |

**This check does NOT short-circuit routing.** It sets a strong PRODUCT_BUG hypothesis that is validated through Path B2 investigation. The data assertion itself is a Tier 1 evidence source.

**Key insight:** When `failure_mode_category == 'data_incorrect'`, dominant signals like "pod instability" or "console restarts" cannot explain this failure — pod instability causes pages not to render, not pages that render correctly with wrong data. See Phase D4b.

---

### Phase PR-6: Backend Probe Source-of-Truth Check (v3.4)

**Purpose:** When backend probes detected anomalies, use pre-computed `classification_hint` from source-of-truth validation to determine whether the anomaly is in the console backend code (PRODUCT_BUG) or the upstream cluster (INFRASTRUCTURE). This is a deterministic comparison, not AI judgment.

**Check for each test whose feature area matches a probe with anomalies:**

1. Read `backend_probes.<probe>.anomaly_source` and `classification_hint`
2. If `anomaly_source == "console_backend"` AND `classification_hint == "PRODUCT_BUG"`:
   - The Kubernetes API returns correct data but the console backend returns different data
   - The console code is transforming/corrupting data
   - Use as **Tier 1 evidence** for PRODUCT_BUG with confidence 0.85
3. If `anomaly_source == "upstream"` AND `classification_hint == "INFRASTRUCTURE"`:
   - Both K8s API and console return the same anomalous data — issue is upstream
   - Use as **Tier 1 evidence** for INFRASTRUCTURE with confidence 0.80
4. If `anomaly_source == "unknown"` or `classification_hint` is null:
   - Cannot determine source — proceed with normal routing
   - Add probe anomaly as supplementary evidence only

**This check does NOT short-circuit routing** but provides strong directional evidence. The `classification_hint` should be trusted because it is based on a factual data comparison (console response vs cluster API response), not on AI inference.

---

### Phase PR-7: Environment Oracle Dependency Check (v3.5)

**Purpose:** Use ALL pre-computed oracle data to detect broken feature dependencies, understand component architecture, and cross-reference Polarion test prerequisites — before standard routing.

The oracle contains three data sections. Use ALL of them for every test.

#### PR-7a: Reading `cluster_oracle.dependency_health`

For each test, check if ANY dependency relevant to the test's feature area has `status == "degraded"` or `status == "missing"`. Iterate every entry and match against the test's feature area.

**Dependency types and what each status means:**

| Target Type | `missing` Means | `degraded` Means |
|---|---|---|
| `operator` | CSV not in Succeeded phase — operator is broken, the feature cannot function | CSV exists but operator pods restarting or not all replicas ready |
| `addon` | ManagedClusterAddon not present on managed clusters — feature has no data from spokes | Addon present on some clusters but not all — partial data coverage |
| `crd` | CRD does not exist on the cluster — feature prerequisites not met, API endpoints unavailable | CRD exists but version mismatch or conditions not met |
| `component` | Pod not found in expected namespace — component never deployed | Pod exists but not Running, high restart count (>3), or CrashLoopBackOff |
| `managed_clusters` | ManagedCluster resource missing — spoke cluster decommissioned or import failed | Cluster exists but status NotReady — network partition, expired certs, or agent down |

**Classification routing from dependency_health:**

| Oracle Status | Dependency Type | Classification | Confidence |
|---|---|---|---|
| `missing` | operator | INFRASTRUCTURE | 0.90 |
| `missing` | addon | INFRASTRUCTURE | 0.90 |
| `missing` | crd | INFRASTRUCTURE | 0.90 |
| `missing` | component | INFRASTRUCTURE | 0.90 |
| `missing` | managed_clusters | INFRASTRUCTURE | 0.85 |
| `degraded` | operator | INFRASTRUCTURE | 0.85 |
| `degraded` | addon (partial) | INFRASTRUCTURE | 0.80 |
| `degraded` | component | INFRASTRUCTURE | 0.85 |
| `degraded` | managed_clusters | INFRASTRUCTURE | 0.85 |

**When `overall_feature_health.score < 0.5`:** Strong INFRASTRUCTURE signal for ALL tests in that feature area.

**This check does NOT short-circuit routing** but provides strong directional evidence. When oracle confirms a dependency is missing or degraded, it is **Tier 1 evidence** — direct cluster state observation, not inference.

**Example:** Search test fails with "expected 5 results, got 0". Oracle shows `search-collector-addon.status = degraded, detail = "Available on 3/5 clusters. Degraded on: spoke-2, spoke-3"`. Route to INFRASTRUCTURE: "search-collector addon degraded on spoke-2 and spoke-3, resources from those spokes won't appear in search results."

#### PR-7b: Reading `cluster_oracle.knowledge_context`

When `knowledge_context` is present, use it to understand the full architecture of the failing feature's subsystem. This section contains the Knowledge Graph output enriched with playbook data.

**Fields and how to use each:**

- **`feature_components`**: List of ALL components in the feature subsystem. Cross-reference each component against `dependency_health` to build a complete picture of which are healthy and which are degraded. If a component appears here but NOT in `dependency_health`, it was not probed — treat its health as unknown.

- **`internal_data_flow`**: Ordered chain showing how components within the feature communicate (e.g., `search-collector → search-indexer → search-api → console`). Walk this chain and check each link against `dependency_health`. The **first broken link** in the chain is the root cause — downstream components will fail as a consequence. Do not attribute failures to downstream components when an upstream component is broken.

- **`cross_subsystem_dependencies`**: Dependencies on components OUTSIDE the feature's own subsystem (e.g., Search depends on `multicluster-engine`). Check these against `dependency_health` too — an external dependency failure can cause the feature to break even though all internal components are healthy.

- **`transitive_chains`**: Blast radius analysis. If component X is down, this field lists what else breaks transitively. Use this to determine whether a single failure explains multiple test failures across different feature areas.

- **`component_details`**: Per-component upstream/downstream relationships. For a specific failing component, read its `upstream` list to find what feeds it data, and its `downstream` list to find what it feeds. This helps trace the exact failure propagation path.

- **`dependency_details`**: Architecture of each dependency subsystem. Provides context about how each dependency works internally, so the AI can explain WHY a broken dependency causes a specific symptom (e.g., "search-collector pushes ManagedClusterView data to the hub — when it's degraded, search-api returns stale or empty results").

- **`docs_context.docs_path`**: Path to the cloned rhacm-docs repository. Use Read and Grep tools to search for architecture documentation relevant to the failing feature area. The AI decides what to search for based on the failure context — no hardcoded search terms.

  ```
  # Example: Search test fails — learn how Search works
  grep -r "search-collector" <docs_path>/search/ --include="*.adoc"
  cat <docs_path>/search/search_overview.adoc

  # Example: Virtualization test fails — learn how CNV integration works
  grep -r "virtualization\|kubevirt\|cnv" <docs_path>/virtualization/ --include="*.adoc"
  ```

  Use this documentation to understand:
  - How the feature's components interact and where data flows
  - What prerequisites must be met for the feature to work
  - Known failure patterns and troubleshooting steps
  - Cross-subsystem dependencies that may not be in the KG

- **`playbook_architecture.key_insight`**: Domain-specific failure knowledge extracted from feature playbooks. Use this to explain WHY a broken component causes the observed test failure. This is the "so what" — connecting the infrastructure state to the user-visible symptom.

#### PR-7c: Reading `cluster_oracle.polarion_discovery.test_case_context`

When `polarion_discovery` is present, it contains Polarion test case data for each failed test that has a Polarion ID. For each failed test with a matching entry:

1. **Read the `setup` field**: Understand what prerequisites the test expects to be in place before it runs. Cross-reference each prerequisite against `dependency_health` — if a prerequisite mentioned in `setup` is broken in the oracle, that is the root cause. This is the strongest oracle signal (0.90-0.95 confidence).

2. **Read the `description` field**: Understand what the test is designed to validate. This helps determine whether the failure is in the feature being tested (PRODUCT_BUG) or in the test's ability to reach the feature (INFRASTRUCTURE/AUTOMATION_BUG).

3. **Read the `test_steps` field**: Understand the sequence of actions the test performs. Match the step where the test fails against the component architecture — if step 3 fails and it interacts with a component that `dependency_health` shows as degraded, the root cause is clear.

#### PR-7d: Classification routing summary

After reading ALL three oracle sections, apply this routing:

| Condition | Classification | Confidence |
|---|---|---|
| ANY component in the feature's `internal_data_flow` chain is degraded/missing | INFRASTRUCTURE | 0.85-0.90 |
| A Polarion `setup` prerequisite matches a broken oracle dependency | INFRASTRUCTURE | 0.90-0.95 |
| Managed clusters are NotReady AND tests require spoke cluster data | INFRASTRUCTURE | 0.85 |
| `cross_subsystem_dependencies` shows an external dependency is broken | INFRASTRUCTURE | 0.85 |
| `transitive_chains` explains multiple failures from one broken component | INFRASTRUCTURE | 0.90 |
| ALL dependencies healthy AND all components running | Oracle does NOT suggest INFRASTRUCTURE — proceed to standard D0 routing | N/A |

The oracle is **Tier 1 evidence** for all of the above — it is direct cluster state observation, not inference.

**Oracle freshness caveat:** The oracle snapshot is taken during Stage 1 (gather.py). By the time Stage 2 analysis runs, the cluster state may have changed. Apply these modifiers:
- If `cluster_oracle.cluster_access_status == "authenticated"` → full confidence (snapshot is recent)
- If `cluster_oracle.cluster_access_status == "login_failed"` → oracle has NO cluster state data; `dependency_health` is empty. Do NOT use oracle for INFRASTRUCTURE classification. Proceed to standard routing.
- If `cluster_oracle.cluster_access_status == "skipped"` → same as login_failed
- If `cluster_oracle.cluster_access_status == "no_credentials"` → oracle has dependency targets from playbooks but no live verification. Use knowledge_context (KG/docs/Polarion) but reduce any oracle-based INFRASTRUCTURE confidence by 0.15.

Oracle data does NOT supersede live cluster investigation (Tier 1-4 commands in Phase B). If you can re-authenticate to the cluster, verify oracle findings with live commands before finalizing.

---

### Phase PR-4: Feature Knowledge Override (v3.1)

**CRITICAL: Check playbook/tiered investigation results BEFORE standard routing.**

| Condition | Classification | Confidence |
|-----------|----------------|------------|
| Prerequisite unmet AND Tier 2 confirmed with live oc commands | Use playbook `suggested_classification` | 0.95 |
| Tier 2 confirmed failure path (steps matched expected results) | Use failure path classification | Path confidence |
| Tier 3 found data flow break | Classify based on break point | 0.85-0.90 |
| Tier 4 KG found cascading failure | Classify based on upstream root cause | 0.90 |
| Prerequisite disabled (MCH component off) — feature intentionally not enabled | NO_BUG | 0.90 |

If none of these apply, proceed to D0 standard routing.

### Phase PR-4b: Cluster Access Confidence Adjustment (v3.1)

If `cluster_access_available == false` (oc login failed at start of Phase A): **reduce confidence by 0.15 on ALL classifications.** Tier 1-4 live commands were unavailable, so classifications rely on snapshot data only.

### Phase D0: Routing Decision (Updated v3.0)

**MANDATORY:** Before entering D0 routing, confirm B7 backend cross-check has been performed.
If B7 was skipped (no cluster access), note this limitation in the analysis and
reduce any AUTOMATION_BUG confidence by 0.10.

**CRITICAL: Check backend cross-check override FIRST before routing.**

```
                         Failed Test Evidence
                               │
                               ▼
                  ┌────────────────────────────┐
                  │  D0a: Backend cross-check  │
                  │  override?                 │
                  │  backend_caused_ui_failure  │
                  │  == true                   │
                  └───────────┬────────────────┘
                              │
               ┌──────────────┴──────────────┐
               ▼ YES                         ▼ NO
        ┌─────────────────┐     ┌────────────────────────┐
        │   PATH B2       │     │  Selector mismatch?    │
        │ (backend broke  │     │  • element_not_found   │
        │  the UI)        │     │  • console_search.found│
        └─────────────────┘     │    == false            │
                                │  • element_removed     │
                                │    == true             │
                                └───────────┬────────────┘
                                            │
                             ┌──────────────┴──────────────┐
                             ▼ YES                         ▼ NO
                      ┌─────────────┐            ┌──────────────────┐
                      │   PATH A    │            │  Timeout (non-   │
                      │ AUTOMATION  │            │  selector)?      │
                      │   _BUG      │            └────────┬─────────┘
                      └─────────────┘                     │
                                            ┌─────────────┴─────────────┐
                                            ▼ YES                       ▼ NO
                                   ┌─────────────────┐        ┌─────────────────┐
                                   │    PATH B1      │        │    PATH B2      │
                                   │ INFRASTRUCTURE  │        │ JIRA-INFORMED   │
                                   │                 │        │ INVESTIGATION   │
                                   └─────────────────┘        └─────────────────┘
```

**Backend cross-check override (v3.0):** If `backend_caused_ui_failure == true`, the element was not found because the backend broke (e.g., search-api crashed, search results never loaded), NOT because the selector changed. Route to Path B2 for JIRA-informed investigation → likely PRODUCT_BUG.

**Oracle-enhanced D0 (v3.5):** When `cluster_oracle` is present in core-data.json, perform the following BEFORE entering the standard D0 routing:
1. Walk the `internal_data_flow` chain for the test's feature area (from `cluster_oracle.knowledge_context`)
2. Check each component in the chain against `cluster_oracle.dependency_health` — the first broken link is the root cause; downstream failures are consequences, not independent issues
3. Check `cross_subsystem_dependencies` for external failure points that could break the feature even if internal components are healthy
4. Use `playbook_architecture.key_insight` to explain WHY the broken component causes this specific test failure (e.g., "search-collector pushes data to hub — when degraded, search-api returns empty results, causing the assertion 'expected 5, got 0'")
5. If `polarion_discovery.test_case_context` exists for this test, check whether a setup prerequisite matches a broken dependency — this is the highest-confidence oracle signal (0.90-0.95)
6. If ANY relevant dependency is degraded/missing, this is Tier 1 evidence that supersedes console log analysis alone — route through PR-7d classification table before falling through to D0a

**Important edge case:** A timeout caused by a missing selector (e.g., `cy.get('#missing-btn', {timeout: 30000})`) routes to **Path A**, not Path B1. Check whether the timed-out operation was waiting for a selector that doesn't exist in the product.

---

### Path A: Selector Mismatch → AUTOMATION_BUG

**Trigger conditions (any of these):**
- `failure_type == 'element_not_found'`
- `extracted_context.console_search.found == false`
- `investigation_hints.timeline_evidence[selector].element_removed == true`

**Classification:** AUTOMATION_BUG

**Confidence:** 0.75 - 0.90
- 0.90 if `console_search.found == false` AND `element_removed == true` AND B7 confirms backend healthy
- 0.85 if `console_search.found == false` with `similar_selectors` AND B7 confirms backend healthy
- 0.80 if only `element_not_found` without console_search confirmation
- 0.75 if `element_not_found` AND B7 was not performed (no cluster access)

**Recommended fix format:**
```json
{
  "recommended_fix": {
    "action": "Update selector in automation",
    "steps": [
      "Verify selector '#old-btn' was renamed to '#new-btn' in console repo",
      "Update cypress/views/<file>.js line <N>",
      "Change '#old-btn' to '#new-btn'"
    ],
    "owner": "Automation Team"
  }
}
```

All recommended fixes should be verified before applying.

**Path A requires minimum 2 evidence sources:**
  1. Selector evidence (console_search or timeline_evidence)
  2. Backend health confirmation (B7 result OR cluster landscape data)
Single-source Path A is NOT allowed — reduce to 0.70 if only one source.

**Output fields:**
```json
{
  "classification": "AUTOMATION_BUG",
  "classification_path": "A",
  "confidence": 0.88
}
```

---

### Path B1: Timeout (Non-Selector) → INFRASTRUCTURE

**Trigger conditions (all of these):**
- `failure_type == 'timeout'`
- The timeout is NOT caused by waiting for a missing selector
- No `element_not_found` sub-cause in the error

**Classification:** INFRASTRUCTURE

**Graduated health scoring (v3.3):** Use per-feature-area health scores instead of the global `environment_score` alone. The `ClusterInvestigationService.get_feature_area_health()` provides graduated infrastructure signal strength:

| Feature Area Health Score | Infrastructure Signal | Confidence |
|---|---|---|
| < 0.3 (definitive) | Route to INFRASTRUCTURE | 0.90 |
| 0.3-0.5 (strong) | Route to INFRASTRUCTURE if timeout present | 0.80 |
| 0.5-0.7 (moderate) | Flag as "possible infra" — investigate per-test | 0.65 |
| > 0.7 (none) | Don't attribute to infra unless direct evidence | N/A |

**Confidence (using graduated scoring):** 0.65 - 0.90
- 0.90 if multiple tests timeout AND feature area health < 0.3
- 0.85 if multiple tests timeout AND feature area health < 0.5
- 0.80 if single test timeout AND feature area health < 0.5
- 0.75 if single test timeout AND global environment_score < 0.5
- 0.65 if feature area health 0.5-0.7 (moderate — requires additional investigation)

**Output fields:**
```json
{
  "classification": "INFRASTRUCTURE",
  "classification_path": "B1",
  "confidence": 0.85
}
```

---

### Path B2: JIRA-Informed Investigation → PRODUCT_BUG or AUTOMATION_BUG

**Trigger conditions:**
- Everything that doesn't match Path A or Path B1
- 500 errors, assertion failures, auth errors, unexpected responses, render failures, etc.

**Investigation steps:**

**B2-1. Extract Polarion ID from test name:**
```
Regex: RHACM4K-\d+
Example: "RHACM4K-3046 - Verify cluster upgrade" → "RHACM4K-3046"
```

**B2-2. Search JIRA for feature story:**
```
mcp__jira__search_issues({
  "jql": "summary ~ 'RHACM4K-3046' OR description ~ 'RHACM4K-3046'",
  "max_results": 10
})
```

**B2-3. Get full story details:**
```
mcp__jira__get_issue({ "issue_key": "ACM-22079" })
```
Read: summary, description, acceptance criteria, linked PRs, fix versions.

**B2-4. Build feature understanding:**
- What is this feature supposed to do?
- What are the acceptance criteria?
- Were there recent changes (linked PRs)?

**B2-5. Compare feature intent vs failure:**
- Does the product fail to do what the story describes? → PRODUCT_BUG
- Does the test check something incorrectly or check the wrong thing? → AUTOMATION_BUG
- Does a linked PR introduce a regression? → PRODUCT_BUG

**B2-6. Classify with JIRA context:**

| Finding | Classification |
|---------|----------------|
| Product doesn't meet acceptance criteria | PRODUCT_BUG |
| 500 error from backend component | PRODUCT_BUG |
| Test asserts wrong expected value | AUTOMATION_BUG |
| Test checks removed/changed behavior correctly described in story | AUTOMATION_BUG |
| Linked PR introduced breaking change | PRODUCT_BUG |
| No JIRA context found, 500 errors present | PRODUCT_BUG (fallback) |
| No JIRA context found, no 500 errors | UNKNOWN (insufficient evidence) |
| Test passes on retry, no code changes explain failure | FLAKY |
| Failure expected given intentional product change (story/PR confirms) | NO_BUG |
| Feature prerequisite disabled (MCH component off, test expects feature not enabled) | NO_BUG |

**Confidence:** 0.75 - 0.95
- 0.95 if JIRA story clearly contradicts product behavior + 500 errors
- 0.85-0.90 if JIRA story provides clear context for classification
- 0.75-0.80 if JIRA found but context is ambiguous
- 0.80 if no JIRA found but strong error evidence (500 errors, assertion failures with clear backend cause)
- 0.75 if no JIRA found and error evidence is ambiguous
- 0.80 for FLAKY if retry data available and test passes on rerun
- 0.70 for FLAKY if no retry data but failure is intermittent/timing-based
- 0.85 for NO_BUG if JIRA story or linked PR confirms intentional behavior change
- 0.75 for NO_BUG if product change likely but no JIRA confirmation

**Without JIRA:** Classify using console log + error patterns + oracle data directly. Do not default to UNKNOWN solely because JIRA is unavailable. Apply the same evidence standards regardless of JIRA availability:
- 500 errors from backend components → PRODUCT_BUG at 0.80
- Selector missing in product source + no backend errors → AUTOMATION_BUG at 0.80
- Oracle shows dependency broken + error matches affected feature → INFRASTRUCTURE at 0.80
- Insufficient evidence for any classification → UNKNOWN at 0.60

**Output fields:**
```json
{
  "classification": "PRODUCT_BUG",
  "classification_path": "B2",
  "confidence": 0.88,
  "jira_correlation": {
    "search_performed": true,
    "related_issues": ["ACM-22079", "ACM-22080"],
    "match_confidence": "high"
  }
}
```

---

### Phase D4: Final Validation (All Paths)

After routing through the appropriate path, validate:

| Check | Required |
|-------|----------|
| At least 2 evidence sources | Yes |
| No conflicting evidence unresolved | Yes |
| Ruled out alternatives documented | Yes |
| MCP tools used (if available) | Yes |

**Confidence modifiers (applied after path-specific calculation):**
```
- JIRA correlation found (Phase E): +0.05
- Feature story confirms classification (Phase E): +0.05
- Feature story contradicts classification (Phase E): -0.05
- POR/linked PR provides regression evidence (Phase E): +0.10
- Cascading failure confirmed: +0.05
- Cross-test pattern match: +0.05
- Conflicting evidence unresolved: -0.15
```

**Cap final confidence at 1.0 after applying all modifiers.** The schema enforces `maximum: 1`.

**Rule out alternatives (MANDATORY):**

| If Classifying As | Must Rule Out |
|-------------------|---------------|
| PRODUCT_BUG | Selector mismatch, test logic error |
| AUTOMATION_BUG | Backend 500 errors, environment issues |
| INFRASTRUCTURE | Individual test bugs, product issues |

### Phase D4b: Per-Test Causal Link Verification (v3.3 — MANDATORY)

**Purpose:** Prevent over-attribution to a single dominant signal (e.g., "console pod instability" applied to all failures). Every test attributed to a shared pattern MUST have a direct causal mechanism linking the pattern to its specific error.

**For each test classified under a dominant pattern or shared root cause:**

1. **State the causal mechanism:** How does [dominant signal] cause [this test's specific error]?
2. **Check failure_mode_category compatibility:**

| Dominant Signal | Compatible Failure Modes | Incompatible Failure Modes |
|-----------------|--------------------------|----------------------------|
| Pod restarts / instability | `render_failure`, `timeout_general` | `data_incorrect`, `assertion_logic` |
| Network errors | `render_failure`, `timeout_general`, `server_error` | `data_incorrect`, `element_missing` (unless server-rendered) |
| Backend 500 errors | `server_error`, `render_failure`, `element_missing` | `data_incorrect` (unless the 500 caused empty data) |
| Selector removed | `element_missing` | `data_incorrect`, `timeout_general`, `render_failure` |

3. **If incompatible:** Re-classify this test independently, ignoring the dominant pattern. Example:
   - Dominant: "console pod restarted 6 times"
   - Test error: "expected 5 items, got 0" (`failure_mode_category: data_incorrect`)
   - Question: "How does a pod restart cause a page to show 0 items instead of 5?"
   - Answer: It doesn't — the page rendered (showing 0), so the pod was running. This is a data issue, not a render issue.
   - Action: Re-investigate independently → likely PRODUCT_BUG (backend returned empty data)

4. **3-test threshold rule:** If more than 3 tests share the same classification AND the same `root_cause` explanation, independently re-investigate at least 1 test from that group to verify the explanation holds. If the re-investigation reveals a different root cause, flag the entire group for review.

**Output:** For each test, include a `causal_link` field in the reasoning:
```json
{
  "reasoning": {
    "summary": "...",
    "evidence": ["..."],
    "causal_link": "Pod restart at 14:32 caused page render timeout at 14:33 — 1 minute overlap confirms causal connection",
    "conclusion": "..."
  }
}
```

### Phase D5: Counter-Bias Validation (v3.3)

Before finalizing any classification, perform these mandatory checks:
- If AUTOMATION_BUG: Was B7 performed? Could a backend failure explain the missing element?
- If PRODUCT_BUG: Does the selector exist in console source? Is the test logic correct?
- If INFRASTRUCTURE: Is only one test affected? (suggests PRODUCT_BUG or AUTOMATION_BUG instead)
- If `failure_mode_category == 'data_incorrect'`: Have you verified the backend API response path? A data mismatch almost never results from infrastructure or selector issues.
- **Dominant signal check:** If a signal (e.g., pod restarts) is cited in more than 5 test classifications, verify at least 2 tests have a direct `causal_link` documented. If not, the signal may be over-attributed.
- Self-check: "If the first routing signal pointed to a DIFFERENT classification, would I reach the same conclusion?"

---

## Phase E: Feature Context & JIRA Correlation

**Purpose:** Build feature understanding via Knowledge Graph + JIRA, validate classification against feature intent, then search for existing bugs.

### Phase E0: Build Subsystem Context (Knowledge Graph)

For each `detected_components` entry from Phase B5, query Knowledge Graph to understand the subsystem and related components.

**When Knowledge Graph is available:**

```cypher
# 1. Get component info (subsystem, type)
MATCH (c:RHACMComponent)
WHERE c.label =~ '(?i).*search-api.*'
RETURN c.label, c.subsystem, c.type
```

```cypher
# 2. Get all components in the same subsystem
MATCH (c:RHACMComponent)
WHERE c.subsystem = 'Search'
RETURN c.label, c.type
```

```cypher
# 3. Check component dependencies (is failure in a dependency?)
MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent)
WHERE c.label =~ '(?i).*search-api.*'
RETURN dep.label as dependency, dep.subsystem as dep_subsystem
```

```
mcp__neo4j-rhacm__read_neo4j_cypher({
  "query": "MATCH (c:RHACMComponent) WHERE c.label =~ '(?i).*search-api.*' RETURN c.label, c.subsystem, c.type"
})
```

**Output:** subsystem name, components in workflow, dependency chain, whether failure is in the component itself or a dependency it relies on.

**Fallback (Knowledge Graph unavailable):** Use the `subsystem` field from ComponentExtractor's `detected_components` entries. This provides the subsystem name without the full component list or dependency chain.

### Phase E1: Carry Forward Path B2 Findings

If `classification_path == "B2"`, reuse the `jira_correlation` output from Phase D:
- `related_issues` — already found via JIRA search
- `match_confidence` — already assessed during classification

Skip to Phase E4 (bug search) since feature context was already gathered during Path B2 classification.

If classification was via Path A or Path B1, no B2 findings exist — proceed to Phase E2 for fresh feature context search.

### Phase E2: Search for Feature Stories and PORs (JIRA)

Search for the feature story that describes what the failing test validates. Use 3 strategies in order of specificity — stop when a relevant story is found. Max 3 JIRA search queries.

**Strategy 1: Polarion ID from test name**
```
# Extract RHACM4K-XXXX from test name
Regex: RHACM4K-\d+

mcp__jira__search_issues({
  "jql": "summary ~ 'RHACM4K-3046' OR description ~ 'RHACM4K-3046'",
  "max_results": 5
})
```

**Strategy 2: Component + subsystem from E0**
```
mcp__jira__search_issues({
  "jql": "project = ACM AND type = Story AND (summary ~ 'search-api' OR component = 'Search') ORDER BY updated DESC",
  "max_results": 5
})
```

**Strategy 3: Feature area keywords from test name**
```
# Parse test name for feature keywords
# "test_cluster_upgrade_digest" → "cluster upgrade"

mcp__jira__search_issues({
  "jql": "project = ACM AND type in (Story, Epic) AND summary ~ 'cluster upgrade' ORDER BY updated DESC",
  "max_results": 5
})
```

### Phase E3: Read Feature Stories, Acceptance Criteria, Linked PRs

For each relevant story found in E2, read the full details:

```
mcp__jira__get_issue({ "issue_key": "ACM-22079" })
```

**Extract from story:**
- **Summary/description** — feature intent (what it should do)
- **Acceptance criteria** — expected behavior
- **Linked PRs** — recent changes that may have caused regression
- **Fix versions** — is this a new feature? (new features may have expected instability)
- **Linked Epics/PORs** — broader plan context

**For linked PORs or Epics, read those too:**
```
mcp__jira__get_issue({ "issue_key": "ACM-20000" })
```

**Feature-informed classification validation:**

| Finding | Impact |
|---------|--------|
| Acceptance criteria say X, product doesn't do X | Supports PRODUCT_BUG |
| Acceptance criteria changed, test checks old behavior | Supports AUTOMATION_BUG |
| Linked PR recently merged, test started failing | Supports PRODUCT_BUG (regression) |
| POR shows feature redesigned, test not updated | Supports AUTOMATION_BUG |

### Phase E4: Search for Related Bugs

Search for existing bugs related to the failure. Use enriched search terms from E0 (subsystem name, other components in subsystem) when available.

```
mcp__jira__search_issues({
  "jql": "project = ACM AND type = Bug AND status != Closed AND (summary ~ 'search-api' OR description ~ 'search-api' OR summary ~ 'Search') ORDER BY updated DESC",
  "max_results": 10
})
```

**Search patterns (enriched by E0 context):**
- Component name from error
- Subsystem name from Knowledge Graph
- Other components in the same subsystem
- Failing selector
- Feature area
- Error message keywords

### Phase E5: Known Issue Matching + Feature-Informed Validation

If related JIRA bugs found, get full details:
```
mcp__jira__get_issue({ "issue_key": "ACM-12345" })
```

- Check if bug matches exact symptoms
- Validate found bugs against subsystem context from E0
- Note JIRA key in analysis
- Adjust recommended_fix to reference JIRA

**Feature-informed validation (from E3):**
- Does the feature story from E3 contradict the current classification?
- If feature acceptance criteria say X and product doesn't do X → strengthens PRODUCT_BUG
- If feature was redesigned per POR and test wasn't updated → strengthens AUTOMATION_BUG
- If contradiction found, document it and adjust confidence accordingly

If matching JIRA exists:
```json
{
  "recommended_fix": "Known issue ACM-12345 - search-api index failures",
  "jira_correlation": {
    "search_performed": true,
    "related_issues": ["ACM-12345"],
    "match_confidence": "high"
  }
}
```

### Phase E6: Create/Link Issues (Optional)

When a definitive new bug is found with no existing JIRA:
```
mcp__jira__create_issue({
  "project_key": "ACM",
  "summary": "Component X returns 500 on Y operation",
  "description": "Found during z-stream analysis of pipeline Z...",
  "issue_type": "Bug",
  "priority": "Major",
  ...
})
```

To link related failures to the same root cause:
```
mcp__jira__link_issue({
  "link_type": "Relates",
  "inward_issue": "ACM-111",
  "outward_issue": "ACM-222"
})
```

---

## ACM-UI MCP Server Reference (19 Tools)

### Supported Versions

| Repo | Range | Latest GA | Dev |
|------|-------|-----------|-----|
| ACM Console (stolostron/console) | 2.11 - 2.17 | **2.16** | 2.17 (main) |
| Fleet Virt (kubevirt-ui/kubevirt-plugin) | 4.14 - 4.22 | **4.21** | 4.22 (main) |

ACM and CNV versions are **independent** - set each to match your target environment.

### Version Management Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `list_repos` | List available repos with versions | |
| `list_versions` | Show ACM/CNV version mappings | |
| `set_acm_version` | Set ACM Console branch | `set_acm_version('2.16')` |
| `set_cnv_version` | Set kubevirt-plugin branch | `set_cnv_version('4.21')` |
| `get_current_version` | Get active version | `get_current_version('acm')` |

### Cluster Detection Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `detect_cnv_version` | Auto-detect CNV from cluster | |
| `get_cluster_virt_info` | Comprehensive virt info | |

### Code Discovery Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `find_test_ids` | Find automation attributes | `find_test_ids('path/file.tsx', 'acm')` |
| `get_component_source` | Get file source code | `get_component_source('path/file.tsx', 'acm')` |
| `search_component` | Search by component name | `search_component('ClusterTable', 'acm')` |
| `search_code` | GitHub code search | `search_code('create-btn', 'acm')` |
| `get_route_component` | Map URL to source | `get_route_component('/clusters')` |

### Specialized Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `get_fleet_virt_selectors` | VM UI selectors | |
| `search_translations` | Find UI text | `search_translations('Create cluster')` |
| `get_acm_selectors` | QE repo selectors | `get_acm_selectors('catalog', 'clc')` |
| `get_component_types` | TypeScript interfaces | `get_component_types('path/types.ts', 'acm')` |
| `get_wizard_steps` | Wizard structure | `get_wizard_steps('path/wizard.tsx', 'acm')` |
| `get_routes` | All ACM navigation paths | |
| `get_patternfly_selectors` | PF v6 CSS fallbacks | `get_patternfly_selectors('button')` |

### Supported Repositories (6 Total)

| Key | Repository | Use Case |
|-----|------------|----------|
| `acm` | stolostron/console | ACM Console source |
| `kubevirt` | kubevirt-ui/kubevirt-plugin | Fleet Virt source |
| `acm-e2e` | stolostron/clc-ui-e2e | Cluster Lifecycle selectors |
| `search-e2e` | stolostron/search-e2e-test | Search selectors |
| `app-e2e` | stolostron/application-ui-test | Applications selectors |
| `grc-e2e` | stolostron/acmqe-grc-test | Governance selectors |

---

## JIRA MCP Server Reference (25 Tools)

### Issue Operations

| Tool | Purpose | Example |
|------|---------|---------|
| `search_issues` | JQL search | `search_issues(jql="project = ACM AND ...")` |
| `search_issues_by_team` | Search by team members | `search_issues_by_team(team_name="qe")` |
| `get_issue` | Full issue details | `get_issue(issue_key="ACM-12345")` |
| `create_issue` | Create bug/task | `create_issue(project_key="ACM", ...)` |
| `update_issue` | Update fields | `update_issue(issue_key="ACM-12345", ...)` |
| `transition_issue` | Change status | `transition_issue(issue_key="ACM-12345", transition="Done")` |
| `add_comment` | Comment on issue | `add_comment(issue_key="ACM-12345", comment="...")` |
| `log_time` | Log work hours | `log_time(issue_key="ACM-12345", time_spent="1h")` |
| `link_issue` | Link two issues | `link_issue(link_type="Relates", ...)` |
| `search_users` | Search users by name/email | `search_users(query="jsmith")` |

### Project & Metadata

| Tool | Purpose |
|------|---------|
| `get_projects` | List accessible projects |
| `get_project_components` | List components in a project |
| `get_link_types` | Available link types (Blocks, Relates, Duplicates) |
| `debug_issue_fields` | Show all raw fields for debugging |

### Team & Watcher Management

| Tool | Purpose |
|------|---------|
| `list_teams` / `add_team` / `remove_team` | Manage team configs |
| `assign_team_to_issue` | Add all team members as watchers |
| `add_watcher_to_issue` / `remove_watcher_from_issue` | Individual watchers |
| `get_issue_watchers` | List current watchers |
| `list_component_aliases` / `add_component_alias` / `remove_component_alias` | Component shortcuts |

---

## Polarion MCP Reference (25 Tools)

**Tool prefix:** `mcp__polarion__`

Polarion test case access + dependency discovery. Used by the Environment Oracle (Phase B) to fetch test case setup sections and discover infrastructure dependencies. Also available during Stage 2 for deeper queries.

**Key tools for z-stream analysis:**

| Tool | Purpose | Example |
|------|---------|---------|
| `get_polarion_setup_html` | Fetch test case setup HTML (dependency keywords) | `get_polarion_setup_html(project_id='RHACM4K', work_item_id='RHACM4K-XXXX')` |
| `get_polarion_test_steps` | Get test case steps | `get_polarion_test_steps(project_id='RHACM4K', work_item_id='RHACM4K-XXXX')` |
| `get_polarion_test_case_summary` | Get test case summary | `get_polarion_test_case_summary(project_id='RHACM4K', work_item_id='RHACM4K-XXXX')` |
| `get_polarion_work_item` | Full work item details | `get_polarion_work_item(project_id='RHACM4K', work_item_id='RHACM4K-XXXX')` |

**Setup:** Requires `POLARION_PAT` in `mcp/polarion/.env`. Run `bash mcp/setup.sh` or see `mcp/polarion/README.md`.

---

## Knowledge Graph MCP Reference (Optional)

**Tool:** `mcp__neo4j-rhacm__read_neo4j_cypher` — may not be connected in all environments. Check `feature_knowledge.kg_status.available` in core-data.json. If `false`, flag the gap explicitly in analysis-results.json (do NOT silently skip). Report to user that KG is unavailable, Tier 3-4 investigation is degraded, and include the remediation from `feature_knowledge.kg_status.remediation`.

### Available Queries

```cypher
# Get all dependents of a component
MATCH (dep)-[:DEPENDS_ON]->(c:RHACMComponent)
WHERE c.label =~ '(?i).*{component}.*'
RETURN DISTINCT dep.label

# Find common dependencies across components
MATCH (c)-[:DEPENDS_ON]->(common)
WHERE c.label IN ['comp1', 'comp2']
WITH common, count(DISTINCT c) as cnt
WHERE cnt >= 2
RETURN common.label

# Get component by subsystem
MATCH (c:RHACMComponent)
WHERE c.subsystem = 'Search'
RETURN c.label
```

### Subsystem Reference

| Subsystem | Key Components |
|-----------|----------------|
| Governance | grc-policy-propagator, config-policy-controller |
| Search | search-api, search-collector, search-indexer |
| Cluster | cluster-curator, managedcluster-import-controller |
| Provisioning | hive, hypershift, assisted-service |
| Observability | thanos-query, thanos-receive, metrics-collector |
| Virtualization | kubevirt-operator, virt-api, virt-controller |
| Console | console, console-api, acm-console |
| Infrastructure | klusterlet, multicluster-engine |

---

## Output Schema (analysis-results.json)

```json
{
  "analysis_metadata": {
    "jenkins_url": "<URL>",
    "analyzed_at": "2026-02-04T15:00:00Z",
    "run_directory": "runs/<dir>",
    "analyzer": "z-stream-analysis-agent-v3.2",
    "investigation_framework": "5-phase-systematic"
  },
  "investigation_phases_completed": ["A", "B", "C", "D", "E"],
  "mcp_queries_executed": [
    {"tool": "mcp__acm-ui__set_acm_version", "query": "2.16", "success": true},
    {"tool": "mcp__jira__search_issues", "query": "project = ACM...", "success": true}
  ],
  "cross_test_correlations": {
    "shared_selectors": {"#create-btn": ["test1", "test2"]},
    "shared_components": {"search-api": ["test3", "test4"]},
    "pattern_type": "single_selector_failure",
    "root_cause_affects_count": 3
  },
  "cascading_failure_analysis": {
    "analysis_performed": true,
    "root_cause_component": "search-api",
    "root_cause_subsystem": "Search",
    "dependent_components": ["console", "observability-dashboard"],
    "tests_affected_by_cascade": ["test3", "test4"]
  },
  "per_test_analysis": [
    {
      "test_name": "test_create_cluster",
      "feature_area": "CLC",
      "classification": "AUTOMATION_BUG",
      "confidence": 0.92,
      "backend_cross_check": {
        "performed": true,
        "backend_caused_ui_failure": false,
        "failing_components": [],
        "evidence": [],
        "overrides_path_a": false
      },
      "evidence_sources": [
        {"source": "console_search", "finding": "selector not found in product", "tier": 1},
        {"source": "timeline_evidence", "finding": "element_removed=true", "tier": 1}
      ],
      "ruled_out_alternatives": [
        {"classification": "PRODUCT_BUG", "reason": "No 500 errors, environment healthy"},
        {"classification": "INFRASTRUCTURE", "reason": "Cluster accessible, single test affected"}
      ],
      "reasoning": {
        "summary": "Selector '#create-btn' removed from console repo on 2026-01-15",
        "evidence": [
          "console_search.found = false",
          "similar_selectors = ['#cluster-create-btn']",
          "timeline_evidence['#create-btn'].element_removed = true",
          "No 500 errors in console log"
        ],
        "conclusion": "Automation uses outdated selector"
      },
      "root_cause": "Selector renamed in console commit abc123",
      "recommended_fix": {
        "action": "Update selector in automation",
        "steps": [
          "Edit cypress/views/cluster.js line 12",
          "Change '#create-btn' to '#cluster-create-btn'"
        ],
        "owner": "Automation Team"
      },
      "jira_correlation": {
        "search_performed": true,
        "related_issues": [],
        "match_confidence": "none"
      },
      "feature_context": {
        "subsystem": "Search",
        "components_involved": ["search-api", "search-collector", "search-indexer"],
        "feature_story": "ACM-22079",
        "feature_description": "ClusterCurator digest-based upgrades",
        "acceptance_criteria_summary": "Upgrades should use digest references...",
        "linked_prs": ["https://github.com/stolostron/console/pull/1234"],
        "por_reference": null,
        "knowledge_graph_context": {
          "subsystem_queried": true,
          "component_dependencies": ["console", "observability-dashboard"],
          "failure_in_dependency": false
        },
        "source": "knowledge_graph+jira"
      },
      "prerequisite_analysis": {
        "feature_area": "CLC",
        "all_prerequisites_met": true,
        "unmet_prerequisites": [],
        "matched_failure_mode": null
      },
      "playbook_investigation": {
        "failure_path_id": "clc-selector-rename",
        "failure_path_description": "Selector renamed in console repo",
        "steps_executed": [
          {"step": "Check console_search.found", "result": "false", "matched_expectation": true}
        ],
        "path_confirmed": true,
        "suggested_classification": "AUTOMATION_BUG",
        "confidence": 0.92
      },
      "cluster_investigation_detail": {
        "tier_reached": 2,
        "key_findings": ["All CLC pods healthy", "No degraded operators"],
        "commands_run": [
          {"command": "oc get pods -n open-cluster-management -l app=cluster-curator", "output_summary": "1/1 Running"}
        ]
      },
      "is_cascading_hook_failure": false,
      "blank_page_detected": false,
      "owner": "Automation Team",
      "priority": "HIGH"
    }
  ],
  "cluster_investigation_summary": {
    "cluster_reauth_status": "authenticated",
    "investigation_mode": "live",
    "tier_0_health": {
      "mch_status": "Running",
      "degraded_operators": [],
      "resource_pressure": {"memory": false, "cpu": false, "disk": false, "pid": false},
      "non_healthy_pods_count": 0
    },
    "component_health_overview": [
      {"feature_area": "CLC", "component": "cluster-curator", "status": "Running", "restart_count": 0, "key_finding": "Healthy"}
    ],
    "prerequisite_summary": [
      {"feature_area": "Search", "prerequisite": "search component enabled in MCH", "met": true, "tests_affected": 2}
    ]
  },
  "cluster_oracle": {
    "version": "1.0.0",
    "oracle_phase": "A",
    "feature_areas": ["Search"],
    "dependency_health": {
      "search-collector-addon": {
        "status": "degraded",
        "type": "addon",
        "detail": "Available on 3/5 clusters. Degraded on: spoke-2, spoke-3"
      },
      "search-api": {
        "status": "healthy",
        "type": "component",
        "detail": "Pod running, 0 restarts"
      },
      "search-indexer": {
        "status": "healthy",
        "type": "component",
        "detail": "Pod running, 0 restarts"
      }
    },
    "overall_feature_health": {
      "score": 0.60,
      "signal": "moderate",
      "blocking_issues": ["search-collector (addon): Available on 3/5 clusters"]
    },
    "knowledge_context": {
      "feature_components": ["search-collector", "search-indexer", "search-api", "console"],
      "internal_data_flow": ["search-collector → search-indexer → search-api → console"],
      "cross_subsystem_dependencies": ["multicluster-engine", "ocm-controller"],
      "transitive_chains": [
        {"source": "search-collector", "affects": ["search-indexer", "search-api", "console"], "reason": "collector pushes ManagedClusterView data — without it, index is stale and API returns empty results"}
      ],
      "component_details": {
        "search-collector": {
          "upstream": ["managed-clusters"],
          "downstream": ["search-indexer"]
        },
        "search-indexer": {
          "upstream": ["search-collector"],
          "downstream": ["search-api"]
        },
        "search-api": {
          "upstream": ["search-indexer"],
          "downstream": ["console"]
        }
      },
      "dependency_details": {
        "multicluster-engine": {
          "role": "Provides ManagedCluster lifecycle — required for spoke registration",
          "upstream": [],
          "downstream": ["search-collector", "ocm-controller"]
        }
      },
      "docs_context": {
        "docs_path": "/path/to/rhacm-docs",
        "available_directories": ["about", "add-ons", "applications", "clusters", "console", "governance", "observability", "search", "virtualization"],
        "note": "Use Read/Grep tools to search these docs during Stage 2 analysis."
      },
      "playbook_architecture": {
        "key_insight": "Search collector pushes ManagedClusterView data to hub. When collector addon is degraded on spoke clusters, the search index becomes stale and search-api returns incomplete or empty results."
      }
    },
    "polarion_discovery": {
      "test_case_context": {
        "RHACM4K-12345": {
          "title": "Search: verify search results include spoke resources",
          "description": "Validates that resources from all managed clusters appear in search results",
          "setup": "Requires search-collector addon deployed on all managed clusters. Requires at least 2 managed clusters in Ready state.",
          "test_steps": [
            {"step": 1, "action": "Navigate to Search page", "expected": "Search page loads"},
            {"step": 2, "action": "Search for kind:Pod", "expected": "Results include pods from all managed clusters"},
            {"step": 3, "action": "Verify result count matches expected", "expected": "Count >= 5 pods across all clusters"}
          ]
        }
      }
    }
  },
  "feature_context_summary": {
    "subsystems_investigated": ["Search"],
    "feature_stories_read": ["ACM-22079"],
    "linked_prs_found": 2,
    "knowledge_graph_queries": 3,
    "jira_feature_queries": 2
  },
  "summary": {
    "total_failures": 3,
    "by_classification": {
      "PRODUCT_BUG": 1,
      "AUTOMATION_BUG": 2,
      "INFRASTRUCTURE": 0
    },
    "cascading_hook_failures": 0,
    "blank_page_failures": 0,
    "overall_classification": "MIXED",
    "overall_confidence": 0.88
  },
  "jira_correlation": {
    "search_performed": true,
    "queries_executed": 2,
    "related_issues_found": ["ACM-12345"]
  },
  "action_items": [
    {"priority": 1, "action": "Fix search-api 500 errors", "owner": "Product Team", "type": "PRODUCT_BUG"},
    {"priority": 2, "action": "Update cluster selectors", "owner": "Automation Team", "type": "AUTOMATION_BUG"}
  ]
}
```

---

## Workflow Summary

### Step 1: Run Data Gathering

```bash
python -m src.scripts.gather "<JENKINS_URL>"
```

Wait for completion. Note the run directory path.

### Step 2: Execute 5-Phase Investigation

1. **Phase A:** Read core-data.json, check environment, detect patterns
2. **Phase B:** For each test, analyze extracted_context, timeline, console, MCP, repos
3. **Phase C:** Validate multi-evidence, check cascading, correlate patterns
4. **Phase D:** Route through 3-path classification (selector → A, timeout → B1, else → B2 JIRA investigation)
5. **Phase E:** Build feature context (Knowledge Graph + JIRA), validate classification against feature intent, search for related bugs

### Step 3: Generate Reports

```bash
python -m src.scripts.report runs/<dir>
```

---

## Key Principles

1. **Systematic over ad-hoc** - Follow 5 phases in order, every time
2. **Multi-evidence required** - Single source is never sufficient
3. **MCP tools mandatory** - Use ACM-UI, Knowledge Graph, JIRA when available
4. **Cross-test correlation** - Patterns reveal root causes
5. **Rule out alternatives** - Document why other classifications don't fit
6. **JIRA validation** - Check for known issues before finalizing
7. **Evidence over intuition** - Every claim backed by data
8. **Deterministic order** - Same investigation path = reproducible results

---

## Run Directory Structure

```
runs/<job>_<timestamp>/
│
│  Created by Stage 1 (gather.py):
├── core-data.json              # Primary data (read first)
├── run-metadata.json           # Run metadata (timing, version)
├── manifest.json               # File index
├── console-log.txt             # Full Jenkins console output
├── jenkins-build-info.json     # Build metadata (masked)
├── test-report.json            # Per-test failure details
├── environment-status.json     # Cluster health
├── element-inventory.json      # MCP element locations (if available)
├── repos/
│   ├── automation/             # Full cloned automation repo
│   ├── console/                # Full cloned console repo
│   └── kubevirt-plugin/        # For VM tests only
│
│  Created by Stage 2 (AI agent):
├── analysis-results.json       # YOUR OUTPUT
│
│  Created by Stage 3 (report.py):
├── Detailed-Analysis.md        # Report
├── per-test-breakdown.json     # Structured data for tooling
├── SUMMARY.txt                 # Brief summary
│
│  Created by feedback CLI (optional):
└── feedback.json               # Classification feedback (v3.0)
```

---

## Security Requirements

- All credentials masked in output (PASSWORD, TOKEN, SECRET, KEY patterns)
- READ-ONLY cluster operations only
- Complete audit trail in run directory
