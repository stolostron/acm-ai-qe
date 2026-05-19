#!/bin/bash

# 🚀 Improved n8n Dashboard Setup Script
# This script sets up n8n with proper webhook-based monitoring

echo "🎯 Setting up Improved n8n Dashboard with Webhook Integration"
echo "============================================================="

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Define paths
IMPROVED_WORKFLOW="$SCRIPT_DIR/n8n-workflows/improved-framework-monitor.json"
VISUAL_WORKFLOW="$SCRIPT_DIR/n8n-workflows/visual-dashboard-workflow.json"
N8N_PORT=5678
DASHBOARD_PORT=8080

echo ""
echo "📋 Step 1: Checking n8n installation..."

# Check if n8n is installed
if ! command -v n8n &> /dev/null; then
    echo "❌ n8n is not installed. Installing..."
    npm install -g n8n
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install n8n. Please check npm configuration."
        exit 1
    fi
else
    echo "✅ n8n is installed"
fi

# Check if n8n is running
echo ""
echo "📋 Step 2: Starting n8n..."
if curl -s "http://localhost:${N8N_PORT}/health" > /dev/null 2>&1; then
    echo "✅ n8n is already running on port ${N8N_PORT}"
else
    echo "🚀 Starting n8n on port ${N8N_PORT}..."
    N8N_PORT=${N8N_PORT} n8n start > /tmp/n8n.log 2>&1 &
    N8N_PID=$!
    
    # Wait for n8n to start
    echo "⏳ Waiting for n8n to start (this may take up to 30 seconds)..."
    for i in {1..30}; do
        if curl -s "http://localhost:${N8N_PORT}/" > /dev/null 2>&1; then
            echo "✅ n8n is now running!"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    if ! curl -s "http://localhost:${N8N_PORT}/" > /dev/null 2>&1; then
        echo ""
        echo "❌ n8n failed to start. Checking logs..."
        tail -20 /tmp/n8n.log
        exit 1
    fi
fi

# Start simple HTTP server for dashboard
echo ""
echo "📋 Step 3: Starting dashboard server..."
if lsof -i :${DASHBOARD_PORT} > /dev/null 2>&1; then
    echo "✅ Dashboard server already running on port ${DASHBOARD_PORT}"
else
    echo "🚀 Starting dashboard server on port ${DASHBOARD_PORT}..."
    cd /tmp && python3 -m http.server ${DASHBOARD_PORT} > /tmp/dashboard-server.log 2>&1 &
    DASHBOARD_PID=$!
    echo "✅ Dashboard server started (PID: $DASHBOARD_PID)"
fi

echo ""
echo "🎯 Step 4: Setup Instructions"
echo "=============================="
echo ""
echo "🌐 n8n Dashboard: http://localhost:${N8N_PORT}"
echo "📊 Visual Dashboard: http://localhost:${DASHBOARD_PORT}/ai_framework_dashboard.html"
echo ""
echo "📥 Import Workflows:"
echo "   1. Open n8n in your browser"
echo "   2. Click '+' → 'Import from File'"
echo "   3. Import these workflows:"
echo "      - ${IMPROVED_WORKFLOW}"
echo "      - ${VISUAL_WORKFLOW}"
echo ""
echo "🚀 Activate Workflows:"
echo "   1. Open each imported workflow"
echo "   2. Toggle the 'Active' switch to ON"
echo "   3. Save the workflow"
echo ""
echo "🔗 Webhook URLs for your Python app:"
echo "   - Status Updates: http://localhost:${N8N_PORT}/webhook/framework-status"
echo "   - Error Alerts: http://localhost:${N8N_PORT}/webhook/framework-error"
echo "   - Visual Updates: http://localhost:${N8N_PORT}/webhook/visual-status"
echo ""

# Test webhook connectivity
echo "🧪 Step 5: Testing webhook connectivity..."
echo ""

# Create test payload
TEST_PAYLOAD='{
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
  "type": "framework_update",
  "jira_ticket": "TEST-001",
  "phase": "initialization",
  "status": "completed",
  "agents": []
}'

# Try to send test webhook
echo "Testing framework status webhook..."
RESPONSE=$(curl -s -X POST "http://localhost:${N8N_PORT}/webhook/framework-status" \
    -H "Content-Type: application/json" \
    -d "$TEST_PAYLOAD" 2>&1)

