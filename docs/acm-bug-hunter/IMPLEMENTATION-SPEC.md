# ACM Bug Hunter -- Implementation Specification

## For: Claude Code implementation in `ai_systems_v2/skills/investigation/acm-bug-hunter/`

This document is the complete specification for building the `acm-bug-hunter` skill. It contains every decision made during the design phase, including architectural choices, confidence mechanisms, iteration limits, safety protocols, and integration with existing skills. Implement exactly as specified unless a technical constraint requires deviation -- in which case, document the deviation and rationale.

---

## 1. What This Skill Does

The skill takes a **test case** as input (Polarion ID, local markdown file, or inline content) and autonomously hunts for **bugs in the feature implementation** that the test case describes. It does NOT audit the test case quality -- it uses the test case as a starting point to systematically investigate whether the implemented feature has bugs that the test case scenarios might miss.

The name is `acm-bug-hunter` (not "test-case-auditor") because the goal is to find bugs in the implementation, not to review the test case itself.

### Success Criteria

A run is successful if it either:
- **Finds real bugs** in the implementation (frontend or backend), OR
- **Provides high-confidence evidence** that the implementation is solid across all investigated dimensions

Both are valuable outcomes.

### How It Differs from Existing Skills

| Existing Skill | Relationship |
|----------------|--------------|
| `grill-me` | Inspiration for the questioning methodology, but this skill asks itself and investigates autonomously instead of asking the user |
| `acm-test-case-generator` | Opposite direction -- that skill builds test cases from JIRA tickets; this skill takes a finished test case and stress-tests the implementation it covers |
| `acm-failure-classifier` | Analyzes *failed* test runs; this skill analyzes *passing or untested* cases to predict bugs proactively |
| `acm-cluster-health` 12-layer model | The 10-dimension model here was NOT adapted from the 12-layer infrastructure model. The 12-layer model maps infrastructure failure domains (compute, network, storage). This skill's dimensions map implementation correctness categories derived from ACM's architecture. |

---

## 2. Input Handling

The skill accepts one of three inputs:

1. **Polarion test case ID** (e.g., `RHACM4K-61726`) -- fetched via Polarion MCP (`get_polarion_work_item`, `get_polarion_test_steps`)
2. **Local markdown file** (e.g., a `.md` file with test steps) -- read from disk
3. **Inline test case content** pasted in the conversation

From the test case, the skill extracts:
- JIRA ticket reference (from "Dev JIRA Coverage" or description field)
- PR number (from JIRA or test case metadata)
- Feature area and ACM version
- Test steps and expected results
- Setup requirements and prerequisites

---

## 3. The 10-Dimension Analysis Model

### Origin and Rationale

Derived from two complementary sources:

1. **ACM 8-subsystem architecture** (primary source of universality): Hub-spoke ManifestWork delivery, console plugin proxy chain, search collector pipeline, addon framework, GRC compliance propagation, ALC channel/subscription deployment, observability metrics chain, cluster lifecycle (Hive/HyperShift).

2. **77 existing Console/CLC Polarion test cases** (validation for one area): RBAC wizard flows, Fleet Virt VM lifecycle, CCLM migration, GRC policy labels, Search cluster-proxy, OIDC. These validated the model for Console specifically but do NOT represent all ACM areas.

The infrastructure 12-layer model (compute, network, storage, etc.) was intentionally NOT reused because those are infrastructure failure domains, not implementation correctness dimensions.

**Bias acknowledgment:** Evidence citations below are drawn primarily from Console/CLC test cases. Question templates must adapt dynamically based on the detected feature area.

### The 10 Dimensions

```
    BUGS SURFACE HERE (top)
    ─────────────────────────
    Dim 10: Observable Output
    Dim  9: Failure & Recovery Paths
    Dim  8: Boundary & Edge Conditions
    Dim  7: State & Transition Logic
    Dim  6: Integration Surface
    Dim  5: Data Pipeline Integrity
    Dim  4: Multicluster Propagation
    Dim  3: Authorization Chain
    Dim  2: Resource Lifecycle
    Dim  1: Specification Fidelity
    ─────────────────────────
    ROOT GAPS LIVE HERE (bottom)
```

### Dimension 1: Specification Fidelity

Does the implementation match what was specified?

