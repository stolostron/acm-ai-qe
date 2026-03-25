#!/usr/bin/env bash
#
# MCP Server Setup for Z-Stream Analysis
#
# Sets up the MCP servers used by the z-stream-analysis app.
# Run from the repository root: bash mcp/setup.sh
#
# Servers set up by this script:
#   [Required] acm-ui     -- Search ACM Console & Fleet Virt source code via GitHub
#   [Required] jira       -- Search/create JIRA issues for bug correlation
#   [Optional] neo4j-rhacm -- RHACM component dependency graph (needs Podman)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_DIR="$REPO_ROOT/apps/z-stream-analysis"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

# -----------------------------------------------
# Prerequisites Check
# -----------------------------------------------
echo ""
echo "============================================"
echo "  MCP Server Setup for Z-Stream Analysis"
echo "============================================"
echo ""

info "Checking prerequisites..."

# Python
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    ok "Python $PY_VERSION"
else
    fail "Python 3.10+ is required. Install: brew install python3"
    exit 1
fi

# gh CLI
if command -v gh &>/dev/null; then
    ok "GitHub CLI (gh) installed"
    if gh auth status &>/dev/null 2>&1; then
        ok "GitHub CLI authenticated"
    else
        warn "GitHub CLI not authenticated"
        echo ""
        echo "  You need to authenticate with GitHub to use the ACM UI MCP server."
        echo "  This gives the server read access to stolostron/console and other repos."
        echo ""
        read -p "  Run 'gh auth login' now? [Y/n] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            gh auth login
        else
            warn "Skipping gh auth. ACM UI MCP will not work until you run: gh auth login"
        fi
    fi
else
    fail "GitHub CLI (gh) is required."
    echo "  Install: brew install gh  (macOS) or sudo dnf install gh (Fedora/RHEL)"
    echo "  Then run: gh auth login"
    exit 1
fi

echo ""

# -----------------------------------------------
# [1] ACM UI MCP Server (Required)
# -----------------------------------------------
echo "--------------------------------------------"
echo "  [1/3] ACM UI MCP Server (Required)"
echo "--------------------------------------------"
echo ""
echo "  What: Searches ACM Console and Fleet Virtualization source code on GitHub."
echo "  Used for: Finding UI selectors, component source, translations during analysis."
echo ""

ACM_UI_DIR="$SCRIPT_DIR/acm-ui-mcp-server"

if python3 -c "import acm_ui_mcp_server" 2>/dev/null; then
    ok "Already installed"
