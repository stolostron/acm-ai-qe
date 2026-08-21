"""
Component Extractor Service

Extracts ACM component names from error messages for Knowledge Graph integration.
This service enables cascading failure detection and 500 error attribution.

Part of the lightweight, optional RHACM Knowledge Graph integration.
Works standalone without Neo4j - component extraction is always available.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Set


@dataclass
class ExtractedComponent:
    """Represents an extracted component with context."""
    name: str
    source: str  # 'error_message', 'stack_trace', 'console_log'
    context: str  # The snippet of text where it was found


class ComponentExtractor:
    """
    Extract ACM component names from error messages, stack traces, and logs.

    This service identifies backend component names in failure data, enabling
    the Knowledge Graph client to query component dependencies for root cause
    analysis.

    Usage:
        extractor = ComponentExtractor()
        components = extractor.extract_from_error("search-api returned 500")
        # Returns: ['search-api']
    """

    # ACM/MCE Core Components
    # Organized by subsystem for maintainability
    GOVERNANCE_COMPONENTS = [
        'grc-policy-propagator',
        'config-policy-controller',
        'governance-policy-framework',
        'policy-propagator',
        'iam-policy-controller',
        'cert-policy-controller',
    ]

    SEARCH_COMPONENTS = [
        'search-api',
        'search-collector',
        'search-indexer',
        'search-aggregator',
        'search-operator',
        'search-redisgraph',
    ]

    CLUSTER_MANAGEMENT_COMPONENTS = [
        'cluster-curator',
        'cluster-curator-controller',
        'clusterclaims-controller',
        'managedcluster-import-controller',
        'cluster-manager',
        'registration-controller',
        'registration-operator',
        'placement-controller',
        'work-manager',
        'managed-serviceaccount',
    ]

    PROVISIONING_COMPONENTS = [
        'hive',
        'hive-operator',
        'hive-controllers',
        'hypershift',
        'hypershift-operator',
        'assisted-service',
        'assisted-installer',
        'infrastructure-operator',
        'agent-service-config',
    ]

    OBSERVABILITY_COMPONENTS = [
        'observability-operator',
        'observability-controller',
        'metrics-collector',
        'thanos-query',
        'thanos-receive',
        'thanos-rule',
        'thanos-store',
        'grafana',
        'alertmanager',
        'multicluster-observability-operator',
    ]

    APPLICATION_COMPONENTS = [
        'application-manager',
        'subscription-controller',
        'channel-controller',
        'subscription-operator',
        'multicluster-operators-subscription',
        'argocd-application-controller',
    ]

    CONSOLE_COMPONENTS = [
        'console',
        'console-api',
        'console-header',
        'acm-console',
        'mce-console',
    ]

    VIRTUALIZATION_COMPONENTS = [
        'kubevirt-plugin',
        'kubevirt-operator',
        'virt-api',
        'virt-controller',
        'virt-handler',
        'vm-import-controller',
        'hyperconverged-cluster-operator',
        'cdi-operator',
        'cdi-apiserver',
    ]

    INFRASTRUCTURE_COMPONENTS = [
        'klusterlet',
        'klusterlet-agent',
        'klusterlet-addon-controller',
        'multicluster-engine',
        'multicluster-hub',
        'foundation-controller',
        'addon-manager',
    ]

    def __init__(self):
        """Initialize the component extractor with compiled patterns."""
        # Combine all component lists
        all_components = (
            self.GOVERNANCE_COMPONENTS +
            self.SEARCH_COMPONENTS +
            self.CLUSTER_MANAGEMENT_COMPONENTS +
            self.PROVISIONING_COMPONENTS +
            self.OBSERVABILITY_COMPONENTS +
            self.APPLICATION_COMPONENTS +
            self.CONSOLE_COMPONENTS +
            self.VIRTUALIZATION_COMPONENTS +
            self.INFRASTRUCTURE_COMPONENTS
        )

        # Build a single regex pattern for efficiency
        # Escape special characters and join with alternation
        escaped_components = [re.escape(c) for c in all_components]
        self._component_pattern = re.compile(
            r'\b(' + '|'.join(escaped_components) + r')\b',
            re.IGNORECASE
        )

        # Subsystem mapping for categorization
        self._subsystem_map = self._build_subsystem_map()

    def _build_subsystem_map(self) -> dict:
        """Build a mapping from component name to subsystem."""
        mapping = {}
        subsystems = [
            ('Governance', self.GOVERNANCE_COMPONENTS),
            ('Search', self.SEARCH_COMPONENTS),
            ('Cluster', self.CLUSTER_MANAGEMENT_COMPONENTS),
            ('Provisioning', self.PROVISIONING_COMPONENTS),
            ('Observability', self.OBSERVABILITY_COMPONENTS),
            ('Application', self.APPLICATION_COMPONENTS),
            ('Console', self.CONSOLE_COMPONENTS),
            ('Virtualization', self.VIRTUALIZATION_COMPONENTS),
            ('Infrastructure', self.INFRASTRUCTURE_COMPONENTS),
        ]
        for subsystem_name, components in subsystems:
            for component in components:
                mapping[component.lower()] = subsystem_name
        return mapping

    def extract_from_error(self, error_message: str) -> List[str]:
        """
        Extract component names from an error message.

        Args:
            error_message: Error message text to search

        Returns:
            List of unique component names found (lowercase, normalized)
        """
        if not error_message:
            return []

        matches = self._component_pattern.findall(error_message)
        # Normalize to lowercase and deduplicate while preserving order
        seen: Set[str] = set()
        result = []
        for match in matches:
            normalized = match.lower()
            if normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        return result

    def extract_from_stack_trace(self, stack_trace: str) -> List[str]:
        """
        Extract component names from a stack trace.

        Args:
            stack_trace: Stack trace text to search

        Returns:
            List of unique component names found
        """
        return self.extract_from_error(stack_trace)

    def extract_from_console_log(
        self,
        console_log: str,
        error_lines_only: bool = True
    ) -> List[str]:
        """
        Extract component names from Jenkins console log.

        Args:
            console_log: Full console log text
            error_lines_only: If True, only search lines containing 'error' or 'fail'

        Returns:
            List of unique component names found
        """
        if not console_log:
            return []

        if error_lines_only:
            # Filter to error lines for more relevant results
            lines = console_log.split('\n')
            error_lines = [
                line for line in lines
                if 'error' in line.lower() or 'fail' in line.lower()
            ]
            text_to_search = '\n'.join(error_lines)
        else:
            text_to_search = console_log

        return self.extract_from_error(text_to_search)

    def extract_with_context(
        self,
        text: str,
        source: str = 'unknown',
        context_chars: int = 50
    ) -> List[ExtractedComponent]:
        """
        Extract components with surrounding context for debugging.

        Args:
            text: Text to search
            source: Source identifier (e.g., 'error_message', 'stack_trace')
            context_chars: Number of characters of context to include

        Returns:
            List of ExtractedComponent objects with context
        """
        if not text:
            return []

        results = []
        seen: Set[str] = set()

        for match in self._component_pattern.finditer(text):
            component_name = match.group(1).lower()
            if component_name in seen:
                continue
            seen.add(component_name)

            # Extract context around the match
            start = max(0, match.start() - context_chars)
            end = min(len(text), match.end() + context_chars)
            context = text[start:end].strip()

            results.append(ExtractedComponent(
                name=component_name,
                source=source,
                context=context
            ))

        return results

    def get_subsystem(self, component_name: str) -> Optional[str]:
        """
        Get the subsystem a component belongs to.

        Args:
            component_name: Component name (case-insensitive)

        Returns:
            Subsystem name or None if not found
        """
        return self._subsystem_map.get(component_name.lower())

    def extract_all_from_test_failure(
        self,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        console_snippet: Optional[str] = None
    ) -> List[ExtractedComponent]:
        """
        Extract components from all available test failure data.

        Combines extraction from error message, stack trace, and console log
        with deduplication and source tracking.

        Args:
            error_message: Test failure error message
            stack_trace: Test failure stack trace
            console_snippet: Relevant console log snippet

        Returns:
            List of ExtractedComponent objects from all sources
        """
        all_components: List[ExtractedComponent] = []
        seen: Set[str] = set()

        sources = [
            (error_message, 'error_message'),
            (stack_trace, 'stack_trace'),
            (console_snippet, 'console_log'),
        ]

        for text, source in sources:
            if text:
                extracted = self.extract_with_context(text, source)
                for component in extracted:
                    if component.name not in seen:
                        seen.add(component.name)
                        all_components.append(component)

        return all_components

    def get_component_list(self) -> List[str]:
        """
        Get the full list of known component names.

        Returns:
            List of all known component names (lowercase)
        """
        return [c.lower() for c in (
            self.GOVERNANCE_COMPONENTS +
            self.SEARCH_COMPONENTS +
            self.CLUSTER_MANAGEMENT_COMPONENTS +
            self.PROVISIONING_COMPONENTS +
            self.OBSERVABILITY_COMPONENTS +
            self.APPLICATION_COMPONENTS +
            self.CONSOLE_COMPONENTS +
            self.VIRTUALIZATION_COMPONENTS +
            self.INFRASTRUCTURE_COMPONENTS
        )]

    def get_components_by_subsystem(self, subsystem: str) -> List[str]:
        """
        Get all components in a subsystem.

        Args:
            subsystem: Subsystem name (case-insensitive)

        Returns:
            List of component names in that subsystem
        """
        subsystem_lower = subsystem.lower()
        subsystem_map = {
            'governance': self.GOVERNANCE_COMPONENTS,
            'search': self.SEARCH_COMPONENTS,
            'cluster': self.CLUSTER_MANAGEMENT_COMPONENTS,
            'provisioning': self.PROVISIONING_COMPONENTS,
            'observability': self.OBSERVABILITY_COMPONENTS,
            'application': self.APPLICATION_COMPONENTS,
            'console': self.CONSOLE_COMPONENTS,
            'virtualization': self.VIRTUALIZATION_COMPONENTS,
            'infrastructure': self.INFRASTRUCTURE_COMPONENTS,
        }
        return [c.lower() for c in subsystem_map.get(subsystem_lower, [])]
