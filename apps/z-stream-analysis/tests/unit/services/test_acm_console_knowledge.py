#!/usr/bin/env python3
"""
Unit tests for ACM Console Knowledge Service
"""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from src.services.acm_console_knowledge import ACMConsoleKnowledge


class TestFeatureMapping:
    """Tests for feature area mapping."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_map_cluster_test(self):
        """Test mapping cluster-related tests."""
        result = self.service.map_test_to_feature(
            "cypress/e2e/clusters/managedCluster.spec.js"
        )
        assert result in ["clusters", "managedcluster"]

    def test_map_managed_cluster_test(self):
        """Test mapping managed cluster tests."""
        result = self.service.map_test_to_feature(
            "test_create_managedcluster"
        )
        assert result == "managedcluster"

    def test_map_clusterset_test(self):
        """Test mapping clusterset tests."""
        result = self.service.map_test_to_feature(
            "test_clusterset_binding"
        )
        assert result == "clusterset"

    def test_map_clusterpool_test(self):
        """Test mapping clusterpool tests."""
        result = self.service.map_test_to_feature(
            "cypress/e2e/clusters/cluster-pool.spec.ts"
        )
        assert result == "clusterpool"

    def test_map_policy_test(self):
        """Test mapping policy tests."""
        result = self.service.map_test_to_feature(
            "cypress/e2e/policies/createPolicy.spec.ts"
        )
        assert result == "policy"

    def test_map_governance_test(self):
        """Test mapping governance tests."""
        result = self.service.map_test_to_feature(
            "test_governance_check"
        )
        assert result == "governance"

    def test_map_application_test(self):
        """Test mapping application tests."""
        result = self.service.map_test_to_feature(
            "cypress/e2e/applications/subscription.spec.js"
        )
        assert result == "application"

    def test_map_credential_test(self):
        """Test mapping credential tests."""
        result = self.service.map_test_to_feature(
            "test_create_credential"
        )
        assert result == "credential"

    def test_map_ansible_test(self):
        """Test mapping ansible/automation tests."""
        result = self.service.map_test_to_feature(
            "test_ansible_automation"
        )
        assert result == "ansible"

    def test_map_vm_test(self):
        """Test mapping virtual machine tests."""
        result = self.service.map_test_to_feature(
            "test_create_virtualmachine"
        )
        assert result == "virtualmachine"

    def test_map_search_test(self):
        """Test mapping search tests."""
        result = self.service.map_test_to_feature(
            "cypress/e2e/search/search-queries.spec.ts"
        )
        assert result == "search"

    def test_map_unknown_test(self):
        """Test unmapped tests return None."""
        result = self.service.map_test_to_feature(
            "test_some_random_feature"
        )
        assert result is None

    def test_map_empty_test(self):
        """Test empty test name returns None."""
        result = self.service.map_test_to_feature("")
        assert result is None

    def test_map_none_test(self):
        """Test None test name returns None."""
        result = self.service.map_test_to_feature(None)
        assert result is None


class TestDirectoryMapping:
    """Tests for directory mapping."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_cluster_test_returns_infrastructure_path(self):
        """Test cluster tests return Infrastructure directory."""
        result = self.service.get_relevant_directories(
            "test_create_cluster",
            "Timed out waiting for element: #create-btn"
        )
        assert result['primary_route'] is not None
        assert 'Infrastructure/Clusters' in result['primary_route']

    def test_policy_test_returns_governance_path(self):
        """Test policy tests return Governance directory."""
        result = self.service.get_relevant_directories(
            "test_create_policy",
            ""
        )
        assert result['primary_route'] is not None
        assert 'Governance' in result['primary_route']

    def test_always_includes_ui_components(self):
        """Test that UI components directory is always included."""
        result = self.service.get_relevant_directories(
            "test_any_test",
            ""
        )
        assert 'ui_components' in result
        assert 'ui-components' in result['ui_components']

    def test_always_includes_shared_components(self):
        """Test that shared components directory is always included."""
        result = self.service.get_relevant_directories(
            "test_any_test",
            ""
        )
        assert 'shared_components' in result

    def test_modal_error_adds_hint(self):
        """Test modal errors add look_for hint."""
        result = self.service.get_relevant_directories(
            "test_create_cluster",
            "Cannot find modal element"
        )
        assert 'look_for' in result
        assert 'AcmModal' in result['look_for']

    def test_table_error_adds_hint(self):
        """Test table errors add look_for hint."""
        result = self.service.get_relevant_directories(
            "test_list_clusters",
            "Table row not found"
        )
        assert 'look_for' in result
        assert 'AcmTable' in result['look_for']

    def test_form_error_adds_wizard(self):
        """Test form/wizard errors add wizard directory."""
        result = self.service.get_relevant_directories(
            "test_create_cluster",
            "Form wizard step failed"
        )
        assert 'wizard' in result
        assert 'react-form-wizard' in result['wizard']

    def test_cluster_features_add_plugins(self):
        """Test cluster features add plugin paths."""
        result = self.service.get_relevant_directories(
            "test_managedcluster_create",
            ""
        )
        assert 'acm_plugin' in result
        assert 'mce_plugin' in result


