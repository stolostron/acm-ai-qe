"""
Unit tests for FeatureKnowledgeService.

Tests playbook loading, prerequisite checking, symptom matching,
feature readiness assessment, and KG fallback behavior.
"""

import os
import tempfile
import pytest
import yaml

from src.services.feature_knowledge_service import (
    FeatureKnowledgeService,
    PrerequisiteCheck,
    MatchedFailurePath,
    FeatureReadiness,
)


@pytest.fixture
def base_playbook_content():
    """Minimal base playbook for testing."""
    return {
        'profiles': {
            'Search': {
                'display_name': 'Search & Discovery',
                'docs_ref': 'rhacm-docs/observability/search',
                'architecture': {
                    'summary': 'Search indexes resources from spoke clusters.',
                    'data_flow': [
                        'search-collector collects resources',
                        'search-api serves queries',
                    ],
                    'key_insight': 'If search-collector addon is not running on a spoke, resources wont appear.',
                    'key_components': [
                        {
                            'name': 'search-api',
                            'role': 'Serves search queries',
                            'type': 'hub-deployment',
                            'namespace': 'open-cluster-management',
                            'pod_label': 'app=search-api',
                        },
                    ],
                },
                'prerequisites': [
                    {
                        'id': 'search-mch-component',
                        'type': 'mch_component',
                        'check_spec': {'component_name': 'search'},
                        'default_enabled': True,
                        'description': 'Search component enabled in MCH',
                    },
                    {
                        'id': 'search-collector-addon',
                        'type': 'addon',
                        'check_spec': {'addon_name': 'search-collector'},
                        'default_enabled': True,
                        'description': 'search-collector addon on spokes',
                    },
                ],
                'dependencies': ['Infrastructure'],
                'failure_paths': [
                    {
                        'id': 'search-disabled',
                        'description': 'Search disabled in MCH',
                        'category': 'prerequisite',
                        'symptoms': [
                            '(?i)search.*not found',
                            '(?i)search.*tab.*missing',
                        ],
                        'prerequisite_id': 'search-mch-component',
                        'investigation': [
                            {
                                'step': 'Check MCH',
                                'command': "oc get mch -A -o jsonpath='{...}'",
                                'expect': 'search enabled',
                                'if_not': 'Search is disabled',
                            },
                        ],
                        'classification': 'NO_BUG',
                        'confidence': 0.95,
                        'explanation': 'Search is intentionally disabled.',
                    },
                    {
                        'id': 'search-api-down',
                        'description': 'search-api pod crashed',
                        'category': 'component_health',
                        'symptoms': [
                            '(?i)500.*search',
                            '(?i)search.*error',
                        ],
                        'investigation': [],
                        'classification': 'INFRASTRUCTURE',
                        'confidence': 0.85,
                        'explanation': 'search-api is down.',
                    },
                    {
                        'id': 'search-index-stale',
                        'description': 'Indexer lag',
                        'category': 'data_flow',
                        'symptoms': [
                            '(?i)no results.*found',
                        ],
                        'investigation': [],
                        'classification': 'PRODUCT_BUG',
                        'confidence': 0.75,
                        'explanation': 'Search indexer has lag.',
                    },
                ],
            },
            'Infrastructure': {
                'display_name': 'Infrastructure Foundation',
                'architecture': {
                    'summary': 'Foundation layer.',
                    'key_insight': 'Infrastructure failures cascade.',
                },
                'prerequisites': [
                    {
                        'id': 'mce-installed',
                        'type': 'operator',
                        'check_spec': {'operator_name': 'multicluster-engine'},
                        'default_enabled': True,
                        'description': 'MCE operator installed',
                    },
                ],
                'dependencies': [],
                'failure_paths': [],
            },
        },
    }


@pytest.fixture
def version_playbook_content():
    """Minimal version-specific playbook for testing."""
    return {
        'profiles': {
            'RBAC': {
                'display_name': 'Fine-Grained RBAC',
                'architecture': {
                    'summary': 'Fine-grained RBAC extends Kubernetes RBAC.',
                    'key_insight': 'fine-grained-rbac-preview is disabled by default.',
                },
                'prerequisites': [
                    {
                        'id': 'rbac-mch-component',
                        'type': 'mch_component',
                        'check_spec': {'component_name': 'fine-grained-rbac-preview'},
                        'default_enabled': False,
                        'description': 'fine-grained-rbac-preview MCH component',
                    },
                    {
                        'id': 'idp-configured',
                        'type': 'informational',
                        'check_spec': {},
                        'default_enabled': True,
                        'description': 'IDP configured on hub',
                    },
                ],
                'dependencies': ['Console'],
                'failure_paths': [
                    {
                        'id': 'rbac-flag-disabled',
                        'description': 'MCH component off',
                        'category': 'prerequisite',
                        'symptoms': [
                            '(?i)user.*management.*not found',
                            '(?i)user.*management.*timeout',
                        ],
                        'prerequisite_id': 'rbac-mch-component',
                        'investigation': [],
                        'classification': 'NO_BUG',
                        'confidence': 0.95,
                        'explanation': 'RBAC flag disabled.',
                    },
                ],
            },
        },
    }


