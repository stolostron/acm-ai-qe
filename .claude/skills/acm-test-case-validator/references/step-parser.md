# Step Parser -- Test Case Markdown Parsing Specification

How to parse an ACM Console UI test case markdown file into a structured execution plan.

## Document Structure (Expected Sections)

Every test case follows this section order:

```
# RHACM4K-XXXXX - [Tag-Version] Area - Test Name    <- Title (H1)
**Polarion ID:** ...                                  <- Metadata block
## Type: Test Case                                    <- Polarion fields (## key: value)
## Level: ...
...
---
## Description                                        <- Description section
...
---
## Setup                                              <- Setup section
**Prerequisites:**                                    <- Human-readable prereqs
**Setup Commands:**                                   <- Bash code blocks
```bash
...
```
---
### Step N: Title                                     <- Test Steps (H3)
1. Action...
**Expected Result:**
- Bullet...
---
## Teardown                                           <- Teardown section
```bash
...
```
## Notes                                              <- Optional notes (ignore)
```

## Parsing Algorithm

### 1. Extract Metadata

Find lines matching these patterns at the top of the file:

| Field | Pattern | Example |
|-------|---------|---------|
| Polarion ID | `**Polarion ID:** RHACM4K-\d+` | RHACM4K-64019 |
| Title | First H1: `# RHACM4K-...` | Full title string |
| Area | From title tag: `[Tag-Version]` | Clusters, FG-RBAC, GRC, Fleet Virt |
| Release | `## Release: X.XX` | 2.17 |
| Component | `## Component: ...` | console |

### 2. Extract Description

Everything between `## Description` and the next `---` or `## Setup`.

Key fields to extract:
- **Entry Point**: Line starting with `**Entry Point:**` -- the navigation path (e.g., "Infrastructure > Clusters > Cluster list")
- **Route**: Line starting with `**Route:**` -- the URL path pattern

### 3. Extract Setup

The Setup section has two parts:

#### Prerequisites (text)

Lines between `**Prerequisites:**` and `**Setup Commands:**`. These are human-readable conditions:

```
- ACM 2.17.x hub cluster with console access
- cluster-admin access to the hub cluster
- multicluster-observability installed and running
```

Parse each bullet into a prerequisite object:

**Hub vs Spoke terminology:** "Managed clusters" in test case prerequisites always means **spoke clusters** -- remote clusters registered with the hub. The hub itself (often listed as `local-cluster` in `oc get managedclusters`) does NOT count. When a test case says "at least 2 managed clusters in Available state", it means 2 spokes, not counting `local-cluster`.

```
{ text: "ACM 2.17.x hub cluster", check_type: "acm_version", expected: "2.17" }
{ text: "cluster-admin access", check_type: "rbac", expected: "cluster-admin" }
{ text: "multicluster-observability installed", check_type: "resource_exists", resource: "multiclusterobservability" }
{ text: "managed clusters in Available state", check_type: "spoke_clusters", min_count: 2, exclude: "local-cluster" }
```

The `spoke_clusters` check type uses: `oc get managedclusters -o name | grep -v local-cluster` and counts only those with `ManagedClusterConditionAvailable=True`.

#### Setup Commands (bash)

Content inside ` ```bash ... ``` ` blocks after `**Setup Commands:**`.

Parse each command:
1. Lines starting with `#` followed by a number and period (e.g., `# 1. Verify ACM...`) are step labels
2. Lines starting with `# Expected:` are expected output patterns
3. All other non-comment lines are executable commands
4. Variable assignments (e.g., `GRAFANA_LINK=$(...)`) should be captured and preserved across the session

Result: Array of setup command objects:

```
[
  {
    label: "Verify ACM 2.17+ is installed",
    command: "oc get mch multiclusterhub -n open-cluster-management -o jsonpath='Version: {.status.currentVersion}'",
    expected_pattern: "Version: 2.17.*",
    is_state_changing: false
  },
  ...
]
```

**Classification of state-changing commands:**
- `oc apply`, `oc create`, `oc patch`, `oc delete`, `oc annotate`, `oc label` -> `is_state_changing: true`
- `oc get`, `oc describe`, `oc whoami`, variable assignments, `echo` -> `is_state_changing: false`

