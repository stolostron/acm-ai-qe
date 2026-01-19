#!/usr/bin/env python3
"""
Jenkins MCP Client
Client for interacting with Jenkins via the MCP (Model Context Protocol) server.

When the Jenkins MCP server is available, it provides a more reliable and feature-rich
way to interact with Jenkins compared to direct curl calls.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class JenkinsMCPClient:
    """
    Jenkins MCP Client
    Interfaces with the Jenkins MCP server for pipeline analysis.
    """
    
    # Default MCP config locations
    MCP_CONFIG_PATHS = [
        Path.home() / '.cursor' / 'mcp.json',
        Path.home() / '.config' / 'cursor' / 'mcp.json',
        Path.home() / '.claude' / 'mcp.json',
    ]
    
    def __init__(self):
        """Initialize the Jenkins MCP client."""
        self.logger = logging.getLogger(__name__)
        self.mcp_config = self._load_mcp_config()
        self.jenkins_server = self._get_jenkins_server_config()
        self._available = self.jenkins_server is not None
        
        if self._available:
            self.logger.info(f"Jenkins MCP server found: {self.jenkins_server.get('url', 'unknown')}")
        else:
            self.logger.debug("Jenkins MCP server not configured")
    
    @property
    def is_available(self) -> bool:
        """Check if Jenkins MCP server is available."""
        return self._available
    
    def _load_mcp_config(self) -> Optional[Dict[str, Any]]:
        """Load MCP configuration from known locations."""
        for config_path in self.MCP_CONFIG_PATHS:
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        self.logger.debug(f"Loaded MCP config from: {config_path}")
                        return config
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.warning(f"Failed to load MCP config from {config_path}: {e}")
        
        return None
    
    def _get_jenkins_server_config(self) -> Optional[Dict[str, Any]]:
        """Extract Jenkins server configuration from MCP config."""
        if not self.mcp_config:
            return None
        
        servers = self.mcp_config.get('mcpServers', {})
        
        # Look for Jenkins server
        jenkins_server = servers.get('jenkins')
        if jenkins_server:
            return jenkins_server
        
        # Try alternate names
        for name in ['jenkins-server', 'Jenkins', 'jenkins-mcp']:
            if name in servers:
                return servers[name]
        
        return None
    
    def get_jenkins_url(self) -> Optional[str]:
        """Get the Jenkins base URL from MCP config."""
        if not self.jenkins_server:
            return None
        
        url = self.jenkins_server.get('url', '')
        # Extract base URL (remove /mcp-server/mcp suffix if present)
        if '/mcp-server' in url:
            url = url.split('/mcp-server')[0]
        return url
    
    def get_auth_header(self) -> Optional[str]:
        """Get the authorization header from MCP config."""
        if not self.jenkins_server:
            return None
        
        headers = self.jenkins_server.get('headers', {})
        return headers.get('Authorization')
    
    def get_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract username and API token from the MCP config.
        
        Returns:
            Tuple of (username, api_token) or (None, None) if not available
        """
        auth_header = self.get_auth_header()
        if not auth_header:
            return None, None
        
        # Parse Basic auth header
        if auth_header.startswith('Basic '):
            import base64
            try:
                encoded = auth_header.split(' ', 1)[1]
                decoded = base64.b64decode(encoded).decode('utf-8')
                if ':' in decoded:
                    username, token = decoded.split(':', 1)
                    return username, token
            except Exception as e:
                self.logger.warning(f"Failed to decode auth header: {e}")
        
        return None, None
    
    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call a Jenkins MCP tool.
        
        Note: This is a placeholder for actual MCP protocol interaction.
        In a full implementation, this would use the MCP protocol to call tools.
        
        For now, we extract credentials and use them with direct API calls.
        
        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments
            
        Returns:
            Tool result or None if failed
        """
        self.logger.debug(f"MCP tool call: {tool_name} with args: {arguments}")
        
        # Map MCP tools to API endpoints
        base_url = self.get_jenkins_url()
        username, token = self.get_credentials()
        
        if not base_url or not username or not token:
            self.logger.warning("MCP credentials not available for tool call")
            return None
        
        # Handle specific tools
        if tool_name == 'jenkins_get_build':
            return self._get_build(base_url, username, token, arguments)
        elif tool_name == 'jenkins_get_console':
            return self._get_console(base_url, username, token, arguments)
        elif tool_name == 'jenkins_list_jobs':
            return self._list_jobs(base_url, username, token, arguments)
        elif tool_name == 'jenkins_get_test_report':
            return self._get_test_report(base_url, username, token, arguments)
        else:
            self.logger.warning(f"Unknown MCP tool: {tool_name}")
            return None
    
    def _make_api_request(self, url: str, username: str, token: str) -> Optional[Dict[str, Any]]:
        """Make an authenticated API request to Jenkins."""
        try:
            cmd = [
                'curl', '-k', '-s', '--max-time', '30',
                '-u', f'{username}:{token}',
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=35
            )
            
            if result.returncode == 0 and result.stdout:
                # Check for HTML response (auth error)
                if result.stdout.strip().startswith('<'):
                    self.logger.warning("Received HTML response - authentication may have failed")
                    return None
                
                return json.loads(result.stdout)
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            self.logger.warning(f"API request failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in API request: {e}")
        
        return None
    
    def _get_build(self, base_url: str, username: str, token: str, 
                   arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get build information using Jenkins API."""
        job_path = arguments.get('job_path', '')
        build_number = arguments.get('build_number', 'lastBuild')
        
        # Construct API URL
        api_url = f"{base_url}/job/{job_path}/{build_number}/api/json"
        
        return self._make_api_request(api_url, username, token)
    
    def _get_console(self, base_url: str, username: str, token: str,
                     arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get console output using Jenkins API."""
        job_path = arguments.get('job_path', '')
        build_number = arguments.get('build_number', 'lastBuild')
        
        # Construct console URL
        console_url = f"{base_url}/job/{job_path}/{build_number}/consoleText"
        
        try:
            cmd = [
                'curl', '-k', '-s', '--max-time', '60',
                '-u', f'{username}:{token}',
                console_url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=65
            )
            
            if result.returncode == 0:
                return {'console_output': result.stdout}
            
        except Exception as e:
            self.logger.warning(f"Console fetch failed: {e}")
        
        return None
    
    def _list_jobs(self, base_url: str, username: str, token: str,
                   arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """List jobs in a folder."""
        folder_path = arguments.get('folder_path', '')
        
        if folder_path:
            api_url = f"{base_url}/job/{folder_path}/api/json"
        else:
            api_url = f"{base_url}/api/json"
        
        return self._make_api_request(api_url, username, token)
    
    def _get_test_report(self, base_url: str, username: str, token: str,
                         arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get test report for a build."""
        job_path = arguments.get('job_path', '')
        build_number = arguments.get('build_number', 'lastBuild')
        
        api_url = f"{base_url}/job/{job_path}/{build_number}/testReport/api/json"
        
        return self._make_api_request(api_url, username, token)
    
    def get_build_info(self, jenkins_url: str) -> Optional[Dict[str, Any]]:
        """
        Get build information from a Jenkins URL.
        
        Args:
            jenkins_url: Full Jenkins build URL
            
        Returns:
            Build information dictionary or None
        """
        if not self.is_available:
            return None
        
        # Parse the URL to extract job path and build number
        job_path, build_number = self._parse_jenkins_url(jenkins_url)
        
        if not job_path:
            return None
        
        return self.call_mcp_tool('jenkins_get_build', {
            'job_path': job_path,
            'build_number': build_number
        })
    
    def get_console_output(self, jenkins_url: str) -> Optional[str]:
        """
        Get console output from a Jenkins build URL.
        
        Args:
            jenkins_url: Full Jenkins build URL
            
        Returns:
            Console output string or None
        """
        if not self.is_available:
            return None
        
        job_path, build_number = self._parse_jenkins_url(jenkins_url)
        
        if not job_path:
            return None
        
        result = self.call_mcp_tool('jenkins_get_console', {
            'job_path': job_path,
            'build_number': build_number
        })
        
        if result:
            return result.get('console_output', '')
        
        return None
    
    def get_test_report(self, jenkins_url: str) -> Optional[Dict[str, Any]]:
        """
        Get test report from a Jenkins build URL.
        
        Args:
            jenkins_url: Full Jenkins build URL
            
        Returns:
            Test report dictionary or None
        """
        if not self.is_available:
            return None
        
        job_path, build_number = self._parse_jenkins_url(jenkins_url)
        
        if not job_path:
            return None
        
        return self.call_mcp_tool('jenkins_get_test_report', {
            'job_path': job_path,
            'build_number': build_number
        })
    
    def _parse_jenkins_url(self, jenkins_url: str) -> Tuple[Optional[str], str]:
        """
        Parse a Jenkins URL to extract job path and build number.
        
        Args:
            jenkins_url: Full Jenkins build URL
            
        Returns:
            Tuple of (job_path, build_number)
        """
        import re
        from urllib.parse import urlparse
        
        parsed = urlparse(jenkins_url)
        path = parsed.path.strip('/')
        
        # Extract job path and build number
        # Pattern: job/folder1/job/folder2/job/jobname/123
        parts = path.split('/')
        
        job_parts = []
        build_number = 'lastBuild'
        
        i = 0
        while i < len(parts):
            if parts[i] == 'job' and i + 1 < len(parts):
                job_parts.append(parts[i + 1])
                i += 2
            else:
                # Check if this is a build number
                if parts[i].isdigit():
                    build_number = parts[i]
                i += 1
        
        if job_parts:
            job_path = '/job/'.join(job_parts)
            return job_path, build_number
        
        return None, 'lastBuild'


# Singleton instance for easy access
_mcp_client: Optional[JenkinsMCPClient] = None


def get_mcp_client() -> JenkinsMCPClient:
    """Get the singleton MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = JenkinsMCPClient()
    return _mcp_client


def is_mcp_available() -> bool:
    """Check if Jenkins MCP is available."""
    return get_mcp_client().is_available
