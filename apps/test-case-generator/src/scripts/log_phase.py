"""Log a pipeline phase event to pipeline.log.jsonl.

Lightweight CLI utility called by the orchestrator after each AI phase
completes. Fills the telemetry gap between Stage 1 (gather.py) and
Stage 3 (report.py) for Phases 1-4.5.

Usage:
    python -m src.scripts.log_phase <run-dir> <phase> [--key value ...]

Examples:
    python -m src.scripts.log_phase runs/ACM-30459/... phase_1 --agents 3
    python -m src.scripts.log_phase runs/ACM-30459/... phase_2 --scenarios 6
    python -m src.scripts.log_phase runs/ACM-30459/... phase_3 --live true --cluster_version 2.17.0
    python -m src.scripts.log_phase runs/ACM-30459/... phase_4 --steps 7 --complexity medium
    python -m src.scripts.log_phase runs/ACM-30459/... phase_4_5 --verdict PASS --mcp_verifications 5
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("Usage: python -m src.scripts.log_phase <run-dir> <phase> [--key value ...]")
        sys.exit(1)

    run_dir = Path(sys.argv[1])
    phase = sys.argv[2]

    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}")
        sys.exit(1)

    metadata: dict = {}
    args = sys.argv[3:]
    i = 0
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            key = args[i][2:]
            value = args[i + 1]
            if value.isdigit():
                metadata[key] = int(value)
            elif value.lower() in ("true", "false"):
                metadata[key] = value.lower() == "true"
            else:
                metadata[key] = value
            i += 2
        else:
            i += 1

    # Read jira_id from gather-output.json if available
    jira_id = "unknown"
    gather_path = run_dir / "gather-output.json"
    if gather_path.exists():
        try:
            with open(gather_path, encoding="utf-8") as f:
                data = json.load(f)
                jira_id = data.get("jira_id", "unknown")
        except (json.JSONDecodeError, KeyError):
            pass

    # Capture session ID from environment (set by Claude Code runtime)
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "phase_end",
        "jira_id": jira_id,
        "phase": phase,
    }
    if session_id:
        entry["session_id"] = session_id
    entry.update(metadata)

    log_path = run_dir / "pipeline.log.jsonl"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"Logged phase_end: {phase} -> {log_path.name}")


if __name__ == "__main__":
    main()
