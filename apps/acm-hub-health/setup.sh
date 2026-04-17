#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up ACM Hub Health Agent..."
echo ""

# 1. Clone rhacm-docs if not present
if [ ! -d "docs/rhacm-docs" ]; then
  echo "Cloning official ACM documentation (rhacm-docs)..."
  mkdir -p docs
  git clone --depth 1 https://github.com/stolostron/rhacm-docs.git docs/rhacm-docs
  echo "Done."
else
  echo "rhacm-docs already present, skipping clone."
fi
echo ""

# 2. Ensure acm-ui MCP server is set up (lives at repo level)
MCP_DIR="$REPO_ROOT/mcp"
ACM_UI_DIR="$MCP_DIR/acm-ui-mcp-server"
if [ -d "$ACM_UI_DIR" ]; then
  if [ ! -d "$ACM_UI_DIR/.venv" ]; then
    echo "Setting up acm-ui MCP server virtual environment..."
    echo "  (at $ACM_UI_DIR)"
    python3 -m venv "$ACM_UI_DIR/.venv"
    "$ACM_UI_DIR/.venv/bin/pip" install -e "$ACM_UI_DIR/" 2>/dev/null || {
      echo "Note: acm-ui MCP install requires the package. Check mcp/acm-ui-mcp-server/README.md"
    }
    echo "Done."
  else
    echo "acm-ui MCP venv already exists, skipping."
  fi
else
  echo "Warning: mcp/acm-ui-mcp-server/ not found at repo root."
  echo "Run 'bash mcp/setup.sh' from the ai_systems_v2 root, or copy the server manually."
fi
echo ""

# 3. Set up acm-search MCP server (on-cluster SSE deployment)
#    The search MCP runs as a pod on the ACM hub cluster, accessed via SSE over
#    an OpenShift route. We use mcp-remote as a stdio-to-SSE bridge so Claude Code
#    can connect to it.

# 3a. Clone the repo (needed for deployment manifests)
SEARCH_MCP_DIR="$MCP_DIR/.external/acm-mcp-server"
if [ ! -d "$SEARCH_MCP_DIR" ]; then
  echo "Cloning acm-mcp-server..."
  mkdir -p "$MCP_DIR/.external"
  git clone --depth 1 https://github.com/stolostron/acm-mcp-server.git "$SEARCH_MCP_DIR"
  echo "Done."
else
  echo "acm-mcp-server already cloned, skipping."
fi

# 3b. Ensure mcp-remote is installed globally (stdio-to-SSE bridge)
MCP_REMOTE_PATH=""
if command -v mcp-remote &> /dev/null; then
  MCP_REMOTE_PATH="$(which mcp-remote)"
  echo "  mcp-remote: found at $MCP_REMOTE_PATH"
else
  echo "  mcp-remote: NOT FOUND -- installing globally..."
  npm install -g mcp-remote 2>/dev/null
  if command -v mcp-remote &> /dev/null; then
    MCP_REMOTE_PATH="$(which mcp-remote)"
    echo "  mcp-remote: installed at $MCP_REMOTE_PATH"
  else
    echo "  WARNING: mcp-remote install failed. Install manually: npm install -g mcp-remote"
  fi
fi

# 3c. Deploy on-cluster if oc is logged in and acm-search namespace doesn't exist
ACM_SEARCH_ROUTE=""
ACM_SEARCH_TOKEN=""
if command -v oc &> /dev/null && oc whoami &> /dev/null; then
  SEARCH_PG_DIR="$SEARCH_MCP_DIR/servers/postgresql"

  # Check if already deployed
  if oc get namespace acm-search &> /dev/null 2>&1; then
    echo "  acm-search namespace exists, skipping deployment."
  else
    echo "  Deploying acm-search MCP server on-cluster..."
    if [ -f "$SEARCH_PG_DIR/scripts/create-secret.sh" ]; then
      (cd "$SEARCH_PG_DIR" && bash scripts/create-secret.sh 2>&1) || {
        echo "  WARNING: create-secret.sh failed. You may need to deploy manually."
      }
    fi
    if [ -f "$SEARCH_PG_DIR/Makefile" ]; then
      (cd "$SEARCH_PG_DIR" && make deploy-prebuilt 2>&1) || {
        echo "  WARNING: deploy-prebuilt failed. Check 'oc get pods -n acm-search'."
      }
    fi
  fi

  # Extract route URL
  ACM_SEARCH_ROUTE=$(oc get route -n acm-search -o jsonpath='{.items[0].spec.host}' 2>/dev/null || true)
  if [ -n "$ACM_SEARCH_ROUTE" ]; then
    echo "  acm-search route: $ACM_SEARCH_ROUTE"
  else
    echo "  WARNING: No route found in acm-search namespace."
    echo "           Deploy manually: cd $SEARCH_PG_DIR && bash scripts/create-secret.sh && make deploy-prebuilt"
  fi

  # Extract service account token
  ACM_SEARCH_TOKEN=$(oc get secret acm-search-client-token -n acm-search -o jsonpath='{.data.token}' 2>/dev/null | base64 -d || true)
  if [ -n "$ACM_SEARCH_TOKEN" ]; then
    echo "  acm-search token: extracted"
  else
    echo "  WARNING: Could not extract acm-search-client-token."
    echo "           Check: oc get secret -n acm-search"
  fi
