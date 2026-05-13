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

# ACM Bug Hunter

Use a test case as a starting point to systematically investigate whether the implemented feature has bugs that the test case scenarios might miss. The skill does NOT audit the test case quality -- it uses the test case to identify critical implementation paths and then hunts for bugs across 10 dimensions of implementation correctness.

## ASK QUESTIONS FIRST

| Category | Questions to Ask |
|----------|------------------|
| **Test Case** | "What test case? (Polarion ID, file path, or paste it)" |
| **ACM Version** | "Which ACM version? (e.g., 2.16, 2.17)" |
| **Environment** | "Is a live cluster available? (hub console URL, or 'no cluster')" |
| **Focus** | "Any specific concern to investigate? (or 'full audit')" |

---

## MANDATORY: Phase Gate Enforcement

On skill start, IMMEDIATELY create tasks for ALL phases:

```
TaskCreate: Phase 0: Parse input, detect area, adapt
TaskCreate: Phase 1: Deep context gathering (parallel)
TaskCreate: Phase 2: Dimension investigation (subagent loop)
TaskCreate: Phase 3: Internal documentation research
TaskCreate: Phase 4: Cross-dimension synthesis and report
TaskCreate: Phase 5: Deliver to user
```

Gate rules:
1. A phase CANNOT be marked `completed` without executing it.
2. Phase 2 is the core investigation -- do NOT rush through it.
3. Phase 3 fires ONLY when the orchestrator has a specific unresolved question.
4. Phase 4 MUST complete before Phase 5.

---

## Phase 0: Parse Input, Detect Area, and Adapt

1. **Read the test case**:
   - Polarion ID -> use Polarion MCP (`get_polarion_work_item`, `get_polarion_test_steps`, project `RHACM4K`)
   - Local file -> read from disk
   - Inline -> parse from the conversation

2. **Extract metadata**:
   - JIRA ticket (from "Dev JIRA Coverage" or description)
   - PR number (from JIRA comments or test case metadata)
   - ACM version (from test case tags or user input)
   - Test steps and expected results
   - Setup requirements

3. **Detect feature area** from JIRA components, test case tags, file path, or content keywords. Map to one of:
   `console-rbac` | `console-general` | `fleet-virt` | `clusters` | `grc` | `alc` | `search` | `observability` | `submariner` | `install` | `hosted-clusters` | `other`

4. **Determine dimension priority** based on area:
   - `console-rbac` -> Dim 3 (auth) and Dim 10 (observable output) get up to 6 questions
   - `grc` -> Dim 4 (multicluster) and Dim 7 (state transitions) get up to 6 questions
   - `alc` -> Dim 2 (resource lifecycle) and Dim 4 (multicluster) get up to 6 questions
   - `observability` -> Dim 5 (data pipeline) and Dim 6 (integration) get up to 6 questions
   - Other areas: orchestrator decides dynamically based on test case content

5. **Check environment** (if cluster URL provided):
   - Verify the feature is deployed: `oc get csv -n open-cluster-management`, `oc get crd | grep <feature-crd>`
   - If feature not deployed -> switch to source-code-only mode, adjust confidence thresholds
   - If no cluster provided -> source-code-only mode from the start

6. **Query architectural context**: Use Neo4j RHACM to get the dependency graph for the detected area:
   ```
   read_neo4j_cypher("MATCH (c)-[:BELONGS_TO]->(s) WHERE s.label CONTAINS '<area>' RETURN c.label, c.type")
   ```

---

## Phase 1: Deep Context Gathering

Launch subagents in parallel based on detected area.

### For ALL areas:

**Subagent A: Feature Investigator**

Spawn via the Agent tool (`subagent_type: "general-purpose"`). Brief the subagent with:
- The JIRA ticket key extracted in Phase 0
- Instructions to use JIRA MCP for deep investigation:
  - `get_issue(issue_key)` -- full story, comments, acceptance criteria
  - `search_issues(jql)` -- find linked tickets, QE tracking, known bugs
  - Read ALL comments -- they contain implementation decisions and edge cases
  - Find PRs referenced in the ticket
- Return format: structured summary of ACs, decisions, edge cases, linked PRs, known bugs

**Subagent B: Code Change Analyzer**

Spawn via the Agent tool (`subagent_type: "general-purpose"`). Brief the subagent with:
- PR number and **repo name** (from JIRA or test case metadata)
- Instructions from the `acm-qe-code-analyzer` skill process (Steps 1-10)
- For console repos: full UI + backend analysis
- For non-console repos: controller logic, CRD changes, webhook changes, API changes
- Return format: the CODE CHANGE ANALYSIS format from acm-qe-code-analyzer

