"""
Knowledge Graph Client Service

Optional client for RHACM Knowledge Graph (Neo4j) dependency queries.
Provides cascading failure detection and component dependency analysis.

This service is OPTIONAL - the system works without Neo4j.
When Neo4j is available, it enriches AI analysis with dependency insights.

Prerequisites:
    - Neo4j database with RHACM data loaded (podman start neo4j-rhacm)
    - Neo4j HTTP API accessible at NEO4J_HTTP_URL (default: http://localhost:7474)

Usage:
    client = KnowledgeGraphClient()
    if client.available:
        deps = client.get_dependencies('search-api')
        # Returns: ['console', 'observability-operator', ...]
"""

import json
import logging
import os
import re
import urllib.request
import urllib.error
from base64 import b64encode
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


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


# Default Neo4j connection settings (match the podman container config)
_DEFAULT_NEO4J_HTTP_URL = 'http://localhost:7474'
_DEFAULT_NEO4J_USER = 'neo4j'
_DEFAULT_NEO4J_PASSWORD = 'rhacmgraph'
_DEFAULT_NEO4J_DATABASE = 'neo4j'

# Mapping from app feature area names to KG subsystem names.
# The KG uses broad subsystem categories (7 total: Overview, Cluster,
# Governance, Console, Application, Observability, Search) while the
# app uses 12+ feature area names. Some app areas map to multiple KG
# subsystems (e.g., RBAC spans Cluster + Console).
#
# Verified against live KG (370 components, 541 relationships).
KG_SUBSYSTEM_MAP: Dict[str, List[str]] = {
    'CLC': ['Cluster'],
    'GRC': ['Governance'],
    'Search': ['Search'],
    'Console': ['Console'],
    'Application': ['Application'],
    'Observability': ['Observability'],
    'Virtualization': ['Cluster'],
    'RBAC': ['Cluster', 'Console'],
    'Automation': ['Cluster'],
    'Infrastructure': ['Overview'],
    'Foundation': ['Overview', 'Cluster'],
    'Install': ['Overview'],
    'CrossClusterMigration': ['Cluster'],
    # Display names used as fallbacks by the oracle
    'Cluster Lifecycle': ['Cluster'],
    'Governance, Risk & Compliance': ['Governance'],
    'Governance & Risk': ['Governance'],
    'Search & Discovery': ['Search'],
    'Application Lifecycle': ['Application'],
    'ACM Console': ['Console'],
    'Infrastructure Foundation': ['Overview'],
}


