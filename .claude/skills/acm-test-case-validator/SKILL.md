---
name: acm-test-case-validator
description: >-
  Executes an existing ACM Console UI test case step-by-step against a live
  environment and produces a per-step pass/fail report with evidence (screenshots,
  CLI output, accessibility snapshots). Takes a test case markdown file, Polarion ID,
  or inline content as input. Does NOT generate or modify test cases -- only validates
  them. TRIGGER: validate test case, execute test case, run test case on cluster,
  validate RHACM4K-XXXXX on environment, dry-run test case, check if test case passes.
  DO NOT TRIGGER: generate test case from JIRA (use acm-test-case-generator); review
  test case quality/format (use acm-test-case-reviewer); verify a bug fix (use
  acm-bug-fix-verifier).
compatibility: >-
  Required: playwright MCP (UI actions), oc CLI (setup/teardown/backend checks).
  Optional: polarion MCP (fetch test case by Polarion ID), acm-kubectl MCP (spoke
  cluster checks), acm-search MCP (resource existence). Run /onboard to configure.
metadata:
  author: acm-qe
  version: "1.0.0"
  skill-standard: "anthropic-agent-skills-v1"
  category: validation
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash(oc:*)
  - Bash(kubectl:*)
  - Bash(echo:*)
  - Bash(date:*)
  - Bash(mkdir:*)
  - Bash(ls:*)
  - Bash(cat:*)
  - Bash(grep:*)
  - Bash(head:*)
  - Bash(tail:*)
  - Bash(jq:*)
  - Bash(wc:*)
  - Bash(basename:*)
  - Bash(dirname:*)
  - Bash(realpath:*)
  - mcp__playwright__browser_navigate
  - mcp__playwright__browser_snapshot
  - mcp__playwright__browser_click
  - mcp__playwright__browser_fill
  - mcp__playwright__browser_hover
  - mcp__playwright__browser_take_screenshot
  - mcp__playwright__browser_console_messages
  - mcp__playwright__browser_wait_for
  - mcp__polarion__get_polarion_work_item
  - mcp__polarion__get_polarion_test_steps
  - mcp__polarion__get_polarion_setup_html
  - mcp__polarion__get_polarion_test_case_summary
---

# ACM Test Case Validator

Executes an existing test case step-by-step against a live ACM environment. Produces a per-step pass/fail report with evidence. This skill validates -- it does not generate or modify test cases.

## Progressive Disclosure

| Level | Source | When Loaded |
|-------|--------|-------------|
| 1 -- Frontmatter | YAML `description` above | Always (system prompt) |
| 2 -- This file | Full workflow, phases 0-6, safety rules | On skill activation |
| 3 -- References | Loaded on demand during specific phases | During execution |

Reference files (load only when executing the relevant phase):
- `references/step-parser.md` -- Phase 1: markdown parsing rules, action classification
- `references/execution-patterns.md` -- Phase 4: action-to-tool mapping, verification techniques
- `references/verdict-format.md` -- Phase 6: report structure, evidence format, run directory layout

## Knowledge Database (Fallback Context)

The shared knowledge database at `${SKILLS_DIR}/../knowledge/` provides supplementary context when the test case itself doesn't specify enough detail for execution. **The test case is always the primary source of truth** -- knowledge DB is a fallback for filling execution gaps.

**When to consult the knowledge DB:**

| Situation | What to Read | Example |
|-----------|-------------|---------|
| Test case says "Navigate to X" but no route specified | `knowledge/ui/<area>.md` (Navigation Routes table) | "Navigate to Applications" -> lookup route `/multicloud/applications` |
| A button/element cannot be found in the snapshot | `knowledge/ui/<area>.md` (Key Components, Testing Considerations) | Button may be behind a menu, or have a different label |
| CLI step references a CRD you need context for | `knowledge/architecture/<subsystem>/architecture.md` | Understanding what a ManifestWork or PlacementDecision is |
| Step references managed cluster behavior | `knowledge/architecture/cluster-lifecycle/` | Understanding ManagedCluster conditions, addon status |
| Feature area context needed for ambiguous expected results | `knowledge/ui/<area>.md` (Overview, Testing Considerations) | Understanding what "sync status" means in Applications context |

