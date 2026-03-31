"""
Unit tests for EnvironmentOracleService (Phases A+B+C).

Tests cover:
- Phase 1: Feature area identification from pipeline names and test names
- Phase 2: Polarion test case context fetching (description, setup, steps)
- Phase 3: KG-driven feature learning (component topology, data flow)
- Phase 4: KG-driven dependency learning (per-dependency architecture)
- Phase 5: Dependency model synthesis from playbooks
- Phase 6: Cluster health checks (operator, addon, CRD) with mocked commands
- Overall health computation
- Read-only command validation
- Oracle integration with FeatureKnowledgeService
- Graceful degradation (missing data, failed login, etc.)
"""

import os
import re
import sys
import unittest
from unittest.mock import patch, MagicMock
from dataclasses import asdict

# Setup path
test_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(os.path.dirname(os.path.dirname(test_dir)))
sys.path.insert(0, app_dir)

from src.services.environment_oracle_service import (
    EnvironmentOracleService,
    DependencyTarget,
    DependencyHealth,
    OracleResult,
)


class TestPhase1Identify(unittest.TestCase):
    """Phase 1: Feature area identification."""

    def setUp(self):
        self.oracle = EnvironmentOracleService()

    def test_pipeline_to_feature_area_clc(self):
        areas = self.oracle._pipeline_to_feature_areas('clc-e2e-pipeline')
        self.assertEqual(areas, ['CLC'])

    def test_pipeline_to_feature_area_alc(self):
        areas = self.oracle._pipeline_to_feature_areas('alc_e2e_tests')
        self.assertEqual(areas, ['Application'])

    def test_pipeline_to_feature_area_search(self):
        areas = self.oracle._pipeline_to_feature_areas('search-e2e')
        self.assertEqual(areas, ['Search'])

    def test_pipeline_to_feature_area_grc(self):
        areas = self.oracle._pipeline_to_feature_areas('grc-e2e-pipeline')
        self.assertEqual(areas, ['GRC'])

    def test_pipeline_to_feature_area_virt(self):
        areas = self.oracle._pipeline_to_feature_areas('fleet-virt-tests')
        self.assertEqual(areas, ['Virtualization'])

    def test_pipeline_to_feature_area_unknown(self):
        areas = self.oracle._pipeline_to_feature_areas('unknown-job')
        self.assertEqual(areas, [])

    def test_pipeline_to_feature_area_case_insensitive(self):
        areas = self.oracle._pipeline_to_feature_areas('CLC-E2E-Pipeline')
        self.assertEqual(areas, ['CLC'])

    def test_tests_to_feature_areas_from_test_names(self):
        tests = [
            {'test_name': 'RHACM4K-1234: CLC: Create cluster', 'class_name': ''},
            {'test_name': 'RHACM4K-5678: CLC: Destroy cluster', 'class_name': ''},
        ]
        areas = self.oracle._tests_to_feature_areas(tests)
        self.assertIn('CLC', areas)

    def test_phase1_extracts_polarion_ids(self):
        jenkins_data = {'job_name': 'clc-e2e-pipeline'}
        test_report = {
            'failed_tests': [
                {'test_name': 'RHACM4K-7473: CLC: Create AWS cluster'},
                {'test_name': 'RHACM4K-2576: CLC: Verify release images'},
                {'test_name': 'Some test without ID'},
            ]
        }
        result = self.oracle._phase1_identify(jenkins_data, test_report)
        self.assertEqual(result['feature_areas'], ['CLC'])
        self.assertEqual(result['failed_test_count'], 3)
        self.assertIn('RHACM4K-7473', result['polarion_ids'])
        self.assertIn('RHACM4K-2576', result['polarion_ids'])
        self.assertEqual(len(result['polarion_ids']), 2)

    def test_phase1_fallback_to_test_names(self):
        jenkins_data = {'job_name': 'unknown-job-name'}
        test_report = {
            'failed_tests': [
                {'test_name': 'RHACM4K-1: search results empty', 'class_name': ''},
            ]
        }
        result = self.oracle._phase1_identify(jenkins_data, test_report)
        self.assertIn('Search', result['feature_areas'])


