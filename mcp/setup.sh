#!/usr/bin/env bash
#
# MCP Server Setup for AI Systems Suite
#
# Interactive setup that configures MCP servers for the app(s) you choose.
# Each app only gets the MCP servers it actually needs.
#
# Run from the repository root:  bash mcp/setup.sh
#
# Apps and their MCP requirements:
#   acm-hub-health    -> acm-ui
#   z-stream-analysis -> acm-ui, jira, jenkins, polarion, neo4j-rhacm
#
# All paths are resolved dynamically -- no machine-specific references.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MCP_DIR="$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

# -----------------------------------------------
# App / MCP Definitions
# -----------------------------------------------

# Which MCPs each app requires (space-separated)
APP_HUB_HEALTH_MCPS="acm-ui"
APP_ZSTREAM_MCPS="acm-ui jira jenkins polarion neo4j-rhacm"

# App directory names (relative to $REPO_ROOT/apps/)
APP_HUB_HEALTH_DIR="acm-hub-health"
APP_ZSTREAM_DIR="z-stream-analysis"

# Track which MCPs and apps to set up
SELECTED_MCPS=""
SELECTED_APPS=""

# Portable helper: check if an MCP is in the selected list (bash 3.x safe)
needs_mcp() {
    case " $SELECTED_MCPS " in
        *" $1 "*) return 0 ;;
        *) return 1 ;;
    esac
}

# -----------------------------------------------
# App Selection Menu
# -----------------------------------------------
echo ""
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  MCP Server Setup -- AI Systems Suite${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""
echo "  Which app(s) would you like to configure?"
echo ""
echo -e "    ${CYAN}1)${NC} ACM Hub Health Agent"
echo -e "       Needs: acm-ui"
echo ""
echo -e "    ${CYAN}2)${NC} Z-Stream Pipeline Analysis"
echo -e "       Needs: acm-ui, jira, jenkins, polarion, neo4j-rhacm"
echo ""
echo -e "    ${CYAN}3)${NC} Both"
echo -e "       Sets up all MCP servers for both apps"
echo ""

while true; do
    read -p "  Select [1/2/3]: " APP_CHOICE
    case "$APP_CHOICE" in
        1)
            SELECTED_APPS="$APP_HUB_HEALTH_DIR"
            SELECTED_MCPS="$APP_HUB_HEALTH_MCPS"
            echo ""
            ok "Selected: ACM Hub Health Agent"
            break
            ;;
        2)
            SELECTED_APPS="$APP_ZSTREAM_DIR"
            SELECTED_MCPS="$APP_ZSTREAM_MCPS"
            echo ""
            ok "Selected: Z-Stream Pipeline Analysis"
            break
            ;;
        3)
            SELECTED_APPS="$APP_HUB_HEALTH_DIR $APP_ZSTREAM_DIR"
            # Union of both -- deduplicated
            SELECTED_MCPS="$APP_ZSTREAM_MCPS"
            echo ""
            ok "Selected: Both apps"
            break
            ;;
        *)
            echo -e "  ${RED}Invalid choice. Enter 1, 2, or 3.${NC}"
            ;;
    esac
done

# Count MCPs for progress indicator
TOTAL_MCPS=$(echo $SELECTED_MCPS | wc -w | tr -d ' ')
CURRENT_MCP=0

echo ""
echo "  Will set up $TOTAL_MCPS MCP server(s): $SELECTED_MCPS"
echo ""
echo "  If you don't have credentials for a server,"
echo "  press Enter to skip -- you can add them later."
echo ""

# -----------------------------------------------
# Prerequisites Check
# -----------------------------------------------
info "Checking prerequisites..."

# Python
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    ok "Python $PY_VERSION"
else
    fail "Python 3.10+ is required. Install: brew install python3 (macOS) or sudo dnf install python3 (Fedora/RHEL)"
    exit 1
fi

# gh CLI (needed for acm-ui)
if needs_mcp "acm-ui"; then
    if command -v gh &>/dev/null; then
        ok "GitHub CLI (gh) installed"
        if gh auth status &>/dev/null 2>&1; then
            ok "GitHub CLI authenticated"
        else
            warn "GitHub CLI not authenticated"
            echo ""
            echo "  You need to authenticate with GitHub for the ACM UI MCP server."
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
        warn "GitHub CLI (gh) not found. ACM UI MCP server will not work."
        echo "  Install: brew install gh  (macOS) or sudo dnf install gh (Fedora/RHEL)"
        echo "  Then run: gh auth login"
    fi
