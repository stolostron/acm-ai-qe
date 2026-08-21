"""
Unit tests for ClusterInvestigationService.

Tests cluster landscape, component diagnostics, and resource pressure
using mocked subprocess.run output.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from src.services.cluster_investigation_service import (
    ClusterInvestigationService,
    ClusterLandscape,
    PodDiagnostics,
    ComponentDiagnostics,
    COMPONENT_NAMESPACE_MAP,
    SUBSYSTEM_COMPONENTS,
)


def mock_run(returncode=0, stdout='', stderr=''):
    """Create a mock subprocess.run result."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TestClusterInvestigationServiceInit:
    """Test initialization and command safety."""

    def test_default_init(self):
        service = ClusterInvestigationService()
        assert service.cli == 'oc'
        assert service.kubeconfig is None

    def test_custom_init(self):
        service = ClusterInvestigationService(
            kubeconfig_path='/tmp/kube', cli='kubectl'
        )
        assert service.cli == 'kubectl'
        assert service.kubeconfig == '/tmp/kube'

    def test_readonly_validation_blocks_delete(self):
        service = ClusterInvestigationService()
        assert service._validate_readonly(['delete', 'pod', 'foo']) is False

    def test_readonly_validation_blocks_apply(self):
        service = ClusterInvestigationService()
        assert service._validate_readonly(['apply', '-f', 'foo.yaml']) is False

    def test_readonly_validation_allows_get(self):
        service = ClusterInvestigationService()
        assert service._validate_readonly(['get', 'pods']) is True

    def test_readonly_validation_allows_describe(self):
        service = ClusterInvestigationService()
        assert service._validate_readonly(['describe', 'pod', 'foo']) is True

    def test_readonly_validation_allows_logs(self):
        service = ClusterInvestigationService()
        assert service._validate_readonly(['logs', 'pod-1', '-n', 'ns']) is True

    def test_readonly_validation_allows_adm_top(self):
        service = ClusterInvestigationService()
        assert service._validate_readonly(['adm', 'top', 'nodes']) is True

    def test_readonly_validation_blocks_adm_other(self):
        service = ClusterInvestigationService()
        assert service._validate_readonly(['adm', 'drain', 'node-1']) is False


