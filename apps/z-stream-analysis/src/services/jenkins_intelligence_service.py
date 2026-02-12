#!/usr/bin/env python3
"""
Jenkins Intelligence Service
Core service for extracting intelligence from Jenkins pipeline failures

Authentication Priority:
    1. JenkinsAPIClient (checks: constructor args > env vars > config file)
    2. Environment variables: JENKINS_USER and JENKINS_API_TOKEN
    3. Constructor arguments: username and api_token

Uses JenkinsAPIClient for all Jenkins REST API interactions.
"""

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass, asdict, field
from typing import Callable, Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

# Import stack trace parser
from .stack_trace_parser import StackTraceParser, ParsedStackTrace

# Import shared utilities (replaces duplicate functions)
from .shared_utils import (
    get_jenkins_credentials,
    get_auth_header,
    run_subprocess,
    build_curl_command,
    parse_json_response,
    TIMEOUTS,
)

# Import Jenkins API client (lazy import to avoid circular dependencies)
_api_client = None


def get_jenkins_client():
    """Get the Jenkins API client, lazy loading to avoid circular imports."""
    global _api_client
    if _api_client is None:
        try:
            from .jenkins_api_client import JenkinsAPIClient
            _api_client = JenkinsAPIClient()
        except ImportError:
            _api_client = None
    return _api_client


# Note: get_jenkins_credentials and get_auth_header are now imported from shared_utils


@dataclass
class JenkinsTestCaseFailure:
    """
    Individual test case failure details.

    Note: Named with 'Jenkins' prefix to avoid pytest collection warnings
    (pytest tries to collect classes starting with 'Test' as test classes).
    """
    test_name: str
    class_name: str
    status: str  # FAILED, REGRESSION, PASSED, SKIPPED
    duration: float
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None  # Full stack trace (no truncation)
    failure_type: Optional[str] = None  # timeout, element_not_found, network, assertion, etc.
    # Parsed stack trace data
    parsed_stack_trace: Optional[Dict[str, Any]] = None
    root_cause_file: Optional[str] = None
    root_cause_line: Optional[int] = None
    failing_selector: Optional[str] = None


# Short alias used throughout codebase (avoids pytest collection warnings on 'Test' prefix)
TestCaseFailure = JenkinsTestCaseFailure


@dataclass
class JenkinsTestReport:
    """
    Jenkins test report summary.

    Note: Named with 'Jenkins' prefix to avoid pytest collection warnings
    (pytest tries to collect classes starting with 'Test' as test classes).
    """
    total_tests: int
    passed_count: int
    failed_count: int
    skipped_count: int
    pass_rate: float
    failed_tests: List[JenkinsTestCaseFailure]
    duration: float


# Short alias used throughout codebase (avoids pytest collection warnings on 'Test' prefix)
TestReport = JenkinsTestReport


@dataclass
class JenkinsMetadata:
    """Jenkins build metadata structure"""
    build_url: str
    job_name: str
    build_number: int
    build_result: str
    timestamp: str
    parameters: Dict[str, Any]
    console_log_snippet: str
    artifacts: List[str]
    branch: Optional[str] = None
    commit_sha: Optional[str] = None


@dataclass
class JenkinsIntelligence:
    """Complete Jenkins intelligence analysis result"""
    metadata: JenkinsMetadata
    failure_analysis: Dict[str, Any]
    environment_info: Dict[str, Any]
    evidence_sources: List[str]
    confidence_score: float
    test_report: Optional[TestReport] = None  # Individual test case analysis


