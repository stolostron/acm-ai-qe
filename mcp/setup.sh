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
#   acm-hub-health    -> acm-ui, neo4j-rhacm, acm-search
#   z-stream-analysis -> acm-ui, jira, jenkins, polarion, neo4j-rhacm
#   test-case-generator -> acm-ui, jira, polarion, neo4j-rhacm, acm-search, acm-kubectl, playwright
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
APP_HUB_HEALTH_MCPS="acm-ui neo4j-rhacm acm-search"
APP_ZSTREAM_MCPS="acm-ui jira jenkins polarion neo4j-rhacm"
APP_TESTCASE_GEN_MCPS="acm-ui jira polarion neo4j-rhacm acm-search acm-kubectl playwright"

# App directory names (relative to $REPO_ROOT/apps/)
APP_HUB_HEALTH_DIR="acm-hub-health"
APP_ZSTREAM_DIR="z-stream-analysis"
APP_TESTCASE_GEN_DIR="test-case-generator"

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
echo -e "       Needs: acm-ui, neo4j-rhacm, acm-search"
echo ""
echo -e "    ${CYAN}2)${NC} Z-Stream Pipeline Analysis"
echo -e "       Needs: acm-ui, jira, jenkins, polarion, neo4j-rhacm"
echo ""
echo -e "    ${CYAN}3)${NC} Test Case Generator"
echo -e "       Needs: acm-ui, jira, polarion, neo4j-rhacm, acm-search, acm-kubectl, playwright"
echo ""
echo -e "    ${CYAN}4)${NC} All apps"
echo -e "       Sets up all MCP servers for all apps"
echo ""

while true; do
    read -p "  Select [1/2/3/4]: " APP_CHOICE
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
            SELECTED_APPS="$APP_TESTCASE_GEN_DIR"
            SELECTED_MCPS="$APP_TESTCASE_GEN_MCPS"
            echo ""
            ok "Selected: Test Case Generator"
            break
            ;;
        4)
            SELECTED_APPS="$APP_HUB_HEALTH_DIR $APP_ZSTREAM_DIR $APP_TESTCASE_GEN_DIR"
            # Union of all app MCPs (no single app is the superset anymore)
            SELECTED_MCPS="acm-ui jira jenkins polarion neo4j-rhacm acm-search acm-kubectl playwright"
            echo ""
            ok "Selected: All apps"
            break
            ;;
        *)
            echo -e "  ${RED}Invalid choice. Enter 1, 2, 3, or 4.${NC}"
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

# Node.js (needed for acm-search, acm-kubectl, playwright)
if needs_mcp "acm-search" || needs_mcp "acm-kubectl" || needs_mcp "playwright"; then
    if command -v node &>/dev/null; then
        ok "Node.js $(node --version)"
    else
        warn "Node.js not found. Install: brew install node (macOS) or sudo dnf install nodejs (Fedora/RHEL)"
        echo "  Node.js is needed for acm-search (mcp-remote), acm-kubectl, and playwright."
    fi
fi

# mcp-remote (needed for acm-search SSE bridge)
if needs_mcp "acm-search"; then
    if command -v mcp-remote &>/dev/null; then
        ok "mcp-remote installed"
    else
        warn "mcp-remote not found. Will attempt to install during acm-search setup."
        echo "  Or install manually: npm install -g mcp-remote"
    fi
fi

# npx (needed for acm-kubectl and playwright)
if needs_mcp "acm-kubectl" || needs_mcp "playwright"; then
    if command -v npx &>/dev/null; then
        ok "npx is available"
    else
        warn "npx not found. Install Node.js 18+ which includes npx."
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

# Knowledge Graph: https://github.com/stolostron/knowledge-graph/pull/19
KG_REPO="https://github.com/atifshafi/knowledge-graph.git"
KG_BRANCH="atif-depth-improvements"

# ACM Search: https://github.com/stolostron/acm-mcp-server (upstream, no fork needed)
ACM_SEARCH_REPO="https://github.com/stolostron/acm-mcp-server.git"
ACM_SEARCH_BRANCH="main"

