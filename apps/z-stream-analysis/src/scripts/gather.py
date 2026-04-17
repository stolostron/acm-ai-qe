#!/usr/bin/env python3
"""
Data Gathering Script (v4.0)

Collects FACTUAL DATA from Jenkins, environment, and repository.
Clones repositories to persistent location for AI to access during analysis.
Pre-computes evidence to accelerate Stage 2 AI analysis.
Extracts complete test context upfront for systematic AI analysis.

9-step pipeline:
    Step 1:  Jenkins build info
    Step 2:  Console log
    Step 3:  Test report
    Step 4:  Cluster login + landscape (MCH namespace discovery)
    Step 5:  Environment Oracle — feature-aware dependency health
    Step 6:  Clone repositories
    Step 7:  Extract test context (code, selectors, imports)
    Step 8:  Feature area grounding
    Step 9:  Feature knowledge + KG dependency context

Usage:
    python -m src.scripts.gather <jenkins_url>
    python -m src.scripts.gather --url <jenkins_url> --output-dir ./runs

Output:
    Creates a run directory with:
    - core-data.json (primary data for AI - includes pre-parsed stack traces)
    - repos/automation/ (full cloned automation repo)
    - repos/console/ (full cloned console repo)
    - repos/kubevirt-plugin/ (version-correct kubevirt repo for VM tests)
    - console-log.txt
    - jenkins-build-info.json
    - test-report.json
    - cluster.kubeconfig (persisted cluster auth for Stage 1.5 and Stage 2)
"""

import argparse
import json
import logging
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add parent directories to path for imports
script_dir = Path(__file__).parent
src_dir = script_dir.parent
app_dir = src_dir.parent
sys.path.insert(0, str(app_dir))

from src.services.jenkins_api_client import JenkinsAPIClient, is_jenkins_available
from src.services.jenkins_intelligence_service import JenkinsIntelligenceService
from src.services.environment_validation_service import EnvironmentValidationService
from src.services.repository_analysis_service import RepositoryAnalysisService
from src.services.timeline_comparison_service import TimelineComparisonService
from src.services.stack_trace_parser import StackTraceParser
from src.services.shared_utils import mask_sensitive_dict, SENSITIVE_PATTERNS
from src.services.acm_console_knowledge import ACMConsoleKnowledge
from src.services.acm_ui_mcp_client import (
    ACMUIMCPClient,
    get_acm_ui_mcp_client,
    is_acm_ui_mcp_available
)
from src.services.component_extractor import ComponentExtractor
from src.services.knowledge_graph_client import (
    KnowledgeGraphClient,
    get_knowledge_graph_client,
    is_knowledge_graph_available
)
from src.services.cluster_investigation_service import ClusterInvestigationService
from src.services.feature_area_service import FeatureAreaService
from src.services.feature_knowledge_service import FeatureKnowledgeService
from src.services.environment_oracle_service import EnvironmentOracleService
from src.logging_config import configure_logging, bind_context


