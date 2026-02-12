"""
Unit tests for ComponentExtractor service.

Tests component name extraction from error messages, stack traces,
and console logs for Knowledge Graph integration.
"""

import pytest
from src.services.component_extractor import ComponentExtractor, ExtractedComponent


class TestComponentExtractorBasics:
    """Test basic component extraction functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ComponentExtractor()

    def test_extract_single_component_from_error(self):
        """Test extracting a single component from error message."""
        error = "Error: search-api returned 500: index not available"
        components = self.extractor.extract_from_error(error)
        assert components == ['search-api']

    def test_extract_multiple_components(self):
        """Test extracting multiple components from error message."""
        error = "grc-policy-propagator failed to connect to search-api"
        components = self.extractor.extract_from_error(error)
        assert 'grc-policy-propagator' in components
        assert 'search-api' in components
        assert len(components) == 2

    def test_case_insensitive_extraction(self):
        """Test that extraction is case-insensitive."""
        error1 = "SEARCH-API returned error"
        error2 = "Search-Api returned error"
        error3 = "search-api returned error"

        components1 = self.extractor.extract_from_error(error1)
        components2 = self.extractor.extract_from_error(error2)
        components3 = self.extractor.extract_from_error(error3)

        assert components1 == ['search-api']
        assert components2 == ['search-api']
        assert components3 == ['search-api']

    def test_no_components_found(self):
        """Test when no components are in the error message."""
        error = "Element #create-btn not found after 30000ms"
        components = self.extractor.extract_from_error(error)
        assert components == []

    def test_empty_input(self):
        """Test handling of empty input."""
        assert self.extractor.extract_from_error("") == []
        assert self.extractor.extract_from_error(None) == []

    def test_deduplication(self):
        """Test that duplicate components are removed."""
        error = "search-api failed, retrying search-api, search-api still down"
        components = self.extractor.extract_from_error(error)
        assert components == ['search-api']
        assert len(components) == 1


class TestComponentCategories:
    """Test extraction of components from different categories."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ComponentExtractor()

    def test_governance_components(self):
        """Test extraction of Governance subsystem components."""
        error = "grc-policy-propagator timeout waiting for config-policy-controller"
        components = self.extractor.extract_from_error(error)
        assert 'grc-policy-propagator' in components
        assert 'config-policy-controller' in components

    def test_search_components(self):
        """Test extraction of Search subsystem components."""
        error = "search-collector failed to push to search-indexer"
        components = self.extractor.extract_from_error(error)
        assert 'search-collector' in components
        assert 'search-indexer' in components

    def test_cluster_management_components(self):
        """Test extraction of Cluster Management components."""
        error = "cluster-curator failed: managedcluster-import-controller not ready"
        components = self.extractor.extract_from_error(error)
        assert 'cluster-curator' in components
        assert 'managedcluster-import-controller' in components

    def test_provisioning_components(self):
        """Test extraction of Provisioning components."""
        error = "hive provisioning timeout, hypershift unreachable, assisted-service failed"
        components = self.extractor.extract_from_error(error)
        assert 'hive' in components
        assert 'hypershift' in components
        assert 'assisted-service' in components

    def test_observability_components(self):
        """Test extraction of Observability components."""
        error = "thanos-query failed to reach thanos-receive"
        components = self.extractor.extract_from_error(error)
        assert 'thanos-query' in components
        assert 'thanos-receive' in components

    def test_virtualization_components(self):
        """Test extraction of Virtualization components."""
        error = "virt-api returned 503, kubevirt-operator degraded"
        components = self.extractor.extract_from_error(error)
        assert 'virt-api' in components
        assert 'kubevirt-operator' in components


class TestSubsystemMapping:
    """Test subsystem mapping functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ComponentExtractor()

    def test_get_subsystem_for_search_component(self):
        """Test getting subsystem for Search component."""
        assert self.extractor.get_subsystem('search-api') == 'Search'
        assert self.extractor.get_subsystem('search-collector') == 'Search'

    def test_get_subsystem_for_governance_component(self):
        """Test getting subsystem for Governance component."""
        assert self.extractor.get_subsystem('grc-policy-propagator') == 'Governance'

    def test_get_subsystem_for_unknown_component(self):
        """Test getting subsystem for unknown component."""
        assert self.extractor.get_subsystem('unknown-component') is None

    def test_get_subsystem_case_insensitive(self):
        """Test that subsystem lookup is case-insensitive."""
        assert self.extractor.get_subsystem('SEARCH-API') == 'Search'
        assert self.extractor.get_subsystem('Search-Api') == 'Search'


class TestExtractWithContext:
    """Test extraction with context information."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ComponentExtractor()

    def test_extract_with_context_returns_extracted_component(self):
        """Test that extract_with_context returns ExtractedComponent objects."""
        error = "Error from search-api: connection refused"
        results = self.extractor.extract_with_context(error, 'error_message')

        assert len(results) == 1
        assert isinstance(results[0], ExtractedComponent)
        assert results[0].name == 'search-api'
        assert results[0].source == 'error_message'
        assert 'search-api' in results[0].context

    def test_context_truncation(self):
        """Test that context is properly truncated."""
        # Create a long error message
        prefix = "x" * 100
        suffix = "y" * 100
        error = f"{prefix} search-api error {suffix}"

        results = self.extractor.extract_with_context(error, 'test', context_chars=20)

        assert len(results) == 1
        # Context should include some chars before and after
        assert 'search-api' in results[0].context
        # Context should be truncated
        assert len(results[0].context) < len(error)


