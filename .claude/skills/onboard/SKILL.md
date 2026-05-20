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
    acm-cluster-health        12-layer cluster health diagnostics
    acm-knowledge-base        ACM domain knowledge (area architecture, conventions)
    acm-jenkins-client        Jenkins CI interface

  Test case generation:
    acm-test-case-generator   Orchestrator: generate test cases from JIRA tickets
    acm-qe-code-analyzer         PR diff analysis for code changes
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
test -d mcp/acm-source-mcp-server/.venv && echo "acm-source venv: exists" || echo "acm-source venv: missing"
test -d mcp/.external/jira-mcp-server/.venv && echo "jira venv: exists" || echo "jira venv: missing"
test -d mcp/.external/jenkins-mcp/.venv && echo "jenkins venv: exists" || echo "jenkins venv: missing"

# Credentials (check for real values, not placeholders)
test -f mcp/.external/jira-mcp-server/.env && ! grep -q "PASTE_YOUR" mcp/.external/jira-mcp-server/.env 2>/dev/null && echo "jira creds: configured" || echo "jira creds: missing"
test -f mcp/.external/jenkins-mcp/.env && ! grep -q "PASTE_YOUR" mcp/.external/jenkins-mcp/.env 2>/dev/null && echo "jenkins creds: configured" || echo "jenkins creds: missing"
test -f mcp/polarion/.env && ! grep -q "PASTE_YOUR" mcp/polarion/.env 2>/dev/null && echo "polarion creds: configured" || echo "polarion creds: missing"

# Neo4j container
podman ps --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm && echo "neo4j: running" || echo "neo4j: not running"

# acm-search and acm-kubectl (deployed per-cluster, not required during onboarding)
# Check command != 'echo' to distinguish real config from placeholder
test -f .mcp.json && python3 -c "import json; d=json.load(open('.mcp.json')); s=d.get('mcpServers',{}).get('acm-search',{}); print('acm-search: deployed' if s and s.get('command','')!='echo' else 'acm-search: not deployed (deploy per-cluster when needed)')" 2>/dev/null || echo "acm-search: not deployed (deploy per-cluster when needed)"
test -f .mcp.json && python3 -c "import json; d=json.load(open('.mcp.json')); s=d.get('mcpServers',{}).get('acm-kubectl',{}); print('acm-kubectl: configured' if s and s.get('command','')!='echo' else 'acm-kubectl: not configured (needs oc login)')" 2>/dev/null || echo "acm-kubectl: not configured (needs oc login)"

# Playwright (npm package, needs Node.js)
which npx >/dev/null 2>&1 && echo "playwright: available" || echo "playwright: not available (needs Node.js)"

# oc login status (needed for acm-search and acm-kubectl deployment)
oc whoami 2>/dev/null && echo "oc login: active" || echo "oc login: not active"
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
  Podman:    5.3.1            OK

MCP Servers:
  acm-source:  venv exists    OK
  jira:        configured     OK
  jenkins:     configured     OK
  polarion:    configured     OK
  neo4j-rhacm: running        OK
  acm-search:  deployed       OK        (or: not deployed — deploy per-cluster when needed)
  acm-kubectl: configured     OK        (or: needs oc login)
  playwright:  configured     OK        (or: not available — needs Node.js)

Skills Config:
  root .mcp.json:        exists     OK     (8 MCP servers)

App Configs:
  z-stream-analysis:     .mcp.json exists   OK
  acm-hub-health:        .mcp.json exists   OK
  test-case-generator:   .mcp.json exists   OK
