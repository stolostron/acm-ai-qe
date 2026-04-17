"""
Cross-module consistency tests.

Catches mismatches between the 3 sources of component/subsystem truth:
- feature_area_service.py -> FEATURE_AREAS dict
- cluster_investigation_service.py -> COMPONENT_NAMESPACE_MAP, SUBSYSTEM_COMPONENTS
- src/data/feature_playbooks/*.yaml -> playbook key_components
"""

import warnings

import pytest

from src.services.feature_area_service import FEATURE_AREAS
from src.services.cluster_investigation_service import (
    COMPONENT_NAMESPACE_MAP,
    SUBSYSTEM_COMPONENTS,
)

pytestmark = pytest.mark.regression

# Known subsystem naming divergences (intentional design decisions).
# New undocumented divergences should fail; these should not.
KNOWN_DIVERGENCES = {
    # feature_area_service uses 'Cluster Lifecycle', cluster_investigation splits
    # into 'Cluster' + 'Provisioning'
    ("feature_area_service", "CLC", "Cluster Lifecycle"): [
        ("cluster_investigation", "Cluster"),
        ("cluster_investigation", "Provisioning"),
    ],
    # feature_area_service uses 'Application Lifecycle',
    # cluster_investigation uses 'Application'
    ("feature_area_service", "Application", "Application Lifecycle"): [
        ("cluster_investigation", "Application"),
    ],
    # RBAC shares Console components in cluster_investigation
    ("feature_area_service", "RBAC", "RBAC"): [],
}


class TestPlaybookComponentsInNamespaceMap:
    """Every component named in a playbook key_components must exist
    in COMPONENT_NAMESPACE_MAP."""

    def test_playbook_components_in_namespace_map(self, all_playbook_profiles):
        missing = []
        for profile_name, profile in all_playbook_profiles.items():
            arch = profile.get("architecture", {})
            for comp in arch.get("key_components", []):
                comp_name = comp.get("name", "")
                if comp_name and comp_name not in COMPONENT_NAMESPACE_MAP:
                    missing.append(f"{profile_name}/{comp_name}")

        assert not missing, (
            f"Playbook components not in COMPONENT_NAMESPACE_MAP: {missing}"
        )


class TestPlaybookNamespacesMatchMap:
    """For each playbook component, its namespace must match
    COMPONENT_NAMESPACE_MAP."""

    def test_playbook_namespaces_match_map(self, all_playbook_profiles):
        mismatches = []
        # Resolve {mch_ns} template to default namespace for comparison
        default_ns = 'open-cluster-management'
        for profile_name, profile in all_playbook_profiles.items():
            arch = profile.get("architecture", {})
            for comp in arch.get("key_components", []):
                comp_name = comp.get("name", "")
                playbook_ns = comp.get("namespace", "")
                # Resolve template variables for comparison
                resolved_ns = playbook_ns.replace("{mch_ns}", default_ns)
                if comp_name in COMPONENT_NAMESPACE_MAP:
                    map_ns, _ = COMPONENT_NAMESPACE_MAP[comp_name]
                    if resolved_ns and map_ns != resolved_ns:
                        mismatches.append(
                            f"{profile_name}/{comp_name}: "
                            f"playbook={resolved_ns} vs map={map_ns}"
                        )

        assert not mismatches, (
            f"Namespace mismatches between playbooks and COMPONENT_NAMESPACE_MAP: "
            f"{mismatches}"
        )


class TestFeatureAreaNamesMatchPlaybooks:
    """Every profile key in playbooks must exist in FEATURE_AREAS
    (or be a known version-specific addition like CrossClusterMigration)."""

    # Profiles that are version-specific and not in FEATURE_AREAS
    KNOWN_PLAYBOOK_ONLY_PROFILES = {"CrossClusterMigration"}

    def test_feature_area_names_match_playbooks(self, all_playbook_profiles):
        missing = []
        for profile_key in all_playbook_profiles:
            if profile_key in self.KNOWN_PLAYBOOK_ONLY_PROFILES:
                continue
            if profile_key not in FEATURE_AREAS:
                missing.append(profile_key)

        assert not missing, (
            f"Playbook profiles not in FEATURE_AREAS: {missing}. "
            f"Add them to FEATURE_AREAS or KNOWN_PLAYBOOK_ONLY_PROFILES."
        )


class TestSubsystemNamesAlignment:
    """Cross-check subsystem names across all 3 sources.
    Known divergences are documented; undocumented ones fail."""

    def test_subsystem_names_alignment(self):
        # Collect subsystem names from each source
        fa_subsystems = {
            name: grounding.subsystem
            for name, grounding in FEATURE_AREAS.items()
        }
        ci_subsystems = set(SUBSYSTEM_COMPONENTS.keys())

        # Every SUBSYSTEM_COMPONENTS key should either match a
        # FEATURE_AREAS.subsystem value or be in known divergences
        known_ci_names = set()
        for _, divergences in KNOWN_DIVERGENCES.items():
            for _, ci_name in divergences:
                known_ci_names.add(ci_name)

        fa_subsystem_values = set(fa_subsystems.values())
        undocumented = []
        for ci_name in ci_subsystems:
            if ci_name not in fa_subsystem_values and ci_name not in known_ci_names:
                undocumented.append(ci_name)

        if undocumented:
            pytest.fail(
                f"Undocumented subsystem names in SUBSYSTEM_COMPONENTS "
                f"not matching FEATURE_AREAS: {undocumented}. "
                f"Add to KNOWN_DIVERGENCES if intentional."
            )

        # Log known divergences as warnings
        for key, divs in KNOWN_DIVERGENCES.items():
            source, area, name = key
            if divs:
                div_names = [d[1] for d in divs]
                warnings.warn(
                    f"Known divergence: {source}/{area} uses '{name}', "
                    f"cluster_investigation uses {div_names}"
                )


