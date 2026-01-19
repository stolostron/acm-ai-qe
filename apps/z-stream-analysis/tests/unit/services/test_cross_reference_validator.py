#!/usr/bin/env python3
"""
Unit tests for Cross-Reference Validator Service
"""

import pytest
from src.services.cross_reference_validator import (
    CrossReferenceValidator,
    ValidationAction,
    ValidationResult,
    CrossValidationReport,
    validate_classification
)


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = ValidationResult(
            rule_name="test_rule",
            action=ValidationAction.CORRECT,
            original_classification="AUTOMATION_BUG",
            suggested_classification="PRODUCT_BUG",
            confidence_adjustment=0.1,
            reason="Test reason",
            evidence=["Evidence 1"],
        )
        d = result.to_dict()
        assert d["rule_name"] == "test_rule"
        assert d["action"] == "correct"
        assert d["original_classification"] == "AUTOMATION_BUG"
        assert d["suggested_classification"] == "PRODUCT_BUG"


class TestCrossValidationReport:
    """Tests for CrossValidationReport dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        report = CrossValidationReport(
            original_classification="AUTOMATION_BUG",
            final_classification="PRODUCT_BUG",
            original_confidence=0.7,
            final_confidence=0.8,
            was_corrected=True,
            needs_review=False,
            summary="Test summary",
        )
        d = report.to_dict()
        assert d["original_classification"] == "AUTOMATION_BUG"
        assert d["final_classification"] == "PRODUCT_BUG"
        assert d["was_corrected"] is True


class TestCrossReferenceValidator:
    """Tests for CrossReferenceValidator class."""

    def setup_method(self):
        """Setup for each test."""
        self.validator = CrossReferenceValidator()

    def test_500_error_overrides_automation_bug(self):
        """Test that 500 errors override AUTOMATION_BUG to PRODUCT_BUG."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=True,
            console_has_500_errors=True,
        )

        assert report.was_corrected is True
        assert report.final_classification == "PRODUCT_BUG"
        assert report.final_confidence > report.original_confidence

    def test_500_error_confirms_product_bug(self):
        """Test that 500 errors boost PRODUCT_BUG confidence."""
        report = self.validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.7,
            failure_type="server_error",
            env_healthy=True,
            console_has_500_errors=True,
        )

        assert report.was_corrected is False
        assert report.final_classification == "PRODUCT_BUG"
        assert report.final_confidence > report.original_confidence

    def test_cluster_unhealthy_overrides_automation_bug(self):
        """Test that unhealthy cluster overrides AUTOMATION_BUG to INFRASTRUCTURE."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=False,
            cluster_accessible=False,
        )

        assert report.was_corrected is True
        assert report.final_classification == "INFRASTRUCTURE"

    def test_cluster_unhealthy_confirms_infrastructure(self):
        """Test that unhealthy cluster boosts INFRASTRUCTURE confidence."""
        report = self.validator.validate(
            classification="INFRASTRUCTURE",
            confidence=0.7,
            failure_type="network",
            env_healthy=False,
            cluster_accessible=False,
        )

        assert report.was_corrected is False
        assert report.final_confidence > report.original_confidence

    def test_selector_change_flags_product_bug(self):
        """Test that selector recently changed flags PRODUCT_BUG for review."""
        report = self.validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.7,
            failure_type="element_not_found",
            env_healthy=True,
            selector_recently_changed=True,
        )

        assert report.needs_review is True
        assert report.final_confidence < report.original_confidence

    def test_selector_change_confirms_automation_bug(self):
        """Test that selector recently changed boosts AUTOMATION_BUG."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="element_not_found",
            env_healthy=True,
            selector_recently_changed=True,
        )

        assert report.was_corrected is False
        assert report.final_confidence > report.original_confidence

    def test_infrastructure_with_healthy_env_flags(self):
        """Test that INFRASTRUCTURE with healthy env is flagged."""
        report = self.validator.validate(
            classification="INFRASTRUCTURE",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=True,
            cluster_accessible=True,
        )

        assert report.needs_review is True
        assert report.final_confidence < report.original_confidence

    def test_network_error_with_automation_bug_flags(self):
        """Test that network errors with AUTOMATION_BUG are flagged."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="element_not_found",
            env_healthy=True,
            console_has_network_errors=True,
        )

        assert report.needs_review is True

    def test_api_error_boosts_product_bug(self):
        """Test that API errors boost PRODUCT_BUG confidence."""
        report = self.validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.7,
            failure_type="server_error",
            env_healthy=True,
            console_has_api_errors=True,
        )

        assert report.final_confidence > report.original_confidence

    def test_element_not_found_selector_missing(self):
        """Test element_not_found with missing selector → PRODUCT_BUG."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=False,
        )

        assert report.was_corrected is True
        assert report.final_classification == "PRODUCT_BUG"

    def test_element_not_found_selector_confirms_product(self):
        """Test element_not_found with missing selector confirms PRODUCT_BUG."""
        report = self.validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.7,
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=False,
        )

        assert report.was_corrected is False
        assert report.final_confidence > report.original_confidence

    def test_timeout_healthy_env_confirms_automation(self):
        """Test timeout in healthy env confirms AUTOMATION_BUG."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=True,
        )

        assert report.final_confidence >= report.original_confidence

    def test_timeout_healthy_env_flags_infrastructure(self):
        """Test timeout in healthy env flags INFRASTRUCTURE."""
        report = self.validator.validate(
            classification="INFRASTRUCTURE",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=True,
        )

        assert report.needs_review is True

    def test_no_corrections_clean_scenario(self):
        """Test no corrections for consistent evidence."""
        report = self.validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.8,
            failure_type="server_error",
            env_healthy=True,
            selector_found=True,
        )

        assert report.was_corrected is False
        assert report.needs_review is False
        assert "validated" in report.summary.lower()

    def test_multiple_corrections_strongest_wins(self):
        """Test that strongest correction wins when multiple apply."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=False,
            cluster_accessible=False,
            console_has_500_errors=True,
        )

        # Should pick the strongest correction
        assert report.was_corrected is True
        # Cluster health has higher adjustment than 500 error
        assert report.final_classification in ["INFRASTRUCTURE", "PRODUCT_BUG"]

    def test_confidence_clamping(self):
        """Test that confidence is clamped to valid range."""
        # Many negative adjustments
        report = self.validator.validate(
            classification="INFRASTRUCTURE",
            confidence=0.3,
            failure_type="timeout",
            env_healthy=True,
            cluster_accessible=True,
        )

        assert report.final_confidence >= 0.1
        assert report.final_confidence <= 0.95

    def test_summary_generated(self):
        """Test that summary is generated."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=True,
        )

        assert len(report.summary) > 0

    def test_validation_results_populated(self):
        """Test that validation results list is populated."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="element_not_found",
            env_healthy=True,
            selector_recently_changed=True,
            console_has_500_errors=True,
        )

        assert len(report.validation_results) > 0


