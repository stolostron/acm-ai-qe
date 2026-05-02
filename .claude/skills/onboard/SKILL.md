---
name: onboard
description: |
  Interactive onboarding for the AI Systems Suite. Detects current
  environment state, explains the three apps, and guides MCP server
  setup with credential configuration. Run at first clone or to
  verify an existing setup.
when_to_use: |
  When the user says "set up", "onboard", "getting started",
  "configure", "how do I start", or asks how to use this repo.
disable-model-invocation: true
allowed-tools:
  - Read
  - Write
  - Edit
  - AskUserQuestion
  - Bash(python3 *)
  - Bash(node *)
  - Bash(oc *)
  - Bash(gh *)
  - Bash(jq *)
  - Bash(podman *)
  - Bash(which *)
  - Bash(test *)
  - Bash(ls *)
  - Bash(cat *)
  - Bash(grep *)
  - Bash(bash mcp/setup.sh *)
  - Bash(echo *)
  - Bash(command *)
  - Bash(python3 mcp/verify.py *)
metadata:
  author: acm-qe
  version: "1.0.0"
---

# Onboard — AI Systems Suite Setup

Follow these 5 steps in order. Do NOT skip steps. Print status updates to the terminal between each step.

## Step 1: Welcome

Print this to the user:

```
AI Systems Suite — Interactive Setup

This repo provides ACM QE capabilities as portable skills:

  Skills (portable, in .claude/skills/):
  ──────────────────────────────────────
  Shared capabilities:
    acm-jira-client           JIRA ticket investigation interface
    acm-ui-source             ACM Console source code queries
    acm-polarion-client       Polarion test case queries
    acm-neo4j-explorer        RHACM component dependency graph
    acm-cluster-health        12-layer cluster health diagnostics
    acm-knowledge-base        ACM domain knowledge (area architecture, conventions)

  Test case generation:
    acm-test-case-generator   Orchestrator: generate test cases from JIRA tickets
    acm-code-analyzer         PR diff analysis for code changes
    acm-test-case-writer      Test case markdown authoring
    acm-test-case-reviewer    Quality gate with MCP verification

  Hub health diagnostics:
    acm-hub-health-check      Orchestrator: 6-phase cluster health diagnosis
    acm-cluster-remediation   Cluster fix execution with approval gates
    acm-knowledge-learner     Discover and learn from live cluster state

  Z-stream pipeline analysis:
    acm-z-stream-analyzer     Orchestrator: Jenkins failure classification pipeline
    acm-failure-classifier    5-phase classification engine (A through E)
    acm-cluster-investigator  Per-group 12-layer root cause investigation
    acm-data-enricher         Data enrichment (selectors, timeline, knowledge gaps)
    acm-jenkins-client        Jenkins CI interface

  Apps (Claude Code specific, in apps/):
  ───────────────────────────────────────
  z-stream-analysis         Jenkins pipeline failure classification
  acm-hub-health            ACM hub cluster health diagnosis
  test-case-generator       Test case generation (original app)

Checking your environment...
```

For details on each app's architecture and MCP requirements, see [app-summaries.md](app-summaries.md).

## Step 2: Detect Current State

Run these checks (all in parallel where possible) and build a status table:

### Prerequisites

Run each command and record the version or "not found":

```bash
python3 --version 2>&1 || echo "NOT FOUND"
node --version 2>&1 || echo "NOT FOUND"
oc version --client 2>&1 | head -1 || echo "NOT FOUND"
gh --version 2>&1 | head -1 || echo "NOT FOUND"
jq --version 2>&1 || echo "NOT FOUND"
podman --version 2>&1 || echo "NOT FOUND"
```

### MCP Server State

Check root-level and app-level `.mcp.json` files, venvs, and credentials:

