#!/usr/bin/env python3
"""
Unit tests for Evidence Package Builder Service
"""

import pytest
from src.services.evidence_package_builder import (
    EvidencePackageBuilder,
    EvidencePackage,
    TestFailureEvidencePackage,
    FailureEvidence,
    RepositoryEvidence,
    EnvironmentEvidence,
    ConsoleEvidence,
    SelectorEvidence,
    build_evidence_package
)


class TestSelectorEvidence:
    """Tests for SelectorEvidence dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        evidence = SelectorEvidence(
            selector="#my-button",
            found_in_codebase=True,
            file_paths=["test.js", "page.js"],
            last_modified_date="2026-01-10",
            days_since_modified=5,
            recently_changed=True,
        )
        d = evidence.to_dict()
        assert d["selector"] == "#my-button"
        assert d["found_in_codebase"] is True
        assert len(d["file_paths"]) == 2
        assert d["recently_changed"] is True


class TestEnvironmentEvidence:
    """Tests for EnvironmentEvidence dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        evidence = EnvironmentEvidence(
            cluster_healthy=True,
            cluster_accessible=True,
            api_accessible=True,
            target_cluster_used=True,
            cluster_url="https://api.cluster.example.com",
        )
        d = evidence.to_dict()
        assert d["cluster_healthy"] is True
        assert d["cluster_accessible"] is True


class TestConsoleEvidence:
    """Tests for ConsoleEvidence dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        evidence = ConsoleEvidence(
            has_500_errors=True,
            has_network_errors=False,
            has_api_errors=True,
            error_snippets=["Error: 500 Internal Server Error"],
        )
        d = evidence.to_dict()
        assert d["has_500_errors"] is True
        assert d["has_network_errors"] is False
        assert len(d["error_snippets"]) == 1


class TestRepositoryEvidence:
    """Tests for RepositoryEvidence dataclass."""

    def test_to_dict_basic(self):
        """Test basic dictionary conversion."""
        evidence = RepositoryEvidence(
            repository_cloned=True,
            branch="main",
            commit_sha="abc123",
            test_file_exists=True,
        )
        d = evidence.to_dict()
        assert d["repository_cloned"] is True
        assert d["branch"] == "main"

    def test_to_dict_with_selector(self):
        """Test dictionary with selector evidence."""
        evidence = RepositoryEvidence(
            repository_cloned=True,
            branch="main",
            selector_evidence=SelectorEvidence(
                selector="#test",
                found_in_codebase=True,
            ),
        )
        d = evidence.to_dict()
        assert "selector_evidence" in d
        assert d["selector_evidence"]["selector"] == "#test"


class TestFailureEvidence:
    """Tests for FailureEvidence dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        evidence = FailureEvidence(
            test_name="test_login",
            error_message="Element not found",
            error_type="AssertionError",
            failure_category="element_not_found",
            root_cause_file="test.js",
            root_cause_line=42,
        )
        d = evidence.to_dict()
        assert d["test_name"] == "test_login"
        assert d["failure_category"] == "element_not_found"
        assert d["root_cause_line"] == 42