- Compare JIRA acceptance criteria to implemented behavior in the PR diff
- Compare API contracts (CRD schemas, webhook validations) to what the code actually enforces
- Check for spec drift: role names changed between versions, field renames, deprecated APIs
- Verify the test case tests the right thing (not a stale version of the spec)
- Tools: JIRA MCP, GitHub MCP (PR diff), ACM Source MCP (CRD schemas)
- Skip when: test case has no JIRA reference

### Dimension 2: Resource Lifecycle

Are resources created, read, updated, and deleted correctly?

- Trace each resource the test case creates: create with all required fields? Update preserves untouched fields? Delete cleans up dependents (finalizers, owner references)?
- Check for orphaned resources, naming conflicts, label selector collisions, namespace scoping errors
- Verify webhook validations prevent invalid resource creation
- Tools: ACM Source MCP (controller code, webhook code), `oc` CLI, GitHub MCP
- Skip when: test case is read-only/observational

### Dimension 3: Authorization Chain

Are permissions checked correctly at every hop?

- ACM auth chain: User token -> OCP Console -> ConsolePlugin proxy (UserToken forwarding) -> ACM console backend -> Kubernetes API -> controllers
- Multicluster: hub RBAC -> ManifestWork -> spoke RBAC -> ClusterPermission/MCRA
- Check positive and negative authorization paths
- Check `oc auth can-i` alignment with UI state
- Tools: ACM Source MCP (RBAC code), `oc auth can-i`, Neo4j RHACM
- Skip when: test uses cluster-admin and doesn't test permission boundaries

### Dimension 4: Multicluster Propagation

Does the hub-to-spoke delivery chain work correctly?

- Hub CR -> Controller -> ManifestWork -> klusterlet work-agent -> spoke resources -> status back to hub
- Addons: ClusterManagementAddOn + Placement -> ManagedClusterAddOn -> ManifestWork -> spoke agent
- Verify hub actions reach spoke, status propagation back, ManifestWork ordering, addon health
- Tools: `acm-kubectl` MCP, `oc get managedclusteraddons/manifestwork`, Neo4j RHACM
- Skip when: test is hub-only

### Dimension 5: Data Pipeline Integrity

Does data flow correctly across component boundaries?

- Search: collectors -> indexer -> postgres -> search-api -> console
- Metrics: spoke -> observability -> thanos -> grafana
- Policy: spoke compliance -> hub -> propagator -> console
- RBAC: MCRA -> controller -> ClusterPermission -> spoke SA
- Check for transformation errors, timing (indexing delay), data consistency
- Tools: ACM Source MCP, `acm-search` MCP, `oc` CLI, Neo4j RHACM
- Skip when: test doesn't cross component boundaries

### Dimension 6: Integration Surface & Cross-Component Probing

The most thorough dimension. 5 sub-steps:

**6.1: Dependency Mapping** -- Neo4j RHACM dependency graph, classify REQUIRED/OPTIONAL/INFORMATIONAL

**6.2: Dependency Health Audit (Read-Only)** -- Verify REQUIRED dependencies exist and are healthy

**6.3: Data Workflow Trace (Read-Only)** -- Trace data path across component boundaries in source code

**6.4: Integration Probing (Minimal Resource Creation)** -- Create small probe resources to verify integration paths. Full safety protocol below.

**6.5: Cleanup and Verification (MANDATORY)** -- Delete all probe resources, verify cleanup.

#### 6.4 Safety Protocol (MANDATORY)

```
BEFORE creating ANY resource:
  1. PLAN: Write out the exact YAML/command
  2. NAMESPACE: Use dedicated "tca-probe-<timestamp>"
  3. LABEL: Every resource gets "tca-probe=true" and "tca-session=<timestamp>"
  4. SCOPE: Prefer namespaced over cluster-scoped
  5. MINIMAL: Smallest possible definition, no real workloads/images/secrets
  6. INVENTORY: Running list of every resource created
  7. DRY-RUN FIRST: oc apply --dry-run=server
  8. IMPACT CHECK: Check resourcequota, limitrange, validatingwebhookconfigurations
  9. ONE AT A TIME: Never batch-apply
 10. TIMEOUT: 60 seconds, then abandon
```

Allowed probe types: Namespaces (tca-probe-*), ConfigMaps, labels/annotations on probe namespace, ManagedClusterSetBindings, minimal CRs for the feature's own CRDs.