class TestPhase5Synthesize(unittest.TestCase):
    """Phase 5: Comprehensive synthesis from ALL sources."""

    def setUp(self):
        self.oracle = EnvironmentOracleService()

    def test_synthesize_extracts_operator_targets(self):
        identification = {'feature_areas': ['CLC'], 'polarion_ids': []}
        landscape = {'mch_version': '2.17.0-76'}

        targets = self.oracle._phase5_synthesize(identification, landscape, {})

        operator_targets = [t for t in targets if t.type == 'operator']
        self.assertTrue(
            len(operator_targets) > 0,
            "CLC should have at least one operator dependency"
        )
        hive_ids = [t.id for t in operator_targets]
        self.assertIn('hive-operator', hive_ids)

    def test_synthesize_extracts_addon_targets(self):
        identification = {'feature_areas': ['Search'], 'polarion_ids': []}
        landscape = {'mch_version': '2.17.0-76'}

        targets = self.oracle._phase5_synthesize(identification, landscape, {})

        addon_targets = [t for t in targets if t.type == 'addon']
        self.assertTrue(
            len(addon_targets) > 0,
            "Search should have search-collector addon dependency"
        )

    def test_synthesize_skips_mch_and_informational(self):
        identification = {'feature_areas': ['CLC'], 'polarion_ids': []}
        landscape = {'mch_version': '2.17.0-76'}

        targets = self.oracle._phase5_synthesize(identification, landscape, {})

        # Playbook targets should only be operator/addon/crd
        playbook_targets = [t for t in targets if t.source == 'playbook']
        for t in playbook_targets:
            self.assertIn(t.type, ('operator', 'addon', 'crd'))

    def test_synthesize_includes_kg_components(self):
        """KG-discovered components from Phase 3 become collection targets."""
        identification = {'feature_areas': ['Search'], 'polarion_ids': []}
        landscape = {'mch_version': '2.17.0-76'}
        knowledge_context = {
            'feature_components': {
                'Search': ['search-api', 'search-collector', 'search-indexer']
            }
        }

        targets = self.oracle._phase5_synthesize(
            identification, landscape, knowledge_context
        )

        # Should have both playbook deps AND KG components
        kg_targets = [t for t in targets if t.source == 'kg']
        self.assertTrue(len(kg_targets) > 0, "Should include KG components")
        kg_names = [t.name for t in kg_targets]
        self.assertIn('search-api', kg_names)
        self.assertIn('search-collector', kg_names)

    def test_synthesize_includes_managed_clusters(self):
        """Managed clusters target is always included."""
        identification = {'feature_areas': ['CLC'], 'polarion_ids': []}
        landscape = {'mch_version': '2.17.0-76'}

        targets = self.oracle._phase5_synthesize(identification, landscape, {})

        mc_targets = [t for t in targets if t.type == 'managed_clusters']
        self.assertEqual(len(mc_targets), 1)

    def test_synthesize_deduplicates(self):
        identification = {'feature_areas': ['Search', 'GRC'], 'polarion_ids': []}
        landscape = {'mch_version': '2.17.0-76'}

        targets = self.oracle._phase5_synthesize(identification, landscape, {})
        ids = [t.id for t in targets]
        self.assertEqual(len(ids), len(set(ids)), "Target IDs should be unique")

    def test_synthesize_empty_feature_areas(self):
        identification = {'feature_areas': [], 'polarion_ids': []}
        targets = self.oracle._phase5_synthesize(identification, {}, {})
        self.assertIsInstance(targets, list)

    def test_extract_acm_version(self):
        self.assertEqual(
            self.oracle._extract_acm_version({'mch_version': '2.17.0-76'}),
            '2.17'
        )
        self.assertIsNone(self.oracle._extract_acm_version({}))


