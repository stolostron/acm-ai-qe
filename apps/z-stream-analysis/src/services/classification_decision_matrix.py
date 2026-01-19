#!/usr/bin/env python3
"""
Classification Decision Matrix

Formal decision matrix for classifying test failures as:
- PRODUCT_BUG: Backend/API/feature issues
- AUTOMATION_BUG: Test code/framework issues
- INFRASTRUCTURE: Cluster/network/environment issues

Uses a weighted scoring system based on:
- failure_type: What type of error occurred
- env_healthy: Is the environment/cluster accessible
- selector_found: Is the failing selector in the codebase
- additional factors: Recent changes, console errors, etc.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any


class Classification(Enum):
    """Bug classification types."""
    PRODUCT_BUG = "PRODUCT_BUG"
    AUTOMATION_BUG = "AUTOMATION_BUG"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    UNKNOWN = "UNKNOWN"
    FLAKY = "FLAKY"


class FailureType(Enum):
    """Types of test failures."""
    TIMEOUT = "timeout"
    ELEMENT_NOT_FOUND = "element_not_found"
    ASSERTION = "assertion"
    NETWORK = "network"
    SERVER_ERROR = "server_error"
    AUTH_ERROR = "auth_error"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"


@dataclass
class ClassificationScores:
    """Weighted scores for each classification type."""
    product_bug: float = 0.0
    automation_bug: float = 0.0
    infrastructure: float = 0.0

    def __post_init__(self):
        """Normalize scores to sum to 1.0."""
        total = self.product_bug + self.automation_bug + self.infrastructure
        if total > 0:
            self.product_bug /= total
            self.automation_bug /= total
            self.infrastructure /= total

    @property
    def primary(self) -> Classification:
        """Get the primary (highest scoring) classification."""
        scores = {
            Classification.PRODUCT_BUG: self.product_bug,
            Classification.AUTOMATION_BUG: self.automation_bug,
            Classification.INFRASTRUCTURE: self.infrastructure,
        }
        return max(scores, key=scores.get)

    @property
    def separation(self) -> float:
        """How much the winner beats the runner-up (0-1)."""
        scores = sorted([self.product_bug, self.automation_bug, self.infrastructure], reverse=True)
        if scores[0] == 0:
            return 0.0
        return (scores[0] - scores[1]) / scores[0]

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "product_bug_score": round(self.product_bug, 3),
            "automation_bug_score": round(self.automation_bug, 3),
            "infrastructure_score": round(self.infrastructure, 3),
            "primary_classification": self.primary.value,
            "score_separation": round(self.separation, 3),
        }


@dataclass
class ClassificationResult:
    """Complete classification result with reasoning."""
    classification: Classification
    scores: ClassificationScores
    confidence: float
    reasoning: str
    evidence: List[str] = field(default_factory=list)
    adjustments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "classification": self.classification.value,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "scores": self.scores.to_dict(),
            "adjustments": self.adjustments,
        }


class ClassificationDecisionMatrix:
    """
    Formal decision matrix for failure classification.

    Combines failure_type + environment_status + repository_evidence
    to produce weighted classification scores.
    """

    # Core decision matrix
    # Key: (failure_type, env_healthy, selector_found)
    # Value: (product_bug_weight, automation_bug_weight, infrastructure_weight)
    MATRIX: Dict[Tuple[str, bool, bool], Tuple[float, float, float]] = {
        # TIMEOUT failures
        ('timeout', True, True): (0.20, 0.70, 0.10),   # Likely wait strategy issue
        ('timeout', True, False): (0.40, 0.50, 0.10),  # UI may have changed
        ('timeout', False, True): (0.10, 0.20, 0.70),  # Infra slowdown
        ('timeout', False, False): (0.20, 0.20, 0.60), # Infra affecting everything

        # ELEMENT_NOT_FOUND failures
        ('element_not_found', True, True): (0.30, 0.60, 0.10),   # Selector stale
        ('element_not_found', True, False): (0.60, 0.30, 0.10),  # UI changed, element gone
        ('element_not_found', False, True): (0.20, 0.30, 0.50),  # Page not loading
        ('element_not_found', False, False): (0.30, 0.30, 0.40), # Multiple factors

        # ASSERTION failures
        ('assertion', True, True): (0.70, 0.20, 0.10),   # Expected != actual
        ('assertion', True, False): (0.60, 0.30, 0.10),  # Test may have wrong expectation
        ('assertion', False, True): (0.30, 0.20, 0.50),  # Infra affecting data
        ('assertion', False, False): (0.40, 0.20, 0.40), # Mixed factors

        # NETWORK failures
        ('network', True, True): (0.60, 0.10, 0.30),   # Backend network issue
        ('network', True, False): (0.50, 0.20, 0.30),  # Backend issue
        ('network', False, True): (0.10, 0.10, 0.80),  # Cluster network issue
        ('network', False, False): (0.10, 0.10, 0.80), # Infrastructure down

        # SERVER_ERROR failures (5xx)
        ('server_error', True, True): (0.90, 0.05, 0.05),   # Backend bug
        ('server_error', True, False): (0.90, 0.05, 0.05),  # Backend bug
        ('server_error', False, True): (0.60, 0.10, 0.30),  # May be overload
        ('server_error', False, False): (0.50, 0.10, 0.40), # Mixed factors

        # AUTH_ERROR failures
        ('auth_error', True, True): (0.30, 0.60, 0.10),   # Test creds issue
        ('auth_error', True, False): (0.40, 0.50, 0.10),  # Could be either
        ('auth_error', False, True): (0.20, 0.30, 0.50),  # Infra auth issue
        ('auth_error', False, False): (0.20, 0.30, 0.50), # Infrastructure

        # NOT_FOUND failures (404)
        ('not_found', True, True): (0.70, 0.20, 0.10),   # Route/endpoint missing
        ('not_found', True, False): (0.60, 0.30, 0.10),  # Could be test or product
        ('not_found', False, True): (0.30, 0.20, 0.50),  # Service may be down
        ('not_found', False, False): (0.30, 0.20, 0.50), # Infrastructure

        # UNKNOWN failures
        ('unknown', True, True): (0.40, 0.40, 0.20),
        ('unknown', True, False): (0.40, 0.40, 0.20),
        ('unknown', False, True): (0.30, 0.30, 0.40),
        ('unknown', False, False): (0.30, 0.30, 0.40),
    }

    # Adjustment factors for additional evidence
    ADJUSTMENTS = {
        # Console log patterns that suggest product bugs
        'console_500_error': (0.20, -0.10, -0.10),
        'console_api_error': (0.15, -0.05, -0.10),
        'console_backend_error': (0.15, -0.05, -0.10),

        # Console log patterns that suggest infrastructure
        'console_connection_refused': (-0.10, -0.10, 0.20),
        'console_dns_error': (-0.10, -0.10, 0.20),
        'console_cluster_error': (-0.10, -0.05, 0.15),

        # Repository evidence
        'selector_recently_changed': (-0.10, 0.15, -0.05),
        'selector_never_existed': (-0.05, 0.20, -0.05),
        'test_file_recently_changed': (-0.05, 0.10, -0.05),

        # Historical patterns
        'flaky_test_history': (-0.10, 0.10, 0.00),
        'first_time_failure': (0.05, 0.05, -0.05),
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def classify(
        self,
        failure_type: str,
        env_healthy: bool,
        selector_found: bool,
        additional_factors: Optional[Dict[str, bool]] = None
    ) -> ClassificationResult:
        """
        Apply decision matrix to get weighted classification.

        Args:
            failure_type: Type of failure (timeout, element_not_found, etc.)
            env_healthy: Whether the environment/cluster is healthy
            selector_found: Whether the failing selector exists in codebase
            additional_factors: Dict of adjustment factor names to apply

        Returns:
            ClassificationResult with scores, classification, and reasoning
        """
        # Normalize failure type
        failure_type = failure_type.lower().replace(' ', '_')
        if failure_type not in [ft.value for ft in FailureType]:
            failure_type = 'unknown'

        # Get base scores from matrix
        key = (failure_type, env_healthy, selector_found)
        if key not in self.MATRIX:
            # Default fallback
            key = ('unknown', env_healthy, selector_found)

        product, automation, infra = self.MATRIX.get(
            key, (0.33, 0.34, 0.33)
        )

        evidence = []
        adjustments_applied = []

        # Build evidence list
        evidence.append(f"Failure type: {failure_type}")
        evidence.append(f"Environment healthy: {env_healthy}")
        evidence.append(f"Selector found in codebase: {selector_found}")

        # Apply additional adjustments
        if additional_factors:
            for factor_name, applies in additional_factors.items():
                if applies and factor_name in self.ADJUSTMENTS:
                    adj = self.ADJUSTMENTS[factor_name]
                    product += adj[0]
                    automation += adj[1]
                    infra += adj[2]
                    adjustments_applied.append(
                        f"{factor_name}: product {adj[0]:+.2f}, automation {adj[1]:+.2f}, infra {adj[2]:+.2f}"
                    )

        # Ensure non-negative scores
        product = max(0, product)
        automation = max(0, automation)
        infra = max(0, infra)

        # Create normalized scores
        scores = ClassificationScores(
            product_bug=product,
            automation_bug=automation,
            infrastructure=infra
        )

        # Determine primary classification
        classification = scores.primary

        # Calculate confidence based on score separation
        # Higher separation = higher confidence
        base_confidence = 0.5 + (0.4 * scores.separation)

        # Adjust confidence based on evidence quality
        if not env_healthy and classification != Classification.INFRASTRUCTURE:
            base_confidence *= 0.85  # Less confident if env unhealthy but not classifying as infra

        if not selector_found and classification == Classification.AUTOMATION_BUG:
            base_confidence *= 0.9  # Slightly less confident

        confidence = min(0.95, max(0.3, base_confidence))

        # Generate reasoning
        reasoning = self._generate_reasoning(
            failure_type, env_healthy, selector_found,
            classification, scores
        )

        return ClassificationResult(
            classification=classification,
            scores=scores,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
            adjustments=adjustments_applied
        )

    def _generate_reasoning(
        self,
        failure_type: str,
        env_healthy: bool,
        selector_found: bool,
        classification: Classification,
        scores: ClassificationScores
    ) -> str:
        """Generate human-readable reasoning for the classification."""
        reasons = []

        # Primary classification reasoning
        if classification == Classification.PRODUCT_BUG:
            if failure_type == 'server_error':
                reasons.append("Server returned 5xx error indicating backend issue")
            elif failure_type == 'assertion':
                reasons.append("Assertion failure suggests unexpected product behavior")
            elif failure_type == 'element_not_found' and not selector_found:
                reasons.append("Element not found and selector doesn't exist in codebase - UI likely changed")
            elif failure_type == 'not_found':
                reasons.append("Resource not found (404) suggests missing API endpoint or route")
            else:
                reasons.append("Evidence points to product-side issue")

        elif classification == Classification.AUTOMATION_BUG:
            if failure_type == 'element_not_found' and selector_found:
                reasons.append("Element not found but selector exists in codebase - likely stale selector")
            elif failure_type == 'timeout' and env_healthy:
                reasons.append("Timeout in healthy environment suggests wait strategy issue")
            elif failure_type == 'auth_error':
                reasons.append("Authentication error may indicate test credential configuration issue")
            else:
                reasons.append("Evidence suggests test code needs update")

        elif classification == Classification.INFRASTRUCTURE:
            if not env_healthy:
                reasons.append("Environment is unhealthy - cluster connectivity issue")
            elif failure_type == 'network':
                reasons.append("Network error indicates connectivity or infrastructure issue")
            elif failure_type == 'timeout' and not env_healthy:
                reasons.append("Timeout in unhealthy environment suggests infrastructure slowdown")
            else:
                reasons.append("Evidence points to infrastructure/environment issue")

        # Add score context
        reasons.append(
            f"Scores: Product {scores.product_bug:.0%}, "
            f"Automation {scores.automation_bug:.0%}, "
            f"Infrastructure {scores.infrastructure:.0%}"
        )

        return ". ".join(reasons)

    def get_matrix_entry(
        self,
        failure_type: str,
        env_healthy: bool,
        selector_found: bool
    ) -> Tuple[float, float, float]:
        """
        Get raw matrix entry for a given condition.

        Returns:
            Tuple of (product_weight, automation_weight, infrastructure_weight)
        """
        key = (failure_type.lower(), env_healthy, selector_found)
        return self.MATRIX.get(key, (0.33, 0.34, 0.33))


def classify_failure(
    failure_type: str,
    env_healthy: bool = True,
    selector_found: bool = True,
    additional_factors: Optional[Dict[str, bool]] = None
) -> ClassificationResult:
    """Convenience function to classify a failure."""
    matrix = ClassificationDecisionMatrix()
    return matrix.classify(failure_type, env_healthy, selector_found, additional_factors)