**When NOT to consult the knowledge DB:**
- Do NOT use it to second-guess the test case's expected results
- Do NOT flag a step as FAIL because the knowledge DB says something different from what the test case expects
- Do NOT add extra verifications beyond what the test case specifies
- The test case defines what "correct" means -- the knowledge DB only helps you get there

**This principle applies universally, not just to the knowledge DB.** During verdict evaluation (Phase 4.4), the same rules apply to your own domain knowledge, training data, and reasoning about how Kubernetes, ArgoCD, or ACM "should" behave. The test case text is the sole authority for what constitutes PASS or FAIL.

**Area-to-file mapping:**

| Test Case Area | Knowledge File |
|---------------|---------------|
| Applications / ALC / GitOps | `knowledge/ui/applications.md` |
| Governance / Policies | `knowledge/ui/governance.md` |
| RBAC / FG-RBAC / Roles | `knowledge/ui/rbac.md` |
| Clusters / Infrastructure | `knowledge/ui/clusters.md` |
| Fleet Virtualization / VMs | `knowledge/ui/fleet-virt.md` |
| Search | `knowledge/ui/search.md` |
| Credentials | `knowledge/ui/credentials.md` |
| MTV / Migration | `knowledge/ui/mtv.md` |
| CCLM | `knowledge/ui/cclm.md` |

## ASK QUESTIONS FIRST

| Missing Input | Ask |
|---------------|-----|
| Test case source | "Path to the .md file, Polarion ID (RHACM4K-XXXXX), or paste content?" |
| Environment | "Console URL or cluster API? (I'll try `oc whoami --show-server` first)" |
| Credentials | "Login method? (kubeadmin, SSO/Keycloak user, or FG-RBAC test user)" |
| Execution mode | "Stop on first failure (fail-fast) or run all steps (full)? Default: full" |

If the user provides a file path and is already `oc login`-ed, proceed without asking further.

## MANDATORY: Phase Gate Enforcement

On skill start, create a TodoWrite with ALL phases:

```
TodoWrite (merge=false):
  tcv-phase-0  | Phase 0: Determine inputs and resolve test case source | pending
  tcv-phase-1  | Phase 1: Parse test case into executable steps          | pending
  tcv-phase-2  | Phase 2: Environment readiness check                    | pending
  tcv-phase-3  | Phase 3: Execute setup commands                         | pending
  tcv-phase-4  | Phase 4: Execute test steps (core loop)                 | pending
  tcv-phase-5  | Phase 5: Execute teardown                               | pending
  tcv-phase-6  | Phase 6: Generate validation report                     | pending
```

Gate rules:
1. A phase CANNOT be marked `completed` without executing it.
2. Phase 1 MUST complete before Phase 2 starts (parsed steps are input to readiness check).
3. Phase 2 produces a readiness table. If critical prerequisites are MISSING, mark Phase 3-5 as `cancelled` and skip to Phase 6 with BLOCKED verdict.
4. Phase 3 failure (setup command fails) prompts user: continue or abort.
5. Phase 4 runs INLINE (not as subagent) due to Playwright MCP limitation.
6. Phase 5 teardown failures are non-blocking for the overall verdict.
7. Phase 6 ALWAYS runs -- even if earlier phases were cancelled/blocked.

### Approval Gates

| Action | Gate |
|--------|------|
| oc get/describe/logs, browser read-only (navigate, snapshot) | No approval needed |
| oc apply/create/patch/delete (setup and teardown commands) | Show command, ask: "Run setup/teardown command?" |
| Playwright interactions (click, fill, hover) | No approval needed (test execution) |
| Writing report to `runs/` directory | No approval needed |

---

## Phase 0: Determine Inputs

### Step 1: Resolve test case source

Priority cascade:
1. **File path** provided by user -> Read the file directly
2. **Polarion ID** (matches `RHACM4K-\d+`) -> Fetch via `mcp__polarion__get_polarion_work_item` and `mcp__polarion__get_polarion_test_steps`
3. **Inline content** -> Parse directly from the prompt

If a file path is provided, verify it exists:
```bash
ls <path>
```