EXTERNAL_DIR="$MCP_DIR/.external"

clone_external() {
    local name="$1"
    local repo="$2"
    local branch="$3"
    local target="$EXTERNAL_DIR/$name"

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

    JENKINS_ENV="$JENKINS_DIR/.env"
    if [ -f "$JENKINS_ENV" ] && ! grep -q "PASTE_YOUR" "$JENKINS_ENV" 2>/dev/null; then
        ok "Credentials file exists: $JENKINS_ENV"
    else
        # Migrate from legacy ~/.jenkins/config.json if it exists
        LEGACY_CONFIG="$HOME/.jenkins/config.json"
        if [ -f "$LEGACY_CONFIG" ] && ! grep -q "PASTE_YOUR" "$LEGACY_CONFIG" 2>/dev/null; then
            info "Migrating credentials from legacy $LEGACY_CONFIG..."
            JENKINS_USER_INPUT=$(python3 -c "import json; print(json.load(open('$LEGACY_CONFIG')).get('jenkins_user',''))" 2>/dev/null || true)
            JENKINS_TOKEN_INPUT=$(python3 -c "import json; print(json.load(open('$LEGACY_CONFIG')).get('jenkins_token',''))" 2>/dev/null || true)
            if [ -n "$JENKINS_USER_INPUT" ] && [ -n "$JENKINS_TOKEN_INPUT" ]; then
                cat > "$JENKINS_ENV" <<EOF
JENKINS_USER=$JENKINS_USER_INPUT
JENKINS_API_TOKEN=$JENKINS_TOKEN_INPUT
EOF
                ok "Migrated to $JENKINS_ENV"
            else
                warn "Could not parse legacy config. Will prompt for credentials."
                JENKINS_USER_INPUT=""
                JENKINS_TOKEN_INPUT=""
            fi
        fi

        # Prompt if we still don't have credentials
        if [ ! -f "$JENKINS_ENV" ] || grep -q "PASTE_YOUR" "$JENKINS_ENV" 2>/dev/null; then
            echo ""
            info "Jenkins credentials needed."
            echo ""
            echo "  To get your Jenkins API token:"
            echo "    1. Log into Jenkins"
            echo "    2. Click your username (top right) -> Configure"
            echo "    3. Under 'API Token', click 'Add new Token'"
            echo "    4. Copy the generated token"
            echo ""

            read -p "  Jenkins Username (or Enter to skip): " JENKINS_USER_INPUT

            if [ -n "$JENKINS_USER_INPUT" ]; then
                read -sp "  Jenkins API Token (or Enter to skip): " JENKINS_TOKEN_INPUT
                echo ""
                if [ -z "$JENKINS_TOKEN_INPUT" ]; then
                    warn "No token provided. Creating .env with placeholder -- update later."
                    JENKINS_TOKEN_INPUT="PASTE_YOUR_API_TOKEN_HERE"
                fi

                cat > "$JENKINS_ENV" <<EOF
JENKINS_USER=$JENKINS_USER_INPUT
JENKINS_API_TOKEN=$JENKINS_TOKEN_INPUT
EOF
                ok "Created $JENKINS_ENV"
                echo "  Edit this file later to update credentials: $JENKINS_ENV"
            else
                warn "Skipped credentials. Create $JENKINS_ENV later."
                echo "  Template:"
                echo "  JENKINS_USER=your_username"
                echo "  JENKINS_API_TOKEN=your_token"
            fi
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
    echo "  What: RHACM component dependency graph (339 components, 479 relationships)."
    echo "  Used for: Understanding which components depend on each other during analysis."
    echo "  Requires: Podman (container runtime)"
    echo "  Credentials: None (local container, password set automatically)."
    echo ""

    if ! command -v podman &>/dev/null; then
        warn "Podman not found. Install: brew install podman (macOS) or sudo dnf install podman (Fedora/RHEL)"
        echo "  Neo4j will be added to .mcp.json but won't work until Podman is installed."
        echo "  Re-run this script after installing Podman to complete setup."
        echo ""
        return
    fi

    ok "Podman installed"

    # Ensure podman machine is running (macOS only; Linux runs natively)
    if [[ "$(uname)" == "Darwin" ]]; then
        if ! podman machine info &>/dev/null 2>&1; then
            info "Initializing Podman machine (first-time setup, may take a minute)..."
            podman machine init --cpus 2 --memory 2048 --disk-size 20 2>/dev/null || true
        fi
        if ! podman info &>/dev/null 2>&1; then
            info "Starting Podman machine..."
            podman machine start 2>/dev/null || true
        fi
        if podman info &>/dev/null 2>&1; then
            ok "Podman machine running"
        else
            warn "Could not start Podman machine. Run 'podman machine start' manually."
            echo ""
            return
        fi
    fi

    # Clone the knowledge graph repo (contains Cypher data files)
    clone_external "knowledge-graph" "$KG_REPO" "$KG_BRANCH"
    KG_DATA_DIR="$EXTERNAL_DIR/knowledge-graph/acm/agentic-docs/dependency-analysis/knowledge-graph"

    # Create or start the Neo4j container
    if podman ps --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
        ok "Neo4j container running"
    elif podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
        info "Starting existing Neo4j container..."
        podman start neo4j-rhacm >/dev/null
        ok "Neo4j container started"
    else
        info "Creating Neo4j container..."
        if podman run -d --name neo4j-rhacm \
            -p 7474:7474 -p 7687:7687 \
            -e NEO4J_AUTH=neo4j/rhacmgraph \
            -e 'NEO4J_PLUGINS=["apoc"]' \
            neo4j:5-community >/dev/null 2>&1; then
            ok "Neo4j container created"
        else
            fail "Failed to create Neo4j container"
            echo "  Try manually: podman run -d --name neo4j-rhacm -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/rhacmgraph neo4j:5-community"
            echo ""
            return
        fi
    fi

    # Wait for Neo4j to be ready (accepts connections)
    info "Waiting for Neo4j to be ready..."
    NEO4J_READY=false
    for i in $(seq 1 30); do
        if podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph "RETURN 1" >/dev/null 2>&1; then
            NEO4J_READY=true
            break
        fi
        sleep 2
    done

    if [ "$NEO4J_READY" = false ]; then
        warn "Neo4j not ready after 60s. It may still be starting."
        echo "  Check status: podman logs neo4j-rhacm"
        echo "  Re-run this script once it's ready to load the graph data."
        echo ""
        return
    fi
    ok "Neo4j accepting connections"

    # Check if graph data is already loaded
    NODE_COUNT=$(podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph \
        "MATCH (n) RETURN count(n) AS c" --format plain 2>/dev/null | tail -1 | tr -d ' ')

    if [ -n "$NODE_COUNT" ] && [ "$NODE_COUNT" -gt 200 ] 2>/dev/null; then
        ok "Knowledge graph already loaded ($NODE_COUNT nodes)"
    else
        # Load base graph
        BASE_CYPHER="$KG_DATA_DIR/rhacm_architecture_comprehensive_final.cypher"
        if [ -f "$BASE_CYPHER" ]; then
            info "Loading base graph (~291 base components)..."
            if podman exec -i neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph < "$BASE_CYPHER" >/dev/null 2>&1; then
                ok "Base graph loaded"
            else
                fail "Failed to load base graph"
                echo "  Try manually: cat $BASE_CYPHER | podman exec -i neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph"
                echo ""
                return
            fi
        else
            fail "Base graph file not found: $BASE_CYPHER"
            echo ""
            return
        fi

        # Load extensions (Virtualization, etc.)
        EXT_DIR="$KG_DATA_DIR/extensions"
        if [ -d "$EXT_DIR" ]; then
            EXT_COUNT=0
            for ext in "$EXT_DIR"/*.cypher; do
                [ -f "$ext" ] || continue
                EXT_NAME=$(basename "$ext" .cypher)
                info "Loading extension: $EXT_NAME..."
                if podman exec -i neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph < "$ext" >/dev/null 2>&1; then
                    ok "Extension loaded: $EXT_NAME"
                    EXT_COUNT=$((EXT_COUNT + 1))
                else
                    warn "Failed to load extension: $EXT_NAME (non-fatal, continuing)"
                fi
            done
            if [ "$EXT_COUNT" -gt 0 ]; then
                ok "Loaded $EXT_COUNT extension(s)"
            fi
        fi

        # Verify final count
        FINAL_COUNT=$(podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph \
            "MATCH (n) RETURN count(n) AS c" --format plain 2>/dev/null | tail -1 | tr -d ' ')
        ok "Knowledge graph ready: $FINAL_COUNT nodes"
    fi

    echo ""
}

setup_acm_search() {
    CURRENT_MCP=$((CURRENT_MCP + 1))
    echo "--------------------------------------------"
    echo "  [$CURRENT_MCP/$TOTAL_MCPS] ACM Search MCP Server"
    echo "--------------------------------------------"
    echo ""
    echo "  What: Fleet-wide resource queries across all managed clusters via search-postgres."
    echo "  Used for: Spoke-side pod visibility, addon health verification, fleet health aggregation."
    echo "  Requires: Node.js + mcp-remote (npm), oc logged into an ACM hub with search enabled."
    echo "  Deployment: Runs as a pod on the ACM hub, accessed via SSE over an OpenShift route."
    echo "  Source: https://github.com/stolostron/acm-mcp-server"
    echo ""

    clone_external "acm-mcp-server" "$ACM_SEARCH_REPO" "$ACM_SEARCH_BRANCH"

    ACM_SEARCH_DIR="$EXTERNAL_DIR/acm-mcp-server/servers/postgresql"

    if [ ! -d "$ACM_SEARCH_DIR" ]; then
        fail "PostgreSQL server directory not found: $ACM_SEARCH_DIR"
        echo ""
        return
    fi

    # Ensure mcp-remote is installed globally (stdio-to-SSE bridge)
    if command -v mcp-remote &>/dev/null; then
        ACM_SEARCH_MCP_REMOTE="$(which mcp-remote)"
        ok "mcp-remote found at $ACM_SEARCH_MCP_REMOTE"
    else
        if command -v node &>/dev/null; then
            info "Installing mcp-remote globally..."
            npm install -g mcp-remote 2>/dev/null
            if command -v mcp-remote &>/dev/null; then
                ACM_SEARCH_MCP_REMOTE="$(which mcp-remote)"
                ok "mcp-remote installed at $ACM_SEARCH_MCP_REMOTE"
            else
                warn "mcp-remote install failed. Install manually: npm install -g mcp-remote"
                ACM_SEARCH_MCP_REMOTE=""
            fi
        else
            warn "Node.js not found. Install Node.js, then: npm install -g mcp-remote"
            ACM_SEARCH_MCP_REMOTE=""
        fi
    fi

    # Deploy on-cluster if oc is logged in
    ACM_SEARCH_ROUTE=""
    ACM_SEARCH_TOKEN=""
    if command -v oc &>/dev/null && oc whoami &>/dev/null 2>&1; then
        if oc get namespace acm-search &>/dev/null 2>&1; then
            ok "acm-search namespace exists on cluster"
        else
            info "Deploying acm-search MCP server on-cluster..."
            if [ -f "$ACM_SEARCH_DIR/scripts/create-secret.sh" ]; then
                (cd "$ACM_SEARCH_DIR" && bash scripts/create-secret.sh 2>&1) || {
                    warn "create-secret.sh failed. You may need to deploy manually."
                }
            fi
            if [ -f "$ACM_SEARCH_DIR/Makefile" ]; then
                (cd "$ACM_SEARCH_DIR" && make deploy-prebuilt 2>&1) || {
                    warn "deploy-prebuilt failed. Check: oc get pods -n acm-search"
                }
            fi
        fi

        # Extract route URL
        ACM_SEARCH_ROUTE=$(oc get route -n acm-search -o jsonpath='{.items[0].spec.host}' 2>/dev/null || true)
        if [ -n "$ACM_SEARCH_ROUTE" ]; then
            ok "Route: $ACM_SEARCH_ROUTE"
        else
            warn "No route found in acm-search namespace."
            echo "  Deploy manually: cd $ACM_SEARCH_DIR && bash scripts/create-secret.sh && make deploy-prebuilt"
        fi

        # Extract service account token
        ACM_SEARCH_TOKEN=$(oc get secret acm-search-client-token -n acm-search -o jsonpath='{.data.token}' 2>/dev/null | base64 -d || true)
        if [ -n "$ACM_SEARCH_TOKEN" ]; then
            ok "Service account token extracted"
        else
            warn "Could not extract acm-search-client-token. Check: oc get secret -n acm-search"
        fi
    else
        warn "oc not logged in. Skipping on-cluster deployment."
        echo "  Log in first, then re-run: oc login <hub-api-url> && bash mcp/setup.sh"
    fi

    echo ""
}

setup_acm_kubectl() {
    CURRENT_MCP=$((CURRENT_MCP + 1))
    echo "--------------------------------------------"
    echo "  [$CURRENT_MCP/$TOTAL_MCPS] ACM Kubectl MCP Server"
    echo "--------------------------------------------"
    echo ""
    echo "  What: Multicluster kubectl -- list managed clusters, run kubectl on hub/spoke clusters."
    echo "  Used for: Live cluster validation (checking spoke state, verifying resources)."
    echo "  Requires: Node.js 18+, oc/kubectl logged into an ACM hub cluster."
    echo "  Source: https://github.com/stolostron/acm-mcp-server (servers/multicluster-kubectl)"
    echo ""

    # The repo is shared with acm-search -- clone if not already present
    clone_external "acm-mcp-server" "$ACM_SEARCH_REPO" "$ACM_SEARCH_BRANCH"

    ACM_KUBECTL_DIR="$EXTERNAL_DIR/acm-mcp-server/servers/multicluster-kubectl"

    if [ ! -d "$ACM_KUBECTL_DIR" ]; then
        fail "Multicluster kubectl directory not found: $ACM_KUBECTL_DIR"
        echo ""
        return
    fi

    if command -v npx &>/dev/null; then
        ok "npx available -- acm-kubectl will run via: npx -y acm-mcp-server@latest"
    else
        warn "npx not found. Install Node.js 18+ which includes npx."
    fi

    # Check if oc/kubectl is available for runtime
    if command -v oc &>/dev/null && oc whoami &>/dev/null 2>&1; then
        ok "oc logged in (kubectl commands will target this cluster)"
    elif command -v kubectl &>/dev/null; then
        ok "kubectl available (ensure KUBECONFIG points to ACM hub)"
    else
        warn "oc/kubectl not found. acm-kubectl needs cluster access at runtime."
        echo "  Log into an ACM hub: oc login <hub-api-url>"
    fi

    echo ""
}

setup_playwright() {
    CURRENT_MCP=$((CURRENT_MCP + 1))
    echo "--------------------------------------------"
    echo "  [$CURRENT_MCP/$TOTAL_MCPS] Playwright MCP Server"
    echo "--------------------------------------------"
    echo ""
    echo "  What: Browser automation for live UI validation (navigate, click, snapshot, screenshot)."
    echo "  Used for: Live cluster validation (verifying ACM console UI behavior)."
    echo "  Requires: Node.js 18+, Chromium browser (installed by Playwright)."
    echo "  Source: @playwright/mcp (npm package)"
    echo ""

    if ! command -v npx &>/dev/null; then
        warn "npx not found. Install Node.js 18+ which includes npx."
        echo ""
        return
    fi

    ok "npx available -- playwright will run via: npx @playwright/mcp@latest"

    # Check if Playwright browsers are installed
    if npx playwright install --dry-run chromium &>/dev/null 2>&1; then
        ok "Playwright browsers check passed"
    else
        info "Installing Playwright Chromium browser (first-time setup)..."
        if npx playwright install chromium 2>/dev/null; then
            ok "Chromium browser installed"
        else
            warn "Could not install Chromium automatically."
            echo "  Install manually: npx playwright install chromium"
            echo "  Playwright MCP will still be added to .mcp.json."
        fi
    fi

    echo ""
}

# -----------------------------------------------
# Install Selected MCP Servers
# -----------------------------------------------

needs_mcp "acm-ui"      && setup_acm_ui
needs_mcp "jira"         && setup_jira
needs_mcp "jenkins"      && setup_jenkins
needs_mcp "polarion"     && setup_polarion
needs_mcp "neo4j-rhacm"  && setup_neo4j
needs_mcp "acm-search"   && setup_acm_search
needs_mcp "acm-kubectl"  && setup_acm_kubectl
needs_mcp "playwright"   && setup_playwright

# -----------------------------------------------
# Generate .mcp.json for Each Selected App
# -----------------------------------------------
echo "--------------------------------------------"
echo "  Generating .mcp.json for selected app(s)"
echo "--------------------------------------------"
echo ""

# MCP config definitions as JSON fragments, assembled per app.
# All paths are resolved from $MCP_DIR at generation time.
# Credentials are read from .env files and injected into the config's "env"
# field so the MCP server process receives them regardless of working directory.
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
import json, os, sys

mcp_dir = sys.argv[1]
mcps = sys.argv[2:-1]  # MCP names between mcp_dir and output path
ext_dir = f'{mcp_dir}/.external'

def read_env_file(path):
    \"\"\"Read a .env file and return a dict of key=value pairs.\"\"\"
    env = {}
    if not os.path.isfile(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                env[key.strip()] = value.strip()
    return env

# Read credential .env files
jira_env = read_env_file(f'{ext_dir}/jira-mcp-server/.env')
jenkins_env = read_env_file(f'{ext_dir}/jenkins-mcp/.env')
polarion_env = read_env_file(f'{mcp_dir}/polarion/.env')

def _build_acm_search_config():
    \"\"\"Build acm-search MCP config using mcp-remote + on-cluster SSE route.\"\"\"
    import shutil, subprocess
    mcp_remote = shutil.which('mcp-remote')
    if not mcp_remote:
        return {'command': 'echo', 'args': ['acm-search not configured -- install mcp-remote and deploy on-cluster'], 'timeout': 10}
    try:
        route = subprocess.check_output(
            ['oc', 'get', 'route', '-n', 'acm-search', '-o', 'jsonpath={.items[0].spec.host}'],
            stderr=subprocess.DEVNULL, timeout=10).decode().strip()
        token = subprocess.check_output(
            ['oc', 'get', 'secret', 'acm-search-client-token', '-n', 'acm-search',
             '-o', 'jsonpath={.data.token}'],
            stderr=subprocess.DEVNULL, timeout=10).decode().strip()
        if token:
            import base64
            token = base64.b64decode(token).decode()
    except Exception:
        route, token = '', ''
    if not route or not token:
        return {'command': 'echo', 'args': ['acm-search not configured -- deploy on-cluster and re-run setup'], 'timeout': 10}
    return {
        'command': mcp_remote,
        'args': [f'https://{route}/sse', '--header', f'Authorization: Bearer {token}', '--transport', 'sse-only'],
        'env': {'NODE_TLS_REJECT_UNAUTHORIZED': '0'},
        'timeout': 90
    }

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
        'env': {k: v for k, v in jira_env.items() if v and 'PASTE_YOUR' not in v},
        'timeout': 60
    },
    'jenkins': {
        'command': f'{ext_dir}/jenkins-mcp/.venv/bin/python',
        'args': [f'{mcp_dir}/jenkins-acm-tools.py'],
        'env': {k: v for k, v in jenkins_env.items()
                if v and 'PASTE_YOUR' not in v
                and k in ('JENKINS_USER', 'JENKINS_API_TOKEN')},
        'timeout': 60
    },
    'polarion': {
        'command': 'uvx',
        'args': ['--with', 'polarion-mcp', 'python',
                 f'{mcp_dir}/polarion/polarion-mcp-wrapper.py'],
        'env': {
            'POLARION_BASE_URL': polarion_env.get('POLARION_BASE_URL',
                'https://polarion.engineering.redhat.com/polarion'),
            **({} if not polarion_env.get('POLARION_PAT') or
               'PASTE_YOUR' in polarion_env.get('POLARION_PAT', '')
               else {'POLARION_PAT': polarion_env['POLARION_PAT']})
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
    },
    'acm-search': _build_acm_search_config(),
    'acm-kubectl': {
        'command': 'npx',
        'args': ['-y', 'acm-mcp-server@latest'],
        'timeout': 60
    },
    'playwright': {
        'command': 'npx',
        'args': ['@playwright/mcp@latest'],
        'timeout': 30
    }
}

# Build config with only the requested MCPs
config = {'mcpServers': {name: all_servers[name] for name in mcps if name in all_servers}}

# Remove empty env dicts
for name, server in config['mcpServers'].items():
    if 'env' in server and not server['env']:
        del server['env']

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
        "$APP_TESTCASE_GEN_DIR")
            # shellcheck disable=SC2086
            generate_mcp_json "$app" $APP_TESTCASE_GEN_MCPS
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
    if podman ps --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
        echo -e "    ${GREEN}OK${NC}   neo4j-rhacm  -- RHACM dependency graph (2 tools, container running)"
    elif podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
        echo -e "    ${YELLOW}STOP${NC} neo4j-rhacm  -- Container exists but stopped. Run: podman start neo4j-rhacm"
    else
        echo -e "    ${YELLOW}SETUP${NC} neo4j-rhacm  -- Needs Podman. Re-run setup after installing."
    fi
fi

if needs_mcp "acm-search"; then
    if [ -n "$ACM_SEARCH_ROUTE" ] && [ -n "$ACM_SEARCH_TOKEN" ] && [ -n "$ACM_SEARCH_MCP_REMOTE" ]; then
        echo -e "    ${GREEN}OK${NC}   acm-search   -- Fleet-wide resource queries (5 tools, on-cluster SSE)"
    elif [ -n "$ACM_SEARCH_ROUTE" ]; then
        echo -e "    ${YELLOW}DEPS${NC} acm-search   -- Deployed, but missing mcp-remote or token. Re-run setup."
    else
        echo -e "    ${YELLOW}SETUP${NC} acm-search   -- Not deployed. Log into ACM hub and re-run setup."
    fi
fi

if needs_mcp "acm-kubectl"; then
    if command -v npx &>/dev/null; then
        echo -e "    ${GREEN}OK${NC}   acm-kubectl  -- Multicluster kubectl (3 tools, via npx)"
    else
        echo -e "    ${YELLOW}DEPS${NC} acm-kubectl  -- Needs Node.js 18+ with npx"
    fi
fi

if needs_mcp "playwright"; then
    if command -v npx &>/dev/null; then
        echo -e "    ${GREEN}OK${NC}   playwright   -- Browser automation (24 tools, via npx)"
    else
        echo -e "    ${YELLOW}DEPS${NC} playwright   -- Needs Node.js 18+ with npx"
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
        if [ -f "$EXTERNAL_DIR/jenkins-mcp/.env" ] && ! grep -q "PASTE_YOUR" "$EXTERNAL_DIR/jenkins-mcp/.env" 2>/dev/null; then
            echo -e "    ${GREEN}OK${NC}   jenkins      -- $EXTERNAL_DIR/jenkins-mcp/.env"
        else
            echo -e "    ${YELLOW}TODO${NC} jenkins      -- Edit $EXTERNAL_DIR/jenkins-mcp/.env with your credentials"
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
        "$APP_TESTCASE_GEN_DIR")
            echo "    $STEP. Test Case Generator: cd apps/test-case-generator && claude"
            ;;
    esac
done

echo ""
echo "  To verify MCP connections in Claude Code:"
echo "    Run: claude mcp list"
echo ""
echo "  If you update credentials in .env files later,"
echo "  re-run this script to regenerate .mcp.json."
echo ""
