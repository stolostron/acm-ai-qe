"""Integration tests for deterministic pipeline stages.

Tests validate_artifact.py and review_enforcement.py against fixture
data. No MCP, JIRA, or cluster access needed.
"""

import importlib.util
import json
import shutil
import textwrap
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
SCRIPTS = Path(__file__).resolve().parents[4] / ".claude" / "skills" / "acm-test-case-generator" / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


validate_artifact = _load_module("validate_artifact", SCRIPTS / "validate_artifact.py")
review_enforcement = _load_module("review_enforcement", SCRIPTS / "review_enforcement.py")


pytestmark = pytest.mark.integration


class TestGatherOutputValidation:
    def test_valid_fixture_passes(self):
        ok, errors = validate_artifact.validate_artifact(
            FIXTURES / "gather-output.json", "gather-output"
        )
        assert ok, f"Expected PASS, got errors: {errors}"

    def test_missing_required_field_fails(self, tmp_path):
        data = json.loads((FIXTURES / "gather-output.json").read_text())
        del data["jira_id"]
        broken = tmp_path / "gather-output.json"
        broken.write_text(json.dumps(data))
        ok, errors = validate_artifact.validate_artifact(broken, "gather-output")
        assert not ok
        assert any("jira_id" in e for e in errors)


class TestPhaseArtifactValidation:
    @pytest.mark.parametrize("artifact,schema", [
        ("phase1-jira.json", "phase1-jira"),
        ("phase2-code.json", "phase2-code"),
        ("phase3-ui.json", "phase3-ui"),
    ])
    def test_valid_fixture_passes(self, artifact, schema):
        ok, errors = validate_artifact.validate_artifact(
            FIXTURES / artifact, schema
        )
        assert ok, f"{artifact} failed: {errors}"

    def test_empty_test_scenarios_fails(self, tmp_path):
        data = json.loads((FIXTURES / "phase1-jira.json").read_text())
        data["test_scenarios"] = []
        broken = tmp_path / "phase1-jira.json"
        broken.write_text(json.dumps(data))
        ok, errors = validate_artifact.validate_artifact(broken, "phase1-jira")
        assert not ok
        assert any("test_scenarios" in e for e in errors)

    def test_missing_pr_number_fails(self, tmp_path):
        data = json.loads((FIXTURES / "phase2-code.json").read_text())
        del data["pr"]["number"]
        broken = tmp_path / "phase2-code.json"
        broken.write_text(json.dumps(data))
        ok, errors = validate_artifact.validate_artifact(broken, "phase2-code")
        assert not ok
        assert any("number" in e for e in errors)


class TestPreSynthesisCheck:
    def test_valid_fixtures_pass(self, tmp_path):
        for fname in ["phase1-jira.json", "phase2-code.json", "phase3-ui.json"]:
            shutil.copy(FIXTURES / fname, tmp_path / fname)
        ok, errors = validate_artifact.check_pre_synthesis(tmp_path)
        assert ok, f"Pre-synthesis check failed: {errors}"

    def test_missing_file_fails(self, tmp_path):
        shutil.copy(FIXTURES / "phase1-jira.json", tmp_path / "phase1-jira.json")
        shutil.copy(FIXTURES / "phase2-code.json", tmp_path / "phase2-code.json")
        ok, errors = validate_artifact.check_pre_synthesis(tmp_path)
        assert not ok
        assert any("phase3-ui" in e.lower() for e in errors)


class TestReviewEnforcementIntegration:
    def test_passing_review(self):
        text = (FIXTURES / "review-pass.md").read_text()
        assert review_enforcement.count_mcp_verifications(text) >= 3
        assert review_enforcement.check_source_verification(text) is True
        assert review_enforcement.check_translation_verification(text) is True
        assert review_enforcement.extract_verdict(text) == "PASS"

    def test_failing_review_no_mcp(self):
        text = (FIXTURES / "review-fail-no-mcp.md").read_text()
        assert review_enforcement.count_mcp_verifications(text) == 0
        assert review_enforcement.check_source_verification(text) is False
        assert review_enforcement.check_translation_verification(text) is False

    def test_verdict_extraction(self):
        assert review_enforcement.extract_verdict("Verdict: PASS") == "PASS"
        assert review_enforcement.extract_verdict("Verdict: NEEDS_FIXES") == "NEEDS_FIXES"
        assert review_enforcement.extract_verdict("no verdict") == "UNKNOWN"

    def test_source_only_in_blocking_not_counted(self):
        text = textwrap.dedent("""\
            MCP VERIFICATIONS
            1. search_translations -- query: "test", result: found, matches: yes
            2. get_routes -- query: "gov", result: found, matches: yes

            BLOCKING (must fix):
            1. get_component_source shows mismatch

            Verdict: NEEDS_FIXES
        """)
        assert review_enforcement.check_source_verification(text) is False

    def test_translation_only_in_warning_not_counted(self):
        text = textwrap.dedent("""\
            MCP VERIFICATIONS
            1. get_routes -- query: "gov", result: found, matches: yes
            2. get_component_source -- path: "X.tsx", claim: Y, matches: yes

            WARNING (should fix):
            1. search_translations should verify this label

            Verdict: NEEDS_FIXES
        """)
        assert review_enforcement.check_translation_verification(text) is False
