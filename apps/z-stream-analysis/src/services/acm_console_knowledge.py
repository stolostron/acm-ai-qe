#!/usr/bin/env python3
"""
ACM Console Knowledge Service

Provides structured knowledge about the ACM (Advanced Cluster Management) console
repository structure to improve UI failure investigation accuracy.

This service maps test names to feature areas and provides relevant directory
paths for focused investigation.

Optionally integrates with ACM UI MCP Server for version-aware element discovery
when available, with fallback to static patterns.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .acm_ui_mcp_client import ACMUIMCPClient


class ACMConsoleKnowledge:
    """ACM console repository structure knowledge with optional MCP integration."""

    # ACM console directory structure (stolostron/console)
    DIRECTORY_STRUCTURE = {
        'ui_components': 'frontend/src/ui-components/',
        'routes': 'frontend/src/routes/',
        'components': 'frontend/src/components/',
        'plugins_acm': 'frontend/plugins/acm/',
        'plugins_mce': 'frontend/plugins/mce/',
        'form_wizard': 'frontend/packages/react-form-wizard/',
        'multicluster_sdk': 'frontend/packages/multicluster-sdk/',
        'lib': 'frontend/src/lib/',
        'atoms': 'frontend/src/atoms/',
        'wizards': 'frontend/src/wizards/',
    }

    # KubeVirt plugin directory structure (kubevirt-ui/kubevirt-plugin)
    # Virtualization feature UI components are stored in this separate repo
    KUBEVIRT_DIRECTORY_STRUCTURE = {
        'src': 'src/',
        'views': 'src/views/',
        'components': 'src/components/',
        'utils': 'src/utils/',
        'templates': 'src/templates/',
        'console_extensions': 'src/utils/extensions/',
        'cypress': 'cypress/',
        'locales': 'locales/',
    }

    # Feature area routing paths in console
    FEATURE_ROUTES = {
        'clusters': 'Infrastructure/Clusters/',
        'managedcluster': 'Infrastructure/Clusters/ManagedClusters/',
        'clusterset': 'Infrastructure/Clusters/ClusterSets/',
        'clusterpool': 'Infrastructure/Clusters/ClusterPools/',
        'discovered': 'Infrastructure/Clusters/DiscoveredClusters/',
        'vm': 'Infrastructure/VirtualMachines/',
        'virtualmachine': 'Infrastructure/VirtualMachines/',
        'kubevirt': 'Infrastructure/VirtualMachines/',
        'policy': 'Governance/',
        'governance': 'Governance/',
        'policyset': 'Governance/PolicySets/',
        'application': 'Applications/',
        'applicationset': 'Applications/ApplicationSets/',
        'subscription': 'Applications/',
        'credential': 'Credentials/',
        'ansible': 'Infrastructure/Automations/',
        'automation': 'Infrastructure/Automations/',
        'search': 'Search/',
        'overview': 'Overview/',
        'home': 'Home/',
    }

    # Features that require kubevirt-plugin repo investigation
    KUBEVIRT_FEATURES = {'vm', 'virtualmachine', 'kubevirt'}

    # Common ACM UI component prefixes
    ACM_COMPONENT_PREFIXES = [
        'Acm',      # AcmTable, AcmModal, AcmButton, etc.
        'Pf',       # PatternFly wrappers
        'Mce',      # MCE-specific components
    ]

    # Common data-testid patterns in ACM console
    TESTID_PATTERNS = [
        r'data-testid=["\']([^"\']+)["\']',
        r'data-test-id=["\']([^"\']+)["\']',
        r'testId=["\']([^"\']+)["\']',
        r'id=["\']([^"\']+)["\']',
    ]

    def __init__(self, mcp_client: Optional['ACMUIMCPClient'] = None):
        """
        Initialize ACM Console Knowledge service.

        Args:
            mcp_client: Optional ACM UI MCP client for version-aware lookups.
                       If not provided, falls back to static patterns only.
        """
        self.logger = logging.getLogger(__name__)
        self._mcp_client = mcp_client
        self._element_cache: Dict[str, List[Any]] = {}

    def map_test_to_feature(self, test_name: str) -> Optional[str]:
        """
        Map a test name to its corresponding ACM feature area.

        Args:
            test_name: Test name or file path from stack trace

        Returns:
            Feature area identifier (e.g., 'clusters', 'policy') or None
        """
        if not test_name:
            return None

        test_lower = test_name.lower()

        # Check for specific feature patterns first (more specific before general)
        # Order matters - check more specific patterns before general ones
        feature_patterns = [
            # Specific cluster features first
            (r'managedcluster', 'managedcluster'),
            (r'cluster[-_]?set', 'clusterset'),
            (r'cluster[-_]?pool', 'clusterpool'),
            (r'discovered[-_]?cluster', 'discovered'),
            # General cluster pattern last for cluster features
            (r'cluster', 'clusters'),
            # VM/KubeVirt patterns - check kubevirt first (more specific)
            (r'kubevirt', 'kubevirt'),
            (r'virtualmachine', 'virtualmachine'),
            (r'virtual[-_]?machine', 'virtualmachine'),
            (r'vm[-_]', 'vm'),
            (r'\bvm\b', 'vm'),
            # Policy/Governance
            (r'policyset', 'policyset'),
            (r'polic(?:y|ies)', 'policy'),
            (r'governance', 'governance'),
            # Applications
            (r'applicationset', 'applicationset'),
            (r'application', 'application'),
            (r'subscription', 'subscription'),
            # Others
            (r'credential', 'credential'),
            (r'ansible', 'ansible'),
            (r'automation', 'automation'),
            (r'search', 'search'),
            (r'overview', 'overview'),
            (r'home', 'home'),
        ]

        for pattern, feature in feature_patterns:
            if re.search(pattern, test_lower):
                self.logger.debug(f"Mapped test '{test_name}' to feature '{feature}'")
                return feature

        return None

    def get_relevant_directories(
        self,
        test_name: str,
        error_message: str = ""
    ) -> Dict[str, str]:
        """
        Get relevant console directories for investigating a test failure.

        Args:
            test_name: Test name or file path
            error_message: Error message from the failure

        Returns:
            Dict mapping directory purposes to paths
        """
        feature = self.map_test_to_feature(test_name)

        result = {
            'primary_route': None,
            'ui_components': self.DIRECTORY_STRUCTURE['ui_components'],
            'shared_components': self.DIRECTORY_STRUCTURE['components'],
        }

        if feature and feature in self.FEATURE_ROUTES:
            route_path = self.FEATURE_ROUTES[feature]
            result['primary_route'] = f"{self.DIRECTORY_STRUCTURE['routes']}{route_path}"

        # Add plugin paths for ACM/MCE features
        if feature in ['clusters', 'managedcluster', 'clusterset', 'clusterpool']:
            result['acm_plugin'] = self.DIRECTORY_STRUCTURE['plugins_acm']
            result['mce_plugin'] = self.DIRECTORY_STRUCTURE['plugins_mce']

        # Add kubevirt-plugin paths for virtualization features
        if feature in self.KUBEVIRT_FEATURES:
            result['kubevirt_plugin'] = True  # Flag to indicate kubevirt repo needed
            result['kubevirt_src'] = self.KUBEVIRT_DIRECTORY_STRUCTURE['src']
            result['kubevirt_views'] = self.KUBEVIRT_DIRECTORY_STRUCTURE['views']
            result['kubevirt_components'] = self.KUBEVIRT_DIRECTORY_STRUCTURE['components']

        # Check error message for component hints
        if error_message:
            error_lower = error_message.lower()

            # Check for specific component mentions
            if 'modal' in error_lower:
                result['look_for'] = 'AcmModal components in ui_components'
            elif 'table' in error_lower:
                result['look_for'] = 'AcmTable components in ui_components'
            elif 'form' in error_lower or 'wizard' in error_lower:
                result['wizard'] = self.DIRECTORY_STRUCTURE['form_wizard']

        return result

    def get_console_structure(self) -> Dict[str, str]:
        """
        Get the full ACM console directory structure.

        Returns:
            Dict mapping directory names to paths
        """
        return self.DIRECTORY_STRUCTURE.copy()

    def get_feature_routes(self) -> Dict[str, str]:
        """
        Get the feature-to-route mapping.

        Returns:
            Dict mapping feature names to route paths
        """
        return self.FEATURE_ROUTES.copy()

    def extract_patternfly_version(self, console_path: Path) -> Optional[Dict[str, str]]:
        """
        Extract PatternFly version information from console repo's package.json.

        Args:
            console_path: Path to the cloned console repository

        Returns:
            Dict with PatternFly versions or None if not found
        """
        package_json_paths = [
            console_path / 'frontend' / 'package.json',
            console_path / 'package.json',
        ]

        for pkg_path in package_json_paths:
            if pkg_path.exists():
                try:
                    with open(pkg_path, 'r', encoding='utf-8') as f:
                        pkg_data = json.load(f)

                    dependencies = pkg_data.get('dependencies', {})
                    dev_dependencies = pkg_data.get('devDependencies', {})
                    all_deps = {**dependencies, **dev_dependencies}

                    pf_versions = {}
                    for key, value in all_deps.items():
                        if key.startswith('@patternfly/'):
                            pf_versions[key] = value

                    if pf_versions:
                        self.logger.info(f"Found PatternFly versions: {len(pf_versions)} packages")
                        return pf_versions

                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse {pkg_path}: {e}")
                except Exception as e:
                    self.logger.warning(f"Error reading {pkg_path}: {e}")

        return None

    def validate_structure(self, console_path: Path) -> Dict[str, bool]:
        """
        Validate that expected ACM console directories exist.

        Args:
            console_path: Path to the cloned console repository

        Returns:
            Dict mapping directory names to existence status
        """
        results = {}

        for name, rel_path in self.DIRECTORY_STRUCTURE.items():
            full_path = console_path / rel_path
            exists = full_path.exists()
            results[name] = exists

            if not exists:
                self.logger.debug(f"Directory not found: {rel_path}")

        return results

    def get_investigation_paths(
        self,
        feature_area: Optional[str],
        failure_type: str = 'element_not_found'
    ) -> List[str]:
        """
        Get prioritized list of paths to investigate for a failure.

        Args:
            feature_area: The feature area (e.g., 'clusters', 'policy')
            failure_type: Type of failure (element_not_found, timeout, assertion, etc.)

        Returns:
            Ordered list of relative paths to check
        """
        paths = []

        # Add feature-specific route first
        if feature_area and feature_area in self.FEATURE_ROUTES:
            route_path = self.FEATURE_ROUTES[feature_area]
            paths.append(f"frontend/src/routes/{route_path}")

        # Add common locations based on failure type
        if failure_type == 'element_not_found':
            paths.extend([
                self.DIRECTORY_STRUCTURE['ui_components'],
                self.DIRECTORY_STRUCTURE['components'],
            ])
        elif failure_type == 'timeout':
            paths.extend([
                self.DIRECTORY_STRUCTURE['lib'],
                self.DIRECTORY_STRUCTURE['components'],
            ])
        elif failure_type == 'assertion':
            paths.extend([
                self.DIRECTORY_STRUCTURE['multicluster_sdk'],
                self.DIRECTORY_STRUCTURE['lib'],
            ])

        # Always include plugins for cluster-related features
        if feature_area in ['clusters', 'managedcluster', 'clusterset', 'clusterpool']:
            paths.extend([
                self.DIRECTORY_STRUCTURE['plugins_acm'],
                self.DIRECTORY_STRUCTURE['plugins_mce'],
            ])

        # Include kubevirt-plugin paths for virtualization features
        if feature_area in self.KUBEVIRT_FEATURES:
            paths.extend([
                self.KUBEVIRT_DIRECTORY_STRUCTURE['src'],
                self.KUBEVIRT_DIRECTORY_STRUCTURE['views'],
                self.KUBEVIRT_DIRECTORY_STRUCTURE['components'],
            ])

        return paths

    def extract_selector_from_error(self, error_message: str) -> Optional[str]:
        """
        Extract a selector from an error message.

        Args:
            error_message: Error message containing selector

        Returns:
            Extracted selector or None
        """
        if not error_message:
            return None

        # Common selector patterns in Cypress errors
        patterns = [
            r"Timed out.*?['\"]([#\.\[\]][^'\"]+)['\"]",
            r"get\(['\"]([^'\"]+)['\"]\)",
            r"find\(['\"]([^'\"]+)['\"]\)",
            r"Expected to find element: ([^\n]+)",
            r"element: ([#\.\[][^\s]+)",
            r"selector ['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_message, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def suggest_search_patterns(self, selector: str) -> List[str]:
        """
        Suggest search patterns for finding an element in the console repo.

        Args:
            selector: The failing selector (e.g., '#my-button', '[data-testid="x"]')

        Returns:
            List of grep patterns to try
        """
        patterns = []

        # Handle ID selectors: #my-button -> my-button
        if selector.startswith('#'):
            element_id = selector[1:]
            patterns.extend([
                f'id="{element_id}"',
                f"id='{element_id}'",
                f'data-testid="{element_id}"',
                f"data-testid='{element_id}'",
                f'testId="{element_id}"',
            ])

        # Handle attribute selectors: [data-testid='x'] -> x
        elif selector.startswith('['):
            match = re.search(r"\[[\w-]+=['\"]([^'\"]+)['\"]\]", selector)
            if match:
                value = match.group(1)
                patterns.extend([
                    f'data-testid="{value}"',
                    f"data-testid='{value}'",
                    f'testId="{value}"',
                    f'id="{value}"',
                ])

        # Handle class selectors: .my-class -> my-class
        elif selector.startswith('.'):
            class_name = selector[1:]
            patterns.extend([
                f'className="{class_name}"',
                f'className="[^"]*{class_name}[^"]*"',
                f"className='[^']*{class_name}[^']*'",
            ])

        # Default: try as-is
        if not patterns:
            patterns.append(selector)

        return patterns

    def requires_kubevirt_repo(self, test_name: str) -> bool:
        """
        Check if a test requires the kubevirt-plugin repository for investigation.

        Args:
            test_name: Test name or file path

        Returns:
            True if kubevirt-plugin repo should be cloned and investigated
        """
        feature = self.map_test_to_feature(test_name)
        return feature in self.KUBEVIRT_FEATURES

    def get_kubevirt_structure(self) -> Dict[str, str]:
        """
        Get the kubevirt-plugin directory structure.

        Returns:
            Dict mapping directory names to paths
        """
        return self.KUBEVIRT_DIRECTORY_STRUCTURE.copy()

    def validate_kubevirt_structure(self, kubevirt_path: Path) -> Dict[str, bool]:
        """
        Validate that expected kubevirt-plugin directories exist.

        Args:
            kubevirt_path: Path to the cloned kubevirt-plugin repository

        Returns:
            Dict mapping directory names to existence status
        """
        results = {}

        for name, rel_path in self.KUBEVIRT_DIRECTORY_STRUCTURE.items():
            full_path = kubevirt_path / rel_path
            exists = full_path.exists()
            results[name] = exists

            if not exists:
                self.logger.debug(f"KubeVirt directory not found: {rel_path}")

        return results

    # =========================================================================
    # MCP Integration Methods
    # =========================================================================

    @property
    def mcp_available(self) -> bool:
        """Check if MCP client is available and configured."""
        return self._mcp_client is not None and self._mcp_client.is_available

    def set_mcp_client(self, mcp_client: Optional['ACMUIMCPClient']) -> None:
        """
        Set or update the MCP client.

        Args:
            mcp_client: ACM UI MCP client instance or None to disable
        """
        self._mcp_client = mcp_client
        self._element_cache.clear()  # Clear cache when client changes

    def find_element_with_mcp(
        self,
        selector: str,
        search_all_repos: bool = True
    ) -> Dict[str, Any]:
        """
        Find element definition using MCP if available, with fallback to static patterns.

        Args:
            selector: The selector to search for
            search_all_repos: Search both ACM and kubevirt repos

        Returns:
            Dict with search results and metadata
        """
        result = {
            'selector': selector,
            'found': False,
            'source': 'none',
            'locations': {},
            'search_patterns': []
        }

        # Try MCP first if available
        if self.mcp_available:
            try:
                mcp_results = self._mcp_client.find_element_definition(
                    selector,
                    search_all_repos=search_all_repos
                )
                if mcp_results:
                    result['found'] = True
                    result['source'] = 'mcp'
                    result['locations'] = {
                        repo: [
                            {
                                'file': r.file_path,
                                'line': r.line_number,
                                'content': r.line_content,
                                'url': r.url
                            }
                            for r in results
                        ]
                        for repo, results in mcp_results.items()
                    }
                    return result
            except Exception as e:
                self.logger.debug(f"MCP element lookup failed, using fallback: {e}")

        # Fallback to static patterns
        result['source'] = 'static_patterns'
        result['search_patterns'] = self.suggest_search_patterns(selector)

        return result

    def get_fleet_virt_selectors(self) -> Optional[Dict[str, Any]]:
        """
        Get Fleet Virtualization selectors via MCP.

        Returns:
            Dict with selector information or None if unavailable
        """
        if not self.mcp_available:
            return None

        try:
            selectors = self._mcp_client.get_fleet_virt_selectors()
            if selectors:
                return {
                    'selectors': selectors.selectors,
                    'total_count': selectors.total_count,
                    'version': selectors.version,
                    'source': 'mcp'
                }
        except Exception as e:
            self.logger.debug(f"Failed to get Fleet Virt selectors: {e}")

        return None

    def get_cnv_version(self) -> Optional[Dict[str, str]]:
        """
        Get CNV version information via MCP.

        Returns:
            Dict with version info or None if unavailable
        """
        if not self.mcp_available:
            return None

        try:
            version_info = self._mcp_client.detect_cnv_version()
            if version_info:
                return {
                    'version': version_info.version,
                    'branch': version_info.branch,
                    'detected_from': version_info.detected_from
                }
        except Exception as e:
            self.logger.debug(f"Failed to get CNV version: {e}")

        return None

    def build_element_inventory(
        self,
        repository: str = 'acm',
        component_paths: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build element inventory for components using MCP.

        Args:
            repository: Repository to scan ('acm' or 'kubevirt')
            component_paths: Specific paths to scan (None for defaults)

        Returns:
            Dict mapping paths to element lists
        """
        if not self.mcp_available:
            return {}

        # Check cache first
        cache_key = f"{repository}:{','.join(component_paths or [])}"
        if cache_key in self._element_cache:
            return self._element_cache[cache_key]

        try:
            inventory = self._mcp_client.get_element_inventory(
                component_paths=component_paths,
                repository=repository
            )

            # Convert to serializable format
            result = {}
            for path, elements in inventory.items():
                result[path] = [
                    {
                        'selector': elem.selector,
                        'type': elem.selector_type,
                        'file': elem.file_path,
                        'line': elem.line_number,
                        'context': elem.context
                    }
                    for elem in elements
                ]

            # Cache result
            self._element_cache[cache_key] = result
            return result

        except Exception as e:
            self.logger.debug(f"Failed to build element inventory: {e}")

        return {}

    def get_investigation_hints_with_mcp(
        self,
        test_name: str,
        error_message: str = "",
        failure_type: str = 'element_not_found'
    ) -> Dict[str, Any]:
        """
        Get investigation hints enhanced with MCP data when available.

        Args:
            test_name: Test name or file path
            error_message: Error message from failure
            failure_type: Type of failure

        Returns:
            Dict with investigation hints including MCP-enhanced data
        """
        # Start with base hints
        hints = {
            'feature_area': self.map_test_to_feature(test_name),
            'relevant_directories': self.get_relevant_directories(test_name, error_message),
            'investigation_paths': [],
            'mcp_data': {}
        }

        # Get investigation paths
        if hints['feature_area']:
            hints['investigation_paths'] = self.get_investigation_paths(
                hints['feature_area'],
                failure_type
            )

        # Extract selector from error
        selector = self.extract_selector_from_error(error_message)
        if selector:
            hints['extracted_selector'] = selector
            hints['search_patterns'] = self.suggest_search_patterns(selector)

            # Enhance with MCP if available
            if self.mcp_available:
                element_info = self.find_element_with_mcp(selector)
                if element_info['found']:
                    hints['mcp_data']['element_locations'] = element_info['locations']

        # Add Fleet Virt selectors for VM tests
        if hints['feature_area'] in self.KUBEVIRT_FEATURES:
            fleet_selectors = self.get_fleet_virt_selectors()
            if fleet_selectors:
                hints['mcp_data']['fleet_virt_selectors'] = fleet_selectors

        return hints