```

Mark items as OK or MISSING. Use OK for present, MISSING for required but absent.
Exception: acm-search and acm-kubectl are cluster-dependent — show their actual state without marking as MISSING. These are deployed per-cluster when needed, not required during onboarding.

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

Otherwise (missing app configs or venvs), ask the user what they want to configure.

### Level 1: Apps or Skills?

Ask: "How do you want to use this repo?"

1. **Apps** — Work with a specific application (z-stream analysis, hub health, test case generator)
2. **Skills** — Use portable skills from the repo root

### Level 2a: If the user chose Apps

Show the app selection:

1. **ACM Hub Health** — cluster diagnostics (needs: acm-source, neo4j-rhacm, acm-search)
2. **Z-Stream Analysis** — pipeline failure classification (needs: acm-source, jira, jenkins, polarion, neo4j-rhacm)
3. **Test Case Generator** — Polarion test cases from JIRA (needs: acm-source, jira, polarion, neo4j-rhacm, acm-search, acm-kubectl, playwright)
4. **All apps**

Map the selection to a setup.sh app number:
- Hub Health = 1
- Z-Stream = 2
- Test Case Generator = 3
- All = 4

### Level 2b: If the user chose Skills

Skills can invoke any MCP depending on the workflow, so all servers will be configured. Map directly to `--app 4` (all MCPs). Tell the user: "Skills use different MCP servers depending on the workflow. Setting up all servers so every skill works."

## Step 4: Collect Credentials, Run Setup, Then Write Credential Files

For the selected app(s), check which credentials are needed and missing.

### Credential Requirements by App

| App | JIRA | Jenkins | Polarion |
|-----|------|---------|----------|
| Z-Stream | Required | Required | Required |
| Hub Health | - | - | - |
| Test Case Generator | Required | - | Required |

### Collect credentials from the user (do NOT write files yet):

**JIRA** (if needed and missing):
Tell the user: "I need your JIRA API credentials. Get a token at https://id.atlassian.com/manage-profile/security/api-tokens"

Ask for:
1. JIRA email (their Atlassian account email)
2. JIRA API token

Hold these values in memory — they will be written after setup.sh runs.

**Jenkins** (if needed and missing):
Tell the user: "I need your Jenkins credentials. Get a token from Jenkins > your username > Configure > API Token."

Ask for:
1. Jenkins username
2. Jenkins API token

Hold these values in memory — they will be written after setup.sh runs.

**Polarion** (if needed and missing):
Tell the user: "I need your Polarion JWT token. Connect to Red Hat VPN, go to https://polarion.engineering.redhat.com/polarion/ > My Account > Personal Access Tokens."

Ask for:
1. Polarion JWT token

Hold this value in memory — it will be written after setup.sh runs.

### Run setup.sh (clones repos, creates venvs)

Run setup.sh:

```bash
bash mcp/setup.sh --app <N> --no-creds
```

Where N is the mapped number from Step 3. This will:
- Clone external repos into `mcp/.external/` (jira: [atifshafi/jira-mcp-server@feat/redhat-fields](https://github.com/atifshafi/jira-mcp-server/tree/feat/redhat-fields), jenkins-mcp, knowledge-graph, acm-mcp-server)
- Create venvs and install JIRA with `pip install -e '.[dev]'` + `scripts/verify-startup.sh`
- Set up Neo4j container if Podman is available
- Generate `.mcp.json` for each selected app

Show the setup.sh output to the user.

### Write credential files (AFTER setup.sh completes)

Now that `setup.sh` has cloned the repos and created the directories, write the `.env` files:

**JIRA** (if collected above):
Write to `mcp/.external/jira-mcp-server/.env`:
```
JIRA_SERVER_URL=https://redhat.atlassian.net
JIRA_ACCESS_TOKEN=<their token>
JIRA_EMAIL=<their email>
JIRA_TIMEOUT=30
JIRA_MAX_RESULTS=100
```

**Jenkins** (if collected above):
Write to `mcp/.external/jenkins-mcp/.env`:
```
JENKINS_USER=<their username>
JENKINS_API_TOKEN=<their token>
```

**Polarion** (if collected above):
Write to `mcp/polarion/.env`:
```
POLARION_BASE_URL=https://polarion.engineering.redhat.com/polarion
POLARION_PAT=<their token>
```

### Regenerate .mcp.json with credentials

The initial `setup.sh --no-creds` run generated `.mcp.json` files before credentials existed.
Now that `.env` files have real values, re-run setup.sh to regenerate `.mcp.json` with credentials injected:

```bash
bash mcp/setup.sh --app <N>
```

Use the same app number from Step 3. This time credentials exist in `.env` files, so setup.sh will find them and skip prompting. Repos and venvs are already set up, so this run is fast — it just regenerates `.mcp.json` files with correct credential env blocks.

Show the output to the user.

### Generate root `.mcp.json`

This merge must run AFTER the setup.sh regeneration pass above, because setup.sh (including deploy-acm-search.sh if oc is logged in) updates app-level `.mcp.json` files with credentials and live acm-search config.

Merge all app-level MCP configs into a single root `.mcp.json`:

```bash
python3 -c "
import json, sys
from pathlib import Path

app_configs = ['apps/test-case-generator/.mcp.json', 'apps/z-stream-analysis/.mcp.json', 'apps/acm-hub-health/.mcp.json']
missing = [c for c in app_configs if not Path(c).exists()]
if missing:
    print(f'WARNING: Missing app configs: {missing}')
    print('Root .mcp.json will be incomplete. Re-run: bash mcp/setup.sh --app 4')

merged = {'mcpServers': {}}
for app_config in app_configs:
    p = Path(app_config)
    if p.exists():
        data = json.loads(p.read_text())
        merged['mcpServers'].update(data.get('mcpServers', {}))

if not merged['mcpServers']:
    print('ERROR: No MCP servers found in any app config. Cannot create root .mcp.json.')
    sys.exit(1)

Path('.mcp.json').write_text(json.dumps(merged, indent=2))
print(f'Root .mcp.json created with {len(merged[\"mcpServers\"])} MCP servers: {list(merged[\"mcpServers\"].keys())}')
"
```

This gives all skills at the repo root access to every MCP server. The root `.mcp.json` is the UNION of all app-level configs — every MCP that any skill might need.

Print: `Root .mcp.json created with N MCP servers.`

Note: acm-search is a cluster-side MCP deployed per-cluster as needed — it is NOT required during onboarding. If `oc` happens to be logged into an ACM hub, setup.sh deploys it automatically. If not, setup.sh skips it with instructions for later. When a skill or app needs acm-search at runtime and it's not deployed, it will prompt the user to log in and run `bash mcp/deploy-acm-search.sh`. If the user rotates to a different cluster, they re-run the deploy script on the new cluster.

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