class TestPhase6Investigate(unittest.TestCase):
    """Phase 6: Cluster health checks with mocked commands."""

    def setUp(self):
        self.oracle = EnvironmentOracleService()
        self.oracle._logged_in = True

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_operator_healthy(self, mock_cmd):
        mock_cmd.return_value = (
            True,
            'hive-operator.v1.2.3   Hive   1.2.3      Succeeded\n',
            ''
        )
        target = DependencyTarget(
            id='hive-operator', type='operator', name='hive-operator',
            description='Hive operator', namespace='hive',
            component_name='hive-operator',
        )
        result = self.oracle._check_operator(target)
        self.assertEqual(result.status, 'healthy')
        self.assertIn('Succeeded', result.detail)

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_operator_degraded(self, mock_cmd):
        mock_cmd.return_value = (
            True,
            'hive-operator.v1.2.3   Hive   1.2.3      InstallReady\n',
            ''
        )
        target = DependencyTarget(
            id='hive-operator', type='operator', name='hive-operator',
            description='Hive', namespace='hive',
            component_name='hive-operator',
        )
        result = self.oracle._check_operator(target)
        self.assertEqual(result.status, 'degraded')

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_operator_missing(self, mock_cmd):
        mock_cmd.return_value = (True, '', '')
        target = DependencyTarget(
            id='aap-operator', type='operator', name='aap-operator',
            description='AAP', namespace='aap',
            component_name='aap-operator',
        )
        result = self.oracle._check_operator(target)
        self.assertEqual(result.status, 'missing')

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_addon_healthy(self, mock_cmd):
        mock_cmd.return_value = (
            True,
            'cluster1   search-collector   True\ncluster2   search-collector   True\n',
            ''
        )
        target = DependencyTarget(
            id='search-collector-addon', type='addon',
            name='search-collector', description='Search collector',
            component_name='search-collector',
        )
        result = self.oracle._check_addon(target)
        self.assertEqual(result.status, 'healthy')

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_addon_missing(self, mock_cmd):
        mock_cmd.return_value = (True, '', '')
        target = DependencyTarget(
            id='search-collector-addon', type='addon',
            name='search-collector', description='Search collector',
            component_name='search-collector',
        )
        result = self.oracle._check_addon(target)
        self.assertEqual(result.status, 'missing')

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_crd_exists(self, mock_cmd):
        mock_cmd.return_value = (
            True,
            'consoleplugins.console.openshift.io   2024-01-01T00:00:00Z\n',
            ''
        )
        target = DependencyTarget(
            id='console-plugin-crs', type='crd',
            name='consoleplugins.console.openshift.io',
            description='ConsolePlugin CRD',
            component_name='consoleplugins.console.openshift.io',
        )
        result = self.oracle._check_crd(target)
        self.assertEqual(result.status, 'healthy')

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_crd_missing(self, mock_cmd):
        mock_cmd.return_value = (False, '', 'not found')
        target = DependencyTarget(
            id='console-plugin-crs', type='crd',
            name='consoleplugins.console.openshift.io',
            description='ConsolePlugin CRD',
            component_name='consoleplugins.console.openshift.io',
        )
        result = self.oracle._check_crd(target)
        self.assertEqual(result.status, 'missing')


    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_component_healthy(self, mock_cmd):
        mock_cmd.return_value = (
            True,
            'open-cluster-management   search-api   1/1   1   1   5d\n',
            ''
        )
        target = DependencyTarget(
            id='kg-search-search-api', type='component', name='search-api',
            description='KG component', namespace='open-cluster-management',
            component_name='search-api',
        )
        result = self.oracle._check_component(target)
        self.assertEqual(result.status, 'healthy')
        self.assertIn('search-api', result.detail)

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_component_degraded(self, mock_cmd):
        mock_cmd.return_value = (
            True,
            'open-cluster-management   search-api   0/1   1   0   5d\n',
            ''
        )
        target = DependencyTarget(
            id='kg-search-search-api', type='component', name='search-api',
            description='KG component', component_name='search-api',
        )
        result = self.oracle._check_component(target)
        self.assertEqual(result.status, 'degraded')

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_component_missing(self, mock_cmd):
        mock_cmd.return_value = (True, '', '')  # No matching deployments or pods
        target = DependencyTarget(
            id='kg-search-nonexistent', type='component', name='nonexistent',
            description='KG component', component_name='nonexistent',
        )
        result = self.oracle._check_component(target)
        self.assertEqual(result.status, 'missing')

    @patch.object(EnvironmentOracleService, '_run_command')
    def test_check_managed_clusters(self, mock_cmd):
        mock_cmd.return_value = (
            True,
            'local-cluster   true    True    True\nspoke-1   true    True    False\n',
            ''
        )
        target = DependencyTarget(
            id='managed-clusters-status', type='managed_clusters',
            name='managed-clusters', description='Managed clusters',
        )
        result = self.oracle._check_managed_clusters(target)
        self.assertIn('2', result.detail)  # 2 total clusters
        self.assertIn('local-cluster', result.detail)


