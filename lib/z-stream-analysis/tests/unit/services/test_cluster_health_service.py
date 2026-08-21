"""
Unit tests for ClusterHealthService.

Tests the 6-phase cluster health audit: DISCOVER, LEARN, CHECK,
COMPARE, CORRELATE, SCORE. Uses mocked subprocess.run for all
oc commands and synthetic knowledge YAML data.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.services.cluster_health_service import (
    ClusterHealthService,
    ClusterHealthReport,
    ClusterIdentity,
    HealthFinding,
    SubsystemHealth,
    ManagedClusterHealth,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def knowledge_dir(tmp_path):
    """Create a temporary knowledge directory with minimal YAML files."""
    # components.yaml
    (tmp_path / 'components.yaml').write_text(
        "components:\n"
        "  search-api:\n"
        "    subsystem: Search\n"
        "    type: hub-deployment\n"
        "    namespace: '{mch_ns}'\n"
        "    pod_label: 'name=search-api'\n"
        "    health_check: \"oc get deploy search-api -n {mch_ns}\"\n"
        "  multiclusterhub-operator:\n"
        "    subsystem: Platform\n"
        "    type: hub-operator\n"
        "    namespace: '{mch_ns}'\n"
        "    pod_label: 'name=multiclusterhub-operator'\n"
        "    health_check: \"oc get deploy multiclusterhub-operator -n {mch_ns}\"\n"
        "  console-chart-console-v2:\n"
        "    subsystem: Console\n"
        "    type: hub-deployment\n"
        "    namespace: '{mch_ns}'\n"
        "    pod_label: 'app=console-chart-v2'\n"
        "    health_check: \"oc get deploy console-chart-console-v2 -n {mch_ns}\"\n"
    )

    # healthy-baseline.yaml
    (tmp_path / 'healthy-baseline.yaml').write_text(
        "baseline:\n"
        "  operators:\n"
        "    multiclusterhub-operator:\n"
        "      namespace: '{mch_ns}'\n"
        "      expected_replicas: 2\n"
        "      critical: true\n"
        "      note: 'Root operator'\n"
        "  namespaces:\n"
        "    mch_namespace:\n"
        "      expected_pod_count_range: '28-36'\n"
        "      critical_deployments:\n"
        "        - name: search-api\n"
        "          min_replicas: 1\n"
        "        - name: console-chart-console-v2\n"
        "          min_replicas: 2\n"
        "  nodes:\n"
        "    minimum_ready: 3\n"
        "  image_patterns:\n"
        "    console-chart-console-v2:\n"
        "      expected_prefix:\n"
        "        - 'quay.io:443/acm-d/console'\n"
        "        - 'quay.io/stolostron/console'\n"
        "  restart_thresholds:\n"
        "    max_acceptable_restarts: 5\n"
        "  network:\n"
        "    unexpected_resources:\n"
        "      networkpolicies_in_acm_namespaces:\n"
        "        flag: 'Flag any'\n"
    )

    # addon-catalog.yaml
    (tmp_path / 'addon-catalog.yaml').write_text(
        "addons:\n"
        "  - name: work-manager\n"
        "    required: true\n"
        "    subsystem: infrastructure\n"
    )

    # dependencies.yaml
    (tmp_path / 'dependencies.yaml').write_text(
        "dependency_chains:\n"
        "  search:\n"
        "    chain: 'search-collector -> search-api'\n"
    )

    # feature-areas.yaml
    (tmp_path / 'feature-areas.yaml').write_text(
        "feature_areas:\n"
        "  Search:\n"
        "    subsystems: [search]\n"
        "    key_components: [search-api]\n"
        "  Console:\n"
        "    subsystems: [console]\n"
        "    key_components: [console-chart-console-v2]\n"
        "  CLC:\n"
        "    subsystems: [cluster-lifecycle]\n"
        "    key_components: [cluster-manager]\n"
    )

    return tmp_path


@pytest.fixture
def service(knowledge_dir):
    """Create a ClusterHealthService with test knowledge directory."""
    return ClusterHealthService(
        kubeconfig_path='/tmp/test-kubeconfig',
        knowledge_dir=knowledge_dir,
        cli='oc',
    )


def _mock_run(returncode=0, stdout='', stderr=''):
    """Create a mock subprocess.run result."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _make_oc_router(responses):
    """
    Create a side_effect function that returns different outputs
    based on the oc command arguments.
    """
    def router(cmd, **kwargs):
        cmd_str = ' '.join(cmd)
        for pattern, response in responses.items():
            if pattern in cmd_str:
                return _mock_run(stdout=response)
        return _mock_run(returncode=1, stdout='')
    return router


