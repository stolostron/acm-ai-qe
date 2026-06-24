# Execution Patterns -- Action-to-Tool Mapping

How to translate test case actions into executable Playwright MCP and CLI tool calls.

## Playwright MCP Workflow

Every UI interaction follows this cycle:

```
1. browser_snapshot() -> get current state + element refs
2. Identify target element by text/role/ref in the snapshot
3. Execute action (click, fill, hover, navigate)
4. Wait 1-3 seconds
5. browser_snapshot() -> confirm action took effect
6. (Optional) browser_take_screenshot() -> evidence capture
```

Always snapshot BEFORE interacting. Element `ref` values from the snapshot are required for click/fill/hover.

## Action Mapping Table

### Navigation Actions

| Test Case Language | Tool Sequence | Notes |
|-------------------|---------------|-------|
| "Navigate to X > Y > Z" | `browser_navigate(url)` if route is known; OR sequential `browser_click` through menu items | Use Entry Point route from Description if available |
| "Go to Infrastructure > Clusters" | `browser_navigate` to `/multicloud/infrastructure/clusters` | Map known ACM routes directly |
| "Navigate back to X" | `browser_navigate` to the known route for X | Use browser back only as fallback |
| "Open the ACM console" | `browser_navigate` to the multicloud base URL | Typically `/multicloud` |
| "Refresh the page" | `browser_navigate` to the current URL (re-navigate) | |
| "Click on [cluster name]" (navigation) | `browser_click` on the link element | Snapshot first to find the ref |

### Click Actions

| Test Case Language | Tool | Target Resolution |
|-------------------|------|-------------------|
| "Click on X" / "Click the X button" | `browser_click(ref)` | Find element with text "X" or role "button" with name "X" in snapshot |
| "Click the X tab" | `browser_click(ref)` | Find element with role "tab" and name containing "X" |
| "Click the X column header" | `browser_click(ref)` | Find element with role "columnheader" and name containing "X" |
| "Click the X link" | `browser_click(ref)` | Find element with role "link" and name containing "X" |
| "Select X from dropdown" | `browser_click` on dropdown trigger, then `browser_click` on option "X" | Two-step: open dropdown, then select |
| "Toggle X" / "Enable X" | `browser_click(ref)` | Find checkbox/switch element |
| "Click the tooltip trigger" | `browser_click(ref)` | Find element with role "button" near the target text |

### Hover Actions

| Test Case Language | Tool | Notes |
|-------------------|------|-------|
| "Hover over X" | `browser_hover(ref)` | Find element, hover, then snapshot to see tooltip/popover |
| "Mouse over the X header" | `browser_hover(ref)` | After hover, wait 1s for tooltip to appear |

### Form Actions

| Test Case Language | Tool | Notes |
|-------------------|------|-------|
| "Enter X in the Y field" | `browser_fill(ref, "X")` | Find input with label "Y" |
| "Type X" | `browser_fill(ref, "X")` | Find the focused or specified input |
| "Clear the X field" | `browser_fill(ref, "")` | Fill with empty string |
| "Select X from the Y dropdown" | `browser_click` (open) + `browser_click` (option) | |

### Observation Actions (No Interaction)

| Test Case Language | Tool | Notes |
|-------------------|------|-------|
| "Observe the table" | `browser_snapshot()` | Read the accessibility tree for table content |
| "View the X section" | `browser_snapshot()` | Locate section in snapshot output |
| "Note the current values" | `browser_snapshot()` | Extract values for later comparison |
| "Read the tooltip text" | `browser_snapshot()` | Tooltip content should be in the snapshot after hover |

### CLI Actions