class TestOverallHealth(unittest.TestCase):
    """Overall health computation."""

    def setUp(self):
        self.oracle = EnvironmentOracleService()

    def test_all_healthy(self):
        health = {
            'dep1': {'status': 'healthy', 'detail': 'ok'},
            'dep2': {'status': 'healthy', 'detail': 'ok'},
        }
        result = self.oracle._compute_overall_health(health, ['CLC'])
        self.assertEqual(result['score'], 1.0)
        self.assertEqual(result['signal'], 'none')
        self.assertEqual(result['blocking_issues'], [])

    def test_mixed_health(self):
        health = {
            'dep1': {'status': 'healthy', 'name': 'dep1', 'type': 'op', 'detail': 'ok'},
            'dep2': {'status': 'degraded', 'name': 'dep2', 'type': 'addon', 'detail': 'not ready'},
        }
        result = self.oracle._compute_overall_health(health, ['Search'])
        self.assertEqual(result['score'], 0.5)
        self.assertEqual(result['signal'], 'moderate')
        self.assertEqual(len(result['blocking_issues']), 1)

    def test_all_degraded(self):
        health = {
            'dep1': {'status': 'missing', 'name': 'dep1', 'type': 'op', 'detail': 'gone'},
        }
        result = self.oracle._compute_overall_health(health, ['Automation'])
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['signal'], 'definitive')

    def test_empty_health(self):
        result = self.oracle._compute_overall_health({}, ['CLC'])
        self.assertIsNone(result['score'])
        self.assertEqual(result['signal'], 'unknown')


class TestReadOnlyEnforcement(unittest.TestCase):
    """Read-only command validation."""

    def setUp(self):
        self.oracle = EnvironmentOracleService()

    def test_get_allowed(self):
        self.assertTrue(self.oracle._validate_readonly(['get', 'pods']))

    def test_describe_allowed(self):
        self.assertTrue(self.oracle._validate_readonly(['describe', 'pod', 'foo']))

    def test_create_blocked(self):
        self.assertFalse(self.oracle._validate_readonly(['create', 'pod']))

    def test_delete_blocked(self):
        self.assertFalse(self.oracle._validate_readonly(['delete', 'pod', 'foo']))

    def test_apply_blocked(self):
        self.assertFalse(self.oracle._validate_readonly(['apply', '-f', 'file.yaml']))

    def test_patch_blocked(self):
        self.assertFalse(self.oracle._validate_readonly(['patch', 'deployment']))

    def test_exec_blocked(self):
        self.assertFalse(self.oracle._validate_readonly(['exec', 'pod', '--', 'cmd']))

    def test_auth_cani_allowed(self):
        self.assertTrue(self.oracle._validate_readonly(['auth', 'can-i', 'get', 'pods']))

    def test_auth_other_blocked(self):
        self.assertFalse(self.oracle._validate_readonly(['auth', 'reconcile']))

    def test_empty_args_blocked(self):
        self.assertFalse(self.oracle._validate_readonly([]))


class TestOracleIntegration(unittest.TestCase):
    """Integration: FeatureKnowledgeService._lookup_oracle uses oracle data."""

    def test_lookup_healthy(self):
        from src.services.feature_knowledge_service import FeatureKnowledgeService
        oracle_data = {
            'dependency_health': {
                'hive-operator': {
                    'status': 'healthy',
                    'detail': 'CSV hive-operator.v1.2.3 phase=Succeeded',
                }
            }
        }
        result = FeatureKnowledgeService._lookup_oracle(
            oracle_data, 'hive-operator', 'operator'
        )
        self.assertIsNotNone(result)
        met, detail = result
        self.assertTrue(met)
        self.assertIn('Oracle', detail)

    def test_lookup_degraded(self):
        from src.services.feature_knowledge_service import FeatureKnowledgeService
        oracle_data = {
            'dependency_health': {
                'search-collector-addon': {
                    'status': 'degraded',
                    'detail': 'Not available on 2 clusters',
                }
            }
        }
        result = FeatureKnowledgeService._lookup_oracle(
            oracle_data, 'search-collector-addon', 'addon'
        )
        self.assertIsNotNone(result)
        met, detail = result
        self.assertFalse(met)

    def test_lookup_not_found(self):
        from src.services.feature_knowledge_service import FeatureKnowledgeService
        result = FeatureKnowledgeService._lookup_oracle(
            {'dependency_health': {}}, 'nonexistent', 'operator'
        )
        self.assertIsNone(result)

    def test_lookup_no_oracle(self):
        from src.services.feature_knowledge_service import FeatureKnowledgeService
        result = FeatureKnowledgeService._lookup_oracle(
            None, 'foo', 'operator'
        )
        self.assertIsNone(result)