### 4. Extract Test Steps

Each step starts with `### Step N: Title` and ends at the next `---` or `### Step`.

#### Actions

Numbered lines (e.g., `1. Navigate to...`, `2. Click...`) are actions. Multi-line actions continue until the next numbered line or `**Expected Result:**`.

Actions that contain embedded bash code blocks are CLI actions:
```
1. Remove the launch-link annotation:
```bash
oc annotate clustermanagementaddon ...
```
```

#### Expected Results

Lines after `**Expected Result:**` that start with `-` are expected result bullets. They continue until `---` or the next `### Step`.

#### Action Classification

For each action, determine its type:

| Contains | Classification |
|----------|---------------|
| "Navigate to", "Go to", "Open" + UI path | `UI_ACTION` |
| "Click", "Press", "Select", "Toggle" | `UI_ACTION` |
| "Hover over", "Mouse over" | `UI_ACTION` |
| "Fill", "Type", "Enter" + input/field | `UI_ACTION` |
| "Observe", "View", "Look at", "Note" | `UI_ACTION` (read-only) |
| "Refresh the page", "Reload" | `UI_ACTION` |
| "`oc `", "```bash", "Run the command" | `CLI_ACTION` |
| "Verify" + no explicit UI action | `UI_ACTION` (observation) |
| Mixed (UI action + embedded CLI) | `HYBRID` |

#### Step Object

```
{
  number: 1,
  title: "Verify GPU Count Column Appears With Observability",
  actions: [
    { index: 1, text: "Log into the ACM console as cluster-admin", type: "UI_ACTION" },
    { index: 2, text: "Navigate to Infrastructure > Clusters > Cluster list tab", type: "UI_ACTION" },
    { index: 3, text: "Click on a managed cluster name", type: "UI_ACTION" },
    { index: 4, text: "Click the Nodes tab", type: "UI_ACTION" },
    { index: 5, text: "Observe the table column headers", type: "UI_ACTION" }
  ],
  expected_results: [
    "The Nodes table displays 9 columns: Name, Status, Role, Region, Zone, Instance type, CPU, RAM, GPU count.",
    "The GPU count column appears as the last column (9th position, after RAM).",
    "The column header text reads \"GPU count\"."
  ],
  classification: "UI_ACTION",
  has_state_change: false
}
```

The step-level `classification` is determined by the majority type. If any action is CLI, and any is UI, the step is `HYBRID`.

The `has_state_change` flag is true if any action modifies cluster state (annotate, create, patch, delete).

### 5. Extract Teardown

Content inside ` ```bash ... ``` ` blocks after `## Teardown`.

Parse identically to Setup Commands, but all commands are assumed state-changing (deletes, label removals, annotation restores).

```
[
  {
    label: "Restore launch-link annotation",
    command: "oc annotate clustermanagementaddon observability-controller console.open-cluster-management.io/launch-link=\"$GRAFANA_LINK\" --overwrite",
    expected_pattern: "clustermanagementaddon.* annotated",
    is_state_changing: true
  }
]
```

### 6. Handle Polarion Input

When the input is a Polarion ID instead of a file path:

1. Fetch the work item: `mcp__polarion__get_polarion_work_item(project_id="RHACM4K", work_item_id="<ID>", fields="@all")`
2. Fetch test steps: `mcp__polarion__get_polarion_test_steps(project_id="RHACM4K", work_item_id="<ID>")`
3. Fetch setup HTML: `mcp__polarion__get_polarion_setup_html(project_id="RHACM4K", work_item_id="<ID>")`

Convert Polarion HTML format to the internal step structure:
- Polarion steps have `columns[0]` = Step (action) and `columns[1]` = Expected Result
- Strip HTML tags, preserve structure
- Apply the same action classification logic

### 7. Validation of Parsed Output

Before proceeding to Phase 2, verify:
- At least 1 test step was extracted
- Each step has at least 1 action and at least 1 expected result
- Entry point was found (warn if not -- navigation will require explicit URL)
- Release version was found (warn if not -- cannot check version compatibility)

If no steps could be parsed: STOP the pipeline with error "Could not parse test case -- format may not match expected conventions."
