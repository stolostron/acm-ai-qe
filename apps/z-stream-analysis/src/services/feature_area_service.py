#!/usr/bin/env python3
"""
Feature Area Service

Identifies the feature area under test BEFORE analyzing failures.
Grounds every analysis in what feature is actually being tested
(GRC, Search, CLC, etc.) so the AI knows which subsystem, components,
and namespaces to investigate.

Used in Stage 1 gather (Step 8) to group tests by feature area
and provide grounding context in core-data.json.
"""

import re
import logging
from dataclasses import dataclass

from .shared_utils import dataclass_to_dict
from typing import Dict, Any, List, Optional


@dataclass
class FeatureGrounding:
    """Grounding context for a feature area."""
    subsystem: str
    key_components: List[str]
    key_namespaces: List[str]
    investigation_focus: str


@dataclass
class FeatureMapping:
    """Mapping of a test to its feature area with confidence."""
    test_name: str
    feature_area: str
    confidence: float
    identification_method: str  # path, name_pattern, component, console_url


@dataclass
class FeatureGrouping:
    """A group of tests in the same feature area."""
    feature_area: str
    grounding: FeatureGrounding
    tests: List[str]
    test_count: int = 0


# Feature area definitions - hardcoded knowledge base
FEATURE_AREAS: Dict[str, FeatureGrounding] = {
    'GRC': FeatureGrounding(
        subsystem='Governance',
        key_components=[
            'grc-policy-propagator', 'config-policy-controller',
            'governance-policy-framework', 'iam-policy-controller',
            'cert-policy-controller',
        ],
        key_namespaces=['open-cluster-management'],
        investigation_focus='Policy creation, propagation, compliance status, '
                          'policy templates, placement rules',
    ),
    'Search': FeatureGrounding(
        subsystem='Search',
        key_components=[
            'search-api', 'search-collector', 'search-indexer',
            'search-aggregator',
        ],
        key_namespaces=['open-cluster-management'],
        investigation_focus='Search query execution, result display, indexing, '
                          'saved searches, search suggestions',
    ),
    'CLC': FeatureGrounding(
        subsystem='Cluster Lifecycle',
        key_components=[
            'cluster-curator', 'cluster-curator-controller',
            'managedcluster-import-controller', 'cluster-manager',
            'hive-controllers',
        ],
        key_namespaces=[
            'open-cluster-management', 'hive',
            'open-cluster-management-hub',
        ],
        investigation_focus='Cluster creation, import, upgrade, destroy, '
                          'cluster pools, cluster sets, placements',
    ),
    'Observability': FeatureGrounding(
        subsystem='Observability',
        key_components=[
            'multicluster-observability-operator', 'thanos-query',
            'thanos-receive', 'grafana', 'metrics-collector',
        ],
        key_namespaces=[
            'open-cluster-management',
            'open-cluster-management-observability',
        ],
        investigation_focus='Metrics collection, dashboards, alerts, '
                          'Grafana panels, Thanos queries',
    ),
    'Virtualization': FeatureGrounding(
        subsystem='Virtualization',
        key_components=[
            'kubevirt-operator', 'virt-api', 'virt-controller',
            'virt-handler', 'hyperconverged-cluster-operator',
            'cdi-operator',
        ],
        key_namespaces=['openshift-cnv'],
        investigation_focus='VM creation, migration, snapshots, templates, '
                          'Fleet Virt UI, cross-cluster VM management',
    ),
    'Application': FeatureGrounding(
        subsystem='Application Lifecycle',
        key_components=[
            'application-manager', 'subscription-controller',
            'channel-controller', 'multicluster-operators-subscription',
        ],
        key_namespaces=['open-cluster-management'],
        investigation_focus='Application deployment, subscriptions, channels, '
                          'placement rules, ArgoCD integration',
    ),
    'Console': FeatureGrounding(
        subsystem='Console',
        key_components=['console-api', 'acm-console', 'mce-console'],
        key_namespaces=['open-cluster-management', 'multicluster-engine'],
        investigation_focus='Console UI rendering, navigation, header, '
                          'overview page, welcome page',
    ),
    'Foundation': FeatureGrounding(
        subsystem='Foundation',
        key_components=[
            'registration-controller', 'work-agent', 'cluster-proxy',
            'managed-serviceaccount', 'addon-manager', 'work-manager',
        ],
        key_namespaces=[
            'open-cluster-management', 'multicluster-engine',
            'open-cluster-management-agent', 'open-cluster-management-hub',
        ],
        investigation_focus='Addon health, managed cluster registration, '
                          'import strategies, cluster-proxy connectivity, '
                          'work-agent scheduling, managed-serviceaccount tokens',
    ),
    'Install': FeatureGrounding(
        subsystem='Install',
        key_components=[
            'multiclusterhub-operator', 'multicluster-engine',
            'hive-operator', 'assisted-service',
        ],
        key_namespaces=[
            'open-cluster-management', 'multicluster-engine',
            'hive', 'assisted-installer',
        ],
        investigation_focus='ACM/MCE CSV phase, operator installation sequence, '
                          'component enablement, CRD availability, image tag resolution',
    ),
    'Infrastructure': FeatureGrounding(
        subsystem='Infrastructure',
        key_components=[
            'klusterlet', 'foundation-controller',
        ],
        key_namespaces=[
            'open-cluster-management', 'multicluster-engine',
            'open-cluster-management-agent',
        ],
        investigation_focus='Agent connectivity, '
                          'foundation services, MCE components',
    ),
    'RBAC': FeatureGrounding(
        subsystem='RBAC',
        key_components=['console-api', 'acm-console'],
        key_namespaces=['open-cluster-management'],
        investigation_focus='Role assignments, user management, permissions, '
                          'cluster roles, namespace roles',
    ),
    'Automation': FeatureGrounding(
        subsystem='Automation',
        key_components=['aap-controller'],
        key_namespaces=['aap', 'ansible-automation-platform'],
        investigation_focus='Ansible automation templates, ClusterCurator hooks, '
                          'AAP integration, pre/post upgrade automation',
    ),
}