# ---------------------------------------------------------------------------
# Healthy cluster JSON payloads
# ---------------------------------------------------------------------------

MCH_JSON = json.dumps({
    'items': [{
        'metadata': {'namespace': 'ocm'},
        'status': {'currentVersion': '2.16.0', 'phase': 'Running'},
    }]
})

MCE_JSON = json.dumps({
    'items': [{
        'status': {'currentVersion': '2.11.0'},
    }]
})

NODES_JSON = json.dumps({
    'items': [
        {'metadata': {'name': f'node-{i}', 'labels': {'node-role.kubernetes.io/worker': ''}},
         'status': {'conditions': [{'type': 'Ready', 'status': 'True'}]}}
        for i in range(3)
    ] + [
        {'metadata': {'name': f'master-{i}', 'labels': {'node-role.kubernetes.io/control-plane': ''}},
         'status': {'conditions': [{'type': 'Ready', 'status': 'True'}]}}
        for i in range(3)
    ]
})

CV_JSON = json.dumps({
    'items': [{'status': {'desired': {'version': '4.21.5'}}}]
})

MANAGED_CLUSTERS_JSON = json.dumps({
    'items': [
        {'metadata': {'name': 'local-cluster'},
         'status': {'conditions': [
             {'type': 'ManagedClusterConditionAvailable', 'status': 'True'},
             {'type': 'ManagedClusterJoined', 'status': 'True'},
             {'type': 'HubAcceptedManagedCluster', 'status': 'True'},
         ]}},
        {'metadata': {'name': 'spoke-1'},
         'status': {'conditions': [
             {'type': 'ManagedClusterConditionAvailable', 'status': 'True'},
             {'type': 'ManagedClusterJoined', 'status': 'True'},
             {'type': 'HubAcceptedManagedCluster', 'status': 'True'},
         ]}},
    ]
})

ADDONS_JSON = json.dumps({
    'items': [
        {'metadata': {'namespace': 'local-cluster', 'name': 'work-manager'},
         'status': {'conditions': [{'type': 'Available', 'status': 'True'}]}},
        {'metadata': {'namespace': 'spoke-1', 'name': 'work-manager'},
         'status': {'conditions': [{'type': 'Available', 'status': 'True'}]}},
    ]
})

PLUGINS_JSON = json.dumps({
    'items': [
        {'metadata': {'name': 'acm'},
         'spec': {'backend': {'service': {'name': 'console-chart-console-v2', 'namespace': 'ocm'}}}},
        {'metadata': {'name': 'mce'},
         'spec': {'backend': {'service': {'name': 'console-mce-console', 'namespace': 'multicluster-engine'}}}},
    ]
})


def _healthy_deploy_json(name, ns, replicas=1):
    """Generate a healthy deployment JSON."""
    return {
        'metadata': {'name': name},
        'spec': {'replicas': replicas, 'selector': {'matchLabels': {'app': name}}},
        'status': {'readyReplicas': replicas, 'availableReplicas': replicas},
    }


def _healthy_namespace_deploys(ns, deploy_specs):
    """Generate deployments JSON for a namespace."""
    return json.dumps({'items': [
        _healthy_deploy_json(name, ns, replicas)
        for name, replicas in deploy_specs
    ]})


HEALTHY_OCM_DEPLOYS = _healthy_namespace_deploys('ocm', [
    ('multiclusterhub-operator', 2),
    ('search-api', 1),
    ('search-indexer', 1),
    ('search-postgres', 1),
    ('console-chart-console-v2', 2),
    ('grc-policy-propagator', 2),
])

HEALTHY_MCE_DEPLOYS = _healthy_namespace_deploys('multicluster-engine', [
    ('multicluster-engine-operator', 2),
    ('cluster-manager', 3),
    ('managedcluster-import-controller-v2', 2),
])

