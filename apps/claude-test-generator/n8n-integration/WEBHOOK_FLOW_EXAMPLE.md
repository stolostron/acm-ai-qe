# Webhook Data Flow Example

## 🔄 Step-by-Step Webhook Processing

### Step 1: Python App Sends Webhook
```python
# In your framework execution
from framework_monitor_client import send_phase_update

# This line in your code:
send_phase_update("foundation_analysis", "starting", agents=["agent_a", "agent_d"])

# Triggers this HTTP request:
POST http://localhost:5678/webhook/framework-status
{
  "timestamp": "2025-01-03T15:32:18.123Z",
  "type": "framework_update",
  "jira_ticket": "ACM-22079",
  "phase": "foundation_analysis", 
  "status": "starting",
  "agents": ["agent_a", "agent_d"]
}
```

### Step 2: n8n Webhook Node Receives Data
The webhook node in n8n immediately receives this JSON and makes it available as `$json`:

```javascript
// Available in n8n as:
$json.timestamp     // "2025-01-03T15:32:18.123Z"
$json.type          // "framework_update"
$json.jira_ticket   // "ACM-22079"
$json.phase         // "foundation_analysis"
$json.status        // "starting"
$json.agents        // ["agent_a", "agent_d"]
```

### Step 3: IF Node Routes Data
The IF node checks the type and routes accordingly:

```javascript
// IF condition:
$json.type === "framework_update" // TRUE → goes to Framework Update branch
$json.type === "agent_update"     // FALSE → skips this branch
```

### Step 4: Data Processing Node Enriches Data
```javascript
// The processing node adds:
const enrichedData = {
  ...data,
  progress_percentage: 30,  // Calculated based on phase
  phase_display: "FOUNDATION ANALYSIS",
  timestamp_formatted: "3:32:18 PM",
  execution_id: "ACM-22079-20250103-153218"
};

// Stores in static data for persistence:
staticData.executions[execution_id].phases["foundation_analysis"] = {
  status: "starting",
  timestamp: "2025-01-03T15:32:18.123Z",
  agents: ["agent_a", "agent_d"]
};
```

### Step 5: Merge Node Combines Data
The merge node waits for both framework and agent updates, then combines them:

```javascript
// When both branches have data:
{
  framework_data: { phase: "foundation_analysis", status: "starting" },
  agent_data: { agent: "agent_a", status: "running" },
  combined_state: "Phase starting with agent running"
}
```

### Step 6: Dashboard Generator Creates Visual Data
```javascript
// Generates dashboard data:
{
  execution_id: "ACM-22079-20250103-153218",
  jira_ticket: "ACM-22079",
  overall_progress: 30,
  phases: {
    foundation_analysis: { status: "starting", icon: "🔄", color: "#ff9800" }
  },
  agents: {
    agent_a: { status: "running", confidence: null, icon: "⚡" }
  }
}
```

### Step 7: Multiple Outputs
The dashboard data simultaneously:
1. **Updates Slack**: Sends notification to #ai-test-generator
2. **Updates Dashboard**: Writes HTML to `/tmp/ai_framework_dashboard.html`
3. **Logs Metrics**: Stores performance data

## 🎯 Real-Time Comparison

### Old System (File Polling):
```bash
# n8n checks every 2 seconds:
00:00 → Check files → No change
00:02 → Check files → No change  
00:04 → Check files → Found change! → Update dashboard
# Total delay: 0-4 seconds
```

### New System (Webhooks):
```bash
# Instant when event happens:
00:00.123 → Python sends webhook
00:00.145 → n8n receives data
00:00.167 → Dashboard updated
# Total delay: ~50ms
```

## 📡 Webhook URLs in Your Environment

After running the setup script, these URLs become active:

```bash
# Framework status updates
curl -X POST http://localhost:5678/webhook/framework-status \
  -H "Content-Type: application/json" \
  -d '{"type":"framework_update","phase":"test","status":"starting"}'

# Error notifications  
curl -X POST http://localhost:5678/webhook/framework-error \
  -H "Content-Type: application/json" \
  -d '{"type":"error_alert","error_message":"Test error"}'

# Visual dashboard updates
curl -X POST http://localhost:5678/webhook/visual-status \
  -H "Content-Type: application/json" \
  -d '{"type":"visual_update","jira_ticket":"TEST-001"}'
```

## 🔧 Configuration in Your Python App

Your existing monitoring client already supports this! Just set the environment variable:

```bash
export N8N_WEBHOOK_URL="http://localhost:5678/webhook"
```

The client automatically constructs the full URLs:
- Status: `${N8N_WEBHOOK_URL}/framework-status`
- Errors: `${N8N_WEBHOOK_URL}/framework-error`

## 🎨 Visual Dashboard Updates

When the visual webhook receives data, it:

1. **Updates Static State**: Stores current execution state
2. **Generates HTML**: Creates beautiful animated dashboard
3. **Serves File**: Makes it available at `http://localhost:8080/ai_framework_dashboard.html`
4. **Auto-Refresh**: Browser refreshes every 5 seconds to show latest state

The result is a real-time, animated dashboard that shows exactly what's happening in your framework as it happens!

