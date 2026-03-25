#!/usr/bin/env python3
"""Tests for backend API probing (Step 4c)."""

import pytest
from unittest.mock import patch, MagicMock
from src.scripts.gather import DataGatherer


class TestProbeValidation:
    """Tests for individual probe validation logic."""

    def setup_method(self):
        with patch('src.scripts.gather.is_acm_ui_mcp_available', return_value=False):
            with patch('src.scripts.gather.is_knowledge_graph_available', return_value=False):
                self.gatherer = DataGatherer.__new__(DataGatherer)
                import logging
                self.gatherer.logger = logging.getLogger(__name__)
                self.gatherer.gathered_data = {}

    def test_probe_authenticated_healthy(self):
        """Healthy /authenticated returns no anomalies."""
        result = {
            'status': 200,
            'response_time_ms': 45,
            'response': None,
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_authenticated(
                'oc', [], 'pod', 'ns', 'token'
            )
        assert probe['response_valid'] is True
        assert len([a for a in probe['anomalies'] if a.get('is_anomaly', True)]) == 0

    def test_probe_authenticated_slow(self):
        """Slow /authenticated flags anomaly."""
        result = {
            'status': 200,
            'response_time_ms': 6000,
            'response': None,
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_authenticated(
                'oc', [], 'pod', 'ns', 'token'
            )
        assert probe['response_valid'] is False
        assert any('slow' in a.get('description', '').lower() for a in probe['anomalies'])

    def test_probe_authenticated_timeout(self):
        """Timeout on /authenticated flags anomaly."""
        result = {
            'status': 'timeout',
            'error': 'timed out',
            'response': None,
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_authenticated(
                'oc', [], 'pod', 'ns', 'token'
            )
        assert probe['response_valid'] is False

    def test_probe_hub_healthy(self):
        """Healthy /hub with correct name returns no anomalies."""
        result = {
            'status': 200,
            'response_time_ms': 30,
            'response': {
                'isGlobalHub': False,
                'localHubName': 'local-cluster',
                'isHubSelfManaged': True,
                'isObservabilityInstalled': True,
            },
        }
        landscape = {
            'multiclusterhub_status': 'Running',
            'managed_cluster_count': 3,
            'managed_cluster_statuses': {'Ready': 3},
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_hub(
                'oc', [], 'pod', 'ns', 'token', landscape
            )
        assert probe['response_valid'] is True

    def test_probe_hub_wrong_name(self):
        """Hub name with unexpected suffix flags anomaly."""
        result = {
            'status': 200,
            'response_time_ms': 30,
            'response': {
                'localHubName': 'local-cluster-replica',
                'isHubSelfManaged': False,
            },
        }
        landscape = {'multiclusterhub_status': 'Running', 'managed_cluster_count': 1}
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_hub(
                'oc', [], 'pod', 'ns', 'token', landscape
            )
        assert probe['response_valid'] is False
        assert any('suffix' in a.get('description', '').lower() for a in probe['anomalies'])

    def test_probe_username_correct(self):
        """Correct kube:admin username returns no anomalies."""
        result = {
            'status': 200,
            'response_time_ms': 20,
            'response': {'statusCode': 201, 'body': {'username': 'kube:admin'}},
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_username(
                'oc', [], 'pod', 'ns', 'token'
            )
        assert probe['response_valid'] is True

    def test_probe_username_reversed(self):
        """Reversed admin:kube username flags anomaly."""
        result = {
            'status': 200,
            'response_time_ms': 20,
            'response': {'statusCode': 201, 'body': {'username': 'admin:kube'}},
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_username(
                'oc', [], 'pod', 'ns', 'token'
            )
        assert probe['response_valid'] is False
        assert any('reversed' in a.get('description', '').lower() for a in probe['anomalies'])

    def test_probe_ansibletower_skipped_no_tower(self):
        """Ansible probe skipped when no tower host in Jenkins params."""
        self.gatherer.gathered_data = {'jenkins': {'parameters': {}}}
        probe = self.gatherer._probe_ansibletower(
            'oc', [], 'pod', 'ns', 'token', {}
        )
        assert probe['status'] == 'skipped'
        assert probe.get('response_valid') is None

    def test_probe_ansibletower_empty_results(self):
        """Empty ansible results with configured tower flags anomaly."""
        self.gatherer.gathered_data = {
            'jenkins': {'parameters': {'TOWER_HOST': 'https://tower.example.com'}}
        }
        result = {
            'status': 200,
            'response_time_ms': 100,
            'response': {'count': 0, 'results': []},
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_ansibletower(
                'oc', [], 'pod', 'ns', 'token', {}
            )
        assert probe['response_valid'] is False
        assert any('empty' in a.get('description', '').lower() for a in probe['anomalies'])

    def test_probe_ansibletower_with_results(self):
        """Non-empty ansible results returns no anomalies."""
        self.gatherer.gathered_data = {
            'jenkins': {'parameters': {'TOWER_HOST': 'https://tower.example.com'}}
        }
        result = {
            'status': 200,
            'response_time_ms': 100,
            'response': {'count': 2, 'results': [{'name': 'template1'}, {'name': 'template2'}]},
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_ansibletower(
                'oc', [], 'pod', 'ns', 'token', {}
            )
        assert probe['response_valid'] is True

    def test_probe_search_healthy(self):
        """Search API returning pods returns no anomalies."""
        result = {
            'status': 200,
            'response_time_ms': 500,
            'response': {
                'data': {
                    'searchResult': [{'items': [{'name': 'pod-1'}, {'name': 'pod-2'}]}]
                }
            },
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_search(
                'oc', [], 'pod', 'ns', 'token'
            )
        assert probe['response_valid'] is True

    def test_probe_search_empty_items(self):
        """Search API returning empty items flags anomaly."""
        result = {
            'status': 200,
            'response_time_ms': 500,
            'response': {
                'data': {'searchResult': [{'items': []}]}
            },
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_search(
                'oc', [], 'pod', 'ns', 'token'
            )
        assert probe['response_valid'] is False

    def test_probe_search_timeout(self):
        """Search API timeout flags anomaly."""
        result = {
            'status': 'timeout',
            'error': 'curl timed out after 20s',
            'response': None,
            'response_time_ms': 20000,
        }
        with patch.object(self.gatherer, '_exec_curl_in_pod', return_value=result):
            probe = self.gatherer._probe_search(
                'oc', [], 'pod', 'ns', 'token'
            )
        assert probe['response_valid'] is False


class TestProbeSkipping:
    """Tests for conditions where probes are skipped."""

    def setup_method(self):
        with patch('src.scripts.gather.is_acm_ui_mcp_available', return_value=False):
            with patch('src.scripts.gather.is_knowledge_graph_available', return_value=False):
                self.gatherer = DataGatherer.__new__(DataGatherer)
                import logging
                self.gatherer.logger = logging.getLogger(__name__)

    def test_skip_when_no_credentials(self):
        """Probes skipped when no cluster credentials."""
        self.gatherer.gathered_data = {
            'cluster_access': {'has_credentials': False}
        }
        self.gatherer._probe_backend_apis()
        probes = self.gatherer.gathered_data['backend_probes']
        assert probes['skipped'] is True
        assert probes['total_anomalies'] == 0

    @patch('subprocess.run')
    def test_skip_when_no_pod(self, mock_run):
        """Probes skipped when console pod not found."""
        mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='')
        self.gatherer.gathered_data = {
            'cluster_access': {'has_credentials': True}
        }
        self.gatherer.cluster_investigation_service = MagicMock()
        self.gatherer.cluster_investigation_service.cli = 'oc'
        self.gatherer.cluster_investigation_service.kubeconfig = None
        self.gatherer._probe_backend_apis()
        probes = self.gatherer.gathered_data['backend_probes']
        assert probes['skipped'] is True
        assert 'pod_not_found' in probes.get('reason', '')


class TestFeatureAreaProbeMapping:
    """Tests for the feature area to probe mapping."""

    def test_all_feature_areas_mapped(self):
        """All 10 feature areas should have a probe mapping."""
        expected = [
            'GRC', 'Search', 'CLC', 'Observability', 'Virtualization',
            'Application', 'Console', 'Infrastructure', 'RBAC', 'Automation',
        ]
        for area in expected:
            assert area in DataGatherer.FEATURE_AREA_PROBE_MAP, f"Missing probe mapping for {area}"

    def test_mapping_values_are_valid_probes(self):
        """All mapped probes should be valid endpoint names."""
        valid_probes = {'authenticated', 'hub', 'username', 'ansibletower', 'search'}
        for area, probe in DataGatherer.FEATURE_AREA_PROBE_MAP.items():
            assert probe in valid_probes, f"Area {area} maps to invalid probe '{probe}'"


class TestSourceOfTruthValidation:
    """Tests for source-of-truth cross-referencing (v3.4)."""

    def setup_method(self):
        with patch('src.scripts.gather.is_acm_ui_mcp_available', return_value=False):
            with patch('src.scripts.gather.is_knowledge_graph_available', return_value=False):
                self.gatherer = DataGatherer.__new__(DataGatherer)
                import logging
                self.gatherer.logger = logging.getLogger(__name__)
                self.gatherer.gathered_data = {}

    def test_username_mismatch_is_product_bug(self):
        """Reversed username with correct oc whoami -> PRODUCT_BUG."""
        probe = {
            'status': 200,
            'response': {'statusCode': 201, 'body': {'username': 'admin:kube'}},
            'anomalies': [{'field': 'username', 'is_anomaly': True}],
        }
        with patch.object(self.gatherer, '_run_oc_command', return_value='kube:admin'):
            self.gatherer._validate_username_probe('oc', [], probe)
        assert probe['anomaly_source'] == 'console_backend'
        assert probe['classification_hint'] == 'PRODUCT_BUG'
        assert probe['cluster_ground_truth']['username'] == 'kube:admin'

    def test_username_match_is_infrastructure(self):
        """Both return same anomalous value -> INFRASTRUCTURE."""
        probe = {
            'status': 200,
            'response': {'statusCode': 201, 'body': {'username': 'admin:kube'}},
            'anomalies': [{'field': 'username', 'is_anomaly': True}],
        }
        with patch.object(self.gatherer, '_run_oc_command', return_value='admin:kube'):
            self.gatherer._validate_username_probe('oc', [], probe)
        assert probe['anomaly_source'] == 'upstream'
        assert probe['classification_hint'] == 'INFRASTRUCTURE'

    def test_username_oc_fails_is_unknown(self):
        """oc whoami failure -> unknown source."""
        probe = {
            'status': 200,
            'response': {'statusCode': 201, 'body': {'username': 'admin:kube'}},
            'anomalies': [{'field': 'username', 'is_anomaly': True}],
        }
        with patch.object(self.gatherer, '_run_oc_command', return_value=None):
            self.gatherer._validate_username_probe('oc', [], probe)
        assert probe['anomaly_source'] == 'unknown'
        assert probe['classification_hint'] is None

    def test_hub_mismatch_is_product_bug(self):
        """Hub name differs between console and cluster -> PRODUCT_BUG."""
        probe = {
            'status': 200,
            'response': {'localHubName': 'local-cluster-replica'},
            'anomalies': [{'field': 'localHubName', 'is_anomaly': True}],
        }
        with patch.object(self.gatherer, '_run_oc_command', return_value='local-cluster'):
            self.gatherer._validate_hub_probe('oc', [], 'ns', probe)
        assert probe['anomaly_source'] == 'console_backend'
        assert probe['classification_hint'] == 'PRODUCT_BUG'

    def test_ansibletower_healthy_but_empty_is_product_bug(self):
        """AAP Succeeded but console returns empty -> PRODUCT_BUG."""
        probe = {
            'status': 200,
            'response': {'count': 0, 'results': []},
            'anomalies': [{'field': 'results', 'is_anomaly': True}],
        }
        csv_output = 'aap-operator.v2.5.0 Succeeded'
        with patch.object(self.gatherer, '_run_oc_command', return_value=csv_output):
            self.gatherer._validate_ansibletower_probe('oc', [], probe)
        assert probe['anomaly_source'] == 'console_backend'
        assert probe['classification_hint'] == 'PRODUCT_BUG'

    def test_ansibletower_not_installed_clears_anomaly(self):
        """AAP not installed -> anomaly cleared, INFRASTRUCTURE."""
        probe = {
            'status': 200,
            'response': {'count': 0, 'results': []},
            'anomalies': [{'field': 'results', 'is_anomaly': True,
                           'description': 'Ansible Tower returns empty'}],
        }
        with patch.object(self.gatherer, '_run_oc_command', return_value=''):
            self.gatherer._validate_ansibletower_probe('oc', [], probe)
        assert probe['anomaly_source'] == 'upstream'
        assert probe['classification_hint'] == 'INFRASTRUCTURE'
        # Anomaly should be cleared since empty is expected
        assert probe['anomalies'][0]['is_anomaly'] is False

    def test_search_pods_healthy_but_empty_is_product_bug(self):
        """Search pods running but console returns empty -> PRODUCT_BUG."""
        probe = {
            'status': 200,
            'response': {'data': {'searchResult': [{'items': []}]}},
            'anomalies': [{'field': 'items', 'is_anomaly': True}],
        }
        with patch.object(self.gatherer, '_run_oc_command', return_value='1'):
            self.gatherer._validate_search_probe('oc', [], 'ns', probe)
        assert probe['anomaly_source'] == 'console_backend'
        assert probe['classification_hint'] == 'PRODUCT_BUG'

    def test_search_pods_down_is_infrastructure(self):
        """Search pods not running -> INFRASTRUCTURE."""
        probe = {
            'status': 200,
            'response': {'data': {'searchResult': [{'items': []}]}},
            'anomalies': [{'field': 'items', 'is_anomaly': True}],
        }
        with patch.object(self.gatherer, '_run_oc_command', return_value='0'):
            self.gatherer._validate_search_probe('oc', [], 'ns', probe)
        assert probe['anomaly_source'] == 'upstream'
        assert probe['classification_hint'] == 'INFRASTRUCTURE'

    def test_no_validation_when_no_anomalies(self):
        """Probes without anomalies are not validated."""
        probes_result = {
            'username': {'anomalies': [], 'response_valid': True},
            'hub': {'anomalies': [{'is_anomaly': False}], 'response_valid': True},
            'ansibletower': {'anomalies': [], 'response_valid': True},
            'authenticated': {'anomalies': [], 'response_valid': True},
            'search': {'anomalies': [], 'response_valid': True},
        }
        with patch.object(self.gatherer, '_run_oc_command') as mock_oc:
            self.gatherer._validate_probes_against_cluster(
                'oc', [], 'ns', probes_result
            )
        # No oc commands should have been called
        mock_oc.assert_not_called()

    def test_authenticated_cluster_works_is_product_bug(self):
        """Cluster auth works but console auth fails -> PRODUCT_BUG."""
        probe = {
            'status': 'timeout',
            'anomalies': [{'field': 'response', 'is_anomaly': True}],
        }
        with patch.object(self.gatherer, '_run_oc_command', return_value='kube:admin'):
            self.gatherer._validate_authenticated_probe('oc', [], probe)
        assert probe['anomaly_source'] == 'console_backend'
        assert probe['classification_hint'] == 'PRODUCT_BUG'
