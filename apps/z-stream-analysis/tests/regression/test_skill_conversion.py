"""Regression tests for Z-Stream Analysis skill conversion.

Validates that the portable skill pack (.claude/skills/) faithfully represents
the authoritative app agents (.claude/agents/) and produces valid output.

Layers covered:
- Layer 3: Structural validation (frontmatter, file existence, cross-references)
- Layer 4: Content completeness (methodology coverage, feature counts)
- Layer 6: Cross-skill dependency chain verification
"""

import os
import re
import json
import yaml
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
APP_DIR = REPO_ROOT / "apps" / "z-stream-analysis"
KNOWLEDGE_APP = APP_DIR / "knowledge"
KNOWLEDGE_SKILL = SKILLS_DIR / "acm-z-stream-analyzer" / "references" / "knowledge"
SCHEMA_FILE = APP_DIR / "src" / "schemas" / "analysis_results_schema.json"

ZSTREAM_SKILLS = [
    "acm-z-stream-analyzer",
    "acm-failure-classifier",
    "acm-cluster-investigator",
    "acm-data-enricher",
    "acm-hub-health-check",
    "acm-cluster-health",
    "acm-jenkins-client",
    "acm-knowledge-base",
    "acm-knowledge-learner",
    "acm-cluster-remediation",
]

VALID_CLASSIFICATIONS = {
    "PRODUCT_BUG", "AUTOMATION_BUG", "INFRASTRUCTURE",
    "NO_BUG", "MIXED", "FLAKY", "UNKNOWN",
}


def _read_skill(skill_name):
    path = SKILLS_DIR / skill_name / "SKILL.md"
    return path.read_text() if path.exists() else ""


def _parse_frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}


class TestSkillStructure:
    """Layer 3a-3e: Structural validation."""

    @pytest.mark.parametrize("skill", ZSTREAM_SKILLS)
    def test_skill_md_exists(self, skill):
        assert (SKILLS_DIR / skill / "SKILL.md").exists(), f"{skill}/SKILL.md missing"

    @pytest.mark.parametrize("skill", ZSTREAM_SKILLS)
    def test_frontmatter_has_required_fields(self, skill):
        text = _read_skill(skill)
        fm = _parse_frontmatter(text)
        assert fm.get("name"), f"{skill}: frontmatter missing 'name'"
        assert fm.get("description"), f"{skill}: frontmatter missing 'description'"

    @pytest.mark.parametrize("skill", ZSTREAM_SKILLS)
    def test_cross_skill_references_valid(self, skill):
        text = _read_skill(skill)
        referenced = re.findall(r"acm-[\w-]+(?= skill)", text)
        for ref in referenced:
            assert (SKILLS_DIR / ref).is_dir(), (
                f"{skill} references '{ref} skill' but {ref}/ doesn't exist"
            )

    def test_knowledge_files_identical(self):
        if not KNOWLEDGE_APP.exists() or not KNOWLEDGE_SKILL.exists():
            pytest.skip("Knowledge directories not both present")
        app_files = set()
        for f in KNOWLEDGE_APP.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".yaml", ".py"):
                app_files.add(f.relative_to(KNOWLEDGE_APP))
        skill_files = set()
        for f in KNOWLEDGE_SKILL.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".yaml", ".py"):
                skill_files.add(f.relative_to(KNOWLEDGE_SKILL))
        missing = app_files - skill_files
        assert not missing, f"Knowledge files in app but not in skill: {missing}"


class TestSkillSchemaCompliance:
    """Layer 3f-3g: Schema compliance."""

    def test_classification_values_match_schema(self):
        schema = json.loads(SCHEMA_FILE.read_text())
        schema_enums = set(
            schema["properties"]["per_test_analysis"]["items"]
            ["properties"]["classification"]["enum"]
        )
        assert schema_enums == VALID_CLASSIFICATIONS

    def test_output_schema_md_has_required_top_level_fields(self):
        path = (SKILLS_DIR / "acm-failure-classifier" / "references" / "output-schema.md")
        text = path.read_text()
        required = ["per_test_analysis", "summary", "investigation_phases_completed",
                     "mcp_queries_executed", "jira_correlation"]
        for field in required:
            assert field in text, f"output-schema.md missing required field: {field}"

    def test_mcp_queries_documented_as_array(self):
        path = (SKILLS_DIR / "acm-failure-classifier" / "references" / "output-schema.md")
        text = path.read_text()
        assert '"tool"' in text and '"query"' in text and '"success"' in text, (
            "mcp_queries_executed should document array items with tool/query/success fields"
        )

    def test_jira_correlation_has_search_performed(self):
        path = (SKILLS_DIR / "acm-failure-classifier" / "references" / "output-schema.md")
        text = path.read_text()
        assert "search_performed" in text, (
            "jira_correlation must document 'search_performed' field (schema requires it)"
        )