### Step 2: Resolve target environment

Priority cascade:
1. User-provided `--cluster-url` argument
2. Current `oc login` session:
```bash
oc whoami --show-server 2>/dev/null
oc whoami 2>/dev/null
```
3. Ask the user

### Step 3: Resolve credentials

For Playwright console login:
1. User-provided credentials (username/password)
2. Default kubeadmin: `oc get secret kubeadmin -n kube-system -o jsonpath='{.data.password}' 2>/dev/null | base64 -d`
3. Ask the user

### Step 4: Determine execution mode and teardown policy

- `--fail-fast`: Stop on first step failure (resources preserved for debugging)
- `--full` (default): Execute all steps regardless of failures
- `--always-teardown`: Force teardown even if steps fail (overrides conditional teardown)

Initialize the resource tracking registry:
```
CREATED_RESOURCES = []
```

### Step 5: Create run directory

```bash
POLARION_ID="<extracted-id>"
TIMESTAMP=$(date +%Y-%m-%dT%H-%M-%S)
RUN_DIR="runs/test-case-validator/${POLARION_ID}/${POLARION_ID}-${TIMESTAMP}"
mkdir -p "$RUN_DIR/evidence"
```

---

## Phase 1: Parse Test Case

Read `${CLAUDE_SKILL_DIR}/references/step-parser.md` for the full parsing specification.

Extract:
1. **Metadata**: Polarion ID, Area, Release version, Component
2. **Description**: Entry point, route
3. **Setup**: Ordered list of bash commands with expected output patterns
4. **Steps**: Array of `{ number, title, actions[], expected_results[], classification }` where classification is `UI_ACTION`, `CLI_ACTION`, or `HYBRID`
5. **Teardown**: Ordered list of cleanup bash commands

After parsing, present the execution plan to the user:

```
Parsed test case: RHACM4K-XXXXX ([area])
  Setup: N commands
  Steps: M test steps (X UI, Y CLI, Z hybrid)
  Teardown: K cleanup commands
  Entry point: [route]

Proceed with execution? (Y/n)
```

Wait for user confirmation before Phase 2.

---

## Phase 2: Environment Readiness

### Step 1: Verify cluster access

```bash
oc whoami --show-server
oc whoami
oc get mch -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.status.currentVersion}{"\n"}{end}'
```

### Step 2: Version compatibility check

Compare detected ACM version against test case `Release` metadata:
- Match -> proceed
- Mismatch -> warn: "Test case targets ACM [X] but cluster runs [Y]. Results may not be reliable. Continue?"

### Step 3: Prerequisite check

Parse the Setup section's prerequisites (text above the bash commands). For each prerequisite, run a targeted check:

**Hub vs Spoke distinction:** The cluster you are logged into is the **hub**. "Managed clusters" refers exclusively to **spoke clusters** (remote clusters registered with the hub). The hub itself (`local-cluster`) does NOT count as a managed/spoke cluster for prerequisite purposes. When a test case says "at least N managed clusters", it means N spoke clusters in Available state, excluding `local-cluster`.

| Prerequisite Pattern | Check Command | Counting Rule |
|---------------------|---------------|---------------|
| "ACM X.Y hub cluster" | `oc get mch` version check | The cluster you're on |
| "cluster-admin access" | `oc auth can-i '*' '*'` | On the hub |
| "multicluster-observability installed" | `oc get multiclusterobservability` | On the hub |
| "managed clusters" / "spoke clusters" | `oc get managedclusters` | Count only non-hub clusters (exclude `local-cluster`) |
| "at least N managed clusters" | `oc get managedclusters -o name \| grep -v local-cluster \| wc -l` | Spokes only |
| "CNV/MTV installed" | `oc get csv -A \| grep kubevirt` | On spoke(s) typically |
| "FG-RBAC enabled" | `oc get mch -o yaml \| grep enableFineGrainedRBAC` | On the hub |

### Step 4: Produce readiness table

