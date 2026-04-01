"""
Structured logging configuration for z-stream-analysis.

Dual-output logging using structlog with stdlib integration:
- Console: human-readable, colored output (INFO+)
- JSONL file: machine-parseable structured logs (DEBUG+) in the run directory

Context propagation via contextvars — run_id and stage are automatically
attached to every log entry from every module without parameter passing.

Usage:
    from src.logging_config import configure_logging, bind_context

    # At pipeline entry point:
    configure_logging(run_dir=Path("runs/..."), verbose=False)
    bind_context(run_id="job_20260331_143022", stage="gather")

    # At stage transitions:
    bind_context(stage="oracle")

    # In service modules — no changes needed:
    # existing logging.getLogger(__name__) calls produce structured output
"""

import json
import logging
import logging.config
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog


# ---------------------------------------------------------------------------
# Context variables — propagated to every log entry automatically
# ---------------------------------------------------------------------------
_run_id_var: ContextVar[str] = ContextVar("run_id", default="")
_stage_var: ContextVar[str] = ContextVar("stage", default="init")

# Track the JSONL log file path so callers can reference it
_log_file_path: Optional[Path] = None

# Track whether configure_logging has been called
_configured = False


def bind_context(**kwargs) -> None:
    """Bind context variables that appear in every subsequent log entry.

    Supported keys: run_id, stage.  Unknown keys are silently ignored
    so callers don't need to worry about the exact set of supported vars.
    """
    if "run_id" in kwargs:
        _run_id_var.set(kwargs["run_id"])
    if "stage" in kwargs:
        _stage_var.set(kwargs["stage"])


def get_log_file_path() -> Optional[Path]:
    """Return the JSONL log file path, or None if file logging is disabled."""
    return _log_file_path


# ---------------------------------------------------------------------------
# Custom processors
# ---------------------------------------------------------------------------

def _add_pipeline_context(logger_name, method_name, event_dict):
    """Inject run_id and stage from contextvars into every log entry."""
    run_id = _run_id_var.get()
    if run_id:
        event_dict["run_id"] = run_id
    event_dict["stage"] = _stage_var.get()
    return event_dict


# ---------------------------------------------------------------------------
# Console formatter for progress output
# ---------------------------------------------------------------------------

class _BriefConsoleFormatter(logging.Formatter):
    """Compact console format: HH:MM:SS LEVEL  logger: message

    Preserves the existing gather.py feel while adding the logger name
    for traceability.  Does NOT include run_id/stage (those go to JSONL).
    """

    LEVEL_COLORS = {
        "DEBUG": "\033[36m",     # cyan
        "INFO": "\033[32m",      # green
        "WARNING": "\033[33m",   # yellow
        "ERROR": "\033[31m",     # red
        "CRITICAL": "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"

    def format(self, record):
        ts = self.formatTime(record, "%H:%M:%S")
        color = self.LEVEL_COLORS.get(record.levelname, "")
        reset = self.RESET if color else ""
        level = f"{color}{record.levelname:<7}{reset}"
        name = record.name.rsplit(".", 1)[-1]  # short module name
        return f"{ts} {level} {name}: {record.getMessage()}"


# ---------------------------------------------------------------------------
# JSON formatter for JSONL file
# ---------------------------------------------------------------------------

class _JSONFormatter(logging.Formatter):
    """Produces one JSON object per line for the JSONL log file.

    Includes: timestamp (ISO-8601 UTC), level, logger, message,
    run_id, stage, and exception info when present.
    """

    def format(self, record):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": _run_id_var.get(),
            "stage": _stage_var.get(),
        }
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def configure_logging(
    run_dir: Optional[Path] = None,
    verbose: bool = False,
) -> None:
    """Configure structured logging for the pipeline.

    Args:
        run_dir: If provided, a ``pipeline.log.jsonl`` file is created here
                 with DEBUG-level structured JSON logs.
        verbose: If True, console output includes DEBUG messages.
                 Default (False) shows INFO and above.

    Safe to call multiple times — subsequent calls update the root logger
    level and add a file handler for the new run_dir if one is provided
    and not already attached.
    """
    global _log_file_path, _configured

    root = logging.getLogger()

    if not _configured:
        # First-time setup: clear any basicConfig handlers and configure
        # the console handler.
        root.handlers.clear()
        root.setLevel(logging.DEBUG)

        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG if verbose else logging.INFO)
        console.setFormatter(_BriefConsoleFormatter())
        console.set_name("z-stream-console")
        root.addHandler(console)

        _configured = True
    else:
        # Subsequent calls: update console level
        for h in root.handlers:
            if getattr(h, "name", None) == "z-stream-console":
                h.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Add JSONL file handler for this run (if not already attached)
    if run_dir is not None:
        run_dir = Path(run_dir)
        log_path = run_dir / "pipeline.log.jsonl"
        _log_file_path = log_path

        # Avoid duplicate file handlers for the same path
        existing_paths = {
            getattr(h, "baseFilename", None) for h in root.handlers
        }
        if str(log_path.resolve()) not in existing_paths:
            fh = logging.FileHandler(str(log_path), encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(_JSONFormatter())
            fh.set_name("z-stream-jsonl")
            root.addHandler(fh)