else
  echo "  WARNING: oc not logged in. Skipping on-cluster deployment."
  echo "           Log in first, then re-run: oc login <hub-api-url> && bash setup.sh"
fi
echo ""

# 4. Generate .mcp.json (acm-hub-health needs acm-ui + neo4j-rhacm + acm-search)
echo "Generating .mcp.json..."

# Build acm-search config dynamically based on what we discovered
ACM_SEARCH_JSON=""
if [ -n "$ACM_SEARCH_ROUTE" ] && [ -n "$ACM_SEARCH_TOKEN" ] && [ -n "$MCP_REMOTE_PATH" ]; then
  ACM_SEARCH_JSON=$(python3 -c "
import json
cfg = {
    'command': '$MCP_REMOTE_PATH',
    'args': [
        'https://${ACM_SEARCH_ROUTE}/sse',
        '--header', 'Authorization: Bearer ${ACM_SEARCH_TOKEN}',
        '--transport', 'sse-only'
    ],
    'env': {'NODE_TLS_REJECT_UNAUTHORIZED': '0'},
    'timeout': 90
}
print(json.dumps(cfg))
")
else
  echo "  NOTE: acm-search MCP not fully configured (missing route, token, or mcp-remote)."
  echo "        The .mcp.json will include a placeholder. Re-run setup.sh after deploying."
  ACM_SEARCH_JSON='{"command": "echo", "args": ["acm-search not configured -- re-run setup.sh after deploying on-cluster"], "timeout": 10}'
fi

python3 -c "
import json, sys

acm_search = json.loads(sys.argv[1])

config = {
    'mcpServers': {
        'acm-ui': {
            'command': '../../mcp/acm-ui-mcp-server/.venv/bin/python',
            'args': ['-m', 'acm_ui_mcp_server.main'],
            'cwd': '../../mcp/acm-ui-mcp-server',
            'timeout': 30
        },
        'neo4j-rhacm': {
            'command': 'uvx',
            'args': ['--with', 'fastmcp<3', 'mcp-neo4j-cypher',
                     '--db-url', 'bolt://localhost:7687',
                     '--username', 'neo4j', '--password', 'rhacmgraph',
                     '--read-only'],
            'timeout': 60
        },
        'acm-search': acm_search
    }
}

with open('$SCRIPT_DIR/.mcp.json', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "$ACM_SEARCH_JSON"

echo "Done."
echo ""

# 5. Verify prerequisites
echo "Checking prerequisites..."

if command -v oc &> /dev/null; then
  echo "  oc CLI: found"
else
  echo "  oc CLI: NOT FOUND - install from https://mirror.openshift.com/pub/openshift-v4/clients/ocp/latest/"
fi

if command -v claude &> /dev/null; then
  echo "  claude CLI: found"
else
  echo "  claude CLI: NOT FOUND - install from https://docs.anthropic.com/en/docs/claude-code/getting-started"
fi

if command -v uvx &> /dev/null; then
  echo "  uvx: found"
else
  echo "  uvx: NOT FOUND - install: pip install uv (needed for neo4j-rhacm MCP)"
fi

if command -v node &> /dev/null; then
  echo "  node: found ($(node --version))"
else
  echo "  node: NOT FOUND - install Node.js (needed for mcp-remote)"
fi

if command -v mcp-remote &> /dev/null; then
  echo "  mcp-remote: found at $(which mcp-remote)"
else
  echo "  mcp-remote: NOT FOUND - install: npm install -g mcp-remote (needed for acm-search MCP)"
fi

# Check acm-search on-cluster deployment
if command -v oc &> /dev/null && oc whoami &> /dev/null 2>&1; then
  if oc get namespace acm-search &> /dev/null 2>&1; then
    ROUTE_HOST=$(oc get route -n acm-search -o jsonpath='{.items[0].spec.host}' 2>/dev/null || true)
    if [ -n "$ROUTE_HOST" ]; then
      echo "  acm-search: deployed (route: $ROUTE_HOST)"
    else
      echo "  acm-search: namespace exists but no route found"
    fi
  else
    echo "  acm-search: NOT DEPLOYED on cluster - re-run setup.sh to deploy"
  fi
fi

# Check if Neo4j knowledge graph container is available
if command -v podman &> /dev/null; then
  if podman ps --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
    echo "  neo4j-rhacm: container running"
  elif podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
    echo "  neo4j-rhacm: container stopped - run: podman start neo4j-rhacm"
  else
    echo "  neo4j-rhacm: NOT SET UP - run 'bash mcp/setup.sh' from repo root to create the container"
    echo "               (optional: hub health works without it, using curated dependency chains)"
  fi
else
  echo "  neo4j-rhacm: podman not found - install podman, then run 'bash mcp/setup.sh' from repo root"
  echo "               (optional: hub health works without it, using curated dependency chains)"
fi

echo ""
echo "Setup complete."
echo ""
echo "Usage:"
echo "  oc login <hub-api-url> -u <user> -p <password>"
echo "  claude"
echo ""
echo "Then try: /health-check, /sanity, or ask in natural language"