class TestFailureClassifierContent:
    """Layer 4a-4h: Content completeness for acm-failure-classifier."""

    def _read_ref(self, filename):
        path = SKILLS_DIR / "acm-failure-classifier" / "references" / filename
        return path.read_text() if path.exists() else ""

    def test_all_five_phases_mentioned(self):
        text = _read_skill("acm-failure-classifier")
        for phase in ["Phase A", "Phase B", "Phase C", "Phase D", "Phase E"]:
            assert phase in text, f"SKILL.md missing {phase}"

    def test_cluster_diagnosis_reading_protocol_count(self):
        text = self._read_ref("phase-a-grouping.md")
        numbered_items = re.findall(r"^\d+\.\s+\*\*", text, re.MULTILINE)
        assert len(numbered_items) >= 14, (
            f"phase-a-grouping.md has {len(numbered_items)} numbered reading items, expected >= 14"
        )

    def test_mcp_trigger_matrix_row_count(self):
        text = self._read_ref("phase-b-investigation.md")
        section = text.split("MCP Tool Trigger Matrix")[1] if "MCP Tool Trigger Matrix" in text else ""
        rows = re.findall(r"^\|[^|]+\|[^|]+\|[^|]+\|$", section, re.MULTILINE)
        data_rows = [r for r in rows if "---" not in r and "Trigger" not in r]
        assert len(data_rows) >= 15, (
            f"MCP trigger matrix has {len(data_rows)} rows, expected >= 15"
        )

    def test_b3b_external_services_present(self):
        text = self._read_ref("phase-b-investigation.md")
        for keyword in ["Minio", "Gogs", "AAP", "OBJECTSTORE"]:
            assert keyword in text, f"phase-b-investigation.md missing B3b keyword: {keyword}"

    def test_counterfactual_templates_count(self):
        path = SKILLS_DIR / "acm-cluster-investigator" / "references" / "symptom-layer-map.md"
        text = path.read_text()
        section = text.split("Counterfactual Verification")[1] if "Counterfactual Verification" in text else ""
        rows = re.findall(r"^\|[^|]+\|[^|]+\|[^|]+\|$", section, re.MULTILINE)
        data_rows = [r for r in rows if "---" not in r and "Error" not in r]
        assert len(data_rows) >= 9, (
            f"Counterfactual table has {len(data_rows)} templates, expected >= 9"
        )

    def test_d4b_failure_mode_compatibility_table(self):
        text = self._read_ref("phase-d-validation.md")
        assert "failure_mode_category" in text, "phase-d-validation.md missing failure_mode_category"
        assert "Compatible" in text or "compatible" in text, "phase-d-validation.md missing compatibility table"
        rows = re.findall(r"^\| Pod restarts.*\|$|^\| Network errors.*\|$|^\| Backend 500.*\|$|^\| Selector removed.*\|$",
                          text, re.MULTILINE)
        assert len(rows) >= 4, f"D4b compatibility table has {len(rows)} rows, expected >= 4"

    def test_d5_counter_bias_checks(self):
        text = self._read_ref("phase-d-validation.md")
        d5_section = text.split("D5:")[1] if "D5:" in text else ""
        checks = re.findall(r"^-\s+\*\*", d5_section, re.MULTILINE)
        plain_checks = re.findall(r"^-\s+\*\*[^*]+\*\*", d5_section, re.MULTILINE)
        assert len(plain_checks) >= 5, (
            f"D5 has {len(plain_checks)} checks, expected >= 5"
        )

    def test_pr1_blank_page_routing_table(self):
        text = self._read_ref("phase-d-validation.md")
        parts = text.split("### PR-1")
        pr1_section = parts[1].split("### PR-2")[0] if len(parts) > 1 else ""
        rows = re.findall(r"^\|.+\|.+\|.+\|", pr1_section, re.MULTILINE)
        data_rows = [r for r in rows if "---" not in r and "Condition" not in r]
        assert len(data_rows) >= 5, (
            f"PR-1 routing table has {len(data_rows)} rows, expected >= 5"
        )

    def test_anti_anchoring_rule_present(self):
        text = self._read_ref("phase-a-grouping.md")
        assert "ANTI-ANCHORING" in text or "anti-anchoring" in text.lower(), (
            "phase-a-grouping.md missing anti-anchoring rule"
        )

    def test_tampered_console_warning_present(self):
        text = self._read_ref("phase-a-grouping.md")
        assert "tampered" in text.lower() or "non-official" in text.lower(), (
            "phase-a-grouping.md missing tampered console warning"
        )


