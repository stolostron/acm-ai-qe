# Pipeline Phases

The test case validator runs a 7-phase pipeline (Phases 0-6) from test case input to validation report. All phases run inline in the main orchestrator context -- no subagents are spawned. Phase 4 is the core execution loop where Playwright MCP drives the browser step-by-step.

## Phase 0: Parse Inputs

**Type:** Interactive (orchestrator)
**Duration:** ~5 seconds

Resolves all inputs needed for execution.

### Input Resolution

| Input | Source | Required? | Resolution Priority |
|-------|--------|-----------|---------------------|
| Test case source | CLI arg (path, Polarion ID, or inline) | Always | 1. File path, 2. Polarion ID fetch, 3. Inline parse |
| Cluster URL | CLI arg `--cluster-url` or `oc whoami` | Yes | 1. Explicit arg, 2. Auto-detect from `oc login`, 3. Ask |
| Credentials | CLI `--user`/`--password` or cluster secret | Yes (for browser) | 1. Explicit args, 2. kubeadmin secret extraction, 3. Ask |
| Execution mode | CLI `--fail-fast` or `--full` | No (default: full) | Default: execute all steps regardless of failures |

### Run Directory Creation

```bash
POLARION_ID="RHACM4K-64019"
TIMESTAMP=$(date +%Y-%m-%dT%H-%M-%S)
RUN_DIR="runs/test-case-validator/${POLARION_ID}/${POLARION_ID}-${TIMESTAMP}"
mkdir -p "$RUN_DIR/evidence"
```

---

## Phase 1: Parse Test Case

**Type:** Deterministic (inline)
**Duration:** ~3 seconds
**Reference:** `references/step-parser.md`

Parses the test case markdown into a structured execution plan.

### Extraction Targets

| Section | Extracted As | Used In |
|---------|-------------|---------|
| Title + Metadata | Polarion ID, area, release, component | Phase 2 (version check), Phase 6 (report header) |
| Description | Entry point route, navigation path | Phase 4 (initial navigation) |
| Prerequisites | Array of prerequisite objects | Phase 2 (readiness check) |
| Setup Commands | Ordered bash commands with expected patterns | Phase 3 (setup execution) |
| Test Steps | `[{ number, title, actions[], expected_results[], classification }]` | Phase 4 (core loop) |
| Teardown | Ordered cleanup commands | Phase 5 (teardown) |

### Action Classification

Each action in a test step is classified to determine which tool executes it:

| Classification | Tools Used | Examples |
|---------------|-----------|----------|
| `UI_ACTION` | Playwright MCP (navigate, click, fill, hover, snapshot) | "Click the Nodes tab", "Navigate to Infrastructure > Clusters" |
| `CLI_ACTION` | Bash shell (`oc`, `kubectl`) | "Run: `oc get pods`", embedded ```bash blocks |
| `HYBRID` | Both Playwright + Bash | Steps mixing UI observation with CLI verification |

### User Confirmation Gate

After parsing, the execution plan is presented:

```
Parsed test case: RHACM4K-64019 (Clusters)
  Setup: 6 commands
  Steps: 7 test steps (5 UI, 1 CLI, 1 hybrid)
  Teardown: 2 cleanup commands
  Entry point: /multicloud/infrastructure/clusters/details/:ns/:name/nodes

Proceed with execution? (Y/n)
```

Pipeline waits for user confirmation before Phase 2.

---

## Phase 2: Environment Readiness

**Type:** CLI check (inline)
**Duration:** ~10 seconds

Verifies the target cluster can support the test case.

### Checks Performed

| Check | Command | Gate |
|-------|---------|------|
| Cluster connectivity | `oc whoami --show-server` | Hard block if fails |
| User identity | `oc whoami` | Informational |
| ACM version | `oc get mch -A -o jsonpath='{...}'` | Warn if mismatch with test case Release |
| Cluster-admin access | `oc auth can-i '*' '*'` | Depends on test case user requirement |
| Per-prerequisite | Varies (see prerequisite check table in SKILL.md) | Hard block if critical missing |

### Hub vs Spoke Distinction

"Managed clusters" in prerequisites refers exclusively to spoke clusters. The hub (`local-cluster`) is excluded from counts:

```bash
oc get managedclusters -o name | grep -v local-cluster | wc -l
```

### Readiness Verdict

| All prerequisites PRESENT | -> READY, proceed to Phase 3 |
| Critical prerequisite MISSING | -> BLOCKED, skip to Phase 6 |
| Non-critical MISSING | -> READY with warning, proceed |

---

## Phase 3: Execute Setup

**Type:** CLI + Browser (inline)
**Duration:** ~30-60 seconds

### Part A: CLI Setup

For each setup command from the parsed test case:

1. Display the command to the user
2. If state-changing (`oc apply`, `create`, `patch`, `annotate`, `delete`): ask "Execute? (Y/n)"
3. Execute the command
4. Compare output against `# Expected:` pattern
5. Record PASS/FAIL

Variable assignments (e.g., `GRAFANA_LINK=$(...)`) are preserved across the session for teardown.

### Part B: Console Login

