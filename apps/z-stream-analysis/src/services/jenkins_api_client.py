#!/usr/bin/env python3
"""
Jenkins API Client

A robust client for interacting with Jenkins REST API.
This client provides:
- Direct Jenkins REST API access
- Multiple credential sources (env vars, MCP config, constructor args)
- Proper error handling and timeout management
- Clean, well-documented API

Credential Priority:
1. Constructor arguments (username, api_token)
2. Environment variables (JENKINS_USER, JENKINS_API_TOKEN)
3. MCP config file (~/.cursor/mcp.json or ~/.claude.json)
"""

import base64
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from .shared_utils import TIMEOUTS, build_curl_command


class JenkinsAPIClient:
    """
    Jenkins API Client

    Provides authenticated access to Jenkins REST API for pipeline analysis.
    """

    # Config file locations for credential extraction (legacy MCP configs)
    CONFIG_PATHS = [
        Path.home() / '.cursor' / 'mcp.json',
        Path.home() / '.claude.json',
        Path.home() / '.config' / 'cursor' / 'mcp.json',
    ]

    def __init__(
        self,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        verify_ssl: bool = False
    ):
        """
        Initialize Jenkins API Client.

        Args:
            username: Jenkins username (overrides env/config)
            api_token: Jenkins API token (overrides env/config)
            base_url: Jenkins base URL (optional, can be extracted from build URLs)
            verify_ssl: Whether to verify SSL certificates (default False for internal Jenkins)
        """
        self.logger = logging.getLogger(__name__)
        self.verify_ssl = verify_ssl

        # Load credentials with priority: args > env > config
        self._username, self._api_token = self._load_credentials(username, api_token)
        self._base_url = base_url or self._extract_base_url_from_config()

        if self._username and self._api_token:
            self.logger.info(f"Jenkins API client initialized for user: {self._username}")
        else:
            self.logger.warning("Jenkins API client initialized without credentials")

    @property
    def is_authenticated(self) -> bool:
        """Check if credentials are available."""
        return bool(self._username and self._api_token)

    @property
    def username(self) -> Optional[str]:
        """Get the configured username."""
        return self._username

    @property
    def base_url(self) -> Optional[str]:
        """Get the configured base URL."""
        return self._base_url

    def _load_credentials(
        self,
        username: Optional[str],
        api_token: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Load credentials from available sources.

        Priority:
        1. Constructor arguments
        2. Environment variables
        3. Config files (MCP configs)

        Returns:
            Tuple of (username, api_token)
        """
        # 1. Constructor arguments
        if username and api_token:
            self.logger.debug("Using credentials from constructor arguments")
            return username, api_token

        # 2. Environment variables
        env_user = os.environ.get('JENKINS_USER')
        env_token = os.environ.get('JENKINS_API_TOKEN')
        if env_user and env_token:
            self.logger.debug("Using credentials from environment variables")
            return env_user, env_token

        # 3. Config files
        config_creds = self._load_credentials_from_config()
        if config_creds[0] and config_creds[1]:
            self.logger.debug("Using credentials from config file")
            return config_creds

        return None, None

    def _load_credentials_from_config(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract Jenkins credentials from MCP config files.

        Looks for Jenkins server config with Authorization header.

        Returns:
            Tuple of (username, api_token)
        """
        for config_path in self.CONFIG_PATHS:
            if not config_path.exists():
                continue

            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)

                # Check mcpServers section
                servers = config.get('mcpServers', {})
                jenkins_config = servers.get('jenkins')

                if not jenkins_config:
                    # Try alternate names
                    for name in ['jenkins-server', 'Jenkins', 'jenkins-mcp']:
                        if name in servers:
                            jenkins_config = servers[name]
                            break

                if jenkins_config:
                    # Extract from headers
                    headers = jenkins_config.get('headers', {})
                    auth_header = headers.get('Authorization', '')

                    if auth_header.startswith('Basic '):
                        try:
                            encoded = auth_header.split(' ', 1)[1]
                            decoded = base64.b64decode(encoded).decode('utf-8')
                            if ':' in decoded:
                                user, token = decoded.split(':', 1)
                                self.logger.debug(f"Found credentials in {config_path}")
                                return user, token
                        except Exception as e:
                            self.logger.warning(f"Failed to decode auth from {config_path}: {e}")

            except (json.JSONDecodeError, IOError) as e:
                self.logger.debug(f"Failed to read config {config_path}: {e}")

        return None, None

    def _extract_base_url_from_config(self) -> Optional[str]:
        """Extract Jenkins base URL from config files."""
        for config_path in self.CONFIG_PATHS:
            if not config_path.exists():
                continue

            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)

                servers = config.get('mcpServers', {})
                jenkins_config = servers.get('jenkins')

                if jenkins_config and 'url' in jenkins_config:
                    url = jenkins_config['url']
                    # Remove MCP path suffix if present
                    if '/mcp-server' in url:
                        url = url.split('/mcp-server')[0]
                    return url

            except Exception:
                continue

        return None

    def _make_request(
        self,
        url: str,
        timeout: int = None,
        raw_text: bool = False
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Make an authenticated request to Jenkins.

        Args:
            url: Full URL to request
            timeout: Request timeout in seconds
            raw_text: If True, return raw text instead of JSON

        Returns:
            Tuple of (success, data/text, error_message)
        """
        if not self.is_authenticated:
            return False, None, "No credentials configured"

        timeout = timeout or TIMEOUTS.API_REQUEST

        # Build curl command using centralized utility
        cmd = build_curl_command(
            url=url,
            username=self._username,
            token=self._api_token,
            timeout=timeout,
            verify_ssl=self.verify_ssl
        )

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + TIMEOUTS.SUBPROCESS_BUFFER
            )

            if result.returncode != 0:
                return False, None, f"curl failed with code {result.returncode}: {result.stderr}"

            output = result.stdout

            # Check for HTML response (usually auth error)
            if output.strip().startswith('<'):
                if 'authentication' in output.lower() or 'login' in output.lower():
                    return False, None, "Authentication failed - check credentials"
                if '404' in output or 'Not Found' in output:
                    return False, None, "Resource not found (404)"
                return False, None, "Received HTML response instead of JSON"

            if raw_text:
                return True, output, None

            # Parse JSON
            try:
                data = json.loads(output)
                return True, data, None
            except json.JSONDecodeError as e:
                return False, None, f"Invalid JSON response: {e}"

        except subprocess.TimeoutExpired:
            return False, None, f"Request timed out after {timeout}s"
        except Exception as e:
            return False, None, f"Request failed: {e}"

    def parse_build_url(self, jenkins_url: str) -> Tuple[Optional[str], str, Optional[str]]:
        """
        Parse a Jenkins build URL to extract components.

        Args:
            jenkins_url: Full Jenkins build URL

        Returns:
            Tuple of (base_url, job_path, build_number)
            build_number may be None if not specified in URL
        """
        parsed = urlparse(jenkins_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        path = parsed.path.strip('/')
        parts = path.split('/')

        # Extract job path and build number
        # Pattern: job/folder1/job/folder2/job/jobname/123
        job_parts = []
        build_number = None
        i = 0

        while i < len(parts):
            if parts[i] == 'job' and i + 1 < len(parts):
                job_parts.append(parts[i + 1])
                i += 2
            else:
                if parts[i].isdigit():
                    build_number = parts[i]
                i += 1

        job_path = '/job/'.join(job_parts) if job_parts else ''

        return base_url, job_path, build_number

    def get_build_info(self, jenkins_url: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Get build information from a Jenkins build URL.

        Args:
            jenkins_url: Full Jenkins build URL

        Returns:
            Tuple of (success, build_info_dict, error_message)
        """
        base_url, job_path, build_number = self.parse_build_url(jenkins_url)

        if not job_path:
            return False, None, "Could not parse job path from URL"

        build_num = build_number or 'lastBuild'
        api_url = f"{base_url}/job/{job_path}/{build_num}/api/json"

        return self._make_request(api_url)

    def get_console_output(
        self,
        jenkins_url: str,
        max_lines: Optional[int] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Get console output from a Jenkins build.

        Args:
            jenkins_url: Full Jenkins build URL
            max_lines: Optional limit on number of lines to return

        Returns:
            Tuple of (success, console_text, error_message)
        """
        base_url, job_path, build_number = self.parse_build_url(jenkins_url)

        if not job_path:
            return False, None, "Could not parse job path from URL"

        build_num = build_number or 'lastBuild'
        console_url = f"{base_url}/job/{job_path}/{build_num}/consoleText"

        success, output, error = self._make_request(
            console_url,
            timeout=TIMEOUTS.CONSOLE_LOG_FETCH,
            raw_text=True
        )

        if success and max_lines and output:
            lines = output.split('\n')
            if len(lines) > max_lines:
                output = '\n'.join(lines[-max_lines:])

        return success, output, error

    def get_test_report(self, jenkins_url: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Get test report from a Jenkins build.

        Args:
            jenkins_url: Full Jenkins build URL

        Returns:
            Tuple of (success, test_report_dict, error_message)
        """
        base_url, job_path, build_number = self.parse_build_url(jenkins_url)

        if not job_path:
            return False, None, "Could not parse job path from URL"

        build_num = build_number or 'lastBuild'
        api_url = f"{base_url}/job/{job_path}/{build_num}/testReport/api/json"

        return self._make_request(api_url, timeout=TIMEOUTS.TEST_REPORT_FETCH)

    def get_build_parameters(self, jenkins_url: str) -> Tuple[bool, Optional[Dict[str, str]], Optional[str]]:
        """
        Extract build parameters from a Jenkins build.

        Args:
            jenkins_url: Full Jenkins build URL

        Returns:
            Tuple of (success, parameters_dict, error_message)
        """
        success, build_info, error = self.get_build_info(jenkins_url)

        if not success:
            return False, None, error

        # Extract parameters from actions
        params = {}
        for action in build_info.get('actions', []):
            if action.get('_class', '').endswith('ParametersAction'):
                for param in action.get('parameters', []):
                    name = param.get('name', '')
                    value = param.get('value', '')
                    if name:
                        params[name] = str(value) if value is not None else ''

        return True, params, None

    def get_job_info(self, job_url: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Get job configuration and recent builds.

        Args:
            job_url: Jenkins job URL

        Returns:
            Tuple of (success, job_info_dict, error_message)
        """
        api_url = job_url.rstrip('/') + '/api/json'
        return self._make_request(api_url)

    def verify_connection(self) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verify Jenkins connection and authentication.

        Returns:
            Tuple of (success, username, error_message)
        """
        if not self._base_url:
            return False, None, "No base URL configured"

        api_url = f"{self._base_url}/me/api/json"
        success, data, error = self._make_request(api_url)

        if success and data:
            return True, data.get('fullName', data.get('id', 'unknown')), None

        return False, None, error


# Singleton instance
_api_client: Optional[JenkinsAPIClient] = None


def get_jenkins_api_client() -> JenkinsAPIClient:
    """Get the singleton Jenkins API client instance."""
    global _api_client
    if _api_client is None:
        _api_client = JenkinsAPIClient()
    return _api_client


def is_jenkins_available() -> bool:
    """Check if Jenkins API client has credentials."""
    return get_jenkins_api_client().is_authenticated
