#!/usr/bin/env bash
#
# deploy-acm-search.sh
#
# Non-interactive deployment of the ACM Search MCP server onto the current
# OpenShift cluster, with automatic .mcp.json updates for Claude Code.
#
# Usage:
#   bash mcp/deploy-acm-search.sh                       # Deploy + update root .mcp.json
#   bash mcp/deploy-acm-search.sh --mcp-json <path>     # Deploy + update specific .mcp.json
#   bash mcp/deploy-acm-search.sh --kubeconfig <path>    # Use specific kubeconfig
#
# Pre-flight (recommended workflow):
#   oc login <hub-api-url>
#   bash mcp/deploy-acm-search.sh
#   claude                    # session reads fresh .mcp.json
#
# What it does:
#   1. Verifies oc login, jq, mcp-remote prerequisites
#   2. Auto-discovers ACM namespace and extracts DB credentials
#   3. Creates acm-search namespace, RBAC, service accounts
#   4. Generates and applies the database secret
#   5. Deploys the MCP server pod (pre-built Quay.io images)
#   6. Waits for rollout, extracts route URL + client token
#   7. Updates .mcp.json file(s) with the working acm-search entry
#   8. Writes a marker file for setup.sh to reuse without re-deploying
#   9. Runs a health check

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_DIR="${SCRIPT_DIR}/.external/acm-mcp-server/servers/postgresql"

NAMESPACE="acm-search"
DEPLOYMENT_NAME="acm-search-mcp-server"
SERVICE_NAME="acm-search-mcp-server-service"
ROUTE_NAME="acm-search-mcp-server-route"
SECRET_NAME="acm-search-mcp-secret"
CLIENT_SA="acm-search-client"
CLIENT_TOKEN_SECRET="acm-search-client-token"
MARKER_FILE="${SCRIPT_DIR}/.acm-search-config.json"

# ── Parse arguments ─────────────────────────────────────────────────
KUBECONFIG_ARG=""
MCP_JSON_ARG=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --kubeconfig)
            KUBECONFIG_ARG="$2"
            shift 2
            ;;
        --mcp-json)
            MCP_JSON_ARG="$2"
            shift 2
            ;;
        --help|-h)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Usage: $0 [--kubeconfig PATH] [--mcp-json PATH]" >&2
            exit 1
            ;;
    esac
done

if [[ -n "$KUBECONFIG_ARG" ]]; then
    export KUBECONFIG="$KUBECONFIG_ARG"
fi

# ── Helpers ────────────────────────────────────────────────────────
fail() { echo "ERROR: $*" >&2; exit 1; }
info() { echo ":: $*"; }

# ── 1. Pre-flight checks ───────────────────────────────────────────
info "Pre-flight checks"

oc whoami &>/dev/null || fail "Not logged into OpenShift. Run 'oc login' first."
CLUSTER_URL=$(oc whoami --show-server)
CLUSTER_DOMAIN=$(echo "$CLUSTER_URL" | sed 's|https://api\.\(.*\):.*|\1|')
echo "  Cluster : $CLUSTER_DOMAIN"
echo "  User    : $(oc whoami)"

command -v jq &>/dev/null || fail "jq not found. Install: brew install jq"

MCP_REMOTE_PATH=$(command -v mcp-remote 2>/dev/null || true)
[[ -n "$MCP_REMOTE_PATH" ]] || fail "mcp-remote not found. Install: npm install -g mcp-remote"
echo "  mcp-remote: $MCP_REMOTE_PATH"

[[ -d "$SERVER_DIR" ]] || fail "Server source not found at $SERVER_DIR. Run 'bash mcp/setup.sh' first to clone the repo."

# ── 2. Discover ACM namespace + extract DB credentials ──────────────
info "Discovering ACM Search database"

ACM_NAMESPACE=""
for ns in open-cluster-management ocm multicluster-engine rhacm; do
    if oc get secret search-postgres -n "$ns" &>/dev/null; then
        ACM_NAMESPACE="$ns"
        break
    fi
done

if [[ -z "$ACM_NAMESPACE" ]]; then
    ACM_NAMESPACE=$(oc get secret --all-namespaces 2>/dev/null \
        | grep search-postgres | head -1 | awk '{print $1}')
fi

[[ -n "$ACM_NAMESPACE" ]] || fail \
    "search-postgres secret not found in any namespace. Is ACM installed with Search enabled?"

DB_USER=$(oc get secret search-postgres -n "$ACM_NAMESPACE" \
    -o jsonpath='{.data.database-user}' | base64 -d)
