# Skill Gap Report: Test Step Granularity and Backend Validation

**Run compared:** ACM-32282 (GPU Count Column)
- Skill run: `runs/ACM-32282/ACM-32282-2026-04-30T22-18-41/test-case.md` (6 steps)
- Original app run: `runs/ACM-32282/ACM-32282-2026-04-30T15-57-13/test-case.md` (7 steps)

---

## Gap 1: Steps Combine Multiple Verifications Into One

### Evidence

**Skill run Step 3 (combined tooltip + Grafana link + click behavior):**
```markdown
### Step 3: Verify GPU Count Column Tooltip

1. On the Nodes tab, hover over the info icon (?) next to the **GPU count** column header.
2. Read the tooltip content.
3. Observe whether an **Observability metrics** link is displayed in the tooltip.

**Expected Result:**
- The tooltip displays: *The count of GPUs on a Node is gathered from the "node_accelerator_card_info" metric...*
- An **Observability metrics** link is displayed below the tooltip text (with an external link icon).
- Clicking the **Observability metrics** link opens a new browser tab to the Grafana Explore page with the `node_accelerator_card_info` query pre-populated.
```

This step verifies THREE distinct things:
1. Tooltip text content
2. Grafana link presence
3. Grafana link click behavior (opens new tab with specific URL)

**Original app run separates these into Step 3 + Step 4:**

```markdown
### Step 3: Verify GPU Count Column Tooltip

1. Hover over the **GPU count** column header.
2. Observe the tooltip that appears.

**Expected Result:**
- A tooltip appears with the text: *"The count of GPUs on a Node..."*
- The tooltip also contains an **Observability metrics** link...

---

### Step 4: Verify Grafana Link in Tooltip

1. In the GPU count column tooltip (from Step 3), locate the **Observability metrics** link.
2. Click the **Observability metrics** link.

**Expected Result:**
- The link opens in a new browser tab.
- The link navigates to Grafana's Explore page with the `node_accelerator_card_info` query pre-populated.
- The Grafana URL matches the pattern: `<grafana-origin>/explore?schemaVersion=1&panes={"jjq":{"queries":[{"expr":"node_accelerator_card_info"}]}}&orgId=1`
```

### Why This Matters

For manual testers executing these steps:
- A combined step means "did it pass or fail?" is ambiguous when ONE of three checks fails
- If the tooltip text is correct but the link is broken, the step is "partial pass" -- hard to report in Polarion
- Separate steps allow precise pass/fail tracking per verification point
- Polarion test execution records pass/fail PER STEP -- granular steps give better signal

### Root Cause

The skill's `acm-test-case-writer` SKILL.md says "each step as `### Step N: Title` with numbered actions and bullet expected results" but does NOT specify a **one-verification-point-per-step** rule. The synthesized context's TEST PLAN section proposed 6 steps:

```
Per-step validations:
1. Verify prerequisites...
2. Navigate to cluster Nodes tab, verify GPU count column present with correct position
3. Verify GPU count values for nodes
4. Verify tooltip content and Observability metrics link    <-- COMBINED
5. Verify GPU count column sorting
6. Negative scenario...
```

