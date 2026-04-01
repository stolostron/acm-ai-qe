#!/usr/bin/env python3
"""
Data Gathering Script (v3.5)

Collects FACTUAL DATA from Jenkins, environment, and repository.
Clones repositories to persistent location for AI to access during analysis.
Pre-computes evidence to accelerate Stage 2 AI analysis.
Extracts complete test context upfront for systematic AI analysis.

11-step pipeline:
    Step 1:  Jenkins build info
    Step 2:  Console log
    Step 3:  Test report
    Step 4:  Environment check + cluster landscape + backend probes
    Step 5:  Environment Oracle — feature-aware dependency health (v3.5)
    Step 6:  Clone repositories
    Step 7:  Extract test context (code, selectors, imports)
    Step 8:  Feature area grounding
    Step 9:  Feature knowledge + KG dependency context
    Step 10: Element inventory
    Step 11: Investigation hints + temporal summaries

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
    - environment-status.json
    - element-inventory.json (if repos cloned)
"""

import argparse
import json
import logging
import os
import re
import shutil
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
    Data Gatherer v3.5 - Collects factual data and clones repos for AI access.

    This class performs MECHANICAL data collection only.
    NO classification or reasoning is done here - that's the AI's job.

    Gathers data in 11 steps: Jenkins info, console log, test report,
    environment + cluster landscape, environment oracle, repo cloning,
    context extraction, feature grounding, feature knowledge, element
    inventory, and investigation hints.
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
        self.knowledge_graph_client: Optional[KnowledgeGraphClient] = None
        if is_knowledge_graph_available():
            self.knowledge_graph_client = get_knowledge_graph_client()
            self.logger.info("RHACM Knowledge Graph available - dependency analysis enabled")

        # Track what we've gathered
        self.gathered_data = {}

        # Track repo paths for run directory
        self.automation_repo_path: Optional[Path] = None
        self.console_repo_path: Optional[Path] = None
        self.kubevirt_repo_path: Optional[Path] = None

        # Cache for expensive checks (avoid duplicate iterations)
        self._needs_kubevirt_repo: Optional[bool] = None

    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging (console + optional JSONL file)."""
        configure_logging(verbose=self.verbose)
        return logging.getLogger(__name__)

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

        # Create repos subdirectory
        repos_dir = run_dir / 'repos'
        repos_dir.mkdir(parents=True, exist_ok=True)

        # Initialize gathered data structure
        self.gathered_data = {
            'metadata': {
                'jenkins_url': jenkins_url,
                'gathered_at': datetime.now().isoformat(),
                'gatherer_version': '3.5.0',
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
            'element_inventory': {},  # MCP-enhanced element data
            'errors': []
        }

        total_steps = 11

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

        # Step 4: Environment check + cluster landscape + backend probes (optional)
        if not skip_environment:
            self._print_step(4, total_steps, "Checking environment & cluster landscape...")
            self._gather_environment_status(run_dir)
            self._gather_cluster_landscape()
            self._probe_backend_apis()
            # Show environment score
            env_score = self.gathered_data.get('environment', {}).get('environment_score')
            if env_score is not None:
                print(f"  Environment score: {env_score:.0%}", flush=True)
        else:
            self._print_step(4, total_steps, "Skipping environment check (--skip-env)")
            self.gathered_data['cluster_landscape'] = {'skipped': True}

        # ── STAGE 0: ENVIRONMENT ORACLE ──
        if not skip_environment:
            bind_context(stage="oracle")
            self._print_stage(0, 'ENVIRONMENT ORACLE',
                              'Feature-aware dependency health & knowledge database')
            self._print_step(5, total_steps, "Running environment oracle...")
            self._run_environment_oracle(skip_cluster=skip_environment)
            # Show oracle summary
            oracle = self.gathered_data.get('cluster_oracle', {})
            overall = oracle.get('overall_feature_health', {})
            healthy = overall.get('healthy_count', 0)
            total_deps = overall.get('total_dependencies', 0)
            issues = overall.get('blocking_issues', [])
            if total_deps > 0:
                print(f"  Dependencies: {healthy}/{total_deps} healthy", flush=True)
            for issue in issues[:3]:
                print(f"  Issue: {issue}", flush=True)
            if len(issues) > 3:
                print(f"  ... and {len(issues) - 3} more issues", flush=True)
        else:
            self._print_step(5, total_steps, "Skipping environment oracle (--skip-env)")
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

        # Step 10: Build element inventory from cloned repos (optional)
        if not skip_repository:
            self._print_step(10, total_steps, "Building element inventory...")
            self._gather_element_inventory(run_dir)
        else:
            self._print_step(10, total_steps, "Skipping element inventory (no repos)")

        # Step 11: Build investigation hints + temporal summaries
        self._print_step(11, total_steps, "Building investigation hints...")
        self._build_investigation_hints(run_dir)
        self._inject_temporal_summaries()

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
        """Create timestamped run directory."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Extract job name from URL
        job_name = "analysis"
        if '/job/' in jenkins_url:
            parts = jenkins_url.split('/job/')
            if len(parts) > 1:
                job_parts = [p.split('/')[0] for p in parts[1:] if p]
                job_name = '_'.join(job_parts)[:50]

        run_dir = self.output_dir / f"{job_name}_{timestamp}"
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
                    if detected_components:
                        test_entry['detected_components'] = detected_components

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

    def _gather_environment_status(self, run_dir: Path):
        """Gather environment/cluster status."""
        self.logger.info("Gathering environment status...")

        try:
            api_url, username, password = self._extract_cluster_credentials()

            # Persist cluster access info for Stage 2 re-authentication
            self.gathered_data['cluster_access'] = {
                'api_url': api_url,
                'username': username,
                'has_credentials': bool(api_url and username and password),
                'password': password,
                'note': 'Credentials from Jenkins parameters. Used by AI agent for Stage 2 cluster investigation.',
            }

            if api_url and username and password:
                self.logger.info(f"Validating TARGET cluster: {api_url}")
            else:
                self.logger.warning(
                    "Target cluster credentials not found. "
                    "Falling back to local kubeconfig."
                )

            result = self.env_service.validate_environment(
                namespaces=['open-cluster-management', 'openshift-operators'],
                target_api_url=api_url,
                username=username,
                password=password
            )

            env_data = self.env_service.to_dict(result)
            self.gathered_data['environment'] = env_data

            # Persist kubeconfig for Stage 2 re-authentication.
            # The env_service creates a temp kubeconfig during validation
            # but cleans it up afterwards. We create a separate persistent
            # kubeconfig so Stage 2 can authenticate without needing
            # the (now-masked) password from core-data.json.
            kubeconfig_path = None
            if api_url and username and password:
                kubeconfig_path = self._persist_cluster_kubeconfig(
                    run_dir, api_url, username, password
                )
                if kubeconfig_path:
                    # Make kubeconfig available for subsequent gather steps
                    # (cluster landscape, backend probes, oracle)
                    self.env_service.kubeconfig = kubeconfig_path
                    print(f"  Cluster kubeconfig persisted for Stage 2", flush=True)
            self.gathered_data['cluster_access']['kubeconfig_path'] = kubeconfig_path

            # Save to file
            output_path = run_dir / 'environment-status.json'
            output_path.write_text(json.dumps(env_data, indent=2, default=str))

            self.logger.info(f"Environment score: {result.environment_score:.1%}")

        except Exception as e:
            error_msg = f"Failed to gather environment status: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['errors'].append(error_msg)
            self.gathered_data['environment'] = {
                'error': error_msg,
                'cluster_connectivity': False
            }

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
            env_kubeconfig = self.env_service._temp_kubeconfig or self.env_service.kubeconfig
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

    # =========================================================================
    # Feature area to backend probe mapping
    # =========================================================================
    FEATURE_AREA_PROBE_MAP = {
        'Automation': 'ansibletower',
        'CLC': 'hub',
        'RBAC': 'username',
        'Search': 'search',
        'Console': 'authenticated',
        'GRC': 'authenticated',
        'Observability': 'hub',
        'Application': 'authenticated',
        'Virtualization': 'authenticated',
        'Infrastructure': 'hub',
    }

    def _probe_backend_apis(self):
        """
        Step 4c: Probe ACM console backend API endpoints and validate
        responses against known cluster state (v3.3).

        Runs inside the console-api pod via oc exec + curl. Each probe is
        independent — one failure does not block others. Results are stored
        in gathered_data['backend_probes'] for Stage 2 Phase B7 analysis.

        Probes:
        - /authenticated: auth health check (baseline)
        - /hub: hub metadata (name, observability, self-managed)
        - /username: current user identity
        - /ansibletower: Ansible template list (if AAP installed)
        - /proxy/search: search API health (basic Pod query)
        """
        self.logger.info("Probing backend APIs...")

        # Check if we have cluster access
        cluster_access = self.gathered_data.get('cluster_access', {})
        if not cluster_access.get('has_credentials'):
            self.logger.info("No cluster credentials — skipping backend probes")
            self.gathered_data['backend_probes'] = {
                'skipped': True,
                'reason': 'no_cluster_credentials',
                'total_anomalies': 0,
            }
            return

        probes_result = {
            'probe_timestamp': datetime.now().isoformat(),
            'total_anomalies': 0,
        }

        try:
            cli = self.cluster_investigation_service.cli
            kubeconfig_args = []
            if self.cluster_investigation_service.kubeconfig:
                kubeconfig_args = [
                    '--kubeconfig',
                    self.cluster_investigation_service.kubeconfig,
                ]

            # Find a running console-api pod
            pod_name = self._find_console_api_pod(cli, kubeconfig_args)
            if not pod_name:
                self.logger.warning("Console-api pod not found — skipping backend probes")
                probes_result['skipped'] = True
                probes_result['reason'] = 'console_api_pod_not_found'
                self.gathered_data['backend_probes'] = probes_result
                return

            # Get bearer token for API calls
            token = self._get_bearer_token(cli, kubeconfig_args)
            if not token:
                self.logger.warning("Could not get bearer token — skipping backend probes")
                probes_result['skipped'] = True
                probes_result['reason'] = 'no_bearer_token'
                self.gathered_data['backend_probes'] = probes_result
                return

            namespace = 'open-cluster-management'
            landscape = self.gathered_data.get('cluster_landscape', {})

            # Run each probe independently
            probes_result['authenticated'] = self._probe_authenticated(
                cli, kubeconfig_args, pod_name, namespace, token
            )
            probes_result['hub'] = self._probe_hub(
                cli, kubeconfig_args, pod_name, namespace, token, landscape
            )
            probes_result['username'] = self._probe_username(
                cli, kubeconfig_args, pod_name, namespace, token
            )
            probes_result['ansibletower'] = self._probe_ansibletower(
                cli, kubeconfig_args, pod_name, namespace, token, landscape
            )
            probes_result['search'] = self._probe_search(
                cli, kubeconfig_args, pod_name, namespace, token
            )

            # Source-of-truth validation (v3.4): for each probe with
            # anomalies, query the Kubernetes API directly to determine
            # whether the anomaly originates in the console backend code
            # (PRODUCT_BUG) or in the upstream cluster (INFRASTRUCTURE).
            self._validate_probes_against_cluster(
                cli, kubeconfig_args, namespace, probes_result
            )

            # Count total anomalies
            total = 0
            for key in ('authenticated', 'hub', 'username', 'ansibletower', 'search'):
                probe = probes_result.get(key, {})
                total += len([a for a in probe.get('anomalies', [])
                              if a.get('is_anomaly', True)])
            probes_result['total_anomalies'] = total

            if total > 0:
                self.logger.warning(f"Backend probes found {total} anomalies")
            else:
                self.logger.info("Backend probes: all endpoints healthy")

        except Exception as e:
            error_msg = f"Backend probe error: {e}"
            self.logger.warning(error_msg)
            probes_result['error'] = error_msg

        self.gathered_data['backend_probes'] = probes_result

    def _find_console_api_pod(
        self, cli: str, kubeconfig_args: List[str]
    ) -> Optional[str]:
        """Find a running console-api pod name."""
        cmd = [
            cli, *kubeconfig_args,
            'get', 'pods', '-n', 'open-cluster-management',
            '-l', 'app=console-chart-console-v2,component=console',
            '--field-selector=status.phase=Running',
            '-o', 'jsonpath={.items[0].metadata.name}',
            '--ignore-not-found',
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            pod = result.stdout.strip().strip("'")
            if pod and result.returncode == 0:
                self.logger.info(f"Console API pod: {pod}")
                return pod
        except Exception as e:
            self.logger.debug(f"Console pod lookup failed: {e}")

        # Fallback: try name-based match
        cmd = [
            cli, *kubeconfig_args,
            'get', 'pods', '-n', 'open-cluster-management',
            '--field-selector=status.phase=Running',
            '-o', 'jsonpath={.items[*].metadata.name}',
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                for name in result.stdout.split():
                    if 'console' in name:
                        self.logger.info(f"Console pod (fallback): {name}")
                        return name
        except Exception as e:
            self.logger.debug(f"Console pod fallback failed: {e}")

        return None

    def _get_bearer_token(
        self, cli: str, kubeconfig_args: List[str]
    ) -> Optional[str]:
        """Get bearer token from current oc session."""
        cmd = [cli, *kubeconfig_args, 'whoami', '-t']
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception as e:
            self.logger.debug(f"Token retrieval failed: {e}")
        return None

    def _exec_curl_in_pod(
        self,
        cli: str,
        kubeconfig_args: List[str],
        pod_name: str,
        namespace: str,
        token: str,
        path: str,
        method: str = 'GET',
        data: Optional[str] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """Execute a curl command inside the console pod."""
        curl_cmd = (
            f"curl -sk https://localhost:3000{path} "
            f"-H 'Authorization: Bearer {token}' "
            f"--max-time {timeout} -w '\\n%{{http_code}}\\n%{{time_total}}'"
        )
        if method == 'POST' and data:
            curl_cmd += f" -X POST -H 'Content-Type: application/json' -d '{data}'"

        cmd = [
            cli, *kubeconfig_args,
            'exec', pod_name, '-n', namespace, '--', 'sh', '-c', curl_cmd,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 15
            )
            if result.returncode != 0:
                return {
                    'status': 'error',
                    'error': result.stderr.strip()[:200],
                    'response': None,
                }

            lines = result.stdout.strip().rsplit('\n', 2)
            if len(lines) >= 3:
                body = '\n'.join(lines[:-2])
                status_code = int(lines[-2])
                response_time = float(lines[-1])
            elif len(lines) == 2:
                body = lines[0]
                status_code = int(lines[1]) if lines[1].isdigit() else 0
                response_time = 0.0
            else:
                body = result.stdout.strip()
                status_code = 0
                response_time = 0.0

            parsed = None
            if body.strip():
                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError:
                    parsed = body[:500]

            return {
                'status': status_code,
                'response_time_ms': int(response_time * 1000),
                'response': parsed,
            }
        except subprocess.TimeoutExpired:
            return {
                'status': 'timeout',
                'error': f'curl timed out after {timeout}s',
                'response': None,
                'response_time_ms': timeout * 1000,
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)[:200],
                'response': None,
            }

    def _probe_authenticated(
        self, cli, kubeconfig_args, pod_name, namespace, token
    ) -> Dict[str, Any]:
        """Probe /authenticated — baseline health check."""
        probe = self._exec_curl_in_pod(
            cli, kubeconfig_args, pod_name, namespace, token, '/authenticated'
        )
        anomalies = []

        if isinstance(probe.get('status'), int) and probe['status'] == 200:
            response_time = probe.get('response_time_ms', 0)
            if response_time > 5000:
                anomalies.append({
                    'field': 'response_time',
                    'expected': '<5000ms',
                    'actual': f'{response_time}ms',
                    'description': 'Console backend slow response',
                    'is_anomaly': True,
                })
        elif probe.get('status') == 'timeout':
            anomalies.append({
                'field': 'response',
                'description': 'Console backend did not respond — possible crash or resource issue',
                'is_anomaly': True,
            })
        elif probe.get('status') == 'error':
            anomalies.append({
                'field': 'response',
                'description': f"Console backend error: {probe.get('error', 'unknown')}",
                'is_anomaly': True,
            })

        probe['anomalies'] = anomalies
        probe['response_valid'] = len([a for a in anomalies if a.get('is_anomaly', True)]) == 0
        return probe

    def _probe_hub(
        self, cli, kubeconfig_args, pod_name, namespace, token, landscape
    ) -> Dict[str, Any]:
        """Probe /hub — validate hub metadata against cluster landscape."""
        probe = self._exec_curl_in_pod(
            cli, kubeconfig_args, pod_name, namespace, token, '/hub'
        )
        anomalies = []
        resp = probe.get('response')

        if isinstance(resp, dict) and isinstance(probe.get('status'), int) and probe['status'] == 200:
            # Check hub name against MCH
            mch_status = landscape.get('multiclusterhub_status')
            if mch_status:
                hub_name = resp.get('localHubName', '')
                # The expected hub name is typically 'local-cluster'
                if hub_name and 'local-cluster' in hub_name and hub_name != 'local-cluster':
                    anomalies.append({
                        'field': 'localHubName',
                        'expected': 'local-cluster',
                        'actual': hub_name,
                        'description': f"Hub name has unexpected suffix: '{hub_name}'",
                        'is_anomaly': True,
                    })

            # Check isHubSelfManaged against managed cluster list
            managed_statuses = landscape.get('managed_cluster_statuses', {})
            if managed_statuses:
                has_local = landscape.get('managed_cluster_count', 0) > 0
                is_self_managed = resp.get('isHubSelfManaged')
                # This is informational, not always an anomaly
                anomalies.append({
                    'field': 'isHubSelfManaged',
                    'expected': has_local,
                    'actual': is_self_managed,
                    'description': f"Hub self-managed: {is_self_managed}",
                    'is_anomaly': False,  # informational
                })

        elif probe.get('status') in ('timeout', 'error'):
            anomalies.append({
                'field': 'response',
                'description': f"Hub probe failed: {probe.get('error', probe.get('status'))}",
                'is_anomaly': True,
            })

        probe['anomalies'] = anomalies
        probe['response_valid'] = len([a for a in anomalies if a.get('is_anomaly', True)]) == 0
        return probe

    def _probe_username(
        self, cli, kubeconfig_args, pod_name, namespace, token
    ) -> Dict[str, Any]:
        """Probe /username — validate user identity format."""
        probe = self._exec_curl_in_pod(
            cli, kubeconfig_args, pod_name, namespace, token, '/username'
        )
        anomalies = []
        resp = probe.get('response')

        if isinstance(resp, dict) and isinstance(probe.get('status'), int) and probe['status'] in (200, 201):
            body = resp.get('body', resp)
            username = body.get('username', '') if isinstance(body, dict) else str(resp.get('username', ''))

            if username:
                # Check for reversed username (kube:admin should not be admin:kube)
                if ':' in username:
                    parts = username.split(':')
                    if len(parts) == 2 and parts[0] == 'admin' and parts[1] == 'kube':
                        anomalies.append({
                            'field': 'username',
                            'expected': 'kube:admin',
                            'actual': username,
                            'description': 'Username appears reversed (expected provider:user format)',
                            'is_anomaly': True,
                        })

        elif probe.get('status') in ('timeout', 'error'):
            anomalies.append({
                'field': 'response',
                'description': f"Username probe failed: {probe.get('error', probe.get('status'))}",
                'is_anomaly': True,
            })

        probe['anomalies'] = anomalies
        probe['response_valid'] = len([a for a in anomalies if a.get('is_anomaly', True)]) == 0
        return probe

    def _probe_ansibletower(
        self, cli, kubeconfig_args, pod_name, namespace, token, landscape
    ) -> Dict[str, Any]:
        """Probe /ansibletower — validate Ansible template list against AAP status."""
        # Only probe if AAP operator is installed
        mch_components = landscape.get('mch_enabled_components', {})
        # Check if any operator related to AAP/ansible exists
        # Also check Jenkins params for tower credentials
        jenkins_params = self.gathered_data.get('jenkins', {}).get('parameters', {})
        tower_host = jenkins_params.get('TOWER_HOST') or jenkins_params.get('ANSIBLE_TOWER_HOST')

        if not tower_host:
            return {
                'status': 'skipped',
                'reason': 'no_tower_host_in_jenkins_params',
                'response': None,
                'anomalies': [],
                'response_valid': None,
            }

        probe = self._exec_curl_in_pod(
            cli, kubeconfig_args, pod_name, namespace, token, '/ansibletower'
        )
        anomalies = []
        resp = probe.get('response')

        if isinstance(resp, dict) and isinstance(probe.get('status'), int) and probe['status'] == 200:
            count = resp.get('count', -1)
            results = resp.get('results', [])

            # If AAP operator is healthy and tower host is configured,
            # the endpoint should return templates
            if count == 0 and len(results) == 0:
                anomalies.append({
                    'field': 'results',
                    'expected': 'non-empty (Tower host configured)',
                    'actual': 'empty array (count=0)',
                    'description': 'Ansible Tower returns empty results despite configured tower host',
                    'is_anomaly': True,
                })

        elif probe.get('status') in ('timeout', 'error'):
            anomalies.append({
                'field': 'response',
                'description': f"Ansible Tower probe failed: {probe.get('error', probe.get('status'))}",
                'is_anomaly': True,
            })

        probe['anomalies'] = anomalies
        probe['response_valid'] = len([a for a in anomalies if a.get('is_anomaly', True)]) == 0
        return probe

    def _probe_search(
        self, cli, kubeconfig_args, pod_name, namespace, token
    ) -> Dict[str, Any]:
        """Probe /proxy/search — validate search pipeline with basic Pod query."""
        query = json.dumps({
            "operationName": "searchResult",
            "variables": {
                "input": [{
                    "filters": [{"property": "kind", "values": ["Pod"]}],
                    "limit": 3,
                }]
            },
            "query": "query searchResult($input: [SearchInput]) { searchResult: search(input: $input) { items } }",
        })
        # Escape single quotes for shell
        query_escaped = query.replace("'", "'\\''")

        probe = self._exec_curl_in_pod(
            cli, kubeconfig_args, pod_name, namespace, token,
            '/proxy/search',
            method='POST',
            data=query_escaped,
            timeout=20,
        )
        anomalies = []
        resp = probe.get('response')

        if isinstance(resp, dict) and isinstance(probe.get('status'), int) and probe['status'] == 200:
            search_results = resp.get('data', {}).get('searchResult', [])
            if search_results:
                items = search_results[0].get('items', [])
                if len(items) == 0:
                    anomalies.append({
                        'field': 'items',
                        'expected': 'at least 1 Pod',
                        'actual': 'empty array',
                        'description': 'Search API returns no Pods on a running cluster — search pipeline may be broken',
                        'is_anomaly': True,
                    })
            else:
                anomalies.append({
                    'field': 'searchResult',
                    'expected': 'non-empty searchResult array',
                    'actual': 'empty or missing',
                    'description': 'Search API returned no searchResult data',
                    'is_anomaly': True,
                })

        elif probe.get('status') == 'timeout':
            anomalies.append({
                'field': 'response',
                'description': 'Search API did not respond within 20s — possible search pipeline issue',
                'is_anomaly': True,
            })
        elif probe.get('status') == 'error':
            anomalies.append({
                'field': 'response',
                'description': f"Search probe failed: {probe.get('error', 'unknown')}",
                'is_anomaly': True,
            })

        probe['anomalies'] = anomalies
        probe['response_valid'] = len([a for a in anomalies if a.get('is_anomaly', True)]) == 0
        return probe

    # ------------------------------------------------------------------
    # Source-of-truth validation (v3.4)
    # ------------------------------------------------------------------

    def _validate_probes_against_cluster(
        self,
        cli: str,
        kubeconfig_args: List[str],
        namespace: str,
        probes_result: Dict[str, Any],
    ):
        """
        Cross-reference probe anomalies against Kubernetes API ground truth.

        For each probe with anomalies, query the same data directly from the
        Kubernetes API (bypassing the console backend). If the cluster returns
        correct data but the console returns different data, the anomaly
        originates in the console backend code (PRODUCT_BUG). If both return
        the same anomalous data, the issue is upstream (INFRASTRUCTURE).

        Enriches each probe dict with:
          - cluster_ground_truth: raw data from K8s API
          - anomaly_source: 'console_backend' | 'upstream' | 'unknown'
          - classification_hint: 'PRODUCT_BUG' | 'INFRASTRUCTURE' | None
        """
        self.logger.info("Validating probe anomalies against cluster ground truth...")

        # /username validation
        username_probe = probes_result.get('username', {})
        has_username_anomaly = any(
            a.get('is_anomaly') for a in username_probe.get('anomalies', [])
        )
        if has_username_anomaly:
            self._validate_username_probe(
                cli, kubeconfig_args, username_probe
            )

        # /hub validation
        hub_probe = probes_result.get('hub', {})
        has_hub_anomaly = any(
            a.get('is_anomaly') for a in hub_probe.get('anomalies', [])
        )
        if has_hub_anomaly:
            self._validate_hub_probe(
                cli, kubeconfig_args, namespace, hub_probe
            )

        # /ansibletower validation
        tower_probe = probes_result.get('ansibletower', {})
        has_tower_anomaly = any(
            a.get('is_anomaly') for a in tower_probe.get('anomalies', [])
        )
        if has_tower_anomaly:
            self._validate_ansibletower_probe(
                cli, kubeconfig_args, tower_probe
            )

        # /authenticated validation
        auth_probe = probes_result.get('authenticated', {})
        has_auth_anomaly = any(
            a.get('is_anomaly') for a in auth_probe.get('anomalies', [])
        )
        if has_auth_anomaly:
            self._validate_authenticated_probe(
                cli, kubeconfig_args, auth_probe
            )

        # /proxy/search validation
        search_probe = probes_result.get('search', {})
        has_search_anomaly = any(
            a.get('is_anomaly') for a in search_probe.get('anomalies', [])
        )
        if has_search_anomaly:
            self._validate_search_probe(
                cli, kubeconfig_args, namespace, search_probe
            )

    def _run_oc_command(
        self, cli: str, kubeconfig_args: List[str], args: List[str],
        timeout: int = 10,
    ) -> Optional[str]:
        """Run an oc command and return stdout, or None on failure."""
        cmd = [cli, *kubeconfig_args, *args]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def _validate_username_probe(
        self, cli, kubeconfig_args, probe,
    ):
        """Validate /username anomaly against oc whoami."""
        cluster_user = self._run_oc_command(cli, kubeconfig_args, ['whoami'])
        if cluster_user is None:
            probe['cluster_ground_truth'] = None
            probe['anomaly_source'] = 'unknown'
            probe['classification_hint'] = None
            return

        probe['cluster_ground_truth'] = {'username': cluster_user}

        # Extract console username from probe response
        resp = probe.get('response', {})
        if isinstance(resp, dict):
            body = resp.get('body', resp)
            console_user = (
                body.get('username', '') if isinstance(body, dict)
                else str(resp.get('username', ''))
            )
        else:
            console_user = ''

        if cluster_user and console_user and cluster_user != console_user:
            probe['anomaly_source'] = 'console_backend'
            probe['classification_hint'] = 'PRODUCT_BUG'
            self.logger.info(
                f"Username validation: cluster='{cluster_user}', "
                f"console='{console_user}' -> PRODUCT_BUG"
            )
        elif cluster_user == console_user:
            probe['anomaly_source'] = 'upstream'
            probe['classification_hint'] = 'INFRASTRUCTURE'
        else:
            probe['anomaly_source'] = 'unknown'
            probe['classification_hint'] = None

    def _validate_hub_probe(
        self, cli, kubeconfig_args, namespace, probe,
    ):
        """Validate /hub anomaly against MCH and ManagedCluster resources."""
        # Try to get the authoritative hub name from the local-cluster
        # ManagedCluster resource
        hub_name = self._run_oc_command(
            cli, kubeconfig_args,
            ['get', 'managedcluster', 'local-cluster',
             '-o', 'jsonpath={.metadata.name}'],
        )
        if hub_name is None:
            probe['cluster_ground_truth'] = None
            probe['anomaly_source'] = 'unknown'
            probe['classification_hint'] = None
            return

        probe['cluster_ground_truth'] = {'hubClusterName': hub_name}

        resp = probe.get('response', {})
        console_hub = resp.get('localHubName', '') if isinstance(resp, dict) else ''

        if hub_name and console_hub and hub_name != console_hub:
            probe['anomaly_source'] = 'console_backend'
            probe['classification_hint'] = 'PRODUCT_BUG'
            self.logger.info(
                f"Hub validation: cluster='{hub_name}', "
                f"console='{console_hub}' -> PRODUCT_BUG"
            )
        elif hub_name == console_hub:
            probe['anomaly_source'] = 'upstream'
            probe['classification_hint'] = 'INFRASTRUCTURE'
        else:
            probe['anomaly_source'] = 'unknown'
            probe['classification_hint'] = None

    def _validate_ansibletower_probe(
        self, cli, kubeconfig_args, probe,
    ):
        """Validate /ansibletower anomaly against AAP operator status."""
        # Check if AAP operator CSV is installed and healthy
        csv_output = self._run_oc_command(
            cli, kubeconfig_args,
            ['get', 'csv', '-A', '-o',
             'jsonpath={range .items[*]}{.metadata.name} {.status.phase}{"\\n"}{end}'],
            timeout=15,
        )
        aap_status = None
        if csv_output:
            for line in csv_output.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 2:
                    name_lower = parts[0].lower()
                    if any(k in name_lower for k in ('aap', 'ansible', 'automation-platform')):
                        aap_status = parts[1]
                        break

        probe['cluster_ground_truth'] = {
            'aap_operator_status': aap_status or 'not_found',
            'aap_healthy': aap_status == 'Succeeded',
        }

        resp = probe.get('response', {})
        console_count = resp.get('count', -1) if isinstance(resp, dict) else -1

        if aap_status == 'Succeeded' and console_count == 0:
            # AAP is healthy but console returns empty -> console code issue
            probe['anomaly_source'] = 'console_backend'
            probe['classification_hint'] = 'PRODUCT_BUG'
            self.logger.info(
                "Ansible validation: AAP operator Succeeded but "
                "console returns 0 templates -> PRODUCT_BUG"
            )
        elif aap_status != 'Succeeded':
            # AAP is not healthy -> empty response is expected
            probe['anomaly_source'] = 'upstream'
            probe['classification_hint'] = 'INFRASTRUCTURE'
            # Clear the anomaly — empty results are expected when AAP is down
            for anomaly in probe.get('anomalies', []):
                if anomaly.get('field') == 'results':
                    anomaly['is_anomaly'] = False
                    anomaly['description'] += ' (AAP operator not healthy — expected)'
        else:
            probe['anomaly_source'] = 'unknown'
            probe['classification_hint'] = None

    def _validate_authenticated_probe(
        self, cli, kubeconfig_args, probe,
    ):
        """Validate /authenticated anomaly against oc whoami."""
        cluster_auth = self._run_oc_command(cli, kubeconfig_args, ['whoami'])
        probe['cluster_ground_truth'] = {
            'oc_whoami_works': cluster_auth is not None,
        }

        if cluster_auth is not None:
            # Cluster auth works but console auth has issues -> console code
            probe['anomaly_source'] = 'console_backend'
            probe['classification_hint'] = 'PRODUCT_BUG'
        else:
            # Cluster auth also fails -> infrastructure issue
            probe['anomaly_source'] = 'upstream'
            probe['classification_hint'] = 'INFRASTRUCTURE'

    def _validate_search_probe(
        self, cli, kubeconfig_args, namespace, probe,
    ):
        """Validate /proxy/search anomaly against search-api deployment."""
        ready = self._run_oc_command(
            cli, kubeconfig_args,
            ['get', 'deploy', 'search-v2-operator-controller-manager',
             '-n', namespace,
             '-o', 'jsonpath={.status.readyReplicas}'],
        )
        # Fallback: try search-api directly
        if ready is None:
            ready = self._run_oc_command(
                cli, kubeconfig_args,
                ['get', 'deploy', '-n', namespace, '-l', 'app=search',
                 '-o', 'jsonpath={.items[0].status.readyReplicas}'],
            )

        probe['cluster_ground_truth'] = {
            'search_ready_replicas': int(ready) if ready and ready.isdigit() else None,
        }

        if ready and ready.isdigit() and int(ready) > 0:
            # Search pods are running but console returns empty/error
            probe['anomaly_source'] = 'console_backend'
            probe['classification_hint'] = 'PRODUCT_BUG'
            self.logger.info(
                f"Search validation: {ready} ready replicas but "
                "console search returns empty -> PRODUCT_BUG"
            )
        elif ready is None or (ready.isdigit() and int(ready) == 0):
            # Search pods are down -> infrastructure issue
            probe['anomaly_source'] = 'upstream'
            probe['classification_hint'] = 'INFRASTRUCTURE'
        else:
            probe['anomaly_source'] = 'unknown'
            probe['classification_hint'] = None

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
        Step 5: Run Environment Oracle (v3.5) — feature-aware dependency health.

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
            dep_health = oracle_result.get('dependency_health', {})
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
            acm_version = params.get('DOWNSTREAM_RELEASE')
            if not acm_version:
                landscape = self.gathered_data.get('cluster_landscape', {})
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
            landscape = self.gathered_data.get('cluster_landscape', {})
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

                # Get readiness (pass oracle data to resolve addon/operator/crd)
                oracle_data = self.gathered_data.get('cluster_oracle', {})
                readiness = self.feature_knowledge_service.get_feature_readiness(
                    area,
                    mch_components=mch_components,
                    cluster_landscape=landscape,
                    error_messages=area_errors,
                    oracle_data=oracle_data,
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

            # Build feature_knowledge section
            self.gathered_data['feature_knowledge'] = {
                'acm_version': acm_version,
                'profiles_loaded': list(profiles.keys()),
                'feature_readiness': feature_readiness,
                'investigation_playbooks': investigation_playbooks,
                'kg_dependency_context': kg_dependency_context,
                'kg_status': kg_status,
            }

            # Log summary
            self.logger.info(
                f"Loaded {len(profiles)} playbooks for: "
                f"{', '.join(profiles.keys())}"
            )
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

        This method runs AFTER repos are cloned and provides AI with
        all needed context upfront, eliminating on-demand file reads.

        For each failing test, extracts:
        - Test file content (the actual test code)
        - Page object/selector definitions (imported files)
        - Console repo search results for failing selectors
        - Similar selectors if exact match not found

        This enables systematic AI analysis without repo access.
        """
        self.logger.info("Extracting complete test context for AI analysis...")

        test_report = self.gathered_data.get('test_report', {})
        failed_tests = test_report.get('failed_tests', [])

        if not failed_tests:
            self.logger.info("No failed tests - skipping context extraction")
            return

        repos_dir = run_dir / 'repos'
        automation_path = repos_dir / 'automation'
        console_path = repos_dir / 'console'

        # Pre-compute selector changes from git diff (runs once, cached for all tests)
        selector_changes_cache = None
        if console_path.exists() and hasattr(self, 'timeline_service') and self.timeline_service:
            self.timeline_service.console_path = console_path
            selector_changes_cache = self.timeline_service.find_recent_selector_changes(
                lookback_commits=200
            )
            self.logger.info(
                f"Selector diff: {selector_changes_cache.get('total_files_with_changes', 0)} "
                f"files with changes in last 200 commits"
            )

        for i, test in enumerate(failed_tests):
            test_name = test.get('test_name', '')
            parsed_stack = test.get('parsed_stack_trace', {})

            self.logger.debug(f"Extracting context for: {test_name}")

            extracted_context = {
                'test_file': None,
                'page_objects': [],
                'console_search': None,
                'recent_selector_changes': None,
            }

            # 1. Extract test file content
            test_file_path = parsed_stack.get('root_cause_file') or parsed_stack.get('test_file')
            if test_file_path and automation_path.exists():
                test_content = self._read_test_file(automation_path, test_file_path)
                if test_content:
                    extracted_context['test_file'] = test_content

            # 2. Extract page object definitions (imports with selectors)
            if extracted_context['test_file'] and automation_path.exists():
                page_objects = self._extract_page_objects(
                    automation_path,
                    extracted_context['test_file'].get('content', ''),
                    parsed_stack.get('failing_selector')
                )
                if page_objects:
                    extracted_context['page_objects'] = page_objects

            # 3. Search console repo for failing selector
            failing_selector = parsed_stack.get('failing_selector')
            if failing_selector and console_path.exists():
                console_search = self._search_console_for_selector(
                    console_path,
                    failing_selector
                )
                extracted_context['console_search'] = console_search

                # Also search kubevirt if it's a VM test
                if self.kubevirt_repo_path and self.kubevirt_repo_path.exists():
                    kubevirt_search = self._search_console_for_selector(
                        self.kubevirt_repo_path,
                        failing_selector
                    )
                    if kubevirt_search.get('found') or kubevirt_search.get('similar_selectors'):
                        extracted_context['kubevirt_search'] = kubevirt_search

            # 4. Cross-reference failing selector against recent git diff changes
            if failing_selector and selector_changes_cache and self.timeline_service:
                xref = self.timeline_service.cross_reference_selector(
                    failing_selector, selector_changes_cache
                )
                extracted_context['recent_selector_changes'] = xref

            # 5. Extract assertion values from error message
            error_message = test.get('error_message', '')
            if error_message:
                assertion_values = self.stack_parser.extract_assertion_values(error_message)
                if assertion_values:
                    extracted_context['assertion_analysis'] = assertion_values

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

    def _extract_page_objects(
        self,
        automation_path: Path,
        test_content: str,
        failing_selector: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Extract page object definitions from imported files.

        Finds imports in the test file and extracts selector definitions.

        Args:
            automation_path: Path to automation repo
            test_content: Content of the test file
            failing_selector: The selector that failed (to highlight)

        Returns:
            List of page object dicts with path and relevant content
        """
        page_objects = []

        try:
            # Find import statements
            import_pattern = r"import\s+.*?from\s+['\"]([^'\"]+)['\"]"
            imports = re.findall(import_pattern, test_content)

            # Focus on views/ imports (where selectors usually live)
            view_imports = [
                imp for imp in imports
                if 'views' in imp or 'selectors' in imp or 'page' in imp.lower()
            ]

            for import_path in view_imports[:5]:  # Limit to 5 imports
                # Resolve the import path
                if import_path.startswith('.'):
                    # Relative import - skip for now (complex resolution)
                    continue

                # Try common locations
                possible_paths = [
                    automation_path / 'cypress' / 'views' / f"{import_path.split('/')[-1]}.js",
                    automation_path / 'cypress' / 'views' / f"{import_path.split('/')[-1]}.ts",
                    automation_path / 'cypress' / 'support' / f"{import_path.split('/')[-1]}.js",
                ]

                for path in possible_paths:
                    if path.exists():
                        content = path.read_text(encoding='utf-8', errors='ignore')

                        # If we have a failing selector, extract only relevant parts
                        if failing_selector:
                            relevant_lines = self._extract_relevant_lines(
                                content, failing_selector
                            )
                        else:
                            # Just take first 50 lines
                            relevant_lines = '\n'.join(content.split('\n')[:50])

                        page_objects.append({
                            'path': str(path.relative_to(automation_path)),
                            'content': relevant_lines,
                            'contains_failing_selector': failing_selector in content if failing_selector else False
                        })
                        break

        except Exception as e:
            self.logger.debug(f"Failed to extract page objects: {e}")

        return page_objects

    def _extract_relevant_lines(
        self,
        content: str,
        selector: str,
        context_lines: int = 5
    ) -> str:
        """
        Extract lines relevant to a selector with context.

        Args:
            content: File content
            selector: Selector to find
            context_lines: Number of lines before/after to include

        Returns:
            Relevant lines as string
        """
        lines = content.split('\n')
        relevant = []

        # Find lines containing the selector
        for i, line in enumerate(lines):
            if selector in line or (selector.startswith('#') and selector[1:] in line):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                relevant.extend(lines[start:end])
                relevant.append('---')  # Separator

        if relevant:
            return '\n'.join(relevant)
        else:
            # Return first 30 lines if selector not found
            return '\n'.join(lines[:30])

    def _search_console_for_selector(
        self,
        console_path: Path,
        selector: str
    ) -> Dict[str, Any]:
        """
        Search the console repo for a selector.

        Args:
            console_path: Path to console repo
            selector: Selector to search for (e.g., '#create-btn' or 'create-btn')

        Returns:
            Dict with search results including found status, locations, and similar selectors
        """
        result = {
            'selector': selector,
            'found': False,
            'locations': [],
            'similar_selectors': []
        }

        try:
            # Normalize selector - remove # prefix for search
            search_term = selector.lstrip('#').lstrip('.')

            # Search using grep
            search_dirs = [
                console_path / 'frontend' / 'src',
                console_path / 'src',  # fallback for kubevirt-plugin
            ]

            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue

                # Use grep to find the selector
                try:
                    grep_result = self._run_grep(search_dir, search_term)
                    if grep_result:
                        result['found'] = True
                        result['locations'] = grep_result[:10]  # Limit to 10 matches
                        break
                except Exception:
                    pass

            # If not found, search for similar selectors
            if not result['found'] and len(search_term) > 3:
                # Try partial match
                partial_term = search_term[:len(search_term)//2]
                for search_dir in search_dirs:
                    if not search_dir.exists():
                        continue
                    try:
                        similar = self._run_grep(search_dir, partial_term)
                        if similar:
                            # Extract just the selector-like strings
                            similar_selectors = self._extract_similar_selectors(
                                similar, search_term
                            )
                            result['similar_selectors'] = similar_selectors[:5]
                            break
                    except Exception:
                        pass

        except Exception as e:
            self.logger.debug(f"Failed to search console for {selector}: {e}")
            result['error'] = str(e)

        return result

    def _run_grep(
        self,
        search_dir: Path,
        term: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Run grep to find a term in a directory.

        Args:
            search_dir: Directory to search
            term: Term to search for
            max_results: Maximum results to return

        Returns:
            List of match dicts with file, line, and content
        """
        results = []

        try:
            # Use grep with line numbers
            cmd = [
                'grep', '-rn', '--include=*.tsx', '--include=*.ts',
                '--include=*.jsx', '--include=*.js',
                term, str(search_dir)
            ]

            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            for line in proc.stdout.split('\n')[:max_results]:
                if not line.strip():
                    continue

                # Parse grep output: file:line:content
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    file_path = parts[0]
                    line_num = parts[1]
                    content = parts[2].strip()

                    # Make path relative
                    try:
                        rel_path = Path(file_path).relative_to(search_dir.parent)
                    except ValueError:
                        rel_path = Path(file_path).name

                    results.append({
                        'file': str(rel_path),
                        'line': int(line_num) if line_num.isdigit() else 0,
                        'content': content[:200]  # Limit content length
                    })

        except subprocess.TimeoutExpired:
            self.logger.debug(f"Grep timed out for {term}")
        except Exception as e:
            self.logger.debug(f"Grep failed: {e}")

        return results

    def _extract_similar_selectors(
        self,
        grep_results: List[Dict[str, Any]],
        original_term: str
    ) -> List[str]:
        """
        Extract selector-like strings from grep results that are similar to the original.

        Args:
            grep_results: List of grep match dicts
            original_term: The original selector we're looking for

        Returns:
            List of similar selector strings
        """
        similar = set()

        # Patterns for extracting selectors
        patterns = [
            r'data-testid=["\']([^"\']+)["\']',
            r'data-test=["\']([^"\']+)["\']',
            r'id=["\']([^"\']+)["\']',
            r'#([a-zA-Z][a-zA-Z0-9_-]+)',
        ]

        for result in grep_results:
            content = result.get('content', '')
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Check if it's similar to original
                    if self._is_similar(match, original_term):
                        similar.add(match)

        return list(similar)

    def _is_similar(self, s1: str, s2: str, threshold: float = 0.5) -> bool:
        """
        Check if two strings are similar using simple ratio.

        Args:
            s1, s2: Strings to compare
            s2: Second string
            threshold: Similarity threshold (0-1)

        Returns:
            True if strings are similar
        """
        s1 = s1.lower()
        s2 = s2.lower()

        # Quick check for substring
        if s1 in s2 or s2 in s1:
            return True

        # Simple character overlap ratio
        common = len(set(s1) & set(s2))
        total = len(set(s1) | set(s2))

        if total == 0:
            return False

        return (common / total) >= threshold

    @staticmethod
    def _classify_selector_type(selector: str) -> str:
        """
        Classify a selector into a type category.

        Categories:
        - id: starts with # (e.g., #create-btn)
        - css_class: starts with . (e.g., .my-class)
        - patternfly_class: PatternFly class (pf-v5-*, pf-v6-*, pf-c-*, pf-m-*, pf-l-*, pf-u-*)
        - attribute: bracket notation (e.g., [data-testid="x"])
        - text: plain text without selector prefix
        - unknown: empty or unrecognized

        Args:
            selector: The selector string

        Returns:
            Classification string
        """
        if not selector or not selector.strip():
            return 'unknown'

        selector = selector.strip()

        # Check PatternFly class patterns (before generic css_class)
        pf_prefixes = ('pf-v5-', 'pf-v6-', 'pf-c-', 'pf-m-', 'pf-l-', 'pf-u-')
        bare = selector.lstrip('.')
        if bare.startswith(pf_prefixes):
            return 'patternfly_class'

        if selector.startswith('#'):
            return 'id'
        if selector.startswith('.'):
            return 'css_class'
        if selector.startswith('['):
            return 'attribute'

        # Plain text selector (no prefix character)
        if re.match(r'^[a-zA-Z]', selector):
            return 'text'

        return 'unknown'

    def _extract_test_ids_from_file(
        self,
        file_path: Path,
        max_ids: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Extract data-testid, data-test-id, data-test, testId, and aria-label
        attributes from a source file.

        Args:
            file_path: Absolute path to the source file
            max_ids: Maximum number of IDs to return

        Returns:
            List of dicts with attribute, value, file, and line
        """
        results = []

        if not file_path.exists():
            return results

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')

            patterns = [
                (r'data-testid=["\']([^"\']+)["\']', 'data-testid'),
                (r'data-test-id=["\']([^"\']+)["\']', 'data-test-id'),
                (r'data-test=["\']([^"\']+)["\']', 'data-test'),
                (r'testId=["\']([^"\']+)["\']', 'testId'),
                (r'aria-label=["\']([^"\']+)["\']', 'aria-label'),
            ]

            for line_num, line in enumerate(lines, start=1):
                for pattern, attr_name in patterns:
                    for match in re.finditer(pattern, line):
                        results.append({
                            'attribute': attr_name,
                            'value': match.group(1),
                            'file': file_path.name,
                            'line': line_num
                        })
                        if len(results) >= max_ids:
                            return results

        except Exception as e:
            self.logger.debug(f"Failed to extract test IDs from {file_path}: {e}")

        return results

    def _search_element_in_repos(
        self,
        selector: str
    ) -> Dict[str, Any]:
        """
        Multi-pattern search for a selector across cloned repos.

        For a given selector:
        1. Classify type via _classify_selector_type
        2. Generate search patterns via acm_knowledge.suggest_search_patterns
        3. Also search the raw term (stripped of #/. prefix)
        4. Grep console repo (frontend/src) and kubevirt repo (src/)
        5. Deduplicate by file path
        6. Extract component file names from matches
        7. Extract neighboring test IDs from top matching files

        Args:
            selector: The selector to search for

        Returns:
            Dict with selector_type, found_in_console, locations,
            component_files, and neighboring_test_ids
        """
        result = {
            'selector_type': self._classify_selector_type(selector),
            'found_in_console': False,
            'locations': [],
            'component_files': [],
            'neighboring_test_ids': []
        }

        if not self.console_repo_path and not self.kubevirt_repo_path:
            return result

        # Generate search patterns
        search_patterns = self.acm_knowledge.suggest_search_patterns(selector)

        # Also search the raw term (stripped of #/. prefix)
        raw_term = selector.lstrip('#').lstrip('.')
        if raw_term and raw_term not in search_patterns:
            search_patterns.append(raw_term)

        # Build search targets: (search_dir, repo_name)
        search_targets = []
        if self.console_repo_path and self.console_repo_path.exists():
            console_src = self.console_repo_path / 'frontend' / 'src'
            if console_src.exists():
                search_targets.append((console_src, 'console'))
            # Fallback to root src/ (e.g., for kubevirt-plugin structure)
            console_src_fallback = self.console_repo_path / 'src'
            if console_src_fallback.exists() and not console_src.exists():
                search_targets.append((console_src_fallback, 'console'))

        if self.kubevirt_repo_path and self.kubevirt_repo_path.exists():
            kubevirt_src = self.kubevirt_repo_path / 'src'
            if kubevirt_src.exists():
                search_targets.append((kubevirt_src, 'kubevirt'))

        # Search across all patterns and targets
        seen_files = set()
        all_locations = []

        for search_dir, repo_name in search_targets:
            for pattern in search_patterns:
                try:
                    matches = self._run_grep(search_dir, pattern, max_results=10)
                    for match in matches:
                        file_key = match.get('file', '')
                        if file_key not in seen_files:
                            seen_files.add(file_key)
                            match['repo'] = repo_name
                            match['matched_pattern'] = pattern
                            all_locations.append(match)
                except Exception:
                    pass

        if all_locations:
            result['found_in_console'] = True
            result['locations'] = all_locations[:20]  # Cap at 20

            # Extract component file names
            component_files = set()
            for loc in all_locations:
                file_path = loc.get('file', '')
                basename = Path(file_path).name
                if basename.endswith(('.tsx', '.ts', '.jsx', '.js')):
                    component_files.add(basename)
            result['component_files'] = sorted(component_files)[:10]

            # Extract neighboring test IDs from top 3 matching files
            neighboring_ids = []
            for loc in all_locations[:3]:
                rel_path = loc.get('file', '')
                # Resolve to absolute path - _run_grep returns paths
                # relative to search_dir.parent
                abs_path = self._resolve_grep_path(rel_path, loc.get('repo', ''))
                if abs_path and abs_path.exists():
                    ids = self._extract_test_ids_from_file(abs_path, max_ids=10)
                    neighboring_ids.extend(ids)

            # Deduplicate by value
            seen_values = set()
            unique_ids = []
            for tid in neighboring_ids:
                if tid['value'] not in seen_values:
                    seen_values.add(tid['value'])
                    unique_ids.append(tid)
            result['neighboring_test_ids'] = unique_ids[:20]

        return result

    def _resolve_grep_path(self, rel_path: str, repo_name: str) -> Optional[Path]:
        """
        Resolve a grep-returned relative path to an absolute path.

        _run_grep makes paths relative to search_dir.parent. For console
        repo searching frontend/src, paths are relative to console/frontend/.

        Args:
            rel_path: Relative path from grep output
            repo_name: Which repo ('console' or 'kubevirt')

        Returns:
            Absolute Path or None if not resolved
        """
        if not rel_path:
            return None

        candidates = []
        if repo_name == 'console' and self.console_repo_path:
            candidates.extend([
                self.console_repo_path / rel_path,
                self.console_repo_path / 'frontend' / rel_path,
            ])
        elif repo_name == 'kubevirt' and self.kubevirt_repo_path:
            candidates.extend([
                self.kubevirt_repo_path / rel_path,
            ])

        for candidate in candidates:
            if candidate.exists():
                return candidate

        return None

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

    def _gather_element_inventory(self, run_dir: Path):
        """
        Build element inventory by searching cloned repos for failing selectors.

        Uses local grep-based search across console and kubevirt repos to
        pre-compute element locations, selector classification, component files,
        and neighboring test IDs. Requires repos to be cloned (Step 6).
        """
        has_console = self.console_repo_path and self.console_repo_path.exists()
        has_kubevirt = self.kubevirt_repo_path and self.kubevirt_repo_path.exists()

        if not has_console and not has_kubevirt:
            self.logger.debug("No cloned repos available - skipping element inventory")
            return

        self.logger.info("Building element inventory from cloned repos...")

        try:
            element_inventory = {
                'source': 'local_repos',
                'cnv_version': None,
                'fleet_virt_selectors': 'deferred_to_phase2',
                'failed_test_elements': [],
                'element_lookup': {}
            }

            # Step 1: Detect CNV version if available (uses oc commands, not MCP)
            if self.acm_ui_mcp_client:
                try:
                    cnv_info = self.acm_ui_mcp_client.detect_cnv_version()
                    if cnv_info:
                        element_inventory['cnv_version'] = {
                            'version': getattr(cnv_info, 'version', None),
                            'branch': getattr(cnv_info, 'branch', None),
                            'detected_from': getattr(cnv_info, 'detected_from', None)
                        }
                        self.logger.info(
                            f"Detected CNV version: {getattr(cnv_info, 'version', 'unknown')}"
                        )
                except Exception as e:
                    self.logger.debug(f"CNV version detection failed: {e}")

            # Step 2: Pre-compute element locations for failing selectors
            test_report = self.gathered_data.get('test_report', {})
            failed_tests = test_report.get('failed_tests', [])
            processed_selectors = set()

            for test in failed_tests:
                error_message = test.get('error_message', '')
                test_name = test.get('test_name', '')
                parsed_stack = test.get('parsed_stack_trace', {})

                # Try parsed_stack_trace.failing_selector first, then extract from error
                selector = None
                if parsed_stack:
                    selector = parsed_stack.get('failing_selector')
                if not selector:
                    selector = self.acm_knowledge.extract_selector_from_error(error_message)

                if not selector or selector in processed_selectors:
                    continue

                processed_selectors.add(selector)

                # Search for element in cloned repos
                element_info = self._search_element_in_repos(selector)

                element_inventory['element_lookup'][selector] = element_info
                element_inventory['failed_test_elements'].append({
                    'test_name': test_name,
                    'selector': selector,
                    'selector_type': element_info['selector_type'],
                    'found_in_console': element_info['found_in_console'],
                    'component_files': element_info['component_files'],
                    'location_count': len(element_info['locations'])
                })
                self.logger.debug(
                    f"Element '{selector}' ({element_info['selector_type']}): "
                    f"{'found' if element_info['found_in_console'] else 'not found'} "
                    f"in {len(element_info['locations'])} locations"
                )

            self.gathered_data['element_inventory'] = element_inventory

            # Save to file if we found any elements
            if element_inventory['element_lookup']:
                output_path = run_dir / 'element-inventory.json'
                output_path.write_text(json.dumps(element_inventory, indent=2, default=str))
                self.logger.info(
                    f"Element inventory saved: {len(element_inventory['element_lookup'])} "
                    f"selectors searched"
                )

        except Exception as e:
            error_msg = f"Failed to build element inventory: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['errors'].append(error_msg)
            self.gathered_data['element_inventory'] = {'error': error_msg}

    def _collect_timeline_evidence(
        self,
        selectors: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Collect git timeline evidence for failing selectors.

        Provides pre-computed evidence about:
        - Whether element exists in console repo
        - When element was last modified/removed
        - Days since automation last touched the selector
        - Classification hints based on timeline comparison

        Args:
            selectors: List of failing selectors to analyze

        Returns:
            Dict mapping selector to timeline evidence
        """
        evidence = {}
        unique_selectors = list(set(selectors))[:10]  # Limit to 10 unique selectors

        for selector in unique_selectors:
            try:
                # Use timeline service to compare dates
                comparison = self.timeline_service.compare_timelines(selector)

                # Provide FACTUAL DATA only - no classification hints
                # AI makes classification decisions based on these facts
                selector_evidence = {
                    'selector': selector,
                    'element_id': comparison.element_id,
                    'exists_in_console': not comparison.element_removed_from_console and not comparison.element_never_existed,
                    'element_removed': comparison.element_removed_from_console,
                    'element_never_existed': comparison.element_never_existed,
                    'days_difference': comparison.days_difference,
                    'console_changed_after_automation': comparison.console_changed_after_automation,
                    'stale_test_signal': comparison.stale_test_signal,
                    'product_commit_type': comparison.product_commit_type,
                    # NO classification_hint - AI determines classification
                }

                # Add timeline details if available
                if comparison.console_timeline:
                    timeline = comparison.console_timeline
                    selector_evidence['console_timeline'] = {
                        'file_path': timeline.file_path,
                        'last_modified': timeline.last_modified_date.isoformat() if timeline.last_modified_date else None,
                        'last_commit': timeline.last_commit_sha[:8] if timeline.last_commit_sha else None,
                        'commit_message': timeline.last_commit_message
                    }

                if comparison.automation_timeline:
                    timeline = comparison.automation_timeline
                    selector_evidence['automation_timeline'] = {
                        'file_path': timeline.file_path,
                        'last_modified': timeline.last_modified_date.isoformat() if timeline.last_modified_date else None,
                        'last_commit': timeline.last_commit_sha[:8] if timeline.last_commit_sha else None,
                        'commit_message': timeline.last_commit_message
                    }

                evidence[selector] = selector_evidence
                self.logger.debug(f"Collected timeline evidence for: {selector}")

            except Exception as e:
                self.logger.debug(f"Failed to collect timeline for {selector}: {e}")
                evidence[selector] = {
                    'selector': selector,
                    'error': str(e)
                }

        return evidence

    def _build_investigation_hints(self, run_dir: Path):
        """Build investigation hints with ACM-specific directory knowledge and timeline data."""
        self.logger.info("Building investigation hints for AI...")

        test_report = self.gathered_data.get('test_report', {})
        failed_tests = test_report.get('failed_tests', [])
        repos_dir = run_dir / 'repos'

        # Set up timeline service with automation repo path if available
        if self.automation_repo_path and self.automation_repo_path.exists():
            self.timeline_service.set_automation_path(self.automation_repo_path)
        if self.console_repo_path and self.console_repo_path.exists():
            self.timeline_service.console_path = self.console_repo_path

        # Extract test file locations from stack traces with ACM feature mapping
        failed_test_locations = []
        selectors_for_timeline = []

        for test in failed_tests:
            error_message = test.get('error_message', '')
            test_name = test.get('test_name', '')

            # Use pre-parsed stack trace data from _gather_test_report
            # NO re-parsing needed - already done in Phase 1 data gathering
            parsed_data = test.get('parsed_stack_trace', {})

            # Get root cause info from pre-parsed data
            root_file = parsed_data.get('root_cause_file')
            root_line = parsed_data.get('root_cause_line')
            selector = parsed_data.get('failing_selector')

            # Get ACM-specific feature mapping and directories
            feature_area = self.acm_knowledge.map_test_to_feature(test_name)
            relevant_dirs = self.acm_knowledge.get_relevant_directories(
                test_name,
                error_message
            )

            # Get search patterns for the selector
            search_patterns = []
            if selector:
                search_patterns = self.acm_knowledge.suggest_search_patterns(selector)
                selectors_for_timeline.append(selector)

            location = {
                'test_name': test_name,
                'file': root_file,
                'line': root_line,
                'extracted_selectors': [selector] if selector else [],
                'feature_area': feature_area,
                'relevant_console_dirs': relevant_dirs,
                'search_patterns': search_patterns
            }
            failed_test_locations.append(location)

        # Collect timeline evidence for failing selectors (Phase 1 enhancement)
        timeline_evidence = {}
        if selectors_for_timeline and self.console_repo_path:
            self.logger.info(f"Collecting timeline evidence for {len(selectors_for_timeline)} selectors...")
            timeline_evidence = self._collect_timeline_evidence(selectors_for_timeline)

        self.gathered_data['investigation_hints'] = {
            'start_here': [
                '1. Read failed test files from stack traces',
                '2. Check timeline_evidence for selector existence/removal history',
                '3. Check feature_area to identify relevant console directories',
                '4. Trace selectors to their definitions in views/',
                '5. Search relevant_console_dirs for the failing element',
                '6. Cross-reference with console_log errors'
            ],
            'failed_test_locations': failed_test_locations,
            'timeline_evidence': timeline_evidence,
            'key_directories': {
                # Automation paths
                'automation_tests': 'repos/automation/cypress/e2e/',
                'automation_views': 'repos/automation/cypress/views/',
                'automation_support': 'repos/automation/cypress/support/',
                # Console paths (ACM-specific)
                'console_ui_components': 'repos/console/frontend/src/ui-components/',
                'console_routes': 'repos/console/frontend/src/routes/',
                'console_components': 'repos/console/frontend/src/components/',
                'console_plugins_acm': 'repos/console/frontend/plugins/acm/',
                'console_plugins_mce': 'repos/console/frontend/plugins/mce/',
                # KubeVirt plugin paths (virtualization features)
                'kubevirt_src': 'repos/kubevirt-plugin/src/',
                'kubevirt_views': 'repos/kubevirt-plugin/src/views/',
                'kubevirt_components': 'repos/kubevirt-plugin/src/components/',
            },
            # Full ACM structure for reference
            'acm_console_structure': self.acm_knowledge.get_console_structure(),
            'kubevirt_structure': self.acm_knowledge.get_kubevirt_structure(),
            'feature_route_mapping': self.acm_knowledge.get_feature_routes(),
        }

    def _inject_temporal_summaries(self):
        """
        Inject per-test temporal_summary into each failed test's extracted_context.

        Copies the relevant timeline evidence (keyed by failing selector) into
        each test entry so the AI can read per-test temporal data without
        cross-referencing investigation_hints.timeline_evidence.

        Must run AFTER _build_investigation_hints() has populated timeline_evidence.
        """
        timeline_evidence = self.gathered_data.get('investigation_hints', {}).get('timeline_evidence', {})
        if not timeline_evidence:
            return

        failed_tests = self.gathered_data.get('test_report', {}).get('failed_tests', [])

        for i, test in enumerate(failed_tests):
            parsed_stack = test.get('parsed_stack_trace', {})
            selector = parsed_stack.get('failing_selector')
            if not selector or selector not in timeline_evidence:
                continue

            evidence = timeline_evidence[selector]
            if 'error' in evidence:
                continue

            temporal_summary = {
                'stale_test_signal': evidence.get('stale_test_signal', False),
                'product_commit_type': evidence.get('product_commit_type'),
                'days_difference': evidence.get('days_difference'),
            }

            # Add dates from timeline sub-objects if available
            console_tl = evidence.get('console_timeline', {})
            automation_tl = evidence.get('automation_timeline', {})
            if console_tl.get('last_modified'):
                temporal_summary['product_last_modified'] = console_tl['last_modified']
            if console_tl.get('commit_message'):
                temporal_summary['product_commit_message'] = console_tl['commit_message']
            if automation_tl.get('last_modified'):
                temporal_summary['automation_last_modified'] = automation_tl['last_modified']

            # Inject into extracted_context
            extracted_context = test.get('extracted_context')
            if extracted_context is None:
                extracted_context = {}
                self.gathered_data['test_report']['failed_tests'][i]['extracted_context'] = extracted_context

            extracted_context['temporal_summary'] = temporal_summary

        injected_count = sum(
            1 for t in failed_tests
            if t.get('extracted_context', {}).get('temporal_summary')
        )
        if injected_count:
            self.logger.info(f"Injected temporal_summary into {injected_count} failed test(s)")

    def _save_combined_data(self, run_dir: Path):
        """Save data in multi-file structure."""
        self.logger.info("Saving gathered data...")

        # Finalize metadata
        self.gathered_data['metadata']['status'] = 'complete'
        self.gathered_data['metadata']['data_version'] = '3.5.0'

        # Mask sensitive data
        masked_data = self._mask_sensitive_data(self.gathered_data)

        # Build core-data.json
        core_data = {
            'metadata': masked_data.get('metadata', {}),
            'jenkins': masked_data.get('jenkins', {}),
            'test_report': masked_data.get('test_report', {}),
            'console_log': masked_data.get('console_log', {}),
            'environment': masked_data.get('environment', {}),
            'repositories': masked_data.get('repositories', {}),
            'investigation_hints': masked_data.get('investigation_hints', {}),
            'cluster_landscape': masked_data.get('cluster_landscape', {}),
            'feature_grounding': masked_data.get('feature_grounding', {}),
            'feature_knowledge': masked_data.get('feature_knowledge', {}),
            'cluster_access': masked_data.get('cluster_access', {}),
            'cluster_oracle': masked_data.get('cluster_oracle', {}),
            'backend_probes': masked_data.get('backend_probes', {}),
            'errors': masked_data.get('errors', []),
            'ai_instructions': self._build_ai_instructions()
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
            'version': '3.5.0',
            'file_structure': 'multi-file-with-repos',
            'created_at': datetime.now().isoformat(),
            'acm_ui_mcp_available': True,  # Always available via Claude Code native MCP
            'files': {
                'core-data.json': {
                    'description': 'Primary analysis data (metadata, jenkins, test_report, console_log, environment, investigation_hints)',
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
                '2. Check element-inventory.json for pre-computed element locations (if available)',
                '3. Navigate to repos/automation/ and read failed test files',
                '4. Trace imports, understand test logic',
                '5. Check repos/console/ for element existence',
                '6. For VM tests, also check repos/kubevirt-plugin/ for virtualization UI',
                '7. Cross-reference with console_log errors',
                '8. Classify each test as PRODUCT_BUG, AUTOMATION_BUG, or INFRASTRUCTURE',
                '9. Save analysis-results.json'
            ]
        }

        # Add element-inventory.json if MCP data was gathered
        element_inventory_path = run_dir / 'element-inventory.json'
        if element_inventory_path.exists():
            manifest['files']['element-inventory.json'] = {
                'description': 'Pre-computed element locations for failing selectors from cloned repos',
                'required': False,
                'use_case': 'Selector classification, component files, and neighboring test IDs'
            }

        return manifest

    def _build_ai_instructions(self) -> Dict[str, Any]:
        """Build AI instructions for 5-phase systematic investigation framework."""
        return {
            'version': '3.5.0',
            'architecture': '5-phase-systematic-investigation-with-playbooks',
            'purpose': 'Systematic deep investigation through 5 mandatory phases with feature playbooks, tiered cluster investigation, and KG dependency analysis',

            # Cluster Re-Authentication
            'cluster_access': {
                'description': 'Re-authenticate to the cluster at the start of Stage 2 using the persisted kubeconfig',
                'steps': [
                    'A-1a. Read cluster_access from core-data.json — check kubeconfig_path',
                    'A-1b. If kubeconfig_path exists: Run oc whoami --kubeconfig <kubeconfig_path> to verify authentication',
                    'A-1c. If kubeconfig_path is null: credentials were unavailable during Stage 1 — set cluster_access_available=false',
                    'A-1d. If oc whoami fails: kubeconfig expired — set cluster_access_available=false, proceed with snapshot data only (reduce confidence by 0.15)',
                    'A-1e. IMPORTANT: Use --kubeconfig <kubeconfig_path> on ALL oc commands throughout Stage 2',
                ],
            },

            # Tiered Cluster Investigation Methodology
            'tiered_investigation': {
                'description': 'Systematic cluster investigation following SRE debugging methodology. Always do Tier 0-2, go deeper based on findings.',
                'tier_0_health_snapshot': {
                    'purpose': 'Verify Stage 1 snapshot is still current. Run ONCE at start of Stage 2.',
                    'commands': [
                        "oc get mch -A -o yaml  # MCH phase, version, spec.overrides.components",
                        "oc get managedclusters  # cluster health summary",
                        "oc get clusteroperators | grep -v 'True.*False.*False'  # degraded operators only",
                        "oc adm top nodes  # resource pressure",
                        "oc get pods -A | grep -Ev 'Running|Completed'  # non-healthy pods",
                    ],
                },
                'tier_1_component_health': {
                    'purpose': 'Check health of every backend component the feature depends on. Run per feature area with failures.',
                    'per_component_steps': [
                        "oc get pods -n <namespace> -l app=<component>  # Running? Ready? Restart count?",
                        "If not Running/Ready: oc describe pod <pod> -n <ns>  # Events, conditions",
                        "If not Running/Ready: oc logs <pod> -n <ns> --tail=100  # Error messages",
                        "If restart count > 3: oc logs <pod> -n <ns> --previous --tail=50  # Previous crash reason",
                        "oc get events -n <ns> --sort-by=.lastTimestamp | tail -10  # Recent events",
                    ],
                },
                'tier_2_playbook_investigation': {
                    'purpose': 'Verify prerequisites and investigate known failure paths from playbooks. Run when playbook loaded.',
                    'prerequisite_checks': {
                        'mch_component': "oc get mch -A -o jsonpath='{.items[0].spec.overrides.components}'",
                        'addon': "oc get managedclusteraddon <addon> -n <cluster>",
                        'operator': "oc get csv -n <namespace> | grep <operator>",
                        'crd': "oc get crd <crd-name>",
                    },
                    'failure_path_steps': 'Match test error against symptom regexes, execute investigation steps, compare against expected results',
                },
                'tier_3_data_flow': {
                    'purpose': 'Trace feature data flow to find where things break. Run when Tier 1-2 dont explain the failure.',
                    'triggers': [
                        'All components healthy but tests still fail',
                        'Feature involves spoke clusters (cross-cluster data flow)',
                        'Error suggests data not flowing (empty results, stale data)',
                        'KG shows cross-subsystem dependencies',
                    ],
                },
                'tier_4_deep_investigation': {
                    'purpose': 'Cast a wider net for root causes. Run when Tier 1-3 dont explain, or multiple feature areas failing.',
                    'triggers': [
                        'Tier 1-3 dont explain the failure',
                        'Multiple feature areas failing simultaneously',
                        'Suspected infrastructure-wide issue',
                        'KG common dependency analysis finds shared root cause',
                    ],
                    'includes': [
                        'Cross-namespace event scan',
                        'Network connectivity checks',
                        'Resource deep-dive (node pressure, memory-heavy pods)',
                        'KG cascading failure analysis (find_common_dependency)',
                        'Recent changes (recently created pods, image pulls)',
                    ],
                },
            },

            # 5-Phase Framework Overview
            'investigation_framework': {
                'description': 'Every analysis MUST complete all 5 phases in order. Use tiered_investigation within phases.',
                'phases': {
                    'A': {
                        'name': 'Initial Assessment',
                        'purpose': 'Re-authenticate cluster, review feature knowledge, detect global patterns',
                        'steps': [
                            'A-1. Cluster re-authentication: Read cluster_access.kubeconfig_path from core-data.json, verify with oc whoami --kubeconfig <path>. If fails or null, proceed in degraded mode (snapshot only, reduced confidence).',
                            'A0. Read feature_grounding from core-data.json - note subsystem and key components per test group',
                            'A0b. Read feature_knowledge from core-data.json - review architecture summaries, key insights, prerequisite status, pre-matched failure paths, and KG dependency context for each feature area',
                            'A0c. Run Tier 0 health snapshot (tiered_investigation.tier_0_health_snapshot) - compare live state against cluster_landscape snapshot',
                            'A1. Check environment health (cluster_connectivity, environment_score)',
                            'A1b. Read cluster_landscape from core-data.json - check for degraded operators overlapping feature components',
                            'A2. Detect failure patterns (mass timeouts, single selector, 500 errors)',
                            'A3. Scan cross-test correlations (shared selectors, components, feature areas)',
                            'A3b. If multiple feature areas have failures, query KG find_common_dependency across failing subsystems. If common dependency found, flag as investigation priority for Tier 4.'
                        ]
                    },
                    'B': {
                        'name': 'Deep Investigation',
                        'purpose': 'Systematically gather ALL evidence for each test using tiered investigation',
                        'steps': [
                            'B1. Analyze extracted_context (test_file, page_objects, console_search)',
                            'B2. Check timeline_evidence (element removed? changed?)',
                            'B3. Review console_log evidence (500 errors, network errors)',
                            'B4. Execute MCP queries (ACM-UI, Knowledge Graph)',
                            'B5. Analyze detected_components (backend component names)',
                            'B5b. Run Tier 1 component health check for the feature area key_components (always when cluster access available)',
                            'B6. Deep dive repos/ when extracted_context insufficient',
                            'B7. Backend cross-check - for element_not_found/timeout failures, check if backend components are failing (CrashLoopBackOff, 500s, degraded). If yes, set backend_caused_ui_failure=true and route to Path B2 in Phase D',
                            'B8. Run Tier 2 playbook investigation - check prerequisites with live oc commands, execute failure path investigation steps from matched playbook paths',
                            'B8b. If Tier 2 confirms a failure path, query KG for upstream dependencies of confirmed failing component. If upstream also failing, root cause is upstream.',
                            'B8c. If Tier 1-2 dont explain failure, run Tier 3 data flow tracing using KG dependency context + playbook architecture.data_flow',
                            'B8d. If Tier 1-3 dont explain OR multiple areas failing, run Tier 4 deep investigation',
                        ]
                    },
                    'C': {
                        'name': 'Cross-Reference Validation',
                        'purpose': 'Validate through multiple evidence sources',
                        'steps': [
                            'C1. Verify multi-evidence requirement (minimum 2 sources)',
                            'C2. Detect cascading failures via Knowledge Graph',
                            'C3. Correlate patterns with Phase A findings'
                        ]
                    },
                    'D': {
                        'name': 'Classification',
                        'purpose': 'Apply classification with evidence matrix (check feature knowledge FIRST, then backend cross-check)',
                        'steps': [
                            'PR-4. Feature Knowledge Override: If prerequisite unmet AND Tier 2 confirmed with live oc commands, use playbook suggested classification at 0.95 confidence. If Tier 2 confirmed failure path, use path classification and confidence. If Tier 3 found data flow break, classify based on break point. If Tier 4 KG found cascading failure, classify based on upstream root cause.',
                            'PR-4b. If cluster_access_available=false (login failed): reduce confidence by 0.15 on all classifications.',
                            'D0. Check backend cross-check override - if backend_caused_ui_failure=true, route to Path B2 NOT Path A',
                            'D1. Check evidence sufficiency (2+ sources, no conflicts)',
                            'D2. Calculate confidence score (Tier 2 confirmed with live commands > Tier 2 snapshot-only > standard B1-B7 evidence)',
                            'D3. Rule out alternatives (document why others dont fit)'
                        ]
                    },
                    'E': {
                        'name': 'Feature Context & JIRA Correlation',
                        'purpose': 'Build feature understanding via Knowledge Graph + JIRA, validate classification, search for existing bugs',
                        'steps': [
                            'E0. Build subsystem context via Knowledge Graph (mcp__neo4j-rhacm__read_neo4j_cypher) - get component info, subsystem peers, dependencies',
                            'E1. Carry forward Path B2 findings if classification_path == B2 (skip to E4)',
                            'E2. Search for feature stories and PORs via JIRA (mcp__jira__search_issues) - by Polarion ID, component, or keywords',
                            'E3. Read feature stories and acceptance criteria (mcp__jira__get_issue) - understand intended behavior, linked PRs',
                            'E4. Search for related bugs (mcp__jira__search_issues) - enriched by E0 subsystem context',
                            'E5. Known issue matching + feature-informed classification validation',
                            'E6. Create/link JIRA issues when definitive new bugs found (optional)'
                        ]
                    }
                }
            },

            # Multi-Evidence Requirements
            'evidence_requirements': {
                'description': 'Every classification MUST have minimum 2 evidence sources',
                'evidence_tiers': {
                    'tier_1_definitive': ['500 errors in console log', 'element_removed=true', 'environment_score < 0.3'],
                    'tier_2_strong': ['selector mismatch', 'multiple tests same error', 'cascading failure'],
                    'tier_3_supportive': ['similar selectors exist', 'timing issues', 'single test timeout']
                },
                'minimum_requirement': '1 Tier 1 + 1 Tier 2, OR 2 Tier 1, OR 3 Tier 2',
                'classification_evidence_matrix': {
                    'PRODUCT_BUG': ['Console log 500 errors', 'Environment healthy', 'Test logic correct'],
                    'AUTOMATION_BUG': ['Selector mismatch', 'No 500 errors', 'Element exists in product'],
                    'INFRASTRUCTURE': ['Environment unhealthy', 'Multiple tests affected', 'Network errors']
                }
            },

            # MCP Tool Integration - Five MCP servers available for Phase 2 AI analysis
            # These tools are called natively by the Claude Code agent (not via Python).
            # Tool names use the format: mcp__<server>__<tool_name>
            'mcp_integration': {
                'available': {
                    'acm_ui': True,
                    'knowledge_graph': True,
                    'jira': True
                },
                'how_to_call': 'Use native MCP tool calls. Example: mcp__jira__search_issues(jql="project = ACM AND type = Bug")',

                # ACM-UI MCP Server (19 tools) - stolostron/console and kubevirt-plugin source code via GitHub
                'acm_ui': {
                    'tool_prefix': 'mcp__acm-ui__',
                    'description': 'Access ACM Console and kubevirt-plugin source code, selectors, and component structure via GitHub',
                    'setup_required': 'MUST call set_acm_version at start of every investigation to match the ACM version under test',
                    'supported_versions': {
                        'acm_console': {'range': '2.11-2.17', 'latest_ga': '2.16', 'dev': '2.17 (main)'},
                        'kubevirt_plugin': {'range': '4.14-4.22', 'latest_ga': '4.21', 'dev': '4.22 (main)'},
                        'note': 'ACM and CNV versions are independent - set each to match the target environment'
                    },
                    'tools': {
                        'version_management': {
                            'set_acm_version': {
                                'call': "mcp__acm-ui__set_acm_version(version='2.16')",
                                'purpose': 'Set ACM Console branch. CALL FIRST before any code searches.',
                                'params': "version: '2.11'-'2.17', 'latest' (=2.16), or 'main' (=2.17)"
                            },
                            'set_cnv_version': {
                                'call': "mcp__acm-ui__set_cnv_version(version='4.21')",
                                'purpose': 'Set kubevirt-plugin branch for VM/Fleet Virt tests',
                                'params': "version: '4.14'-'4.22', 'latest' (=4.21), or 'main'"
                            },
                            'detect_cnv_version': {
                                'call': 'mcp__acm-ui__detect_cnv_version()',
                                'purpose': 'Auto-detect CNV version from connected cluster and set kubevirt branch',
                                'when': 'VM test failures - auto-sets correct kubevirt-plugin branch'
                            },
                            'list_versions': {
                                'call': 'mcp__acm-ui__list_versions()',
                                'purpose': 'Show all supported ACM/CNV version-to-branch mappings'
                            },
                            'get_current_version': {
                                'call': "mcp__acm-ui__get_current_version(repo='acm')",
                                'purpose': 'Check which version is currently active',
                                'params': "repo: 'acm' or 'kubevirt'"
                            },
                            'list_repos': {
                                'call': 'mcp__acm-ui__list_repos()',
                                'purpose': 'List available repos with current version settings'
                            },
                            'get_cluster_virt_info': {
                                'call': 'mcp__acm-ui__get_cluster_virt_info()',
                                'purpose': 'Get CNV version, console plugins, Fleet Virt status from cluster'
                            }
                        },
                        'code_discovery': {
                            'search_code': {
                                'call': "mcp__acm-ui__search_code(query='create-btn', repo='acm')",
                                'purpose': 'GitHub code search across repos - find where a selector, string, or component is used',
                                'params': "query: search term, repo: 'acm' or 'kubevirt'",
                                'when': 'Selector not found in extracted_context, need to check if it exists anywhere in product'
                            },
                            'find_test_ids': {
                                'call': "mcp__acm-ui__find_test_ids(component_path='frontend/src/routes/Infrastructure/Clusters/ManagedClusters/ManagedClusters.tsx', repo='acm')",
                                'purpose': 'Find data-testid, id, aria-label, data-test attributes in a specific file',
                                'when': 'Need to verify exact selector names in a known component file'
                            },
                            'get_component_source': {
                                'call': "mcp__acm-ui__get_component_source(path='frontend/src/routes/Infrastructure/Clusters/ClusterDetails/ClusterDetails.tsx', repo='acm')",
                                'purpose': 'Get raw source code for a specific file',
                                'when': 'Need to read actual component code to understand rendering logic'
                            },
                            'search_component': {
                                'call': "mcp__acm-ui__search_component(query='ClusterTable', repo='acm')",
                                'purpose': 'Search for component files by name in common directories',
                                'when': 'Know the component name but not the file path'
                            },
                            'get_route_component': {
                                'call': "mcp__acm-ui__get_route_component(url_path='/multicloud/infrastructure/clusters')",
                                'purpose': 'Map a URL path to source files in ACM and kubevirt-plugin repos',
                                'when': 'Test navigates to a URL and you need to find the rendering component'
                            }
                        },
                        'selectors_and_ui': {
                            'get_acm_selectors': {
                                'call': "mcp__acm-ui__get_acm_selectors(source='catalog', component='clc')",
                                'purpose': 'Get QE-proven selectors from test automation repos. More reliable than source extraction.',
                                'params': "source: 'catalog' (curated), 'source' (raw), 'both'. component: 'all', 'clc', 'search', 'app', 'grc'",
                                'components': {
                                    'clc': 'stolostron/clc-ui-e2e - Cluster Lifecycle + RBAC selectors',
                                    'search': 'stolostron/search-e2e-test - Search selectors',
                                    'app': 'stolostron/application-ui-test - Applications/ALC selectors',
                                    'grc': 'stolostron/acmqe-grc-test - Governance/GRC selectors'
                                },
                                'when': 'Selector mismatch detected - find the correct/current selector name'
                            },
                            'get_fleet_virt_selectors': {
                                'call': 'mcp__acm-ui__get_fleet_virt_selectors()',
                                'purpose': 'Get Fleet Virtualization UI selectors from kubevirt-plugin',
                                'when': 'VM/Fleet Virt test failures with selector issues'
                            },
                            'search_translations': {
                                'call': "mcp__acm-ui__search_translations(query='Create cluster')",
                                'purpose': 'Find exact UI text (button labels, messages, error strings) from ACM translation files',
                                'when': 'Test asserts specific UI text that may have changed'
                            },
                            'get_patternfly_selectors': {
                                'call': "mcp__acm-ui__get_patternfly_selectors(component='button')",
                                'purpose': 'Get PatternFly v6 CSS selector reference when data-testid not available',
                                'params': "component: 'button', 'modal', 'table', etc. or empty for all"
                            }
                        },
                        'component_analysis': {
                            'get_component_types': {
                                'call': "mcp__acm-ui__get_component_types(path='frontend/src/routes/Infrastructure/Clusters/ManagedClusters/ManagedClusters.tsx', repo='acm')",
                                'purpose': 'Extract TypeScript type/interface definitions - understand props, state, data models'
                            },
                            'get_wizard_steps': {
                                'call': "mcp__acm-ui__get_wizard_steps(path='frontend/src/wizards/ClusterCreation/CreateClusterWizard.tsx', repo='acm')",
                                'purpose': 'Extract wizard step structure and visibility conditions',
                                'when': 'Test fails in a wizard flow - understand step order and conditions'
                            },
                            'get_routes': {
                                'call': 'mcp__acm-ui__get_routes()',
                                'purpose': 'Get all ACM Console navigation paths and route definitions'
                            }
                        }
                    },
                    'investigation_workflow': [
                        '1. ALWAYS call set_acm_version first (check core-data.json metadata for ACM version)',
                        '2. For VM tests: call detect_cnv_version or set_cnv_version',
                        '3. When selector not found: search_code to check if selector exists anywhere in product',
                        '4. When selector mismatch confirmed: get_acm_selectors to find correct selector',
                        '5. When need to verify component rendering: get_component_source',
                        '6. When UI text assertion fails: search_translations'
                    ]
                },

                # JIRA MCP Server (25 tools) - Full JIRA integration
                'jira': {
                    'tool_prefix': 'mcp__jira__',
                    'description': 'Full JIRA integration for searching bugs, reading feature stories, creating issues, and managing workflows',
                    'tools': {
                        'issue_search_and_read': {
                            'search_issues': {
                                'call': "mcp__jira__search_issues(jql=\"project = ACM AND type = Bug AND status != Closed AND summary ~ 'search-api'\", max_results=10)",
                                'purpose': 'Search for issues using JQL (Jira Query Language)',
                                'common_jql_patterns': {
                                    'related_bugs': "project = ACM AND type = Bug AND status != Closed AND (summary ~ '{component}' OR description ~ '{component}')",
                                    'feature_stories_by_polarion': "summary ~ 'RHACM4K-{id}' OR description ~ 'RHACM4K-{id}'",
                                    'feature_stories_by_component': "project = ACM AND type = Story AND (summary ~ '{component}' OR component = '{subsystem}') ORDER BY updated DESC",
                                    'feature_stories_by_keywords': "project = ACM AND type in (Story, Epic) AND summary ~ '{keywords}' ORDER BY updated DESC",
                                    'recent_bugs_by_subsystem': "project = ACM AND type = Bug AND component = '{subsystem}' ORDER BY created DESC"
                                }
                            },
                            'get_issue': {
                                'call': "mcp__jira__get_issue(issue_key='ACM-22079')",
                                'purpose': 'Get full issue details - summary, description, acceptance criteria, linked PRs, fix versions, linked epics/PORs',
                                'when': 'After search_issues finds relevant issues, read full details for classification context'
                            },
                            'search_issues_by_team': {
                                'call': "mcp__jira__search_issues_by_team(team_name='qe', project_key='ACM', status='Open')",
                                'purpose': 'Find issues assigned to any member of a configured team'
                            }
                        },
                        'issue_creation_and_update': {
                            'create_issue': {
                                'call': "mcp__jira__create_issue(project_key='ACM', summary='Component X returns 500', description='Found during z-stream analysis...', issue_type='Bug', priority='Major', components=['Search'], work_type='10608', due_date='2026-03-01')",
                                'purpose': 'Create new bug when definitive new issue found with no existing JIRA',
                                'when': 'Phase E6 - only when classification is definitive and no existing bug matches'
                            },
                            'update_issue': {
                                'call': "mcp__jira__update_issue(issue_key='ACM-12345', priority='Critical', components=['Search'], work_type='10608', due_date='2026-03-01')",
                                'purpose': 'Update fields on an existing issue'
                            },
                            'transition_issue': {
                                'call': "mcp__jira__transition_issue(issue_key='ACM-12345', transition='In Progress')",
                                'purpose': 'Move issue to new status (e.g., In Progress, Done)'
                            },
                            'add_comment': {
                                'call': "mcp__jira__add_comment(issue_key='ACM-12345', comment='Z-stream analysis: confirmed regression from PR #1234')",
                                'purpose': 'Add analysis findings as a comment on existing bug'
                            },
                            'link_issue': {
                                'call': "mcp__jira__link_issue(link_type='Relates', inward_issue='ACM-111', outward_issue='ACM-222')",
                                'purpose': 'Link related failures to same root cause',
                                'link_types': ['Blocks', 'Relates', 'Duplicates']
                            }
                        },
                        'project_and_metadata': {
                            'get_projects': {'call': 'mcp__jira__get_projects()', 'purpose': 'List accessible projects'},
                            'get_project_components': {'call': "mcp__jira__get_project_components(project_key='ACM')", 'purpose': 'List components in a project'},
                            'get_link_types': {'call': 'mcp__jira__get_link_types()', 'purpose': 'List available link types'},
                            'debug_issue_fields': {'call': "mcp__jira__debug_issue_fields(issue_key='ACM-12345')", 'purpose': 'Show all raw fields for debugging'}
                        }
                    },
                    'investigation_workflow': [
                        '1. Phase B (Path B2): Extract Polarion ID (RHACM4K-XXXX) from test name → search_issues for feature story → get_issue to read acceptance criteria',
                        '2. Phase E0: Use subsystem/component from Knowledge Graph to search for related feature stories',
                        '3. Phase E2-E3: Search for feature stories by Polarion ID, component, or keywords → read full details',
                        '4. Phase E4: Search for existing bugs by component name, subsystem, selector, error keywords',
                        '5. Phase E5: get_issue on matching bugs → compare symptoms → note in recommended_fix',
                        '6. Phase E6 (optional): create_issue for new bugs, link_issue for related failures'
                    ]
                },

                # Knowledge Graph MCP Server (Neo4j RHACM) - Component dependency analysis
                'knowledge_graph': {
                    'tool_prefix': 'mcp__neo4j-rhacm__',
                    'tool_name': 'mcp__neo4j-rhacm__read_neo4j_cypher',
                    'description': 'Component dependency analysis and feature workflow context via Cypher queries against RHACM architecture graph',
                    'availability_note': 'Optional - may not be connected in all environments. Skip gracefully if tool call fails.',
                    'call_format': "mcp__neo4j-rhacm__read_neo4j_cypher(query=\"MATCH (c:RHACMComponent) WHERE c.subsystem = 'Search' RETURN c.label, c.type\")",
                    'use_cases': {
                        'phase_B5': 'Component dependency analysis - find what depends on failing component',
                        'phase_C2': 'Cascading failure detection - find common dependency across multiple failing components',
                        'phase_E0': 'Subsystem context building - get all components in a subsystem, understand component relationships'
                    },
                    'label_mapping_note': (
                        'KG uses descriptive labels (e.g., "API Gateway Controller"), NOT '
                        'pod/deployment names (e.g., "search-api"). When querying by component, '
                        'use get_subsystem_components FIRST to discover the actual KG labels, '
                        'then use those labels in subsequent queries. The pod_to_kg_label map '
                        'provides known translations. For unmapped components, query by subsystem.'
                    ),
                    'pod_to_kg_label': {
                        'search-api': 'API Gateway Controller',
                        'search-collector': 'Collection Agent',
                        'search-indexer': 'Resource Indexer',
                        'search-redisgraph': 'ElasticSearch Integration',
                        'grc-policy-propagator': 'Policy Propagator Controller',
                        'config-policy-controller': 'Config Policy Controller',
                        'governance-policy-framework': 'Governance Policy Framework',
                        'cluster-curator': 'Cluster Curator',
                        'managedcluster-import-controller': 'ManagedCluster Import Controller',
                        'hive-controllers': 'Hive Controllers',
                        'console-api': 'Console API Server',
                        'acm-console': 'Web Console',
                        'thanos-query': 'Thanos Query',
                        'thanos-receive': 'Thanos Receive',
                        'grafana': 'Grafana',
                    },
                    'query_strategy': [
                        '1. ALWAYS start with get_subsystem_components to discover actual KG labels for the subsystem',
                        '2. Use the returned labels (not pod names) in get_dependents/get_dependencies queries',
                        '3. If a pod name is in pod_to_kg_label, use the mapped label directly',
                        '4. For internal data flow: query relationships within the subsystem',
                        '5. For cross-subsystem: query relationships leaving the subsystem',
                    ],
                    'query_templates': {
                        'get_subsystem_components': {
                            'query': "MATCH (c:RHACMComponent) WHERE c.subsystem = '{subsystem}' RETURN c.label, c.type",
                            'when': 'FIRST query for any subsystem — discover actual KG labels before other queries',
                            'example': "MATCH (c:RHACMComponent) WHERE c.subsystem = 'Search' RETURN c.label, c.type"
                        },
                        'get_component_info': {
                            'query': "MATCH (c:RHACMComponent) WHERE c.label =~ '(?i).*{kg_label}.*' RETURN c.label, c.subsystem, c.type",
                            'when': 'Get subsystem and type for a component. Use KG label from pod_to_kg_label or get_subsystem_components, NOT pod name.',
                            'example': "MATCH (c:RHACMComponent) WHERE c.label =~ '(?i).*API Gateway Controller.*' RETURN c.label, c.subsystem, c.type"
                        },
                        'get_dependents': {
                            'query': "MATCH (dep:RHACMComponent)-[:DEPENDS_ON]->(c:RHACMComponent) WHERE c.label =~ '(?i).*{kg_label}.*' RETURN DISTINCT dep.label as dependent, dep.subsystem as subsystem",
                            'when': 'Find what breaks when this component fails (cascading impact). Use KG label.',
                            'example': "MATCH (dep:RHACMComponent)-[:DEPENDS_ON]->(c:RHACMComponent) WHERE c.label =~ '(?i).*Web Console.*' RETURN DISTINCT dep.label, dep.subsystem"
                        },
                        'get_dependencies': {
                            'query': "MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent) WHERE c.label =~ '(?i).*{kg_label}.*' RETURN dep.label as dependency, dep.subsystem as dep_subsystem",
                            'when': 'Find what this component depends on (root cause may be upstream). Use KG label.',
                            'example': "MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent) WHERE c.label =~ '(?i).*API Gateway Controller.*' RETURN dep.label, dep.subsystem"
                        },
                        'get_internal_data_flow': {
                            'query': "MATCH (c:RHACMComponent)-[r]->(dep:RHACMComponent) WHERE c.subsystem = '{subsystem}' AND dep.subsystem = '{subsystem}' RETURN DISTINCT c.label as source, type(r) as relationship, dep.label as target ORDER BY c.label",
                            'when': 'Trace internal data flow within a subsystem',
                            'example': "MATCH (c:RHACMComponent)-[r]->(dep:RHACMComponent) WHERE c.subsystem = 'Search' AND dep.subsystem = 'Search' RETURN DISTINCT c.label as source, type(r) as relationship, dep.label as target ORDER BY c.label"
                        },
                        'get_cross_subsystem_deps': {
                            'query': "MATCH (c:RHACMComponent)-[r]->(dep:RHACMComponent) WHERE c.subsystem = '{subsystem}' AND NOT dep.subsystem = '{subsystem}' RETURN DISTINCT dep.label as target, dep.subsystem as target_subsystem, type(r) as relationship",
                            'when': 'Find external dependencies of a subsystem (cross-cutting issues)',
                            'example': "MATCH (c:RHACMComponent)-[r]->(dep:RHACMComponent) WHERE c.subsystem = 'Search' AND NOT dep.subsystem = 'Search' RETURN DISTINCT dep.label, dep.subsystem, type(r)"
                        },
                        'find_common_dependency': {
                            'query': "MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent) WHERE c.label IN ['{kg_label1}', '{kg_label2}'] WITH common, count(DISTINCT c) as cnt WHERE cnt >= 2 RETURN common.label as shared_dependency",
                            'when': 'Multiple failing components — check if they share a root cause dependency. Use KG labels.',
                            'example': "MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent) WHERE c.label IN ['Web Console', 'API Gateway Controller'] WITH common, count(DISTINCT c) as cnt WHERE cnt >= 2 RETURN common.label"
                        }
                    },
                    'subsystem_reference': {
                        'Governance': {
                            'pod_names': ['grc-policy-propagator', 'config-policy-controller', 'governance-policy-framework'],
                            'kg_labels': ['Policy Propagator Controller', 'Config Policy Controller', 'Governance Policy Framework'],
                        },
                        'Search': {
                            'pod_names': ['search-api', 'search-collector', 'search-indexer'],
                            'kg_labels': ['API Gateway Controller', 'Collection Agent', 'Resource Indexer'],
                        },
                        'Cluster': {
                            'pod_names': ['cluster-curator', 'managedcluster-import-controller', 'cluster-lifecycle'],
                            'kg_labels': ['Cluster Curator', 'ManagedCluster Import Controller'],
                        },
                        'Provisioning': {
                            'pod_names': ['hive', 'hypershift', 'assisted-service'],
                            'kg_labels': ['Hive Controllers'],
                        },
                        'Observability': {
                            'pod_names': ['thanos-query', 'thanos-receive', 'metrics-collector'],
                            'kg_labels': ['Thanos Query', 'Thanos Receive'],
                        },
                        'Virtualization': {
                            'pod_names': ['kubevirt-operator', 'virt-api', 'virt-controller'],
                            'kg_labels': [],
                        },
                        'Console': {
                            'pod_names': ['console', 'console-api', 'acm-console'],
                            'kg_labels': ['Console API Server', 'Web Console'],
                        },
                        'Infrastructure': {
                            'pod_names': ['klusterlet', 'multicluster-engine', 'foundation'],
                            'kg_labels': [],
                        },
                    },
                    'when_unavailable': 'Check feature_knowledge.kg_status.available in core-data.json. If false, report to user: KG is not connected, Tier 3-4 investigation degraded, include kg_status.remediation in the analysis report. Do NOT silently skip KG queries — flag the gap explicitly in analysis_results.'
                },

                # Trigger matrix: when to call which MCP tool
                'trigger_matrix': {
                    'start_of_investigation': {
                        'tool': "mcp__acm-ui__set_acm_version(version='2.16')",
                        'condition': 'ALWAYS - first action in every investigation'
                    },
                    'vm_test_failure': {
                        'tool': 'mcp__acm-ui__detect_cnv_version()',
                        'condition': 'Test name or path contains vm, virtual, kubevirt, or fleet'
                    },
                    'selector_not_found': {
                        'tool': "mcp__acm-ui__search_code(query='{selector}', repo='acm')",
                        'condition': 'console_search.found == false - verify selector state in product code'
                    },
                    'selector_mismatch_confirmed': {
                        'tool': "mcp__acm-ui__get_acm_selectors(source='catalog', component='{area}')",
                        'condition': 'After confirming selector mismatch - get current correct selectors'
                    },
                    'component_in_error': {
                        'tool': "mcp__neo4j-rhacm__read_neo4j_cypher(query='...')",
                        'condition': 'detected_components present - query dependencies and subsystem'
                    },
                    'path_b2_investigation': {
                        'tool': "mcp__jira__search_issues(jql='...')",
                        'condition': 'Path B2 routing - search for feature story by Polarion ID'
                    },
                    'feature_story_found': {
                        'tool': "mcp__jira__get_issue(issue_key='ACM-XXXXX')",
                        'condition': 'After search_issues returns results - read full story details'
                    },
                    'any_classification': {
                        'tool': "mcp__jira__search_issues(jql='project = ACM AND type = Bug AND ...')",
                        'condition': 'Phase E4 - search for existing bugs before finalizing'
                    }
                }
            },

            # Pre-computed Context (from Phase 1)
            'precomputed_context': {
                'description': 'Phase 1 provides complete context upfront',
                'fields': {
                    'extracted_context.test_file': 'Actual test code (up to 200 lines)',
                    'extracted_context.page_objects': 'Imported selector definitions',
                    'extracted_context.console_search': 'Whether selector exists in console repo',
                    'parsed_stack_trace': 'Pre-parsed stack with root_cause_file, failing_selector',
                    'timeline_evidence': 'Git history for failing selectors',
                    'detected_components': 'Backend component names for Knowledge Graph',
                    'feature_knowledge.feature_readiness': 'Per-area prerequisite checks, unmet prereqs, pre-matched failure paths',
                    'feature_knowledge.investigation_playbooks': 'Architecture, prerequisites, failure paths per feature area',
                    'feature_knowledge.kg_dependency_context': 'Internal data flow and cross-subsystem dependencies per feature area (from KG)',
                    'feature_knowledge.kg_status': 'KG availability status. If available=false, warn user about degraded Tier 3-4 analysis and include remediation instructions in report.',
                    'cluster_access': 'API URL, username, password for Stage 2 re-authentication',
                },
                'fallback_to_repo_when': [
                    'test_file.truncated=true AND failing line beyond 200',
                    'Need deeper import chains not in page_objects',
                    'Need git history beyond timeline_evidence',
                    'console_search result ambiguous'
                ]
            },

            # Classification Guide
            'classification_guide': {
                'PRODUCT_BUG': 'Backend 500 errors, API broken, feature not working (needs 2+ sources)',
                'AUTOMATION_BUG': 'Selector not found, timeout on wait, test logic wrong (needs 2+ sources)',
                'INFRASTRUCTURE': 'Cluster down, network errors, provisioning failed (needs 2+ sources)',
                'NO_BUG': 'Feature prerequisite disabled (MCH component off) — test expects feature that is intentionally not enabled',
                'FLAKY': 'Test passes on retry, intermittent timing issue, no consistent root cause',
            },

            # Ruled Out Alternatives
            'ruled_out_alternatives': {
                'description': 'MUST document why other classifications dont fit',
                'required_for': ['PRODUCT_BUG', 'AUTOMATION_BUG', 'INFRASTRUCTURE'],
                'format': [
                    {'classification': 'PRODUCT_BUG', 'reason': 'No 500 errors, environment healthy'},
                    {'classification': 'INFRASTRUCTURE', 'reason': 'Cluster accessible, single test affected'}
                ]
            },

            # Output Schema Requirements
            'output_schema': {
                'required_top_level': [
                    'investigation_phases_completed (array of A,B,C,D,E)',
                    'per_test_analysis (array with evidence_sources)',
                    'summary.by_classification'
                ],
                'per_test_required': {
                    'test_name': 'string',
                    'classification': 'PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE | NO_BUG | FLAKY | MIXED | UNKNOWN',
                    'confidence': '0.0 to 1.0',
                    'evidence_sources': 'array (minimum 2 items) with source, finding, tier'
                },
                'per_test_recommended': {
                    'ruled_out_alternatives': 'array of {classification, reason}',
                    'jira_correlation': '{search_performed, related_issues, match_confidence}',
                    'reasoning': 'string or {summary, evidence, conclusion}'
                }
            },

            # Key Principles
            'key_principles': [
                '1. Systematic over ad-hoc - follow 5 phases in order, every time',
                '2. Multi-evidence required - single source is never sufficient',
                '3. MCP tools mandatory - use ACM-UI, Knowledge Graph, JIRA when available',
                '4. Cross-test correlation - patterns reveal root causes',
                '5. Rule out alternatives - document why other classifications dont fit',
                '6. JIRA validation - check for known issues before finalizing',
                '7. Evidence over intuition - every claim backed by data',
                '8. Deterministic order - same investigation path = reproducible results'
            ]
        }


def gather_all_data(jenkins_url: str, output_dir: str = './runs',
                    verbose: bool = False) -> Tuple[Path, Dict[str, Any]]:
    """Convenience function to gather all data."""
    gatherer = DataGatherer(output_dir=output_dir, verbose=verbose)
    return gatherer.gather_all(jenkins_url)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Z-Stream Analysis - Data Gathering Script (v3.5)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script gathers FACTUAL DATA and clones repos for AI analysis.
NO classification is performed - AI handles all classification.

Key Features (v3.5):
  - 5-Phase systematic investigation framework
  - Complete context extraction upfront
  - Multi-evidence validation requirements
  - Component extraction for Knowledge Graph
  - Optional ACM UI MCP for element discovery

Output Files:
  core-data.json         Primary data for AI (read this first)
  manifest.json          File index with workflow instructions
  repos/automation/      Full cloned automation repository
  repos/console/         Full cloned console repository
  console-log.txt        Full console output
  jenkins-build-info.json
  test-report.json
  environment-status.json

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