Prohibited: Deployments/Pods/StatefulSets, Secrets with real credentials, ClusterRoleBindings/ClusterRoles, ManagedClusterActions/Views, anything triggering cloud provider calls.

#### 6.5 Cleanup Rules

```
  1. Only delete resources with label "tca-probe=true" AND "tca-session=<this-session>"
  2. NEVER delete in system namespaces (openshift-*, kube-*, open-cluster-management*)
  3. NEVER use broad selectors like "oc delete all"
  4. Delete namespace LAST
  5. Verify cleanup with final label-based query
  6. Log every deletion
```

### Dimension 7: State & Transition Logic

- Map the state machine, check intermediate states the test case doesn't verify
- Check side effects of modifying one resource on another
- Check eventual consistency handling
- Tools: ACM Source MCP (state management code), JIRA comments
- Skip when: test is stateless

### Dimension 8: Boundary & Edge Conditions

- Zero items, one item, maximum items, special characters, concurrent operations, permission boundaries, empty sets, intersections
- Tools: ACM Source MCP (conditional branches, validation code), rhacm-docs (official documentation)
- Always applies

### Dimension 9: Failure & Recovery Paths

- Error handling for invalid input, network failures, API errors
- Partial failure scenarios, recovery/rollback, error message accuracy
- Controller reconciliation failures
- Tools: ACM Source MCP (error handling code), JIRA (existing bugs)
- Skip when: purely happy-path with no known failure modes (rare)

### Dimension 10: Observable Output

- UI tests: UI reflects backend state? Buttons enabled/disabled correctly? Labels accurate?
- Non-UI tests: CR status conditions accurate? CLI output correct? Compliance status matches reality?
- All tests: Observable output matches actual state verified by `oc` CLI?
- A discrepancy = strong evidence of product bug
- Tools: ACM Source MCP (rendering/status code), browser MCP (if live env + UI), `oc` CLI
- Always applies

### Cross-Area Applicability

Each dimension applies across ALL ACM areas with area-specific questions:

| Area | Key Dimensions | Example Question |
|------|---------------|------------------|
| Console RBAC | Dim 3, 10 | Does UI button state match `oc auth can-i`? |
| GRC | Dim 4, 7 | Does compliance state machine handle inform vs enforce? |
| ALC | Dim 2, 4 | Does Subscription lifecycle clean up Deployables? |
| Observability | Dim 5, 6 | Does metrics pipeline from spoke reach Thanos? |
| Submariner | Dim 4, 6 | Does SubmarinerConfig reach spoke gateway? |
| Cluster LC | Dim 2, 7 | Does deprovision clean up all cloud resources? |

### Dimension Applicability Matrix

```
Dimension                    | UI Test | CLI/API Test | Policy Test | Install Test
-----------------------------|---------|--------------|-------------|-------------
1. Specification Fidelity    | YES     | YES          | YES         | YES
2. Resource Lifecycle        | if CRUD | YES          | YES         | YES
3. Authorization Chain       | if RBAC | if non-admin | if non-admin| skip
4. Multicluster Propagation  | if spoke| YES          | YES         | skip
5. Data Pipeline Integrity   | if data | if cross-svc | if status   | skip
6. Integration Surface       | depends | depends      | depends     | YES
7. State & Transition Logic  | if CRUD | if stateful  | if status   | if upgrade
8. Boundary & Edge Cases     | YES     | YES          | YES         | YES
9. Failure & Recovery        | YES     | YES          | YES         | YES
10. Observable Output        | YES     | YES          | YES         | YES
```

---

## 4. Orchestrator-Investigator Architecture

### Why Subagents, Not Inline

Two problems with inline investigation:

1. **Context pressure**: 10 dimensions with multiple MCP tool calls accumulates massive context. Quality degrades by dimension 7.
2. **Self-bias**: When the same agent formulates AND answers questions, it confirms its own assumptions. Separate context windows force evidence-based reasoning.

### Roles

- **Orchestrator** = the lead/skeptic. Has full Phase 1 context. Identifies critical paths, evaluates subagent findings, catches false negatives (missed bugs) and false positives (hallucinated bugs). Stays in the main conversation.
- **Dimension subagent** = the focused engineer. Gets a targeted brief for ONE dimension. Fresh context window. Uses MCP tools to gather evidence. Returns structured findings with confidence assessment.

