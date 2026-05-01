# Agent Skills Open Standard Compliance Report

**Source:** https://agentskills.io (official Agent Skills open standard specification)
**Date:** 2026-05-01
**Scope:** All 18 ACM skills on the `skill-implementation` branch
**Purpose:** Identify strengths, gaps, and implementation instructions for each skill pack (test-case-generator, hub-health, z-stream) against the agentskills.io standard and best practices.

---

## Part 1: Current Strengths (What We Do Right)

### 1.1 Specification Compliance

All 18 skills fully comply with the agentskills.io specification:

| Spec Requirement | Our Status | Evidence |
|---|---|---|
| `name` field: 1-64 chars, lowercase+hyphens, matches directory | PASS | All 18 skills verified |
| `description` field: 1-1024 chars, WHAT + WHEN | PASS | All descriptions include trigger phrases |
| `compatibility` field: environment requirements | PASS | All 18 skills have it |
| Directory structure: SKILL.md + optional scripts/references/assets | PASS | Consistent structure across all skills |
| SKILL.md under 500 lines | PASS | Largest is 247 lines (acm-test-case-generator) |
| Progressive disclosure: metadata → body → references | PASS | All skills use references/ for detail |
| File references use relative paths from skill root | PASS | All reference links are relative |

### 1.2 Best Practices Compliance

| Best Practice | Our Status | Evidence |
|---|---|---|
| "Start from real expertise" | PASS | Skills extracted from 3 working apps with real production runs |
| "Refine with real execution" | PASS | Tested on ACM-30459, ACM-32282, live Azure cluster |
| "Design coherent units" | PASS | Each skill has a single clear purpose; composes with others |
| "Provide defaults, not menus" | PASS | Shared skills give one interface; orchestrators specify usage |
| "Favor procedures over declarations" | PASS | Steps describe HOW, not just WHAT |
| "Gotchas sections" (partial) | PARTIAL | Present in shared skills (jira, ui, polarion); missing in some app-specific skills |
| "Templates for output format" | PASS | Output schemas in failure-classifier, report templates in hub-health |
| "Checklists for multi-step workflows" | PASS | Phase-gates.md, self-review checklists in writer/reviewer |
| "Validation loops" | PASS | Quality review + programmatic enforcement loop in TC-gen |
| "Plan-validate-execute" | PASS | Synthesis → write → review → enforce pattern |
| "Bundling reusable scripts" | PASS | gather.py, report.py, review_enforcement.py, validate_conventions.py |

### 1.3 Cross-Platform Portability

Our skills work on 35+ platforms that support the Agent Skills standard (confirmed via agentskills.io client showcase):
- Claude Code, Claude.ai, Claude API
- Cursor, VS Code, GitHub Copilot
- Gemini CLI, OpenAI Codex
- Roo Code, Goose, Junie (JetBrains)
- Factory, Amp, OpenHands, and more

---

## Part 2: Gaps by Skill Pack

### 2.1 Test Case Generator Skills (acm-test-case-generator, acm-code-analyzer, acm-test-case-writer, acm-test-case-reviewer)

#### Gap A: No Eval Framework

**What's missing:** No `evals/evals.json` with test cases, assertions, or benchmark tracking.

**Why it matters:** agentskills.io says: "Running structured evaluations answers whether a skill works reliably — across varied prompts, in edge cases, better than no skill at all."

**Data we already have for evals:**

From `runs/ACM-30459/` (the story we analyzed exhaustively):
- Known correct answers: filter logic (`cluster-name`, `cluster-namespace`, `policy.open-cluster-management.io/*`), field order (Name, Engine, Cluster, Kind, API version, Labels), empty state ("-" dash)
- Known failure modes: Run 1 had 3 critical factual errors; Run 2 fixed them but added wrong filter prefixes

From `runs/ACM-32282/` (GPU count column):
- Known correct answers: metric name (`node_accelerator_card_info`), conditional on observability, column position (last after RAM), tooltip text verified via MCP
- Known quality gaps: step granularity (combined tooltip+link), embedded CLI

**Implementation:**