@pytest.fixture
def playbook_dir(base_playbook_content, version_playbook_content):
    """Create a temporary directory with playbook YAML files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = os.path.join(tmpdir, 'base.yaml')
        with open(base_path, 'w') as f:
            yaml.dump(base_playbook_content, f)

        version_path = os.path.join(tmpdir, 'acm-2.16.yaml')
        with open(version_path, 'w') as f:
            yaml.dump(version_playbook_content, f)

        yield tmpdir


class TestPlaybookLoading:
    """Test playbook loading and merging."""

    def test_load_base_playbooks(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        profiles = service.load_playbooks()
        assert 'Search' in profiles
        assert 'Infrastructure' in profiles
        assert len(profiles) == 2

    def test_load_with_version_overlay(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        profiles = service.load_playbooks(acm_version='2.16')
        assert 'Search' in profiles
        assert 'Infrastructure' in profiles
        assert 'RBAC' in profiles
        assert len(profiles) == 3

    def test_load_nonexistent_version(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        profiles = service.load_playbooks(acm_version='2.99')
        # Should still load base profiles
        assert 'Search' in profiles
        assert 'RBAC' not in profiles

    def test_filter_feature_areas(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        profiles = service.load_playbooks(
            acm_version='2.16',
            feature_areas=['Search', 'RBAC'],
        )
        assert 'Search' in profiles
        assert 'RBAC' in profiles
        assert 'Infrastructure' not in profiles

    def test_filter_case_insensitive(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        profiles = service.load_playbooks(feature_areas=['search'])
        assert 'Search' in profiles

    def test_filter_unknown_area(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        profiles = service.load_playbooks(feature_areas=['Nonexistent'])
        assert len(profiles) == 0

    def test_load_from_nonexistent_dir(self):
        service = FeatureKnowledgeService(data_dir='/nonexistent/path')
        profiles = service.load_playbooks()
        assert len(profiles) == 0


class TestPrerequisiteChecking:
    """Test prerequisite checking against MCH components."""

    def test_mch_component_enabled(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        checks = service.check_prerequisites(
            'Search',
            mch_components={'search': True},
        )
        mch_check = next(c for c in checks if c.type == 'mch_component')
        assert mch_check.met is True
        assert 'enabled' in mch_check.detail

    def test_mch_component_disabled(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        checks = service.check_prerequisites(
            'Search',
            mch_components={'search': False},
        )
        mch_check = next(c for c in checks if c.type == 'mch_component')
        assert mch_check.met is False
        assert 'disabled' in mch_check.detail

    def test_mch_component_not_in_overrides_uses_default(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        # Search has default_enabled=True, so if not in overrides, should be True
        checks = service.check_prerequisites(
            'Search',
            mch_components={'other-component': True},
        )
        mch_check = next(c for c in checks if c.type == 'mch_component')
        assert mch_check.met is True
        assert 'default' in mch_check.detail

    def test_rbac_default_disabled(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks(acm_version='2.16')
        # RBAC has default_enabled=False
        checks = service.check_prerequisites(
            'RBAC',
            mch_components={'other-component': True},
        )
        mch_check = next(c for c in checks if c.type == 'mch_component')
        assert mch_check.met is False
        assert 'default=False' in mch_check.detail

    def test_addon_returns_none(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        checks = service.check_prerequisites(
            'Search',
            mch_components={'search': True},
        )
        addon_check = next(c for c in checks if c.type == 'addon')
        assert addon_check.met is None
        assert 'live cluster check' in addon_check.detail

    def test_informational_returns_none(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks(acm_version='2.16')
        checks = service.check_prerequisites('RBAC')
        info_check = next(c for c in checks if c.type == 'informational')
        assert info_check.met is None
        assert 'Informational' in info_check.detail

    def test_no_mch_components_available(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        checks = service.check_prerequisites('Search')
        mch_check = next(c for c in checks if c.type == 'mch_component')
        assert mch_check.met is None

    def test_unknown_feature_area(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        checks = service.check_prerequisites('Nonexistent')
        assert checks == []


class TestSymptomMatching:
    """Test error message matching against failure path symptom regexes."""

    def test_match_search_disabled(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        matches = service.match_symptoms(
            'Search',
            ['The search tab was not found in the UI'],
        )
        assert len(matches) == 1
        assert matches[0].path_id == 'search-disabled'
        assert matches[0].suggested_classification == 'NO_BUG'
        assert matches[0].confidence == 0.95

    def test_match_search_api_error(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        matches = service.match_symptoms(
            'Search',
            ['Got 500 error from search endpoint'],
        )
        assert len(matches) == 1
        assert matches[0].path_id == 'search-api-down'
        assert matches[0].suggested_classification == 'INFRASTRUCTURE'

    def test_match_rbac_timeout(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks(acm_version='2.16')
        matches = service.match_symptoms(
            'RBAC',
            ['Timed out waiting for User management page timeout'],
        )
        assert len(matches) == 1
        assert matches[0].path_id == 'rbac-flag-disabled'
        assert matches[0].suggested_classification == 'NO_BUG'

    def test_no_match(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        matches = service.match_symptoms(
            'Search',
            ['Some completely unrelated error message'],
        )
        assert len(matches) == 0

    def test_match_multiple_paths(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        matches = service.match_symptoms(
            'Search',
            [
                'Search tab not found',
                '500 error from search api',
                'no results found for query',
            ],
        )
        # Should match multiple failure paths
        assert len(matches) >= 2

    def test_unknown_feature_area(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        matches = service.match_symptoms('Nonexistent', ['error'])
        assert matches == []

    def test_empty_error_messages(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        matches = service.match_symptoms('Search', [])
        assert matches == []


class TestFeatureReadiness:
    """Test combined readiness assessment."""

    def test_readiness_with_unmet_prerequisite(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks(acm_version='2.16')
        readiness = service.get_feature_readiness(
            'RBAC',
            mch_components={'other': True},  # RBAC flag not present
            error_messages=['User management not found'],
        )
        assert readiness.feature_area == 'RBAC'
        assert readiness.all_prerequisites_met is False
        assert len(readiness.unmet_prerequisites) >= 1
        assert len(readiness.pre_matched_paths) >= 1

    def test_readiness_all_met(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        readiness = service.get_feature_readiness(
            'Search',
            mch_components={'search': True},
        )
        assert readiness.all_prerequisites_met is True
        assert len(readiness.unmet_prerequisites) == 0

    def test_readiness_includes_architecture(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        readiness = service.get_feature_readiness('Search')
        assert 'indexes resources' in readiness.architecture_summary
        assert 'search-collector' in readiness.key_insight

    def test_readiness_unknown_feature(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        readiness = service.get_feature_readiness('Nonexistent')
        assert readiness.feature_area == 'Nonexistent'
        assert readiness.all_prerequisites_met is None
        assert readiness.prerequisite_checks == []


class TestInvestigationPlaybook:
    """Test investigation playbook retrieval."""

    def test_get_playbook(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        playbook = service.get_investigation_playbook('Search')
        assert playbook is not None
        assert playbook['display_name'] == 'Search & Discovery'
        assert 'architecture' in playbook
        assert 'failure_paths' in playbook
        assert len(playbook['failure_paths']) == 3

    def test_get_playbook_nonexistent(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        playbook = service.get_investigation_playbook('Nonexistent')
        assert playbook is None


class TestSerialization:
    """Test dataclass serialization."""

    def test_to_dict_prerequisite_check(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        check = PrerequisiteCheck(
            id='test', type='mch_component',
            description='Test', met=True, detail='ok',
        )
        result = service.to_dict(check)
        assert result['id'] == 'test'
        assert result['met'] is True

    def test_to_dict_feature_readiness(self, playbook_dir):
        service = FeatureKnowledgeService(data_dir=playbook_dir)
        service.load_playbooks()
        readiness = service.get_feature_readiness(
            'Search', mch_components={'search': True},
        )
        result = service.to_dict(readiness)
        assert result['feature_area'] == 'Search'
        assert isinstance(result['prerequisite_checks'], list)


class TestRealPlaybooks:
    """Test against the actual playbook files shipped with the codebase."""

    def test_load_real_base_playbook(self):
        """Verify the real base.yaml parses and has expected profiles."""
        service = FeatureKnowledgeService()
        profiles = service.load_playbooks()
        expected = {'Search', 'GRC', 'CLC', 'Application', 'Console', 'Infrastructure'}
        assert expected.issubset(set(profiles.keys()))

    def test_load_real_version_playbook(self):
        """Verify the real acm-2.16.yaml parses and has expected profiles."""
        service = FeatureKnowledgeService()
        profiles = service.load_playbooks(acm_version='2.16')
        expected = {'RBAC', 'Virtualization', 'CrossClusterMigration', 'Observability'}
        assert expected.issubset(set(profiles.keys()))

    def test_real_search_prerequisite(self):
        """Verify Search prerequisite checking works with real playbook."""
        service = FeatureKnowledgeService()
        service.load_playbooks()
        checks = service.check_prerequisites(
            'Search',
            mch_components={'search': True},
        )
        assert len(checks) >= 1
        mch_check = next(c for c in checks if c.type == 'mch_component')
        assert mch_check.met is True

    def test_real_rbac_flag_disabled(self):
        """RBAC without fine-grained-rbac-preview -> unmet prerequisite."""
        service = FeatureKnowledgeService()
        service.load_playbooks(acm_version='2.16')
        readiness = service.get_feature_readiness(
            'RBAC',
            mch_components={},  # Flag not in overrides, default=false
        )
        assert readiness.all_prerequisites_met is False
        assert any('fine-grained' in u for u in readiness.unmet_prerequisites)

    def test_real_search_symptom_match(self):
        """Search error matching 'no results found' -> correct path."""
        service = FeatureKnowledgeService()
        service.load_playbooks()
        matches = service.match_symptoms(
            'Search',
            ['Expected resource not found in search results'],
        )
        # Should match search-index-stale or collector-not-on-spoke
        assert len(matches) >= 1


# ── Gap Detection Tests (v4.0) ──


class TestDetectStaleComponents:
    """Test stale component detection between playbooks and components.yaml."""

    def test_detects_component_not_in_knowledge(self, tmp_path):
        """Components in base.yaml not in components.yaml are flagged."""
        service = FeatureKnowledgeService()
        service.profiles = {
            'Search': {
                'architecture': {
                    'key_components': [
                        {'name': 'search-api', 'namespace': '{mch_ns}'},
                        {'name': 'nonexistent-widget', 'namespace': '{mch_ns}'},
                    ]
                }
            }
        }
        # Create a components.yaml with only search-api
        comp_file = tmp_path / 'components.yaml'
        comp_file.write_text(yaml.dump({
            'components': {
                'search-api': {'subsystem': 'Search', 'type': 'deployment'},
            }
        }))
        stale = service.detect_stale_components(comp_file)
        assert len(stale) == 1
        assert stale[0]['component'] == 'nonexistent-widget'
        assert stale[0]['profile'] == 'Search'

    def test_no_stale_when_all_match(self, tmp_path):
        """No stale components when all match."""
        service = FeatureKnowledgeService()
        service.profiles = {
            'Search': {
                'architecture': {
                    'key_components': [
                        {'name': 'search-api', 'namespace': '{mch_ns}'},
                    ]
                }
            }
        }
        comp_file = tmp_path / 'components.yaml'
        comp_file.write_text(yaml.dump({
            'components': {
                'search-api': {'subsystem': 'Search', 'type': 'deployment'},
            }
        }))
        stale = service.detect_stale_components(comp_file)
        assert len(stale) == 0

    def test_missing_components_file(self):
        """Returns empty if components.yaml doesn't exist."""
        service = FeatureKnowledgeService()
        from pathlib import Path
        stale = service.detect_stale_components(Path('/nonexistent/path.yaml'))
        assert stale == []

    def test_real_playbooks_against_real_components(self):
        """Real base.yaml vs real components.yaml — should find some mismatches."""
        service = FeatureKnowledgeService()
        service.load_playbooks()
        from pathlib import Path
        stale = service.detect_stale_components(
            Path('knowledge/components.yaml')
        )
        # Some naming mismatches expected (cluster-curator vs cluster-curator-controller)
        assert isinstance(stale, list)
        # Search should not have search-redisgraph anymore
        stale_names = [s['component'] for s in stale]
        assert 'search-redisgraph' not in stale_names