### The Confidence Mechanism (Hybrid Model)

Inspired by the [ralph-orchestrator "Confession" pattern](https://github.com/mikeyobrien/ralph-orchestrator/issues/74) and [OpenAI's confessions research](https://alignment.openai.com/confessions/).

Each subagent returns TWO outputs:

**A) Investigation Findings** (optimized for thoroughness):
- For each question: evidence found, tool calls made, classification (CLEAN / GAP / POTENTIAL_BUG / CONFIRMED_BUG)
- Any NEW questions that emerged during investigation

**B) Confidence Report** (optimized for honesty -- the "confession"):
- **Evidence Inventory** (authoritative signal):
  - Source code verified: YES/NO (which files read)
  - API/CLI verified: YES/NO (which commands run)
  - Counter-case checked: YES/NO (what counter-evidence was sought)
  - Contradicting evidence found: YES/NO (what contradicts the finding)
  - JIRA/docs cross-referenced: YES/NO
- **Self-Assessed Confidence Score**: 0-100% per finding (secondary signal)
- **Uncertainties and Assumptions**: What the subagent is NOT sure about
- **Single Easiest Item to Verify**: One concrete, verifiable claim the orchestrator can spot-check to calibrate trust in the entire report

### How the Orchestrator Evaluates Findings

The orchestrator uses the Evidence Inventory as the authoritative signal. The self-assessed number is a secondary gut-check:

1. **If evidence inventory is thorough + self-assessed score is high**: Accept the finding.
2. **If evidence inventory is shallow + any score**: PUSHBACK with specific gaps ("you didn't read the webhook code -- read it").
3. **If evidence inventory is thorough + self-assessed score is LOW**: This is a signal the subagent noticed something it couldn't articulate. Worth pushing on: "Your evidence looks solid but your confidence is 55%. What's bothering you?"
4. **Trust calibration**: The orchestrator picks the "Single Easiest Item to Verify" from the confidence report and spot-checks it. If the spot-check passes, the rest of the report is trusted. If it fails, the entire report is treated skeptically.

### Per-Dimension Flow

```
FOR each applicable dimension (1 through 10):

  Step 0 - APPLICABILITY CHECK (orchestrator, inline):
    Check the dimension applicability matrix.
    If not applicable, skip with a one-line note.

  Step 1 - BRIEF PREPARATION (orchestrator, inline):
    Prepare a focused brief containing:
    - Test case content (steps, expected results, setup)
    - Relevant Phase 1 context (filtered to this dimension only)
    - 1-6 critical questions to investigate (dynamically allocated
      based on feature complexity and risk for this dimension)
    - Feature area (for area-appropriate investigation lens)
    - Available MCP tools and usage instructions
    - INSTRUCTION: "Return both Investigation Findings AND
      Confidence Report in the format specified."

  Step 2 - SPAWN SUBAGENT:
    Launch subagent with the brief. Subagent investigates and returns
    structured findings + confidence report.

  Step 3 - EVALUATE (orchestrator, inline):
    A) Check Evidence Inventory completeness
    B) Spot-check one item from "Single Easiest Item to Verify"
    C) Apply classification decision tree (see below)

  Step 4 - PUSHBACK LOOP (if needed):
    Resume SAME subagent with specific feedback.
    Max 3 back-and-forth rounds.
    Each round should increase confidence as more evidence is gathered.

  Step 5 - FRESH SUBAGENT (if still unresolved after 3 rounds):
    Spawn a FRESH subagent with:
    - Original brief
    - Orchestrator's specific objections and counter-evidence
    - NO access to prior subagent's reasoning (unbiased)
    Fresh subagent also gets max 3 rounds.
    Compare both subagents' evidence. Stronger evidence wins.
    If tied -> POTENTIAL_BUG with both perspectives.

  Step 6 - RECORD final classification + evidence trail.
```

### Classification Decision Tree