class KnowledgeGraphClient:
    """
    Client for RHACM Knowledge Graph queries via Neo4j HTTP API.

    Queries Neo4j directly using the HTTP query endpoint. This works in
    both Stage 1 (gather.py) and Stage 2 (AI agent), unlike the MCP tool
    which is only available to the AI agent.

    Connection settings can be overridden via environment variables:
        NEO4J_HTTP_URL  (default: http://localhost:7474)
        NEO4J_USER      (default: neo4j)
        NEO4J_PASSWORD  (default: rhacmgraph)
        NEO4J_DATABASE  (default: neo4j)

    Example:
        client = KnowledgeGraphClient()
        if client.available:
            # Get what depends on search-api
            deps = client.get_dependents('search-api')

            # Check if multiple failures share a common dependency
            common = client.find_common_dependency(['search-api', 'console'])
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the Knowledge Graph client.

        Reads connection settings from environment variables with fallbacks
        to defaults that match the standard podman container configuration.
        """
        self.logger = logger or logging.getLogger(__name__)
        self._available: Optional[bool] = None

        # Connection settings
        self._base_url = os.environ.get('NEO4J_HTTP_URL', _DEFAULT_NEO4J_HTTP_URL)
        self._user = os.environ.get('NEO4J_USER', _DEFAULT_NEO4J_USER)
        self._password = os.environ.get('NEO4J_PASSWORD', _DEFAULT_NEO4J_PASSWORD)
        self._database = os.environ.get('NEO4J_DATABASE', _DEFAULT_NEO4J_DATABASE)
        self._query_url = f"{self._base_url}/db/{self._database}/query/v2"

        # Build auth header
        credentials = f"{self._user}:{self._password}"
        self._auth_header = 'Basic ' + b64encode(credentials.encode()).decode()

        # Cache for expensive queries (instance-level to avoid shared mutable state)
        self._component_cache: Dict[str, ComponentInfo] = {}
        self._dependency_cache: Dict[str, List[str]] = {}

    @staticmethod
    def _escape_regex(value: str) -> str:
        """Escape special regex characters in user input for Cypher regex patterns."""
        return re.escape(value)

    @property
    def available(self) -> bool:
        """
        Check if the Knowledge Graph is available.

        Caches the result to avoid repeated checks.
        """
        if self._available is None:
            self._available = self._check_availability()
        return self._available

    def _check_availability(self) -> bool:
        """
        Check if Neo4j is available by probing the HTTP API root.

        Uses a lightweight GET to the Neo4j root endpoint which returns
        version info without requiring authentication in some configs,
        then falls back to an authenticated query.
        """
        try:
            result = self._execute_cypher("RETURN 1 as test")
            if result is not None:
                self.logger.debug("Knowledge Graph available via Neo4j HTTP API")
                return True
            return False
        except Exception as e:
            self.logger.debug(f"Knowledge Graph not available: {e}")
            return False

    def _execute_cypher(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a Cypher query via the Neo4j HTTP query API.

        Uses the Neo4j v2 query endpoint (POST /db/{db}/query/v2) which
        returns results in a compact format.

        Args:
            query: Cypher query string

        Returns:
            List of result dicts or None if query failed
        """
        try:
            payload = json.dumps({"statement": query}).encode('utf-8')
            req = urllib.request.Request(
                self._query_url,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': self._auth_header,
                },
                method='POST',
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode('utf-8'))

            # Check for errors
            if body.get('errors'):
                error_msg = body['errors'][0].get('message', 'Unknown error')
                self.logger.warning(f"Neo4j query error: {error_msg}")
                return None

            # Parse v2 response format: {"data": {"fields": [...], "values": [[...], ...]}}
            data = body.get('data', {})
            fields = data.get('fields', [])
            values = data.get('values', [])

            if not fields:
                return []

            # Convert to list of dicts
            results = []
            for row in values:
                row_dict = {}
                for i, field in enumerate(fields):
                    row_dict[field] = row[i] if i < len(row) else None
                results.append(row_dict)

            return results

        except urllib.error.URLError as e:
            self.logger.debug(f"Neo4j connection failed: {e}")
            return None
        except Exception as e:
            self.logger.debug(f"Neo4j query failed: {e}")
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

        escaped = self._escape_regex(component)
        query = f"""
        MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(dep:RHACMComponent)
        WHERE c.label =~ '(?i).*{escaped}.*'
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

        escaped = self._escape_regex(component)
        query = f"""
        MATCH (dep:RHACMComponent)-[:DEPENDS_ON]->(c:RHACMComponent)
        WHERE c.label =~ '(?i).*{escaped}.*'
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

        escaped = self._escape_regex(component)
        query = f"""
        MATCH path = (dep:RHACMComponent)-[:DEPENDS_ON*1..{max_depth}]->(c:RHACMComponent)
        WHERE c.label =~ '(?i).*{escaped}.*'
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

        escaped = self._escape_regex(component)
        query = f"""
        MATCH (c:RHACMComponent)
        WHERE c.label =~ '(?i).*{escaped}.*'
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
        # Wrap alternation in a group so the regex is valid: (?i)(.*comp1.*|.*comp2.*)
        inner_patterns = '|'.join(f'.*{self._escape_regex(c)}.*' for c in components)
        component_patterns = f'(?i)({inner_patterns})'

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

    @staticmethod
    def resolve_kg_subsystems(subsystem: str) -> List[str]:
        """
        Resolve an app feature area name to KG subsystem name(s).

        Uses KG_SUBSYSTEM_MAP for translation. Returns the input as-is
        if no mapping exists (allows direct KG subsystem names to pass through).

        Args:
            subsystem: App feature area name (e.g., 'CLC', 'GRC')

        Returns:
            List of KG subsystem names (e.g., ['Cluster'], ['Governance'])
        """
        return KG_SUBSYSTEM_MAP.get(subsystem, [subsystem])

    def get_subsystem_components(self, subsystem: str) -> List[str]:
        """
        Get all components in a subsystem.

        Uses KG_SUBSYSTEM_MAP to translate app feature area names (e.g.,
        'CLC', 'GRC') to KG subsystem names (e.g., 'Cluster', 'Governance').
        Falls back to regex matching if the subsystem is not in the map.

        Args:
            subsystem: Feature area or subsystem name (e.g., 'CLC', 'Search')

        Returns:
            List of component names in that subsystem
        """
        if not self.available:
            return []

        # Map app feature area name to KG subsystem name(s)
        kg_subsystems = KG_SUBSYSTEM_MAP.get(subsystem, [subsystem])

        all_components = []
        for kg_sub in kg_subsystems:
            escaped = self._escape_regex(kg_sub)
            query = f"""
            MATCH (c:RHACMComponent)
            WHERE c.subsystem =~ '(?i).*{escaped}.*'
            RETURN DISTINCT c.label as component
            ORDER BY c.label
            """

            result = self._execute_cypher(query)
            if result:
                all_components.extend(
                    [r['component'] for r in result if r.get('component')]
                )

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for c in all_components:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

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
        True if Neo4j is accessible via HTTP API
    """
    client = KnowledgeGraphClient()
    return client.available