class TestPatternFlyExtraction:
    """Tests for PatternFly version extraction."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_extract_pf_version_from_package_json(self):
        """Test extracting PatternFly versions from package.json."""
        with TemporaryDirectory() as tmpdir:
            # Create mock console repo structure
            frontend_dir = Path(tmpdir) / "frontend"
            frontend_dir.mkdir()

            package_json = {
                "name": "console",
                "dependencies": {
                    "@patternfly/react-core": "^4.276.0",
                    "@patternfly/react-table": "^4.113.0",
                    "react": "^17.0.2"
                },
                "devDependencies": {
                    "@patternfly/react-icons": "^4.93.0"
                }
            }

            (frontend_dir / "package.json").write_text(json.dumps(package_json))

            result = self.service.extract_patternfly_version(Path(tmpdir))

            assert result is not None
            assert "@patternfly/react-core" in result
            assert "@patternfly/react-table" in result
            assert "@patternfly/react-icons" in result
            assert "react" not in result

    def test_extract_pf_version_no_package_json(self):
        """Test extraction when no package.json exists."""
        with TemporaryDirectory() as tmpdir:
            result = self.service.extract_patternfly_version(Path(tmpdir))
            assert result is None

    def test_extract_pf_version_no_pf_deps(self):
        """Test extraction when no PatternFly dependencies exist."""
        with TemporaryDirectory() as tmpdir:
            frontend_dir = Path(tmpdir) / "frontend"
            frontend_dir.mkdir()

            package_json = {
                "name": "console",
                "dependencies": {
                    "react": "^17.0.2",
                    "lodash": "^4.17.21"
                }
            }

            (frontend_dir / "package.json").write_text(json.dumps(package_json))

            result = self.service.extract_patternfly_version(Path(tmpdir))
            assert result is None


class TestStructureValidation:
    """Tests for structure validation."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_validate_structure_all_present(self):
        """Test validation when all directories exist."""
        with TemporaryDirectory() as tmpdir:
            console_path = Path(tmpdir)

            # Create expected directories
            for rel_path in self.service.DIRECTORY_STRUCTURE.values():
                (console_path / rel_path).mkdir(parents=True, exist_ok=True)

            result = self.service.validate_structure(console_path)

            for name, exists in result.items():
                assert exists is True, f"Directory {name} should exist"

    def test_validate_structure_none_present(self):
        """Test validation when no directories exist."""
        with TemporaryDirectory() as tmpdir:
            result = self.service.validate_structure(Path(tmpdir))

            for name, exists in result.items():
                assert exists is False, f"Directory {name} should not exist"

    def test_validate_structure_partial(self):
        """Test validation with partial directory structure."""
        with TemporaryDirectory() as tmpdir:
            console_path = Path(tmpdir)

            # Only create ui_components
            ui_comp_path = self.service.DIRECTORY_STRUCTURE['ui_components']
            (console_path / ui_comp_path).mkdir(parents=True, exist_ok=True)

            result = self.service.validate_structure(console_path)

            assert result['ui_components'] is True
            assert result['routes'] is False


class TestInvestigationPaths:
    """Tests for investigation path generation."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_cluster_feature_paths(self):
        """Test investigation paths for cluster feature."""
        paths = self.service.get_investigation_paths(
            "clusters",
            "element_not_found"
        )

        assert len(paths) > 0
        assert any("Clusters" in p for p in paths)
        assert any("ui-components" in p for p in paths)

    def test_element_not_found_includes_components(self):
        """Test element_not_found failures include component directories."""
        paths = self.service.get_investigation_paths(
            "policy",
            "element_not_found"
        )

        assert any("ui-components" in p for p in paths)
        assert any("components" in p for p in paths)

    def test_timeout_includes_lib(self):
        """Test timeout failures include lib directory."""
        paths = self.service.get_investigation_paths(
            "clusters",
            "timeout"
        )

        assert any("lib" in p for p in paths)

    def test_assertion_includes_sdk(self):
        """Test assertion failures include SDK directory."""
        paths = self.service.get_investigation_paths(
            "clusters",
            "assertion"
        )

        assert any("multicluster-sdk" in p for p in paths)

    def test_vm_includes_kubevirt_paths(self):
        """Test VM features include kubevirt-plugin directories."""
        paths = self.service.get_investigation_paths(
            "vm",
            "element_not_found"
        )

        # VM features should include kubevirt-plugin paths, not ACM/MCE plugins
        assert any("src/" in p for p in paths)
        assert any("views/" in p for p in paths)


class TestSelectorExtraction:
    """Tests for selector extraction from errors."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_extract_cypress_get_selector(self):
        """Test extracting selector from Cypress get() error."""
        error = "Timed out retrying after 4000ms: get('#create-btn')"
        result = self.service.extract_selector_from_error(error)
        assert result == "#create-btn"

    def test_extract_cypress_find_selector(self):
        """Test extracting selector from Cypress find() error."""
        error = "Timed out retrying after 4000ms: find('[data-testid=\"submit\"]')"
        result = self.service.extract_selector_from_error(error)
        assert result is not None
        assert "submit" in result or "data-testid" in result

    def test_extract_element_selector(self):
        """Test extracting selector from element error."""
        error = "Expected to find element: #cluster-table"
        result = self.service.extract_selector_from_error(error)
        assert result == "#cluster-table"

    def test_extract_from_empty_error(self):
        """Test extraction from empty error message."""
        result = self.service.extract_selector_from_error("")
        assert result is None

    def test_extract_from_none(self):
        """Test extraction from None."""
        result = self.service.extract_selector_from_error(None)
        assert result is None


