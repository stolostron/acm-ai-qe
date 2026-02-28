"""
AI instructions consistency tests.

Validates the AI instructions dict returned by _build_ai_instructions()
for internal consistency, completeness, and absence of contradictions.
"""

import json
import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.regression


@pytest.fixture(scope="module")
def ai_instructions():
    """Build AI instructions from the gather module."""
    # Import the DataGatherer class and call _build_ai_instructions
    # We need to instantiate minimally to call the method
    sys.path.insert(
        0,
        str(Path(__file__).parent.parent.parent),
    )
    from src.scripts.gather import DataGatherer

    gatherer = DataGatherer.__new__(DataGatherer)
    return gatherer._build_ai_instructions()


class TestAllPhasesReferencedInFramework:
    """Phases A, B, C, D, E all present in investigation_framework.phases."""

    def test_all_phases_referenced_in_framework(self, ai_instructions):
        framework = ai_instructions.get("investigation_framework", {})
        phases = framework.get("phases", {})
        expected = {"A", "B", "C", "D", "E"}
        actual = set(phases.keys())

        missing = expected - actual
        assert not missing, f"Missing phases in framework: {missing}"


class TestPhaseStepsAreOrdered:
    """Phase A steps start with A, Phase B with B, etc."""

    def test_phase_steps_are_ordered(self, ai_instructions):
        framework = ai_instructions.get("investigation_framework", {})
        phases = framework.get("phases", {})
        issues = []

        for phase_key, phase_data in phases.items():
            steps = phase_data.get("steps", [])
            for step in steps:
                # Extract step ID prefix (e.g., 'A0', 'B1', 'C-1', 'D0', 'PR-1')
                # Steps start with the phase letter, except PR-* steps
                # which are pre-routing checks belonging to Phase D
                step_prefix = step.split(".")[0].strip()
                if step_prefix.startswith("PR-"):
                    # PR-* steps belong to Phase D (pre-routing checks)
                    phase_letter = "D"
                else:
                    phase_letter = step_prefix[0] if step_prefix else ""
                if phase_letter != phase_key:
                    issues.append(
                        f"Phase {phase_key} contains step "
                        f"starting with '{step_prefix}': {step[:60]}"
                    )

        assert not issues, f"Steps in wrong phases: {issues}"


class TestNoRemovedStepsStillReferenced:
    """Old step names that were refactored into tiered investigation
    are not still referenced as standalone steps."""

    REMOVED_STANDALONE_STEPS = {
        "B5b_standalone",
        "B7_standalone",
    }

    def test_no_removed_steps_still_referenced(self, ai_instructions):
        # Serialize the entire instructions to search for references
        text = json.dumps(ai_instructions)

        # Check for references to old standalone step names
        # B5b and B7 should be part of the tiered system, not standalone
        # They should exist in steps but not as separate top-level sections
        framework = ai_instructions.get("investigation_framework", {})
        phases = framework.get("phases", {})

        # B5b and B7 should be steps within Phase B, which is correct
        # They should NOT appear as separate top-level keys outside the framework
        top_level_keys = set(ai_instructions.keys())
        bad_keys = {"B5b", "B7", "phase_b5b", "phase_b7"}
        found = top_level_keys & bad_keys

        assert not found, (
            f"Old standalone step references found as top-level keys: {found}"
        )


class TestTieredInvestigationPresent:
    """tiered_investigation section exists with tiers 0-4."""

    def test_tiered_investigation_present(self, ai_instructions):
        tiered = ai_instructions.get("tiered_investigation")
        assert tiered is not None, "Missing 'tiered_investigation' section"

        expected_tiers = {
            "tier_0_health_snapshot",
            "tier_1_component_health",
            "tier_2_playbook_investigation",
            "tier_3_data_flow",
            "tier_4_deep_investigation",
        }
        actual_tiers = set(tiered.keys()) - {"description"}
        missing = expected_tiers - actual_tiers

        assert not missing, (
            f"Missing tiers in tiered_investigation: {missing}"
        )


class TestClusterAccessSectionPresent:
    """cluster_access section with re-authentication steps exists."""

    def test_cluster_access_section_present(self, ai_instructions):
        cluster_access = ai_instructions.get("cluster_access")
        assert cluster_access is not None, "Missing 'cluster_access' section"
        assert "steps" in cluster_access, "cluster_access missing 'steps'"
        assert len(cluster_access["steps"]) >= 3, (
            "cluster_access should have at least 3 steps "
            "(read creds, login, verify)"
        )


class TestPrecomputedContextListsAllNewFields:
    """precomputed_context.fields includes new v3.1 fields."""

    EXPECTED_FIELDS = {
        "feature_knowledge.feature_readiness",
        "feature_knowledge.investigation_playbooks",
        "feature_knowledge.kg_status",
        "cluster_access",
    }

    def test_precomputed_context_lists_all_new_fields(self, ai_instructions):
        precomputed = ai_instructions.get("precomputed_context", {})
        fields = precomputed.get("fields", {})
        field_keys = set(fields.keys())

        missing = self.EXPECTED_FIELDS - field_keys
        assert not missing, (
            f"precomputed_context.fields missing new fields: {missing}"
        )


