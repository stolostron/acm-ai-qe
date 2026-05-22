"""Tests for validate_artifact.py schema validation."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / ".claude"
    / "skills"
    / "acm-test-case-generator"
    / "scripts"
    / "validate_artifact.py"
)


def _run(artifact_path: Path, schema: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(artifact_path), schema],
        capture_output=True,
        text=True,
    )


def _run_pre_synthesis(run_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--pre-synthesis", str(run_dir)],
        capture_output=True,
        text=True,
    )


def _write_json(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# --- Phase 2: JIRA ---


class TestPhase1Jira:
    VALID = {
        "story": {"key": "ACM-30459", "summary": "Labels field"},
        "acceptance_criteria": ["AC1"],
        "linked_tickets": {},
        "pr_references": [],
        "test_scenarios": ["scenario1"],
        "anomalies": [],
    }

    def test_valid_passes(self, tmp_path):
        result = _run(_write_json(tmp_path / "a.json", self.VALID), "phase1-jira")
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_missing_acceptance_criteria(self, tmp_path):
        data = {**self.VALID}
        del data["acceptance_criteria"]
        result = _run(_write_json(tmp_path / "a.json", data), "phase1-jira")
        assert result.returncode == 1
        assert "[MISSING] acceptance_criteria" in result.stdout

    def test_empty_test_scenarios(self, tmp_path):
        data = {**self.VALID, "test_scenarios": []}
        result = _run(_write_json(tmp_path / "a.json", data), "phase1-jira")
        assert result.returncode == 1
        assert "[EMPTY] test_scenarios" in result.stdout

    def test_story_missing_nested_key(self, tmp_path):
        data = {**self.VALID, "story": {"key": "ACM-1"}}
        result = _run(_write_json(tmp_path / "a.json", data), "phase1-jira")
        assert result.returncode == 1
        assert '[NESTED] story: missing required nested key "summary"' in result.stdout

    def test_story_key_null(self, tmp_path):
        data = {**self.VALID, "story": {"key": None, "summary": "x"}}
        result = _run(_write_json(tmp_path / "a.json", data), "phase1-jira")
        assert result.returncode == 1
        assert "[TYPE] story.key" in result.stdout

    def test_extra_keys_ignored(self, tmp_path):
        data = {**self.VALID, "extra_field": "ok"}
        result = _run(_write_json(tmp_path / "a.json", data), "phase1-jira")
        assert result.returncode == 0


# --- Phase 3: Code ---


class TestPhase2Code:
    VALID = {
        "pr": {"number": 5790, "repo": "stolostron/console", "title": "Labels"},
        "primary_files": ["src/a.tsx"],
        "translations": {},
        "test_scenarios": ["s1"],
        "anomalies": [],
    }

    def test_valid_passes(self, tmp_path):
        result = _run(_write_json(tmp_path / "a.json", self.VALID), "phase2-code")
        assert result.returncode == 0

    def test_missing_pr(self, tmp_path):
        data = {**self.VALID}
        del data["pr"]
        result = _run(_write_json(tmp_path / "a.json", data), "phase2-code")
        assert result.returncode == 1
        assert "[MISSING] pr" in result.stdout

    def test_pr_missing_number(self, tmp_path):
        data = {**self.VALID, "pr": {"repo": "r", "title": "t"}}
        result = _run(_write_json(tmp_path / "a.json", data), "phase2-code")
        assert result.returncode == 1
        assert "[NESTED] pr" in result.stdout

    def test_empty_primary_files(self, tmp_path):
        data = {**self.VALID, "primary_files": []}
        result = _run(_write_json(tmp_path / "a.json", data), "phase2-code")
        assert result.returncode == 1
        assert "[EMPTY] primary_files" in result.stdout


# --- Phase 4: UI ---


class TestPhase3UI:
    VALID = {
        "acm_version": "2.17",
        "routes": {"/governance": "/multicloud/governance"},
        "entry_point": "/multicloud/governance",
        "translations_verified": {},
        "anomalies": [],
    }

    def test_valid_passes(self, tmp_path):
        result = _run(_write_json(tmp_path / "a.json", self.VALID), "phase3-ui")
        assert result.returncode == 0

    def test_missing_acm_version(self, tmp_path):
        data = {**self.VALID}
        del data["acm_version"]
        result = _run(_write_json(tmp_path / "a.json", data), "phase3-ui")
        assert result.returncode == 1
        assert "[MISSING] acm_version" in result.stdout

    def test_empty_routes(self, tmp_path):
        data = {**self.VALID, "routes": {}}
        result = _run(_write_json(tmp_path / "a.json", data), "phase3-ui")
        assert result.returncode == 1
        assert "[EMPTY] routes" in result.stdout

    def test_missing_entry_point(self, tmp_path):
        data = {**self.VALID}
        del data["entry_point"]
        result = _run(_write_json(tmp_path / "a.json", data), "phase3-ui")
        assert result.returncode == 1
        assert "[MISSING] entry_point" in result.stdout


# --- Analysis Results ---


class TestAnalysisResults:
    VALID = {
        "jira_id": "ACM-30459",
        "acm_version": "2.17",
        "area": "governance",
        "steps_count": 8,
        "test_case_file": "test-case.md",
    }

    def test_valid_passes(self, tmp_path):
        result = _run(
            _write_json(tmp_path / "a.json", self.VALID), "analysis-results"
        )
        assert result.returncode == 0

    def test_jira_id_wrong_pattern(self, tmp_path):
        data = {**self.VALID, "jira_id": "PROJ-123"}
        result = _run(
            _write_json(tmp_path / "a.json", data), "analysis-results"
        )
        assert result.returncode == 1
        assert "[PATTERN] jira_id" in result.stdout

    def test_steps_count_zero(self, tmp_path):
        data = {**self.VALID, "steps_count": 0}
        result = _run(
            _write_json(tmp_path / "a.json", data), "analysis-results"
        )
        assert result.returncode == 1
        assert "[VALUE] steps_count" in result.stdout

    def test_missing_area(self, tmp_path):
        data = {**self.VALID}
        del data["area"]
        result = _run(
            _write_json(tmp_path / "a.json", data), "analysis-results"
        )
        assert result.returncode == 1
        assert "[MISSING] area" in result.stdout


# --- Synthesized Context (Markdown) ---


class TestSynthesizedContext:
    VALID_MD = (
        "# Synthesized Context\n\n"
        "## JIRA INVESTIGATION\nContent\n\n"
        "## CODE CHANGE ANALYSIS\nContent\n\n"
        "## UI DISCOVERY\nContent\n\n"
        "## TEST PLAN\nContent\n"
    )

    def test_valid_passes(self, tmp_path):
        f = tmp_path / "ctx.md"
        f.write_text(self.VALID_MD, encoding="utf-8")
        result = _run(f, "synthesized-context")
        assert result.returncode == 0

    def test_missing_section(self, tmp_path):
        f = tmp_path / "ctx.md"
        f.write_text("## JIRA INVESTIGATION\n## CODE CHANGE ANALYSIS\n", encoding="utf-8")
        result = _run(f, "synthesized-context")
        assert result.returncode == 1
        assert "[SECTION]" in result.stdout
        assert "UI DISCOVERY" in result.stdout

    def test_case_insensitive(self, tmp_path):
        f = tmp_path / "ctx.md"
        content = self.VALID_MD.replace("JIRA INVESTIGATION", "Jira Investigation")
        f.write_text(content, encoding="utf-8")
        result = _run(f, "synthesized-context")
        assert result.returncode == 0


# --- Gather Output ---


class TestGatherOutput:
    VALID = {
        "jira_id": "ACM-30459",
        "run_dir": "runs/ACM-30459/ACM-30459-2026-05-03",
        "timestamp": "2026-05-03T19:56:26",
        "options": {},
    }

    def test_valid_passes(self, tmp_path):
        result = _run(_write_json(tmp_path / "a.json", self.VALID), "gather-output")
        assert result.returncode == 0

    def test_missing_jira_id(self, tmp_path):
        data = {**self.VALID}
        del data["jira_id"]
        result = _run(_write_json(tmp_path / "a.json", data), "gather-output")
        assert result.returncode == 1
        assert "[MISSING] jira_id" in result.stdout


# --- Edge Cases ---


class TestEdgeCases:
    def test_nonexistent_file(self, tmp_path):
        result = _run(tmp_path / "nope.json", "phase1-jira")
        assert result.returncode == 1
        assert "not found" in result.stdout

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{broken", encoding="utf-8")
        result = _run(f, "phase1-jira")
        assert result.returncode == 1
        assert "[PARSE]" in result.stdout

    def test_unknown_schema(self, tmp_path):
        f = tmp_path / "a.json"
        f.write_text("{}", encoding="utf-8")
        result = _run(f, "nonexistent-schema")
        assert result.returncode == 1
        assert "Unknown schema" in result.stdout

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("", encoding="utf-8")
        result = _run(f, "phase1-jira")
        assert result.returncode == 1
        assert "[PARSE]" in result.stdout

    def test_json_array_root(self, tmp_path):
        f = tmp_path / "arr.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        result = _run(f, "phase1-jira")
        assert result.returncode == 1
        assert "[TYPE] Root" in result.stdout

    def test_null_value(self, tmp_path):
        data = {
            "story": None,
            "acceptance_criteria": [],
            "linked_tickets": {},
            "pr_references": [],
            "test_scenarios": [],
            "anomalies": [],
        }
        result = _run(_write_json(tmp_path / "a.json", data), "phase1-jira")
        assert result.returncode == 1
        assert "[TYPE] story: expected dict, got null" in result.stdout


# --- Output Format ---


class TestOutputFormat:
    def test_pass_format(self, tmp_path):
        data = {
            "jira_id": "ACM-1",
            "run_dir": "r",
            "timestamp": "t",
            "options": {},
        }
        result = _run(_write_json(tmp_path / "a.json", data), "gather-output")
        assert "VALIDATION: PASS" in result.stdout
        assert "Schema: gather-output" in result.stdout

    def test_fail_format(self, tmp_path):
        result = _run(_write_json(tmp_path / "a.json", {}), "gather-output")
        assert "VALIDATION: FAIL" in result.stdout
        assert "Errors:" in result.stdout

    def test_usage_with_no_args(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Usage:" in result.stdout

    def test_usage_shows_pre_synthesis(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
        )
        assert "--pre-synthesis" in result.stdout


# --- Pre-Synthesis Readiness ---


class TestPreSynthesis:
    VALID_JIRA = {
        "story": {"key": "ACM-30459", "summary": "Labels field"},
        "acceptance_criteria": ["AC1", "AC2"],
        "linked_tickets": {},
        "pr_references": [],
        "test_scenarios": ["s1"],
        "anomalies": [],
    }
    VALID_CODE = {
        "pr": {"number": 5790, "repo": "stolostron/console", "title": "Labels"},
        "primary_files": [{"path": "src/a.tsx", "changes": "added labels"}],
        "translations": {},
        "test_scenarios": ["s1"],
        "anomalies": [],
    }
    VALID_UI = {
        "acm_version": "2.17",
        "routes": {"governance": "/multicloud/governance"},
        "entry_point": "Governance > Policies > Details",
        "translations_verified": {},
        "anomalies": [],
    }

    def _setup_run(self, tmp_path, jira=None, code=None, ui=None):
        if jira is not None:
            _write_json(tmp_path / "phase1-jira.json", jira)
        if code is not None:
            _write_json(tmp_path / "phase2-code.json", code)
        if ui is not None:
            _write_json(tmp_path / "phase3-ui.json", ui)

    def test_all_valid_passes(self, tmp_path):
        self._setup_run(tmp_path, self.VALID_JIRA, self.VALID_CODE, self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 0
        assert "PASS" in result.stdout
        assert "pre-synthesis" in result.stdout

    def test_missing_jira_file(self, tmp_path):
        self._setup_run(tmp_path, code=self.VALID_CODE, ui=self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "[FILE] phase1-jira.json" in result.stdout

    def test_missing_code_file(self, tmp_path):
        self._setup_run(tmp_path, jira=self.VALID_JIRA, ui=self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "[FILE] phase2-code.json" in result.stdout

    def test_missing_ui_file(self, tmp_path):
        self._setup_run(tmp_path, jira=self.VALID_JIRA, code=self.VALID_CODE)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "[FILE] phase3-ui.json" in result.stdout

    def test_empty_acceptance_criteria(self, tmp_path):
        jira = {**self.VALID_JIRA, "acceptance_criteria": []}
        self._setup_run(tmp_path, jira, self.VALID_CODE, self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "[MINIMUM]" in result.stdout
        assert "acceptance_criteria" in result.stdout

    def test_missing_story_key(self, tmp_path):
        jira = {**self.VALID_JIRA, "story": {"summary": "Labels"}}
        self._setup_run(tmp_path, jira, self.VALID_CODE, self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "story.key" in result.stdout

    def test_missing_story_summary(self, tmp_path):
        jira = {**self.VALID_JIRA, "story": {"key": "ACM-1"}}
        self._setup_run(tmp_path, jira, self.VALID_CODE, self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "story.summary" in result.stdout

    def test_missing_pr_number(self, tmp_path):
        code = {**self.VALID_CODE, "pr": {"repo": "r", "title": "t"}}
        self._setup_run(tmp_path, self.VALID_JIRA, code, self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "pr.number" in result.stdout

    def test_missing_pr_repo(self, tmp_path):
        code = {**self.VALID_CODE, "pr": {"number": 1, "title": "t"}}
        self._setup_run(tmp_path, self.VALID_JIRA, code, self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "pr.repo" in result.stdout

    def test_empty_primary_files(self, tmp_path):
        code = {**self.VALID_CODE, "primary_files": []}
        self._setup_run(tmp_path, self.VALID_JIRA, code, self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "primary_files" in result.stdout

    def test_missing_entry_point(self, tmp_path):
        ui = {**self.VALID_UI}
        del ui["entry_point"]
        self._setup_run(tmp_path, self.VALID_JIRA, self.VALID_CODE, ui)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "entry_point" in result.stdout

    def test_empty_routes(self, tmp_path):
        ui = {**self.VALID_UI, "routes": {}}
        self._setup_run(tmp_path, self.VALID_JIRA, self.VALID_CODE, ui)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "routes" in result.stdout

    def test_multiple_failures_reported(self, tmp_path):
        jira = {**self.VALID_JIRA, "acceptance_criteria": []}
        ui = {**self.VALID_UI, "routes": {}}
        self._setup_run(tmp_path, jira, self.VALID_CODE, ui)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "acceptance_criteria" in result.stdout
        assert "routes" in result.stdout

    def test_extra_fields_ignored(self, tmp_path):
        jira = {**self.VALID_JIRA, "extra": "ok"}
        code = {**self.VALID_CODE, "extra": "ok"}
        ui = {**self.VALID_UI, "extra": "ok"}
        self._setup_run(tmp_path, jira, code, ui)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 0

    def test_invalid_json_in_artifact(self, tmp_path):
        _write_json(tmp_path / "phase1-jira.json", self.VALID_JIRA)
        (tmp_path / "phase2-code.json").write_text("{broken", encoding="utf-8")
        _write_json(tmp_path / "phase3-ui.json", self.VALID_UI)
        result = _run_pre_synthesis(tmp_path)
        assert result.returncode == 1
        assert "[FILE] phase2-code.json" in result.stdout
