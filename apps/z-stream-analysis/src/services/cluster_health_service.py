#!/usr/bin/env python3
"""
Cluster Health Service (v3.7)

Comprehensive ACM cluster health audit modeled on the acm-hub-health
diagnostic pipeline. Replaces EnvironmentValidationService for Step 4
of gather.py.

Six-phase pipeline:
  Phase 1: DISCOVER — inventory what's deployed (MCH, MCE, operators, nodes, clusters)
  Phase 2: LEARN    — load knowledge baselines from knowledge/ YAML files
  Phase 3: CHECK    — systematic health verification (pods, infra guards, image integrity)
  Phase 4: COMPARE  — baseline deviation detection
  Phase 5: CORRELATE — map findings to feature areas
  Phase 6: SCORE    — compute health scores, produce cluster-health.json

All cluster operations are strictly read-only.
Output: ClusterHealthReport dataclass + cluster-health.json file.
"""

import json
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

from .shared_utils import TIMEOUTS, validate_command_readonly

try:
    import yaml
except ImportError:
    yaml = None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class HealthFinding:
    """A single health finding (deviation from expected state)."""
    id: str
    severity: str  # CRITICAL, WARNING, INFO
    category: str  # operator_health, pod_health, network_policy, resource_quota,
                   # image_integrity, subsystem_health, managed_cluster, node_health
    component: str
    namespace: str = ''
    finding: str = ''
    impact: str = ''
    diagnostic_trap: str = ''
    remediation: str = ''


@dataclass
class SubsystemHealth:
    """Health status for a single subsystem."""
    name: str
    status: str  # OK, DEGRADED, CRITICAL
    components_checked: int = 0
    components_healthy: int = 0
    root_issue: str = ''
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ManagedClusterHealth:
    """Health status for a single managed cluster."""
    name: str
    available: bool = False
    joined: bool = False
    hub_accepted: bool = False
    addon_count: int = 0
    addons_healthy: int = 0
    conditions: Dict[str, str] = field(default_factory=dict)


@dataclass
class ClusterIdentity:
    """Cluster identity information."""
    api_url: str = ''
    ocp_version: str = ''
    acm_version: str = ''
    mce_version: str = ''
    mch_namespace: str = ''
    mch_phase: str = ''
    node_count: int = 0
    node_ready_count: int = 0
    managed_cluster_count: int = 0
    managed_cluster_ready_count: int = 0