Create `acm-test-case-generator/evals/evals.json`:
```json
{
  "skill_name": "acm-test-case-generator",
  "evals": [
    {
      "id": 1,
      "prompt": "Generate a test case for ACM-30459",
      "expected_output": "Test case for labels on PolicyTemplateDetails page with correct filtering, field order, and empty state",
      "assertions": [
        "Label filtering references isUserDefinedPolicyLabel with exact conditions: key !== 'cluster-name' && key !== 'cluster-namespace' && !key.startsWith('policy.open-cluster-management.io/')",
        "Field order states: Name, [Namespace if namespaced], Engine, Cluster, Kind, API version, Labels",
        "Empty state behavior: Labels field IS always present, shows '-' when no user-defined labels",
        "Component used: AcmLabels (NOT renderLabelsAsList)",
        "Route includes optional apiGroup parameter: :apiGroup?",
        "Does NOT list 'cluster.open-cluster-management.io/' or 'velero.io/' as filtered prefixes",
        "Translation key: table.labels -> Labels"
      ]
    },
    {
      "id": 2,
      "prompt": "Generate a test case for ACM-32282 with live validation on https://console-openshift-console.apps.ashafi-test-az-217.az.dev09.red-chesterfield.com",
      "expected_output": "Test case for GPU count column in Nodes table with correct metric name, conditional rendering, and sorting",
      "assertions": [
        "Metric name is node_accelerator_card_info (NOT accelerator_card_info)",
        "Column is conditional on MultiClusterObservability installation",
        "Column position is last (after RAM)",
        "Each step verifies ONE distinct behavior (no combined tooltip+link steps)",
        "Backend validation is in a dedicated step (not embedded in UI step)",
        "Sorting is described as numeric not alphabetical",
        "Negative scenario included (column absent without observability)",
        "Follow-up PR #6062 metric rename is documented in Notes"
      ]
    },
    {
      "id": 3,
      "prompt": "Generate a test case for ACM-32282",
      "expected_output": "Same as eval 2 but without live validation -- graceful degradation should still produce correct test case",
      "assertions": [
        "All assertions from eval 2 apply",
        "No live validation phase ran (or noted as skipped)",
        "Test case is still factually correct without live cluster data"
      ]
    }
  ]
}
```

#### Gap B: Missing Gotchas in Writer Skill

**What's missing:** The `acm-test-case-writer` has rules but no explicit "Gotchas" section. agentskills.io says gotchas are "the highest-value content in many skills."

**Known gotchas (from our analysis reports):**
1. Never copy filter rules from the PR diff — the merged source may differ. Always read via `get_component_source`.
2. Test file data (`.test.tsx`) is MOCK DATA, not rendering behavior. Never derive UI behavior from test fixtures.
3. `cols.push()` in React means the field is appended at the END of the array, not inserted at the push() call site.
4. When the description says "field after Name" — verify the full array construction; it likely means after ALL preceding fields.
5. Translation key `table.labels` maps to display text "Labels" — the key and the display text are different.

**Implementation:** Add a `## Gotchas` section to `acm-test-case-writer/SKILL.md` with these 5 items.

#### Gap C: No `metadata` Version Field

**What's missing:** No version tracking in frontmatter.

**Implementation:** Add to all TC-gen skills:
```yaml
metadata:
  author: acm-qe
  version: "1.0.0"
```

---

### 2.2 Hub Health Skills (acm-hub-health-check, acm-cluster-remediation, acm-knowledge-learner)

#### Gap D: No Eval Framework

**What's missing:** No `evals/evals.json` with test cases.

**Data we already have:**

From the Azure cluster test (ACM 2.17.0-176):
- Known correct answers: MCH namespace `ocm`, verdict HEALTHY, 0 NetworkPolicies, 0 non-Running pods, search-postgres 16,884 resources, console image from `quay.io:443/acm-d/console`
- All 14 traps should be NOT triggered on this healthy cluster

**Implementation:**

