# Pipeline Implementation Detail

Input schemas, validation commands, credential resolution, MCP availability checks, retry protocol, and run directory structure. The orchestrator (SKILL.md) directs you here for implementation specifics.

## Phase 0: Credential Resolution

Resolve console credentials via priority cascade (stop at first match):

a. **Environment variables** (highest priority): `CONSOLE_PASSWORD` or `KUBEADMIN_PASSWORD` env var is set and non-empty.

b. **oc login command in user input**: If the user's message contains an `oc login` command with `-p` flag, extract the password value. Also extract the username from `-u` flag if present (default: `kubeadmin`). Example: `oc login https://api.cluster.com:6443 -u kubeadmin -p 'WXHWj-C25aT-fQ9cF-FQFUB'`.

c. **URL + password pair in user input**: If the user provides a console or API URL alongside a string matching the kubeadmin password format (4 groups of 4-6 alphanumeric characters separated by hyphens, e.g., `WXHWj-C25aT-fQ9cF-FQFUB`), extract the password. The URL and password may appear on the same line, adjacent lines, or in the same message.

d. **Explicit label in user input**: If the user writes something like `password: VALUE`, `pw VALUE`, `credentials VALUE`, or `creds: VALUE` near a cluster URL, extract the password value.

e. **oc whoami fallback** (backend-only): If `oc whoami` succeeds, the existing session supports oc CLI validation but NOT browser auth (session tokens don't work for OAuth form login). Browser auth requires an explicit password.

If NO credentials are found: Phase 5 uses backend-only validation (oc CLI, acm-search, acm-kubectl).

Store resolved values as `CONSOLE_PASSWORD` and `CONSOLE_USERNAME` (default: `kubeadmin`) for Phase 5.

## Phase 0: MCP Availability Check

Before starting Phase 1, probe each MCP server with one lightweight call. Classify results by tier:

| Tier | MCP Server | Probe Call | If Unavailable |
|------|-----------|------------|----------------|
| REQUIRED | jira | `mcp__jira__get_issue(issue_key=<JIRA_ID>)` | Warn user: "JIRA MCP is unavailable. Check MCP config with /onboard. Pipeline cannot produce meaningful output without JIRA data." Ask whether to proceed with user-provided context or stop. |
| IMPORTANT | acm-source | `mcp__acm-source__list_repos()` | Warn: "ACM Source MCP is unavailable. Source verification will be skipped -- test case quality may be reduced." Proceed. |
| OPTIONAL | polarion | `mcp__polarion__check_polarion_status()` | Note silently. Existing coverage check skipped. |
| OPTIONAL | neo4j-rhacm | Skip probe | Agent files handle gracefully. |
| OPTIONAL | acm-search | Skip probe | Live validator falls back to oc CLI. |
| OPTIONAL | acm-kubectl | Skip probe | Live validator falls back to oc CLI. |
| OPTIONAL | playwright | Skip probe | Live validator uses backend-only validation. |

Each probe is ONE call with no retries. If the call errors or times out, classify the MCP as unavailable.

## Phase Input Schemas

### Phase 1: Data Gathering + JIRA Investigation

```
<input>
JIRA_ID: <value>
ACM_VERSION: <value>
AREA: <value>
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>
```

**Run directory creation:** Do NOT pre-create a run directory. The agent runs `gather.py` internally, which creates the run directory at `runs/test-case-generator/<JIRA_ID>/<JIRA_ID>-<YYYY-MM-DDTHH-MM-SS>/` and prints the path on its last stdout line. The agent writes all artifacts to that directory and returns the path. Capture `RUN_DIR` from the agent's result.

The agent produces `gather-output.json`, `pr-diff.txt`, and `phase1-jira.json`.

**Validation:**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/gather-output.json gather-output
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase1-jira.json phase1-jira
```

### Phase 2: Code Analysis

```
<input>
JIRA_ID: <value>
PR_NUMBER: <value>
REPO: <value>
ACM_VERSION: <value>
AREA: <value>
RUN_DIR: <path>
PR_DIFF_PATH: <path to pr-diff.txt>
KNOWLEDGE_DIR: ${CLAUDE_SKILL_DIR}/../../knowledge
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>
```

**Validation:**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase2-code.json phase2-code
```

### Phase 3: UI Discovery

```
<input>
ACM_VERSION: <value>
CNV_VERSION: <value or "N/A">
AREA: <value>
FEATURE_NAME: <JIRA summary>
RUN_DIR: <path>
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>
```

**Validation:**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/phase3-ui.json phase3-ui
```

### Pre-Synthesis Readiness Check

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py --pre-synthesis <RUN_DIR>
```

### Phase 4: Synthesis

```
<input>
JIRA_ID: <value>
ACM_VERSION: <value>
AREA: <value>
CLUSTER_URL: <value or "NONE">
RUN_DIR: <path>
SYNTHESIS_TEMPLATE_PATH: ${CLAUDE_SKILL_DIR}/references/synthesis-template.md
KNOWLEDGE_DIR: ${CLAUDE_SKILL_DIR}/../../knowledge
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>
```

**Validation:**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/synthesized-context.md synthesized-context
```

### Phase 5: Live Validation

```
<input>
CONSOLE_URL: <value>
ACM_VERSION: <value>
RUN_DIR: <path>
SYNTHESIZED_CONTEXT_PATH: <path to synthesized-context.md>
GATHER_OUTPUT_PATH: <path to gather-output.json>
AUTH_REFERENCE_PATH: ${CLAUDE_SKILL_DIR}/references/console-auth.md
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
CONSOLE_USERNAME: <resolved username, default "kubeadmin">
CONSOLE_PASSWORD: <resolved password, or "NONE" if not available>
</input>
```

**Credential re-check:** Before spawning the Phase 5 subagent, re-check for credentials if `CONSOLE_PASSWORD` is still unresolved. The user may have provided credentials in a follow-up message after Phase 0. Apply the same priority cascade from Phase 0 to the full conversation history up to this point.

### Phase 6: Test Case Writing

```
<input>
JIRA_ID: <value>
ACM_VERSION: <value>
AREA: <value>
RUN_DIR: <path>
SYNTHESIZED_CONTEXT_PATH: <path to synthesized-context.md>
LIVE_VALIDATION_PATH: <path to phase5-live-validation.md or "N/A">
GATHER_OUTPUT_PATH: <path to gather-output.json>
SKILL_DIR: ${CLAUDE_SKILL_DIR}
KNOWLEDGE_DIR: ${CLAUDE_SKILL_DIR}/../../knowledge
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>
```

**Validation:**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate_artifact.py <RUN_DIR>/analysis-results.json analysis-results
```

### Phase 7: Quality Review

```
<input>
ACM_VERSION: <value>
AREA: <value>
RUN_DIR: <path>
TEST_CASE_PATH: <path to test-case.md>
GATHER_OUTPUT_PATH: <path to gather-output.json>
SKILL_DIR: ${CLAUDE_SKILL_DIR}
KNOWLEDGE_DIR: ${CLAUDE_SKILL_DIR}/../../knowledge
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>
```

**Enforcement:**

```bash
python ${CLAUDE_SKILL_DIR}/scripts/review_enforcement.py <review-output-file>
```

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

## Run Directory

Each run: `runs/test-case-generator/<JIRA_ID>/<JIRA_ID>-<YYYY-MM-DDTHH-MM-SS>/` (e.g., `runs/test-case-generator/ACM-32280/ACM-32280-2026-05-04T15-09-19/`).

The directory is created by `gather.py` -- do NOT pre-create it. The orchestrator captures the path from gather.py's stdout (last line) via the data-gatherer agent.

```
gather-output.json        -- Phase 1: PR metadata, conventions
pr-diff.txt               -- Phase 1: full PR diff
phase1-jira.json          -- Phase 1: JIRA findings
phase2-code.json          -- Phase 2: code analysis
phase3-ui.json            -- Phase 3: UI elements
synthesized-context.md    -- Phase 4: merged test plan
phase5-live-validation.md -- Phase 5: live results (optional)
test-case.md              -- Phase 6: primary deliverable
analysis-results.json     -- Phase 6: investigation metadata
phase7-review.md          -- Phase 7: quality review output
test-case-description.html -- Phase 8: Polarion description HTML
test-case-setup.html      -- Phase 8: Polarion setup HTML
test-case-steps.html      -- Phase 8: Polarion steps HTML
validation-warnings.json  -- Retry Protocol: present only if validation failed after 3 attempts
review-results.json       -- Phase 8: structural validation
SUMMARY.txt               -- Phase 8: human-readable summary
pipeline.log.jsonl        -- All phases: telemetry log
```
