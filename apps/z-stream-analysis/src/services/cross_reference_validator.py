#!/usr/bin/env python3
"""
Cross-Reference Validator Service

Catches misclassifications by checking evidence consistency.
Applies validation rules to detect when classification contradicts
strong evidence signals.

Key validation scenarios:
- AUTOMATION_BUG with 500 errors in console → correct to PRODUCT_BUG
- AUTOMATION_BUG with cluster unhealthy → correct to INFRASTRUCTURE
- PRODUCT_BUG with selector recently changed → flag for review
- INFRASTRUCTURE with no env issues → flag for review
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class ValidationAction(Enum):
    """Actions the validator can recommend."""
    KEEP = "keep"              # Classification is consistent
    CORRECT = "correct"        # Strong evidence to change classification
    FLAG_REVIEW = "flag"       # Conflicting signals, needs human review
    BOOST_CONFIDENCE = "boost" # Evidence strongly supports classification
    REDUCE_CONFIDENCE = "reduce"  # Some inconsistency detected


@dataclass
class ValidationRule:
    """A single validation rule."""
    name: str
    description: str
    priority: int = 0  # Higher = more important


@dataclass
class ValidationResult:
    """Result of a validation check."""
    rule_name: str
    action: ValidationAction
    original_classification: str
    suggested_classification: Optional[str] = None
    confidence_adjustment: float = 0.0  # Positive = boost, negative = reduce
    reason: str = ""
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_name": self.rule_name,
            "action": self.action.value,
            "original_classification": self.original_classification,
            "suggested_classification": self.suggested_classification,
            "confidence_adjustment": round(self.confidence_adjustment, 3),
            "reason": self.reason,
            "evidence": self.evidence,
        }


@dataclass
class CrossValidationReport:
    """Complete cross-validation report."""
    original_classification: str
    final_classification: str
    original_confidence: float
    final_confidence: float
    was_corrected: bool = False
    needs_review: bool = False
    validation_results: List[ValidationResult] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_classification": self.original_classification,
            "final_classification": self.final_classification,
            "original_confidence": round(self.original_confidence, 3),
            "final_confidence": round(self.final_confidence, 3),
            "was_corrected": self.was_corrected,
            "needs_review": self.needs_review,
            "validation_results": [v.to_dict() for v in self.validation_results],
            "summary": self.summary,
        }


class CrossReferenceValidator:
    """
    Validates classifications by cross-referencing evidence.

    Catches common misclassification scenarios and either corrects
    them automatically or flags them for human review.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate(
        self,
        classification: str,
        confidence: float,
        failure_type: str,
        env_healthy: bool,
        selector_found: Optional[bool] = None,
        selector_recently_changed: Optional[bool] = None,
        console_has_500_errors: bool = False,
        console_has_network_errors: bool = False,
        console_has_api_errors: bool = False,
        cluster_accessible: bool = True,
        git_history_supports: Optional[bool] = None,
    ) -> CrossValidationReport:
        """
        Validate a classification against all evidence.

        Args:
            classification: Current classification (PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE)
            confidence: Current confidence score (0-1)
            failure_type: Type of failure (timeout, element_not_found, etc.)
            env_healthy: Whether environment is healthy
            selector_found: Whether failing selector was found in codebase
            selector_recently_changed: Whether selector was recently modified
            console_has_500_errors: Whether console log has 500 errors
            console_has_network_errors: Whether console has connection/network errors
            console_has_api_errors: Whether console has API errors
            cluster_accessible: Whether cluster is accessible
            git_history_supports: Whether git history supports classification

        Returns:
            CrossValidationReport with validation results
        """
        report = CrossValidationReport(
            original_classification=classification,
            final_classification=classification,
            original_confidence=confidence,
            final_confidence=confidence,
        )

        # Collect all validation results
        results = []

        # Rule 1: AUTOMATION_BUG with 500 errors → PRODUCT_BUG
        results.append(self._check_500_errors_override(
            classification, console_has_500_errors
        ))

        # Rule 2: AUTOMATION_BUG with cluster unhealthy → INFRASTRUCTURE
        results.append(self._check_cluster_health_override(
            classification, env_healthy, cluster_accessible
        ))

        # Rule 3: PRODUCT_BUG with selector recently changed → FLAG
        results.append(self._check_selector_change_conflict(
            classification, selector_recently_changed
        ))

        # Rule 4: INFRASTRUCTURE with healthy env → FLAG
        results.append(self._check_infrastructure_env_conflict(
            classification, env_healthy, cluster_accessible
        ))

        # Rule 5: Network errors with AUTOMATION_BUG → FLAG
        results.append(self._check_network_error_conflict(
            classification, console_has_network_errors
        ))

        # Rule 6: API errors support PRODUCT_BUG
        results.append(self._check_api_error_support(
            classification, console_has_api_errors
        ))

        # Rule 7: Element not found + selector not found → PRODUCT_BUG
        results.append(self._check_element_not_found_no_selector(
            classification, failure_type, selector_found
        ))

        # Rule 8: Timeout + healthy env → AUTOMATION_BUG
        results.append(self._check_timeout_healthy_env(
            classification, failure_type, env_healthy
        ))

        # Filter out None results
        valid_results = [r for r in results if r is not None]
        report.validation_results = valid_results

        # Apply corrections and adjustments
        self._apply_validations(report)

        return report

    def _check_500_errors_override(
        self, classification: str, has_500_errors: bool
    ) -> Optional[ValidationResult]:
        """
        Rule: If classified as AUTOMATION_BUG but console has 500 errors,
        this is likely a PRODUCT_BUG.
        """
        if classification == "AUTOMATION_BUG" and has_500_errors:
            return ValidationResult(
                rule_name="500_error_override",
                action=ValidationAction.CORRECT,
                original_classification=classification,
                suggested_classification="PRODUCT_BUG",
                confidence_adjustment=0.1,
                reason="Console log contains 500 errors indicating backend issue",
                evidence=["HTTP 500 error detected in console log"],
            )
        elif classification == "PRODUCT_BUG" and has_500_errors:
            return ValidationResult(
                rule_name="500_error_confirm",
                action=ValidationAction.BOOST_CONFIDENCE,
                original_classification=classification,
                confidence_adjustment=0.1,
                reason="500 errors in console confirm product bug classification",
                evidence=["HTTP 500 error supports PRODUCT_BUG classification"],
            )
        return None

    def _check_cluster_health_override(
        self, classification: str, env_healthy: bool, cluster_accessible: bool
    ) -> Optional[ValidationResult]:
        """
        Rule: If classified as AUTOMATION_BUG but cluster is unhealthy,
        this is likely INFRASTRUCTURE.
        """
        if classification == "AUTOMATION_BUG" and (not env_healthy or not cluster_accessible):
            return ValidationResult(
                rule_name="cluster_health_override",
                action=ValidationAction.CORRECT,
                original_classification=classification,
                suggested_classification="INFRASTRUCTURE",
                confidence_adjustment=0.15,
                reason="Cluster is unhealthy - infrastructure issue likely cause",
                evidence=[
                    f"Environment healthy: {env_healthy}",
                    f"Cluster accessible: {cluster_accessible}",
                ],
            )
        elif classification == "INFRASTRUCTURE" and not cluster_accessible:
            return ValidationResult(
                rule_name="cluster_health_confirm",
                action=ValidationAction.BOOST_CONFIDENCE,
                original_classification=classification,
                confidence_adjustment=0.15,
                reason="Cluster inaccessible confirms infrastructure classification",
                evidence=["Cluster connection failed"],
            )
        return None

    def _check_selector_change_conflict(
        self, classification: str, selector_recently_changed: Optional[bool]
    ) -> Optional[ValidationResult]:
        """
        Rule: If classified as PRODUCT_BUG but selector recently changed,
        flag for review - might be AUTOMATION_BUG.
        """
        if classification == "PRODUCT_BUG" and selector_recently_changed is True:
            return ValidationResult(
                rule_name="selector_change_conflict",
                action=ValidationAction.FLAG_REVIEW,
                original_classification=classification,
                suggested_classification="AUTOMATION_BUG",
                confidence_adjustment=-0.1,
                reason="Selector was recently changed - may be stale selector issue",
                evidence=["Selector modified in recent commit"],
            )
        elif classification == "AUTOMATION_BUG" and selector_recently_changed is True:
            return ValidationResult(
                rule_name="selector_change_confirm",
                action=ValidationAction.BOOST_CONFIDENCE,
                original_classification=classification,
                confidence_adjustment=0.1,
                reason="Recent selector change supports automation bug classification",
                evidence=["Selector modification detected in git history"],
            )
        return None

    def _check_infrastructure_env_conflict(
        self, classification: str, env_healthy: bool, cluster_accessible: bool
    ) -> Optional[ValidationResult]:
        """
        Rule: If classified as INFRASTRUCTURE but environment is fully healthy,
        flag for review.
        """
        if classification == "INFRASTRUCTURE" and env_healthy and cluster_accessible:
            return ValidationResult(
                rule_name="infrastructure_env_conflict",
                action=ValidationAction.FLAG_REVIEW,
                original_classification=classification,
                suggested_classification=None,
                confidence_adjustment=-0.15,
                reason="Environment appears healthy - infrastructure classification may be incorrect",
                evidence=[
                    "Environment validation passed",
                    "Cluster is accessible",
                ],
            )
        return None

    def _check_network_error_conflict(
        self, classification: str, has_network_errors: bool
    ) -> Optional[ValidationResult]:
        """
        Rule: If classified as AUTOMATION_BUG but console has network errors,
        flag for review.
        """
        if classification == "AUTOMATION_BUG" and has_network_errors:
            return ValidationResult(
                rule_name="network_error_conflict",
                action=ValidationAction.FLAG_REVIEW,
                original_classification=classification,
                suggested_classification="INFRASTRUCTURE",
                confidence_adjustment=-0.1,
                reason="Network errors detected - may be infrastructure issue",
                evidence=["Network/connection errors in console log"],
            )
        return None

    def _check_api_error_support(
        self, classification: str, has_api_errors: bool
    ) -> Optional[ValidationResult]:
        """
        Rule: API errors in console support PRODUCT_BUG classification.
        """
        if classification == "PRODUCT_BUG" and has_api_errors:
            return ValidationResult(
                rule_name="api_error_support",
                action=ValidationAction.BOOST_CONFIDENCE,
                original_classification=classification,
                confidence_adjustment=0.05,
                reason="API errors in console support product bug classification",
                evidence=["API error patterns detected"],
            )
        return None

    def _check_element_not_found_no_selector(
        self, classification: str, failure_type: str, selector_found: Optional[bool]
    ) -> Optional[ValidationResult]:
        """
        Rule: If element_not_found and selector doesn't exist in codebase,
        flag for review rather than auto-correcting.

        NOTE: This rule does NOT auto-correct to PRODUCT_BUG because
        TimelineComparisonService provides more accurate classification by
        comparing git modification dates between automation and console repos.

        - If console changed AFTER automation → AUTOMATION_BUG (automation fell behind)
        - If automation changed AFTER console → PRODUCT_BUG (UI broke something)

        Without timeline data, missing selector could be either - flag for review.
        """
        if failure_type == "element_not_found" and selector_found is False:
            if classification == "AUTOMATION_BUG":
                # This could be correct if automation fell behind - just flag for review
                return ValidationResult(
                    rule_name="element_selector_mismatch",
                    action=ValidationAction.FLAG_REVIEW,
                    original_classification=classification,
                    suggested_classification=None,  # Don't suggest - timeline data is better
                    confidence_adjustment=-0.05,
                    reason="Selector not in codebase - verify with timeline comparison if available",
                    evidence=[
                        "Failure type: element_not_found",
                        "Selector not found in repository",
                        "Note: TimelineComparisonService provides more accurate classification",
                    ],
                )
            elif classification == "PRODUCT_BUG":
                return ValidationResult(
                    rule_name="element_selector_confirm",
                    action=ValidationAction.BOOST_CONFIDENCE,
                    original_classification=classification,
                    confidence_adjustment=0.05,  # Reduced from 0.1 - timeline data is more reliable
                    reason="Selector not in codebase supports UI change (product bug)",
                    evidence=["Selector not found in repository search"],
                )
        return None

    def _check_timeout_healthy_env(
        self, classification: str, failure_type: str, env_healthy: bool
    ) -> Optional[ValidationResult]:
        """
        Rule: Timeout with healthy environment is likely AUTOMATION_BUG
        (wait strategy issue).
        """
        if failure_type == "timeout" and env_healthy:
            if classification == "AUTOMATION_BUG":
                return ValidationResult(
                    rule_name="timeout_healthy_confirm",
                    action=ValidationAction.BOOST_CONFIDENCE,
                    original_classification=classification,
                    confidence_adjustment=0.1,
                    reason="Timeout in healthy environment suggests wait strategy issue",
                    evidence=[
                        "Failure type: timeout",
                        "Environment is healthy",
                    ],
                )
            elif classification == "INFRASTRUCTURE":
                return ValidationResult(
                    rule_name="timeout_healthy_conflict",
                    action=ValidationAction.FLAG_REVIEW,
                    original_classification=classification,
                    suggested_classification="AUTOMATION_BUG",
                    confidence_adjustment=-0.1,
                    reason="Timeout in healthy environment - likely not infrastructure",
                    evidence=["Environment validation passed"],
                )
        return None

    def _apply_validations(self, report: CrossValidationReport) -> None:
        """Apply all validation results to the report."""
        corrections = []
        flags = []
        confidence_delta = 0.0

        for result in report.validation_results:
            if result.action == ValidationAction.CORRECT:
                corrections.append(result)
                confidence_delta += result.confidence_adjustment
            elif result.action == ValidationAction.FLAG_REVIEW:
                flags.append(result)
                confidence_delta += result.confidence_adjustment
            elif result.action == ValidationAction.BOOST_CONFIDENCE:
                confidence_delta += result.confidence_adjustment
            elif result.action == ValidationAction.REDUCE_CONFIDENCE:
                confidence_delta += result.confidence_adjustment

        # Apply strongest correction (if any)
        if corrections:
            # Sort by confidence adjustment (highest = strongest evidence)
            corrections.sort(key=lambda x: x.confidence_adjustment, reverse=True)
            strongest = corrections[0]
            if strongest.suggested_classification:
                report.final_classification = strongest.suggested_classification
                report.was_corrected = True

        # Mark for review if there are flags
        if flags:
            report.needs_review = True

        # Apply confidence adjustment
        report.final_confidence = max(0.1, min(0.95,
            report.original_confidence + confidence_delta
        ))

        # Generate summary
        report.summary = self._generate_summary(report, corrections, flags)

    def _generate_summary(
        self,
        report: CrossValidationReport,
        corrections: List[ValidationResult],
        flags: List[ValidationResult]
    ) -> str:
        """Generate human-readable summary."""
        parts = []

        if report.was_corrected:
            parts.append(
                f"Classification corrected from {report.original_classification} "
                f"to {report.final_classification}"
            )
            if corrections:
                parts.append(f"Reason: {corrections[0].reason}")

        if report.needs_review:
            parts.append("Manual review recommended due to conflicting evidence")
            for flag in flags:
                parts.append(f"- {flag.reason}")

        if not report.was_corrected and not report.needs_review:
            parts.append("Classification validated - no conflicts detected")

        confidence_change = report.final_confidence - report.original_confidence
        if abs(confidence_change) > 0.05:
            direction = "increased" if confidence_change > 0 else "decreased"
            parts.append(
                f"Confidence {direction} by {abs(confidence_change):.1%}"
            )

        return ". ".join(parts)


def validate_classification(
    classification: str,
    confidence: float,
    failure_type: str,
    env_healthy: bool = True,
    selector_found: Optional[bool] = None,
    console_has_500_errors: bool = False,
) -> CrossValidationReport:
    """Convenience function for cross-validation."""
    validator = CrossReferenceValidator()
    return validator.validate(
        classification=classification,
        confidence=confidence,
        failure_type=failure_type,
        env_healthy=env_healthy,
        selector_found=selector_found,
        console_has_500_errors=console_has_500_errors,
    )