fi

# uvx (needed for polarion and neo4j-rhacm)
if needs_mcp "polarion" || needs_mcp "neo4j-rhacm"; then
    if command -v uvx &>/dev/null; then
        ok "uvx is available"
    else
        warn "uvx not found. Install: pip install uv"
        echo "  Some servers use uvx and may not work until it's installed."
    fi
fi

echo ""

# -----------------------------------------------
# External MCP sources (cloned at setup time, not bundled)
# Once upstream PRs are merged, switch to upstream URLs.
# -----------------------------------------------

# JIRA: https://github.com/stolostron/jira-mcp-server/pull/24
JIRA_REPO="https://github.com/atifshafi/jira-mcp-server.git"
JIRA_BRANCH="feat/redhat-fields"

# Jenkins: https://github.com/redhat-community-ai-tools/jenkins-mcp/pull/13
JENKINS_REPO="https://github.com/atifshafi/jenkins-mcp.git"
JENKINS_BRANCH="fix/auth-logs-paths"

EXTERNAL_DIR="$MCP_DIR/.external"

clone_external() {
    local name="$1" repo="$2" branch="$3" target="$EXTERNAL_DIR/$name"

    if [ -d "$target/.git" ]; then
        info "Updating $name from upstream..."
        git -C "$target" fetch origin "$branch" --quiet 2>/dev/null || true
        git -C "$target" checkout "$branch" --quiet 2>/dev/null || true
        git -C "$target" pull --quiet 2>/dev/null || true
        ok "$name up to date"
    else
        info "Cloning $name..."
        mkdir -p "$EXTERNAL_DIR"
        git clone --branch "$branch" --depth 1 "$repo" "$target" --quiet
        ok "$name cloned (branch: $branch)"
    fi
}

# -----------------------------------------------
# MCP Server Installation Functions
# -----------------------------------------------

setup_acm_ui() {
    CURRENT_MCP=$((CURRENT_MCP + 1))
    echo "--------------------------------------------"
    echo "  [$CURRENT_MCP/$TOTAL_MCPS] ACM UI MCP Server"
    echo "--------------------------------------------"
    echo ""
    echo "  What: Searches ACM Console and Fleet Virtualization source code on GitHub."
    echo "  Used for: Finding UI selectors, component source, translations."
    echo ""

    ACM_UI_DIR="$MCP_DIR/acm-ui-mcp-server"
    ACM_UI_VENV="$ACM_UI_DIR/.venv"

    if [ ! -d "$ACM_UI_VENV" ]; then
        info "Creating virtual environment..."
        python3 -m venv "$ACM_UI_VENV"
        ok "Virtual environment created"
    fi

    if "$ACM_UI_VENV/bin/python" -c "import acm_ui_mcp_server" 2>/dev/null; then
        ok "Already installed"
    else
        info "Installing ACM UI MCP server..."
        "$ACM_UI_VENV/bin/pip" install -e "$ACM_UI_DIR" --quiet 2>/dev/null || \
        "$ACM_UI_VENV/bin/pip" install mcp pydantic pydantic-settings python-dotenv --quiet
        ok "Dependencies installed (in venv)"
    fi

    echo ""
}

setup_jira() {
    CURRENT_MCP=$((CURRENT_MCP + 1))
    echo "--------------------------------------------"
    echo "  [$CURRENT_MCP/$TOTAL_MCPS] JIRA MCP Server"
    echo "--------------------------------------------"
    echo ""
    echo "  What: Searches and manages JIRA issues."
    echo "  Used for: Finding related bugs, reading feature stories during analysis."
    echo "  Source: https://github.com/stolostron/jira-mcp-server"
    echo ""

    clone_external "jira-mcp-server" "$JIRA_REPO" "$JIRA_BRANCH"

    JIRA_DIR="$EXTERNAL_DIR/jira-mcp-server"
    JIRA_VENV="$JIRA_DIR/.venv"

    if [ ! -d "$JIRA_VENV" ]; then
        info "Creating virtual environment..."
        python3 -m venv "$JIRA_VENV"
        ok "Virtual environment created"
    fi

    if "$JIRA_VENV/bin/python" -c "import jira_mcp_server" 2>/dev/null; then
        ok "Already installed"
    else
        info "Installing JIRA MCP server..."
        "$JIRA_VENV/bin/pip" install -e "$JIRA_DIR" --quiet 2>/dev/null || \
        "$JIRA_VENV/bin/pip" install fastmcp jira pydantic asyncio-throttle python-dotenv uvicorn --quiet
        ok "Dependencies installed (in venv)"
    fi

    JIRA_ENV="$JIRA_DIR/.env"
    if [ -f "$JIRA_ENV" ] && ! grep -q "PASTE_YOUR" "$JIRA_ENV" 2>/dev/null; then
        ok "Credentials file exists: $JIRA_ENV"
    else
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

        read -sp "  JIRA API Token (or Enter to skip): " JIRA_TOKEN
        echo ""
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
    fi

    echo ""
}

