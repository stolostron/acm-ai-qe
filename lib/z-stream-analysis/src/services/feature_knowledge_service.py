#!/usr/bin/env python3
"""
Feature Knowledge Service

Loads feature investigation playbooks (YAML), checks prerequisites against
cluster state, and matches test error messages to known failure paths.

Used in Stage 1 gather (Step 9) to provide the AI with domain knowledge
about feature architecture, prerequisites, and known failure patterns.
"""

import logging
import re
from dataclasses import dataclass, field

from .shared_utils import dataclass_to_dict
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml


@dataclass
class PrerequisiteCheck:
    """Result of checking a single prerequisite."""
    id: str
    type: str  # mch_component | addon | operator | crd | informational
    description: str
    met: Optional[bool] = None  # True | False | None (couldn't check)
    detail: Optional[str] = None  # What was found


@dataclass
class MatchedFailurePath:
    """A failure path that matched test error messages."""
    path_id: str
    description: str
    category: str  # prerequisite | component_health | data_flow | configuration | connectivity
    matched_symptom: str
    investigation_steps: List[dict] = field(default_factory=list)
    suggested_classification: str = 'UNKNOWN'
    confidence: float = 0.0
    explanation: str = ''


@dataclass
class FeatureReadiness:
    """Readiness assessment for a feature area."""
    feature_area: str
    architecture_summary: str = ''
    key_insight: str = ''
    all_prerequisites_met: Optional[bool] = None
    prerequisite_checks: List[PrerequisiteCheck] = field(default_factory=list)
    unmet_prerequisites: List[str] = field(default_factory=list)
    failure_paths: List[dict] = field(default_factory=list)
    pre_matched_paths: List[MatchedFailurePath] = field(default_factory=list)


# Path to playbook data directory
_DATA_DIR = Path(__file__).parent.parent / 'data' / 'feature_playbooks'