# Test file path patterns for feature area identification
_PATH_PATTERNS: List[tuple] = [
    (r'governance|grc|policy', 'GRC'),
    (r'search', 'Search'),
    (r'cluster|clc|create.*cluster|import.*cluster|upgrade', 'CLC'),
    (r'observ|metrics|grafana|thanos', 'Observability'),
    (r'virtual|vm|kubevirt|virt|fleet', 'Virtualization'),
    (r'app|application|subscription|channel|argo', 'Application'),
    (r'rbac|role|user.*management|permission', 'RBAC'),
    (r'automat|ansible|aap|template.*automat', 'Automation'),
    (r'console|overview|welcome|header', 'Console'),
    (r'install|csv|operator.*install', 'Install'),
    (r'server.?foundation|addon.?framework|registration|work.?agent', 'Foundation'),
    (r'infra|klusterlet|addon|foundation|mce', 'Infrastructure'),
]

# Test name patterns
_NAME_PATTERNS: List[tuple] = [
    (r'policy|compliance|govern|grc', 'GRC'),
    (r'search|query|saved.search', 'Search'),
    (r'cluster.*creat|cluster.*import|cluster.*upgrad|cluster.*destroy|'
     r'cluster.*pool|cluster.*set|hive|hypershift|placement', 'CLC'),
    (r'observ|metric|grafana|alert|dashboard', 'Observability'),
    (r'virtual.machine|vm.*creat|vm.*migrat|vm.*snapshot|kubevirt|fleet.virt',
     'Virtualization'),
    (r'application|subscription|channel|argo|deploy.*app', 'Application'),
    (r'rbac|role.assign|permission|user.manage', 'RBAC'),
    (r'automat.*template|ansible.*automat|aap.*integrat', 'Automation'),
    (r'console.*nav|overview.*page|welcome|header', 'Console'),
    (r'\[Install\]|\[install\]|csv.*phase|operator.*install|install.*acm|install.*mce', 'Install'),
    (r'\[ServerFoundation\]|\[addon-framework\]|\[registration\]|\[work-agent\]|'
     r'managedclusteraddon|managed.service.account', 'Foundation'),
    (r'addon|klusterlet|foundation|mce|infrastructure', 'Infrastructure'),
]

# Component name to feature area
_COMPONENT_TO_FEATURE: Dict[str, str] = {
    'grc-policy-propagator': 'GRC',
    'config-policy-controller': 'GRC',
    'governance-policy-framework': 'GRC',
    'iam-policy-controller': 'GRC',
    'cert-policy-controller': 'GRC',
    'policy-propagator': 'GRC',
    'search-api': 'Search',
    'search-collector': 'Search',
    'search-indexer': 'Search',
    'search-aggregator': 'Search',
    'search-operator': 'Search',
    'search-redisgraph': 'Search',
    'cluster-curator': 'CLC',
    'cluster-curator-controller': 'CLC',
    'managedcluster-import-controller': 'CLC',
    'cluster-manager': 'CLC',
    'hive': 'CLC',
    'hive-controllers': 'CLC',
    'hypershift-operator': 'CLC',
    'assisted-service': 'CLC',
    'observability-operator': 'Observability',
    'multicluster-observability-operator': 'Observability',
    'thanos-query': 'Observability',
    'grafana': 'Observability',
    'metrics-collector': 'Observability',
    'kubevirt-operator': 'Virtualization',
    'virt-api': 'Virtualization',
    'virt-controller': 'Virtualization',
    'hyperconverged-cluster-operator': 'Virtualization',
    'application-manager': 'Application',
    'subscription-controller': 'Application',
    'console-api': 'Console',
    'acm-console': 'Console',
    'mce-console': 'Console',
    'aap-controller': 'Automation',
    'registration-controller': 'Foundation',
    'work-agent': 'Foundation',
    'work-manager': 'Foundation',
    'cluster-proxy': 'Foundation',
    'managed-serviceaccount': 'Foundation',
    'addon-manager': 'Foundation',
    'multiclusterhub-operator': 'Install',
    'hive-operator': 'Install',
    'klusterlet': 'Infrastructure',
    'multicluster-engine': 'Infrastructure',
    'foundation-controller': 'Infrastructure',
}


