# ACM Search MCP Reference (acm-search)

Read-only access to ACM's search PostgreSQL database -- the same database
that powers the Console Search UI. Indexes Kubernetes resources from ALL
managed clusters, providing spoke-side visibility that `oc` commands
cannot (since `oc` only queries the hub cluster).

## Available Tools

| Tool | Purpose | Phase |
|------|---------|-------|
| `find_resources` | Cross-cluster resource search with filtering, grouping, and health analysis | 3, 5, 6 |
| `get_database_stats` | Database health: table count, row count, size, connections | 3 (prerequisite check) |
| `query_database` | Raw read-only SQL for complex queries not possible via `find_resources` | 5, 6 |

## What It Provides (That `oc` Cannot)

- **Spoke-side pod queries**: See pods running ON managed clusters, not
  just hub-side addon status CRs. A managedclusteraddon may show
  Available while the actual spoke pod is in CrashLoopBackOff.
- **Fleet-wide health aggregation**: One `find_resources(outputMode="health")`
  call returns pod health across ALL clusters. Replaces dozens of
  per-namespace `oc get pods` calls that only cover the hub.
- **Cross-cluster pattern detection**: `groupBy="cluster"` shows which
  clusters share symptoms. Answers "is this a spoke-specific issue or
  fleet-wide?" in one query.
- **Search data integrity verification**: `get_database_stats` confirms
  the search database has data (row counts, table sizes) without
  needing `oc exec ... psql`.

## What It Does NOT Replace

- **`oc get` for hub resources**: `oc` returns real-time state; search
  has seconds-to-minutes indexing lag. For hub pod health, use `oc`.
- **`oc get mch/mce -o yaml`**: Full resource YAML with nested status
  maps. Search stores flattened properties, not the full spec/status.
- **`oc logs`**: Search does not index pod logs.
- **`oc describe`**: Search does not index events or full conditions.
- **`oc exec`**: No equivalent (psql queries, connectivity checks).
- **`oc adm top`**: No metrics in search.

## `find_resources` Key Parameters

```
kind:           Resource kind (Pod, Deployment, ManagedCluster, etc.)
name:           Exact match or shell-style pattern (name="klusterlet-addon-*")
namespace:      Single or comma-separated list
cluster:        Single or comma-separated list
labelSelector:  Kubernetes label selector ("app=nginx,env!=test")
status:         Status filter ("Running,CrashLoopBackOff")
ageNewerThan:   Duration filter ("1h", "2d")
outputMode:     list | count | summary | health
groupBy:        status | namespace | cluster | kind | label:<key>
limit:          Max results for list mode (default: 50, max: 1000)
```

## Common Query Patterns

| Scenario | Query |
|----------|-------|
| Fleet-wide pod health | `find_resources(kind="Pod", outputMode="health")` |
| Spoke addon pods | `find_resources(kind="Pod", namespace="open-cluster-management-agent-addon", outputMode="count", groupBy="cluster")` |
| What's broken on a spoke | `find_resources(kind="Pod", cluster="<name>", status="CrashLoopBackOff,Error,Pending", outputMode="list")` |
| Search-collector running? | `find_resources(kind="Pod", name="klusterlet-addon-search*", outputMode="list")` |
| Hub deployments health | `find_resources(kind="Deployment", namespace="<mch-ns>", outputMode="list")` |
| Recent pod disruptions | `find_resources(kind="Pod", ageNewerThan="1h", outputMode="count", groupBy="cluster")` |
| Managed cluster summary | `find_resources(kind="ManagedCluster", outputMode="list")` |
| Search DB health | `get_database_stats()` |
| Spoke-side addon deploys | `find_resources(kind="Deployment", cluster="<cluster>", namespace="open-cluster-management-agent-addon", outputMode="list")` |
| Recently created pods | `find_resources(kind="Pod", cluster="<cluster>", ageNewerThan="1h", outputMode="list")` |

## Availability

The search MCP requires:
- `oc` logged into an ACM hub with search enabled
- The acm-search MCP server deployed on-cluster as a pod (via
  `create-secret.sh` + `make deploy-prebuilt` in the acm-mcp-server repo)
- `mcp-remote` installed globally (`npm install -g mcp-remote`) as a
  stdio-to-SSE bridge
- A valid service account token from the `acm-search` namespace

The MCP server runs as a pod on the ACM hub cluster, accessed via SSE
over an OpenShift route. `mcp-remote` bridges stdio (what Claude Code
expects) to SSE (what the on-cluster server speaks). The `--transport
sse-only` flag and `NODE_TLS_REJECT_UNAUTHORIZED=0` env var are set
in `.mcp.json` to handle self-signed certs and skip the Streamable
HTTP probe.

If the MCP is not configured or the server fails to connect, skip
search MCP usage and rely on `oc` commands -- the agent works
without it, just with reduced spoke-side visibility.

When the cluster is torn down and reprovisioned, redeploy the MCP
server and re-run `setup.sh` to extract the new route URL and token.
