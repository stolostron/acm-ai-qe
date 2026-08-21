"""
Playbook quality tests.

Structural and content validation of YAML playbooks to catch:
- Missing required sections
- Invalid classification/confidence values
- Broken symptom regexes
- Overlapping failure paths
"""

import re

import pytest

pytestmark = pytest.mark.regression

VALID_CLASSIFICATIONS = {
    "PRODUCT_BUG",
    "AUTOMATION_BUG",
    "INFRASTRUCTURE",
    "MIXED",
    "UNKNOWN",
    "NO_BUG",
    "FLAKY",
}

VALID_CATEGORIES = {
    "prerequisite",
    "component_health",
    "data_flow",
    "configuration",
    "connectivity",
}


class TestAllProfilesHaveRequiredSections:
    """Every profile must have architecture, prerequisites, failure_paths."""

    def test_all_profiles_have_required_sections(self, all_playbook_profiles):
        issues = []
        for name, profile in all_playbook_profiles.items():
            arch = profile.get("architecture")
            if not arch:
                issues.append(f"{name}: missing 'architecture'")
            else:
                for field in ("summary", "key_insight", "key_components"):
                    if field not in arch:
                        issues.append(f"{name}: architecture missing '{field}'")

            if "prerequisites" not in profile:
                issues.append(f"{name}: missing 'prerequisites'")

            if "failure_paths" not in profile:
                issues.append(f"{name}: missing 'failure_paths'")

        assert not issues, f"Profile structural issues: {issues}"


class TestAllFailurePathsHaveRequiredFields:
    """Every failure path has id, description, category, symptoms,
    classification, confidence, explanation."""

    REQUIRED_FIELDS = {
        "id",
        "description",
        "category",
        "symptoms",
        "classification",
        "confidence",
        "explanation",
    }

    def test_all_failure_paths_have_required_fields(self, all_playbook_profiles):
        issues = []
        for name, profile in all_playbook_profiles.items():
            for path in profile.get("failure_paths", []):
                path_id = path.get("id", "<no id>")
                for field in self.REQUIRED_FIELDS:
                    if field not in path:
                        issues.append(f"{name}/{path_id}: missing '{field}'")

                # symptoms must be non-empty
                symptoms = path.get("symptoms", [])
                if not symptoms:
                    issues.append(f"{name}/{path_id}: 'symptoms' is empty")

        assert not issues, f"Failure path field issues: {issues}"


class TestClassificationValuesAreValidEnums:
    """Classification in every failure path is one of the valid enums."""

    def test_classification_values_are_valid_enums(self, all_playbook_profiles):
        invalid = []
        for name, profile in all_playbook_profiles.items():
            for path in profile.get("failure_paths", []):
                classification = path.get("classification", "")
                if classification not in VALID_CLASSIFICATIONS:
                    invalid.append(
                        f"{name}/{path.get('id', '?')}: '{classification}'"
                    )

        assert not invalid, (
            f"Invalid classification values: {invalid}. "
            f"Valid: {VALID_CLASSIFICATIONS}"
        )


class TestConfidenceValuesInRange:
    """Every confidence is between 0.0 and 1.0."""

    def test_confidence_values_in_range(self, all_playbook_profiles):
        out_of_range = []
        for name, profile in all_playbook_profiles.items():
            for path in profile.get("failure_paths", []):
                conf = path.get("confidence")
                if conf is not None:
                    if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
                        out_of_range.append(
                            f"{name}/{path.get('id', '?')}: {conf}"
                        )

        assert not out_of_range, (
            f"Confidence values out of [0.0, 1.0] range: {out_of_range}"
        )


class TestSymptomRegexesCompile:
    """Every symptom pattern compiles as a valid regex."""

    def test_symptom_regexes_compile(self, all_playbook_profiles):
        broken = []
        for name, profile in all_playbook_profiles.items():
            for path in profile.get("failure_paths", []):
                for pattern in path.get("symptoms", []):
                    try:
                        re.compile(pattern)
                    except re.error as e:
                        broken.append(
                            f"{name}/{path.get('id', '?')}: "
                            f"'{pattern}' -> {e}"
                        )

        assert not broken, f"Invalid regex patterns in playbooks: {broken}"


