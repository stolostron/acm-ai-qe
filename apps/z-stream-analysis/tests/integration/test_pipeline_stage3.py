"""
Stage 3 report integration tests.

Uses real gathered data + synthetic analysis to test report generation.
"""

import json
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module")
def report_output(report_run_dir, app_root):
    """Run report.py on the prepared run directory."""
    result = subprocess.run(
        [
            sys.executable, "-m", "src.scripts.report",
            str(report_run_dir),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(app_root),
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "run_dir": report_run_dir,
    }


class TestReportGeneratesWithoutError:
    def test_report_generates_without_error(self, report_output):
        assert report_output["returncode"] == 0, (
            f"report.py failed with rc={report_output['returncode']}.\n"
            f"stderr: {report_output['stderr'][-500:]}"
        )


class TestDetailedAnalysisFileCreated:
    def test_detailed_analysis_file_created(self, report_output):
        path = report_output["run_dir"] / "Detailed-Analysis.md"
        assert path.exists(), "Detailed-Analysis.md not created"


class TestPerTestBreakdownFileCreated:
    def test_per_test_breakdown_file_created(self, report_output):
        path = report_output["run_dir"] / "per-test-breakdown.json"
        assert path.exists(), "per-test-breakdown.json not created"


class TestSummaryFileCreated:
    def test_summary_file_created(self, report_output):
        path = report_output["run_dir"] / "SUMMARY.txt"
        assert path.exists(), "SUMMARY.txt not created"


class TestReportContainsHeader:
    def test_report_contains_header(self, report_output):
        path = report_output["run_dir"] / "Detailed-Analysis.md"
        if not path.exists():
            pytest.skip("Report file not generated")
        content = path.read_text()
        assert "# Pipeline Failure Analysis Report" in content


class TestReportContainsFeatureKnowledgeSection:
    def test_report_contains_feature_knowledge_section(self, report_output):
        path = report_output["run_dir"] / "Detailed-Analysis.md"
        if not path.exists():
            pytest.skip("Report file not generated")
        content = path.read_text()
        assert "## Feature Knowledge & Cluster Investigation" in content


class TestReportContainsPrerequisitesTable:
    def test_report_contains_prerequisites_table(self, report_output):
        path = report_output["run_dir"] / "Detailed-Analysis.md"
        if not path.exists():
            pytest.skip("Report file not generated")
        content = path.read_text()
        assert "### Prerequisites" in content
        assert "| Feature" in content


class TestReportContainsComponentHealthTable:
    def test_report_contains_component_health_table(self, report_output):
        path = report_output["run_dir"] / "Detailed-Analysis.md"
        if not path.exists():
            pytest.skip("Report file not generated")
        content = path.read_text()
        assert "### Component Health" in content


class TestReportContainsPlaybookInvestigationsTable:
    def test_report_contains_playbook_investigations_table(self, report_output):
        path = report_output["run_dir"] / "Detailed-Analysis.md"
        if not path.exists():
            pytest.skip("Report file not generated")
        content = path.read_text()
        assert "### Playbook Investigations" in content


class TestReportContainsClusterAccessStatus:
    def test_report_contains_cluster_access_status(self, report_output):
        path = report_output["run_dir"] / "Detailed-Analysis.md"
        if not path.exists():
            pytest.skip("Report file not generated")
        content = path.read_text()
        assert "Cluster Access:" in content


class TestReportContainsPerTestClassifications:
    def test_report_contains_per_test_classifications(self, report_output):
        path = report_output["run_dir"] / "Detailed-Analysis.md"
        if not path.exists():
            pytest.skip("Report file not generated")
        content = path.read_text()
        # report.py renders classifications with spaces (replace('_', ' '))
        assert any(
            cls in content
            for cls in [
                "PRODUCT BUG",
                "AUTOMATION BUG",
                "INFRASTRUCTURE",
            ]
        )


class TestPerTestBreakdownIsValidJson:
    def test_per_test_breakdown_is_valid_json(self, report_output):
        path = report_output["run_dir"] / "per-test-breakdown.json"
        if not path.exists():
            pytest.skip("Breakdown file not generated")
        data = json.loads(path.read_text())
        assert isinstance(data, dict)

    def test_per_test_breakdown_has_metadata(self, report_output):
        path = report_output["run_dir"] / "per-test-breakdown.json"
        if not path.exists():
            pytest.skip("Breakdown file not generated")
        data = json.loads(path.read_text())
        assert "metadata" in data

    def test_per_test_breakdown_has_all_tests(self, report_output):
        path = report_output["run_dir"] / "per-test-breakdown.json"
        if not path.exists():
            pytest.skip("Breakdown file not generated")
        data = json.loads(path.read_text())
        # report.py writes the key as 'per_test_breakdown'
        per_test = data.get("per_test_breakdown", [])
        assert isinstance(per_test, list)
        assert len(per_test) > 0, "per_test_breakdown should have entries"