class TestDetectHardcodedNamespaces:
    """Test hardcoded namespace detection in investigation commands."""

    def test_detects_hardcoded_namespace(self):
        """Flags literal namespaces in oc commands."""
        service = FeatureKnowledgeService()
        service.profiles = {
            'Search': {
                'failure_paths': [{
                    'id': 'test-path',
                    'investigation': [{
                        'step': 'Check pods',
                        'command': 'oc get pods -n my-custom-ns -l app=search-api',
                    }]
                }]
            }
        }
        hardcoded = service.detect_hardcoded_namespaces()
        assert len(hardcoded) == 1
        assert hardcoded[0]['namespace'] == 'my-custom-ns'

    def test_ignores_parameterized_namespace(self):
        """Parameterized {mch_ns} should not be flagged."""
        service = FeatureKnowledgeService()
        service.profiles = {
            'Search': {
                'failure_paths': [{
                    'id': 'test-path',
                    'investigation': [{
                        'step': 'Check pods',
                        'command': 'oc get pods -n {mch_ns} -l app=search-api',
                    }]
                }]
            }
        }
        hardcoded = service.detect_hardcoded_namespaces()
        assert len(hardcoded) == 0

    def test_ignores_known_fixed_namespaces(self):
        """Fixed namespaces like multicluster-engine should not be flagged."""
        service = FeatureKnowledgeService()
        service.profiles = {
            'CLC': {
                'failure_paths': [{
                    'id': 'test-path',
                    'investigation': [{
                        'step': 'Check hive',
                        'command': 'oc get pods -n hive -l app=hive-controllers',
                    }]
                }]
            }
        }
        hardcoded = service.detect_hardcoded_namespaces()
        assert len(hardcoded) == 0

    def test_real_playbooks_no_hardcoded(self):
        """After namespace parameterization, real playbooks should have 0 hardcoded."""
        service = FeatureKnowledgeService()
        service.load_playbooks()
        hardcoded = service.detect_hardcoded_namespaces()
        assert len(hardcoded) == 0


