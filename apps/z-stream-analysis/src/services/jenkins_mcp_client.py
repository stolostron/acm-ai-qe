#!/usr/bin/env python3
"""
Jenkins MCP Client - DEPRECATED

This module is deprecated and maintained only for backward compatibility.
Use JenkinsAPIClient from jenkins_api_client.py instead.

The original "MCP" naming was misleading - this module never used MCP protocol.
It only extracted credentials from MCP config files and made direct curl calls.

The new JenkinsAPIClient provides:
- Proper naming (not pretending to be MCP)
- Multiple credential sources (env vars, config files, constructor args)
- Better error handling with proper return types
- Clean, well-documented API
"""

import warnings
from typing import Dict, Any, Optional, Tuple

# Import everything from the new module
from .jenkins_api_client import (
    JenkinsAPIClient,
    get_jenkins_api_client,
    is_jenkins_available,
)


class JenkinsMCPClient:
    """
    DEPRECATED: Use JenkinsAPIClient instead.

    This class is maintained for backward compatibility only.
    It wraps JenkinsAPIClient with the old interface.
    """

    def __init__(self):
        """Initialize the legacy MCP client wrapper."""
        warnings.warn(
            "JenkinsMCPClient is deprecated. Use JenkinsAPIClient instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._client = JenkinsAPIClient()

    @property
    def is_available(self) -> bool:
        """Check if credentials are available."""
        return self._client.is_authenticated

    def get_jenkins_url(self) -> Optional[str]:
        """Get the Jenkins base URL."""
        return self._client.base_url

    def get_auth_header(self) -> Optional[str]:
        """Get the authorization header (legacy method)."""
        if not self._client.is_authenticated:
            return None
        import base64
        creds = f"{self._client._username}:{self._client._api_token}"
        encoded = base64.b64encode(creds.encode()).decode()
        return f"Basic {encoded}"

    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """Get username and API token."""
        return self._client._username, self._client._api_token

    def get_build_info(self, jenkins_url: str) -> Optional[Dict[str, Any]]:
        """Get build information (legacy interface)."""
        success, data, _ = self._client.get_build_info(jenkins_url)
        return data if success else None

    def get_console_output(self, jenkins_url: str) -> Optional[str]:
        """Get console output (legacy interface)."""
        success, output, _ = self._client.get_console_output(jenkins_url)
        return output if success else None

    def get_test_report(self, jenkins_url: str) -> Optional[Dict[str, Any]]:
        """Get test report (legacy interface)."""
        success, data, _ = self._client.get_test_report(jenkins_url)
        return data if success else None

    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        DEPRECATED: MCP tool calls are no longer supported.

        For Phase 2 analysis, use Claude Code's native MCP integration instead.
        This method now returns None.
        """
        warnings.warn(
            "call_mcp_tool is deprecated. Use Claude Code's native MCP for Phase 2.",
            DeprecationWarning,
            stacklevel=2
        )
        return None

    def _parse_jenkins_url(self, jenkins_url: str) -> Tuple[Optional[str], str]:
        """Parse Jenkins URL (legacy interface)."""
        _, job_path, build_num = self._client.parse_build_url(jenkins_url)
        return job_path if job_path else None, build_num or 'lastBuild'


# Singleton instance
_mcp_client: Optional[JenkinsMCPClient] = None


def get_mcp_client() -> JenkinsMCPClient:
    """
    DEPRECATED: Use get_jenkins_api_client() instead.

    Get the singleton MCP client instance.
    """
    global _mcp_client
    if _mcp_client is None:
        # Suppress the deprecation warning for internal use
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            _mcp_client = JenkinsMCPClient()
    return _mcp_client


def is_mcp_available() -> bool:
    """
    DEPRECATED: Use is_jenkins_available() instead.

    Check if Jenkins MCP is available.
    """
    return is_jenkins_available()