### For CONSOLE/UI areas only:

**Subagent C: UI Discovery**

Spawn via the Agent tool (`subagent_type: "general-purpose"`). Brief the subagent with:
- ACM version, CNV version (if Fleet Virt), feature name, area
- Instructions to use ACM Source MCP:
  - `set_acm_version(version)` -- MUST call first
  - `search_code(query, repo, scope)` -- find relevant components
  - `get_component_source(path, repo)` -- read source files
  - `search_translations(query)` -- find UI label strings
  - `get_routes()` -- ACM navigation routes
- Return format: selectors, routes, translations, wizard structure

### For ALL areas (documentation research):

**In-phase documentation lookup** (orchestrator, inline):
- Search `stolostron/rhacm-docs` (branch matching ACM version) for feature documentation:
  ```bash
  gh search code "<feature keyword>" --repo stolostron/rhacm-docs --ref <version>_stage
  ```
- Read relevant doc files for architectural understanding.

---

## Phase 2: Dimension-by-Dimension Investigation (Subagent Loop)

Read [analysis-dimensions.md](references/analysis-dimensions.md) for the full 10-dimension model.

### Orchestrator-Investigator Architecture

Two distinct roles prevent self-bias:

- **Orchestrator** (this agent) = the lead/skeptic. Holds Phase 1 context. Identifies what to investigate, evaluates subagent findings, catches false negatives and false positives.
- **Dimension subagent** = the focused engineer. Gets a targeted brief for ONE dimension. Fresh context window. Investigates using MCP tools. Returns findings + confidence report.

Read [confidence-mechanism.md](references/confidence-mechanism.md) for the full confidence scoring specification.

### Per-Dimension Flow

For each applicable dimension (1 through 10):

**Step 0 -- Applicability Check** (orchestrator, inline):
Check the dimension applicability matrix in [analysis-dimensions.md](references/analysis-dimensions.md).
If not applicable, skip with a one-line note and move on.

**Step 1 -- Brief Preparation** (orchestrator, inline):
Prepare a focused brief for the subagent containing:
- The test case content (steps, expected results, setup)
- Relevant Phase 1 context (filtered to this dimension only)
- 1-6 critical questions (dynamically allocated based on dimension priority from Phase 0)
- Feature area for area-appropriate investigation lens
- Available MCP tools with usage instructions
- INSTRUCTION: "Return both Investigation Findings AND Confidence Report as specified in your brief."

**Step 2 -- Spawn Subagent**:
Launch via the Agent tool (`subagent_type: "general-purpose"`) with the brief. The subagent:
- Investigates independently using MCP tools
- Returns structured findings with evidence
- Returns a Confidence Report (evidence inventory + self-assessed score + uncertainties + single easiest item to verify)

**Step 3 -- Evaluate Findings** (orchestrator, inline):
A) Check the Evidence Inventory from the Confidence Report
B) Spot-check the "Single Easiest Item to Verify" as trust calibration
C) Apply the classification decision tree:

```
CLEAN + thorough evidence     -> Accept. Move on.
CLEAN + shallow evidence      -> PUSHBACK: specify missing checks.
POTENTIAL_BUG + strong evidence -> Spot-check via different path.
                                  Corroborated -> CONFIRMED_BUG.
                                  Not reproducible -> keep POTENTIAL_BUG.
POTENTIAL_BUG + weak evidence -> PUSHBACK: request harder proof.
CONFIRMED_BUG                 -> ALWAYS corroborate via different
                                  evidence path. If contradicted ->
                                  downgrade, pushback.
```

**Step 4 -- Pushback Loop** (if needed):
Send a follow-up message to the SAME subagent (via SendMessage) with specific feedback. Max 3 back-and-forth rounds.
Each round should increase confidence as more evidence is gathered.

**Step 5 -- Fresh Subagent** (if still unresolved after 3 rounds):
Spawn a FRESH Agent (`subagent_type: "general-purpose"`) with:
- The original brief
- The orchestrator's specific objections and counter-evidence
- NO access to prior subagent's reasoning (unbiased second opinion)
Fresh subagent also gets max 3 rounds.
Compare both subagents' evidence. Stronger evidence wins.
If tied -> POTENTIAL_BUG with both perspectives noted.

**Step 6 -- Record** final classification + evidence trail.

### No-Cluster Adjustments

When no live cluster is available:
- Do not drill more than 2 rounds per dimension
- Backend logic bugs CAN reach high confidence from source code
- UI bugs are capped at POTENTIAL_BUG (cannot confirm without live validation)
- Dimension 6.4 (probe creation) is skipped entirely
- Dimensions 6.1-6.3 can still run from source code and Neo4j

