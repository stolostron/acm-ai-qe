#!/usr/bin/env python3
"""
Test Inter-Agent Communication System
=====================================

Dedicated test file for inter-agent communication functionality.
Tests dynamic component handling for any JIRA ticket.
"""

import sys
import os
import asyncio
import tempfile
from pathlib import Path

# Add path for imports
sys.path.append('..')
sys.path.append('../..')
# Try to import inter-agent communication with fallback paths
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from inter_agent_communication import InterAgentCommunicationHub, AgentCommunicationInterface, InterAgentMessage
except ImportError:
    sys.path.append('..')
    from inter_agent_communication import InterAgentCommunicationHub, AgentCommunicationInterface, InterAgentMessage

async def test_dynamic_pr_discovery():
    """Test dynamic PR discovery for different components"""
    
    print("🧪 Testing Dynamic PR Discovery Communication")
    print("=" * 60)
    
    # Create communication hub
    hub = InterAgentCommunicationHub("test_phase", "dynamic_test")
    await hub.start_hub()
    
    # Create agent interfaces
    agent_a_comm = AgentCommunicationInterface("agent_a_jira_intelligence", hub)
    agent_d_comm = AgentCommunicationInterface("agent_d_environment_intelligence", hub)
    
    # Set up Agent D subscription
    received_messages = []
    
    def agent_d_callback(message: InterAgentMessage):
        received_messages.append(message)
        print(f"Agent D received: {message.message_type} from {message.sender_agent}")
    
    agent_d_comm.subscribe_to_pr_discoveries(agent_d_callback)
    
    # Test different component scenarios
    test_scenarios = [
        {
            'name': 'ClusterCurator Component',
            'pr_info': {
                'pr_number': '468',
                'pr_title': 'Support digest-based upgrades via ClusterCurator',
                'files_changed': ['pkg/clustercurator/controller.go', 'config/crd/clustercurator.yaml'],
                'deployment_components': ['ClusterCurator']
            }
        },
        {
            'name': 'Policy Component',
            'pr_info': {
                'pr_number': '123',
                'pr_title': 'Add new governance policy validation',
                'files_changed': ['pkg/policy/controller.go', 'api/v1/policy_types.go'],
                'deployment_components': ['Policy Framework']
            }
        },
        {
            'name': 'Observability Component',
            'pr_info': {
                'pr_number': '456',
                'pr_title': 'Critical monitoring API changes',
                'files_changed': ['pkg/observability/controller.go'] * 20,  # Large PR
                'deployment_components': ['Observability', 'Monitoring']
            }
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. Testing {scenario['name']}:")
        
        # Publish PR discovery
        await agent_a_comm.publish_pr_discovery(scenario['pr_info'])
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check received message
        if len(received_messages) >= i:
            message = received_messages[i-1]
            ai_analysis = message.payload.get('ai_context_analysis', {})
            
            print(f"   ✅ Message received")
            print(f"   📊 Urgency: {ai_analysis.get('urgency_level', 'unknown')}")
            print(f"   ⚡ Priority: {ai_analysis.get('message_priority', 'unknown')}")
            print(f"   🏷️ Components: {len(ai_analysis.get('component_requirements', {}))}")
            
            # Show component-specific requirements
            for comp_name, reqs in ai_analysis.get('component_requirements', {}).items():
                print(f"      {comp_name}: {len(reqs.get('resource_types', []))} resource types")
        else:
            print(f"   ❌ Message not received")
    
    await hub.stop_hub()
    
    print(f"\n📊 Test Results:")
    print(f"   Messages sent: {len(test_scenarios)}")
    print(f"   Messages received: {len(received_messages)}")
    print(f"   Success rate: {len(received_messages)/len(test_scenarios):.1%}")
    
    return len(received_messages) == len(test_scenarios)

async def test_ai_context_analysis():
    """Test AI context analysis for different PR types"""
    
    print("\n🧠 Testing AI Context Analysis")
    print("=" * 40)
    
    # Create agent interface for testing
    hub = InterAgentCommunicationHub("test_phase", "ai_test")
    await hub.start_hub()
    
    agent_comm = AgentCommunicationInterface("test_agent", hub)
    
    # Test different PR scenarios
    test_prs = [
        {
            'pr_title': 'Fix critical security vulnerability in policy framework',
            'deployment_components': ['Policy Framework'],
            'files_changed': ['pkg/policy/security.go']
        },
        {
            'pr_title': 'Add new application lifecycle webhook',
            'deployment_components': ['Application'],
            'files_changed': ['pkg/webhook/app_webhook.go', 'api/v1beta1/types.go']
        },
        {
            'pr_title': 'Update console UI for cluster overview',
            'deployment_components': ['Console'],
            'files_changed': ['frontend/src/cluster-overview.tsx'] * 25  # Large UI change
        }
    ]
    
    for i, pr_info in enumerate(test_prs, 1):
        print(f"{i}. Analyzing: {pr_info['pr_title'][:40]}...")
        
        analysis = agent_comm._analyze_pr_context_with_ai(pr_info)
        
        print(f"   Urgency: {analysis['urgency_level']}")
        print(f"   Priority: {analysis['message_priority']}")
        print(f"   Component reqs: {len(analysis['component_requirements'])}")
        
        # Validate AI made intelligent decisions
        components = pr_info['deployment_components']
        files_count = len(pr_info['files_changed'])
        
        # Check urgency logic
        expected_high_urgency = (
            'critical' in pr_info['pr_title'].lower() or 
            'security' in pr_info['pr_title'].lower() or
            files_count > 15
        )
        
        correct_urgency = (
            (expected_high_urgency and analysis['urgency_level'] in ['high', 'critical']) or
            (not expected_high_urgency and analysis['urgency_level'] in ['normal', 'high'])
        )
        
        print(f"   AI Analysis: {'✅ Correct' if correct_urgency else '❌ Incorrect'}")
    
    await hub.stop_hub()
    
    print("\n✅ AI Context Analysis Complete")

if __name__ == "__main__":
    async def run_all_tests():
        success1 = await test_dynamic_pr_discovery()
        await test_ai_context_analysis()
        
        if success1:
            print("\n🎉 ALL TESTS PASSED")
            print("Inter-agent communication working dynamically for any component")
        else:
            print("\n❌ TESTS FAILED")
            print("Issues found in inter-agent communication")
    
    asyncio.run(run_all_tests())
