# Claude Test Generator ↔ n8n Webhook Integration

## 🎯 What "Python App" Means

When I refer to the **"Python app"** sending webhooks, I mean your **Claude Test Generator Framework** - the AI system that runs when you interact with Claude.

## 🚀 How Users Actually Execute the Framework

### Method 1: Natural Language with Claude (Most Common)
```
User in Claude Code: "Generate test plan for ACM-22079"
```

**What happens behind the scenes:**
1. Claude detects this is a test generation request
2. Claude navigates to the framework directory
3. Claude executes the AI Agent Orchestrator
4. The orchestrator runs the 4-agent investigation
5. **This is where the webhook integration kicks in!**

### Method 2: Direct Python Execution
```bash
cd apps/claude-test-generator
python3 .claude/ai-services/ai_agent_orchestrator.py ACM-22079 mist10
```

### Method 3: Through Test Runner
```bash
python3 tests/run_tests.py
```

## 🔗 Where Webhooks Fit In

The webhook integration happens **inside** the framework execution, specifically in the **AI Agent Orchestrator** (`ai_agent_orchestrator.py`).

### Current Architecture:
```
User Request → Claude → Framework Directory → AI Agent Orchestrator → 4 Agents Execute
```

### With n8n Integration:
```
User Request → Claude → Framework Directory → AI Agent Orchestrator → 4 Agents Execute → Webhooks to n8n → Real-time Dashboard
```

## 📡 Integration Points in Your Framework

### 1. **PhaseBasedOrchestrator Integration**

Your main orchestrator (`ai_agent_orchestrator.py`) would integrate webhooks like this:

```python
# In ai_agent_orchestrator.py - PhaseBasedOrchestrator class
from n8n_integration.framework_monitor_client import init_framework_monitoring, send_phase_update, send_agent_update

class PhaseBasedOrchestrator:
    def __init__(self):
        # Initialize n8n monitoring
        self.monitor = init_framework_monitoring()
    
    async def execute_full_framework(self, jira_id: str, environment: str = None):
        # Initialize monitoring for this execution
        self.monitor.start_execution(jira_id)
        
        # Phase 0: Initialization
        send_phase_update("initialization", "starting")
        await self._phase_0_initialization()
        send_phase_update("initialization", "completed")
        
        # Phase 1: Foundation Analysis
        send_phase_update("foundation_analysis", "starting", agents=["agent_a", "agent_d"])
        
        # Agent A: JIRA Intelligence
        send_agent_update("agent_a", "starting")
        agent_a_result = await self._execute_agent_a(jira_id)
        send_agent_update("agent_a", "completed", 
                         confidence=agent_a_result.get('confidence'),
                         execution_time=agent_a_result.get('execution_time'))
        
        # Continue for all phases and agents...
```

### 2. **When Webhooks Are Sent**

The webhooks are sent at these exact moments during framework execution:

#### Phase Updates:
- **Initialization starts**: `send_phase_update("initialization", "starting")`
- **Foundation analysis begins**: `send_phase_update("foundation_analysis", "starting")`
- **Deep investigation starts**: `send_phase_update("deep_investigation", "starting")`
- **AI analysis begins**: `send_phase_update("ai_analysis", "starting")`
- **Test generation starts**: `send_phase_update("test_generation", "starting")`
- **Cleanup begins**: `send_phase_update("cleanup", "starting")`

#### Agent Updates:
- **Agent A starts JIRA analysis**: `send_agent_update("agent_a", "starting")`
- **Agent A completes**: `send_agent_update("agent_a", "completed", confidence=85.0)`
- **Agent D starts environment assessment**: `send_agent_update("agent_d", "starting")`
- **Agent D completes**: `send_agent_update("agent_d", "completed", confidence=90.0)`
- And so on for Agents B and C...

## 🎬 Real Example Execution Flow

### User Types in Claude:
```
"Generate test plan for ACM-22079"
```

### What Actually Happens:

1. **Claude Navigation** (from repo root, e.g. `$(git rev-parse --show-toplevel)`):
   ```bash
   cd apps/claude-test-generator
   ```

2. **Framework Execution**:
   ```python
   # Claude internally executes something like:
   from .claude.ai-services.ai_agent_orchestrator import execute_ai_enhanced_framework
   result = await execute_ai_enhanced_framework("ACM-22079", "mist10")
   ```

3. **Webhook Sequence** (happens automatically):
   ```http
   # Phase starts
   POST http://localhost:5678/webhook/framework-status
   {
     "type": "framework_update",
     "jira_ticket": "ACM-22079",
     "phase": "foundation_analysis",
     "status": "starting"
   }

   # Agent A starts
   POST http://localhost:5678/webhook/framework-status
   {
     "type": "agent_update",
     "agent": "agent_a",
     "status": "starting"
   }

   # Agent A completes (45 seconds later)
   POST http://localhost:5678/webhook/framework-status
   {
     "type": "agent_update", 
     "agent": "agent_a",
     "status": "completed",
     "confidence": 85.0,
     "execution_time": 45.2
   }
   ```

4. **n8n Dashboard Updates** (in real-time):
   - Shows "Foundation Analysis - Starting"
   - Shows "Agent A: JIRA Intelligence - Running"
   - Shows "Agent A: JIRA Intelligence - Completed (85% confidence)"

## 🔧 How to Enable This Integration

### Option 1: Modify Your Orchestrator (Recommended)
Add monitoring calls to your existing `ai_agent_orchestrator.py`:

```python
# At the top of ai_agent_orchestrator.py
from n8n_integration.framework_monitor_client import init_framework_monitoring, send_phase_update, send_agent_update

# In your execute_full_framework method
async def execute_full_framework(self, jira_id: str, environment: str = None):
    # Initialize monitoring
    monitor = init_framework_monitoring(jira_id)
    
    # Add webhook calls at key points
    send_phase_update("foundation_analysis", "starting")
    # ... your existing code ...
    send_phase_update("foundation_analysis", "completed")
```

### Option 2: Use the Monitoring Wrapper
Use the `MonitoringEnhancedOrchestrator` I created:

```python
# Instead of directly using PhaseBasedOrchestrator
from n8n_integration.orchestrator_monitoring_integration import create_monitoring_integration

# Create monitored version
orchestrator = create_monitoring_integration()
result = orchestrator.execute_with_monitoring("ACM-22079", "mist10")
```

## 📊 What You'll See

### During Framework Execution:
1. **n8n Dashboard**: Shows real-time workflow execution
2. **Visual Dashboard**: Beautiful animated progress at `http://localhost:8080/ai_framework_dashboard.html`
3. **Slack Notifications**: Updates in your configured channels

### Example Visual Dashboard:
```
🚀 AI Test Generator Monitor
JIRA: ACM-22079 | Progress: 45% | Duration: 02:34

Phase Status:
✅ Initialization     ✅ Foundation Analysis
🔄 Deep Investigation ⏳ AI Analysis
⏳ Test Generation   ⏳ Cleanup

Agent Status:
✅ Agent A: JIRA (85% confidence, 45.2s)
✅ Agent D: Environment (90% confidence, 52.1s)  
🔄 Agent B: Documentation (running...)
⏳ Agent C: GitHub (pending)
```

## 💡 Key Point

The "Python app" is **your existing Claude Test Generator Framework**. The webhook integration doesn't change how you use it - you still just ask Claude to "Generate test plan for ACM-22079" and everything works the same, but now you get real-time visual monitoring!

The webhooks are sent **automatically** from within the framework execution, providing visibility into what's happening behind the scenes when Claude is running your 4-agent investigation.