```
Subagent says CLEAN + evidence inventory is thorough:
  -> Accept CLEAN. Move on.

Subagent says CLEAN + evidence inventory is shallow:
  -> PUSHBACK: specify exactly what checks are missing.

Subagent says POTENTIAL_BUG + strong evidence:
  -> Orchestrator spot-checks via a DIFFERENT evidence path
     (e.g., if subagent found bug in source code, orchestrator
     checks PR diff, JIRA comments, or oc CLI to corroborate).
  -> If corroborated -> upgrade to CONFIRMED_BUG
  -> If not reproducible -> keep as POTENTIAL_BUG

Subagent says POTENTIAL_BUG + weak evidence:
  -> PUSHBACK: request harder proof with specific instructions.

Subagent says CONFIRMED_BUG:
  -> Orchestrator ALWAYS corroborates via a different evidence path.
  -> If contradicted -> downgrade, pushback.

Two subagents disagree (original vs fresh):
  -> Compare evidence inventories side by side.
  -> Stronger evidence wins.
  -> If tied -> POTENTIAL_BUG with both perspectives noted.
```

### Iteration Limits

| Limit | Value | Rationale |
|-------|-------|-----------|
| Questions per dimension | 1-6 (dynamic) | Orchestrator allocates based on feature complexity. High-risk dimensions get up to 6; simple ones get 1-2. |
| Back-and-forth rounds per subagent | Max 3 | Research shows diminishing returns after round 3-4. |
| Fresh subagent allowed | Yes, 1 per dimension | Unbiased second opinion when original subagent and orchestrator lock into disagreement. |
| Fresh subagent rounds | Max 3 | Same limit as original. |
| Total hard ceiling | None (per-dimension limits provide the bound) | With 10 dimensions, max 6 questions each, max 3+3 rounds = bounded by design. |

---

## 5. Phase Structure

### Phase 0: Parse Input, Detect Area, and Adapt

1. Read the test case (Polarion MCP or file read)
2. Extract JIRA ticket, PR number, feature area, ACM version
3. Extract test steps and expected results into structured format
4. **Detect feature area** from JIRA components, test case tags, file path, or content keywords. Map to: `console-rbac`, `console-general`, `fleet-virt`, `clusters`, `grc`, `alc`, `search`, `observability`, `submariner`, `install`, `hosted-clusters`, or `other`
5. **Load area-specific context**: Use detected area to determine:
   - Which dimensions get higher question allocation
   - Which Phase 1 skills to launch (skip UI Discovery for non-UI areas)
   - Which rhacm-docs branch to reference
6. Use Neo4j RHACM to query architectural context for the detected area
7. **Verify feature deployment** (if live cluster available): Before any live operations, confirm the feature is actually implemented in the environment. If not deployed, switch to source-code-only mode with adjusted confidence thresholds.

### Phase 1: Deep Context Gathering

Launch skills in parallel based on detected area:

**For all areas:**
- **JIRA Investigation**: Use JIRA MCP to deep-dive the ticket (description, ALL comments, linked tickets, known bugs, design decisions). Equivalent to `acm-test-case-generator`'s data-gatherer subagent functionality.
- **Code Change Analysis**: Use `acm-qe-code-analyzer` skill (needs to be made repo-agnostic -- see Implementation Notes below). Analyzes PR diff, changed components, conditional logic, code paths.

**For console/UI areas only:**
- **UI Discovery**: Use ACM Source MCP for selectors, routes, translations, wizard structure.

**For all areas (architecture context):**
- **Documentation Research**: Search `stolostron/rhacm-docs` (branch matching ACM version) via `gh` CLI for feature documentation. This is the primary source for learning about the feature's architecture.
- Component source repos (secondary) if rhacm-docs doesn't answer.

### Phase 2: Dimension-by-Dimension Investigation (Subagent Loop)

The core loop as described in Section 4. For each applicable dimension:
1. Orchestrator checks applicability
2. Prepares focused brief with relevant Phase 1 context + questions
3. Spawns dimension subagent
4. Evaluates findings with confidence mechanism
5. Pushback loop if needed (max 3 rounds)
6. Fresh subagent if still unresolved
7. Records final classification

### Phase 3: Internal Documentation Research (Conditional)

**NOT external web search.** Only fires when the orchestrator has a specific unresolved question that Phase 1 and Phase 2 sources couldn't answer.

Sources (in priority order):
1. `stolostron/rhacm-docs` -- official ACM docs, branch per version
2. Component source repos in the stolostron org
3. Neo4j RHACM knowledge graph
4. Local architecture docs (if available)

Never searches the open internet. All research stays within Red Hat/stolostron sources.

