#!/usr/bin/env python3
"""
Unit Tests for Data Classes
Tests data class validation, field integrity, and serialization
"""

import unittest
import time
import sys
import os
from dataclasses import asdict
from typing import Dict, Any

# Add source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from services.jenkins_intelligence_service import JenkinsMetadata, JenkinsIntelligence


class TestJenkinsDataClasses(unittest.TestCase):
    """
    Test suite for Jenkins Intelligence data classes

    CRITICAL TESTING GOALS:
    1. Validate JenkinsMetadata field integrity and constraints
    2. Test JenkinsIntelligence composition and validation
    3. Ensure proper serialization and deserialization
    4. Test field type validation and edge cases
    """

    def test_jenkins_metadata_field_validation(self):
        """
        CRITICAL: Test JenkinsMetadata field validation and constraints
        """
        # Valid metadata creation
        valid_metadata = JenkinsMetadata(
            build_url="https://jenkins.example.com/job/test/123/",
            job_name="test-pipeline",
            build_number=123,
            build_result="FAILURE",
            timestamp="2024-08-17T17:55:40Z",
            parameters={"CLUSTER_NAME": "test-cluster"},
            console_log_snippet="Error in test execution",
            artifacts=["results.xml", "console.log"],
            branch="release-2.9",
            commit_sha="abc123def456"
        )

        # Test field access
        self.assertEqual(valid_metadata.build_url, "https://jenkins.example.com/job/test/123/")
        self.assertEqual(valid_metadata.job_name, "test-pipeline")
        self.assertEqual(valid_metadata.build_number, 123)
        self.assertEqual(valid_metadata.build_result, "FAILURE")
        self.assertIsInstance(valid_metadata.parameters, dict)
        self.assertIsInstance(valid_metadata.artifacts, list)

        # Test optional fields
        self.assertEqual(valid_metadata.branch, "release-2.9")
        self.assertEqual(valid_metadata.commit_sha, "abc123def456")

        # Test with None optional fields
        minimal_metadata = JenkinsMetadata(
            build_url="https://jenkins.example.com/job/test/123/",
            job_name="test-pipeline",
            build_number=123,
            build_result="SUCCESS",
            timestamp="2024-08-17T17:55:40Z",
            parameters={},
            console_log_snippet="",
            artifacts=[]
        )

        self.assertIsNone(minimal_metadata.branch)
        self.assertIsNone(minimal_metadata.commit_sha)
        self.assertEqual(minimal_metadata.parameters, {})
        self.assertEqual(minimal_metadata.artifacts, [])

    def test_jenkins_metadata_serialization(self):
        """
        CRITICAL: Test JenkinsMetadata serialization integrity
        """
        metadata = JenkinsMetadata(
            build_url="https://jenkins.example.com/job/test/123/",
            job_name="test-pipeline",
            build_number=123,
            build_result="FAILURE",
            timestamp="2024-08-17T17:55:40Z",
            parameters={"CLUSTER_NAME": "test-cluster", "BRANCH": "main"},
            console_log_snippet="Test failure occurred",
            artifacts=["results.xml"],
            branch="main",
            commit_sha="abcdef123456"
        )

        # Test asdict conversion
        metadata_dict = asdict(metadata)

        # Validate all fields present
        expected_fields = {
            'build_url', 'job_name', 'build_number', 'build_result',
            'timestamp', 'parameters', 'console_log_snippet', 'artifacts',
            'branch', 'commit_sha'
        }
        self.assertEqual(set(metadata_dict.keys()), expected_fields)

        # Validate data types preserved
        self.assertIsInstance(metadata_dict['build_number'], int)
        self.assertIsInstance(metadata_dict['parameters'], dict)
        self.assertIsInstance(metadata_dict['artifacts'], list)

    def test_jenkins_intelligence_composition(self):
        """
        CRITICAL: Test JenkinsIntelligence composite structure
        """
        metadata = JenkinsMetadata(
            build_url="https://jenkins.example.com/job/test/123/",
            job_name="test-pipeline",
            build_number=123,
            build_result="FAILURE",
            timestamp="2024-08-17T17:55:40Z",
            parameters={},
            console_log_snippet="",
            artifacts=[]
        )

        intelligence = JenkinsIntelligence(
            metadata=metadata,
            failure_analysis={'total_failures': 3, 'primary_failure_type': 'timeout'},
            environment_info={'cluster_name': 'test-cluster'},
            evidence_sources=["[Jenkins:test:123:FAILURE]"],
            confidence_score=0.85
        )

        # Test composition integrity
        self.assertIsInstance(intelligence.metadata, JenkinsMetadata)
        self.assertEqual(intelligence.metadata.job_name, "test-pipeline")
        self.assertIsInstance(intelligence.failure_analysis, dict)
        self.assertIsInstance(intelligence.environment_info, dict)
        self.assertIsInstance(intelligence.evidence_sources, list)
        self.assertIsInstance(intelligence.confidence_score, float)

        # Test confidence score constraints
        self.assertGreaterEqual(intelligence.confidence_score, 0.0)
        self.assertLessEqual(intelligence.confidence_score, 1.0)