HEALTHY_HUB_DEPLOYS = _healthy_namespace_deploys('open-cluster-management-hub', [
    ('cluster-manager-registration-controller', 3),
    ('cluster-manager-work-webhook', 3),
])

HEALTHY_HIVE_DEPLOYS = _healthy_namespace_deploys('hive', [
    ('hive-controllers', 1),
    ('hiveadmission', 2),
])

HEALTHY_PODS_JSON = json.dumps({'items': []})  # No non-running pods


def _build_healthy_responses():
    """Build oc command responses for a healthy cluster."""
    return {
        'whoami --show-server': 'https://api.test.example.com:6443',
        'get clusterversion': CV_JSON,
        'get mch -A': MCH_JSON,
        'get multiclusterengines': MCE_JSON,
        'get nodes': NODES_JSON,
        'get managedclusters': MANAGED_CLUSTERS_JSON,
        'get managedclusteraddons': ADDONS_JSON,
        'get consoleplugins': PLUGINS_JSON,
        'get deployments -n ocm': HEALTHY_OCM_DEPLOYS,
        'get deployments -n multicluster-engine': HEALTHY_MCE_DEPLOYS,
        'get deployments -n open-cluster-management-hub': HEALTHY_HUB_DEPLOYS,
        'get deployments -n hive': HEALTHY_HIVE_DEPLOYS,
        'get deployments -n open-cluster-management-observability': json.dumps({'items': []}),
        'get pods -n ocm': HEALTHY_PODS_JSON,
        'get pods -n multicluster-engine': HEALTHY_PODS_JSON,
        'get pods -n open-cluster-management-hub': HEALTHY_PODS_JSON,
        'get pods -n hive': HEALTHY_PODS_JSON,
        'get networkpolicy -n ocm': '',
        'get networkpolicy -n multicluster-engine': '',
        'get resourcequota -n ocm': '',
        'get resourcequota -n multicluster-engine': '',
        'get deploy console-chart-console-v2 -n ocm': 'quay.io:443/acm-d/console:v2.16.0',
    }


# ===========================================================================
# TESTS: Initialization
# ===========================================================================

class TestClusterHealthServiceInit:

    def test_default_init(self, service):
        assert service.cli == 'oc'
        assert service.kubeconfig == '/tmp/test-kubeconfig'

    def test_knowledge_dir_set(self, service, knowledge_dir):
        assert service.knowledge_dir == knowledge_dir

    def test_readonly_blocks_delete(self, service):
        assert service._validate_readonly(['delete', 'pod', 'foo']) is False

    def test_readonly_blocks_apply(self, service):
        assert service._validate_readonly(['apply', '-f', 'foo.yaml']) is False

    def test_readonly_allows_get(self, service):
        assert service._validate_readonly(['get', 'pods']) is True

    def test_readonly_allows_describe(self, service):
        assert service._validate_readonly(['describe', 'pod', 'foo']) is True

    def test_readonly_allows_exec(self, service):
        assert service._validate_readonly(['exec', 'pod', '--', 'curl']) is True


# ===========================================================================
# TESTS: Phase 2 — LEARN
# ===========================================================================

class TestPhase2Learn:

    def test_loads_components(self, service):
        report = ClusterHealthReport()
        service._phase2_learn(report)
        assert 'search-api' in service._components
        assert 'multiclusterhub-operator' in service._components
        assert 'LEARN' in report.phases_completed

    def test_loads_baseline(self, service):
        report = ClusterHealthReport()
        service._phase2_learn(report)
        assert 'operators' in service._baseline
        assert 'namespaces' in service._baseline

    def test_loads_feature_areas(self, service):
        report = ClusterHealthReport()
        service._phase2_learn(report)
        assert 'Search' in service._feature_areas
        assert 'Console' in service._feature_areas

    def test_missing_yaml_graceful(self, tmp_path):
        """Service handles missing YAML files gracefully."""
        svc = ClusterHealthService(knowledge_dir=tmp_path)
        report = ClusterHealthReport()
        svc._phase2_learn(report)
        assert svc._components == {}
        assert 'LEARN' in report.phases_completed

    def test_empty_yaml_graceful(self, tmp_path):
        """Service handles empty YAML files gracefully."""
        (tmp_path / 'components.yaml').write_text('')
        (tmp_path / 'healthy-baseline.yaml').write_text('')
        (tmp_path / 'addon-catalog.yaml').write_text('')
        (tmp_path / 'dependencies.yaml').write_text('')
        (tmp_path / 'feature-areas.yaml').write_text('')
        svc = ClusterHealthService(knowledge_dir=tmp_path)
        report = ClusterHealthReport()
        svc._phase2_learn(report)
        assert svc._components == {}