class TestStackTraceExtraction:
    """Test extraction from stack traces."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ComponentExtractor()

    def test_extract_from_stack_trace(self):
        """Test extracting components from stack trace."""
        stack_trace = """
        Error: search-api connection failed
            at SearchService.query (search.js:45)
            at ApiHandler.handle (api.js:123)
        Caused by: search-indexer not responding
        """
        components = self.extractor.extract_from_stack_trace(stack_trace)
        assert 'search-api' in components
        assert 'search-indexer' in components


class TestConsoleLogExtraction:
    """Test extraction from console logs."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ComponentExtractor()

    def test_extract_from_console_log_error_lines_only(self):
        """Test extracting from error lines only."""
        console_log = """
        INFO: Starting test
        DEBUG: search-api initialized
        ERROR: grc-policy-propagator failed with 500
        INFO: Test complete
        """
        components = self.extractor.extract_from_console_log(
            console_log, error_lines_only=True
        )
        assert 'grc-policy-propagator' in components
        # search-api is on DEBUG line, should not be included
        assert 'search-api' not in components

    def test_extract_from_console_log_all_lines(self):
        """Test extracting from all lines."""
        console_log = """
        INFO: Starting test
        DEBUG: search-api initialized
        ERROR: grc-policy-propagator failed
        """
        components = self.extractor.extract_from_console_log(
            console_log, error_lines_only=False
        )
        assert 'grc-policy-propagator' in components
        assert 'search-api' in components


class TestCombinedExtraction:
    """Test extraction from multiple sources."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ComponentExtractor()

    def test_extract_all_from_test_failure(self):
        """Test extracting from all failure data sources."""
        error_message = "search-api returned 500"
        stack_trace = "Error at grc-policy-propagator"
        console_snippet = "Failed: hive timeout"

        results = self.extractor.extract_all_from_test_failure(
            error_message=error_message,
            stack_trace=stack_trace,
            console_snippet=console_snippet
        )

        names = [r.name for r in results]
        assert 'search-api' in names
        assert 'grc-policy-propagator' in names
        assert 'hive' in names

        # Check sources are tracked
        sources = {r.name: r.source for r in results}
        assert sources['search-api'] == 'error_message'
        assert sources['grc-policy-propagator'] == 'stack_trace'
        assert sources['hive'] == 'console_log'

    def test_deduplication_across_sources(self):
        """Test that duplicates across sources are removed."""
        error_message = "search-api error"
        stack_trace = "also search-api error"

        results = self.extractor.extract_all_from_test_failure(
            error_message=error_message,
            stack_trace=stack_trace
        )

        # Should only have one entry for search-api (from first source found)
        names = [r.name for r in results]
        assert names.count('search-api') == 1
        # Should be from error_message (processed first)
        assert results[0].source == 'error_message'


class TestComponentLists:
    """Test component list retrieval."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ComponentExtractor()

    def test_get_component_list(self):
        """Test getting full component list."""
        components = self.extractor.get_component_list()
        assert len(components) > 50  # Should have many components
        assert 'search-api' in components
        assert 'grc-policy-propagator' in components
        assert 'hive' in components

    def test_get_components_by_subsystem(self):
        """Test getting components by subsystem."""
        search_components = self.extractor.get_components_by_subsystem('Search')
        assert 'search-api' in search_components
        assert 'search-collector' in search_components

        governance_components = self.extractor.get_components_by_subsystem('Governance')
        assert 'grc-policy-propagator' in governance_components

    def test_get_components_unknown_subsystem(self):
        """Test getting components for unknown subsystem."""
        components = self.extractor.get_components_by_subsystem('Unknown')
        assert components == []


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = ComponentExtractor()

    def test_component_as_substring(self):
        """Test that partial matches don't trigger false positives."""
        # 'hive' should match, but 'archive' should not
        error = "Failed to connect to hive controller"
        components = self.extractor.extract_from_error(error)
        assert 'hive' in components

        error2 = "Failed to read archive file"
        components2 = self.extractor.extract_from_error(error2)
        assert 'hive' not in components2

    def test_special_characters_in_error(self):
        """Test handling of special characters in error messages."""
        error = "Error: search-api (v2.1) returned [500] - {timeout}"
        components = self.extractor.extract_from_error(error)
        assert 'search-api' in components

    def test_multiline_error_message(self):
        """Test extraction from multiline error messages."""
        error = """
        Multiple errors detected:
        1. search-api - connection refused
        2. grc-policy-propagator - timeout
        3. hive - not ready
        """
        components = self.extractor.extract_from_error(error)
        assert len(components) == 3
        assert 'search-api' in components
        assert 'grc-policy-propagator' in components
        assert 'hive' in components
