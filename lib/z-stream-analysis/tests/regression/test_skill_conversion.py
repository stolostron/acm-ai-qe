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
LIB_DIR = REPO_ROOT / "lib" / "z-stream-analysis"
SCHEMA_FILE = LIB_DIR / "src" / "schemas" / "analysis_results_schema.json"
KNOWLEDGE_CANONICAL = REPO_ROOT / ".claude" / "knowledge"
KNOWLEDGE_SKILL = SKILLS_DIR / "acm-z-stream-analyzer" / "references" / "knowledge"

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

# Render fields report.py depends on that are NOT in the schema's top-level `required`
# set, so test_output_schema_md_has_required_top_level_fields cannot catch their omission.
# Single source of truth shared with acm-failure-classifier/references/output-schema.md (A1).
RENDER_CONTRACT_FIELDS = [
    # summary.*
    "total_tests", "passed_count", "total_failures", "pass_rate",
    "overall_classification", "overall_confidence",
    # per_test_analysis[].*
    "classification_path", "failure_mode_category", "root_cause_layer_name",
    "verification_status",
    # analysis_metadata.*
    "build_result", "analyzer_version", "analyzed_at",
]

# Repo shared knowledge DB the z-stream skill reads via
# KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/  (resolves to .claude/knowledge/).
KNOWLEDGE_SHARED = REPO_ROOT / ".claude" / "knowledge"


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

    def test_shared_knowledge_files_present(self):
        """The z-stream skill reads the repo shared DB (.claude/knowledge/) via
        KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/, NOT a per-skill copy.
        Assert that pointer and every nested file the orchestrator actually reads.
        Catches a broken KNOWLEDGE_DIR pointer or a renamed knowledge file (the real
        regression risk) instead of silently skipping on a non-existent copy.
        """
        skill_md = (SKILLS_DIR / "acm-z-stream-analyzer" / "SKILL.md").read_text()
        assert "KNOWLEDGE_DIR" in skill_md, "acm-z-stream-analyzer/SKILL.md missing KNOWLEDGE_DIR"
        assert "../../knowledge/" in skill_md, (
            "KNOWLEDGE_DIR must resolve to the repo shared DB (.claude/knowledge/) "
            "via ${CLAUDE_SKILL_DIR}/../../knowledge/"
        )
        for rel in [
            "baselines/healthy-baseline.yaml",
            "baselines/components.yaml",
            "baselines/addon-catalog.yaml",
            "failures/failure-patterns.yaml",
            "diagnostics/diagnostic-traps.md",
            "baselines/dependency-chains.yaml",
        ]:
            assert (KNOWLEDGE_SHARED / rel).exists(), (
                f"shared knowledge file missing: .claude/knowledge/{rel}"
            )


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
        """Schema-derived: every top-level schema `required` field is documented.
        Auto-tracks the schema — a new top-level required field fails here until
        output-schema.md documents it. These 3 are already documented (green throughout).
        """
        schema = json.loads(SCHEMA_FILE.read_text())
        text = (SKILLS_DIR / "acm-failure-classifier" / "references" / "output-schema.md").read_text()
        for field in schema["required"]:
            assert field in text, f"output-schema.md missing top-level required field: {field}"

    def test_output_schema_md_documents_render_contract(self):
        """Curated render contract: fields report.py renders but that are NOT in the
        schema's top-level `required` set (so the schema-derived check can't catch them).
        Identical to output-schema.md's A1 additions. Word-boundary match so
        `total_failures` does not spuriously match a longer invented token.
        """
        text = (SKILLS_DIR / "acm-failure-classifier" / "references" / "output-schema.md").read_text()
        missing = [f for f in RENDER_CONTRACT_FIELDS
                   if not re.search(r"\b" + re.escape(f) + r"\b", text)]
        assert not missing, f"output-schema.md missing render-contract fields: {missing}"

    def test_output_schema_md_has_no_invented_fields(self):
        """Invented (non-schema) fields must be absent — they render blank and mislead
        the analysis stage into emitting keys report.py never reads.
        """
        text = (SKILLS_DIR / "acm-failure-classifier" / "references" / "output-schema.md").read_text()
        for invented in ("total_analyzed", "total_failures_analyzed"):
            assert invented not in text, f"output-schema.md documents invented field: {invented}"

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

    # --- Unit 2 rigor guards (C2): parity with the app's classification gates ---

    def test_product_bug_hard_gate_present(self):
        """A3: PRODUCT_BUG hard gate — 4 checks, defaults to AUTOMATION_BUG when unmet
        (ported from analysis.md:1858-1865)."""
        text = self._read_ref("phase-d-validation.md")
        assert "PRODUCT_BUG Hard Gate" in text, "phase-d-validation.md missing PRODUCT_BUG Hard Gate (A3)"
        gate = text.split("PRODUCT_BUG Hard Gate")[1].split("\n## ")[0]
        checks = re.findall(r"^\d+\.\s+\*\*", gate, re.MULTILINE)
        assert len(checks) >= 4, f"PRODUCT_BUG Hard Gate has {len(checks)} checks, expected >= 4"
        assert re.search(r"default.*AUTOMATION_BUG", gate, re.IGNORECASE | re.DOTALL), (
            "PRODUCT_BUG Hard Gate must default to AUTOMATION_BUG when a check is unmet"
        )
        assert "ACM-Source MCP" in gate, "PRODUCT_BUG Hard Gate must require ACM-Source MCP verification"

    def test_dv5e_mandatory_gate(self):
        """A4: D-V5e upgraded from soft bullets to a MANDATORY GATE with >=4 checks
        (ported from analysis.md:1234-1278)."""
        text = self._read_ref("phase-d-validation.md")
        parts = text.split("D-V5e")
        assert len(parts) > 1, "phase-d-validation.md missing D-V5e"
        dv5e = parts[1].split("\n### ")[0]
        assert "MANDATORY GATE" in dv5e, "D-V5e must be a MANDATORY GATE (A4)"
        checks = re.findall(r"^\d+\.\s+\*\*", dv5e, re.MULTILINE)
        assert len(checks) >= 4, f"D-V5e has {len(checks)} numbered checks, expected >= 4"
        assert "ACM-Source MCP" in dv5e, "D-V5e must require ACM-Source MCP verification"

    def test_dv5c_parity(self):
        """A4b: D-V5c ports BOTH app checks — backend confirmation (layer discrepancy ->
        PRODUCT_BUG) and the Polarion known-product-change check (analysis.md:1214-1230)."""
        text = self._read_ref("phase-d-validation.md")
        parts = text.split("D-V5c")
        assert len(parts) > 1, "phase-d-validation.md missing D-V5c"
        dv5c = parts[1].split("\n### ")[0]
        assert "oc auth can-i" in dv5c and "oc get" in dv5c, (
            "D-V5c missing the read-only backend-confirmation method (oc auth can-i / oc get)"
        )
        assert "layer discrepancy" in dv5c.lower() and "PRODUCT_BUG" in dv5c, (
            "D-V5c missing the layer-discrepancy -> PRODUCT_BUG reclassification"
        )
        assert "Polarion" in dv5c, "D-V5c missing the Polarion known-product-change check (Check 2)"

    def test_phase_d_crosslinks_symptom_layer_map(self):
        """A5: the 9 verification templates are named inline and the canonical table is
        cross-linked to symptom-layer-map.md (kept the single source of the >=9-row table)."""
        text = self._read_ref("phase-d-validation.md")
        assert "symptom-layer-map.md" in text, "phase-d must cross-link symptom-layer-map.md (A5)"
        low = text.lower()
        for probe in ["selector not found", "button disabled", "resourcequota"]:
            assert probe in low, f"phase-d missing named verification template: {probe}"

    def test_dv1_evidence_gate(self):
        """A6: D-V1 evidence gate (>=2 sources + combined weight >= 1.8) ported into phase-d
        (analysis.md:1145-1148)."""
        text = self._read_ref("phase-d-validation.md")
        assert "D-V1" in text, "phase-d missing the D-V1 evidence gate (A6)"
        dv1 = text.split("D-V1")[1].split("\n## ")[0]
        assert "1.8" in dv1, "D-V1 must state the >= 1.8 high-confidence gate"
        assert re.search(r"2\s+(evidence\s+)?sources", dv1, re.IGNORECASE), (
            "D-V1 must require at least 2 evidence sources"
        )

    def test_combination_rule_in_evidence_requirements(self):
        """A6: evidence-requirements.md states the discrete combination rule
        (1 Tier1 + 1 Tier2, OR 2 Tier1, OR 3 Tier2) distinct from the 1.8 confidence gate;
        weights and the 1.8 gate are preserved (analysis.md:1084)."""
        path = SKILLS_DIR / "acm-z-stream-analyzer" / "references" / "evidence-requirements.md"
        text = path.read_text()
        assert re.search(
            r"1\s*Tier\s*1.*1\s*Tier\s*2.*2\s*Tier\s*1.*3\s*Tier\s*2",
            text, re.IGNORECASE | re.DOTALL,
        ), "evidence-requirements.md missing the combination rule (A6)"
        assert "1.8" in text, "evidence-requirements.md must keep the >= 1.8 high-confidence gate"
        for w in ["1.0", "0.5", "0.25"]:
            assert w in text, f"evidence-requirements.md missing tier weight {w}"

    def test_investigator_crosslinks_evidence_requirements(self):
        """A6: cluster-investigator cross-links the shared combination rule rather than
        carrying a divergent copy."""
        text = _read_skill("acm-cluster-investigator")
        assert "evidence-requirements.md" in text, (
            "acm-cluster-investigator should cross-link evidence-requirements.md for the combination rule"
        )

    def test_phase_c_cascade_detection_documented(self):
        """A8: phase-c-correlation.md documents the component-dependency cascade (common
        dependency -> root-cause component -> single PRODUCT_BUG collapse) and the bulk-selector
        rule (analysis.md:1088-1111)."""
        text = self._read_ref("phase-c-correlation.md")
        assert text, "phase-c-correlation.md missing (A8)"
        low = text.lower()
        assert "depends_on" in low or ("common" in low and "dependency" in low), (
            "phase-c must document common-dependency cascade detection"
        )
        assert "root-cause component" in low or ("root" in low and "cause" in low and "component" in low), (
            "phase-c must identify the root-cause component"
        )
        assert re.search(r"single\s+product_bug|collapse", low), (
            "phase-c must collapse the cascade into a single PRODUCT_BUG"
        )
        assert "80%" in text and "AUTOMATION_BUG" in text, (
            "phase-c must document the 80% same-selector bulk AUTOMATION_BUG rule (C3)"
        )

    def test_cascade_output_object_documented(self):
        """A8: output-schema.md documents the cascading_failure_analysis object fields
        (analysis_results_schema.json:220-250) so the restored methodology stays render-valid."""
        path = SKILLS_DIR / "acm-failure-classifier" / "references" / "output-schema.md"
        text = path.read_text()
        assert "cascading_failure_analysis" in text
        for field in [
            "root_cause_component", "root_cause_subsystem", "dependent_components",
            "tests_affected_by_cascade", "knowledge_graph_query", "analysis_performed",
        ]:
            assert field in text, f"output-schema.md missing cascading_failure_analysis field: {field}"


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


