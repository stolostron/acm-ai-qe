# Pipeline Phases

The test case generator runs a 7-step pipeline from JIRA ticket to Polarion-ready output. Two steps are deterministic Python scripts (Stage 1, Stage 3). Five steps are AI-driven (Phases 0-4.5). This document describes each step in execution order.

## Phase 0: Parse Inputs and Ask Questions

**Type:** Interactive (orchestrator)
**Duration:** ~10 seconds

The orchestrator checks if critical inputs are missing and asks the user before proceeding.

### Inputs Required

| Input | Source | Required? | Ask if missing? |
|-------|--------|-----------|----------------|
| JIRA ID | CLI arg | Always | Always |
| ACM version | JIRA `fix_versions` or `--version` | Yes | Yes, if not in JIRA |
| CNV version | CLI arg `--cnv-version` | Only for Fleet Virt | Yes |
| Cluster URL | CLI arg `--cluster-url` | No (skips Phase 3) | Yes (offer to skip) |
| Feature scope | JIRA ACs | Only if multiple ACs | Yes |

### Decision Logic

If `--version` not provided and not detectable from JIRA: prompt user.
If `--skip-live` not set and `--cluster-url` not provided: ask if user has a cluster or should skip.
If JIRA has multiple acceptance criteria with distinct flows: ask which to cover.

---

## Stage 1: Gather Data

**Type:** Deterministic Python script
**Script:** `src/scripts/gather.py`
**Duration:** ~2-5 seconds
**Output:** `gather-output.json`, `pr-diff.txt`

### What It Collects

| Step | Action | Tool | Output Field |
|------|--------|------|-------------|
| 1 | Search for PR by JIRA ID | `gh search prs` | `pr_data.number` |
| 2 | Fetch PR metadata | `gh pr view --json` | `pr_data` (title, files, additions, deletions) |
| 3 | Download full PR diff | `gh pr diff` | `pr-diff.txt` file |
| 4 | Auto-detect area from file paths | Python (path patterns) | `area` |
| 5 | Find existing peer test cases | Filesystem glob | `existing_test_cases` |
| 6 | Load conventions | Read `knowledge/conventions/test-case-format.md` | `conventions` |
| 7 | Load area knowledge | Read `knowledge/architecture/<area>.md` | `area_knowledge` |
| 8 | Load HTML templates | Read `knowledge/conventions/polarion-html-templates.md` | `html_templates` |

### Area Detection

The `detect_area_from_files()` function in `github_service.py` maps PR file paths to areas:

| Path Patterns | Detected Area |
|--------------|--------------|
| `Governance`, `governance`, `policy`, `Policy` | governance |
| `rbac`, `RBAC`, `RoleAssignment`, `ClusterPermission`, `user-management` | rbac |
| `Virtualization`, `virtualization`, `kubevirt`, `fleet-virt` | fleet-virt |
| `CCLM`, `cclm`, `LiveMigration`, `live-migration` | cclm |
| `MTV`, `mtv`, `forklift`, `migration-toolkit` | mtv |
| `Clusters`, `clusters`, `ClusterSet`, `ClusterDeployment`, `ClusterPool` | clusters |
| `Search`, `search` | search |
| `Applications`, `applications`, `Subscription`, `Channel` | applications |
| `Credentials`, `credentials` | credentials |

Detection uses a scoring system: each file path match increments the area's score, and the highest-scoring area wins. This handles PRs that touch files across multiple areas.

### Peer Test Case Discovery

The `find_existing_test_cases()` function in `file_service.py` searches three locations in priority order:

1. External automation workspace (opt-in via `$ACM_AUTOMATION_WORKSPACE` env var)
2. Previous pipeline runs (`runs/`)
3. Shipped sample (`knowledge/examples/sample-test-case.md`)

Returns up to 3 test cases matching the area and version.

### Output Schema

`gather-output.json` is a serialized `GatherOutput` Pydantic model:

