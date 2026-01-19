#!/usr/bin/env python3
"""
Unit tests for Confidence Calculator Service
"""

import pytest
from src.services.confidence_calculator import (
    ConfidenceCalculator,
    EvidenceCompleteness,
    SourceConsistency,
    ConfidenceBreakdown,
    calculate_confidence
)


class TestEvidenceCompleteness:
    """Tests for EvidenceCompleteness dataclass."""

    def test_full_completeness(self):
        """Test completeness score with all evidence."""
        completeness = EvidenceCompleteness(
            has_stack_trace=True,
            has_parsed_frames=True,
            has_root_cause_file=True,
            has_environment_status=True,
            has_repository_analysis=True,
            has_selector_lookup=True,
            has_git_history=True,
            has_console_errors=True,
            has_test_file_content=True,
        )
        assert completeness.completeness_score == 1.0

    def test_empty_completeness(self):
        """Test completeness score with no evidence."""
        completeness = EvidenceCompleteness()
        assert completeness.completeness_score == 0.0

    def test_partial_completeness(self):
        """Test completeness score with partial evidence."""
        completeness = EvidenceCompleteness(
            has_stack_trace=True,
            has_parsed_frames=True,
            has_environment_status=True,
        )
        # 3 out of 9 factors
        assert abs(completeness.completeness_score - 3/9) < 0.001

    def test_to_dict(self):
        """Test dictionary conversion."""
        completeness = EvidenceCompleteness(
            has_stack_trace=True,
            has_environment_status=True,
        )
        d = completeness.to_dict()
        assert "has_stack_trace" in d
        assert d["has_stack_trace"] is True
        assert "completeness_score" in d


class TestSourceConsistency:
    """Tests for SourceConsistency dataclass."""

    def test_full_agreement(self):
        """Test consistency when all sources agree."""
        consistency = SourceConsistency(
            jenkins_suggests="PRODUCT_BUG",
            environment_suggests="PRODUCT_BUG",
            repository_suggests="PRODUCT_BUG",
            console_suggests="PRODUCT_BUG",
        )
        assert consistency.consistency_score == 1.0
        assert consistency.dominant_suggestion == "PRODUCT_BUG"

    def test_no_agreement(self):
        """Test consistency when all sources disagree."""
        consistency = SourceConsistency(
            jenkins_suggests="PRODUCT_BUG",
            environment_suggests="AUTOMATION_BUG",
            repository_suggests="INFRASTRUCTURE",
            console_suggests="PRODUCT_BUG",
        )
        # 2 agree on PRODUCT_BUG out of 4
        assert consistency.consistency_score == 0.5
        assert consistency.dominant_suggestion == "PRODUCT_BUG"

    def test_majority_agreement(self):
        """Test consistency with majority agreement."""
        consistency = SourceConsistency(
            jenkins_suggests="AUTOMATION_BUG",
            environment_suggests="AUTOMATION_BUG",
            repository_suggests="AUTOMATION_BUG",
            console_suggests="PRODUCT_BUG",
        )
        # 3 out of 4 agree
        assert consistency.consistency_score == 0.75
        assert consistency.dominant_suggestion == "AUTOMATION_BUG"

    def test_insufficient_sources(self):
        """Test consistency with only one source."""
        consistency = SourceConsistency(
            jenkins_suggests="PRODUCT_BUG",
        )
        # Not enough sources to compare
        assert consistency.consistency_score == 0.5

    def test_no_sources(self):
        """Test consistency with no sources."""
        consistency = SourceConsistency()
        assert consistency.consistency_score == 0.5
        assert consistency.dominant_suggestion is None

    def test_to_dict(self):
        """Test dictionary conversion."""
        consistency = SourceConsistency(
            jenkins_suggests="PRODUCT_BUG",
            console_suggests="PRODUCT_BUG",
        )
        d = consistency.to_dict()
        assert "jenkins_suggests" in d
        assert "consistency_score" in d
        assert "dominant_suggestion" in d