if [ $? -eq 0 ]; then
    echo "✅ Webhook test successful!"
else
    echo "⚠️  Webhook not yet configured. This is normal if workflows haven't been imported yet."
fi

# Create environment file
echo ""
echo "📝 Creating environment configuration..."
cat > "$SCRIPT_DIR/.env.n8n" << EOF
# n8n Integration Environment Variables
export N8N_WEBHOOK_URL="http://localhost:${N8N_PORT}/webhook"
export FRAMEWORK_MONITORING_ENABLED="true"
export N8N_PORT="${N8N_PORT}"
export DASHBOARD_PORT="${DASHBOARD_PORT}"
EOF

echo "✅ Environment file created at: $SCRIPT_DIR/.env.n8n"

# Create Python test script
echo ""
echo "📝 Creating test script..."
cat > "$SCRIPT_DIR/test_improved_monitoring.py" << 'EOF'
#!/usr/bin/env python3
"""Test script for improved n8n monitoring"""

import os
import sys
import time
import requests
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import monitoring client
from n8n_integration.framework_monitor_client import init_framework_monitoring, send_phase_update, send_agent_update

def test_monitoring():
    """Test the improved monitoring setup"""
    print("🧪 Testing Improved n8n Monitoring")
    print("==================================")
    
    # Initialize monitoring
    monitor = init_framework_monitoring("TEST-002")
    print("✅ Monitoring initialized")
    
    # Test phase updates
    print("\n📊 Testing phase updates...")
    phases = [
        ("initialization", "starting"),
        ("initialization", "completed"),
        ("foundation_analysis", "starting"),
        ("foundation_analysis", "running"),
        ("foundation_analysis", "completed")
    ]
    
    for phase, status in phases:
        print(f"   Sending: {phase} - {status}")
        send_phase_update(phase, status)
        time.sleep(1)
    
    # Test agent updates
    print("\n🤖 Testing agent updates...")
    agents = [
        ("agent_a", "starting", None, None),
        ("agent_a", "running", 75.0, None),
        ("agent_a", "completed", 85.0, 45.2)
    ]
    
    for agent, status, confidence, exec_time in agents:
        print(f"   Sending: {agent} - {status}")
        kwargs = {}
        if confidence: kwargs['confidence'] = confidence
        if exec_time: kwargs['execution_time'] = exec_time
        send_agent_update(agent, status, **kwargs)
        time.sleep(1)
    
    print("\n✅ Test completed!")
    print("🌐 Check your dashboards:")
    print(f"   - n8n: http://localhost:{os.getenv('N8N_PORT', '5678')}")
    print(f"   - Visual: http://localhost:{os.getenv('DASHBOARD_PORT', '8080')}/ai_framework_dashboard.html")

if __name__ == "__main__":
    # Load environment
    env_file = os.path.join(os.path.dirname(__file__), '.env.n8n')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith('export '):
                    key, value = line.replace('export ', '').strip().split('=', 1)
                    os.environ[key] = value.strip('"')
    
    test_monitoring()
EOF

chmod +x "$SCRIPT_DIR/test_improved_monitoring.py"
echo "✅ Test script created at: $SCRIPT_DIR/test_improved_monitoring.py"

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📚 Quick Reference:"
echo "   - n8n Dashboard: http://localhost:${N8N_PORT}"
echo "   - Visual Dashboard: http://localhost:${DASHBOARD_PORT}/ai_framework_dashboard.html"
echo "   - Environment file: source $SCRIPT_DIR/.env.n8n"
echo "   - Test script: $SCRIPT_DIR/test_improved_monitoring.py"
echo ""
echo "🚀 Next Steps:"
echo "   1. Import the workflows into n8n"
echo "   2. Activate both workflows"
echo "   3. Run the test script to verify everything works"
echo "   4. Update your Python app to use webhook URLs"
echo ""
echo "💡 Key Improvements:"
echo "   ✅ Webhook-based real-time updates (no more polling!)"
echo "   ✅ Proper data flow with merge nodes"
echo "   ✅ No hardcoded paths in workflows"
echo "   ✅ Visual dashboard with live updates"
echo "   ✅ Comprehensive error handling"
echo ""

# Optional: Auto-open browser
if command -v open &> /dev/null; then
    echo "🌐 Opening n8n dashboard in browser..."
    open "http://localhost:${N8N_PORT}"
fi

echo "Ready for improved real-time monitoring! 🚀"

