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
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple


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


# Component-to-namespace mapping for targeted investigation
COMPONENT_NAMESPACE_MAP = {
    # Governance
    'grc-policy-propagator': ('open-cluster-management', 'deployment'),
    'config-policy-controller': ('open-cluster-management', 'deployment'),
    'governance-policy-framework': ('open-cluster-management', 'deployment'),
    'policy-propagator': ('open-cluster-management', 'deployment'),
    'iam-policy-controller': ('open-cluster-management', 'deployment'),
    'cert-policy-controller': ('open-cluster-management', 'deployment'),
    # Search
    'search-api': ('open-cluster-management', 'deployment'),
    'search-collector': ('open-cluster-management', 'deployment'),
    'search-indexer': ('open-cluster-management', 'deployment'),
    'search-aggregator': ('open-cluster-management', 'deployment'),
    'search-operator': ('open-cluster-management', 'deployment'),
    'search-redisgraph': ('open-cluster-management', 'statefulset'),
    # Cluster Management
    'cluster-curator': ('open-cluster-management', 'deployment'),
    'cluster-curator-controller': ('open-cluster-management', 'deployment'),
    'managedcluster-import-controller': ('open-cluster-management', 'deployment'),
    'cluster-manager': ('open-cluster-management', 'deployment'),
    'registration-controller': ('open-cluster-management-hub', 'deployment'),
    'registration-operator': ('open-cluster-management', 'deployment'),
    'placement-controller': ('open-cluster-management-hub', 'deployment'),
    'work-manager': ('open-cluster-management-hub', 'deployment'),
    # Provisioning
    'hive': ('hive', 'deployment'),
    'hive-operator': ('hive', 'deployment'),
    'hive-controllers': ('hive', 'deployment'),
    'hypershift-operator': ('hypershift', 'deployment'),
    'assisted-service': ('assisted-installer', 'deployment'),
    'infrastructure-operator': ('open-cluster-management', 'deployment'),
    # Observability
    'observability-operator': ('open-cluster-management', 'deployment'),
    'multicluster-observability-operator': ('open-cluster-management', 'deployment'),
    'thanos-query': ('open-cluster-management-observability', 'statefulset'),
    'thanos-receive': ('open-cluster-management-observability', 'statefulset'),
    'thanos-store': ('open-cluster-management-observability', 'statefulset'),
    'grafana': ('open-cluster-management-observability', 'deployment'),
    'alertmanager': ('open-cluster-management-observability', 'statefulset'),
    # Application
    'application-manager': ('open-cluster-management', 'deployment'),
    'subscription-controller': ('open-cluster-management', 'deployment'),
    'multicluster-operators-subscription': ('open-cluster-management', 'deployment'),
    'channel-controller': ('open-cluster-management', 'deployment'),
    # Console
    'console-api': ('open-cluster-management', 'deployment'),
    'acm-console': ('open-cluster-management', 'deployment'),
    'mce-console': ('multicluster-engine', 'deployment'),
    # Virtualization
    'kubevirt-operator': ('openshift-cnv', 'deployment'),
    'virt-api': ('openshift-cnv', 'deployment'),
    'virt-controller': ('openshift-cnv', 'deployment'),
    'virt-handler': ('openshift-cnv', 'daemonset'),
    'hyperconverged-cluster-operator': ('openshift-cnv', 'deployment'),
    'cdi-operator': ('openshift-cnv', 'deployment'),
    'cdi-apiserver': ('openshift-cnv', 'deployment'),
    # Cross-Cluster Migration (MTV + Submariner)
    'forklift-controller': ('openshift-mtv', 'deployment'),
    'submariner-gateway': ('submariner-operator', 'daemonset'),
    # Infrastructure
    'klusterlet': ('open-cluster-management-agent', 'deployment'),
    'klusterlet-agent': ('open-cluster-management-agent', 'deployment'),
    'multicluster-engine': ('multicluster-engine', 'deployment'),
    'multicluster-hub': ('open-cluster-management', 'deployment'),
    'foundation-controller': ('open-cluster-management', 'deployment'),
    'addon-manager': ('open-cluster-management', 'deployment'),
}

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
    'Infrastructure': [
        'klusterlet', 'multicluster-engine',
        'foundation-controller', 'addon-manager',
    ],
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

    def _build_command(self, args: List[str]) -> List[str]:
        cmd = [self.cli]
        if self.kubeconfig:
            cmd.extend(['--kubeconfig', self.kubeconfig])
        cmd.extend(args)
        return cmd

    def _validate_readonly(self, args: List[str]) -> bool:
        if not args:
            return False
        primary = args[0]
        if primary not in self.ALLOWED_COMMANDS:
            self.logger.warning(
                f"READ-ONLY VIOLATION: '{primary}' not in allowed commands"
            )
            return False
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
            except (json.JSONDecodeError, KeyError):
                pass

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
            except (json.JSONDecodeError, KeyError):
                pass

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
            except (json.JSONDecodeError, KeyError):
                pass

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

        if component_lower in COMPONENT_NAMESPACE_MAP:
            mapped_ns, mapped_kind = COMPONENT_NAMESPACE_MAP[component_lower]
            if not ns:
                ns = mapped_ns
            kind = mapped_kind
        elif not ns:
            ns = 'open-cluster-management'

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

    def to_dict(self, obj) -> Dict[str, Any]:
        """Convert dataclass to dict for serialization."""
        return asdict(obj)
