#!/usr/bin/env python3
"""
Confidence Calculator Service

Multi-factor confidence scoring for failure classifications.
Combines multiple evidence quality signals to produce a reliable
confidence score that reflects how certain we are about a classification.

Factors considered:
- Score separation: How clearly one classification wins
- Evidence completeness: How much data we have
- Source consistency: Do different sources agree
- Selector certainty: How sure are we about selector status
- History signal: Does git history support the classification
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class EvidenceCompleteness:
    """Tracks what evidence is available."""
    has_stack_trace: bool = False
    has_parsed_frames: bool = False
    has_root_cause_file: bool = False
    has_environment_status: bool = False
    has_repository_analysis: bool = False
    has_selector_lookup: bool = False
    has_git_history: bool = False
    has_console_errors: bool = False
    has_test_file_content: bool = False

    @property
    def completeness_score(self) -> float:
        """Calculate overall completeness (0-1)."""
        factors = [
            self.has_stack_trace,
            self.has_parsed_frames,
            self.has_root_cause_file,
            self.has_environment_status,
            self.has_repository_analysis,
            self.has_selector_lookup,
            self.has_git_history,
            self.has_console_errors,
            self.has_test_file_content,
        ]
        return sum(1 for f in factors if f) / len(factors)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_stack_trace": self.has_stack_trace,
            "has_parsed_frames": self.has_parsed_frames,
            "has_root_cause_file": self.has_root_cause_file,
            "has_environment_status": self.has_environment_status,
            "has_repository_analysis": self.has_repository_analysis,
            "has_selector_lookup": self.has_selector_lookup,
            "has_git_history": self.has_git_history,
            "has_console_errors": self.has_console_errors,
            "has_test_file_content": self.has_test_file_content,
            "completeness_score": round(self.completeness_score, 3),
        }


@dataclass
class SourceConsistency:
    """Tracks agreement between different evidence sources."""
    jenkins_suggests: Optional[str] = None  # Classification from Jenkins data
    environment_suggests: Optional[str] = None  # Classification from env status
    repository_suggests: Optional[str] = None  # Classification from repo analysis
    console_suggests: Optional[str] = None  # Classification from console errors

    @property
    def consistency_score(self) -> float:
        """Calculate how much sources agree (0-1)."""
        suggestions = [
            self.jenkins_suggests,
            self.environment_suggests,
            self.repository_suggests,
            self.console_suggests,
        ]
        # Filter out None values
        valid_suggestions = [s for s in suggestions if s is not None]

        if len(valid_suggestions) < 2:
            return 0.5  # Not enough sources to compare

        # Count occurrences of each classification
        counts: Dict[str, int] = {}
        for s in valid_suggestions:
            counts[s] = counts.get(s, 0) + 1

        # Find the most common classification
        max_count = max(counts.values())

        # Consistency = percentage of sources that agree with majority
        return max_count / len(valid_suggestions)

    @property
    def dominant_suggestion(self) -> Optional[str]:
        """Get the most common suggestion."""
        suggestions = [
            self.jenkins_suggests,
            self.environment_suggests,
            self.repository_suggests,
            self.console_suggests,
        ]
        valid = [s for s in suggestions if s is not None]

        if not valid:
            return None

        counts: Dict[str, int] = {}
        for s in valid:
            counts[s] = counts.get(s, 0) + 1

        return max(counts, key=counts.get)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "jenkins_suggests": self.jenkins_suggests,
            "environment_suggests": self.environment_suggests,
            "repository_suggests": self.repository_suggests,
            "console_suggests": self.console_suggests,
            "consistency_score": round(self.consistency_score, 3),
            "dominant_suggestion": self.dominant_suggestion,
        }


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence factors."""
    score_separation: float = 0.0
    evidence_completeness: float = 0.0
    source_consistency: float = 0.0
    selector_certainty: float = 0.0
    history_signal: float = 0.0

    final_confidence: float = 0.0
    confidence_level: str = "UNKNOWN"  # HIGH, MEDIUM, LOW, UNKNOWN

    factors_detail: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "final_confidence": round(self.final_confidence, 3),
            "confidence_level": self.confidence_level,
            "factors": {
                "score_separation": round(self.score_separation, 3),
                "evidence_completeness": round(self.evidence_completeness, 3),
                "source_consistency": round(self.source_consistency, 3),
                "selector_certainty": round(self.selector_certainty, 3),
                "history_signal": round(self.history_signal, 3),
            },
            "factors_detail": self.factors_detail,
            "warnings": self.warnings,
        }


