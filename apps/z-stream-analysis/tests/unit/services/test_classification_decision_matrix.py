#!/usr/bin/env python3
"""
Unit tests for Classification Decision Matrix Service
"""

import pytest
from src.services.classification_decision_matrix import (
    ClassificationDecisionMatrix,
    Classification,
    FailureType,
    ClassificationScores,
    ClassificationResult,
    classify_failure
)


class TestClassificationScores:
    """Tests for ClassificationScores dataclass."""

    def test_normalization(self):
        """Test that scores are normalized to sum to 1.0."""
        scores = ClassificationScores(
            product_bug=0.4,
            automation_bug=0.4,
            infrastructure=0.2
        )
        total = scores.product_bug + scores.automation_bug + scores.infrastructure
        assert abs(total - 1.0) < 0.001

    def test_normalization_unequal(self):
        """Test normalization with unequal inputs."""
        scores = ClassificationScores(
            product_bug=0.9,
            automation_bug=0.05,
            infrastructure=0.05
        )
        assert scores.product_bug == 0.9
        assert scores.automation_bug == 0.05
        assert scores.infrastructure == 0.05

    def test_primary_classification(self):
        """Test primary classification selection."""
        scores = ClassificationScores(
            product_bug=0.7,
            automation_bug=0.2,
            infrastructure=0.1
        )
        assert scores.primary == Classification.PRODUCT_BUG

    def test_primary_automation_bug(self):
        """Test primary when automation bug wins."""
        scores = ClassificationScores(
            product_bug=0.2,
            automation_bug=0.6,
            infrastructure=0.2
        )
        assert scores.primary == Classification.AUTOMATION_BUG

    def test_primary_infrastructure(self):
        """Test primary when infrastructure wins."""
        scores = ClassificationScores(
            product_bug=0.1,
            automation_bug=0.1,
            infrastructure=0.8
        )
        assert scores.primary == Classification.INFRASTRUCTURE

    def test_separation_clear_winner(self):
        """Test separation with clear winner."""
        scores = ClassificationScores(
            product_bug=0.9,
            automation_bug=0.05,
            infrastructure=0.05
        )
        # Winner (0.9) - runner up (0.05) / winner (0.9) = 0.944
        assert scores.separation > 0.9

    def test_separation_close_race(self):
        """Test separation with close race."""
        scores = ClassificationScores(
            product_bug=0.4,
            automation_bug=0.35,
            infrastructure=0.25
        )
        # Should be relatively low separation
        assert scores.separation < 0.3

    def test_to_dict(self):
        """Test dictionary conversion."""
        scores = ClassificationScores(
            product_bug=0.5,
            automation_bug=0.3,
            infrastructure=0.2
        )
        result = scores.to_dict()
        assert "product_bug_score" in result
        assert "automation_bug_score" in result
        assert "infrastructure_score" in result
        assert "primary_classification" in result
        assert "score_separation" in result


