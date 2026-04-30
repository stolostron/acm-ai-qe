# Session Tracing

Every diagnostic session is automatically traced via Claude Code hooks.
The trace captures all tool calls, MCP interactions, prompts, subagent
operations, and errors in structured JSONL format.

## What Gets Traced

| Event | What's Captured |
|-------|----------------|
| `oc` commands | verb, resource type, namespace, mutation flag |
| MCP calls | server name, tool name, input/output summaries |
| Knowledge reads | file path, diagnostic phase inference |
| Knowledge writes | file path (learned/ directory) |
| Agent/subagent ops | prompts, subagent type, completion |
| Prompts | user input, diagnostic type detection |
| Errors | tool failures, MCP errors |

## Trace Files

```
.claude/traces/
├── <session-id>.jsonl     # Per-session detailed trace (one JSON per line)
└── sessions.jsonl         # Session index (one-line summary per session)
```

Each trace entry includes: `timestamp`, `event`, `session_id`, `tool`,
summarized `input`/`output`, and diagnostic enrichments (`oc_verb`,
`oc_resource`, `oc_namespace`, `is_mutation`, `mcp_server`, `mcp_tool`,
`diagnostic_phase`, `is_knowledge_read`, `is_knowledge_write`).

The session index (`sessions.jsonl`) is appended on session end with
aggregate stats: diagnostic type, duration, tool call count, MCP call
count, oc command count, mutation count, knowledge reads/writes, errors.

## Diagnostic Phase Inference

Knowledge file reads are tagged with the diagnostic phase they support:

| File Pattern | Inferred Phase |
|-------------|----------------|
| `architecture/`, `component-registry` | learn |
| `healthy-baseline`, `addon-catalog`, `webhook-registry`, `certificate-inventory` | check |
| `failure-patterns`, `known-issues` | pattern-match |
| `dependency-chains`, `evidence-tiers`, `diagnostics/` | correlate |
| `learned/` | learn |

## Implementation

- Hook script: `.claude/hooks/agent_trace.py`
- Hook configuration: `.claude/settings.json` (hooks section)
- Trace storage: `.claude/traces/` (gitignored)

Hooks are configured for 6 event types: `PreToolUse` (Bash, MCP, Agent,
Read, Write, Edit), `PostToolUse` (Bash, MCP), `PostToolUseFailure`
(Bash, MCP), `UserPromptSubmit`, `SubagentStop`, `Stop`.
