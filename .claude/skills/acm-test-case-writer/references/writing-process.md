# Test Case Writing Process

## Step 1: Read Conventions

Before writing, read these files from the knowledge database:
- `${SKILLS_DIR}/../knowledge/conventions/test-case-format.md` -- section order, naming, complexity levels
- `${SKILLS_DIR}/../knowledge/conventions/area-naming-patterns.md` -- title tag patterns by area
- `${SKILLS_DIR}/../knowledge/conventions/cli-in-steps-rules.md` -- when CLI is allowed in test steps

## Step 2: Read Area Knowledge as Constraints

Read `${SKILLS_DIR}/../knowledge/ui/<area>.md`. Extract:
- **Field order** in description lists or tables
- **Filtering behavior** (which labels/items are filtered, which function does it)
- **Empty state behavior** (shows "-" vs hidden vs "No items")
- **Component patterns** (compact vs full mode, popover vs inline)

These are **CONSTRAINTS** the test case MUST follow. If the investigation context contradicts the knowledge file, **trust the knowledge file** and flag the discrepancy in the Notes section. Then verify via the acm-source MCP's `get_component_source` to determine which is correct.

## Step 3: Scope Gate

Extract the target JIRA story's Acceptance Criteria from the investigation context. Only write steps that validate these specific ACs. If the PR covers multiple stories, filter to only the target story's scope. Mention other stories in the Notes section as "Related functionality delivered in same PR but scoped to [other-story]."

## Step 4: Spot-Check Key UI Elements

Use the acm-source MCP tools directly for quick verification:
1. `set_acm_version` -- set the target version
2. `get_routes` -- verify the entry point route exists, get the full parameterized path
3. `search_translations` -- spot-check 1-2 key labels
4. `get_component_source` -- read the primary component, verify field order, filtering logic, empty state behavior
5. For filtering functions: read the utility file source and extract exact filter conditions

## Step 4.5: Follow Synthesis Design Optimizations and Coverage Gap Triage

If the SYNTHESIZED CONTEXT includes "Test Design Notes" with consolidation instructions (e.g., "use one policy for before/after", "resource count reduced from 4 to 2"), follow them exactly. Do NOT revert to a multi-resource approach. The synthesis phase optimized the plan for efficiency; the writer phase executes it faithfully.

For coverage gap handling, read `${CLAUDE_SKILL_DIR}/references/coverage-gap-handling.md`.

## Step 5: Write the Test Case

Follow conventions EXACTLY:

**Title:** `# RHACM4K-XXXXX - [Tag-Version] Area - Test Name`
**Metadata:** Polarion ID, Status (Draft), Created/Updated dates
**Polarion Fields:** Type, Level, Component, Subcomponent, Test Type, Pos/Neg, Importance, Automation, Tags, Release
**Description:** What is tested, numbered verification list, Entry Point (verified via MCP), Dev JIRA Coverage
**Setup:** Prerequisites, Test Environment, numbered bash commands with `# Expected:` comments
**Test Steps:** `## Test Steps` header, then each step as `### Step N: Title` with numbered actions and bullet expected results, separated by `---`. Apply the quality rules below.
**Teardown:** Bash cleanup commands with `--ignore-not-found`
**Notes:** Implementation details, AC-vs-implementation discrepancies with source code citations

## Quality Rules

### Step Granularity Rule

Each test step should verify ONE distinct behavior or interaction. If a step has expected results that test different aspects (e.g., tooltip text content AND link click navigation), split into separate steps. Ask: "If one expected result passes but another fails, would a tester need to report this as a partial pass?" If yes, split.

Signs a step needs splitting:
- Expected results verify both READ (observe/check text) and ACTION (click/interact/navigate) outcomes
- Expected results mix UI verification with backend CLI verification
- A single step has 4+ expected result bullets covering different behaviors
- The step title uses "and" connecting two distinct verifications

### Backend Validation Placement Rule

First, decide whether a CLI backend validation step is needed at all. **Omit it** when UI steps already provide full coverage — e.g., the UI displays data from a backend source and the test steps already verify the values are correct. A CLI step that only confirms what the UI already shows is redundant. See `cli-in-steps-rules.md` "When CLI Backend Validation Is NOT Needed" for the full rule.

When a CLI backend validation step IS needed (UI action creates/modifies a resource, or backend state is not visible in UI), place it in a DEDICATED step titled "Verify [what] via CLI (Backend Validation)" — do NOT embed CLI commands within a UI-focused step. This ensures:
- Clear context switch (browser → terminal) is visible in the step title
- Pass/fail is cleanly attributed to UI behavior vs backend state
- Automation can map UI steps to browser functions and CLI steps to shell functions

Place backend validation steps AFTER UI steps, so the test flow is: UI verification first, then backend cross-check.

Exception: Setup commands in the Setup section are not affected by this rule.

### Implementation Detail Translation Rule