class TestConvenienceFunction:
    """Tests for validate_classification convenience function."""

    def test_basic_usage(self):
        """Test basic convenience function usage."""
        report = validate_classification(
            classification="PRODUCT_BUG",
            confidence=0.8,
            failure_type="server_error",
        )

        assert isinstance(report, CrossValidationReport)
        assert report.original_classification == "PRODUCT_BUG"

    def test_with_all_params(self):
        """Test with all parameters."""
        report = validate_classification(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=True,
            selector_found=True,
            console_has_500_errors=True,
        )

        assert isinstance(report, CrossValidationReport)
        assert report.was_corrected is True

    def test_default_values(self):
        """Test with default values."""
        report = validate_classification(
            classification="PRODUCT_BUG",
            confidence=0.8,
            failure_type="assertion",
        )

        # Should use defaults (env_healthy=True, etc.)
        assert report.needs_review is False


class TestEdgeCases:
    """Edge case tests for validation."""

    def setup_method(self):
        """Setup for each test."""
        self.validator = CrossReferenceValidator()

    def test_unknown_classification(self):
        """Test with unknown classification type."""
        report = self.validator.validate(
            classification="UNKNOWN",
            confidence=0.5,
            failure_type="unknown",
            env_healthy=True,
        )

        # Should not crash, return valid report
        assert isinstance(report, CrossValidationReport)

    def test_empty_failure_type(self):
        """Test with empty failure type."""
        report = self.validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.7,
            failure_type="",
            env_healthy=True,
        )

        assert isinstance(report, CrossValidationReport)

    def test_all_flags_false(self):
        """Test with all optional flags false."""
        report = self.validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.8,
            failure_type="server_error",
            env_healthy=True,
            selector_found=None,
            selector_recently_changed=None,
            console_has_500_errors=False,
            console_has_network_errors=False,
            console_has_api_errors=False,
            cluster_accessible=True,
            git_history_supports=None,
        )

        # Should get minimal validation results
        assert report.was_corrected is False

    def test_very_low_confidence(self):
        """Test with very low initial confidence."""
        report = self.validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.1,
            failure_type="timeout",
            env_healthy=True,
        )

        assert report.final_confidence >= 0.1

    def test_very_high_confidence(self):
        """Test with very high initial confidence."""
        report = self.validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.95,
            failure_type="server_error",
            env_healthy=True,
            console_has_500_errors=True,
        )

        # Should not exceed 0.95 even with boost
        assert report.final_confidence <= 0.95