Create `acm-hub-health-check/evals/evals.json`:
```json
{
  "skill_name": "acm-hub-health-check",
  "evals": [
    {
      "id": 1,
      "prompt": "Quick sanity check on my hub",
      "expected_output": "Phase 1 only, MCH namespace discovered dynamically, operator replicas checked, verdict produced within ~30s",
      "assertions": [
        "Only Phase 1 executed (not Phases 2-6)",
        "MCH namespace discovered via oc get mch -A (NOT hardcoded open-cluster-management)",
        "Operator replica check performed for both multiclusterhub-operator and multicluster-engine-operator",
        "Verdict is one of: HEALTHY, DEGRADED, CRITICAL (no qualifiers)",
        "Execution time under 60 seconds"
      ]
    },
    {
      "id": 2,
      "prompt": "How's my hub health?",
      "expected_output": "Standard check running Phases 1-4 with layer-by-layer verification",
      "assertions": [
        "Phases 1-4 executed",
        "Phase 2 reads knowledge files (component-registry, healthy-baseline, diagnostic-traps)",
        "Phase 3 checks layers bottom-up (foundational before component)",
        "Infrastructure guards checked BEFORE pod health (NetworkPolicies, ResourceQuotas)",
        "All 14 diagnostic traps checked with TRIGGERED/NOT triggered/N-A status",
        "Search-postgres data integrity verified (row count query)",
        "Console image integrity verified (compared against expected prefix)",
        "Report uses 9-field format for any issues found",
        "Verdict is mechanical (any CRIT -> CRITICAL, any WARN without CRIT -> DEGRADED, else HEALTHY)"
      ]
    },
    {
      "id": 3,
      "prompt": "Why are my managed clusters showing Unknown?",
      "expected_output": "Targeted investigation focused on cluster connectivity and addon health",
      "assertions": [
        "Investigation focuses on managed cluster health (not broad diagnostic)",
        "Checks managedcluster conditions and lease freshness",
        "Checks addon health on affected clusters",
        "References Trap 6 (ManagedCluster NotReady) and Trap 7 (All addons down)",
        "Provides root cause with evidence"
      ]
    }
  ]
}
```

#### Gap E: Gotchas Not Labeled as "Gotchas"

**What's missing:** The hub-health skill has the 14 traps which ARE gotchas, but they're in a reference file, not in the main SKILL.md. The agentskills.io guide says: "Keep gotchas in SKILL.md where the agent reads them before encountering the situation."

**Implementation:** Add a brief `## Diagnostic Gotchas (Top 5)` section to `acm-hub-health-check/SKILL.md` with the most critical traps inline:
```markdown
## Diagnostic Gotchas

1. MCH/MCE status says "Running" but operator has 0 replicas -- status is STALE (Trap 1)
2. NetworkPolicies in ACM namespaces make pods LOOK healthy while being non-functional (Trap 11)
3. Search pods all Running but database has 0 rows -- data was lost (Trap 3)
4. ResourceQuota silently prevents pod scheduling -- pods can't be recreated (Trap 9)
5. All addons unavailable on ALL clusters? Check addon-manager pod FIRST (Trap 7)

See references/knowledge/diagnostics/common-diagnostic-traps.md for all 14 traps.
```

#### Gap F: Remediation Skill Missing Gotchas

**What's missing:** `acm-cluster-remediation` has no gotchas about common remediation mistakes.

**Implementation:** Add:
```markdown
## Remediation Gotchas

1. `oc delete pod` restarts a pod. `oc delete deployment` REMOVES the deployment permanently -- never do this.
2. After `oc rollout restart`, wait for ALL pods to become Ready before checking health. Don't verify immediately.
3. ResourceQuota in ACM namespaces is likely a test artifact -- verify ownerReferences before assuming it's intentional.
4. Scaling to 0 is reversible. Deleting is not. Always prefer scale over delete.
5. Post-remediation verification must re-run Phase 1 + Phase 3 -- don't skip.
```

---

### 2.3 Z-Stream Analysis Skills (acm-z-stream-analyzer, acm-failure-classifier, acm-cluster-investigator, acm-data-enricher)

#### Gap G: No Eval Framework

**What's missing:** No `evals/evals.json` with test cases. This is the most complex skill pack and arguably needs evals the most.

**Data we already have:**

From `runs/2026-04-20_17-54-34_clc-e2e-pipeline/`:
- `core-data.json` (10,921 lines) with 64 failed tests
- `cluster-diagnosis.json` (856 lines) with full health assessment
- Previous `analysis-results.json` with per-test classifications

**Implementation:**

