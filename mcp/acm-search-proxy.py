#!/usr/bin/env python3
"""
Resilient MCP proxy for ACM Search.

Proxies to stolostron/acm-mcp-server (https://github.com/stolostron/acm-mcp-server)
which provides the ACM Search PostgreSQL MCP server deployed on-cluster.

When the cluster is reachable: execs into mcp-remote (zero overhead passthrough).
When unreachable or not deployed: serves a stub MCP that returns structured
"cluster unreachable" errors so agents can detect the state and fall back to oc CLI.

Copyright Red Hat, Inc.
SPDX-License-Identifier: Apache-2.0

Usage in .mcp.json:
  "acm-search": {
    "command": "python3",
    "args": ["/path/to/acm-search-proxy.py"],
    "timeout": 30
  }
"""

import json
import os
import sys
import urllib.request
import ssl

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MARKER_FILE = os.path.join(SCRIPT_DIR, ".acm-search-config.json")
CONNECT_TIMEOUT = 5

TOOLS = [
    {
        "name": "query_database",
        "description": "Execute a SQL query against the ACM database containing Kubernetes resources from all managed clusters in the fleet",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "The SQL query to execute"},
                "parameters": {"type": "array", "items": {"type": "string"}, "description": "Query parameters (for parameterized queries)"},
                "maxRows": {"type": "number", "description": "Maximum number of rows to return", "default": 100},
            },
            "required": ["sql"],
        },
    },
    {
        "name": "list_tables",
        "description": "Get a list of all tables in the ACM database that stores Kubernetes resources from managed clusters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schema": {"type": "string", "description": "Schema name to filter by", "default": "public"},
            },
        },
    },
    {
        "name": "describe_table",
        "description": "Get detailed schema information for a table",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tableName": {"type": "string", "description": "Name of the table to describe"},
                "schema": {"type": "string", "description": "Schema name", "default": "public"},
            },
            "required": ["tableName"],
        },
    },
    {
        "name": "get_table_data",
        "description": "Get sample data from a table",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tableName": {"type": "string", "description": "Name of the table"},
                "schema": {"type": "string", "description": "Schema name", "default": "public"},
                "limit": {"type": "number", "description": "Number of rows to return", "default": 10},
            },
            "required": ["tableName"],
        },
    },
    {
        "name": "get_database_stats",
        "description": "Get statistics about the ACM database containing Kubernetes resources from all managed clusters in the fleet",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_tables",
        "description": "Search for tables by name in the ACM database containing Kubernetes resources from managed clusters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "searchTerm": {"type": "string", "description": "Search term to match table names"},
            },
            "required": ["searchTerm"],
        },
    },
    {
        "name": "find_resources",
        "description": "Find and analyze Kubernetes resources across ACM managed clusters with advanced filtering, counting, and health analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "description": "Resource kind (Pod, Deployment, Service, ManagedCluster, etc.)"},
                "name": {"type": "string", "description": "Resource name (exact match or shell-style pattern with * and ?)"},
                "namespace": {"type": "string", "description": "Namespace name or comma-separated list"},
                "cluster": {"type": "string", "description": "Cluster name or comma-separated list"},
                "labelSelector": {"type": "string", "description": "Kubernetes label selector: \"app=nginx,env!=test\""},
                "clusterSelector": {"type": "string", "description": "Filter by cluster labels: \"env=prod,cloud=AWS\""},
                "status": {"type": "string", "description": "Status filter: \"Running,Failed\" or \"CrashLoopBackOff\""},
                "textSearch": {"type": "string", "description": "Search across all resource fields"},
                "ageNewerThan": {"type": "string", "description": "Resources newer than: \"1h\", \"2d\", \"1w\""},
                "ageOlderThan": {"type": "string", "description": "Resources older than: \"1h\", \"2d\", \"1w\""},
                "outputMode": {"type": "string", "enum": ["list", "count", "summary", "health"], "description": "Output format", "default": "list"},
                "groupBy": {"type": "string", "description": "Group results by: status, namespace, cluster, kind, or label:key"},
                "countOnly": {"type": "boolean", "description": "Return only count numbers, no details"},
                "limit": {"type": "number", "description": "Max results for list mode (1-1000)", "default": 50},
                "sortBy": {"type": "string", "description": "Sort by: name, created, namespace, cluster", "default": "name"},
                "sortOrder": {"type": "string", "enum": ["asc", "desc"], "description": "Sort direction", "default": "asc"},
            },
        },
    },
]


def read_marker():
    """Read deployment config from marker file. Returns dict or None."""
    try:
        with open(MARKER_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def check_sse_reachable(url):
    """Quick connectivity check to the SSE endpoint. Returns True if reachable."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, method="GET")
        urllib.request.urlopen(req, timeout=CONNECT_TIMEOUT, context=ctx)
        return True
    except Exception:
        return False


def exec_mcp_remote(config):
    """Replace this process with mcp-remote. Never returns on success."""
    mcp_remote = config["mcp_remote"]
    sse_url = config["sse_url"]
    auth_header = f"Authorization: Bearer {config['token']}"

    env = os.environ.copy()
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"

    os.execve(
        mcp_remote,
        [mcp_remote, sse_url, "--header", auth_header, "--transport", "sse-only"],
        env,
    )


# ── Minimal JSON-RPC / MCP stub server (pure stdlib) ──────────────


def read_message():
    """Read a JSON-RPC message using Content-Length framing."""
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        line_str = line.decode("utf-8").rstrip("\r\n")
        if line_str == "":
            break
        if ":" in line_str:
            key, value = line_str.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", 0))
    if length == 0:
        return None
    body = sys.stdin.buffer.read(length)
    return json.loads(body.decode("utf-8"))


def write_message(msg):
    """Write a JSON-RPC message with Content-Length framing."""
    body = json.dumps(msg).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    sys.stdout.buffer.write(header + body)
    sys.stdout.buffer.flush()


def make_response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def make_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def run_stub(reason):
    """Run the stub MCP server. Handles initialize, tools/list, tools/call."""
    log(f"stub mode: {reason}")

    while True:
        msg = read_message()
        if msg is None:
            break

        method = msg.get("method", "")
        req_id = msg.get("id")

        if method == "initialize":
            write_message(make_response(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "acm-search-proxy", "version": "1.0.0"},
            }))

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            write_message(make_response(req_id, {"tools": TOOLS}))

        elif method == "tools/call":
            tool_name = msg.get("params", {}).get("name", "unknown")
            write_message(make_response(req_id, {
                "content": [{"type": "text", "text": (
                    f"ACM Search is unavailable ({reason}). "
                    f"Tool '{tool_name}' cannot execute. "
                    "Fall back to 'oc' CLI for resource queries."
                )}],
                "isError": True,
            }))

        elif method == "ping":
            write_message(make_response(req_id, {}))

        elif req_id is not None:
            write_message(make_error(req_id, -32601, f"Method not found: {method}"))


def log(msg):
    print(f"[acm-search-proxy] {msg}", file=sys.stderr)


def main():
    config = read_marker()

    if config is None:
        run_stub("not deployed — run: bash mcp/deploy-acm-search.sh")
        return

    sse_url = config.get("sse_url", "")
    cluster = config.get("cluster", "unknown")

    if not sse_url:
        run_stub("marker file missing sse_url")
        return

    if check_sse_reachable(sse_url):
        log(f"cluster reachable ({cluster}), handing off to mcp-remote")
        exec_mcp_remote(config)
    else:
        run_stub(f"cluster unreachable: {cluster}")


if __name__ == "__main__":
    main()
