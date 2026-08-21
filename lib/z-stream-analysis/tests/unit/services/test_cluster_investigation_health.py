#!/usr/bin/env python3
"""Tests for per-feature-area health scoring (GAP-04)."""

import pytest
from unittest.mock import patch, MagicMock
from src.services.cluster_investigation_service import (
    ClusterInvestigationService,
    ClusterLandscape,
    ComponentDiagnostics,
    PodDiagnostics,
    FeatureAreaHealth,
    FEATURE_AREA_SUBSYSTEM_MAP,
)


class TestFeatureAreaHealth:
    """Tests for get_feature_area_health."""

    def setup_method(self):
        self.service = ClusterInvestigationService()

    def _mock_diagnose(self, status='Available', restart_count=0):
        """Create a mock ComponentDiagnostics."""
        pod = PodDiagnostics(
            name='test-pod', namespace='test', status='Running',
            restart_count=restart_count, ready=(status == 'Available'),
        )
        return ComponentDiagnostics(
            component_name='test-comp', subsystem='Test',
            deployment_status=status,
            desired_replicas=1, ready_replicas=1 if status == 'Available' else 0,
            pods=[pod],
        )

    @patch.object(ClusterInvestigationService, 'diagnose_component')
    def test_all_healthy(self, mock_diag):
        """All components healthy = score 1.0."""
        mock_diag.return_value = self._mock_diagnose('Available', 0)
        health = self.service.get_feature_area_health('Search')
        assert health.health_score >= 0.9
        assert health.infrastructure_signal == 'none'
        assert health.healthy_components > 0
        assert len(health.unhealthy_components) == 0

    @patch.object(ClusterInvestigationService, 'diagnose_component')
    def test_all_unhealthy(self, mock_diag):
        """All components unhealthy = low score."""
        mock_diag.return_value = self._mock_diagnose('Unavailable', 0)
        health = self.service.get_feature_area_health('Search')
        assert health.health_score < 0.3
        assert health.infrastructure_signal == 'definitive'

    @patch.object(ClusterInvestigationService, 'diagnose_component')
    def test_degraded_component(self, mock_diag):
        """Degraded component reduces score."""
        mock_diag.return_value = self._mock_diagnose('Degraded', 5)
        health = self.service.get_feature_area_health('Search')
        assert 0.0 <= health.health_score <= 1.0
        assert len(health.degraded_components) > 0

    @patch.object(ClusterInvestigationService, 'diagnose_component')
    def test_high_restart_count_penalty(self, mock_diag):
        """High restart count applies penalty."""
        mock_diag.return_value = self._mock_diagnose('Available', 15)
        health = self.service.get_feature_area_health('Search')
        # Should be < 1.0 due to restart penalty
        assert health.health_score < 1.0
        assert health.total_restart_count > 0

    @patch.object(ClusterInvestigationService, 'diagnose_component')
    def test_operator_degraded_penalty(self, mock_diag):
        """Degraded operator applies penalty."""
        mock_diag.return_value = self._mock_diagnose('Available', 0)
        landscape = ClusterLandscape(degraded_operators=['search-api'])
        health = self.service.get_feature_area_health('Search', landscape)
        assert health.has_operator_degraded is True
        assert health.health_score < 1.0

    def test_unknown_feature_area(self):
        """Unknown feature area returns healthy default."""
        health = self.service.get_feature_area_health('NonexistentArea')
        assert health.health_score == 1.0
        assert health.total_components == 0

    @patch.object(ClusterInvestigationService, 'diagnose_component')
    @patch.object(ClusterInvestigationService, 'get_cluster_landscape')
    def test_get_all_feature_area_health(self, mock_landscape, mock_diag):
        """Test batch health check for multiple areas."""
        mock_landscape.return_value = ClusterLandscape()
        mock_diag.return_value = self._mock_diagnose('Available', 0)
        results = self.service.get_all_feature_area_health(['Search', 'GRC'])
        assert 'Search' in results
        assert 'GRC' in results
        assert isinstance(results['Search'], FeatureAreaHealth)


class TestScoreToSignal:
    """Tests for _score_to_signal graduated bands."""

    def test_definitive(self):
        assert ClusterInvestigationService._score_to_signal(0.1) == 'definitive'
        assert ClusterInvestigationService._score_to_signal(0.29) == 'definitive'

    def test_strong(self):
        assert ClusterInvestigationService._score_to_signal(0.3) == 'strong'
        assert ClusterInvestigationService._score_to_signal(0.49) == 'strong'

    def test_moderate(self):
        assert ClusterInvestigationService._score_to_signal(0.5) == 'moderate'
        assert ClusterInvestigationService._score_to_signal(0.69) == 'moderate'

    def test_none(self):
        assert ClusterInvestigationService._score_to_signal(0.7) == 'none'
        assert ClusterInvestigationService._score_to_signal(1.0) == 'none'


class TestFeatureAreaSubsystemMap:
    """Tests for feature area to subsystem mapping."""

    def test_all_feature_areas_mapped(self):
        """All known feature areas should have a subsystem mapping."""
        expected_areas = ['GRC', 'Search', 'CLC', 'Observability', 'Virtualization',
                          'Application', 'Console', 'Infrastructure', 'RBAC', 'Automation']
        for area in expected_areas:
            assert area in FEATURE_AREA_SUBSYSTEM_MAP, f"Missing mapping for {area}"