### Phase 4: Cross-Dimension Synthesis and Report

1. Consolidate findings across all dimensions
2. Identify root causes (multiple symptoms may share one root cause)
3. Prioritize by severity: CONFIRMED_BUG > POTENTIAL_BUG > GAP
4. Generate the markdown report

### Phase 5: Deliver to User

Present findings in the structured report format (see Section 6). Markdown report only for V1.

---

## 6. Report Format

```markdown
# Bug Hunt Report

## Input
- **Source**: [Polarion ID or file path]
- **Feature**: [Feature name from JIRA]
- **JIRA**: [ACM-XXXXX]
- **ACM Version**: [X.XX]
- **Feature Area**: [detected area]
- **Environment**: [cluster URL or "source-code only"]

## Executive Summary
- Dimensions analyzed: [N]/10 (N applicable, M skipped)
- Questions investigated: [N]
- Subagent interactions: [N total, N pushbacks, N fresh spawns]
- Confirmed bugs found: [N]
- Potential bugs found: [N]
- Coverage gaps identified: [N]
- Probe resources created/cleaned: [N created, N cleaned, N remaining]

## Findings (by severity)

### CONFIRMED BUGS
1. **[Dim N - Title]**
   - Question: [what was asked]
   - Evidence: [MCP tool output, code snippet, JIRA reference]
   - Confidence: [score]% | Evidence: [inventory summary]
   - Corroboration: [how orchestrator verified independently]
   - Impact: [what could go wrong for end users]
   - Suggested action: [file JIRA bug / update test case / verify manually]

### POTENTIAL BUGS
[same structure, plus why it couldn't be confirmed]

### COVERAGE GAPS
[same structure, plus assessment of risk]

## Dimension Analysis Summary

| Dimension | Status | Questions | Rounds | Findings |
|-----------|--------|-----------|--------|----------|
| 1. Specification Fidelity | CLEAN | 3 | 1 | 0 |
| 2. Resource Lifecycle | GAP | 2 | 2 | 1 gap |
| 3. Authorization Chain | SKIPPED | - | - | hub-admin test |
| ... | ... | ... | ... | ... |

## Investigation Trail
[Condensed log of every question asked, tool used, and evidence found -- for traceability]
```

---

## 7. No-Cluster Behavior

When no live cluster is connected:

1. **Graceful degradation**: Run source-code-only analysis. Clearly mark findings as "source-code evidence only, not verified on live cluster."
2. **Adjusted confidence**: Orchestrator accepts lower confidence scores without excessive pushback. Do not drill more than 2 rounds per dimension in no-cluster mode.
3. **Backend bugs**: CAN reach high confidence from source code alone (missing null checks, incorrect field mapping, wrong RBAC definitions).
4. **UI bugs**: CANNOT be confirmed without live validation. Cap at POTENTIAL_BUG.
5. **Dimension 6.4 (probe creation)**: Skip entirely. Dimensions 6.1-6.3 can still run from source code and Neo4j.
6. **Feature deployment check**: If no cluster, skip this check and note it in the report.

---

## 8. Existing Skill Dependencies and Updates Required

### Skills this skill reuses from `ai_systems_v2/skills/`:

| Skill | Role in Bug Hunter | Update Needed? |
|-------|-------------------|----------------|
| `acm-qe-code-analyzer` | Phase 1: PR diff analysis | YES -- must be made repo-agnostic (currently hardcoded to stolostron/console and kubevirt-plugin) |
| `acm-knowledge-base` | Architecture references for question formulation | NO -- read-only reference, already generic |
| `grill-me` | Inspiration only (separate skill, not invoked) | NO |

### `acm-qe-code-analyzer` Update

**Current state**: Hardcoded to `stolostron/console` and `kubevirt-ui/kubevirt-plugin`. Steps reference console-specific patterns (NavigationPath.tsx, PatternFly components, i18n keys).

**Required change**: Accept a `repo` parameter so it works for any stolostron repo. Default to console repos for backward compatibility with `acm-test-case-generator`.

**Backward compatibility**: `acm-test-case-generator` invokes this skill without specifying a repo. After the update, the default behavior must remain identical -- only when explicitly given a different repo does the behavior change.

