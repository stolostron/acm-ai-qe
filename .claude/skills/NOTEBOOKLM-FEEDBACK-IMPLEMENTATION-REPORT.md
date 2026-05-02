# NotebookLM Feedback Implementation Report

**Source:** Audio overview feedback from NotebookLM on the ACM Test Case Generator skill architecture
**Date:** 2026-05-02
**Scope:** 3 architectural critiques with proposed fixes, applied to all 18 ACM skills
**Purpose:** Provide Claude Code with precise implementation instructions for each finding

---

## Finding 1: Graceful Degradation Creates Silent Failures

### The Problem

The `acm-test-case-writer` skill has a "standalone mode" that performs lightweight self-investigation when invoked without orchestrator context. This creates two issues:

1. **Unpredictable behavior:** A developer can't tell whether a bad test case resulted from bad orchestrator data or from the writer's own rogue investigation
2. **Silent failure masking:** If the orchestrator fails to pass Phase 5 synthesis context, the writer silently degrades instead of failing loudly -- hiding the upstream problem

### Current Code (acm-test-case-writer/SKILL.md, lines 9-18)

```markdown
**Full context mode (via orchestrator):** Receives pre-analyzed investigation data
(JIRA analysis, code analysis, UI discovery) and converts it into a formatted test
case. This produces the highest quality output.

**Standalone mode (direct invocation):** If no investigation context is available,
perform a lightweight investigation first:
1. Ask the user for a JIRA ticket ID
2. Use the acm-jira-client skill to read the story, ACs, and comments
3. Use the acm-ui-source skill to discover routes and translations for the feature
4. Use the acm-code-analyzer skill to analyze the PR if one is referenced
5. Then proceed to write the test case from the gathered data
```

### The Issue in Detail

The writer skill is supposed to be a WRITER -- its job is applying conventions, formatting test steps, and producing Polarion-ready markdown. When it enters "standalone mode," it takes on the roles of the JIRA investigator, UI discoverer, and code analyzer -- roles that belong to OTHER skills called by the orchestrator.

This means:
- The writer now has 3 hidden execution paths (full context, standalone investigation, missing context error)
- A tester can't predict which path ran by looking at the output alone
- If the orchestrator has a bug that drops synthesis context, the writer covers it up by doing its own (lower quality) investigation

### Evidence From Our Runs

In the ACM-30459 analysis, the app's test-case-generator agent (equivalent of the writer) produced 3 factual errors when it had to interpret investigation data itself -- wrong filter logic, wrong field order, wrong empty state. These errors came from the agent doing analytical work it shouldn't have been doing. The writer should WRITE from verified data, not INVESTIGATE.

### Proposed Fix: Standardized Missing Context Protocol

**What to change:** Replace the writer's standalone investigation mode with a clear, standardized error protocol that applies to ALL skills that depend on prior context.

**Implementation for `acm-test-case-writer/SKILL.md`:**

Replace the current "Standalone mode" section with:

```markdown
**Standalone mode (direct invocation):** If no investigation context is available
in the conversation, this skill DOES NOT perform its own investigation. Instead:

1. Check if synthesized context (JIRA findings, code analysis, UI discovery) exists
   in the conversation history
2. If context IS present: proceed to write the test case
3. If context is NOT present: inform the user clearly:

   "I need investigation context before I can write a test case. I have two options:
   
   Option A: Run the full pipeline -- ask me to 'generate a test case for ACM-XXXXX'
   and the acm-test-case-generator skill will run investigation, synthesis, and then
   I'll write the test case with full context.
   
   Option B: Provide context manually -- give me the JIRA ticket details, PR diff
   summary, and the UI elements to test, and I'll write from that."

This ensures:
- The writer NEVER silently degrades into a mini-investigator
- Missing context is always visible to the user
- The user makes the explicit choice of how to proceed
- Debugging is straightforward: if the test case is wrong, the input data was wrong
```

**Implementation for `acm-cluster-remediation/SKILL.md`:**

Replace the current "Standalone operation" self-assessment section with:

```markdown
**Standalone operation:** If invoked directly without prior diagnosis findings
in the conversation:

1. Inform the user: "I need diagnosis findings before proposing remediation.
   Ask me to 'check my hub health' first, or describe the specific issue
   you want to fix and I'll verify it before proposing a remediation plan."
2. If the user describes a specific issue: perform ONLY a targeted verification
   of that specific issue (not a full diagnostic), then propose a fix
3. NEVER run a full diagnostic as a hidden prerequisite -- that's the
   acm-hub-health-check skill's job
```

