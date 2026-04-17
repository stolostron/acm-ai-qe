"""Tests for Pydantic data models — schema contract enforcement."""

import json
from pathlib import Path

import pytest

from src.models.analysis_result import AnalysisResult
from src.models.gather_output import GatherOptions, GatherOutput, PRData
from src.models.review_result import ReviewResult, ValidationIssue, Verdict


class TestGatherOutput:
    def test_minimal_valid(self):
        output = GatherOutput(jira_id="ACM-12345", run_dir="/tmp/test")
        assert output.jira_id == "ACM-12345"
        assert output.acm_version is None
        assert output.options.skip_live is False
        assert output.options.cluster_url is None

    def test_full_valid(self):
        output = GatherOutput(
            jira_id="ACM-30459",
            acm_version="2.17",
            area="governance",
            pr_data=PRData(number=5790, title="Labels PR"),
            existing_test_cases=["/path/to/test.md"],
            conventions="test conventions",
            area_knowledge="governance knowledge",
            html_templates="<html>",
            run_dir="/tmp/runs/ACM-30459/run-1",
            options=GatherOptions(skip_live=True, cluster_url="https://example.com", repo="stolostron/console"),
        )
        assert output.pr_data.number == 5790
        assert output.options.cluster_url == "https://example.com"

    def test_cluster_url_field_exists(self):
        opts = GatherOptions(cluster_url="https://console.example.com")
        assert opts.cluster_url == "https://console.example.com"

    def test_serialization_roundtrip(self):
        output = GatherOutput(jira_id="ACM-99999", run_dir="/tmp/test")
        json_str = json.dumps(output.model_dump(), default=str)
        data = json.loads(json_str)
        assert data["jira_id"] == "ACM-99999"
        assert "cluster_url" in data["options"]

    def test_existing_gather_output_valid(self):
        """Verify the real gather-output.json from an actual run matches the model."""
        runs_dir = Path(__file__).resolve().parent.parent.parent / "runs" / "ACM-30459"
        if not runs_dir.exists():
            pytest.skip("No real gather-output.json available")
        # Find any gather-output.json in ACM-30459 runs
        gather_files = list(runs_dir.glob("*/gather-output.json"))
        if not gather_files:
            pytest.skip("No real gather-output.json available")
        data = json.loads(gather_files[0].read_text())
        output = GatherOutput(**data)
        assert output.jira_id == "ACM-30459"


class TestReviewResult:
    def test_pass_verdict(self):
        result = ReviewResult(test_case_file="test.md", verdict=Verdict.PASS)
        assert result.verdict == Verdict.PASS
        assert len(result.blocking_issues) == 0

    def test_fail_with_blocking(self):
        result = ReviewResult(
            test_case_file="test.md",
            verdict=Verdict.FAIL,
            issues=[
                ValidationIssue(severity="blocking", category="title", message="Bad title"),
                ValidationIssue(severity="warning", category="setup", message="Missing setup"),
            ],
        )
        assert result.verdict == Verdict.FAIL
        assert len(result.blocking_issues) == 1
        assert len(result.warnings) == 1


class TestAnalysisResult:
    def test_minimal_valid(self):
        result = AnalysisResult(
            jira_id="ACM-30459",
            jira_summary="Test summary",
            acm_version="2.17",
            area="governance",
        )
        assert result.steps_count == 0
        assert result.complexity == "medium"
        assert result.live_validation_performed is False

    def test_full_valid(self):
        result = AnalysisResult(
            jira_id="ACM-30459",
            jira_summary="Labels for policy details",
            acm_version="2.17",
            area="governance",
            pr_number=5790,
            pr_repo="stolostron/console",
            test_case_file="test-case.md",
            steps_count=8,
            complexity="medium",
            routes_discovered=["/multicloud/governance/discovered/..."],
            translations_discovered={"table.labels": "Labels"},
            selectors_discovered=["acm-table-filter-select-Label"],
            existing_polarion_coverage=["RHACM4K-63381"],
            live_validation_performed=False,
            self_review_verdict="PASS",
        )
        assert result.pr_number == 5790
        assert len(result.routes_discovered) == 1

    def test_all_17_fields_present(self):
        result = AnalysisResult(
            jira_id="ACM-1", jira_summary="s", acm_version="2.17", area="governance",
        )
        dumped = result.model_dump()
        expected_keys = {
            "jira_id", "jira_summary", "acm_version", "area", "pr_number",
            "pr_repo", "test_case_file", "steps_count", "complexity",
            "routes_discovered", "translations_discovered", "selectors_discovered",
            "existing_polarion_coverage", "live_validation_performed",
            "self_review_verdict", "self_review_issues", "timestamp",
        }
        assert set(dumped.keys()) == expected_keys
