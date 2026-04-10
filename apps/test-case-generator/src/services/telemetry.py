"""Pipeline telemetry for tracking stage timing and events."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class PipelineTelemetry:
    """Track timing and events across pipeline stages."""

    def __init__(self, run_dir: str, jira_id: str):
        self.run_dir = Path(run_dir)
        self.jira_id = jira_id
        self.log_path = self.run_dir / "pipeline.log.jsonl"
        self._stage_start: Optional[float] = None
        self._stage_name: Optional[str] = None
        self._pipeline_start = time.monotonic()
        self._log_event("pipeline_start", {"jira_id": jira_id})

    def _log_event(self, event_type: str, data: Optional[dict] = None):
        """Append a JSONL event to the telemetry log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "jira_id": self.jira_id,
        }
        if data:
            entry.update(data)

        self.run_dir.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def start_stage(self, stage_name: str):
        """Mark the start of a pipeline stage."""
        self._stage_name = stage_name
        self._stage_start = time.monotonic()
        self._log_event("stage_start", {"stage": stage_name})

    def end_stage(self, stage_name: str, metadata: Optional[dict] = None):
        """Mark the end of a pipeline stage with optional metadata."""
        elapsed = 0.0
        if self._stage_start is not None:
            elapsed = time.monotonic() - self._stage_start

        data = {
            "stage": stage_name,
            "elapsed_seconds": round(elapsed, 2),
        }
        if metadata:
            data.update(metadata)

        self._log_event("stage_end", data)
        self._stage_start = None
        self._stage_name = None

    def end_pipeline(self, verdict: str = "complete"):
        """Mark the end of the full pipeline."""
        total_elapsed = time.monotonic() - self._pipeline_start
        self._log_event("pipeline_end", {
            "total_elapsed_seconds": round(total_elapsed, 2),
            "verdict": verdict,
        })

    def log_error(self, stage: str, error: str):
        """Log an error event."""
        self._log_event("error", {"stage": stage, "error": error})