setup_jenkins() {
    CURRENT_MCP=$((CURRENT_MCP + 1))
    echo "--------------------------------------------"
    echo "  [$CURRENT_MCP/$TOTAL_MCPS] Jenkins MCP Server"
    echo "--------------------------------------------"
    echo ""
    echo "  What: Jenkins pipeline analysis, build monitoring, failure investigation."
    echo "  Used for: Analyzing CI/CD pipeline failures, fetching test results."
    echo "  Requires: Red Hat VPN for internal Jenkins access."
    echo "  Source: https://github.com/redhat-community-ai-tools/jenkins-mcp"
    echo ""

    clone_external "jenkins-mcp" "$JENKINS_REPO" "$JENKINS_BRANCH"

    JENKINS_DIR="$EXTERNAL_DIR/jenkins-mcp"
    JENKINS_VENV="$JENKINS_DIR/.venv"

    if [ ! -d "$JENKINS_VENV" ]; then
        info "Creating virtual environment..."
        python3 -m venv "$JENKINS_VENV"
        ok "Virtual environment created"
    fi

    info "Installing Jenkins MCP dependencies..."
    "$JENKINS_VENV/bin/pip" install -r "$JENKINS_DIR/requirements.txt" --quiet
    ok "Dependencies installed (in venv)"

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
            read -sp "  Jenkins API Token (or Enter to skip): " JENKINS_TOKEN_INPUT
            echo ""
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
}

setup_polarion() {
    CURRENT_MCP=$((CURRENT_MCP + 1))
    echo "--------------------------------------------"
    echo "  [$CURRENT_MCP/$TOTAL_MCPS] Polarion MCP"
    echo "--------------------------------------------"
    echo ""
    echo "  What: Read-only access to Polarion test cases (RHACM4K project)."
    echo "  Used for: Reading test case details, steps, and setup instructions."
    echo "  Requires: Red Hat VPN + Polarion JWT personal access token."
    echo "  No pip install needed (uses uvx to run polarion-mcp from PyPI)."
    echo ""

    POLARION_DIR="$MCP_DIR/polarion"
    POLARION_ENV="$POLARION_DIR/.env"

    if [ -f "$POLARION_ENV" ] && ! grep -q "PASTE_YOUR" "$POLARION_ENV" 2>/dev/null; then
        ok "Credentials file exists: $POLARION_ENV"
    else
        echo ""
        info "Polarion JWT token needed."
        echo ""
        echo "  To get your token:"
        echo "    1. Connect to Red Hat VPN"
        echo "    2. Go to https://polarion.engineering.redhat.com/polarion/"
        echo "    3. Click your avatar -> My Account -> Personal Access Tokens"
        echo "    4. Create a new token and copy it"
        echo ""

        read -sp "  Polarion JWT Token (or Enter to skip): " POLARION_TOKEN_INPUT
        echo ""
        if [ -z "$POLARION_TOKEN_INPUT" ]; then
            warn "No token provided. Creating .env with placeholder -- update later."
            POLARION_TOKEN_INPUT="PASTE_YOUR_JWT_TOKEN_HERE"
        fi

        cat > "$POLARION_ENV" <<EOF
POLARION_BASE_URL=https://polarion.engineering.redhat.com/polarion
POLARION_PAT=$POLARION_TOKEN_INPUT
EOF
        ok "Created $POLARION_ENV"
        echo "  Edit this file later to update credentials: $POLARION_ENV"
    fi

    echo ""
}

