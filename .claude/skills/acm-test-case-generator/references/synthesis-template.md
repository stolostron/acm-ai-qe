# Synthesis Template

Use this template when merging investigation results from JIRA, code analysis, and UI discovery into a unified context block for the test case writer.

## Template

```
SYNTHESIZED CONTEXT
===================

--- JIRA INVESTIGATION (source: phase2-jira.json) ---
[Read from phase2-jira.json. JSON values are authoritative for: acceptance_criteria, linked_tickets, pr_references]

--- CODE CHANGE ANALYSIS (source: phase3-code.json) ---
[Read from phase3-code.json. JSON values are authoritative for: field_orders, filter_functions (exact conditions), coverage_gaps]

--- UI DISCOVERY (source: phase4-ui.json) ---
[Read from phase4-ui.json. JSON values are authoritative for: routes, translations_verified, selectors, entry_point]

--- TEST PLAN ---
Scenarios: [N]
Steps: [estimated count, typically 5-10 for medium complexity]
Setup: [prerequisites, test users, resources needed]
Per-step validations: [what each step validates -- UI action + expected result]
CLI checkpoints: [where backend validation is needed mid-test]
Teardown: [resources to clean up]
Negative scenarios: [if feature is conditionally rendered/gated, plan at least one step verifying absence when condition is not met]

Conflict resolution (if findings disagree):
- UI elements (labels, routes, selectors): trust UI DISCOVERY (reads source directly via MCP)
- Business requirements (ACs, scope): trust JIRA INVESTIGATION (reads JIRA directly)
- What changed (files, diff): trust CODE CHANGE ANALYSIS (reads the diff)
- Knowledge file authority: if ANY finding contradicts architecture knowledge, flag the contradiction and trust the knowledge file until MCP verification resolves it
- Metric names, translation strings, UI field labels: ALWAYS trust CURRENT source code (verified via `search_translations` or `get_component_source`) over JIRA descriptions. JIRA descriptions may contain stale or proposed names changed during implementation. When a discrepancy is found, use the source code value and add a Note: "JIRA says '[jira-name]' but source code uses '[source-name]' (verified via [tool])"
- JSON file authority: when phase JSON files (`phase2-jira.json`, `phase3-code.json`, `phase4-ui.json`) exist in the run directory, their structured values (filter conditions, field order arrays, route paths, AC lists) take precedence over conversation text for the same data point
```

## Test Design Optimization (MANDATORY)

After building the raw TEST PLAN from investigation outputs, apply these optimization passes before finalizing:

### Pass 1: State Transition Consolidation

When the test plan has scenarios that differ only by the state of a single entity (e.g., "resource before modification" vs "resource after modification", "VM powered off" vs "VM powered on", "user without role" vs "user with role assigned"), consolidate into a single sequential flow on ONE entity:

1. Set up the entity in its initial state.
2. Test the initial-state scenarios.
3. Modify the entity (via CLI or UI action) to transition it to the target state.
4. Test the target-state scenarios on the SAME entity.

This is always preferred over creating multiple independent entities because:
- Fewer resources to set up and tear down.
- Tighter cause-and-effect narrative (the tester sees the before/after on the same object).
- Catches state transition bugs that independent-entity tests miss.

**Examples (these illustrate the general principle -- apply to any resource type or feature area):**
- BAD: "Create Resource-A (with property X) for steps 1-3. Create Resource-B (without property X) for steps 4-5."
- GOOD: "Navigate to Resource-A (property X absent). Steps 1-2 verify empty/absent state. Step 3 adds property X via CLI/UI. Steps 4-5 verify property X now displayed on the same Resource-A."
- BAD: "Use Entity-1 (default config) to test default behavior. Use Entity-2 (modified config) to test modified behavior."
- GOOD: "Use Entity-1. Steps 1-2 test default behavior. Step 3 modifies config. Steps 4-5 test modified behavior on Entity-1."

The decision of whether a resource's initial state belongs in Setup (prerequisites) vs test steps depends on what you are testing:
- If you are testing state transitions (before/after), the state change happens in test steps -- that IS the test.
- If you only need a resource in a particular state as a starting condition (you are not testing the state change itself), put the setup in prerequisites.

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

