# Synthesis Template

Use this template when merging investigation results from JIRA, code analysis, and UI discovery into a unified context block for the test case writer.

## Template

```
SYNTHESIZED CONTEXT
===================

--- JIRA INVESTIGATION ---
[Paste structured JIRA findings: story summary, ACs, comments, edge cases, linked tickets, PR references]

--- CODE CHANGE ANALYSIS ---
[Paste structured code analysis: changed components, new UI elements, filtering logic, field orders, test scenarios]

--- UI DISCOVERY ---
[Paste structured UI discovery: selectors, translations, routes, entry point, wizard steps]

--- TEST PLAN ---
Scenarios: [N]
Steps: [estimated count, typically 5-10 for medium complexity]
Setup: [prerequisites, test users, resources needed]
Per-step validations: [what each step validates -- UI action + expected result]
CLI checkpoints: [where backend validation is needed mid-test]
Teardown: [resources to clean up]

Conflict resolution (if findings disagree):
- UI elements (labels, routes, selectors): trust UI DISCOVERY (reads source directly via MCP)
- Business requirements (ACs, scope): trust JIRA INVESTIGATION (reads JIRA directly)
- What changed (files, diff): trust CODE CHANGE ANALYSIS (reads the diff)
- Knowledge file authority: if ANY finding contradicts architecture knowledge, flag the contradiction and trust the knowledge file until MCP verification resolves it
```

## Scope Gating

1. Extract the target JIRA story's Acceptance Criteria
2. For each planned test step, verify it maps to at least one AC
3. If a step tests functionality from a DIFFERENT story (even if same PR):
   - Do NOT include as a test step
   - Mention in Notes as "Related but scoped to [other-story]"
4. Title reflects target story scope, not PR scope

## AC vs Implementation Cross-Reference

1. For each AC bullet, find the corresponding code behavior from the code analysis
2. If they AGREE: no action needed
3. If they DISAGREE (AC says X, code does Y):
   - Flag as "AC-IMPLEMENTATION DISCREPANCY"
   - The test case MUST validate against the IMPLEMENTATION (what users see)
   - Include a Note explaining the discrepancy with source code citation
