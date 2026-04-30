# Onboard Skill Update Report

**Purpose:** The onboard skill needs to be updated to configure MCPs at the REPO ROOT level so portable skills (under `.claude/skills/`) can access them. Currently it only configures app-level `.mcp.json` files which skills at the root can't see.

## The Problem

### How Claude Code loads MCP configs

Claude Code reads `.mcp.json` from the **current working directory** when it starts. MCP servers defined in that file become available to all skills and conversations in that session.

### Current state

```
ai_systems_v2/
├── .mcp.json                              <-- DOES NOT EXIST (the problem)
├── .claude/skills/acm-*/                  <-- Skills live here, need MCPs
├── apps/
│   ├── test-case-generator/.mcp.json      <-- EXISTS: acm-ui, jira, polarion, neo4j, acm-search, acm-kubectl, playwright
│   ├── z-stream-analysis/.mcp.json        <-- EXISTS: acm-ui, jira, jenkins, polarion, neo4j
│   └── acm-hub-health/.mcp.json           <-- EXISTS: acm-ui, neo4j, acm-search
```

### What happens

- User runs `claude` from `ai_systems_v2/` root (where skills live)
- Claude Code looks for `.mcp.json` in the current directory -> NOT FOUND
- Skills load (they're under `.claude/skills/`) but have NO MCP access
- Skills degrade gracefully (use curl/gh CLI instead of MCPs) but lose depth
- Meanwhile, the app-level `.mcp.json` files sit unused because Claude Code isn't running from those directories

### What should happen

- User runs `/onboard` from the root
- Onboard detects skills need MCPs and no root `.mcp.json` exists
- Onboard creates/updates a ROOT-LEVEL `.mcp.json` with ALL MCPs needed by installed skills
- Claude Code restarts and all skills have full MCP access

## Current Onboard Behavior (what needs to change)

### Step 2: Detect Current State
**Problem:** Only checks `apps/*/.mcp.json` files. Does NOT check for root `.mcp.json`.
```bash
# CURRENT: only checks app-level configs
test -f apps/z-stream-analysis/.mcp.json && echo "z-stream: configured"
test -f apps/acm-hub-health/.mcp.json && echo "hub-health: configured"
test -f apps/test-case-generator/.mcp.json && echo "test-case-gen: configured"
```
**Fix:** Also check for root `.mcp.json` and report its status separately:
```bash
# ADD: check root-level config
test -f .mcp.json && echo "root .mcp.json: configured" || echo "root .mcp.json: MISSING (skills won't have MCP access)"
```

### Step 3: "All configured" short-circuit
**Problem:** If all three app `.mcp.json` files exist, it says "All apps and skills are already configured. No setup needed." and stops. But skills DON'T have MCP access because there's no root `.mcp.json`.
```
# CURRENT: this triggers even when root .mcp.json is missing
All apps and skills are already configured. No setup needed.
```
**Fix:** The "all configured" check MUST also verify root `.mcp.json` exists. If app configs exist but root doesn't, it should NOT short-circuit. Instead it should offer to create the root config from the existing app configs.

### Step 4: Run setup.sh
**Problem:** `setup.sh` generates `.mcp.json` files inside `apps/*/` directories only. It does not create a root-level `.mcp.json`.
**Fix:** After `setup.sh` runs (or if app configs already exist), merge all app-level MCP configs into a single root `.mcp.json` that contains the UNION of all MCP servers across all apps.

### Step 5: Next Steps
**Problem:** Tells users to `cd apps/<app> && claude`. This is the OLD app-based workflow.
**Fix:** For skills, tell users to just run `claude` from the repo root. The skills are automatically available.

## What the Root `.mcp.json` Should Contain

The union of all MCP servers across all 3 apps. Every MCP that ANY skill might need:

```json
{
  "mcpServers": {
    "acm-ui": { ... },         // Used by: acm-ui-source, acm-code-analyzer, acm-test-case-writer, acm-test-case-reviewer, acm-data-enricher, acm-failure-classifier
    "jira": { ... },           // Used by: acm-jira-client
    "polarion": { ... },       // Used by: acm-polarion-client
    "neo4j-rhacm": { ... },    // Used by: acm-neo4j-explorer
    "jenkins": { ... },        // Used by: acm-jenkins-client
    "acm-search": { ... },     // Used by: acm-cluster-health (optional)
    "acm-kubectl": { ... },    // Used by: acm-cluster-health (optional)
    "playwright": { ... }      // Used by: acm-test-case-generator (optional)
  }
}
```

The server configs can be copied verbatim from any app's `.mcp.json` since they all reference the same MCP server binaries/paths. Where configs differ (e.g., z-stream has jenkins but tc-gen doesn't), include ALL servers from ALL apps.

## Specific Changes Needed

### 1. Step 2: Add root `.mcp.json` detection

In the "MCP Server State" section, ADD this check:
```bash
# Root-level MCP config (needed for skills)
test -f .mcp.json && echo "root .mcp.json: configured" || echo "root .mcp.json: MISSING"
```

In the status table, ADD a new section:
```
Skill Config:
  root .mcp.json:        MISSING    <- skills won't have MCP access
```

### 2. Step 3: Fix short-circuit logic

Change the "all configured" check from:
```
If ALL three app .mcp.json files exist and all required venvs are present
```
To:
```
If ALL three app .mcp.json files exist AND root .mcp.json exists AND all required venvs are present
```

If app configs exist but root doesn't, say:
```
App configs exist but skills don't have MCP access.
Creating root .mcp.json from existing app configs...
```
Then merge the app configs into a root `.mcp.json` and proceed to Step 5.

### 3. Step 4: Generate root `.mcp.json` after setup

After `setup.sh` completes (or after verifying app configs exist), add a new substep:

**Generate root .mcp.json:**
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

This merges all app configs into the root, giving skills access to every MCP server.

### 4. Step 5: Update next steps for skills

Change the next steps from app-centric to skill-centric:

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

   Z-Stream:    cd apps/z-stream-analysis && claude && /analyze <URL>
   Hub Health:  cd apps/acm-hub-health && claude && /health-check
   TC Generator: cd apps/test-case-generator && claude && /generate ACM-XXXXX

To verify MCP connections: claude mcp list
To re-run this setup: /onboard
```

### 5. Step 2 Status Table: Add skills section

Update the printed status table to include:

```
Environment Status
==================
Prerequisites:
  Python:    3.12.4           OK
  Node.js:   v22.17.1         OK
  ...

MCP Servers:
  acm-ui:      venv exists    OK
  jira:        configured     OK
  jenkins:     configured     OK
  polarion:    configured     OK
  neo4j-rhacm: running        OK
  acm-search:  not deployed   OPTIONAL

Skills Config:
  root .mcp.json:        exists     OK     (8 MCP servers)
  -- OR --
  root .mcp.json:        MISSING    NEEDS FIX (skills can't access MCPs)

App Configs:
  z-stream-analysis:     .mcp.json exists   OK
  acm-hub-health:        .mcp.json exists   OK
  test-case-generator:   .mcp.json exists   OK
```

## Summary of Changes

| What | Current | New |
|------|---------|-----|
| Root `.mcp.json` | Not created, not checked | Created by merging app configs |
| Short-circuit logic | Checks only app configs | Checks app configs AND root config |
| MCP config generation | Only writes to `apps/*/` | Also writes merged config to root |
| Next steps | "cd apps/<app> && claude" | Skills from root + apps from app dirs |
| Status table | Only apps section | Apps + Skills Config section |
| Primary workflow | App-centric (cd to app dir) | Skill-centric (run from root) |