class ConfidenceCalculator:
    """
    Multi-factor confidence calculation for failure classifications.

    Combines weighted factors to produce a confidence score that
    accurately reflects the certainty of a classification.
    """

    # Weight of each factor in final confidence
    WEIGHTS = {
        'score_separation': 0.30,      # How clearly one classification wins
        'evidence_completeness': 0.25,  # How much data we have
        'source_consistency': 0.20,    # Do sources agree
        'selector_certainty': 0.15,    # How sure about selector status
        'history_signal': 0.10,        # Git history support
    }

    # Thresholds for confidence levels
    THRESHOLDS = {
        'HIGH': 0.75,
        'MEDIUM': 0.50,
        'LOW': 0.30,
    }

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def calculate(
        self,
        classification_scores: Dict[str, float],
        evidence_completeness: EvidenceCompleteness,
        source_consistency: SourceConsistency,
        selector_found: Optional[bool] = None,
        selector_recently_changed: Optional[bool] = None,
        git_history_supports: Optional[bool] = None,
    ) -> ConfidenceBreakdown:
        """
        Calculate multi-factor confidence score.

        Args:
            classification_scores: Dict with product_bug, automation_bug, infrastructure scores
            evidence_completeness: EvidenceCompleteness instance
            source_consistency: SourceConsistency instance
            selector_found: Whether failing selector was found in codebase
            selector_recently_changed: Whether selector was recently modified
            git_history_supports: Whether git history supports the classification

        Returns:
            ConfidenceBreakdown with detailed confidence information
        """
        breakdown = ConfidenceBreakdown()
        breakdown.factors_detail = {}

        # Factor 1: Score Separation (0-1)
        # How clearly does the winning classification beat the others?
        breakdown.score_separation = self._calculate_score_separation(
            classification_scores
        )
        breakdown.factors_detail['score_separation'] = {
            'scores': classification_scores,
            'separation': breakdown.score_separation,
        }

        # Factor 2: Evidence Completeness (0-1)
        breakdown.evidence_completeness = evidence_completeness.completeness_score
        breakdown.factors_detail['evidence_completeness'] = evidence_completeness.to_dict()

        # Factor 3: Source Consistency (0-1)
        breakdown.source_consistency = source_consistency.consistency_score
        breakdown.factors_detail['source_consistency'] = source_consistency.to_dict()

        # Factor 4: Selector Certainty (0-1)
        breakdown.selector_certainty = self._calculate_selector_certainty(
            selector_found, selector_recently_changed
        )
        breakdown.factors_detail['selector_certainty'] = {
            'selector_found': selector_found,
            'selector_recently_changed': selector_recently_changed,
            'certainty': breakdown.selector_certainty,
        }

        # Factor 5: History Signal (0-1)
        breakdown.history_signal = self._calculate_history_signal(
            git_history_supports, selector_recently_changed
        )
        breakdown.factors_detail['history_signal'] = {
            'git_history_supports': git_history_supports,
            'signal': breakdown.history_signal,
        }

        # Calculate weighted final confidence
        breakdown.final_confidence = (
            self.WEIGHTS['score_separation'] * breakdown.score_separation +
            self.WEIGHTS['evidence_completeness'] * breakdown.evidence_completeness +
            self.WEIGHTS['source_consistency'] * breakdown.source_consistency +
            self.WEIGHTS['selector_certainty'] * breakdown.selector_certainty +
            self.WEIGHTS['history_signal'] * breakdown.history_signal
        )

        # Clamp to valid range
        breakdown.final_confidence = max(0.1, min(0.95, breakdown.final_confidence))

        # Determine confidence level
        if breakdown.final_confidence >= self.THRESHOLDS['HIGH']:
            breakdown.confidence_level = 'HIGH'
        elif breakdown.final_confidence >= self.THRESHOLDS['MEDIUM']:
            breakdown.confidence_level = 'MEDIUM'
        elif breakdown.final_confidence >= self.THRESHOLDS['LOW']:
            breakdown.confidence_level = 'LOW'
        else:
            breakdown.confidence_level = 'VERY_LOW'

        # Add warnings for low confidence areas
        breakdown.warnings = self._generate_warnings(breakdown)

        return breakdown

    def _calculate_score_separation(self, scores: Dict[str, float]) -> float:
        """
        Calculate how clearly one classification wins.

        Returns 1.0 if winner has 100% score, 0.0 if it's a three-way tie.
        """
        if not scores:
            return 0.0

        sorted_scores = sorted(scores.values(), reverse=True)

        if len(sorted_scores) < 2:
            return 1.0

        winner = sorted_scores[0]
        runner_up = sorted_scores[1]

        if winner == 0:
            return 0.0

        # How much winner beats runner-up relative to winner's score
        separation = (winner - runner_up) / winner

        # Apply mild boost for very clear wins
        if separation > 0.5:
            separation = min(1.0, separation * 1.1)

        return separation

    def _calculate_selector_certainty(
        self,
        selector_found: Optional[bool],
        selector_recently_changed: Optional[bool]
    ) -> float:
        """
        Calculate certainty about selector status.

        High certainty when we definitively know selector status.
        Low certainty when we couldn't determine or it's ambiguous.
        """
        if selector_found is None:
            return 0.3  # Unknown - low certainty

        if selector_found:
            # Selector exists
            if selector_recently_changed is True:
                return 0.9  # High certainty - we know it changed recently
            elif selector_recently_changed is False:
                return 0.85  # Good certainty - selector exists, not recently changed
            else:
                return 0.7  # Moderate certainty - exists but unknown history
        else:
            # Selector not found
            return 0.8  # Good certainty - definitely not in codebase

    def _calculate_history_signal(
        self,
        git_history_supports: Optional[bool],
        selector_recently_changed: Optional[bool]
    ) -> float:
        """
        Calculate how much git history supports the classification.
        """
        if git_history_supports is None and selector_recently_changed is None:
            return 0.5  # No history information - neutral

        score = 0.5  # Start neutral

        if git_history_supports is True:
            score += 0.3  # History supports classification
        elif git_history_supports is False:
            score -= 0.2  # History contradicts

        if selector_recently_changed is True:
            score += 0.2  # Recent change provides strong signal

        return max(0.0, min(1.0, score))

    def _generate_warnings(self, breakdown: ConfidenceBreakdown) -> List[str]:
        """Generate warnings for low confidence areas."""
        warnings = []

        if breakdown.score_separation < 0.3:
            warnings.append(
                "Classification scores are very close - consider manual review"
            )

        if breakdown.evidence_completeness < 0.4:
            warnings.append(
                "Limited evidence available - classification may be unreliable"
            )

        if breakdown.source_consistency < 0.5:
            warnings.append(
                "Evidence sources disagree - conflicting signals detected"
            )

        if breakdown.selector_certainty < 0.4:
            warnings.append(
                "Selector status unclear - could not verify in codebase"
            )

        if breakdown.final_confidence < 0.5:
            warnings.append(
                "Overall confidence is low - recommend human verification"
            )

        return warnings

    def quick_confidence(
        self,
        score_separation: float,
        has_full_evidence: bool = True
    ) -> float:
        """
        Quick confidence calculation for simple cases.

        Use this when you don't need the full breakdown.
        """
        base = 0.5 + (0.4 * score_separation)

        if not has_full_evidence:
            base *= 0.85

        return max(0.3, min(0.95, base))


def calculate_confidence(
    classification_scores: Dict[str, float],
    has_stack_trace: bool = False,
    has_environment_status: bool = False,
    has_repository_analysis: bool = False,
    selector_found: Optional[bool] = None,
) -> ConfidenceBreakdown:
    """Convenience function for confidence calculation."""
    calculator = ConfidenceCalculator()

    evidence = EvidenceCompleteness(
        has_stack_trace=has_stack_trace,
        has_parsed_frames=has_stack_trace,
        has_environment_status=has_environment_status,
        has_repository_analysis=has_repository_analysis,
        has_selector_lookup=selector_found is not None,
    )

    consistency = SourceConsistency()

    return calculator.calculate(
        classification_scores=classification_scores,
        evidence_completeness=evidence,
        source_consistency=consistency,
        selector_found=selector_found,
    )