class TestEvidencePackageBuilder:
    """Tests for EvidencePackageBuilder class."""

    def setup_method(self):
        """Setup for each test."""
        self.builder = EvidencePackageBuilder()

    def test_build_for_test_basic(self):
        """Test building evidence for a single test."""
        result = self.builder.build_for_test(
            test_name="test_login_button",
            error_message="Timed out waiting for element: #login-button",
            stack_trace="Error: Timeout\n    at test.js:10:5",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True, "branch": "main"},
            console_data={"key_errors": []},
        )

        assert isinstance(result, TestFailureEvidencePackage)
        assert result.test_name == "test_login_button"
        assert result.final_classification in ["PRODUCT_BUG", "AUTOMATION_BUG", "INFRASTRUCTURE"]
        assert 0 <= result.final_confidence <= 1

    def test_build_for_test_server_error(self):
        """Test building evidence for server error."""
        result = self.builder.build_for_test(
            test_name="test_api_call",
            error_message="Internal Server Error 500",
            stack_trace="Error: 500\n    at api.js:20:10",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": ["Error: 500 Internal Server Error"]},
        )

        assert result.final_classification == "PRODUCT_BUG"

    def test_build_for_test_element_not_found(self):
        """Test building evidence for element not found."""
        result = self.builder.build_for_test(
            test_name="test_click_button",
            error_message="Expected to find element: `#submit-btn`, but never found it",
            stack_trace="Error: Element not found\n    at test.js:15:5",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={
                "repository_cloned": True,
                "selector_lookup": {"#submit-btn": ["test.js"]},
            },
            console_data={"key_errors": []},
        )

        # Element not found with selector in codebase → likely AUTOMATION_BUG
        assert result.final_classification in ["AUTOMATION_BUG", "PRODUCT_BUG"]

    def test_build_for_test_infrastructure(self):
        """Test building evidence for infrastructure failure."""
        result = self.builder.build_for_test(
            test_name="test_cluster_access",
            error_message="Connection refused",
            stack_trace="Error: Network\n    at client.js:5:2",
            environment_data={"healthy": False, "accessible": False, "api_accessible": False},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": ["Error: ECONNREFUSED", "network error"]},
        )

        assert result.final_classification == "INFRASTRUCTURE"

    def test_build_for_test_with_selector_history(self):
        """Test building evidence with selector git history."""
        result = self.builder.build_for_test(
            test_name="test_button",
            error_message="Element not found: #old-button",
            stack_trace="",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={
                "repository_cloned": True,
                "selector_lookup": {"#old-button": ["page.js"]},
                "selector_history": {
                    "#old-button": {
                        "date": "2026-01-10",
                        "sha": "abc123",
                        "message": "Renamed button ID",
                        "days_ago": 5,
                    }
                },
            },
            console_data={"key_errors": []},
        )

        # Selector recently changed should influence classification
        assert result.repository_evidence.selector_evidence is not None
        assert result.repository_evidence.selector_evidence.recently_changed is True

    def test_build_package_multiple_tests(self):
        """Test building complete package for multiple tests."""
        package = self.builder.build_package(
            jenkins_url="https://jenkins.example.com/job/test/123/",
            build_info={"build_number": 123, "result": "UNSTABLE", "branch": "main"},
            failed_tests=[
                {
                    "test_name": "test_1",
                    "error_message": "Timeout waiting for element",
                    "stack_trace": "",
                },
                {
                    "test_name": "test_2",
                    "error_message": "500 Internal Server Error",
                    "stack_trace": "",
                },
            ],
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": []},
        )

        assert isinstance(package, EvidencePackage)
        assert package.total_failures == 2
        assert len(package.test_failures) == 2
        assert package.overall_classification is not None

    def test_build_package_classification_counts(self):
        """Test that classification counts are correct."""
        package = self.builder.build_package(
            jenkins_url="https://jenkins.example.com/job/test/123/",
            build_info={"build_number": 123, "result": "UNSTABLE"},
            failed_tests=[
                {
                    "test_name": "test_1",
                    "error_message": "500 Internal Server Error",
                    "stack_trace": "",
                },
                {
                    "test_name": "test_2",
                    "error_message": "500 Backend Error",
                    "stack_trace": "",
                },
            ],
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": ["500 error"]},
        )

        # Both should be PRODUCT_BUG
        assert package.by_classification.get("PRODUCT_BUG", 0) >= 1

    def test_determine_failure_category_timeout(self):
        """Test failure category detection for timeout."""
        category = self.builder._determine_failure_category(
            "Timed out waiting for element",
            "TimeoutError"
        )
        assert category == "timeout"

    def test_determine_failure_category_element_not_found(self):
        """Test failure category detection for element not found."""
        category = self.builder._determine_failure_category(
            "Element not found: #button",
            "Error"
        )
        assert category == "element_not_found"

    def test_determine_failure_category_assertion(self):
        """Test failure category detection for assertion."""
        category = self.builder._determine_failure_category(
            "Expected true to equal false",
            "AssertionError"
        )
        assert category == "assertion"

    def test_determine_failure_category_server_error(self):
        """Test failure category detection for server error."""
        category = self.builder._determine_failure_category(
            "500 Internal Server Error",
            "Error"
        )
        assert category == "server_error"

    def test_determine_failure_category_auth(self):
        """Test failure category detection for auth error."""
        category = self.builder._determine_failure_category(
            "401 Unauthorized",
            "Error"
        )
        assert category == "auth_error"

    def test_determine_failure_category_network(self):
        """Test failure category detection for network error."""
        category = self.builder._determine_failure_category(
            "Network connection failed",
            "Error"
        )
        assert category == "network"

    def test_to_dict_complete(self):
        """Test complete dictionary conversion."""
        result = self.builder.build_for_test(
            test_name="test_example",
            error_message="Test error",
            stack_trace="",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": []},
        )

        d = result.to_dict()
        assert "test_name" in d
        assert "failure_evidence" in d
        assert "repository_evidence" in d
        assert "environment_evidence" in d
        assert "console_evidence" in d
        assert "pre_calculated_scores" in d
        assert "final_classification" in d
        assert "final_confidence" in d

    def test_package_to_dict(self):
        """Test package dictionary conversion."""
        package = self.builder.build_package(
            jenkins_url="https://jenkins.example.com/job/test/123/",
            build_info={"build_number": 123, "result": "UNSTABLE"},
            failed_tests=[{"test_name": "test_1", "error_message": "Error", "stack_trace": ""}],
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": []},
        )

        d = package.to_dict()
        assert "metadata" in d
        assert "test_failures" in d
        assert "summary" in d
        assert d["metadata"]["jenkins_url"] == "https://jenkins.example.com/job/test/123/"