**Apply the same pattern to `acm-knowledge-learner/SKILL.md`:**

The learner's standalone mode currently "performs its own discovery phase." Change to:

```markdown
**Standalone operation:** Works independently when given cluster access.
If no prior diagnostic findings exist in the conversation:

1. Inform the user: "I can discover and learn from this cluster. I'll perform
   my own discovery. For richer results, run a health check first using
   'check my hub health' and then ask me to learn from the findings."
2. Proceed with discovery (this IS the learner's primary function -- unlike
   the writer and remediation skills, discovery is not a hidden fallback,
   it's the skill's core purpose)
```

Note: The learner is different from the writer and remediation -- discovery IS its job, not a fallback. So standalone mode is appropriate here, just needs clear communication.

---

## Finding 2: Missing Developer Experience Documentation

### The Problem

All documentation is machine-focused (how the AI pipeline works) with zero coverage of:
- How a new developer contributes to the skill pack
- How to test a single skill in isolation
- What the "blast radius" is when modifying each skill
- A step-by-step onboarding task for a new team member
- How another team reuses the shared skills for a different domain

### Evidence

Current `docs/` directory contents (30 files):

```
docs/skill-architecture.md              -- skill inventory (machine/architect focus)
docs/mcp-setup-guide.md                 -- MCP configuration (setup focus)
docs/test-case-generator/               -- 8 files (pipeline phases, agents, MCPs, quality gates)
docs/hub-health/                        -- 10 files (diagnostic pipeline, knowledge, reporting)
docs/z-stream-analysis/                 -- 10 files (stages, services, classification)
```

Every file describes what the SYSTEM does. None describes what a DEVELOPER does.

### Proposed Fix: Add Developer Experience Documentation

**Create `docs/developer-guide.md`:**

```markdown
# Developer Guide: Contributing to the ACM Skill Pack

## Understanding the Architecture

The skill pack has 3 layers:

1. **Shared skills** (7): Raw tools with zero workflow logic. Safe to modify independently.
2. **App-specific skills** (11): Workflow logic for specific use cases. Modify with awareness of the orchestrator.
3. **Orchestrators** (3): Pipeline brains. Modify with full system understanding.

## Blast Radius Map

When you modify a skill, here's what could be affected:

| Skill You Modify | What Could Break | Safe to Change Independently? |
|---|---|---|
| acm-jira-client | Nothing else (vanilla tool) | YES |
| acm-ui-source | Nothing else (vanilla tool) | YES |
| acm-polarion-client | Nothing else (vanilla tool) | YES |
| acm-neo4j-explorer | Nothing else (vanilla tool) | YES |
| acm-cluster-health | Nothing else (methodology only) | YES |
| acm-knowledge-base | Area knowledge consumers (writer, reviewer) may be affected | YES with caution |
| acm-jenkins-client | Nothing else (vanilla tool) | YES |
| acm-code-analyzer | TC-gen Phase 3 output changes | YES -- orchestrator consumes output |
| acm-test-case-writer | TC-gen Phase 7 output changes | YES -- output format only |
| acm-test-case-reviewer | TC-gen Phase 8 verdict changes | YES -- verdict logic only |
| acm-failure-classifier | Z-stream Stage 2 classification changes | CAUTION -- core logic |
| acm-cluster-investigator | Z-stream investigation results change | CAUTION -- evidence chains |
| acm-data-enricher | Z-stream enrichment data changes | YES -- data format only |
| acm-hub-health-check | Hub health report changes | CAUTION -- diagnostic logic |
| acm-cluster-remediation | Remediation behavior changes | CAUTION -- cluster mutations |
| acm-knowledge-learner | Knowledge file writes change | YES -- output format only |
| acm-test-case-generator | ENTIRE TC-gen pipeline affected | HIGH RISK -- test thoroughly |
| acm-z-stream-analyzer | ENTIRE z-stream pipeline affected | HIGH RISK -- test thoroughly |

## Hello World: Your First Contribution

### Task: Add a new JQL pattern to acm-jira-client

You've been asked to add a JQL pattern for finding tickets by sprint.

**Step 1:** Open the file:
```
.claude/skills/acm-jira-client/references/jql-patterns.md
```

**Step 2:** Add your pattern under "## Advanced Patterns":
```markdown
### Find tickets in current sprint
\```
project = ACM AND sprint in openSprints() AND component = "Governance"
\```
```

**Step 3:** Test it in isolation. Open Claude Code at the repo root:
```bash
claude
> Search JIRA for governance tickets in the current sprint
```