```json
{
  "jira_id": "ACM-30459",
  "acm_version": "2.17",
  "area": "governance",
  "pr_data": {
    "number": 5790,
    "title": "...",
    "repo": "stolostron/console",
    "state": "MERGED",
    "files": ["frontend/src/routes/..."],
    "additions": 1238,
    "deletions": 16,
    "diff_file": "/path/to/pr-diff.txt"
  },
  "existing_test_cases": ["/path/to/peer1.md", "/path/to/peer2.md"],
  "conventions": "# Test Case Conventions\n...",
  "area_knowledge": "# Governance Area Knowledge\n...",
  "html_templates": "# Polarion HTML Templates\n...",
  "run_dir": "/path/to/runs/test-case-generator/ACM-30459/ACM-30459-2026-04-18T02-00-46",
  "options": {
    "skip_live": false,
    "cluster_url": null,
    "repo": "stolostron/console"
  },
  "test_files": ["frontend/src/routes/Governance/PolicyDetails.test.tsx"],
  "production_files": ["frontend/src/routes/Governance/PolicyDetails.tsx"]
}
```

### Telemetry

Stage 1 emits three events to `pipeline.log.jsonl`:

```
pipeline_start  {"jira_id": "ACM-30459"}
stage_start     {"stage": "gather"}
stage_end       {"stage": "gather", "elapsed_seconds": 1.72, "pr_found": true, "pr_number": 5790, "area": "governance", "existing_test_cases_count": 3, "conventions_loaded": true}
```

---

## Phase 1: Parallel Investigation

**Type:** AI (3 subagents launched simultaneously)
**Duration:** ~30-60 seconds total
**Agents:** feature-investigator, code-change-analyzer, ui-discovery

Three agents run in parallel. Each receives specific inputs from `gather-output.json` and returns a structured block. See [02-AGENTS.md](02-AGENTS.md) for detailed agent specifications.

**Artifact persistence:** Each agent's full output is saved to the run directory (`phase1-feature-investigation.md`, `phase1-code-change-analysis.md`, `phase1-ui-discovery.md`). Phase telemetry logged via `python -m src.scripts.log_phase <run-dir> phase_1 --agents 3`.

### Agent A: Feature Investigator

**Input:** JIRA ID
**MCP:** jira, polarion, neo4j-rhacm, bash (gh CLI)
**Output:** `FEATURE INVESTIGATION` block containing:
- Story summary, acceptance criteria, fix versions
- Comments with design decisions
- Linked tickets (parent epic, sibling stories)
- Existing Polarion coverage
- Test scenarios derived from ACs

### Agent B: Code Change Analyzer

**Input:** PR number, repo, ACM version
**MCP:** acm-source, neo4j-rhacm, bash (gh CLI)
**Output:** `CODE CHANGE ANALYSIS` block containing:
- Changed components (file-by-file)
- New UI elements (columns, fields, filters)
- UI interaction models (dropdown vs text input, PatternFly component types)
- Affected routes
- Discovered translations
- Test scenarios from code changes

### Agent C: UI Discovery

**Input:** ACM version, CNV version (if Fleet Virt), feature name, area, cluster URL (optional)
**MCP:** acm-source, neo4j-rhacm, playwright (conditional — only with cluster URL), bash (oc CLI for cluster auth)
**Output:** `UI DISCOVERY RESULTS` block containing:
- Translations (key → UI string)
- Routes (route name → path pattern)
- Selectors (component → CSS selector)
- Test IDs
- Component structure
- Live verification status (if cluster URL provided)

---

## Phase 2: Synthesize

**Type:** AI (orchestrator in main conversation)
**Duration:** ~10 seconds

The orchestrator merges all three Phase 1 outputs into a `SYNTHESIZED CONTEXT` block. This block becomes the primary input to Phase 4.

### Synthesis Steps

1. **Concatenate** all three investigation outputs verbatim
2. **Scope gate:** Extract target JIRA story's ACs and filter test scenarios to only those ACs
3. **AC vs Implementation cross-reference:** Compare each AC bullet against code behavior, flag discrepancies
4. **Write TEST PLAN:** Scenario count, step estimates, setup/teardown, CLI checkpoints
5. **Resolve conflicts:** If agents disagree:
   - UI elements: trust UI Discovery (reads source directly)
   - Business requirements: trust Feature Investigator (reads JIRA)
   - What changed: trust Code Change Analyzer (reads diff)