class TestConvenienceFunction:
    """Tests for build_evidence_package convenience function."""

    def test_basic_usage(self):
        """Test basic convenience function usage."""
        package = build_evidence_package(
            jenkins_url="https://jenkins.example.com/job/test/123/",
            build_info={"build_number": 123, "result": "UNSTABLE"},
            failed_tests=[{"test_name": "test_1", "error_message": "Error", "stack_trace": ""}],
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": []},
        )

        assert isinstance(package, EvidencePackage)
        assert package.total_failures == 1


class TestEdgeCases:
    """Edge case tests for evidence package builder."""

    def setup_method(self):
        """Setup for each test."""
        self.builder = EvidencePackageBuilder()

    def test_empty_error_message(self):
        """Test with empty error message."""
        result = self.builder.build_for_test(
            test_name="test_1",
            error_message="",
            stack_trace="",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": []},
        )

        assert isinstance(result, TestFailureEvidencePackage)
        assert result.failure_evidence.failure_category == "unknown"

    def test_empty_failed_tests(self):
        """Test with empty failed tests list."""
        package = self.builder.build_package(
            jenkins_url="https://jenkins.example.com/job/test/123/",
            build_info={"build_number": 123, "result": "SUCCESS"},
            failed_tests=[],
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": []},
        )

        assert package.total_failures == 0
        assert len(package.test_failures) == 0

    def test_missing_environment_data(self):
        """Test with minimal environment data."""
        result = self.builder.build_for_test(
            test_name="test_1",
            error_message="Error",
            stack_trace="",
            environment_data={},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": []},
        )

        # Should use defaults
        assert result.environment_evidence.cluster_healthy is True

    def test_missing_repository_data(self):
        """Test with minimal repository data."""
        result = self.builder.build_for_test(
            test_name="test_1",
            error_message="Error",
            stack_trace="",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={},
            console_data={"key_errors": []},
        )

        assert result.repository_evidence.repository_cloned is False

    def test_long_error_message_truncated(self):
        """Test that long error messages are handled."""
        long_message = "Error: " + "x" * 1000
        result = self.builder.build_for_test(
            test_name="test_1",
            error_message=long_message,
            stack_trace="",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={"key_errors": []},
        )

        # Error message should be truncated
        assert len(result.failure_evidence.error_message) <= 500

    def test_console_errors_parsed(self):
        """Test console error parsing."""
        result = self.builder.build_for_test(
            test_name="test_1",
            error_message="Test failed",
            stack_trace="",
            environment_data={"healthy": True, "accessible": True, "api_accessible": True},
            repository_data={"repository_cloned": True},
            console_data={
                "key_errors": [
                    "HTTP 500 Internal Server Error",
                    "API endpoint failed",
                    "ECONNREFUSED connection refused",
                ]
            },
        )

        assert result.console_evidence.has_500_errors is True
        assert result.console_evidence.has_api_errors is True
        assert result.console_evidence.has_connection_refused is True
