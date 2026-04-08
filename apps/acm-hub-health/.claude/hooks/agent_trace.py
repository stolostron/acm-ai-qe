#!/usr/bin/env python3
"""
Agent trace hook for acm-hub-health.

Captures every Claude Code tool call, MCP interaction, prompt, and
subagent operation into a structured JSONL trace file.

Trace files are written to:
    .claude/traces/<session_id>.jsonl

Session index (one-line summary per session) is maintained at:
    .claude/traces/sessions.jsonl

Each trace line is a JSON object with:
    timestamp, event, session_id, tool, input (summarized),
    output (summarized),
    mcp_server, mcp_tool (for MCP calls),
    oc_verb, oc_resource, oc_namespace (for oc commands),
    diagnostic_phase (when detectable from context)

Invoked by Claude Code hooks (PreToolUse, PostToolUse, etc.).
Receives hook event JSON on stdin.  Exits 0 to allow all operations.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Max chars to capture from tool input/output to keep trace files manageable
MAX_INPUT_LEN = 2000
MAX_OUTPUT_LEN = 1000

# Trace directory relative to the project root
TRACES_DIR = Path(__file__).resolve().parent.parent / "traces"

# Session index file
SESSION_INDEX = TRACES_DIR / "sessions.jsonl"

# Diagnostic command patterns (matched against user prompts)
# Covers both slash commands (/deep) and natural language ("thorough check")
DIAGNOSTIC_PATTERNS = {
    "sanity": re.compile(
        r"(?:^|/)sanity\b|(?:quick|pulse)\s*check|is\s+(?:my\s+)?hub\s+(?:alive|ok|up)",
        re.IGNORECASE,
    ),
    "health-check": re.compile(
        r"(?:^|/)health[_-]?check\b|(?:health|standard)\s*(?:check|diagnostic)"
        r"|(?:how(?:'s| is)\s+(?:my\s+)?hub)|analyze\s+(?:the\s+)?health",
        re.IGNORECASE,
    ),
    "deep": re.compile(
        r"(?:^|/)deep\b|(?:deep|thorough|full)\s*(?:audit|check|dive|diagnostic)"
        r"|in\s+depth|all\s+6\s+phases",
        re.IGNORECASE,
    ),
    "investigate": re.compile(
        r"(?:^|/)investigate\b|(?:check|look\s+into|dig\s+into|why\s+(?:are|is))",
        re.IGNORECASE,
    ),
    "learn": re.compile(
        r"(?:^|/)learn\b|(?:refresh|update)\s+knowledge",
        re.IGNORECASE,
    ),
}

# oc command verb extraction
OC_PATTERN = re.compile(
    r"^(?:oc|kubectl)\s+"
    r"(get|describe|logs|version|whoami|cluster-info|api-resources|"
    r"adm\s+top|exec|auth|patch|scale|rollout\s+restart|"
    r"delete\s+pod|annotate|label|apply)\b"
    r"(?:\s+(\S+))?"  # resource type or target
    r"(?:.*?(?:-n|--namespace)\s+(\S+))?",  # namespace flag
    re.IGNORECASE,
)

# Mutation verbs that indicate remediation activity
MUTATION_VERBS = {"patch", "scale", "rollout restart", "delete pod",
                  "annotate", "label", "apply"}

# Knowledge file read detection
KNOWLEDGE_PATH_PATTERN = re.compile(r"knowledge/")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(value, max_len):
    """Truncate a string or JSON-serialized value."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = json.dumps(value, default=str)
    if len(value) > max_len:
        return value[:max_len] + f"... [{len(value) - max_len} chars truncated]"
    return value


def _parse_mcp_tool(tool_name):
    """Extract MCP server and tool from 'mcp__<server>__<tool>' format."""
    if tool_name and tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) == 3:
            return parts[1], parts[2]
    return None, None


def _parse_oc_command(command_str):
    """Extract verb, resource, and namespace from an oc/kubectl command."""
    if not command_str:
        return None, None, None
    match = OC_PATTERN.search(command_str)
    if match:
        verb = match.group(1).strip().lower()
        resource = match.group(2)
        namespace = match.group(3)
        return verb, resource, namespace
    return None, None, None


def _detect_diagnostic_type(prompt_text):
    """Detect the diagnostic command type from a user prompt."""
    if not prompt_text:
        return None
    for dtype, pattern in DIAGNOSTIC_PATTERNS.items():
        if pattern.search(prompt_text):
            return dtype
    return None


