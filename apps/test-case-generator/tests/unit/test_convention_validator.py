"""Tests for convention_validator.py structural validation."""

import tempfile
import textwrap
from pathlib import Path

import pytest

from src.services.convention_validator import validate_test_case


@pytest.fixture
def valid_test_case(tmp_path: Path) -> str:
    """A fully valid test case that should pass all checks."""
    content = textwrap.dedent("""\
        # RHACM4K-99999 - [GRC-2.17] Governance - Sample Test

        **Polarion ID:** RHACM4K-99999
        **Status:** Draft
        **Created:** 2026-01-01
        **Updated:** 2026-01-01

        ---

        ## Type: Test Case
        ## Level: System
        ## Component: Governance
        ## Subcomponent: Policies
        ## Test Type: Functional
        ## Pos/Neg: Positive
        ## Importance: High
        ## Automation: Not Automated
        ## Tags: ui, governance
        ## Release: 2.17

        ---

        ## Description

        This test validates sample functionality.

        This test verifies:
        1. Item one
        2. Item two

        **Entry Point:** Governance → Policies
        **Dev JIRA Coverage:**
        - Primary: ACM-99999

        ---

        ## Setup

        ```bash
        # 1. Verify ACM version
        oc get mch -n open-cluster-management
        # Expected: Running
        ```

        ---

        ## Test Steps

        ### Step 1: Navigate to page

        1. Log in as cluster-admin.
        2. Navigate to Governance.

        **Expected Result:**
        - Page loads.

        ---

        ### Step 2: Verify element

        1. Click on the element.
        2. Observe the result.

        **Expected Result:**
        - Element is visible.

        ---

        ## Teardown

        ```bash
        oc delete policy test-policy -n default --ignore-not-found
        ```
    """)
    path = tmp_path / "test-case.md"
    path.write_text(content)
    return str(path)


@pytest.fixture
def minimal_broken_case(tmp_path: Path) -> str:
    """A test case missing key elements."""
    content = textwrap.dedent("""\
        # Wrong Title Format

        Some content without any structure.
    """)
    path = tmp_path / "broken.md"
    path.write_text(content)
    return str(path)


class TestValidTestCase:
    def test_valid_case_passes(self, valid_test_case):
        result = validate_test_case(valid_test_case, area="governance")
        assert result.verdict.value == "PASS"
        assert len(result.blocking_issues) == 0

    def test_valid_case_step_count(self, valid_test_case):
        result = validate_test_case(valid_test_case)
        assert result.total_steps == 2

    def test_valid_case_metadata_complete(self, valid_test_case):
        result = validate_test_case(valid_test_case)
        assert result.metadata_complete is True
        assert result.title_pattern_valid is True
        assert result.entry_point_present is True
        assert result.jira_coverage_present is True
        assert result.teardown_present is True

    def test_valid_case_no_warnings(self, valid_test_case):
        result = validate_test_case(valid_test_case, area="governance")
        assert len(result.warnings) == 0


class TestTitleValidation:
    def test_missing_rhacm_prefix(self, minimal_broken_case):
        result = validate_test_case(minimal_broken_case)
        assert result.verdict.value == "FAIL"
        blocking_msgs = [i.message for i in result.blocking_issues]
        assert any("# RHACM4K-" in m for m in blocking_msgs)

    def test_wrong_area_tag(self, valid_test_case):
        result = validate_test_case(valid_test_case, area="rbac")
        tag_warnings = [i for i in result.warnings if i.category == "title"]
        assert len(tag_warnings) == 1
        assert "rbac" in tag_warnings[0].message

    def test_correct_area_tag(self, valid_test_case):
        result = validate_test_case(valid_test_case, area="governance")
        tag_warnings = [i for i in result.warnings if i.category == "title"]
        assert len(tag_warnings) == 0

    def test_no_area_skips_tag_check(self, valid_test_case):
        result = validate_test_case(valid_test_case, area=None)
        tag_warnings = [i for i in result.warnings if "tag" in i.message.lower()]
        assert len(tag_warnings) == 0