class FeatureAreaService:
    """
    Identifies feature areas under test and provides grounding context.

    Usage:
        service = FeatureAreaService()
        area = service.identify_feature_area('test_policy_create', 'cypress/e2e/governance/policy.cy.ts')
        grounding = service.get_grounding('GRC')
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def identify_feature_area(
        self,
        test_name: str,
        test_file: Optional[str] = None,
        error_message: Optional[str] = None,
        detected_components: Optional[List[str]] = None,
    ) -> FeatureMapping:
        """
        Identify the feature area for a test.

        Identification priority (ordered by reliability):
        1. Test file path (most reliable)
        2. Test name patterns
        3. Detected components from error messages
        4. Error message content

        Returns:
            FeatureMapping with feature_area and confidence.
        """
        # 1. Test file path (highest reliability)
        if test_file:
            for pattern, area in _PATH_PATTERNS:
                if re.search(pattern, test_file, re.IGNORECASE):
                    return FeatureMapping(
                        test_name=test_name,
                        feature_area=area,
                        confidence=0.95,
                        identification_method='path',
                    )

        # 2. Test name patterns
        if test_name:
            for pattern, area in _NAME_PATTERNS:
                if re.search(pattern, test_name, re.IGNORECASE):
                    return FeatureMapping(
                        test_name=test_name,
                        feature_area=area,
                        confidence=0.85,
                        identification_method='name_pattern',
                    )

        # 3. Detected components
        if detected_components:
            for comp in detected_components:
                comp_lower = comp.lower()
                if comp_lower in _COMPONENT_TO_FEATURE:
                    return FeatureMapping(
                        test_name=test_name,
                        feature_area=_COMPONENT_TO_FEATURE[comp_lower],
                        confidence=0.80,
                        identification_method='component',
                    )

        # 4. Error message content (lowest reliability)
        if error_message:
            for pattern, area in _NAME_PATTERNS:
                if re.search(pattern, error_message, re.IGNORECASE):
                    return FeatureMapping(
                        test_name=test_name,
                        feature_area=area,
                        confidence=0.60,
                        identification_method='error_message',
                    )

        # Unknown
        return FeatureMapping(
            test_name=test_name,
            feature_area='Unknown',
            confidence=0.0,
            identification_method='none',
        )

    def group_tests_by_feature(
        self, failed_tests: List[Dict[str, Any]]
    ) -> Dict[str, FeatureGrouping]:
        """
        Group all failed tests by feature area.

        Args:
            failed_tests: List of test dicts from core-data.json
                          (each with test_name, class_name, etc.)

        Returns:
            Dict mapping feature_area -> FeatureGrouping
        """
        groups: Dict[str, List[str]] = {}

        for test in failed_tests:
            test_name = test.get('test_name', '')
            test_file = test.get('parsed_stack_trace', {}).get('root_cause_file') or \
                        test.get('parsed_stack_trace', {}).get('test_file') or \
                        test.get('class_name', '')
            error_message = test.get('error_message', '')
            detected = [
                c.get('name', '') for c in test.get('detected_components', [])
            ]

            mapping = self.identify_feature_area(
                test_name=test_name,
                test_file=test_file,
                error_message=error_message,
                detected_components=detected,
            )

            area = mapping.feature_area
            if area not in groups:
                groups[area] = []
            groups[area].append(test_name)

        # Build FeatureGrouping objects
        result = {}
        for area, tests in groups.items():
            grounding = self.get_grounding(area)
            result[area] = FeatureGrouping(
                feature_area=area,
                grounding=grounding,
                tests=tests,
                test_count=len(tests),
            )

        return result

    def get_grounding(self, feature_area: str) -> FeatureGrounding:
        """
        Get grounding context for a feature area.

        Returns:
            FeatureGrounding with subsystem, components, namespaces,
            and investigation focus.
        """
        if feature_area in FEATURE_AREAS:
            return FEATURE_AREAS[feature_area]

        # Unknown area
        return FeatureGrounding(
            subsystem='Unknown',
            key_components=[],
            key_namespaces=['open-cluster-management'],
            investigation_focus='General ACM feature investigation',
        )

    def to_dict(self, obj) -> Dict[str, Any]:
        """Convert dataclass to dict for serialization."""
        return dataclass_to_dict(obj)
