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
**Max iterations:** 3 (orchestrator fixes issues between iterations)

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

The reviewer spot-checks 2-3 UI elements via MCP:

1. `set_acm_version(<version>)` on acm-ui
2. Check UI labels via `search_translations` — verify they match test case
3. Check entry point via `get_routes` — verify navigation path exists
4. If wizard steps mentioned: verify via `get_wizard_steps`
5. Flag any unverifiable element as `POTENTIALLY ASSUMED`

#### Step 4.5: AC vs Implementation Check

If the test case targets a specific JIRA story:

1. Extract JIRA story's Acceptance Criteria
2. For each AC bullet, check if test expected results are consistent
3. If AC says behavior X but test expects behavior Y:
   - Check if a Note explains the discrepancy (citing source code)
   - If Note exists: PASS
   - If no Note: flag as BLOCKING
4. Check test scope matches target story, not broader PR
   - Flag out-of-scope steps as BLOCKING

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

## Stage 3: Structural Validator

**Script:** `src/services/convention_validator.py`
**Input:** `test-case.md` file path, optional area
**Output:** `ReviewResult` model (written to `review-results.json`)

### Validation Rules

The validator (`validate_test_case()`, 298 lines) applies 7 categories of structural checks:

#### 1. Title Pattern

```python
TITLE_PATTERN = re.compile(r"^# RHACM4K-\d+ - \[.+\] .+ - .+$|^# RHACM4K-XXXXX - \[.+\] .+ - .+$")
```

Checks that the H1 title matches the convention pattern. Placeholder `XXXXX` is accepted for new test cases.

If an `area` is provided, also checks the tag pattern:

| Area | Expected Tag |
|------|-------------|
| governance | `[GRC-` |
| rbac | `[FG-RBAC-` |
| fleet-virt | `[FG-RBAC-` + `Fleet Virtualization` |
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

#### 5. Step Format

For each `### Step N:` heading, verifies:
- An `**Expected Result:**` section exists within the step
- Steps are not empty

Missing expected results are blocking issues.

#### 6. Entry Point

Checks for `**Entry Point:**` in the Description section. Warning if missing.

#### 7. Teardown Quality

Checks `oc delete` commands in the Teardown section for `--ignore-not-found` flag. Warning if missing on any delete command.

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
