"""
Knowledge Graph Client Service

Optional client for RHACM Knowledge Graph (Neo4j) dependency queries.
Provides cascading failure detection and component dependency analysis.

This service is OPTIONAL - the system works without Neo4j.
When Neo4j is available, it enriches AI analysis with dependency insights.

Prerequisites:
    - Neo4j database with RHACM data loaded
    - MCP server registered: mcp__neo4j-rhacm__read_neo4j_cypher

Usage:
    client = KnowledgeGraphClient()
    if client.available:
        deps = client.get_dependencies('search-api')
        # Returns: ['console', 'observability-operator', ...]
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple

from .shared_utils import run_subprocess, TIMEOUTS


@dataclass
class ComponentInfo:
    """Information about an RHACM component."""
    name: str
    subsystem: Optional[str] = None
    component_type: Optional[str] = None  # operator, controller, CRD, etc.
    dependencies: Optional[List[str]] = None
    dependents: Optional[List[str]] = None


@dataclass
class DependencyChain:
    """Represents a chain of component dependencies."""
    source_component: str
    affected_components: List[str]
    chain_length: int
    subsystems_affected: List[str]


class KnowledgeGraphClient:
    """
    Optional client for RHACM Knowledge Graph queries via MCP.

    Provides component dependency analysis to enrich failure classification.
    Falls back gracefully when Neo4j is unavailable.

    Features:
        - Component dependency lookup
        - Cascading failure detection
        - Subsystem impact analysis
        - Root cause correlation

    Example:
        client = KnowledgeGraphClient()
        if client.available:
            # Get what depends on search-api
            deps = client.get_dependents('search-api')

            # Check if multiple failures share a common dependency
            common = client.find_common_dependency(['search-api', 'console'])
    """

    # Cache for expensive queries
    _component_cache: Dict[str, ComponentInfo] = {}
    _dependency_cache: Dict[str, List[str]] = {}

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the Knowledge Graph client.

        Checks for Neo4j MCP availability and sets up connection.
        """
        self.logger = logger or logging.getLogger(__name__)
        self._available: Optional[bool] = None
        self._mcp_tool_name = 'mcp__neo4j-rhacm__read_neo4j_cypher'

    @property
    def available(self) -> bool:
        """
        Check if the Knowledge Graph MCP is available.

        Caches the result to avoid repeated checks.
        """
        if self._available is None:
            self._available = self._check_availability()
        return self._available

    def _check_availability(self) -> bool:
        """
        Check if the Neo4j MCP server is available.

        This is a lightweight check that doesn't require a full query.
        """
        try:
            # Try to execute a minimal query to verify connection
            result = self._execute_cypher("RETURN 1 as test")
            return result is not None
        except Exception as e:
            self.logger.debug(f"Knowledge Graph not available: {e}")
            return False

    def _execute_cypher(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a Cypher query via MCP.

        This method would normally use the MCP tool, but since we're in
        Phase 1 (gather.py), we can only prepare the query. The actual
        execution happens in Phase 2 when Claude Code agent runs.

        For Phase 1, we return None and let Phase 2 handle queries.

        Args:
            query: Cypher query string

        Returns:
            Query results or None if unavailable
        """
        # In Phase 1 (gather.py context), we cannot call MCP tools directly.
        # MCP tools are available in Phase 2 when Claude Code agent runs.
        # This method is provided for Phase 2 usage.
        self.logger.debug(f"Cypher query prepared: {query[:100]}...")
        return None

    def get_dependencies(self, component: str) -> List[str]:
        """
        Get components that the specified component depends on.

        Args:
            component: Component name (e.g., 'search-api')

        Returns:
            List of component names this component depends on
        """
        if not self.available:
            return []

        cache_key = f"deps:{component}"
        if cache_key in self._dependency_cache:
            return self._dependency_cache[cache_key]

        query = f"""
        MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent)
        WHERE c.label =~ '(?i).*{component}.*'
        RETURN DISTINCT dep.label as dependency
        ORDER BY dep.label
        """

        result = self._execute_cypher(query)
        if result:
            deps = [r['dependency'] for r in result if r.get('dependency')]
            self._dependency_cache[cache_key] = deps
            return deps
        return []

    def get_dependents(self, component: str) -> List[str]:
        """
        Get components that depend on the specified component.

        This is the key query for cascading failure detection.
        If component X is failing, all its dependents may be affected.

        Args:
            component: Component name (e.g., 'search-api')

        Returns:
            List of component names that depend on this component
        """
        if not self.available:
            return []

        cache_key = f"dependents:{component}"
        if cache_key in self._dependency_cache:
            return self._dependency_cache[cache_key]

        query = f"""
        MATCH (dep:RHACMComponent)-[:DEPENDS_ON]->(c:RHACMComponent)
        WHERE c.label =~ '(?i).*{component}.*'
        RETURN DISTINCT dep.label as dependent
        ORDER BY dep.label
        """

        result = self._execute_cypher(query)
        if result:
            deps = [r['dependent'] for r in result if r.get('dependent')]
            self._dependency_cache[cache_key] = deps
            return deps
        return []

    def get_transitive_dependents(
        self,
        component: str,
        max_depth: int = 3
    ) -> DependencyChain:
        """
        Get all components affected by a failure in the specified component.

        Follows the dependency chain up to max_depth levels to identify
        all potentially affected components.

        Args:
            component: Component name
            max_depth: Maximum depth to traverse (default: 3)

        Returns:
            DependencyChain with all affected components
        """
        if not self.available:
            return DependencyChain(
                source_component=component,
                affected_components=[],
                chain_length=0,
                subsystems_affected=[]
            )

        query = f"""
        MATCH path = (dep:RHACMComponent)-[:DEPENDS_ON*1..{max_depth}]->(c:RHACMComponent)
        WHERE c.label =~ '(?i).*{component}.*'
        WITH dep, length(path) as depth
        RETURN DISTINCT dep.label as affected, dep.subsystem as subsystem
        ORDER BY affected
        """

        result = self._execute_cypher(query)
        if result:
            affected = [r['affected'] for r in result if r.get('affected')]
            subsystems = list(set(
                r['subsystem'] for r in result
                if r.get('subsystem')
            ))
            return DependencyChain(
                source_component=component,
                affected_components=affected,
                chain_length=max_depth,
                subsystems_affected=subsystems
            )

        return DependencyChain(
            source_component=component,
            affected_components=[],
            chain_length=0,
            subsystems_affected=[]
        )

    def get_component_info(self, component: str) -> Optional[ComponentInfo]:
        """
        Get detailed information about a component.

        Args:
            component: Component name

        Returns:
            ComponentInfo or None if not found
        """
        if not self.available:
            return None

        if component in self._component_cache:
            return self._component_cache[component]

        query = f"""
        MATCH (c:RHACMComponent)
        WHERE c.label =~ '(?i).*{component}.*'
        OPTIONAL MATCH (c)-[:DEPENDS_ON]->(dep:RHACMComponent)
        OPTIONAL MATCH (dependent:RHACMComponent)-[:DEPENDS_ON]->(c)
        RETURN c.label as name, c.subsystem as subsystem, c.type as type,
               collect(DISTINCT dep.label) as dependencies,
               collect(DISTINCT dependent.label) as dependents
        LIMIT 1
        """

        result = self._execute_cypher(query)
        if result and len(result) > 0:
            r = result[0]
            info = ComponentInfo(
                name=r.get('name', component),
                subsystem=r.get('subsystem'),
                component_type=r.get('type'),
                dependencies=r.get('dependencies', []),
                dependents=r.get('dependents', [])
            )
            self._component_cache[component] = info
            return info
        return None

    def find_common_dependency(
        self,
        components: List[str]
    ) -> Optional[str]:
        """
        Find a common dependency shared by multiple components.

        Useful for identifying root cause when multiple unrelated
        tests fail simultaneously.

        Args:
            components: List of component names

        Returns:
            Common dependency name or None if not found
        """
        if not self.available or len(components) < 2:
            return None

        # Build a query to find intersection of dependencies
        component_patterns = '|'.join(
            f'(?i).*{c}.*' for c in components
        )

        query = f"""
        MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common:RHACMComponent)
        WHERE c.label =~ '{component_patterns}'
        WITH common, count(DISTINCT c) as component_count
        WHERE component_count = {len(components)}
        RETURN common.label as common_dependency
        ORDER BY common.label
        LIMIT 1
        """

        result = self._execute_cypher(query)
        if result and len(result) > 0:
            return result[0].get('common_dependency')
        return None

    def get_subsystem_components(self, subsystem: str) -> List[str]:
        """
        Get all components in a subsystem.

        Args:
            subsystem: Subsystem name (e.g., 'Governance', 'Search')

        Returns:
            List of component names in that subsystem
        """
        if not self.available:
            return []

        query = f"""
        MATCH (c:RHACMComponent)
        WHERE c.subsystem =~ '(?i).*{subsystem}.*'
        RETURN DISTINCT c.label as component
        ORDER BY c.label
        """

        result = self._execute_cypher(query)
        if result:
            return [r['component'] for r in result if r.get('component')]
        return []

    def analyze_failure_impact(
        self,
        components: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze the impact of failures in the given components.

        Provides a comprehensive view of:
        - Which subsystems are affected
        - Cascading effects
        - Potential root cause (if common dependency exists)

        Args:
            components: List of failing component names

        Returns:
            Analysis dict with impact information
        """
        analysis = {
            'failing_components': components,
            'subsystems_affected': [],
            'cascading_effects': {},
            'common_dependency': None,
            'total_affected_count': 0,
            'recommendations': []
        }

        if not self.available or not components:
            analysis['recommendations'].append(
                'Knowledge Graph unavailable - manual dependency analysis needed'
            )
            return analysis

        # Analyze each component
        all_affected: List[str] = []
        subsystems: set = set()

        for component in components:
            chain = self.get_transitive_dependents(component)
            if chain.affected_components:
                analysis['cascading_effects'][component] = chain.affected_components
                all_affected.extend(chain.affected_components)
                subsystems.update(chain.subsystems_affected)

            info = self.get_component_info(component)
            if info and info.subsystem:
                subsystems.add(info.subsystem)

        analysis['subsystems_affected'] = list(subsystems)
        analysis['total_affected_count'] = len(set(all_affected))

        # Look for common root cause
        if len(components) > 1:
            common = self.find_common_dependency(components)
            if common:
                analysis['common_dependency'] = common
                analysis['recommendations'].append(
                    f"Multiple failures share dependency on '{common}' - investigate this component first"
                )

        # Add recommendations based on analysis
        if len(subsystems) > 2:
            analysis['recommendations'].append(
                'Failures span multiple subsystems - likely infrastructure or cross-cutting issue'
            )

        if analysis['total_affected_count'] > 5:
            analysis['recommendations'].append(
                f'{analysis["total_affected_count"]} components potentially affected - prioritize root cause identification'
            )

        return analysis

    def clear_cache(self):
        """Clear all cached data."""
        self._component_cache.clear()
        self._dependency_cache.clear()
        self._available = None


def get_knowledge_graph_client(
    logger: Optional[logging.Logger] = None
) -> KnowledgeGraphClient:
    """
    Get a configured Knowledge Graph client instance.

    Args:
        logger: Optional logger instance

    Returns:
        Configured KnowledgeGraphClient
    """
    return KnowledgeGraphClient(logger=logger)


def is_knowledge_graph_available() -> bool:
    """
    Quick check if Knowledge Graph is available.

    Returns:
        True if Neo4j MCP is accessible
    """
    client = KnowledgeGraphClient()
    return client.available
