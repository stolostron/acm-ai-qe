#!/usr/bin/env python3
"""
Agent trace hook for test-case-generator.

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
    oc_verb, oc_resource, oc_namespace (for oc/kubectl commands),
    pipeline_phase (when detectable from agent type or context),
    pipeline_command (generate, review, batch)

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

MAX_INPUT_LEN = 2000
MAX_OUTPUT_LEN = 1000

TRACES_DIR = Path(__file__).resolve().parent.parent / "traces"
SESSION_INDEX = TRACES_DIR / "sessions.jsonl"

# Pipeline command patterns (matched against user prompts)
COMMAND_PATTERNS = {
    "generate": re.compile(
        r"(?:^|/)generate\b|generate\s+(?:a\s+)?test\s+case",
        re.IGNORECASE,
    ),
    "review": re.compile(
        r"(?:^|/)review\b|review\s+(?:the\s+)?test\s+case",
        re.IGNORECASE,
    ),
    "batch": re.compile(
        r"(?:^|/)batch\b|batch\s+generate",
        re.IGNORECASE,
    ),
}

# Pipeline phase detection from subagent type
SUBAGENT_TO_PHASE = {
    "feature-investigator": "phase_1",
    "code-change-analyzer": "phase_1",
    "ui-discovery": "phase_1",
    "live-validator": "phase_3",
    "test-case-generator": "phase_4",
    "quality-reviewer": "phase_4_5",
}

# oc/kubectl command verb extraction
OC_PATTERN = re.compile(
    r"^(?:oc|kubectl)\s+"
    r"(get|describe|logs|version|whoami|cluster-info|api-resources|"
    r"adm\s+top|exec|auth|patch|scale|rollout\s+restart|"
    r"delete\s+pod|annotate|label|apply)\b"
    r"(?:\s+(\S+))?"
    r"(?:.*?(?:-n|--namespace)\s+(\S+))?",
    re.IGNORECASE,
)

MUTATION_VERBS = {"patch", "scale", "rollout restart", "delete pod",
                  "annotate", "label", "apply"}

KNOWLEDGE_PATH_PATTERN = re.compile(r"knowledge/")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(value, max_len):
    if value is None:
        return None
    if not isinstance(value, str):
        value = json.dumps(value, default=str)
    if len(value) > max_len:
        return value[:max_len] + f"... [{len(value) - max_len} chars truncated]"
    return value


def _parse_mcp_tool(tool_name):
    if tool_name and tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) == 3:
            return parts[1], parts[2]
    return None, None


def _parse_oc_command(command_str):
    if not command_str:
        return None, None, None
    match = OC_PATTERN.search(command_str)
    if match:
        verb = match.group(1).strip().lower()
        resource = match.group(2)
        namespace = match.group(3)
        return verb, resource, namespace
    return None, None, None


def _detect_command_type(prompt_text):
    if not prompt_text:
        return None
    for cmd_type, pattern in COMMAND_PATTERNS.items():
        if pattern.search(prompt_text):
            return cmd_type
    return None


def _detect_phase_from_read(file_path):
    """Infer pipeline context from knowledge file reads."""
    if not file_path:
        return None
    if "conventions/" in file_path:
        return "conventions"
    if "architecture/" in file_path:
        return "architecture"
    if "patterns/" in file_path:
        return "patterns"
    if "examples/" in file_path:
        return "examples"
    return None


def _detect_phase_from_agent(tool_input):
    """Infer pipeline phase from Agent subagent_type."""
    if not tool_input:
        return None
    subagent_type = tool_input.get("subagent_type", "")
    return SUBAGENT_TO_PHASE.get(subagent_type)


def _is_pipeline_output(file_path):
    """Check if a write targets a pipeline output file."""
    if not file_path:
        return False
    return "runs/" in file_path or "knowledge/patterns/" in file_path


def _summarize_input(tool_name, tool_input):
    if not tool_input:
        return None

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        summary = {"command": _truncate(cmd, MAX_INPUT_LEN)}
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
            summary["knowledge_category"] = phase
        if KNOWLEDGE_PATH_PATTERN.search(fp):
            summary["is_knowledge_read"] = True
        return summary

    if tool_name in ("Write", "Edit"):
        fp = tool_input.get("file_path", "")
        summary = {"file_path": fp}
        if _is_pipeline_output(fp):
            summary["is_pipeline_output"] = True
        if "knowledge/patterns/" in fp:
            summary["is_pattern_write"] = True
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

    try:
        return json.loads(_truncate(tool_input, MAX_INPUT_LEN))
    except (json.JSONDecodeError, TypeError):
        return _truncate(str(tool_input), MAX_INPUT_LEN)


# ---------------------------------------------------------------------------
# Entry builder
# ---------------------------------------------------------------------------

def _build_entry(event_data):
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
        # Promote oc command details to top level
        if tool_name == "Bash" and entry.get("input"):
            inp = entry["input"]
            for key in ("oc_verb", "oc_resource", "oc_namespace"):
                if inp.get(key):
                    entry[key] = inp[key]
            if inp.get("is_mutation"):
                entry["is_mutation"] = True
        # Promote knowledge read flags
        if tool_name == "Read" and entry.get("input"):
            inp = entry["input"]
            if inp.get("knowledge_category"):
                entry["knowledge_category"] = inp["knowledge_category"]
            if inp.get("is_knowledge_read"):
                entry["is_knowledge_read"] = True
        # Flag pipeline output writes
        if tool_name in ("Write", "Edit") and entry.get("input"):
            inp = entry["input"]
            if inp.get("is_pipeline_output"):
                entry["is_pipeline_output"] = True
            if inp.get("is_pattern_write"):
                entry["is_pattern_write"] = True
        # For Agent tool calls, detect pipeline phase and capture prompt
        if tool_name == "Agent":
            phase = _detect_phase_from_agent(tool_input)
            if phase:
                entry["pipeline_phase"] = phase
            if tool_input:
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
        cmd_type = _detect_command_type(prompt_text)
        if cmd_type:
            entry["pipeline_command"] = cmd_type
        if not prompt_text:
            entry["is_continuation"] = True

    elif event_name == "SubagentStop":
        entry["event"] = "subagent_complete"
        entry["agent_id"] = event_data.get("agent_id")
        entry["agent_type"] = event_data.get("agent_type")
        entry["tool_use_id"] = event_data.get("tool_use_id")
        agent_type = event_data.get("agent_type", "")
        phase = SUBAGENT_TO_PHASE.get(agent_type)
        if phase:
            entry["pipeline_phase"] = phase

    elif event_name == "Stop":
        entry["event"] = "turn_complete"
        _write_session_summary(session_id)

    else:
        entry["event"] = event_name
        entry["data"] = _truncate(str(event_data), MAX_INPUT_LEN)

    return entry


# ---------------------------------------------------------------------------
# Session summary (written on Stop events)
# ---------------------------------------------------------------------------

def _write_session_summary(session_id):
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
        pattern_writes = 0
        pipeline_outputs = 0
        errors = 0
        pipeline_command = None
        subagent_launches = 0
        phases_seen = set()
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
                    if entry.get("is_pattern_write"):
                        pattern_writes += 1
                    if entry.get("is_pipeline_output"):
                        pipeline_outputs += 1
                    if entry.get("pipeline_phase"):
                        phases_seen.add(entry["pipeline_phase"])
                    if entry.get("tool") == "Agent":
                        subagent_launches += 1
                elif event == "tool_error":
                    errors += 1
                elif event == "prompt":
                    prompts += 1
                    if entry.get("pipeline_command") and not pipeline_command:
                        pipeline_command = entry["pipeline_command"]
                elif event == "subagent_complete":
                    if entry.get("pipeline_phase"):
                        phases_seen.add(entry["pipeline_phase"])

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
            "pipeline_command": pipeline_command,
            "phases_seen": sorted(phases_seen),
            "duration_sec": duration_sec,
            "prompts": prompts,
            "tool_calls": tool_calls,
            "subagent_launches": subagent_launches,
            "mcp_calls": mcp_calls,
            "oc_commands": oc_commands,
            "mutations": mutations,
            "knowledge_reads": knowledge_reads,
            "pattern_writes": pattern_writes,
            "pipeline_outputs": pipeline_outputs,
            "errors": errors,
        }

        with open(SESSION_INDEX, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary, default=str) + "\n")

    except Exception:
        pass


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

        TRACES_DIR.mkdir(parents=True, exist_ok=True)

        entry = _build_entry(event_data)

        trace_file = TRACES_DIR / f"{session_id}.jsonl"
        with open(trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