Create `acm-z-stream-analyzer/evals/evals.json`:
```json
{
  "skill_name": "acm-z-stream-analyzer",
  "evals": [
    {
      "id": 1,
      "prompt": "Analyze this Jenkins run: https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/qe-acm-automation-poc/job/alc_e2e_tests/2745/",
      "expected_output": "Full pipeline: gather -> cluster diagnostic -> data enrichment -> classification -> report",
      "assertions": [
        "Stage 1 produces core-data.json with failed tests array",
        "Stage 1.5 produces cluster-diagnosis.json with structured health data",
        "Data enrichment populates console_search.found for each test with a failing_selector",
        "Every test has a classification (one of 7 valid types)",
        "Every classification has 2+ evidence sources",
        "Every classification has ruled_out_alternatives",
        "Every classification has root_cause_layer (1-12) and root_cause_layer_name",
        "After-all hook cascades are classified NO_BUG without investigation",
        "Dead selectors (console_search.found=false, 3+ tests) are AUTOMATION_BUG without investigation",
        "Provably linked grouping uses STRICT criteria only (not 'same feature area')",
        "Output file is analysis-results.json with per_test_analysis field (NOT failed_tests)",
        "Report generates Detailed-Analysis.md and analysis-report.html"
      ]
    },
    {
      "id": 2,
      "prompt": "Classify this test failure: element '#cluster-dropdown-toggle' not found in the DOM",
      "expected_output": "Investigation with selector verification and timeline analysis",
      "assertions": [
        "Checks if selector exists in official source via acm-ui-source MCP",
        "If not found in official source: AUTOMATION_BUG (dead selector)",
        "If found in official source but not on page: investigates backend health",
        "Does NOT assume INFRASTRUCTURE without counterfactual verification",
        "Provides root_cause_layer and evidence_sources"
      ]
    }
  ]
}
```

#### Gap H: Classification Gotchas Missing from SKILL.md

**What's missing:** The anti-patterns section is in `acm-cluster-investigator` but NOT in `acm-failure-classifier`. The classifier is the entry point skill and should have top-level gotchas.

**Implementation:** Add to `acm-failure-classifier/SKILL.md`:
```markdown
## Classification Gotchas

1. ANCHORING BIAS: When you find one strong signal (tampered image, NetworkPolicy), it does NOT explain every test failure. MUST run counterfactual per test.
2. "Selector not found" does NOT always mean AUTOMATION_BUG -- check if the feature's backend is down first (backend down = element can't render regardless of selector correctness).
3. Test file data (.test.tsx) is MOCK DATA. Mock objects showing system labels rendered does NOT mean the UI renders them -- verify against production source.
4. `console_search.found=false` on a tampered-image cluster tells you nothing about the OFFICIAL source. Must verify via acm-ui-source MCP `search_code`.
5. "Same feature area" is NOT a valid grouping criterion. Only: same selector+function, same before-all hook, or same spec+error+line.
6. A selector missing from BOTH tampered AND official source = AUTOMATION_BUG (dead selector), not INFRASTRUCTURE.
7. Layer discrepancy (lower layer healthy, higher layer defective) = Tier 1 PRODUCT_BUG evidence. Don't attribute to infrastructure.
```

#### Gap I: Data Enricher Missing Gotchas

**What's missing:** `acm-data-enricher` has no gotchas about common enrichment mistakes.

**Implementation:** Add:
```markdown
## Enrichment Gotchas

1. PatternFly classes (pf-v6-c-*) are generated at runtime by React components. Grep won't find them as literal strings -- derive the component name and search for that instead.
2. Hex color codes (#DB242F) extracted from error HTML are NOT CSS selectors. Skip them.
3. `git log -S` is case-sensitive. Normalize the selector before searching.
4. When automation repo added a selector that product doesn't have yet: direction is `automation_ahead_of_product`, not `removed_from_product`.
5. Task 4 gap filling: validate EVERY constructed failure path entry against the schema before writing. Invalid regex patterns crash the matcher.
```

---

### 2.4 Shared Skills (acm-jira-client, acm-ui-source, acm-polarion-client, acm-neo4j-explorer, acm-cluster-health, acm-jenkins-client, acm-knowledge-base)

#### Gap J: No `metadata` Version Fields

**What's missing:** None of the shared skills have `metadata.version`.

