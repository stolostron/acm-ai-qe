# Coverage Gap Handling

The synthesis phase (Phase 4) triages coverage gaps found during investigation. Each gap is assigned one of three dispositions:

## ADD TO TEST PLAN

Create test steps for these gaps. They represent functionality that the Acceptance Criteria require but that no existing test step covers.

How to translate a coverage gap into a step:
1. Read the gap description — it identifies a specific behavior or UI element
2. Determine the observable verification: what would a tester check to confirm this works?
3. Write a step using the same conventions as other steps (numbered actions, bullet expected results)
4. Place the step in logical sequence — usually after the related UI steps

Example gap: "AC says 'user can filter by compliance status' but no test step verifies filtering"
→ Step: "Verify Compliance Status Filtering" with actions to select filter, observe results, clear filter.

## NOTE ONLY

Mention these gaps in the **Notes** section of the test case. They are known uncovered behaviors that do not warrant dedicated test steps — either because they are covered by other test cases, they are low-risk, or the gap is about a behavior outside the target story's scope.

Format in Notes: "Coverage note: [gap description] — covered by [other test case / reason for exclusion]."

## SKIP

Ignore these gaps entirely. They were flagged during investigation but determined to be false positives, out of scope, or already adequately covered by the steps being written.

Do not mention SKIP gaps in the test case output.
