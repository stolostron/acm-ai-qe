# Pipeline Implementation Detail — Index

This file is an index pointing to split reference files. Read the specific file for your current phase.

| File | Content | Load When |
|------|---------|-----------|
| `phase0-inputs.md` | Credential resolution cascade, MCP availability check | Phase 0 |
| `validation-protocol.md` | Per-phase validation commands, retry protocol, live validation corrections | On first validation or retry |
| `run-directory.md` | Run directory structure, artifact naming | Phase 1 (before creating run dir) |

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

### Phase 2: Code Analysis

```
<input>
JIRA_ID: <value>
PR_NUMBER: <value>
REPO: <value>
ACM_VERSION: <value>
CNV_VERSION: <value or "N/A">
AREA: <value>
RUN_DIR: <path>
PR_DIFF_PATH: <path to pr-diff.txt>
KNOWLEDGE_DIR: ${CLAUDE_SKILL_DIR}/../../knowledge
SKILLS_DIR: ${CLAUDE_SKILL_DIR}/..
</input>
```

CNV_VERSION: Read from `gather-output.json` (`cnv_version` field). If null, check `phase1-jira.json`. Use `"N/A"` for non-virtualization areas.

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

**Credential re-check:** Before spawning the Phase 5 subagent, re-check for credentials if `CONSOLE_PASSWORD` is still unresolved. The user may have provided credentials in a follow-up message after Phase 0. Apply the same priority cascade from `phase0-inputs.md` to the full conversation history up to this point.

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