class TestPhase2PolarionDiscovery(unittest.TestCase):
    """Phase 2: Polarion test case context fetching (description + setup + steps)."""

    def setUp(self):
        self.oracle = EnvironmentOracleService()

    def test_strip_html(self):
        html_str = '<p>Hello <b>world</b> &amp; friends</p>'
        text = self.oracle._strip_html(html_str)
        self.assertEqual(text, 'Hello world & friends')

    def test_strip_html_complex(self):
        html_str = '<span style="font-size:10pt">1. install gitops</span><br/><span>2. set up cluster set</span>'
        text = self.oracle._strip_html(html_str)
        self.assertIn('install gitops', text)
        self.assertIn('set up cluster set', text)

    def test_normalize_polarion_id(self):
        self.assertEqual(self.oracle._normalize_polarion_id('7473'), 'RHACM4K-7473')
        self.assertEqual(self.oracle._normalize_polarion_id('RHACM4K-7473'), 'RHACM4K-7473')

    def test_parse_test_steps(self):
        steps_data = {
            'data': [
                {'attributes': {'values': [
                    {'type': 'text/html', 'value': '<p>Navigate to clusters</p>'},
                    {'type': 'text/html', 'value': '<p>Click Create cluster</p>'},
                ]}},
                {'attributes': {'values': [
                    {'type': 'text/html', 'value': '<p>Select AWS provider</p>'},
                ]}},
            ]
        }
        steps = self.oracle._parse_test_steps(steps_data)
        self.assertEqual(len(steps), 3)
        self.assertIn('Navigate to clusters', steps[0])
        self.assertIn('Select AWS provider', steps[2])

    def test_parse_test_steps_empty(self):
        self.assertEqual(self.oracle._parse_test_steps({}), [])
        self.assertEqual(self.oracle._parse_test_steps({'data': []}), [])

    @patch.object(EnvironmentOracleService, '_fetch_polarion_test_context')
    def test_phase2_fetches_full_context(self, mock_fetch):
        self.oracle._polarion_token = 'mock-token'
        mock_fetch.side_effect = [
            {
                'title': 'Create Argo appset',
                'setup': 'install gitops 1.3.0, set up managed cluster set',
                'description': 'Verify user can create a Helm Argo applicationset',
                'test_steps': ['Navigate to applications', 'Click create'],
            },
            {
                'title': 'Create AWS cluster',
                'setup': 'Have an AWS provider connection prepared.',
            },
            None,  # Third ID has no content
        ]
        discovery = self.oracle._phase2_discover_from_polarion(
            ['RHACM4K-7184', 'RHACM4K-7473', 'RHACM4K-9999']
        )
        self.assertTrue(discovery.polarion_available)
        self.assertEqual(discovery.tests_queried, 3)
        self.assertEqual(discovery.tests_with_content, 2)
        # Full context stored for AI interpretation
        ctx_7184 = discovery.test_case_context.get('RHACM4K-7184', {})
        self.assertIn('setup', ctx_7184)
        self.assertIn('gitops', ctx_7184['setup'])
        self.assertIn('description', ctx_7184)
        self.assertIn('test_steps', ctx_7184)
        ctx_7473 = discovery.test_case_context.get('RHACM4K-7473', {})
        self.assertIn('setup', ctx_7473)
        self.assertIn('AWS provider', ctx_7473['setup'])

    @patch.object(EnvironmentOracleService, '_fetch_polarion_test_context')
    def test_phase2_no_token(self, mock_fetch):
        self.oracle._polarion_token = ''
        discovery = self.oracle._phase2_discover_from_polarion(['RHACM4K-1'])
        self.assertFalse(discovery.polarion_available)
        mock_fetch.assert_not_called()

    @patch.object(EnvironmentOracleService, '_fetch_polarion_test_context')
    def test_phase2_handles_fetch_error(self, mock_fetch):
        self.oracle._polarion_token = 'mock-token'
        mock_fetch.side_effect = Exception("Connection refused")
        discovery = self.oracle._phase2_discover_from_polarion(['RHACM4K-1'])
        self.assertEqual(discovery.tests_queried, 1)
        self.assertTrue(len(discovery.errors) > 0)

    def test_oracle_result_includes_polarion_discovery(self):
        """Verify oracle result contains polarion_discovery field."""
        result = self.oracle.run_oracle(
            jenkins_data={'job_name': 'clc-e2e-pipeline'},
            test_report={'failed_tests': [
                {'test_name': 'RHACM4K-7473: CLC test'}
            ]},
            cluster_landscape={'mch_version': '2.17.0'},
            skip_cluster=True,
        )
        self.assertIn('polarion_discovery', result)
        pd = result['polarion_discovery']
        self.assertIn('test_case_context', pd)
        self.assertIn('polarion_available', pd)


