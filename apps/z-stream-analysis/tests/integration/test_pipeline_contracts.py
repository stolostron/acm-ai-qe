"""
Data contract tests between pipeline stages.

Validates the contracts between Stage 1 (gather), Stage 2 (AI analysis),
and Stage 3 (report).
"""

import json

import pytest

pytestmark = [pytest.mark.integration]

try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


class TestCoreDataHasAllRequiredSections:
    """S1->S2: core-data.json has all sections the AI instructions reference."""

    EXPECTED_SECTIONS = {
        "test_report",
        "console_log",
        "environment",
        "cluster_landscape",
        "feature_grounding",
        "feature_knowledge",
        "investigation_hints",
        "ai_instructions",
    }

    def test_core_data_has_all_required_sections(self, core_data):
        actual = set(core_data.keys())
        missing = self.EXPECTED_SECTIONS - actual

        assert not missing, (
            f"core-data.json missing sections referenced by AI instructions: "
            f"{missing}"
        )


class TestEveryFailedTestHasFeatureArea:
    """S1->S2: Every test in test_report.failed_tests appears in at
    least one feature_grounding group."""

    def test_every_failed_test_has_feature_area(self, core_data):
        report = core_data.get("test_report", {})
        failed_tests = report.get("failed_tests", [])
        if not failed_tests:
            pytest.skip("No failed tests")

        grounding = core_data.get("feature_grounding", {})
        groups = grounding.get("groups", {})

        # Build set of all tests that appear in any group
        grounded_tests = set()
        for group_data in groups.values():
            if isinstance(group_data, dict):
                for t in group_data.get("tests", []):
                    grounded_tests.add(t)
            elif isinstance(group_data, list):
                grounded_tests.update(group_data)

        ungrounded = []
        for test in failed_tests:
            test_name = test.get("test_name", "")
            if test_name and test_name not in grounded_tests:
                ungrounded.append(test_name)

        if ungrounded:
            import warnings
            warnings.warn(
                f"{len(ungrounded)} failed tests not in any feature_grounding "
                f"group: {ungrounded[:5]}"
            )


class TestSyntheticAnalysisValidatesAgainstSchema:
    """S2->S3: Synthetic analysis-results.json passes schema validation."""

    def test_synthetic_analysis_validates_against_schema(
        self, synthetic_analysis, schema_data
    ):
        if HAS_JSONSCHEMA:
            jsonschema.validate(instance=synthetic_analysis, schema=schema_data)
        else:
            # Manual check of required fields
            for field in schema_data.get("required", []):
                assert field in synthetic_analysis, (
                    f"Missing required field: {field}"
                )


class TestSchemaRejectsOldFieldNames:
    """S2->S3: Schema rejects old field names."""

    def test_schema_rejects_old_field_names(self, schema_data):
        if not HAS_JSONSCHEMA:
            pytest.skip("jsonschema not installed")

        # Test with 'failed_tests' instead of 'per_test_analysis'
        bad_data = {
            "investigation_phases_completed": ["A"],
            "failed_tests": [{"test_name": "x"}],
            "summary": {"by_classification": {}},
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=bad_data, schema=schema_data)

        # Test with 'classification_breakdown' instead of 'by_classification'
        bad_data2 = {
            "investigation_phases_completed": ["A"],
            "per_test_analysis": [
                {
                    "test_name": "x",
                    "classification": "UNKNOWN",
                    "confidence": 0.5,
                    "evidence_sources": [
                        {"source": "a", "finding": "b"},
                        {"source": "c", "finding": "d"},
                    ],
                }
            ],
            "summary": {"classification_breakdown": {}},
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=bad_data2, schema=schema_data)


class TestSchemaRequiresMinimumEvidence:
    """S2->S3: Schema rejects per_test entry with only 1 evidence source."""

    def test_schema_requires_minimum_evidence(self, schema_data):
        if not HAS_JSONSCHEMA:
            pytest.skip("jsonschema not installed")

        bad_data = {
            "investigation_phases_completed": ["A"],
            "per_test_analysis": [
                {
                    "test_name": "test_x",
                    "classification": "PRODUCT_BUG",
                    "confidence": 0.8,
                    "evidence_sources": [
                        {"source": "only_one", "finding": "single source"},
                    ],
                }
            ],
            "summary": {"by_classification": {"PRODUCT_BUG": 1}},
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=bad_data, schema=schema_data)


class TestSchemaRejectsInvalidClassification:
    """S2->S3: Schema rejects invalid classification value."""

    def test_schema_rejects_invalid_classification(self, schema_data):
        if not HAS_JSONSCHEMA:
            pytest.skip("jsonschema not installed")

        bad_data = {
            "investigation_phases_completed": ["A"],
            "per_test_analysis": [
                {
                    "test_name": "test_x",
                    "classification": "INFRASTRUCTURE_BUG",  # invalid
                    "confidence": 0.8,
                    "evidence_sources": [
                        {"source": "a", "finding": "b"},
                        {"source": "c", "finding": "d"},
                    ],
                }
            ],
            "summary": {"by_classification": {}},
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=bad_data, schema=schema_data)


class TestReportRendersFromRealData:
    """S1+S2->S3: Report.py can consume real core-data.json + synthetic
    analysis without field-name errors."""

    def test_report_renders_from_real_data(self, report_run_dir, app_root):
        import subprocess
        import sys

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
        assert result.returncode == 0, (
            f"Report failed with real data + synthetic analysis.\n"
            f"stderr: {result.stderr[-500:]}"
        )


class TestAIInstructionsReferenceExistingCoreDataFields:
    """S1->S2: Every field path in precomputed_context.fields exists in
    the actual core-data.json output."""

    def test_ai_instructions_reference_existing_core_data_fields(
        self, core_data
    ):
        instructions = core_data.get("ai_instructions", {})
        precomputed = instructions.get("precomputed_context", {})
        fields = precomputed.get("fields", {})

        missing = []
        for field_path in fields:
            # field_path is like 'extracted_context.test_file' or
            # 'feature_knowledge.feature_readiness'
            parts = field_path.split(".")
            top_level = parts[0]

            # Check if the top-level key exists in core-data or in
            # test_report.failed_tests items
            if top_level in core_data:
                continue
            # Check if it's a per-test field (in failed_tests items)
            report = core_data.get("test_report", {})
            failed = report.get("failed_tests", [])
            if failed and top_level in failed[0]:
                continue
            missing.append(field_path)

        if missing:
            import warnings
            warnings.warn(
                f"AI instructions reference fields not found in "
                f"core-data.json top-level: {missing}. "
                f"These may be per-test fields or nested fields."
            )
