#!/usr/bin/env python3
"""
Evidence Package Builder Service

Builds structured evidence bundles for each failed test.
Combines data from multiple sources (Jenkins, environment, repository)
into a comprehensive package that includes pre-calculated classification scores.

This is the central integration point for all evidence sources.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .stack_trace_parser import StackTraceParser, ParsedStackTrace, StackFrame
from .classification_decision_matrix import (
    ClassificationDecisionMatrix,
    ClassificationResult,
    FailureType,
)
from .confidence_calculator import (
    ConfidenceCalculator,
    EvidenceCompleteness,
    SourceConsistency,
    ConfidenceBreakdown,
)
from .cross_reference_validator import (
    CrossReferenceValidator,
    CrossValidationReport,
)


@dataclass
class SelectorEvidence:
    """Evidence about a specific selector."""
    selector: str
    found_in_codebase: bool
    file_paths: List[str] = field(default_factory=list)
    last_modified_date: Optional[str] = None
    last_commit_sha: Optional[str] = None
    last_commit_message: Optional[str] = None
    days_since_modified: Optional[int] = None
    recently_changed: bool = False  # Changed in last 30 days

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "selector": self.selector,
            "found_in_codebase": self.found_in_codebase,
            "file_paths": self.file_paths,
            "last_modified_date": self.last_modified_date,
            "last_commit_sha": self.last_commit_sha,
            "last_commit_message": self.last_commit_message,
            "days_since_modified": self.days_since_modified,
            "recently_changed": self.recently_changed,
        }


@dataclass
class EnvironmentEvidence:
    """Evidence from environment validation."""
    cluster_healthy: bool
    cluster_accessible: bool
    api_accessible: bool
    target_cluster_used: bool = False
    cluster_url: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    pod_status: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cluster_healthy": self.cluster_healthy,
            "cluster_accessible": self.cluster_accessible,
            "api_accessible": self.api_accessible,
            "target_cluster_used": self.target_cluster_used,
            "cluster_url": self.cluster_url,
            "validation_errors": self.validation_errors,
            "pod_status": self.pod_status,
        }


@dataclass
class ConsoleEvidence:
    """Evidence from console log analysis."""
    has_500_errors: bool = False
    has_network_errors: bool = False
    has_api_errors: bool = False
    has_timeout_errors: bool = False
    has_connection_refused: bool = False
    error_snippets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "has_500_errors": self.has_500_errors,
            "has_network_errors": self.has_network_errors,
            "has_api_errors": self.has_api_errors,
            "has_timeout_errors": self.has_timeout_errors,
            "has_connection_refused": self.has_connection_refused,
            "error_snippets": self.error_snippets,
        }


@dataclass
class RepositoryEvidence:
    """Evidence from repository analysis."""
    repository_cloned: bool
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    test_file_exists: bool = False
    test_file_content: Optional[str] = None  # ±20 lines around failure
    imports_resolved: bool = False
    import_chain: List[str] = field(default_factory=list)
    selector_evidence: Optional[SelectorEvidence] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "repository_cloned": self.repository_cloned,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "test_file_exists": self.test_file_exists,
            "test_file_content": self.test_file_content,
            "imports_resolved": self.imports_resolved,
            "import_chain": self.import_chain,
        }
        if self.selector_evidence:
            result["selector_evidence"] = self.selector_evidence.to_dict()
        return result


@dataclass
class FailureEvidence:
    """Core failure evidence from test report."""
    test_name: str
    error_message: str
    error_type: str
    failure_category: str  # timeout, element_not_found, assertion, etc.
    stack_trace: Optional[ParsedStackTrace] = None
    root_cause_file: Optional[str] = None
    root_cause_line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "test_name": self.test_name,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "failure_category": self.failure_category,
            "root_cause_file": self.root_cause_file,
            "root_cause_line": self.root_cause_line,
        }
        if self.stack_trace:
            result["stack_frames"] = [
                {
                    "file": f.file_path,
                    "line": f.line_number,
                    "function": f.function_name,
                    "is_test_file": f.is_test_file,
                    "is_framework_file": f.is_framework_file,
                }
                for f in self.stack_trace.frames[:10]  # Top 10 frames
            ]
        return result


@dataclass
class TestFailureEvidencePackage:
    """Complete evidence package for a single test failure."""
    test_name: str
    failure_evidence: FailureEvidence
    repository_evidence: RepositoryEvidence
    environment_evidence: EnvironmentEvidence
    console_evidence: ConsoleEvidence

    # Pre-calculated classification
    classification_result: ClassificationResult
    confidence_breakdown: ConfidenceBreakdown
    validation_report: CrossValidationReport

    # Final outputs
    final_classification: str
    final_confidence: float
    reasoning: str
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "test_name": self.test_name,
            "failure_evidence": self.failure_evidence.to_dict(),
            "repository_evidence": self.repository_evidence.to_dict(),
            "environment_evidence": self.environment_evidence.to_dict(),
            "console_evidence": self.console_evidence.to_dict(),
            "pre_calculated_scores": {
                "product_bug_score": round(self.classification_result.scores.product_bug, 3),
                "automation_bug_score": round(self.classification_result.scores.automation_bug, 3),
                "infrastructure_score": round(self.classification_result.scores.infrastructure, 3),
            },
            "classification_result": self.classification_result.to_dict(),
            "confidence_breakdown": self.confidence_breakdown.to_dict(),
            "validation_report": self.validation_report.to_dict(),
            "final_classification": self.final_classification,
            "final_confidence": round(self.final_confidence, 3),
            "reasoning": self.reasoning,
            "warnings": self.warnings,
        }


@dataclass
class EvidencePackage:
    """Complete evidence package for all test failures in a build."""
    jenkins_url: str
    build_number: int
    build_result: str
    branch: Optional[str]
    timestamp: str
    test_failures: List[TestFailureEvidencePackage] = field(default_factory=list)

    # Summary statistics
    total_failures: int = 0
    by_classification: Dict[str, int] = field(default_factory=dict)
    overall_classification: Optional[str] = None
    overall_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": {
                "jenkins_url": self.jenkins_url,
                "build_number": self.build_number,
                "build_result": self.build_result,
                "branch": self.branch,
                "timestamp": self.timestamp,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            },
            "test_failures": [tf.to_dict() for tf in self.test_failures],
            "summary": {
                "total_failures": self.total_failures,
                "by_classification": self.by_classification,
                "overall_classification": self.overall_classification,
                "overall_confidence": round(self.overall_confidence, 3),
            },
        }


class EvidencePackageBuilder:
    """
    Builds comprehensive evidence packages for failed tests.

    Integrates:
    - Stack trace parsing
    - Repository analysis
    - Environment validation
    - Console log analysis
    - Classification decision matrix
    - Confidence calculation
    - Cross-reference validation
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.stack_parser = StackTraceParser()
        self.decision_matrix = ClassificationDecisionMatrix()
        self.confidence_calculator = ConfidenceCalculator()
        self.validator = CrossReferenceValidator()

    def build_for_test(
        self,
        test_name: str,
        error_message: str,
        stack_trace: str,
        environment_data: Dict[str, Any],
        repository_data: Dict[str, Any],
        console_data: Dict[str, Any],
    ) -> TestFailureEvidencePackage:
        """
        Build complete evidence package for a single failed test.

        Args:
            test_name: Name of the failed test
            error_message: Error message from the failure
            stack_trace: Raw stack trace string
            environment_data: Environment validation data
            repository_data: Repository analysis data
            console_data: Console log analysis data

        Returns:
            Complete TestFailureEvidencePackage
        """
        # Step 1: Parse stack trace
        parsed_stack = self.stack_parser.parse(stack_trace)

        # Step 2: Extract failure category
        failure_category = self._determine_failure_category(
            error_message, parsed_stack.error_type
        )

        # Step 3: Build failure evidence
        failure_evidence = FailureEvidence(
            test_name=test_name,
            error_message=error_message[:500] if error_message else "",
            error_type=parsed_stack.error_type,
            failure_category=failure_category,
            stack_trace=parsed_stack,
            root_cause_file=parsed_stack.root_cause_frame.file_path if parsed_stack.root_cause_frame else None,
            root_cause_line=parsed_stack.root_cause_frame.line_number if parsed_stack.root_cause_frame else None,
        )

        # Step 4: Build environment evidence
        environment_evidence = self._build_environment_evidence(environment_data)

        # Step 5: Build repository evidence
        failing_selector = self.stack_parser.extract_failing_selector(error_message)
        repository_evidence = self._build_repository_evidence(
            repository_data, parsed_stack.root_cause_frame, failing_selector
        )

        # Step 6: Build console evidence
        console_evidence = self._build_console_evidence(console_data)

        # Step 7: Apply decision matrix for initial classification
        selector_found = repository_evidence.selector_evidence.found_in_codebase if repository_evidence.selector_evidence else None
        classification_result = self.decision_matrix.classify(
            failure_type=failure_category,
            env_healthy=environment_evidence.cluster_healthy,
            selector_found=selector_found if selector_found is not None else True,
            additional_factors=self._get_additional_factors(
                console_evidence, repository_evidence
            ),
        )

        # Step 8: Calculate confidence
        evidence_completeness = self._build_evidence_completeness(
            parsed_stack, environment_evidence, repository_evidence, console_evidence
        )
        source_consistency = self._build_source_consistency(
            failure_category, environment_evidence, console_evidence, repository_evidence
        )

        confidence_breakdown = self.confidence_calculator.calculate(
            classification_scores={
                "product_bug": classification_result.scores.product_bug,
                "automation_bug": classification_result.scores.automation_bug,
                "infrastructure": classification_result.scores.infrastructure,
            },
            evidence_completeness=evidence_completeness,
            source_consistency=source_consistency,
            selector_found=selector_found,
            selector_recently_changed=repository_evidence.selector_evidence.recently_changed if repository_evidence.selector_evidence else None,
        )

        # Step 9: Cross-validate classification
        validation_report = self.validator.validate(
            classification=classification_result.classification.value,
            confidence=confidence_breakdown.final_confidence,
            failure_type=failure_category,
            env_healthy=environment_evidence.cluster_healthy,
            selector_found=selector_found,
            selector_recently_changed=repository_evidence.selector_evidence.recently_changed if repository_evidence.selector_evidence else None,
            console_has_500_errors=console_evidence.has_500_errors,
            console_has_network_errors=console_evidence.has_network_errors,
            console_has_api_errors=console_evidence.has_api_errors,
            cluster_accessible=environment_evidence.cluster_accessible,
        )

        # Step 10: Determine final classification and confidence
        final_classification = validation_report.final_classification
        final_confidence = validation_report.final_confidence

        # Collect warnings
        warnings = confidence_breakdown.warnings.copy()
        if validation_report.needs_review:
            warnings.append("Cross-validation flagged for review")

        # Build reasoning
        reasoning = self._build_reasoning(
            classification_result, validation_report, failure_category
        )

        return TestFailureEvidencePackage(
            test_name=test_name,
            failure_evidence=failure_evidence,
            repository_evidence=repository_evidence,
            environment_evidence=environment_evidence,
            console_evidence=console_evidence,
            classification_result=classification_result,
            confidence_breakdown=confidence_breakdown,
            validation_report=validation_report,
            final_classification=final_classification,
            final_confidence=final_confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def build_package(
        self,
        jenkins_url: str,
        build_info: Dict[str, Any],
        failed_tests: List[Dict[str, Any]],
        environment_data: Dict[str, Any],
        repository_data: Dict[str, Any],
        console_data: Dict[str, Any],
    ) -> EvidencePackage:
        """
        Build complete evidence package for all failed tests.

        Args:
            jenkins_url: Jenkins build URL
            build_info: Jenkins build information
            failed_tests: List of failed test dictionaries
            environment_data: Environment validation data
            repository_data: Repository analysis data
            console_data: Console log analysis data

        Returns:
            Complete EvidencePackage for the build
        """
        package = EvidencePackage(
            jenkins_url=jenkins_url,
            build_number=build_info.get("build_number", 0),
            build_result=build_info.get("result", "UNKNOWN"),
            branch=build_info.get("branch"),
            timestamp=build_info.get("timestamp", datetime.utcnow().isoformat()),
        )

        classification_counts: Dict[str, int] = {}

        for test in failed_tests:
            test_package = self.build_for_test(
                test_name=test.get("test_name", "Unknown"),
                error_message=test.get("error_message", ""),
                stack_trace=test.get("stack_trace", ""),
                environment_data=environment_data,
                repository_data=repository_data,
                console_data=console_data,
            )
            package.test_failures.append(test_package)

            # Count classifications
            cls = test_package.final_classification
            classification_counts[cls] = classification_counts.get(cls, 0) + 1

        # Summary statistics
        package.total_failures = len(package.test_failures)
        package.by_classification = classification_counts

        if classification_counts:
            package.overall_classification = max(
                classification_counts, key=classification_counts.get
            )
            # Average confidence for the dominant classification
            dominant_packages = [
                p for p in package.test_failures
                if p.final_classification == package.overall_classification
            ]
            if dominant_packages:
                package.overall_confidence = sum(
                    p.final_confidence for p in dominant_packages
                ) / len(dominant_packages)

        return package

    def _determine_failure_category(
        self, error_message: str, error_type: str
    ) -> str:
        """Determine the failure category from error message and type."""
        error_lower = (error_message or "").lower()
        type_lower = (error_type or "").lower()

        # Check patterns - ORDER MATTERS (most specific first)
        # Element not found is often wrapped in timeout messages in Cypress
        # "Timed out retrying: Expected to find element" is element_not_found, not timeout
        if "element" in error_lower and ("not found" in error_lower or "never found" in error_lower):
            return "element_not_found"
        # Server errors - check before generic patterns
        if "500" in error_lower or "internal server error" in error_lower:
            return "server_error"
        if "econnrefused" in error_lower or "connection refused" in error_lower:
            return "network"  # Explicit connection refused
        # Generic timeout (not element-related)
        if "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        if "assert" in type_lower or "expected" in error_lower:
            return "assertion"
        if "401" in error_lower or "403" in error_lower or "auth" in error_lower:
            return "auth_error"
        if "404" in error_lower or "not found" in error_lower:
            return "not_found"
        if "network" in error_lower or "connection" in error_lower:
            return "network"

        return "unknown"

    def _build_environment_evidence(
        self, env_data: Dict[str, Any]
    ) -> EnvironmentEvidence:
        """Build environment evidence from raw data."""
        return EnvironmentEvidence(
            cluster_healthy=env_data.get("healthy", True),
            cluster_accessible=env_data.get("accessible", True),
            api_accessible=env_data.get("api_accessible", True),
            target_cluster_used=env_data.get("target_cluster_used", False),
            cluster_url=env_data.get("cluster_url"),
            validation_errors=env_data.get("errors", []),
            pod_status=env_data.get("pod_status"),
        )

    def _build_repository_evidence(
        self,
        repo_data: Dict[str, Any],
        root_cause_frame: Optional[StackFrame],
        failing_selector: Optional[str],
    ) -> RepositoryEvidence:
        """Build repository evidence from raw data."""
        evidence = RepositoryEvidence(
            repository_cloned=repo_data.get("repository_cloned", False),
            branch=repo_data.get("branch"),
            commit_sha=repo_data.get("commit_sha"),
        )

        # Check if test file exists
        if root_cause_frame:
            evidence.test_file_exists = root_cause_frame.file_path in repo_data.get("test_files", [])
            evidence.test_file_content = repo_data.get("file_contents", {}).get(
                root_cause_frame.file_path
            )

        # Build selector evidence
        if failing_selector:
            selector_lookup = repo_data.get("selector_lookup", {})
            found = failing_selector in selector_lookup
            evidence.selector_evidence = SelectorEvidence(
                selector=failing_selector,
                found_in_codebase=found,
                file_paths=selector_lookup.get(failing_selector, []),
            )

            # Check git history for selector
            selector_history = repo_data.get("selector_history", {}).get(failing_selector, {})
            if selector_history:
                evidence.selector_evidence.last_modified_date = selector_history.get("date")
                evidence.selector_evidence.last_commit_sha = selector_history.get("sha")
                evidence.selector_evidence.last_commit_message = selector_history.get("message")
                evidence.selector_evidence.days_since_modified = selector_history.get("days_ago")
                evidence.selector_evidence.recently_changed = (
                    selector_history.get("days_ago", 999) <= 30
                )

        return evidence

    def _build_console_evidence(
        self, console_data: Dict[str, Any]
    ) -> ConsoleEvidence:
        """Build console evidence from raw data."""
        key_errors = console_data.get("key_errors", [])
        error_text = " ".join(key_errors).lower()

        return ConsoleEvidence(
            has_500_errors="500" in error_text or "internal server error" in error_text,
            has_network_errors="network" in error_text or "econnrefused" in error_text,
            has_api_errors="api" in error_text and "error" in error_text,
            has_timeout_errors="timeout" in error_text,
            has_connection_refused="connection refused" in error_text or "econnrefused" in error_text,
            error_snippets=key_errors[:10],  # First 10 errors
        )

    def _get_additional_factors(
        self,
        console_evidence: ConsoleEvidence,
        repository_evidence: RepositoryEvidence,
    ) -> Dict[str, bool]:
        """Build additional factors for decision matrix."""
        factors = {}

        if console_evidence.has_500_errors:
            factors["console_500_error"] = True
        if console_evidence.has_api_errors:
            factors["console_api_error"] = True
        if console_evidence.has_connection_refused:
            factors["console_connection_refused"] = True

        if repository_evidence.selector_evidence:
            if repository_evidence.selector_evidence.recently_changed:
                factors["selector_recently_changed"] = True
            if not repository_evidence.selector_evidence.found_in_codebase:
                factors["selector_never_existed"] = True

        return factors

    def _build_evidence_completeness(
        self,
        parsed_stack: ParsedStackTrace,
        env_evidence: EnvironmentEvidence,
        repo_evidence: RepositoryEvidence,
        console_evidence: ConsoleEvidence,
    ) -> EvidenceCompleteness:
        """Build evidence completeness assessment."""
        return EvidenceCompleteness(
            has_stack_trace=bool(parsed_stack.raw_trace),
            has_parsed_frames=len(parsed_stack.frames) > 0,
            has_root_cause_file=parsed_stack.root_cause_frame is not None,
            has_environment_status=True,  # Always have some env data
            has_repository_analysis=repo_evidence.repository_cloned,
            has_selector_lookup=repo_evidence.selector_evidence is not None,
            has_git_history=repo_evidence.selector_evidence.last_commit_sha is not None if repo_evidence.selector_evidence else False,
            has_console_errors=len(console_evidence.error_snippets) > 0,
            has_test_file_content=repo_evidence.test_file_content is not None,
        )

    def _build_source_consistency(
        self,
        failure_category: str,
        env_evidence: EnvironmentEvidence,
        console_evidence: ConsoleEvidence,
        repo_evidence: RepositoryEvidence,
    ) -> SourceConsistency:
        """Build source consistency assessment."""
        consistency = SourceConsistency()

        # Jenkins/test report suggestion based on failure category
        if failure_category in ["server_error", "not_found"]:
            consistency.jenkins_suggests = "PRODUCT_BUG"
        elif failure_category in ["element_not_found", "timeout"]:
            consistency.jenkins_suggests = "AUTOMATION_BUG"
        elif failure_category == "network":
            consistency.jenkins_suggests = "INFRASTRUCTURE"

        # Environment suggestion
        if not env_evidence.cluster_healthy or not env_evidence.cluster_accessible:
            consistency.environment_suggests = "INFRASTRUCTURE"
        else:
            consistency.environment_suggests = None  # Healthy env doesn't strongly suggest

        # Console suggestion
        if console_evidence.has_500_errors:
            consistency.console_suggests = "PRODUCT_BUG"
        elif console_evidence.has_network_errors or console_evidence.has_connection_refused:
            consistency.console_suggests = "INFRASTRUCTURE"

        # Repository suggestion
        # NOTE: Missing selector no longer automatically suggests PRODUCT_BUG
        # because TimelineComparisonService provides more accurate classification
        # by comparing git modification dates between automation and console repos.
        # Only recent selector changes strongly suggest AUTOMATION_BUG.
        if repo_evidence.selector_evidence:
            if repo_evidence.selector_evidence.recently_changed:
                consistency.repository_suggests = "AUTOMATION_BUG"
            # Missing selector doesn't suggest either way - timeline comparison
            # determines if automation fell behind or product broke something

        return consistency

    def _build_reasoning(
        self,
        classification_result: ClassificationResult,
        validation_report: CrossValidationReport,
        failure_category: str,
    ) -> str:
        """Build human-readable reasoning."""
        parts = []

        # Base reasoning from decision matrix
        parts.append(classification_result.reasoning)

        # Add validation corrections
        if validation_report.was_corrected:
            parts.append(
                f"Classification was corrected based on cross-validation: {validation_report.summary}"
            )

        # Add validation warnings
        if validation_report.needs_review:
            parts.append("Manual review recommended due to conflicting evidence")

        return " ".join(parts)


def build_evidence_package(
    jenkins_url: str,
    build_info: Dict[str, Any],
    failed_tests: List[Dict[str, Any]],
    environment_data: Dict[str, Any],
    repository_data: Dict[str, Any],
    console_data: Dict[str, Any],
) -> EvidencePackage:
    """Convenience function to build evidence package."""
    builder = EvidencePackageBuilder()
    return builder.build_package(
        jenkins_url=jenkins_url,
        build_info=build_info,
        failed_tests=failed_tests,
        environment_data=environment_data,
        repository_data=repository_data,
        console_data=console_data,
    )
