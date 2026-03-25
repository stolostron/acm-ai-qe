#!/usr/bin/env bash
#
# MCP Server Setup for Z-Stream Analysis
#
# Sets up ALL MCP servers used by the z-stream-analysis app.
# Run from the repository root: bash mcp/setup.sh
#
# Servers:
#   acm-ui       -- Search ACM Console & Fleet Virt source code via GitHub
#   jira         -- Search/create JIRA issues for bug correlation
#   jenkins      -- Jenkins pipeline analysis, build monitoring (needs VPN)
#   polarion     -- Polarion test case management (needs VPN + JWT)
#   neo4j-rhacm  -- RHACM component dependency graph (needs Podman)
#
# All servers are set up by default. If you don't have credentials for a
# server, press Enter to skip the credential prompt -- a placeholder will
# be created that you can fill in later.

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

POLARION_TOKEN_INPUT=""

# -----------------------------------------------
# Prerequisites Check
# -----------------------------------------------
echo ""
echo "============================================"
echo "  MCP Server Setup for Z-Stream Analysis"
echo "============================================"
echo ""
echo "  This script sets up all 5 MCP servers."
echo "  If you don't have credentials for a server,"
echo "  press Enter to skip -- you can add them later."
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
# [1/5] ACM UI MCP Server
# -----------------------------------------------
echo "--------------------------------------------"
echo "  [1/5] ACM UI MCP Server"
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
# [2/5] JIRA MCP Server
# -----------------------------------------------
echo "--------------------------------------------"
echo "  [2/5] JIRA MCP Server"
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

    read -p "  JIRA API Token (or Enter to skip): " JIRA_TOKEN
    if [ -z "$JIRA_TOKEN" ]; then
        warn "No token provided. Creating .env with placeholder -- update later."
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
# [3/5] Jenkins MCP Server
# -----------------------------------------------
echo "--------------------------------------------"
echo "  [3/5] Jenkins MCP Server"
echo "--------------------------------------------"
echo ""
echo "  What: Jenkins pipeline analysis, build monitoring, failure investigation."
echo "  Used for: Analyzing CI/CD pipeline failures, fetching test results."
echo "  Requires: Red Hat VPN for internal Jenkins access."
echo ""

JENKINS_DIR="$SCRIPT_DIR/jenkins-mcp"

info "Installing Jenkins MCP dependencies..."
pip3 install -r "$JENKINS_DIR/requirements.txt" --quiet 2>/dev/null
ok "Dependencies installed"

JENKINS_CONFIG="$HOME/.jenkins/config.json"
if [ -f "$JENKINS_CONFIG" ]; then
    ok "Jenkins credentials found: $JENKINS_CONFIG"
else
    echo ""
    info "Jenkins credentials needed."
    echo ""
    echo "  To get your Jenkins API token:"
    echo "    1. Log into Jenkins"
    echo "    2. Click your username (top right) -> Configure"
    echo "    3. Under 'API Token', click 'Add new Token'"
    echo "    4. Copy the generated token"
    echo ""

    read -p "  Jenkins URL [https://jenkins-csb-rhacm-tests.dno.corp.redhat.com]: " JENKINS_URL_INPUT
    JENKINS_URL_INPUT="${JENKINS_URL_INPUT:-https://jenkins-csb-rhacm-tests.dno.corp.redhat.com}"

    read -p "  Jenkins Username (or Enter to skip): " JENKINS_USER_INPUT

    if [ -n "$JENKINS_USER_INPUT" ]; then
        read -p "  Jenkins API Token (or Enter to skip): " JENKINS_TOKEN_INPUT
        if [ -z "$JENKINS_TOKEN_INPUT" ]; then
            warn "No token provided. Creating config with placeholder -- update later."
            JENKINS_TOKEN_INPUT="PASTE_YOUR_API_TOKEN_HERE"
        fi

        mkdir -p "$HOME/.jenkins"
        cat > "$JENKINS_CONFIG" <<EOF
{
  "jenkins_url": "$JENKINS_URL_INPUT",
  "jenkins_user": "$JENKINS_USER_INPUT",
  "jenkins_token": "$JENKINS_TOKEN_INPUT"
}
EOF
        ok "Created $JENKINS_CONFIG"
        echo "  Edit this file later to update credentials: $JENKINS_CONFIG"
    else
        warn "Skipped credentials. Create ~/.jenkins/config.json later."
        echo "  Template:"
        echo '  {"jenkins_url":"https://...","jenkins_user":"...","jenkins_token":"..."}'
    fi
