#!/usr/bin/env python3
"""
ACM UI MCP Client

Provides ACM UI data for Phase 1 data gathering.

IMPORTANT: For Phase 2 (AI Analysis), use Claude Code's native MCP integration
instead of this client. Claude Code CLI has native MCP support and can directly
call ACM UI MCP tools during analysis.

Native MCP tools available in Claude Code (Phase 2):
- mcp__acm-ui__detect_cnv_version
- mcp__acm-ui__find_test_ids
- mcp__acm-ui__search_code
- mcp__acm-ui__get_fleet_virt_selectors
- mcp__acm-ui__get_component_source

This Python client is used ONLY during Phase 1 for:
- Fallback CNV version detection from cluster (when MCP unavailable)
- Pre-computing element inventory for gather.py output

The subprocess-based MCP protocol simulation has been removed.
Claude Code's native MCP implementation is more reliable and efficient.
"""

import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

from .shared_utils import TIMEOUTS, run_subprocess


@dataclass
class ElementInfo:
    """Information about a UI element/selector."""
    selector: str
    selector_type: str  # 'data-test', 'data-testid', 'aria-label', etc.
    file_path: str
    line_number: Optional[int] = None
    context: Optional[str] = None
    repository: str = ""


@dataclass
class SearchResult:
    """Result from code search."""
    file_path: str
    line_number: int
    line_content: str
    repository: str
    url: Optional[str] = None


@dataclass
class CNVVersionInfo:
    """Container Native Virtualization version information."""
    version: str
    branch: str
    detected_from: str  # 'cluster', 'env', 'default'
    csv_name: Optional[str] = None


@dataclass
class FleetVirtSelectors:
    """Fleet Virtualization selectors from kubevirt-plugin."""
    selectors: Dict[str, List[str]] = field(default_factory=dict)
    selector_file: Optional[str] = None
    common_selector_file: Optional[str] = None
    version: Optional[str] = None
    total_count: int = 0