If two planned steps verify the same behavior in the same context, merge them. Keep both only if the duplicate explicitly tests a different entry point or route.

### Pass 5: Negative Scenario Placement

If the feature has conditional rendering (permission checks, feature gates, addon dependencies), place the negative scenario (feature NOT visible) as the FIRST step, before any state setup. If the negative condition requires specific setup (e.g., logging in as a non-admin user), place it after the positive flow to avoid extra login/logout cycles.

### Optimization Output

After applying all passes, the TEST PLAN should include:

```
Test Design Notes:
- Optimizations applied: [list which passes changed the plan]
- Resource count: [N] (reduced from [M] in raw plan)
- Consolidations: [describe any state-transition consolidations]
```

## Entry Point Selection

Select the test's entry point (where the tester starts navigating) based on UI topology and environment prerequisites, NOT from JIRA epic/story hierarchy.

### Decision Process

1. **Identify the target component** -- the UI element being tested (e.g., PolicyTemplateDetails, ClusterOverview, VirtualMachineDetails).
2. **Read the area knowledge file** (`knowledge/architecture/<area>.md`) for documented navigation paths to that component.
3. **Choose the shortest click path** from the ACM console landing page through the side panel (Home, Search, Infrastructure, Applications, Governance, Credentials, User Management) to the target component.
4. **Consider prerequisites** -- if one path requires creating resources that don't exist in a fresh environment while another path uses resources that are more commonly available, prefer the path with fewer prerequisites. Every prerequisite the test needs (managed clusters, policies, credentials, RBAC permissions, specific resource states) must be explicitly declared in the Setup section.
5. **Document the entry point** in the Description with the full navigation path and route.

### Why Not JIRA Hierarchy

JIRA epic/story hierarchy (e.g., "this is under the discovered policies epic") is fragile and often inaccurate. A story may be filed under one epic but the UI component it touches is reachable from multiple paths. The tester navigating the console doesn't think in JIRA structure -- they think in click paths from the side panel.

### Prerequisite Completeness

The test case must declare ALL environmental dependencies the tester needs:
- Managed clusters (always a prerequisite -- they do not exist by default)
- RBAC permissions or specific user configurations
- Credentials (provider credentials, cloud credentials)
- Specific resource states (policies deployed, addons enabled, operators installed)
- CLI access (oc CLI, specific cluster contexts)
- Console access (URL, authentication method)

Nothing should be assumed. A tester should be able to read the Setup section cold and know exactly what they need before starting.

## Cross-Entity Verification

If the feature operates on a per-entity basis (per-cluster, per-namespace, per-resource, per-policy), the TEST PLAN should include at least one step that validates behavior on a DIFFERENT entity of the same type. This catches:
- Hardcoded entity names or IDs in the implementation
- Filtering logic that only works for the first entity
- Cache or state leakage between entity views

Example: if testing a cluster-scoped action on cluster-A, add a step that performs the same action on cluster-B. If testing a namespace-scoped policy, verify it also appears correctly under a different namespace.

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

## Coverage Gap Triage

After cross-referencing ACs vs implementation, review the code analysis output for a `Coverage Gaps` section. For each gap, classify as:

1. **ADD TO TEST PLAN** — User-visible behavior worth testing. Add a test step or extend an existing step's expected results.
2. **NOTE ONLY** — Real but too minor for a dedicated step, or implicitly covered. Mention in Notes.
3. **SKIP** — Not user-visible from the console, or defensive code not triggerable via UI.

Add to the TEST PLAN:

```
Coverage Gap Triage:
- GAP-1: [description] → ADD TO TEST PLAN (adding as Step N)
- GAP-2: [description] → NOTE ONLY (implicitly covered by Step M)
- GAP-3: [description] → SKIP (internal defensive code, not UI-testable)
- Total: [N] gaps found, [X] added to test plan, [Y] noted, [Z] skipped
```

If no Coverage Gaps section exists in the code analysis output, skip this step.
