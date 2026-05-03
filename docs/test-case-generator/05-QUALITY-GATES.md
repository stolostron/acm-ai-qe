# Quality Gates

The pipeline has two independent validation systems. Both must pass before a test case is considered complete. Phase 4.5 validates semantic correctness (are the right things tested?). Stage 3 validates structural correctness (is the format right?).

## Validation Layers

| Layer | When | Type | What it checks | Authoritative for |
|-------|------|------|---------------|-------------------|
| Phase 4.5 | Before Stage 3 | AI (quality-reviewer agent) | MCP verification of UI elements, Polarion coverage, peer consistency, discovered vs assumed, AC vs implementation | Semantic correctness |
| Stage 3 | After Phase 4.5 | Deterministic (`convention_validator.py`) | Title pattern, metadata fields, section order, step format, entry point, teardown | Structural correctness |

---

## Phase 4.5: Quality Reviewer Agent

**Agent:** `.claude/agents/quality-reviewer.md`
**Tools:** acm-ui, polarion
**Verdict:** `PASS` or `NEEDS_FIXES`
**Recovery:** 3-tier escalation -- targeted MCP re-investigation, focused retry with evidence, placeholder and proceed (pipeline does not abort)

### Review Checklist

#### Step 3: Structural Validation

| Check | Severity | Pattern |
|-------|----------|---------|
| Title format | Blocking | `# RHACM4K-XXXXX - [Tag-Version] Area - Test Name` |
| Title tag matches area | Warning | `[GRC-X.XX]` for governance, `[FG-RBAC-X.XX]` for RBAC, etc. |
| Polarion ID format | Blocking | `RHACM4K-XXXXX` (placeholder acceptable for new) |
| Status set | Blocking | `Draft` or `proposed` |
| Created/Updated dates | Blocking | `YYYY-MM-DD` format |
| All Polarion fields | Blocking | 10 fields: Type, Level, Component, Subcomponent, Test Type, Pos/Neg, Importance, Automation, Tags, Release |
| Release matches version | Blocking | Release field = ACM version from JIRA |
| Tags relevant to area | Warning | `ui`, area-specific tags |
| Description complete | Blocking | Clear explanation, numbered verification list |
| Entry Point present | Blocking | `**Entry Point:**` with route |
| JIRA Coverage listed | Blocking | `**Dev JIRA Coverage:**` with primary ticket |
| Setup prerequisites | Warning | ACM version, access level, required features |
| Setup commands numbered | Warning | Numbered bash steps with `# Expected:` |
| Step heading format | Blocking | `### Step N: Title` |
| Step actions numbered | Blocking | `1. Action` format |
| Step expected results | Blocking | `**Expected Result:**` with bullet items |
| Steps separated by `---` | Blocking | Horizontal rule between steps |
| CLI-in-steps rule | Blocking | CLI only for backend validation |
| Teardown present | Warning | Cleanup section exists |
| `--ignore-not-found` on deletes | Warning | Idempotent cleanup |

#### Step 4: Discovered vs Assumed (MCP Verification)

The reviewer performs **minimum 3 MCP verifications**. Fewer than 3 = automatic `NEEDS_FIXES`.

1. `set_acm_version(<version>)` on acm-ui
2. Check UI labels via `search_translations` — verify they match test case
3. Check entry point via `get_routes` — verify navigation path exists
4. If wizard steps mentioned: verify via `get_wizard_steps`
5. **MANDATORY: Read primary changed component** via `get_component_source()` — verify at least one behavioral claim (field order, filtering, empty state) against actual source code
6. Flag any unverifiable element as `POTENTIALLY ASSUMED`

#### Step 4.5: AC vs Implementation Check

If the test case targets a specific JIRA story:

1. Extract JIRA story's Acceptance Criteria
2. For each AC bullet, check if test expected results are consistent
3. If AC says behavior X but test expects behavior Y:
   - Check if a Note explains the discrepancy (citing source code)
   - If Note exists: verify the cited behavior is accurate via `get_component_source()`
   - If no Note: flag as BLOCKING
4. Check test scope matches target story, not broader PR
   - Flag out-of-scope steps as BLOCKING

#### Step 4.6: Knowledge File Cross-Reference

Read `knowledge/architecture/<area>.md` and verify:
1. Field order claims match the knowledge file
2. Filtering behavior claims match the knowledge file
3. Component names and CRD references are consistent
4. Flag contradictions as BLOCKING

#### Step 4.7: Design Efficiency Check

