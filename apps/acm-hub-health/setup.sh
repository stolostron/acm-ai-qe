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

# 3. Generate .mcp.json (acm-hub-health only needs acm-ui)
# Use relative paths from the app directory for portability
echo "Generating .mcp.json..."
cat > "$SCRIPT_DIR/.mcp.json" <<'MCPEOF'
{
  "mcpServers": {
    "acm-ui": {
      "command": "../../mcp/acm-ui-mcp-server/.venv/bin/python",
      "args": ["-m", "acm_ui_mcp_server.main"],
      "cwd": "../../mcp/acm-ui-mcp-server",
      "timeout": 30
    }
  }
}
MCPEOF
echo "Done."
echo ""

# 4. Verify prerequisites
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

echo ""
echo "Setup complete."
echo ""
echo "Usage:"
echo "  oc login <hub-api-url> -u <user> -p <password>"
echo "  claude"
echo ""
echo "Then try: /health-check, /sanity, or ask in natural language"
