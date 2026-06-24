# Execution Engine

How the validator translates test case actions into live interactions and verifies expected results.

## Action Classification

Every action in a test step is classified before execution. Classification determines which tool handles it.

```
Test Step Action Text
       │
       ▼
┌──────────────────┐     ┌───────────────────┐
│ Contains UI verb │────▶│ UI_ACTION          │
│ (click, navigate,│     │ Tool: Playwright   │
│  hover, observe) │     └───────────────────┘
└──────────────────┘
       │ No
       ▼
┌──────────────────┐     ┌───────────────────┐
│ Contains CLI/bash│────▶│ CLI_ACTION         │
│ (oc, kubectl,    │     │ Tool: Bash shell   │
│  ```bash block)  │     └───────────────────┘
└──────────────────┘
       │ No
       ▼
┌──────────────────┐     ┌───────────────────┐
│ Mixed (both)     │────▶│ HYBRID             │
│                  │     │ Tool: Both         │
└──────────────────┘     └───────────────────┘
```

### UI Action Verbs

| Verb Category | Keywords | Tool Call |
|--------------|----------|-----------|
| Navigation | "Navigate to", "Go to", "Open" | `browser_navigate(url)` or sequential `browser_click` |
| Click | "Click", "Press", "Select", "Toggle" | `browser_click(ref)` |
| Hover | "Hover over", "Mouse over" | `browser_hover(ref)` |
| Form input | "Fill", "Type", "Enter", "Clear" | `browser_fill(ref, value)` |
| Observation | "Observe", "View", "Look at", "Note" | `browser_snapshot()` (no interaction) |
| Refresh | "Refresh", "Reload" | `browser_navigate(current_url)` |

### CLI Action Patterns

| Pattern | Detection |
|---------|-----------|
| Inline code: `` `oc get pods` `` | Backtick-wrapped command |
| Code block: ` ```bash ... ``` ` | Fenced code block |
| Explicit: "Run the command:" | Followed by command on next line |

## Playwright MCP Workflow

Every UI interaction follows a strict cycle:

```
┌────────────────────────────────────────────┐
│ 1. browser_snapshot()                      │
│    → Get current page state + element refs │
├────────────────────────────────────────────┤
│ 2. Identify target element                 │
│    → Match by text, role, or ref ID        │
├────────────────────────────────────────────┤
│ 3. Execute action                          │
│    → browser_click / fill / hover          │
├────────────────────────────────────────────┤
│ 4. Wait 1-3 seconds                        │
├────────────────────────────────────────────┤
│ 5. browser_snapshot()                      │
│    → Confirm action took effect            │
├────────────────────────────────────────────┤
│ 6. If action failed → retry once           │
│    If retry fails → BLOCKED                │
└────────────────────────────────────────────┘
```

### Element Resolution Strategy

When finding a target element in the accessibility snapshot:

| Priority | Method | Example |
|:--------:|--------|---------|
| 1 | Exact text match in role | Button with name "Actions" |
| 2 | Partial text match in role | Tab containing "Nodes" |
| 3 | Role type + position | 9th columnheader element |
| 4 | Nearby text context | Button adjacent to "GPU count" header |
| 5 | Knowledge DB fallback | Route table for navigation targets |

### Error Recovery

| Situation | Recovery Action | Max Retries |
|-----------|----------------|:-----------:|
| Element not found | Wait 3s, re-snapshot | 2 |
| Click had no effect | Wait 2s, retry click | 1 |
| Loading spinner visible | Wait up to 10s with periodic snapshot | 3 |
| Navigation error page | Screenshot, mark BLOCKED | 0 |
| Form validation error | Capture error message, mark FAIL | 0 |
| Timeout (10s+) | Mark BLOCKED with details | 0 |

## Verification Methods

Each bullet in a test step's "Expected Result" section is verified using a pattern-matched method.

### Text Presence

**Triggers:** "is displayed", "appears", "reads", "shows", "contains"

```
Expected: "The column header text reads 'GPU count'"
Method:   Search accessibility snapshot for exact text "GPU count"
          in an element with role "columnheader"
Verdict:  PASS if found at expected position
          FAIL if text absent or at wrong position
```

### Text Absence

**Triggers:** "NOT present", "not displayed", "does not appear", "is hidden"

```
Expected: "The Observability metrics link is NOT present"
Method:   Confirm NO element with role "link" contains "Observability metrics"
Verdict:  PASS if truly absent
          FAIL if found
```

### Element Count

**Triggers:** "N columns", "N items", "N rows", "at least N"

```
Expected: "The Nodes table displays 9 columns"
Method:   Count elements with role "columnheader" inside the nearest table
Verdict:  PASS if count == 9
          FAIL if count != 9 (report actual: "Found 8 columns")
```

### Sort Order

**Triggers:** "sorted", "ascending", "descending", "numeric sort"

```
Expected: "Values sort as 0, 1, 2, 10 -- not 0, 1, 10, 2"
Method:   1. Extract column cell values from table rows
          2. Parse as numbers
          3. Verify sequence is monotonically increasing (ascending) or decreasing
Verdict:  PASS if correctly ordered
          FAIL if wrong order (report actual sequence)
```

### Navigation/URL

**Triggers:** "navigates to", "URL contains", "opens to", "redirects to"

```
Expected: "Grafana explore URL contains node_accelerator_card_info"
Method:   After click, check page URL in next snapshot
Verdict:  PASS if URL substring matches
          FAIL if URL doesn't contain expected string (report actual URL)