class TestSearchPatternSuggestion:
    """Tests for search pattern suggestion."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_id_selector_patterns(self):
        """Test patterns for ID selector."""
        patterns = self.service.suggest_search_patterns("#my-button")

        assert 'id="my-button"' in patterns
        assert "id='my-button'" in patterns
        assert 'data-testid="my-button"' in patterns

    def test_attribute_selector_patterns(self):
        """Test patterns for attribute selector."""
        patterns = self.service.suggest_search_patterns("[data-testid='submit']")

        assert 'data-testid="submit"' in patterns
        assert "data-testid='submit'" in patterns

    def test_class_selector_patterns(self):
        """Test patterns for class selector."""
        patterns = self.service.suggest_search_patterns(".pf-c-button")

        assert any("className" in p for p in patterns)
        assert any("pf-c-button" in p for p in patterns)

    def test_fallback_for_unknown(self):
        """Test fallback for unknown selector format."""
        patterns = self.service.suggest_search_patterns("some-random-text")

        assert len(patterns) > 0
        assert "some-random-text" in patterns


class TestConsoleStructureConstants:
    """Tests for console structure constants."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_directory_structure_not_empty(self):
        """Test directory structure is defined."""
        structure = self.service.get_console_structure()
        assert len(structure) > 0
        assert 'ui_components' in structure
        assert 'routes' in structure

    def test_feature_routes_not_empty(self):
        """Test feature routes are defined."""
        routes = self.service.get_feature_routes()
        assert len(routes) > 0
        assert 'clusters' in routes
        assert 'policy' in routes

    def test_structure_returns_copy(self):
        """Test get_console_structure returns a copy."""
        structure1 = self.service.get_console_structure()
        structure2 = self.service.get_console_structure()
        structure1['new_key'] = 'value'
        assert 'new_key' not in structure2

    def test_routes_returns_copy(self):
        """Test get_feature_routes returns a copy."""
        routes1 = self.service.get_feature_routes()
        routes2 = self.service.get_feature_routes()
        routes1['new_key'] = 'value'
        assert 'new_key' not in routes2