fi

echo ""

# -----------------------------------------------
# [4/5] Polarion MCP
# -----------------------------------------------
echo "--------------------------------------------"
echo "  [4/5] Polarion MCP"
echo "--------------------------------------------"
echo ""
echo "  What: Read-only access to Polarion test cases (RHACM4K project)."
echo "  Used for: Reading test case details, steps, and setup instructions."
echo "  Requires: Red Hat VPN + Polarion JWT personal access token."
echo "  No pip install needed (uses uvx to run polarion-mcp from PyPI)."
echo ""

if command -v uvx &>/dev/null; then
    ok "uvx is available"
else
    warn "uvx not found. Install: pip install uv"
    echo "  Polarion will be added to .mcp.json but may not work until uvx is installed."
fi

echo ""
info "Polarion JWT token needed."
echo ""
echo "  To get your token:"
echo "    1. Connect to Red Hat VPN"
echo "    2. Go to https://polarion.engineering.redhat.com/polarion/"
echo "    3. Click your avatar -> My Account -> Personal Access Tokens"
echo "    4. Create a new token and copy it"
echo ""

read -p "  Polarion JWT Token (or Enter to skip): " POLARION_TOKEN_INPUT
if [ -z "$POLARION_TOKEN_INPUT" ]; then
    warn "No token provided. Set POLARION_PAT in .mcp.json later."
    POLARION_TOKEN_INPUT="PASTE_YOUR_JWT_TOKEN_HERE"
else
    ok "Token received"
fi

echo ""

# -----------------------------------------------
# [5/5] Neo4j RHACM Knowledge Graph
# -----------------------------------------------
echo "--------------------------------------------"
echo "  [5/5] Neo4j RHACM Knowledge Graph"
echo "--------------------------------------------"
echo ""
echo "  What: RHACM component dependency graph (291 components, 419 relationships)."
echo "  Used for: Understanding which components depend on each other during analysis."
echo "  Requires: Podman (container runtime)"
echo ""

if command -v podman &>/dev/null; then
    ok "Podman installed"

    if podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
        ok "Neo4j container already exists"
        echo "  Start it with: podman machine start && podman start neo4j-rhacm"
    else
        info "Neo4j container not found."
        echo ""
        echo "  To set up Neo4j:"
        echo "    1. podman machine start"
        echo "    2. podman run -d --name neo4j-rhacm \\"
        echo "         -p 7474:7474 -p 7687:7687 \\"
        echo "         -e NEO4J_AUTH=neo4j/rhacmgraph \\"
        echo "         -e NEO4J_PLUGINS='[\"apoc\"]' \\"
        echo "         neo4j:5-community"
        echo "    3. Load the RHACM data (see mcp/neo4j-rhacm/README.md)"
        echo ""
        echo "  See mcp/neo4j-rhacm/Neo4j-RHACM-MCP-Complete-Guide.md for full instructions."
    fi
else
    warn "Podman not found. Install: brew install podman (macOS)"
    echo "  Neo4j will be added to .mcp.json but needs Podman to run."
    echo "  See mcp/neo4j-rhacm/README.md for setup instructions."
fi

echo ""

# -----------------------------------------------
# Update .mcp.json (always includes ALL servers)
# -----------------------------------------------
echo "--------------------------------------------"
echo "  Updating .mcp.json"
echo "--------------------------------------------"
echo ""

MCP_JSON="$APP_DIR/.mcp.json"

python3 -c "
import json

config = {'mcpServers': {
    'acm-ui': {
        'command': 'python',
        'args': ['-m', 'acm_ui_mcp_server.main'],
        'cwd': '../../mcp/acm-ui-mcp-server'
    },
    'jira': {
        'command': 'python',
        'args': ['-m', 'jira_mcp_server.main'],
        'cwd': '../../mcp/jira-mcp-server',
        'timeout': 60
    },
    'jenkins': {
        'command': 'python',
        'args': ['jenkins_mcp_server.py'],
        'cwd': '../../mcp/jenkins-mcp',
        'timeout': 60
    },
    'polarion': {
        'command': 'uvx',
        'args': ['--with', 'polarion-mcp', 'python',
                 '../../mcp/polarion/polarion-mcp-wrapper.py'],
        'env': {
            'POLARION_BASE_URL': 'https://polarion.engineering.redhat.com/polarion',
            'POLARION_PAT': '${POLARION_TOKEN_INPUT}'
        },
        'timeout': 90
    },
    'neo4j-rhacm': {
        'command': 'uvx',
        'args': ['--with', 'fastmcp<3', 'mcp-neo4j-cypher',
                 '--db-url', 'bolt://localhost:7687',
                 '--username', 'neo4j',
                 '--password', 'rhacmgraph',
                 '--read-only'],
        'timeout': 60
    }
}}

