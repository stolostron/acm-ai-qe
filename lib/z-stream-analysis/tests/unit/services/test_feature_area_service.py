"""
Unit tests for FeatureAreaService.

Tests feature area identification from test names, file paths,
detected components, and grouping logic.
"""

import pytest
from src.services.feature_area_service import (
    FeatureAreaService,
    FeatureGrounding,
    FeatureMapping,
    FeatureGrouping,
    FEATURE_AREAS,
)


class TestFeatureAreaIdentification:
    """Test feature area identification from various inputs."""

    def setup_method(self):
        self.service = FeatureAreaService()

    # Path-based identification (highest reliability)

    def test_identify_grc_from_path(self):
        result = self.service.identify_feature_area(
            test_name='test_policy_create',
            test_file='cypress/e2e/governance/policy-create.cy.ts',
        )
        assert result.feature_area == 'GRC'
        assert result.confidence == 0.95
        assert result.identification_method == 'path'

    def test_identify_search_from_path(self):
        result = self.service.identify_feature_area(
            test_name='test_search_query',
            test_file='cypress/e2e/search/search-query.cy.ts',
        )
        assert result.feature_area == 'Search'
        assert result.confidence == 0.95

    def test_identify_clc_from_path(self):
        result = self.service.identify_feature_area(
            test_name='test_create_cluster',
            test_file='cypress/e2e/cluster/create-cluster.cy.ts',
        )
        assert result.feature_area == 'CLC'
        assert result.confidence == 0.95

    def test_identify_virtualization_from_path(self):
        result = self.service.identify_feature_area(
            test_name='test_vm_create',
            test_file='cypress/e2e/virtualization/vm-create.cy.ts',
        )
        assert result.feature_area == 'Virtualization'
        assert result.confidence == 0.95

    def test_identify_observability_from_path(self):
        result = self.service.identify_feature_area(
            test_name='test_metrics',
            test_file='cypress/e2e/observability/metrics.cy.ts',
        )
        assert result.feature_area == 'Observability'
        assert result.confidence == 0.95

    def test_identify_app_from_path(self):
        result = self.service.identify_feature_area(
            test_name='test_app_deploy',
            test_file='cypress/e2e/application/deploy.cy.ts',
        )
        assert result.feature_area == 'Application'
        assert result.confidence == 0.95

    def test_identify_rbac_from_path(self):
        result = self.service.identify_feature_area(
            test_name='test_rbac',
            test_file='cypress/e2e/rbac/role-assignment.cy.ts',
        )
        assert result.feature_area == 'RBAC'
        assert result.confidence == 0.95

    # Name-based identification

    def test_identify_grc_from_name(self):
        result = self.service.identify_feature_area(
            test_name='RHACM4K-1234 - Verify policy compliance status',
        )
        assert result.feature_area == 'GRC'
        assert result.confidence == 0.85
        assert result.identification_method == 'name_pattern'

    def test_identify_search_from_name(self):
        result = self.service.identify_feature_area(
            test_name='RHACM4K-5678 - Verify search query returns results',
        )
        assert result.feature_area == 'Search'
        assert result.confidence == 0.85

    def test_identify_clc_from_name_cluster_create(self):
        result = self.service.identify_feature_area(
            test_name='RHACM4K-9999 - Verify cluster creation workflow',
        )
        assert result.feature_area == 'CLC'
        assert result.confidence == 0.85

    def test_identify_clc_from_name_upgrade(self):
        result = self.service.identify_feature_area(
            test_name='RHACM4K-3046 - Verify cluster upgrade digest',
        )
        assert result.feature_area == 'CLC'
        assert result.confidence == 0.85

    def test_identify_vm_from_name(self):
        result = self.service.identify_feature_area(
            test_name='test virtual machine migration across clusters',
        )
        assert result.feature_area == 'Virtualization'
        assert result.confidence == 0.85

    # Component-based identification

    def test_identify_from_component_search_api(self):
        result = self.service.identify_feature_area(
            test_name='test_unknown',
            detected_components=['search-api'],
        )
        assert result.feature_area == 'Search'
        assert result.confidence == 0.80
        assert result.identification_method == 'component'

    def test_identify_from_component_grc(self):
        result = self.service.identify_feature_area(
            test_name='test_unknown',
            detected_components=['grc-policy-propagator'],
        )
        assert result.feature_area == 'GRC'
        assert result.confidence == 0.80

    def test_identify_from_component_hive(self):
        result = self.service.identify_feature_area(
            test_name='test_unknown',
            detected_components=['hive-controllers'],
        )
        assert result.feature_area == 'CLC'
        assert result.confidence == 0.80

    # Error message fallback

    def test_identify_from_error_message(self):
        result = self.service.identify_feature_area(
            test_name='test_something',
            error_message='search-api returned 500: index not available',
        )
        assert result.feature_area == 'Search'
        assert result.confidence == 0.60
        assert result.identification_method == 'error_message'

    # Unknown

    def test_unknown_feature_area(self):
        result = self.service.identify_feature_area(
            test_name='test_something_generic',
        )
        assert result.feature_area == 'Unknown'
        assert result.confidence == 0.0
        assert result.identification_method == 'none'

    # Priority: path > name > component > error

    def test_path_takes_priority_over_name(self):
        result = self.service.identify_feature_area(
            test_name='test_search_in_policy',  # name suggests Search
            test_file='cypress/e2e/governance/search.cy.ts',  # path says GRC
        )
        assert result.feature_area == 'GRC'
        assert result.identification_method == 'path'

    # Foundation identification

    def test_identify_foundation_from_path(self):
        result = self.service.identify_feature_area(
            test_name='test_addon_health',
            test_file='pkg/tests/server_foundation/addon_test.go',
        )
        assert result.feature_area == 'Foundation'
        assert result.confidence == 0.95
        assert result.identification_method == 'path'

    def test_identify_foundation_from_path_addon_framework(self):
        result = self.service.identify_feature_area(
            test_name='test_addon',
            test_file='pkg/tests/addon_framework/managed_test.go',
        )
        assert result.feature_area == 'Foundation'
        assert result.confidence == 0.95

    def test_identify_foundation_from_path_registration(self):
        result = self.service.identify_feature_area(
            test_name='test_registration',
            test_file='pkg/tests/registration/spoke_test.go',
        )
        assert result.feature_area == 'Foundation'
        assert result.confidence == 0.95

    def test_identify_foundation_from_name_ginkgo_label(self):
        result = self.service.identify_feature_area(
            test_name='[ServerFoundation] [P1][Sev1][addon-framework] Addon should reach Available',
        )
        assert result.feature_area == 'Foundation'
        assert result.confidence == 0.85
        assert result.identification_method == 'name_pattern'

    def test_identify_foundation_from_name_addon_framework_label(self):
        result = self.service.identify_feature_area(
            test_name='[addon-framework] ManagedClusterAddon should be Available',
        )
        assert result.feature_area == 'Foundation'
        assert result.confidence == 0.85

    def test_identify_foundation_from_name_managedclusteraddon(self):
        result = self.service.identify_feature_area(
            test_name='RHACM4K-12345 - Verify managedclusteraddon health',
        )
        assert result.feature_area == 'Foundation'
        assert result.confidence == 0.85

    def test_identify_foundation_from_component(self):
        result = self.service.identify_feature_area(
            test_name='test_unknown',
            detected_components=['registration-controller'],
        )
        assert result.feature_area == 'Foundation'
        assert result.confidence == 0.80
        assert result.identification_method == 'component'

    def test_identify_foundation_from_component_work_agent(self):
        result = self.service.identify_feature_area(
            test_name='test_unknown',
            detected_components=['work-agent'],
        )
        assert result.feature_area == 'Foundation'

    def test_identify_foundation_from_component_addon_manager(self):
        result = self.service.identify_feature_area(
            test_name='test_unknown',
            detected_components=['addon-manager'],
        )
        assert result.feature_area == 'Foundation'

    # Install identification

    def test_identify_install_from_path(self):
        result = self.service.identify_feature_area(
            test_name='test_acm_install',
            test_file='pkg/tests/install/acm_install_test.go',
        )
        assert result.feature_area == 'Install'
        assert result.confidence == 0.95
        assert result.identification_method == 'path'

    def test_identify_install_from_path_csv(self):
        result = self.service.identify_feature_area(
            test_name='test_csv_check',
            test_file='pkg/tests/csv/csv_phase_test.go',
        )
        assert result.feature_area == 'Install'
        assert result.confidence == 0.95

    def test_identify_install_from_name_ginkgo_label(self):
        result = self.service.identify_feature_area(
            test_name='[Install] ACM CSV should reach Succeeded phase',
        )
        assert result.feature_area == 'Install'
        assert result.confidence == 0.85
        assert result.identification_method == 'name_pattern'

    def test_identify_install_from_name_csv_phase(self):
        result = self.service.identify_feature_area(
            test_name='RHACM4K-99999 - Verify csv phase is Succeeded',
        )
        assert result.feature_area == 'Install'
        assert result.confidence == 0.85

    def test_identify_install_from_name_install_acm(self):
        result = self.service.identify_feature_area(
            test_name='install acm operator on cluster',
        )
        assert result.feature_area == 'Install'
        assert result.confidence == 0.85

    def test_identify_install_from_component(self):
        result = self.service.identify_feature_area(
            test_name='test_unknown',
            detected_components=['multiclusterhub-operator'],
        )
        assert result.feature_area == 'Install'
        assert result.confidence == 0.80
        assert result.identification_method == 'component'

    # Foundation vs Infrastructure priority (more specific wins)

    def test_foundation_path_beats_infrastructure_catchall(self):
        """Foundation-specific path patterns must match before Infrastructure catch-all."""
        result = self.service.identify_feature_area(
            test_name='test_addon_framework_health',
            test_file='pkg/tests/addon_framework/health_test.go',
        )
        assert result.feature_area == 'Foundation', \
            "addon_framework path should match Foundation, not Infrastructure"

    def test_generic_addon_path_falls_to_infrastructure(self):
        """Generic 'addon' in path without Foundation qualifiers matches Infrastructure."""
        result = self.service.identify_feature_area(
            test_name='test_something',
            test_file='pkg/tests/addon_status.go',
        )
        assert result.feature_area == 'Infrastructure'

    def test_install_path_beats_infrastructure_catchall(self):
        """Install path patterns must match before Infrastructure catch-all."""
        result = self.service.identify_feature_area(
            test_name='test_operator_install',
            test_file='pkg/tests/install/operator_test.go',
        )
        assert result.feature_area == 'Install'


