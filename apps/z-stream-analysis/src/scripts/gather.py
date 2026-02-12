#!/usr/bin/env python3
"""
Data Gathering Script (v2.4 - Complete Context Upfront)

Collects FACTUAL DATA from Jenkins, environment, and repository.
Clones repositories to persistent location for AI to access during analysis.
Pre-computes evidence to accelerate Phase 2 AI analysis.
Extracts complete test context upfront for systematic AI analysis.

Key Changes in v2.4:
- Complete context extraction: Test file content, page objects, and console search results
- Eliminated on-demand repo access - AI receives everything upfront
- Enhanced extracted_context structure for each failed test

Key Changes in v2.3:
- Knowledge Graph integration: Component extraction from error messages
- Neo4j dependency queries for cascading failure detection

Key Changes in v2.2:
- Stack trace pre-parsing: Extracts root cause file:line and failing selectors
- Timeline evidence collection: Git history comparison for failing selectors
- CNV version detection: Auto-detects CNV version and clones kubevirt-plugin on correct branch
- Enhanced AI instructions: Documents new pre-computed data fields

Key Changes in v2.0:
- Repos cloned to runs/<dir>/repos/ (not /tmp) for AI access
- No pre-classification - AI performs all classification
- Investigation hints added to guide AI analysis
- Repos NOT cleaned up after gathering (AI needs full access)

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
import sys
import time
from dataclasses import asdict
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


class DataGatherer:
    """
    Data Gatherer v2.0 - Collects factual data and clones repos for AI access.

    This class performs MECHANICAL data collection only.
    NO classification or reasoning is done here - that's the AI's job.

    Key differences from v1.0:
    - Repos cloned to run directory (persistent, not /tmp)
    - No EvidencePackageBuilder (classification removed)
    - Investigation hints added for AI guidance
    - Repos NOT cleaned up (AI needs full access)
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
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        return logging.getLogger(__name__)

    def _mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data before saving."""
        return mask_sensitive_dict(data, SENSITIVE_PATTERNS)

    def _print_step(self, step: int, total: int, message: str):
        """Print progress step to user."""
        print(f"\n[{step}/{total}] {message}", flush=True)

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
        self.logger.info(f"Starting data gathering for: {jenkins_url}")

        print("\n" + "=" * 60)
        print("STAGE 1: DATA GATHERING")
        print("=" * 60)

        # Create run directory
        run_dir = self._create_run_directory(jenkins_url)
        self.logger.info(f"Output directory: {run_dir}")

        # Create repos subdirectory
        repos_dir = run_dir / 'repos'
        repos_dir.mkdir(parents=True, exist_ok=True)

        # Initialize gathered data structure
        self.gathered_data = {
            'metadata': {
                'jenkins_url': jenkins_url,
                'gathered_at': datetime.now().isoformat(),
                'gatherer_version': '2.4.0',
                'jenkins_api_available': is_jenkins_available(),
                'acm_ui_mcp_available': True,
                'knowledge_graph_available': True,
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

        total_steps = 8

        # Step 1: Gather Jenkins build info
        self._print_step(1, total_steps, "Fetching Jenkins build info...")
        self._gather_jenkins_build_info(jenkins_url, run_dir)

        # Step 2: Gather console log
        self._print_step(2, total_steps, "Downloading console log...")
        self._gather_console_log(jenkins_url, run_dir)

        # Step 3: Gather test report (CRITICAL for per-test analysis)
        self._print_step(3, total_steps, "Extracting test report...")
        self._gather_test_report(jenkins_url, run_dir)

        # Step 4: Gather environment status (optional)
        if not skip_environment:
            self._print_step(4, total_steps, "Checking cluster environment...")
            self._gather_environment_status(run_dir)
        else:
            self._print_step(4, total_steps, "Skipping environment check (--skip-env)")

        # Step 5: Clone repositories to run directory (optional)
        if not skip_repository:
            self._print_step(5, total_steps, "Cloning repositories...")
            self._clone_repositories(jenkins_url, run_dir)
        else:
            self._print_step(5, total_steps, "Skipping repository clone (--skip-repo)")

        # Step 6: Extract complete test context (AFTER repos are cloned)
        # This provides AI with all needed context upfront
        if not skip_repository:
            self._print_step(6, total_steps, "Extracting test context (code, selectors, imports)...")
            self._extract_complete_test_context(run_dir)
        else:
            self._print_step(6, total_steps, "Skipping context extraction (no repos)")

        # Step 7: Build element inventory from cloned repos (optional)
        if not skip_repository:
            self._print_step(7, total_steps, "Building element inventory...")
            self._gather_element_inventory(run_dir)
        else:
            self._print_step(7, total_steps, "Skipping element inventory (no repos)")

        # Step 8: Build investigation hints for AI
        self._print_step(8, total_steps, "Building investigation hints...")
        self._build_investigation_hints(run_dir)

        # Step 8b: Inject per-test temporal_summary into extracted_context
        # (runs after timeline evidence is collected in step 8)
        self._inject_temporal_summaries()

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
            params.get('CLUSTER_API_URL') or
            params.get('API_URL') or
            params.get('HUB_API_URL')
        )

        username = (
            params.get('CYPRESS_OPTIONS_HUB_USER') or
            params.get('CLUSTER_USER') or
            params.get('USERNAME') or
            params.get('HUB_USER')
        )

        password = (
            params.get('CYPRESS_OPTIONS_HUB_PASSWORD') or
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

        for i, test in enumerate(failed_tests):
            test_name = test.get('test_name', '')
            parsed_stack = test.get('parsed_stack_trace', {})

            self.logger.debug(f"Extracting context for: {test_name}")

            extracted_context = {
                'test_file': None,
                'page_objects': [],
                'console_search': None
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

            # Store extracted context in the test entry
            self.gathered_data['test_report']['failed_tests'][i]['extracted_context'] = extracted_context

        self.logger.info(f"Extracted context for {len(failed_tests)} failed tests")

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
        import subprocess

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
        and neighboring test IDs. Requires repos to be cloned (Step 5).
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
        self.gathered_data['metadata']['data_version'] = '2.4.0'

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
            'version': '2.4.0',
            'file_structure': 'multi-file-with-repos',
            'created_at': datetime.now().isoformat(),
            'acm_ui_mcp_available': True,
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
            'version': '2.5.0',
            'architecture': '5-phase-systematic-investigation',
            'purpose': 'Systematic deep investigation through 5 mandatory phases for 100% classification accuracy',

            # 5-Phase Framework Overview
            'investigation_framework': {
                'description': 'Every analysis MUST complete all 5 phases in order',
                'phases': {
                    'A': {
                        'name': 'Initial Assessment',
                        'purpose': 'Detect global patterns before individual analysis',
                        'steps': [
                            'A1. Check environment health (cluster_connectivity, environment_score)',
                            'A2. Detect failure patterns (mass timeouts, single selector, 500 errors)',
                            'A3. Scan cross-test correlations (shared selectors, components, feature areas)'
                        ]
                    },
                    'B': {
                        'name': 'Deep Investigation',
                        'purpose': 'Systematically gather ALL evidence for each test',
                        'steps': [
                            'B1. Analyze extracted_context (test_file, page_objects, console_search)',
                            'B2. Check timeline_evidence (element removed? changed?)',
                            'B3. Review console_log evidence (500 errors, network errors)',
                            'B4. Execute MCP queries (ACM-UI, Knowledge Graph)',
                            'B5. Analyze detected_components (backend component names)',
                            'B6. Deep dive repos/ when extracted_context insufficient'
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
                        'purpose': 'Apply classification with evidence matrix',
                        'steps': [
                            'D1. Check evidence sufficiency (2+ sources, no conflicts)',
                            'D2. Calculate confidence score',
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

            # MCP Tool Integration - Three MCP servers available for Phase 2 AI analysis
            # These tools are called natively by the Claude Code agent (not via Python).
            # Tool names use the format: mcp__<server>__<tool_name>
            'mcp_integration': {
                'available': {
                    'acm_ui': True,
                    'knowledge_graph': True,
                    'jira': True
                },
                'how_to_call': 'Use native MCP tool calls. Example: mcp__jira__search_issues(jql="project = ACM AND type = Bug")',

                # ACM-UI MCP Server (20 tools) - stolostron/console and kubevirt-plugin source code via GitHub
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

                # JIRA MCP Server (23 tools) - Full JIRA integration
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
                                'call': "mcp__jira__create_issue(project_key='ACM', summary='Component X returns 500', description='Found during z-stream analysis...', issue_type='Bug', priority='Major', components=['Search'], work_type='46653', due_date='2026-03-01')",
                                'purpose': 'Create new bug when definitive new issue found with no existing JIRA',
                                'when': 'Phase E6 - only when classification is definitive and no existing bug matches'
                            },
                            'update_issue': {
                                'call': "mcp__jira__update_issue(issue_key='ACM-12345', priority='Critical', components=['Search'], work_type='46653', due_date='2026-03-01')",
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
                    'call_format': "mcp__neo4j-rhacm__read_neo4j_cypher(query=\"MATCH (c:RHACMComponent) WHERE c.label =~ '(?i).*search-api.*' RETURN c.label, c.subsystem\")",
                    'use_cases': {
                        'phase_B5': 'Component dependency analysis - find what depends on failing component',
                        'phase_C2': 'Cascading failure detection - find common dependency across multiple failing components',
                        'phase_E0': 'Subsystem context building - get all components in a subsystem, understand component relationships'
                    },
                    'query_templates': {
                        'get_component_info': {
                            'query': "MATCH (c:RHACMComponent) WHERE c.label =~ '(?i).*{component}.*' RETURN c.label, c.subsystem, c.type",
                            'when': 'First query for any detected component - get subsystem and type',
                            'example': "MATCH (c:RHACMComponent) WHERE c.label =~ '(?i).*search-api.*' RETURN c.label, c.subsystem, c.type"
                        },
                        'get_dependents': {
                            'query': "MATCH (dep:RHACMComponent)-[:DEPENDS_ON]->(c:RHACMComponent) WHERE c.label =~ '(?i).*{component}.*' RETURN DISTINCT dep.label as dependent, dep.subsystem as subsystem",
                            'when': 'Find what breaks when this component fails (cascading impact)',
                            'example': "MATCH (dep:RHACMComponent)-[:DEPENDS_ON]->(c:RHACMComponent) WHERE c.label =~ '(?i).*search-api.*' RETURN DISTINCT dep.label, dep.subsystem"
                        },
                        'get_dependencies': {
                            'query': "MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent) WHERE c.label =~ '(?i).*{component}.*' RETURN dep.label as dependency, dep.subsystem as dep_subsystem",
                            'when': 'Find what this component depends on (root cause may be upstream)',
                            'example': "MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent) WHERE c.label =~ '(?i).*search-api.*' RETURN dep.label, dep.subsystem"
                        },
                        'get_subsystem_components': {
                            'query': "MATCH (c:RHACMComponent) WHERE c.subsystem = '{subsystem}' RETURN c.label, c.type",
                            'when': 'Get all components in a subsystem for comprehensive search',
                            'example': "MATCH (c:RHACMComponent) WHERE c.subsystem = 'Search' RETURN c.label, c.type"
                        },
                        'find_common_dependency': {
                            'query': "MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent) WHERE c.label IN ['{comp1}', '{comp2}'] WITH common, count(DISTINCT c) as cnt WHERE cnt >= 2 RETURN common.label as shared_dependency",
                            'when': 'Multiple failing components - check if they share a root cause dependency',
                            'example': "MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent) WHERE c.label IN ['console', 'search-api'] WITH common, count(DISTINCT c) as cnt WHERE cnt >= 2 RETURN common.label"
                        }
                    },
                    'subsystem_reference': {
                        'Governance': ['grc-policy-propagator', 'config-policy-controller', 'governance-policy-framework'],
                        'Search': ['search-api', 'search-collector', 'search-indexer'],
                        'Cluster': ['cluster-curator', 'managedcluster-import-controller', 'cluster-lifecycle'],
                        'Provisioning': ['hive', 'hypershift', 'assisted-service'],
                        'Observability': ['thanos-query', 'thanos-receive', 'metrics-collector'],
                        'Virtualization': ['kubevirt-operator', 'virt-api', 'virt-controller'],
                        'Console': ['console', 'console-api', 'acm-console'],
                        'Infrastructure': ['klusterlet', 'multicluster-engine', 'foundation']
                    },
                    'fallback_when_unavailable': 'Use the subsystem field from detected_components entries. This provides the subsystem name without the full component list or dependency chain.'
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
                    'detected_components': 'Backend component names for Knowledge Graph'
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
                'INFRASTRUCTURE': 'Cluster down, network errors, provisioning failed (needs 2+ sources)'
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
                    'classification': 'PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE | MIXED | UNKNOWN',
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
        description='Z-Stream Analysis - Data Gathering Script (v2.5)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script gathers FACTUAL DATA and clones repos for AI analysis.
NO classification is performed - AI handles all classification.

Key Features (v2.5):
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

        # Print summary
        print("\n" + "=" * 60)
        print("DATA GATHERING COMPLETE (v2.5)")
        print("=" * 60)
        print(f"\nOutput directory: {run_dir}")

        # Show integration status
        print(f"\nIntegrations:")
        print(f"  - ACM UI MCP: Available for Phase 2 AI analysis (20 tools)")
        print(f"  - Knowledge Graph: Available for Phase 2 AI analysis")
        print(f"  - JIRA MCP: Available for Phase 2 AI analysis (23 tools)")

        print(f"\nFiles generated:")
        print(f"  - core-data.json (primary data for AI)")
        print(f"  - manifest.json (file index)")
        if (run_dir / 'element-inventory.json').exists():
            print(f"  - element-inventory.json (element locations from cloned repos)")
        print(f"  - repos/automation/ (full cloned automation repo)")
        print(f"  - repos/console/ (full cloned console repo)")
        print(f"  - repos/kubevirt-plugin/ (cloned for VM tests only)")
        print(f"  - console-log.txt")
        print(f"  - jenkins-build-info.json")
        print(f"  - test-report.json")

        # Summary stats
        test_report = data.get('test_report', {})
        summary = test_report.get('summary', {})
        if summary.get('total_tests', 0) > 0:
            print(f"\nTest Summary:")
            print(f"  Total: {summary.get('total_tests', 0)}")
            print(f"  Failed: {summary.get('failed_count', 0)}")
            print(f"  Pass Rate: {summary.get('pass_rate', 0):.1f}%")

        failed_tests = test_report.get('failed_tests', [])
        if failed_tests:
            print(f"\nFailed Tests ({len(failed_tests)}):")
            for test in failed_tests[:5]:
                print(f"  - {test.get('test_name', 'Unknown')}")
            if len(failed_tests) > 5:
                print(f"  ... and {len(failed_tests) - 5} more")

        print("\n" + "=" * 60)
        print("NEXT STEP: AI reads core-data.json and investigates repos/")
        print("=" * 60 + "\n")

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