```
ENVIRONMENT READINESS
=====================
Hub Cluster: https://api.hub.example.com:6443
ACM Version: 2.17.0 (matches test case: 2.17)
User: kube:admin

Prerequisites:
  cluster-admin access ........... PRESENT
  multicluster-observability ..... PRESENT
  spoke clusters (>=2) ........... PRESENT (2 spokes: cluster-1, cluster-2; excludes local-cluster)
  observability-controller addon . PRESENT

Verdict: READY (all prerequisites met)
```

**Reporting format for managed clusters:** Always list spoke names explicitly and note that `local-cluster` (the hub) is excluded from the count. Example: "2 spokes: ashafi-spoke-50, cluster-2 (local-cluster excluded)".

If any critical prerequisite is MISSING: set overall verdict to BLOCKED, skip to Phase 6.

---

## Phase 3: Execute Setup

### Step 1: Run setup bash commands

For each setup command from the parsed test case:
1. Show the command to the user
2. Ask: "Execute setup command N/M?" (if the command is state-changing: create, apply, patch, annotate)
3. Run the command
4. Compare output against the `# Expected:` comment
5. Record PASS/FAIL

### Step 2: Console login

After CLI setup, log into the ACM console via Playwright:

1. Derive console URL:
```bash
oc get route console -n openshift-console -o jsonpath='https://{.spec.host}'
```

2. Navigate and authenticate:
- `browser_navigate` to the console URL
- `browser_snapshot` to identify login form
- Fill credentials using `browser_fill`
- Submit and wait for dashboard

3. Navigate to ACM console:
- `browser_navigate` to the multicloud console URL (typically `/multicloud`)
- `browser_snapshot` to confirm landing page

Record: "Console login: PASS/FAIL"

---

## Phase 4: Execute Test Steps

Read `${CLAUDE_SKILL_DIR}/references/execution-patterns.md` for the full action-to-tool mapping.

This phase runs INLINE (not as a subagent) because Playwright MCP requires inline execution.

**Knowledge DB loading:** At the start of Phase 4, read `${SKILLS_DIR}/../knowledge/ui/<area>.md` for the test case's area. This provides route tables, component structure, and known UI patterns that help when the test case uses shorthand navigation or when elements are not immediately findable in snapshots. Do NOT use the knowledge DB to override or question the test case's expected results.

### Core loop

For each step `i` in `steps[0..N]`:

```
[Step i/N] <step_title>
```

#### 4.1 Pre-step snapshot

Before any action, capture the current state:
```
browser_snapshot -> save to evidence/step-{i}-pre-snapshot.txt
```

#### 4.2 Execute actions

For each numbered action in the step, classify and execute:

| Action Pattern | Tool | Execution |
|---------------|------|-----------|
| "Navigate to X > Y > Z" | `browser_navigate` + `browser_click` | Follow navigation path via sidebar/menu clicks |
| "Click on X" / "Click the X button" | `browser_click` | Find element ref in snapshot, click it |
| "Hover over X" | `browser_hover` | Find element ref, hover |
| "Fill/Enter X in Y field" | `browser_fill` | Find input ref, fill value |
| "Observe/View/Look at X" | `browser_snapshot` | Capture state, no interaction |
| "Refresh the page" | `browser_navigate` | Re-navigate to current URL |
| "`oc get ...`" or CLI command | `Bash` | Execute and capture output |
| "Sort by X" / "Click column header" | `browser_click` | Click the header element |
| "Open new tab" / "Verify new tab" | `browser_snapshot` | Check URL or page state |

Between each action, wait briefly (1-2s) then `browser_snapshot` to confirm the action took effect.

#### 4.3 Verify expected results

For each bullet in the Expected Result section:

| Expected Pattern | Verification Method |
|-----------------|-------------------|
| "X is displayed" / "X appears" | Search accessibility snapshot for text X |
| "N columns" / "N items" | Count matching elements in snapshot |
| "Column header reads X" | Find header element, compare text |
| "URL contains X" | Check current URL from snapshot metadata |
| "Sorted in ascending/descending order" | Capture column values, verify order |
| "Link opens to X" | Check navigation target |
| "No errors" / "No broken UI" | Check `browser_console_messages` for errors |
| CLI expected output | Pattern match against command output |
| "NOT present" / "NOT displayed" | Confirm absence in snapshot |

