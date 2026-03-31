"""
Environment Oracle Service (v3.5)

Feature-aware dependency health checking and comprehensive cluster state
collection. Resolves the met=None gap in FeatureKnowledgeService for
addon, operator, and CRD prerequisites.

Six-phase pipeline (each phase feeds the next):
  Phase 1: IDENTIFY — extract feature area + failed test Polarion IDs
  Phase 2: DISCOVER — fetch Polarion test case context (description, setup, steps)
  Phase 3: LEARN THE FEATURE — KG component topology + rhacm-docs path
  Phase 4: LEARN THE DEPENDENCIES — KG architecture for each dependency subsystem
  Phase 5: SYNTHESIZE — merge playbook prereqs + KG feature/dep components
  Phase 6: COLLECT CLUSTER STATE — comprehensive oc data for ALL targets

All cluster operations are strictly read-only.
All Polarion operations are read-only (GET requests only).
"""

import html
import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from src.services.shared_utils import validate_command_readonly, THRESHOLDS
from src.services.feature_knowledge_service import FeatureKnowledgeService


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DependencyTarget:
    """A single dependency or component to check on the cluster."""
    id: str
    type: str  # operator | addon | crd | component | managed_clusters
    name: str
    description: str
    namespace: Optional[str] = None
    component_name: Optional[str] = None
    plugin_name: Optional[str] = None
    check_command: Optional[str] = None
    source: str = 'playbook'  # playbook | kg | system
    subsystem: Optional[str] = None


@dataclass
class DependencyHealth:
    """Health status for a single dependency after cluster investigation."""
    id: str
    type: str
    name: str
    status: str  # healthy | degraded | missing | unknown | unchecked
    detail: str = ''
    raw_output: str = ''
    check_command: str = ''