with open('$MCP_JSON', 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" 2>/dev/null

ok "Updated $MCP_JSON"

echo ""

# -----------------------------------------------
# Summary
# -----------------------------------------------
echo "============================================"
echo "  Setup Complete -- All 5 Servers Configured"
echo "============================================"
echo ""
echo "  Server status:"

if python3 -c "import acm_ui_mcp_server" 2>/dev/null; then
    echo -e "    ${GREEN}OK${NC}   acm-ui       -- ACM Console & Fleet Virt source code (20 tools)"
else
    echo -e "    ${YELLOW}DEPS${NC} acm-ui       -- Run: pip install -e mcp/acm-ui-mcp-server/"
fi

if python3 -c "import jira_mcp_server" 2>/dev/null; then
    echo -e "    ${GREEN}OK${NC}   jira         -- JIRA issue management (25 tools)"
else
    echo -e "    ${YELLOW}DEPS${NC} jira         -- Run: pip install -e mcp/jira-mcp-server/"
fi

if python3 -c "import mcp, httpx" 2>/dev/null; then
    echo -e "    ${GREEN}OK${NC}   jenkins      -- Jenkins pipeline analysis (11 tools)"
else
    echo -e "    ${YELLOW}DEPS${NC} jenkins      -- Run: pip install -r mcp/jenkins-mcp/requirements.txt"
fi

if command -v uvx &>/dev/null; then
    echo -e "    ${GREEN}OK${NC}   polarion     -- Polarion test cases (17+ tools)"
else
    echo -e "    ${YELLOW}DEPS${NC} polarion     -- Run: pip install uv (for uvx)"
fi

if podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
    echo -e "    ${GREEN}OK${NC}   neo4j-rhacm  -- RHACM dependency graph (3 tools)"
else
    echo -e "    ${YELLOW}SETUP${NC} neo4j-rhacm  -- See mcp/neo4j-rhacm/README.md"
fi

echo ""

# Credential status
echo "  Credential status:"

if [ -f "$JIRA_DIR/.env" ] && ! grep -q "PASTE_YOUR" "$JIRA_DIR/.env" 2>/dev/null; then
    echo -e "    ${GREEN}OK${NC}   jira         -- $JIRA_DIR/.env"
else
    echo -e "    ${YELLOW}TODO${NC} jira         -- Edit $JIRA_DIR/.env with your API token"
fi

if [ -f "$HOME/.jenkins/config.json" ] && ! grep -q "PASTE_YOUR" "$HOME/.jenkins/config.json" 2>/dev/null; then
    echo -e "    ${GREEN}OK${NC}   jenkins      -- ~/.jenkins/config.json"
else
    echo -e "    ${YELLOW}TODO${NC} jenkins      -- Create/edit ~/.jenkins/config.json"
fi

if [ "$POLARION_TOKEN_INPUT" != "PASTE_YOUR_JWT_TOKEN_HERE" ] && [ -n "$POLARION_TOKEN_INPUT" ]; then
    echo -e "    ${GREEN}OK${NC}   polarion     -- Token set in .mcp.json"
else
    echo -e "    ${YELLOW}TODO${NC} polarion     -- Set POLARION_PAT in apps/z-stream-analysis/.mcp.json"
fi

echo ""
echo "  Next steps:"
echo "    1. Fill in any TODO credentials above"
echo "    2. Restart Claude Code or Cursor to pick up the new MCP config"
echo "    3. Run the z-stream analysis: cd apps/z-stream-analysis/"
echo "    4. See apps/z-stream-analysis/CLAUDE.md for usage"
echo ""
echo "  To verify MCP connections in Claude Code:"
echo "    Run: claude mcp list"
echo ""