For each expected result: record PASS (confirmed), FAIL (contradicted), or MANUAL_CHECK (cannot programmatically verify).

#### 4.4 Pre-verdict checkpoint (MANDATORY)

Before assigning ANY step verdict, complete this checklist:

1. **Re-read** the exact expected result text from the test case (Polarion step HTML or markdown bullets). Quote it.
2. **Cite concrete evidence.** For UI verification: take a `browser_snapshot` and reference the snapshot content. For CLI verification: quote the command output. Never base a verdict on memory of what you saw -- cite the artifact.
3. **Compare literally.** For each expected result bullet, place the expected text next to the observed evidence. Does the evidence confirm or contradict the literal text?
4. **Check for injected assumptions.** Ask: "Am I failing this because the test case says it should fail, or because I THINK it should fail based on my own reasoning?" If the latter, stop and re-evaluate.

A verdict of FAIL requires a specific expected result bullet that is contradicted by concrete evidence. "I expected X based on how ArgoCD works" is not a valid FAIL reason -- only "the test case expected X and the evidence shows Y" is valid.

**Anti-assumption rule (applies to ALL verdict reasoning):**
- Do NOT inject domain knowledge about how a feature "should" behave when the test case provides specific verification criteria.
- Do NOT dismiss observed evidence based on metadata (resource age, labels, creation timestamp, suspected origin). If the test case asks "does resource X exist?" and the resource exists, that is confirmation.
- Do NOT add conditions the test case does not specify. If the test case does not require resources on a specific cluster, do not fail because one cluster lacks them.
- Do NOT qualify a PASS with "but..." reasoning. If evidence matches the expected result text, record PASS.

#### 4.5 Post-step evidence

After verifying all expected results:
```
browser_take_screenshot -> save to evidence/step-{i}-screenshot.png
browser_snapshot -> save to evidence/step-{i}-post-snapshot.txt
```

#### 4.6 Record step verdict

- **PASS**: All expected results confirmed
- **FAIL**: One or more expected results contradicted (with details)
- **MANUAL_CHECK**: One or more expected results could not be programmatically verified
- **BLOCKED**: Cannot execute actions (element not found, page error, timeout)

#### 4.7 Failure handling

- If `fail-fast` mode and verdict is FAIL or BLOCKED: skip remaining steps, proceed to Phase 5
- If `full` mode: continue to next step regardless

---

## Phase 5: Execute Teardown (Conditional)

**BEFORE running any teardown command**, evaluate the conditional teardown rules from the Safety Rules section.

### Step 1: Evaluate teardown eligibility

Compute the preliminary overall verdict from Phase 4 step results:
- If ALL steps PASS -> teardown ELIGIBLE
- If ANY step is FAIL or BLOCKED -> teardown SKIPPED (unless `--always-teardown` was passed)
- If `--always-teardown` flag was provided -> teardown ELIGIBLE regardless of verdict

### Step 2: If teardown is SKIPPED

1. Log: "Teardown SKIPPED -- resources preserved for debugging."
2. List all items in CREATED_RESOURCES registry with their origin phase
3. Generate manual cleanup commands for each item (with `--ignore-not-found`)
4. Include this in the Phase 6 report
5. Close browser session
6. Proceed to Phase 6

### Step 3: If teardown is ELIGIBLE

For each teardown command from the parsed test case:
1. Apply the 5-point delete safety check (Section 3 of Safety Rules)
2. If all checks pass: execute the command (with `--ignore-not-found` on deletes)
3. Record success/failure
4. Remove the resource from CREATED_RESOURCES registry on successful delete
5. Teardown failures are logged but do NOT affect the overall test verdict

After all teardown commands: if any items remain in CREATED_RESOURCES (created during steps but not covered by teardown), log them as "Orphaned test resources" with manual cleanup commands.

Close the browser session after teardown.

---

## Phase 6: Generate Report

Read `${CLAUDE_SKILL_DIR}/references/verdict-format.md` for the full report specification.

### Step 1: Compute overall verdict

| Condition | Overall Verdict |
|-----------|----------------|
| All steps PASS | `ALL_PASS` |
| Some steps PASS, some FAIL/MANUAL_CHECK | `PARTIAL_PASS (N/M steps passed)` |
| Critical prerequisite missing | `BLOCKED` |
| All/most steps FAIL | `FAILED` |

