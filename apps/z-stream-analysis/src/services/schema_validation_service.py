#!/usr/bin/env python3
"""
Schema Validation Service
Validates analysis-results.json against expected schema with helpful error messages.

This service provides custom validation without external dependencies.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class ValidationSeverity(Enum):
    """Severity level of validation issues."""
    ERROR = "error"       # Required field missing or invalid type
    WARNING = "warning"   # Recommended field missing
    INFO = "info"         # Optional enhancement available


@dataclass
class ValidationIssue:
    """Single validation issue."""
    path: str                         # JSON path to the issue
    message: str                      # Human-readable error message
    severity: ValidationSeverity
    suggestion: Optional[str] = None  # How to fix the issue


@dataclass
class ValidationResult:
    """Complete validation result."""
    is_valid: bool            # True if no ERROR-level issues
    issues: List[ValidationIssue]
    warnings_count: int
    errors_count: int
    validated_fields: List[str]
    missing_optional: List[str]


class SchemaValidationService:
    """
    Schema Validation Service for analysis-results.json.

    Provides validation with helpful, actionable error messages.
    Works without external dependencies (no jsonschema library required).
    """

    # Valid classification values
    VALID_CLASSIFICATIONS = [
        'PRODUCT_BUG', 'AUTOMATION_BUG', 'INFRASTRUCTURE', 'MIXED',
        'UNKNOWN', 'NO_BUG', 'FLAKY', 'REQUIRES_INVESTIGATION'
    ]

    VALID_PRIORITIES = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

    VALID_OWNERS = [
        'Product Team', 'Automation Team', 'Platform Team',
        'Infrastructure Team', 'Platform/Infrastructure Team',
        'Multiple Teams', 'Product Team + Automation Team'
    ]

    def __init__(self, schema_path: Optional[Path] = None):
        """
        Initialize the validation service.

        Args:
            schema_path: Path to JSON Schema file (optional, uses built-in rules)
        """
        self.logger = logging.getLogger(__name__)
        self.schema = self._load_schema(schema_path)

    def _load_schema(self, schema_path: Optional[Path]) -> Optional[Dict[str, Any]]:
        """Load JSON Schema from file if provided."""
        if schema_path and schema_path.exists():
            with open(schema_path) as f:
                return json.load(f)
        return None

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate analysis-results.json data.

        Args:
            data: Parsed JSON data to validate

        Returns:
            ValidationResult with all issues found
        """
        issues = []
        validated_fields = []
        missing_optional = []

        # Required fields validation
        issues.extend(self._validate_required_fields(data, validated_fields))

        # per_test_analysis validation
        if 'per_test_analysis' in data and isinstance(data['per_test_analysis'], list):
            issues.extend(self._validate_per_test_analysis(
                data['per_test_analysis'], validated_fields
            ))

        # summary validation
        if 'summary' in data and isinstance(data['summary'], dict):
            issues.extend(self._validate_summary(data['summary'], validated_fields))

        # Optional but recommended fields
        issues.extend(self._validate_optional_fields(data, missing_optional))

        # Calculate counts
        errors_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warnings_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)

        return ValidationResult(
            is_valid=(errors_count == 0),
            issues=issues,
            warnings_count=warnings_count,
            errors_count=errors_count,
            validated_fields=validated_fields,
            missing_optional=missing_optional
        )

    def _validate_required_fields(self, data: Dict[str, Any],
                                   validated: List[str]) -> List[ValidationIssue]:
        """Validate required top-level fields."""
        issues = []

        # per_test_analysis is required
        if 'per_test_analysis' not in data:
            issues.append(ValidationIssue(
                path='per_test_analysis',
                message="Missing required field 'per_test_analysis'",
                severity=ValidationSeverity.ERROR,
                suggestion="Add 'per_test_analysis' array with analysis for each failed test"
            ))
        elif not isinstance(data['per_test_analysis'], list):
            issues.append(ValidationIssue(
                path='per_test_analysis',
                message="'per_test_analysis' must be an array",
                severity=ValidationSeverity.ERROR,
                suggestion="Change 'per_test_analysis' to an array of test analysis objects"
            ))
        else:
            validated.append('per_test_analysis')

        # summary is required
        if 'summary' not in data:
            issues.append(ValidationIssue(
                path='summary',
                message="Missing required field 'summary'",
                severity=ValidationSeverity.ERROR,
                suggestion="Add 'summary' object with overall_classification and by_classification"
            ))
        elif not isinstance(data['summary'], dict):
            issues.append(ValidationIssue(
                path='summary',
                message="'summary' must be an object",
                severity=ValidationSeverity.ERROR,
                suggestion="Change 'summary' to an object with classification breakdown"
            ))
        else:
            validated.append('summary')

        return issues

    def _validate_per_test_analysis(self, tests: List[Any],
                                     validated: List[str]) -> List[ValidationIssue]:
        """Validate each item in per_test_analysis array."""
        issues = []

        for i, test in enumerate(tests):
            path_prefix = f'per_test_analysis[{i}]'

            if not isinstance(test, dict):
                issues.append(ValidationIssue(
                    path=path_prefix,
                    message=f"Test analysis at index {i} must be an object",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Each item in per_test_analysis must be a JSON object"
                ))
                continue

            # Required: test_name
            if 'test_name' not in test:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.test_name',
                    message="Missing required field 'test_name'",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Add the test name from test_report.failed_tests"
                ))
            elif not test['test_name']:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.test_name',
                    message="'test_name' cannot be empty",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Provide the full test name"
                ))
            else:
                validated.append(f'{path_prefix}.test_name')

            # Required: classification
            if 'classification' not in test:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.classification',
                    message="Missing required field 'classification'",
                    severity=ValidationSeverity.ERROR,
                    suggestion=f"Add classification: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or MIXED"
                ))
            elif test['classification'] not in self.VALID_CLASSIFICATIONS:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.classification',
                    message=f"Invalid classification: '{test['classification']}'",
                    severity=ValidationSeverity.ERROR,
                    suggestion=f"Use: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or MIXED"
                ))
            else:
                validated.append(f'{path_prefix}.classification')

            # Required: confidence
            if 'confidence' not in test:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.confidence',
                    message="Missing required field 'confidence'",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Add confidence score between 0.0 and 1.0"
                ))
            elif not isinstance(test['confidence'], (int, float)):
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.confidence',
                    message="'confidence' must be a number",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Provide confidence as a decimal (e.g., 0.85)"
                ))
            elif not 0 <= test['confidence'] <= 1:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.confidence',
                    message=f"Confidence {test['confidence']} out of range [0.0, 1.0]",
                    severity=ValidationSeverity.ERROR,
                    suggestion="Confidence must be between 0.0 and 1.0"
                ))
            else:
                validated.append(f'{path_prefix}.confidence')

            # Recommended: reasoning
            if 'reasoning' not in test:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.reasoning',
                    message="Missing recommended field 'reasoning'",
                    severity=ValidationSeverity.WARNING,
                    suggestion="Add reasoning explaining why this classification was chosen"
                ))

            # Recommended: recommended_fix
            if 'recommended_fix' not in test:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.recommended_fix',
                    message="Missing recommended field 'recommended_fix'",
                    severity=ValidationSeverity.WARNING,
                    suggestion="Add specific action to resolve this failure"
                ))

            # Validate owner if present
            if 'owner' in test and test['owner'] not in self.VALID_OWNERS:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.owner',
                    message=f"Non-standard owner: '{test['owner']}'",
                    severity=ValidationSeverity.INFO,
                    suggestion=f"Consider using: Product Team, Automation Team, or Platform Team"
                ))

            # Validate priority if present
            if 'priority' in test and test['priority'] not in self.VALID_PRIORITIES:
                issues.append(ValidationIssue(
                    path=f'{path_prefix}.priority',
                    message=f"Invalid priority: '{test['priority']}'",
                    severity=ValidationSeverity.WARNING,
                    suggestion=f"Use: CRITICAL, HIGH, MEDIUM, or LOW"
                ))

        return issues

    def _validate_summary(self, summary: Dict[str, Any],
                          validated: List[str]) -> List[ValidationIssue]:
        """Validate the summary object."""
        issues = []

        # Required: by_classification
        if 'by_classification' not in summary:
            issues.append(ValidationIssue(
                path='summary.by_classification',
                message="Missing required field 'by_classification'",
                severity=ValidationSeverity.ERROR,
                suggestion="Add by_classification object with counts for each type"
            ))
        elif not isinstance(summary['by_classification'], dict):
            issues.append(ValidationIssue(
                path='summary.by_classification',
                message="'by_classification' must be an object",
                severity=ValidationSeverity.ERROR,
                suggestion='Provide as: {"PRODUCT_BUG": 0, "AUTOMATION_BUG": 0, ...}'
            ))
        else:
            validated.append('summary.by_classification')

            # Validate classification keys
            for key in summary['by_classification']:
                if key not in self.VALID_CLASSIFICATIONS:
                    issues.append(ValidationIssue(
                        path=f'summary.by_classification.{key}',
                        message=f"Unknown classification key: '{key}'",
                        severity=ValidationSeverity.WARNING,
                        suggestion="Use: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE"
                    ))

        # Recommended: overall_classification
        if 'overall_classification' not in summary:
            issues.append(ValidationIssue(
                path='summary.overall_classification',
                message="Missing recommended field 'overall_classification'",
                severity=ValidationSeverity.WARNING,
                suggestion="Add the dominant classification across all failures"
            ))
        elif summary['overall_classification'] not in self.VALID_CLASSIFICATIONS:
            issues.append(ValidationIssue(
                path='summary.overall_classification',
                message=f"Invalid overall_classification: '{summary['overall_classification']}'",
                severity=ValidationSeverity.WARNING,
                suggestion="Use: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, or MIXED"
            ))
        else:
            validated.append('summary.overall_classification')

        # Recommended: overall_confidence
        if 'overall_confidence' not in summary:
            issues.append(ValidationIssue(
                path='summary.overall_confidence',
                message="Missing recommended field 'overall_confidence'",
                severity=ValidationSeverity.WARNING,
                suggestion="Add overall confidence score (0.0 to 1.0)"
            ))
        elif 'overall_confidence' in summary:
            conf = summary['overall_confidence']
            if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
                issues.append(ValidationIssue(
                    path='summary.overall_confidence',
                    message=f"Invalid overall_confidence: {conf}",
                    severity=ValidationSeverity.WARNING,
                    suggestion="Provide as decimal between 0.0 and 1.0"
                ))
            else:
                validated.append('summary.overall_confidence')

        return issues

    def _validate_optional_fields(self, data: Dict[str, Any],
                                   missing: List[str]) -> List[ValidationIssue]:
        """Check for optional but valuable fields."""
        issues = []

        optional_fields = [
            ('analysis_metadata', 'Adds context about when/how analysis was performed'),
            ('environment_summary', 'Documents cluster health at time of failure'),
            ('patterns_detected', 'Highlights common issues across tests'),
            ('action_items', 'Provides prioritized fix actions')
        ]

        for field, description in optional_fields:
            if field not in data:
                missing.append(field)
                issues.append(ValidationIssue(
                    path=field,
                    message=f"Optional field '{field}' not present",
                    severity=ValidationSeverity.INFO,
                    suggestion=description
                ))

        return issues

    def format_issues(self, result: ValidationResult) -> str:
        """Format validation issues as human-readable text."""
        lines = []

        if result.is_valid:
            lines.append("VALIDATION PASSED")
            lines.append(f"  Validated fields: {len(result.validated_fields)}")
            if result.warnings_count > 0:
                lines.append(f"  Warnings: {result.warnings_count}")
        else:
            lines.append("VALIDATION FAILED")
            lines.append(f"  Errors: {result.errors_count}")
            lines.append(f"  Warnings: {result.warnings_count}")

        lines.append("")

        # Group by severity
        errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in result.issues if i.severity == ValidationSeverity.WARNING]
        info = [i for i in result.issues if i.severity == ValidationSeverity.INFO]

        if errors:
            lines.append("ERRORS (must fix):")
            for issue in errors:
                lines.append(f"  [{issue.path}] {issue.message}")
                if issue.suggestion:
                    lines.append(f"    -> {issue.suggestion}")

        if warnings:
            lines.append("\nWARNINGS (recommended):")
            for issue in warnings:
                lines.append(f"  [{issue.path}] {issue.message}")
                if issue.suggestion:
                    lines.append(f"    -> {issue.suggestion}")

        if info and not errors:  # Only show info if no errors
            lines.append("\nINFO (optional enhancements):")
            for issue in info[:3]:  # Limit to 3
                lines.append(f"  [{issue.path}] {issue.suggestion}")

        return '\n'.join(lines)

    def validate_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate a JSON file and return (is_valid, message).

        Convenience method for report.py integration.
        """
        try:
            with open(file_path) as f:
                data = json.load(f)

            result = self.validate(data)
            return result.is_valid, self.format_issues(result)

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except FileNotFoundError:
            return False, f"File not found: {file_path}"
        except Exception as e:
            return False, f"Validation error: {e}"

    def to_dict(self, result: ValidationResult) -> Dict[str, Any]:
        """Convert ValidationResult to dictionary for JSON serialization."""
        return {
            'is_valid': result.is_valid,
            'errors_count': result.errors_count,
            'warnings_count': result.warnings_count,
            'validated_fields': result.validated_fields,
            'missing_optional': result.missing_optional,
            'issues': [
                {
                    'path': issue.path,
                    'message': issue.message,
                    'severity': issue.severity.value,
                    'suggestion': issue.suggestion
                }
                for issue in result.issues
            ]
        }
