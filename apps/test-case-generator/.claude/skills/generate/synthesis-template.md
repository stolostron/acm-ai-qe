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
Per-step validations (apply ONE-BEHAVIOR-PER-STEP rule):
- [what each step validates -- UI action + expected result]
- If a planned step covers multiple behaviors (e.g., "tooltip content AND link click navigation"), split into separate steps
- If a planned step mixes UI observation and CLI verification, split into "UI step" + "Backend validation step"
- Target: each step should have 2-3 expected result bullets covering the SAME behavior or observation
Backend validation steps: [dedicated steps for CLI-based verification, placed AFTER UI steps -- not embedded within UI steps]
Teardown: [resources to clean up]
Negative scenarios: [if feature is conditionally rendered/gated, plan at least one step verifying absence when condition is not met]
Implementation details to translate: [code-level details like sort algorithms, default values, parsing logic that should become observable verifications in expected results]

Conflict resolution (if agents disagree):
- UI elements (labels, routes, selectors): trust UI Discovery (reads source directly)
- Business requirements (ACs, scope): trust Feature Investigator (reads JIRA)
- What changed (files, diff): trust Code Change Analyzer (reads the diff)
- **Knowledge file authority:** if ANY agent's findings contradict `knowledge/architecture/<area>.md` on field order, filtering behavior, or component structure, flag the contradiction and mark the knowledge file version as the default until MCP verification resolves the conflict
- **Metric names, translation strings, UI field labels:** ALWAYS trust CURRENT source code (verified via `search_translations` or `get_component_source`) over JIRA descriptions. JIRA descriptions may contain stale or proposed names changed during implementation. When a discrepancy is found, use the source code value and add a Note: "JIRA says '[jira-name]' but source code uses '[source-name]' (verified via [tool])"
```

The TEST PLAN section is written by the orchestrator based on the three investigation blocks.

## Cross-Entity Verification

If the feature operates on a per-entity basis (per-cluster, per-namespace, per-resource, per-policy), the TEST PLAN should include at least one step that validates behavior on a DIFFERENT entity of the same type. This catches:
- Hardcoded entity names or IDs in the implementation
- Filtering logic that only works for the first entity
- Cache or state leakage between entity views

Example: if testing a cluster-scoped action on cluster-A, add a step that performs the same action on cluster-B. If testing a namespace-scoped policy, verify it also appears correctly under a different namespace.

## Test File Data Warning

If any investigation agent derived behavioral claims from test files (`.test.tsx`, `.test.ts`), mark those claims in the SYNTHESIZED CONTEXT as: "FROM TEST MOCK DATA — VERIFY AGAINST PRODUCTION CODE." Test mock data (jest.mock returns, fixture objects) does NOT represent what the UI renders. Phase 4 and Phase 4.5 agents must verify these claims via `get_component_source()` before using them in the test case.

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