```bash
# Root-level MCP config (needed for skills to access MCPs)
test -f .mcp.json && echo "root .mcp.json: configured" || echo "root .mcp.json: MISSING"

# If root .mcp.json exists, count MCP servers in it
test -f .mcp.json && python3 -c "import json; d=json.load(open('.mcp.json')); print(f'root MCP servers: {len(d.get(\"mcpServers\", {}))}')" 2>/dev/null

# App-level MCP configs
test -f apps/z-stream-analysis/.mcp.json && echo "z-stream: configured" || echo "z-stream: not configured"
test -f apps/acm-hub-health/.mcp.json && echo "hub-health: configured" || echo "hub-health: not configured"
test -f apps/test-case-generator/.mcp.json && echo "test-case-gen: configured" || echo "test-case-gen: not configured"

# venvs
test -d mcp/acm-ui-mcp-server/.venv && echo "acm-ui venv: exists" || echo "acm-ui venv: missing"
test -d mcp/.external/jira-mcp-server/.venv && echo "jira venv: exists" || echo "jira venv: missing"
test -d mcp/.external/jenkins-mcp/.venv && echo "jenkins venv: exists" || echo "jenkins venv: missing"

# Credentials (check for real values, not placeholders)
test -f mcp/.external/jira-mcp-server/.env && ! grep -q "PASTE_YOUR" mcp/.external/jira-mcp-server/.env 2>/dev/null && echo "jira creds: configured" || echo "jira creds: missing"
test -f mcp/.external/jenkins-mcp/.env && ! grep -q "PASTE_YOUR" mcp/.external/jenkins-mcp/.env 2>/dev/null && echo "jenkins creds: configured" || echo "jenkins creds: missing"
test -f mcp/polarion/.env && ! grep -q "PASTE_YOUR" mcp/polarion/.env 2>/dev/null && echo "polarion creds: configured" || echo "polarion creds: missing"

# Neo4j container
podman ps --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm && echo "neo4j: running" || echo "neo4j: not running"
```

### Print Status Table

Build and print a formatted status table from the check results:

```
Environment Status
==================
Prerequisites:
  Python:    3.12.4           OK
  Node.js:   v22.17.1         OK
  oc CLI:    4.16.0           OK
  gh CLI:    2.65.0           OK
  jq:        1.7.1            OK
  Podman:    5.3.1            OK (optional)

MCP Servers:
  acm-ui:      venv exists    OK
  jira:        configured     OK
  jenkins:     configured     OK
  polarion:    configured     OK
  neo4j-rhacm: running        OK (optional)
  acm-search:  not deployed   OPTIONAL

Skills Config:
  root .mcp.json:        exists     OK     (8 MCP servers)

App Configs:
  z-stream-analysis:     .mcp.json exists   OK
  acm-hub-health:        .mcp.json exists   OK
  test-case-generator:   .mcp.json exists   OK
```

Mark items as OK, MISSING, or OPTIONAL. Use OK for present, MISSING for required but absent, OPTIONAL for nice-to-have.

## Step 3: Ask What to Set Up

If ALL app `.mcp.json` files exist AND root `.mcp.json` exists AND all required venvs are present, print:

```
All apps and skills are already configured. No setup needed.
```

And stop here (idempotent behavior).

If app configs exist but root `.mcp.json` is MISSING, print:

```
App configs exist but skills don't have MCP access.
Creating root .mcp.json from existing app configs...
```

Then generate the root `.mcp.json` by merging app configs (see Step 4 merge procedure) and proceed to Step 5. Do NOT re-run setup.sh or ask what to configure.

Otherwise (missing app configs or venvs), ask the user what they want to configure. Present the options:

**Skills (portable):**
- Test Case Generator skills (needs: acm-ui, jira, polarion; recommended: neo4j-rhacm; optional: acm-search, acm-kubectl, playwright)
- Hub Health Diagnostic skills (needs: oc CLI; recommended: neo4j-rhacm; optional: acm-search)
- Z-Stream Analysis skills (needs: acm-ui, jira, jenkins, polarion; recommended: neo4j-rhacm; optional: acm-search, acm-kubectl)

**Apps (Claude Code):**
- Z-Stream Analysis (needs: acm-ui, jira, jenkins, polarion, neo4j-rhacm)
- ACM Hub Health (needs: acm-ui, neo4j-rhacm, acm-search)
- Test Case Generator app (needs: acm-ui, jira, polarion, neo4j-rhacm, acm-search, acm-kubectl, playwright)
- All apps

Let the user pick one or more.

Map the selection to a setup.sh app number:
- Hub Health = 1
- Z-Stream = 2
- Test Case Generator (app or skills) = 3
- All = 4

Note: The Test Case Generator skills use the SAME MCPs as the Test Case Generator app. Configuring one configures the other.

## Step 4: Set Up Credentials and Run Setup

For the selected app(s), check which credentials are needed and missing.

### Credential Requirements by App

| App | JIRA | Jenkins | Polarion |
|-----|------|---------|----------|
| Z-Stream | Required | Required | Required |
| Hub Health | - | - | - |
| Test Case Generator | Required | - | Required |