class TestDetectMissingOverlay:
    """Test missing version overlay detection."""

    def test_detects_missing_overlay(self):
        """Returns filename when overlay doesn't exist."""
        service = FeatureKnowledgeService()
        result = service.detect_missing_overlay('2.17')
        assert result == 'acm-2.17.yaml'

    def test_existing_overlay(self):
        """Returns None when overlay exists."""
        service = FeatureKnowledgeService()
        result = service.detect_missing_overlay('2.16')
        assert result is None

    def test_no_version(self):
        """Returns None when version is unknown."""
        service = FeatureKnowledgeService()
        result = service.detect_missing_overlay(None)
        assert result is None


class TestCountUnmatchedErrors:
    """Test error message match counting."""

    def test_counts_matched_and_unmatched(self):
        """Correct counts for mixed matched/unmatched errors."""
        service = FeatureKnowledgeService()
        service.profiles = {
            'Search': {
                'failure_paths': [{
                    'id': 'search-api-down',
                    'symptoms': ['(?i)500.*search'],
                }]
            }
        }
        result = service.count_unmatched_errors('Search', [
            'Got 500 error from search',  # matches
            'Element not found: .pf-tree',  # no match
            'Timeout waiting for page',  # no match
        ])
        assert result['total_errors'] == 3
        assert result['matched_count'] == 1
        assert result['unmatched_count'] == 2
        assert result['match_rate'] == pytest.approx(0.333, abs=0.01)

    def test_empty_errors(self):
        """Handles empty error list."""
        service = FeatureKnowledgeService()
        service.profiles = {'Search': {'failure_paths': []}}
        result = service.count_unmatched_errors('Search', [])
        assert result['total_errors'] == 0
        assert result['match_rate'] == 0.0

    def test_unknown_profile(self):
        """Unknown profile returns all unmatched."""
        service = FeatureKnowledgeService()
        service.profiles = {}
        result = service.count_unmatched_errors('Unknown', ['some error'])
        assert result['unmatched_count'] == 1