class FeatureKnowledgeService:
    """
    Feature knowledge service — loads playbooks, checks prerequisites,
    matches symptoms to known failure paths.

    Usage:
        service = FeatureKnowledgeService()
        service.load_playbooks('2.16', ['Search', 'RBAC'])
        readiness = service.get_feature_readiness('RBAC', mch_components={'fine-grained-rbac-preview': False})
    """

    def __init__(self, data_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.data_dir = Path(data_dir) if data_dir else _DATA_DIR
        self.profiles: Dict[str, dict] = {}

    def load_playbooks(
        self,
        acm_version: Optional[str] = None,
        feature_areas: Optional[List[str]] = None,
    ) -> Dict[str, dict]:
        """
        Load base.yaml + version overlay, merge profiles, return
        only requested feature areas.

        Args:
            acm_version: ACM version (e.g., '2.16'). Loads acm-{version}.yaml overlay.
            feature_areas: List of feature areas to load. None = all.

        Returns:
            Dict of feature_area -> profile dict.
        """
        self.profiles = {}

        # Load base profiles
        base_path = self.data_dir / 'base.yaml'
        if base_path.exists():
            try:
                with open(base_path, 'r') as f:
                    base_data = yaml.safe_load(f) or {}
                base_profiles = base_data.get('profiles', {})
                self.profiles.update(base_profiles)
                self.logger.info(f"Loaded {len(base_profiles)} base profiles")
            except Exception as e:
                self.logger.warning(f"Failed to load base playbooks: {e}")

        # Load version overlay (deep-merge into base profiles)
        if acm_version:
            version_path = self.data_dir / f'acm-{acm_version}.yaml'
            if version_path.exists():
                try:
                    with open(version_path, 'r') as f:
                        version_data = yaml.safe_load(f) or {}
                    version_profiles = version_data.get('profiles', {})
                    for name, version_profile in version_profiles.items():
                        if name in self.profiles:
                            self.profiles[name] = self._deep_merge_profile(
                                self.profiles[name], version_profile
                            )
                        else:
                            self.profiles[name] = version_profile
                    self.logger.info(
                        f"Loaded {len(version_profiles)} profiles from acm-{acm_version}.yaml"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Failed to load version playbooks for {acm_version}: {e}"
                    )
            else:
                self.logger.info(f"No version-specific playbook for acm-{acm_version}")

        # Filter to requested feature areas
        if feature_areas:
            # Case-insensitive matching
            area_lower_map = {k.lower(): k for k in self.profiles}
            filtered = {}
            for area in feature_areas:
                key = area_lower_map.get(area.lower())
                if key:
                    filtered[key] = self.profiles[key]
                else:
                    self.logger.debug(f"No playbook for feature area: {area}")
            self.profiles = filtered

        return self.profiles

    def check_prerequisites(
        self,
        feature_area: str,
        mch_components: Optional[Dict[str, bool]] = None,
        cluster_landscape: Optional[dict] = None,
        oracle_data: Optional[dict] = None,
        cluster_health: Optional[dict] = None,
    ) -> List[PrerequisiteCheck]:
        """
        Check each prerequisite against cluster state.

        mch_component type checks mch_components dict.
        addon, operator, crd types use oracle results when available,
        otherwise return met=None (checked by AI at runtime).
        informational always returns met=None.

        Args:
            feature_area: Feature area name (e.g., 'Search', 'RBAC')
            mch_components: Dict of MCH component name -> enabled bool
            cluster_landscape: Cluster landscape dict (optional, for future use)
            oracle_data: Environment Oracle results (v3.5) for resolving
                         addon/operator/crd prerequisites

        Returns:
            List of PrerequisiteCheck results.
        """
        profile = self.profiles.get(feature_area)
        if not profile:
            return []

        mch_available = mch_components is not None
        mch_components = mch_components if mch_components is not None else {}
        checks = []

        for prereq in profile.get('prerequisites', []):
            prereq_id = prereq.get('id', '')
            prereq_type = prereq.get('type', '')
            description = prereq.get('description', '')
            check_spec = prereq.get('check_spec', {})

            check = PrerequisiteCheck(
                id=prereq_id,
                type=prereq_type,
                description=description,
            )

            if prereq_type == 'mch_component':
                component_name = check_spec.get('component_name', '')
                if component_name and mch_available:
                    if component_name in mch_components:
                        check.met = mch_components[component_name]
                        check.detail = (
                            f"{component_name}={'enabled' if check.met else 'disabled'} in MCH"
                        )
                    else:
                        # Component not listed in overrides — use default
                        default = prereq.get('default_enabled', True)
                        check.met = default
                        check.detail = (
                            f"{component_name} not in MCH overrides, using default={default}"
                        )
                else:
                    check.met = None
                    check.detail = "MCH components not available for checking"

            elif prereq_type in ('addon', 'operator', 'crd'):
                # Try oracle results first (v3.5)
                oracle_result = self._lookup_oracle(oracle_data, prereq_id, prereq_type)
                if oracle_result is not None:
                    check.met, check.detail = oracle_result
                else:
                    # Try cluster health data (v3.7) as fallback
                    health_result = self._lookup_cluster_health(
                        cluster_health, prereq_id, prereq_type, check_spec
                    )
                    if health_result is not None:
                        check.met, check.detail = health_result
                    else:
                        # No data — flagged for AI
                        check.met = None
                        check.detail = f"Requires live cluster check (type={prereq_type})"

            elif prereq_type == 'informational':
                check.met = None
                check.detail = "Informational — context for AI, no automated check"

            checks.append(check)

        return checks

    @staticmethod
    def _lookup_oracle(
        oracle_data: Optional[dict],
        prereq_id: str,
        prereq_type: str,
    ) -> Optional[tuple]:
        """
        Look up a prerequisite's health from oracle results.

        Returns:
            Tuple of (met: bool, detail: str) or None if not available.
        """
        if not oracle_data:
            return None

        dependency_health = oracle_data.get('dependency_health', {})
        health = dependency_health.get(prereq_id)

        if not health:
            return None

        status = health.get('status', 'unknown')
        detail = health.get('detail', '')

        if status == 'healthy':
            return True, f"Oracle: {detail}"
        elif status in ('degraded', 'missing'):
            return False, f"Oracle: {detail}"
        else:
            return None

    @staticmethod
    def _lookup_cluster_health(
        cluster_health: Optional[dict],
        prereq_id: str,
        prereq_type: str,
        check_spec: dict,
    ) -> Optional[tuple]:
        """
        DEPRECATED (v4.0): cluster_health data no longer populated by gather.py.
        Health data now provided by Stage 1.5 cluster-diagnostic agent.
        This method returns None for new runs (cluster_health contains
        {'deferred_to_stage_1_5': True}). Kept for backward compatibility
        with older run directories that still have cluster_health in core-data.json.

        Original purpose: Look up a prerequisite's health from ClusterHealthService data (v3.7).

        Uses the cluster_health summary from core-data.json to infer
        prerequisite status based on the overall health verdict and
        affected feature areas.

        Returns:
            Tuple of (met: bool, detail: str) or None if not available.
        """
        if not cluster_health or cluster_health.get('skipped'):
            return None

        verdict = cluster_health.get('overall_verdict', 'UNKNOWN')
        score = cluster_health.get('environment_health_score')

        if score is None:
            return None

        # For operators: if health score is high, operators are likely healthy
        if prereq_type == 'operator' and verdict == 'HEALTHY':
            return True, f"ClusterHealthService: cluster HEALTHY (score={score})"

        # For addons: can't definitively confirm from summary alone
        # Return None to let AI check at runtime
        return None

    def match_symptoms(
        self,
        feature_area: str,
        error_messages: List[str],
    ) -> List[MatchedFailurePath]:
        """
        Match error messages against failure path symptom regexes.

        Args:
            feature_area: Feature area name
            error_messages: List of error messages from failed tests

        Returns:
            List of MatchedFailurePath for matching failure paths.
        """
        profile = self.profiles.get(feature_area)
        if not profile:
            return []

        matched = []
        for path in profile.get('failure_paths', []):
            symptoms = path.get('symptoms', [])
            for symptom_pattern in symptoms:
                for msg in error_messages:
                    try:
                        if re.search(symptom_pattern, msg):
                            matched.append(MatchedFailurePath(
                                path_id=path.get('id', ''),
                                description=path.get('description', ''),
                                category=path.get('category', ''),
                                matched_symptom=symptom_pattern,
                                investigation_steps=path.get('investigation', []),
                                suggested_classification=path.get('classification', 'UNKNOWN'),
                                confidence=path.get('confidence', 0.0),
                                explanation=path.get('explanation', ''),
                            ))
                            # Only match once per path
                            break
                    except re.error:
                        self.logger.warning(
                            f"Invalid regex pattern in {feature_area}/{path.get('id')}: {symptom_pattern}"
                        )
                else:
                    continue
                break  # Move to next failure path after first match

        return matched

    def get_feature_readiness(
        self,
        feature_area: str,
        mch_components: Optional[Dict[str, bool]] = None,
        cluster_landscape: Optional[dict] = None,
        error_messages: Optional[List[str]] = None,
        oracle_data: Optional[dict] = None,
        cluster_health: Optional[dict] = None,
    ) -> FeatureReadiness:
        """
        Combine prerequisite checks + symptom matching into a
        FeatureReadiness assessment.

        Args:
            feature_area: Feature area name
            mch_components: MCH component states
            cluster_landscape: Cluster landscape dict
            error_messages: Error messages from failed tests
            oracle_data: Environment Oracle results (v3.5)

        Returns:
            FeatureReadiness with checks, unmet prereqs, and matched paths.
        """
        profile = self.profiles.get(feature_area)
        if not profile:
            return FeatureReadiness(feature_area=feature_area)

        architecture = profile.get('architecture', {})

        # Check prerequisites (with oracle + cluster health for addon/operator/crd)
        checks = self.check_prerequisites(
            feature_area, mch_components, cluster_landscape,
            oracle_data=oracle_data,
            cluster_health=cluster_health,
        )

        # Determine unmet prerequisites
        unmet = [
            c.description for c in checks
            if c.met is False
        ]

        # Determine overall readiness
        checkable = [c for c in checks if c.met is not None]
        if checkable:
            all_met = all(c.met for c in checkable)
        else:
            all_met = None

        # Match symptoms
        matched_paths = []
        if error_messages:
            matched_paths = self.match_symptoms(feature_area, error_messages)

        return FeatureReadiness(
            feature_area=feature_area,
            architecture_summary=architecture.get('summary', ''),
            key_insight=architecture.get('key_insight', ''),
            all_prerequisites_met=all_met,
            prerequisite_checks=checks,
            unmet_prerequisites=unmet,
            failure_paths=profile.get('failure_paths', []),
            pre_matched_paths=matched_paths,
        )

    def get_investigation_playbook(
        self,
        feature_area: str,
    ) -> Optional[dict]:
        """
        Return the full playbook (architecture + failure_paths) for
        injection into core-data.json.

        Args:
            feature_area: Feature area name

        Returns:
            Dict with architecture + failure_paths, or None if not found.
        """
        profile = self.profiles.get(feature_area)
        if not profile:
            return None

        return {
            'display_name': profile.get('display_name', feature_area),
            'architecture': profile.get('architecture', {}),
            'prerequisites': profile.get('prerequisites', []),
            'dependencies': profile.get('dependencies', []),
            'failure_paths': profile.get('failure_paths', []),
        }

    def to_dict(self, obj) -> dict:
        """Convert dataclass to dict for serialization."""
        return dataclass_to_dict(obj)

    # ── Profile Merging ──

    @staticmethod
    def _deep_merge_profile(base: dict, overlay: dict) -> dict:
        """
        Deep-merge a version overlay into a base profile.

        Merge rules:
        - Scalar fields (display_name, docs_ref): overlay wins
        - architecture dict: overlay fields override base fields
        - prerequisites list: merge by 'id' — overlay entries with the
          same id replace base entries; new entries are appended
        - failure_paths list: same merge-by-id logic as prerequisites
        - dependencies list: overlay replaces base entirely
        - Any other keys: overlay wins
        """
        merged = dict(base)

        for key, value in overlay.items():
            if key == 'architecture' and isinstance(value, dict):
                merged_arch = dict(merged.get('architecture', {}))
                merged_arch.update(value)
                merged['architecture'] = merged_arch

            elif key in ('prerequisites', 'failure_paths') and isinstance(value, list):
                base_list = list(merged.get(key, []))
                base_ids = {item.get('id'): i for i, item in enumerate(base_list)
                            if isinstance(item, dict) and 'id' in item}
                for overlay_item in value:
                    if not isinstance(overlay_item, dict):
                        continue
                    item_id = overlay_item.get('id')
                    if item_id and item_id in base_ids:
                        base_list[base_ids[item_id]] = overlay_item
                    else:
                        base_list.append(overlay_item)
                merged[key] = base_list

            else:
                merged[key] = value

        return merged

    # ── Gap Detection Methods (v4.0) ──

    def detect_stale_components(
        self,
        components_path: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compare base.yaml key_components against knowledge/components.yaml.
        Flag any component in a playbook that doesn't appear in the
        knowledge database (likely renamed or removed).

        Returns:
            List of stale component dicts with profile, old_name, and
            suggested_replacement (if a close match exists in components.yaml).
        """
        if components_path is None:
            components_path = self.data_dir.parent.parent.parent / 'knowledge' / 'components.yaml'
        if not components_path.exists():
            return []

        try:
            with open(components_path) as f:
                comp_data = yaml.safe_load(f) or {}
        except Exception:
            return []

        # Build set of known component names from knowledge database.
        # components.yaml uses dict-of-dicts: {component_name: {subsystem, type, ...}}
        # nested under a top-level 'components' key.
        known_names = set()
        components = comp_data.get('components', comp_data)
        for key, val in components.items():
            if isinstance(val, dict) and 'subsystem' in val:
                # This is a component entry (has subsystem field)
                known_names.add(key)
            elif isinstance(val, list):
                # List of component dicts
                for entry in val:
                    if isinstance(entry, dict):
                        name = entry.get('name', key)
                        known_names.add(name)

        stale = []
        for profile_name, profile in self.profiles.items():
            arch = profile.get('architecture', {})
            for comp in arch.get('key_components', []):
                comp_name = comp.get('name', '')
                if comp_name and comp_name not in known_names:
                    stale.append({
                        'profile': profile_name,
                        'component': comp_name,
                        'namespace': comp.get('namespace', ''),
                        'detail': f'{comp_name} not found in knowledge/components.yaml',
                    })
        return stale

    def detect_hardcoded_namespaces(self) -> List[Dict[str, Any]]:
        """
        Scan playbook investigation commands for literal namespace
        references that should be parameterized as {mch_ns}.

        Returns:
            List of dicts with profile, path_id, command, and the
            hardcoded namespace found.
        """
        # Known fixed namespaces that should NOT be flagged
        fixed_ns = {
            'multicluster-engine', 'hive', 'openshift-cnv',
            'openshift-gitops', 'openshift-monitoring',
            'ansible-automation-platform', 'aap',
            'open-cluster-management-agent',
        }
        # API group names that contain namespace-like strings but aren't namespaces
        api_groups = {'open-cluster-management.io'}

        hardcoded = []
        for profile_name, profile in self.profiles.items():
            for path in profile.get('failure_paths', []):
                for step in path.get('investigation', []):
                    cmd = step.get('command', '')
                    # Look for -n <literal-namespace> patterns
                    for match in re.finditer(r'-n\s+(\S+)', cmd):
                        ns = match.group(1)
                        if ns.startswith('{'):
                            continue  # Already parameterized
                        if ns in fixed_ns:
                            continue  # Known fixed namespace
                        if any(ag in ns for ag in api_groups):
                            continue  # API group, not namespace
                        hardcoded.append({
                            'profile': profile_name,
                            'path_id': path.get('id', ''),
                            'command': cmd,
                            'namespace': ns,
                        })
        return hardcoded

    def detect_missing_overlay(self, acm_version: Optional[str] = None) -> Optional[str]:
        """
        Check if a version-specific overlay exists for the current
        ACM version.

        Returns:
            The missing overlay filename, or None if overlay exists
            or version is unknown.
        """
        if not acm_version:
            return None
        overlay_name = f'acm-{acm_version}.yaml'
        overlay_path = self.data_dir / overlay_name
        if not overlay_path.exists():
            return overlay_name
        return None

    def count_unmatched_errors(
        self,
        feature_area: str,
        error_messages: List[str],
    ) -> Dict[str, Any]:
        """
        Count how many error messages in a feature area have zero
        matching failure paths.

        Returns:
            Dict with total_errors, matched_count, unmatched_count,
            match_rate, and unmatched_samples (first 3 unmatched errors).
        """
        profile = self.profiles.get(feature_area)
        if not profile or not error_messages:
            return {
                'total_errors': len(error_messages),
                'matched_count': 0,
                'unmatched_count': len(error_messages),
                'match_rate': 0.0,
                'unmatched_samples': error_messages[:3],
            }

        matched_count = 0
        unmatched = []
        for msg in error_messages:
            found = False
            for path in profile.get('failure_paths', []):
                for symptom in path.get('symptoms', []):
                    try:
                        if re.search(symptom, msg):
                            found = True
                            break
                    except re.error:
                        pass
                if found:
                    break
            if found:
                matched_count += 1
            else:
                unmatched.append(msg[:200])

        total = len(error_messages)
        return {
            'total_errors': total,
            'matched_count': matched_count,
            'unmatched_count': total - matched_count,
            'match_rate': matched_count / total if total > 0 else 0.0,
            'unmatched_samples': unmatched[:3],
        }

    def run_gap_detection(
        self,
        acm_version: Optional[str] = None,
        feature_areas_with_errors: Optional[Dict[str, List[str]]] = None,
        components_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Run all deterministic gap detection checks.

        Args:
            acm_version: Current ACM version string (e.g., '2.17')
            feature_areas_with_errors: Dict of feature_area -> list of error messages
            components_path: Path to knowledge/components.yaml

        Returns:
            Dict with gap detection results for core-data.json.
        """
        result = {
            'stale_components': self.detect_stale_components(components_path),
            'hardcoded_namespaces': self.detect_hardcoded_namespaces(),
            'missing_overlay': self.detect_missing_overlay(acm_version),
        }

        # Per-area match rates
        if feature_areas_with_errors:
            area_match_rates = {}
            for area, errors in feature_areas_with_errors.items():
                area_match_rates[area] = self.count_unmatched_errors(area, errors)
            result['match_rates'] = area_match_rates

            # Summary
            total_errors = sum(m['total_errors'] for m in area_match_rates.values())
            total_matched = sum(m['matched_count'] for m in area_match_rates.values())
            result['overall_match_rate'] = total_matched / total_errors if total_errors > 0 else 0.0
            result['gap_areas'] = [
                area for area, m in area_match_rates.items()
                if m['match_rate'] < 0.5 and m['total_errors'] > 0
            ]

        return result
