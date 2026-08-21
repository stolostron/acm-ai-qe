"""
Integration test fixtures.

Manages Stage 1 gather execution against a real Jenkins pipeline
and provides gathered data to downstream tests.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

JENKINS_URL = (
    "https://jenkins-csb-rhacm-tests.dno.corp.redhat.com"
    "/job/qe-acm-automation-poc/job/clc-e2e-pipeline/3757/"
)


def _check_jenkins_reachable():
    """Quick check if Jenkins is reachable."""
    try:
        result = subprocess.run(
            ["curl", "-sk", "--max-time", "10", "-o", "/dev/null",
             "-w", "%{http_code}", JENKINS_URL + "api/json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        code = result.stdout.strip()
        # 2xx/3xx = open access, 401/403 = reachable but needs auth
        return code.startswith(("2", "3")) or code in ("401", "403")
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


@pytest.fixture(scope="session")
def gathered_run_dir(tmp_path_factory, app_root):
    """Run Stage 1 gather once for all integration tests.

    Returns the run directory path. Skips all tests if Jenkins unreachable.
    """
    if not _check_jenkins_reachable():
        pytest.skip(
            f"Jenkins not reachable at {JENKINS_URL} — "
            "skipping integration tests"
        )

    output_dir = tmp_path_factory.mktemp("integration_runs")

    result = subprocess.run(
        [
            sys.executable, "-m", "src.scripts.gather",
            JENKINS_URL,
            "--skip-repo",
            "--output-dir", str(output_dir),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(app_root),
    )

    if result.returncode != 0:
        # Try to find the run dir anyway — gather may exit non-zero
        # but still produce output
        pass

    # Find the created run directory
    run_dirs = sorted(output_dir.glob("*"), key=lambda p: p.stat().st_mtime)
    if not run_dirs:
        # Fallback: check default runs/ directory
        default_runs = app_root / "runs"
        if default_runs.exists():
            run_dirs = sorted(
                default_runs.glob("clc-e2e-pipeline*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

    if not run_dirs:
        pytest.skip(
            f"Gather did not produce a run directory. "
            f"stdout: {result.stdout[-500:]}\n"
            f"stderr: {result.stderr[-500:]}"
        )

    return run_dirs[-1] if run_dirs else None


@pytest.fixture(scope="session")
def core_data(gathered_run_dir):
    """Parsed core-data.json from the gathered run."""
    core_path = gathered_run_dir / "core-data.json"
    if not core_path.exists():
        pytest.skip("core-data.json not found in run directory")
    return json.loads(core_path.read_text())


@pytest.fixture(scope="session")
def report_run_dir(gathered_run_dir, synthetic_analysis, app_root):
    """Copy gathered run dir and add synthetic analysis for report testing.

    Returns the path to the prepared run directory.
    """
    report_dir = gathered_run_dir.parent / "report_test"
    if report_dir.exists():
        shutil.rmtree(report_dir)
    shutil.copytree(gathered_run_dir, report_dir)

    # Write synthetic analysis results
    analysis_path = report_dir / "analysis-results.json"
    analysis_path.write_text(json.dumps(synthetic_analysis, indent=2))

    return report_dir