class JenkinsIntelligenceService:
    """
    Jenkins Intelligence Service
    Extracts comprehensive intelligence from Jenkins pipeline failures

    Authentication Priority:
        1. JenkinsAPIClient (checks: constructor args > env vars > config)
        2. Environment variables JENKINS_USER and JENKINS_API_TOKEN
        3. Constructor arguments
    """
    
    def __init__(self, username: Optional[str] = None, api_token: Optional[str] = None,
                 use_api_client: bool = True):
        """
        Initialize Jenkins Intelligence Service.

        Args:
            username: Jenkins username (optional, falls back to API client or env vars)
            api_token: Jenkins API token (optional, falls back to API client or env vars)
            use_api_client: Whether to use JenkinsAPIClient when available (default: True)
        """
        self.logger = logging.getLogger(__name__)
        self.use_api_client = use_api_client
        self.api_client = None
        self.api_available = False
        self.stack_parser = StackTraceParser()

        # Initialize credentials to None to avoid AttributeError
        # These will be populated from API client, env vars, or constructor args
        self.username: Optional[str] = None
        self.api_token: Optional[str] = None

        # Check for Jenkins API client availability
        if self.use_api_client:
            self.api_client = get_jenkins_client()
            if self.api_client and self.api_client.is_authenticated:
                self.api_available = True
                # Get credentials from API client
                api_user = self.api_client._username
                client_token = self.api_client._api_token
                if api_user and client_token:
                    self.username = api_user
                    self.api_token = client_token
                    self.logger.info(f"Using Jenkins API client for user: {self.username}")
                else:
                    self.logger.warning("API client available but credentials not found")

        # Fall back to environment variables or constructor args
        if not self.username or not self.api_token:
            env_user, env_token = get_jenkins_credentials()
            self.username = username or env_user or self.username
            self.api_token = api_token or env_token or self.api_token
        
        # Log authentication status
        if self.username and self.api_token:
            auth_source = "API client" if self.api_available else "env vars/args"
            self.logger.info(f"Jenkins authentication configured for user: {self.username} (via {auth_source})")
        else:
            self.logger.warning("No Jenkins authentication configured. Some Jenkins instances may reject requests.")
        
    def analyze_jenkins_url(self, jenkins_url: str, skip_console_fetch: bool = False) -> JenkinsIntelligence:
        """
        Main method to analyze Jenkins pipeline failure

        Args:
            jenkins_url: Jenkins build URL
            skip_console_fetch: If True, skip fetching console log during metadata extraction.
                               Use this when console log is fetched separately (e.g., by gather.py).

        Returns:
            JenkinsIntelligence: Complete analysis result with per-test-case analysis
        """
        self.logger.info(f"Starting Jenkins intelligence analysis for: {jenkins_url}")

        # Extract metadata
        metadata = self._extract_jenkins_metadata(jenkins_url, skip_console_fetch=skip_console_fetch)

        # Analyze failure patterns from console log (only if we have it)
        if skip_console_fetch or not metadata.console_log_snippet:
            failure_analysis = {
                'patterns': {},
                'total_failures': 0,
                'primary_failure_type': 'unknown',
                'note': 'Console log analysis skipped (fetched separately)'
            }
        else:
            failure_analysis = self._analyze_failure_patterns(metadata.console_log_snippet)
        
        # Fetch and analyze test report for per-test-case analysis
        test_report = self._fetch_and_analyze_test_report(jenkins_url)
        
        # If we have test report, enhance failure analysis
        if test_report and test_report.failed_tests:
            failure_analysis['test_report_available'] = True
            failure_analysis['individual_failures'] = len(test_report.failed_tests)
            failure_analysis['failure_breakdown'] = self._summarize_failure_types(test_report.failed_tests)
        else:
            failure_analysis['test_report_available'] = False
            failure_analysis['individual_failures'] = 0
            failure_analysis['failure_breakdown'] = {}
        
        # Extract environment information
        environment_info = self._extract_environment_info(metadata.parameters)
        
        # Build evidence sources
        evidence_sources = self._build_evidence_sources(metadata)
        
        # Add test report to evidence sources if available
        if test_report:
            evidence_sources.append(f"[TestReport:{metadata.job_name}:{metadata.build_number}:failed={test_report.failed_count}]({jenkins_url}testReport/)")
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(metadata, failure_analysis, test_report)
        
        return JenkinsIntelligence(
            metadata=metadata,
            failure_analysis=failure_analysis,
            environment_info=environment_info,
            evidence_sources=evidence_sources,
            confidence_score=confidence_score,
            test_report=test_report
        )
    
    def _extract_jenkins_metadata(self, jenkins_url: str, skip_console_fetch: bool = False) -> JenkinsMetadata:
        """Extract basic metadata from Jenkins build.

        Args:
            jenkins_url: Jenkins build URL
            skip_console_fetch: If True, skip fetching console log (saves a network call
                               when console log is fetched separately by gather.py)
        """
        parsed_url = urlparse(jenkins_url)

        # Parse job name and build number from URL
        path_parts = parsed_url.path.strip('/').split('/')

        if 'job' in path_parts:
            job_index = path_parts.index('job')
            job_name = path_parts[job_index + 1] if job_index + 1 < len(path_parts) else "unknown"
        else:
            job_name = "unknown"

        # Extract build number
        build_number = self._extract_build_number(jenkins_url)

        # Get console log (optional) and build info
        if skip_console_fetch:
            console_log = ""
            self.logger.debug("Skipping console log fetch (will be fetched separately)")
        else:
            console_log = self._fetch_console_log(jenkins_url)
        build_info = self._fetch_build_info(jenkins_url)
        
        return JenkinsMetadata(
            build_url=jenkins_url,
            job_name=job_name,
            build_number=build_number,
            build_result=build_info.get('result', 'UNKNOWN'),
            timestamp=build_info.get('timestamp', ''),
            parameters=build_info.get('parameters', {}),
            console_log_snippet=console_log[:2000],  # First 2KB for analysis
            artifacts=build_info.get('artifacts', []),
            branch=self._extract_branch_from_parameters(build_info.get('parameters', {})),
            commit_sha=self._extract_commit_from_console(console_log)
        )
    
    def _extract_build_number(self, jenkins_url: str) -> int:
        """Extract build number from Jenkins URL"""
        # Match patterns like /123/ or /123 at end of URL
        match = re.search(r'/(\d+)/?$', jenkins_url)
        if match:
            return int(match.group(1))
        return 0
    
    def _build_curl_command(self, url: str, timeout: int = 30) -> List[str]:
        """
        Build curl command with optional authentication.

        Delegates to shared_utils.build_curl_command to avoid code duplication.

        Args:
            url: The URL to fetch
            timeout: Request timeout in seconds

        Returns:
            List of command arguments for subprocess
        """
        # Use centralized curl command builder from shared_utils
        return build_curl_command(
            url=url,
            username=self.username,
            token=self.api_token,
            timeout=timeout
        )
    
    def _try_api_fetch(self, jenkins_url: str, fetch_type: str) -> Optional[Any]:
        """
        Try to fetch data using JenkinsAPIClient.

        Args:
            jenkins_url: Jenkins build URL
            fetch_type: Type of data to fetch ('console', 'build_info', 'test_report')

        Returns:
            Fetched data or None if API client is not available
        """
        if not self.api_available or not self.api_client:
            return None

        try:
            if fetch_type == 'console':
                success, result, error = self.api_client.get_console_output(jenkins_url)
                if success and result:
                    self.logger.debug("Console log fetched via API client")
                    return result
                elif error:
                    self.logger.debug(f"Console fetch error: {error}")
            elif fetch_type == 'build_info':
                success, result, error = self.api_client.get_build_info(jenkins_url)
                if success and result:
                    self.logger.debug("Build info fetched via API client")
                    return result
                elif error:
                    self.logger.debug(f"Build info fetch error: {error}")
            elif fetch_type == 'test_report':
                success, result, error = self.api_client.get_test_report(jenkins_url)
                if success and result:
                    self.logger.debug("Test report fetched via API client")
                    return result
                elif error:
                    self.logger.debug(f"Test report fetch error: {error}")
        except Exception as e:
            self.logger.warning(f"API client fetch failed for {fetch_type}: {e}")

        return None
    
    def _fetch_console_log(self, jenkins_url: str) -> str:
        """Fetch console log, trying API client first then falling back to curl"""

        # Try API client first if available
        api_result = self._try_api_fetch(jenkins_url, 'console')
        if api_result:
            self.logger.info("Console log fetched via Jenkins API client")
            return api_result
        
        # Fall back to curl
        console_url = f"{jenkins_url.rstrip('/')}/consoleText"
        
        try:
            cmd = self._build_curl_command(console_url, timeout=TIMEOUTS.CONSOLE_LOG_FETCH)
            self.logger.debug(f"Fetching console log from: {console_url}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.CONSOLE_LOG_FETCH + TIMEOUTS.SUBPROCESS_BUFFER
            )

            if result.returncode == 0:
                # Check if we got an authentication error (HTML response)
                if '<html' in result.stdout.lower()[:200]:
                    self.logger.warning("Received HTML response - may need authentication")
                    if not self.username:
                        self.logger.warning("Set JENKINS_USER and JENKINS_API_TOKEN environment variables")
                return result.stdout
            else:
                self.logger.warning(f"Failed to fetch console log: {result.stderr}")
                return ""

        except subprocess.TimeoutExpired:
            self.logger.warning("Console log fetch timed out")
            return ""
        except Exception as e:
            self.logger.error(f"Error fetching console log: {str(e)}")
            return ""

    def _fetch_build_info(self, jenkins_url: str) -> Dict[str, Any]:
        """Fetch build information, trying API client first then falling back to curl"""

        # Try API client first if available
        api_result = self._try_api_fetch(jenkins_url, 'build_info')
        if api_result:
            self.logger.info("Build info fetched via Jenkins API client")
            return self._process_build_info(api_result)
        
        # Fall back to curl
        api_url = f"{jenkins_url.rstrip('/')}/api/json"
        
        try:
            cmd = self._build_curl_command(api_url)
            self.logger.debug(f"Fetching build info from: {api_url}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.API_REQUEST + TIMEOUTS.SUBPROCESS_BUFFER
            )

            if result.returncode == 0 and result.stdout:
                # Check for HTML response (authentication error)
                if result.stdout.strip().startswith('<'):
                    self.logger.warning("Received HTML response instead of JSON - authentication may be required")
                    if not self.username:
                        self.logger.warning("Set JENKINS_USER and JENKINS_API_TOKEN environment variables")
                    return {}

                data = json.loads(result.stdout)
                return self._process_build_info(data)
            else:
                self.logger.warning("Failed to fetch build info via API")
                return {}
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            self.logger.warning(f"Error fetching build info: {str(e)}")
            return {}
        except Exception as e:
            self.logger.error(f"Unexpected error fetching build info: {str(e)}")
            return {}
    
    def _process_build_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw Jenkins API response into standardized format."""
        # Extract parameters from actions
        parameters = {}
        for action in data.get('actions', []):
            if action and 'parameters' in action:
                for param in action['parameters']:
                    if 'name' in param and 'value' in param:
                        parameters[param['name']] = param['value']
        
        return {
            'result': data.get('result', 'UNKNOWN'),
            'timestamp': data.get('timestamp', ''),
            'parameters': parameters,
            'artifacts': [a.get('fileName', '') for a in data.get('artifacts', [])],
            'duration': data.get('duration', 0),
            'building': data.get('building', False),
            'displayName': data.get('displayName', ''),
            'fullDisplayName': data.get('fullDisplayName', '')
        }
    
    def _fetch_and_analyze_test_report(self, jenkins_url: str) -> Optional[TestReport]:
        """
        Fetch test report and analyze each failed test case individually.
        Uses API client if available, falls back to curl.
        """
        self.logger.info("Fetching test report for per-test-case analysis...")

        # Try API client first if available
        api_result = self._try_api_fetch(jenkins_url, 'test_report')
        if api_result:
            self.logger.info("Test report fetched via Jenkins API client")
            return self._process_test_report(api_result)
        
        # Fall back to curl
        test_report_url = f"{jenkins_url.rstrip('/')}/testReport/api/json"
        
        try:
            cmd = self._build_curl_command(test_report_url)
            self.logger.debug(f"Fetching test report from: {test_report_url}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUTS.TEST_REPORT_FETCH
            )
            
            if result.returncode == 0 and result.stdout:
                # Check for HTML response or 404
                if result.stdout.strip().startswith('<') or 'Not Found' in result.stdout:
                    self.logger.info("No test report available for this build")
                    return None
                
                data = json.loads(result.stdout)
                return self._process_test_report(data)
            else:
                self.logger.info("No test report available or failed to fetch")
                return None
                
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            self.logger.warning(f"Error fetching test report: {str(e)}")
            return None
        except Exception as e:
            self.logger.debug(f"Test report not available: {str(e)}")
            return None
    
    def _process_test_report(self, data: Dict[str, Any]) -> TestReport:
        """Process raw test report JSON into TestReport with analyzed failures."""
        failed_tests = []
        total_duration = data.get('duration', 0)
        
        # Extract counts
        total_tests = data.get('passCount', 0) + data.get('failCount', 0) + data.get('skipCount', 0)
        passed_count = data.get('passCount', 0)
        failed_count = data.get('failCount', 0)
        skipped_count = data.get('skipCount', 0)
        
        # Process each suite
        for suite in data.get('suites', []):
            for case in suite.get('cases', []):
                status = case.get('status', 'UNKNOWN')
                
                # Only analyze failed or regression tests
                if status in ['FAILED', 'REGRESSION']:
                    test_failure = self._analyze_single_test_failure(case)
                    failed_tests.append(test_failure)
        
        # Calculate pass rate
        pass_rate = (passed_count / total_tests * 100) if total_tests > 0 else 0.0
        
        self.logger.info(f"Test report: {total_tests} total, {failed_count} failed, {passed_count} passed")
        
        return TestReport(
            total_tests=total_tests,
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            pass_rate=pass_rate,
            failed_tests=failed_tests,
            duration=total_duration
        )
    
    def _analyze_single_test_failure(self, case: Dict[str, Any]) -> TestCaseFailure:
        """
        Analyze a single test case failure and classify it.
        This provides per-test granularity with full stack trace parsing.
        """
        test_name = case.get('name', 'Unknown')
        class_name = case.get('className', 'Unknown')
        status = case.get('status', 'FAILED')
        duration = case.get('duration', 0)
        error_message = case.get('errorDetails', '')
        stack_trace = case.get('errorStackTrace', '')

        # Parse the stack trace to extract structured information
        parsed_stack = self.stack_parser.parse(stack_trace) if stack_trace else None

        # Extract root cause information from parsed stack
        root_cause_file = None
        root_cause_line = None
        if parsed_stack and parsed_stack.root_cause_frame:
            root_cause_file = parsed_stack.root_cause_frame.file_path
            root_cause_line = parsed_stack.root_cause_frame.line_number

        # Extract failing selector from error message
        failing_selector = self.stack_parser.extract_failing_selector(error_message) if error_message else None

        # Combine error info for analysis
        error_text = f"{error_message} {stack_trace}".lower()

        # Determine failure type (FACTUAL - not classification)
        # This identifies what TYPE of error occurred, not who is responsible
        failure_type = self._classify_failure_type(error_text)

        # NOTE: Classification (PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE)
        # is now performed by AI during the analysis phase, not by this script.
        # We only provide factual data here.

        # Build parsed stack trace dict for serialization
        parsed_stack_dict = None
        if parsed_stack:
            parsed_stack_dict = {
                'error_type': parsed_stack.error_type,
                'error_message': parsed_stack.error_message,
                'total_frames': parsed_stack.total_frames,
                'user_code_frames': parsed_stack.user_code_frames,
                'frames': [
                    {
                        'file_path': f.file_path,
                        'line_number': f.line_number,
                        'column_number': f.column_number,
                        'function_name': f.function_name,
                        'is_test_file': f.is_test_file,
                        'is_framework_file': f.is_framework_file,
                        'is_support_file': f.is_support_file,
                    }
                    for f in parsed_stack.frames[:20]  # Top 20 frames for context
                ]
            }

        return TestCaseFailure(
            test_name=test_name,
            class_name=class_name,
            status=status,
            duration=duration,
            error_message=error_message,  # Full error message (no truncation)
            stack_trace=stack_trace,  # Full stack trace (no truncation)
            failure_type=failure_type,
            # classification fields left at defaults (None, 0.0) - AI fills these
            parsed_stack_trace=parsed_stack_dict,
            root_cause_file=root_cause_file,
            root_cause_line=root_cause_line,
            failing_selector=failing_selector
        )
    
    def _classify_failure_type(self, error_text: str) -> str:
        """
        Identify the failure type based on error content (FACTUAL DATA).

        This returns the TYPE of error (timeout, element_not_found, network, etc.),
        not the bug classification (PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE).
        Bug classification is performed by the AI during analysis.
        """
        # Check for specific patterns
        if any(p in error_text for p in ['timeout', 'timed out', 'exceeded']):
            return 'timeout'
        elif any(p in error_text for p in ['element', 'not found', 'selector', 'nosuchelement']):
            return 'element_not_found'
        elif any(p in error_text for p in ['connection', 'network', 'refused', 'dns']):
            return 'network'
        elif any(p in error_text for p in ['assert', 'expect', 'should', 'equal', 'match']):
            return 'assertion'
        elif any(p in error_text for p in ['500', '502', '503', 'internal server', 'bad gateway']):
            return 'server_error'
        elif any(p in error_text for p in ['401', '403', 'unauthorized', 'forbidden', 'permission']):
            return 'auth_error'
        elif any(p in error_text for p in ['404', 'not found', 'no such']):
            return 'not_found'
        else:
            return 'unknown'

    def _summarize_failure_types(self, failed_tests: List[TestCaseFailure]) -> Dict[str, Any]:
        """
        Summarize failure types across all failed tests.

        NOTE: This provides FACTUAL data only (failure_type = timeout, element_not_found, etc.).
        Bug classification (PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE) is determined by AI
        during the analysis phase, not pre-computed here.
        """
        summary = {
            'by_failure_type': {},  # Factual: timeout, element_not_found, network, assertion, etc.
            'tests_by_failure_type': {}  # Group test names by failure type
        }

        for test in failed_tests:
            # Count by failure type (factual data)
            ft = test.failure_type or 'unknown'
            summary['by_failure_type'][ft] = summary['by_failure_type'].get(ft, 0) + 1

            # Group test names by failure type
            if ft not in summary['tests_by_failure_type']:
                summary['tests_by_failure_type'][ft] = []
            summary['tests_by_failure_type'][ft].append(test.test_name)

        return summary
    
    def _analyze_failure_patterns(self, console_log: str) -> Dict[str, Any]:
        """Analyze console log for failure patterns"""
        failure_patterns = {
            'timeout_errors': [],
            'element_not_found': [],
            'network_errors': [],
            'assertion_failures': [],
            'build_failures': [],
            'environment_issues': []
        }
        
        # Timeout patterns
        timeout_patterns = [
            r'timeout.*waiting.*for.*element',
            r'TimeoutError',
            r'timed out after \d+',
            r'cypress.*timed.*out'
        ]
        
        for pattern in timeout_patterns:
            matches = re.findall(pattern, console_log, re.IGNORECASE)
            failure_patterns['timeout_errors'].extend(matches)
        
        # Element not found patterns
        element_patterns = [
            r'element.*not.*found',
            r'selector.*not.*found',
            r'NoSuchElementException',
            r'ElementNotInteractableException'
        ]
        
        for pattern in element_patterns:
            matches = re.findall(pattern, console_log, re.IGNORECASE)
            failure_patterns['element_not_found'].extend(matches)
        
        # Network error patterns
        network_patterns = [
            r'connection.*refused',
            r'network.*error',
            r'failed.*to.*connect',
            r'DNS.*resolution.*failed'
        ]
        
        for pattern in network_patterns:
            matches = re.findall(pattern, console_log, re.IGNORECASE)
            failure_patterns['network_errors'].extend(matches)
        
        # Count total failures
        total_failures = sum(len(errors) for errors in failure_patterns.values())
        
        return {
            'patterns': failure_patterns,
            'total_failures': total_failures,
            'primary_failure_type': self._determine_primary_failure_type(failure_patterns)
        }
    
    def _determine_primary_failure_type(self, patterns: Dict[str, List]) -> str:
        """Determine the primary type of failure"""
        failure_counts = {key: len(values) for key, values in patterns.items()}
        
        if not any(failure_counts.values()):
            return 'unknown'
            
        return max(failure_counts, key=failure_counts.get)
    
    def _extract_first_matching_parameter(
        self,
        parameters: Dict[str, Any],
        param_names: List[str],
        clean_func: Optional[Callable[[str], str]] = None
    ) -> Optional[str]:
        """
        Extract the first matching parameter value from a list of possible names.

        Args:
            parameters: Build parameters dictionary
            param_names: List of parameter names to check (in priority order)
            clean_func: Optional function to clean/transform the value

        Returns:
            The first matching parameter value, or None if not found
        """
        for param in param_names:
            if param in parameters:
                value = parameters[param]
                if isinstance(value, str) and value.strip():
                    if clean_func:
                        return clean_func(value)
                    return value.strip()
        return None

    def _extract_environment_info(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Extract environment information from build parameters"""
        # Common parameter names for each field
        cluster_params = ['CLUSTER_NAME', 'cluster', 'environment', 'ENVIRONMENT']
        branch_params = ['BRANCH', 'branch', 'GIT_BRANCH', 'git_branch']
        suite_params = ['TEST_SUITE', 'test_suite', 'SUITE']

        # Note: target_branch is NOT cleaned here (preserves origin/ prefix)
        # Use _extract_branch_from_parameters for cleaned branch name
        return {
            'cluster_name': self._extract_first_matching_parameter(parameters, cluster_params),
            'environment_type': None,
            'target_branch': self._extract_first_matching_parameter(parameters, branch_params),
            'test_suite': self._extract_first_matching_parameter(parameters, suite_params)
        }

    def _extract_branch_from_parameters(self, parameters: Dict[str, Any]) -> Optional[str]:
        """Extract branch name from build parameters"""
        branch_params = ['BRANCH', 'branch', 'GIT_BRANCH', 'git_branch']

        def clean_branch(value: str) -> str:
            """Remove origin/ prefix from branch name"""
            return value.replace('origin/', '').strip()

        return self._extract_first_matching_parameter(parameters, branch_params, clean_branch)
    
    def _extract_commit_from_console(self, console_log: str) -> Optional[str]:
        """Extract commit SHA from console log"""
        # Look for git commit patterns
        commit_patterns = [
            r'commit\s+([a-f0-9]{7,40})',
            r'Revision:\s+([a-f0-9]{7,40})',
            r'Checking out\s+([a-f0-9]{7,40})'
        ]
        
        for pattern in commit_patterns:
            match = re.search(pattern, console_log, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _build_evidence_sources(self, metadata: JenkinsMetadata) -> List[str]:
        """Build list of evidence sources for citations"""
        sources = []
        
        # Jenkins build source
        sources.append(f"[Jenkins:{metadata.job_name}:{metadata.build_number}:{metadata.build_result}:{metadata.timestamp}]({metadata.build_url})")
        
        # Console log source
        console_url = f"{metadata.build_url.rstrip('/')}/console"
        sources.append(f"[Console:{metadata.job_name}:{metadata.build_number}]({console_url})")
        
        # Repository source if commit is available
        if metadata.commit_sha and metadata.branch:
            sources.append(f"[Repo:{metadata.branch}:commit:{metadata.commit_sha}]")
        
        return sources
    
    def _calculate_confidence_score(self, metadata: JenkinsMetadata, failure_analysis: Dict[str, Any],
                                    test_report: Optional[TestReport] = None) -> float:
        """
        Calculate data quality confidence score.

        This measures how complete our gathered data is (not classification confidence).
        Higher score = more complete data for AI to analyze.
        """
        score = 0.0
        
        # Base score for having metadata
        if metadata.build_result != 'UNKNOWN':
            score += 0.2
        
        # Score for having console log data
        if metadata.console_log_snippet:
            score += 0.1
        
        # Score for having failure analysis
        if failure_analysis['total_failures'] > 0:
            score += 0.15
        
        # Score for having build parameters
        if metadata.parameters:
            score += 0.1
        
        # Score for having branch and commit info
        if metadata.branch:
            score += 0.05
        if metadata.commit_sha:
            score += 0.05
        
        # MAJOR score boost for having test report with per-test analysis
        if test_report:
            score += 0.2  # Test report available
            if test_report.failed_tests:
                # Higher confidence when we have detailed failure data
                # NOTE: Classification is now done by AI, so we score based on
                # factual data completeness (failure_type, stack_trace, selector)
                detailed_tests = sum(1 for t in test_report.failed_tests
                                    if t.failure_type and t.stack_trace)
                detail_rate = detailed_tests / len(test_report.failed_tests)
                score += 0.15 * detail_rate  # Up to 0.15 more for detailed failure data

        return min(score, 1.0)
    
    def to_dict(self, intelligence: JenkinsIntelligence) -> Dict[str, Any]:
        """Convert JenkinsIntelligence to dictionary for serialization"""
        result = {
            'metadata': asdict(intelligence.metadata),
            'failure_analysis': intelligence.failure_analysis,
            'environment_info': intelligence.environment_info,
            'evidence_sources': intelligence.evidence_sources,
            'confidence_score': intelligence.confidence_score
        }
        
        # Add test report if available
        if intelligence.test_report:
            result['test_report'] = {
                'total_tests': intelligence.test_report.total_tests,
                'passed_count': intelligence.test_report.passed_count,
                'failed_count': intelligence.test_report.failed_count,
                'skipped_count': intelligence.test_report.skipped_count,
                'pass_rate': intelligence.test_report.pass_rate,
                'duration': intelligence.test_report.duration,
                'failed_tests': [asdict(t) for t in intelligence.test_report.failed_tests]
            }
        else:
            result['test_report'] = None
        
        return result