DB_PASS=$(oc get secret search-postgres -n "$ACM_NAMESPACE" \
    -o jsonpath='{.data.database-password}' | base64 -d)
DB_NAME=$(oc get secret search-postgres -n "$ACM_NAMESPACE" \
    -o jsonpath='{.data.database-name}' | base64 -d)
DB_HOST="search-postgres.${ACM_NAMESPACE}.svc.cluster.local"
DB_PORT="5432"

echo "  ACM namespace : $ACM_NAMESPACE"
echo "  Database      : $DB_NAME @ $DB_HOST (user: $DB_USER)"

# ── 3. Create namespace ────────────────────────────────────────────
info "Setting up namespace: $NAMESPACE"

if ! oc get namespace "$NAMESPACE" &>/dev/null; then
    oc create namespace "$NAMESPACE"
    echo "  Created namespace"
else
    echo "  Namespace exists"
fi
oc project "$NAMESPACE" >/dev/null

# ── 4. Apply RBAC + service accounts ───────────────────────────────
info "Applying RBAC and service accounts"

cd "$SERVER_DIR"

sed "s/namespace: mcp-server/namespace: ${NAMESPACE}/g" \
    k8s/rbac_proxy.yaml | oc apply -f - >/dev/null

sed -e "s/namespace: mcp-server/namespace: ${NAMESPACE}/g" \
    -e "s/postgres-mcp-server-proxy/${DEPLOYMENT_NAME}/g" \
    -e "s/mcp-client-proxy/${CLIENT_SA}/g" \
    -e "s/mcp-client-proxy-token/${CLIENT_TOKEN_SECRET}/g" \
    k8s/service-account_proxy.yaml | oc apply -f - >/dev/null

echo "  RBAC, ServiceAccounts, token secret applied"

# ── 5. Generate + apply database secret ─────────────────────────────
info "Generating database secret"

DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
ENCODED_URL=$(echo -n "$DATABASE_URL" | base64)

cat > k8s/secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: ${SECRET_NAME}
  namespace: ${NAMESPACE}
type: Opaque
data:
  database-url: ${ENCODED_URL}
EOF

oc apply -f k8s/secret.yaml >/dev/null
echo "  Database secret applied (fresh credentials)"

# ── 6. Generate + apply deployment ──────────────────────────────────
info "Deploying MCP server (pre-built Quay.io images)"

REGISTRY="quay.io/bjoydeep"
MCP_IMAGE="${REGISTRY}/acm-search-mcp-server:latest"
AUTH_IMAGE="${REGISTRY}/acm-search-auth-proxy:latest"

sed -e "s|image-registry.openshift-image-registry.svc:5000/mcp-server/postgres-mcp-server:latest|${MCP_IMAGE}|g" \
    -e "s|image-registry.openshift-image-registry.svc:5000/mcp-server/auth-proxy:latest|${AUTH_IMAGE}|g" \
    -e "s|namespace: mcp-server|namespace: ${NAMESPACE}|g" \
    -e "s|postgres-mcp-server-proxy|${DEPLOYMENT_NAME}|g" \
    -e "s|postgres-mcp-server-service-proxy|${SERVICE_NAME}|g" \
    -e "s|postgres-mcp-server-route-proxy|${ROUTE_NAME}|g" \
    -e "s|postgres-mcp-secret|${SECRET_NAME}|g" \
    -e "s|serviceAccountName: postgres-mcp-server-proxy|serviceAccountName: ${DEPLOYMENT_NAME}|g" \
    -e "s|app: postgres-mcp-server-proxy|app: ${DEPLOYMENT_NAME}|g" \
    k8s/deployment_proxy.yaml > k8s/deployment_docker.yaml

