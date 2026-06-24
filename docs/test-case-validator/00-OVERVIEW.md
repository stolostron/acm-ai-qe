# ACM Test Case Validator Overview

Executes existing ACM Console UI test cases step-by-step against a live environment, producing a per-step pass/fail report with evidence (screenshots, accessibility snapshots, CLI output). Takes a test case markdown file, Polarion ID, or inline content as input. Does not generate or modify test cases -- only validates them.

## Architecture

```
                 ┌─────────────────────────────────────┐
                 │         Claude Code (main)           │
                 │  Orchestrator: /acm-test-case-       │
                 │  validator skill                     │
                 └────────────┬────────────────────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 0      │
                     │  Parse Inputs   │
                     │  (orchestrator) │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 1      │
                     │  Parse Test     │
                     │  Case (inline)  │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 2      │
                     │  Environment    │
                     │  Readiness      │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 3      │
                     │  Execute Setup  │
                     │  (oc + browser) │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 4      │
                     │  Execute Steps  │
                     │  (INLINE loop)  │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 5      │
                     │  Conditional    │
                     │  Teardown       │
                     └────────┬────────┘
                              │
                     ┌────────▼────────┐
                     │    Phase 6      │
                     │  Generate       │
                     │  Report         │
                     └─────────────────┘
```

## Pipeline Phases

7 phases (0-6): All run inline in the main orchestrator context (no subagents). Phase 4 is the core execution loop where test steps are performed against the live UI via Playwright MCP and CLI via shell.

| Phase | Type | Duration | Input | Output |
|:-----:|------|----------|-------|--------|
| 0 | Interactive | ~5 sec | User args (file path, cluster URL, creds) | Resolved inputs, run directory |
| 1 | Deterministic | ~3 sec | Test case markdown | Parsed execution plan (steps, actions, expected results) |
| 2 | CLI check | ~10 sec | Parsed prerequisites | Readiness table (READY / BLOCKED) |
| 3 | CLI + Browser | ~30-60 sec | Setup commands, console URL | Setup results, browser session |
| 4 | Browser + CLI | ~2-15 min | Parsed steps (N steps) | Per-step verdicts with evidence |
| 5 | Conditional CLI | ~10-30 sec | Verdict + teardown commands | Cleanup results (or SKIPPED) |
| 6 | Write | ~5 sec | All phase outputs | `validation-report.md` + evidence/ |

**Total duration:** 3-20 minutes depending on test case complexity (number of steps, live cluster response times, wait periods).

## Key Differences from Test Case Generator

| Aspect | Generator | Validator |
|--------|-----------|-----------|
| Input | JIRA ticket | Existing test case (markdown / Polarion) |
| Output | Test case document | Pass/fail report + evidence |
| Subagents | 7 parallel/sequential | None (all inline) |
| Modifies cluster? | No | Yes (setup/teardown, with approval) |
| Browser usage | Investigation only | Full step execution |
| MCP dependency | 7 MCP servers | 2 required (Playwright, oc), 2 optional |
| Context source | JIRA + PRs + source code | The test case itself + knowledge DB fallback |

## MCP and Tool Requirements

| MCP / Tool | Role | Required? |
|------------|------|-----------|
| `playwright` | All UI actions: navigate, click, fill, hover, snapshot, screenshot | Required |
| `oc` CLI | Setup commands, mid-step backend checks, teardown, environment detection | Required |
| `polarion` | Fetch test case by Polarion ID (alternative to file path) | Optional |
| `acm-kubectl` | Spoke cluster checks if steps reference managed clusters | Optional |
| `acm-search` | Resource existence verification | Optional |

## Input Formats

| Format | Example | Resolution |
|--------|---------|------------|
| File path | `documentation/.../RHACM4K-64019-GPU-Count.md` | Read directly |
| Polarion ID | `RHACM4K-64019` | Fetch via Polarion MCP (`get_polarion_work_item` + `get_polarion_test_steps`) |
| Inline content | Pasted markdown in prompt | Parse directly |

## Verdict Discipline (Phase 4.4)

Phase 4 includes a mandatory pre-verdict checkpoint that prevents the agent from injecting assumptions into verdict evaluation. Before assigning any step verdict, the agent must:

1. **Re-read** the exact expected result text from the test case and quote it
2. **Cite concrete evidence** -- browser snapshot for UI, command output for CLI (never from memory)
3. **Compare literally** -- place expected text next to observed evidence
4. **Check for injected assumptions** -- distinguish "the test case says FAIL" from "I think it should fail"

Anti-assumption rules enforce that the agent does not dismiss evidence based on metadata (resource age, labels, creation source), does not add conditions the test case does not specify, and does not inject domain knowledge about how a feature "should" behave. The test case text is the sole authority for what constitutes PASS or FAIL.

The same general method applies to all verification patterns (see `references/execution-patterns.md`): identify what the test case literally asks, gather concrete evidence, compare, do not filter evidence, do not stop at the first negative.

## Verdict System

### Per-Step Verdicts

| Verdict | Meaning | When |
|---------|---------|------|
| PASS | All expected results confirmed | Evidence matches every bullet in Expected Result |
| FAIL | Expected result contradicted | Evidence shows different state than expected |
| BLOCKED | Cannot execute | Element not found, page error, timeout after retries |
| MANUAL_CHECK | Cannot verify programmatically | Subjective language ("looks correct"), no baseline |

### Overall Verdicts