class TestPhase3LearnFeature(unittest.TestCase):
    """Phase 3: KG-driven feature learning."""

    def setUp(self):
        self.oracle = EnvironmentOracleService()

    def _mock_kg_client(self):
        """Create a mock KG client with realistic responses."""
        kg = MagicMock()
        kg.available = True
        kg._escape_regex = lambda s: re.escape(s)
        kg.get_subsystem_components.return_value = [
            'search-api', 'search-collector', 'search-indexer'
        ]
        kg._execute_cypher.return_value = [
            {'source': 'search-collector', 'rel': 'DEPENDS_ON', 'target': 'search-indexer'},
            {'source': 'search-indexer', 'rel': 'DEPENDS_ON', 'target': 'search-api'},
        ]

        chain_mock = MagicMock()
        chain_mock.affected_components = ['console', 'observability']
        chain_mock.subsystems_affected = ['Console', 'Observability']
        chain_mock.chain_length = 2
        kg.get_transitive_dependents.return_value = chain_mock

        return kg

    def test_phase3_builds_feature_context(self):
        kg = self._mock_kg_client()
        identification = {'feature_areas': ['Search'], 'polarion_ids': []}
        # Load playbooks so profiles are populated
        self.oracle.feature_knowledge.load_playbooks(feature_areas=['Search'])

        context = self.oracle._phase3_learn_feature(identification, kg)

        self.assertTrue(context.get('kg_available'))
        self.assertIn('Search', context.get('subsystems_investigated', []))
        self.assertIn('Search', context.get('feature_components', {}))
        self.assertIn('search-api', context['feature_components']['Search'])

    def test_phase3_includes_playbook_architecture(self):
        kg = self._mock_kg_client()
        identification = {'feature_areas': ['Search'], 'polarion_ids': []}
        self.oracle.feature_knowledge.load_playbooks(feature_areas=['Search'])

        context = self.oracle._phase3_learn_feature(identification, kg)

        self.assertIn('playbook_architecture', context)
        self.assertIn('Search', context['playbook_architecture'])
        arch = context['playbook_architecture']['Search']
        self.assertIn('summary', arch)
        self.assertIn('key_insight', arch)

    def test_phase3_gets_transitive_chains(self):
        kg = self._mock_kg_client()
        identification = {'feature_areas': ['Search'], 'polarion_ids': []}
        self.oracle.feature_knowledge.load_playbooks(feature_areas=['Search'])

        context = self.oracle._phase3_learn_feature(identification, kg)

        transitive = context.get('transitive_chains', {}).get('Search', {})
        # Should have chains for some components
        self.assertIsInstance(transitive, dict)

    def test_phase3_handles_kg_error(self):
        kg = MagicMock()
        kg.available = True
        kg._escape_regex = lambda s: re.escape(s)
        kg.get_subsystem_components.side_effect = Exception("KG connection lost")
        identification = {'feature_areas': ['Search'], 'polarion_ids': []}
        self.oracle.feature_knowledge.load_playbooks(feature_areas=['Search'])

        context = self.oracle._phase3_learn_feature(identification, kg)

        # Should still return context with errors, not crash
        self.assertIn('errors', context)
        self.assertTrue(len(context['errors']) > 0)

    def test_phase3_no_kg_returns_playbook_and_docs(self):
        identification = {'feature_areas': ['CLC'], 'polarion_ids': []}
        self.oracle.feature_knowledge.load_playbooks(feature_areas=['CLC'])

        # Run oracle without KG — should still get playbook + docs
        result = self.oracle.run_oracle(
            jenkins_data={'job_name': 'clc-e2e'},
            test_report={'failed_tests': [{'test_name': 'RHACM4K-1: CLC test'}]},
            cluster_landscape={'mch_version': '2.17.0'},
            skip_cluster=True,
            knowledge_graph_client=None,
        )
        kc = result.get('knowledge_context', {})
        self.assertFalse(kc.get('kg_available', True))
        # Playbook architecture should always be present
        self.assertIn('playbook_architecture', kc)

    def test_phase3_provides_docs_path(self):
        """Verify Phase 3 provides docs path for AI to search."""
        self.oracle.feature_knowledge.load_playbooks(feature_areas=['Search'])
        identification = {'feature_areas': ['Search'], 'polarion_ids': []}

        context = self.oracle._phase3_learn_feature(identification, kg_client=None)

        if self.oracle._docs_dir:
            docs = context.get('docs_context', {})
            self.assertIn('docs_path', docs)
            self.assertIn('available_directories', docs)
            self.assertIsInstance(docs['available_directories'], list)
            self.assertIn('note', docs)

    def test_learn_from_docs_empty_dir(self):
        self.oracle._docs_dir = '/nonexistent/path'
        result = self.oracle._learn_from_docs(['Search'])
        self.assertEqual(result, {})

    def test_learn_from_docs_no_docs_dir(self):
        self.oracle._docs_dir = None
        result = self.oracle._learn_from_docs(['Search'])
        self.assertEqual(result, {})

    def test_learn_from_docs_lists_directories(self):
        """When docs dir exists, returns directory listing."""
        if self.oracle._docs_dir:
            result = self.oracle._learn_from_docs(['Search'])
            self.assertIn('docs_path', result)
            self.assertIn('available_directories', result)
            self.assertTrue(len(result['available_directories']) > 0)