def _detect_phase_from_read(file_path):
    """Infer diagnostic phase from knowledge file reads."""
    if not file_path:
        return None
    if "architecture/" in file_path or "component-registry" in file_path:
        return "learn"
    if "dependency-chains" in file_path or "evidence-tiers" in file_path:
        return "correlate"
    if "diagnostics/" in file_path:
        return "correlate"
    if "failure-patterns" in file_path or "known-issues" in file_path:
        return "pattern-match"
    if any(p in file_path for p in (
        "healthy-baseline", "addon-catalog",
        "webhook-registry", "certificate-inventory",
    )):
        return "check"
    if "learned/" in file_path:
        return "learn"
    return None


def _summarize_input(tool_name, tool_input):
    """Produce a compact summary of tool input based on tool type."""
    if not tool_input:
        return None

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        summary = {"command": _truncate(cmd, MAX_INPUT_LEN)}
        # Enrich with oc command details
        oc_verb, oc_resource, oc_ns = _parse_oc_command(cmd)
        if oc_verb:
            summary["oc_verb"] = oc_verb
            if oc_resource:
                summary["oc_resource"] = oc_resource
            if oc_ns:
                summary["oc_namespace"] = oc_ns
            if oc_verb in MUTATION_VERBS:
                summary["is_mutation"] = True
        return summary

    if tool_name == "Read":
        summary = {"file_path": tool_input.get("file_path")}
        fp = tool_input.get("file_path", "")
        phase = _detect_phase_from_read(fp)
        if phase:
            summary["diagnostic_phase"] = phase
        if KNOWLEDGE_PATH_PATTERN.search(fp):
            summary["is_knowledge_read"] = True
        return summary

    if tool_name in ("Write", "Edit"):
        summary = {"file_path": tool_input.get("file_path")}
        fp = tool_input.get("file_path", "")
        if "knowledge/learned/" in fp:
            summary["is_knowledge_write"] = True
        if tool_name == "Edit":
            summary["old_string"] = _truncate(
                tool_input.get("old_string"), 200
            )
        return summary

    if tool_name == "Grep":
        return {
            "pattern": tool_input.get("pattern"),
            "path": tool_input.get("path"),
            "glob": tool_input.get("glob"),
        }

    if tool_name == "Glob":
        return {
            "pattern": tool_input.get("pattern"),
            "path": tool_input.get("path"),
        }

    if tool_name == "Agent":
        return {
            "description": tool_input.get("description"),
            "subagent_type": tool_input.get("subagent_type"),
            "prompt": _truncate(tool_input.get("prompt"), 500),
        }

    # MCP and other tools: truncate the full input
    try:
        return json.loads(_truncate(tool_input, MAX_INPUT_LEN))
    except (json.JSONDecodeError, TypeError):
        return _truncate(str(tool_input), MAX_INPUT_LEN)


# ---------------------------------------------------------------------------
# Entry builder
# ---------------------------------------------------------------------------