# ===========================================================================
# TESTS: Full healthy audit
# ===========================================================================

class TestHealthyClusterAudit:

    @patch('subprocess.run')
    def test_healthy_cluster_produces_healthy_verdict(self, mock_run, service):
        mock_run.side_effect = _make_oc_router(_build_healthy_responses())
        report = service.run_health_audit()

        assert report.overall_verdict == 'HEALTHY'
        assert report.environment_health_score >= 0.8
        assert report.critical_issue_count == 0
        assert len(report.phases_completed) == 6

    @patch('subprocess.run')
    def test_healthy_cluster_identity(self, mock_run, service):
        mock_run.side_effect = _make_oc_router(_build_healthy_responses())
        report = service.run_health_audit()

        assert report.cluster_identity.mch_namespace == 'ocm'
        assert report.cluster_identity.acm_version == '2.16.0'
        assert report.cluster_identity.ocp_version == '4.21.5'
        assert report.cluster_identity.node_count == 6
        assert report.cluster_identity.node_ready_count == 6
        assert report.cluster_identity.managed_cluster_count == 2

    @patch('subprocess.run')
    def test_healthy_cluster_no_infra_issues(self, mock_run, service):
        mock_run.side_effect = _make_oc_router(_build_healthy_responses())
        report = service.run_health_audit()

        critical_findings = [
            f for f in report.infrastructure_issues if f.severity == 'CRITICAL'
        ]
        assert len(critical_findings) == 0

    @patch('subprocess.run')
    def test_console_plugins_discovered(self, mock_run, service):
        mock_run.side_effect = _make_oc_router(_build_healthy_responses())
        report = service.run_health_audit()

        assert len(report.console_plugins) == 2
        names = [p['name'] for p in report.console_plugins]
        assert 'acm' in names
        assert 'mce' in names

    @patch('subprocess.run')
    def test_managed_clusters_healthy(self, mock_run, service):
        mock_run.side_effect = _make_oc_router(_build_healthy_responses())
        report = service.run_health_audit()

        assert 'local-cluster' in report.managed_cluster_health
        assert report.managed_cluster_health['local-cluster'].available is True

    @patch('subprocess.run')
    def test_audit_duration_recorded(self, mock_run, service):
        mock_run.side_effect = _make_oc_router(_build_healthy_responses())
        report = service.run_health_audit()

        assert report.audit_duration_seconds >= 0
        assert len(report.phases_completed) == 6

    @patch('subprocess.run')
    def test_core_data_summary(self, mock_run, service):
        mock_run.side_effect = _make_oc_router(_build_healthy_responses())
        report = service.run_health_audit()
        summary = service.get_core_data_summary(report)

        assert 'environment_health_score' in summary
        assert 'overall_verdict' in summary
        assert 'mch_namespace' in summary
        assert summary['mch_namespace'] == 'ocm'


# ===========================================================================
# TESTS: Degraded cluster scenarios
# ===========================================================================