setup_neo4j() {
    CURRENT_MCP=$((CURRENT_MCP + 1))
    echo "--------------------------------------------"
    echo "  [$CURRENT_MCP/$TOTAL_MCPS] Neo4j RHACM Knowledge Graph"
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
            echo "    3. Load the RHACM data from stolostron/knowledge-graph"
            echo ""
            echo "  Docs: https://github.com/stolostron/knowledge-graph/tree/main/acm/agentic-docs/dependency-analysis"
        fi
    else
        warn "Podman not found. Install: brew install podman (macOS)"
        echo "  Neo4j will be added to .mcp.json but needs Podman to run."
        echo "  Docs: https://github.com/stolostron/knowledge-graph"
    fi

    echo ""
}

# -----------------------------------------------
# Install Selected MCP Servers
# -----------------------------------------------

needs_mcp "acm-ui"     && setup_acm_ui
needs_mcp "jira"        && setup_jira
needs_mcp "jenkins"     && setup_jenkins
needs_mcp "polarion"    && setup_polarion
needs_mcp "neo4j-rhacm" && setup_neo4j

# -----------------------------------------------
# Generate .mcp.json for Each Selected App
# -----------------------------------------------
echo "--------------------------------------------"
echo "  Generating .mcp.json for selected app(s)"
echo "--------------------------------------------"
echo ""