def _build_entry(event_data):
    """Build a trace entry from the raw hook event data."""
    event_name = event_data.get("hook_event_name", "unknown")
    tool_name = event_data.get("tool_name", "")
    tool_input = event_data.get("tool_input")
    tool_response = event_data.get("tool_response")
    session_id = event_data.get("session_id", "")

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
    }

    mcp_server, mcp_tool = _parse_mcp_tool(tool_name)

    if event_name == "PreToolUse":
        entry["event"] = "tool_call"
        entry["tool"] = tool_name
        entry["input"] = _summarize_input(tool_name, tool_input)
        if mcp_server:
            entry["mcp_server"] = mcp_server
            entry["mcp_tool"] = mcp_tool
        # For Bash oc commands, promote oc details to top level
        if tool_name == "Bash" and entry.get("input"):
            inp = entry["input"]
            if inp.get("oc_verb"):
                entry["oc_verb"] = inp["oc_verb"]
            if inp.get("oc_resource"):
                entry["oc_resource"] = inp["oc_resource"]
            if inp.get("oc_namespace"):
                entry["oc_namespace"] = inp["oc_namespace"]
            if inp.get("is_mutation"):
                entry["is_mutation"] = True
        # For Read, promote diagnostic phase and knowledge flags
        if tool_name == "Read" and entry.get("input"):
            inp = entry["input"]
            if inp.get("diagnostic_phase"):
                entry["diagnostic_phase"] = inp["diagnostic_phase"]
            if inp.get("is_knowledge_read"):
                entry["is_knowledge_read"] = True
        # For Write/Edit to knowledge/learned/, flag it
        if tool_name in ("Write", "Edit") and entry.get("input"):
            if entry["input"].get("is_knowledge_write"):
                entry["is_knowledge_write"] = True
        # For Agent tool calls, capture the full prompt
        if tool_name == "Agent" and tool_input:
            entry["agent_prompt"] = _truncate(
                tool_input.get("prompt", ""), MAX_INPUT_LEN
            )

    elif event_name == "PostToolUse":
        entry["event"] = "tool_result"
        entry["tool"] = tool_name
        entry["output"] = _truncate(tool_response, MAX_OUTPUT_LEN)
        if mcp_server:
            entry["mcp_server"] = mcp_server
            entry["mcp_tool"] = mcp_tool

    elif event_name == "PostToolUseFailure":
        entry["event"] = "tool_error"
        entry["tool"] = tool_name
        entry["error"] = _truncate(tool_response, MAX_OUTPUT_LEN)
        if mcp_server:
            entry["mcp_server"] = mcp_server
            entry["mcp_tool"] = mcp_tool

    elif event_name == "UserPromptSubmit":
        entry["event"] = "prompt"
        prompt_text = (
            event_data.get("user_prompt")
            or event_data.get("prompt")
            or event_data.get("message")
            or event_data.get("content")
            or ""
        )
        entry["prompt"] = _truncate(prompt_text, MAX_INPUT_LEN)
        # Detect diagnostic command type
        diag_type = _detect_diagnostic_type(prompt_text)
        if diag_type:
            entry["diagnostic_type"] = diag_type
        # Mark subagent continuations
        if not prompt_text:
            entry["is_continuation"] = True

    elif event_name == "SubagentStop":
        entry["event"] = "subagent_complete"
        entry["agent_id"] = event_data.get("agent_id")
        entry["agent_type"] = event_data.get("agent_type")
        entry["tool_use_id"] = event_data.get("tool_use_id")

    elif event_name == "Stop":
        entry["event"] = "turn_complete"
        # On session end, compute session summary and append to index
        _write_session_summary(session_id)

    else:
        entry["event"] = event_name
        entry["data"] = _truncate(str(event_data), MAX_INPUT_LEN)

    return entry


# ---------------------------------------------------------------------------
# Session summary (written on Stop events)
# ---------------------------------------------------------------------------

def _write_session_summary(session_id):
    """Read back the trace file and write a one-line summary to the index."""
    if not session_id or session_id == "unknown":
        return

    trace_file = TRACES_DIR / f"{session_id}.jsonl"
    if not trace_file.exists():
        return

    try:
        tool_calls = 0
        mcp_calls = 0
        oc_commands = 0
        mutations = 0
        knowledge_reads = 0
        knowledge_writes = 0
        errors = 0
        diagnostic_type = None
        first_ts = None
        last_ts = None
        prompts = 0

        with open(trace_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                ts = entry.get("timestamp")
                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

                event = entry.get("event")
                if event == "tool_call":
                    tool_calls += 1
                    if entry.get("mcp_server"):
                        mcp_calls += 1
                    if entry.get("oc_verb"):
                        oc_commands += 1
                    if entry.get("is_mutation"):
                        mutations += 1
                    if entry.get("is_knowledge_read"):
                        knowledge_reads += 1
                    if entry.get("is_knowledge_write"):
                        knowledge_writes += 1
                elif event == "tool_error":
                    errors += 1
                elif event == "prompt":
                    prompts += 1
                    if entry.get("diagnostic_type") and not diagnostic_type:
                        diagnostic_type = entry["diagnostic_type"]

        # Compute duration
        duration_sec = None
        if first_ts and last_ts:
            try:
                t0 = datetime.fromisoformat(first_ts)
                t1 = datetime.fromisoformat(last_ts)
                duration_sec = round((t1 - t0).total_seconds())
            except (ValueError, TypeError):
                pass

        summary = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "diagnostic_type": diagnostic_type,
            "duration_sec": duration_sec,
            "prompts": prompts,
            "tool_calls": tool_calls,
            "mcp_calls": mcp_calls,
            "oc_commands": oc_commands,
            "mutations": mutations,
            "knowledge_reads": knowledge_reads,
            "knowledge_writes": knowledge_writes,
            "errors": errors,
        }

        with open(SESSION_INDEX, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, default=str) + "\n")

    except Exception:
        pass  # Never block the agent


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        event_data = json.loads(raw)
        session_id = event_data.get("session_id", "unknown")

        # Ensure traces directory exists
        TRACES_DIR.mkdir(parents=True, exist_ok=True)

        # Build the trace entry
        entry = _build_entry(event_data)

        # Write to session-specific trace file
        trace_file = TRACES_DIR / f"{session_id}.jsonl"
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    except Exception:
        # Never block the agent -- silently fail
        pass

    # Always allow the operation
    sys.exit(0)


if __name__ == "__main__":
    main()