class TestNoDuplicateComponentEntries:
    """No component appears twice in COMPONENT_NAMESPACE_MAP."""

    def test_no_duplicate_component_entries(self):
        # COMPONENT_NAMESPACE_MAP is a dict so keys are unique by definition.
        # But check that no component is listed in multiple SUBSYSTEM_COMPONENTS.
        seen = {}
        duplicates = []
        for subsystem, components in SUBSYSTEM_COMPONENTS.items():
            for comp in components:
                if comp in seen:
                    duplicates.append(
                        f"{comp}: in both '{seen[comp]}' and '{subsystem}'"
                    )
                seen[comp] = subsystem

        assert not duplicates, (
            f"Components in multiple SUBSYSTEM_COMPONENTS: {duplicates}"
        )


class TestPlaybookPrerequisiteIdsUnique:
    """Within each playbook profile, prerequisite IDs are unique."""

    def test_playbook_prerequisite_ids_unique(self, all_playbook_profiles):
        issues = []
        for profile_name, profile in all_playbook_profiles.items():
            ids = [p.get("id", "") for p in profile.get("prerequisites", [])]
            dupes = [x for x in ids if ids.count(x) > 1]
            if dupes:
                issues.append(f"{profile_name}: duplicate IDs {set(dupes)}")

        assert not issues, f"Duplicate prerequisite IDs: {issues}"


class TestFailurePathIdsUnique:
    """Within each playbook profile, failure path IDs are unique.
    No two profiles share the same path ID."""

    def test_failure_path_ids_unique(self, all_playbook_profiles):
        all_ids = {}
        issues = []

        for profile_name, profile in all_playbook_profiles.items():
            profile_ids = []
            for path in profile.get("failure_paths", []):
                path_id = path.get("id", "")
                profile_ids.append(path_id)

                if path_id in all_ids:
                    issues.append(
                        f"Duplicate path ID '{path_id}': "
                        f"in '{all_ids[path_id]}' and '{profile_name}'"
                    )
                all_ids[path_id] = profile_name

            # Check within-profile duplicates
            within_dupes = [x for x in profile_ids if profile_ids.count(x) > 1]
            if within_dupes:
                issues.append(
                    f"{profile_name}: duplicate path IDs within profile: "
                    f"{set(within_dupes)}"
                )

        assert not issues, f"Failure path ID conflicts: {issues}"


class TestPlaybookDependenciesReferenceValidProfiles:
    """Each dependencies list references profiles that actually exist."""

    def test_playbook_dependencies_reference_valid_profiles(
        self, all_playbook_profiles
    ):
        invalid = []
        for profile_name, profile in all_playbook_profiles.items():
            deps = profile.get("dependencies", [])
            for dep in deps:
                if dep not in all_playbook_profiles:
                    invalid.append(f"{profile_name} -> {dep}")

        assert not invalid, (
            f"Playbook dependencies reference non-existent profiles: {invalid}"
        )


class TestMchComponentNamesAreReal:
    """MCH component names in playbook prerequisites should match known
    MCH component names."""

    # Known MCH component names from cluster_investigation_service and playbooks
    KNOWN_MCH_COMPONENTS = {
        "search",
        "grc",
        "cluster-lifecycle",
        "app-lifecycle",
        "console",
        "fine-grained-rbac",
        "cnv-mtv-integrations",
        "multicluster-observability-operator",
    }

    def test_mch_component_names_are_real(self, all_playbook_profiles):
        unknown = []
        for profile_name, profile in all_playbook_profiles.items():
            for prereq in profile.get("prerequisites", []):
                if prereq.get("type") == "mch_component":
                    comp_name = prereq.get("check_spec", {}).get(
                        "component_name", ""
                    )
                    if comp_name and comp_name not in self.KNOWN_MCH_COMPONENTS:
                        unknown.append(f"{profile_name}/{comp_name}")

        assert not unknown, (
            f"Unknown MCH component names in playbooks: {unknown}. "
            f"Add to KNOWN_MCH_COMPONENTS if valid."
        )


class TestExportsMatchServiceClasses:
    """Every class exported from __init__.py is importable and matches an
    actual class in the service module."""

    def test_exports_match_service_classes(self):
        from src.services import __all__

        import src.services as services_module

        missing = []
        for name in __all__:
            if not hasattr(services_module, name):
                missing.append(name)

        assert not missing, (
            f"Names in __all__ not importable from src.services: {missing}"
        )
