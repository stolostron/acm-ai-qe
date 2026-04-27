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
---

# Onboard — AI Systems Suite Setup

Follow these 5 steps in order. Do NOT skip steps. Print status updates to the terminal between each step.

## Step 1: Welcome

Print this to the user:

```
AI Systems Suite — Interactive Setup

This repo has three apps:

  1. Z-Stream Analysis
     Classify Jenkins pipeline test failures as PRODUCT_BUG,
     AUTOMATION_BUG, or INFRASTRUCTURE using 12-layer diagnostics.
     Usage: cd apps/z-stream-analysis && claude
            /analyze <JENKINS_URL>

  2. ACM Hub Health
     Diagnose ACM hub cluster health with 6-phase investigation.
     Read-only diagnosis; fixes only after approval.
     Usage: cd apps/acm-hub-health && oc login <hub> && claude
            /health-check

  3. Test Case Generator
     Generate Polarion-ready test cases from JIRA tickets using
     a 6-phase subagent pipeline with quality review gate.
     Usage: cd apps/test-case-generator && claude
            /generate ACM-XXXXX

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

Check each app's `.mcp.json` and related venvs/credentials:

```bash
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

App Configs:
  z-stream-analysis:     .mcp.json exists   OK
  acm-hub-health:        .mcp.json exists   OK
  test-case-generator:   .mcp.json exists   OK
```

Mark items as OK, MISSING, or OPTIONAL. Use OK for present, MISSING for required but absent, OPTIONAL for nice-to-have.

## Step 3: Ask Which App(s) to Set Up

If ALL three app `.mcp.json` files exist and all required venvs are present, print:

```
All apps are already configured. No setup needed.
```

And stop here (idempotent behavior).

Otherwise, ask the user which app(s) they want to configure. Present the options:

- Z-Stream Analysis (needs: acm-ui, jira, jenkins, polarion, neo4j-rhacm)
- ACM Hub Health (needs: acm-ui, neo4j-rhacm, acm-search)
- Test Case Generator (needs: acm-ui, jira, polarion, neo4j-rhacm, acm-search, acm-kubectl, playwright)
- All apps

Let the user pick one or more.

Map the selection to a setup.sh app number:
- Hub Health = 1
- Z-Stream = 2
- Test Case Generator = 3
- All = 4

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

## Step 5: Verify and Next Steps

Re-run the state detection from Step 2. Print the updated status table.

Then print next steps:

```
Setup complete. Next steps:

1. Restart Claude Code to pick up the new MCP configuration
2. Navigate to an app directory and start working:

   Z-Stream Analysis:
     cd apps/z-stream-analysis && claude
     /analyze <JENKINS_URL>

   ACM Hub Health:
     cd apps/acm-hub-health && oc login <hub> && claude
     /health-check

   Test Case Generator:
     cd apps/test-case-generator && claude
     /generate ACM-XXXXX

To verify MCP connections: claude mcp list
To re-run this setup: /onboard
```

If any MCP servers failed to install, note them with instructions for manual recovery.