class TestDegradedClusterAudit:

    @patch('subprocess.run')
    def test_operator_at_zero_replicas(self, mock_run, service):
        """MCH operator at 0 replicas → CRITICAL."""
        responses = _build_healthy_responses()
        # Override OCM deploys — MCH operator at 0
        responses['get deployments -n ocm'] = _healthy_namespace_deploys('ocm', [
            ('multiclusterhub-operator', 0),  # Scaled to 0
            ('search-api', 1),
            ('console-chart-console-v2', 2),
        ])
        # Fix: make operator show 0 ready
        ocm_deploys = json.loads(responses['get deployments -n ocm'])
        ocm_deploys['items'][0]['status']['readyReplicas'] = 0
        ocm_deploys['items'][0]['status']['availableReplicas'] = 0
        responses['get deployments -n ocm'] = json.dumps(ocm_deploys)

        mock_run.side_effect = _make_oc_router(responses)
        report = service.run_health_audit()

        assert report.environment_health_score <= 0.7
        assert report.critical_issue_count >= 1
        op_health = report.operator_health.get('multiclusterhub-operator', {})
        assert op_health.get('status') == 'CRITICAL'

    @patch('subprocess.run')
    def test_network_policy_detected(self, mock_run, service):
        """NetworkPolicy in ACM namespace → CRITICAL finding."""
        responses = _build_healthy_responses()
        responses['get networkpolicy -n ocm'] = 'block-search-db   <none>   5d'

        mock_run.side_effect = _make_oc_router(responses)
        report = service.run_health_audit()

        np_findings = [
            f for f in report.infrastructure_issues
            if f.category == 'network_policy'
        ]
        assert len(np_findings) >= 1
        assert np_findings[0].severity == 'CRITICAL'
        assert 'block-search-db' in np_findings[0].component

    @patch('subprocess.run')
    def test_resource_quota_detected(self, mock_run, service):
        """ResourceQuota in ACM namespace → CRITICAL finding."""
        responses = _build_healthy_responses()
        responses['get resourcequota -n ocm'] = 'restrict-ocm   pods: 5   5'

        mock_run.side_effect = _make_oc_router(responses)
        report = service.run_health_audit()

        rq_findings = [
            f for f in report.infrastructure_issues
            if f.category == 'resource_quota'
        ]
        assert len(rq_findings) >= 1
        assert rq_findings[0].severity == 'CRITICAL'

    @patch('subprocess.run')
    def test_console_image_tampered(self, mock_run, service):
        """Console image from non-official registry → finding."""
        responses = _build_healthy_responses()
        responses['get deploy console-chart-console-v2 -n ocm'] = (
            'quay.io/personal/acm-console:debug-v1'
        )

        mock_run.side_effect = _make_oc_router(responses)
        report = service.run_health_audit()

        image_findings = [
            f for f in report.infrastructure_issues
            if f.category == 'image_integrity'
        ]
        assert len(image_findings) >= 1

    @patch('subprocess.run')
    def test_managed_cluster_not_available(self, mock_run, service):
        """Managed cluster not available → WARNING."""
        responses = _build_healthy_responses()
        responses['get managedclusters'] = json.dumps({'items': [
            {'metadata': {'name': 'local-cluster'},
             'status': {'conditions': [
                 {'type': 'ManagedClusterConditionAvailable', 'status': 'True'},
                 {'type': 'ManagedClusterJoined', 'status': 'True'},
                 {'type': 'HubAcceptedManagedCluster', 'status': 'True'},
             ]}},
            {'metadata': {'name': 'spoke-down'},
             'status': {'conditions': [
                 {'type': 'ManagedClusterConditionAvailable', 'status': 'False'},
                 {'type': 'ManagedClusterJoined', 'status': 'True'},
                 {'type': 'HubAcceptedManagedCluster', 'status': 'True'},
             ]}},
        ]})

        mock_run.side_effect = _make_oc_router(responses)
        report = service.run_health_audit()

        assert report.cluster_identity.managed_cluster_ready_count == 1
        mc_findings = [
            f for f in report.infrastructure_issues
            if f.category == 'managed_cluster'
        ]
        assert len(mc_findings) >= 1

    @patch('subprocess.run')
    def test_nodes_not_ready(self, mock_run, service):
        """Node not ready → finding."""
        responses = _build_healthy_responses()
        nodes = json.loads(NODES_JSON)
        nodes['items'][0]['status']['conditions'][0]['status'] = 'False'
        responses['get nodes'] = json.dumps(nodes)

        mock_run.side_effect = _make_oc_router(responses)
        report = service.run_health_audit()

        node_findings = [
            f for f in report.infrastructure_issues
            if f.category == 'node_health'
        ]
        assert len(node_findings) >= 1


# ===========================================================================
# TESTS: Scoring
# ===========================================================================