class TestNoOverlappingSymptomsWithinProfile:
    """Within a single profile, no two failure paths have identical
    symptom patterns. Warns if symptoms are subsets of each other."""

    def test_no_overlapping_symptoms_within_profile(self, all_playbook_profiles):
        duplicates = []
        for name, profile in all_playbook_profiles.items():
            all_symptoms = {}
            for path in profile.get("failure_paths", []):
                path_id = path.get("id", "?")
                for symptom in path.get("symptoms", []):
                    if symptom in all_symptoms:
                        duplicates.append(
                            f"{name}: symptom '{symptom}' in both "
                            f"'{all_symptoms[symptom]}' and '{path_id}'"
                        )
                    all_symptoms[symptom] = path_id

        assert not duplicates, (
            f"Duplicate symptom patterns within profiles: {duplicates}"
        )


class TestPrerequisiteFailurePathsReferenceValidPrereqs:
    """If a failure path has prerequisite_id, that ID must exist in the
    same profile's prerequisites."""

    def test_prerequisite_failure_paths_reference_valid_prereqs(
        self, all_playbook_profiles
    ):
        invalid = []
        for name, profile in all_playbook_profiles.items():
            prereq_ids = {
                p.get("id", "") for p in profile.get("prerequisites", [])
            }
            for path in profile.get("failure_paths", []):
                ref = path.get("prerequisite_id")
                if ref and ref not in prereq_ids:
                    invalid.append(
                        f"{name}/{path.get('id', '?')}: "
                        f"references prerequisite_id '{ref}' "
                        f"not in profile prerequisites {prereq_ids}"
                    )

        assert not invalid, (
            f"Failure paths reference non-existent prerequisites: {invalid}"
        )


class TestInvestigationStepsHaveRequiredFields:
    """Every investigation step has step, command, expect, and if_not."""

    REQUIRED_STEP_FIELDS = {"step", "command", "expect", "if_not"}

    def test_investigation_steps_have_command_and_expect(
        self, all_playbook_profiles
    ):
        issues = []
        for name, profile in all_playbook_profiles.items():
            for path in profile.get("failure_paths", []):
                path_id = path.get("id", "?")
                for i, step in enumerate(path.get("investigation", [])):
                    for field in self.REQUIRED_STEP_FIELDS:
                        if field not in step:
                            issues.append(
                                f"{name}/{path_id}/step[{i}]: "
                                f"missing '{field}'"
                            )

        assert not issues, f"Investigation step field issues: {issues}"


class TestKeyComponentsHavePodLabel:
    """Every key_component has name, role, type, namespace, pod_label."""

    REQUIRED_COMPONENT_FIELDS = {"name", "role", "type", "namespace", "pod_label"}

    def test_key_components_have_pod_label(self, all_playbook_profiles):
        issues = []
        for name, profile in all_playbook_profiles.items():
            arch = profile.get("architecture", {})
            for comp in arch.get("key_components", []):
                comp_name = comp.get("name", "?")
                for field in self.REQUIRED_COMPONENT_FIELDS:
                    if field not in comp:
                        issues.append(
                            f"{name}/{comp_name}: missing '{field}'"
                        )

        assert not issues, f"Key component field issues: {issues}"


class TestVersionOverlayDoesntRedefineBaseProfiles:
    """acm-2.16.yaml should NOT redefine profiles that exist in base.yaml
    unless intentional override."""

    def test_version_overlay_doesnt_redefine_base_profiles(
        self, base_playbook_data, version_playbook_data
    ):
        base_profiles = set(base_playbook_data.get("profiles", {}).keys())
        version_profiles = set(version_playbook_data.get("profiles", {}).keys())

        overlaps = base_profiles & version_profiles
        if overlaps:
            pytest.fail(
                f"Version overlay redefines base profiles: {overlaps}. "
                f"This may be intentional (version-specific override) — "
                f"verify and add to allow-list if so."
            )


class TestCategoryValuesAreValid:
    """Category in every failure path is one of the valid categories."""

    def test_category_values_are_valid(self, all_playbook_profiles):
        invalid = []
        for name, profile in all_playbook_profiles.items():
            for path in profile.get("failure_paths", []):
                category = path.get("category", "")
                if category not in VALID_CATEGORIES:
                    invalid.append(
                        f"{name}/{path.get('id', '?')}: '{category}'"
                    )

        assert not invalid, (
            f"Invalid category values: {invalid}. Valid: {VALID_CATEGORIES}"
        )