class TestKubeVirtIntegration:
    """Tests for KubeVirt plugin repository integration."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_map_kubevirt_test(self):
        """Test mapping kubevirt-related tests."""
        result = self.service.map_test_to_feature(
            "test_kubevirt_virtualization"
        )
        assert result == "kubevirt"

    def test_map_virtualmachine_test(self):
        """Test mapping virtualmachine tests."""
        result = self.service.map_test_to_feature(
            "test_create_virtualmachine"
        )
        assert result == "virtualmachine"

    def test_map_vm_test_pattern(self):
        """Test mapping vm-prefixed tests."""
        result = self.service.map_test_to_feature(
            "test_vm_lifecycle"
        )
        assert result == "vm"

    def test_kubevirt_features_set(self):
        """Test KUBEVIRT_FEATURES contains expected values."""
        assert 'vm' in self.service.KUBEVIRT_FEATURES
        assert 'virtualmachine' in self.service.KUBEVIRT_FEATURES
        assert 'kubevirt' in self.service.KUBEVIRT_FEATURES

    def test_requires_kubevirt_repo_true(self):
        """Test requires_kubevirt_repo returns True for VM tests."""
        assert self.service.requires_kubevirt_repo("test_kubevirt_create") is True
        assert self.service.requires_kubevirt_repo("test_virtualmachine_delete") is True
        assert self.service.requires_kubevirt_repo("test_vm_lifecycle") is True

    def test_requires_kubevirt_repo_false(self):
        """Test requires_kubevirt_repo returns False for non-VM tests."""
        assert self.service.requires_kubevirt_repo("test_create_cluster") is False
        assert self.service.requires_kubevirt_repo("test_policy_create") is False
        assert self.service.requires_kubevirt_repo("test_application") is False

    def test_requires_kubevirt_repo_empty(self):
        """Test requires_kubevirt_repo returns False for empty input."""
        assert self.service.requires_kubevirt_repo("") is False
        assert self.service.requires_kubevirt_repo(None) is False

    def test_get_kubevirt_structure(self):
        """Test get_kubevirt_structure returns structure."""
        structure = self.service.get_kubevirt_structure()
        assert 'src' in structure
        assert 'views' in structure
        assert 'components' in structure
        assert structure['src'] == 'src/'

    def test_get_kubevirt_structure_returns_copy(self):
        """Test get_kubevirt_structure returns a copy."""
        structure1 = self.service.get_kubevirt_structure()
        structure2 = self.service.get_kubevirt_structure()
        structure1['new_key'] = 'value'
        assert 'new_key' not in structure2

    def test_kubevirt_directory_structure_defined(self):
        """Test KUBEVIRT_DIRECTORY_STRUCTURE is properly defined."""
        assert len(self.service.KUBEVIRT_DIRECTORY_STRUCTURE) > 0
        assert 'src' in self.service.KUBEVIRT_DIRECTORY_STRUCTURE
        assert 'views' in self.service.KUBEVIRT_DIRECTORY_STRUCTURE
        assert 'components' in self.service.KUBEVIRT_DIRECTORY_STRUCTURE

    def test_get_relevant_directories_kubevirt(self):
        """Test get_relevant_directories includes kubevirt paths for VM tests."""
        result = self.service.get_relevant_directories(
            "test_kubevirt_create_vm",
            "Element not found"
        )
        assert 'kubevirt_plugin' in result
        assert result['kubevirt_plugin'] is True
        assert 'kubevirt_src' in result
        assert 'kubevirt_views' in result
        assert 'kubevirt_components' in result

    def test_get_relevant_directories_non_kubevirt(self):
        """Test get_relevant_directories excludes kubevirt paths for non-VM tests."""
        result = self.service.get_relevant_directories(
            "test_create_cluster",
            ""
        )
        assert 'kubevirt_plugin' not in result

    def test_get_investigation_paths_kubevirt(self):
        """Test investigation paths for kubevirt include kubevirt-plugin paths."""
        paths = self.service.get_investigation_paths(
            "kubevirt",
            "element_not_found"
        )
        assert any("src/" in p for p in paths)
        assert any("views/" in p for p in paths)
        assert any("components/" in p for p in paths)

    def test_get_investigation_paths_vm(self):
        """Test investigation paths for vm include kubevirt-plugin paths."""
        paths = self.service.get_investigation_paths(
            "vm",
            "element_not_found"
        )
        # Should include kubevirt paths
        assert any("src/" in p for p in paths)

    def test_get_investigation_paths_virtualmachine(self):
        """Test investigation paths for virtualmachine include kubevirt paths."""
        paths = self.service.get_investigation_paths(
            "virtualmachine",
            "element_not_found"
        )
        assert any("src/" in p for p in paths)


class TestKubeVirtStructureValidation:
    """Tests for KubeVirt structure validation."""

    def setup_method(self):
        """Setup for each test."""
        self.service = ACMConsoleKnowledge()

    def test_validate_kubevirt_structure_all_present(self):
        """Test validation when all kubevirt directories exist."""
        with TemporaryDirectory() as tmpdir:
            kubevirt_path = Path(tmpdir)

            # Create expected directories
            for rel_path in self.service.KUBEVIRT_DIRECTORY_STRUCTURE.values():
                (kubevirt_path / rel_path).mkdir(parents=True, exist_ok=True)

            result = self.service.validate_kubevirt_structure(kubevirt_path)

            for name, exists in result.items():
                assert exists is True, f"Directory {name} should exist"

    def test_validate_kubevirt_structure_none_present(self):
        """Test validation when no kubevirt directories exist."""
        with TemporaryDirectory() as tmpdir:
            result = self.service.validate_kubevirt_structure(Path(tmpdir))

            for name, exists in result.items():
                assert exists is False, f"Directory {name} should not exist"

    def test_validate_kubevirt_structure_partial(self):
        """Test validation with partial kubevirt directory structure."""
        with TemporaryDirectory() as tmpdir:
            kubevirt_path = Path(tmpdir)

            # Only create src directory
            (kubevirt_path / "src").mkdir(parents=True, exist_ok=True)

            result = self.service.validate_kubevirt_structure(kubevirt_path)

            assert result['src'] is True
            assert result['views'] is False  # src/views/ not created