class TestZStreamClusterDiagnosisContent:
    """Layer 4m: Stage 1.5 cluster-diagnosis schema fidelity for acm-z-stream-analyzer.

    The in-skill reference is the authoritative schema for the health-score formula
    (originally from the now-deleted app agent cluster-diagnostic.md). The 5 penalty
    CATEGORY NAMES are identical to acm-hub-health-check's diagnostic-output-schema.md, so
    name-only checks cannot enforce fidelity; the app's discriminating VALUE tokens (weight
    column 30%/20%, subsystem -0.06/-0.03, cap 0.20, managed <50%/50-99%) are absent from
    the hub-health doc and are what prevent re-drift toward hub-health's divergent numbers.
    """

    REF = SKILLS_DIR / "acm-z-stream-analyzer" / "references" / "cluster-diagnosis-schema.md"

    def _read(self):
        return self.REF.read_text() if self.REF.exists() else ""

    def test_cluster_diagnosis_schema_reference_exists(self):
        assert self.REF.exists(), (
            "acm-z-stream-analyzer/references/cluster-diagnosis-schema.md missing "
            "(A7: port the Stage 1.5 health-score formula + cluster-diagnosis.json schema)"
        )

    def test_cluster_diagnosis_health_score_formula_tokens(self):
        text = self._read()
        # App-specific discriminating value tokens, verbatim from cluster-diagnostic.md:699-703.
        # 7 of these 8 are ABSENT from acm-hub-health-check's divergent formula (only
        # "non-standard registry" is shared); asserting them enforces skill==app fidelity.
        for tok in ["30%", "20%", "-0.06", "-0.03", "cap 0.20",
                    "<50%", "50-99%", "non-standard registry"]:
            assert tok in text, (
                f"cluster-diagnosis-schema.md missing app formula token '{tok}' "
                "(must match cluster-diagnostic.md, NOT hub-health's divergent values)"
            )

    def test_cluster_diagnosis_penalty_categories(self):
        text = self._read()
        for category in ["Operator health", "Infrastructure guards", "Subsystem health",
                         "Managed clusters", "Image integrity"]:
            assert category in text, (
                f"cluster-diagnosis-schema.md missing penalty category: {category}"
            )

    def test_cluster_diagnosis_required_fields(self):
        text = self._read()
        for field in ["cluster_connectivity", "environment_health_score",
                      "critical_issue_count", "warning_issue_count", "cluster_identity",
                      "operator_health", "subsystem_health", "image_integrity",
                      "classification_guidance", "counter_signals", "console_plugins",
                      "health_depth", "unchecked_layers"]:
            assert field in text, (
                f"cluster-diagnosis-schema.md missing cluster-diagnosis.json field: {field}"
            )

    def test_zstream_skill_points_to_in_skill_cluster_diagnosis_reference(self):
        # A7: SKILL.md must point to the self-contained in-skill reference, not the app agent
        # file (removes skill->app coupling). The app path is allowed to remain only as an
        # optional "see also"; the in-skill reference pointer is what this guard requires.
        text = _read_skill("acm-z-stream-analyzer")
        assert "references/cluster-diagnosis-schema.md" in text, (
            "acm-z-stream-analyzer/SKILL.md should point to the in-skill "
            "references/cluster-diagnosis-schema.md (A7 self-containment)"
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

    def test_zstream_relative_references_resolve(self):
        """Relative '../' references to sibling skills must resolve from the
        *containing file's* directory. A SKILL.md at the skill root uses
        ../acm-X/... (one level up); a file in a references/ subdir needs
        ../../acm-X/... (one extra level). Scan every z-stream skill file
        (SKILL.md + references/*.md) and assert each relative acm-*.md
        reference points at a real file. Guards the latent path bug where a
        references/ file used a single ../ and silently pointed nowhere.
        """
        ref_re = re.compile(r"(?:\.\./)+acm-[\w./-]+\.md")
        checked = 0
        for skill in [
            "acm-z-stream-analyzer", "acm-failure-classifier",
            "acm-cluster-investigator", "acm-data-enricher",
        ]:
            skill_dir = SKILLS_DIR / skill
            files = [skill_dir / "SKILL.md"]
            files += sorted((skill_dir / "references").glob("*.md"))
            for md in files:
                if not md.exists():
                    continue
                for rel in ref_re.findall(md.read_text()):
                    target = (md.parent / rel).resolve()
                    assert target.exists(), (
                        f"{md.relative_to(SKILLS_DIR)} references '{rel}' -> "
                        f"non-existent {target}"
                    )
                    checked += 1
        assert checked >= 5, (
            f"expected >=5 relative acm-*.md references across the z-stream "
            f"skills, checked {checked} (regex may have stopped matching)"
        )


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
            KNOWLEDGE_CANONICAL / "diagnostics" / "diagnostic-traps.md",
            KNOWLEDGE_SKILL / "diagnostics" / "diagnostic-traps.md",
        ]:
            if path.parent.exists():
                assert path.exists(), f"Missing diagnostic traps knowledge file: {path}"
