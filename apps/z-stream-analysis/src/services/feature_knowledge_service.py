#!/usr/bin/env python3
"""
Feature Knowledge Service

Loads feature investigation playbooks (YAML), checks prerequisites against
cluster state, and matches test error messages to known failure paths.

Used in Stage 1 gather (Step 9) to provide the AI with domain knowledge
about feature architecture, prerequisites, and known failure patterns.
"""

import logging
import os
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

        # Load version overlay
        if acm_version:
            version_path = self.data_dir / f'acm-{acm_version}.yaml'
            if version_path.exists():
                try:
                    with open(version_path, 'r') as f:
                        version_data = yaml.safe_load(f) or {}
                    version_profiles = version_data.get('profiles', {})
                    # Version profiles override/add to base
                    self.profiles.update(version_profiles)
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
                    # No oracle data — flagged for AI
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

        # Check prerequisites (with oracle data for addon/operator/crd)
        checks = self.check_prerequisites(
            feature_area, mch_components, cluster_landscape,
            oracle_data=oracle_data,
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
