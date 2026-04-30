---
name: acm-test-case-reviewer
description: Quality gate for ACM Console UI test cases. Validates conventions, verifies UI elements are discovered not assumed, checks AC vs implementation consistency, cross-references area knowledge, and enforces minimum MCP verification. Use after a test case is written to validate it before delivery.
compatibility: "Requires acm-ui MCP (for MCP verification spot-checks). Uses acm-polarion-client skill (requires polarion MCP). Uses acm-knowledge-base skill (no MCP needed)."
---

# ACM Test Case Quality Reviewer

Validates generated test cases against conventions, verifies UI elements were discovered (not assumed), checks peer consistency, and enforces Polarion metadata completeness. This is the mandatory quality gate before a test case is delivered.

## Prerequisites

- A test case `.md` file to review
- acm-ui-source skill available for MCP spot-checks
- acm-polarion-client skill available for coverage checks
- acm-knowledge-base skill available for conventions and area knowledge

## Review Process

### Step 1: Read the Test Case

Read the full test case markdown file.

### Step 2: Read Conventions

Read from acm-knowledge-base skill:
- `references/conventions/test-case-format.md`
- `references/conventions/area-naming-patterns.md`
- `references/conventions/cli-in-steps-rules.md`

### Step 3: Structural Validation

Check each section against conventions. Flag as BLOCKING if:
- Title doesn't match `# RHACM4K-XXXXX - [Tag-Version] Area - Test Name`
- Any required Polarion metadata field is missing (Type, Level, Component, Subcomponent, Test Type, Pos/Neg, Importance, Automation, Tags, Release)
- `## Type:` value is not `Test Case`
- Description missing Entry Point or Dev JIRA Coverage
- `## Test Steps` header missing
- Steps missing `### Step N: Title` format, numbered actions, or bullet expected results
- Steps not separated by `---`

Flag as WARNING if:
- Setup commands missing `# Expected:` comments
- Teardown missing `--ignore-not-found` on delete commands
- Tags don't match the area conventions

### Step 4: MCP Verification (MANDATORY -- minimum 3 checks)

Use acm-ui-source skill for spot-checks. You MUST perform at least 3 MCP verifications:

1. `set_acm_version` -- set the version from the test case
2. `search_translations` for 1-2 key UI labels -- verify they match the test case
3. `get_routes` -- verify the entry point route exists and matches
4. `get_component_source` for the primary component -- verify at least ONE factual claim (field order, filtering behavior, empty state, conditional rendering)

For each verification, record:
- Tool used
- Query made
- Result summary
- Whether it matches the test case (true/false)

If fewer than 3 verifications are performed, the verdict MUST be NEEDS_FIXES.

### Step 5: AC vs Implementation Check

1. Extract the JIRA story's Acceptance Criteria from the investigation context
2. For each AC, check if the test case's expected results are consistent
3. If an AC says behavior X but the test expects behavior Y:
   - Check if a Note explains the discrepancy with source code citation
   - If a Note cites source code: verify the cited behavior via `get_component_source`
   - If no Note exists: flag as BLOCKING
4. Check scope: test case should validate the target JIRA story's ACs, not the broader PR scope

### Step 6: Knowledge File Cross-Reference

Read `references/architecture/<area>.md` from acm-knowledge-base. Verify:
- Field order claims match the knowledge file
- Filtering behavior claims match the knowledge file
- Component names and CRDs are consistent
- Flag contradictions as BLOCKING

### Step 7: Polarion Coverage Check

Use acm-polarion-client skill:
- Search for existing test cases with similar titles
- Check for potential duplication
- Verify metadata accuracy if a Polarion ID is referenced

### Step 8: Peer Consistency

Read 2-3 existing test cases from the same area for comparison:
- Similar section structure?
- Similar level of detail in expected results?
- Similar setup format?
- Similar teardown approach?

## Output Format

```
TEST CASE REVIEW
================
File: [path]
Area: [area]
Version: [version]

MCP VERIFICATIONS (minimum 3 required):
1. [tool]: [query] -> [result] -> matches test case: [true/false]
2. [tool]: [query] -> [result] -> matches test case: [true/false]
3. [tool]: [query] -> [result] -> matches test case: [true/false]

BLOCKING (must fix):
1. [issue] -- Fix: [instruction]

WARNING (should fix):
1. [issue] -- Fix: [instruction]

Verdict: PASS | NEEDS_FIXES
```

## Programmatic Enforcement

After the review, the calling skill runs `scripts/validate_conventions.py` to programmatically verify structural compliance. Additionally, the calling skill runs `scripts/review_enforcement.py` to verify this review output contains at least 3 MCP verification entries. If either check fails, the verdict is overridden to NEEDS_FIXES regardless of what this review concluded.

## Critical Rules

- ALWAYS perform at least 3 MCP verifications -- no exceptions
- ALWAYS read the primary component source to verify at least ONE factual claim
- ALWAYS check Polarion for duplicate/existing test cases
- ALWAYS cross-reference area knowledge file
- Flag as BLOCKING if any test step states a numeric threshold without evidence
- Flag as BLOCKING if filter prefixes/conditions don't match source code
- The verdict MUST be either PASS or NEEDS_FIXES -- no ambiguity