class TestGroupTestsByFeature:
    """Test grouping of failed tests by feature area."""

    def setup_method(self):
        self.service = FeatureAreaService()

    def test_group_single_feature(self):
        failed_tests = [
            {
                'test_name': 'RHACM4K-1234 - policy create',
                'class_name': 'governance/policy.cy.ts',
                'error_message': '',
                'parsed_stack_trace': {'root_cause_file': 'cypress/e2e/governance/policy.cy.ts'},
            },
            {
                'test_name': 'RHACM4K-1235 - policy compliance',
                'class_name': 'governance/compliance.cy.ts',
                'error_message': '',
                'parsed_stack_trace': {'root_cause_file': 'cypress/e2e/governance/compliance.cy.ts'},
            },
        ]

        groups = self.service.group_tests_by_feature(failed_tests)

        assert 'GRC' in groups
        assert groups['GRC'].test_count == 2
        assert len(groups['GRC'].tests) == 2
        assert groups['GRC'].grounding.subsystem == 'Governance'

    def test_group_multiple_features(self):
        failed_tests = [
            {
                'test_name': 'test_policy_create',
                'class_name': '',
                'error_message': '',
                'parsed_stack_trace': {'root_cause_file': 'cypress/e2e/governance/policy.cy.ts'},
            },
            {
                'test_name': 'test_search_query',
                'class_name': '',
                'error_message': '',
                'parsed_stack_trace': {'root_cause_file': 'cypress/e2e/search/query.cy.ts'},
            },
            {
                'test_name': 'test_cluster_create',
                'class_name': '',
                'error_message': '',
                'parsed_stack_trace': {'root_cause_file': 'cypress/e2e/cluster/create.cy.ts'},
            },
        ]

        groups = self.service.group_tests_by_feature(failed_tests)

        assert len(groups) == 3
        assert 'GRC' in groups
        assert 'Search' in groups
        assert 'CLC' in groups

    def test_group_empty_tests(self):
        groups = self.service.group_tests_by_feature([])
        assert len(groups) == 0

    def test_group_with_detected_components(self):
        failed_tests = [
            {
                'test_name': 'test_unknown_1',
                'class_name': '',
                'error_message': '',
                'parsed_stack_trace': {},
                'detected_components': [{'name': 'search-api'}],
            },
        ]

        groups = self.service.group_tests_by_feature(failed_tests)

        assert 'Search' in groups
        assert groups['Search'].test_count == 1


