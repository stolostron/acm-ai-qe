"""Regression test for the ABORTED-build report path (Unit 1: A2 + C5).

Exercises report.py's empty-per_test ABORTED branch (report.py:319-338) end to end on a
committed fixture, and verifies the skill documents the empty/ABORTED short-circuit contract.

No external deps: report.py runs on local fixture files only (safe for the no-VPN baseline).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.regression]

REPO_ROOT = Path(__file__).resolve().parents[4]
LIB_DIR = REPO_ROOT / "lib" / "z-stream-analysis"
FIXTURE_DIR = LIB_DIR / "tests" / "fixtures" / "aborted_run"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"


def test_aborted_fixture_has_both_required_files():
    """report.py needs a non-empty core-data.json AND a correctly-named
    analysis-results.json, or __init__ raises before the ABORTED branch runs."""
    core = json.loads((FIXTURE_DIR / "core-data.json").read_text())
    analysis = json.loads((FIXTURE_DIR / "analysis-results.json").read_text())
    assert core.get("jenkins"), "core-data.json must be non-empty (else FileNotFoundError)"
    assert analysis["per_test_analysis"] == []
    assert isinstance(analysis["summary"]["by_classification"], dict)
    assert analysis["analysis_metadata"]["build_result"] == "ABORTED"


def test_report_renders_build_aborted(tmp_path):
    """report.py exits 0 and renders a 'Build Aborted' section for an ABORTED build with
    empty per_test_analysis (report.py:319-338). Copies the fixture into tmp_path first so
    the committed fixture stays clean (a run writes Detailed-Analysis.md, SUMMARY.txt, etc.)."""
    run_dir = tmp_path / "aborted_run"
    shutil.copytree(FIXTURE_DIR, run_dir)

    result = subprocess.run(
        [sys.executable, "-m", "src.scripts.report", str(run_dir)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(LIB_DIR),
    )
    assert result.returncode == 0, (
        f"report.py failed rc={result.returncode}\nstderr: {result.stderr[-800:]}"
    )
    md = (run_dir / "Detailed-Analysis.md").read_text()
    assert "## Build Aborted" in md, "missing 'Build Aborted' section"
    assert "ABORTED" in md
    # optional pipeline_failure.recommendation is rendered when present
    assert "Recommendation:" in md


def test_skill_documents_aborted_short_circuit():
    """The skill must document the empty/ABORTED short-circuit contract in all three places
    the analyzer and classifier read."""
    phase_a = (SKILLS_DIR / "acm-failure-classifier" / "references" / "phase-a-grouping.md").read_text()
    schema_md = (SKILLS_DIR / "acm-failure-classifier" / "references" / "output-schema.md").read_text()
    skill_md = (SKILLS_DIR / "acm-z-stream-analyzer" / "SKILL.md").read_text()
    assert "ABORTED" in phase_a and "short-circuit" in phase_a.lower()
    assert "pipeline_failure" in schema_md
    assert "ABORTED" in skill_md
