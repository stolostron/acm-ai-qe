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

## Test Design Optimization (MANDATORY)

After building the raw TEST PLAN from investigation outputs, apply these optimization passes before finalizing:

### Pass 1: State Transition Consolidation

When the test plan has scenarios that differ only by the state of a single entity (e.g., "resource before modification" vs "resource after modification", "VM powered off" vs "VM powered on", "user without role" vs "user with role assigned", "cluster without addon" vs "cluster with addon enabled"), consolidate into a single sequential flow on ONE entity:

1. Set up the entity in its initial state.
2. Test the initial-state scenarios.
3. Modify the entity (via CLI or UI action) to transition it to the target state.
4. Test the target-state scenarios on the SAME entity.

This is always preferred over creating multiple independent entities because:
- Fewer resources to set up and tear down.
- Tighter cause-and-effect narrative (the tester sees the before/after on the same object).
- Catches state transition bugs that independent-entity tests miss.

**Examples (any area):**
- BAD: "Create Resource A (default state) for steps 1-3. Create Resource B (modified state) for steps 4-6."
- GOOD: "Use Resource A. Steps 1-3 test default state. Step 4 modifies it via CLI/UI. Steps 5-7 test modified state on Resource A."
- BAD (RBAC): "Create User X without role for negative test. Create User Y with role for positive test."
- GOOD (RBAC): "Use User X. Step 1 verifies access is denied (no role). Step 2 assigns role via CLI. Step 3 verifies access is granted."
- BAD (Clusters): "Import Cluster A to test detach. Import Cluster B to test destroy."
- GOOD (Clusters): "Import Cluster A. Steps 1-3 test cluster actions. Step 4 detaches. Step 5 verifies detach state."

### Pass 2: Resource Minimization

For each test resource planned in Setup:
- Is it actually consumed by a test step? If not, remove it.
- Can two planned resources be replaced by one used at different points in the flow? If yes, consolidate.
- Does the test need N instances of something, or would 1-2 suffice to prove the behavior?

Target: the minimum set of resources that still exercises all planned scenarios.

### Pass 3: Step Flow Sequencing

Order test steps to build on each other rather than resetting state:

1. Start with read-only observations (verify initial state).
2. Progress to state-changing actions (create, modify, delete).
3. After each state change, verify the effect before the next change.
4. End with the most destructive or complex action.

This creates a natural narrative arc: observe → act → verify → act → verify → clean up.

### Pass 4: Deduplication

If two planned steps verify the same behavior in the same context, merge them. Signs of duplication:
- Same navigation path + same expected result.
- Step A verifies "field X shows value Y" and Step B also verifies "field X shows value Y" (just from a different navigation entry point that reaches the same page).

Keep both only if the duplicate explicitly tests a different entry point or route (e.g., two distinct navigation paths that reach the same component -- same UI, different route, worth testing both).

### Pass 5: Negative Scenario Placement

If the feature has conditional rendering (permission checks, feature gates, addon dependencies), place the negative scenario (feature NOT visible) as the FIRST step, before any state setup. This way:
- The negative check doesn't require any setup.
- The tester sees "this feature is absent when the condition isn't met" before seeing "this feature appears when the condition IS met."

If the negative condition requires specific setup (e.g., logging in as a non-admin user), place it after the positive flow to avoid extra login/logout cycles.

### Optimization Output

After applying all passes, the TEST PLAN should include:

```
Test Design Notes:
- Optimizations applied: [list which passes changed the plan]
- Resource count: [N] (reduced from [M] in raw plan)
- Consolidations: [describe any state-transition consolidations]
```

This is reviewed by the quality reviewer in Phase 4.5 -- if the plan uses multiple independent entities where a state-transition approach would work, flag it.

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

## Coverage Gap Triage (MANDATORY)

After cross-referencing ACs vs implementation, review the CODE CHANGE ANALYSIS output for a `Coverage Gaps` section. For each gap listed:

### Triage Decision

Classify each gap into one of three categories:

1. **ADD TO TEST PLAN** — The gap describes user-visible behavior that is important enough to test. Add a test step (or extend an existing step's expected results) to cover it.
   - Criteria: Would a user notice if this behavior broke? Would a QE engineer test this manually?
   - Example: "Labels column hidden for Gatekeeper mutations" — yes, a tester would check this.

2. **NOTE ONLY** — The gap is real but too minor for a dedicated test step, or it's covered implicitly by an existing step. Add it to the test case Notes section.
   - Criteria: Valid behavior but testing it explicitly would add complexity without proportional value.
   - Example: "Label parser trims whitespace" — implicitly covered by any label display step.

3. **SKIP** — The gap is not user-visible from the console, or it's defensive code that can't be triggered through normal UI interaction.
   - Criteria: A manual tester would never encounter this scenario through the UI.
   - Example: "Null check on labels array before mapping" — defensive code, not testable via UI.

### Triage Output

Add to the TEST PLAN:

```
Coverage Gap Triage:
- GAP-1: [description] → ADD TO TEST PLAN (adding as Step N)
- GAP-2: [description] → NOTE ONLY (implicitly covered by Step M)
- GAP-3: [description] → SKIP (internal defensive code, not UI-testable)
- Total: [N] gaps found, [X] added to test plan, [Y] noted, [Z] skipped
```

If the CODE CHANGE ANALYSIS output has no Coverage Gaps section, skip this step and add a note: "Coverage gap analysis not available."