class TestPerStepValidation:
    def test_missing_expected_result_is_blocking(self, tmp_path):
        content = textwrap.dedent("""\
            # RHACM4K-11111 - [GRC-2.17] Governance - Test

            **Polarion ID:** RHACM4K-11111
            **Status:** Draft
            **Created:** 2026-01-01
            **Updated:** 2026-01-01

            ## Type: Test Case
            ## Level: System
            ## Component: Governance
            ## Subcomponent: Policies
            ## Test Type: Functional
            ## Pos/Neg: Positive
            ## Importance: High
            ## Automation: Not Automated
            ## Tags: ui
            ## Release: 2.17

            ## Description

            Test description.
            **Entry Point:** Page
            **Dev JIRA Coverage:** ACM-11111

            ## Setup

            ```bash
            # 1. Setup
            echo hello
            # Expected: hello
            ```

            ## Test Steps

            ### Step 1: Do something

            Click a button.

            ### Step 2: Do another thing

            Click another button.

            ## Teardown

            No cleanup needed.
        """)
        path = tmp_path / "no-expected.md"
        path.write_text(content)
        result = validate_test_case(str(path))
        assert result.verdict.value == "FAIL"
        blocking_msgs = [i.message for i in result.blocking_issues]
        assert any("Step 1" in m and "Expected Result" in m for m in blocking_msgs)
        assert any("Step 2" in m and "Expected Result" in m for m in blocking_msgs)


class TestTeardownValidation:
    def test_delete_without_ignore_not_found(self, tmp_path):
        content = textwrap.dedent("""\
            # RHACM4K-22222 - [GRC-2.17] Governance - Test

            **Polarion ID:** RHACM4K-22222
            **Status:** Draft
            **Created:** 2026-01-01
            **Updated:** 2026-01-01

            ## Type: Test Case
            ## Level: System
            ## Component: Governance
            ## Subcomponent: Policies
            ## Test Type: Functional
            ## Pos/Neg: Positive
            ## Importance: High
            ## Automation: Not Automated
            ## Tags: ui
            ## Release: 2.17

            ## Description

            Test.
            **Entry Point:** Page
            **Dev JIRA Coverage:** ACM-22222

            ## Setup

            ```bash
            # 1. Setup
            echo test
            # Expected: test
            ```

            ## Test Steps

            ### Step 1: Action

            1. Do something.

            **Expected Result:**
            - Something happens.

            ## Teardown

            ```bash
            oc delete policy test-policy -n default
            ```
        """)
        path = tmp_path / "bad-teardown.md"
        path.write_text(content)
        result = validate_test_case(str(path))
        warnings = [i for i in result.warnings if i.category == "teardown"]
        assert len(warnings) == 1
        assert "--ignore-not-found" in warnings[0].message


class TestFileNotFound:
    def test_nonexistent_file(self):
        result = validate_test_case("/nonexistent/path.md")
        assert result.verdict.value == "FAIL"
        assert len(result.blocking_issues) == 1
        assert "not found" in result.blocking_issues[0].message.lower()


def _find_approved_test_case() -> Path | None:
    """Dynamically find the approved ACM-30459 test case."""
    runs_dir = Path(__file__).resolve().parent.parent.parent / "runs" / "ACM-30459"
    if not runs_dir.exists():
        return None
    for run_dir in sorted(runs_dir.iterdir(), reverse=True):
        tc = run_dir / "test-case.md"
        if tc.exists():
            return tc
    return None


class TestApprovedTestCase:
    """Validate the approved ACM-30459 test case passes all checks."""

    def test_approved_case_passes(self):
        approved = _find_approved_test_case()
        if approved is None:
            pytest.skip("Approved test case not available")
        result = validate_test_case(str(approved), area="governance")
        assert result.verdict.value == "PASS"
        assert result.total_steps == 8
        assert len(result.blocking_issues) == 0

    def test_sample_case_passes(self):
        sample = Path(__file__).resolve().parent.parent.parent / "knowledge" / "examples" / "sample-test-case.md"
        if not sample.exists():
            pytest.skip("Sample test case not available")
        result = validate_test_case(str(sample), area="governance")
        assert result.verdict.value == "PASS"
        assert result.total_steps == 6
        assert len(result.blocking_issues) == 0