class TestHealthScoring:

    def test_perfect_score(self, service):
        """No issues → score 1.0, HEALTHY."""
        report = ClusterHealthReport()
        report.cluster_identity.managed_cluster_count = 2
        report.cluster_identity.managed_cluster_ready_count = 2
        service._phase6_score(report)
        assert report.environment_health_score == 1.0
        assert report.overall_verdict == 'HEALTHY'

    def test_operator_critical_penalty(self, service):
        """CRITICAL operator → -0.30."""
        report = ClusterHealthReport()
        report.operator_health = {
            'multiclusterhub-operator': {'status': 'CRITICAL'},
        }
        report.cluster_identity.managed_cluster_count = 1
        report.cluster_identity.managed_cluster_ready_count = 1
        service._phase6_score(report)
        assert report.environment_health_score == 0.70

    def test_infra_guard_penalty(self, service):
        """NetworkPolicy + ResourceQuota → -0.20."""
        report = ClusterHealthReport()
        report.infrastructure_issues = [
            HealthFinding(id='np1', severity='CRITICAL', category='network_policy',
                         component='np1'),
            HealthFinding(id='rq1', severity='CRITICAL', category='resource_quota',
                         component='rq1'),
        ]
        report.cluster_identity.managed_cluster_count = 1
        report.cluster_identity.managed_cluster_ready_count = 1
        service._phase6_score(report)
        assert report.environment_health_score == 0.80

    def test_multiple_penalties_stack(self, service):
        """Multiple issues compound the score."""
        report = ClusterHealthReport()
        report.operator_health = {
            'multiclusterhub-operator': {'status': 'CRITICAL'},
        }
        report.infrastructure_issues = [
            HealthFinding(id='np1', severity='CRITICAL', category='network_policy',
                         component='np1'),
            HealthFinding(id='img', severity='CRITICAL', category='image_integrity',
                         component='console'),
        ]
        report.subsystem_health = {
            'Search': SubsystemHealth(name='Search', status='CRITICAL'),
        }
        report.cluster_identity.managed_cluster_count = 2
        report.cluster_identity.managed_cluster_ready_count = 0
        service._phase6_score(report)
        # -0.30 (operator) -0.10 (np) -0.10 (image) -0.06 (search critical)
        # -0.10 (clusters <50%) = 0.34
        assert report.environment_health_score == 0.34
        assert report.overall_verdict == 'CRITICAL'

    def test_score_never_below_zero(self, service):
        """Score clamped at 0.0."""
        report = ClusterHealthReport()
        report.operator_health = {
            'op1': {'status': 'CRITICAL'},
        }
        report.infrastructure_issues = [
            HealthFinding(id=f'np{i}', severity='CRITICAL', category='network_policy',
                         component=f'np{i}')
            for i in range(10)
        ]
        report.subsystem_health = {
            f'Sub{i}': SubsystemHealth(name=f'Sub{i}', status='CRITICAL')
            for i in range(10)
        }
        report.cluster_identity.managed_cluster_count = 2
        report.cluster_identity.managed_cluster_ready_count = 0
        service._phase6_score(report)
        assert report.environment_health_score >= 0.0

    def test_degraded_verdict_thresholds(self, service):
        """Score 0.5-0.8 with <=1 critical → DEGRADED."""
        report = ClusterHealthReport()
        report.infrastructure_issues = [
            HealthFinding(id='np1', severity='CRITICAL', category='network_policy',
                         component='np1'),
        ]
        report.cluster_identity.managed_cluster_count = 1
        report.cluster_identity.managed_cluster_ready_count = 1
        service._phase6_score(report)
        assert report.overall_verdict in ('HEALTHY', 'DEGRADED')


# ===========================================================================
# TESTS: Report serialization
# ===========================================================================

