---
name: acm-test-case-writer
description: Write Polarion-ready ACM Console UI test case markdown from synthesized investigation context, or independently from a JIRA ticket. Use when you need to produce a test case document for an ACM Console feature.
compatibility: "Uses acm-ui-source skill (requires acm-ui MCP) for spot-check verification. Uses acm-knowledge-base skill (no MCP needed)."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Test Case Writer

Produces Polarion-ready test case markdown files. Works in two modes depending on available context:

**Full context mode (via orchestrator):** Receives pre-analyzed investigation data (JIRA analysis, code analysis, UI discovery) and converts it into a formatted test case. This produces the highest quality output.

**Standalone mode (direct invocation):** If no investigation context is available, perform a lightweight investigation first:
1. Ask the user for a JIRA ticket ID
2. Use the acm-jira-client skill to read the story, ACs, and comments
3. Use the acm-ui-source skill to discover routes and translations for the feature
4. Use the acm-code-analyzer skill to analyze the PR if one is referenced in the JIRA ticket
5. Then proceed to write the test case from the gathered data

Standalone mode produces a functional test case but may be less thorough than the full pipeline (fewer edge cases, less cross-referencing, no live validation).

## Prerequisites

- acm-knowledge-base skill available for conventions and area knowledge
- acm-ui-source skill available for spot-check verification
- For standalone mode: acm-jira-client skill available for JIRA investigation

## Process

### Step 1: Read Conventions

Before writing, read these files from the acm-knowledge-base skill:
- `references/conventions/test-case-format.md` -- section order, naming, complexity levels
- `references/conventions/area-naming-patterns.md` -- title tag patterns by area
- `references/conventions/cli-in-steps-rules.md` -- when CLI is allowed in test steps

### Step 2: Read Area Knowledge as Constraints

Read `references/architecture/<area>.md` from the acm-knowledge-base skill. Extract:
- **Field order** in description lists or tables
- **Filtering behavior** (which labels/items are filtered, which function does it)
- **Empty state behavior** (shows "-" vs hidden vs "No items")
- **Component patterns** (compact vs full mode, popover vs inline)

These are **CONSTRAINTS** the test case MUST follow. If the investigation context contradicts the knowledge file, **trust the knowledge file** and flag the discrepancy in the Notes section. Then verify via acm-ui-source skill's `get_component_source` to determine which is correct.

### Step 3: Scope Gate

Extract the target JIRA story's Acceptance Criteria from the investigation context. Only write steps that validate these specific ACs. If the PR covers multiple stories, filter to only the target story's scope. Mention other stories in the Notes section as "Related functionality delivered in same PR but scoped to [other-story]."

### Step 4: Spot-Check Key UI Elements

Use the acm-ui-source skill for quick verification:
1. `set_acm_version` -- set the target version
2. `get_routes` -- verify the entry point route exists, get the full parameterized path
3. `search_translations` -- spot-check 1-2 key labels
4. `get_component_source` -- read the primary component, verify field order, filtering logic, empty state behavior
5. For filtering functions: read the utility file source and extract exact filter conditions

### Step 4.5: Follow Synthesis Design Optimizations

If the SYNTHESIZED CONTEXT includes "Test Design Notes" with consolidation instructions (e.g., "use one policy for before/after", "resource count reduced from 4 to 2"), follow them exactly. Do NOT revert to a multi-resource approach. The synthesis phase optimized the plan for efficiency; the writer phase executes it faithfully.

### Step 5: Write the Test Case

Follow conventions EXACTLY:

**Title:** `# RHACM4K-XXXXX - [Tag-Version] Area - Test Name`
**Metadata:** Polarion ID, Status (Draft), Created/Updated dates
**Polarion Fields:** Type, Level, Component, Subcomponent, Test Type, Pos/Neg, Importance, Automation, Tags, Release
**Description:** What is tested, numbered verification list, Entry Point (verified via MCP), Dev JIRA Coverage
**Setup:** Prerequisites, Test Environment, numbered bash commands with `# Expected:` comments
**Test Steps:** `## Test Steps` header, then each step as `### Step N: Title` with numbered actions and bullet expected results, separated by `---`. Apply the step granularity, backend validation placement, and implementation detail translation rules below.
**Teardown:** Bash cleanup commands with `--ignore-not-found`
**Notes:** Implementation details, AC-vs-implementation discrepancies with source code citations

#### Step Granularity Rule

Each test step should verify ONE distinct behavior or interaction. If a step has expected results that test different aspects (e.g., tooltip text content AND link click navigation), split into separate steps. Ask: "If one expected result passes but another fails, would a tester need to report this as a partial pass?" If yes, split.

Signs a step needs splitting:
- Expected results verify both READ (observe/check text) and ACTION (click/interact/navigate) outcomes
- Expected results mix UI verification with backend CLI verification
- A single step has 4+ expected result bullets covering different behaviors
- The step title uses "and" connecting two distinct verifications

#### Backend Validation Placement Rule

When a test case includes CLI-based backend verification (checking resource state, querying APIs, verifying metric data), place it in a DEDICATED step titled "Verify [what] via CLI (Backend Validation)" — do NOT embed CLI commands within a UI-focused step. This ensures:
- Clear context switch (browser → terminal) is visible in the step title
- Pass/fail is cleanly attributed to UI behavior vs backend state
- Automation can map UI steps to browser functions and CLI steps to shell functions

Place backend validation steps AFTER UI steps, so the test flow is: UI verification first, then backend cross-check.

Exception: Setup commands in the Setup section are not affected by this rule.

#### Implementation Detail Translation Rule

When the synthesized context includes implementation details (sort algorithm, comparison function, data parsing logic), translate them into OBSERVABLE verifications a tester can check. Ask: "What would a tester SEE if this implementation detail were wrong?"

Examples:
- `compareNumbers(a, b)` → "Sorting is numeric, not alphabetical (e.g., 0, 1, 2, 10 — not 0, 1, 10, 2)"
- `text.split(':')[0]` → "The hostname displayed matches the node name (port suffix stripped)"
- `value ?? 0` → "When no data exists, the field shows '0' (not a dash or empty)"
- `skip: !isInstalled` → "The column/feature is NOT present when [component] is not installed"

### Step 6: Self-Review Before Finalizing

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

## Critical Rules

- NEVER assume UI labels -- use labels from investigation context or MCP verification
- NEVER assume navigation paths -- use routes from MCP verification
- NEVER state specific numeric thresholds unless found in PR diff, JIRA AC, MCP source, or area knowledge
- NEVER fabricate filter rules -- extract exact conditions from source code via `get_component_source`
- If investigation context is incomplete for a step, note it as "[NEEDS VERIFICATION]"
- If a filtering function is referenced, read its source via MCP and extract exact conditions -- do NOT paraphrase from the PR diff
- Always include a `## Test Steps` section header before the first `### Step N:`

## Gotchas

1. **Filter rules from PR diffs are summaries, not source** -- PR diffs show what changed, not the full logic. Always read the filter function source via `get_component_source` to get exact conditions, thresholds, and edge cases.
2. **Field order assumptions break silently** -- Table column order in area knowledge files reflects the current product. If a PR reorders columns via `cols.push()` or `splice()`, the test case must match the NEW order, not the knowledge file order.
3. **Translation keys are not display text** -- A key like `policy.table.actionGroup` resolves to a different string than the key name implies. Always call `search_translations` with the key to get the actual rendered label.
4. **Test file mock data is not product behavior** -- Automation test files often contain mock data or fixture objects. Never cite test-repo data as evidence of what the product actually does. Product source and MCP verification are the only reliable sources.
5. **`cols.push()` means append, not insert** -- When a PR adds a column via `push()`, it goes at the END of the table. Do not assume it inserts at a specific position unless the code uses `splice()` with an explicit index.
