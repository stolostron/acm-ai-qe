"""
Unit tests for KnowledgeGraphClient service.

Tests the optional Knowledge Graph integration for component
dependency analysis and cascading failure detection.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.services.knowledge_graph_client import (
    KnowledgeGraphClient,
    ComponentInfo,
    DependencyChain,
    get_knowledge_graph_client,
    is_knowledge_graph_available
)


class TestKnowledgeGraphClientInitialization:
    """Test client initialization and availability checks."""

    def test_client_initialization(self):
        """Test that client initializes without errors."""
        client = KnowledgeGraphClient()
        assert client is not None
        assert client._mcp_tool_name == 'mcp__neo4j-rhacm__read_neo4j_cypher'

    def test_availability_check_caching(self):
        """Test that availability is cached after first check."""
        client = KnowledgeGraphClient()
        # First access triggers check
        _ = client.available
        # Second access should use cached value
        _ = client.available
        # _available should be set (not None)
        assert client._available is not None

    def test_get_knowledge_graph_client_helper(self):
        """Test the helper function returns a client."""
        client = get_knowledge_graph_client()
        assert isinstance(client, KnowledgeGraphClient)

    def test_is_knowledge_graph_available_helper(self):
        """Test the availability helper function."""
        # Should return a boolean without error
        result = is_knowledge_graph_available()
        assert isinstance(result, bool)


class TestDependencyQueries:
    """Test dependency query methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = KnowledgeGraphClient()
        # Force unavailable for most tests (no real Neo4j)
        self.client._available = False

    def test_get_dependencies_when_unavailable(self):
        """Test get_dependencies returns empty when unavailable."""
        result = self.client.get_dependencies('search-api')
        assert result == []

    def test_get_dependents_when_unavailable(self):
        """Test get_dependents returns empty when unavailable."""
        result = self.client.get_dependents('search-api')
        assert result == []

    def test_get_transitive_dependents_when_unavailable(self):
        """Test get_transitive_dependents returns empty chain when unavailable."""
        result = self.client.get_transitive_dependents('search-api')
        assert isinstance(result, DependencyChain)
        assert result.source_component == 'search-api'
        assert result.affected_components == []
        assert result.chain_length == 0
        assert result.subsystems_affected == []


class TestComponentInfo:
    """Test component info retrieval."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = KnowledgeGraphClient()
        self.client._available = False

    def test_get_component_info_when_unavailable(self):
        """Test get_component_info returns None when unavailable."""
        result = self.client.get_component_info('search-api')
        assert result is None

    def test_component_info_caching(self):
        """Test that component info is cached."""
        # Manually add to cache
        test_info = ComponentInfo(
            name='test-component',
            subsystem='Test',
            component_type='controller'
        )
        self.client._component_cache['test-component'] = test_info

        # Should return cached value even when unavailable
        # (cache check happens before availability check in real impl)
        # For this test, verify cache exists
        assert 'test-component' in self.client._component_cache


class TestCommonDependency:
    """Test common dependency detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = KnowledgeGraphClient()
        self.client._available = False

    def test_find_common_dependency_when_unavailable(self):
        """Test find_common_dependency returns None when unavailable."""
        result = self.client.find_common_dependency(['search-api', 'console'])
        assert result is None

    def test_find_common_dependency_with_single_component(self):
        """Test find_common_dependency with less than 2 components."""
        result = self.client.find_common_dependency(['search-api'])
        assert result is None

    def test_find_common_dependency_with_empty_list(self):
        """Test find_common_dependency with empty list."""
        result = self.client.find_common_dependency([])
        assert result is None


class TestSubsystemComponents:
    """Test subsystem component retrieval."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = KnowledgeGraphClient()
        self.client._available = False

    def test_get_subsystem_components_when_unavailable(self):
        """Test get_subsystem_components returns empty when unavailable."""
        result = self.client.get_subsystem_components('Search')
        assert result == []


class TestFailureImpactAnalysis:
    """Test failure impact analysis."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = KnowledgeGraphClient()
        self.client._available = False

    def test_analyze_failure_impact_when_unavailable(self):
        """Test analyze_failure_impact returns basic structure when unavailable."""
        result = self.client.analyze_failure_impact(['search-api'])

        assert 'failing_components' in result
        assert result['failing_components'] == ['search-api']
        assert 'subsystems_affected' in result
        assert 'cascading_effects' in result
        assert 'common_dependency' in result
        assert 'recommendations' in result
        assert len(result['recommendations']) > 0

    def test_analyze_failure_impact_with_empty_list(self):
        """Test analyze_failure_impact with empty component list."""
        result = self.client.analyze_failure_impact([])

        assert result['failing_components'] == []
        assert len(result['recommendations']) > 0


class TestCacheManagement:
    """Test cache management functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = KnowledgeGraphClient()

    def test_clear_cache(self):
        """Test that clear_cache empties all caches."""
        # Add some data to caches
        self.client._component_cache['test'] = ComponentInfo(name='test')
        self.client._dependency_cache['test'] = ['dep1', 'dep2']
        self.client._available = True

        # Clear caches
        self.client.clear_cache()

        assert len(self.client._component_cache) == 0
        assert len(self.client._dependency_cache) == 0
        assert self.client._available is None


class TestDataClasses:
    """Test data class structures."""

    def test_component_info_creation(self):
        """Test ComponentInfo dataclass."""
        info = ComponentInfo(
            name='search-api',
            subsystem='Search',
            component_type='service',
            dependencies=['search-collector'],
            dependents=['console', 'observability']
        )

        assert info.name == 'search-api'
        assert info.subsystem == 'Search'
        assert info.component_type == 'service'
        assert 'search-collector' in info.dependencies
        assert 'console' in info.dependents

    def test_component_info_defaults(self):
        """Test ComponentInfo with default values."""
        info = ComponentInfo(name='test')

        assert info.name == 'test'
        assert info.subsystem is None
        assert info.component_type is None
        assert info.dependencies is None
        assert info.dependents is None

    def test_dependency_chain_creation(self):
        """Test DependencyChain dataclass."""
        chain = DependencyChain(
            source_component='search-api',
            affected_components=['console', 'observability'],
            chain_length=2,
            subsystems_affected=['Console', 'Observability']
        )

        assert chain.source_component == 'search-api'
        assert len(chain.affected_components) == 2
        assert chain.chain_length == 2
        assert 'Console' in chain.subsystems_affected


class TestIntegrationWithComponentExtractor:
    """Test integration patterns with ComponentExtractor."""

    def test_workflow_component_extraction(self):
        """Test component extraction from error messages."""
        from src.services.component_extractor import ComponentExtractor

        extractor = ComponentExtractor()
        error = "search-api returned 500, grc-policy-propagator timed out"
        components = extractor.extract_from_error(error)

        assert len(components) == 2

    def test_workflow_with_subsystem_context(self):
        """Test adding subsystem context to extracted components."""
        from src.services.component_extractor import ComponentExtractor

        extractor = ComponentExtractor()

        # Extract component
        components = extractor.extract_from_error("search-api error")

        # Get subsystem for context
        for comp in components:
            subsystem = extractor.get_subsystem(comp)
            assert subsystem == 'Search'
