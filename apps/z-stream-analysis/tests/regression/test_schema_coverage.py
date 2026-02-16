"""
Schema coverage tests.

Validates the JSON schema covers all fields that code can produce
and rejects invalid data.
"""

import json

import pytest

pytestmark = pytest.mark.regression

try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def _validate_against_schema(data, schema):
    """Validate data against JSON schema using jsonschema if available,
    otherwise do structural checks."""
    if HAS_JSONSCHEMA:
        jsonschema.validate(instance=data, schema=schema)
    else:
        # Fallback: check required fields
        required = schema.get("required", [])
        for field in required:
            assert field in data, f"Missing required field: {field}"


def _expect_validation_failure(data, schema):
    """Assert that data fails validation."""
    if HAS_JSONSCHEMA:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=data, schema=schema)
    else:
        pytest.skip("jsonschema not installed — cannot test rejection")


class TestSchemaIsValidJsonSchema:
    """Schema file parses as valid JSON Schema draft-07."""

    def test_schema_is_valid_json_schema(self, schema_data):
        assert schema_data.get("$schema") is not None, "Missing $schema field"
        assert "json-schema" in schema_data["$schema"], (
            "Not a JSON Schema draft reference"
        )
        assert schema_data.get("type") == "object", "Root type should be object"
        assert "properties" in schema_data, "Missing properties"
        assert "required" in schema_data, "Missing required array"


class TestNewPerTestFieldsInSchema:
    """prerequisite_analysis, playbook_investigation,
    cluster_investigation_detail all defined in per_test_analysis items."""

    EXPECTED_FIELDS = {
        "prerequisite_analysis",
        "playbook_investigation",
        "cluster_investigation_detail",
    }

    def test_new_per_test_fields_in_schema(self, schema_data):
        per_test = schema_data["properties"]["per_test_analysis"]
        item_props = per_test["items"]["properties"]

        missing = self.EXPECTED_FIELDS - set(item_props.keys())
        assert not missing, (
            f"per_test_analysis items missing new fields: {missing}"
        )


class TestClusterInvestigationSummaryInSchema:
    """cluster_investigation_summary defined at top level with expected
    subfields."""

    EXPECTED_SUBFIELDS = {
        "cluster_reauth_status",
        "investigation_mode",
        "tier_0_health",
    }

    def test_cluster_investigation_summary_in_schema(self, schema_data):
        props = schema_data["properties"]
        assert "cluster_investigation_summary" in props, (
            "Missing cluster_investigation_summary at top level"
        )

        summary_props = props["cluster_investigation_summary"]["properties"]
        missing = self.EXPECTED_SUBFIELDS - set(summary_props.keys())
        assert not missing, (
            f"cluster_investigation_summary missing subfields: {missing}"
        )


class TestClassificationEnumMatchesGuide:
    """The classification enum in schema matches all 7 categories."""

    EXPECTED = {
        "PRODUCT_BUG",
        "AUTOMATION_BUG",
        "INFRASTRUCTURE",
        "MIXED",
        "UNKNOWN",
        "NO_BUG",
        "FLAKY",
    }

    def test_classification_enum_matches_guide(self, schema_data):
        per_test_props = schema_data["properties"]["per_test_analysis"][
            "items"
        ]["properties"]
        classification_enum = set(
            per_test_props["classification"]["enum"]
        )

        missing = self.EXPECTED - classification_enum
        assert not missing, (
            f"Schema classification enum missing: {missing}"
        )

        extra = classification_enum - self.EXPECTED
        # Extra values (like REQUIRES_INVESTIGATION) are OK but note them
        if extra:
            import warnings
            warnings.warn(
                f"Schema classification enum has extra values: {extra}"
            )


class TestRequiredFieldsAreMinimal:
    """Only per_test_analysis, summary, investigation_phases_completed
    are required. All new fields are optional."""

    EXPECTED_REQUIRED = {
        "per_test_analysis",
        "summary",
        "investigation_phases_completed",
    }

    def test_required_fields_are_minimal(self, schema_data):
        required = set(schema_data["required"])
        assert required == self.EXPECTED_REQUIRED, (
            f"Expected required fields {self.EXPECTED_REQUIRED}, "
            f"got {required}"
        )


class TestSyntheticAnalysisValidates:
    """The synthetic analysis_results.json fixture validates
    against the schema."""

    def test_synthetic_analysis_validates(self, synthetic_analysis, schema_data):
        _validate_against_schema(synthetic_analysis, schema_data)


class TestMinimalAnalysisValidates:
    """A minimal analysis result (just required fields) also validates."""

    def test_minimal_analysis_validates(self, schema_data):
        minimal = {
            "investigation_phases_completed": ["A", "B", "C", "D", "E"],
            "per_test_analysis": [
                {
                    "test_name": "test_example",
                    "classification": "UNKNOWN",
                    "confidence": 0.5,
                    "evidence_sources": [
                        {"source": "console_log", "finding": "some finding"},
                        {"source": "test_code", "finding": "another finding"},
                    ],
                }
            ],
            "summary": {
                "by_classification": {
                    "UNKNOWN": 1,
                }
            },
        }
        _validate_against_schema(minimal, schema_data)


class TestSchemaRejectsWrongFieldNames:
    """An analysis with failed_tests instead of per_test_analysis
    fails validation."""

    def test_schema_rejects_wrong_field_names(self, schema_data):
        wrong = {
            "investigation_phases_completed": ["A"],
            "failed_tests": [{"test_name": "x"}],  # wrong field name
            "summary": {"by_classification": {}},
        }
        _expect_validation_failure(wrong, schema_data)