When the synthesized context includes implementation details (sort algorithm, comparison function, data parsing logic), translate them into OBSERVABLE verifications a tester can check. Ask: "What would a tester SEE if this implementation detail were wrong?"

Examples:
- `compareNumbers(a, b)` → "Sorting is numeric, not alphabetical (e.g., 0, 1, 2, 10 — not 0, 1, 10, 2)"
- `text.split(':')[0]` → "The hostname displayed matches the node name (port suffix stripped)"
- `value ?? 0` → "When no data exists, the field shows '0' (not a dash or empty)"
- `skip: !isInstalled` → "The column/feature is NOT present when [component] is not installed"

## Step 5.5: Functional Outcome Verification (E2E)

If the synthesized context includes an `Outcome Verification` section with status `OUTCOME_VERIFICATION_NEEDED` or `OUTCOME_VERIFICATION_REQUIRED`, generate a final test step that verifies the feature's stated functional outcome — not just the UI state.

### When to Generate

- `OUTCOME_VERIFICATION_REQUIRED`: MUST generate the E2E step. Skip only if the backend behavior is provably untestable from the test environment (document why in Notes).
- `OUTCOME_VERIFICATION_NEEDED`: SHOULD generate the E2E step. Skip if the outcome is already implicitly covered by existing CLI backend validation steps (document the coverage in Notes).
- `NOT_NEEDED`: Do not generate.

### How to Write the E2E Step

The step follows a 4-part structure:

1. **Precondition setup** — Create the resource with the feature enabled (may reuse resources from earlier steps)
2. **Trigger action** — Perform the action the feature is designed to handle (e.g., delete the parent resource, revoke access, disconnect the cluster)
3. **Outcome verification** — Verify the stated user outcome occurred (e.g., child resources preserved, access blocked, failover completed)
4. **Wait-for-ready** — If the backend behavior is asynchronous (controller reconciliation, ArgoCD sync, policy propagation), include explicit wait conditions before checking the outcome

### Step Title Format

```
### Step N: Verify Functional Outcome — [outcome description]
```

The "Verify Functional Outcome" prefix marks this as an outcome verification step for the reviewer to identify. Do not append tags like `[E2E]` to the step title.

### Pitfalls

- **Understand the mechanism.** Read the JIRA description AND any linked documentation to understand what specifically the backend does. The JIRA value statement ("prevents accidental deletion") is marketing language — the test must verify the technical behavior ("deployed K8s resources are orphaned, not cleaned up by the finalizer").
- **Verify what survives vs what is expected to be deleted.** Some resources are expected to be removed (e.g., Kubernetes garbage collection of owned objects). The E2E step must distinguish between expected deletions and unexpected ones.
- **Environment readiness.** If the outcome depends on resources being synced/deployed/healthy before the trigger action, add explicit readiness checks. A test that triggers deletion before resources exist proves nothing.
- **Prerequisite documentation.** Add any extra Setup prerequisites the E2E step needs (target cluster access, specific Git repo branch, addon installation) to the test case Setup section.

## Step 6: Self-Review Checklist

Check before completing:
1. All Polarion metadata fields present and correct?
2. `## Type: Test Case` (not "Functional")?
3. Entry point from MCP-verified route (not assumed)?
4. All UI labels from investigation or MCP (not from memory)?
5. CLI only for backend validation in test steps?
6. Setup has numbered commands with `# Expected:` comments?
7. Teardown cleans up ALL resources created?
8. `## Test Steps` section header present before first step?
9. Steps separated by `---`?
10. No fabricated filter prefixes or numeric thresholds?
11. Any step combining passive observation with active interaction (click/navigate)? Split them.
12. Is CLI backend validation in its own dedicated step, not embedded in a UI step?
13. Are implementation details (sort algorithm, default values, parsing logic) translated into observable verifications?
14. Is any CLI backend validation step redundant because UI steps already verify the same data?

## Gotchas

1. **Filter rules from PR diffs are summaries, not source** -- PR diffs show what changed, not the full logic. Always read the filter function source via `get_component_source` to get exact conditions, thresholds, and edge cases.
2. **Field order assumptions break silently** -- Table column order in area knowledge files reflects the current product. If a PR reorders columns via `cols.push()` or `splice()`, the test case must match the NEW order, not the knowledge file order.
3. **Translation keys are not display text** -- A key like `policy.table.actionGroup` resolves to a different string than the key name implies. Always call `search_translations` with the key to get the actual rendered label.
4. **Test file mock data is not product behavior** -- Automation test files often contain mock data or fixture objects. Never cite test-repo data as evidence of what the product actually does. Product source and MCP verification are the only reliable sources.
5. **`cols.push()` means append, not insert** -- When a PR adds a column via `push()`, it goes at the END of the table. Do not assume it inserts at a specific position unless the code uses `splice()` with an explicit index.