else
    info "Installing dependencies..."
    pip3 install -r <(python3 -c "
import tomllib, pathlib
data = tomllib.loads(pathlib.Path('$ACM_UI_DIR/pyproject.toml').read_text())
for dep in data.get('project', {}).get('dependencies', []):
    print(dep)
") --quiet 2>/dev/null || pip3 install mcp pydantic pydantic-settings python-dotenv --quiet
    ok "Dependencies installed"
    info "Note: The .mcp.json cwd field handles module discovery at runtime."
fi

echo ""

# -----------------------------------------------
# [2] JIRA MCP Server (Required)
# -----------------------------------------------
echo "--------------------------------------------"
echo "  [2/3] JIRA MCP Server (Required)"
echo "--------------------------------------------"
echo ""
echo "  What: Searches and manages JIRA issues."
echo "  Used for: Finding related bugs, reading feature stories during analysis."
echo ""

JIRA_DIR="$SCRIPT_DIR/jira-mcp-server"

if python3 -c "import jira_mcp_server" 2>/dev/null; then
    ok "Already installed"
else
    info "Installing dependencies..."
    pip3 install -r <(python3 -c "
import tomllib, pathlib
data = tomllib.loads(pathlib.Path('$JIRA_DIR/pyproject.toml').read_text())
for dep in data.get('project', {}).get('dependencies', []):
    print(dep)
") --quiet 2>/dev/null || pip3 install jira mcp pydantic pydantic-settings python-dotenv --quiet
    ok "Dependencies installed"
fi

# Check for .env
JIRA_ENV="$JIRA_DIR/.env"
if [ ! -f "$JIRA_ENV" ]; then
    echo ""
    info "JIRA credentials needed."
    echo ""
    echo "  The JIRA MCP server connects to Jira Cloud using basic auth (email + API token)."
    echo ""
    echo "  To get your API token:"
    echo "    1. Go to https://id.atlassian.com/manage-profile/security/api-tokens"
    echo "    2. Click 'Create API token'"
    echo "    3. Copy the token"
    echo ""

    read -p "  JIRA Server URL [https://redhat.atlassian.net]: " JIRA_URL
    JIRA_URL="${JIRA_URL:-https://redhat.atlassian.net}"

    read -p "  JIRA Email (your Atlassian account email): " JIRA_EMAIL_INPUT

    read -p "  JIRA API Token: " JIRA_TOKEN
    if [ -z "$JIRA_TOKEN" ]; then
        warn "No token provided. Creating .env with placeholder."
        JIRA_TOKEN="PASTE_YOUR_API_TOKEN_HERE"
    fi

    cat > "$JIRA_ENV" <<EOF
JIRA_SERVER_URL=$JIRA_URL
JIRA_ACCESS_TOKEN=$JIRA_TOKEN
JIRA_EMAIL=$JIRA_EMAIL_INPUT
JIRA_TIMEOUT=30
JIRA_MAX_RESULTS=100
EOF
    ok "Created $JIRA_ENV"
    echo "  Edit this file later to update credentials: $JIRA_ENV"
else
    ok "Credentials file exists: $JIRA_ENV"
fi

echo ""

# -----------------------------------------------
# [3] Neo4j RHACM Knowledge Graph (Optional)
# -----------------------------------------------
echo "--------------------------------------------"
echo "  [3/3] Neo4j RHACM Knowledge Graph (Optional)"
echo "--------------------------------------------"
echo ""
echo "  What: RHACM component dependency graph (291 components, 419 relationships)."
echo "  Used for: Understanding which components depend on each other during analysis."
echo "  Requires: Podman and Node.js"
echo ""

read -p "  Set up Neo4j RHACM? [y/N] " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    NEO4J_SETUP="$SCRIPT_DIR/neo4j-rhacm/setup.sh"
    if [ -f "$NEO4J_SETUP" ]; then
        bash "$NEO4J_SETUP"
    else
        fail "Setup script not found: $NEO4J_SETUP"
    fi
else
    info "Skipping. You can set it up later: bash mcp/neo4j-rhacm/setup.sh"
fi

echo ""

# -----------------------------------------------
# Update .mcp.json
# -----------------------------------------------
echo "--------------------------------------------"
echo "  Updating .mcp.json"
echo "--------------------------------------------"
echo ""

MCP_JSON="$APP_DIR/.mcp.json"

cat > "$MCP_JSON" <<'MCPEOF'
{
  "mcpServers": {
    "acm-ui": {
      "command": "python",
      "args": ["-m", "acm_ui_mcp_server.main"],
      "cwd": "../../mcp/acm-ui-mcp-server"
    },
    "jira": {
      "command": "python",
      "args": ["-m", "jira_mcp_server.main"],
      "cwd": "../../mcp/jira-mcp-server",
      "timeout": 60
    },
    "neo4j-rhacm": {
      "command": "uvx",
      "args": [
        "--with", "fastmcp<3",
        "mcp-neo4j-cypher",
        "--db-url", "bolt://localhost:7687",
        "--username", "neo4j",
        "--password", "rhacmgraph",
        "--read-only"
      ],
      "timeout": 60
    }
  }
}
MCPEOF
ok "Updated $MCP_JSON"

echo ""

# -----------------------------------------------
# Summary
# -----------------------------------------------
echo "============================================"
echo "  Setup Complete"
echo "============================================"
echo ""
echo "  Configured servers:"

# Check each
if python3 -c "import acm_ui_mcp_server" 2>/dev/null; then
    echo -e "    ${GREEN}OK${NC} acm-ui       -- ACM Console & Fleet Virt source code (20 tools)"
else
    echo -e "    ${RED}FAIL${NC} acm-ui       -- Not installed"
fi

if python3 -c "import jira_mcp_server" 2>/dev/null; then
    echo -e "    ${GREEN}OK${NC} jira         -- JIRA issue management (25 tools)"
else
    echo -e "    ${RED}FAIL${NC} jira         -- Not installed"
fi

if podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q neo4j-mcp; then
    echo -e "    ${GREEN}OK${NC} neo4j-rhacm  -- RHACM component dependency graph (3 tools)"
else
    echo -e "    ${YELLOW}--${NC} neo4j-rhacm  -- Not set up (optional)"
fi

echo ""
echo "  Next steps:"
echo "    1. Restart Claude Code or Cursor to pick up the new MCP config"
echo "    2. Run the z-stream analysis: cd apps/z-stream-analysis/"
echo "    3. See apps/z-stream-analysis/CLAUDE.md for usage"
echo ""
echo "  To verify MCP connections in Claude Code:"
echo "    Run: claude mcp list"
echo ""
