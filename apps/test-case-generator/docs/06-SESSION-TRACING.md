# Session Tracing

Claude Code hooks capture every tool call, MCP interaction, prompt, subagent launch, and error into structured JSONL trace files. This provides full observability across all pipeline phases, including the AI agent phases (1-4.5) that the Python telemetry does not cover.

## Architecture

The app uses two complementary telemetry systems:

| System | Covers | Format | Location |
|--------|--------|--------|----------|
| Pipeline telemetry (`PipelineTelemetry`) | Stage 1 + Stage 3 (deterministic Python scripts) | JSONL | `runs/<run>/pipeline.log.jsonl` |
| Session tracing (Claude Code hooks) | All phases (0-4.5 + Stage 3), all tool calls | JSONL | `.claude/traces/<session_id>.jsonl` |

Pipeline telemetry captures timing and metadata for the Python scripts. Session tracing captures everything Claude Code does, including the AI agent phases that have no Python instrumentation.

## Hook Configuration

Defined in `.claude/settings.json` under the `hooks` key. Six event types are captured:

| Hook Event | Fires When | What Is Logged |
|-----------|-----------|---------------|
| `PreToolUse` | Before any tool call | Tool name, input summary, MCP server/tool, oc verb/resource, pipeline phase, knowledge category |
| `PostToolUse` | After successful tool execution | Tool name, output (truncated to 1000 chars) |
| `PostToolUseFailure` | After tool execution error | Tool name, error message |
| `UserPromptSubmit` | When user submits a prompt | Prompt text, pipeline command detection (generate/review/batch) |
| `SubagentStop` | When a subagent completes | Agent ID, agent type, pipeline phase |
| `Stop` | At turn completion | Triggers session summary computation |

All hooks invoke the same script: `python3 $CLAUDE_PROJECT_DIR/.claude/hooks/agent_trace.py`

### Matched Tools

| Event | Matched Tools |
|-------|--------------|
| PreToolUse | Bash, `mcp__.*` (regex), Agent, Read, Write, Edit |
| PostToolUse | Bash, `mcp__.*` |
| PostToolUseFailure | `mcp__.*`, Bash |
| UserPromptSubmit | All prompts (no matcher) |
| SubagentStop | All subagents (no matcher) |
| Stop | All stops (no matcher) |

---

## Trace File Format

Each session produces a JSONL file at `.claude/traces/<session_id>.jsonl`.

### Common Fields (all entries)

```json
{
  "timestamp": "2026-04-18T03:50:32.008478+00:00",
  "session_id": "d9b279cd-c560-4fae-a2cd-70414b71e62c",
  "event": "tool_call"
}
```

### Event Types

#### tool_call (PreToolUse)

```json
{
  "event": "tool_call",
  "tool": "Bash",
  "input": {"command": "oc get pods -n open-cluster-management"},
  "oc_verb": "get",
  "oc_resource": "pods",
  "oc_namespace": "open-cluster-management"
}
```

For MCP tools:
```json
{
  "event": "tool_call",
  "tool": "mcp__acm-source__search_translations",
  "input": {"query": "Labels"},
  "mcp_server": "acm-source",
  "mcp_tool": "search_translations"
}
```

For Agent launches:
```json
{
  "event": "tool_call",
  "tool": "Agent",
  "input": {"description": "JIRA deep dive", "subagent_type": "feature-investigator"},
  "pipeline_phase": "phase_1",
  "agent_prompt": "Investigate ACM-30459..."
}
```

For knowledge file reads:
```json
{
  "event": "tool_call",
  "tool": "Read",
  "input": {"file_path": "knowledge/conventions/test-case-format.md"},
  "knowledge_category": "conventions",
  "is_knowledge_read": true
}
```

#### tool_result (PostToolUse)

```json
{
  "event": "tool_result",
  "tool": "Bash",
  "output": "Stage 1: Gathering data for ACM-30459..."
}
```

#### tool_error (PostToolUseFailure)

```json
{
  "event": "tool_error",
  "tool": "mcp__jira__get_issue",
  "error": "Connection timeout"
}
```

#### prompt (UserPromptSubmit)

```json
{
  "event": "prompt",
  "prompt": "/generate ACM-30459 --version 2.17",
  "pipeline_command": "generate"
}
```

#### subagent_complete (SubagentStop)

```json
{
  "event": "subagent_complete",
  "agent_id": "a1a01994c5deb0ea2",
  "agent_type": "feature-investigator",
  "pipeline_phase": "phase_1"
}
```

#### turn_complete (Stop)

```json
{
  "event": "turn_complete"
}
```

---

## Enrichment

The hook script enriches trace entries with pipeline-specific metadata.

### Pipeline Command Detection

User prompts are matched against patterns to detect the pipeline command:

| Pattern | Detected Command |
|---------|-----------------|
| `/generate` or `generate a test case` | `generate` |
| `/review` or `review the test case` | `review` |
| `/batch` or `batch generate` | `batch` |

### Pipeline Phase Detection

Subagent launches are tagged with their pipeline phase based on `subagent_type`:

| Subagent Type | Phase |
|---------------|-------|
| `feature-investigator` | `phase_1` |
| `code-change-analyzer` | `phase_1` |
| `ui-discovery` | `phase_1` |
| `live-validator` | `phase_3` |
| `test-case-generator` | `phase_4` |
| `quality-reviewer` | `phase_4_5` |

### Knowledge Category Detection

