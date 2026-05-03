"""Tests for artifact completeness checking in report.py."""

from pathlib import Path

import pytest

from src.scripts.report import check_artifact_completeness


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    return tmp_path


def _touch(run_dir: Path, *names: str):
    for name in names:
        (run_dir / name).write_text("", encoding="utf-8")


class TestAppPipelineNames:
    """App pipeline uses phase1-*, phase2-*, phase3-*, phase4.5-* names."""

    def test_all_present(self, run_dir):
        _touch(
            run_dir,
            "gather-output.json",
            "pr-diff.txt",
            "phase1-feature-investigation.md",
            "phase1-code-change-analysis.md",
            "phase1-ui-discovery.md",
            "phase2-synthesized-context.md",
            "phase3-live-validation.md",
            "test-case.md",
            "phase4.5-quality-review.md",
        )
        result = check_artifact_completeness(run_dir)
        assert result["artifacts_present"] == 9
        assert result["artifacts_expected"] == 9
        assert result["artifacts_missing"] == []
        assert result["pipeline_complete"] is True

    def test_missing_live_validation(self, run_dir):
        _touch(
            run_dir,
            "gather-output.json",
            "pr-diff.txt",
            "phase1-feature-investigation.md",
            "phase1-code-change-analysis.md",
            "phase1-ui-discovery.md",
            "phase2-synthesized-context.md",
            "test-case.md",
            "phase4.5-quality-review.md",
        )
        result = check_artifact_completeness(run_dir)
        assert result["artifacts_present"] == 8
        assert result["artifacts_missing"] == ["phase3-live-validation.md"]
        assert result["pipeline_complete"] is False


class TestPortableSkillNames:
    """Portable skill uses phase2-jira.json, phase3-code.json, etc."""

    def test_all_present(self, run_dir):
        _touch(
            run_dir,
            "gather-output.json",
            "pr-diff.txt",
            "phase2-jira.json",
            "phase3-code.json",
            "phase4-ui.json",
            "synthesized-context.md",
            "phase6-live-validation.md",
            "test-case.md",
            "phase8-review.md",
        )
        result = check_artifact_completeness(run_dir)
        assert result["artifacts_present"] == 9
        assert result["artifacts_expected"] == 9
        assert result["artifacts_missing"] == []
        assert result["pipeline_complete"] is True

    def test_missing_live_validation(self, run_dir):
        _touch(
            run_dir,
            "gather-output.json",
            "pr-diff.txt",
            "phase2-jira.json",
            "phase3-code.json",
            "phase4-ui.json",
            "synthesized-context.md",
            "test-case.md",
            "phase8-review.md",
        )
        result = check_artifact_completeness(run_dir)
        assert result["artifacts_present"] == 8
        assert result["artifacts_missing"] == ["phase3-live-validation.md"]
        assert result["pipeline_complete"] is False


class TestMixedNames:
    """Run directory with a mix of both naming schemes."""

    def test_prefers_first_found(self, run_dir):
        _touch(
            run_dir,
            "gather-output.json",
            "pr-diff.txt",
            "phase1-feature-investigation.md",
            "phase3-code.json",
            "phase4-ui.json",
            "phase2-synthesized-context.md",
            "phase6-live-validation.md",
            "test-case.md",
            "phase4.5-quality-review.md",
        )
        result = check_artifact_completeness(run_dir)
        assert result["artifacts_present"] == 9
        assert result["pipeline_complete"] is True


class TestEmptyRunDir:
    """Run directory with no artifacts."""

    def test_nothing_present(self, run_dir):
        result = check_artifact_completeness(run_dir)
        assert result["artifacts_present"] == 0
        assert result["artifacts_expected"] == 9
        assert len(result["artifacts_missing"]) == 9
        assert result["pipeline_complete"] is False

    def test_missing_reports_primary_name(self, run_dir):
        result = check_artifact_completeness(run_dir)
        assert "phase1-feature-investigation.md" in result["artifacts_missing"]
        assert "phase2-jira.json" not in result["artifacts_missing"]