EXISTING_DEPLOY=$(oc get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" 2>/dev/null && echo "yes" || echo "no")

oc apply -f k8s/deployment_docker.yaml >/dev/null

if [[ "$EXISTING_DEPLOY" == "yes" ]]; then
    oc rollout restart deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE" 2>/dev/null || true
fi

echo "  Waiting for rollout (up to 5 min)..."
if ! oc rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE" --timeout=300s; then
    echo ""
    echo "  Pod logs:"
    oc logs deployment/"$DEPLOYMENT_NAME" -c acm-search-mcp-server -n "$NAMESPACE" --tail=10 2>/dev/null || true
    fail "Deployment rollout failed. Check logs above."
fi
echo "  Deployment ready"

# ── 7. Extract route URL + client token ─────────────────────────────
info "Extracting connection details"

ROUTE_HOST=$(oc get route "$ROUTE_NAME" -n "$NAMESPACE" \
    -o jsonpath='{.spec.host}' 2>/dev/null)
[[ -n "$ROUTE_HOST" ]] || fail "Route not found after deployment"

SSE_URL="https://${ROUTE_HOST}/sse"
echo "  SSE endpoint: $SSE_URL"

for i in $(seq 1 15); do
    CLIENT_TOKEN=$(oc get secret "$CLIENT_TOKEN_SECRET" -n "$NAMESPACE" \
        -o jsonpath='{.data.token}' 2>/dev/null | base64 -d 2>/dev/null || true)
    [[ -n "$CLIENT_TOKEN" ]] && break
    sleep 2
done

[[ -n "$CLIENT_TOKEN" ]] || fail "Client token not populated after 30s"
echo "  Client token: extracted (${#CLIENT_TOKEN} chars)"

# ── 8. Write marker file ───────────────────────────────────────────
info "Writing config marker"

jq -n \
   --arg route "$ROUTE_HOST" \
   --arg sse_url "$SSE_URL" \
   --arg token "$CLIENT_TOKEN" \
   --arg mcp_remote "$MCP_REMOTE_PATH" \
   --arg cluster "$CLUSTER_DOMAIN" \
   --arg acm_ns "$ACM_NAMESPACE" \
   --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
   '{
     route: $route,
     sse_url: $sse_url,
     token: $token,
     mcp_remote: $mcp_remote,
     cluster: $cluster,
     acm_namespace: $acm_ns,
     deployed_at: $timestamp
   }' > "$MARKER_FILE"

echo "  Wrote $MARKER_FILE"

# ── 9. Update .mcp.json file(s) ────────────────────────────────────
info "Updating MCP configuration"

AUTH_HEADER="Authorization: Bearer ${CLIENT_TOKEN}"

update_mcp_json() {
    local target="$1"
    local label="$2"

    if [[ ! -f "$target" ]]; then
        echo "  Skipped $label (file not found)"
        return
    fi

    # Check if file contains acm-search in its server list
    if ! jq -e '.mcpServers["acm-search"]' "$target" &>/dev/null; then
        echo "  Skipped $label (no acm-search entry)"
        return
    fi

    local backup="${target}.bak"
    cp "$target" "$backup"

    jq --arg url "$SSE_URL" \
       --arg auth "$AUTH_HEADER" \
       --arg mcp_remote "$MCP_REMOTE_PATH" \
       '.mcpServers["acm-search"] = {
          "command": $mcp_remote,
          "args": [
            $url,
            "--header",
            $auth,
            "--transport",
            "sse-only"
          ],
          "env": {
            "NODE_TLS_REJECT_UNAUTHORIZED": "0"
          },
          "timeout": 90
        }' "$backup" > "$target"

    rm -f "$backup"
    echo "  Updated $label"
}

# Determine which .mcp.json files to update
if [[ -n "$MCP_JSON_ARG" ]]; then
    update_mcp_json "$MCP_JSON_ARG" "$MCP_JSON_ARG"
else
    update_mcp_json "$REPO_ROOT/.mcp.json" "root .mcp.json"
    update_mcp_json "$REPO_ROOT/apps/acm-hub-health/.mcp.json" "acm-hub-health .mcp.json"
    update_mcp_json "$REPO_ROOT/apps/test-case-generator/.mcp.json" "test-case-generator .mcp.json"
fi

# ── 10. Health check ───────────────────────────────────────────────
info "Health check"

HEALTH=""
for i in $(seq 1 5); do
    HEALTH=$(curl -sk "https://${ROUTE_HOST}/health" 2>/dev/null || true)
    if echo "$HEALTH" | jq -e '.status' &>/dev/null; then
        echo "  $HEALTH"
        break
    fi
    sleep 3
done

if [[ -z "$HEALTH" ]]; then
    echo "  Health endpoint not responding yet (pod may still be starting)"
fi

# ── Done ────────────────────────────────────────────────────────────
echo ""
echo "================================================"
echo " ACM Search MCP deployed"
echo "================================================"
echo " Cluster  : $CLUSTER_DOMAIN"
echo " Endpoint : $SSE_URL"
echo " Namespace: $NAMESPACE"
echo ""
echo " If Claude Code is already running, exit and"
echo " restart to pick up the new .mcp.json."
echo "================================================"