The synthesis template already combined tooltip + link into one item (#4). The writer followed the plan without splitting.

---

## Gap 2: Backend Validation Embedded Mid-Step Instead of Dedicated Step

### Evidence

**Skill run Step 2 (GPU values + inline CLI):**
```markdown
### Step 2: Verify GPU Count Values for Nodes

1. On the Nodes tab, observe the **GPU count** column values for each node.
2. Note the GPU count for each node.
3. Verify the backend metric data:

\`\`\`bash
PROXY_ROUTE=$(oc get route rbac-query-proxy -n open-cluster-management-observability -o jsonpath='{.spec.host}')
TOKEN=$(oc whoami -t)
curl -sk -H "Authorization: Bearer $TOKEN" "https://${PROXY_ROUTE}/api/v1/query?query=node_accelerator_card_info" | python3 -m json.tool
\`\`\`

4. Compare the CLI metric results with the GPU count values displayed in the UI.

**Expected Result:**
- Nodes with GPUs show a positive integer GPU count...
- Nodes without GPUs show **0**.
- The UI values match the metric data from the observability API...
```

This mixes UI verification (actions 1-2) with backend CLI verification (action 3-4) in the same step.

**Original app run dedicates a separate step (Step 6):**
```markdown
### Step 6: Verify GPU Metric Data via CLI (Backend Validation)

1. Query the `node_accelerator_card_info` metric via the Observability API:
\`\`\`bash
curl -sk -H "Authorization: Bearer $(oc whoami -t)" \
  "https://$(oc get route rbac-query-proxy -n open-cluster-management-observability -o jsonpath='{.spec.host}')/api/v1/query?query=node_accelerator_card_info" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); r=d.get('data',{}).get('result',[]); print(f'Total GPU metric instances: {len(r)}'); [print(f\"  Node: {x['metric'].get('instance','?')}\") for x in r]"
\`\`\`

**Expected Result:**
- The query returns the `node_accelerator_card_info` metric results.
- The number of metric instances per node matches the GPU count values displayed in the UI (Step 2).
- If no GPUs are present in the environment, the result set is empty...
```

### Why This Matters

- The CLI-in-steps rule from `test-case-format.md` says: "CLI is allowed mid-test ONLY for backend validation" -- but the INTENT is that backend validation is clearly demarcated so testers know when to switch from browser to terminal
- Embedding CLI in the middle of a UI step creates a context switch that testers may miss
- A dedicated backend step makes the test flow clear: UI first (Steps 1-5), then backend cross-check (Step 6)
- For automation: separated steps map cleanly to separate test functions

### Root Cause

The writer skill's instructions don't specify WHERE CLI backend validation should be placed. The self-review checklist (Step 6 in the writer) says "CLI only for backend validation in test steps?" which confirms CLI IS allowed, but doesn't say "put backend validation in its own step" or "don't embed CLI in UI-focused steps."

---

## Gap 3: Missing Numeric Sorting Precision

### Evidence

**Skill run Step 4 (sorting):**
```markdown
### Step 4: Verify GPU Count Column Sorting

1. On the Nodes tab, click the **GPU count** column header to sort.
2. Observe the sort order of the rows.
3. Click the column header again to reverse the sort order.

**Expected Result:**
- Clicking the GPU count column header sorts nodes by GPU count in ascending order (0s first, then increasing counts).
- Clicking again sorts in descending order (highest GPU count first).
- The sort indicator (arrow icon) reflects the current sort direction.
```

**Original app run Step 5 (sorting):**
```markdown
**Expected Result:**
- Clicking the column header sorts nodes by GPU count in ascending order (lowest count first).
- Clicking again sorts in descending order (highest count first).
- Sorting is numeric, not alphabetical (e.g., 0, 1, 2, 10 — not 0, 1, 10, 2).
```

### Why This Matters

The distinction between numeric and alphabetical sorting is a REAL BUG SCENARIO. If the sort function treats GPU counts as strings, "10" sorts before "2" (alphabetical). The original explicitly calls this out as a verification point. The skill run doesn't -- a tester might not think to check this edge case.

### Root Cause

The synthesized context (phase2-synthesized-context.md line 63) documents:
```
SORTING: compareNumbers(nodeGPUCounts[a.name], nodeGPUCounts[b.name])
- Handles undefined/null (sorts to end)
```

The code uses `compareNumbers` (numeric sorting) but the skill's writer didn't translate this implementation detail into a testable verification point. The synthesis captured it, but the writer didn't emphasize it as a distinct expected result.

---

## Proposed Solutions

### Solution 1: Add "One Verification Per Step" Rule to Writer

Add to `acm-test-case-writer/SKILL.md` under "Step 5: Write the Test Case" section:

```markdown
**Step granularity rule:** Each test step should verify ONE distinct behavior or interaction. If a step has expected results that test different aspects (e.g., text content AND link behavior AND click navigation), split into separate steps. Ask: "If one expected result passes but another fails, would a tester need to report this as a partial pass?" If yes, split.

Signs a step needs splitting:
- Expected results verify both READ (observe text) and ACTION (click/interact) outcomes
- Expected results mix UI verification with backend CLI verification
- A single step has 4+ expected result bullets covering different behaviors
- The step title uses "and" connecting two distinct verifications
```

### Solution 2: Add "Backend Validation Placement" Rule to Writer

Add to `acm-test-case-writer/SKILL.md` under "Step 5: Write the Test Case" section:

```markdown
**Backend validation placement:** When a test case includes CLI-based backend verification (checking resource state, querying APIs, verifying metric data), place it in a DEDICATED step titled "Verify [what] via CLI (Backend Validation)" -- do NOT embed it within a UI-focused step. This ensures:
- Clear context switch (browser → terminal) is visible in the step title
- Pass/fail is cleanly attributed to UI behavior vs backend state
- Automation can map UI steps to browser functions and CLI steps to shell functions

Exception: Setup commands in the Setup section are not affected by this rule.
```

### Solution 3: Add "Implementation Detail Translation" Rule to Writer

Add to `acm-test-case-writer/SKILL.md` under "Step 5: Write the Test Case" section:

```markdown
**Translate implementation details to tester-visible verifications:** When the synthesized context includes implementation details (sort algorithm, comparison function, data parsing logic), translate them into OBSERVABLE verifications. Ask: "What would a tester SEE if this implementation detail were wrong?"

Examples:
- `compareNumbers(a, b)` → "Sorting is numeric, not alphabetical (e.g., 0, 1, 2, 10 — not 0, 1, 10, 2)"
- `text.split(':')[0]` → "The hostname displayed matches the node name (port suffix stripped)"
- `Object.keys(labels).length > 0 ? render : '-'` → "When no data exists, the field shows '-' (dash)"
- `skip: !isInstalled` → "The column/feature is NOT present when [component] is not installed"
```

### Solution 4: Update Synthesis Template with Step Splitting Guidance

Add to `acm-test-case-generator/references/synthesis-template.md` under the TEST PLAN section:

```markdown
Per-step validations (apply the ONE-VERIFICATION-PER-STEP rule):
- If a planned step covers multiple behaviors (e.g., "tooltip content AND Grafana link"), split into separate steps
- If a planned step mixes UI and CLI verification, split into "UI step" + "Backend validation step"
- Target: each step should have 2-3 expected result bullets covering the SAME behavior
```

---

## Summary

| Gap | Root Cause Location | Fix Location | Impact |
|-----|-------------------|--------------|--------|
| Combined verifications in one step | Synthesis template + writer skill | synthesis-template.md + acm-test-case-writer/SKILL.md | Manual testers can't report granular pass/fail |
| Backend CLI embedded in UI steps | Writer skill (no placement rule) | acm-test-case-writer/SKILL.md | Context switch unclear, automation harder |
| Implementation details not translated | Writer skill (no translation rule) | acm-test-case-writer/SKILL.md | Edge-case verifications missed |

All three fixes are additive (new rules added to existing files). No existing functionality is removed.