class TestConfidenceBreakdown:
    """Tests for ConfidenceBreakdown dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        breakdown = ConfidenceBreakdown(
            score_separation=0.5,
            evidence_completeness=0.7,
            source_consistency=0.8,
            selector_certainty=0.6,
            history_signal=0.5,
            final_confidence=0.72,
            confidence_level="MEDIUM",
        )
        d = breakdown.to_dict()
        assert "final_confidence" in d
        assert "confidence_level" in d
        assert "factors" in d
        assert d["factors"]["score_separation"] == 0.5


class TestConfidenceCalculator:
    """Tests for ConfidenceCalculator class."""

    def setup_method(self):
        """Setup for each test."""
        self.calculator = ConfidenceCalculator()

    def test_high_confidence_scenario(self):
        """Test high confidence with good evidence."""
        scores = {
            "product_bug": 0.85,
            "automation_bug": 0.10,
            "infrastructure": 0.05,
        }
        completeness = EvidenceCompleteness(
            has_stack_trace=True,
            has_parsed_frames=True,
            has_root_cause_file=True,
            has_environment_status=True,
            has_repository_analysis=True,
            has_selector_lookup=True,
            has_git_history=True,
            has_console_errors=True,
            has_test_file_content=True,
        )
        consistency = SourceConsistency(
            jenkins_suggests="PRODUCT_BUG",
            console_suggests="PRODUCT_BUG",
        )

        result = self.calculator.calculate(
            classification_scores=scores,
            evidence_completeness=completeness,
            source_consistency=consistency,
            selector_found=True,
        )

        assert result.confidence_level == "HIGH"
        assert result.final_confidence >= 0.75

    def test_low_confidence_scenario(self):
        """Test low confidence with poor evidence."""
        scores = {
            "product_bug": 0.35,
            "automation_bug": 0.35,
            "infrastructure": 0.30,
        }
        completeness = EvidenceCompleteness(
            has_stack_trace=True,
        )
        consistency = SourceConsistency(
            jenkins_suggests="PRODUCT_BUG",
            console_suggests="INFRASTRUCTURE",
        )

        result = self.calculator.calculate(
            classification_scores=scores,
            evidence_completeness=completeness,
            source_consistency=consistency,
        )

        assert result.final_confidence < 0.5

    def test_score_separation_factor(self):
        """Test that score separation affects confidence."""
        completeness = EvidenceCompleteness()
        consistency = SourceConsistency()

        # High separation
        high_sep_result = self.calculator.calculate(
            classification_scores={
                "product_bug": 0.9,
                "automation_bug": 0.05,
                "infrastructure": 0.05,
            },
            evidence_completeness=completeness,
            source_consistency=consistency,
        )

        # Low separation
        low_sep_result = self.calculator.calculate(
            classification_scores={
                "product_bug": 0.4,
                "automation_bug": 0.35,
                "infrastructure": 0.25,
            },
            evidence_completeness=completeness,
            source_consistency=consistency,
        )

        assert high_sep_result.score_separation > low_sep_result.score_separation

    def test_selector_certainty_found(self):
        """Test selector certainty when selector found."""
        result = self.calculator.calculate(
            classification_scores={"product_bug": 0.5, "automation_bug": 0.3, "infrastructure": 0.2},
            evidence_completeness=EvidenceCompleteness(),
            source_consistency=SourceConsistency(),
            selector_found=True,
            selector_recently_changed=True,
        )
        # High certainty when we know selector exists and changed
        assert result.selector_certainty >= 0.7

    def test_selector_certainty_not_found(self):
        """Test selector certainty when selector not found."""
        result = self.calculator.calculate(
            classification_scores={"product_bug": 0.5, "automation_bug": 0.3, "infrastructure": 0.2},
            evidence_completeness=EvidenceCompleteness(),
            source_consistency=SourceConsistency(),
            selector_found=False,
        )
        # Good certainty when selector definitely not in codebase
        assert result.selector_certainty >= 0.7

    def test_selector_certainty_unknown(self):
        """Test selector certainty when selector unknown."""
        result = self.calculator.calculate(
            classification_scores={"product_bug": 0.5, "automation_bug": 0.3, "infrastructure": 0.2},
            evidence_completeness=EvidenceCompleteness(),
            source_consistency=SourceConsistency(),
            selector_found=None,
        )
        # Low certainty when we don't know
        assert result.selector_certainty <= 0.5

    def test_history_signal_supports(self):
        """Test history signal when git history supports classification."""
        result = self.calculator.calculate(
            classification_scores={"product_bug": 0.5, "automation_bug": 0.3, "infrastructure": 0.2},
            evidence_completeness=EvidenceCompleteness(),
            source_consistency=SourceConsistency(),
            git_history_supports=True,
            selector_recently_changed=True,
        )
        assert result.history_signal > 0.5

    def test_history_signal_contradicts(self):
        """Test history signal when git history contradicts."""
        result = self.calculator.calculate(
            classification_scores={"product_bug": 0.5, "automation_bug": 0.3, "infrastructure": 0.2},
            evidence_completeness=EvidenceCompleteness(),
            source_consistency=SourceConsistency(),
            git_history_supports=False,
        )
        assert result.history_signal < 0.5

    def test_warnings_generated(self):
        """Test that warnings are generated for low confidence areas."""
        result = self.calculator.calculate(
            classification_scores={
                "product_bug": 0.35,
                "automation_bug": 0.35,
                "infrastructure": 0.30,
            },
            evidence_completeness=EvidenceCompleteness(),
            source_consistency=SourceConsistency(
                jenkins_suggests="PRODUCT_BUG",
                console_suggests="INFRASTRUCTURE",
            ),
        )

        assert len(result.warnings) > 0
        # Should warn about close scores
        assert any("close" in w.lower() or "scores" in w.lower() for w in result.warnings)

    def test_confidence_levels(self):
        """Test confidence level thresholds."""
        completeness = EvidenceCompleteness(
            has_stack_trace=True,
            has_environment_status=True,
            has_repository_analysis=True,
            has_console_errors=True,
        )
        consistency = SourceConsistency(
            jenkins_suggests="PRODUCT_BUG",
            console_suggests="PRODUCT_BUG",
        )

        # HIGH confidence scenario
        high_result = self.calculator.calculate(
            classification_scores={"product_bug": 0.9, "automation_bug": 0.05, "infrastructure": 0.05},
            evidence_completeness=completeness,
            source_consistency=consistency,
            selector_found=True,
        )
        assert high_result.confidence_level in ["HIGH", "MEDIUM"]

    def test_factors_detail_populated(self):
        """Test that factors_detail is populated."""
        result = self.calculator.calculate(
            classification_scores={"product_bug": 0.5, "automation_bug": 0.3, "infrastructure": 0.2},
            evidence_completeness=EvidenceCompleteness(has_stack_trace=True),
            source_consistency=SourceConsistency(),
            selector_found=True,
        )

        assert "score_separation" in result.factors_detail
        assert "evidence_completeness" in result.factors_detail
        assert "selector_certainty" in result.factors_detail

    def test_confidence_clamped(self):
        """Test that confidence is clamped to valid range."""
        # Even with worst case scenario
        result = self.calculator.calculate(
            classification_scores={"product_bug": 0.33, "automation_bug": 0.34, "infrastructure": 0.33},
            evidence_completeness=EvidenceCompleteness(),
            source_consistency=SourceConsistency(),
        )
        assert 0.1 <= result.final_confidence <= 0.95

    def test_quick_confidence(self):
        """Test quick confidence calculation."""
        confidence = self.calculator.quick_confidence(
            score_separation=0.8,
            has_full_evidence=True
        )
        assert confidence > 0.7

        confidence_partial = self.calculator.quick_confidence(
            score_separation=0.8,
            has_full_evidence=False
        )
        assert confidence_partial < confidence


class TestConvenienceFunction:
    """Tests for calculate_confidence convenience function."""

    def test_basic_usage(self):
        """Test basic convenience function usage."""
        result = calculate_confidence(
            classification_scores={
                "product_bug": 0.6,
                "automation_bug": 0.3,
                "infrastructure": 0.1,
            },
            has_stack_trace=True,
            has_environment_status=True,
        )

        assert isinstance(result, ConfidenceBreakdown)
        assert result.final_confidence > 0

    def test_with_selector(self):
        """Test convenience function with selector info."""
        result = calculate_confidence(
            classification_scores={
                "product_bug": 0.5,
                "automation_bug": 0.3,
                "infrastructure": 0.2,
            },
            selector_found=True,
        )
        assert result.selector_certainty > 0.5

    def test_minimal_inputs(self):
        """Test with minimal inputs."""
        result = calculate_confidence(
            classification_scores={
                "product_bug": 0.5,
                "automation_bug": 0.3,
                "infrastructure": 0.2,
            },
        )
        assert isinstance(result, ConfidenceBreakdown)
