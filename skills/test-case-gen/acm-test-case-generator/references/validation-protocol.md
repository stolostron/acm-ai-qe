# Validation Protocol

## Per-Phase Validation Commands

### Phase 1: Data Gathering + JIRA Investigation

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/gather-output.json gather-output
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase1-jira.json phase1-jira
```

### Phase 2: Code Analysis

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase2-code.json phase2-code
```

### Phase 3: UI Discovery

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase3-ui.json phase3-ui
```

### Pre-Synthesis Readiness Check

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py --pre-synthesis <RUN_DIR>
```

### Phase 4: Synthesis

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/synthesized-context.md synthesized-context
```

### Phase 6: Test Case Writing

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/analysis-results.json analysis-results
```

### Phase 7: Quality Review Enforcement

```bash
python ${CLAUDE_SKILL_DIR}/scripts/review_enforcement.py <review-output-file>
```

## Retry Protocol

When artifact validation fails for an AI-produced phase (1, 2, 3, 4, or 6), retry up to 3 times before proceeding with incomplete data.

**For each attempt:** Re-spawn the SAME agent type with the original `<input>` block PLUS a `<retry>` block appended:

```
<retry>
ATTEMPT: N of 3
PREVIOUS_OUTPUT_PATH: <path to the invalid artifact>
VALIDATION_ERRORS:
- [error lines from validate_artifact.py]
INSTRUCTION: Review the validation errors above. Re-investigate where data is
missing or malformed — do not add placeholder values. Write corrected output
to the same path.
</retry>
```

**After 3 failures:** Proceed with incomplete data:
1. Write `validation-warnings.json` to the run directory containing the phase name, schema, attempt count, and final errors
2. Print: `"Phase N: validation failed after 3 attempts. Proceeding with incomplete data."`
3. Pass `VALIDATION_WARNINGS_PATH` in all downstream `<input>` blocks so agents are aware of gaps

**Phase 1 exception:** `gather-output.json` is produced by deterministic Python (gather.py) within the data-gatherer agent. Validation failure means a script bug -- stop the pipeline immediately instead of retrying. However, `phase1-jira.json` is AI-produced and follows the normal retry protocol.

**Phase 5 and 7 exceptions:** Phase 5 (live validation) produces unstructured markdown -- no schema validation. Phase 7 (quality review) has its own enforcement via `review_enforcement.py` -- no change.

## Phase 5: Live Validation Corrections

After the live validator subagent returns, check its output for a `## Corrections` section.
If corrections exist:
1. Parse each correction row (Field, Phase 3 Value, Correct Value, Evidence)
2. Update the synthesized context with the corrected values
3. Specifically: if `entry_point` was corrected, use the live-validated value for the test case
4. Log: "Correction applied: {field} changed from '{old}' to '{new}' (source: live validation)"

Arbitration rule: For user-visible labels (tab names, button text, breadcrumbs, column headers),
live UI observation ALWAYS overrides source-code-inferred values. Source code tells you the route
exists; the live UI tells you what label the user sees.