**Scope of change**:
- Add repo parameter to the skill interface
- Generalize step descriptions to work for any repo (not just console)
- Keep console-specific patterns as the DEFAULT behavior when repo is console/kubevirt-plugin
- For non-console repos: skip console-specific steps (UI strings, translations, PatternFly analysis) and focus on generic code analysis (API changes, CRD changes, controller logic, webhook changes)

### MCP Servers Required

| MCP Server | Required/Optional | Used For |
|------------|-------------------|----------|
| `acm-source` | Required | Source code reading, selectors, translations |
| `jira` | Required | JIRA ticket investigation |
| `polarion` | Optional | Polarion test case fetching (only if input is Polarion ID) |
| `neo4j-rhacm` | Recommended | Architecture dependency graphs |
| `jenkins` | Not used | -- |
| `acm-search` | Optional | Live cluster search verification |
| `acm-kubectl` | Optional | Spoke cluster verification |

---

## 9. File Structure

```
ai_systems_v2/skills/investigation/acm-bug-hunter/
  SKILL.md                    # Main skill file (orchestrator logic)
  references/
    analysis-dimensions.md    # 10-dimension model with question templates,
                              # cross-area applicability, tool mappings
    safety-protocol.md        # Dimension 6 probe resource safety rules
    report-template.md        # Output format template
    confidence-mechanism.md   # Confession/confidence scoring specification
```

---

## 10. Trigger Keywords

The skill should activate when the user says any of:
- `hunt bugs`, `bug hunt`, `find bugs`
- `stress test this test case`, `grill this test case`
- `analyze implementation`, `find issues in implementation`
- `audit this workflow`, `probe for bugs`

---

## 11. SKILL.md Frontmatter

```yaml
---
name: acm-bug-hunter
description: >-
  Autonomously hunts for bugs in ACM feature implementations by using test cases
  as a starting point for systematic 10-dimension investigation. Spawns focused
  subagents per dimension with an orchestrator-investigator adversarial architecture
  to prevent self-bias. Uses confidence-aware feedback loops inspired by the
  "confession" pattern. Supports all ACM areas (Console, GRC, ALC, Observability,
  Cluster Lifecycle, Submariner, Search, Install). Works with or without a live
  cluster (graceful degradation). Input: Polarion test case ID, local .md file,
  or inline test case content.
when_to_use: >-
  When the user wants to find bugs in an ACM feature implementation by analyzing
  a test case. Trigger: hunt bugs, bug hunt, find bugs, stress test this test case,
  grill this test case, analyze implementation, probe for bugs.
compatibility: >-
  Requires: acm-source MCP, jira MCP. Recommended: neo4j-rhacm MCP.
  Optional: polarion MCP, acm-search MCP, acm-kubectl MCP, oc CLI.
  Uses: acm-qe-code-analyzer skill (must be repo-agnostic version),
  acm-knowledge-base skill (read-only references).
metadata:
  author: acm-qe
  version: "1.0.0"
---
```

---

## 12. Reference Implementation

The implementation lives at `skills/investigation/acm-bug-hunter/`:

| File | Path |
|------|------|
| SKILL.md (orchestrator) | `skills/investigation/acm-bug-hunter/SKILL.md` |
| 10-dimension model | `skills/investigation/acm-bug-hunter/references/analysis-dimensions.md` |
| Confidence mechanism | `skills/investigation/acm-bug-hunter/references/confidence-mechanism.md` |
| Safety protocol | `skills/investigation/acm-bug-hunter/references/safety-protocol.md` |
| Report template | `skills/investigation/acm-bug-hunter/references/report-template.md` |

---

## 13. Validated Test Run Results

The skill was tested against two real ACM test cases in Cursor IDE. These results validate the architecture and provide examples of what the skill should produce.

### Test Run 1: RHACM4K-64019 (GPU Count Column, console-general)

- **Dimensions investigated**: 7/10 (skipped Dims 2, 3, 4)
- **Questions asked**: 22
- **Findings**: 2 POTENTIAL_BUGs, 6 GAPs

Key bugs found:
1. **Missing null guard** on `data.metric.instance.split(':')[0]` in ClusterNodes.tsx line 124. Missing `instance` label crashes entire Nodes table. Found independently by Dim 8 and Dim 9.
2. **"Indistinguishable Zero"** -- GPU column shows `0` for loading, error, unavailable data, AND genuine zero GPUs. Found by 6 dimensions converging (Dims 5, 6, 7, 8, 9, 10).

