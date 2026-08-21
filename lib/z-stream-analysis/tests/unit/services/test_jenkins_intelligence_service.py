#!/usr/bin/env python3
"""
Unit Tests for Jenkins Intelligence Service
Tests the core functionality of Jenkins pipeline failure analysis
"""

import unittest
import json
import tempfile
import os
import sys
import subprocess
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Add source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from services.jenkins_intelligence_service import (
    JenkinsIntelligenceService,
    JenkinsMetadata,
    JenkinsIntelligence,
    TestReport,
    TestCaseFailure
)


class TestJenkinsIntelligenceService(unittest.TestCase):
    """
    Test suite for Jenkins Intelligence Service
    
    CRITICAL TESTING GOALS:
    1. Verify Jenkins URL parsing and metadata extraction
    2. Validate console log analysis and failure pattern detection
    3. Test environment information extraction from parameters
    4. Ensure evidence source generation for citations
    5. Validate confidence scoring accuracy
    """
    
    def setUp(self):
        """Set up test environment"""
        self.service = JenkinsIntelligenceService()
        self.sample_jenkins_urls = self._load_sample_jenkins_urls()
        self.sample_console_logs = self._load_sample_console_logs()
        self.sample_build_info = self._load_sample_build_info()
        
    def _load_sample_jenkins_urls(self) -> Dict[str, str]:
        """Load sample Jenkins URLs for testing"""
        return {
            "clc_e2e_3313": "https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/clc-e2e-pipeline/3313/",
            "alc_e2e_2412": "https://jenkins-csb-rhacm-tests.dno.corp.redhat.com/job/qe-acm-automation-poc/job/alc_e2e_tests/2412/",
            "invalid_url": "https://invalid-jenkins.com/job/nonexistent/999/"
        }
    
    def _load_sample_console_logs(self) -> Dict[str, str]:
        """Load sample console logs for testing"""
        return {
            "timeout_failure": """
                [INFO] Starting test execution
                [ERROR] TimeoutError: Timed out after 30 seconds waiting for element
                cypress timed out waiting for selector '.cluster-list'
                Test failed due to timeout in cluster management page
            """,
            "element_not_found": """
                [INFO] Navigating to cluster page
                [ERROR] ElementNotInteractableException: Element not found
                selector 'button[data-test="create-cluster"]' not found
                NoSuchElementException: Unable to locate element
            """,
            "network_error": """
                [INFO] Connecting to cluster API
                [ERROR] Connection refused to https://api.cluster.example.com
                DNS resolution failed for cluster endpoint
                Network error: failed to connect to cluster
            """,
            "mixed_failures": """
                [ERROR] TimeoutError: timeout waiting for element
                [ERROR] ElementNotInteractableException: element not found
                [ERROR] Connection refused to cluster API
                Test suite failed with multiple errors
            """
        }
    
    def _load_sample_build_info(self) -> Dict[str, Dict[str, Any]]:
        """Load sample build info for testing"""
        return {
            "successful_build": {
                "result": "SUCCESS",
                "timestamp": "2024-08-17T17:55:40Z",
                "parameters": {
                    "CLUSTER_NAME": "qe6-vmware-ibm",
                    "BRANCH": "release-2.9",
                    "TEST_SUITE": "clc-e2e"
                },
                "artifacts": [
                    {"fileName": "test-results.xml"},
                    {"fileName": "screenshots.zip"}
                ]
            },
            "failed_build": {
                "result": "FAILURE",
                "timestamp": "2024-08-17T14:03:00Z",
                "actions": [
                    {
                        "parameters": [
                            {"name": "environment", "value": "staging-cluster"},
                            {"name": "git_branch", "value": "origin/release-2.11"},
                            {"name": "SUITE", "value": "alc_e2e_tests"}
                        ]
                    }
                ],
                "artifacts": [
                    {"fileName": "console.log"},
                    {"fileName": "cypress-results.json"}
                ]
            },
            "minimal_build": {
                "result": "UNKNOWN",
                "timestamp": "",
                "parameters": {},
                "artifacts": []
            }
        }

    # CRITICAL TEST 1: Jenkins URL Parsing and Metadata Extraction
    def test_jenkins_url_parsing_and_metadata_extraction(self):
        """
        CRITICAL: Test Jenkins URL parsing and metadata extraction accuracy
        """
        test_cases = [
            {
                "name": "Standard Jenkins URL",
                "url": "https://jenkins-server.com/job/clc-e2e-pipeline/3313/",
                "expected_job": "clc-e2e-pipeline",
                "expected_build": 3313
            },
            {
                "name": "Nested Job URL",
                "url": "https://jenkins-server.com/job/qe-acm-automation-poc/job/alc_e2e_tests/2412/",
                "expected_job": "qe-acm-automation-poc",  # Should get first job name
                "expected_build": 2412
            },
            {
                "name": "URL without trailing slash",
                "url": "https://jenkins-server.com/job/test-pipeline/123",
                "expected_job": "test-pipeline",
                "expected_build": 123
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case["name"]):
                # Mock the external calls
                with patch.object(self.service, '_fetch_console_log', return_value="mock console log"):
                    with patch.object(self.service, '_fetch_build_info', return_value=self.sample_build_info["successful_build"]):
                        
                        metadata = self.service._extract_jenkins_metadata(case["url"])
                        
                        self.assertEqual(metadata.build_url, case["url"])
                        self.assertEqual(metadata.job_name, case["expected_job"])
                        self.assertEqual(metadata.build_number, case["expected_build"])
                        self.assertEqual(metadata.build_result, "SUCCESS")

    # CRITICAL TEST 2: Console Log Analysis and Failure Pattern Detection
    def test_console_log_failure_pattern_detection(self):
        """
        CRITICAL: Test console log analysis for different failure patterns
        """
        test_cases = [
            {
                "name": "Timeout Failures",
                "console_log": self.sample_console_logs["timeout_failure"],
                "expected_primary": "timeout_errors",
                "expected_min_failures": 2
            },
            {
                "name": "Element Not Found Failures", 
                "console_log": self.sample_console_logs["element_not_found"],
                "expected_primary": "element_not_found",
                "expected_min_failures": 2
            },
            {
                "name": "Network Errors",
                "console_log": self.sample_console_logs["network_error"],
                "expected_primary": "network_errors",
                "expected_min_failures": 1
            },
            {
                "name": "Mixed Failure Types",
                "console_log": self.sample_console_logs["mixed_failures"],
                "expected_primary": None,  # Could be any type
                "expected_min_failures": 3
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case["name"]):
                analysis = self.service._analyze_failure_patterns(case["console_log"])
                
                # Validate structure
                self.assertIn('patterns', analysis)
                self.assertIn('total_failures', analysis)
                self.assertIn('primary_failure_type', analysis)
                
                # Validate failure detection
                self.assertGreaterEqual(analysis['total_failures'], case["expected_min_failures"])
                
                if case["expected_primary"]:
                    self.assertEqual(analysis['primary_failure_type'], case["expected_primary"])

    # CRITICAL TEST 3: Environment Information Extraction
    def test_environment_information_extraction(self):
        """
        CRITICAL: Test extraction of environment info from build parameters
        """
        test_cases = [
            {
                "name": "Standard Parameters",
                "parameters": {
                    "CLUSTER_NAME": "qe6-vmware-ibm",
                    "BRANCH": "release-2.9", 
                    "TEST_SUITE": "clc-e2e"
                },
                "expected_cluster": "qe6-vmware-ibm",
                "expected_branch": "release-2.9",
                "expected_suite": "clc-e2e"
            },
            {
                "name": "Alternative Parameter Names",
                "parameters": {
                    "environment": "staging-cluster",
                    "git_branch": "origin/release-2.11",
                    "SUITE": "alc_e2e_tests"
                },
                "expected_cluster": "staging-cluster",
                "expected_branch": "origin/release-2.11",
                "expected_suite": "alc_e2e_tests"
            },
            {
                "name": "Empty Parameters",
                "parameters": {},
                "expected_cluster": None,
                "expected_branch": None,
                "expected_suite": None
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case["name"]):
                env_info = self.service._extract_environment_info(case["parameters"])
                
                self.assertEqual(env_info['cluster_name'], case["expected_cluster"])
                self.assertEqual(env_info['target_branch'], case["expected_branch"])
                self.assertEqual(env_info['test_suite'], case["expected_suite"])

    # CRITICAL TEST 4: Branch and Commit Extraction
    def test_branch_and_commit_extraction(self):
        """
        CRITICAL: Test branch and commit SHA extraction accuracy
        """
        # Test branch extraction from parameters
        branch_test_cases = [
            {
                "parameters": {"BRANCH": "release-2.9"},
                "expected": "release-2.9"
            },
            {
                "parameters": {"git_branch": "origin/release-2.11"},
                "expected": "release-2.11"  # Should remove origin/ prefix
            },
            {
                "parameters": {"GIT_BRANCH": "main"},
                "expected": "main"
            },
            {
                "parameters": {},
                "expected": None
            }
        ]
        
        for case in branch_test_cases:
            with self.subTest(parameters=case["parameters"]):
                result = self.service._extract_branch_from_parameters(case["parameters"])
                self.assertEqual(result, case["expected"])
        
        # Test commit extraction from console logs
        commit_test_cases = [
            {
                "console": "Revision: b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1",
                "expected": "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"
            },
            {
                "console": "commit a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
                "expected": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
            },
            {
                "console": "Checking out abcd1234",
                "expected": "abcd1234"
            },
            {
                "console": "No commit information available",
                "expected": None
            }
        ]
        
        for case in commit_test_cases:
            with self.subTest(console=case["console"][:20]):
                result = self.service._extract_commit_from_console(case["console"])
                self.assertEqual(result, case["expected"])

    # CRITICAL TEST 5: Evidence Source Generation
    def test_evidence_source_generation(self):
        """
        CRITICAL: Test generation of evidence sources for citations
        """
        sample_metadata = JenkinsMetadata(
            build_url="https://jenkins-server.com/job/clc-e2e-pipeline/3313/",
            job_name="clc-e2e-pipeline",
            build_number=3313,
            build_result="FAILURE",
            timestamp="2024-08-17T17:55:40Z",
            parameters={"CLUSTER_NAME": "qe6-vmware-ibm"},
            console_log_snippet="Test failure log...",
            artifacts=["results.xml"],
            branch="release-2.9",
            commit_sha="b2c3d4e5f6a7b8c9"
        )
        
        sources = self.service._build_evidence_sources(sample_metadata)
        
        # Should have at least Jenkins, Console, and Repo sources
        self.assertGreaterEqual(len(sources), 3)
        
        # Validate Jenkins source format
        jenkins_source = sources[0]
        self.assertIn("Jenkins:clc-e2e-pipeline:3313:FAILURE", jenkins_source)
        self.assertIn("https://jenkins-server.com/job/clc-e2e-pipeline/3313/", jenkins_source)
        
        # Validate Console source
        console_source = sources[1]
        self.assertIn("Console:clc-e2e-pipeline:3313", console_source)
        
        # Validate Repo source
        repo_source = sources[2]
        self.assertIn("Repo:release-2.9:commit:b2c3d4e5f6a7b8c9", repo_source)

    # CRITICAL TEST 6: Confidence Score Calculation
    def test_confidence_score_calculation(self):
        """
        CRITICAL: Test confidence score calculation accuracy
        """
        # Create complete test report with factual data (failure_type and stack_trace)
        complete_test_report = TestReport(
            total_tests=5,
            passed_count=0,
            failed_count=5,
            skipped_count=0,
            pass_rate=0.0,
            failed_tests=[
                TestCaseFailure(
                    test_name="test_example",
                    class_name="TestClass",
                    status="FAILED",
                    duration=10.0,
                    failure_type="element_not_found",
                    stack_trace="at test.js:10"
                )
            ],
            duration=50.0
        )

        test_cases = [
            {
                "name": "Complete Information",
                "metadata": JenkinsMetadata(
                    build_url="https://jenkins.com/job/test/123/",
                    job_name="test",
                    build_number=123,
                    build_result="FAILURE",
                    timestamp="2024-08-17T17:55:40Z",
                    parameters={"CLUSTER_NAME": "test-cluster"},
                    console_log_snippet="Error details here...",
                    artifacts=[],
                    branch="release-2.9",
                    commit_sha="abc123"
                ),
                "failure_analysis": {"total_failures": 5},
                "test_report": complete_test_report,
                "expected_min": 0.9
            },
            {
                "name": "Minimal Information",
                "metadata": JenkinsMetadata(
                    build_url="https://jenkins.com/job/test/123/",
                    job_name="test",
                    build_number=123,
                    build_result="UNKNOWN",
                    timestamp="",
                    parameters={},
                    console_log_snippet="",
                    artifacts=[]
                ),
                "failure_analysis": {"total_failures": 0},
                "expected_max": 0.3
            }
        ]
        
        for case in test_cases:
            with self.subTest(case=case["name"]):
                score = self.service._calculate_confidence_score(
                    case["metadata"],
                    case["failure_analysis"],
                    case.get("test_report")  # Pass test_report if available
                )
                
                self.assertIsInstance(score, float)
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)
                
                if "expected_min" in case:
                    self.assertGreaterEqual(score, case["expected_min"])
                if "expected_max" in case:
                    self.assertLessEqual(score, case["expected_max"])

    # CRITICAL TEST 7: Complete Integration Test
    @patch('subprocess.run')
    def test_complete_jenkins_analysis_integration(self, mock_subprocess):
        """
        CRITICAL: Test complete Jenkins intelligence analysis flow
        """
        # Mock curl responses
        mock_console_response = Mock()
        mock_console_response.returncode = 0
        mock_console_response.stdout = self.sample_console_logs["timeout_failure"]
        
        mock_api_response = Mock()
        mock_api_response.returncode = 0
        mock_api_response.stdout = json.dumps(self.sample_build_info["failed_build"])
        
        # Configure subprocess mock to return different responses based on URL
        def subprocess_side_effect(*args, **kwargs):
            cmd_args = args[0]
            if 'consoleText' in ' '.join(cmd_args):
                return mock_console_response
            elif 'api/json' in ' '.join(cmd_args):
                return mock_api_response
            else:
                return Mock(returncode=1, stdout="", stderr="Unknown URL")
        
        mock_subprocess.side_effect = subprocess_side_effect
        
        # Execute complete analysis
        jenkins_url = "https://jenkins-server.com/job/test-pipeline/123/"
        result = self.service.analyze_jenkins_url(jenkins_url)
        
        # Validate result structure
        self.assertIsInstance(result, JenkinsIntelligence)
        self.assertIsInstance(result.metadata, JenkinsMetadata)
        self.assertIsInstance(result.failure_analysis, dict)
        self.assertIsInstance(result.environment_info, dict)
        self.assertIsInstance(result.evidence_sources, list)
        self.assertIsInstance(result.confidence_score, float)
        
        # Validate metadata extraction
        self.assertEqual(result.metadata.build_url, jenkins_url)
        self.assertEqual(result.metadata.job_name, "test-pipeline")
        self.assertEqual(result.metadata.build_number, 123)
        self.assertEqual(result.metadata.build_result, "FAILURE")
        
        # Validate failure analysis
        self.assertIn('patterns', result.failure_analysis)
        self.assertGreater(result.failure_analysis['total_failures'], 0)
        
        # Validate environment info extraction
        self.assertEqual(result.environment_info['cluster_name'], "staging-cluster")
        self.assertEqual(result.environment_info['target_branch'], "origin/release-2.11")
        
        # Validate evidence sources
        self.assertGreater(len(result.evidence_sources), 0)
        
        # Validate confidence score
        self.assertGreater(result.confidence_score, 0.5)

    # CRITICAL TEST 8: Error Handling and Edge Cases
    @patch('subprocess.run')
    def test_error_handling_and_edge_cases(self, mock_subprocess):
        """
        CRITICAL: Test error handling for network failures and invalid data
        """
        error_scenarios = [
            {
                "name": "Network Timeout",
                "side_effect": subprocess.TimeoutExpired(cmd=['curl'], timeout=30),
                "expected_behavior": "graceful_fallback"
            },
            {
                "name": "Invalid JSON Response",
                "response": Mock(returncode=0, stdout="invalid json{"),
                "expected_behavior": "empty_build_info"
            },
            {
                "name": "Network Connection Failed",
                "response": Mock(returncode=1, stdout="", stderr="Connection refused"),
                "expected_behavior": "empty_response"
            }
        ]
        
        for scenario in error_scenarios:
            with self.subTest(scenario=scenario["name"]):
                if "side_effect" in scenario:
                    mock_subprocess.side_effect = scenario["side_effect"]
                else:
                    mock_subprocess.return_value = scenario["response"]
                
                try:
                    # Test individual methods for robustness
                    if scenario["expected_behavior"] == "graceful_fallback":
                        console_log = self.service._fetch_console_log("https://test.com/job/test/123/")
                        self.assertEqual(console_log, "")  # Should return empty string
                    
                    elif scenario["expected_behavior"] == "empty_build_info":
                        build_info = self.service._fetch_build_info("https://test.com/job/test/123/")
                        self.assertEqual(build_info, {})  # Should return empty dict
                    
                    elif scenario["expected_behavior"] == "empty_response":
                        console_log = self.service._fetch_console_log("https://test.com/job/test/123/")
                        self.assertEqual(console_log, "")
                        
                except Exception as e:
                    self.fail(f"Error handling failed for {scenario['name']}: {str(e)}")
                
                # Reset mock for next test
                mock_subprocess.side_effect = None

    # CRITICAL TEST 9: Serialization and Data Persistence
    def test_serialization_and_data_persistence(self):
        """
        CRITICAL: Test serialization of analysis results for persistence
        """
        # Create sample intelligence result
        metadata = JenkinsMetadata(
            build_url="https://jenkins.com/job/test/123/",
            job_name="test",
            build_number=123,
            build_result="FAILURE",
            timestamp="2024-08-17T17:55:40Z",
            parameters={"CLUSTER_NAME": "test-cluster"},
            console_log_snippet="Error log...",
            artifacts=["results.xml"],
            branch="release-2.9",
            commit_sha="abc123"
        )
        
        intelligence = JenkinsIntelligence(
            metadata=metadata,
            failure_analysis={"total_failures": 3, "primary_failure_type": "timeout_errors"},
            environment_info={"cluster_name": "test-cluster"},
            evidence_sources=["[Jenkins:test:123:FAILURE]"],
            confidence_score=0.85
        )
        
        # Test serialization
        serialized = self.service.to_dict(intelligence)
        
        # Validate serialized structure
        self.assertIn('metadata', serialized)
        self.assertIn('failure_analysis', serialized)
        self.assertIn('environment_info', serialized)
        self.assertIn('evidence_sources', serialized)
        self.assertIn('confidence_score', serialized)
        
        # Test JSON serialization
        json_str = json.dumps(serialized)
        self.assertIsInstance(json_str, str)
        
        # Test JSON deserialization
        restored = json.loads(json_str)
        self.assertEqual(restored['metadata']['job_name'], "test")
        self.assertEqual(restored['confidence_score'], 0.85)


if __name__ == '__main__':
    # Set up test discovery and execution
    test_loader = unittest.TestLoader()
    test_suite = test_loader.loadTestsFromTestCase(TestJenkinsIntelligenceService)
    
    # Run tests with detailed output
    test_runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = test_runner.run(test_suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)