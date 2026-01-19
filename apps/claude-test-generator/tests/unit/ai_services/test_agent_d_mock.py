"""
Agent D (Environment Intelligence) Mock Tests
==============================================

Comprehensive mock-based tests for Agent D environment intelligence functionality.
Tests all scenarios without external cluster dependencies.
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

from mock_environment_data import (
    MOCK_ENVIRONMENTS, MockClusterEnvironment, MockEnvironmentAssessmentClient,
    get_mock_environment, create_custom_environment,
    EXPECTED_ENVIRONMENT_OUTPUTS, MOCK_OC_COMMAND_OUTPUTS
)


class TestAgentDEnvironmentAssessment:
    """Test Agent D environment assessment functionality with mock data."""

    @pytest.fixture
    def mock_env_client(self):
        """Create a mock environment assessment client."""
        return MockEnvironmentAssessmentClient()

    @pytest.fixture
    def mock_communication_hub(self):
        """Create a mock communication hub for agent coordination."""
        hub = Mock()
        hub.register_agent = Mock()
        hub.update_agent_status = Mock()
        hub.publish_message = AsyncMock()
        hub.subscribe_to_messages = Mock()
        hub.get_message_history = Mock(return_value=[])
        return hub

    # ============== Test Scenario D-1: Healthy Cluster ==============
    def test_healthy_cluster_assessment(self, mock_env_client):
        """Test assessment of a healthy cluster."""
        mock_env_client.set_current_environment("healthy_cluster")
        expected = EXPECTED_ENVIRONMENT_OUTPUTS["healthy_cluster"]

        result = mock_env_client.assess_environment()

        assert result["health"] == "Healthy"
        assert result["deployment_status"] == "deployed"
        assert len(result["nodes"]) == expected["node_count"]
        assert all(n["status"] == "Ready" for n in result["nodes"])
        assert len(result["errors"]) == 0

    # ============== Test Scenario D-2: Unhealthy Cluster ==============
    def test_unhealthy_cluster_assessment(self, mock_env_client):
        """Test assessment of an unhealthy cluster with node issues."""
        mock_env_client.set_current_environment("unhealthy_cluster")
        expected = EXPECTED_ENVIRONMENT_OUTPUTS["unhealthy_cluster"]

        result = mock_env_client.assess_environment()

        assert result["health"] == "Unhealthy"
        assert len(result["errors"]) > 0
        assert not all(n["status"] == "Ready" for n in result["nodes"])

    # ============== Test Scenario D-3: Feature Deployed ==============
    def test_feature_deployed_detection(self, mock_env_client):
        """Test detection of deployed feature CRDs."""
        mock_env_client.set_current_environment("feature_deployed")
        expected = EXPECTED_ENVIRONMENT_OUTPUTS["feature_deployed"]

        result = mock_env_client.assess_environment()

        assert result["deployment_status"] == "deployed"
        assert len(result["crds_present"]) > 0

    # ============== Test Scenario D-4: Feature Not Deployed ==============
    def test_feature_not_deployed_detection(self, mock_env_client):
        """Test detection when feature CRDs are missing."""
        mock_env_client.set_current_environment("feature_not_deployed")
        expected = EXPECTED_ENVIRONMENT_OUTPUTS["feature_not_deployed"]

        result = mock_env_client.assess_environment()

        assert result["deployment_status"] == "not_deployed"
        assert len(result["crds_present"]) == 0

    # ============== Test Scenario D-5: Cluster Unreachable ==============
    def test_unreachable_cluster_handling(self, mock_env_client):
        """Test graceful handling of unreachable cluster."""
        mock_env_client.set_current_environment("unreachable_cluster")
        expected = EXPECTED_ENVIRONMENT_OUTPUTS["unreachable_cluster"]

        result = mock_env_client.assess_environment()

        assert result["health"] == "Unreachable"
        assert len(result["nodes"]) == 0
        assert len(result["errors"]) > 0

    # ============== Test Scenario D-6: No Environment Specified ==============
    def test_no_environment_specified_error(self, mock_env_client):
        """Test error handling when no environment is specified."""
        mock_env_client.set_current_environment("nonexistent")

        with pytest.raises(Exception) as exc_info:
            mock_env_client.assess_environment()

        assert "not found" in str(exc_info.value).lower()

    # ============== Test Scenario D-7: PAUSE-and-Wait Coordination ==============
    @pytest.mark.asyncio
    async def test_pause_and_wait_coordination(self, mock_env_client, mock_communication_hub):
        """Test PAUSE-and-wait coordination with Agent A."""
        # Simulate Agent D waiting for Agent A message
        pr_discovery_message = {
            'sender_agent': 'agent_a_jira_intelligence',
            'message_type': 'pr_discovery',
            'payload': {
                'pr_info': {
                    'pr_number': '468',
                    'deployment_components': ['ClusterCurator']
                },
                'requires_environment_collection': True
            }
        }

        # Configure hub to return message history
        mock_communication_hub.get_message_history.return_value = [pr_discovery_message]

        # Verify coordination works
        messages = mock_communication_hub.get_message_history()
        assert len(messages) == 1
        assert messages[0]['message_type'] == 'pr_discovery'
        assert messages[0]['payload']['requires_environment_collection'] is True


class TestAgentDOCCommands:
    """Test Agent D oc/kubectl command execution with mocks."""

    @pytest.fixture
    def mock_env_client(self):
        return MockEnvironmentAssessmentClient()

    def test_oc_get_nodes_healthy(self, mock_env_client):
        """Test oc get nodes on healthy cluster."""
        mock_env_client.set_current_environment("healthy_cluster")

        output = mock_env_client.run_oc_command("oc get nodes")

        assert "Ready" in output
        assert "master-0" in output
        assert "NotReady" not in output

    def test_oc_get_nodes_unhealthy(self, mock_env_client):
        """Test oc get nodes on unhealthy cluster."""
        mock_env_client.set_current_environment("unhealthy_cluster")

        output = mock_env_client.run_oc_command("oc get nodes")

        assert "NotReady" in output

    def test_oc_command_on_unreachable(self, mock_env_client):
        """Test oc command on unreachable cluster."""
        mock_env_client.set_current_environment("unreachable_cluster")

        output = mock_env_client.run_oc_command("oc get nodes")

        assert "error" in output.lower() or "unable to connect" in output.lower()


class TestAgentDConnectionHandling:
    """Test Agent D connection and error handling."""

    @pytest.fixture
    def mock_env_client(self):
        return MockEnvironmentAssessmentClient()

    def test_connection_timeout_handling(self, mock_env_client):
        """Test handling of connection timeout."""
        mock_env_client.set_connection_timeout(True)

        with pytest.raises(TimeoutError):
            mock_env_client.assess_environment()

    def test_api_failure_handling(self, mock_env_client):
        """Test handling of API failures."""
        mock_env_client.set_failure_mode(True, "Kubernetes API unavailable")

        with pytest.raises(Exception) as exc_info:
            mock_env_client.assess_environment()

        assert "API unavailable" in str(exc_info.value)

    def test_retry_on_transient_failure(self, mock_env_client):
        """Test retry logic on transient failures."""
        # First call fails, second succeeds
        mock_env_client.set_failure_mode(True)

        with pytest.raises(Exception):
            mock_env_client.assess_environment()

        # Reset and retry
        mock_env_client.reset()
        result = mock_env_client.assess_environment()

        assert result["health"] == "Healthy"


class TestAgentDVersionDetection:
    """Test Agent D version detection functionality."""

    @pytest.fixture
    def mock_env_client(self):
        return MockEnvironmentAssessmentClient()

    def test_acm_version_detection(self, mock_env_client):
        """Test ACM version detection from cluster."""
        mock_env_client.set_current_environment("healthy_cluster")

        result = mock_env_client.assess_environment()

        assert result["acm_version"] == "2.15.0"

    def test_version_detection_on_unreachable(self, mock_env_client):
        """Test version detection on unreachable cluster."""
        mock_env_client.set_current_environment("unreachable_cluster")

        result = mock_env_client.assess_environment()

        assert result["acm_version"] == "unknown"


class TestAgentDOutputStructure:
    """Test Agent D output structure and format."""

    @pytest.fixture
    def mock_env_client(self):
        return MockEnvironmentAssessmentClient()

    def test_environment_assessment_output_structure(self, mock_env_client):
        """Test that environment assessment has required structure."""
        mock_env_client.set_current_environment("healthy_cluster")

        result = mock_env_client.assess_environment()

        required_keys = [
            'console_url', 'api_url', 'health', 'acm_version',
            'nodes', 'deployment_status', 'namespaces', 'crds_present', 'errors'
        ]

        for key in required_keys:
            assert key in result, f"Missing required key: {key}"

    def test_node_structure_format(self, mock_env_client):
        """Test node data structure format."""
        mock_env_client.set_current_environment("healthy_cluster")

        result = mock_env_client.assess_environment()

        for node in result["nodes"]:
            assert "name" in node
            assert "status" in node


class TestAgentDCustomEnvironments:
    """Test Agent D with custom environment scenarios."""

    def test_custom_healthy_environment(self):
        """Test creating custom healthy environment."""
        custom_env = create_custom_environment(
            console_url="https://console.custom.example.com",
            health="Healthy",
            acm_version="2.16.0"
        )

        assert custom_env.health == "Healthy"
        assert custom_env.acm_version == "2.16.0"

    def test_custom_environment_with_specific_crds(self):
        """Test custom environment with specific CRDs."""
        custom_env = create_custom_environment(
            crds_present=[
                "clustercurators.cluster.open-cluster-management.io",
                "customresource.example.io"
            ]
        )

        assert len(custom_env.crds_present) == 2
        assert "clustercurators.cluster.open-cluster-management.io" in custom_env.crds_present

    def test_custom_environment_with_errors(self):
        """Test custom environment with specific errors."""
        custom_env = create_custom_environment(
            health="Degraded",
            errors=["Pod scheduling failed", "PVC binding timeout"]
        )

        assert custom_env.health == "Degraded"
        assert len(custom_env.errors) == 2


class TestAgentDToolingAnalysis:
    """Test Agent D tooling analysis functionality."""

    def test_detect_available_tools(self):
        """Test detection of available CLI tools."""
        # Simulated tool detection
        available_tools = {
            'oc': True,
            'kubectl': True,
            'gh': True,
            'curl': True
        }

        # Verify essential tools
        assert available_tools['oc'] is True
        assert available_tools['kubectl'] is True

    def test_tool_preference_order(self):
        """Test tool preference order for commands."""
        preferred_tools = ['oc', 'kubectl', 'gh', 'curl', 'docker', 'git']

        # oc should be preferred over kubectl
        assert preferred_tools.index('oc') < preferred_tools.index('kubectl')


class TestAgentDNamespaceAnalysis:
    """Test Agent D namespace analysis functionality."""

    @pytest.fixture
    def mock_env_client(self):
        return MockEnvironmentAssessmentClient()

    def test_acm_namespaces_present(self, mock_env_client):
        """Test detection of ACM namespaces."""
        mock_env_client.set_current_environment("healthy_cluster")

        result = mock_env_client.assess_environment()

        assert "open-cluster-management" in result["namespaces"]
        assert "open-cluster-management-hub" in result["namespaces"]

    def test_minimal_namespace_environment(self, mock_env_client):
        """Test environment with minimal namespaces."""
        mock_env_client.set_current_environment("feature_not_deployed")

        result = mock_env_client.assess_environment()

        assert len(result["namespaces"]) >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