class TestPhase4LearnDependencies(unittest.TestCase):
    """Phase 4: Comprehensive dependency learning from KG."""

    def setUp(self):
        self.oracle = EnvironmentOracleService()

    def test_phase4_learns_dependency_subsystem(self):
        kg = MagicMock()
        kg.get_subsystem_components.return_value = ['console-api', 'acm-console']
        kg._escape_regex = lambda s: re.escape(s)
        kg._execute_cypher.return_value = []

        comp_info = MagicMock()
        comp_info.component_type = 'Service'
        comp_info.dependencies = []
        comp_info.dependents = []
        kg.get_component_info.return_value = comp_info

        identification = {'feature_areas': ['Search']}
        dep_subsystems = {'Console'}
        details = self.oracle._phase4_learn_dependencies_comprehensive(
            identification, dep_subsystems, kg
        )

        self.assertIn('Console', details)
        self.assertIn('console-api', details['Console']['components'])
        self.assertIn('acm-console', details['Console']['components'])

    def test_phase4_skips_primary_feature(self):
        """Phase 4 should NOT re-learn the primary feature (already done in Phase 3)."""
        kg = MagicMock()
        identification = {'feature_areas': ['Search']}
        dep_subsystems = {'Search', 'Console'}  # Search is primary, Console is dep
        kg.get_subsystem_components.return_value = ['console-api']
        kg._escape_regex = lambda s: re.escape(s)
        kg._execute_cypher.return_value = []
        kg.get_component_info.return_value = None

        details = self.oracle._phase4_learn_dependencies_comprehensive(
            identification, dep_subsystems, kg
        )

        self.assertNotIn('Search', details)  # Primary feature skipped
        self.assertIn('Console', details)  # Dependency learned

    def test_phase4_handles_empty_subsystem(self):
        kg = MagicMock()
        kg.get_subsystem_components.return_value = []
        identification = {'feature_areas': ['CLC']}
        details = self.oracle._phase4_learn_dependencies_comprehensive(
            identification, {'Unknown'}, kg
        )
        self.assertEqual(len(details), 0)

    def test_full_oracle_with_kg(self):
        """Integration test: run_oracle with mocked KG client."""
        kg = MagicMock()
        kg.available = True
        kg._escape_regex = lambda s: re.escape(s)
        kg.get_subsystem_components.return_value = ['cluster-curator', 'hive']
        kg._execute_cypher.return_value = []
        kg.get_transitive_dependents.return_value = MagicMock(
            affected_components=[], subsystems_affected=[], chain_length=0
        )
        comp_info = MagicMock()
        comp_info.name = 'hive-operator'
        comp_info.subsystem = 'Provisioning'
        comp_info.component_type = 'Operator'
        comp_info.dependencies = []
        comp_info.dependents = []
        kg.get_component_info.return_value = comp_info

        result = self.oracle.run_oracle(
            jenkins_data={'job_name': 'clc-e2e'},
            test_report={'failed_tests': [{'test_name': 'RHACM4K-1: CLC test'}]},
            cluster_landscape={'mch_version': '2.17.0'},
            skip_cluster=True,
            knowledge_graph_client=kg,
        )

        kc = result.get('knowledge_context', {})
        self.assertTrue(kc.get('kg_available'))
        # Phase 5 should now include KG components as targets
        targets = result.get('dependency_targets', [])
        kg_targets = [t for t in targets if t.get('source') == 'kg']
        self.assertTrue(len(kg_targets) > 0, "KG components should be in targets")
        self.assertIn('dependency_details', kc)


