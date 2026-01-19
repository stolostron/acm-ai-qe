#!/usr/bin/env python3
"""
Inter-Agent Communication System
Enables real-time coordination between agents within the same phase
"""

import asyncio
import json
import logging
import threading
import uuid
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class InterAgentMessage:
    """Message structure for inter-agent communication"""
    message_id: str
    sender_agent: str
    target_agent: str  # Can be specific agent or "all" for broadcast
    message_type: str  # "pr_discovery", "environment_request", "data_share", etc.
    payload: Dict[str, Any]
    timestamp: str
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    requires_response: bool = False
    correlation_id: Optional[str] = None


@dataclass
class AgentSubscription:
    """Agent subscription configuration"""
    agent_id: str
    message_types: List[str]
    callback: Callable
    active: bool = True


class InterAgentCommunicationHub:
    """
    Real-time communication hub for agents within the same phase
    Thread-safe, async-compatible message passing system
    """
    
    def __init__(self, phase_id: str, run_id: str):
        self.phase_id = phase_id
        self.run_id = run_id
        self.hub_id = f"{phase_id}_{run_id}_{uuid.uuid4().hex[:8]}"
        
        # Message storage and routing
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.message_history: List[InterAgentMessage] = []
        self.subscriptions: Dict[str, List[AgentSubscription]] = defaultdict(list)
        
        # Agent registry
        self.active_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_status: Dict[str, str] = {}  # "starting", "active", "completed", "failed"
        
        # Hub control
        self.hub_active = False
        self.hub_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        
        logger.info(f"Inter-agent communication hub initialized: {self.hub_id}")
    
    async def start_hub(self):
        """Start the communication hub"""
        self.hub_active = True
        self.hub_task = asyncio.create_task(self._message_processor())
        logger.info(f"Communication hub started for phase {self.phase_id}")
    
    async def stop_hub(self):
        """Stop the communication hub"""
        self.hub_active = False
        if self.hub_task:
            self.hub_task.cancel()
            try:
                await self.hub_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Communication hub stopped for phase {self.phase_id}")
    
    def register_agent(self, agent_id: str, agent_metadata: Dict[str, Any]):
        """Register an agent with the communication hub"""
        with self._lock:
            self.active_agents[agent_id] = {
                'metadata': agent_metadata,
                'registered_at': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat()
            }
            self.agent_status[agent_id] = "starting"
        
        logger.info(f"Agent {agent_id} registered with communication hub")
    
    def update_agent_status(self, agent_id: str, status: str):
        """Update agent status"""
        with self._lock:
            if agent_id in self.agent_status:
                self.agent_status[agent_id] = status
                self.active_agents[agent_id]['last_activity'] = datetime.now().isoformat()
        
        logger.debug(f"Agent {agent_id} status updated to: {status}")
    
    def subscribe_to_messages(self, agent_id: str, message_types: List[str], 
                            callback: Callable[[InterAgentMessage], None]):
        """Subscribe agent to specific message types"""
        subscription = AgentSubscription(
            agent_id=agent_id,
            message_types=message_types,
            callback=callback
        )
        
        with self._lock:
            for msg_type in message_types:
                self.subscriptions[msg_type].append(subscription)
        
        logger.info(f"Agent {agent_id} subscribed to message types: {message_types}")
    
    async def publish_message(self, sender_agent: str, target_agent: str, 
                            message_type: str, payload: Dict[str, Any],
                            priority: str = "normal", requires_response: bool = False) -> str:
        """Publish a message to the communication hub"""
        
        message = InterAgentMessage(
            message_id=uuid.uuid4().hex,
            sender_agent=sender_agent,
            target_agent=target_agent,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now().isoformat(),
            priority=priority,
            requires_response=requires_response
        )
        
        # Add to queue for processing
        await self.message_queue.put(message)
        
        # Store in history
        with self._lock:
            self.message_history.append(message)
            if sender_agent in self.active_agents:
                self.active_agents[sender_agent]['last_activity'] = datetime.now().isoformat()
        
        logger.info(f"Message published: {sender_agent} → {target_agent} ({message_type})")
        return message.message_id
    
    async def _message_processor(self):
        """Background message processor"""
        logger.info("Message processor started")
        
        while self.hub_active:
            try:
                # Get message from queue with timeout
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # Route message to subscribers
                await self._route_message(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                continue
    
    async def _route_message(self, message: InterAgentMessage):
        """Route message to appropriate subscribers"""
        
        # Find subscribers for this message type
        subscribers = []
        with self._lock:
            if message.message_type in self.subscriptions:
                subscribers = [sub for sub in self.subscriptions[message.message_type] 
                             if sub.active and (sub.agent_id == message.target_agent or message.target_agent == "all")]
        
        # Deliver to subscribers
        for subscriber in subscribers:
            try:
                # Call subscriber callback
                if asyncio.iscoroutinefunction(subscriber.callback):
                    await subscriber.callback(message)
                else:
                    subscriber.callback(message)
                
                logger.debug(f"Message delivered to {subscriber.agent_id}")
                
            except Exception as e:
                logger.error(f"Failed to deliver message to {subscriber.agent_id}: {e}")
    
    def get_hub_status(self) -> Dict[str, Any]:
        """Get hub status"""
        with self._lock:
            return {
                'hub_id': self.hub_id,
                'phase_id': self.phase_id,
                'run_id': self.run_id,
                'hub_active': self.hub_active,
                'active_agents': dict(self.agent_status),
                'total_messages': len(self.message_history),
                'subscription_count': sum(len(subs) for subs in self.subscriptions.values()),
                'message_types': list(self.subscriptions.keys())
            }
    
    def get_message_history(self, agent_id: Optional[str] = None, 
                          message_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get message history with optional filtering"""
        with self._lock:
            filtered_messages = self.message_history
            
            if agent_id:
                filtered_messages = [msg for msg in filtered_messages 
                                   if msg.sender_agent == agent_id or msg.target_agent == agent_id]
            
            if message_type:
                filtered_messages = [msg for msg in filtered_messages 
                                   if msg.message_type == message_type]
            
            return [asdict(msg) for msg in filtered_messages]


class AgentCommunicationInterface:
    """
    Interface for agents to interact with the communication hub
    Provides simplified API for publishing and subscribing to messages
    """
    
    def __init__(self, agent_id: str, communication_hub: InterAgentCommunicationHub):
        self.agent_id = agent_id
        self.hub = communication_hub
        self.subscribed_types: List[str] = []
        
        # Register with hub
        self.hub.register_agent(agent_id, {'agent_type': 'framework_agent'})
        
        logger.info(f"Communication interface initialized for {agent_id}")
    
    async def publish_pr_discovery(self, pr_info: Dict[str, Any], target_agent: str = "agent_d_environment_intelligence"):
        """Publish PR discovery information with AI-driven context analysis"""
        
        # Use AI to analyze PR context and determine collection requirements
        ai_analysis = self._analyze_pr_context_with_ai(pr_info)
        
        await self.hub.publish_message(
            sender_agent=self.agent_id,
            target_agent=target_agent,
            message_type="pr_discovery",
            payload={
                'pr_info': pr_info,
                'ai_context_analysis': ai_analysis,
                'discovery_timestamp': datetime.now().isoformat(),
                'requires_environment_collection': ai_analysis.get('requires_collection', True),
                'collection_urgency': ai_analysis.get('urgency_level', 'normal'),
                'component_specific_requirements': ai_analysis.get('component_requirements', {})
            },
            priority=ai_analysis.get('message_priority', 'high'),
            requires_response=True
        )
        
        logger.info(f"Published PR discovery with AI analysis: {pr_info.get('pr_number', 'unknown')}")
    
    def _analyze_pr_context_with_ai(self, pr_info: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to analyze PR context and determine optimal collection strategy"""
        
        # Extract component information
        components = pr_info.get('deployment_components', [])
        pr_title = pr_info.get('pr_title', '')
        files_changed = pr_info.get('files_changed', [])
        
        # AI-driven analysis
        analysis = {
            'requires_collection': True,
            'urgency_level': 'normal',
            'message_priority': 'high',
            'component_requirements': {}
        }
        
        # Determine urgency based on PR characteristics
        if len(files_changed) > 15:
            analysis['urgency_level'] = 'high'
            analysis['message_priority'] = 'urgent'
        elif len(components) > 2:
            analysis['urgency_level'] = 'high'
        
        # Component-specific analysis
        for component in components:
            component_lower = component.lower()
            
            if 'cluster' in component_lower or 'curator' in component_lower:
                analysis['component_requirements']['cluster_lifecycle'] = {
                    'namespace_focus': ['open-cluster-management', 'open-cluster-management-hub'],
                    'resource_types': ['clustercurators', 'managedclusters'],
                    'critical_logs': ['clustercurator-controller-manager']
                }
            elif 'policy' in component_lower:
                analysis['component_requirements']['governance'] = {
                    'namespace_focus': ['open-cluster-management'],
                    'resource_types': ['policies', 'policysets'],
                    'critical_logs': ['governance-policy-framework']
                }
            elif 'observability' in component_lower:
                analysis['component_requirements']['monitoring'] = {
                    'namespace_focus': ['open-cluster-management-observability'],
                    'resource_types': ['multiclusterobservabilities', 'observabilityaddon'],
                    'critical_logs': ['observability-controller']
                }
            elif 'application' in component_lower:
                analysis['component_requirements']['app_lifecycle'] = {
                    'namespace_focus': ['open-cluster-management-agent-addon'],
                    'resource_types': ['applications', 'subscriptions'],
                    'critical_logs': ['application-manager']
                }
            elif 'console' in component_lower:
                analysis['component_requirements']['ui'] = {
                    'namespace_focus': ['openshift-console'],
                    'resource_types': ['console.operator'],
                    'critical_logs': ['console']
                }
        
        # Analyze title for additional context
        title_lower = pr_title.lower()
        if any(keyword in title_lower for keyword in ['critical', 'urgent', 'security', 'breaking']):
            analysis['urgency_level'] = 'critical'
            analysis['message_priority'] = 'urgent'
        elif any(keyword in title_lower for keyword in ['api', 'crd', 'controller']):
            analysis['urgency_level'] = 'high'
        
        return analysis
    
    async def publish_jira_intelligence(self, jira_analysis: Dict[str, Any], target_agent: str = "agent_d_environment_intelligence"):
        """Publish JIRA analysis"""
        await self.hub.publish_message(
            sender_agent=self.agent_id,
            target_agent=target_agent,
            message_type="jira_intelligence",
            payload={
                'jira_analysis': jira_analysis,
                'analysis_timestamp': datetime.now().isoformat(),
                'environment_requirements': jira_analysis.get('environment_requirements', {})
            },
            priority="normal"
        )
    
    async def request_environment_data(self, data_requirements: Dict[str, Any], target_agent: str = "agent_d_environment_intelligence"):
        """Request specific environment data collection"""
        await self.hub.publish_message(
            sender_agent=self.agent_id,
            target_agent=target_agent,
            message_type="environment_data_request",
            payload={
                'requirements': data_requirements,
                'urgency': 'high',
                'expected_data_types': ['yamls', 'logs', 'commands', 'configurations']
            },
            priority="high",
            requires_response=True
        )
    
    def subscribe_to_pr_discoveries(self, callback: Callable[[InterAgentMessage], None]):
        """Subscribe to PR discovery messages"""
        self.hub.subscribe_to_messages(self.agent_id, ["pr_discovery"], callback)
        self.subscribed_types.append("pr_discovery")
    
    def subscribe_to_jira_intelligence(self, callback: Callable[[InterAgentMessage], None]):
        """Subscribe to JIRA intelligence messages"""
        self.hub.subscribe_to_messages(self.agent_id, ["jira_intelligence"], callback)
        self.subscribed_types.append("jira_intelligence")
    
    def subscribe_to_environment_requests(self, callback: Callable[[InterAgentMessage], None]):
        """Subscribe to environment data requests"""
        self.hub.subscribe_to_messages(self.agent_id, ["environment_data_request"], callback)
        self.subscribed_types.append("environment_data_request")
    
    def update_status(self, status: str):
        """Update agent status"""
        self.hub.update_agent_status(self.agent_id, status)
    
    def get_communication_history(self) -> List[Dict[str, Any]]:
        """Get communication history for this agent"""
        return self.hub.get_message_history(agent_id=self.agent_id)


# Global hub registry for managing multiple communication hubs
_communication_hubs: Dict[str, InterAgentCommunicationHub] = {}

def get_communication_hub(phase_id: str, run_id: str) -> InterAgentCommunicationHub:
    """Get or create communication hub for a phase"""
    hub_key = f"{phase_id}_{run_id}"
    
    if hub_key not in _communication_hubs:
        _communication_hubs[hub_key] = InterAgentCommunicationHub(phase_id, run_id)
    
    return _communication_hubs[hub_key]

def cleanup_communication_hub(phase_id: str, run_id: str):
    """Cleanup communication hub after phase completion"""
    hub_key = f"{phase_id}_{run_id}"
    
    if hub_key in _communication_hubs:
        del _communication_hubs[hub_key]
        logger.info(f"Communication hub cleaned up: {hub_key}")


if __name__ == '__main__':
    # Production module - no test code in main files
    print("Inter-Agent Communication System - Production Module")
    print("Use dedicated test files for testing functionality")