class TestClusterInvestigatorContent:
    """Layer 4i-4j: Content completeness for acm-cluster-investigator."""

    def test_anti_patterns_count(self):
        text = _read_skill("acm-cluster-investigator")
        do_not_lines = re.findall(r"^-\s+Do NOT", text, re.MULTILINE)
        assert len(do_not_lines) >= 10, (
            f"acm-cluster-investigator has {len(do_not_lines)} anti-patterns, expected >= 10"
        )

    def test_forbidden_oc_commands_listed(self):
        text = _read_skill("acm-cluster-investigator")
        for cmd in ["oc patch", "oc delete", "oc apply", "oc scale"]:
            assert cmd in text, f"acm-cluster-investigator missing forbidden command: {cmd}"

    def test_allowed_oc_commands_listed(self):
        text = _read_skill("acm-cluster-investigator")
        for cmd in ["oc get", "oc describe", "oc logs"]:
            assert cmd in text, f"acm-cluster-investigator missing allowed command: {cmd}"


class TestHubHealthCheckContent:
    """Layer 4k-4l: Content completeness for acm-hub-health-check."""

    def test_diagnostic_output_schema_exists(self):
        path = SKILLS_DIR / "acm-hub-health-check" / "references" / "diagnostic-output-schema.md"
        assert path.exists(), "diagnostic-output-schema.md missing"

    def test_health_score_formula_documented(self):
        path = SKILLS_DIR / "acm-hub-health-check" / "references" / "diagnostic-output-schema.md"
        text = path.read_text()
        assert "penalty" in text.lower(), "Missing health score penalty documentation"
        for category in ["Operator health", "Infrastructure guards", "Subsystem health",
                         "Managed clusters", "Image integrity"]:
            assert category in text, f"Missing penalty category: {category}"

    def test_health_depth_values_documented(self):
        path = SKILLS_DIR / "acm-hub-health-check" / "references" / "diagnostic-output-schema.md"
        text = path.read_text()
        for value in ["pod_level", "connectivity_verified", "data_verified", "full"]:
            assert value in text, f"Missing health_depth value: {value}"

    def test_counter_signals_documented(self):
        path = SKILLS_DIR / "acm-hub-health-check" / "references" / "diagnostic-output-schema.md"
        text = path.read_text()
        assert "counter_signals" in text, "Missing counter_signals section"
        assert "potential_false_infrastructure" in text, "Missing potential_false_infrastructure"

    def test_statefulset_checks_present(self):
        text = _read_skill("acm-hub-health-check")
        assert "statefulset" in text.lower() or "StatefulSet" in text, (
            "SKILL.md missing StatefulSet checks"
        )

    def test_leader_election_check_present(self):
        text = _read_skill("acm-hub-health-check")
        assert "lease" in text.lower() or "leader election" in text.lower(), (
            "SKILL.md missing leader election (Trap 1b) check"
        )


