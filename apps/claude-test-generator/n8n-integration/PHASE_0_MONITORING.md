# Phase 0 Monitoring Integration

## 🔄 Phase 0: Version Intelligence & Framework Initialization

Phase 0 is **not empty** - it performs critical initialization that should be monitored!

## 📋 What Actually Happens in Phase 0

### 1. **Version Intelligence Service**
- Analyzes JIRA ticket for version compatibility
- Performs foundation context analysis
- Creates baseline for all agents

### 2. **Framework Initialization**
- Creates run directory structure
- Generates execution metadata
- Sets up logging and enforcement
- Prepares agent inheritance context

### 3. **Environment Assessment**
- Establishes environment baseline
- Validates infrastructure readiness
- Prepares deployment context

## 📡 Phase 0 Webhook Monitoring

### Integration Points in Your Framework:

```python
# In version_intelligence_service.py - execute_phase_0()
def execute_phase_0(jira_id: str, environment: str = None) -> FoundationContext:
    """Execute Phase 0 - Version Intelligence analysis"""
    
    # 🚀 WEBHOOK: Phase 0 starts
    send_phase_update("initialization", "starting", 
                     agents=[], 
                     metrics={"phase": "version_intelligence"})
    
    logger.info(f"🚀 Executing Phase 0 for {jira_id}")
    
    try:
        service = VersionIntelligenceService()
        
        # 📊 WEBHOOK: Version analysis starting
        send_phase_update("initialization", "running",
                         agents=[],
                         metrics={"step": "version_analysis", "jira_id": jira_id})
        
        foundation_context = service.analyze_version_gap(jira_id, environment)
        
        # Validate readiness for agent inheritance
        if not foundation_context.is_ready_for_agent_inheritance():
            # 🚨 WEBHOOK: Validation failed
            send_error("Phase 0 validation failed - Foundation context not ready", 
                      phase="initialization",
                      error_details={"validation_results": foundation_context.validation_results})
            raise VersionIntelligenceError(...)
        
        # ✅ WEBHOOK: Phase 0 completed successfully
        send_phase_update("initialization", "completed",
                         agents=[],
                         metrics={
                             "foundation_context_ready": True,
                             "version_compatibility": foundation_context.version_status,
                             "execution_time": phase_duration
                         })
        
        logger.info(f"✅ Phase 0 completed successfully for {jira_id}")
        return foundation_context
        
    except Exception as e:
        # 🚨 WEBHOOK: Phase 0 failed
        send_error(f"Phase 0 execution failed: {str(e)}", 
                  phase="initialization",
                  error_details={"exception_type": type(e).__name__})
        raise
```

## 📊 Phase 0 Webhook Data Examples

### Phase 0 Start:
```http
POST http://localhost:5678/webhook/framework-status
{
  "timestamp": "2025-01-03T15:32:00.000Z",
  "type": "framework_update",
  "jira_ticket": "ACM-22079",
  "phase": "initialization",
  "status": "starting",
  "agents": [],
  "metrics": {
    "phase": "version_intelligence",
    "step": "framework_setup"
  }
}
```

### Version Analysis Running:
```http
POST http://localhost:5678/webhook/framework-status
{
  "timestamp": "2025-01-03T15:32:05.123Z", 
  "type": "framework_update",
  "jira_ticket": "ACM-22079",
  "phase": "initialization",
  "status": "running",
  "agents": [],
  "metrics": {
    "step": "version_analysis",
    "jira_id": "ACM-22079",
    "progress": "analyzing_version_compatibility"
  }
}
```

### Phase 0 Success:
```http
POST http://localhost:5678/webhook/framework-status
{
  "timestamp": "2025-01-03T15:32:18.456Z",
  "type": "framework_update", 
  "jira_ticket": "ACM-22079",
  "phase": "initialization",
  "status": "completed",
  "agents": [],
  "metrics": {
    "foundation_context_ready": true,
    "version_compatibility": "compatible",
    "execution_time": 18.4,
    "run_directory": "/path/to/runs/ACM-22079-20250103-153200"
  }
}
```

### Phase 0 Error Example:
```http
POST http://localhost:5678/webhook/framework-error
{
  "timestamp": "2025-01-03T15:32:10.789Z",
  "type": "error_alert",
  "jira_ticket": "ACM-22079", 
  "phase": "initialization",
  "error_message": "JIRA ticket ACM-22079 not found or inaccessible",
  "error_details": {
    "exception_type": "JIRAAccessError",
    "step": "version_analysis"
  }
}
```

## 🎨 Dashboard Visualization for Phase 0

### Visual Dashboard Shows:
```
🚀 AI Test Generator Monitor
JIRA: ACM-22079 | Progress: 5% | Duration: 00:18

Phase Status:
🔄 Initialization (Version Intelligence Analysis)
⏳ Foundation Analysis (waiting...)
⏳ Deep Investigation (waiting...)
⏳ AI Analysis (waiting...)
⏳ Test Generation (waiting...)
⏳ Cleanup (waiting...)

Current Activity:
📋 Version Intelligence Service
🔍 Analyzing JIRA ticket compatibility
⚙️ Setting up foundation context
```

### n8n Workflow Processing:
1. **Receives Phase 0 webhook**
2. **Routes to Phase 0 handler** (no agents involved)
3. **Updates dashboard** with initialization progress
4. **Shows version analysis status**
5. **Displays foundation context creation**

## 🔧 Key Differences from Agent Phases

### Phase 0 Characteristics:
- **No agents** - but has services (Version Intelligence Service)
- **Foundation setup** - creates context for all agents
- **Critical validation** - must succeed for framework to continue
- **Service-based monitoring** - tracks services instead of agents

### Webhook Pattern:
```python
# Phase 0: Service-based monitoring
send_phase_update("initialization", "starting", agents=[])
send_phase_update("initialization", "running", metrics={"service": "version_intelligence"})
send_phase_update("initialization", "completed", metrics={"foundation_ready": True})

# Phase 1+: Agent-based monitoring  
send_phase_update("foundation_analysis", "starting", agents=["agent_a", "agent_d"])
send_agent_update("agent_a", "starting")
send_agent_update("agent_a", "completed", confidence=85.0)
```

## 💡 Why Phase 0 Monitoring Matters

1. **Early Error Detection**: Catch JIRA access issues immediately
2. **Setup Validation**: Ensure foundation context is properly created
3. **Progress Visibility**: Show that framework is actively initializing
4. **Debugging**: Track version intelligence analysis steps
5. **Performance**: Monitor initialization time

Phase 0 is the **foundation** of your entire framework - monitoring it ensures you catch issues before agents even start running!

