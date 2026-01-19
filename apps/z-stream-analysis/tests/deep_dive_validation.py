#!/usr/bin/env python3
"""
Comprehensive Deep Dive Validation
Tests every stage of the z-stream-analysis workflow with mock data.

This validates all the new services and integrations:
1. Stack Trace Parser
2. Classification Decision Matrix
3. Confidence Calculator
4. Cross-Reference Validator
5. Evidence Package Builder
6. Repository Analysis (git history, selector lookup)
7. Full Integration Flow

Run with: python -m tests.deep_dive_validation
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import asdict
import traceback

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DeepDiveValidator:
    """Comprehensive validator for all app components."""

    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "errors": []
        }
        self.total_tests = 0

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result."""
        self.total_tests += 1
        if passed:
            self.results["passed"].append({"test": test_name, "details": details})
            print(f"  ✓ {test_name}")
        else:
            self.results["failed"].append({"test": test_name, "details": details})
            print(f"  ✗ {test_name}: {details}")

    def log_error(self, test_name: str, error: Exception):
        """Log a test error."""
        self.total_tests += 1
        self.results["errors"].append({
            "test": test_name,
            "error": str(error),
            "traceback": traceback.format_exc()
        })
        print(f"  ✗ {test_name}: ERROR - {error}")

    def run_all(self):
        """Run all validation stages."""
        print("\n" + "=" * 70)
        print("Z-STREAM ANALYSIS - DEEP DIVE VALIDATION")
        print("=" * 70)

        stages = [
            ("Stage 1: Stack Trace Parser", self.validate_stack_trace_parser),
            ("Stage 2: Classification Decision Matrix", self.validate_classification_matrix),
            ("Stage 3: Confidence Calculator", self.validate_confidence_calculator),
            ("Stage 4: Cross-Reference Validator", self.validate_cross_reference_validator),
            ("Stage 5: Evidence Package Builder", self.validate_evidence_package_builder),
            ("Stage 6: Repository Analysis Integration", self.validate_repository_analysis),
            ("Stage 7: Full Integration Flow", self.validate_full_integration),
            ("Stage 8: Edge Cases & Error Handling", self.validate_edge_cases),
        ]

        for stage_name, stage_func in stages:
            print(f"\n{stage_name}")
            print("-" * 50)
            try:
                stage_func()
            except Exception as e:
                print(f"  STAGE FAILED: {e}")
                traceback.print_exc()

        self.print_summary()

    def print_summary(self):
        """Print final validation summary."""
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        passed = len(self.results["passed"])
        failed = len(self.results["failed"])
        errors = len(self.results["errors"])

        print(f"\nTotal tests: {self.total_tests}")
        print(f"Passed: {passed} ✓")
        print(f"Failed: {failed} ✗")
        print(f"Errors: {errors} ⚠")

        if failed > 0:
            print("\nFailed tests:")
            for f in self.results["failed"]:
                print(f"  - {f['test']}: {f['details']}")

        if errors > 0:
            print("\nErrors:")
            for e in self.results["errors"]:
                print(f"  - {e['test']}: {e['error']}")

        print("\n" + "=" * 70)
        if failed == 0 and errors == 0:
            print("ALL VALIDATIONS PASSED ✓")
        else:
            print(f"VALIDATION FAILED ({failed} failures, {errors} errors)")
        print("=" * 70 + "\n")

    # =========================================================================
    # Stage 1: Stack Trace Parser
    # =========================================================================
    def validate_stack_trace_parser(self):
        """Validate stack trace parser with realistic mock data."""
        from src.services.stack_trace_parser import StackTraceParser, parse_stack_trace

        parser = StackTraceParser()

        # Test Case 1: Webpack stack trace (Cypress)
        webpack_trace = """
AssertionError: Timed out retrying after 10000ms: Expected to find element: `#managedClusterSet-radio`, but never found it.

Because this error occurred during a `after all` hook we are skipping all of the remaining tests.

    at webpack://app/./cypress/views/clusters/managedCluster.js:181:11
    at Context.eval (webpack://app/./cypress/tests/managedCluster.spec.js:42:15)
    at runCallback (/app/node_modules/cypress/runner.js:100:10)
"""
        result = parser.parse(webpack_trace)
        self.log_result(
            "Parse webpack stack trace",
            result.total_frames >= 2 and result.error_type == "AssertionError",
            f"Frames: {result.total_frames}, Error: {result.error_type}"
        )

        self.log_result(
            "Extract root cause file",
            result.root_cause_frame is not None and "managedCluster.js" in result.root_cause_frame.file_path,
            f"Root cause: {result.root_cause_frame.file_path if result.root_cause_frame else 'None'}"
        )

        self.log_result(
            "Identify test file frame",
            result.test_file_frame is not None and ".spec.js" in result.test_file_frame.file_path,
            f"Test file: {result.test_file_frame.file_path if result.test_file_frame else 'None'}"
        )

        # Test Case 2: Extract selector from error
        selector = parser.extract_failing_selector(
            "Expected to find element: `#managedClusterSet-radio`, but never found it"
        )
        self.log_result(
            "Extract selector from error",
            selector == "#managedClusterSet-radio",
            f"Extracted: {selector}"
        )

        # Test Case 3: Different selector patterns
        test_cases = [
            ("cy.get('#my-button') failed", "#my-button"),
            ("Element not found: `.submit-button`", ".submit-button"),
            ("Expected to find element: `[data-test=submit-form]`", "[data-test=submit-form]"),
        ]
        for msg, expected in test_cases:
            sel = parser.extract_failing_selector(msg)
            self.log_result(
                f"Extract selector: {expected[:20]}...",
                sel == expected,
                f"Got: {sel}, Expected: {expected}"
            )

        # Test Case 4: Node.js stack trace
        nodejs_trace = """
Error: Connection refused
    at Context.eval (/Users/test/project/cypress/tests/api.spec.js:25:10)
    at async Context.eval (/Users/test/project/cypress/tests/api.spec.js:30:3)
"""
        result2 = parser.parse(nodejs_trace)
        self.log_result(
            "Parse Node.js stack trace",
            result2.total_frames >= 1 and result2.error_type == "Error",
            f"Frames: {result2.total_frames}"
        )

        # Test Case 5: Empty trace handling
        empty_result = parser.parse("")
        self.log_result(
            "Handle empty stack trace",
            empty_result.total_frames == 0 and empty_result.root_cause_frame is None,
            "Empty trace handled correctly"
        )

        # Test Case 6: Frame deduplication
        dup_trace = """
Error: Test
    at Context.eval (webpack://app/./cypress/tests/test.js:10:5)
    at Context.eval (webpack://app/./cypress/tests/test.js:10:5)
    at Context.eval (webpack://app/./cypress/tests/test.js:10:5)
    at Object.run (webpack://app/./cypress/views/other.js:20:10)
"""
        dup_result = parser.parse(dup_trace)
        self.log_result(
            "Deduplicate stack frames",
            dup_result.total_frames == 2,
            f"Frames after dedup: {dup_result.total_frames}"
        )

    # =========================================================================
    # Stage 2: Classification Decision Matrix
    # =========================================================================
    def validate_classification_matrix(self):
        """Validate classification decision matrix with all failure scenarios."""
        from src.services.classification_decision_matrix import (
            ClassificationDecisionMatrix,
            Classification,
            classify_failure
        )

        matrix = ClassificationDecisionMatrix()

        # Define test scenarios with expected outcomes
        scenarios = [
            # (failure_type, env_healthy, selector_found, expected_classification)
            ("server_error", True, True, Classification.PRODUCT_BUG),
            ("server_error", True, False, Classification.PRODUCT_BUG),
            ("server_error", False, True, Classification.PRODUCT_BUG),
            ("element_not_found", True, True, Classification.AUTOMATION_BUG),
            ("element_not_found", True, False, Classification.PRODUCT_BUG),
            ("element_not_found", False, True, Classification.INFRASTRUCTURE),
            ("timeout", True, True, Classification.AUTOMATION_BUG),
            ("timeout", False, True, Classification.INFRASTRUCTURE),
            ("network", False, True, Classification.INFRASTRUCTURE),
            ("assertion", True, True, Classification.PRODUCT_BUG),
            ("auth_error", True, True, Classification.AUTOMATION_BUG),
        ]

        for failure_type, env_healthy, selector_found, expected in scenarios:
            result = matrix.classify(failure_type, env_healthy, selector_found)
            passed = result.classification == expected
            self.log_result(
                f"Classify {failure_type} (env={env_healthy}, sel={selector_found})",
                passed,
                f"Got: {result.classification.value}, Expected: {expected.value}"
            )

        # Test additional factors
        result = matrix.classify(
            "timeout",
            env_healthy=True,
            selector_found=True,
            additional_factors={"console_500_error": True}
        )
        self.log_result(
            "Additional factors boost product score",
            result.scores.product_bug > 0.25,
            f"Product score with 500 error: {result.scores.product_bug:.2f}"
        )

        # Test selector recently changed
        result = matrix.classify(
            "element_not_found",
            env_healthy=True,
            selector_found=True,
            additional_factors={"selector_recently_changed": True}
        )
        self.log_result(
            "Selector change boosts automation score",
            result.scores.automation_bug >= 0.5,
            f"Automation score: {result.scores.automation_bug:.2f}"
        )

        # Test confidence calculation
        high_conf = matrix.classify("server_error", True, True)
        low_conf = matrix.classify("unknown", True, True)
        self.log_result(
            "Confidence higher for clear cases",
            high_conf.confidence > low_conf.confidence,
            f"Server error: {high_conf.confidence:.2f}, Unknown: {low_conf.confidence:.2f}"
        )

        # Test reasoning generation
        result = matrix.classify("server_error", True, True)
        self.log_result(
            "Reasoning generated",
            len(result.reasoning) > 20 and "500" in result.reasoning.lower() or "backend" in result.reasoning.lower(),
            f"Reasoning: {result.reasoning[:50]}..."
        )

    # =========================================================================
    # Stage 3: Confidence Calculator
    # =========================================================================
    def validate_confidence_calculator(self):
        """Validate multi-factor confidence calculation."""
        from src.services.confidence_calculator import (
            ConfidenceCalculator,
            EvidenceCompleteness,
            SourceConsistency,
            calculate_confidence
        )

        calc = ConfidenceCalculator()

        # Test 1: Full evidence = high confidence
        full_evidence = EvidenceCompleteness(
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
        self.log_result(
            "Full evidence completeness = 1.0",
            full_evidence.completeness_score == 1.0,
            f"Score: {full_evidence.completeness_score}"
        )

        # Test 2: Source consistency
        agree_consistency = SourceConsistency(
            jenkins_suggests="PRODUCT_BUG",
            environment_suggests="PRODUCT_BUG",
            console_suggests="PRODUCT_BUG",
        )
        self.log_result(
            "Sources agree = high consistency",
            agree_consistency.consistency_score == 1.0,
            f"Score: {agree_consistency.consistency_score}"
        )

        disagree_consistency = SourceConsistency(
            jenkins_suggests="PRODUCT_BUG",
            environment_suggests="INFRASTRUCTURE",
            console_suggests="AUTOMATION_BUG",
        )
        self.log_result(
            "Sources disagree = low consistency",
            disagree_consistency.consistency_score < 0.5,
            f"Score: {disagree_consistency.consistency_score}"
        )

        # Test 3: Full calculation
        result = calc.calculate(
            classification_scores={
                "product_bug": 0.85,
                "automation_bug": 0.10,
                "infrastructure": 0.05,
            },
            evidence_completeness=full_evidence,
            source_consistency=agree_consistency,
            selector_found=True,
            selector_recently_changed=False,
        )
        self.log_result(
            "High evidence + agreement = HIGH confidence",
            result.confidence_level == "HIGH",
            f"Level: {result.confidence_level}, Score: {result.final_confidence:.2f}"
        )

        # Test 4: Low evidence scenario
        low_evidence = EvidenceCompleteness(has_stack_trace=True)
        low_result = calc.calculate(
            classification_scores={
                "product_bug": 0.4,
                "automation_bug": 0.35,
                "infrastructure": 0.25,
            },
            evidence_completeness=low_evidence,
            source_consistency=disagree_consistency,
        )
        self.log_result(
            "Low evidence + disagreement = warnings",
            len(low_result.warnings) >= 2,
            f"Warnings: {len(low_result.warnings)}"
        )

        # Test 5: Selector certainty
        known_selector = calc.calculate(
            classification_scores={"product_bug": 0.5, "automation_bug": 0.3, "infrastructure": 0.2},
            evidence_completeness=EvidenceCompleteness(),
            source_consistency=SourceConsistency(),
            selector_found=True,
            selector_recently_changed=True,
        )
        unknown_selector = calc.calculate(
            classification_scores={"product_bug": 0.5, "automation_bug": 0.3, "infrastructure": 0.2},
            evidence_completeness=EvidenceCompleteness(),
            source_consistency=SourceConsistency(),
            selector_found=None,
        )
        self.log_result(
            "Known selector = higher certainty",
            known_selector.selector_certainty > unknown_selector.selector_certainty,
            f"Known: {known_selector.selector_certainty:.2f}, Unknown: {unknown_selector.selector_certainty:.2f}"
        )

    # =========================================================================
    # Stage 4: Cross-Reference Validator
    # =========================================================================
    def validate_cross_reference_validator(self):
        """Validate cross-reference validation rules."""
        from src.services.cross_reference_validator import (
            CrossReferenceValidator,
            validate_classification
        )

        validator = CrossReferenceValidator()

        # Test 1: 500 error overrides AUTOMATION_BUG → PRODUCT_BUG
        report = validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=True,
            console_has_500_errors=True,
        )
        self.log_result(
            "500 errors override AUTOMATION → PRODUCT",
            report.was_corrected and report.final_classification == "PRODUCT_BUG",
            f"Final: {report.final_classification}, Corrected: {report.was_corrected}"
        )

        # Test 2: Unhealthy cluster overrides AUTOMATION_BUG → INFRASTRUCTURE
        report = validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=False,
            cluster_accessible=False,
        )
        self.log_result(
            "Unhealthy cluster overrides AUTOMATION → INFRA",
            report.was_corrected and report.final_classification == "INFRASTRUCTURE",
            f"Final: {report.final_classification}"
        )

        # Test 3: Selector change flags PRODUCT_BUG for review
        report = validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.7,
            failure_type="element_not_found",
            env_healthy=True,
            selector_recently_changed=True,
        )
        self.log_result(
            "Selector change flags PRODUCT_BUG for review",
            report.needs_review,
            f"Needs review: {report.needs_review}"
        )

        # Test 4: INFRASTRUCTURE with healthy env flagged
        report = validator.validate(
            classification="INFRASTRUCTURE",
            confidence=0.7,
            failure_type="timeout",
            env_healthy=True,
            cluster_accessible=True,
        )
        self.log_result(
            "INFRASTRUCTURE with healthy env flagged",
            report.needs_review and report.final_confidence < 0.7,
            f"Needs review: {report.needs_review}, Conf: {report.final_confidence:.2f}"
        )

        # Test 5: element_not_found + selector missing → FLAGS for review (not auto-correct)
        # NOTE: This no longer auto-corrects to PRODUCT_BUG because TimelineComparisonService
        # provides more accurate classification by comparing git dates between repos.
        report = validator.validate(
            classification="AUTOMATION_BUG",
            confidence=0.7,
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=False,
        )
        self.log_result(
            "Element not found + no selector → flagged for review",
            report.needs_review and not report.was_corrected,
            f"Final: {report.final_classification}, Needs review: {report.needs_review}"
        )

        # Test 6: Consistent classification not corrected
        report = validator.validate(
            classification="PRODUCT_BUG",
            confidence=0.8,
            failure_type="server_error",
            env_healthy=True,
            console_has_500_errors=True,
        )
        self.log_result(
            "Consistent classification boosted not corrected",
            not report.was_corrected and report.final_confidence > 0.8,
            f"Corrected: {report.was_corrected}, Conf: {report.final_confidence:.2f}"
        )

    # =========================================================================
    # Stage 5: Evidence Package Builder
    # =========================================================================
    def validate_evidence_package_builder(self):
        """Validate evidence package builder with complete mock data."""
        from src.services.evidence_package_builder import (
            EvidencePackageBuilder,
            build_evidence_package
        )

        builder = EvidencePackageBuilder()

        # Complete mock data for a server error scenario
        server_error_package = builder.build_for_test(
            test_name="test_api_returns_data",
            error_message="HTTP 500 Internal Server Error: /api/clusters endpoint failed",
            stack_trace="""
Error: Request failed with status code 500
    at createError (webpack://app/./node_modules/axios/lib/core/createError.js:16:15)
    at settle (webpack://app/./node_modules/axios/lib/core/settle.js:17:12)
    at Context.eval (webpack://app/./cypress/tests/api.spec.js:45:20)
""",
            environment_data={
                "healthy": True,
                "accessible": True,
                "api_accessible": True,
                "target_cluster_used": True,
                "cluster_url": "https://api.cluster.example.com"
            },
            repository_data={
                "repository_cloned": True,
                "branch": "release-2.15",
                "commit_sha": "abc123def456",
                "test_files": ["cypress/tests/api.spec.js"],
                "selector_lookup": {},
            },
            console_data={
                "key_errors": [
                    "Error: 500 Internal Server Error",
                    "API request to /api/clusters failed",
                ]
            }
        )

        self.log_result(
            "Build server error package",
            server_error_package.final_classification == "PRODUCT_BUG",
            f"Classification: {server_error_package.final_classification}"
        )

        self.log_result(
            "Server error has high confidence",
            server_error_package.final_confidence >= 0.7,
            f"Confidence: {server_error_package.final_confidence:.2f}"
        )

        # Element not found with selector in codebase
        element_package = builder.build_for_test(
            test_name="test_click_submit_button",
            error_message="Expected to find element: `#submit-btn`, but never found it",
            stack_trace="""
AssertionError: Expected to find element
    at webpack://app/./cypress/views/forms/loginForm.js:42:10
    at Context.eval (webpack://app/./cypress/tests/login.spec.js:25:5)
""",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={
                "repository_cloned": True,
                "selector_lookup": {"#submit-btn": ["cypress/views/forms/loginForm.js"]},
                "selector_history": {
                    "#submit-btn": {
                        "date": "2026-01-10",
                        "sha": "xyz789",
                        "message": "Update form button ID",
                        "days_ago": 5,
                    }
                },
            },
            console_data={"key_errors": []}
        )

        self.log_result(
            "Element not found (selector exists, recently changed) → AUTOMATION",
            element_package.final_classification == "AUTOMATION_BUG",
            f"Classification: {element_package.final_classification}"
        )

        self.log_result(
            "Selector evidence captured",
            element_package.repository_evidence.selector_evidence is not None and
            element_package.repository_evidence.selector_evidence.recently_changed,
            "Selector recently changed detected"
        )

        # Infrastructure failure
        infra_package = builder.build_for_test(
            test_name="test_cluster_access",
            error_message="Connection refused: unable to connect to cluster",
            stack_trace="Error: ECONNREFUSED\n    at connect.js:10:5",
            environment_data={
                "healthy": False,
                "accessible": False,
                "api_accessible": False,
                "errors": ["Connection to cluster failed"]
            },
            repository_data={"repository_cloned": True},
            console_data={
                "key_errors": [
                    "Error: ECONNREFUSED",
                    "Network connection failed",
                ]
            }
        )

        self.log_result(
            "Infrastructure failure classified correctly",
            infra_package.final_classification == "INFRASTRUCTURE",
            f"Classification: {infra_package.final_classification}"
        )

        # Build complete package with multiple failures
        package = builder.build_package(
            jenkins_url="https://jenkins.example.com/job/test/123/",
            build_info={
                "build_number": 123,
                "result": "UNSTABLE",
                "branch": "release-2.15",
            },
            failed_tests=[
                {
                    "test_name": "test_api",
                    "error_message": "500 Internal Server Error",
                    "stack_trace": ""
                },
                {
                    "test_name": "test_button",
                    "error_message": "Element not found: #button",
                    "stack_trace": ""
                },
            ],
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True, "selector_lookup": {}},
            console_data={"key_errors": ["500 error"]}
        )

        self.log_result(
            "Build package with multiple failures",
            package.total_failures == 2,
            f"Total failures: {package.total_failures}"
        )

        self.log_result(
            "Classification counts populated",
            len(package.by_classification) > 0,
            f"Counts: {package.by_classification}"
        )

        # Verify to_dict works
        pkg_dict = package.to_dict()
        self.log_result(
            "Package serializes to dict",
            "metadata" in pkg_dict and "test_failures" in pkg_dict and "summary" in pkg_dict,
            f"Keys: {list(pkg_dict.keys())}"
        )

    # =========================================================================
    # Stage 6: Repository Analysis Integration
    # =========================================================================
    def validate_repository_analysis(self):
        """Validate repository analysis with selector lookup and git history."""
        from src.services.repository_analysis_service import (
            RepositoryAnalysisService,
            SelectorHistory
        )

        service = RepositoryAnalysisService()

        # Test selector lookup building
        mock_test_files = [
            type('TestFile', (), {
                'path': 'cypress/tests/login.spec.js',
                'selectors': ['#username', '#password', '#submit']
            })(),
            type('TestFile', (), {
                'path': 'cypress/views/loginForm.js',
                'selectors': ['#username', '#submit', '.error-msg']
            })(),
        ]

        selector_lookup = {}
        for tf in mock_test_files:
            for selector in tf.selectors:
                if selector not in selector_lookup:
                    selector_lookup[selector] = []
                selector_lookup[selector].append(tf.path)

        self.log_result(
            "Build selector lookup",
            "#username" in selector_lookup and len(selector_lookup["#username"]) == 2,
            f"#username in {len(selector_lookup.get('#username', []))} files"
        )

        self.log_result(
            "Selector appears in multiple files",
            "#submit" in selector_lookup and len(selector_lookup["#submit"]) == 2,
            f"#submit in {len(selector_lookup.get('#submit', []))} files"
        )

        self.log_result(
            "Unique selector tracked",
            ".error-msg" in selector_lookup and len(selector_lookup[".error-msg"]) == 1,
            f".error-msg in {len(selector_lookup.get('.error-msg', []))} files"
        )

        # Test SelectorHistory dataclass
        history = SelectorHistory(
            selector="#submit-btn",
            file_path="cypress/views/forms.js",
            last_modified_date="2026-01-10",
            last_commit_sha="abc123",
            last_commit_message="Update form selectors",
            days_since_modified=5
        )
        self.log_result(
            "SelectorHistory dataclass works",
            history.days_since_modified == 5 and history.selector == "#submit-btn",
            f"Selector: {history.selector}, Days: {history.days_since_modified}"
        )

    # =========================================================================
    # Stage 7: Full Integration Flow
    # =========================================================================
    def validate_full_integration(self):
        """Validate full integration flow with realistic mock data."""
        from src.services.stack_trace_parser import StackTraceParser
        from src.services.classification_decision_matrix import ClassificationDecisionMatrix
        from src.services.confidence_calculator import (
            ConfidenceCalculator, EvidenceCompleteness, SourceConsistency
        )
        from src.services.cross_reference_validator import CrossReferenceValidator
        from src.services.evidence_package_builder import EvidencePackageBuilder

        # Simulate a realistic failed test scenario
        mock_failed_test = {
            "test_name": "test_create_managed_cluster",
            "error_message": "Timed out retrying after 10000ms: Expected to find element: `#managedClusterSet-radio`, but never found it.",
            "stack_trace": """
AssertionError: Timed out retrying after 10000ms: Expected to find element: `#managedClusterSet-radio`, but never found it.
    at webpack://app/./cypress/views/clusters/managedCluster.js:181:11
    at Context.eval (webpack://app/./cypress/tests/managedCluster.spec.js:42:15)
"""
        }

        mock_environment = {
            "healthy": True,
            "accessible": True,
            "api_accessible": True,
            "target_cluster_used": True,
        }

        mock_repository = {
            "repository_cloned": True,
            "branch": "release-2.15",
            "selector_lookup": {
                "#managedClusterSet-radio": ["cypress/views/clusters/managedCluster.js"]
            },
            "selector_history": {
                "#managedClusterSet-radio": {
                    "date": "2026-01-05",
                    "sha": "def456",
                    "message": "Update cluster set radio button ID",
                    "days_ago": 10,
                }
            },
        }

        mock_console = {
            "key_errors": [
                "Timed out retrying",
            ]
        }

        # Step 1: Parse stack trace
        parser = StackTraceParser()
        parsed = parser.parse(mock_failed_test["stack_trace"])
        self.log_result(
            "Integration: Parse stack trace",
            parsed.root_cause_frame is not None,
            f"Root cause: {parsed.root_cause_frame.file_path if parsed.root_cause_frame else 'None'}"
        )

        # Step 2: Extract selector
        selector = parser.extract_failing_selector(mock_failed_test["error_message"])
        self.log_result(
            "Integration: Extract selector",
            selector == "#managedClusterSet-radio",
            f"Selector: {selector}"
        )

        # Step 3: Check selector in repository
        selector_found = selector in mock_repository.get("selector_lookup", {})
        selector_recently_changed = mock_repository.get("selector_history", {}).get(selector, {}).get("days_ago", 999) <= 30
        self.log_result(
            "Integration: Selector lookup",
            selector_found and selector_recently_changed,
            f"Found: {selector_found}, Recently changed: {selector_recently_changed}"
        )

        # Step 4: Apply decision matrix
        matrix = ClassificationDecisionMatrix()
        classification = matrix.classify(
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=True,
            additional_factors={"selector_recently_changed": True}
        )
        self.log_result(
            "Integration: Decision matrix",
            classification.classification.value == "AUTOMATION_BUG",
            f"Classification: {classification.classification.value}"
        )

        # Step 5: Calculate confidence
        calc = ConfidenceCalculator()
        confidence = calc.calculate(
            classification_scores={
                "product_bug": classification.scores.product_bug,
                "automation_bug": classification.scores.automation_bug,
                "infrastructure": classification.scores.infrastructure,
            },
            evidence_completeness=EvidenceCompleteness(
                has_stack_trace=True,
                has_parsed_frames=True,
                has_root_cause_file=True,
                has_environment_status=True,
                has_repository_analysis=True,
                has_selector_lookup=True,
                has_git_history=True,
            ),
            source_consistency=SourceConsistency(
                jenkins_suggests="AUTOMATION_BUG",
                repository_suggests="AUTOMATION_BUG",
            ),
            selector_found=True,
            selector_recently_changed=True,
        )
        self.log_result(
            "Integration: Confidence calculation",
            confidence.final_confidence >= 0.5,
            f"Confidence: {confidence.final_confidence:.2f}, Level: {confidence.confidence_level}"
        )

        # Step 6: Cross-validate
        validator = CrossReferenceValidator()
        validation = validator.validate(
            classification="AUTOMATION_BUG",
            confidence=confidence.final_confidence,
            failure_type="element_not_found",
            env_healthy=True,
            selector_found=True,
            selector_recently_changed=True,
        )
        self.log_result(
            "Integration: Cross-validation",
            not validation.was_corrected and validation.final_classification == "AUTOMATION_BUG",
            f"Final: {validation.final_classification}, Corrected: {validation.was_corrected}"
        )

        # Step 7: Build complete evidence package
        builder = EvidencePackageBuilder()
        package = builder.build_for_test(
            test_name=mock_failed_test["test_name"],
            error_message=mock_failed_test["error_message"],
            stack_trace=mock_failed_test["stack_trace"],
            environment_data=mock_environment,
            repository_data=mock_repository,
            console_data=mock_console,
        )
        self.log_result(
            "Integration: Build evidence package",
            package.final_classification == "AUTOMATION_BUG" and package.final_confidence >= 0.5,
            f"Final: {package.final_classification}, Confidence: {package.final_confidence:.2f}"
        )

        # Step 8: Verify package serialization
        pkg_dict = package.to_dict()
        self.log_result(
            "Integration: Package serializable",
            "pre_calculated_scores" in pkg_dict and "final_classification" in pkg_dict,
            f"Keys present: {bool('pre_calculated_scores' in pkg_dict)}"
        )

    # =========================================================================
    # Stage 8: Edge Cases & Error Handling
    # =========================================================================
    def validate_edge_cases(self):
        """Validate edge cases and error handling."""
        from src.services.stack_trace_parser import StackTraceParser
        from src.services.classification_decision_matrix import classify_failure
        from src.services.evidence_package_builder import EvidencePackageBuilder

        parser = StackTraceParser()
        builder = EvidencePackageBuilder()

        # Edge case 1: Empty error message
        package = builder.build_for_test(
            test_name="test_empty",
            error_message="",
            stack_trace="",
            environment_data={},
            repository_data={},
            console_data={}
        )
        self.log_result(
            "Handle empty error message",
            package.failure_evidence.failure_category == "unknown",
            f"Category: {package.failure_evidence.failure_category}"
        )

        # Edge case 2: Very long error message
        long_msg = "Error: " + "x" * 2000
        package = builder.build_for_test(
            test_name="test_long",
            error_message=long_msg,
            stack_trace="",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={},
            console_data={}
        )
        self.log_result(
            "Handle long error message (truncated)",
            len(package.failure_evidence.error_message) <= 500,
            f"Length: {len(package.failure_evidence.error_message)}"
        )

        # Edge case 3: Unknown failure type
        result = classify_failure(
            failure_type="some_random_type",
            env_healthy=True,
            selector_found=True
        )
        self.log_result(
            "Handle unknown failure type",
            result.classification is not None,
            f"Classification: {result.classification.value}"
        )

        # Edge case 4: Malformed stack trace
        malformed = "This is not a stack trace at all\nJust some random text"
        parsed = parser.parse(malformed)
        self.log_result(
            "Handle malformed stack trace",
            parsed.total_frames == 0,
            f"Frames: {parsed.total_frames}"
        )

        # Edge case 5: Selector with special characters
        selector = parser.extract_failing_selector(
            "Element not found: `[data-testid='complex-selector-123']`"
        )
        self.log_result(
            "Handle complex selector",
            selector is not None and "data-testid" in selector,
            f"Selector: {selector}"
        )

        # Edge case 6: All optional fields missing
        package = builder.build_for_test(
            test_name="minimal_test",
            error_message="Test failed",
            stack_trace="",
            environment_data={},
            repository_data={},
            console_data={}
        )
        pkg_dict = package.to_dict()
        self.log_result(
            "Handle minimal input data",
            "final_classification" in pkg_dict and "final_confidence" in pkg_dict,
            "Minimal package built successfully"
        )

        # Edge case 7: Conflicting signals
        # 500 error but classified as INFRASTRUCTURE
        from src.services.cross_reference_validator import validate_classification
        report = validate_classification(
            classification="INFRASTRUCTURE",
            confidence=0.6,
            failure_type="timeout",
            env_healthy=True,
            console_has_500_errors=True,
        )
        self.log_result(
            "Handle conflicting signals (500 + INFRASTRUCTURE)",
            report.needs_review or report.final_confidence < 0.6,
            f"Needs review: {report.needs_review}, Confidence: {report.final_confidence:.2f}"
        )


def main():
    """Run the deep dive validation."""
    validator = DeepDiveValidator()
    validator.run_all()

    # Return exit code based on results
    if validator.results["failed"] or validator.results["errors"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