---

## Phase 3: Internal Documentation Research (Conditional)

Fires ONLY when the orchestrator has a specific unresolved question from Phase 2 that internal sources couldn't answer.

Sources (in priority order):
1. `stolostron/rhacm-docs` -- official ACM docs, branch per version (`2.15_stage`, `2.16_stage`, `2.17_stage`)
2. Component source repos in the stolostron org
3. Neo4j RHACM knowledge graph
4. Local architecture docs

**No external web search.** All research stays within Red Hat/stolostron sources.

---

## Phase 4: Cross-Dimension Synthesis and Report

1. Consolidate findings across all dimensions
2. Check: do findings at different dimensions point to the same root issue?
3. Prioritize by severity: CONFIRMED_BUG > POTENTIAL_BUG > GAP
4. Generate the markdown report per [report-template.md](references/report-template.md)

---

## Phase 5: Deliver to User

Present the markdown report. Highlight:
- Total CONFIRMED_BUGs and POTENTIAL_BUGs found
- For each finding: the question asked, evidence found, and suggested action
- Dimensions that were clean (high-confidence evidence the implementation is solid)
- Any dimensions skipped and why

---

## MCP and Tool Reference

### JIRA MCP (`jira`)
| Tool | Purpose |
|------|---------|
| `get_issue(issue_key)` | Full story, comments, ACs |
| `search_issues(jql)` | Linked tickets, known bugs |

### Polarion MCP (`user-polarion`)
| Tool | Purpose |
|------|---------|
| `get_polarion_work_item(project_id, work_item_id)` | Test case details |
| `get_polarion_test_steps(project_id, work_item_id)` | Ordered test steps |

### ACM Source MCP (`user-acm-source`)
| Tool | Purpose |
|------|---------|
| `set_acm_version(version)` | MUST call first |
| `search_code(query, repo, scope)` | Find files by content |
| `get_component_source(path, repo)` | Read source file |
| `search_translations(query)` | Find UI label strings |
| `get_routes()` | ACM navigation routes |

### Neo4j RHACM MCP (`neo4j-rhacm`)
| Tool | Purpose |
|------|---------|
| `read_neo4j_cypher(query)` | Architecture dependency queries |

### ACM Search MCP (`acm-search`) -- if available
| Tool | Purpose |
|------|---------|
| `find_resources(...)` | Search K8s resources across clusters |

### ACM Kubectl MCP (`acm-kubectl`) -- if available
| Tool | Purpose |
|------|---------|
| `clusters()` | List managed clusters |
| `kubectl(command, cluster)` | Run kubectl on hub or spoke |

### CLI Tools
| Tool | Purpose |
|------|---------|
| `gh pr view/diff` | PR metadata and code diff |
| `gh search code` | Search stolostron/rhacm-docs |
| `oc get/describe` | Live cluster state (read-only) |
| `oc auth can-i` | RBAC verification |
| `oc apply --dry-run=server` | Dry-run probe validation (Dim 6 only) |

---

## Subagent Usage

### Phase 1 Subagents (Parallel)
Spawn via the Agent tool (`subagent_type: "general-purpose"`):
- **Feature Investigator** -- deep JIRA investigation with JIRA MCP access
- **Code Change Analyzer** -- PR diff analysis following acm-qe-code-analyzer process (repo-agnostic)
- **UI Discovery** -- selectors, routes, translations via ACM Source MCP (console areas only)

### Phase 2 Subagents (Sequential, per dimension)
Spawn via the Agent tool (`subagent_type: "general-purpose"`):
- One per applicable dimension
- Full MCP access
- Can receive follow-up messages up to 3 times for pushback (via SendMessage)
- Fresh subagent spawned if still unresolved after 3 rounds (also max 3 rounds)

---

## Iteration Limits

| Limit | Value |
|-------|-------|
| Questions per dimension | 1-6 (dynamic, based on feature complexity and dimension priority) |
| Back-and-forth rounds per subagent | Max 3 |
| Fresh subagent allowed | Yes, 1 per dimension |
| Fresh subagent rounds | Max 3 |

---

## Skill File Structure

```
.claude/skills/acm-bug-hunter/
  SKILL.md                              # This file (orchestrator)
  references/
    analysis-dimensions.md              # 10-dimension model
    confidence-mechanism.md             # Confidence scoring spec
    safety-protocol.md                  # Dimension 6 probe safety rules
    report-template.md                  # Output format template
```