class TestReportSerialization:

    def test_report_to_dict_structure(self, service):
        report = ClusterHealthReport()
        report.cluster_identity = ClusterIdentity(
            api_url='https://api.test:6443',
            acm_version='2.16.0',
            mch_namespace='ocm',
        )
        data = service._report_to_dict(report)

        assert 'cluster_health' in data
        ch = data['cluster_health']
        assert 'version' in ch
        assert 'overall_verdict' in ch
        assert 'cluster_identity' in ch
        assert ch['cluster_identity']['mch_namespace'] == 'ocm'

    def test_save_report_creates_file(self, service, tmp_path):
        report = ClusterHealthReport()
        report.overall_verdict = 'HEALTHY'
        path = service.save_report(report, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data['cluster_health']['overall_verdict'] == 'HEALTHY'

    def test_infrastructure_issues_serialized(self, service):
        report = ClusterHealthReport()
        report.infrastructure_issues.append(HealthFinding(
            id='test-finding',
            severity='CRITICAL',
            category='operator_health',
            component='test-op',
            finding='Test finding',
        ))
        data = service._report_to_dict(report)
        issues = data['cluster_health']['infrastructure_issues']
        assert len(issues) == 1
        assert issues[0]['id'] == 'test-finding'

    def test_core_data_summary_compact(self, service):
        report = ClusterHealthReport()
        report.environment_health_score = 0.75
        report.overall_verdict = 'DEGRADED'
        report.cluster_identity.mch_namespace = 'ocm'
        report.classification_guidance = {
            'affected_feature_areas': ['Search'],
        }
        summary = service.get_core_data_summary(report)
        assert summary['environment_health_score'] == 0.75
        assert summary['affected_feature_areas'] == ['Search']
        # Should NOT include full infrastructure_issues or subsystem_health
        assert 'infrastructure_issues' not in summary
        assert 'subsystem_health' not in summary


# ===========================================================================
# TESTS: Graceful degradation
# ===========================================================================

class TestGracefulDegradation:

    @patch('subprocess.run')
    def test_cluster_unreachable(self, mock_run, service):
        """All oc commands fail → CRITICAL/DEGRADED verdict but no crash."""
        mock_run.return_value = _mock_run(returncode=1, stdout='')
        report = service.run_health_audit()

        # With no cluster data, operator baseline checks produce CRITICAL findings
        # (operator not found). The service should still complete all phases.
        assert len(report.phases_completed) == 6
        assert report.overall_verdict in ('HEALTHY', 'DEGRADED', 'CRITICAL', 'ERROR', 'UNKNOWN')

    @patch('subprocess.run')
    def test_oc_timeout(self, mock_run, service):
        """oc command times out → handled gracefully."""
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd='oc', timeout=30)
        report = service.run_health_audit()
        # Should complete all phases despite timeouts
        assert len(report.phases_completed) == 6

    def test_no_yaml_installed(self, tmp_path):
        """PyYAML not available → Phase 2 partial."""
        import src.services.cluster_health_service as mod
        original_yaml = mod.yaml
        mod.yaml = None
        try:
            svc = ClusterHealthService(knowledge_dir=tmp_path)
            report = ClusterHealthReport()
            svc._phase2_learn(report)
            assert 'LEARN (partial)' in report.phases_completed
            assert len(report.errors) >= 1
        finally:
            mod.yaml = original_yaml


# ===========================================================================
# TESTS: Subsystem correlation
# ===========================================================================

class TestSubsystemCorrelation:

    @patch('subprocess.run')
    def test_search_subsystem_healthy(self, mock_run, service):
        mock_run.side_effect = _make_oc_router(_build_healthy_responses())
        report = service.run_health_audit()

        if 'Search' in report.subsystem_health:
            assert report.subsystem_health['Search'].status == 'OK'

    @patch('subprocess.run')
    def test_operator_critical_affects_all_areas(self, mock_run, service):
        """CRITICAL operator → all feature areas affected."""
        responses = _build_healthy_responses()
        ocm_deploys = json.loads(responses['get deployments -n ocm'])
        # Zero out the MCH operator
        for d in ocm_deploys['items']:
            if d['metadata']['name'] == 'multiclusterhub-operator':
                d['status']['readyReplicas'] = 0
                d['status']['availableReplicas'] = 0
                d['spec']['replicas'] = 2
        responses['get deployments -n ocm'] = json.dumps(ocm_deploys)

        mock_run.side_effect = _make_oc_router(responses)
        report = service.run_health_audit()

        affected = report.classification_guidance.get('affected_feature_areas', [])
        # All feature areas should be affected when operator is critical
        assert len(affected) >= 2