class TestGetGrounding:
    """Test feature grounding retrieval."""

    def setup_method(self):
        self.service = FeatureAreaService()

    def test_grc_grounding(self):
        grounding = self.service.get_grounding('GRC')
        assert grounding.subsystem == 'Governance'
        assert 'grc-policy-propagator' in grounding.key_components
        assert 'open-cluster-management' in grounding.key_namespaces

    def test_search_grounding(self):
        grounding = self.service.get_grounding('Search')
        assert grounding.subsystem == 'Search'
        assert 'search-api' in grounding.key_components

    def test_clc_grounding(self):
        grounding = self.service.get_grounding('CLC')
        assert grounding.subsystem == 'Cluster Lifecycle'
        assert 'cluster-curator' in grounding.key_components

    def test_foundation_grounding(self):
        grounding = self.service.get_grounding('Foundation')
        assert grounding.subsystem == 'Foundation'
        assert 'registration-controller' in grounding.key_components
        assert 'work-agent' in grounding.key_components
        assert 'addon-manager' in grounding.key_components
        assert 'open-cluster-management-hub' in grounding.key_namespaces

    def test_install_grounding(self):
        grounding = self.service.get_grounding('Install')
        assert grounding.subsystem == 'Install'
        assert 'multiclusterhub-operator' in grounding.key_components
        assert 'hive-operator' in grounding.key_components
        assert 'multicluster-engine' in grounding.key_namespaces

    def test_unknown_grounding(self):
        grounding = self.service.get_grounding('NonExistent')
        assert grounding.subsystem == 'Unknown'
        assert grounding.key_components == []

    def test_all_known_areas_have_grounding(self):
        for area in FEATURE_AREAS:
            grounding = self.service.get_grounding(area)
            assert grounding.subsystem != 'Unknown', f"Area '{area}' has Unknown subsystem"
            assert len(grounding.key_components) > 0, f"Area '{area}' has no key_components"
            assert len(grounding.key_namespaces) > 0, f"Area '{area}' has no key_namespaces"


class TestSerialization:
    """Test dataclass serialization."""

    def test_feature_mapping_to_dict(self):
        service = FeatureAreaService()
        mapping = service.identify_feature_area(
            test_name='test_policy', test_file='cypress/e2e/governance/x.cy.ts'
        )
        d = service.to_dict(mapping)
        assert d['feature_area'] == 'GRC'
        assert d['confidence'] == 0.95

    def test_feature_grounding_to_dict(self):
        service = FeatureAreaService()
        grounding = service.get_grounding('Search')
        d = service.to_dict(grounding)
        assert d['subsystem'] == 'Search'
        assert 'search-api' in d['key_components']
