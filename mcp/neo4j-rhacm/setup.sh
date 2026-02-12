#!/usr/bin/env bash
#
# Neo4j RHACM Knowledge Graph Setup
#
# Sets up two Podman containers:
#   1. neo4j-rhacm  — Neo4j database with RHACM architecture graph
#   2. neo4j-mcp    — MCP SSE server exposing the graph to AI agents
#
# After setup:
#   - Neo4j Browser: http://localhost:7474 (neo4j / rhacmgraph)
#   - MCP SSE endpoint: http://localhost:8000/sse
#
# Run: bash mcp/neo4j-rhacm/setup.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; }

echo ""
info "Neo4j RHACM Knowledge Graph Setup"
echo ""

# ── Check prerequisites ──────────────────────

if ! command -v podman &>/dev/null; then
    fail "Podman is required."
    echo "  Install: brew install podman  (macOS) or sudo dnf install podman (Fedora/RHEL)"
    echo "  Then run: podman machine init && podman machine start"
    exit 1
fi
ok "Podman installed"

if ! command -v npx &>/dev/null; then
    fail "Node.js/npx is required for the MCP bridge."
    echo "  Install: brew install node  (macOS) or sudo dnf install nodejs (Fedora/RHEL)"
    exit 1
fi
ok "npx available"

# Start Podman machine if needed (macOS)
if [[ "$(uname)" == "Darwin" ]]; then
    if ! podman machine inspect 2>/dev/null | grep -q '"State": "running"' 2>/dev/null; then
        info "Starting Podman machine..."
        podman machine start 2>/dev/null || true
    fi
fi

# ── Check if already set up ──────────────────

if podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q neo4j-rhacm; then
    warn "Container 'neo4j-rhacm' already exists."
    read -p "  Remove and recreate? [y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Removing existing containers..."
        podman rm -f neo4j-rhacm 2>/dev/null || true
        podman rm -f neo4j-mcp 2>/dev/null || true
    else
        # Just start them if stopped
        info "Starting existing containers..."
        podman start neo4j-rhacm 2>/dev/null || true
        podman start neo4j-mcp 2>/dev/null || true
        ok "Containers started"
        echo ""
        echo "  Neo4j Browser: http://localhost:7474 (neo4j / rhacmgraph)"
        echo "  MCP Endpoint:  http://localhost:8000/sse"
        exit 0
    fi
fi

# ── Step 1: Start Neo4j database ─────────────

info "Step 1/4: Starting Neo4j database container..."

podman run -d \
    --name neo4j-rhacm \
    -p 7474:7474 \
    -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/rhacmgraph \
    -e NEO4J_PLUGINS='["apoc"]' \
    neo4j:2025.01.0

ok "Neo4j container started"

# Wait for Neo4j to be ready
info "Waiting for Neo4j to initialize (this takes ~30 seconds)..."
for i in $(seq 1 60); do
    if podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph "RETURN 1" &>/dev/null; then
        ok "Neo4j is ready"
        break
    fi
    if [ "$i" -eq 60 ]; then
        fail "Neo4j did not start within 60 seconds. Check: podman logs neo4j-rhacm"
        exit 1
    fi
    sleep 1
done

# ── Step 2: Load RHACM data ─────────────────

info "Step 2/4: Loading RHACM knowledge graph data..."

TMPDIR=$(mktemp -d)
git clone --quiet --depth 1 https://github.com/stolostron/knowledge-graph.git "$TMPDIR/knowledge-graph"

CYPHER_FILE="$TMPDIR/knowledge-graph/acm/agentic-docs/dependency-analysis/knowledge-graph/rhacm_architecture_comprehensive_final.cypher"

if [ ! -f "$CYPHER_FILE" ]; then
    fail "Cypher import file not found in stolostron/knowledge-graph repo."
    echo "  Expected: acm/agentic-docs/dependency-analysis/knowledge-graph/rhacm_architecture_comprehensive_final.cypher"
    echo "  The repository structure may have changed. Check https://github.com/stolostron/knowledge-graph"
    rm -rf "$TMPDIR"
    exit 1
fi

podman cp "$CYPHER_FILE" neo4j-rhacm:/tmp/import.cypher
podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph -f /tmp/import.cypher

COMPONENT_COUNT=$(podman exec neo4j-rhacm cypher-shell -u neo4j -p rhacmgraph "MATCH (n) RETURN count(n)" 2>/dev/null | tail -1 | tr -d ' ')
ok "Loaded $COMPONENT_COUNT components"

rm -rf "$TMPDIR"

# ── Step 3: Start MCP SSE server ─────────────

info "Step 3/4: Starting MCP SSE server container..."

podman run -d \
    --name neo4j-mcp \
    -p 8000:8000 \
    quay.io/bjoydeep/neo4j-cypher:fixed \
    mcp-neo4j-cypher \
        --db-url bolt://host.containers.internal:7687 \
        --username neo4j \
        --password rhacmgraph \
        --transport sse

ok "MCP server container started"

# Wait for MCP endpoint
info "Waiting for MCP endpoint..."
for i in $(seq 1 30); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/sse 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "307" ]; then
        ok "MCP endpoint ready at http://localhost:8000/sse"
        break
    fi
    if [ "$i" -eq 30 ]; then
        warn "MCP endpoint not responding yet. It may need more time."
        echo "  Check: podman logs neo4j-mcp"
        echo "  Test:  curl http://localhost:8000/sse"
    fi
    sleep 1
done

# ── Step 4: Verify ───────────────────────────

info "Step 4/4: Verifying setup..."

echo ""
echo "  Neo4j Database:"
echo "    Browser:     http://localhost:7474"
echo "    Credentials: neo4j / rhacmgraph"
echo "    Components:  $COMPONENT_COUNT"
echo ""
echo "  MCP Server:"
echo "    Endpoint:    http://localhost:8000/sse"
echo "    Tools:       read_neo4j_cypher, write_neo4j_cypher, get_neo4j_schema"
echo ""

ok "Neo4j RHACM Knowledge Graph setup complete"
echo ""
echo "  After reboot, restart with:"
echo "    podman machine start && podman start neo4j-rhacm neo4j-mcp"
echo ""