Claude loads the acm-jira-client skill and uses your new pattern. The orchestrator pipeline is never involved.

**Step 4:** That's it. Your change is isolated to one reference file in one skill. No risk to the orchestrator, no risk to the pipeline, no risk to other skills.

### Task: Update an area knowledge file

You've discovered that the governance area's field order documentation is wrong.

**Step 1:** Open:
```
.claude/skills/acm-knowledge-base/references/architecture/governance.md
```

**Step 2:** Fix the field order:
```markdown
### Description List Field Order (PolicyTemplateDetails)
1. Name
2. Engine (with SVG icon)
3. Cluster
4. Kind
5. API version
6. Labels (after API version, before type-specific fields)
```

**Step 3:** Verify via MCP (optional but recommended):
```bash
claude
> Use the acm-ui-source skill. Set ACM version to 2.17, then read the source of
  PolicyTemplateDetails.tsx and tell me the description list field order.
```

**Step 4:** The knowledge file is used as a CONSTRAINT by the writer and reviewer. Your fix ensures future test cases use the correct field order. No orchestrator changes needed.

### Task: Add a new assertion to the TC-gen eval framework

**Step 1:** Open:
```
.claude/skills/acm-test-case-generator/evals/evals.json
```

**Step 2:** Add an assertion to an existing eval:
```json
{
  "id": 1,
  "prompt": "Generate a test case for ACM-30459",
  "assertions": [
    ... existing assertions ...,
    "Setup section includes ACM version verification as the first command"
  ]
}
```

**Step 3:** Run the eval by generating the test case and checking the assertion manually.

## How to Reuse Shared Skills for a New Domain

The 7 shared skills (jira-client, ui-source, polarion-client, neo4j-explorer, cluster-health, jenkins-client, knowledge-base) are designed for reuse by ANY ACM-related application.

To build a new application (e.g., "ACM Release Readiness Checker"):

1. Create a new orchestrator skill: `acm-release-readiness/SKILL.md`
2. In its SKILL.md, reference the shared skills by name
3. Write your pipeline phases -- the shared skills provide the capabilities
4. Add app-specific skills if needed (e.g., `acm-release-validator/`)
5. Add your knowledge to `acm-knowledge-base/references/` or your own skill's `references/`

You don't modify any shared skill. You just USE them with different instructions in your orchestrator.

## Testing a Skill in Isolation

Every skill can be tested independently without the full pipeline:

```bash
# Test JIRA client
claude
> Use the acm-jira-client skill to read ACM-30459. Show me the ACs and comments.

# Test UI source
claude
> Use the acm-ui-source skill. Set version 2.17, search translations for "Labels".

# Test code analyzer
claude
> Use the acm-code-analyzer skill to analyze PR #5790 in stolostron/console.

# Test reviewer
claude
> Use the acm-test-case-reviewer skill to review the test case at
  runs/ACM-30459/.../test-case.md
```

Each runs in isolation. No orchestrator, no pipeline, no 12.5-minute wait.
```

---

## Finding 3: Orchestrator Could Benefit From a Synthesis Sub-Skill

### The Problem

The orchestrator drives 10 phases in one context window. While it delegates investigation to other skills (Phases 2-4) and writing to the writer (Phase 7), Phase 5 (Synthesis) is done inline by the orchestrator itself. This means:

- Synthesis logic can't be tested independently
- The orchestrator must hold all investigation outputs + synthesis template + scope gating rules simultaneously
- Changing synthesis rules requires modifying the orchestrator

### Evidence

The orchestrator's Phase 5 section currently says:

```markdown
### Phase 5: Synthesize

Read `references/synthesis-template.md` for the synthesis template.

Merge all investigation results into a SYNTHESIZED CONTEXT block:
1. Combine JIRA findings, code analysis, and UI discovery
2. Resolve conflicts: trust UI discovery for UI elements, JIRA for requirements...
3. Scope gate: only plan steps for the target story's ACs...
4. AC vs Implementation cross-reference...
5. Plan the test case: step count, setup, per-step validations...
```

This is ~20 lines of instructions that the orchestrator processes inline. If synthesis logic gets more complex (which it will as we add more investigation sources), this section balloons.

### Proposed Fix: Extract Synthesis Into a Dedicated Skill

**Create `acm-context-synthesizer/SKILL.md`:**

```markdown
---
name: acm-context-synthesizer
description: Merge investigation outputs from JIRA, code analysis, and UI discovery
  into a unified synthesis context. Resolves conflicts, applies scope gating, and
  cross-references ACs vs implementation. Use after investigation phases produce
  raw findings that need to be merged before writing.
