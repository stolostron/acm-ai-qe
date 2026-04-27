# Synthesis Template (Phase 2)

Use this template when merging the three Phase 1 agent outputs into the SYNTHESIZED CONTEXT block. This block is the primary input to Phase 4 (test-case-generator agent).

## Template

```
SYNTHESIZED CONTEXT
===================

--- FEATURE INVESTIGATION ---
[paste full output from feature-investigator agent]

--- CODE CHANGE ANALYSIS ---
[paste full output from code-change-analyzer agent]

--- UI DISCOVERY RESULTS ---
[paste full output from ui-discovery agent]

--- TEST PLAN ---
Scenarios: [N]
Steps: [estimated count, typically 5-10 for medium complexity]
Setup: [prerequisites, test users, resources needed]
Per-step validations: [what each step validates -- UI action + expected result]
CLI checkpoints: [where backend validation is needed mid-test]
Teardown: [resources to clean up]

Conflict resolution (if agents disagree):
- UI elements (labels, routes, selectors): trust UI Discovery (reads source directly)
- Business requirements (ACs, scope): trust Feature Investigator (reads JIRA)
- What changed (files, diff): trust Code Change Analyzer (reads the diff)
```

The TEST PLAN section is written by the orchestrator based on the three investigation blocks.

## Scope Gating (CRITICAL)

When creating the TEST PLAN, apply this scope filter:

1. Extract the target JIRA story's Acceptance Criteria from the FEATURE INVESTIGATION output (if ACs are not present there, retrieve them via JIRA MCP `get_issue`)
2. For each planned test step, verify it maps to at least one AC bullet from the target story
3. If a step tests functionality from a DIFFERENT story (even if delivered in the same PR):
   - Do NOT include it as a test step
   - DO mention it in the Notes section as "Related but not tested here: [description] (covered by [other-story])"
4. The test case title should reflect the target story's scope, not the PR's scope

## AC vs Implementation Cross-Reference (MANDATORY)

After merging investigation outputs, cross-reference the JIRA ACs against the code behavior:

1. Extract each numbered AC bullet from the FEATURE INVESTIGATION output
2. For each AC, find the corresponding code behavior from the CODE CHANGE ANALYSIS output
3. If they AGREE: no action needed
4. If they DISAGREE (AC says X, code does Y):
   - Add to the SYNTHESIZED CONTEXT a section:
     ```
     AC-IMPLEMENTATION DISCREPANCIES:
     - AC: "[exact AC text]"
       Code: "[what the code actually does]"
       Source: [file:line or diff reference]
     ```
   - The test-case-generator agent MUST include a Note about each discrepancy
   - The test case MUST validate against the IMPLEMENTATION (what users actually see), not the AC (what was planned)
