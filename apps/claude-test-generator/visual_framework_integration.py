#!/usr/bin/env python3
"""
Visual Framework Integration
Sends real-time status updates to n8n for visual dashboard display
"""

import os
import requests
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class VisualFrameworkMonitor:
    """
    Visual monitoring client for real-time dashboard updates
    """
    
    def __init__(self, n8n_webhook_url: str = None):
        self.webhook_url = n8n_webhook_url or os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook')
        self.visual_webhook = f"{self.webhook_url}/framework-visual-status"
        self.current_jira = None
        
    def start_monitoring(self, jira_ticket: str):
        """Initialize monitoring for a JIRA ticket"""
        self.current_jira = jira_ticket
        logger.info(f"Visual monitoring started for {jira_ticket}")
        
    def send_phase_status(self, phase: str, status: str, **kwargs):
        """Send phase status update for visual display"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "jira_ticket": self.current_jira,
            "phase": phase,
            "status": status,
            **kwargs
        }
        self._send_update(payload)
        
    def send_agent_status(self, agent: str, status: str, confidence: float = None, execution_time: float = None):
        """Send agent status update for visual display"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "jira_ticket": self.current_jira,
            "agent": agent,
            "status": status,
            "confidence": confidence,
            "execution_time": execution_time
        }
        self._send_update(payload)
        
    def _send_update(self, payload: Dict[str, Any]):
        """Send update to n8n visual webhook"""
        try:
            response = requests.post(self.visual_webhook, json=payload, timeout=5)
            response.raise_for_status()
            logger.debug(f"Visual update sent: {payload.get('phase', payload.get('agent'))}")
        except Exception as e:
            logger.warning(f"Failed to send visual update: {e}")


def simulate_framework_execution(jira_ticket: str = "ACM-22079"):
    """
    Simulate complete framework execution with visual updates
    """
    monitor = VisualFrameworkMonitor()
    monitor.start_monitoring(jira_ticket)
    
    print(f"🚀 Starting visual framework simulation for {jira_ticket}")
    print("💡 Open browser to http://localhost:8080/framework_dashboard.html to see real-time updates")
    
    # Phase 0: Initialization
    print("\n🔄 Phase 0: Initialization")
    monitor.send_phase_status("initialization", "starting")
    time.sleep(2)
    monitor.send_phase_status("initialization", "completed")
    
    # Phase 1: Foundation Analysis
    print("🔄 Phase 1: Foundation Analysis")
    monitor.send_phase_status("foundation_analysis", "starting")
    
    # Agent A: JIRA
    print("   🤖 Agent A: JIRA Intelligence")
    monitor.send_agent_status("agent_a", "starting")
    time.sleep(3)
    monitor.send_agent_status("agent_a", "running", confidence=85.0)
    time.sleep(2)
    monitor.send_agent_status("agent_a", "completed", confidence=85.0, execution_time=5.0)
    
    # Agent D: Environment (parallel)
    print("   🤖 Agent D: Environment Assessment")
    monitor.send_agent_status("agent_d", "starting")
    time.sleep(2)
    monitor.send_agent_status("agent_d", "running", confidence=90.0)
    time.sleep(3)
    monitor.send_agent_status("agent_d", "completed", confidence=90.0, execution_time=5.5)
    
    monitor.send_phase_status("foundation_analysis", "completed")
    
    # Phase 2: Deep Investigation
    print("🔄 Phase 2: Deep Investigation")
    monitor.send_phase_status("deep_investigation", "starting")
    
    # Agent B: Documentation
    print("   🤖 Agent B: Documentation Analysis")
    monitor.send_agent_status("agent_b", "starting")
    time.sleep(2)
    monitor.send_agent_status("agent_b", "running", confidence=75.0)
    time.sleep(4)
    monitor.send_agent_status("agent_b", "completed", confidence=75.0, execution_time=6.0)
    
    # Agent C: GitHub
    print("   🤖 Agent C: GitHub Investigation")
    monitor.send_agent_status("agent_c", "starting")
    time.sleep(3)
    monitor.send_agent_status("agent_c", "running", confidence=80.0)
    time.sleep(2)
    monitor.send_agent_status("agent_c", "completed", confidence=80.0, execution_time=5.2)
    
    monitor.send_phase_status("deep_investigation", "completed")
    
    # Phase 2.5: QE Intelligence
    print("🔄 Phase 2.5: QE Intelligence")
    monitor.send_phase_status("qe_intelligence", "starting")
    time.sleep(3)
    monitor.send_phase_status("qe_intelligence", "completed")
    
    # Phase 3: AI Analysis
    print("🔄 Phase 3: AI Analysis")
    monitor.send_phase_status("ai_analysis", "starting")
    time.sleep(4)
    monitor.send_phase_status("ai_analysis", "completed")
    
    # Phase 4: Test Generation
    print("🔄 Phase 4: Test Generation")
    monitor.send_phase_status("test_generation", "starting")
    time.sleep(5)
    monitor.send_phase_status("test_generation", "completed")
    
    # Phase 5: Cleanup
    print("🔄 Phase 5: Cleanup")
    monitor.send_phase_status("cleanup", "starting")
    time.sleep(2)
    monitor.send_phase_status("cleanup", "completed")
    
    print("✅ Framework simulation completed!")
    print("🎉 Check your dashboard for the final state")


def integrate_with_existing_framework():
    """
    Example integration with existing framework
    """
    monitor = VisualFrameworkMonitor()
    
    # Add these calls to your existing framework execution:
    
    # At the start
    monitor.start_monitoring("ACM-12345")  # Your JIRA ticket
    
    # In your orchestrator phases:
    monitor.send_phase_status("foundation_analysis", "starting")
    
    # In your agent execution:
    monitor.send_agent_status("agent_a", "starting")
    monitor.send_agent_status("agent_a", "running", confidence=85.0)
    monitor.send_agent_status("agent_a", "completed", confidence=85.0, execution_time=45.2)
    
    # Continue for all phases and agents...


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🎬 Visual Framework Monitor Demo")
    print("=" * 50)
    print("1. Make sure n8n is running with the visual workflow imported")
    print("2. Start HTTP server: python -m http.server 8080")
    print("3. Open browser: http://localhost:8080/framework_dashboard.html")
    print("4. Run this simulation to see real-time updates")
    print("=" * 50)
    
    input("Press Enter to start simulation...")
    
    simulate_framework_execution()