**Implementation:** Add to ALL 7 shared skills:
```yaml
metadata:
  author: acm-qe
  version: "1.0.0"
```

#### Gap K: Description Triggering Not Tested

**What's missing:** We haven't systematically tested whether skill descriptions trigger on the right prompts and DON'T trigger on wrong prompts.

**Implementation:** Create a triggering test matrix:

| Prompt | Should Trigger | Should NOT Trigger |
|---|---|---|
| "Generate a test case for ACM-30459" | acm-test-case-generator | acm-z-stream-analyzer, acm-hub-health-check |
| "Analyze this Jenkins run: URL" | acm-z-stream-analyzer | acm-test-case-generator, acm-hub-health-check |
| "Check my hub health" | acm-hub-health-check | acm-z-stream-analyzer, acm-test-case-generator |
| "Fix my cluster" | acm-cluster-remediation | acm-hub-health-check (shouldn't fix, only diagnose) |
| "What's this JIRA ticket about?" | acm-jira-client | acm-test-case-generator (shouldn't trigger full pipeline) |
| "Search for test cases in Polarion" | acm-polarion-client | acm-test-case-reviewer |
| "Read the governance architecture" | acm-knowledge-base | acm-hub-health-check |
| "Review this test case file" | acm-test-case-reviewer | acm-test-case-writer |

Run these prompts in Claude Code and record which skills activate. Adjust descriptions based on results.

---

## Part 3: Implementation Summary

### By Priority

| Priority | Gap | Skill(s) Affected | Effort | Impact |
|---|---|---|---|---|
| P1 | Eval framework (evals.json) | TC-gen, hub-health, z-stream orchestrators | Medium (write JSON, set up workspace) | High -- enables systematic improvement |
| P2 | Gotchas in SKILL.md | failure-classifier, test-case-writer, hub-health-check, data-enricher, cluster-remediation | Low (add markdown sections) | High -- prevents known mistakes |
| P3 | `metadata.version` | All 18 skills | Low (add 3 lines to each frontmatter) | Medium -- version tracking for updates |
| P4 | Description triggering test | All 18 skills | Low (manual test, record results) | Medium -- ensures correct activation |

### Files to Create

```
.claude/skills/acm-test-case-generator/evals/evals.json
.claude/skills/acm-hub-health-check/evals/evals.json
.claude/skills/acm-z-stream-analyzer/evals/evals.json
```

### Files to Modify (add Gotchas sections)

```
.claude/skills/acm-failure-classifier/SKILL.md          -- add ## Classification Gotchas (7 items)
.claude/skills/acm-test-case-writer/SKILL.md            -- add ## Gotchas (5 items)
.claude/skills/acm-hub-health-check/SKILL.md            -- add ## Diagnostic Gotchas (5 items)
.claude/skills/acm-cluster-remediation/SKILL.md         -- add ## Remediation Gotchas (5 items)
.claude/skills/acm-data-enricher/SKILL.md               -- add ## Enrichment Gotchas (5 items)
```

### Files to Modify (add metadata.version)

All 18 `SKILL.md` files -- add 3 lines to frontmatter:
```yaml
metadata:
  author: acm-qe
  version: "1.0.0"
```

---

## Part 4: Eval Workspace Structure (for future iterations)

After implementing evals, each skill pack should maintain an eval workspace:

```
acm-test-case-generator-workspace/
├── iteration-1/
│   ├── eval-acm-30459/
│   │   ├── with_skill/
│   │   │   ├── outputs/test-case.md
│   │   │   ├── timing.json          # {"total_tokens": 84852, "duration_ms": 751000}
│   │   │   └── grading.json         # per-assertion PASS/FAIL with evidence
│   │   └── without_skill/
│   │       ├── outputs/test-case.md
│   │       └── grading.json
│   ├── eval-acm-32282/
│   │   └── ...
│   └── benchmark.json               # {"with_skill": {"pass_rate": 0.92}, "without_skill": {"pass_rate": 0.45}}
├── iteration-2/
│   └── ...                           # After skill improvements
```

This gives us:
- **Quantitative comparison** -- pass rate with vs without the skill
- **Regression detection** -- does a skill change break previously passing evals?
- **Iteration tracking** -- how does quality improve across versions?
- **Token/time cost** -- what does the skill cost in resources?