class TestGetClusterLandscape:
    """Test cluster landscape collection."""

    def setup_method(self):
        self.service = ClusterInvestigationService()

    @patch('subprocess.run')
    def test_healthy_cluster(self, mock_subprocess):
        managed_clusters = {
            'items': [
                {
                    'metadata': {'name': 'cluster1'},
                    'status': {'conditions': [
                        {'type': 'ManagedClusterConditionAvailable', 'status': 'True'}
                    ]}
                },
                {
                    'metadata': {'name': 'cluster2'},
                    'status': {'conditions': [
                        {'type': 'ManagedClusterConditionAvailable', 'status': 'True'}
                    ]}
                }
            ]
        }

        operators = {
            'items': [
                {
                    'metadata': {'name': 'authentication'},
                    'status': {'conditions': [
                        {'type': 'Available', 'status': 'True'},
                        {'type': 'Degraded', 'status': 'False'},
                    ]}
                }
            ]
        }

        nodes = {
            'items': [
                {
                    'status': {'conditions': [
                        {'type': 'MemoryPressure', 'status': 'False'},
                        {'type': 'DiskPressure', 'status': 'False'},
                        {'type': 'PIDPressure', 'status': 'False'},
                    ]}
                }
            ]
        }

        def side_effect(cmd, **kwargs):
            cmd_str = ' '.join(cmd)
            if 'managedclusters' in cmd_str:
                return mock_run(stdout=json.dumps(managed_clusters))
            elif 'clusteroperators' in cmd_str:
                return mock_run(stdout=json.dumps(operators))
            elif 'get nodes' in cmd_str:
                return mock_run(stdout=json.dumps(nodes))
            elif 'adm top' in cmd_str:
                return mock_run(stdout='node1  500m  25%  2Gi  40%')
            elif 'policies' in cmd_str:
                return mock_run(stdout='ns1  policy1\nns2  policy2\n')
            elif 'multiclusterhub' in cmd_str:
                mch = {'items': [{'status': {'phase': 'Running'}}]}
                return mock_run(stdout=json.dumps(mch))
            return mock_run(returncode=1)

        mock_subprocess.side_effect = side_effect

        landscape = self.service.get_cluster_landscape()

        assert landscape.managed_cluster_count == 2
        assert landscape.managed_cluster_statuses.get('Ready') == 2
        assert 'authentication' in landscape.operator_statuses
        assert landscape.operator_statuses['authentication'] == 'Available'
        assert len(landscape.degraded_operators) == 0
        assert landscape.resource_pressure['memory'] is False
        assert landscape.policy_count == 2
        assert landscape.multiclusterhub_status == 'Running'

    @patch('subprocess.run')
    def test_degraded_cluster(self, mock_subprocess):
        operators = {
            'items': [
                {
                    'metadata': {'name': 'network'},
                    'status': {'conditions': [
                        {'type': 'Available', 'status': 'True'},
                        {'type': 'Degraded', 'status': 'True'},
                    ]}
                }
            ]
        }

        nodes = {
            'items': [
                {
                    'status': {'conditions': [
                        {'type': 'MemoryPressure', 'status': 'True'},
                        {'type': 'DiskPressure', 'status': 'False'},
                    ]}
                }
            ]
        }

        def side_effect(cmd, **kwargs):
            cmd_str = ' '.join(cmd)
            if 'managedclusters' in cmd_str:
                return mock_run(stdout='{"items": []}')
            elif 'clusteroperators' in cmd_str:
                return mock_run(stdout=json.dumps(operators))
            elif 'get nodes' in cmd_str:
                return mock_run(stdout=json.dumps(nodes))
            elif 'adm top' in cmd_str:
                return mock_run(stdout='node1  900m  95%  6Gi  80%')
            elif 'policies' in cmd_str:
                return mock_run(returncode=1)
            elif 'multiclusterhub' in cmd_str:
                return mock_run(returncode=1)
            return mock_run(returncode=1)

        mock_subprocess.side_effect = side_effect

        landscape = self.service.get_cluster_landscape()

        assert 'network' in landscape.degraded_operators
        assert landscape.operator_statuses['network'] == 'Degraded'
        assert landscape.resource_pressure['memory'] is True
        assert landscape.resource_pressure['cpu'] is True

    @patch('subprocess.run')
    def test_disconnected_cluster(self, mock_subprocess):
        mock_subprocess.return_value = mock_run(returncode=1, stderr='connection refused')

        landscape = self.service.get_cluster_landscape()

        assert landscape.managed_cluster_count == 0
        assert len(landscape.operator_statuses) == 0


class TestDiagnoseComponent:
    """Test component-level diagnostics."""

    def setup_method(self):
        self.service = ClusterInvestigationService()

    @patch('subprocess.run')
    def test_healthy_component(self, mock_subprocess):
        pods_json = {
            'items': [{
                'metadata': {'name': 'search-api-abc123'},
                'status': {
                    'phase': 'Running',
                    'containerStatuses': [{
                        'ready': True,
                        'restartCount': 0,
                        'state': {'running': {}}
                    }]
                }
            }]
        }

        def side_effect(cmd, **kwargs):
            cmd_str = ' '.join(cmd)
            if 'get pods' in cmd_str and '-l' in cmd_str:
                return mock_run(stdout=json.dumps(pods_json))
            elif 'get events' in cmd_str:
                return mock_run(stdout='')
            elif 'logs' in cmd_str:
                return mock_run(stdout='INFO: healthy')
            return mock_run(returncode=1)

        mock_subprocess.side_effect = side_effect

        diag = self.service.diagnose_component('search-api')

        assert diag.component_name == 'search-api'
        assert diag.subsystem == 'Search'
        assert diag.deployment_status == 'Available'
        assert diag.ready_replicas == 1
        assert len(diag.pods) == 1
        assert diag.pods[0].status == 'Running'
        assert diag.pods[0].restart_count == 0

    @patch('subprocess.run')
    def test_crashloopbackoff_component(self, mock_subprocess):
        pods_json = {
            'items': [{
                'metadata': {'name': 'search-api-def456'},
                'status': {
                    'phase': 'Running',
                    'containerStatuses': [{
                        'ready': False,
                        'restartCount': 15,
                        'state': {
                            'waiting': {'reason': 'CrashLoopBackOff'}
                        }
                    }]
                }
            }]
        }

        def side_effect(cmd, **kwargs):
            cmd_str = ' '.join(cmd)
            if 'get pods' in cmd_str and '-l' in cmd_str:
                return mock_run(stdout=json.dumps(pods_json))
            elif 'get events' in cmd_str:
                return mock_run(stdout='Warning  BackOff  pod crashed')
            elif 'logs' in cmd_str:
                return mock_run(stdout='ERROR: index not available')
            return mock_run(returncode=1)

        mock_subprocess.side_effect = side_effect

        diag = self.service.diagnose_component('search-api')

        assert diag.deployment_status == 'Unavailable'
        assert diag.ready_replicas == 0
        assert diag.pods[0].status == 'CrashLoopBackOff'
        assert diag.pods[0].restart_count == 15
        assert diag.pods[0].ready is False

    @patch('subprocess.run')
    def test_missing_component(self, mock_subprocess):
        def side_effect(cmd, **kwargs):
            cmd_str = ' '.join(cmd)
            if 'get pods' in cmd_str:
                return mock_run(stdout='{"items": []}')
            return mock_run(returncode=1)

        mock_subprocess.side_effect = side_effect

        diag = self.service.diagnose_component('nonexistent-component')

        assert diag.deployment_status == 'Missing'
        assert len(diag.pods) == 0