### Output Format

```
SYNTHESIZED CONTEXT
===================

--- FEATURE INVESTIGATION ---
[full output from feature-investigator]

--- CODE CHANGE ANALYSIS ---
[full output from code-change-analyzer]

--- UI DISCOVERY RESULTS ---
[full output from ui-discovery]

AC-IMPLEMENTATION DISCREPANCIES:
- AC: "[exact text]"
  Code: "[actual behavior]"
  Source: [file reference]

--- TEST PLAN ---
Scenarios: [N]
Steps: [estimated count]
Setup: [prerequisites]
Per-step validations: [what each step validates]
CLI checkpoints: [backend validation points]
Teardown: [cleanup plan]
```

---

## Phase 3: Live Validation (Conditional)

**Type:** AI (subagent)
**Duration:** ~2-5 minutes
**Condition:** Runs only when `--cluster-url` is provided and `--skip-live` is not set
**Agent:** live-validator

The live-validator agent opens the ACM console in a real browser, navigates to the feature, exercises the UI flow, and compares observed behavior against source code expectations.

### Tools Used

| Tool | Purpose |
|------|---------|
| Playwright MCP (24 tools) | Browser navigation, snapshot, click, fill, screenshot |
| oc CLI (via bash) | Verify cluster health, check backend resource state |
| ACM Search MCP (5 tools) | Query resources across managed clusters |
| ACM Kubectl MCP (3 tools) | Run kubectl on hub/spoke clusters |

### Process

1. Verify environment (oc whoami, mch health, managed clusters)
2. Navigate to feature entry point in browser
3. Walk through test steps (click, fill, observe)
4. Verify backend state after UI actions
5. Check for JavaScript errors and failed API calls
6. Document discrepancies between source code expectations and live behavior

### Output

```
LIVE VALIDATION RESULTS
=======================
Cluster: [hub name]
ACM Version: [version]

Feature Verification:
Step 1: [action]
  UI State: [observed]
  Backend: [oc get result]
  Match: [yes/no]

Discrepancies Found:
- [source says X, live shows Y]

Confirmed Behavior:
- [list of confirmed behaviors]
```

---

## Phase 4: Write Test Case

**Type:** AI (subagent)
**Duration:** ~30-60 seconds
**Agent:** test-case-generator

Produces the primary deliverable: a Polarion-ready test case markdown file.

### Process

1. Read conventions (`test-case-format.md`, `area-naming-patterns.md`, `cli-in-steps-rules.md`)
2. Read 2-3 peer test cases for format reference
3. Scope gate: plan steps that map to target JIRA story's ACs only
4. MCP spot-check: verify entry point route + key translations
5. Write `test-case.md` following exact convention structure
6. Write `analysis-results.json` with investigation metadata
7. Self-review before finalizing

### Output Files

**`test-case.md`** — Sections in order:
1. Title: `# RHACM4K-XXXXX - [Tag-Version] Area - Test Name`
2. Metadata: Polarion ID, Status, Created/Updated dates
3. Polarion Fields: Type, Level, Component, Subcomponent, Test Type, Pos/Neg, Importance, Automation, Tags, Release
4. Description: What is tested, verification list, Entry Point, Dev JIRA Coverage
5. Setup: Prerequisites, Test Environment, numbered bash commands
6. Test Steps: `### Step N: Title` with numbered actions, bullet expected results, `---` separators
7. Teardown: Cleanup commands with `--ignore-not-found`
8. Notes: Implementation details, AC discrepancies, code references

**`analysis-results.json`** — Audit metadata (not consumed downstream):
```json
{
  "jira_id": "ACM-30459",
  "steps_count": 8,
  "complexity": "medium",
  "routes_discovered": ["/multicloud/governance/discovered"],
  "translations_discovered": {"table.labels": "Labels"},
  "live_validation_performed": false
}
```

---

## Phase 4.5: Quality Review (Mandatory Gate)