```
1. Derive console URL: oc get route console -n openshift-console
2. browser_navigate to console URL
3. browser_snapshot to identify login form
4. browser_fill credentials (kubeadmin or specified user)
5. Submit form, wait for dashboard
6. browser_navigate to ACM multicloud URL
7. browser_snapshot to confirm landing page
```

OAuth form patterns follow the same approach as `verify-bug-fix` Phase 3 (Keycloak IDPs, htpasswd forms, OIDC redirects).

### Failure Handling

- CLI setup failure: ask user "Continue or abort?"
- Console login failure: retry once with different IDP detection; if still fails, BLOCKED

---

## Phase 4: Execute Test Steps (Core Loop)

**Type:** Browser + CLI (inline, NOT subagent)
**Duration:** ~2-15 minutes (depends on step count and wait periods)
**Reference:** `references/execution-patterns.md`

This is the core value of the skill. Each test step is executed sequentially against the live environment.

### Execution Flow Per Step

```
┌──────────────────────────────────────────────────────┐
│ Step i/N: <title>                                    │
├──────────────────────────────────────────────────────┤
│ 4.1 Pre-step snapshot                                │
│   browser_snapshot -> evidence/step-{i}-pre.txt      │
├──────────────────────────────────────────────────────┤
│ 4.2 Execute actions                                  │
│   For each numbered action:                          │
│     Classify (UI/CLI/Hybrid) -> select tool          │
│     Execute (click/navigate/fill/oc)                 │
│     Wait 1-2s                                        │
│     Confirm action via snapshot                      │
├──────────────────────────────────────────────────────┤
│ 4.3 Verify expected results                          │
│   For each bullet in Expected Result:                │
│     Apply verification method (text search, count,   │
│     sort check, URL check, absence check)            │
│     Record: PASS / FAIL / MANUAL_CHECK               │
├──────────────────────────────────────────────────────┤
│ 4.4 Pre-verdict checkpoint (MANDATORY)               │
│   Re-read expected result text, cite evidence,       │
│   compare literally, check for injected assumptions  │
├──────────────────────────────────────────────────────┤
│ 4.5 Post-step evidence                               │
│   browser_take_screenshot -> evidence/step-{i}.png   │
│   browser_snapshot -> evidence/step-{i}-post.txt     │
├──────────────────────────────────────────────────────┤
│ 4.6 Record step verdict                              │
│   PASS | FAIL (details) | BLOCKED | MANUAL_CHECK     │
├──────────────────────────────────────────────────────┤
│ 4.7 Failure handling                                 │
│   fail-fast: stop here, go to Phase 5                │
│   full: continue to step i+1                         │
└──────────────────────────────────────────────────────┘
```

### Knowledge DB Fallback

At Phase 4 start, the area's knowledge file (`knowledge/ui/<area>.md`) is loaded for route tables and UI patterns. This helps when:
- The test case says "Navigate to Applications" without a route
- An element is not immediately findable (knowledge file may describe known UI structure)
- A CRD or concept needs context for CLI verification

The knowledge DB never overrides what the test case says to verify.

---

## Phase 5: Conditional Teardown

**Type:** Conditional CLI (inline)
**Duration:** ~10-30 seconds (or 0 seconds if skipped)

Teardown is **conditional** based on the test verdict. This preserves cluster state for debugging when steps fail.

### Teardown Decision

```
Compute preliminary verdict from Phase 4 step results:

  ALL steps PASS?
    → YES: teardown ELIGIBLE (run cleanup)
    → NO: teardown SKIPPED (preserve resources)

  --always-teardown flag passed?
    → YES: override to ELIGIBLE regardless of verdict
```

### When Teardown is SKIPPED

1. Log: "Teardown SKIPPED -- resources preserved for debugging."
2. List all items from the CREATED_RESOURCES registry
3. Generate manual cleanup commands for each (with `--ignore-not-found`)
4. Include in Phase 6 report
5. Close browser session

### When Teardown is ELIGIBLE

For each teardown command:

1. Apply the 5-point delete safety check:
   - Ownership (in registry?), Scope (this run?), Cluster target correct?, No wildcards?, Log before execute
2. If all checks pass: execute with `--ignore-not-found`
3. Record success/failure
4. Remove from CREATED_RESOURCES registry on success
5. If items remain in registry after all teardown commands: report as "Orphaned test resources"

Teardown failures are logged but do NOT affect the overall test verdict.

Variable references from Phase 3 setup (e.g., `$GRAFANA_LINK`) are available for restoration commands.

Close browser session after teardown.

---

## Phase 6: Generate Report

**Type:** Write (inline)
**Duration:** ~5 seconds
**Reference:** `references/verdict-format.md`

### Step 1: Compute Overall Verdict

Apply verdict rules based on individual step results.

### Step 2: Write Report

Generate `validation-report.md` with:
- Test case metadata
- Environment details (cluster, ACM version, user)
- Prerequisites readiness table
- Setup results table
- Per-step verdict table with evidence file references
- Failure details (for each FAIL: expected vs actual)
- Teardown results
- Overall verdict
- Recommendations (suggested fixes for failed steps)

### Step 3: Present Summary

Display a condensed verdict table to the user in the terminal.
