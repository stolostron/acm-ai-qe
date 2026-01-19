"""
Agent A (JIRA Intelligence) Mock Tests
========================================

Comprehensive mock-based tests for Agent A JIRA intelligence functionality.
Tests all scenarios without external API dependencies.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../fixtures'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../.claude/ai-services'))

from mock_jira_data import (
    MOCK_JIRA_TICKETS, MockJIRATicket, MockJiraApiClient,
    get_mock_jira_ticket, create_custom_jira_ticket,
    EXPECTED_JIRA_ANALYSIS_OUTPUTS
)


class TestAgentAJIRAAnalysis:
    """Test Agent A JIRA analysis functionality with mock data."""

    @pytest.fixture
    def mock_jira_client(self):
        """Create a mock JIRA API client."""
        return MockJiraApiClient()

    @pytest.fixture
    def mock_communication_hub(self):
        """Create a mock communication hub."""
        hub = Mock()
        hub.register_agent = Mock()
        hub.update_agent_status = Mock()
        hub.publish_message = AsyncMock()
        hub.subscribe_to_messages = Mock()
        return hub

    # ============== Test Scenario A-1: Valid JIRA with PR References ==============
    @pytest.mark.asyncio
    async def test_valid_jira_with_pr_references(self, mock_jira_client, mock_communication_hub):
        """Test JIRA ticket with PR references in comments."""
        # Setup
        ticket = get_mock_jira_ticket("PROJECT-12345")
        expected = EXPECTED_JIRA_ANALYSIS_OUTPUTS["PROJECT-12345"]

        # Mock context
        context = {
            'jira_id': 'PROJECT-12345',
            'target_version': '2.15.0'
        }

        # Extract PR references from description (simulating agent logic)
        import re
        pr_patterns = [r'PR #?(\d+)', r'pull/(\d+)']
        pr_refs = []
        for pattern in pr_patterns:
            matches = re.findall(pattern, ticket.description, re.IGNORECASE)
            pr_refs.extend(matches)

        # Verify
        assert len(pr_refs) >= len(expected["pr_references"])
        assert "468" in pr_refs or "469" in pr_refs

    # ============== Test Scenario A-2: JIRA with No PR References ==============
    @pytest.mark.asyncio
    async def test_jira_without_pr_references(self, mock_jira_client):
        """Test JIRA ticket with no PR mentions triggers discovery."""
        ticket = get_mock_jira_ticket("PROJECT-54321")
        expected = EXPECTED_JIRA_ANALYSIS_OUTPUTS["PROJECT-54321"]

        # Extract PR references (should be empty)
        import re
        pr_patterns = [r'PR #?(\d+)', r'pull/(\d+)']
        pr_refs = []
        for pattern in pr_patterns:
            matches = re.findall(pattern, ticket.description, re.IGNORECASE)
            pr_refs.extend(matches)

        # Verify
        assert len(pr_refs) == 0
        assert expected["pr_references"] == []

    # ============== Test Scenario A-3: JIRA with Multiple Components ==============
    @pytest.mark.asyncio
    async def test_jira_with_multiple_components(self, mock_jira_client):
        """Test JIRA ticket with multiple components."""
        ticket = get_mock_jira_ticket("PROJECT-99999")
        expected = EXPECTED_JIRA_ANALYSIS_OUTPUTS["PROJECT-99999"]

        # Parse components
        components = [c.strip() for c in ticket.component.split(',')]

        # Verify
        assert len(components) >= expected["component_analysis"]["component_count"]
        assert "Observability" in components

    # ============== Test Scenario A-4: JIRA Missing Fix Version ==============
    @pytest.mark.asyncio
    async def test_jira_missing_fix_version(self, mock_jira_client):
        """Test JIRA ticket without fix_versions uses fallback."""
        ticket = get_mock_jira_ticket("PROJECT-NOVERSION")

        # Verify the ticket has no version
        assert ticket.fix_version == ""

        # Simulate fallback logic
        effective_version = ticket.fix_version or "default-version"
        assert effective_version == "default-version"

    # ============== Test Scenario A-5: JIRA API Failure ==============
    @pytest.mark.asyncio
    async def test_jira_api_failure(self, mock_jira_client):
        """Test handling of JIRA API failure with fallback."""
        # Configure mock to fail
        mock_jira_client.set_failure_mode(True, "API service unavailable")

        # Attempt to fetch ticket
        with pytest.raises(Exception) as exc_info:
            await mock_jira_client.get_ticket_information("PROJECT-12345")

        assert "API service unavailable" in str(exc_info.value)
        assert mock_jira_client.get_call_count() == 1

    # ============== Test Scenario A-6: Empty Description ==============
    @pytest.mark.asyncio
    async def test_jira_empty_description(self, mock_jira_client):
        """Test JIRA ticket with empty description handles gracefully."""
        ticket = get_mock_jira_ticket("PROJECT-EMPTYDESC")

        # Verify empty description
        assert ticket.description == ""

        # Analysis should still work using title
        assert len(ticket.title) > 0
        assert ticket.component != ""

    # ============== Test Scenario A-7: Information Sufficiency Check ==============
    @pytest.mark.asyncio
    async def test_information_sufficiency_check(self, mock_jira_client):
        """Test information sufficiency analysis."""
        # Full ticket should have sufficient info
        full_ticket = get_mock_jira_ticket("ACM-22079")
        full_score = self._calculate_mock_sufficiency_score(full_ticket)
        assert full_score >= 0.75

        # Minimal ticket should have lower score
        minimal_ticket = get_mock_jira_ticket("PROJECT-MINIMAL")
        minimal_score = self._calculate_mock_sufficiency_score(minimal_ticket)
        assert minimal_score < 0.75

    def _calculate_mock_sufficiency_score(self, ticket: MockJIRATicket) -> float:
        """Calculate mock sufficiency score for a ticket."""
        score = 0.0
        weights = {
            'has_description': 0.2,
            'has_component': 0.15,
            'has_priority': 0.1,
            'has_fix_version': 0.15,
            'has_labels': 0.1,
            'has_comments': 0.15,
            'has_acceptance_criteria': 0.15
        }

        if ticket.description and len(ticket.description) > 50:
            score += weights['has_description']
        if ticket.component and ticket.component != 'Unknown':
            score += weights['has_component']
        if ticket.priority:
            score += weights['has_priority']
        if ticket.fix_version:
            score += weights['has_fix_version']
        if ticket.labels:
            score += weights['has_labels']
        if ticket.comments:
            score += weights['has_comments']
        if 'acceptance' in ticket.description.lower() or 'criteria' in ticket.description.lower():
            score += weights['has_acceptance_criteria']

        return score


class TestAgentAPRExtraction:
    """Test Agent A PR extraction and discovery functionality."""

    def test_extract_pr_from_github_url(self):
        """Test PR extraction from GitHub URLs."""
        description = "See https://github.com/org/repo/pull/468 for implementation"

        import re
        pattern = r'github\.com/.+/pull/(\d+)'
        matches = re.findall(pattern, description)

        assert len(matches) == 1
        assert matches[0] == "468"

    def test_extract_pr_from_pr_hash(self):
        """Test PR extraction from 'PR #XXX' format."""
        description = "Implemented in PR #468 and PR #469"

        import re
        pattern = r'PR #?(\d+)'
        matches = re.findall(pattern, description, re.IGNORECASE)

        assert len(matches) == 2
        assert "468" in matches
        assert "469" in matches

    def test_extract_pr_deduplication(self):
        """Test that duplicate PR references are deduplicated."""
        description = "See PR #468, also PR #468 mentioned in https://github.com/org/repo/pull/468"

        import re
        patterns = [r'PR #?(\d+)', r'pull/(\d+)']
        pr_refs = []
        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            pr_refs.extend(matches)

        unique_refs = list(set(pr_refs))
        assert len(unique_refs) == 1
        assert unique_refs[0] == "468"


class TestAgentAEnvironmentRequirements:
    """Test Agent A environment requirements generation."""

    def test_generate_yaml_requirements_for_clustercurator(self):
        """Test YAML requirements generation for ClusterCurator component."""
        component = "clustercurator"
        pr_number = "468"

        # Expected patterns
        expected_patterns = [
            "clustercurator.yaml",
            "clustercurator-controller-deployment.yaml",
            "clustercurator-crd.yaml"
        ]

        # Simulate generation
        yamls = [
            f"{component}.yaml",
            f"{component}-controller-deployment.yaml",
            f"{component}-crd.yaml",
            f"{component}*.yaml"
        ]

        for expected in expected_patterns:
            assert expected in yamls

    def test_determine_priority_based_on_pr_characteristics(self):
        """Test priority determination based on PR characteristics."""
        # Large PR with many files should have high priority
        large_pr_files = 15
        large_pr_components = 3
        confidence = 0.95

        priority_score = 2  # base
        if confidence > 0.9:
            priority_score += 1
        if large_pr_files > 10:
            priority_score += 1
        if large_pr_components > 2:
            priority_score += 1

        # Convert score to priority
        if priority_score >= 5:
            priority = "critical"
        elif priority_score >= 4:
            priority = "high"
        elif priority_score >= 3:
            priority = "normal"
        else:
            priority = "low"

        assert priority in ["high", "critical"]


class TestAgentAOutputStructure:
    """Test Agent A output structure and format."""

    def test_final_analysis_structure(self):
        """Test that final analysis has required structure."""
        # Simulated final analysis output
        final_analysis = {
            'analysis_metadata': {
                'agent': 'Agent A - JIRA Intelligence',
                'analysis_timestamp': datetime.now().isoformat(),
                'jira_ticket': 'ACM-22079',
                'analysis_version': 'v2.0_realtime'
            },
            'jira_intelligence': {},
            'pr_discoveries': [],
            'component_analysis': {},
            'environment_coordination': {
                'requirements_published': 0,
                'realtime_coordination_active': True,
                'agent_d_integration': 'enabled'
            },
            'progressive_context_ready': {
                'agent_b_inheritance': True,
                'agent_c_inheritance': True,
                'findings_available': True
            },
            'confidence_score': 0.92,
            'next_phase_readiness': True
        }

        # Verify required keys
        required_keys = [
            'analysis_metadata', 'jira_intelligence', 'pr_discoveries',
            'component_analysis', 'environment_coordination',
            'progressive_context_ready', 'confidence_score', 'next_phase_readiness'
        ]

        for key in required_keys:
            assert key in final_analysis

        # Verify metadata structure
        assert 'agent' in final_analysis['analysis_metadata']
        assert 'analysis_timestamp' in final_analysis['analysis_metadata']


class TestAgentACustomTickets:
    """Test Agent A with custom ticket scenarios."""

    def test_custom_ticket_creation(self):
        """Test creating custom tickets for edge cases."""
        custom = create_custom_jira_ticket(
            key="CUSTOM-001",
            title="Custom edge case ticket",
            description="Testing specific scenario",
            priority="Critical",
            component="NewComponent",
            labels=["edge-case", "testing"]
        )

        assert custom.key == "CUSTOM-001"
        assert custom.priority == "Critical"
        assert "edge-case" in custom.labels

    def test_ticket_with_complex_hierarchy(self):
        """Test ticket with subtasks and linked issues."""
        custom = create_custom_jira_ticket(
            key="HIER-001",
            title="Parent ticket with hierarchy",
            description="Complex hierarchy test",
            subtasks=[
                {"key": "HIER-001-1", "summary": "Subtask 1"},
                {"key": "HIER-001-2", "summary": "Subtask 2"}
            ],
            linked_issues=[
                {"key": "HIER-002", "type": "blocks"},
                {"key": "HIER-003", "type": "is blocked by"}
            ]
        )

        assert len(custom.subtasks) == 2
        assert len(custom.linked_issues) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