class TestGracefulDegradation(unittest.TestCase):
    """Oracle degrades gracefully when data is missing."""

    def setUp(self):
        self.oracle = EnvironmentOracleService()

    def test_run_oracle_no_failed_tests(self):
        result = self.oracle.run_oracle(
            jenkins_data={'job_name': ''},
            test_report={'failed_tests': []},
            cluster_landscape={},
        )
        self.assertIn('errors', result)
        self.assertEqual(result['failed_test_count'], 0)

    def test_run_oracle_no_credentials(self):
        result = self.oracle.run_oracle(
            jenkins_data={'job_name': 'clc-e2e-pipeline'},
            test_report={'failed_tests': [
                {'test_name': 'RHACM4K-1: CLC test'}
            ]},
            cluster_landscape={'mch_version': '2.17.0'},
            cluster_credentials=None,
        )
        self.assertEqual(result['cluster_access_status'], 'no_credentials')
        # Should still have dependency targets from playbooks
        self.assertTrue(len(result['dependency_targets']) > 0)

    def test_run_oracle_skip_cluster(self):
        result = self.oracle.run_oracle(
            jenkins_data={'job_name': 'search-e2e'},
            test_report={'failed_tests': [
                {'test_name': 'RHACM4K-2: search test'}
            ]},
            cluster_landscape={'mch_version': '2.17.0'},
            skip_cluster=True,
        )
        self.assertEqual(result['cluster_access_status'], 'skipped')


class TestFeatureKnowledgeOracleIntegration(unittest.TestCase):
    """Test that FeatureKnowledgeService uses oracle data to resolve met=None."""

    def setUp(self):
        from src.services.feature_knowledge_service import FeatureKnowledgeService
        self.fks = FeatureKnowledgeService()
        self.fks.load_playbooks(feature_areas=['CLC', 'Search'])

    def test_without_oracle_returns_none(self):
        checks = self.fks.check_prerequisites('CLC', mch_components={'cluster-lifecycle': True})
        operator_checks = [c for c in checks if c.type == 'operator']
        for c in operator_checks:
            self.assertIsNone(c.met, f"Without oracle, {c.id} should be met=None")

    def test_with_oracle_resolves_operator(self):
        oracle_data = {
            'dependency_health': {
                'hive-operator': {
                    'status': 'healthy',
                    'detail': 'CSV phase=Succeeded',
                }
            }
        }
        checks = self.fks.check_prerequisites(
            'CLC', mch_components={'cluster-lifecycle': True},
            oracle_data=oracle_data,
        )
        hive_checks = [c for c in checks if c.id == 'hive-operator']
        self.assertTrue(len(hive_checks) > 0, "Should have hive-operator check")
        self.assertTrue(hive_checks[0].met, "Oracle says healthy -> met=True")
        self.assertIn('Oracle', hive_checks[0].detail)

    def test_with_oracle_degraded_operator(self):
        oracle_data = {
            'dependency_health': {
                'hive-operator': {
                    'status': 'degraded',
                    'detail': 'CSV phase=InstallReady',
                }
            }
        }
        checks = self.fks.check_prerequisites(
            'CLC', mch_components={'cluster-lifecycle': True},
            oracle_data=oracle_data,
        )
        hive_checks = [c for c in checks if c.id == 'hive-operator']
        self.assertTrue(len(hive_checks) > 0)
        self.assertFalse(hive_checks[0].met, "Oracle says degraded -> met=False")

    def test_readiness_uses_oracle(self):
        oracle_data = {
            'dependency_health': {
                'search-collector-addon': {
                    'status': 'degraded',
                    'detail': 'Not available on spoke-2',
                }
            }
        }
        readiness = self.fks.get_feature_readiness(
            'Search',
            mch_components={'search': True},
            oracle_data=oracle_data,
        )
        # Should have unmet prerequisites now that oracle resolved the addon
        self.assertTrue(
            len(readiness.unmet_prerequisites) > 0,
            "Degraded addon should appear as unmet prerequisite"
        )
        self.assertFalse(readiness.all_prerequisites_met)


if __name__ == '__main__':
    unittest.main()