# MCP config definitions as JSON fragments, assembled per app.
# All paths are resolved from $MCP_DIR at generation time.
generate_mcp_json() {
    local app_dir="$1"
    shift
    local mcps=("$@")
    local app_path="$REPO_ROOT/apps/$app_dir"
    local mcp_json="$app_path/.mcp.json"

    if [ ! -d "$app_path" ]; then
        fail "App directory not found: $app_path"
        return 1
    fi

    python3 -c "
import json, sys

mcp_dir = sys.argv[1]
mcps = sys.argv[2:-1]  # MCP names between mcp_dir and output path
ext_dir = f'{mcp_dir}/.external'

# MCP server definitions
# - acm-ui, polarion: local (our code, in this repo)
# - jira, jenkins: cloned at setup time into .external/
# - neo4j-rhacm: runs from PyPI via uvx (no local code)
all_servers = {
    'acm-ui': {
        'command': f'{mcp_dir}/acm-ui-mcp-server/.venv/bin/python',
        'args': ['-m', 'acm_ui_mcp_server.main'],
        'timeout': 30
    },
    'jira': {
        'command': f'{ext_dir}/jira-mcp-server/.venv/bin/python',
        'args': ['-m', 'jira_mcp_server.main'],
        'timeout': 60
    },
    'jenkins': {
        'command': f'{ext_dir}/jenkins-mcp/.venv/bin/python',
        'args': [f'{mcp_dir}/jenkins-acm-tools.py'],
        'timeout': 60
    },
    'polarion': {
        'command': 'uvx',
        'args': ['--with', 'polarion-mcp', 'python',
                 f'{mcp_dir}/polarion/polarion-mcp-wrapper.py'],
        'env': {
            'POLARION_BASE_URL': 'https://polarion.engineering.redhat.com/polarion'
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
}

# Build config with only the requested MCPs
config = {'mcpServers': {name: all_servers[name] for name in mcps if name in all_servers}}

with open(sys.argv[-1], 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
" "$MCP_DIR" "${mcps[@]}" "$mcp_json"

    ok "Wrote $mcp_json"
    echo "  Servers: ${mcps[*]}"
}

for app in $SELECTED_APPS; do
    case "$app" in
        "$APP_HUB_HEALTH_DIR")
            # shellcheck disable=SC2086
            generate_mcp_json "$app" $APP_HUB_HEALTH_MCPS
            ;;
        "$APP_ZSTREAM_DIR")
            # shellcheck disable=SC2086
            generate_mcp_json "$app" $APP_ZSTREAM_MCPS
            ;;
    esac
done

echo ""

# -----------------------------------------------
# Summary
# -----------------------------------------------
echo -e "${BOLD}============================================${NC}"
echo -e "${BOLD}  Setup Complete${NC}"
echo -e "${BOLD}============================================${NC}"
echo ""

# Server status
echo "  Server status:"

if needs_mcp "acm-ui"; then
    ACM_UI_VENV="$MCP_DIR/acm-ui-mcp-server/.venv"
    if [ -f "$ACM_UI_VENV/bin/python" ] && "$ACM_UI_VENV/bin/python" -c "import acm_ui_mcp_server" 2>/dev/null; then
        echo -e "    ${GREEN}OK${NC}   acm-ui       -- ACM Console & Fleet Virt source code (20 tools)"
    else
        echo -e "    ${YELLOW}DEPS${NC} acm-ui       -- Re-run setup to create venv"
    fi
fi

if needs_mcp "jira"; then
    JIRA_VENV="$EXTERNAL_DIR/jira-mcp-server/.venv"
    if [ -f "$JIRA_VENV/bin/python" ] && "$JIRA_VENV/bin/python" -c "import jira_mcp_server" 2>/dev/null; then
        echo -e "    ${GREEN}OK${NC}   jira         -- JIRA issue management (25 tools)"
    else
        echo -e "    ${YELLOW}DEPS${NC} jira         -- Re-run setup to create venv"
    fi
fi

if needs_mcp "jenkins"; then
    JENKINS_VENV="$EXTERNAL_DIR/jenkins-mcp/.venv"
    if [ -f "$JENKINS_VENV/bin/python" ] && "$JENKINS_VENV/bin/python" -c "import mcp, httpx" 2>/dev/null; then
        echo -e "    ${GREEN}OK${NC}   jenkins      -- Jenkins pipeline analysis (11 tools)"
    else
        echo -e "    ${YELLOW}DEPS${NC} jenkins      -- Re-run setup to create venv"
    fi
fi

if needs_mcp "polarion"; then
    if command -v uvx &>/dev/null; then
        echo -e "    ${GREEN}OK${NC}   polarion     -- Polarion test cases (25 tools)"
    else
        echo -e "    ${YELLOW}DEPS${NC} polarion     -- Run: pip install uv (for uvx)"
    fi
fi

if needs_mcp "neo4j-rhacm"; then
    if podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
        echo -e "    ${GREEN}OK${NC}   neo4j-rhacm  -- RHACM dependency graph (3 tools)"
    else
        echo -e "    ${YELLOW}SETUP${NC} neo4j-rhacm  -- See stolostron/knowledge-graph repo"
    fi
fi

echo ""

# Credential status (only for installed MCPs)
if needs_mcp "jira" || needs_mcp "jenkins" || needs_mcp "polarion"; then
    echo "  Credential status:"

    if needs_mcp "jira"; then
        if [ -f "$EXTERNAL_DIR/jira-mcp-server/.env" ] && ! grep -q "PASTE_YOUR" "$EXTERNAL_DIR/jira-mcp-server/.env" 2>/dev/null; then
            echo -e "    ${GREEN}OK${NC}   jira         -- $EXTERNAL_DIR/jira-mcp-server/.env"
        else
            echo -e "    ${YELLOW}TODO${NC} jira         -- Edit $EXTERNAL_DIR/jira-mcp-server/.env with your API token"
        fi
    fi

    if needs_mcp "jenkins"; then
        if [ -f "$HOME/.jenkins/config.json" ] && ! grep -q "PASTE_YOUR" "$HOME/.jenkins/config.json" 2>/dev/null; then
            echo -e "    ${GREEN}OK${NC}   jenkins      -- ~/.jenkins/config.json"
        else
            echo -e "    ${YELLOW}TODO${NC} jenkins      -- Create/edit ~/.jenkins/config.json"
        fi
    fi

    if needs_mcp "polarion"; then
        if [ -f "$MCP_DIR/polarion/.env" ] && ! grep -q "PASTE_YOUR" "$MCP_DIR/polarion/.env" 2>/dev/null; then
            echo -e "    ${GREEN}OK${NC}   polarion     -- $MCP_DIR/polarion/.env"
        else
            echo -e "    ${YELLOW}TODO${NC} polarion     -- Edit $MCP_DIR/polarion/.env with your JWT token"
        fi
    fi

    echo ""
fi

# Next steps (tailored to selected apps)
echo "  Next steps:"

STEP=0

# Credential TODO only if relevant
if needs_mcp "jira" || needs_mcp "jenkins" || needs_mcp "polarion"; then
    STEP=$((STEP + 1))
    echo "    $STEP. Fill in any TODO credentials above"
fi

STEP=$((STEP + 1))
echo "    $STEP. Restart Claude Code to pick up the new MCP config"

for app in $SELECTED_APPS; do
    STEP=$((STEP + 1))
    case "$app" in
        "$APP_HUB_HEALTH_DIR")
            echo "    $STEP. Hub Health: cd apps/acm-hub-health && oc login <hub> && claude"
            ;;
        "$APP_ZSTREAM_DIR")
            echo "    $STEP. Z-Stream: cd apps/z-stream-analysis && claude"
            ;;
    esac
done

echo ""
echo "  To verify MCP connections in Claude Code:"
echo "    Run: claude mcp list"
echo ""