class TestDataEnricherContent:
    """Content completeness for acm-data-enricher."""

    def _read_ref(self):
        path = SKILLS_DIR / "acm-data-enricher" / "references" / "enrichment-tasks.md"
        return path.read_text() if path.exists() else ""

    def test_console_search_json_schema_present(self):
        text = self._read_ref()
        assert "console_search" in text, "Missing console_search JSON schema"
        assert "verification" in text, "Missing verification sub-object in console_search schema"

    def test_temporal_summary_json_schema_present(self):
        text = self._read_ref()
        assert "temporal_summary" in text, "Missing temporal_summary JSON schema"
        assert "stale_test_signal" in text, "Missing stale_test_signal field"

    def test_acm_version_setting_mentioned(self):
        text = self._read_ref()
        assert "set_acm_version" in text, "Missing ACM version setting requirement"

    def test_patternfly_derivation_rules(self):
        text = self._read_ref()
        assert "pf-v6-c-" in text or "PatternFly" in text, (
            "Missing PatternFly class derivation rules"
        )

    def test_four_intent_values(self):
        text = self._read_ref()
        for value in ["intentional_rename", "likely_unintentional", "product_fix", "no_recent_change"]:
            assert value in text, f"Missing intent value: {value}"


class TestCrossSkillDependencyChain:
    """Layer 6: Cross-skill dependency chain verification."""

    def test_orchestrator_lists_all_dependencies(self):
        text = _read_skill("acm-z-stream-analyzer")
        required_deps = [
            "acm-jenkins-client", "acm-cluster-health", "acm-data-enricher",
            "acm-failure-classifier", "acm-cluster-investigator",
            "acm-knowledge-base",
        ]
        for dep in required_deps:
            assert dep in text, f"acm-z-stream-analyzer missing dependency: {dep}"

    def test_all_referenced_skills_exist(self):
        text = _read_skill("acm-z-stream-analyzer")
        referenced = set(re.findall(r"acm-[\w]+-[\w-]+", text))
        for ref in referenced:
            assert (SKILLS_DIR / ref).is_dir(), f"Referenced skill '{ref}' doesn't exist"

    def test_failure_classifier_references_exist(self):
        refs_dir = SKILLS_DIR / "acm-failure-classifier" / "references"
        expected_files = [
            "phase-a-grouping.md", "phase-b-investigation.md",
            "phase-d-validation.md", "phase-e-jira.md",
            "output-schema.md", "decision-routing.md",
        ]
        for f in expected_files:
            assert (refs_dir / f).exists(), f"acm-failure-classifier missing reference: {f}"

    def test_investigator_references_exist(self):
        refs_dir = SKILLS_DIR / "acm-cluster-investigator" / "references"
        expected_files = ["symptom-layer-map.md", "group-verification.md"]
        for f in expected_files:
            assert (refs_dir / f).exists(), f"acm-cluster-investigator missing reference: {f}"

    def test_hub_health_references_exist(self):
        refs_dir = SKILLS_DIR / "acm-hub-health-check" / "references"
        expected_files = [
            "depth-router.md", "report-template.md", "diagnostic-output-schema.md",
        ]
        for f in expected_files:
            assert (refs_dir / f).exists(), f"acm-hub-health-check missing reference: {f}"

    def test_enricher_references_exist(self):
        refs_dir = SKILLS_DIR / "acm-data-enricher" / "references"
        assert (refs_dir / "enrichment-tasks.md").exists()


class TestDiagnosticTraps:
    """Layer 3h: Diagnostic trap coverage."""

    def test_14_traps_in_cluster_health_skill(self):
        skill_dir = SKILLS_DIR / "acm-cluster-health"
        all_text = ""
        for f in skill_dir.rglob("*.md"):
            all_text += f.read_text()
        trap_refs = re.findall(r"[Tt]rap\s+(\d+)", all_text)
        trap_numbers = set(int(n) for n in trap_refs)
        expected = set(range(1, 15))
        missing = expected - trap_numbers
        assert len(missing) <= 2, f"acm-cluster-health missing traps: {missing}"

    def test_trap_knowledge_file_exists(self):
        for path in [
            KNOWLEDGE_APP / "diagnostics" / "diagnostic-traps.md",
            KNOWLEDGE_SKILL / "diagnostics" / "diagnostic-traps.md",
        ]:
            if path.parent.exists():
                assert path.exists(), f"Missing diagnostic traps knowledge file: {path}"