class TestClassificationDecisionMatrix:
    """Tests for ClassificationDecisionMatrix class."""

    def setup_method(self):
        """Setup for each test."""
        self.matrix = ClassificationDecisionMatrix()

    def test_server_error_healthy_env(self):
        """Test server error with healthy environment → PRODUCT_BUG."""
        result = self.matrix.classify(
            failure_type="server_error",
            env_healthy=True,
            selector_found=True
        )
        assert result.classification == Classification.PRODUCT_BUG
        assert result.scores.product_bug > 0.8

    def test_element_not_found_selector_exists(self):
        """Test element not found with selector in codebase → AUTOMATION_BUG."""
        result = self.matrix.classify(
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=True
        )
        assert result.classification == Classification.AUTOMATION_BUG
        assert result.scores.automation_bug >= 0.5

    def test_element_not_found_selector_missing(self):
        """Test element not found with no selector in codebase → PRODUCT_BUG."""
        result = self.matrix.classify(
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=False
        )
        assert result.classification == Classification.PRODUCT_BUG
        assert result.scores.product_bug >= 0.5

    def test_timeout_healthy_env(self):
        """Test timeout with healthy environment → AUTOMATION_BUG."""
        result = self.matrix.classify(
            failure_type="timeout",
            env_healthy=True,
            selector_found=True
        )
        assert result.classification == Classification.AUTOMATION_BUG
        assert result.scores.automation_bug >= 0.5

    def test_timeout_unhealthy_env(self):
        """Test timeout with unhealthy environment → INFRASTRUCTURE."""
        result = self.matrix.classify(
            failure_type="timeout",
            env_healthy=False,
            selector_found=True
        )
        assert result.classification == Classification.INFRASTRUCTURE
        assert result.scores.infrastructure >= 0.5

    def test_network_error_unhealthy_env(self):
        """Test network error with unhealthy environment → INFRASTRUCTURE."""
        result = self.matrix.classify(
            failure_type="network",
            env_healthy=False,
            selector_found=True
        )
        assert result.classification == Classification.INFRASTRUCTURE
        assert result.scores.infrastructure >= 0.7

    def test_assertion_failure(self):
        """Test assertion failure with healthy environment → PRODUCT_BUG."""
        result = self.matrix.classify(
            failure_type="assertion",
            env_healthy=True,
            selector_found=True
        )
        assert result.classification == Classification.PRODUCT_BUG
        assert result.scores.product_bug >= 0.5

    def test_auth_error_healthy_env(self):
        """Test auth error with healthy environment → AUTOMATION_BUG."""
        result = self.matrix.classify(
            failure_type="auth_error",
            env_healthy=True,
            selector_found=True
        )
        assert result.classification == Classification.AUTOMATION_BUG
        assert result.scores.automation_bug >= 0.5

    def test_unknown_failure_type(self):
        """Test unknown failure type gets reasonable classification."""
        result = self.matrix.classify(
            failure_type="something_random",
            env_healthy=True,
            selector_found=True
        )
        assert result.classification in [
            Classification.PRODUCT_BUG,
            Classification.AUTOMATION_BUG,
            Classification.INFRASTRUCTURE
        ]

    def test_additional_factors_500_error(self):
        """Test additional factors boost product bug score."""
        result = self.matrix.classify(
            failure_type="timeout",
            env_healthy=True,
            selector_found=True,
            additional_factors={"console_500_error": True}
        )
        # 500 error should boost product bug
        assert result.scores.product_bug > 0.2

    def test_additional_factors_selector_changed(self):
        """Test selector recently changed boosts automation bug."""
        result = self.matrix.classify(
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=True,
            additional_factors={"selector_recently_changed": True}
        )
        # Should boost automation bug
        assert result.classification == Classification.AUTOMATION_BUG

    def test_additional_factors_connection_refused(self):
        """Test connection refused boosts infrastructure."""
        result = self.matrix.classify(
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=True,
            additional_factors={"console_connection_refused": True}
        )
        # Should boost infrastructure score
        assert result.scores.infrastructure > 0.1

    def test_confidence_high_separation(self):
        """Test confidence is higher with clear separation."""
        result = self.matrix.classify(
            failure_type="server_error",
            env_healthy=True,
            selector_found=True
        )
        # Server error is strongly product bug
        assert result.confidence >= 0.7

    def test_confidence_low_separation(self):
        """Test confidence is lower with unclear separation."""
        result = self.matrix.classify(
            failure_type="unknown",
            env_healthy=True,
            selector_found=True
        )
        # Unknown failure type has lower confidence
        assert result.confidence <= 0.8

    def test_reasoning_generated(self):
        """Test that reasoning is generated."""
        result = self.matrix.classify(
            failure_type="server_error",
            env_healthy=True,
            selector_found=True
        )
        assert len(result.reasoning) > 0
        assert "500" in result.reasoning.lower() or "backend" in result.reasoning.lower()

    def test_evidence_list(self):
        """Test that evidence list is populated."""
        result = self.matrix.classify(
            failure_type="timeout",
            env_healthy=True,
            selector_found=True
        )
        assert len(result.evidence) >= 3
        assert any("timeout" in e.lower() for e in result.evidence)

    def test_adjustments_list(self):
        """Test that adjustments are recorded."""
        result = self.matrix.classify(
            failure_type="timeout",
            env_healthy=True,
            selector_found=True,
            additional_factors={"console_500_error": True}
        )
        assert len(result.adjustments) >= 1

    def test_get_matrix_entry(self):
        """Test direct matrix entry retrieval."""
        product, automation, infra = self.matrix.get_matrix_entry(
            failure_type="server_error",
            env_healthy=True,
            selector_found=True
        )
        assert product == 0.90
        assert automation == 0.05
        assert infra == 0.05

    def test_result_to_dict(self):
        """Test ClassificationResult to_dict conversion."""
        result = self.matrix.classify(
            failure_type="timeout",
            env_healthy=True,
            selector_found=True
        )
        d = result.to_dict()
        assert "classification" in d
        assert "confidence" in d
        assert "reasoning" in d
        assert "evidence" in d
        assert "scores" in d


class TestConvenienceFunction:
    """Tests for the classify_failure convenience function."""

    def test_basic_usage(self):
        """Test basic convenience function usage."""
        result = classify_failure(
            failure_type="server_error",
            env_healthy=True,
            selector_found=True
        )
        assert isinstance(result, ClassificationResult)
        assert result.classification == Classification.PRODUCT_BUG

    def test_with_additional_factors(self):
        """Test convenience function with additional factors."""
        result = classify_failure(
            failure_type="timeout",
            env_healthy=True,
            selector_found=True,
            additional_factors={"console_500_error": True}
        )
        assert isinstance(result, ClassificationResult)

    def test_default_values(self):
        """Test convenience function with default values."""
        result = classify_failure(failure_type="timeout")
        assert isinstance(result, ClassificationResult)
        # Defaults to healthy env and selector found
        assert result.classification == Classification.AUTOMATION_BUG


class TestEdgeCases:
    """Edge case tests for classification."""

    def setup_method(self):
        """Setup for each test."""
        self.matrix = ClassificationDecisionMatrix()

    def test_all_false_factors(self):
        """Test with all additional factors false."""
        result = self.matrix.classify(
            failure_type="timeout",
            env_healthy=True,
            selector_found=True,
            additional_factors={
                "console_500_error": False,
                "selector_recently_changed": False,
            }
        )
        # Should not apply adjustments
        assert len(result.adjustments) == 0

    def test_multiple_adjustments(self):
        """Test with multiple adjustments applied."""
        result = self.matrix.classify(
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=True,
            additional_factors={
                "console_500_error": True,
                "selector_recently_changed": True,
            }
        )
        assert len(result.adjustments) >= 2

    def test_empty_failure_type(self):
        """Test with empty failure type."""
        result = self.matrix.classify(
            failure_type="",
            env_healthy=True,
            selector_found=True
        )
        # Should fall back to unknown
        assert result.classification is not None

    def test_failure_type_with_spaces(self):
        """Test failure type with spaces gets normalized."""
        result = self.matrix.classify(
            failure_type="element not found",
            env_healthy=True,
            selector_found=True
        )
        # Should normalize to element_not_found
        assert result.classification == Classification.AUTOMATION_BUG

    def test_failure_type_case_insensitive(self):
        """Test failure type is case insensitive."""
        result = self.matrix.classify(
            failure_type="SERVER_ERROR",
            env_healthy=True,
            selector_found=True
        )
        assert result.classification == Classification.PRODUCT_BUG
