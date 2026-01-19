#!/usr/bin/env python3
"""
Data Gathering Script
Collects all raw data from Jenkins, environment, and repository.

This script handles MECHANICAL tasks only - no analysis or classification.
AI (Claude Code) handles analytical tasks using the gathered data.

Usage:
    python -m src.scripts.gather <jenkins_url>
    python -m src.scripts.gather --url <jenkins_url> --output-dir ./runs

Output:
    Creates a run directory with multi-file structure:
    - core-data.json (primary data for AI - read this first)
    - manifest.json (file index)
    - repository-selectors.json (on-demand for element_not_found)
    - repository-test-files.json (on-demand for stack traces)
    - repository-metadata.json (repo summary)
    - raw-data.json (backward-compat stub)
    - jenkins-build-info.json
    - console-log.txt
    - test-report.json
    - environment-status.json (if cluster connected)
    - evidence-package.json (pre-calculated classification scores)
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

from src.services.jenkins_mcp_client import JenkinsMCPClient, is_mcp_available
from src.services.jenkins_intelligence_service import JenkinsIntelligenceService
from src.services.environment_validation_service import EnvironmentValidationService
from src.services.repository_analysis_service import RepositoryAnalysisService
from src.services.evidence_package_builder import EvidencePackageBuilder
from src.services.timeline_comparison_service import TimelineComparisonService
from src.services.stack_trace_parser import StackTraceParser
from src.services.shared_utils import mask_sensitive_dict


class DataGatherer:
    """
    Data Gatherer - Collects raw data from all sources.

    This class performs MECHANICAL data collection only.
    No analysis, classification, or reasoning is done here.
    That's the job of AI (Claude Code).
    """

    # Sensitive parameter patterns to mask
    SENSITIVE_PATTERNS = [
        'password', 'token', 'secret', 'key', 'credential',
        'api_token', 'apitoken', 'auth', 'bearer'
    ]

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
        
        # Initialize services
        self.jenkins_service = JenkinsIntelligenceService(use_mcp=True)
        self.env_service = EnvironmentValidationService()
        self.repo_service = RepositoryAnalysisService()
        self.evidence_builder = EvidencePackageBuilder()
        self.timeline_service = TimelineComparisonService()
        self.stack_parser = StackTraceParser()

        # Track what we've gathered
        self.gathered_data = {}

        # Track cloned paths for timeline comparison
        self.automation_clone_path = None
        
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
        """
        Mask sensitive data in the gathered data before saving.

        Uses shared_utils.mask_sensitive_dict to avoid code duplication.

        Args:
            data: Dictionary to mask

        Returns:
            Copy of data with sensitive values masked
        """
        return mask_sensitive_dict(data, self.SENSITIVE_PATTERNS)

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
        
        # Create run directory
        run_dir = self._create_run_directory(jenkins_url)
        self.logger.info(f"Output directory: {run_dir}")
        
        # Initialize gathered data structure
        self.gathered_data = {
            'metadata': {
                'jenkins_url': jenkins_url,
                'gathered_at': datetime.now().isoformat(),
                'gatherer_version': '1.0.0',
                'mcp_available': is_mcp_available()
            },
            'jenkins': {},
            'test_report': {},
            'console_log': {},
            'environment': {},
            'repository': {},
            'errors': []
        }
        
        # Step 1: Gather Jenkins build info
        self._gather_jenkins_build_info(jenkins_url, run_dir)
        
        # Step 2: Gather console log
        self._gather_console_log(jenkins_url, run_dir)
        
        # Step 3: Gather test report (CRITICAL for per-test analysis)
        self._gather_test_report(jenkins_url, run_dir)
        
        # Step 4: Gather environment status (optional)
        if not skip_environment:
            self._gather_environment_status(run_dir)
        
        # Step 5: Gather repository analysis (optional)
        if not skip_repository:
            self._gather_repository_analysis(jenkins_url, run_dir)

        # Step 6: Build evidence packages for failed tests
        self._build_evidence_packages(jenkins_url, run_dir)

        # Calculate gathering time
        gathering_time = time.time() - start_time
        self.gathered_data['metadata']['gathering_time_seconds'] = gathering_time

        # Save multi-file structure for AI analysis
        self._save_combined_data(run_dir)

        # Cleanup cloned repositories
        self._cleanup_repos()

        self.logger.info(f"Data gathering complete in {gathering_time:.2f}s")
        self.logger.info(f"Files saved to: {run_dir}")

        return run_dir, self.gathered_data

    def _cleanup_repos(self):
        """Cleanup cloned repositories to free disk space."""
        # Cleanup automation repo
        if self.automation_clone_path and self.automation_clone_path.exists():
            self.repo_service.cleanup_repository(str(self.automation_clone_path))
            self.automation_clone_path = None

        # Cleanup console repo
        self.timeline_service.cleanup()
    
    def _create_run_directory(self, jenkins_url: str) -> Path:
        """Create timestamped run directory."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Extract job name from URL
        job_name = "analysis"
        if '/job/' in jenkins_url:
            parts = jenkins_url.split('/job/')
            if len(parts) > 1:
                # Get the last job segment
                job_parts = [p.split('/')[0] for p in parts[1:] if p]
                job_name = '_'.join(job_parts)[:50]  # Limit length
        
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
            # Use the Jenkins intelligence service to fetch build info
            intelligence = self.jenkins_service.analyze_jenkins_url(jenkins_url)
            
            # Extract metadata
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
                'confidence_score': intelligence.confidence_score,
                'evidence_sources': intelligence.evidence_sources
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
            # Try MCP first
            mcp_client = JenkinsMCPClient()
            if mcp_client.is_available:
                console_output = mcp_client.get_console_output(jenkins_url)
            else:
                # Fall back to the service's internal method
                console_output = self.jenkins_service._fetch_console_log(jenkins_url)
            
            if console_output:
                # Save full console log
                console_path = run_dir / 'console-log.txt'
                console_path.write_text(console_output)
                
                # Extract key info for gathered data
                lines = console_output.split('\n')
                error_lines = [l for l in lines if 'error' in l.lower() or 'fail' in l.lower()]
                warning_lines = [l for l in lines if 'warn' in l.lower()]
                
                self.gathered_data['console_log'] = {
                    'file_path': 'console-log.txt',
                    'total_lines': len(lines),
                    'error_lines_count': len(error_lines),
                    'warning_lines_count': len(warning_lines),
                    'key_errors': error_lines[:20],  # First 20 error lines
                    'snippet_start': '\n'.join(lines[:50]),  # First 50 lines
                    'snippet_end': '\n'.join(lines[-50:])    # Last 50 lines
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
        """
        Gather test report - CRITICAL for per-test analysis.
        
        This extracts each failed test with full details for AI to analyze individually.
        """
        self.logger.info("Gathering test report (for per-test analysis)...")
        
        try:
            # Fetch and analyze test report
            test_report = self.jenkins_service._fetch_and_analyze_test_report(jenkins_url)
            
            if test_report:
                # Build structured data for AI
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
                
                # Extract each failed test with FULL details for AI analysis
                for test in test_report.failed_tests:
                    test_entry = {
                        'test_name': test.test_name,
                        'class_name': test.class_name,
                        'status': test.status,
                        'duration_seconds': test.duration,
                        'error_message': test.error_message,
                        'stack_trace': test.stack_trace,
                        'failure_type': test.failure_type,
                        # Pre-classification from script (AI will verify/override)
                        'preliminary_classification': test.classification,
                        'preliminary_confidence': test.classification_confidence,
                        'preliminary_reasoning': test.classification_reasoning,
                        'preliminary_fix': test.recommended_fix
                    }
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
        """
        Extract target cluster URL and credentials from Jenkins parameters.

        Looks for common parameter names used in test pipelines:
        - CYPRESS_HUB_API_URL / CLUSTER_API_URL / API_URL
        - CYPRESS_OPTIONS_HUB_USER / CLUSTER_USER / USERNAME
        - CYPRESS_OPTIONS_HUB_PASSWORD / CLUSTER_PASSWORD / PASSWORD

        Returns:
            Tuple of (api_url, username, password) - any can be None if not found
        """
        jenkins_data = self.gathered_data.get('jenkins', {})
        params = jenkins_data.get('parameters', {})

        # Try different parameter names for API URL
        api_url = (
            params.get('CYPRESS_HUB_API_URL') or
            params.get('CLUSTER_API_URL') or
            params.get('API_URL') or
            params.get('HUB_API_URL')
        )

        # Try different parameter names for username
        username = (
            params.get('CYPRESS_OPTIONS_HUB_USER') or
            params.get('CLUSTER_USER') or
            params.get('USERNAME') or
            params.get('HUB_USER')
        )

        # Try different parameter names for password
        password = (
            params.get('CYPRESS_OPTIONS_HUB_PASSWORD') or
            params.get('CLUSTER_PASSWORD') or
            params.get('PASSWORD') or
            params.get('HUB_PASSWORD')
        )

        if api_url:
            self.logger.info(f"Found target cluster URL from Jenkins: {api_url}")
        if username:
            self.logger.info(f"Found cluster username from Jenkins: {username}")
        if password:
            self.logger.info("Found cluster password from Jenkins: ***")

        return api_url, username, password

    def _gather_environment_status(self, run_dir: Path):
        """
        Gather environment/cluster status.

        IMPORTANT: Uses the TARGET cluster from Jenkins parameters, not the local
        kubeconfig. All operations are READ-ONLY.
        """
        self.logger.info("Gathering environment status...")

        try:
            # Extract target cluster credentials from Jenkins parameters
            api_url, username, password = self._extract_cluster_credentials()

            if api_url and username and password:
                self.logger.info(f"Validating TARGET cluster: {api_url}")
            else:
                self.logger.warning(
                    "Target cluster credentials not found in Jenkins parameters. "
                    "Falling back to local kubeconfig (may be incorrect cluster)."
                )

            # Validate environment - pass target cluster if available
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

            if result.target_cluster_used:
                self.logger.info(f"Environment score: {result.environment_score:.1%} (target cluster)")
            else:
                self.logger.info(f"Environment score: {result.environment_score:.1%} (local kubeconfig)")

        except Exception as e:
            error_msg = f"Failed to gather environment status: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['errors'].append(error_msg)
            self.gathered_data['environment'] = {
                'error': error_msg,
                'note': 'Cluster may not be accessible from this machine'
            }
    
    def _extract_repo_info_from_console(self, run_dir: Path) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract repository URL and branch from console log.

        Parses git checkout commands in Jenkins console output to find:
        - Repository URL (from 'git fetch' or 'Checking out git' lines)
        - Branch name (from build parameters or checkout commands)

        Returns:
            Tuple of (repo_url, branch) - either can be None if not found
        """
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
                self.logger.info(f"Extracted repo URL from checkout: {repo_url}")

            # Pattern 2: "git fetch ... https://github.com/org/repo.git"
            if not repo_url:
                fetch_pattern = r'git fetch[^\n]+(https?://github\.com/[^\s]+\.git)'
                match = re.search(fetch_pattern, content)
                if match:
                    repo_url = match.group(1)
                    self.logger.info(f"Extracted repo URL from git fetch: {repo_url}")

            # Pattern 3: "git config remote.origin.url https://..."
            if not repo_url:
                origin_pattern = r'git config remote\.origin\.url\s+(https?://[^\s]+)'
                match = re.search(origin_pattern, content)
                if match:
                    repo_url = match.group(1)
                    self.logger.info(f"Extracted repo URL from origin config: {repo_url}")

            # Extract branch from various sources
            # Pattern 1: "origin/branch-name" in checkout line
            branch_pattern = r'Checking out Revision [a-f0-9]+ \(origin/([^\)]+)\)'
            match = re.search(branch_pattern, content)
            if match:
                branch = match.group(1)
                self.logger.info(f"Extracted branch from checkout: {branch}")

            # Pattern 2: From build parameters (GIT_BRANCH)
            if not branch:
                # Check gathered jenkins data for branch
                jenkins_data = self.gathered_data.get('jenkins', {})
                params = jenkins_data.get('parameters', {})
                if params.get('GIT_BRANCH'):
                    branch = params.get('GIT_BRANCH')
                    self.logger.info(f"Extracted branch from build params: {branch}")

            # Pattern 3: "--branch release-X.Y" in console
            if not branch:
                branch_arg_pattern = r'--branch\s+([^\s]+)'
                match = re.search(branch_arg_pattern, content)
                if match:
                    branch = match.group(1)
                    self.logger.info(f"Extracted branch from git command: {branch}")

        except Exception as e:
            self.logger.warning(f"Error extracting repo info from console: {e}")

        return repo_url, branch

    def _gather_repository_analysis(self, jenkins_url: str, run_dir: Path):
        """Gather repository analysis."""
        self.logger.info("Gathering repository analysis...")

        try:
            # Extract job name to infer repo
            job_name = self.gathered_data['jenkins'].get('job_name', '')

            # Try to extract repo URL and branch from console log
            repo_url, branch = self._extract_repo_info_from_console(run_dir)

            if repo_url:
                self.logger.info(f"Using repo from console log: {repo_url} (branch: {branch})")
            else:
                self.logger.info(f"No repo URL in console, will try to infer from job: {job_name}")

            # Analyze repository - prefer extracted URL, fall back to job name inference
            result = self.repo_service.analyze_repository(
                repo_url=repo_url,
                branch=branch,
                job_name=job_name
            )

            if result.repository_cloned:
                # Store automation clone path for timeline comparison
                self.automation_clone_path = Path(result.clone_path)
                self.timeline_service.set_automation_path(self.automation_clone_path)

                repo_data = self.repo_service.to_dict(result)

                # Build selector lookup for AI
                selector_lookup = {}
                for tf in result.test_files:
                    for selector in tf.selectors:
                        if selector not in selector_lookup:
                            selector_lookup[selector] = []
                        selector_lookup[selector].append(tf.path)

                repo_data['selector_lookup'] = selector_lookup

                self.gathered_data['repository'] = repo_data

                # Save to file
                output_path = run_dir / 'repository-analysis.json'
                output_path.write_text(json.dumps(repo_data, indent=2, default=str))

                self.logger.info(f"Repository: {len(result.test_files)} test files found")

                # Clone console repo for timeline comparison
                self._clone_console_repo(branch or 'main', run_dir)

                # Cleanup automation repo after timeline comparison is done
                # (moved to end of gather_all to keep it available for evidence building)
            else:
                self.gathered_data['repository'] = {
                    'repository_cloned': False,
                    'errors': result.analysis_errors
                }
                self.logger.warning("Repository could not be cloned")

        except Exception as e:
            error_msg = f"Failed to gather repository analysis: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['errors'].append(error_msg)
            self.gathered_data['repository'] = {
                'error': error_msg,
                'note': 'Repository analysis skipped'
            }

    def _clone_console_repo(self, branch: str, run_dir: Path):
        """
        Clone the stolostron/console repo for timeline comparison.

        Args:
            branch: Branch to checkout (should match automation branch)
            run_dir: Run directory for saving data
        """
        self.logger.info(f"Cloning console repo for timeline comparison (branch: {branch})...")

        try:
            console_path, error = self.timeline_service.clone_console_repo(branch)

            if error:
                self.logger.warning(f"Could not clone console repo: {error}")
                self.gathered_data['timeline_comparison'] = {
                    'console_cloned': False,
                    'error': error
                }
                return

            self.logger.info(f"Console repo cloned to: {console_path}")
            self.gathered_data['timeline_comparison'] = {
                'console_cloned': True,
                'console_path': str(console_path),
                'branch': branch
            }

        except Exception as e:
            error_msg = f"Failed to clone console repo: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['timeline_comparison'] = {
                'console_cloned': False,
                'error': error_msg
            }

    def _build_evidence_packages(self, jenkins_url: str, run_dir: Path):
        """
        Build evidence packages for each failed test.

        Uses the classification decision matrix and confidence calculator
        to provide pre-calculated scores for AI to use or verify.

        Also performs timeline comparison for element_not_found errors.
        """
        self.logger.info("Building evidence packages for failed tests...")

        try:
            test_report = self.gathered_data.get('test_report', {})
            failed_tests = test_report.get('failed_tests', [])

            if not failed_tests:
                self.logger.info("No failed tests - skipping evidence package building")
                self.gathered_data['evidence_package'] = {
                    'test_failures': [],
                    'summary': {
                        'total_failures': 0,
                        'by_classification': {},
                        'overall_classification': None,
                        'overall_confidence': 0.0
                    }
                }
                return

            # Build evidence package using the service
            build_info = {
                'build_number': self.gathered_data.get('jenkins', {}).get('build_number', 0),
                'result': self.gathered_data.get('jenkins', {}).get('build_result', 'UNKNOWN'),
                'branch': self.gathered_data.get('jenkins', {}).get('branch'),
                'timestamp': self.gathered_data.get('metadata', {}).get('gathered_at', ''),
            }

            env_data = {
                'healthy': self.gathered_data.get('environment', {}).get('environment_score', 1.0) > 0.5,
                'accessible': not self.gathered_data.get('environment', {}).get('error'),
                'api_accessible': True,
                'target_cluster_used': self.gathered_data.get('environment', {}).get('target_cluster_used', False),
                'cluster_url': self.gathered_data.get('environment', {}).get('cluster_url'),
                'errors': self.gathered_data.get('environment', {}).get('errors', []),
            }

            repo_data = self.gathered_data.get('repository', {})
            console_data = self.gathered_data.get('console_log', {})

            package = self.evidence_builder.build_package(
                jenkins_url=jenkins_url,
                build_info=build_info,
                failed_tests=failed_tests,
                environment_data=env_data,
                repository_data=repo_data,
                console_data=console_data
            )

            # Convert to dict
            evidence_dict = package.to_dict()

            # Perform timeline comparison for element_not_found errors
            timeline_data = self.gathered_data.get('timeline_comparison', {})
            if timeline_data.get('console_cloned'):
                self._enhance_with_timeline_comparison(evidence_dict, failed_tests, env_data)

            # Analyze timeout patterns
            timeout_result = self.timeline_service.analyze_timeout_pattern(
                failed_tests,
                env_healthy=env_data.get('healthy', True)
            )
            evidence_dict['timeout_analysis'] = timeout_result.to_dict()

            self.gathered_data['evidence_package'] = evidence_dict

            # Save evidence package separately
            output_path = run_dir / 'evidence-package.json'
            output_path.write_text(json.dumps(evidence_dict, indent=2, default=str))

            self.logger.info(f"Evidence packages built for {len(failed_tests)} failed tests")

            # Log summary of classifications
            by_classification = evidence_dict.get('summary', {}).get('by_classification', {})
            if by_classification:
                self.logger.info(f"Pre-calculated classifications: {by_classification}")

        except Exception as e:
            error_msg = f"Failed to build evidence packages: {str(e)}"
            self.logger.warning(error_msg)
            self.gathered_data['errors'].append(error_msg)
            self.gathered_data['evidence_package'] = {
                'error': error_msg,
                'note': 'Evidence package building failed - AI will classify from raw data'
            }

    def _enhance_with_timeline_comparison(
        self,
        evidence_dict: Dict[str, Any],
        failed_tests: List[Dict[str, Any]],
        env_data: Dict[str, Any]
    ):
        """
        Enhance evidence package with timeline comparison for element_not_found errors.

        Compares modification dates between automation and console repos to
        provide definitive classification.
        """
        self.logger.info("Performing timeline comparison for element_not_found errors...")

        timeline_results = []
        reclassified_count = 0

        test_failures = evidence_dict.get('test_failures', [])

        for i, test in enumerate(failed_tests):
            error_msg = test.get('error_message', '')

            # Check if this is an element_not_found error
            if 'element' in error_msg.lower() and ('not found' in error_msg.lower() or 'never found' in error_msg.lower()):
                # Extract selector from error message
                selector = self._extract_selector_from_error(error_msg)

                if selector:
                    self.logger.info(f"Timeline comparison for selector: {selector}")

                    # Compare timelines
                    comparison = self.timeline_service.compare_timelines(selector)
                    timeline_results.append(comparison.to_dict())

                    # Update evidence package with timeline data
                    if i < len(test_failures):
                        test_failures[i]['timeline_comparison'] = comparison.to_dict()

                        # Reclassify if timeline provides high confidence
                        if comparison.confidence >= 0.80:
                            original = test_failures[i].get('final_classification', 'UNKNOWN')
                            if original != comparison.classification:
                                self.logger.info(
                                    f"Reclassifying {test.get('test_name', 'Unknown')}: "
                                    f"{original} -> {comparison.classification} "
                                    f"(timeline confidence: {comparison.confidence:.0%})"
                                )
                                test_failures[i]['final_classification'] = comparison.classification
                                test_failures[i]['final_confidence'] = comparison.confidence
                                test_failures[i]['reasoning'] = comparison.reasoning
                                test_failures[i]['timeline_reclassified'] = True
                                reclassified_count += 1

        # Update summary if any tests were reclassified
        if reclassified_count > 0:
            # Recount classifications
            by_classification = {}
            for tf in test_failures:
                cls = tf.get('final_classification', 'UNKNOWN')
                by_classification[cls] = by_classification.get(cls, 0) + 1

            evidence_dict['summary']['by_classification'] = by_classification
            if by_classification:
                evidence_dict['summary']['overall_classification'] = max(
                    by_classification, key=by_classification.get
                )

            self.logger.info(f"Timeline comparison reclassified {reclassified_count} test(s)")
            self.logger.info(f"Updated classifications: {by_classification}")

        # Store timeline results
        evidence_dict['timeline_comparisons'] = timeline_results

    def _extract_selector_from_error(self, error_message: str) -> Optional[str]:
        """
        Extract selector from error message.

        Uses StackTraceParser's method to avoid code duplication.
        """
        return self.stack_parser.extract_failing_selector(error_message)

    def _save_combined_data(self, run_dir: Path):
        """
        Save data in multi-file structure to stay under token limits.

        Creates:
        - manifest.json: Index file (~150 tokens)
        - core-data.json: Essential analysis data (~5,500 tokens)
        - repository-metadata.json: Repo summary (~800 tokens)
        - repository-test-files.json: Test file details (~7,000 tokens)
        - repository-selectors.json: Selector lookup (~7,500 tokens)
        - raw-data.json: Backward-compat stub (~200 tokens)
        """
        self.logger.info("Saving data in multi-file structure...")

        # Add final metadata
        self.gathered_data['metadata']['status'] = 'complete'
        self.gathered_data['metadata']['data_version'] = '2.0.0'
        self.gathered_data['metadata']['file_structure'] = 'multi-file'

        # Mask sensitive data before saving
        masked_data = self._mask_sensitive_data(self.gathered_data)

        # Build and save each file
        manifest = self._build_manifest(run_dir)
        core_data = self._build_core_data(masked_data)
        repo_metadata = self._build_repository_metadata(masked_data)
        repo_test_files = self._build_repository_test_files(masked_data)
        repo_selectors = self._build_repository_selectors(masked_data)

        # Save all files
        files_saved = []

        # 1. manifest.json
        manifest_path = run_dir / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
        files_saved.append('manifest.json')

        # 2. core-data.json
        core_path = run_dir / 'core-data.json'
        core_path.write_text(json.dumps(core_data, indent=2, default=str))
        files_saved.append('core-data.json')

        # 3. repository-metadata.json
        repo_meta_path = run_dir / 'repository-metadata.json'
        repo_meta_path.write_text(json.dumps(repo_metadata, indent=2, default=str))
        files_saved.append('repository-metadata.json')

        # 4. repository-test-files.json
        repo_files_path = run_dir / 'repository-test-files.json'
        repo_files_path.write_text(json.dumps(repo_test_files, indent=2, default=str))
        files_saved.append('repository-test-files.json')

        # 5. repository-selectors.json
        repo_selectors_path = run_dir / 'repository-selectors.json'
        repo_selectors_path.write_text(json.dumps(repo_selectors, indent=2, default=str))
        files_saved.append('repository-selectors.json')

        # 6. raw-data.json (backward-compat stub)
        self._save_legacy_raw_data_stub(run_dir, files_saved)

        # Log file sizes
        self._log_file_sizes(run_dir, files_saved)

        self.logger.info(f"Saved multi-file structure: {len(files_saved)} files")
        self.logger.info("Sensitive credentials have been masked in output")

    def _build_manifest(self, run_dir: Path) -> Dict[str, Any]:
        """Build the manifest.json index file."""
        return {
            'version': '2.0.0',
            'file_structure': 'multi-file',
            'created_at': datetime.now().isoformat(),
            'files': {
                'core-data.json': {
                    'description': 'Essential analysis data (metadata, jenkins, test_report, console_log, environment, evidence_package)',
                    'required': True,
                    'load_first': True
                },
                'repository-metadata.json': {
                    'description': 'Repository summary without large arrays',
                    'required': False,
                    'load_on_demand': True
                },
                'repository-test-files.json': {
                    'description': 'Test file details with selectors per file',
                    'required': False,
                    'load_on_demand': True,
                    'use_case': 'Stack trace analysis referencing test files'
                },
                'repository-selectors.json': {
                    'description': 'Selector lookup for element_not_found debugging',
                    'required': False,
                    'load_on_demand': True,
                    'use_case': 'Element not found errors'
                }
            },
            'workflow': [
                '1. Read core-data.json first (contains all primary analysis data)',
                '2. Check evidence_package.test_failures for pre-calculated classifications',
                '3. For element_not_found errors, load repository-selectors.json',
                '4. For stack trace analysis, load repository-test-files.json',
                '5. Cross-reference with console_log.key_errors',
                '6. Classify each test and save analysis-results.json'
            ],
            'backward_compatibility': {
                'raw-data.json': 'Stub file pointing to new structure',
                'legacy_support': True
            }
        }

    def _build_core_data(self, masked_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build core-data.json with essential analysis data."""
        # Extract repository summary without large arrays
        repo_data = masked_data.get('repository', {})
        repo_summary = {
            'repository_url': repo_data.get('repository_url'),
            'branch': repo_data.get('branch'),
            'commit_sha': repo_data.get('commit_sha'),
            'repository_cloned': repo_data.get('repository_cloned', False),
            'test_file_count': len(repo_data.get('test_files', [])),
            'selector_count': len(repo_data.get('selector_lookup', {})),
            'errors': repo_data.get('errors', [])
        }

        core_data = {
            'metadata': masked_data.get('metadata', {}),
            'jenkins': masked_data.get('jenkins', {}),
            'test_report': masked_data.get('test_report', {}),
            'console_log': masked_data.get('console_log', {}),
            'environment': masked_data.get('environment', {}),
            'evidence_package': masked_data.get('evidence_package', {}),
            'timeline_comparison': masked_data.get('timeline_comparison', {}),
            'repository_summary': repo_summary,
            'errors': masked_data.get('errors', []),
            'ai_instructions': self._build_multi_file_ai_instructions()
        }

        return core_data

    def _build_repository_metadata(self, masked_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build repository-metadata.json with repo summary."""
        repo_data = masked_data.get('repository', {})

        return {
            'repository_url': repo_data.get('repository_url'),
            'branch': repo_data.get('branch'),
            'commit_sha': repo_data.get('commit_sha'),
            'repository_cloned': repo_data.get('repository_cloned', False),
            'clone_path': repo_data.get('clone_path'),
            'test_file_count': len(repo_data.get('test_files', [])),
            'selector_count': len(repo_data.get('selector_lookup', {})),
            'dependency_analysis': repo_data.get('dependency_analysis', {}),
            'analysis_errors': repo_data.get('analysis_errors', []),
            'errors': repo_data.get('errors', [])
        }

    def _build_repository_test_files(self, masked_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build repository-test-files.json with test file details."""
        repo_data = masked_data.get('repository', {})
        test_files = repo_data.get('test_files', [])

        return {
            'total_count': len(test_files),
            'test_files': test_files
        }

    def _build_repository_selectors(self, masked_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build repository-selectors.json with selector lookup."""
        repo_data = masked_data.get('repository', {})
        selector_lookup = repo_data.get('selector_lookup', {})

        return {
            'total_selectors': len(selector_lookup),
            'selector_lookup': selector_lookup
        }

    def _build_multi_file_ai_instructions(self) -> Dict[str, Any]:
        """Build AI instructions for multi-file structure."""
        return {
            'version': '2.0.0',
            'file_structure': 'multi-file',
            'purpose': 'This file (core-data.json) contains all primary analysis data',
            'workflow': [
                '1. This file (core-data.json) contains all primary analysis data',
                '2. Check evidence_package.test_failures for pre-calculated classifications',
                '3. For element_not_found errors, load repository-selectors.json on-demand',
                '4. For stack trace analysis, load repository-test-files.json on-demand',
                '5. Cross-reference with console_log.key_errors',
                '6. Classify each test as PRODUCT_BUG, AUTOMATION_BUG, or INFRASTRUCTURE',
                '7. Save analysis-results.json following the schema'
            ],
            'on_demand_files': {
                'repository-selectors.json': 'Load when analyzing element_not_found failures',
                'repository-test-files.json': 'Load when stack trace references test files',
                'repository-metadata.json': 'Load for repository details'
            },
            'evidence_package_note': 'The evidence_package section contains pre-calculated classification scores using a formal decision matrix. Use these as a starting point and verify/adjust as needed.',
            'output_schema': {
                'required_fields': {
                    'per_test_analysis': 'Array of test objects (required)',
                    'summary': 'Object with classification breakdown (required)',
                    'summary.by_classification': 'Classification counts (required)'
                },
                'per_test_fields': {
                    'test_name': 'string (required) - from test_report.failed_tests',
                    'classification': 'PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE (required)',
                    'confidence': '0.0 to 1.0 (required)',
                    'reasoning': 'string (recommended) - why this classification',
                    'evidence': 'array of strings (recommended) - supporting evidence',
                    'recommended_fix': 'string (recommended) - how to fix',
                    'owner': 'Product Team | Automation Team | Platform Team (optional)',
                    'priority': 'CRITICAL | HIGH | MEDIUM | LOW (optional)'
                },
                'summary_fields': {
                    'by_classification': '{PRODUCT_BUG: n, AUTOMATION_BUG: n, INFRASTRUCTURE: n} (required)',
                    'overall_classification': 'dominant classification (recommended)',
                    'overall_confidence': '0.0 to 1.0 (recommended)'
                }
            },
            'classification_guide': {
                'PRODUCT_BUG': 'Server 500 errors, API broken, feature not working, backend issues',
                'AUTOMATION_BUG': 'Selector not found, timeout on wait, test logic wrong, stale selectors',
                'INFRASTRUCTURE': 'Cluster down, network errors, provisioning failed, resource limits'
            },
            'validation_note': 'analysis-results.json will be validated before report generation.',
            'template_file': 'See src/schemas/analysis_results_template.json for complete example'
        }

    def _save_legacy_raw_data_stub(self, run_dir: Path, files_saved: List[str]):
        """Save backward-compatible raw-data.json stub."""
        stub = {
            '_migration_version': '2.0.0',
            '_migration_note': 'Data has been split into multiple files for token efficiency',
            '_primary_file': 'core-data.json',
            '_load_instructions': [
                'For AI analysis, read core-data.json instead',
                'This stub exists for backward compatibility only'
            ],
            'files': files_saved,
            'metadata': {
                'jenkins_url': self.gathered_data.get('metadata', {}).get('jenkins_url'),
                'gathered_at': self.gathered_data.get('metadata', {}).get('gathered_at'),
                'file_structure': 'multi-file',
                'data_version': '2.0.0'
            }
        }

        stub_path = run_dir / 'raw-data.json'
        stub_path.write_text(json.dumps(stub, indent=2, default=str))

    def _log_file_sizes(self, run_dir: Path, files: List[str]):
        """Log file sizes for verification."""
        total_size = 0
        for filename in files:
            filepath = run_dir / filename
            if filepath.exists():
                size = filepath.stat().st_size
                total_size += size
                # Estimate tokens (~4 chars per token)
                est_tokens = size // 4
                self.logger.debug(f"  {filename}: {size:,} bytes (~{est_tokens:,} tokens)")

        self.logger.info(f"Total data size: {total_size:,} bytes")


def gather_all_data(jenkins_url: str, output_dir: str = './runs', 
                    verbose: bool = False) -> Tuple[Path, Dict[str, Any]]:
    """
    Convenience function to gather all data.
    
    Args:
        jenkins_url: Jenkins build URL
        output_dir: Output directory
        verbose: Enable verbose logging
        
    Returns:
        Tuple of (run_directory, gathered_data)
    """
    gatherer = DataGatherer(output_dir=output_dir, verbose=verbose)
    return gatherer.gather_all(jenkins_url)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Z-Stream Analysis - Data Gathering Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script gathers RAW DATA only. No analysis or classification is performed.
AI (Claude Code) will analyze the gathered data and provide classifications.

Output Files (multi-file structure):
  core-data.json             Primary data for AI (read this first)
  manifest.json              File index with workflow instructions
  repository-selectors.json  Selector lookup (on-demand for element_not_found)
  repository-test-files.json Test file details (on-demand for stack traces)
  repository-metadata.json   Repository summary
  raw-data.json              Backward-compat stub
  evidence-package.json      Pre-calculated classification scores
  jenkins-build-info.json    Jenkins build metadata
  console-log.txt            Full console output
  test-report.json           Test report with per-test details
  environment-status.json    Cluster health status

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
    parser.add_argument('--skip-repo', action='store_true', help='Skip repository analysis')
    
    args = parser.parse_args()
    
    jenkins_url = args.url or args.url_flag
    
    if not jenkins_url:
        parser.print_help()
        print("\nError: Jenkins URL is required", file=sys.stderr)
        sys.exit(1)
    
    # Validate URL
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
        print("DATA GATHERING COMPLETE")
        print("=" * 60)
        print(f"\nOutput directory: {run_dir}")
        print(f"\nFiles generated (multi-file structure):")
        print(f"  - core-data.json (primary data for AI - read this first)")
        print(f"  - manifest.json (file index)")
        print(f"  - repository-selectors.json (on-demand for element_not_found)")
        print(f"  - repository-test-files.json (on-demand for stack traces)")
        print(f"  - repository-metadata.json (repo summary)")
        print(f"  - raw-data.json (backward-compat stub)")
        print(f"  - jenkins-build-info.json")
        print(f"  - console-log.txt")
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
        print("NEXT STEP: AI analyzes core-data.json")
        print("(Load repository-selectors.json on-demand for element_not_found errors)")
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