| Test Case Language | Tool | Notes |
|-------------------|------|-------|
| Embedded ```bash block | `Bash` (shell execution) | Execute the command directly |
| "Run: `oc get ...`" | `Bash` | Execute the inline command |
| "Verify via CLI" | `Bash` | Execute the specified command |
| Variable assignment | `Bash` | Capture output, store for later use |

## Verification Patterns

How to verify each type of expected result against captured state.

### General Method (applies to EVERY verification, listed or not)

The patterns below are common examples, not an exhaustive list. For ANY expected result -- including types not listed here -- follow this method:

1. **Identify what the test case literally asks.** Read the expected result text. What observable fact does it assert? ("X exists", "Y is displayed", "Z equals N")
2. **Gather concrete evidence.** For UI assertions: `browser_snapshot` and quote the relevant part. For CLI assertions: run the command and quote the output. For multi-cluster assertions: check ALL target clusters before concluding.
3. **Compare evidence to the assertion.** Does the evidence confirm or contradict the literal text? Base the verdict ONLY on this comparison.
4. **Do not filter evidence.** If the test case asks "does resource X exist?" and the resource exists, that is confirmation -- regardless of resource age, labels, creation source, which cluster it's on, or any other metadata the test case did not ask about. Evidence is evidence.
5. **Do not stop at the first negative.** If a check fails on one cluster or one namespace, check all relevant targets before rendering FAIL. A resource found on ANY target cluster satisfies "resources persist on the target cluster" unless the test case names a specific cluster.

The specific patterns below illustrate this method for common cases. When you encounter a verification that does not match any listed pattern, apply the general method directly.

### Text Presence

**Pattern:** "X is displayed" / "X appears" / "text reads X"

**Method:** Search the accessibility snapshot text for the exact string X (case-sensitive first, case-insensitive fallback).

```
Expected: "The column header text reads 'GPU count'"
Verify: snapshot contains text "GPU count" in a columnheader role element
Result: PASS if found, FAIL if not
```

### Text Absence

**Pattern:** "X is NOT present" / "X is not displayed" / "No X appears"

**Method:** Confirm the string X does NOT appear in the accessibility snapshot.

```
Expected: "The Observability metrics link is NOT present"
Verify: snapshot does NOT contain "Observability metrics" as a link
Result: PASS if absent, FAIL if found
```

### Element Count

**Pattern:** "N columns" / "N items" / "at least N rows"

**Method:** Count matching elements in the accessibility snapshot.

```
Expected: "The Nodes table displays 9 columns"
Verify: count elements with role "columnheader" inside the table -> compare to 9
Result: PASS if count == 9, FAIL if different (report actual count)
```

### Sort Order Verification

**Pattern:** "Sorted in ascending/descending order" / "Numeric sort"

**Method:**
1. Capture column values from table rows in snapshot
2. Parse as numbers (for numeric sort) or strings (for alphabetical)
3. Verify sequence matches expected order

```
Expected: "sorts as 0, 1, 2, 10 -- not 0, 1, 10, 2"
Verify: extract GPU column values, confirm numeric ascending order
Result: PASS if correctly ordered, FAIL if not (show actual order)
```

### Navigation Verification

**Pattern:** "navigates to X" / "URL contains X" / "new tab opens"

**Method:** After the click action, check the URL in the next snapshot or capture via `browser_snapshot` metadata.

```
Expected: "The Grafana explore URL contains a query for node_accelerator_card_info"
Verify: new page URL contains "node_accelerator_card_info"
Result: PASS if URL matches, FAIL if different (show actual URL)
```

### Visual/Layout Verification

**Pattern:** "appears as the last column" / "positioned after X" / "9th position"

**Method:** Check element order in the accessibility snapshot (elements are listed in DOM order which matches visual order for tables).

```
Expected: "GPU count column appears as the last column (9th position, after RAM)"
Verify: in columnheader list, "GPU count" is at index 8 (0-based) or last position
Result: PASS if position matches, FAIL if different (report actual position)
```

### Console Error Check

**Pattern:** "No errors" / "No JavaScript errors" / "No broken UI"

**Method:** Call `browser_console_messages()` and check for error-level messages.

```
Expected: "No errors or broken UI elements appear"
Verify: browser_console_messages() returns no error-level entries
Result: PASS if clean, FAIL if errors found (list them)
```

### CLI Output Verification

**Pattern:** Expected output after a CLI command (from `# Expected:` comment)

**Method:** Execute command, pattern-match against expected.

```
Command: oc get mch ... -o jsonpath='Version: {.status.currentVersion}'
Expected: "Version: 2.17.x"
Verify: output matches regex "Version: 2\.17\.\d+"
Result: PASS if matches, FAIL if different (show actual)
```

### Ambiguous Verification (MANUAL_CHECK)

Some expected results cannot be programmatically verified:

| Pattern | Why | Result |
|---------|-----|--------|
| "page looks correct" | Subjective | MANUAL_CHECK |
| "no visual regressions" | Requires baseline image | MANUAL_CHECK |
| "UI is responsive" | Vague definition | MANUAL_CHECK |
| "performance is acceptable" | No threshold | MANUAL_CHECK |

For these: take a screenshot, record MANUAL_CHECK, note what would need human review.

## ACM Console Route Map (Common Navigation)

| Path in Test Case | ACM Route |
|-------------------|-----------|
| Infrastructure > Clusters > Cluster list | `/multicloud/infrastructure/clusters` |
| Infrastructure > Clusters > [name] > Nodes | `/multicloud/infrastructure/clusters/details/:ns/:name/nodes` |
| Infrastructure > Clusters > Cluster sets | `/multicloud/infrastructure/clusters/sets` |
| Governance > Policies | `/multicloud/governance/policies` |
| Applications > Overview | `/multicloud/applications` |
| Credentials | `/multicloud/credentials` |
| Home > Overview | `/multicloud/home/overview` |
| Access control > Roles | `/multicloud/access/roles` |

When the test case Description includes a **Route** field, use that as the direct navigation target after the initial login. This avoids fragile menu clicking for the entry point.

## Error Recovery

| Situation | Recovery |
|-----------|----------|
| Element ref not found in snapshot | Re-snapshot after 3s wait; if still missing, BLOCKED |
| Click produced no visible change | Wait 2s, re-snapshot; if unchanged, retry click once |
| Page shows loading spinner | Wait up to 10s with periodic snapshots; proceed when spinner gone |
| Navigation produced error page | Screenshot, record BLOCKED, note the error |
| Form fill rejected | Check for validation error message in snapshot, record FAIL with message |
| Timeout waiting for element | After 10s total wait, BLOCKED with "element did not appear within timeout" |