### Step 2: Generate report file

Write `validation-report.md` to the run directory with:
- Test case metadata
- Environment details
- Setup results
- Per-step verdict table with evidence references
- Teardown results
- Overall verdict
- Failure analysis (for each FAIL step: what was expected vs what was found)

### Step 3: Present summary to user

```
VALIDATION COMPLETE
===================
Test Case: RHACM4K-XXXXX - [Title]
Environment: https://console-openshift-console.apps.hub.example.com
ACM Version: 2.17.0

Results:
  Step 1: Verify GPU Column Appears ............. PASS
  Step 2: Verify GPU Count Values ............... PASS
  Step 3: Verify Tooltip Content ................ FAIL (tooltip text mismatch)
  Step 4: Verify Observability Link ............. BLOCKED (tooltip did not open)
  Step 5: Verify Numeric Sorting ................ PASS
  Step 6: Verify Second Cluster ................. PASS
  Step 7: Verify Without Launch-Link ............ MANUAL_CHECK

Overall: PARTIAL_PASS (5/7 steps)

Report: runs/test-case-validator/RHACM4K-XXXXX/RHACM4K-XXXXX-2026-06-23T14-30-00/validation-report.md
Evidence: runs/test-case-validator/RHACM4K-XXXXX/RHACM4K-XXXXX-2026-06-23T14-30-00/evidence/
```

---

## Safety Rules and Guardrails

These rules are MANDATORY and apply regardless of execution mode (`-p`, `--dangerously-skip-permissions`, or interactive). They are instruction-level constraints that the agent MUST follow -- they cannot be bypassed by CLI flags.

### 1. Resource Tracking Registry

Maintain a running list of every resource created during this validation run. Track immediately after each successful create/apply/UI-wizard-submit:

```
CREATED_RESOURCES = []
# After setup command creates a namespace:
CREATED_RESOURCES.append({ type: "namespace", name: "test-push-preserve", namespace: "-", cluster: "hub", created_in: "Phase 3, Setup cmd 4" })
# After UI wizard creates an ApplicationSet:
CREATED_RESOURCES.append({ type: "applicationset", name: "test-push-preserve", namespace: "openshift-gitops", cluster: "hub", created_in: "Phase 4, Step 2" })
```

This registry is the ONLY source of truth for what can be deleted during teardown.

### 2. Conditional Teardown (Verdict-Based)

| Overall Verdict | Teardown Behavior | Rationale |
|----------------|-------------------|-----------|
| `ALL_PASS` | Run full teardown | Test passed, safe to clean up |
| `PARTIAL_PASS` | **SKIP teardown** | Preserve state for debugging failed steps |
| `FAILED` | **SKIP teardown** | Preserve state for debugging |
| `BLOCKED` | **SKIP teardown** | Likely nothing was created, or state is uncertain |
| `SETUP_FAILED` | Teardown only what was successfully created | Partial cleanup of known-good creates |
| `--always-teardown` flag passed | Force full teardown regardless of verdict | User explicitly wants cleanup |

When teardown is SKIPPED, include in the report:

```
TEARDOWN SKIPPED -- resources preserved for debugging.

Created resources still on cluster:
  - namespace/test-push-preserve (hub, created in Phase 3)
  - placement/test-push-preserve-placement in openshift-gitops (hub, created in Phase 3)

Manual cleanup commands:
  oc delete ns test-push-preserve --ignore-not-found
  oc delete placement test-push-preserve-placement -n openshift-gitops --ignore-not-found
```

### 3. Delete Safety Checks (5-Point Verification)

Before ANY delete operation (CLI `oc delete` or UI "Delete" button click), ALL five checks must pass:

| # | Check | How | If Fails |
|:-:|-------|-----|----------|
| 1 | **Ownership** | Is the resource in CREATED_RESOURCES registry? | BLOCK the delete |
| 2 | **Scope** | Was it created during THIS run (not pre-existing)? | BLOCK the delete |
| 3 | **Cluster target** | Is the delete targeting the correct cluster (hub vs spoke)? | BLOCK the delete |
| 4 | **No cluster-wide** | Is this a targeted delete (not `--all`, not a wildcard)? | BLOCK the delete |
| 5 | **Log before execute** | Log: `[DESTRUCTIVE] Deleting {type}/{name} in {namespace} (created in {phase})` | N/A (always log) |