compatibility: "Uses acm-knowledge-base for area constraints. No MCP required."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Context Synthesizer

Merges raw investigation outputs into a unified, conflict-resolved synthesis context.
This is a dedicated step between investigation (Phases 2-4) and writing (Phase 7).

**Standalone operation:** Works independently when given investigation outputs.
If invoked without investigation data, informs the user what's needed:
"I need investigation outputs to synthesize. Provide JIRA findings, code analysis,
and UI discovery results, or run the full pipeline via acm-test-case-generator."

## Input

Three investigation output blocks (text or structured data):
1. JIRA Investigation: story summary, ACs, comments, linked tickets
2. Code Change Analysis: changed components, filtering logic, field orders
3. UI Discovery: routes, translations, selectors, entry point

## Process

### Step 1: Conflict Resolution

When investigation outputs disagree:
- UI elements (labels, routes, selectors): trust UI Discovery (reads source directly via MCP)
- Business requirements (ACs, scope): trust JIRA Investigation (reads JIRA directly)
- What changed (files, diff): trust Code Change Analysis (reads the diff)
- Architecture constraints: trust acm-knowledge-base area files over any investigation output

### Step 2: Scope Gating

1. Extract the target JIRA story's Acceptance Criteria
2. For each potential test step, verify it maps to at least one AC
3. If a step tests functionality from a DIFFERENT story (same PR): exclude from steps,
   mention in Notes as "Related but scoped to [other-story]"
4. Title reflects target story scope, not PR scope

### Step 3: AC vs Implementation Cross-Reference

1. For each AC bullet, find corresponding code behavior from code analysis
2. If they AGREE: no action
3. If they DISAGREE: flag as "AC-IMPLEMENTATION DISCREPANCY" with source citation
4. Test case MUST validate against IMPLEMENTATION (what users see), not AC (what was planned)

### Step 4: Test Plan

Produce a structured test plan:
- Scenario count (typically 5-10 for medium complexity)
- Step estimates with per-step validations
- Setup requirements (prerequisites, resources)
- CLI checkpoints (where backend validation is needed)
- Teardown plan

### Step 5: Mark Test File Data

If any investigation output derived claims from test files (.test.tsx, .test.ts),
mark those claims as: "FROM TEST MOCK DATA -- verify against production code."

## Output

A SYNTHESIZED CONTEXT block following the template in references/synthesis-template.md.
```

**Then update `acm-test-case-generator/SKILL.md` Phase 5:**

```markdown
### Phase 5: Synthesize

Using the **acm-context-synthesizer** skill, merge all investigation results.
Provide the JIRA findings from Phase 2, code analysis from Phase 3, and UI
discovery from Phase 4. The synthesizer resolves conflicts, applies scope gating,
and produces a unified SYNTHESIZED CONTEXT block.
```

This makes synthesis testable independently: "Given these JIRA findings and this code analysis, does synthesis produce the correct scope-gated plan?"

---

## Implementation Summary

| Finding | Files to Create | Files to Modify | Priority |
|---------|----------------|-----------------|----------|
| 1. Standardized missing context protocol | None | `acm-test-case-writer/SKILL.md`, `acm-cluster-remediation/SKILL.md` | High |
| 2. Developer experience documentation | `docs/developer-guide.md` | None | High |
| 3. Context synthesizer skill | `acm-context-synthesizer/SKILL.md`, `acm-context-synthesizer/references/synthesis-template.md` | `acm-test-case-generator/SKILL.md` (Phase 5) | Medium |

### Implementation Order

1. **First:** Fix graceful degradation (Finding 1) -- replace silent degradation with clear error protocol in writer and remediation skills
2. **Second:** Add developer guide (Finding 2) -- create `docs/developer-guide.md` with blast radius map, Hello World tasks, isolation testing guide, and reuse instructions
3. **Third:** Extract synthesizer (Finding 3) -- create `acm-context-synthesizer` skill, move synthesis template into it, update orchestrator Phase 5 to delegate

### What NOT to Change

- **Shared skills remain vanilla** -- no changes to jira-client, ui-source, polarion-client, neo4j-explorer, cluster-health, jenkins-client, knowledge-base
- **Knowledge learner keeps standalone mode** -- discovery IS its primary function, not a fallback
- **Orchestrator still drives the pipeline** -- the synthesizer is a new delegation point, not a replacement for the orchestrator
- **Quality gate enforcement stays programmatic** -- review_enforcement.py is working correctly