@dataclass
class PolarionDiscovery:
    """Raw Polarion test case content for AI interpretation in Stage 2."""
    polarion_available: bool = False
    tests_queried: int = 0
    tests_with_content: int = 0
    test_case_context: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class OracleResult:
    """Complete oracle output for inclusion in core-data.json."""
    version: str = '1.0.0'
    oracle_phase: str = 'C'
    snapshot_time: str = ''
    feature_areas: List[str] = field(default_factory=list)
    failed_test_count: int = 0
    polarion_ids: List[str] = field(default_factory=list)
    polarion_discovery: Dict[str, Any] = field(default_factory=dict)
    knowledge_context: Dict[str, Any] = field(default_factory=dict)
    dependency_targets: List[Dict[str, Any]] = field(default_factory=list)
    dependency_health: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    overall_feature_health: Dict[str, Any] = field(default_factory=dict)
    cluster_access_status: str = 'unknown'
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class EnvironmentOracleService:
    """
    Environment Oracle (v3.5) — six-phase pipeline.

    Phase 1: Identify feature area and failed tests
    Phase 2: Fetch Polarion test case context for AI interpretation
    Phase 3: Learn feature architecture from KG + docs
    Phase 4: Learn dependency architectures from KG (same depth as Phase 3)
    Phase 5: Synthesize ALL sources into comprehensive collection plan
    Phase 6: Collect cluster state for every target (read-only)
    """

    ALLOWED_COMMANDS: Set[str] = {
        'login', 'logout', 'whoami', 'version',
        'get', 'describe', 'api-resources', 'auth',
    }

    # Polarion REST API settings
    POLARION_DEFAULT_URL = 'https://polarion.engineering.redhat.com/polarion'
    POLARION_PROJECT = 'RHACM4K'
    POLARION_TIMEOUT = 30

    # Max chars of doc content per feature area (keeps core-data.json manageable)
    DOCS_MAX_CHARS_PER_AREA = 3000

    def __init__(self, playbook_dir: Optional[str] = None, docs_dir: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._playbook_dir = playbook_dir
        self._cli_binary = self._detect_cli()
        self._temp_kubeconfig: Optional[str] = None
        self._logged_in = False
        self.feature_knowledge = FeatureKnowledgeService(data_dir=playbook_dir)

        # rhacm-docs path (configurable, with auto-discovery)
        self._docs_dir = docs_dir or self._find_rhacm_docs()

        # Polarion config (from environment or .env file)
        self._polarion_url = os.environ.get('POLARION_BASE_URL', self.POLARION_DEFAULT_URL)
        self._polarion_token = os.environ.get('POLARION_PAT', '')
        if not self._polarion_token:
            self._polarion_token = self._load_polarion_token()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_oracle(
        self,
        jenkins_data: Dict[str, Any],
        test_report: Dict[str, Any],
        cluster_landscape: Dict[str, Any],
        cluster_credentials: Optional[Dict[str, Any]] = None,
        skip_cluster: bool = False,
        knowledge_graph_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Execute Phases 1-6 of the Environment Oracle.

        Args:
            jenkins_data: Jenkins build info from Step 1
            test_report: Test report from Step 3
            cluster_landscape: Cluster landscape from Step 4
            cluster_credentials: Dict with api_url, username, password
            skip_cluster: Skip Phase 6 cluster investigation
            knowledge_graph_client: Optional KnowledgeGraphClient for Phases 3-4

        Returns:
            Oracle result dict for inclusion in core-data.json
        """
        result = OracleResult(snapshot_time=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        kg_client = knowledge_graph_client
        kg_available = bool(kg_client and getattr(kg_client, 'available', False))

        try:
            # ============================================================
            # Phase 1: IDENTIFY — What component are we testing?
            # ============================================================
            self.logger.info("Oracle Phase 1: Identifying feature area and failed tests...")
            identification = self._phase1_identify(jenkins_data, test_report)
            result.feature_areas = identification['feature_areas']
            result.failed_test_count = identification['failed_test_count']
            result.polarion_ids = identification['polarion_ids']

            if not result.feature_areas:
                self.logger.warning("Oracle: No feature areas identified — skipping Phases 2-6")
                result.errors.append("No feature areas identified from pipeline/test names")
                return asdict(result)

            # ============================================================
            # Phase 2: DISCOVER — What do the failed tests depend on?
            # ============================================================
            polarion_discovery = PolarionDiscovery()
            if result.polarion_ids:
                self.logger.info(
                    f"Oracle Phase 2: Fetching Polarion context for "
                    f"{len(result.polarion_ids)} test cases..."
                )
                polarion_discovery = self._phase2_discover_from_polarion(
                    result.polarion_ids
                )
            else:
                self.logger.info("Oracle Phase 2: Skipped (no Polarion IDs found)")
            result.polarion_discovery = asdict(polarion_discovery)

            # ============================================================
            # Phase 3: LEARN THE FEATURE — How does this feature work?
            # Learns EVERYTHING about the core feature: all components,
            # all data flows, all cross-subsystem dependencies.
            # ============================================================
            self.logger.info("Oracle Phase 3: Learning feature architecture...")
            knowledge_context = self._phase3_learn_feature(
                identification, kg_client
            )

            # ============================================================
            # Phase 4: LEARN THE DEPENDENCIES — How do the deps work?
            # Same depth as Phase 3, but for each dependency (cross-
            # subsystem deps from KG + playbook prerequisites).
            # ============================================================
            if kg_available:
                self.logger.info("Oracle Phase 4: Learning dependency architectures...")
                # Collect all dependency subsystems from Phase 3's cross-subsystem data
                cross_sub_deps = knowledge_context.get('cross_subsystem_dependencies', {})
                dep_subsystems = set()
                for area_deps in cross_sub_deps.values():
                    for dep_str in area_deps:
                        # Parse "source --REL--> target (TargetSubsystem)"
                        paren_match = re.search(r'\(([^)]+)\)$', dep_str)
                        if paren_match:
                            dep_subsystems.add(paren_match.group(1))

                dep_details = self._phase4_learn_dependencies_comprehensive(
                    identification, dep_subsystems, kg_client
                )
                knowledge_context['dependency_details'] = dep_details
            else:
                self.logger.info("Oracle Phase 4: Skipped (KG not available)")

            result.knowledge_context = knowledge_context

            # ============================================================
            # Phase 5: SYNTHESIZE — Complete collection plan
            # Merges ALL sources: playbook prereqs + KG feature components
            # + KG dependency components into one target list.
            # ============================================================
            self.logger.info("Oracle Phase 5: Synthesizing collection plan...")
            dependency_model = self._phase5_synthesize(
                identification, cluster_landscape, knowledge_context,
            )
            result.dependency_targets = [asdict(t) for t in dependency_model]

            self.logger.info(
                f"Phase 5: {len(dependency_model)} total targets to collect"
            )

            # ============================================================
            # Phase 6: COLLECT CLUSTER STATE — Comprehensive collection
            # Collects actual state for EVERY target from Phase 5:
            # operators, addons, CRDs, components/pods, managed clusters.
            # ============================================================
            if skip_cluster:
                self.logger.info("Oracle Phase 6: Skipped (--skip-env)")
                result.cluster_access_status = 'skipped'
            elif not cluster_credentials or not cluster_credentials.get('has_credentials'):
                self.logger.info("Oracle Phase 6: Skipped (no cluster credentials)")
                result.cluster_access_status = 'no_credentials'
            else:
                self.logger.info(
                    f"Oracle Phase 6: Collecting cluster state for "
                    f"{len(dependency_model)} targets..."
                )
                try:
                    logged_in = self._login(
                        cluster_credentials.get('api_url', ''),
                        cluster_credentials.get('username', ''),
                        cluster_credentials.get('password', ''),
                    )
                    if logged_in:
                        result.cluster_access_status = 'authenticated'
                        health_results = self._phase6_collect_cluster_state(
                            dependency_model
                        )
                        result.dependency_health = {
                            h.id: asdict(h) for h in health_results
                        }
                    else:
                        result.cluster_access_status = 'login_failed'
                        result.errors.append("Cluster login failed")
                except Exception as e:
                    result.cluster_access_status = 'error'
                    result.errors.append(f"Phase 6 error: {str(e)}")
                    self.logger.error(f"Oracle Phase 6 failed: {e}")

            # Compute overall health
            result.overall_feature_health = self._compute_overall_health(
                result.dependency_health, result.feature_areas
            )

            dep_count = len(result.dependency_targets)
            checked = len(result.dependency_health)
            self.logger.info(
                f"Oracle complete: {dep_count} targets synthesized, "
                f"{checked} collected from cluster"
            )

        except Exception as e:
            self.logger.error(f"Oracle failed: {e}")
            result.errors.append(f"Oracle error: {str(e)}")
        finally:
            self._cleanup()

        return asdict(result)

    # ------------------------------------------------------------------
    # Phase 1: Identify
    # ------------------------------------------------------------------

    def _phase1_identify(
        self,
        jenkins_data: Dict[str, Any],
        test_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract feature area and failed test Polarion IDs."""
        # Extract pipeline name from URL (more reliable than job_name,
        # which can be the parent folder like 'qe-acm-automation-poc')
        build_url = jenkins_data.get('build_url', '') or ''
        pipeline_name = self._extract_pipeline_name(build_url)
        job_name = pipeline_name or (jenkins_data.get('job_name', '') or '')

        feature_areas = self._pipeline_to_feature_areas(job_name)

        # Extract failed tests and Polarion IDs
        failed_tests = test_report.get('failed_tests', [])
        polarion_ids = []
        for test in failed_tests:
            test_name = test.get('test_name', '')
            match = re.search(r'RHACM4K-\d+', test_name)
            if match:
                polarion_ids.append(match.group())

        # If pipeline name didn't produce results, try from test names
        if not feature_areas:
            feature_areas = self._tests_to_feature_areas(failed_tests)

        self.logger.info(
            f"Phase 1: pipeline={job_name}, feature_areas={feature_areas}, "
            f"failed_tests={len(failed_tests)}, "
            f"polarion_ids={len(polarion_ids)}"
        )

        return {
            'feature_areas': feature_areas,
            'failed_test_count': len(failed_tests),
            'polarion_ids': polarion_ids,
            'job_name': job_name,
        }

    @staticmethod
    def _extract_pipeline_name(build_url: str) -> str:
        """Extract the actual pipeline name from a Jenkins build URL.

        URL format: .../job/{parent}/job/{pipeline}/{build}/
        Returns the innermost job name (pipeline), not the parent folder.
        """
        if not build_url:
            return ''
        # Find all /job/{name}/ segments — the last one before the build
        # number is the actual pipeline name
        segments = re.findall(r'/job/([^/]+)', build_url)
        if segments:
            return segments[-1]  # Last segment is the pipeline
        return ''

    def _pipeline_to_feature_areas(self, job_name: str) -> List[str]:
        """Map Jenkins pipeline name to feature areas.

        Collects ALL matching areas (not first-match-wins) to avoid
        ordering bias. E.g., 'cluster-virt-e2e' matches both CLC and
        Virtualization.
        """
        job_lower = job_name.lower()
        mapping = {
            'clc': 'CLC',
            'cluster': 'CLC',
            'alc': 'Application',
            'application': 'Application',
            'grc': 'GRC',
            'governance': 'GRC',
            'search': 'Search',
            'virt': 'Virtualization',
            'vm': 'Virtualization',
            'rbac': 'RBAC',
            'automation': 'Automation',
            'ansible': 'Automation',
            'observ': 'Observability',
            'console': 'Console',
        }
        areas = set()
        for pattern, area in mapping.items():
            if pattern in job_lower:
                areas.add(area)
        return sorted(areas)

    def _tests_to_feature_areas(self, failed_tests: List[Dict]) -> List[str]:
        """Infer feature areas from failed test names.

        Uses 'if' (not 'elif') so each test can match MULTIPLE feature
        areas. Avoids ordering bias where early checks shadow later ones.
        """
        areas = set()
        # Keyword groups — each is checked independently (no elif chain)
        keyword_map = [
            (['clc'], 'CLC'),
            (['alc', 'application', 'subscription', 'argo'], 'Application'),
            (['grc', 'policy', 'governance'], 'GRC'),
            (['search'], 'Search'),
            (['virt', 'vm ', 'migration'], 'Virtualization'),
            (['rbac', 'role', 'permission'], 'RBAC'),
            (['automation', 'ansible', 'aap'], 'Automation'),
            (['observ', 'metric', 'alert'], 'Observability'),
            (['cluster'], 'CLC'),
            (['console'], 'Console'),
        ]

        for test in failed_tests:
            name = (test.get('test_name', '') or '').lower()
            class_name = (test.get('class_name', '') or '').lower()
            combined = f"{name} {class_name}"

            for keywords, area in keyword_map:
                if any(k in combined for k in keywords):
                    areas.add(area)

        if not areas:
            self.logger.warning(
                "Could not determine feature area from test names — "
                "oracle will use playbook data for all feature areas"
            )
        return sorted(areas)

    # ------------------------------------------------------------------
    # Phase 2: Discover dependencies from Polarion (Phase B)
    # ------------------------------------------------------------------

    def _phase2_discover_from_polarion(
        self, polarion_ids: List[str]
    ) -> PolarionDiscovery:
        """
        Fetch Polarion test case content: description, setup, and test steps.

        All content is stored raw (HTML stripped to text) in test_case_context
        for the AI agent to interpret dynamically during Stage 2. No hardcoded
        keyword matching — the AI determines what dependencies are mentioned
        based on its understanding of the full test case context.
        """
        discovery = PolarionDiscovery()

        if not self._polarion_token:
            self.logger.info("Phase 2: Polarion token not configured — skipping")
            discovery.errors.append("Polarion PAT not configured")
            return discovery

        discovery.polarion_available = True

        for pol_id in polarion_ids:
            discovery.tests_queried += 1
            try:
                context = self._fetch_polarion_test_context(pol_id)
                if context:
                    discovery.tests_with_content += 1
                    discovery.test_case_context[pol_id] = context

            except Exception as e:
                err = f"Polarion fetch failed for {pol_id}: {str(e)}"
                self.logger.warning(err)
                discovery.errors.append(err)

        self.logger.info(
            f"Phase 2: queried {discovery.tests_queried} test cases, "
            f"{discovery.tests_with_content} had content"
        )
        return discovery

    def _fetch_polarion_test_context(
        self, polarion_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch complete test case context: title, description, setup, and steps.

        Returns dict with raw text content, or None if nothing found.
        """
        work_item_id = self._normalize_polarion_id(polarion_id)

        # Fetch work item (title + description + setup) in one call
        work_item = self._polarion_get(
            f"projects/{self.POLARION_PROJECT}/workitems/{work_item_id}",
            params={'fields[workitems]': 'title,description,setup'},
        )
        if not work_item:
            return None

        attrs = work_item.get('data', {}).get('attributes', {})
        title = attrs.get('title', '')

        # Extract description text
        desc_obj = attrs.get('description', {})
        desc_html = desc_obj.get('value', '') if isinstance(desc_obj, dict) else ''
        description = self._strip_html(desc_html) if desc_html else ''

        # Extract setup text
        setup_obj = attrs.get('setup', {})
        setup_html = setup_obj.get('value', '') if isinstance(setup_obj, dict) else ''
        setup = self._strip_html(setup_html) if setup_html else ''

        # Fetch test steps
        steps_data = self._polarion_get(
            f"projects/{self.POLARION_PROJECT}/workitems/{work_item_id}/teststeps",
        )
        test_steps = self._parse_test_steps(steps_data) if steps_data else []

        # Only return if we have meaningful content
        has_content = bool(
            description.strip() or setup.strip() or test_steps
        )
        if not has_content:
            return None

        context = {'title': title}
        if description.strip():
            context['description'] = description[:1000]
        if setup.strip():
            context['setup'] = setup[:500]
        if test_steps:
            context['test_steps'] = test_steps[:20]  # Cap at 20 steps

        return context

    def _parse_test_steps(self, steps_data: dict) -> List[str]:
        """Extract test step text from Polarion test steps response."""
        steps = []
        items = steps_data.get('data', [])
        if not isinstance(items, list):
            return steps

        for item in items:
            attrs = item.get('attributes', {})
            values = attrs.get('values', [])
            if not isinstance(values, list):
                continue
            for val in values:
                if isinstance(val, dict):
                    val_html = val.get('value', '')
                    if val_html:
                        text = self._strip_html(val_html).strip()
                        if text:
                            steps.append(text[:300])
        return steps

    def _normalize_polarion_id(self, polarion_id: str) -> str:
        """Normalize Polarion ID to full format (e.g., RHACM4K-7473)."""
        if not polarion_id.startswith(self.POLARION_PROJECT):
            return f"{self.POLARION_PROJECT}-{polarion_id}"
        return polarion_id

    def _polarion_get(
        self, endpoint: str, params: Optional[dict] = None
    ) -> Optional[dict]:
        """Make a read-only GET request to the Polarion REST API."""
        url = f"{self._polarion_url}/rest/v1/{endpoint}"
        try:
            resp = requests.get(
                url,
                params=params,
                headers={
                    'Authorization': f'Bearer {self._polarion_token}',
                    'Accept': 'application/json',
                },
                timeout=self.POLARION_TIMEOUT,
                verify=False,
            )
            if resp.status_code != 200:
                self.logger.debug(f"Polarion GET {endpoint}: HTTP {resp.status_code}")
                return None
            return resp.json()
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"Polarion request failed: {e}")
            return None

    @staticmethod
    def _strip_html(html_str: str) -> str:
        """Strip HTML tags and decode entities."""
        text = re.sub(r'<[^>]+>', ' ', html_str)
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _load_polarion_token(self) -> str:
        """Try to load Polarion token from .env file in mcp/polarion/."""
        # __file__ is src/services/environment_oracle_service.py
        # App root (z-stream-analysis/) is 3 parents up
        # Repo root (ai_systems_v2/) is 5 parents up — where mcp/ lives
        app_root = Path(__file__).parent.parent.parent
        repo_root = app_root.parent.parent
        for env_path in [
            repo_root / 'mcp' / 'polarion' / '.env',
            app_root / 'mcp' / 'polarion' / '.env',
            Path.home() / '.polarion' / '.env',
        ]:
            if env_path.exists():
                for line in env_path.read_text().splitlines():
                    line = line.strip()
                    if line.startswith('POLARION_PAT=') and not line.endswith('HERE'):
                        return line.split('=', 1)[1].strip()
        return ''

    # ------------------------------------------------------------------
    # Phase 3: Learn how the feature works (KG-driven — Phase C)
    # ------------------------------------------------------------------

    def _phase3_learn_feature(
        self,
        identification: Dict[str, Any],
        kg_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Learn how the feature works from two knowledge sources:
        1. Knowledge Graph — component topology, data flow, dependency chains
        2. rhacm-docs — architecture documentation with detailed explanations

        The KG gives the structural skeleton (what depends on what).
        The docs give the semantic understanding (how it works, what breaks).
        """
        feature_areas = identification.get('feature_areas', [])
        profiles = self.feature_knowledge.profiles
        context: Dict[str, Any] = {}
        subsystems_investigated = []

        # --- Source 1: Knowledge Graph (structural skeleton) ---
        kg_available = bool(kg_client and getattr(kg_client, 'available', False))
        context['kg_available'] = kg_available

        if kg_available:
            for area in feature_areas:
                profile = profiles.get(area, {})
                try:
                    components = kg_client.get_subsystem_components(area)
                    if not components:
                        display = profile.get('display_name', area)
                        components = kg_client.get_subsystem_components(display)

                    if components:
                        subsystems_investigated.append(area)
                        context.setdefault('feature_components', {})[area] = components

                        internal_flow = self._kg_query_internal_flow(kg_client, area)
                        if internal_flow:
                            context.setdefault('internal_data_flow', {})[area] = internal_flow

                        cross_deps = self._kg_query_cross_subsystem(kg_client, area)
                        if cross_deps:
                            context.setdefault('cross_subsystem_dependencies', {})[area] = cross_deps

                        # Get transitive chains for ALL components (no limit)
                        transitive = self._kg_query_transitive_chains(
                            kg_client, components
                        )
                        if transitive:
                            context.setdefault('transitive_chains', {})[area] = transitive

                        # Get detailed component info for ALL components
                        comp_details = {}
                        for comp_name in components:
                            try:
                                info = kg_client.get_component_info(comp_name)
                                if info:
                                    comp_details[comp_name] = {
                                        'subsystem': info.subsystem,
                                        'type': info.component_type,
                                        'depends_on': info.dependencies or [],
                                        'depended_by': info.dependents or [],
                                    }
                            except Exception:
                                continue
                        if comp_details:
                            context.setdefault('component_details', {})[area] = comp_details

                except Exception as e:
                    self.logger.warning(f"Phase 3 KG: query failed for {area}: {e}")
                    context.setdefault('errors', []).append(f"Phase 3 KG {area}: {str(e)}")

        context['subsystems_investigated'] = subsystems_investigated

        # --- Source 2: rhacm-docs (architecture documentation) ---
        docs_context = self._learn_from_docs(feature_areas)
        if docs_context:
            context['docs_context'] = docs_context

        # --- Playbook architecture summaries (always available) ---
        context['playbook_architecture'] = {
            area: {
                'summary': profiles.get(area, {}).get('architecture', {}).get('summary', ''),
                'key_insight': profiles.get(area, {}).get('architecture', {}).get('key_insight', ''),
            }
            for area in feature_areas if profiles.get(area)
        }

        kg_count = len(subsystems_investigated)
        docs_count = len(docs_context) if docs_context else 0
        self.logger.info(
            f"Phase 3: learned from KG ({kg_count} subsystems) + "
            f"docs ({docs_count} feature areas)"
        )
        return context

    def _learn_from_docs(
        self, feature_areas: List[str]
    ) -> Dict[str, Any]:
        """
        Provide the rhacm-docs path and directory index for the AI agent
        to search intelligently during Stage 2. The oracle does NOT
        pre-parse or score docs — the AI decides what to read based on
        its understanding of the feature and failure context.

        Returns: docs path + directory listing for AI navigation.
        """
        if not self._docs_dir or not Path(self._docs_dir).is_dir():
            self.logger.debug("Phase 3 docs: rhacm-docs directory not found — skipping")
            return {}

        docs_root = Path(self._docs_dir)

        # Build a directory index so the AI knows what's available
        directories = sorted([
            str(d.relative_to(docs_root))
            for d in docs_root.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ])

        return {
            'docs_path': str(docs_root),
            'available_directories': directories,
            'note': (
                'Use Read/Grep tools to search these docs during Stage 2 analysis. '
                'Search for feature-relevant architecture, data flows, prerequisites, '
                'and known failure patterns. The AI determines what to search for.'
            ),
        }

    def _find_rhacm_docs(self) -> Optional[str]:
        """Auto-discover rhacm-docs directory."""
        candidates = [
            # Relative to app dir
            Path(__file__).parent.parent.parent.parent.parent.parent
            / 'automation' / 'documentation' / 'architecture' / 'rhacm-docs',
            # Common locations
            Path.home() / 'Documents' / 'work' / 'automation'
            / 'documentation' / 'architecture' / 'rhacm-docs',
        ]
        for p in candidates:
            if p.is_dir() and (p / 'about').is_dir():
                self.logger.info(f"Found rhacm-docs at: {p}")
                return str(p)
        return None

    def _kg_query_internal_flow(
        self, kg_client: Any, subsystem: str
    ) -> List[str]:
        """Query KG for internal data flow within a subsystem."""
        escaped = kg_client._escape_regex(subsystem)
        query = (
            f"MATCH (c:RHACMComponent)-[r]->(dep:RHACMComponent) "
            f"WHERE c.subsystem =~ '(?i).*{escaped}.*' "
            f"AND dep.subsystem =~ '(?i).*{escaped}.*' "
            f"RETURN DISTINCT c.label as source, type(r) as rel, dep.label as target "
            f"ORDER BY c.label LIMIT 30"
        )
        results = kg_client._execute_cypher(query)
        if not results:
            return []
        return [
            f"{r.get('source')} --{r.get('rel')}--> {r.get('target')}"
            for r in results
        ]

    def _kg_query_cross_subsystem(
        self, kg_client: Any, subsystem: str
    ) -> List[str]:
        """Query KG for cross-subsystem dependencies."""
        escaped = kg_client._escape_regex(subsystem)
        query = (
            f"MATCH (c:RHACMComponent)-[r]->(dep:RHACMComponent) "
            f"WHERE c.subsystem =~ '(?i).*{escaped}.*' "
            f"AND NOT dep.subsystem =~ '(?i).*{escaped}.*' "
            f"RETURN DISTINCT c.label as source, type(r) as rel, "
            f"dep.label as target, dep.subsystem as target_subsystem "
            f"ORDER BY dep.subsystem LIMIT 20"
        )
        results = kg_client._execute_cypher(query)
        if not results:
            return []
        return [
            f"{r.get('source')} --{r.get('rel')}--> {r.get('target')} ({r.get('target_subsystem')})"
            for r in results
        ]

    def _kg_query_transitive_chains(
        self, kg_client: Any, components: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get transitive dependency chains for key components."""
        chains = {}
        for comp in components:
            try:
                chain = kg_client.get_transitive_dependents(comp, max_depth=3)
                if chain and chain.affected_components:
                    chains[comp] = {
                        'affected_components': chain.affected_components[:10],
                        'subsystems_affected': chain.subsystems_affected,
                        'chain_length': chain.chain_length,
                    }
            except Exception:
                continue
        return chains

    # ------------------------------------------------------------------
    # Phase 4: Learn the dependencies (KG-driven — Phase C)
    # ------------------------------------------------------------------

    def _phase4_learn_dependencies_comprehensive(
        self,
        identification: Dict[str, Any],
        dep_subsystems: Set[str],
        kg_client: Any,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Learn about each dependency subsystem at the same depth as Phase 3.
        For each cross-subsystem dependency, get ALL its components,
        internal data flow, and component details.
        """
        details: Dict[str, Dict[str, Any]] = {}
        feature_areas = set(identification.get('feature_areas', []))

        for subsystem in dep_subsystems:
            # Skip if this is the primary feature (already learned in Phase 3)
            if subsystem in feature_areas:
                continue

            try:
                components = kg_client.get_subsystem_components(subsystem)
                if not components:
                    continue

                sub_detail: Dict[str, Any] = {
                    'subsystem': subsystem,
                    'components': components,
                }

                # Internal data flow within this dependency subsystem
                internal_flow = self._kg_query_internal_flow(kg_client, subsystem)
                if internal_flow:
                    sub_detail['internal_data_flow'] = internal_flow

                # Component details for each component in this subsystem
                comp_details = {}
                for comp_name in components:
                    try:
                        info = kg_client.get_component_info(comp_name)
                        if info:
                            comp_details[comp_name] = {
                                'type': info.component_type,
                                'depends_on': info.dependencies or [],
                                'depended_by': info.dependents or [],
                            }
                    except Exception:
                        continue
                if comp_details:
                    sub_detail['component_details'] = comp_details

                details[subsystem] = sub_detail

            except Exception as e:
                self.logger.debug(f"Phase 4: KG learning failed for {subsystem}: {e}")

        self.logger.info(
            f"Phase 4: learned {len(details)} dependency subsystem(s) "
            f"from {len(dep_subsystems)} cross-subsystem deps"
        )
        return details

    # ------------------------------------------------------------------
    # Phase 5: Synthesize dependency model from playbooks
    # ------------------------------------------------------------------

    def _phase5_synthesize(
        self,
        identification: Dict[str, Any],
        cluster_landscape: Dict[str, Any],
        knowledge_context: Dict[str, Any],
    ) -> List[DependencyTarget]:
        """
        Merge ALL sources into one comprehensive collection plan:
        1. Playbook prerequisites (operators, addons, CRDs)
        2. KG feature components from Phase 3 (pods/deployments)
        3. KG dependency components from Phase 4 (cross-subsystem pods)
        4. Managed clusters (always collected)
        """
        feature_areas = identification['feature_areas']

        # Load playbooks for the identified feature areas
        acm_version = self._extract_acm_version(cluster_landscape)
        profiles = self.feature_knowledge.load_playbooks(
            acm_version=acm_version,
            feature_areas=feature_areas,
        )

        targets: List[DependencyTarget] = []
        seen_ids: Set[str] = set()

        # --- Source 1: Playbook prerequisites (operators, addons, CRDs) ---
        for area_name, profile in profiles.items():
            for prereq in profile.get('prerequisites', []):
                prereq_id = prereq.get('id', '')
                prereq_type = prereq.get('type', '')

                if prereq_type not in ('operator', 'addon', 'crd'):
                    continue
                if prereq_id in seen_ids:
                    continue
                seen_ids.add(prereq_id)

                check_spec = prereq.get('check_spec', {})
                targets.append(DependencyTarget(
                    id=prereq_id,
                    type=prereq_type,
                    name=check_spec.get('component_name', prereq_id),
                    description=prereq.get('description', ''),
                    namespace=check_spec.get('namespace'),
                    component_name=check_spec.get('component_name'),
                    source='playbook',
                ))

        playbook_count = len(targets)

        # --- Source 2: KG feature components from Phase 3 ---
        feature_components = knowledge_context.get('feature_components', {})
        for area, components in feature_components.items():
            # Get namespace from feature grounding or playbook
            profile = profiles.get(area, {})
            arch = profile.get('architecture', {})
            key_comps = arch.get('key_components', [])
            # Build namespace lookup from playbook key_components
            comp_ns_map = {}
            for kc in key_comps:
                if isinstance(kc, dict) and kc.get('name') and kc.get('namespace'):
                    comp_ns_map[kc['name']] = kc['namespace']

            for comp_name in components:
                comp_id = f"kg-{area.lower()}-{comp_name}"
                if comp_id in seen_ids:
                    continue
                seen_ids.add(comp_id)

                # Use playbook namespace if known, otherwise None
                # (Phase 6 will search all namespaces when namespace is None)
                ns = comp_ns_map.get(comp_name)
                targets.append(DependencyTarget(
                    id=comp_id,
                    type='component',
                    name=comp_name,
                    description=f"KG component in {area} subsystem",
                    namespace=ns,
                    component_name=comp_name,
                    source='kg',
                    subsystem=area,
                ))

        kg_feature_count = len(targets) - playbook_count

        # --- Source 3: KG dependency components from Phase 4 ---
        dep_details = knowledge_context.get('dependency_details', {})
        for subsystem, sub_info in dep_details.items():
            dep_components = sub_info.get('components', [])
            for comp_name in dep_components:
                comp_id = f"kg-dep-{subsystem.lower()}-{comp_name}"
                if comp_id in seen_ids:
                    continue
                seen_ids.add(comp_id)

                targets.append(DependencyTarget(
                    id=comp_id,
                    type='component',
                    name=comp_name,
                    description=f"KG dependency component in {subsystem}",
                    namespace=None,  # Phase 6 searches all namespaces
                    component_name=comp_name,
                    source='kg',
                    subsystem=subsystem,
                ))

        kg_dep_count = len(targets) - playbook_count - kg_feature_count

        # --- Source 4: Managed clusters (always collected) ---
        mc_id = 'managed-clusters-status'
        if mc_id not in seen_ids:
            seen_ids.add(mc_id)
            targets.append(DependencyTarget(
                id=mc_id,
                type='managed_clusters',
                name='managed-clusters',
                description='Status of all managed clusters',
                source='system',
            ))

        self.logger.info(
            f"Phase 5: {len(targets)} total targets "
            f"({playbook_count} playbook, {kg_feature_count} KG feature, "
            f"{kg_dep_count} KG dependency, 1 managed-clusters)"
        )
        return targets

    def _extract_acm_version(self, cluster_landscape: Dict[str, Any]) -> Optional[str]:
        """Extract ACM version from cluster landscape MCH version."""
        mch_version = cluster_landscape.get('mch_version', '')
        if mch_version:
            match = re.match(r'(\d+\.\d+)', mch_version)
            if match:
                return match.group(1)
        return None

    # ------------------------------------------------------------------
    # Phase 6: Cluster investigation
    # ------------------------------------------------------------------

    def _phase6_collect_cluster_state(
        self, targets: List[DependencyTarget]
    ) -> List[DependencyHealth]:
        """
        Comprehensive cluster state collection for EVERY target from Phase 5.
        Collects operators, addons, CRDs, component/pod status, and
        managed cluster state — building the complete knowledge base.
        """
        results: List[DependencyHealth] = []

        for target in targets:
            try:
                if target.type == 'operator':
                    health = self._check_operator(target)
                elif target.type == 'addon':
                    health = self._check_addon(target)
                elif target.type == 'crd':
                    health = self._check_crd(target)
                elif target.type == 'component':
                    health = self._check_component(target)
                elif target.type == 'managed_clusters':
                    health = self._check_managed_clusters(target)
                else:
                    health = DependencyHealth(
                        id=target.id, type=target.type, name=target.name,
                        status='unchecked',
                        detail=f"Unknown target type: {target.type}",
                    )
                results.append(health)
            except Exception as e:
                self.logger.warning(f"Failed to collect {target.id}: {e}")
                results.append(DependencyHealth(
                    id=target.id, type=target.type, name=target.name,
                    status='unknown', detail=f"Collection failed: {str(e)}",
                ))

        healthy = sum(1 for r in results if r.status == 'healthy')
        total = len(results)
        self.logger.info(
            f"Phase 6: collected state for {total} targets, "
            f"{healthy} healthy"
        )
        return results

    def _check_operator(self, target: DependencyTarget) -> DependencyHealth:
        """Check if an operator is installed and healthy via CSV."""
        # Use target namespace if known, otherwise search all namespaces
        if target.namespace:
            cmd_args = ['get', 'csv', '-n', target.namespace, '--no-headers']
            cmd_str = f"get csv -n {target.namespace} --no-headers"
        else:
            cmd_args = ['get', 'csv', '-A', '--no-headers']
            cmd_str = "get csv -A --no-headers"
        namespace = target.namespace or 'all namespaces'
        success, stdout, stderr = self._run_command(cmd_args)

        if not success:
            return DependencyHealth(
                id=target.id, type='operator', name=target.name,
                status='missing',
                detail=f"Cannot list CSVs in namespace {namespace}: {stderr[:200]}",
                check_command=f"oc {cmd_str}",
            )

        # Parse CSV output lines: NAME DISPLAY VERSION REPLACES PHASE
        operator_name = (target.component_name or target.name or '').lower()
        for line in stdout.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 2:
                csv_name = parts[0].lower()
                csv_phase = parts[-1] if len(parts) >= 2 else 'Unknown'

                # Prefix match: 'hive-operator' matches 'hive-operator.v1.2.3'
                # but not 'hive-prereq-checker.v1.0'
                if csv_name.startswith(operator_name):
                    if csv_phase.lower() == 'succeeded':
                        return DependencyHealth(
                            id=target.id, type='operator', name=target.name,
                            status='healthy',
                            detail=f"CSV {parts[0]} phase={csv_phase}",
                            raw_output=line,
                            check_command=f"oc {cmd_str}",
                        )
                    else:
                        return DependencyHealth(
                            id=target.id, type='operator', name=target.name,
                            status='degraded',
                            detail=f"CSV {parts[0]} phase={csv_phase} (expected Succeeded)",
                            raw_output=line,
                            check_command=f"oc {cmd_str}",
                        )

        # CSV not found -- fallback: check if pods are running in the namespace.
        # Some operators (e.g., Hive) are deployed directly by MCH without a CSV.
        if target.namespace:
            pod_success, pod_stdout, _ = self._run_command([
                'get', 'pods', '-n', target.namespace, '--no-headers',
            ])
            if pod_success and pod_stdout.strip():
                running_pods = [
                    line for line in pod_stdout.strip().split('\n')
                    if 'Running' in line
                ]
                if running_pods:
                    return DependencyHealth(
                        id=target.id, type='operator', name=target.name,
                        status='healthy',
                        detail=(
                            f"No CSV found for '{operator_name}' in {namespace}, "
                            f"but {len(running_pods)} pod(s) Running "
                            f"(operator may be deployed without OLM)"
                        ),
                        raw_output=pod_stdout[:300],
                        check_command=f"oc get pods -n {target.namespace} --no-headers",
                    )

        return DependencyHealth(
            id=target.id, type='operator', name=target.name,
            status='missing',
            detail=f"Operator '{operator_name}' CSV not found in {namespace} and no running pods",
            raw_output=stdout[:300],
            check_command=f"oc {cmd_str}",
        )

    def _check_addon(self, target: DependencyTarget) -> DependencyHealth:
        """Check if a managed cluster addon is deployed and available."""
        addon_name = target.component_name or target.name
        cmd_str = f"get managedclusteraddon -A --field-selector metadata.name={addon_name} --no-headers"
        success, stdout, stderr = self._run_command([
            'get', 'managedclusteraddon', '-A',
            f'--field-selector=metadata.name={addon_name}',
            '--no-headers',
        ])

        if not success:
            # Field selector may not be supported — fall back to get all and filter
            success, stdout, stderr = self._run_command([
                'get', 'managedclusteraddon', '-A', '--no-headers',
            ])
            if success and stdout.strip():
                # Filter lines matching addon name
                lines = [
                    l for l in stdout.strip().split('\n')
                    if addon_name.lower() in l.lower()
                ]
                stdout = '\n'.join(lines)
            else:
                return DependencyHealth(
                    id=target.id, type='addon', name=addon_name,
                    status='unknown',
                    detail=f"Cannot list ManagedClusterAddons: {stderr[:200]}",
                    check_command=f"oc get managedclusteraddon -A --no-headers",
                )

        if not stdout.strip():
            return DependencyHealth(
                id=target.id, type='addon', name=addon_name,
                status='missing',
                detail=f"Addon '{addon_name}' not found on any managed cluster",
                check_command=f"oc get managedclusteraddon -A --no-headers",
            )

        # Parse: NAMESPACE(cluster) NAME AVAILABLE DEGRADED STATUS
        lines = stdout.strip().split('\n')
        total = len(lines)
        available_count = 0
        degraded_clusters = []

        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                cluster = parts[0]
                # Look for Available=True in the line
                if 'True' in line.split(addon_name, 1)[-1] if addon_name in line else 'True' in line:
                    available_count += 1
                else:
                    degraded_clusters.append(cluster)

        if available_count == total:
            return DependencyHealth(
                id=target.id, type='addon', name=addon_name,
                status='healthy',
                detail=f"Available on {total} cluster(s)",
                check_command=f"oc get managedclusteraddon -A --no-headers",
            )
        elif available_count > 0:
            return DependencyHealth(
                id=target.id, type='addon', name=addon_name,
                status='degraded',
                detail=(
                    f"Available on {available_count}/{total} clusters. "
                    f"Degraded on: {', '.join(degraded_clusters[:5])}"
                ),
                check_command=f"oc get managedclusteraddon -A --no-headers",
            )
        else:
            return DependencyHealth(
                id=target.id, type='addon', name=addon_name,
                status='degraded',
                detail=f"Not available on any of {total} cluster(s)",
                check_command=f"oc get managedclusteraddon -A --no-headers",
            )

    def _check_crd(self, target: DependencyTarget) -> DependencyHealth:
        """Check if a CRD exists on the cluster."""
        crd_name = target.component_name or target.name
        cmd_str = f"get crd {crd_name} --no-headers"
        success, stdout, stderr = self._run_command(
            ['get', 'crd', crd_name, '--no-headers']
        )

        if success and stdout.strip():
            return DependencyHealth(
                id=target.id, type='crd', name=crd_name,
                status='healthy',
                detail=f"CRD '{crd_name}' exists",
                check_command=f"oc {cmd_str}",
            )
        else:
            return DependencyHealth(
                id=target.id, type='crd', name=crd_name,
                status='missing',
                detail=f"CRD '{crd_name}' not found: {stderr[:200]}",
                check_command=f"oc {cmd_str}",
            )

    def _check_component(self, target: DependencyTarget) -> DependencyHealth:
        """Check a component's deployment/pod status on the cluster."""
        comp_name = target.component_name or target.name
        # No default namespace — search all namespaces with -A

        # Try deployment first
        cmd_str = f"get deployment -A --no-headers"
        success, stdout, stderr = self._run_command(
            ['get', 'deployment', '-A', '--no-headers']
        )

        if success and stdout.strip():
            # Match by deployment name (column 2) — exact match or prefix,
            # not arbitrary substring, to avoid 'api' matching 'search-api'
            matching = []
            for l in stdout.strip().split('\n'):
                parts = l.split()
                if len(parts) >= 2:
                    deploy_name = parts[1].lower()
                    if (deploy_name == comp_name.lower()
                            or deploy_name.startswith(comp_name.lower() + '-')
                            or deploy_name.startswith(comp_name.lower() + '.')):
                        matching.append(l)
            if matching:
                # Parse: NAMESPACE NAME READY UP-TO-DATE AVAILABLE AGE
                line = matching[0]
                parts = line.split()
                if len(parts) >= 4:
                    ns = parts[0]
                    name = parts[1]
                    ready = parts[2]  # e.g., "1/1"
                    available = parts[4] if len(parts) >= 5 else '?'

                    try:
                        ready_parts = ready.split('/')
                        ready_count = int(ready_parts[0])
                        desired_count = int(ready_parts[1])
                        is_ready = ready_count == desired_count and desired_count > 0
                    except (ValueError, IndexError):
                        is_ready = False

                    status = 'healthy' if is_ready else 'degraded'
                    detail = (
                        f"Deployment {name} in {ns}: "
                        f"ready={ready}, available={available}"
                    )
                    if len(matching) > 1:
                        detail += f" (+{len(matching)-1} more matches)"

                    return DependencyHealth(
                        id=target.id, type='component', name=comp_name,
                        status=status, detail=detail,
                        raw_output='\n'.join(matching[:3]),
                        check_command=f"oc {cmd_str} | grep {comp_name}",
                    )

        # Deployment not found — try pods (match by pod name prefix)
        success, stdout, stderr = self._run_command(
            ['get', 'pods', '-A', '--no-headers']
        )
        if success and stdout.strip():
            matching = []
            for l in stdout.strip().split('\n'):
                parts = l.split()
                if len(parts) >= 2:
                    pod_name = parts[1].lower()
                    if (pod_name == comp_name.lower()
                            or pod_name.startswith(comp_name.lower() + '-')
                            or pod_name.startswith(comp_name.lower() + '.')):
                        matching.append(l)
            if matching:
                line = matching[0]
                parts = line.split()
                if len(parts) >= 4:
                    ns = parts[0]
                    pod_name = parts[1]
                    ready = parts[2]
                    pod_status = parts[3]
                    restarts = parts[4] if len(parts) >= 5 else '0'

                    is_running = pod_status.lower() in ('running', 'completed')
                    status = 'healthy' if is_running else 'degraded'
                    detail = (
                        f"Pod {pod_name} in {ns}: "
                        f"status={pod_status}, ready={ready}, restarts={restarts}"
                    )
                    if len(matching) > 1:
                        detail += f" (+{len(matching)-1} more pods)"

                    return DependencyHealth(
                        id=target.id, type='component', name=comp_name,
                        status=status, detail=detail,
                        raw_output='\n'.join(matching[:5]),
                        check_command=f"oc get pods -A --no-headers | grep {comp_name}",
                    )

        return DependencyHealth(
            id=target.id, type='component', name=comp_name,
            status='missing',
            detail=f"No deployment or pod found matching '{comp_name}'",
            check_command=f"oc get deployment -A --no-headers | grep {comp_name}",
        )

    def _check_managed_clusters(self, target: DependencyTarget) -> DependencyHealth:
        """Collect status of all managed clusters.

        Filters out recently-created clusters (< 4 hours old) because those
        are likely test artifacts still being provisioned, not pre-existing
        infrastructure failures.
        """
        success, stdout, stderr = self._run_command(
            ['get', 'managedclusters',
             '-o', 'custom-columns=NAME:.metadata.name,'
             'AVAILABLE:.status.conditions[?(@.type=="ManagedClusterConditionAvailable")].status,'
             'AGE:.metadata.creationTimestamp',
             '--no-headers']
        )

        if not success:
            # Fallback to simple listing
            success, stdout, stderr = self._run_command(
                ['get', 'managedclusters', '--no-headers']
            )
            if not success:
                return DependencyHealth(
                    id=target.id, type='managed_clusters', name='managed-clusters',
                    status='unknown',
                    detail=f"Cannot list managed clusters: {stderr[:200]}",
                    check_command='oc get managedclusters --no-headers',
                )

        if not stdout.strip():
            return DependencyHealth(
                id=target.id, type='managed_clusters', name='managed-clusters',
                status='degraded',
                detail='No managed clusters found',
                check_command='oc get managedclusters --no-headers',
            )

        lines = stdout.strip().split('\n')
        total = 0
        ready_count = 0
        cluster_statuses = []
        skipped_young = 0

        now = datetime.now(timezone.utc)

        for line in lines:
            parts = line.split()
            if len(parts) >= 1:
                cluster_name = parts[0]

                # Try to parse creation timestamp to filter young clusters
                is_young = False
                for part in parts:
                    if re.match(r'\d{4}-\d{2}-\d{2}T', part):
                        try:
                            created = datetime.fromisoformat(
                                part.replace('Z', '+00:00')
                            )
                            age_hours = (now - created).total_seconds() / 3600
                            if age_hours < 4:
                                is_young = True
                        except (ValueError, TypeError):
                            pass

                if is_young and cluster_name != 'local-cluster':
                    skipped_young += 1
                    cluster_statuses.append(
                        f"{cluster_name}: skipped (< 4h old, likely test artifact)"
                    )
                    continue

                total += 1
                is_available = 'True' in line
                if is_available:
                    ready_count += 1
                cluster_statuses.append(
                    f"{cluster_name}: {'Ready' if is_available else 'NotReady'}"
                )

        if total == 0:
            total = 1  # at least local-cluster should exist

        status = 'healthy' if ready_count == total else 'degraded'
        if ready_count == 0:
            status = 'degraded'

        young_note = f" ({skipped_young} young cluster(s) excluded)" if skipped_young else ""

        return DependencyHealth(
            id=target.id, type='managed_clusters', name='managed-clusters',
            status=status,
            detail=f"{ready_count}/{total} clusters ready{young_note}. {'; '.join(cluster_statuses)}",
            raw_output=stdout[:500],
            check_command='oc get managedclusters --no-headers',
        )

    # ------------------------------------------------------------------
    # Overall health computation
    # ------------------------------------------------------------------

    def _compute_overall_health(
        self,
        dependency_health: Dict[str, Dict[str, Any]],
        feature_areas: List[str],
    ) -> Dict[str, Any]:
        """Compute overall feature health from dependency results."""
        if not dependency_health:
            return {
                'score': None,
                'signal': 'unknown',
                'blocking_issues': [],
                'summary': 'No dependency health data available',
            }

        total = len(dependency_health)
        healthy = sum(
            1 for d in dependency_health.values()
            if d.get('status') == 'healthy'
        )
        degraded = [
            d for d in dependency_health.values()
            if d.get('status') in ('degraded', 'missing')
        ]
        # Count only genuinely confirmed-missing (not just CSV-not-found with
        # pods running, which is reported as 'healthy' after the pod fallback).
        confirmed_missing = sum(
            1 for d in dependency_health.values()
            if d.get('status') == 'missing'
        )

        score = healthy / total if total > 0 else 1.0

        # Determine signal strength.  A 'definitive' signal is only warranted
        # when MULTIPLE dependencies are confirmed unhealthy.  A single
        # degraded/missing dependency should produce at most 'strong' to
        # prevent a single false positive from cascading to all tests.
        if confirmed_missing >= 2 and score < THRESHOLDS.INFRA_DEFINITIVE:
            signal = 'definitive'
        elif score < THRESHOLDS.INFRA_STRONG:
            signal = 'strong'
        elif score < THRESHOLDS.INFRA_MODERATE:
            signal = 'moderate'
        else:
            signal = 'none'

        blocking_issues = [
            f"{d.get('name', '?')} ({d.get('type', '?')}): {d.get('detail', 'unhealthy')}"
            for d in degraded
        ]

        return {
            'score': round(score, 2),
            'signal': signal,
            'total_dependencies': total,
            'healthy_count': healthy,
            'degraded_count': len(degraded),
            'blocking_issues': blocking_issues,
            'feature_areas': feature_areas,
            'summary': (
                f"{healthy}/{total} dependencies healthy"
                + (f". Issues: {'; '.join(blocking_issues)}" if blocking_issues else "")
            ),
        }

    # ------------------------------------------------------------------
    # Cluster command execution (read-only enforced)
    # ------------------------------------------------------------------

    def _login(self, api_url: str, username: str, password: str) -> bool:
        """Login to the target cluster. Returns True on success."""
        if not api_url or not username or not password:
            self.logger.warning("Oracle: Missing cluster credentials")
            return False

        try:
            fd, self._temp_kubeconfig = tempfile.mkstemp(
                prefix='oracle_kubeconfig_', suffix='.yaml'
            )
            os.close(fd)

            cmd = [
                self._cli_binary,
                '--kubeconfig', self._temp_kubeconfig,
                'login', api_url,
                '--username', username,
                '--password', password,
                '--insecure-skip-tls-verify=true',
            ]
            # Mask password in logs
            safe_cmd = [
                c if c != password else '***MASKED***' for c in cmd
            ]
            self.logger.info(f"Oracle login: {' '.join(safe_cmd)}")

            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if proc.returncode == 0:
                self._logged_in = True
                self.logger.info("Oracle: Cluster login succeeded")
                return True
            else:
                self.logger.warning(
                    f"Oracle: Cluster login failed: {proc.stderr[:200]}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Oracle login error: {e}")
            return False

    def _run_command(
        self, args: List[str], timeout: int = 30
    ) -> Tuple[bool, str, str]:
        """Run a read-only oc command. Returns (success, stdout, stderr)."""
        if not self._validate_readonly(args):
            return False, '', 'Command blocked: READ-ONLY mode violation'

        cmd = [self._cli_binary]
        if self._temp_kubeconfig:
            cmd.extend(['--kubeconfig', self._temp_kubeconfig])
        cmd.extend(args)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return proc.returncode == 0, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return False, '', f'Command timed out after {timeout}s'
        except Exception as e:
            return False, '', str(e)

    def _validate_readonly(self, args: List[str]) -> bool:
        """Validate command is in the read-only allowed set."""
        if not validate_command_readonly(args, self.ALLOWED_COMMANDS, "EnvironmentOracleService"):
            return False

        primary_cmd = args[0] if args else ''

        # get, describe, api-resources, version, whoami are always safe
        if primary_cmd in ('get', 'describe', 'api-resources', 'version', 'whoami'):
            return True

        # auth only allows can-i
        if primary_cmd == 'auth':
            if len(args) >= 2 and args[1] == 'can-i':
                return True
            self.logger.warning("READ-ONLY VIOLATION: 'auth' only allows 'can-i'")
            return False

        # login/logout are allowed for session management
        if primary_cmd in ('login', 'logout'):
            return True

        self.logger.warning(f"READ-ONLY VIOLATION: command '{primary_cmd}' not allowed")
        return False

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def _detect_cli(self) -> str:
        """Detect oc or kubectl CLI binary."""
        for binary in ['oc', 'kubectl']:
            try:
                result = subprocess.run(
                    ['which', binary], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return binary
            except Exception:
                continue
        return 'oc'

    def _cleanup(self):
        """Clean up temporary kubeconfig."""
        if self._temp_kubeconfig and os.path.exists(self._temp_kubeconfig):
            try:
                os.unlink(self._temp_kubeconfig)
            except OSError:
                pass
            self._temp_kubeconfig = None
        self._logged_in = False