**Type:** AI (subagent, 3-tier escalation)
**Duration:** ~30-60 seconds per iteration
**Agent:** quality-reviewer
**Recovery:** 3-tier escalation (targeted MCP re-investigation, focused retry with evidence, placeholder and proceed)

The quality reviewer validates the generated test case. If it returns `NEEDS_FIXES`, the orchestrator escalates through 3 tiers: targeted MCP re-investigation for factual errors, focused retry with evidence, then marking unresolvable steps with `[MANUAL VERIFICATION REQUIRED]` and proceeding. The pipeline does not abort.

### What It Checks

See [05-QUALITY-GATES.md](05-QUALITY-GATES.md) for the full checklist.

| Check | Type | What |
|-------|------|------|
| Title pattern | Blocking | `# RHACM4K-XXXXX - [Tag-Version] Area - Test Name` |
| Metadata completeness | Blocking | All Polarion fields present |
| Section order | Blocking | Title → Metadata → Fields → Description → Setup → Steps → Teardown |
| Step format | Blocking | H3 heading, numbered actions, bullet expected results |
| CLI-in-steps rule | Blocking | CLI only for backend validation, not as UI substitute |
| Entry point route | Blocking | Verified via acm-source MCP `get_routes()` |
| UI labels | Warning | Spot-checked via `search_translations()` |
| AC vs implementation | Blocking | Expected results consistent with JIRA ACs |
| Scope alignment | Blocking | Steps match target story, not broader PR |

---

## Stage 3: Generate Reports

**Type:** Deterministic Python script
**Script:** `src/scripts/report.py`
**Duration:** ~1 second
**Output:** `test-case-setup.html`, `test-case-steps.html`, `review-results.json`, `SUMMARY.txt`

### Process

1. Find the test case file in the run directory
2. Run structural validation via `convention_validator.py`
3. Generate Polarion HTML via `html_generator.py`
4. Write human-readable `SUMMARY.txt`
5. Log telemetry events

### Structural Validation

`convention_validator.py` checks (319 lines, 11 validation checks):

| Check | Severity | Pattern |
|-------|----------|---------|
| Title pattern | Blocking | `# RHACM4K-XXXXX - [Tag-Version] Area - Name` + area tag match |
| Metadata fields | Blocking | All 4 metadata lines present (Polarion ID, Status, Created, Updated) |
| Polarion fields | Blocking | All 10 `## Field: Value` lines present |
| Type field value | Warning | Must be "Test Case" |
| Test Steps header | Warning | `## Test Steps` section header required |
| Section order | Warning | Description before Setup before Test Steps before Teardown |
| Description present | Blocking | `## Description` section required |
| Entry point | Warning | `Entry Point` in Description |
| JIRA coverage | Warning | `Dev JIRA Coverage` in Description |
| Step format | Blocking | H3 heading + `Expected Result` per step + numbered actions + CLI check + separators |
| Teardown + Setup | Warning | `--ignore-not-found` on deletes, `# Expected:` on setup commands |

### Polarion HTML Generation

`html_generator.py` converts test case markdown to Polarion-compatible HTML:

- **Setup HTML:** Prerequisites, test environment, bash code blocks with inline styles
- **Steps HTML:** Two-column table (Step | Expected Result) matching Polarion's import format

Templates follow `knowledge/conventions/polarion-html-templates.md` exactly:
- `contenteditable="false"` and `id` attributes on table headers
- `background-color:#F0F0F0` for header cells
- Base span style: `font-size:11pt;font-family:Arial,Helvetica,sans-serif;color:#000000;line-height:1.5`
- Bold via `<span style="font-weight:bold;">`, not `<b>`
- `&amp;&amp;` for `&&`, `<br>` for line breaks

### Telemetry

Stage 3 emits events to `pipeline.log.jsonl`:

```
stage_start     {"stage": "report"}
stage_end       {"stage": "report", "verdict": "PASS", "total_steps": 8, "blocking_issues": 0, "warnings": 0, "html_generated": true}
pipeline_end    {"total_elapsed_seconds": 0.5, "verdict": "PASS"}
```
