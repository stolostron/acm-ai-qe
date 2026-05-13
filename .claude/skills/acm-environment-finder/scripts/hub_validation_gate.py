#!/usr/bin/env python3
"""
Preflight gate before delegating to acm-hub-health-check.

Purpose (agent-facing):
  - Fail fast if the clone is missing the hub sibling skill (integrity).
  - Fail fast if oc is missing or the current KUBECONFIG cannot authenticate.
  - Emit a single JSON object on stdout so agents have a deterministic handoff
    payload without scraping prose.

This script does NOT perform ACM hub diagnostics. Full health checks live in
../acm-hub-health-check/SKILL.md only.

Exit codes:
  0  Preflight passed; proceed to read and execute the hub skill (Quick depth unless user asks deeper there).
  2  Hub sibling SKILL.md not found (incomplete clone or this script not from the acm-environment-finder tree).
  3  oc missing, KUBECONFIG unset/invalid, or cluster auth failed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def hub_skill_path(root: Path) -> Path:
    return root.parent / "acm-hub-health-check" / "SKILL.md"


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    sys.stdout.flush()


def run_oc(args: list[str], timeout: int) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["oc", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(["oc", *args], returncode=124, stdout="", stderr=str(exc))
        return proc


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight gate before acm-hub-health-check delegation")
    parser.add_argument(
        "--no-kubeconfig-required",
        action="store_true",
        help="Only verify hub skill exists and oc client is callable (skip cluster auth)",
    )
    parser.add_argument("--oc-timeout", type=int, default=45, help="Seconds for oc calls")
    args = parser.parse_args()
    kube_required = not args.no_kubeconfig_required

    root = skill_root()
    hub = hub_skill_path(root)
    rel = "../acm-hub-health-check/SKILL.md"

    base = {
        "ok": False,
        "finder_skill_dir": str(root),
        "hub_skill_relative": rel,
        "hub_skill_abspath": str(hub.resolve()) if hub.is_file() else str(hub),
        "mandatory_next": (
            "Read and execute the file at hub_skill_abspath (acm-hub-health-check SKILL.md) "
            "at Quick depth by default. Do not treat this gate script as hub diagnosis."
        ),
    }

    if not hub.is_file():
        payload = {
            **base,
            "ok": False,
            "exit_reason": "hub_skill_missing",
            "hint": "Expected sibling at .claude/skills/acm-hub-health-check/SKILL.md next to acm-environment-finder.",
        }
        emit(payload)
        return 2

    oc_check = run_oc(["version", "--client"], timeout=args.oc_timeout)
    if oc_check is None:
        payload = {
            **base,
            "ok": False,
            "exit_reason": "oc_not_found",
            "hint": "Install oc and ensure it is on PATH.",
        }
        emit(payload)
        return 3
    if oc_check.returncode == 124:
        payload = {
            **base,
            "ok": False,
            "exit_reason": "oc_timeout",
            "oc_stderr": (oc_check.stderr or "").strip(),
        }
        emit(payload)
        return 3
    if oc_check.returncode != 0:
        payload = {
            **base,
            "ok": False,
            "exit_reason": "oc_client_failed",
            "oc_stderr": (oc_check.stderr or "").strip(),
        }
        emit(payload)
        return 3

    oc_client_line = (oc_check.stdout or "").strip().splitlines()
    oc_client_summary = oc_client_line[0] if oc_client_line else "unknown"

    if not kube_required:
        payload = {
            **base,
            "ok": True,
            "exit_reason": "hub_skill_and_oc_only",
            "oc_client": oc_client_summary,
        }
        emit(payload)
        return 0

    kube = os.environ.get("KUBECONFIG", "").strip()
    if not kube:
        payload = {
            **base,
            "ok": False,
            "exit_reason": "kubeconfig_env_unset",
            "hint": "export KUBECONFIG to a temp file before running this gate (session-specific path per team rules).",
        }
        emit(payload)
        return 3

    kube_path = Path(kube.split(os.pathsep)[0])
    if not kube_path.is_file():
        payload = {
            **base,
            "ok": False,
            "exit_reason": "kubeconfig_file_missing",
            "kubeconfig_first_path": str(kube_path),
        }
        emit(payload)
        return 3

    whoami = run_oc(["whoami", "--show-server"], timeout=args.oc_timeout)
    if whoami is None:
        payload = {**base, "ok": False, "exit_reason": "oc_not_found", "hint": "Install oc and ensure it is on PATH."}
        emit(payload)
        return 3
    if whoami.returncode == 124:
        payload = {
            **base,
            "ok": False,
            "exit_reason": "oc_whoami_timeout",
            "oc_stderr": (whoami.stderr or "").strip(),
        }
        emit(payload)
        return 3
    if whoami.returncode != 0:
        payload = {
            **base,
            "ok": False,
            "exit_reason": "oc_whoami_failed",
            "oc_stderr": (whoami.stderr or "").strip(),
        }
        emit(payload)
        return 3

    api_server = (whoami.stdout or "").strip()

    payload = {
        **base,
        "ok": True,
        "exit_reason": "preflight_passed",
        "api_server": api_server,
        "oc_client": oc_client_summary,
    }
    emit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