Checks for anti-patterns that indicate suboptimal test design. All issues flagged as WARNING:

| Anti-Pattern Category | What to Check |
|----------------------|---------------|
| Resource optimization | Two resources testing presence/absence of same property (should be one entity with before/after state). Setup creates resources no step consumes. More resources than needed. |
| Entry point selection | Entry point from JIRA hierarchy instead of shortest click path from console side panel. Entry point requires unnecessary resource creation. |
| Prerequisite completeness | Missing managed clusters, RBAC permissions, credentials, CLI access, or any environmental dependency a tester needs but cannot infer from Setup. |
| Step design | Steps mixing observation with interaction. Duplicate verifications of same behavior in same context. Setup/step ratio imbalance. |

#### Step 4.8: Coverage Gap Verification

If the synthesized context includes a Coverage Gap Triage section:

1. For each gap triaged as `ADD TO TEST PLAN`: verify a corresponding test step exists
2. For each gap triaged as `NOTE ONLY`: verify it's mentioned in the Notes section
3. Flag missing coverage as WARNING

#### Step 5: Polarion Coverage Check

Search for duplicate test cases via Polarion MCP:

```
get_polarion_work_items(project_id="RHACM4K", query='type:testcase AND title:"<feature>"')
```

Reports existing similar test cases and potential duplication.

#### Step 6: Peer Consistency Check

Reads 2-3 existing test cases from the same area and compares:
- Section structure and formatting
- Level of detail in expected results
- Setup section format
- Teardown approach

---

### Error Handling and Graceful Degradation

Every agent in the pipeline can encounter MCP failures, missing data, or unavailable services. The pipeline never aborts on tool failures -- it degrades gracefully.

**Agent-level handling:**
- All 6 agents include an `anomalies` array in their output for surfacing data quality issues
- Missing MCP results: note in anomalies, proceed with available data
- MCP timeout or error: skip that verification, flag in anomalies
- Missing JIRA ACs: investigate from PR description and comments instead
- Empty Polarion results: note "no existing coverage found", proceed

**Pipeline-level handling:**
- Phase 1 agent failure: pipeline continues with remaining agents' data
- Live validation skip: synthesis proceeds without live data, notes limitation
- Quality reviewer NEEDS_FIXES: 3-tier escalation (never aborts):
  - Tier 1: targeted MCP re-investigation for factual errors
  - Tier 2: focused retry with accumulated evidence
  - Tier 3: mark unresolvable with `[MANUAL VERIFICATION REQUIRED]`, proceed
- Stage 3 failure after Phase 8 pass: fix structural issue, re-run `report.py` only

**Anomaly reporting format** (all agents):

```json
{
  "anomalies": [
    "acm-ui search_translations returned empty for 'PolicyReport' -- using PR diff label instead",
    "Polarion MCP unavailable -- skipping coverage check"
  ]
}
```

---

### Failure State: Tier 3 Partial Pass

When quality review escalates to Tier 3, unresolvable steps are marked and the pipeline proceeds:

**Test step with manual verification flag:**

```markdown
### Step 4: Verify filter displays only non-compliant clusters

1. Click the "Non-compliant" count in the violation summary card
2. Observe the Clusters tab filters to show non-compliant clusters only

**Expected Result:**
- [MANUAL VERIFICATION REQUIRED: filter condition could not be verified via MCP -- acm-ui search_translations returned no match for "Non-compliant" label. Verify the exact label text on a cluster running this build.]
- Only clusters with violations are displayed
```

The summary reports which steps were flagged:

```
Quality review: 1 step flagged for manual verification.
- Step 4: filter label text unverifiable via MCP
```

---

## Stage 3: Structural Validator

Stage 3 processes test cases regardless of manual verification flags. `[MANUAL VERIFICATION REQUIRED]` markers pass through to the Polarion HTML output unchanged. The `SUMMARY.txt` includes a count of flagged steps when present.

**Script:** `src/services/convention_validator.py`
**Input:** `test-case.md` file path, optional area
**Output:** `ReviewResult` model (written to `review-results.json`)

### Validation Rules

The validator (`validate_test_case()`, 319 lines) applies 11 structural checks across 7 categories:

#### 1. Title Pattern

```python
TITLE_PATTERN = re.compile(r"^# RHACM4K-\d+ - \[.+\] .+ - .+$|^# RHACM4K-XXXXX - \[.+\] .+ - .+$")
```

Checks that the H1 title matches the convention pattern. Placeholder `XXXXX` is accepted for new test cases.