```

### Position/Order

**Triggers:** "last column", "9th position", "after X", "before Y"

```
Expected: "GPU count appears as the last column (9th position, after RAM)"
Method:   In snapshot, locate all columnheader elements in DOM order
          Check "GPU count" is at index 8 (0-based) or last
Verdict:  PASS if position matches
          FAIL if wrong position (report: "Found at position 7")
```

### Console Errors

**Triggers:** "No errors", "No JavaScript errors", "No broken UI"

```
Expected: "No errors or broken UI elements appear"
Method:   Call browser_console_messages(), filter for error-level entries
Verdict:  PASS if no errors
          FAIL if errors found (list them)
```

### CLI Output

**Triggers:** After a bash command, compare output to `# Expected:` pattern

```
Command:  oc get mch ... -o jsonpath='Version: {.status.currentVersion}'
Expected: "Version: 2.17.x"
Method:   Execute command, match output against regex "Version: 2\.17\.\d+"
Verdict:  PASS if matches
          FAIL if different (report actual output)
```

### Ambiguous (MANUAL_CHECK)

**Triggers:** Subjective language with no measurable criterion

| Pattern | Why Unverifiable |
|---------|-----------------|
| "page looks correct" | No baseline image for comparison |
| "no visual regressions" | Requires pixel-diff tooling |
| "UI is responsive" | No defined threshold |
| "performance is acceptable" | No timing metric specified |

For these: capture screenshot, record MANUAL_CHECK, note what needs human review.

## ACM Console Navigation

The skill uses a built-in route map for common ACM navigation paths:

| Test Case Shorthand | Resolved Route |
|--------------------|--------------:|
| Infrastructure > Clusters | `/multicloud/infrastructure/clusters` |
| Infrastructure > Clusters > [name] > Nodes | `/multicloud/infrastructure/clusters/details/:ns/:name/nodes` |
| Governance > Policies | `/multicloud/governance/policies` |
| Applications > Overview | `/multicloud/applications` |
| Credentials | `/multicloud/credentials` |
| Access control > Roles | `/multicloud/access/roles` |
| Search | `/multicloud/search` |

When the test case Description includes a **Route** field, that route is used directly via `browser_navigate` instead of clicking through menus.

If navigation shorthand is ambiguous and not in the route map, the knowledge DB (`knowledge/ui/<area>.md`) is consulted for the correct route.

## State Management

### Session Variables

Variables assigned during setup (e.g., `GRAFANA_LINK=$(oc get ...)`) are preserved across the entire execution session and available during teardown for restoration commands.

### Browser State Continuity

The browser session persists across all steps. Step N starts from wherever Step N-1 left the page. No page is re-navigated between steps unless the step explicitly says to navigate.

### Execution Modes

| Mode | Flag | Behavior on FAIL | Teardown |
|------|------|-----------------|----------|
| Full (default) | `--full` | Continue executing remaining steps | Skipped (preserves resources) |
| Fail-fast | `--fail-fast` | Stop immediately, skip to Phase 5 | Skipped (preserves resources) |
| Always teardown | `--always-teardown` | Per execution mode | Forced regardless of verdict |

## Resource Tracking and Delete Safety

### Resource Registry

Every resource created during the run is tracked in a `CREATED_RESOURCES` registry:

```
{ type: "namespace", name: "test-ns", namespace: "-", cluster: "hub", created_in: "Phase 3, Setup cmd 4" }
{ type: "applicationset", name: "my-app", namespace: "openshift-gitops", cluster: "hub", created_in: "Phase 4, Step 2" }
```

Resources are added to the registry after successful creation (CLI `oc apply`/`create` returns 0, or UI wizard submit confirmed). Only resources in this registry can be deleted.

### 5-Point Delete Safety Check

Applied before every delete operation (CLI or UI):

```
For each delete operation:
  ┌─ 1. OWNERSHIP: Is resource in CREATED_RESOURCES? ──── NO → BLOCK
  ├─ 2. SCOPE: Created during THIS run? ───────────────── NO → BLOCK
  ├─ 3. CLUSTER: Targeting correct cluster? ────────────── NO → BLOCK
  ├─ 4. NO WILDCARD: Targeted (no --all)? ──────────────── NO → BLOCK
  └─ 5. LOG: [DESTRUCTIVE] Deleting type/name ──────────── Always
       ↓
     EXECUTE DELETE
```

### Hard No-Go List

These resources are NEVER deleted or modified, even if they appear in the test case:

**Protected from deletion:**
- ClusterRoles / ClusterRoleBindings
- CustomResourceDefinitions
- Operators / CSVs / Subscriptions (OLM)
- MultiClusterHub
- ManagedCluster resources
- System namespaces: `openshift-*`, `kube-*`, `open-cluster-management*`, `multicluster-engine`

**Protected from modification:**
- OAuth configuration
- Cluster-scoped secrets
- Node labels / taints
- Infrastructure / networking configuration

### UI Delete Gate

When a test step requires clicking a "Delete" button:

1. Identify the target resource from page context (dialog text, heading)
2. Check: is resource in CREATED_RESOURCES registry?
3. If YES + 5-point check passes: proceed
4. If NO: BLOCKED -- "Refusing to delete pre-existing resource"