class ACMUIMCPClient:
    """
    ACM UI MCP Client

    Provides fallback functionality for Phase 1 data gathering.
    For Phase 2 AI analysis, use Claude Code's native MCP integration.
    """

    def __init__(self, mcp_config_path=None):
        """
        Initialize ACM UI MCP Client.

        Note: The mcp_config_path parameter is kept for backward compatibility
        but is no longer used. Claude Code's native MCP handles MCP connections.
        """
        self.logger = logging.getLogger(__name__)
        self._available = False  # No longer checks MCP config
        self.logger.debug(
            "ACM UI MCP Client initialized. "
            "For Phase 2 analysis, use Claude Code's native MCP tools."
        )

    @property
    def is_available(self) -> bool:
        """
        Check if ACM UI MCP is available.

        Note: This now returns False as the Python client no longer
        implements MCP protocol. Use Claude Code's native MCP instead.
        """
        return self._available

    def detect_cnv_version(self) -> Optional[CNVVersionInfo]:
        """
        Detect CNV version from cluster or environment.

        This is the primary fallback method used during Phase 1.
        Uses oc/kubectl commands to detect CNV version from cluster.

        Returns:
            CNVVersionInfo with detected version, or None if unavailable.
        """
        # Try to detect from cluster using oc
        version_info = self._detect_from_cluster()
        if version_info:
            return version_info

        # Try environment variable
        version_info = self._detect_from_env()
        if version_info:
            return version_info

        return None

    def _detect_from_cluster(self) -> Optional[CNVVersionInfo]:
        """Detect CNV version from OpenShift cluster."""
        try:
            # Try CNV CSV
            cmd = [
                'oc', 'get', 'csv', '-n', 'openshift-cnv',
                '-o', 'jsonpath={.items[0].metadata.name},{.items[0].spec.version}'
            ]
            success, stdout, stderr = run_subprocess(cmd, timeout=TIMEOUTS.CLUSTER_COMMAND)

            if success and stdout.strip():
                parts = stdout.strip().split(',')
                if len(parts) >= 2:
                    csv_name = parts[0]
                    version = parts[1]
                    branch = self._version_to_branch(version)
                    return CNVVersionInfo(
                        version=version,
                        branch=branch,
                        detected_from='cluster',
                        csv_name=csv_name
                    )

        except Exception as e:
            self.logger.debug(f"Cluster CNV detection failed: {e}")

        # Try kubevirt version as fallback
        try:
            cmd = [
                'oc', 'get', 'kubevirt', '-n', 'openshift-cnv',
                '-o', 'jsonpath={.items[0].status.observedKubeVirtVersion}'
            ]
            success, stdout, stderr = run_subprocess(cmd, timeout=TIMEOUTS.CLUSTER_COMMAND)

            if success and stdout.strip():
                version = stdout.strip()
                branch = self._version_to_branch(version)
                return CNVVersionInfo(
                    version=version,
                    branch=branch,
                    detected_from='cluster',
                    csv_name=None
                )

        except Exception as e:
            self.logger.debug(f"KubeVirt version detection failed: {e}")

        return None

    def _detect_from_env(self) -> Optional[CNVVersionInfo]:
        """Detect CNV version from environment variables."""
        env_version = os.environ.get('CNV_VERSION')
        if env_version:
            branch = self._version_to_branch(env_version)
            return CNVVersionInfo(
                version=env_version,
                branch=branch,
                detected_from='env',
                csv_name=None
            )
        return None

    def _version_to_branch(self, version: str) -> str:
        """Convert version string to branch name."""
        # e.g., "4.20.3" -> "release-4.20"
        parts = version.split('.')
        if len(parts) >= 2:
            return f"release-{parts[0]}.{parts[1]}"
        return 'main'

    def get_fleet_virt_selectors(self, version: Optional[str] = None) -> Optional[FleetVirtSelectors]:
        """
        Get Fleet Virtualization selectors.

        Note: This method requires the MCP server which is now accessed
        via Claude Code's native MCP. Returns None in Python client.

        For Phase 2, use: mcp__acm-ui__get_fleet_virt_selectors
        """
        self.logger.debug(
            "get_fleet_virt_selectors requires MCP. "
            "Use Claude Code's native mcp__acm-ui__get_fleet_virt_selectors tool."
        )
        return None

    def find_test_ids(self, file_path: str, repository: str = 'acm') -> List[ElementInfo]:
        """
        Find test IDs in a file.

        Note: This method requires the MCP server which is now accessed
        via Claude Code's native MCP. Returns empty list in Python client.

        For Phase 2, use: mcp__acm-ui__find_test_ids
        """
        self.logger.debug(
            "find_test_ids requires MCP. "
            "Use Claude Code's native mcp__acm-ui__find_test_ids tool."
        )
        return []

    def search_code(self, query: str, repository: str = 'acm', max_results: int = 20) -> List[SearchResult]:
        """
        Search code across repositories.

        Note: This method requires the MCP server which is now accessed
        via Claude Code's native MCP. Returns empty list in Python client.

        For Phase 2, use: mcp__acm-ui__search_code
        """
        self.logger.debug(
            "search_code requires MCP. "
            "Use Claude Code's native mcp__acm-ui__search_code tool."
        )
        return []

    def find_element_definition(self, selector: str, search_all_repos: bool = True) -> Dict[str, List[SearchResult]]:
        """
        Find element definitions.

        Note: This method requires the MCP server. Returns empty dict in Python client.

        For Phase 2, use Claude Code's native MCP tools for element discovery.
        """
        return {}

    def get_element_inventory(
        self,
        component_paths: Optional[List[str]] = None,
        repository: str = 'acm'
    ) -> Dict[str, List[ElementInfo]]:
        """
        Build element inventory.

        Note: This method requires the MCP server. Returns empty dict in Python client.

        For Phase 2, use Claude Code's native MCP tools.
        """
        return {}

    def to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert a dataclass to dictionary."""
        if hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        return {}


# Singleton instance
_acm_ui_mcp_client: Optional[ACMUIMCPClient] = None


def get_acm_ui_mcp_client() -> ACMUIMCPClient:
    """Get the singleton ACM UI MCP client instance."""
    global _acm_ui_mcp_client
    if _acm_ui_mcp_client is None:
        _acm_ui_mcp_client = ACMUIMCPClient()
    return _acm_ui_mcp_client


def is_acm_ui_mcp_available() -> bool:
    """
    Check if ACM UI MCP is available.

    Note: Python client MCP calls are deprecated.
    Use Claude Code's native MCP for Phase 2 analysis.
    """
    return get_acm_ui_mcp_client().is_available