class TestRunGapDetection:
    """Test the combined gap detection runner."""

    def test_runs_all_checks(self, tmp_path):
        """Runs all gap detection checks and returns combined results."""
        service = FeatureKnowledgeService()
        service.profiles = {
            'Search': {
                'architecture': {
                    'key_components': [
                        {'name': 'search-api', 'namespace': '{mch_ns}'},
                    ]
                },
                'failure_paths': [{
                    'id': 'test',
                    'symptoms': ['(?i)500.*search'],
                    'investigation': [{
                        'step': 'test',
                        'command': 'oc get pods -n {mch_ns}',
                    }]
                }]
            }
        }
        comp_file = tmp_path / 'components.yaml'
        comp_file.write_text(yaml.dump({
            'components': {
                'search-api': {'subsystem': 'Search', 'type': 'deployment'},
            }
        }))

        result = service.run_gap_detection(
            acm_version='2.17',
            feature_areas_with_errors={'Search': ['Element not found: .pf-tree']},
            components_path=comp_file,
        )
        assert 'stale_components' in result
        assert 'hardcoded_namespaces' in result
        assert 'missing_overlay' in result
        assert 'match_rates' in result
        assert 'overall_match_rate' in result
        assert 'gap_areas' in result
        # Search has 0 matches for this error
        assert result['match_rates']['Search']['matched_count'] == 0
        assert 'Search' in result['gap_areas']