If an `area` is provided, also checks the tag pattern against `AREA_TAG_PATTERNS` (all 9 areas):

| Area | Expected Tag |
|------|-------------|
| governance | `[GRC-` |
| rbac | `[FG-RBAC-` |
| fleet-virt | `[FG-RBAC-` + `Fleet Virtualization` |
| cclm | `[FG-RBAC-` + `CCLM` |
| mtv | `[MTV-` |
| search | `[FG-RBAC-` + `Search` |
| clusters | `[Clusters-` |
| applications | `[Apps-` |
| credentials | `[Credentials-` |

#### 2. Metadata Completeness

Checks for 4 required metadata lines:
- `**Polarion ID:**`
- `**Status:**`
- `**Created:**`
- `**Updated:**`

#### 3. Polarion Fields

Checks for 10 required `## Field: Value` lines:
- Type, Level, Component, Subcomponent, Test Type
- Pos/Neg, Importance, Automation, Tags, Release

#### 4. Section Order

Verifies sections appear in the correct order:
- Description before Setup
- Setup before Test Steps
- Test Steps before Teardown

#### 5. Type Field Value

Checks the `## Type:` field contains "Test Case". Warning if different.

#### 6. Test Steps Section Header

Checks for `## Test Steps` section header before step definitions. Warning if missing but steps exist.

#### 7. Step Format

For each `### Step N:` heading, verifies:
- An `**Expected Result:**` section exists within the step (blocking)
- Numbered actions present (warning)
- CLI commands in action area flagged for review (warning)
- `---` separators between consecutive steps (warning)

Missing expected results are blocking issues.

#### 8. Entry Point

Checks for `Entry Point` in the Description section. Warning if missing.

#### 9. JIRA Coverage

Checks for `Dev JIRA Coverage` or `JIRA Coverage` in Description. Warning if missing.

#### 10. Teardown Quality

Checks `oc delete` commands in the Teardown section for `--ignore-not-found` flag. Warning if missing on any delete command.

#### 11. Setup Commands

Checks the Setup section for:
- Bash code blocks present (warning)
- `# Expected:` comments on setup commands (warning)

### Output Model

```python
class ReviewResult(BaseModel):
    test_case_file: str
    verdict: Verdict           # PASS or FAIL
    issues: list[ValidationIssue]
    metadata_complete: bool
    section_order_valid: bool
    title_pattern_valid: bool
    entry_point_present: bool
    jira_coverage_present: bool
    step_format_valid: bool
    teardown_present: bool
    total_steps: int

class ValidationIssue(BaseModel):
    severity: str     # "blocking" | "warning" | "suggestion"
    category: str     # "metadata" | "description" | "setup" | "steps" | "teardown" | "title"
    message: str
    line: Optional[int]
```

### Verdict Logic

- **PASS:** Zero blocking issues
- **FAIL:** One or more blocking issues

Warnings do not cause FAIL but are reported in `SUMMARY.txt`.

### Phase 4.5 Enforcement

The quality reviewer must start its output with a JSON verification block containing:
- `mcp_verifications` (array of verification entries, min 3)
- `ac_vs_implementation_checked` (boolean)
- `knowledge_file_cross_referenced` (boolean)
- `verdict` ("PASS" or "NEEDS_FIXES")

The orchestrator validates this block before accepting the verdict. If the block is missing or `mcp_verifications` has fewer than 3 entries, the verdict is automatically overridden to `NEEDS_FIXES` and the reviewer is re-launched.

---

## Quality Standards Summary

A test case must pass all of these before delivery:

| Criterion | Phase 4.5 | Stage 3 |
|-----------|-----------|---------|
| Metadata completeness | Checks all fields present | Validates field format |
| Title pattern | Checks tag matches area | Validates regex pattern |
| Section order | Checks against conventions | Validates ordering |
| Entry point discovered | MCP `get_routes()` verification | Checks `**Entry Point:**` present |
| UI elements discovered | MCP `search_translations()` spot-check | Not checked (format only) |
| CLI-in-steps rule | Checks CLI usage context | Not checked |
| Setup completeness | Checks commands and expected output | Checks numbered format |
| Step format | Checks H3 heading, actions, results | Validates `### Step N:` + `**Expected Result:**` |
| Teardown | Checks cleanup coverage | Checks `--ignore-not-found` |
| AC vs implementation | Compares JIRA ACs against test expectations | Not checked |
| Peer consistency | Compares with existing test cases | Not checked |
| Polarion duplicates | Searches Polarion for existing coverage | Not checked |