| Verdict | Condition |
|---------|-----------|
| `ALL_PASS` | Every step is PASS |
| `ALL_PASS_WITH_MANUAL` | All PASS or MANUAL_CHECK, no FAIL/BLOCKED |
| `PARTIAL_PASS` | Mix of PASS and FAIL (includes count: "N/M steps passed") |
| `BLOCKED` | Environment prerequisites missing |
| `FAILED` | All or most steps FAIL/BLOCKED |
| `SETUP_FAILED` | Setup commands failed critically |

## Run Directory Layout

Each validation run produces artifacts under `runs/test-case-validator/<ID>/<ID>-<timestamp>/`:

```
runs/test-case-validator/RHACM4K-64825/RHACM4K-64825-2026-06-23T14-48-40/
  validation-report.md          # Primary deliverable: full report
  execution-plan.json           # Parsed test case structure (Phase 1)
  environment-readiness.md      # Phase 2 readiness table
  evidence/
    step-1-pre-snapshot.txt     # Accessibility snapshot before step 1
    step-1-post-snapshot.txt    # Accessibility snapshot after step 1
    step-1-screenshot.png       # Visual screenshot after step 1
    step-2-pre-snapshot.txt
    step-2-post-snapshot.txt
    step-2-screenshot.png
    ...
    setup-output.txt            # Combined setup command outputs
    teardown-output.txt         # Combined teardown command outputs
    console-errors.txt          # Browser console errors (if any)
```

## Invocation

```bash
# From repo root -- interactive (see live progress)
cd ~/Documents/work/ai/ai_systems_v2_2
claude
/acm-test-case-validator RHACM4K-64825 --cluster-url https://console.apps.hub.example.com --password <pw>

# From repo root -- non-interactive (outputs final result)
claude -p "/acm-test-case-validator path/to/test-case.md"

# With explicit cluster (already oc-logged-in)
oc login https://api.hub:6443 -u kubeadmin -p <pw>
claude -p "/acm-test-case-validator RHACM4K-64019"

# Fail-fast mode (stop on first failure, preserve resources for debugging)
claude -p "/acm-test-case-validator RHACM4K-61726 --fail-fast"

# Force teardown even on failure (override conditional teardown)
claude -p "/acm-test-case-validator RHACM4K-61726 --always-teardown"
```

## Skill Pack Structure

```
.claude/skills/acm-test-case-validator/
├── SKILL.md                         # Orchestrator: phases 0-6, safety rules
└── references/
    ├── step-parser.md               # Phase 1: markdown parsing, action classification
    ├── execution-patterns.md        # Phase 4: action-to-tool mapping, verification methods
    └── verdict-format.md            # Phase 6: report format, evidence structure, run layout
```

## Knowledge DB Integration

The skill uses the shared knowledge database at `.claude/knowledge/` as a **read-only fallback** for filling execution gaps:

| Gap | Knowledge Source |
|-----|-----------------|
| Test case says "Navigate to X" but no route | `knowledge/ui/<area>.md` (routes table) |
| Button/element not found in snapshot | `knowledge/ui/<area>.md` (testing considerations) |
| CLI step references unfamiliar CRD | `knowledge/architecture/<subsystem>/` |
| Need to understand spoke vs hub context | `knowledge/architecture/cluster-lifecycle/` |

The test case is always the primary source of truth. Knowledge DB only helps with *how* to navigate there, never overrides *what* to verify.

## Safety and Guardrails

The skill enforces mandatory safety rules that cannot be bypassed by CLI flags (`-p`, `--dangerously-skip-permissions`). These are instruction-level constraints embedded in the skill.

### Resource Tracking Registry

Every resource created during a run is tracked in a `CREATED_RESOURCES` list. Only resources in this list can be deleted during teardown.

### Conditional Teardown

| Verdict | Teardown Behavior |
|---------|-------------------|
| `ALL_PASS` | Run full teardown |
| `PARTIAL_PASS` / `FAILED` / `BLOCKED` | Skip teardown, preserve resources for debugging |
| `--always-teardown` flag | Force teardown regardless of verdict |

When teardown is skipped, the report lists all created resources with manual cleanup commands.

### 5-Point Delete Safety Checks

Every delete (CLI or UI) must pass all five checks before executing:

1. **Ownership** -- resource is in the CREATED_RESOURCES registry
2. **Scope** -- resource was created during THIS run
3. **Cluster target** -- delete targets the correct cluster
4. **No cluster-wide** -- targeted delete, no wildcards or `--all`
5. **Log before execute** -- mandatory `[DESTRUCTIVE]` log entry

### Hard No-Go Rules

These are NEVER deleted or modified: ClusterRoles, CRDs, Operators/CSVs, MCH, ManagedCluster resources, system namespaces (`openshift-*`, `kube-*`, `open-cluster-management*`), OAuth config, node labels/taints.

### UI Delete Gate

UI "Delete" button clicks require verifying the target resource is in the CREATED_RESOURCES registry before proceeding. Pre-existing resources are never deleted via UI.

## Detailed Documentation

| Document | Description |
|----------|-------------|
| [01-PIPELINE-PHASES.md](01-PIPELINE-PHASES.md) | Phase-by-phase execution detail (Phases 0-6) |
| [02-EXECUTION-ENGINE.md](02-EXECUTION-ENGINE.md) | Action classification, tool mapping, verification patterns |
| [03-EVIDENCE-AND-REPORTING.md](03-EVIDENCE-AND-REPORTING.md) | Evidence capture, verdict rules, report format |
