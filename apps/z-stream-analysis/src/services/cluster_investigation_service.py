#!/usr/bin/env python3
"""
Cluster Investigation Service

Targeted component diagnostics for Stage 2 AI analysis.
Extends EnvironmentValidationService (basic connectivity) with deep pod-level
investigation: pod status, restart counts, events, log tails, resource pressure.

Separate from EnvironmentValidationService because of different lifecycle:
- EnvironmentValidationService runs in Stage 1 gather (always)
- ClusterInvestigationService runs on-demand during Stage 2 AI analysis
  and during Stage 1 gather for cluster landscape snapshot

IMPORTANT: All operations are READ-ONLY.
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field

from .shared_utils import dataclass_to_dict, validate_command_readonly, THRESHOLDS
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class FeatureAreaHealth:
    """Per-feature-area health score based on component diagnostics."""
    feature_area: str
    health_score: float = 0.0  # 0.0 (all components down) to 1.0 (all healthy)
    total_components: int = 0
    healthy_components: int = 0
    degraded_components: List[str] = field(default_factory=list)
    unhealthy_components: List[str] = field(default_factory=list)
    total_restart_count: int = 0
    has_operator_degraded: bool = False
    infrastructure_signal: str = 'none'  # none, moderate, strong, definitive


@dataclass
class PodDiagnostics:
    """Diagnostics for a single pod."""
    name: str
    namespace: str
    status: str  # Running, CrashLoopBackOff, Error, Pending, Unknown
    restart_count: int = 0
    ready: bool = False
    recent_events: List[str] = field(default_factory=list)
    log_tail: Optional[str] = None  # Last 50 lines


@dataclass
class ComponentDiagnostics:
    """Diagnostics for a component (deployment/statefulset)."""
    component_name: str
    subsystem: str
    deployment_status: str  # Available, Degraded, Missing
    desired_replicas: int = 0
    ready_replicas: int = 0
    pods: List[PodDiagnostics] = field(default_factory=list)


@dataclass
class ClusterLandscape:
    """High-level cluster state snapshot (Joydeep's 'lay of the land')."""
    managed_cluster_count: int = 0
    managed_cluster_statuses: Dict[str, int] = field(default_factory=dict)
    operator_statuses: Dict[str, str] = field(default_factory=dict)
    degraded_operators: List[str] = field(default_factory=list)
    resource_pressure: Dict[str, bool] = field(default_factory=dict)
    policy_count: int = 0
    multiclusterhub_status: Optional[str] = None
    mch_enabled_components: Dict[str, bool] = field(default_factory=dict)
    mch_version: Optional[str] = None


def build_component_namespace_map(mch_ns: str = 'open-cluster-management') -> Dict[str, tuple]:
    """
    Build component-to-namespace mapping for targeted investigation.

    The MCH namespace varies by installation (open-cluster-management, ocm, custom).
    Derived namespaces follow the pattern: {mch_ns}-hub, {mch_ns}-observability, etc.

    Args:
        mch_ns: The discovered MCH namespace.

    Returns:
        Dict mapping component name to (namespace, resource_type) tuple.
    """
    return {
        # Governance
        'grc-policy-propagator': (mch_ns, 'deployment'),
        'config-policy-controller': (mch_ns, 'deployment'),
        'governance-policy-framework': (mch_ns, 'deployment'),
        'policy-propagator': (mch_ns, 'deployment'),
        'iam-policy-controller': (mch_ns, 'deployment'),
        'cert-policy-controller': (mch_ns, 'deployment'),
        # Search
        'search-api': (mch_ns, 'deployment'),
        'search-collector': (mch_ns, 'deployment'),
        'search-indexer': (mch_ns, 'deployment'),
        'search-aggregator': (mch_ns, 'deployment'),
        'search-operator': (mch_ns, 'deployment'),
        'search-postgres': (mch_ns, 'deployment'),
        # Cluster Management
        'cluster-curator': (mch_ns, 'deployment'),
        'cluster-curator-controller': (mch_ns, 'deployment'),
        'managedcluster-import-controller': (mch_ns, 'deployment'),
        'cluster-manager': (mch_ns, 'deployment'),
        'registration-controller': (f'{mch_ns}-hub', 'deployment'),
        'registration-operator': (mch_ns, 'deployment'),
        'placement-controller': (f'{mch_ns}-hub', 'deployment'),
        'work-manager': (f'{mch_ns}-hub', 'deployment'),
        # Provisioning (fixed namespaces — not derived from MCH)
        'hive': ('hive', 'deployment'),
        'hive-operator': ('hive', 'deployment'),
        'hive-controllers': ('hive', 'deployment'),
        'hypershift-operator': ('hypershift', 'deployment'),
        'assisted-service': ('assisted-installer', 'deployment'),
        'infrastructure-operator': (mch_ns, 'deployment'),
        # Observability
        'observability-operator': (mch_ns, 'deployment'),
        'multicluster-observability-operator': (mch_ns, 'deployment'),
        'thanos-query': (f'{mch_ns}-observability', 'statefulset'),
        'thanos-receive': (f'{mch_ns}-observability', 'statefulset'),
        'thanos-store': (f'{mch_ns}-observability', 'statefulset'),
        'grafana': (f'{mch_ns}-observability', 'deployment'),
        'alertmanager': (f'{mch_ns}-observability', 'statefulset'),
        # Application
        'application-manager': (mch_ns, 'deployment'),
        'subscription-controller': (mch_ns, 'deployment'),
        'multicluster-operators-subscription': (mch_ns, 'deployment'),
        'channel-controller': (mch_ns, 'deployment'),
        # Console
        'console-api': (mch_ns, 'deployment'),
        'acm-console': (mch_ns, 'deployment'),
        'mce-console': ('multicluster-engine', 'deployment'),
        # Virtualization (fixed namespaces)
        'kubevirt-operator': ('openshift-cnv', 'deployment'),
        'virt-api': ('openshift-cnv', 'deployment'),
        'virt-controller': ('openshift-cnv', 'deployment'),
        'virt-handler': ('openshift-cnv', 'daemonset'),
        'hyperconverged-cluster-operator': ('openshift-cnv', 'deployment'),
        'cdi-operator': ('openshift-cnv', 'deployment'),
        'cdi-apiserver': ('openshift-cnv', 'deployment'),
        # Cross-Cluster Migration (fixed namespaces)
        'forklift-controller': ('openshift-mtv', 'deployment'),
        'submariner-gateway': ('submariner-operator', 'daemonset'),
        # Automation (fixed namespace)
        'aap-controller': ('aap', 'deployment'),
        # Foundation
        'work-agent': (f'{mch_ns}-agent', 'deployment'),
        'cluster-proxy': (mch_ns, 'deployment'),
        'managed-serviceaccount': (mch_ns, 'deployment'),
        # Infrastructure
        'klusterlet': (f'{mch_ns}-agent', 'deployment'),
        'klusterlet-agent': (f'{mch_ns}-agent', 'deployment'),
        'multicluster-engine': ('multicluster-engine', 'deployment'),
        'multicluster-hub': (mch_ns, 'deployment'),
        'foundation-controller': (mch_ns, 'deployment'),
        'addon-manager': (mch_ns, 'deployment'),
    }


# Default map for backward compatibility (used when no MCH namespace is provided)
COMPONENT_NAMESPACE_MAP = build_component_namespace_map()

# Subsystem-to-components mapping for batch diagnostics
SUBSYSTEM_COMPONENTS = {
    'Governance': [
        'grc-policy-propagator', 'config-policy-controller',
        'governance-policy-framework',
    ],
    'Search': [
        'search-api', 'search-collector', 'search-indexer',
    ],
    'Cluster': [
        'cluster-curator', 'managedcluster-import-controller',
        'cluster-manager', 'registration-operator',
    ],
    'Provisioning': [
        'hive-controllers', 'hypershift-operator',
        'assisted-service', 'infrastructure-operator',
    ],
    'Observability': [
        'multicluster-observability-operator',
        'thanos-query', 'grafana',
    ],
    'Application': [
        'application-manager', 'subscription-controller',
    ],
    'Console': [
        'console-api', 'acm-console',
    ],
    'Virtualization': [
        'kubevirt-operator', 'virt-api', 'virt-controller',
        'hyperconverged-cluster-operator',
    ],
    'Foundation': [
        'registration-controller', 'work-agent', 'work-manager',
        'cluster-proxy', 'managed-serviceaccount', 'addon-manager',
    ],
    'Install': [
        'multicluster-hub',
    ],
    'Infrastructure': [
        'klusterlet', 'multicluster-engine',
        'foundation-controller',
    ],
}

# Feature area to subsystem mapping for health scoring.
# Multiple feature areas may share a subsystem — e.g., Automation uses
# cluster-curator (Cluster subsystem) for running Ansible hooks, and
# RBAC uses console-api (Console subsystem) for access control.
FEATURE_AREA_SUBSYSTEM_MAP = {
    'GRC': 'Governance',
    'Search': 'Search',
    'CLC': 'Cluster',
    'Observability': 'Observability',
    'Virtualization': 'Virtualization',
    'Application': 'Application',
    'Console': 'Console',
    'Foundation': 'Foundation',
    'Install': 'Install',
    'Infrastructure': 'Infrastructure',
    'RBAC': 'Console',
    'Automation': 'Cluster',
}


class ClusterInvestigationService:
    """
    Cluster Investigation Service - targeted component diagnostics.

    All operations are READ-ONLY. Uses the same whitelist pattern as
    EnvironmentValidationService.

    Usage:
        service = ClusterInvestigationService()
        landscape = service.get_cluster_landscape()
        diag = service.diagnose_component('search-api')
    """

    ALLOWED_COMMANDS = {
        'get', 'describe', 'logs', 'adm', 'whoami', 'version',
    }

    def __init__(self, kubeconfig_path: Optional[str] = None, cli: str = 'oc'):
        self.logger = logging.getLogger(__name__)
        self.kubeconfig = kubeconfig_path
        self.cli = cli
        self._mch_namespace: str = 'open-cluster-management'
        self._component_map = COMPONENT_NAMESPACE_MAP

    @property
    def mch_namespace(self) -> str:
        return self._mch_namespace

    @mch_namespace.setter
    def mch_namespace(self, value: str):
        """Set MCH namespace and rebuild component map with correct namespaces."""
        self._mch_namespace = value
        self._component_map = build_component_namespace_map(value)
        self.logger.info(f"Component namespace map rebuilt for MCH namespace: {value}")

    def _build_command(self, args: List[str]) -> List[str]:
        cmd = [self.cli]
        if self.kubeconfig:
            cmd.extend(['--kubeconfig', self.kubeconfig])
        cmd.extend(args)
        return cmd

    def _validate_readonly(self, args: List[str]) -> bool:
        if not validate_command_readonly(args, self.ALLOWED_COMMANDS, "ClusterInvestigationService"):
            return False
        primary = args[0]
        if primary == 'adm':
            if len(args) >= 2 and args[1] == 'top':
                return True
            self.logger.warning("Only 'adm top' subcommand allowed")
            return False
        if primary == 'logs':
            # logs is read-only
            return True
        return True

    def _run_command(
        self, args: List[str], timeout: int = 30
    ) -> Tuple[bool, str, str]:
        if not self._validate_readonly(args):
            return False, '', 'Command blocked: READ-ONLY mode violation'
        cmd = self._build_command(args)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, '', f'Command timed out after {timeout}s'
        except Exception as e:
            return False, '', str(e)

    def get_cluster_landscape(self) -> ClusterLandscape:
        """
        Get high-level cluster state: managed clusters, operators,
        resource pressure, policies, MCH status.
        """
        landscape = ClusterLandscape()

        # Managed clusters
        success, stdout, _ = self._run_command(
            ['get', 'managedclusters', '-o', 'json', '--ignore-not-found']
        )
        if success and stdout.strip():
            try:
                data = json.loads(stdout)
                items = data.get('items', [])
                landscape.managed_cluster_count = len(items)
                statuses: Dict[str, int] = {}
                for item in items:
                    conditions = item.get('status', {}).get('conditions', [])
                    status = 'Unknown'
                    for c in conditions:
                        if c.get('type') == 'ManagedClusterConditionAvailable':
                            status = 'Ready' if c.get('status') == 'True' else 'NotReady'
                            break
                    statuses[status] = statuses.get(status, 0) + 1
                landscape.managed_cluster_statuses = statuses
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.debug(f"Failed to parse managed clusters: {e}")

        # Cluster operators
        success, stdout, _ = self._run_command(
            ['get', 'clusteroperators', '-o', 'json']
        )
        if success and stdout.strip():
            try:
                data = json.loads(stdout)
                for item in data.get('items', []):
                    name = item.get('metadata', {}).get('name', '')
                    conditions = item.get('status', {}).get('conditions', [])
                    status = 'Unknown'
                    degraded = False
                    for c in conditions:
                        if c.get('type') == 'Available':
                            status = 'Available' if c.get('status') == 'True' else 'Unavailable'
                        if c.get('type') == 'Degraded' and c.get('status') == 'True':
                            degraded = True
                    if degraded:
                        status = 'Degraded'
                        landscape.degraded_operators.append(name)
                    landscape.operator_statuses[name] = status
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.debug(f"Failed to parse cluster operators: {e}")

        # Resource pressure
        landscape.resource_pressure = self.get_resource_pressure()

        # Policy count
        success, stdout, _ = self._run_command(
            ['get', 'policies', '-A', '--no-headers', '--ignore-not-found']
        )
        if success and stdout.strip():
            landscape.policy_count = len(
                [l for l in stdout.strip().split('\n') if l.strip()]
            )

        # MultiClusterHub status + enabled components + version
        success, stdout, _ = self._run_command(
            ['get', 'multiclusterhub', '-A', '-o', 'json', '--ignore-not-found']
        )
        if success and stdout.strip():
            try:
                data = json.loads(stdout)
                items = data.get('items', [])
                if items:
                    mch = items[0]
                    phase = mch.get('status', {}).get('phase', 'Unknown')
                    landscape.multiclusterhub_status = phase

                    # Extract MCH version
                    mch_version = mch.get('status', {}).get('currentVersion')
                    if mch_version:
                        landscape.mch_version = mch_version

                    # Extract enabled components from spec.overrides.components
                    overrides = mch.get('spec', {}).get('overrides', {})
                    components = overrides.get('components', [])
                    for comp in components:
                        comp_name = comp.get('name', '')
                        comp_enabled = comp.get('enabled', True)
                        if comp_name:
                            landscape.mch_enabled_components[comp_name] = comp_enabled
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.debug(f"Failed to parse MultiClusterHub: {e}")

        return landscape

    def diagnose_component(
        self, component_name: str, namespace: Optional[str] = None
    ) -> ComponentDiagnostics:
        """
        Get pod status, restart count, recent events, and log tail
        for a single component.
        """
        # Resolve namespace and resource kind from map
        ns = namespace
        kind = 'deployment'
        component_lower = component_name.lower()

        if component_lower in self._component_map:
            mapped_ns, mapped_kind = self._component_map[component_lower]
            if not ns:
                ns = mapped_ns
            kind = mapped_kind
        elif not ns:
            ns = self._mch_namespace

        # Determine subsystem
        subsystem = 'Unknown'
        for sub, components in SUBSYSTEM_COMPONENTS.items():
            if component_lower in [c.lower() for c in components]:
                subsystem = sub
                break

        diag = ComponentDiagnostics(
            component_name=component_name,
            subsystem=subsystem,
            deployment_status='Missing',
        )

        # Get pods matching the component
        success, stdout, _ = self._run_command([
            'get', 'pods', '-n', ns,
            '-l', f'app={component_name}',
            '-o', 'json', '--ignore-not-found',
        ])

        pods_data = []
        if success and stdout.strip():
            try:
                data = json.loads(stdout)
                pods_data = data.get('items', [])
            except json.JSONDecodeError:
                pass

        # Fallback: try name-based match if label selector returned nothing
        if not pods_data:
            success, stdout, _ = self._run_command([
                'get', 'pods', '-n', ns, '-o', 'json', '--ignore-not-found',
            ])
            if success and stdout.strip():
                try:
                    data = json.loads(stdout)
                    for item in data.get('items', []):
                        pod_name = item.get('metadata', {}).get('name', '')
                        if component_lower in pod_name.lower():
                            pods_data.append(item)
                except json.JSONDecodeError:
                    pass

        if not pods_data:
            return diag

        # Parse pod data
        total_desired = 0
        total_ready = 0

        for pod_item in pods_data:
            pod_meta = pod_item.get('metadata', {})
            pod_status = pod_item.get('status', {})
            pod_name = pod_meta.get('name', '')

            # Status
            phase = pod_status.get('phase', 'Unknown')
            container_statuses = pod_status.get('containerStatuses', [])

            restart_count = 0
            is_ready = True
            actual_status = phase

            for cs in container_statuses:
                restart_count += cs.get('restartCount', 0)
                if not cs.get('ready', False):
                    is_ready = False
                # Check for CrashLoopBackOff
                waiting = cs.get('state', {}).get('waiting', {})
                if waiting.get('reason') in ('CrashLoopBackOff', 'Error', 'ImagePullBackOff'):
                    actual_status = waiting['reason']

            total_desired += 1
            if is_ready:
                total_ready += 1

            # Get recent events for this pod
            events = self._get_pod_events(pod_name, ns)

            # Get log tail
            log_tail = self._get_pod_log_tail(pod_name, ns)

            diag.pods.append(PodDiagnostics(
                name=pod_name,
                namespace=ns,
                status=actual_status,
                restart_count=restart_count,
                ready=is_ready,
                recent_events=events,
                log_tail=log_tail,
            ))

        diag.desired_replicas = total_desired
        diag.ready_replicas = total_ready

        if total_ready == total_desired and total_desired > 0:
            diag.deployment_status = 'Available'
        elif total_ready > 0:
            diag.deployment_status = 'Degraded'
        else:
            diag.deployment_status = 'Unavailable'

        return diag

    def diagnose_subsystem(self, subsystem: str) -> List[ComponentDiagnostics]:
        """Diagnose all components in a subsystem."""
        components = SUBSYSTEM_COMPONENTS.get(subsystem, [])
        if not components:
            self.logger.warning(f"Unknown subsystem: {subsystem}")
            return []

        results = []
        for component in components:
            diag = self.diagnose_component(component)
            results.append(diag)
        return results

    def get_resource_pressure(self) -> Dict[str, bool]:
        """Check CPU/memory/disk pressure on nodes."""
        pressure = {
            'cpu': False,
            'memory': False,
            'disk': False,
            'pid': False,
        }

        success, stdout, _ = self._run_command(
            ['get', 'nodes', '-o', 'json']
        )
        if not success or not stdout.strip():
            return pressure

        try:
            data = json.loads(stdout)
            for node in data.get('items', []):
                conditions = node.get('status', {}).get('conditions', [])
                for c in conditions:
                    ctype = c.get('type', '')
                    is_true = c.get('status') == 'True'
                    if ctype == 'MemoryPressure' and is_true:
                        pressure['memory'] = True
                    elif ctype == 'DiskPressure' and is_true:
                        pressure['disk'] = True
                    elif ctype == 'PIDPressure' and is_true:
                        pressure['pid'] = True
        except (json.JSONDecodeError, KeyError):
            pass

        # CPU pressure via adm top
        success, stdout, _ = self._run_command(
            ['adm', 'top', 'nodes', '--no-headers']
        )
        if success and stdout.strip():
            for line in stdout.strip().split('\n'):
                parts = line.split()
                # Format: NAME CPU(cores) CPU% MEMORY(bytes) MEMORY%
                if len(parts) >= 3:
                    cpu_pct = parts[2].rstrip('%')
                    try:
                        if int(cpu_pct) > 90:
                            pressure['cpu'] = True
                    except ValueError:
                        pass

        return pressure

    def _get_pod_events(
        self, pod_name: str, namespace: str, limit: int = 5
    ) -> List[str]:
        """Get recent events for a pod."""
        success, stdout, _ = self._run_command([
            'get', 'events', '-n', namespace,
            '--field-selector', f'involvedObject.name={pod_name}',
            '--sort-by=.lastTimestamp',
            '--no-headers',
        ])
        if not success or not stdout.strip():
            return []

        lines = stdout.strip().split('\n')
        return [line.strip() for line in lines[-limit:] if line.strip()]

    def _get_pod_log_tail(
        self, pod_name: str, namespace: str, lines: int = 50
    ) -> Optional[str]:
        """Get last N lines of pod logs."""
        success, stdout, _ = self._run_command([
            'logs', pod_name, '-n', namespace,
            f'--tail={lines}',
        ])
        if success and stdout.strip():
            return stdout.strip()
        return None

    def get_feature_area_health(
        self,
        feature_area: str,
        landscape: Optional[ClusterLandscape] = None,
    ) -> FeatureAreaHealth:
        """
        Calculate health score for a specific feature area based on its components.

        Uses the subsystem's components to determine health. Checks pod status,
        restart counts, and operator degradation.

        Args:
            feature_area: Feature area name (e.g., 'GRC', 'Search', 'CLC').
            landscape: Optional pre-fetched ClusterLandscape. Fetched if None.

        Returns:
            FeatureAreaHealth with score and component details.
        """
        subsystem = FEATURE_AREA_SUBSYSTEM_MAP.get(feature_area)
        components = SUBSYSTEM_COMPONENTS.get(subsystem, [])

        health = FeatureAreaHealth(
            feature_area=feature_area,
            total_components=len(components),
        )

        if not components:
            health.health_score = 1.0
            health.infrastructure_signal = 'none'
            return health

        # Check each component
        for component in components:
            diag = self.diagnose_component(component)

            if diag.deployment_status == 'Available':
                health.healthy_components += 1
            elif diag.deployment_status == 'Degraded':
                health.degraded_components.append(component)
            else:
                health.unhealthy_components.append(component)

            # Sum restart counts across all pods
            for pod in diag.pods:
                health.total_restart_count += pod.restart_count

        # Check if any operator matching this area is degraded
        if landscape:
            for op in landscape.degraded_operators:
                op_lower = op.lower()
                for comp in components:
                    if comp.lower() in op_lower or op_lower in comp.lower():
                        health.has_operator_degraded = True
                        break

        # Calculate health score
        if health.total_components == 0:
            health.health_score = 1.0
        else:
            # Base score from component availability
            base = health.healthy_components / health.total_components

            # Penalty for high restart counts (>10 restarts = significant instability)
            restart_penalty = min(0.2, health.total_restart_count * 0.02)

            # Penalty for degraded operator
            operator_penalty = 0.15 if health.has_operator_degraded else 0.0

            health.health_score = max(0.0, round(base - restart_penalty - operator_penalty, 2))

        # Determine infrastructure signal strength
        health.infrastructure_signal = self._score_to_signal(health.health_score)

        return health

    def get_all_feature_area_health(
        self,
        feature_areas: Optional[List[str]] = None,
    ) -> Dict[str, FeatureAreaHealth]:
        """
        Calculate health scores for multiple feature areas.

        Args:
            feature_areas: List of feature area names. If None, checks all known areas.

        Returns:
            Dict mapping feature_area -> FeatureAreaHealth.
        """
        if feature_areas is None:
            feature_areas = list(FEATURE_AREA_SUBSYSTEM_MAP.keys())

        # Fetch landscape once for all areas
        landscape = self.get_cluster_landscape()

        results = {}
        for area in feature_areas:
            results[area] = self.get_feature_area_health(area, landscape)

        return results

    @staticmethod
    def _score_to_signal(score: float) -> str:
        """
        Convert a health score to an infrastructure signal strength.

        Graduated bands replace the old binary threshold (uses THRESHOLDS config):
            < 0.3  -> definitive  (route to INFRASTRUCTURE at 0.90)
            0.3-0.5 -> strong     (route to INFRASTRUCTURE if timeout, 0.80)
            0.5-0.7 -> moderate   (flag as possible infra, investigate, 0.65)
            >= 0.7 -> none        (don't attribute to infra unless direct evidence)
        """
        if score < THRESHOLDS.INFRA_DEFINITIVE:
            return 'definitive'
        elif score < THRESHOLDS.INFRA_STRONG:
            return 'strong'
        elif score < THRESHOLDS.INFRA_MODERATE:
            return 'moderate'
        else:
            return 'none'

    def to_dict(self, obj) -> Dict[str, Any]:
        """Convert dataclass to dict for serialization."""
        return dataclass_to_dict(obj)