If ANY check fails: mark the step/teardown-command as BLOCKED, do NOT execute the delete, and report why.

### 4. Hard No-Go Rules (Non-Negotiable)

These resources must NEVER be deleted or modified, regardless of what the test case says:

**NEVER delete:**
- ClusterRoles / ClusterRoleBindings
- CustomResourceDefinitions (CRDs)
- Operators / CSVs / Subscriptions (OLM resources)
- MultiClusterHub (MCH)
- ManagedCluster resources
- Namespaces matching: `openshift-*`, `kube-*`, `open-cluster-management*`, `multicluster-engine`
- Any resource NOT in the CREATED_RESOURCES registry

**NEVER modify:**
- OAuth configuration (`config.openshift.io/OAuth`)
- Cluster-scoped secrets
- Node labels or taints
- Infrastructure / networking configuration

If a test case step requires any of the above: mark step as BLOCKED with reason "Safety rule: cannot delete/modify [resource type] -- classified as protected infrastructure."

### 5. UI Delete Gate

When a test step requires clicking a "Delete" / "Remove" / "Destroy" button in the UI:

1. Identify what resource the delete targets (from page context, heading, dialog text)
2. Check: is this resource in the CREATED_RESOURCES registry?
3. If YES and all 5-point checks pass: proceed with the click
4. If NO: BLOCKED -- "Refusing to delete pre-existing resource '{name}' via UI. Not in created resources registry."

Note: UI-based deletes that are PART of the test verification (e.g., "Delete the ApplicationSet and verify resources persist") are valid IF the resource was created during this run.

### 6. Scope-Lock on Resource Creation

- Only create resources that the test case Setup section explicitly specifies
- Never improvise additional resources beyond what the test case requires
- Never modify pre-existing resources (only interact with them read-only: click, view, verify)
- All created resources MUST be tracked in the CREATED_RESOURCES registry

### 7. General Safety (unchanged)

- **Read-only by default** -- `oc get`, `describe`, `logs`, browser navigation and snapshots need no approval
- **Never modify the test case** -- this skill reports findings, it does not fix the test case
- **Never modify JIRA or Polarion** -- read-only access to fetch test case content
- **Kubeconfig isolation** -- use session-specific KUBECONFIG path per workspace rules
- **Evidence preservation** -- all screenshots and snapshots saved to the run directory, never deleted

## Troubleshooting

| Symptom | Cause | What to Do |
|---------|-------|------------|
| Playwright login fails | Wrong IDP tab or form selectors | Snapshot the login page, identify correct form, retry |
| Element not found in snapshot | Page not fully loaded | Add `browser_wait_for` with 3-5s timeout, re-snapshot |
| Step BLOCKED on missing element | Feature not deployed or route changed | Check ACM version compatibility, verify route via `oc` |
| CLI command returns error | Missing permissions or resource | Check user role, verify namespace exists |
| Timeout on navigation | Slow cluster or redirect loop | Increase wait, check for OAuth redirect, snapshot state |
| All steps MANUAL_CHECK | Test case uses subjective language | Flag for human review -- skill cannot verify "looks correct" |

## Examples

```bash
# Validate a local test case file (simplest)
/acm-test-case-validator documentation/acm-components/virt/test-cases/2.17/RHACM4K-64019-GPU-Count-Column-Cluster-Nodes.md

# Validate by Polarion ID with explicit cluster
/acm-test-case-validator RHACM4K-64019 --cluster-url https://console-openshift-console.apps.bm12.example.com

# Fail-fast mode (stop on first failure, preserve resources)
/acm-test-case-validator RHACM4K-61726 --fail-fast

# Force teardown even if steps fail (override conditional teardown)
/acm-test-case-validator RHACM4K-61726 --always-teardown

# With specific credentials
/acm-test-case-validator RHACM4K-61726 --user kubeadmin --password <pw>
```
