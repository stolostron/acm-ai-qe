#!/usr/bin/env python3
"""
Agent trace hook for z-stream-analysis.

Captures every Claude Code tool call, MCP interaction, prompt, and
subagent operation into a structured JSONL trace file.

Trace files are written to:
    .claude/traces/<session_id>.jsonl

Each line is a JSON object with:
    timestamp, event, session_id, tool, input (summarized), output (summarized),
    duration_ms (for PostToolUse), mcp_server, mcp_tool (for MCP calls)

Invoked by Claude Code hooks (PreToolUse, PostToolUse, etc.).
Receives hook event JSON on stdin.  Exits 0 to allow all operations.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# Max chars to capture from tool input/output to keep trace files manageable
MAX_INPUT_LEN = 2000
MAX_OUTPUT_LEN = 1000

# Trace directory relative to the project root
TRACES_DIR = Path(__file__).resolve().parent.parent / "traces"


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


def _summarize_input(tool_name, tool_input):
    """Produce a compact summary of tool input based on tool type."""
    if not tool_input:
        return None

    if tool_name == "Bash":
        return {"command": _truncate(tool_input.get("command"), MAX_INPUT_LEN)}

    if tool_name == "Read":
        return {"file_path": tool_input.get("file_path")}

    if tool_name in ("Write", "Edit"):
        summary = {"file_path": tool_input.get("file_path")}
        if tool_name == "Edit":
            summary["old_string"] = _truncate(tool_input.get("old_string"), 200)
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
    return json.loads(_truncate(tool_input, MAX_INPUT_LEN))


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
        # For Agent tool calls, also capture the full prompt text so the
        # subagent's initial instructions appear in the parent trace.
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
        # Try multiple fields — Claude Code uses different keys depending
        # on context (interactive user vs subagent continuation).
        prompt_text = (
            event_data.get("user_prompt")
            or event_data.get("prompt")
            or event_data.get("message")
            or event_data.get("content")
            or ""
        )
        entry["prompt"] = _truncate(prompt_text, MAX_INPUT_LEN)
        # Mark whether this is a subagent continuation (empty prompt) so
        # downstream renderers can display it appropriately.
        if not prompt_text:
            entry["is_continuation"] = True

    elif event_name == "SubagentStop":
        entry["event"] = "subagent_complete"
        entry["agent_id"] = event_data.get("agent_id")
        entry["agent_type"] = event_data.get("agent_type")
        entry["tool_use_id"] = event_data.get("tool_use_id")

    elif event_name == "Stop":
        entry["event"] = "turn_complete"

    else:
        entry["event"] = event_name
        entry["data"] = _truncate(str(event_data), MAX_INPUT_LEN)

    return entry


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
        # Never block the agent — silently fail
        pass

    # Always allow the operation
    sys.exit(0)


if __name__ == "__main__":
    main()