class DataGatherer:
    """
    Data Gatherer v4.0 - Collects factual data and clones repos for AI access.

    This class performs MECHANICAL data collection only.
    NO classification or reasoning is done here - that's the AI's job.

    Gathers data in 9 steps: Jenkins info, console log, test report,
    environment + cluster landscape, environment oracle, repo cloning,
    context extraction, feature grounding, and feature knowledge.
    """

    def __init__(self, output_dir: str = './runs', verbose: bool = False):
        """
        Initialize the data gatherer.

        Args:
            output_dir: Base directory for output files
            verbose: Enable verbose logging
        """
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.logger = self._setup_logging()

        # Initialize ACM UI MCP client (optional, for element discovery)
        self.acm_ui_mcp_client: Optional[ACMUIMCPClient] = None
        if is_acm_ui_mcp_available():
            self.acm_ui_mcp_client = get_acm_ui_mcp_client()
            self.logger.info("ACM UI MCP server available - element discovery enabled")

        # Initialize services
        self.jenkins_service = JenkinsIntelligenceService(use_api_client=True)
        self.env_service = EnvironmentValidationService()
        self.repo_service = RepositoryAnalysisService()
        self.timeline_service = TimelineComparisonService()
        self.stack_parser = StackTraceParser()

        # ACM Console Knowledge with optional MCP integration
        self.acm_knowledge = ACMConsoleKnowledge(mcp_client=self.acm_ui_mcp_client)

        # Component extractor for Knowledge Graph integration
        self.component_extractor = ComponentExtractor()

        # Cluster investigation for targeted component diagnostics (v3.0)
        self.cluster_investigation_service = ClusterInvestigationService()

        # Feature area grounding (v3.0)
        self.feature_area_service = FeatureAreaService()

        # Feature knowledge playbooks (v3.1)
        self.feature_knowledge_service = FeatureKnowledgeService()

        # Environment Oracle (v3.5) — feature-aware dependency health
        self.environment_oracle_service = EnvironmentOracleService()

        # Knowledge Graph client (optional - for dependency queries in Phase 2)
        # Initialized lazily after pre-flight checks in gather_all() to allow
        # the pre-flight to start Neo4j before we check availability.
        self.knowledge_graph_client: Optional[KnowledgeGraphClient] = None

        # Track what we've gathered
        self.gathered_data = {}

        # Track repo paths for run directory
        self.automation_repo_path: Optional[Path] = None
        self.console_repo_path: Optional[Path] = None
        self.kubevirt_repo_path: Optional[Path] = None

        # MCH namespace — discovered dynamically in Step 4a
        # Can be 'open-cluster-management', 'ocm', or custom
        self.mch_namespace: str = 'open-cluster-management'  # default fallback

        # Cache for expensive checks (avoid duplicate iterations)
        self._needs_kubevirt_repo: Optional[bool] = None

    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging (console + optional JSONL file)."""
        configure_logging(verbose=self.verbose)
        return logging.getLogger(__name__)

    def _preflight_checks(self):
        """
        Pre-flight checks: ensure optional services are running.

        Attempts to start the Neo4j Knowledge Graph container if it exists
        but is stopped. This is best-effort — the pipeline works without
        Neo4j but produces richer dependency analysis when it's available.
        """
        # Check if Neo4j is already reachable
        try:
            import urllib.request
            req = urllib.request.Request('http://localhost:7474/', method='GET')
            urllib.request.urlopen(req, timeout=2)
            self.logger.debug("Neo4j already available")
            return
        except Exception:
            pass

        # Try to start the container runtime and Neo4j container
        self.logger.info("Neo4j not reachable — attempting to start container...")

        # Detect container runtime
        runtime = None
        for cmd in ['podman', 'docker']:
            try:
                result = subprocess.run(
                    ['which', cmd], capture_output=True, timeout=5
                )
                if result.returncode == 0:
                    runtime = cmd
                    break
            except Exception:
                continue

        if not runtime:
            self.logger.debug("No container runtime (podman/docker) available")
            return

        # For podman, ensure the machine is running first
        if runtime == 'podman':
            try:
                # Check if podman can actually communicate
                result = subprocess.run(
                    ['podman', 'ps', '--format', '{{.Names}}'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    # Machine probably stopped — try to start it
                    print("  Starting Podman machine...", flush=True)
                    start_result = subprocess.run(
                        ['podman', 'machine', 'start'],
                        capture_output=True, text=True, timeout=90
                    )
                    if start_result.returncode != 0:
                        self.logger.debug(
                            f"Podman machine start failed: {start_result.stderr[:200]}"
                        )
                        return
                    time.sleep(3)
            except Exception as e:
                self.logger.debug(f"Podman machine check failed: {e}")
                return

        # Check if neo4j-rhacm container exists
        try:
            result = subprocess.run(
                [runtime, 'ps', '-a', '--filter', 'name=neo4j-rhacm',
                 '--format', '{{.Status}}'],
                capture_output=True, text=True, timeout=10
            )
            status = result.stdout.strip()
            if not status:
                self.logger.debug("No neo4j-rhacm container found")
                return

            if 'Up' in status or 'running' in status.lower():
                # Container running but API not responding — give it a moment
                time.sleep(2)
            else:
                # Container exists but stopped — start it
                print("  Starting Neo4j Knowledge Graph...", flush=True)
                subprocess.run(
                    [runtime, 'start', 'neo4j-rhacm'],
                    capture_output=True, timeout=30
                )
                # Wait for Neo4j to be ready (it takes a few seconds to initialize)
                for i in range(5):
                    time.sleep(2)
                    try:
                        req = urllib.request.Request(
                            'http://localhost:7474/', method='GET'
                        )
                        urllib.request.urlopen(req, timeout=2)
                        print("  Neo4j Knowledge Graph ready", flush=True)
                        self.logger.info("Neo4j started successfully")
                        return
                    except Exception:
                        pass

                self.logger.warning(
                    "Neo4j container started but not responding yet. "
                    "Pipeline will continue — KG queries may fail."
                )
        except Exception as e:
            self.logger.debug(f"Container check failed: {e}")

    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data before saving."""
        return mask_sensitive_dict(data, SENSITIVE_PATTERNS)

    def _print_step(self, step: int, total: int, message: str):
        """Print progress step to user."""
        print(f"\n  [{step}/{total}] {message}", flush=True)

    def _print_stage(self, stage_num: int, title: str, subtitle: str = ''):
        """Print a stage banner to the terminal."""
        print(f"\n{'=' * 60}", flush=True)
        print(f"  STAGE {stage_num}: {title}", flush=True)
        if subtitle:
            print(f"  {subtitle}", flush=True)
        print(f"{'=' * 60}", flush=True)

    def _login_to_cluster(self, run_dir: Path):
        """
        Extract cluster credentials from Jenkins parameters, login to the
        target cluster, and persist kubeconfig for all subsequent steps.

        Populates gathered_data['cluster_access'] and configures kubeconfig
        on ClusterInvestigationService and EnvironmentValidationService.

        Returns:
            kubeconfig_path or None if login failed
        """
        api_url, username, password = self._extract_cluster_credentials()

        self.gathered_data['cluster_access'] = {
            'api_url': api_url,
            'username': username,
            'has_credentials': bool(api_url and username and password),
            'password': password,
            'note': 'Credentials from Jenkins parameters.',
        }

        kubeconfig_path = None
        if api_url and username and password:
            self.logger.info(f"Logging into target cluster: {api_url}")
            kubeconfig_path = self._persist_cluster_kubeconfig(
                run_dir, api_url, username, password
            )
            if kubeconfig_path:
                # Share kubeconfig with all services that need cluster access
                self.env_service.kubeconfig = kubeconfig_path
                self.cluster_investigation_service.kubeconfig = kubeconfig_path
                self.cluster_investigation_service.cli = self.env_service.cli
                print(f"  Cluster kubeconfig persisted for all stages", flush=True)

                # Discover MCH namespace (can be open-cluster-management, ocm, or custom)
                self.mch_namespace = self._discover_mch_namespace(kubeconfig_path)
                self.cluster_investigation_service.mch_namespace = self.mch_namespace
                FeatureAreaService.set_mch_namespace(self.mch_namespace)
                self.logger.info(f"MCH namespace: {self.mch_namespace}")
            else:
                self.logger.warning("Failed to login to target cluster")
        else:
            self.logger.warning(
                "Target cluster credentials not found in Jenkins parameters."
            )

        self.gathered_data['cluster_access']['kubeconfig_path'] = kubeconfig_path
        self.gathered_data['cluster_access']['mch_namespace'] = self.mch_namespace
        return kubeconfig_path

    def _discover_mch_namespace(self, kubeconfig_path: str) -> str:
        """
        Discover the MCH namespace dynamically.

        The MultiClusterHub CR can be installed in different namespaces:
        - 'open-cluster-management' (default)
        - 'ocm' (common alternative)
        - Custom namespace

        Uses 'oc get mch -A' to find the actual namespace.

        Returns:
            The discovered namespace, or 'open-cluster-management' as fallback.
        """
        cli = self.env_service.cli or 'oc'
        try:
            result = subprocess.run(
                [cli, '--kubeconfig', kubeconfig_path,
                 'get', 'mch', '-A',
                 '-o', 'jsonpath={.items[0].metadata.namespace}'],
                capture_output=True, text=True, timeout=15
            )
            ns = result.stdout.strip().strip("'")
            if ns and result.returncode == 0:
                return ns
        except Exception as e:
            self.logger.debug(f"MCH namespace discovery failed: {e}")

        self.logger.warning(
            "Could not discover MCH namespace, using default 'open-cluster-management'"
        )
        return 'open-cluster-management'

    def _persist_cluster_kubeconfig(self, run_dir: Path, api_url: str,
                                     username: str, password: str) -> Optional[str]:
        """
        Create a persistent kubeconfig in the run directory for Stage 2.

        This avoids the problem of masked passwords in core-data.json
        by storing an authenticated kubeconfig that the AI agent can
        use directly with --kubeconfig.
        """
        kubeconfig_path = run_dir / 'cluster.kubeconfig'
        try:
            cmd = [
                self.env_service.cli,
                'login', api_url,
                '--username', username,
                '--password', password,
                '--insecure-skip-tls-verify=true',
                '--kubeconfig', str(kubeconfig_path)
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                self.logger.info(
                    f"Persisted cluster kubeconfig for Stage 2: {kubeconfig_path.name}"
                )
                return str(kubeconfig_path)
            else:
                self.logger.warning(
                    f"Failed to persist kubeconfig: {result.stderr.strip()}"
                )
                return None
        except Exception as e:
            self.logger.warning(f"Failed to persist kubeconfig: {e}")
            return None

    def gather_all(self, jenkins_url: str,
                   skip_environment: bool = False,
                   skip_repository: bool = False) -> Tuple[Path, Dict[str, Any]]:
        """
        Gather all data from Jenkins, environment, and repository.

        Args:
            jenkins_url: Full Jenkins build URL
            skip_environment: Skip environment validation
            skip_repository: Skip repository analysis

        Returns:
            Tuple of (run_directory, gathered_data)
        """
        start_time = time.time()

        # Pre-flight: ensure optional services are running
        self._preflight_checks()

        # Initialize Knowledge Graph client AFTER pre-flight (which may start Neo4j)
        if self.knowledge_graph_client is None and is_knowledge_graph_available():
            self.knowledge_graph_client = get_knowledge_graph_client()
            self.logger.info("RHACM Knowledge Graph available - dependency analysis enabled")

        # Create run directory
        run_dir = self._create_run_directory(jenkins_url)

        # Enable JSONL file logging into this run directory
        configure_logging(run_dir=run_dir, verbose=self.verbose)
        bind_context(run_id=run_dir.name, stage="gather")

        self.logger.info(f"Starting data gathering for: {jenkins_url}")

        print("\n" + "=" * 60)
        print("STAGE 1: DATA GATHERING")
        print("=" * 60)

        self.logger.info(f"Output directory: {run_dir}")

        # Initialize gathered data structure
        self.gathered_data = {
            'metadata': {
                'jenkins_url': jenkins_url,
                'gathered_at': datetime.now().isoformat(),
                'gatherer_version': '4.0.0',
                'jenkins_api_available': is_jenkins_available(),
                'acm_ui_mcp_available': True,  # Always available to Claude Code agent via native MCP
                'knowledge_graph_available': None,  # Updated after _check_feature_knowledge()
                'run_directory': str(run_dir)
            },
            'jenkins': {},
            'test_report': {},
            'console_log': {},
            'environment': {},
            'repositories': {},
            'errors': []
        }

        total_steps = 9

        # ── STAGE 1: DATA GATHERING ──
        self._print_stage(1, 'DATA GATHERING',
                          'Fetching Jenkins data, cluster health, and test reports')

        # Step 1: Gather Jenkins build info
        self._print_step(1, total_steps, "Fetching Jenkins build info...")
        self._gather_jenkins_build_info(jenkins_url, run_dir)
        # Show build result immediately
        build_result = self.gathered_data.get('jenkins', {}).get('build_result', '?')
        job_name = self.gathered_data.get('jenkins', {}).get('job_name', '?')
        build_num = self.gathered_data.get('jenkins', {}).get('build_number', '?')
        print(f"  Build: {job_name} #{build_num} — {build_result}", flush=True)

        # Step 2: Gather console log
        self._print_step(2, total_steps, "Downloading console log...")
        self._gather_console_log(jenkins_url, run_dir)

        # Step 3: Gather test report (CRITICAL for per-test analysis)
        self._print_step(3, total_steps, "Extracting test report...")
        self._gather_test_report(jenkins_url, run_dir)
        # Show test summary
        test_summary = self.gathered_data.get('test_report', {}).get('summary', {})
        total_tests = test_summary.get('total_tests', 0)
        failed_count = test_summary.get('failed_count', 0)
        pass_rate = test_summary.get('pass_rate', 0)
        if total_tests > 0:
            print(f"  Tests: {total_tests} total, {failed_count} failed ({pass_rate:.0f}% pass rate)", flush=True)

        # Step 4: Cluster login + landscape
        # Health audit handled by Stage 1.5 cluster-diagnostic agent
        if not skip_environment:
            self._print_step(4, total_steps, "Cluster login & landscape...")
            # 4a: Login to cluster and persist kubeconfig + MCH namespace discovery
            self._login_to_cluster(run_dir)
            # 4b: Cluster landscape (managed clusters, operators, resource pressure)
            self._gather_cluster_landscape()
            # Backend health investigation handled by Stage 1.5 (cluster-diagnostic agent)
            # and Stage 2 (analysis agent with live cluster access)
            self.gathered_data['cluster_health'] = {
                'deferred_to_stage_1_5': True,
                'note': 'Cluster health data provided by cluster-diagnosis.json from Stage 1.5'
            }
            self.gathered_data['environment'] = {
                'cluster_connectivity': self.gathered_data.get('cluster_access', {}).get('has_credentials', False),
                'source': 'cluster-login',
            }
            print("  Health data: provided by Stage 1.5 cluster diagnostic", flush=True)
        else:
            self._print_step(4, total_steps, "Skipping environment check (--skip-env)")
            self.gathered_data['cluster_landscape'] = {'skipped': True}
            self.gathered_data['cluster_health'] = {'skipped': True}
            self.gathered_data['environment'] = {'skipped': True}
            self.gathered_data['cluster_access'] = {'skipped': True}

        # ── STAGE 0: FEATURE CONTEXT ORACLE ──
        if not skip_environment:
            bind_context(stage="oracle")
            self._print_stage(0, 'FEATURE CONTEXT ORACLE',
                              'Feature-area identification, Polarion context & KG topology')
            self._print_step(5, total_steps, "Running feature context oracle...")
            # skip_cluster=True: health checks now handled by Step 4
            self._run_environment_oracle(skip_cluster=True)
            # Show oracle summary
            oracle = self.gathered_data.get('cluster_oracle', {})
            overall = oracle.get('overall_feature_health', {})
            healthy = overall.get('healthy_count', 0)
            total_deps = overall.get('total_dependencies', 0)
            areas = oracle.get('feature_areas', [])
            if areas:
                print(f"  Feature areas: {', '.join(areas)}", flush=True)
            if total_deps > 0:
                print(f"  Dependencies: {healthy}/{total_deps} healthy", flush=True)
        else:
            self._print_step(5, total_steps, "Skipping feature context oracle (--skip-env)")
            self.gathered_data['cluster_oracle'] = {'status': 'skipped'}

        # ── STAGE 1: DATA GATHERING (continued) ──
        bind_context(stage="gather")
        if not skip_environment:
            self._print_stage(1, 'DATA GATHERING (continued)',
                              'Repository cloning, context extraction, feature grounding')

        # Step 6: Clone repositories to run directory (optional)
        if not skip_repository:
            self._print_step(6, total_steps, "Cloning repositories...")
            self._clone_repositories(jenkins_url, run_dir)
        else:
            self._print_step(6, total_steps, "Skipping repository clone (--skip-repo)")

        # Step 7: Extract complete test context (AFTER repos are cloned)
        # This provides AI with all needed context upfront
        if not skip_repository:
            self._print_step(7, total_steps, "Extracting test context (code, selectors, imports)...")
            self._extract_complete_test_context(run_dir)
        else:
            self._print_step(7, total_steps, "Skipping context extraction (no repos)")

        # Step 8: Feature area grounding (v3.0)
        self._print_step(8, total_steps, "Grounding feature areas...")
        self._ground_feature_areas()

        # Step 9: Feature knowledge playbooks + KG dependency context (v3.1)
        # Now uses oracle results to resolve addon/operator/crd prerequisites
        self._print_step(9, total_steps, "Loading feature knowledge...")
        self._check_feature_knowledge()

        # Finalize MCP availability based on actual check results
        kg_status = self.gathered_data.get('feature_knowledge', {}).get('kg_status', {})
        self.gathered_data['metadata']['knowledge_graph_available'] = kg_status.get('available', False)

        # Calculate gathering time
        gathering_time = time.time() - start_time
        self.gathered_data['metadata']['gathering_time_seconds'] = gathering_time

        # Save data (NOTE: repos NOT cleaned up - AI needs access)
        self._save_combined_data(run_dir)

        self.logger.info(f"Data gathering complete in {gathering_time:.2f}s")
        self.logger.info(f"Files saved to: {run_dir}")
        self.logger.info("NOTE: Repos kept in runs/<dir>/repos/ for AI access")

        return run_dir, self.gathered_data

    def _create_run_directory(self, jenkins_url: str) -> Path:
        """Create timestamped run directory.

        Format: {YYYY-MM-DD}_{HH-MM-SS}_{job_name}
        Example: 2026-03-25_18-17-20_clc-e2e-pipeline

        Timestamp-first ensures all runs sort chronologically regardless
        of job name. Readable date format with dashes.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        # Extract job name from URL (last segment of the job path)
        job_name = "analysis"
        if '/job/' in jenkins_url:
            parts = jenkins_url.split('/job/')
            if len(parts) > 1:
                job_parts = [p.split('/')[0] for p in parts[1:] if p]
                # Use only the pipeline name (last part), not the full folder path
                job_name = job_parts[-1] if job_parts else 'analysis'
                job_name = job_name[:50]

        run_dir = self.output_dir / f"{timestamp}_{job_name}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save run metadata
        metadata = {
            'jenkins_url': jenkins_url,
            'created_at': datetime.now().isoformat(),
            'status': 'gathering'
        }
        (run_dir / 'run-metadata.json').write_text(json.dumps(metadata, indent=2))

        return run_dir

    def _gather_jenkins_build_info(self, jenkins_url: str, run_dir: Path):
        """Gather Jenkins build information."""
        self.logger.info("Gathering Jenkins build info...")

        try:
            # Skip console fetch here - we fetch it separately in _gather_console_log()
            # This avoids fetching the console log twice (saves network bandwidth and time)
            intelligence = self.jenkins_service.analyze_jenkins_url(jenkins_url, skip_console_fetch=True)

            build_info = {
                'build_url': intelligence.metadata.build_url,
                'job_name': intelligence.metadata.job_name,
                'build_number': intelligence.metadata.build_number,
                'build_result': intelligence.metadata.build_result,
                'timestamp': intelligence.metadata.timestamp,
                'parameters': intelligence.metadata.parameters,
                'branch': intelligence.metadata.branch,
                'commit_sha': intelligence.metadata.commit_sha,
                'artifacts': intelligence.metadata.artifacts,
                'environment_info': intelligence.environment_info,
            }

            self.gathered_data['jenkins'] = build_info

            # Save to file with masked credentials
            masked_build_info = self._mask_sensitive_data(build_info)
            output_path = run_dir / 'jenkins-build-info.json'
            output_path.write_text(json.dumps(masked_build_info, indent=2, default=str))

            self.logger.info(f"Build result: {build_info['build_result']}")

        except Exception as e:
            error_msg = f"Failed to gather Jenkins build info: {str(e)}"
            self.logger.error(error_msg)
            self.gathered_data['errors'].append(error_msg)
            self.gathered_data['jenkins'] = {'error': error_msg}

    def _gather_console_log(self, jenkins_url: str, run_dir: Path):
        """Gather console log from Jenkins."""
        self.logger.info("Gathering console log...")

        try:
            api_client = JenkinsAPIClient()
            if api_client.is_authenticated:
                success, console_output, error = api_client.get_console_output(jenkins_url)
                if not success:
                    self.logger.warning(f"API client console fetch failed: {error}")
                    console_output = self.jenkins_service._fetch_console_log(jenkins_url)
            else:
                console_output = self.jenkins_service._fetch_console_log(jenkins_url)

            if console_output:
                # Save full console log
                console_path = run_dir / 'console-log.txt'
                console_path.write_text(console_output)

                # Extract key info
                lines = console_output.split('\n')
                error_lines = [l for l in lines if 'error' in l.lower() or 'fail' in l.lower()]

                # Detect error patterns (factual, no classification)
                has_500_errors = any('500' in l for l in error_lines)
                has_network_errors = any('network' in l.lower() or 'connection' in l.lower() for l in error_lines)
                has_timeout_mentions = any('timeout' in l.lower() or 'timed out' in l.lower() for l in lines)

                self.gathered_data['console_log'] = {
                    'file_path': 'console-log.txt',
                    'total_lines': len(lines),
                    'error_lines_count': len(error_lines),
                    'key_errors': error_lines[:20],
                    'error_patterns': {
                        'has_500_errors': has_500_errors,
                        'has_network_errors': has_network_errors,
                        'has_timeout_mentions': has_timeout_mentions
                    }
                }

                self.logger.info(f"Console log: {len(lines)} lines, {len(error_lines)} errors")
            else:
                self.gathered_data['console_log'] = {'error': 'Failed to fetch console log'}

        except Exception as e:
            error_msg = f"Failed to gather console log: {str(e)}"
            self.logger.error(error_msg)
            self.gathered_data['errors'].append(error_msg)
            self.gathered_data['console_log'] = {'error': error_msg}

    def _gather_test_report(self, jenkins_url: str, run_dir: Path):
        """Gather test report - CRITICAL for per-test analysis."""
        self.logger.info("Gathering test report...")

        try:
            test_report = self.jenkins_service._fetch_and_analyze_test_report(jenkins_url)

            if test_report:
                test_data = {
                    'summary': {
                        'total_tests': test_report.total_tests,
                        'passed_count': test_report.passed_count,
                        'failed_count': test_report.failed_count,
                        'skipped_count': test_report.skipped_count,
                        'pass_rate': test_report.pass_rate,
                        'duration': test_report.duration
                    },
                    'failed_tests': []
                }

                # Extract each failed test with FULL details and parsed stack traces
                # NO pre-classification - AI will classify
                for test in test_report.failed_tests:
                    test_entry = {
                        'test_name': test.test_name,
                        'class_name': test.class_name,
                        'status': test.status,
                        'duration_seconds': test.duration,
                        'error_message': test.error_message,
                        'stack_trace': test.stack_trace,
                        'failure_type': test.failure_type
                        # NO classification fields - AI determines this
                    }

                    # Parse stack trace to extract structured data (Phase 1 enhancement)
                    parsed_stack = self._parse_stack_trace_data(
                        test.stack_trace,
                        test.error_message
                    )
                    if parsed_stack:
                        test_entry['parsed_stack_trace'] = parsed_stack

                    # Extract backend component names for Knowledge Graph queries
                    detected_components = self._extract_components_from_failure(
                        test.error_message,
                        test.stack_trace
                    )
                    test_entry['detected_components'] = detected_components or []

                    test_data['failed_tests'].append(test_entry)

                self.gathered_data['test_report'] = test_data

                # Save to file
                output_path = run_dir / 'test-report.json'
                output_path.write_text(json.dumps(test_data, indent=2, default=str))

                self.logger.info(f"Test report: {test_report.total_tests} total, "
                               f"{test_report.failed_count} failed")
            else:
                self.gathered_data['test_report'] = {
                    'summary': {'total_tests': 0, 'failed_count': 0},
                    'failed_tests': [],
                    'note': 'No test report available for this build'
                }
                self.logger.info("No test report available")

        except Exception as e:
            error_msg = f"Failed to gather test report: {str(e)}"
            self.logger.error(error_msg)
            self.gathered_data['errors'].append(error_msg)
            self.gathered_data['test_report'] = {'error': error_msg}

    def _extract_cluster_credentials(self) -> tuple:
        """Extract target cluster URL and credentials from Jenkins parameters."""
        jenkins_data = self.gathered_data.get('jenkins', {})
        params = jenkins_data.get('parameters', {})

        api_url = (
            params.get('CYPRESS_HUB_API_URL') or
            params.get('OC_CLUSTER_API_URL') or
            params.get('CLUSTER_API_URL') or
            params.get('API_URL') or
            params.get('HUB_API_URL')
        )

        username = (
            params.get('CYPRESS_OPTIONS_HUB_USER') or
            params.get('OC_CLUSTER_USER') or
            params.get('CLUSTER_USER') or
            params.get('USERNAME') or
            params.get('HUB_USER')
        )

        password = (
            params.get('CYPRESS_OPTIONS_HUB_PASSWORD') or
            params.get('OC_CLUSTER_PASS') or
            params.get('CLUSTER_PASSWORD') or
            params.get('PASSWORD') or
            params.get('HUB_PASSWORD')
        )

        if api_url:
            self.logger.info(f"Found target cluster URL: {api_url}")

        return api_url, username, password

    def _gather_cluster_landscape(self):
        """
        Gather cluster landscape snapshot (part of Step 4, v3.0).

        Collects managed clusters, operator statuses, resource pressure,
        policies, and MCH status into core-data.json under 'cluster_landscape'.

        Uses the kubeconfig and CLI from the environment validation service
        to ensure both services query the same cluster.
        """
        self.logger.info("Gathering cluster landscape...")

        try:
            # Share kubeconfig and CLI from env service so both query the same cluster
            env_kubeconfig = self.env_service.kubeconfig
            if env_kubeconfig:
                self.cluster_investigation_service.kubeconfig = env_kubeconfig
            self.cluster_investigation_service.cli = self.env_service.cli

            landscape = self.cluster_investigation_service.get_cluster_landscape()
            landscape_data = self.cluster_investigation_service.to_dict(landscape)
            self.gathered_data['cluster_landscape'] = landscape_data

            # Log key findings
            if landscape.degraded_operators:
                self.logger.warning(
                    f"Degraded operators: {', '.join(landscape.degraded_operators)}"
                )
            if any(landscape.resource_pressure.values()):
                pressures = [k for k, v in landscape.resource_pressure.items() if v]
                self.logger.warning(f"Resource pressure: {', '.join(pressures)}")

            self.logger.info(
                f"Cluster landscape: {landscape.managed_cluster_count} managed clusters, "
                f"{len(landscape.degraded_operators)} degraded operators"
            )

        except Exception as e:
            error_msg = f"Failed to gather cluster landscape: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['cluster_landscape'] = {'error': error_msg}

    # Backend probes removed — backend health investigation is handled by:
    # - Stage 1.5 (cluster-diagnostic agent): pod health, operator status,
    #   console plugin health, addon verification, dependency chain tracing
    # - Stage 2 (analysis agent): targeted investigation during per-test analysis
    #   with full context about what feature area and component to check

    def _ground_feature_areas(self):
        """
        Step 8: Ground feature areas for all failed tests (v3.0).

        Groups tests by feature area and adds grounding context
        (subsystem, key components, namespaces) to core-data.json.
        """
        self.logger.info("Grounding feature areas...")

        test_report = self.gathered_data.get('test_report', {})
        failed_tests = test_report.get('failed_tests', [])

        if not failed_tests:
            self.gathered_data['feature_grounding'] = {
                'groups': {},
                'note': 'No failed tests to ground',
            }
            return

        try:
            groups = self.feature_area_service.group_tests_by_feature(failed_tests)

            # Serialize for core-data.json
            grounding_data = {
                'groups': {},
                'feature_areas_found': list(groups.keys()),
                'total_groups': len(groups),
            }

            for area, group in groups.items():
                grounding_data['groups'][area] = {
                    'subsystem': group.grounding.subsystem,
                    'key_components': group.grounding.key_components,
                    'key_namespaces': group.grounding.key_namespaces,
                    'investigation_focus': group.grounding.investigation_focus,
                    'tests': group.tests,
                    'test_count': group.test_count,
                }

            self.gathered_data['feature_grounding'] = grounding_data

            # Log summary
            for area, group in groups.items():
                self.logger.info(
                    f"  {area} ({group.grounding.subsystem}): "
                    f"{group.test_count} test(s)"
                )

        except Exception as e:
            error_msg = f"Failed to ground feature areas: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['feature_grounding'] = {'error': error_msg}

    def _run_environment_oracle(self, skip_cluster: bool = False):
        """
        Step 5: Run Environment Oracle — feature-aware dependency health.

        Discovers feature dependencies from playbooks and checks their health
        on the live cluster. Results are used by Step 9 (feature knowledge)
        to resolve addon/operator/crd prerequisites that were previously
        hardcoded to met=None.
        """
        self.logger.info("Running environment oracle...")
        try:
            jenkins_data = self.gathered_data.get('jenkins', {})
            test_report = self.gathered_data.get('test_report', {})
            cluster_landscape = self.gathered_data.get('cluster_landscape', {})
            cluster_credentials = self.gathered_data.get('cluster_access')

            oracle_result = self.environment_oracle_service.run_oracle(
                jenkins_data=jenkins_data,
                test_report=test_report,
                cluster_landscape=cluster_landscape,
                cluster_credentials=cluster_credentials,
                skip_cluster=skip_cluster,
                knowledge_graph_client=self.knowledge_graph_client,
            )

            self.gathered_data['cluster_oracle'] = oracle_result

            # Log summary
            overall = oracle_result.get('overall_feature_health', {})
            healthy = overall.get('healthy_count', 0)
            total = overall.get('total_dependencies', 0)
            issues = overall.get('blocking_issues', [])

            if total > 0:
                self.logger.info(
                    f"Oracle: {healthy}/{total} dependencies healthy"
                )
            if issues:
                for issue in issues:
                    self.logger.warning(f"Oracle issue: {issue}")

        except Exception as e:
            error_msg = f"Environment oracle failed: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['cluster_oracle'] = {'error': error_msg}
            self.gathered_data['errors'].append(error_msg)

    def _check_feature_knowledge(self):
        """
        Step 9: Load feature investigation playbooks, check MCH prerequisites,
        pre-match test error messages against known failure paths, and query
        Knowledge Graph for dependency context.

        Populates gathered_data['feature_knowledge'] with:
        - acm_version: detected ACM version
        - profiles_loaded: list of loaded feature area names
        - feature_readiness: per-area readiness assessment
        - investigation_playbooks: full playbook content per area
        - kg_dependency_context: per-area KG dependency graph (if available)
        """
        self.logger.info("Loading feature knowledge playbooks...")

        try:
            # Detect ACM version from Jenkins params or MCH
            jenkins_data = self.gathered_data.get('jenkins', {})
            params = jenkins_data.get('parameters', {})
            landscape = self.gathered_data.get('cluster_landscape', {})
            acm_version = params.get('DOWNSTREAM_RELEASE')
            if not acm_version:
                mch_ver = landscape.get('mch_version', '')
                if mch_ver:
                    # Extract major.minor from version like "2.16.1"
                    parts = mch_ver.split('.')
                    if len(parts) >= 2:
                        acm_version = f"{parts[0]}.{parts[1]}"

            # Get detected feature areas from Step 7
            grounding = self.gathered_data.get('feature_grounding', {})
            feature_areas = grounding.get('feature_areas_found', [])

            if not feature_areas:
                self.gathered_data['feature_knowledge'] = {
                    'note': 'No feature areas detected — skipping playbook loading',
                }
                return

            # Load playbooks
            profiles = self.feature_knowledge_service.load_playbooks(
                acm_version=acm_version,
                feature_areas=feature_areas,
            )

            # Get MCH component states from cluster landscape
            mch_components = landscape.get('mch_enabled_components', {})

            # Get error messages per feature area for symptom matching
            groups = grounding.get('groups', {})
            test_report = self.gathered_data.get('test_report', {})
            failed_tests = test_report.get('failed_tests', [])
            test_errors = {}
            for test in failed_tests:
                test_name = test.get('test_name', '')
                error_msg = test.get('error_message', '')
                if error_msg:
                    test_errors[test_name] = error_msg

            # Build readiness and playbooks per feature area
            feature_readiness = {}
            investigation_playbooks = {}
            for area in profiles:
                # Collect error messages for tests in this feature area
                area_group = groups.get(area, {})
                area_tests = area_group.get('tests', [])
                area_errors = [
                    test_errors[t] for t in area_tests if t in test_errors
                ]

                # Get readiness (pass oracle + cluster health to resolve prerequisites)
                oracle_data = self.gathered_data.get('cluster_oracle', {})
                cluster_health = self.gathered_data.get('cluster_health', {})
                readiness = self.feature_knowledge_service.get_feature_readiness(
                    area,
                    mch_components=mch_components,
                    cluster_landscape=landscape,
                    error_messages=area_errors,
                    oracle_data=oracle_data,
                    cluster_health=cluster_health,
                )
                feature_readiness[area] = self.feature_knowledge_service.to_dict(readiness)

                # Get full playbook
                playbook = self.feature_knowledge_service.get_investigation_playbook(area)
                if playbook:
                    investigation_playbooks[area] = playbook

            # Query Knowledge Graph for dependency context
            kg_dependency_context = {}
            kg_status = {}
            if not self.knowledge_graph_client or not self.knowledge_graph_client.available:
                # KG unavailable — warn explicitly
                kg_status = {
                    'available': False,
                    'error': 'Knowledge Graph (Neo4j RHACM) is not connected',
                    'impact': (
                        'Tier 3-4 investigation will lack dependency graphs, '
                        'cascading failure analysis, and cross-subsystem tracing. '
                        'Playbook prerequisites and failure paths still work.'
                    ),
                    'remediation': (
                        'Run: bash mcp/setup.sh from the ai_systems_v2 repo root '
                        'to configure the Neo4j RHACM MCP server. Ensure the Neo4j '
                        'database is running and populated with RHACM component data.'
                    ),
                }
                self.logger.warning(
                    "Knowledge Graph UNAVAILABLE — dependency context will be missing. "
                    "Run 'bash mcp/setup.sh' to configure. "
                    "Tier 3-4 investigation degraded."
                )
                self.gathered_data['errors'].append(
                    "Knowledge Graph unavailable: Tier 3-4 cluster investigation "
                    "will lack dependency analysis. Run 'bash mcp/setup.sh' to fix."
                )
            else:
                kg_status = {'available': True}
                for area in profiles:
                    area_group = groups.get(area, {})
                    subsystem = area_group.get('subsystem', area)
                    try:
                        kg_context = self._query_kg_dependency_context(subsystem)
                        if kg_context:
                            kg_dependency_context[area] = kg_context
                    except Exception as e:
                        kg_error = f"KG query failed for {area}/{subsystem}: {e}"
                        self.logger.warning(kg_error)
                        self.gathered_data['errors'].append(kg_error)

            # Run deterministic gap detection (v4.0)
            feature_areas_with_errors = {}
            for area in profiles:
                area_group = groups.get(area, {})
                area_tests = area_group.get('tests', [])
                errs = [test_errors[t] for t in area_tests if t in test_errors]
                if errs:
                    feature_areas_with_errors[area] = errs

            knowledge_dir = Path(__file__).parent.parent.parent / 'knowledge'
            gap_detection = self.feature_knowledge_service.run_gap_detection(
                acm_version=acm_version,
                feature_areas_with_errors=feature_areas_with_errors,
                components_path=knowledge_dir / 'components.yaml',
            )

            # Build feature_knowledge section
            self.gathered_data['feature_knowledge'] = {
                'acm_version': acm_version,
                'profiles_loaded': list(profiles.keys()),
                'feature_readiness': feature_readiness,
                'investigation_playbooks': investigation_playbooks,
                'kg_dependency_context': kg_dependency_context,
                'kg_status': kg_status,
                'gap_detection': gap_detection,
            }

            # Log summary
            self.logger.info(
                f"Loaded {len(profiles)} playbooks for: "
                f"{', '.join(profiles.keys())}"
            )
            match_rate = gap_detection.get('overall_match_rate', 0)
            stale_count = len(gap_detection.get('stale_components', []))
            gap_areas = gap_detection.get('gap_areas', [])
            if stale_count:
                self.logger.warning(f"  Gap detection: {stale_count} stale component(s)")
            if gap_areas:
                self.logger.warning(f"  Gap detection: low match rate areas: {gap_areas}")
            self.logger.info(f"  Symptom match rate: {match_rate:.0%}")
            for area, readiness_data in feature_readiness.items():
                unmet = readiness_data.get('unmet_prerequisites', [])
                matched = readiness_data.get('pre_matched_paths', [])
                if unmet:
                    self.logger.warning(
                        f"  {area}: {len(unmet)} unmet prerequisite(s)"
                    )
                if matched:
                    self.logger.info(
                        f"  {area}: {len(matched)} failure path(s) pre-matched"
                    )

        except Exception as e:
            error_msg = f"Failed to load feature knowledge: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['feature_knowledge'] = {'error': error_msg}

    def _query_kg_dependency_context(self, subsystem: str) -> Optional[dict]:
        """
        Query Knowledge Graph for a subsystem's internal data flow and
        cross-subsystem dependencies.

        Returns dict with internal_data_flow, cross_subsystem_dependencies,
        and components_in_subsystem, or None if KG unavailable.
        """
        if not self.knowledge_graph_client or not self.knowledge_graph_client.available:
            return None

        try:
            # Get internal relationships within subsystem
            internal_query = f"""
            MATCH (c:RHACMComponent)-[r]->(dep:RHACMComponent)
            WHERE c.subsystem =~ '(?i).*{subsystem}.*'
              AND dep.subsystem =~ '(?i).*{subsystem}.*'
            RETURN DISTINCT c.label as source, type(r) as relationship, dep.label as target
            ORDER BY c.label
            LIMIT 50
            """
            internal_result = self.knowledge_graph_client._execute_cypher(internal_query)
            internal_data_flow = []
            if internal_result:
                for row in internal_result:
                    src = row.get('source', '')
                    rel = row.get('relationship', '')
                    tgt = row.get('target', '')
                    internal_data_flow.append(f"{src} --{rel}--> {tgt}")

            # Get cross-subsystem dependencies
            cross_query = f"""
            MATCH (c:RHACMComponent)-[r]->(dep:RHACMComponent)
            WHERE c.subsystem =~ '(?i).*{subsystem}.*'
              AND NOT dep.subsystem =~ '(?i).*{subsystem}.*'
            RETURN DISTINCT c.subsystem as source_subsystem, type(r) as relationship,
                   dep.label as target, dep.subsystem as target_subsystem
            ORDER BY dep.subsystem
            LIMIT 30
            """
            cross_result = self.knowledge_graph_client._execute_cypher(cross_query)
            cross_deps = []
            if cross_result:
                for row in cross_result:
                    src_sub = row.get('source_subsystem', '')
                    rel = row.get('relationship', '')
                    tgt = row.get('target', '')
                    tgt_sub = row.get('target_subsystem', '')
                    cross_deps.append(f"{src_sub} --{rel}--> {tgt} ({tgt_sub})")

            # Get component count
            components = self.knowledge_graph_client.get_subsystem_components(subsystem)

            return {
                'internal_data_flow': internal_data_flow,
                'cross_subsystem_dependencies': cross_deps,
                'components_in_subsystem': len(components),
            }

        except Exception as e:
            self.logger.debug(f"KG dependency query failed for {subsystem}: {e}")
            return None

    def _extract_repo_info_from_console(self, run_dir: Path) -> Tuple[Optional[str], Optional[str]]:
        """Extract repository URL and branch from console log."""
        console_path = run_dir / 'console-log.txt'

        if not console_path.exists():
            return None, None

        repo_url = None
        branch = None

        try:
            with open(console_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Pattern 1: "Checking out git https://github.com/org/repo.git"
            checkout_pattern = r'Checking out git\s+(https?://[^\s]+\.git)'
            match = re.search(checkout_pattern, content)
            if match:
                repo_url = match.group(1)

            # Pattern 2: "git fetch ... https://github.com/org/repo.git"
            if not repo_url:
                fetch_pattern = r'git fetch[^\n]+(https?://github\.com/[^\s]+\.git)'
                match = re.search(fetch_pattern, content)
                if match:
                    repo_url = match.group(1)

            # Extract branch
            branch_pattern = r'Checking out Revision [a-f0-9]+ \(origin/([^\)]+)\)'
            match = re.search(branch_pattern, content)
            if match:
                branch = match.group(1)

            # From build parameters
            if not branch:
                jenkins_data = self.gathered_data.get('jenkins', {})
                params = jenkins_data.get('parameters', {})
                if params.get('GIT_BRANCH'):
                    branch = params.get('GIT_BRANCH')

        except Exception as e:
            self.logger.warning(f"Error extracting repo info: {e}")

        return repo_url, branch

    def _clone_repositories(self, jenkins_url: str, run_dir: Path):
        """Clone automation and console repositories to run directory."""
        self.logger.info("Cloning repositories to run directory...")

        repos_dir = run_dir / 'repos'
        repos_dir.mkdir(parents=True, exist_ok=True)

        # Extract repo info from console log
        repo_url, branch = self._extract_repo_info_from_console(run_dir)

        if not repo_url:
            job_name = self.gathered_data['jenkins'].get('job_name', '')
            self.logger.info(f"No repo URL in console, inferring from job: {job_name}")
            # Try to infer from job name
            repo_url = self.repo_service._infer_repo_from_job(job_name)

        if not repo_url:
            self.gathered_data['repositories'] = {
                'automation': {'cloned': False, 'error': 'Could not determine repo URL'},
                'console': {'cloned': False, 'error': 'Skipped - no automation repo'}
            }
            return

        branch = branch or 'main'

        # Clone automation repo
        automation_path = repos_dir / 'automation'
        self.logger.info(f"Cloning automation repo: {repo_url} (branch: {branch})")

        success, commit_sha, error = self.repo_service.clone_to(
            repo_url=repo_url,
            branch=branch,
            target_path=automation_path
        )

        if success:
            self.automation_repo_path = automation_path
            self.gathered_data['repositories']['automation'] = {
                'path': 'repos/automation',
                'url': repo_url,
                'branch': branch,
                'commit': commit_sha,
                'cloned': True
            }
            self.logger.info(f"Automation repo cloned to: {automation_path}")

            # Clone console repo
            console_path = repos_dir / 'console'
            self.logger.info(f"Cloning console repo (branch: {branch})...")

            console_success, console_error = self.timeline_service.clone_console_to(
                branch=branch,
                target_path=console_path
            )

            if console_success:
                self.console_repo_path = console_path
                self.gathered_data['repositories']['console'] = {
                    'path': 'repos/console',
                    'url': 'https://github.com/stolostron/console.git',
                    'branch': branch,
                    'cloned': True
                }
                self.logger.info(f"Console repo cloned to: {console_path}")

                # Extract PatternFly version from console repo
                pf_version = self.acm_knowledge.extract_patternfly_version(console_path)
                if pf_version:
                    self.gathered_data['repositories']['console']['patternfly_version'] = pf_version
                    self.logger.info(f"Extracted PatternFly version info ({len(pf_version)} packages)")

                # Validate ACM console structure
                structure_valid = self.acm_knowledge.validate_structure(console_path)
                self.gathered_data['repositories']['console']['structure_valid'] = structure_valid
            else:
                self.gathered_data['repositories']['console'] = {
                    'cloned': False,
                    'error': console_error
                }

            # Check if any failed tests require kubevirt-plugin repo
            needs_kubevirt = self._check_needs_kubevirt_repo()
            if needs_kubevirt:
                self._clone_kubevirt_repo(repos_dir, branch)
        else:
            self.gathered_data['repositories'] = {
                'automation': {'cloned': False, 'error': error},
                'console': {'cloned': False, 'error': 'Skipped - automation clone failed'},
                'kubevirt_plugin': {'cloned': False, 'error': 'Skipped - automation clone failed'}
            }
            self.logger.warning(f"Failed to clone automation repo: {error}")

    def _check_needs_kubevirt_repo(self) -> bool:
        """
        Check if any failed tests require the kubevirt-plugin repository.

        Virtualization tests use UI components from kubevirt-ui/kubevirt-plugin
        which is separate from the main stolostron/console repo.

        Returns:
            True if kubevirt-plugin repo should be cloned

        Note: Result is cached to avoid duplicate iterations over failed_tests.
        """
        # Return cached result if available
        if self._needs_kubevirt_repo is not None:
            return self._needs_kubevirt_repo

        test_report = self.gathered_data.get('test_report', {})
        failed_tests = test_report.get('failed_tests', [])

        for test in failed_tests:
            test_name = test.get('test_name', '')
            if self.acm_knowledge.requires_kubevirt_repo(test_name):
                self.logger.info(f"Test '{test_name}' requires kubevirt-plugin repo")
                self._needs_kubevirt_repo = True
                return True

        self._needs_kubevirt_repo = False
        return False

    def _clone_kubevirt_repo(self, repos_dir: Path, branch: str):
        """
        Clone kubevirt-plugin repository for virtualization test investigation.

        Enhanced with CNV version detection to clone the correct branch.
        Priority:
        1. CNV version-detected branch (e.g., CNV 4.20.x -> release-4.20)
        2. Specified branch from automation repo
        3. Main/master fallback

        Args:
            repos_dir: Base directory for repos (runs/<dir>/repos/)
            branch: Branch to try (falls back to main/master)
        """
        kubevirt_path = repos_dir / 'kubevirt-plugin'

        # Try to detect CNV version for correct branch selection
        detected_branch = None
        cnv_version_info = None

        if self.acm_ui_mcp_client:
            try:
                cnv_info = self.acm_ui_mcp_client.detect_cnv_version()
                if cnv_info:
                    cnv_version_info = {
                        'version': cnv_info.version,
                        'branch': cnv_info.branch,
                        'detected_from': cnv_info.detected_from
                    }
                    detected_branch = cnv_info.branch
                    self.logger.info(
                        f"CNV version {cnv_info.version} detected from {cnv_info.detected_from}, "
                        f"using branch: {detected_branch}"
                    )
            except Exception as e:
                self.logger.debug(f"CNV version detection failed: {e}")

        # Use detected branch if available, otherwise fall back to provided branch
        target_branch = detected_branch or branch
        self.logger.info(f"Cloning kubevirt-plugin repo (branch: {target_branch})...")

        kubevirt_success, kubevirt_error = self.timeline_service.clone_kubevirt_to(
            branch=target_branch,
            target_path=kubevirt_path
        )

        if kubevirt_success:
            self.kubevirt_repo_path = kubevirt_path
            self.gathered_data['repositories']['kubevirt_plugin'] = {
                'path': 'repos/kubevirt-plugin',
                'url': 'https://github.com/kubevirt-ui/kubevirt-plugin.git',
                'branch': target_branch,
                'cloned': True
            }

            # Add CNV version info if detected
            if cnv_version_info:
                self.gathered_data['repositories']['kubevirt_plugin']['cnv_version'] = cnv_version_info

            self.logger.info(f"KubeVirt plugin repo cloned to: {kubevirt_path}")

            # Validate kubevirt structure
            structure_valid = self.acm_knowledge.validate_kubevirt_structure(kubevirt_path)
            self.gathered_data['repositories']['kubevirt_plugin']['structure_valid'] = structure_valid
        else:
            self.gathered_data['repositories']['kubevirt_plugin'] = {
                'cloned': False,
                'error': kubevirt_error
            }
            self.logger.warning(f"Failed to clone kubevirt-plugin repo: {kubevirt_error}")

    def _extract_complete_test_context(self, run_dir: Path):
        """
        Extract complete context for each failing test.

        This method runs AFTER repos are cloned. It populates:
        - test_file: actual test code from repos/automation/
        - recent_selector_changes: selector timeline analysis (populated by data-collector agent)
        - assertion_analysis: parsed expected vs actual from assertion errors
        - failure_mode_category: categorized failure mode

        The following fields are initialized as empty/null and populated
        later by the data-collector agent (after gather.py completes):
        - page_objects: selector definitions from imported files
        - console_search: verified selector existence in product source
        - temporal_summary: populated by data-collector agent (Task 3)
        """
        self.logger.info("Extracting complete test context for AI analysis...")

        test_report = self.gathered_data.get('test_report', {})
        failed_tests = test_report.get('failed_tests', [])

        if not failed_tests:
            self.logger.info("No failed tests - skipping context extraction")
            return

        repos_dir = run_dir / 'repos'
        automation_path = repos_dir / 'automation'

        for i, test in enumerate(failed_tests):
            test_name = test.get('test_name', '')
            parsed_stack = test.get('parsed_stack_trace', {})

            self.logger.debug(f"Extracting context for: {test_name}")

            extracted_context = {
                'test_file': None,
                'page_objects': [],
                'console_search': None,
                'recent_selector_changes': None,
                'assertion_analysis': None,
                'failure_mode_category': None,
                'temporal_summary': None,
            }

            # 1. Extract test file content
            test_file_path = parsed_stack.get('root_cause_file') or parsed_stack.get('test_file')
            if test_file_path and automation_path.exists():
                test_content = self._read_test_file(automation_path, test_file_path)
                if test_content:
                    extracted_context['test_file'] = test_content

            # 2. Page objects — populated by data-collector agent after gather.py completes.
            # The agent traces imports and resolves selector definitions across any
            # test framework (Cypress, Playwright, etc.) using AI code analysis.

            # 3-4. Console search + recent selector changes — populated by data-collector
            # agent after gather.py completes. The agent uses MCP tools and git history
            # analysis for context-aware verification.

            # 5. Extract assertion values from error message
            error_message = test.get('error_message', '')
            if error_message:
                assertion_values = self.stack_parser.extract_assertion_values(error_message)
                if assertion_values:
                    extracted_context['assertion_analysis'] = assertion_values
            # assertion_analysis stays None if no assertion values found

            # 6. Determine failure mode category (GAP-01 + GAP-02)
            extracted_context['failure_mode_category'] = self._classify_failure_mode(
                test.get('failure_type', ''),
                error_message,
                extracted_context.get('console_search'),
                extracted_context.get('assertion_analysis'),
            )

            # Store extracted context in the test entry
            self.gathered_data['test_report']['failed_tests'][i]['extracted_context'] = extracted_context

        self.logger.info(f"Extracted context for {len(failed_tests)} failed tests")

    @staticmethod
    def _classify_failure_mode(
        failure_type: str,
        error_message: str,
        console_search: Optional[Dict],
        assertion_analysis: Optional[Dict],
    ) -> str:
        """
        Categorize each test's failure mode for causal link verification.

        Categories:
            render_failure   - page didn't load, blank page, no elements rendered
            element_missing  - specific selector not found in DOM
            data_incorrect   - element found but wrong data/count/value
            timeout_general  - generic timeout without specific element
            assertion_logic  - test logic assertion that doesn't fit above
            server_error     - 500/502/503 backend error
            unknown          - cannot determine
        """
        ft = (failure_type or '').lower()
        err = (error_message or '').lower()

        # Server errors are their own category
        if ft == 'server_error' or any(p in err for p in ['500', '502', '503', 'internal server']):
            return 'server_error'

        # Blank/empty page
        if any(p in err for p in ['no-js', 'blank page', 'empty body', 'zero interactive']):
            return 'render_failure'

        # Data assertion: element found but data is wrong
        if assertion_analysis and assertion_analysis.get('has_data_assertion'):
            # Check if console_search found the selector (page rendered, data wrong)
            if console_search and console_search.get('found', False):
                return 'data_incorrect'
            # Even without console_search, count_mismatch is data-level
            if assertion_analysis.get('assertion_type') in ('count_mismatch', 'content_missing'):
                return 'data_incorrect'

        # Element not found
        if ft == 'element_not_found' or 'expected to find element' in err:
            return 'element_missing'

        # Timeout without specific element
        if ft == 'timeout':
            if 'expected to find element' in err or 'cy.get(' in err:
                return 'element_missing'
            return 'timeout_general'

        # Generic assertion
        if ft in ('assertion', 'assertion_selector', 'assertion_data'):
            if ft == 'assertion_data':
                return 'data_incorrect'
            return 'assertion_logic'

        return 'unknown'

    def _read_test_file(
        self,
        automation_path: Path,
        test_file_path: str,
        max_lines: int = 200
    ) -> Optional[Dict[str, Any]]:
        """
        Read the content of a test file.

        Args:
            automation_path: Path to automation repo
            test_file_path: Relative path to test file
            max_lines: Maximum lines to include (to avoid huge files)

        Returns:
            Dict with file path, content, and line count
        """
        try:
            # Normalize the path - handle various formats
            # Could be: cypress/e2e/test.cy.ts or just test.cy.ts
            if test_file_path.startswith('/'):
                test_file_path = test_file_path[1:]

            # Try direct path first
            full_path = automation_path / test_file_path

            # If not found, try common prefixes
            if not full_path.exists():
                possible_paths = [
                    automation_path / test_file_path,
                    automation_path / 'cypress' / test_file_path,
                    automation_path / 'cypress' / 'e2e' / test_file_path,
                ]
                for path in possible_paths:
                    if path.exists():
                        full_path = path
                        break

            if not full_path.exists():
                return None

            content = full_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')

            # Truncate if too long
            if len(lines) > max_lines:
                content = '\n'.join(lines[:max_lines])
                truncated = True
            else:
                truncated = False

            return {
                'path': str(full_path.relative_to(automation_path)),
                'content': content,
                'line_count': len(lines),
                'truncated': truncated
            }

        except Exception as e:
            self.logger.debug(f"Failed to read test file {test_file_path}: {e}")
            return None

    # page_objects, console_search, and element verification: populated by data-collector agent
    # (see .claude/agents/data-collector.md, Tasks 1-2)

    def _parse_stack_trace_data(
        self,
        stack_trace: Optional[str],
        error_message: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse stack trace to extract structured data for AI analysis.

        This pre-processing accelerates Phase 2 by providing:
        - Root cause file and line number
        - Extracted failing selector (if element_not_found error)
        - Test file location
        - Error type classification

        Args:
            stack_trace: Raw stack trace string
            error_message: Error message from test failure

        Returns:
            Dict with parsed data or None if parsing fails
        """
        if not stack_trace and not error_message:
            return None

        result = {
            'root_cause_file': None,
            'root_cause_line': None,
            'test_file': None,
            'test_line': None,
            'failing_selector': None,
            'error_type': None,
            'frames_count': 0,
            'user_code_frames': 0
        }

        # Parse stack trace if available
        if stack_trace:
            try:
                parsed = self.stack_parser.parse(stack_trace)

                if parsed.root_cause_frame:
                    result['root_cause_file'] = parsed.root_cause_frame.file_path
                    result['root_cause_line'] = parsed.root_cause_frame.line_number

                if parsed.test_file_frame:
                    result['test_file'] = parsed.test_file_frame.file_path
                    result['test_line'] = parsed.test_file_frame.line_number

                result['error_type'] = parsed.error_type
                result['frames_count'] = parsed.total_frames
                result['user_code_frames'] = parsed.user_code_frames

            except Exception as e:
                self.logger.debug(f"Stack trace parsing failed: {e}")

        # Extract failing selector from error message
        if error_message:
            try:
                selector = self.stack_parser.extract_failing_selector(error_message)
                if selector:
                    result['failing_selector'] = selector
            except Exception as e:
                self.logger.debug(f"Selector extraction failed: {e}")

        # Return None if nothing was extracted
        if not any([
            result['root_cause_file'],
            result['test_file'],
            result['failing_selector'],
            result['error_type'] and result['error_type'] != 'Unknown'
        ]):
            return None

        return result

    def _extract_components_from_failure(
        self,
        error_message: Optional[str],
        stack_trace: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Extract backend component names from test failure data.

        Uses ComponentExtractor to identify ACM/MCE component names in
        error messages and stack traces. These components can be used
        with the Knowledge Graph to identify cascading failures and
        dependency relationships.

        Args:
            error_message: Test failure error message
            stack_trace: Test failure stack trace

        Returns:
            List of extracted component dicts with name, subsystem, and context
        """
        extracted = self.component_extractor.extract_all_from_test_failure(
            error_message=error_message,
            stack_trace=stack_trace
        )

        if not extracted:
            return []

        result = []
        for comp in extracted:
            result.append({
                'name': comp.name,
                'subsystem': self.component_extractor.get_subsystem(comp.name),
                'source': comp.source,
                'context': comp.context[:100] if len(comp.context) > 100 else comp.context
            })

        return result

    def _save_combined_data(self, run_dir: Path):
        """Save data in multi-file structure."""
        self.logger.info("Saving gathered data...")

        # Finalize metadata
        self.gathered_data['metadata']['status'] = 'complete'
        self.gathered_data['metadata']['data_version'] = '4.0.0'

        # Mask sensitive data
        masked_data = self._mask_sensitive_data(self.gathered_data)

        # Build core-data.json
        core_data = {
            'metadata': masked_data.get('metadata', {}),
            'jenkins': masked_data.get('jenkins', {}),
            'test_report': masked_data.get('test_report', {}),
            'console_log': masked_data.get('console_log', {}),
            'environment': masked_data.get('environment', {}),
            'cluster_health': masked_data.get('cluster_health', {}),
            'repositories': masked_data.get('repositories', {}),
            'cluster_landscape': masked_data.get('cluster_landscape', {}),
            'feature_grounding': masked_data.get('feature_grounding', {}),
            'feature_knowledge': masked_data.get('feature_knowledge', {}),
            'cluster_access': masked_data.get('cluster_access', {}),
            'cluster_oracle': masked_data.get('cluster_oracle', {}),
            'errors': masked_data.get('errors', []),
        }

        # Save core-data.json
        core_path = run_dir / 'core-data.json'
        core_path.write_text(json.dumps(core_data, indent=2, default=str))

        # Save manifest.json
        manifest = self._build_manifest(run_dir)
        manifest_path = run_dir / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

        self.logger.info(f"Saved core-data.json and manifest.json")
        self.logger.info("Credentials have been masked in output files")

    def _build_manifest(self, run_dir: Path) -> Dict[str, Any]:
        """Build manifest.json index file."""
        manifest = {
            'version': '4.0.0',
            'file_structure': 'multi-file-with-repos',
            'created_at': datetime.now().isoformat(),
            'acm_ui_mcp_available': True,  # Always available via Claude Code native MCP
            'files': {
                'core-data.json': {
                    'description': 'Primary analysis data (metadata, jenkins, test_report, console_log, environment, feature_knowledge)',
                    'required': True,
                    'load_first': True
                }
            },
            'repositories': {
                'repos/automation/': {
                    'description': 'Full cloned automation repository - AI can read any file',
                    'use_case': 'Read test files, trace imports, check selector definitions'
                },
                'repos/console/': {
                    'description': 'Full cloned console repository - AI can search for elements',
                    'use_case': 'Check if elements exist, find new selectors'
                },
                'repos/kubevirt-plugin/': {
                    'description': 'KubeVirt plugin repository - virtualization UI components (cloned only for VM tests)',
                    'use_case': 'Check virtualization-specific UI elements, find VM-related selectors'
                }
            },
            'workflow': [
                '1. Read core-data.json for failure context',
                '2. Navigate to repos/automation/ and read failed test files',
                '4. Trace imports, understand test logic',
                '5. Check repos/console/ for element existence',
                '6. For VM tests, also check repos/kubevirt-plugin/ for virtualization UI',
                '7. Cross-reference with console_log errors',
                '8. Classify each test as PRODUCT_BUG, AUTOMATION_BUG, or INFRASTRUCTURE',
                '9. Save analysis-results.json'
            ]
        }

        return manifest

    # _build_ai_instructions removed in v4.0 — Stage 2 reads instructions
    # from .claude/agents/analysis.md, not from embedded core-data.json.
    # The embedded instructions were a legacy artifact from v2.5 that drifted
    # from the authoritative agent definition and could confuse the AI.



def gather_all_data(jenkins_url: str, output_dir: str = './runs',
                    verbose: bool = False) -> Tuple[Path, Dict[str, Any]]:
    """Convenience function to gather all data."""
    gatherer = DataGatherer(output_dir=output_dir, verbose=verbose)
    return gatherer.gather_all(jenkins_url)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Z-Stream Analysis - Data Gathering Script (v4.0)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script gathers FACTUAL DATA and clones repos for AI analysis.
NO classification is performed - AI handles all classification.

Key Features (v4.0):
  - 9-step deterministic pipeline
  - Dynamic MCH namespace discovery
  - Complete context extraction upfront
  - Feature area grounding with 14 diagnostic traps
  - Component extraction for Knowledge Graph

Output Files:
  core-data.json         Primary data for AI (read this first)
  manifest.json          File index with workflow instructions
  cluster.kubeconfig     Persisted cluster auth for Stage 1.5 and Stage 2
  repos/automation/      Full cloned automation repository
  repos/console/         Full cloned console repository
  console-log.txt        Full console output
  jenkins-build-info.json
  test-report.json

Examples:
  python -m src.scripts.gather https://jenkins.example.com/job/pipeline/123/
  python -m src.scripts.gather --url https://jenkins.example.com/job/pipeline/123/ --verbose
        """
    )

    parser.add_argument('url', nargs='?', help='Jenkins build URL')
    parser.add_argument('--url', '-u', dest='url_flag', help='Jenkins build URL (alternative)')
    parser.add_argument('--output-dir', '-o', default='./runs', help='Output directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--skip-env', action='store_true', help='Skip environment validation')
    parser.add_argument('--skip-repo', action='store_true', help='Skip repository cloning')

    args = parser.parse_args()

    jenkins_url = args.url or args.url_flag

    if not jenkins_url:
        parser.print_help()
        print("\nError: Jenkins URL is required", file=sys.stderr)
        sys.exit(1)

    if '/job/' not in jenkins_url:
        print(f"Error: Invalid Jenkins URL: {jenkins_url}", file=sys.stderr)
        sys.exit(1)

    try:
        gatherer = DataGatherer(output_dir=args.output_dir, verbose=args.verbose)
        run_dir, data = gatherer.gather_all(
            jenkins_url,
            skip_environment=args.skip_env,
            skip_repository=args.skip_repo
        )

        # Stage 1 completion summary
        print(f"\n{'=' * 60}")
        print(f"  STAGE 1: DATA GATHERING COMPLETE")
        print(f"{'=' * 60}")
        print(f"  Output: {run_dir}")

        # Key stats
        test_report = data.get('test_report', {})
        summary = test_report.get('summary', {})
        if summary.get('total_tests', 0) > 0:
            print(f"  Tests: {summary.get('total_tests', 0)} total, "
                  f"{summary.get('failed_count', 0)} failed "
                  f"({summary.get('pass_rate', 0):.0f}% pass rate)")

        gathering_time = data.get('metadata', {}).get('gathering_time_seconds', 0)
        print(f"  Duration: {gathering_time:.1f}s")

        # Cluster access status
        cluster_access = data.get('cluster_access', {})
        if cluster_access.get('kubeconfig_path'):
            print(f"  Cluster: kubeconfig persisted for Stage 2")
        elif cluster_access.get('has_credentials'):
            print(f"  Cluster: credentials found but kubeconfig not persisted")
        else:
            print(f"  Cluster: no credentials available")

        print(f"\n  Next: Stage 2 (AI Analysis) → Stage 3 (Report)")
        print(f"{'=' * 60}\n")

        sys.exit(0)

    except KeyboardInterrupt:
        print("\nGathering cancelled", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