class TestDataClassEdgeCases(unittest.TestCase):
    """
    Test suite for data class edge cases and validation

    CRITICAL TESTING GOALS:
    1. Test data class behavior with extreme values
    2. Test Unicode and special character handling
    3. Test large data structure performance
    """

    def test_unicode_handling(self):
        """
        CRITICAL: Test Unicode and special character handling
        """
        # Test Unicode in Jenkins metadata
        unicode_metadata = JenkinsMetadata(
            build_url="https://jenkins.example.com/job/test/123/",
            job_name="test-pipeline-special",
            build_number=123,
            build_result="FAILURE",
            timestamp="2024-08-17T17:55:40Z",
            parameters={"CLUSTER_NAME": "test-cluster"},
            console_log_snippet="Error: test failure occurred",
            artifacts=["results.xml"]
        )

        # Test field access
        self.assertIn("test", unicode_metadata.build_url)
        self.assertIn("special", unicode_metadata.job_name)

        # Test serialization
        serialized = asdict(unicode_metadata)
        self.assertIsInstance(serialized, dict)

    def test_large_data_structures(self):
        """
        CRITICAL: Test behavior with large data structures
        """
        # Test large console log
        large_console_log = "Error line\n" * 10000  # ~100KB

        large_metadata = JenkinsMetadata(
            build_url="https://jenkins.example.com/job/test/123/",
            job_name="test-pipeline",
            build_number=123,
            build_result="FAILURE",
            timestamp="2024-08-17T17:55:40Z",
            parameters={"CLUSTER_NAME": "test"},
            console_log_snippet=large_console_log,
            artifacts=[f"artifact_{i}.xml" for i in range(100)]  # 100 artifacts
        )

        # Test large data handling
        self.assertEqual(len(large_metadata.console_log_snippet), len(large_console_log))
        self.assertEqual(len(large_metadata.artifacts), 100)

        # Test serialization performance
        start_time = time.time()
        serialized = asdict(large_metadata)
        serialization_time = time.time() - start_time

        # Should complete within reasonable time (< 1 second)
        self.assertLess(serialization_time, 1.0)
        self.assertIsInstance(serialized, dict)

    def test_extreme_values(self):
        """
        CRITICAL: Test data classes with extreme values
        """
        # Test extreme build numbers
        extreme_metadata = JenkinsMetadata(
            build_url="https://jenkins.example.com/job/test/999999999/",
            job_name="test",
            build_number=999999999,  # Very large build number
            build_result="SUCCESS",
            timestamp="2024-08-17T17:55:40Z",
            parameters={},
            console_log_snippet="",
            artifacts=[]
        )

        self.assertEqual(extreme_metadata.build_number, 999999999)
        self.assertIsInstance(extreme_metadata.build_number, int)


if __name__ == '__main__':
    # Set up test discovery and execution
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    # Add all test classes
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestJenkinsDataClasses))
    test_suite.addTests(test_loader.loadTestsFromTestCase(TestDataClassEdgeCases))

    # Run tests with detailed output
    test_runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = test_runner.run(test_suite)

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