class TestDiagnoseSubsystem:
    """Test subsystem-level diagnostics."""

    def setup_method(self):
        self.service = ClusterInvestigationService()

    @patch('subprocess.run')
    def test_search_subsystem(self, mock_subprocess):
        def side_effect(cmd, **kwargs):
            cmd_str = ' '.join(cmd)
            if 'get pods' in cmd_str:
                return mock_run(stdout='{"items": []}')
            return mock_run(returncode=1)

        mock_subprocess.side_effect = side_effect

        results = self.service.diagnose_subsystem('Search')

        assert len(results) == len(SUBSYSTEM_COMPONENTS['Search'])
        for diag in results:
            assert diag.subsystem == 'Search'

    def test_unknown_subsystem(self):
        results = self.service.diagnose_subsystem('NonExistent')
        assert results == []


class TestResourcePressure:
    """Test resource pressure detection."""

    def setup_method(self):
        self.service = ClusterInvestigationService()

    @patch('subprocess.run')
    def test_no_pressure(self, mock_subprocess):
        nodes = {
            'items': [{
                'status': {'conditions': [
                    {'type': 'MemoryPressure', 'status': 'False'},
                    {'type': 'DiskPressure', 'status': 'False'},
                    {'type': 'PIDPressure', 'status': 'False'},
                ]}
            }]
        }

        def side_effect(cmd, **kwargs):
            cmd_str = ' '.join(cmd)
            if 'get nodes' in cmd_str:
                return mock_run(stdout=json.dumps(nodes))
            elif 'adm top' in cmd_str:
                return mock_run(stdout='node1  500m  25%  2Gi  40%')
            return mock_run(returncode=1)

        mock_subprocess.side_effect = side_effect

        pressure = self.service.get_resource_pressure()
        assert pressure['memory'] is False
        assert pressure['disk'] is False
        assert pressure['cpu'] is False


class TestComponentNamespaceMap:
    """Test the component namespace map completeness."""

    def test_search_components_mapped(self):
        assert 'search-api' in COMPONENT_NAMESPACE_MAP
        assert 'search-collector' in COMPONENT_NAMESPACE_MAP

    def test_governance_components_mapped(self):
        assert 'grc-policy-propagator' in COMPONENT_NAMESPACE_MAP
        assert 'config-policy-controller' in COMPONENT_NAMESPACE_MAP

    def test_all_subsystems_have_components(self):
        for subsystem, components in SUBSYSTEM_COMPONENTS.items():
            assert len(components) > 0, f"Subsystem '{subsystem}' has no components"


class TestSerialization:
    """Test dataclass serialization."""

    def test_cluster_landscape_to_dict(self):
        service = ClusterInvestigationService()
        landscape = ClusterLandscape(
            managed_cluster_count=3,
            managed_cluster_statuses={'Ready': 2, 'NotReady': 1},
        )
        d = service.to_dict(landscape)
        assert d['managed_cluster_count'] == 3
        assert d['managed_cluster_statuses']['Ready'] == 2

    def test_component_diagnostics_to_dict(self):
        service = ClusterInvestigationService()
        diag = ComponentDiagnostics(
            component_name='search-api',
            subsystem='Search',
            deployment_status='Available',
            pods=[PodDiagnostics(
                name='search-api-1',
                namespace='open-cluster-management',
                status='Running',
            )]
        )
        d = service.to_dict(diag)
        assert d['component_name'] == 'search-api'
        assert len(d['pods']) == 1
        assert d['pods'][0]['status'] == 'Running'