class TestClassificationGuideIncludesAllCategories:
    """Classification guide includes all categories with explicit entries.

    Note: MIXED and UNKNOWN are valid classification enums but don't have
    explicit guide entries — they emerge from multi-evidence assessment."""

    EXPECTED_CATEGORIES = {
        "PRODUCT_BUG",
        "AUTOMATION_BUG",
        "INFRASTRUCTURE",
        "NO_BUG",
        "FLAKY",
    }

    def test_classification_guide_includes_all_categories(self, ai_instructions):
        guide = ai_instructions.get("classification_guide", {})
        actual = set(guide.keys())

        missing = self.EXPECTED_CATEGORIES - actual
        assert not missing, (
            f"Classification guide missing categories: {missing}"
        )


class TestOutputSchemaMatchesJsonSchema:
    """Field names in output_schema.required_top_level match the
    required array in analysis_results_schema.json."""

    def test_output_schema_matches_json_schema(self, ai_instructions, schema_data):
        output_schema = ai_instructions.get("output_schema", {})
        required_top_level = output_schema.get("required_top_level", [])

        # Extract field names from the instruction strings
        # Format: 'per_test_analysis (array with evidence_sources)'
        instruction_fields = set()
        for item in required_top_level:
            # Extract the field name (first word or dot-delimited path)
            field = item.split(" ")[0].split(".")[0]
            instruction_fields.add(field)

        # Get required fields from JSON schema
        schema_required = set(schema_data.get("required", []))

        # Instruction fields should be a subset of schema required
        not_in_schema = instruction_fields - schema_required
        assert not not_in_schema, (
            f"output_schema references fields not in JSON schema required: "
            f"{not_in_schema}. Schema requires: {schema_required}"
        )


class TestKgWhenUnavailableNotSilent:
    """KG when_unavailable instruction does NOT contain 'skip' or
    'gracefully'. Must contain 'report', 'flag', or 'warn'."""

    # These indicate silently ignoring KG (without negation)
    FORBIDDEN_PATTERNS = {"skip gracefully", "ignore"}
    REQUIRED_WORDS = {"report", "flag", "warn"}

    def test_kg_when_unavailable_not_silent(self, ai_instructions):
        mcp = ai_instructions.get("mcp_integration", {})
        kg = mcp.get("knowledge_graph", {})
        when_unavailable = kg.get("when_unavailable", "")

        lower = when_unavailable.lower()
        for forbidden in self.FORBIDDEN_PATTERNS:
            # Allow negated forms like "Do NOT silently skip"
            if forbidden in lower:
                # Check if it's negated (preceded by "not" or "don't")
                idx = lower.index(forbidden)
                preceding = lower[max(0, idx - 15):idx].strip()
                if "not" not in preceding and "don't" not in preceding:
                    pytest.fail(
                        f"KG when_unavailable contains '{forbidden}' "
                        f"without negation: '{when_unavailable[:100]}...'"
                    )

        found_required = any(word in lower for word in self.REQUIRED_WORDS)
        assert found_required, (
            f"KG when_unavailable must contain one of {self.REQUIRED_WORDS}. "
            f"Got: '{when_unavailable[:100]}...'"
        )


class TestVersionIsSemver:
    """version field matches X.Y.Z pattern."""

    def test_version_is_semver(self, ai_instructions):
        version = ai_instructions.get("version", "")
        assert re.match(r"^\d+\.\d+\.\d+$", version), (
            f"Version '{version}' does not match X.Y.Z semver pattern"
        )


class TestNoContradictoryPhaseDInstructions:
    """Phase D pre-routing steps (PR-*) run before D0."""

    def test_no_contradictory_phase_d_instructions(self, ai_instructions):
        framework = ai_instructions.get("investigation_framework", {})
        phases = framework.get("phases", {})
        phase_d = phases.get("D", {})
        steps = phase_d.get("steps", [])

        # Find PR-4 (feature knowledge override) and D0 steps
        # PR-* steps are Phase D pre-routing checks that should come before D0
        pr4_idx = None
        d0_idx = None
        for i, step in enumerate(steps):
            if step.startswith("PR-4.") or step.startswith("PR-4 "):
                pr4_idx = i
            if step.startswith("D0"):
                d0_idx = i

        if pr4_idx is not None and d0_idx is not None:
            assert pr4_idx < d0_idx, (
                f"PR-4 (feature knowledge override) must run before "
                f"D0 (backend cross-check). Found PR-4 at index "
                f"{pr4_idx}, D0 at {d0_idx}"
            )