Live cluster verification on Azure 2.17 confirmed the "0" behavior on a cluster with Observability installed but no GPU hardware (metric returns empty results, column shows "0").

### Test Run 2: RHACM4K-61866 (Delete Role Assignment, console-rbac)

- **Dimensions investigated**: 5/10 (skipped Dims 1, 3, 4, 5, 6)
- **Questions asked**: 22
- **Findings**: 4 POTENTIAL_BUGs, 5 GAPs

Key bugs found:
1. **Merge-patch silent data loss** -- `patchResource` uses `application/merge-patch+json` which replaces entire `roleAssignments` array. Concurrent add by another user is silently overwritten with no error. Found by Dim 2.
2. **No abort-on-unmount** during bulk delete. Navigating away mid-operation leaves partial state. Found by Dim 9.
3. **No double-click guard** on Delete button. Race window for duplicate API calls. Found by Dim 9.
4. **No 409 Conflict retry** -- concurrent MCRA modification between GET and PATCH produces generic error with no automatic retry. Found by Dim 2.

Key gaps:
5. **No success toast** on delete (create/edit have toasts, delete doesn't). Test case incorrectly claims "Success notification appears." Found by Dim 10.
6. **Search verification flakiness** -- test case has no wait instruction between delete and Search verification, but indexer lag is 30-60s. Found by Dim 10.

---

## 14. Implementation Checklist

In order of implementation:

1. **Update `acm-qe-code-analyzer`** to accept a repo parameter (backward compatible)
2. **Create `acm-bug-hunter/SKILL.md`** -- see `skills/investigation/acm-bug-hunter/SKILL.md`
3. **Create `acm-bug-hunter/references/analysis-dimensions.md`** -- see `skills/investigation/acm-bug-hunter/references/analysis-dimensions.md`
4. **Create `acm-bug-hunter/references/confidence-mechanism.md`** -- see `skills/investigation/acm-bug-hunter/references/confidence-mechanism.md`
5. **Create `acm-bug-hunter/references/safety-protocol.md`** -- see `skills/investigation/acm-bug-hunter/references/safety-protocol.md`
6. **Create `acm-bug-hunter/references/report-template.md`** -- see `skills/investigation/acm-bug-hunter/references/report-template.md`
7. **Test with RHACM4K-64019** (GPU Count Column) to validate -- compare results against Test Run 1 above
8. **Test with RHACM4K-61866** (Delete RA) to validate -- compare results against Test Run 2 above

---

## 15. Decisions Log (from Grill Me session)

All decisions made during the design phase, for reference:

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Success metric | Find real bugs OR provide high-confidence evidence implementation is solid |
| 2 | Independent verification | Orchestrator evaluates subagent's confidence report, spot-checks one claim for trust calibration. Does NOT re-do the subagent's work. |
| 3 | Subagent count | Full subagent ceremony for every applicable dimension. Robustness over efficiency. |
| 4 | No-cluster behavior | Graceful degradation. Backend bugs can reach high confidence from source code. UI bugs capped at POTENTIAL_BUG. |
| 5 | Iteration limits | Up to 6 questions per dimension (dynamic). Max 3 rounds per subagent. Fresh subagent allowed (also max 3 rounds). |
| 6 | Phase 1 skill mapping | Must use ai_systems_v2 skills. acm-qe-code-analyzer needs repo-agnostic update. Skip UI Discovery for non-console areas. |
| 7 | Output format | Markdown report only (V1). Future: JIRA filing, test case updates. |
| 8 | Confidence mechanism | Hybrid: structured evidence inventory (authoritative) + self-assessed numeric score (secondary). "Confession" pattern from ralph-orchestrator. |
| 9 | External research | NO external web search. Use stolostron/rhacm-docs (branch per ACM version) as primary source. Component repos as secondary. |
| 10 | Naming | `acm-bug-hunter` (not "test-case-auditor"). Goal is finding bugs in implementation, not auditing test cases. |
| 11 | Portability | No Engram dependency. Identical in Cursor IDE and Claude Code. Build AI repo version first, then Cursor IDE. |
| 12 | Grill Me relationship | Grill Me is a separate existing skill. This is a fresh new skill inspired by it. |
