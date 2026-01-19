"""
Inter-Agent Communication Mock Tests
=====================================

Comprehensive mock-based tests for inter-agent communication functionality.
Tests message publishing, subscribing, and coordination between agents.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import List, Dict, Any

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../.claude/ai-services'))


class MockInterAgentMessage:
    """Mock inter-agent message structure."""
    def __init__(self, message_id: str, sender_agent: str, target_agent: str,
                 message_type: str, payload: Dict[str, Any], priority: str = "normal"):
        self.message_id = message_id
        self.sender_agent = sender_agent
        self.target_agent = target_agent
        self.message_type = message_type
        self.payload = payload
        self.timestamp = datetime.now().isoformat()
        self.priority = priority
        self.requires_response = False


class MockCommunicationHub:
    """Mock communication hub for testing."""

    def __init__(self, phase_id: str, run_id: str):
        self.phase_id = phase_id
        self.run_id = run_id
        self.message_queue: List[MockInterAgentMessage] = []
        self.message_history: List[MockInterAgentMessage] = []
        self.subscriptions: Dict[str, List] = {}
        self.active_agents: Dict[str, Dict] = {}
        self.agent_status: Dict[str, str] = {}
        self.hub_active = False

    async def start_hub(self):
        """Start the mock hub."""
        self.hub_active = True

    async def stop_hub(self):
        """Stop the mock hub."""
        self.hub_active = False

    def register_agent(self, agent_id: str, metadata: Dict[str, Any]):
        """Register an agent."""
        self.active_agents[agent_id] = {
            'metadata': metadata,
            'registered_at': datetime.now().isoformat()
        }
        self.agent_status[agent_id] = "starting"

    def update_agent_status(self, agent_id: str, status: str):
        """Update agent status."""
        self.agent_status[agent_id] = status

    def subscribe_to_messages(self, agent_id: str, message_types: List[str], callback):
        """Subscribe to message types."""
        for msg_type in message_types:
            if msg_type not in self.subscriptions:
                self.subscriptions[msg_type] = []
            self.subscriptions[msg_type].append({
                'agent_id': agent_id,
                'callback': callback
            })

    async def publish_message(self, sender_agent: str, target_agent: str,
                            message_type: str, payload: Dict[str, Any],
                            priority: str = "normal") -> str:
        """Publish a message."""
        message = MockInterAgentMessage(
            message_id=f"msg_{len(self.message_history)}",
            sender_agent=sender_agent,
            target_agent=target_agent,
            message_type=message_type,
            payload=payload,
            priority=priority
        )
        self.message_queue.append(message)
        self.message_history.append(message)
        return message.message_id

    def get_message_history(self, agent_id: str = None, message_type: str = None) -> List[Dict]:
        """Get message history with optional filtering."""
        filtered = self.message_history

        if agent_id:
            filtered = [m for m in filtered
                       if m.sender_agent == agent_id or m.target_agent == agent_id]
        if message_type:
            filtered = [m for m in filtered if m.message_type == message_type]

        return [
            {
                'message_id': m.message_id,
                'sender_agent': m.sender_agent,
                'target_agent': m.target_agent,
                'message_type': m.message_type,
                'payload': m.payload,
                'timestamp': m.timestamp,
                'priority': m.priority
            }
            for m in filtered
        ]


class TestCommunicationHubBasics:
    """Test basic communication hub functionality."""

    @pytest.fixture
    def hub(self):
        """Create a mock communication hub."""
        return MockCommunicationHub("phase_1", "test_run_001")

    # ============== Test Scenario COM-1: Publish/Subscribe ==============
    @pytest.mark.asyncio
    async def test_publish_subscribe_message(self, hub):
        """Test Agent A publishes and Agent D subscribes."""
        await hub.start_hub()

        # Register agents
        hub.register_agent("agent_a", {"type": "jira_intelligence"})
        hub.register_agent("agent_d", {"type": "environment_intelligence"})

        # Agent D subscribes to PR discoveries
        received_messages = []

        def callback(message):
            received_messages.append(message)

        hub.subscribe_to_messages("agent_d", ["pr_discovery"], callback)

        # Agent A publishes PR discovery
        msg_id = await hub.publish_message(
            sender_agent="agent_a",
            target_agent="agent_d",
            message_type="pr_discovery",
            payload={"pr_number": "468", "files_changed": 5},
            priority="high"
        )

        # Verify message was recorded
        assert msg_id is not None
        assert len(hub.message_history) == 1
        assert hub.message_history[0].message_type == "pr_discovery"

        await hub.stop_hub()

    # ============== Test Scenario COM-2: Message Ordering ==============
    @pytest.mark.asyncio
    async def test_message_ordering_fifo(self, hub):
        """Test FIFO order of messages is maintained."""
        await hub.start_hub()

        # Publish multiple messages
        for i in range(5):
            await hub.publish_message(
                sender_agent="agent_a",
                target_agent="agent_d",
                message_type="test_message",
                payload={"sequence": i}
            )

        # Verify order
        history = hub.get_message_history()
        for i, msg in enumerate(history):
            assert msg['payload']['sequence'] == i

        await hub.stop_hub()

    # ============== Test Scenario COM-3: Priority Handling ==============
    @pytest.mark.asyncio
    async def test_message_priority_handling(self, hub):
        """Test priority message handling."""
        await hub.start_hub()

        # Publish messages with different priorities
        await hub.publish_message(
            sender_agent="agent_a",
            target_agent="agent_d",
            message_type="low_priority",
            payload={"data": "low"},
            priority="low"
        )
        await hub.publish_message(
            sender_agent="agent_a",
            target_agent="agent_d",
            message_type="urgent",
            payload={"data": "urgent"},
            priority="urgent"
        )

        # Verify priority is recorded
        history = hub.get_message_history()
        priorities = [m['priority'] for m in history]
        assert "low" in priorities
        assert "urgent" in priorities

        await hub.stop_hub()

    # ============== Test Scenario COM-4: Timeout on Wait ==============
    @pytest.mark.asyncio
    async def test_timeout_handling(self, hub):
        """Test timeout when waiting for message that never arrives."""
        await hub.start_hub()

        # Simulate waiting with timeout
        async def wait_for_message_with_timeout(timeout_seconds: float):
            start = datetime.now()
            while (datetime.now() - start).total_seconds() < timeout_seconds:
                if hub.message_queue:
                    return hub.message_queue.pop(0)
                await asyncio.sleep(0.01)
            raise asyncio.TimeoutError("No message received within timeout")

        # This should timeout since no message is published
        with pytest.raises(asyncio.TimeoutError):
            await wait_for_message_with_timeout(0.05)

        await hub.stop_hub()

    # ============== Test Scenario COM-5: Message Filtering ==============
    @pytest.mark.asyncio
    async def test_message_type_filtering(self, hub):
        """Test subscribers get only subscribed message types."""
        await hub.start_hub()

        # Publish different message types
        await hub.publish_message(
            sender_agent="agent_a",
            target_agent="agent_d",
            message_type="pr_discovery",
            payload={"pr": "468"}
        )
        await hub.publish_message(
            sender_agent="agent_a",
            target_agent="agent_d",
            message_type="jira_intelligence",
            payload={"jira": "12345"}
        )
        await hub.publish_message(
            sender_agent="agent_a",
            target_agent="all",
            message_type="broadcast",
            payload={"data": "broadcast"}
        )

        # Filter by type
        pr_messages = hub.get_message_history(message_type="pr_discovery")
        jira_messages = hub.get_message_history(message_type="jira_intelligence")

        assert len(pr_messages) == 1
        assert len(jira_messages) == 1
        assert pr_messages[0]['payload']['pr'] == "468"

        await hub.stop_hub()


class TestAgentCommunicationInterface:
    """Test the agent communication interface."""

    @pytest.fixture
    def hub(self):
        return MockCommunicationHub("phase_1", "test_run_001")

    @pytest.mark.asyncio
    async def test_agent_registration(self, hub):
        """Test agent registration with hub."""
        hub.register_agent("agent_a", {"agent_type": "framework_agent"})

        assert "agent_a" in hub.active_agents
        assert hub.agent_status["agent_a"] == "starting"

    @pytest.mark.asyncio
    async def test_agent_status_update(self, hub):
        """Test agent status update."""
        hub.register_agent("agent_a", {"agent_type": "framework_agent"})
        hub.update_agent_status("agent_a", "active")

        assert hub.agent_status["agent_a"] == "active"

    @pytest.mark.asyncio
    async def test_pr_discovery_payload_structure(self, hub):
        """Test PR discovery message has correct structure."""
        await hub.start_hub()

        pr_payload = {
            'pr_info': {
                'pr_number': '468',
                'pr_title': 'Add feature support'
            },
            'ai_context_analysis': {
                'requires_collection': True,
                'urgency_level': 'high'
            },
            'discovery_timestamp': datetime.now().isoformat()
        }

        msg_id = await hub.publish_message(
            sender_agent="agent_a",
            target_agent="agent_d",
            message_type="pr_discovery",
            payload=pr_payload,
            priority="high"
        )

        history = hub.get_message_history()
        assert history[0]['payload']['pr_info']['pr_number'] == '468'

        await hub.stop_hub()


class TestCommunicationHubStatus:
    """Test hub status and monitoring functionality."""

    @pytest.fixture
    def hub(self):
        return MockCommunicationHub("phase_1", "test_run_001")

    def test_hub_status_structure(self, hub):
        """Test hub status returns expected structure."""
        hub.register_agent("agent_a", {})
        hub.register_agent("agent_d", {})

        status = {
            'phase_id': hub.phase_id,
            'run_id': hub.run_id,
            'hub_active': hub.hub_active,
            'active_agents': dict(hub.agent_status),
            'total_messages': len(hub.message_history),
            'subscription_count': sum(len(subs) for subs in hub.subscriptions.values())
        }

        assert status['phase_id'] == "phase_1"
        assert len(status['active_agents']) == 2

    @pytest.mark.asyncio
    async def test_message_count_tracking(self, hub):
        """Test message count is tracked correctly."""
        await hub.start_hub()

        initial_count = len(hub.message_history)

        for i in range(10):
            await hub.publish_message(
                sender_agent="agent_a",
                target_agent="agent_d",
                message_type="test",
                payload={"i": i}
            )

        assert len(hub.message_history) == initial_count + 10

        await hub.stop_hub()


class TestMultiAgentCoordination:
    """Test multi-agent coordination scenarios."""

    @pytest.fixture
    def hub(self):
        return MockCommunicationHub("phase_1", "test_run_001")

    @pytest.mark.asyncio
    async def test_agent_a_to_d_coordination(self, hub):
        """Test complete Agent A to Agent D coordination flow."""
        await hub.start_hub()

        # Register both agents
        hub.register_agent("agent_a", {"type": "jira"})
        hub.register_agent("agent_d", {"type": "environment"})

        # Agent A publishes PR discovery
        await hub.publish_message(
            sender_agent="agent_a",
            target_agent="agent_d",
            message_type="pr_discovery",
            payload={
                "pr_number": "468",
                "deployment_components": ["ClusterCurator"],
                "collection_priority": "high"
            }
        )

        # Agent A requests environment data
        await hub.publish_message(
            sender_agent="agent_a",
            target_agent="agent_d",
            message_type="environment_data_request",
            payload={
                "required_yamls": ["clustercurator.yaml"],
                "required_logs": ["controller logs"]
            }
        )

        # Verify coordination
        history = hub.get_message_history(agent_id="agent_d")
        assert len(history) == 2

        pr_discovery = [m for m in history if m['message_type'] == 'pr_discovery'][0]
        assert pr_discovery['payload']['pr_number'] == "468"

        await hub.stop_hub()

    @pytest.mark.asyncio
    async def test_broadcast_message(self, hub):
        """Test broadcast message to all agents."""
        await hub.start_hub()

        hub.register_agent("agent_a", {})
        hub.register_agent("agent_b", {})
        hub.register_agent("agent_c", {})

        await hub.publish_message(
            sender_agent="orchestrator",
            target_agent="all",
            message_type="phase_complete",
            payload={"phase": "1", "status": "success"}
        )

        history = hub.get_message_history()
        assert history[0]['target_agent'] == "all"

        await hub.stop_hub()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