Knowledge file reads are categorized by directory:

| Path Contains | Category |
|--------------|----------|
| `conventions/` | `conventions` |
| `architecture/` | `architecture` |
| `patterns/` | `patterns` |
| `examples/` | `examples` |

### oc Command Parsing

Bash commands starting with `oc` or `kubectl` are parsed for verb, resource, and namespace:

```
oc get pods -n open-cluster-management
  -> oc_verb: "get", oc_resource: "pods", oc_namespace: "open-cluster-management"
```

Mutation verbs (`patch`, `scale`, `rollout restart`, `delete pod`, `annotate`, `label`, `apply`) are flagged with `is_mutation: true`.

### MCP Server Extraction

MCP tool names in `mcp__<server>__<tool>` format are parsed:

```
mcp__acm-source__search_translations
  -> mcp_server: "acm-source", mcp_tool: "search_translations"
```

---

## Session Index

On each `Stop` event, the hook reads back the entire trace file and writes a one-line summary to `.claude/traces/sessions.jsonl`.

### Summary Fields

```json
{
  "session_id": "d9b279cd-c560-4fae-a2cd-70414b71e62c",
  "timestamp": "2026-04-18T03:48:36.771524+00:00",
  "pipeline_command": "generate",
  "phases_seen": ["phase_1", "phase_4", "phase_4_5"],
  "duration_sec": 180,
  "prompts": 1,
  "tool_calls": 57,
  "subagent_launches": 5,
  "mcp_calls": 12,
  "oc_commands": 3,
  "mutations": 0,
  "knowledge_reads": 8,
  "pattern_writes": 0,
  "pipeline_outputs": 2,
  "errors": 0
}
```

### Aggregated Counters

| Counter | What it counts |
|---------|---------------|
| `prompts` | User prompt events |
| `tool_calls` | Total tool_call events |
| `subagent_launches` | Agent tool calls |
| `mcp_calls` | Tool calls with `mcp_server` field |
| `oc_commands` | Bash calls with `oc_verb` field |
| `mutations` | Bash calls with `is_mutation: true` |
| `knowledge_reads` | Read calls with `is_knowledge_read: true` |
| `pattern_writes` | Write/Edit calls to `knowledge/patterns/` |
| `pipeline_outputs` | Write/Edit calls to `runs/` |
| `errors` | tool_error events |

---

## Pipeline Telemetry

Three Python scripts write events to `pipeline.log.jsonl` in each run directory:

- **`gather.py`** and **`report.py`** use `PipelineTelemetry` (69 lines, `src/services/telemetry.py`) for Stage 1 and Stage 3
- **`log_phase.py`** (`src/scripts/log_phase.py`) writes `phase_end` events for AI phases (1-4.5), called by the orchestrator after each phase completes

### Events

| Event | Source | Fields | When |
|-------|--------|--------|------|
| `pipeline_start` | `gather.py` | `jira_id` | Script initialization |
| `stage_start` | `gather.py`/`report.py` | `stage` | Stage begins |
| `stage_end` | `gather.py`/`report.py` | `stage`, `elapsed_seconds`, custom metadata | Stage completes |
| `phase_end` | `log_phase.py` | `phase`, custom metadata (agents, verdict, etc.) | AI phase completes |
| `pipeline_end` | `report.py` | `total_elapsed_seconds`, `verdict` | Script finishes |
| `error` | `gather.py`/`report.py` | `stage`, `error` | Error occurs |

### Phase Telemetry (log_phase.py)

```bash
python -m src.scripts.log_phase <run-dir> <phase> [--key value ...]
```

Writes one JSONL entry per call. Reads `jira_id` from `gather-output.json` automatically.

Example output:
```json
{"timestamp": "2026-04-28T03:55:10Z", "event": "phase_end", "jira_id": "ACM-30459", "phase": "phase_1", "agents": 3}
{"timestamp": "2026-04-28T03:56:20Z", "event": "phase_end", "jira_id": "ACM-30459", "phase": "phase_4_5", "verdict": "PASS", "mcp_verifications": 5}
```

### Stage 1 Metadata

```json
{
  "stage": "gather",
  "elapsed_seconds": 1.72,
  "pr_found": true,
  "pr_number": 5790,
  "area": "governance",
  "existing_test_cases_count": 3,
  "conventions_loaded": true
}
```

### Stage 3 Metadata

```json
{
  "stage": "report",
  "elapsed_seconds": 0.5,
  "verdict": "PASS",
  "total_steps": 8,
  "blocking_issues": 0,
  "warnings": 0,
  "html_generated": true
}
```

---

## Implementation

**Hook script:** `.claude/hooks/agent_trace.py` (471 lines)
**Trace directory:** `.claude/traces/` (gitignored)
**Session index:** `.claude/traces/sessions.jsonl`

The hook:
1. Reads JSON event from stdin (hook event data)
2. Parses tool name, input, output, session ID
3. Enriches with pipeline-specific metadata (phase, command, knowledge category, oc parsing, MCP extraction)
4. Appends one JSONL line to the session trace file
5. On Stop events: reads back the trace, aggregates counters, writes summary to session index
6. Always exits with code 0 (never blocks the agent)
7. Exception-safe: silently fails on write errors

### Truncation Limits

- Tool input: max 2000 characters
- Tool output: max 1000 characters
- Agent prompts: max 2000 characters (in `agent_prompt` field), 500 characters (in `input.prompt`)