### For each missing credential, ask the user and write the .env file:

**JIRA** (if needed and missing):
Tell the user: "I need your JIRA API credentials. Get a token at https://id.atlassian.com/manage-profile/security/api-tokens"

Ask for:
1. JIRA email (their Atlassian account email)
2. JIRA API token

Write to `mcp/.external/jira-mcp-server/.env`:
```
JIRA_SERVER_URL=https://redhat.atlassian.net
JIRA_ACCESS_TOKEN=<their token>
JIRA_EMAIL=<their email>
JIRA_TIMEOUT=30
JIRA_MAX_RESULTS=100
```

Create the directory first if it doesn't exist: `mkdir -p mcp/.external/jira-mcp-server`

**Jenkins** (if needed and missing):
Tell the user: "I need your Jenkins credentials. Get a token from Jenkins > your username > Configure > API Token."

Ask for:
1. Jenkins username
2. Jenkins API token

Write to `mcp/.external/jenkins-mcp/.env`:
```
JENKINS_USER=<their username>
JENKINS_API_TOKEN=<their token>
```

Create the directory first if it doesn't exist: `mkdir -p mcp/.external/jenkins-mcp`

**Polarion** (if needed and missing):
Tell the user: "I need your Polarion JWT token. Connect to Red Hat VPN, go to https://polarion.engineering.redhat.com/polarion/ > My Account > Personal Access Tokens."

Ask for:
1. Polarion JWT token

Write to `mcp/polarion/.env`:
```
POLARION_BASE_URL=https://polarion.engineering.redhat.com/polarion
POLARION_PAT=<their token>
```

### Run setup.sh

After credentials are in place, run setup.sh with the --app flag:

```bash
bash mcp/setup.sh --app <N>
```

Where N is the mapped number from Step 3. This will:
- Create venvs for MCP servers
- Clone external repos (jira-mcp-server, jenkins-mcp, knowledge-graph, acm-mcp-server)
- Set up Neo4j container if Podman is available
- Generate `.mcp.json` for each selected app

Show the setup.sh output to the user.

### Generate root `.mcp.json`

After `setup.sh` completes (or when the Step 3 short-circuit detects app configs exist but root is missing), merge all app-level MCP configs into a single root `.mcp.json`:

```bash
python3 -c "
import json
from pathlib import Path

merged = {'mcpServers': {}}
for app_config in ['apps/test-case-generator/.mcp.json', 'apps/z-stream-analysis/.mcp.json', 'apps/acm-hub-health/.mcp.json']:
    p = Path(app_config)
    if p.exists():
        data = json.loads(p.read_text())
        merged['mcpServers'].update(data.get('mcpServers', {}))

Path('.mcp.json').write_text(json.dumps(merged, indent=2))
print(f'Root .mcp.json created with {len(merged[\"mcpServers\"])} MCP servers: {list(merged[\"mcpServers\"].keys())}')
"
```

This gives all skills at the repo root access to every MCP server. The root `.mcp.json` is the UNION of all app-level configs — every MCP that any skill might need.

Print: `Root .mcp.json created with N MCP servers.`

## Step 5: Verify and Next Steps

Run the verification script with the app number from Step 3:

```bash
python3 mcp/verify.py --app <N>
```

Where N is the mapped number from Step 3 (1=Hub Health, 2=Z-Stream, 3=Test Case Gen).
If "All apps" was selected, run without `--app` to check everything.

Print the verify.py output to the user.

If any checks show FAIL, explain the specific fix. If only WARN, explain the reduced functionality.

Then print next steps:

```
Setup complete. Next steps:

1. Restart Claude Code to pick up the new MCP configuration

2. Use portable skills (from the repo root):

   Generate a test case:
     claude
     "Generate a test case for ACM-XXXXX"

   Check hub health:
     oc login <hub>
     claude
     "How's my hub health?"

   Analyze Jenkins failures:
     claude
     "Analyze this Jenkins run: <URL>"

3. Or use Claude Code apps (from app directories):

   Z-Stream:     cd apps/z-stream-analysis && claude && /analyze <URL>
   Hub Health:   cd apps/acm-hub-health && claude && /health-check
   TC Generator: cd apps/test-case-generator && claude && /generate ACM-XXXXX

To verify MCP connections: claude mcp list
To re-run this setup: /onboard
```

If any MCP servers failed to install, note them with instructions for manual recovery.