@dataclass
class ClusterHealthReport:
    """Complete cluster health audit report."""
    version: str = '1.0.0'
    timestamp: str = ''
    audit_duration_seconds: float = 0.0
    overall_verdict: str = 'UNKNOWN'  # HEALTHY, DEGRADED, CRITICAL, UNKNOWN
    environment_health_score: float = 1.0
    critical_issue_count: int = 0
    warning_issue_count: int = 0
    cluster_identity: ClusterIdentity = field(default_factory=ClusterIdentity)
    operator_health: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    subsystem_health: Dict[str, SubsystemHealth] = field(default_factory=dict)
    infrastructure_issues: List[HealthFinding] = field(default_factory=list)
    managed_cluster_health: Dict[str, ManagedClusterHealth] = field(default_factory=dict)
    baseline_comparison: Dict[str, Any] = field(default_factory=dict)
    console_plugins: List[Dict[str, str]] = field(default_factory=list)
    classification_guidance: Dict[str, Any] = field(default_factory=dict)
    backend_probes: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    phases_completed: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ClusterHealthService:
    """
    Comprehensive ACM cluster health audit.

    Reads knowledge/ YAML files for baselines, runs read-only oc commands
    to discover cluster state, compares against baselines, and produces
    a structured ClusterHealthReport.

    All cluster operations are strictly read-only.
    """

    ALLOWED_COMMANDS = {
        'get', 'describe', 'api-resources', 'whoami', 'version',
        'auth', 'exec', 'adm',
    }

    def __init__(
        self,
        kubeconfig_path: Optional[str] = None,
        knowledge_dir: Optional[Path] = None,
        cli: str = 'oc',
    ):
        self.logger = logging.getLogger(__name__)
        self.kubeconfig = kubeconfig_path
        self.knowledge_dir = knowledge_dir or Path(__file__).parent.parent.parent / 'knowledge'
        self.cli = cli

        # Knowledge data (loaded in Phase 2)
        self._components: Dict[str, Any] = {}
        self._baseline: Dict[str, Any] = {}
        self._addons: List[Dict[str, Any]] = []
        self._dependencies: Dict[str, Any] = {}
        self._feature_areas: Dict[str, Any] = {}

        # Discovery data (populated in Phase 1)
        self._mch_namespace: str = ''
        self._discovered_deployments: Dict[str, Dict[str, Any]] = {}
        self._discovered_nodes: List[Dict[str, str]] = []
        self._discovered_clusters: List[Dict[str, Any]] = []
        self._discovered_addons: List[Dict[str, Any]] = []

    # ===================================================================
    # PUBLIC API
    # ===================================================================

    def run_health_audit(self) -> ClusterHealthReport:
        """
        Run the complete 6-phase cluster health audit.

        Returns:
            ClusterHealthReport with complete health assessment.
        """
        start_time = time.time()
        report = ClusterHealthReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        try:
            # Phase 1: DISCOVER
            self._phase1_discover(report)

            # Phase 2: LEARN
            self._phase2_learn(report)

            # Phase 3: CHECK
            self._phase3_check(report)

            # Phase 4: COMPARE
            self._phase4_compare(report)

            # Phase 5: CORRELATE
            self._phase5_correlate(report)

            # Phase 6: SCORE
            self._phase6_score(report)

        except Exception as e:
            self.logger.error(f"Health audit failed: {e}")
            report.errors.append(f"Audit failed: {e}")
            if report.overall_verdict == 'UNKNOWN':
                report.overall_verdict = 'ERROR'

        report.audit_duration_seconds = round(time.time() - start_time, 2)
        return report

    def save_report(self, report: ClusterHealthReport, run_dir: Path) -> Path:
        """Save the health report to cluster-health.json."""
        output_path = run_dir / 'cluster-health.json'
        data = self._report_to_dict(report)
        output_path.write_text(json.dumps(data, indent=2, default=str))
        self.logger.info(f"Cluster health report saved to {output_path}")
        return output_path

    def get_core_data_summary(self, report: ClusterHealthReport) -> Dict[str, Any]:
        """
        Get a summary suitable for inclusion in core-data.json.

        Returns a compact dict (not the full report) for the cluster_health
        key in core-data.json. The full report is in cluster-health.json.
        """
        return {
            'environment_health_score': report.environment_health_score,
            'overall_verdict': report.overall_verdict,
            'critical_issue_count': report.critical_issue_count,
            'warning_issue_count': report.warning_issue_count,
            'affected_feature_areas': report.classification_guidance.get(
                'affected_feature_areas', []
            ),
            'mch_namespace': report.cluster_identity.mch_namespace,
            'acm_version': report.cluster_identity.acm_version,
            'ocp_version': report.cluster_identity.ocp_version,
            'managed_cluster_count': report.cluster_identity.managed_cluster_count,
            'managed_cluster_ready_count': report.cluster_identity.managed_cluster_ready_count,
            'node_count': report.cluster_identity.node_count,
            'phases_completed': report.phases_completed,
            'audit_duration_seconds': report.audit_duration_seconds,
        }

    # ===================================================================
    # PHASE 1: DISCOVER (what's deployed)
    # ===================================================================

    def _phase1_discover(self, report: ClusterHealthReport):
        """Inventory what's deployed on the cluster."""
        self.logger.info("Phase 1: DISCOVER — inventorying cluster state")

        # Cluster identity
        identity = report.cluster_identity
        identity.api_url = self._run_oc(['whoami', '--show-server']) or ''

        # OCP version
        cv_json = self._run_oc_json(['get', 'clusterversion', '-o', 'json'])
        if cv_json and 'items' in cv_json:
            for item in cv_json['items']:
                identity.ocp_version = (
                    item.get('status', {}).get('desired', {}).get('version', '')
                )

        # MCH — discover namespace
        mch_json = self._run_oc_json(['get', 'mch', '-A', '-o', 'json'])
        if mch_json and mch_json.get('items'):
            mch = mch_json['items'][0]
            self._mch_namespace = mch.get('metadata', {}).get('namespace', '')
            identity.mch_namespace = self._mch_namespace
            identity.acm_version = mch.get('status', {}).get('currentVersion', '')
            identity.mch_phase = mch.get('status', {}).get('phase', '')

        # MCE
        mce_json = self._run_oc_json(
            ['get', 'multiclusterengines', '-A', '-o', 'json']
        )
        if mce_json and mce_json.get('items'):
            mce = mce_json['items'][0]
            identity.mce_version = mce.get('status', {}).get('currentVersion', '')

        # Nodes
        nodes_json = self._run_oc_json(['get', 'nodes', '-o', 'json'])
        if nodes_json and nodes_json.get('items'):
            self._discovered_nodes = []
            for node in nodes_json['items']:
                ready = 'False'
                for cond in node.get('status', {}).get('conditions', []):
                    if cond.get('type') == 'Ready':
                        ready = cond.get('status', 'False')
                self._discovered_nodes.append({
                    'name': node.get('metadata', {}).get('name', ''),
                    'ready': ready,
                    'roles': ','.join(
                        k.replace('node-role.kubernetes.io/', '')
                        for k in node.get('metadata', {}).get('labels', {})
                        if k.startswith('node-role.kubernetes.io/')
                    ),
                })
            identity.node_count = len(self._discovered_nodes)
            identity.node_ready_count = sum(
                1 for n in self._discovered_nodes if n['ready'] == 'True'
            )

        # Deployments in key namespaces
        namespaces_to_scan = [
            self._mch_namespace,
            'multicluster-engine',
            'open-cluster-management-hub',
            'hive',
            'open-cluster-management-observability',
        ]
        for ns in namespaces_to_scan:
            if not ns:
                continue
            deploy_json = self._run_oc_json(
                ['get', 'deployments', '-n', ns, '-o', 'json']
            )
            if deploy_json and deploy_json.get('items'):
                for d in deploy_json['items']:
                    name = d.get('metadata', {}).get('name', '')
                    self._discovered_deployments[f"{ns}/{name}"] = {
                        'name': name,
                        'namespace': ns,
                        'desired': d.get('spec', {}).get('replicas', 1),
                        'ready': d.get('status', {}).get('readyReplicas', 0) or 0,
                        'available': d.get('status', {}).get('availableReplicas', 0) or 0,
                        'labels': d.get('spec', {}).get(
                            'selector', {}
                        ).get('matchLabels', {}),
                    }

        # Managed clusters
        mc_json = self._run_oc_json(['get', 'managedclusters', '-o', 'json'])
        if mc_json and mc_json.get('items'):
            for mc in mc_json['items']:
                name = mc.get('metadata', {}).get('name', '')
                conditions = {}
                for cond in mc.get('status', {}).get('conditions', []):
                    conditions[cond.get('type', '')] = cond.get('status', '')
                self._discovered_clusters.append({
                    'name': name,
                    'conditions': conditions,
                })
            identity.managed_cluster_count = len(self._discovered_clusters)
            identity.managed_cluster_ready_count = sum(
                1 for c in self._discovered_clusters
                if c['conditions'].get('ManagedClusterConditionAvailable') == 'True'
            )

        # Managed cluster addons
        addon_json = self._run_oc_json(
            ['get', 'managedclusteraddons', '-A', '-o', 'json']
        )
        if addon_json and addon_json.get('items'):
            for addon in addon_json['items']:
                available = 'Unknown'
                for cond in addon.get('status', {}).get('conditions', []):
                    if cond.get('type') == 'Available':
                        available = cond.get('status', 'Unknown')
                self._discovered_addons.append({
                    'cluster': addon.get('metadata', {}).get('namespace', ''),
                    'name': addon.get('metadata', {}).get('name', ''),
                    'available': available,
                })

        # Console plugins
        plugins_json = self._run_oc_json(['get', 'consoleplugins', '-o', 'json'])
        if plugins_json and plugins_json.get('items'):
            for plugin in plugins_json['items']:
                svc = plugin.get('spec', {}).get('backend', {}).get('service', {})
                report.console_plugins.append({
                    'name': plugin.get('metadata', {}).get('name', ''),
                    'service': svc.get('name', ''),
                    'namespace': svc.get('namespace', ''),
                })

        report.phases_completed.append('DISCOVER')
        self.logger.info(
            f"Phase 1 complete: {len(self._discovered_deployments)} deployments, "
            f"{identity.node_count} nodes, "
            f"{identity.managed_cluster_count} managed clusters"
        )

    # ===================================================================
    # PHASE 2: LEARN (load knowledge baselines)
    # ===================================================================

    def _phase2_learn(self, report: ClusterHealthReport):
        """Load knowledge baselines from YAML files."""
        self.logger.info("Phase 2: LEARN — loading knowledge baselines")

        if yaml is None:
            report.errors.append("PyYAML not installed — cannot load knowledge baselines")
            report.phases_completed.append('LEARN (partial)')
            return

        self._components = self._load_yaml('components.yaml').get('components', {})
        self._baseline = self._load_yaml('healthy-baseline.yaml').get('baseline', {})
        self._addons = self._load_yaml('addon-catalog.yaml').get('addons', [])
        self._dependencies = self._load_yaml('dependencies.yaml')
        self._feature_areas = self._load_yaml('feature-areas.yaml').get(
            'feature_areas', {}
        )

        self.logger.info(
            f"Phase 2 complete: {len(self._components)} components, "
            f"{len(self._addons)} addons, "
            f"{len(self._feature_areas)} feature areas loaded"
        )
        report.phases_completed.append('LEARN')

    # ===================================================================
    # PHASE 3: CHECK (systematic health verification)
    # ===================================================================

    def _phase3_check(self, report: ClusterHealthReport):
        """Systematic health verification against known components."""
        self.logger.info("Phase 3: CHECK — verifying component health")

        # 3a: Operator health (Tier 0)
        self._check_operators(report)

        # 3b: Pod health per namespace
        self._check_pod_health(report)

        # 3c: Infrastructure guards
        self._check_infra_guards(report)

        # 3d: Console image integrity
        self._check_console_image(report)

        # 3e: Managed cluster health
        self._check_managed_clusters(report)

        # 3f: Node health
        self._check_nodes(report)

        report.phases_completed.append('CHECK')

    def _check_operators(self, report: ClusterHealthReport):
        """Check critical operator deployment health."""
        operators_baseline = self._baseline.get('operators', {})
        for op_name, op_spec in operators_baseline.items():
            ns = op_spec.get('namespace', '').replace('{mch_ns}', self._mch_namespace).replace('{mch-ns}', self._mch_namespace)
            key = f"{ns}/{op_name}"
            deploy = self._discovered_deployments.get(key, {})

            desired = op_spec.get('expected_replicas', 1)
            ready = deploy.get('ready', 0)
            status = 'OK'
            detail = ''

            if not deploy:
                status = 'CRITICAL'
                detail = f"Deployment not found in {ns}"
            elif ready == 0:
                status = 'CRITICAL'
                detail = f"Scaled to 0 replicas. MCH CR status is STALE."
            elif ready < desired:
                status = 'DEGRADED'
                detail = f"{ready}/{desired} replicas ready"

            report.operator_health[op_name] = {
                'namespace': ns,
                'desired_replicas': desired,
                'available_replicas': ready,
                'status': status,
                'detail': detail,
                'critical': op_spec.get('critical', False),
            }

            if status == 'CRITICAL':
                impact = op_spec.get('note', f'{op_name} is down')
                report.infrastructure_issues.append(HealthFinding(
                    id=f'{op_name}-critical',
                    severity='CRITICAL',
                    category='operator_health',
                    component=op_name,
                    namespace=ns,
                    finding=detail or f'{op_name} not available',
                    impact=impact,
                    diagnostic_trap='Trap 1: Stale MCH/MCE CR Status' if 'MCH' in impact or 'stale' in detail.lower() else '',
                ))

    def _check_pod_health(self, report: ClusterHealthReport):
        """Check for non-running pods and high restart counts in ACM namespaces."""
        namespaces = [
            self._mch_namespace,
            'multicluster-engine',
            'open-cluster-management-hub',
            'hive',
        ]
        restart_threshold = self._baseline.get(
            'restart_thresholds', {}
        ).get('max_acceptable_restarts', 5)

        for ns in namespaces:
            if not ns:
                continue
            pods_json = self._run_oc_json(['get', 'pods', '-n', ns, '-o', 'json'])
            if not pods_json or not pods_json.get('items'):
                continue
            for pod in pods_json['items']:
                pod_name = pod.get('metadata', {}).get('name', '')
                phase = pod.get('status', {}).get('phase', '')
                if phase in ('Running', 'Succeeded'):
                    # Check restart counts
                    for cs in pod.get('status', {}).get('containerStatuses', []):
                        restarts = cs.get('restartCount', 0)
                        if restarts > restart_threshold:
                            report.infrastructure_issues.append(HealthFinding(
                                id=f'high-restarts-{pod_name}',
                                severity='WARNING',
                                category='pod_health',
                                component=pod_name,
                                namespace=ns,
                                finding=f"Pod has {restarts} restarts (threshold: {restart_threshold})",
                                impact='Component may be unstable despite currently Running',
                            ))
                elif phase != 'Succeeded':
                    report.infrastructure_issues.append(HealthFinding(
                        id=f'non-running-{pod_name}',
                        severity='CRITICAL' if phase in ('CrashLoopBackOff', 'Error', 'Failed') else 'WARNING',
                        category='pod_health',
                        component=pod_name,
                        namespace=ns,
                        finding=f"Pod in {phase} state",
                        impact=f"Component {pod_name} is not operational",
                    ))

    def _check_infra_guards(self, report: ClusterHealthReport):
        """Check for NetworkPolicies and ResourceQuotas in ACM namespaces."""
        namespaces = [self._mch_namespace, 'multicluster-engine']
        for ns in namespaces:
            if not ns:
                continue
            # NetworkPolicies
            np_output = self._run_oc(
                ['get', 'networkpolicy', '-n', ns, '--no-headers']
            )
            if np_output and np_output.strip():
                for line in np_output.strip().split('\n'):
                    np_name = line.split()[0] if line.split() else 'unknown'
                    report.infrastructure_issues.append(HealthFinding(
                        id=f'networkpolicy-{ns}-{np_name}',
                        severity='CRITICAL',
                        category='network_policy',
                        component=np_name,
                        namespace=ns,
                        finding=f"NetworkPolicy '{np_name}' in ACM namespace {ns}",
                        impact='Can silently block pod-to-pod communication',
                        diagnostic_trap='Trap 3: Search empty but pods green',
                        remediation=f'oc delete networkpolicy {np_name} -n {ns}',
                    ))

            # ResourceQuotas
            rq_output = self._run_oc(
                ['get', 'resourcequota', '-n', ns, '--no-headers']
            )
            if rq_output and rq_output.strip():
                for line in rq_output.strip().split('\n'):
                    rq_name = line.split()[0] if line.split() else 'unknown'
                    report.infrastructure_issues.append(HealthFinding(
                        id=f'resourcequota-{ns}-{rq_name}',
                        severity='CRITICAL',
                        category='resource_quota',
                        component=rq_name,
                        namespace=ns,
                        finding=f"ResourceQuota '{rq_name}' in ACM namespace {ns}",
                        impact='Can block pod scheduling if limits exceeded',
                        remediation=f'oc delete resourcequota {rq_name} -n {ns}',
                    ))

    def _check_console_image(self, report: ClusterHealthReport):
        """Check console image integrity."""
        image_patterns = self._baseline.get('image_patterns', {})
        console_spec = image_patterns.get('console-chart-console-v2', {})
        expected_prefixes = console_spec.get('expected_prefix', [])

        if not expected_prefixes or not self._mch_namespace:
            return

        image = self._run_oc([
            'get', 'deploy', 'console-chart-console-v2',
            '-n', self._mch_namespace,
            '-o', "jsonpath={.spec.template.spec.containers[0].image}",
        ])
        if image:
            match = any(image.startswith(prefix) for prefix in expected_prefixes)
            if not match:
                report.infrastructure_issues.append(HealthFinding(
                    id='console-image-mismatch',
                    severity='CRITICAL',
                    category='image_integrity',
                    component='console-chart-console-v2',
                    namespace=self._mch_namespace,
                    finding=f"Console image from unexpected source: {image}",
                    impact='Console may be running tampered or debug image',
                ))

    def _check_managed_clusters(self, report: ClusterHealthReport):
        """Check managed cluster health."""
        for cluster_data in self._discovered_clusters:
            name = cluster_data['name']
            conditions = cluster_data['conditions']
            available = conditions.get('ManagedClusterConditionAvailable') == 'True'
            joined = conditions.get('ManagedClusterJoined') == 'True'
            hub_accepted = conditions.get('HubAcceptedManagedCluster') == 'True'

            # Count addons for this cluster
            cluster_addons = [
                a for a in self._discovered_addons if a['cluster'] == name
            ]
            addons_healthy = sum(
                1 for a in cluster_addons if a['available'] == 'True'
            )

            report.managed_cluster_health[name] = ManagedClusterHealth(
                name=name,
                available=available,
                joined=joined,
                hub_accepted=hub_accepted,
                addon_count=len(cluster_addons),
                addons_healthy=addons_healthy,
                conditions=conditions,
            )

            if not available and name != 'local-cluster':
                report.infrastructure_issues.append(HealthFinding(
                    id=f'cluster-not-available-{name}',
                    severity='WARNING',
                    category='managed_cluster',
                    component=name,
                    finding=f"Managed cluster '{name}' is not available",
                    impact='Tests depending on this cluster will fail',
                ))

    def _check_nodes(self, report: ClusterHealthReport):
        """Check node health."""
        min_ready = self._baseline.get('nodes', {}).get('minimum_ready', 3)
        not_ready = [n for n in self._discovered_nodes if n['ready'] != 'True']

        if not_ready:
            for node in not_ready:
                report.infrastructure_issues.append(HealthFinding(
                    id=f'node-not-ready-{node["name"]}',
                    severity='WARNING',
                    category='node_health',
                    component=node['name'],
                    finding=f"Node {node['name']} is NotReady",
                    impact='Pod scheduling may be affected',
                ))

        ready_count = report.cluster_identity.node_ready_count
        if ready_count < min_ready:
            report.infrastructure_issues.append(HealthFinding(
                id='insufficient-ready-nodes',
                severity='CRITICAL',
                category='node_health',
                component='cluster',
                finding=f"Only {ready_count} ready nodes (minimum: {min_ready})",
                impact='Pod scheduling constrained',
            ))

    # ===================================================================
    # PHASE 4: COMPARE (baseline deviation detection)
    # ===================================================================

    def _phase4_compare(self, report: ClusterHealthReport):
        """Compare discovered state against knowledge baselines."""
        self.logger.info("Phase 4: COMPARE — detecting baseline deviations")

        comparison = {
            'under_replicated_deployments': [],
            'unexpected_resources': [],
            'namespace_pod_counts': {},
        }

        # Compare deployment replicas against baseline
        ns_baselines = self._baseline.get('namespaces', {})
        for ns_key, ns_spec in ns_baselines.items():
            # Resolve namespace name
            if ns_key == 'mch_namespace':
                ns_name = self._mch_namespace
            else:
                ns_name = ns_key

            if not ns_name:
                continue

            # Pod count comparison
            expected_range = ns_spec.get('expected_pod_count_range', '')
            actual_pods = sum(
                1 for key in self._discovered_deployments
                if key.startswith(f"{ns_name}/")
            )
            comparison['namespace_pod_counts'][ns_name] = {
                'expected_range': expected_range,
                'deployment_count': actual_pods,
            }

            # Per-deployment replica check
            for deploy_spec in ns_spec.get('critical_deployments', []):
                deploy_name = deploy_spec.get('name', '')
                min_replicas = deploy_spec.get('min_replicas', 1)
                key = f"{ns_name}/{deploy_name}"
                deploy = self._discovered_deployments.get(key, {})

                if not deploy:
                    comparison['under_replicated_deployments'].append({
                        'name': deploy_name,
                        'namespace': ns_name,
                        'expected': min_replicas,
                        'actual': 0,
                        'status': 'MISSING',
                    })
                elif deploy.get('ready', 0) < min_replicas:
                    comparison['under_replicated_deployments'].append({
                        'name': deploy_name,
                        'namespace': ns_name,
                        'expected': min_replicas,
                        'actual': deploy.get('ready', 0),
                        'status': 'UNDER_REPLICATED',
                    })

        # Collect unexpected resources from infrastructure findings
        for finding in report.infrastructure_issues:
            if finding.category in ('network_policy', 'resource_quota'):
                comparison['unexpected_resources'].append({
                    'type': finding.category.replace('_', ' ').title(),
                    'name': finding.component,
                    'namespace': finding.namespace,
                })

        report.baseline_comparison = comparison
        report.phases_completed.append('COMPARE')

    # ===================================================================
    # PHASE 5: CORRELATE (map findings to feature areas)
    # ===================================================================

    def _phase5_correlate(self, report: ClusterHealthReport):
        """Map infrastructure findings to affected feature areas."""
        self.logger.info("Phase 5: CORRELATE — mapping findings to feature areas")

        # Build subsystem health from discovered deployments + components knowledge
        subsystem_components: Dict[str, List[str]] = {}
        for comp_name, comp_spec in self._components.items():
            subsystem = comp_spec.get('subsystem', 'Unknown')
            if subsystem not in subsystem_components:
                subsystem_components[subsystem] = []
            subsystem_components[subsystem].append(comp_name)

        # Check each subsystem's components against discovered state
        for subsystem, components in subsystem_components.items():
            checked = 0
            healthy = 0
            root_issue = ''
            details = {}

            for comp_name in components:
                comp_spec = self._components.get(comp_name, {})
                ns = comp_spec.get('namespace', '').replace(
                    '{mch_ns}', self._mch_namespace
                ).replace('{mch-ns}', self._mch_namespace)
                comp_type = comp_spec.get('type', '')

                # Skip addon and spoke types — checked via addon health
                if comp_type in ('addon', 'spoke-agent'):
                    continue

                key = f"{ns}/{comp_name}"
                deploy = self._discovered_deployments.get(key)
                if deploy is None:
                    # Not found — may not be deployed (optional component)
                    continue

                checked += 1
                ready = deploy.get('ready', 0)
                desired = deploy.get('desired', 1)

                if ready >= desired and desired > 0:
                    healthy += 1
                    details[comp_name] = {'status': 'Running', 'replicas': f"{ready}/{desired}"}
                elif ready == 0 and desired > 0:
                    details[comp_name] = {'status': 'DOWN', 'replicas': f"0/{desired}"}
                    if not root_issue:
                        root_issue = f"{comp_name} has 0/{desired} replicas"
                else:
                    details[comp_name] = {'status': 'DEGRADED', 'replicas': f"{ready}/{desired}"}
                    if not root_issue:
                        root_issue = f"{comp_name} under-replicated ({ready}/{desired})"

            if checked == 0:
                continue

            status = 'OK'
            if healthy < checked:
                status = 'DEGRADED'
            if checked > 0 and healthy < checked * 0.5:
                status = 'CRITICAL'

            report.subsystem_health[subsystem] = SubsystemHealth(
                name=subsystem,
                status=status,
                components_checked=checked,
                components_healthy=healthy,
                root_issue=root_issue,
                details=details,
            )

        # Build classification guidance
        affected_areas = set()
        infra_signals = []

        for finding in report.infrastructure_issues:
            infra_signals.append(finding.finding)

        # Map subsystem health to feature areas
        for area_name, area_spec in self._feature_areas.items():
            subsystems = area_spec.get('subsystems', [])
            for sub in subsystems:
                # Capitalize to match subsystem_health keys
                sub_title = sub.replace('-', ' ').title().replace(' ', '-')
                sub_health = report.subsystem_health.get(sub_title) or report.subsystem_health.get(sub.title()) or report.subsystem_health.get(sub)
                if sub_health and sub_health.status in ('CRITICAL', 'DEGRADED'):
                    affected_areas.add(area_name)

        # Also check if operator issues affect areas
        for op_name, op_data in report.operator_health.items():
            if op_data.get('status') == 'CRITICAL':
                affected_areas = set(self._feature_areas.keys())
                break

        report.classification_guidance = {
            'infrastructure_signals': infra_signals[:20],
            'affected_feature_areas': sorted(affected_areas),
            'confirmed_healthy': sorted(
                sub for sub, health in report.subsystem_health.items()
                if health.status == 'OK'
            ),
        }

        report.phases_completed.append('CORRELATE')

    # ===================================================================
    # PHASE 6: SCORE (compute health scores)
    # ===================================================================

    def _phase6_score(self, report: ClusterHealthReport):
        """Compute environment_health_score and overall_verdict."""
        self.logger.info("Phase 6: SCORE — computing health scores")

        score = 1.0

        # Operator health (30% weight)
        for op_name, op_data in report.operator_health.items():
            if op_data.get('status') == 'CRITICAL':
                score -= 0.30
                break
            elif op_data.get('status') == 'DEGRADED':
                score -= 0.15
                break

        # Infrastructure guards (20% weight, 0.10 per issue)
        guard_penalty = 0
        for finding in report.infrastructure_issues:
            if finding.category in ('network_policy', 'resource_quota'):
                guard_penalty += 0.10
        score -= min(guard_penalty, 0.20)

        # Subsystem health (30% weight)
        critical_subs = sum(
            1 for s in report.subsystem_health.values() if s.status == 'CRITICAL'
        )
        degraded_subs = sum(
            1 for s in report.subsystem_health.values() if s.status == 'DEGRADED'
        )
        score -= critical_subs * 0.06
        score -= degraded_subs * 0.03

        # Managed cluster health (10% weight)
        total_clusters = report.cluster_identity.managed_cluster_count
        ready_clusters = report.cluster_identity.managed_cluster_ready_count
        if total_clusters > 0:
            ratio = ready_clusters / total_clusters
            if ratio < 0.5:
                score -= 0.10
            elif ratio < 1.0:
                score -= 0.05

        # Image integrity (10% weight)
        image_issues = any(
            f.category == 'image_integrity' for f in report.infrastructure_issues
        )
        if image_issues:
            score -= 0.10

        score = max(0.0, round(score, 2))
        report.environment_health_score = score

        # Count issues
        report.critical_issue_count = sum(
            1 for f in report.infrastructure_issues if f.severity == 'CRITICAL'
        )
        report.warning_issue_count = sum(
            1 for f in report.infrastructure_issues if f.severity == 'WARNING'
        )

        # Overall verdict
        if score >= 0.8 and report.critical_issue_count == 0:
            report.overall_verdict = 'HEALTHY'
        elif score >= 0.5 or report.critical_issue_count <= 1:
            report.overall_verdict = 'DEGRADED'
        else:
            report.overall_verdict = 'CRITICAL'

        report.phases_completed.append('SCORE')
        self.logger.info(
            f"Phase 6 complete: score={score}, verdict={report.overall_verdict}, "
            f"critical={report.critical_issue_count}, warnings={report.warning_issue_count}"
        )

    # ===================================================================
    # HELPERS
    # ===================================================================

    def _run_oc(self, args: List[str], timeout: int = TIMEOUTS.CLUSTER_COMMAND) -> str:
        """Run an oc command and return stdout. Returns empty string on failure."""
        if not self._validate_readonly(args):
            return ''
        cmd = [self.cli]
        if self.kubeconfig:
            cmd.extend(['--kubeconfig', self.kubeconfig])
        cmd.extend(args)

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode != 0:
                self.logger.debug(
                    f"oc {' '.join(args[:3])}... returned {result.returncode}"
                )
                return ''
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            self.logger.warning(f"oc {' '.join(args[:3])}... timed out")
            return ''
        except FileNotFoundError:
            self.logger.error(f"CLI not found: {self.cli}")
            return ''
        except Exception as e:
            self.logger.debug(f"oc error: {e}")
            return ''

    def _run_oc_json(self, args: List[str]) -> Optional[Dict[str, Any]]:
        """Run an oc command and parse JSON output."""
        output = self._run_oc(args)
        if not output:
            return None
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return None

    def _validate_readonly(self, args: List[str]) -> bool:
        """Validate command is read-only."""
        return validate_command_readonly(
            args, self.ALLOWED_COMMANDS, 'ClusterHealthService'
        )

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load a YAML file from the knowledge directory."""
        filepath = self.knowledge_dir / filename
        if not filepath.exists():
            self.logger.warning(f"Knowledge file not found: {filepath}")
            return {}
        try:
            with open(filepath) as f:
                data = yaml.safe_load(f) or {}
            return data
        except Exception as e:
            self.logger.warning(f"Failed to load {filepath}: {e}")
            return {}

    def _report_to_dict(self, report: ClusterHealthReport) -> Dict[str, Any]:
        """Convert ClusterHealthReport to a JSON-serializable dict."""
        data = {
            'cluster_health': {
                'version': report.version,
                'timestamp': report.timestamp,
                'audit_duration_seconds': report.audit_duration_seconds,
                'overall_verdict': report.overall_verdict,
                'environment_health_score': report.environment_health_score,
                'critical_issue_count': report.critical_issue_count,
                'warning_issue_count': report.warning_issue_count,
                'cluster_identity': asdict(report.cluster_identity),
                'operator_health': report.operator_health,
                'subsystem_health': {
                    name: asdict(health)
                    for name, health in report.subsystem_health.items()
                },
                'infrastructure_issues': [
                    asdict(f) for f in report.infrastructure_issues
                ],
                'managed_cluster_health': {
                    name: asdict(health)
                    for name, health in report.managed_cluster_health.items()
                },
                'baseline_comparison': report.baseline_comparison,
                'console_plugins': report.console_plugins,
                'classification_guidance': report.classification_guidance,
                'phases_completed': report.phases_completed,
                'errors': report.errors,
            }
        }
        return data
