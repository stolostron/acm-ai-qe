#!/usr/bin/env python3
"""Tests for external service failure detection patterns."""

import pytest
from src.services.jenkins_intelligence_service import JenkinsIntelligenceService


class TestExternalServiceFailureType:
    """Tests for _classify_failure_type with external service patterns."""

    def setup_method(self):
        self.service = JenkinsIntelligenceService.__new__(JenkinsIntelligenceService)
        import logging
        self.service.logger = logging.getLogger(__name__)

    def test_minio_service_failure(self):
        result = self.service._classify_failure_type(
            "minio server unavailable for objectstore"
        )
        assert result == 'external_service'

    def test_objectstore_failure(self):
        result = self.service._classify_failure_type(
            "objectstore endpoint returned error"
        )
        assert result == 'external_service'

    def test_gogs_server_failure(self):
        result = self.service._classify_failure_type(
            "gogs server is down"
        )
        assert result == 'external_service'

    def test_minio_with_generic_keyword_matches_earlier(self):
        """When error text contains both 'minio' and 'connection refused',
        'network' matches first in the elif chain. This is correct --
        the console log pattern extractor catches minio-specific signals."""
        result = self.service._classify_failure_type(
            "minio connection refused on objectstore endpoint"
        )
        assert result == 'network'

    def test_testrepo_push_failure(self):
        result = self.service._classify_failure_type(
            "failed to push to testrepo Git repository"
        )
        assert result == 'external_service'

    def test_ssl_certificate_problem(self):
        result = self.service._classify_failure_type(
            "SSL certificate problem: unable to get local issuer certificate"
        )
        assert result == 'external_service'

    def test_mtls_setup_failure(self):
        result = self.service._classify_failure_type(
            "MTLS Test Environment setup failure or already operational"
        )
        assert result == 'external_service'

    def test_generic_network_not_matched(self):
        """Generic network errors should still classify as network, not external_service."""
        result = self.service._classify_failure_type(
            "network error: connection refused"
        )
        assert result == 'network'

    def test_generic_timeout_not_matched(self):
        """Generic timeouts should still classify as timeout, not external_service."""
        result = self.service._classify_failure_type(
            "timed out waiting for element"
        )
        assert result == 'timeout'

    def test_generic_element_not_matched(self):
        """Element errors should still classify correctly."""
        result = self.service._classify_failure_type(
            "element not found: button.submit"
        )
        assert result == 'element_not_found'


class TestExternalServiceConsoleLogPatterns:
    """Tests for _analyze_failure_patterns with external service issues."""

    def setup_method(self):
        self.service = JenkinsIntelligenceService.__new__(JenkinsIntelligenceService)
        import logging
        self.service.logger = logging.getLogger(__name__)

    def test_testrepo_push_detected(self):
        log = "ERROR: failed to push to testrepo Git repository"
        result = self.service._analyze_failure_patterns(log)
        assert len(result['patterns']['external_service_issues']) > 0

    def test_ssl_cert_detected(self):
        log = "SSL certificate problem: self signed certificate in certificate chain"
        result = self.service._analyze_failure_patterns(log)
        assert len(result['patterns']['external_service_issues']) > 0

    def test_mtls_setup_detected(self):
        log = "MTLS Test Environment setup failure or already operational"
        result = self.service._analyze_failure_patterns(log)
        assert len(result['patterns']['external_service_issues']) > 0

    def test_minio_connection_detected(self):
        log = "minio connection refused on bucket endpoint"
        result = self.service._analyze_failure_patterns(log)
        assert len(result['patterns']['external_service_issues']) > 0

    def test_gogs_failure_detected(self):
        log = "gogs server connection refused during test setup"
        result = self.service._analyze_failure_patterns(log)
        assert len(result['patterns']['external_service_issues']) > 0

    def test_tower_unreachable_detected(self):
        log = "tower connection refused on port 443"
        result = self.service._analyze_failure_patterns(log)
        assert len(result['patterns']['external_service_issues']) > 0

    def test_no_external_service_for_normal_log(self):
        log = "element not found: button.submit"
        result = self.service._analyze_failure_patterns(log)
        assert len(result['patterns']['external_service_issues']) == 0

    def test_external_service_key_always_present(self):
        """The external_service_issues key should exist even with no matches."""
        log = "all tests passed"
        result = self.service._analyze_failure_patterns(log)
        assert 'external_service_issues' in result['patterns']
        assert len(result['patterns']['external_service_issues']) == 0
