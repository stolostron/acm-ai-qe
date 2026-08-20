---
type: diagnostics
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - architecture/search/architecture.md
  - data-flow/search/data-flow.md
---

# ACM Search MCP Reference (acm-search)

Read-only access to ACM's search PostgreSQL database -- the same database
that powers the Console Search UI. Indexes Kubernetes resources from ALL
managed clusters, providing spoke-side visibility that `oc` commands
cannot (since `oc` only queries the hub cluster).

## Available Tools

| Tool | Purpose | Phase |
|------|---------|-------|
| `find_resources` | Cross-cluster resource search with filtering, grouping, counting, and health analysis | 3, 5, 6 |

Single tool with advanced filtering and output modes. No raw SQL access.

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
- **Label-based filtering**: `labelSelector` finds resources matching
  Kubernetes labels across all clusters without per-cluster access.

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
namespace:      Single or comma-separated list, or wildcard (kube-*)
cluster:        Single or comma-separated list
labelSelector:  Kubernetes label selector ("app=nginx,env!=test")
clusterSelector: Filter by cluster labels ("env=prod,cloud=AWS")
status:         Status filter ("Running,CrashLoopBackOff")
textSearch:     Full-text search across all resource fields
ageNewerThan:   Duration filter ("1h", "2d")
ageOlderThan:   Duration filter ("1h", "2d")
outputMode:     list | count | summary | health
groupBy:        status | namespace | cluster | kind | label:<key>
sortBy:         name | created | namespace | cluster
limit:          Max results for list mode (default: 50, max: 1000)
countOnly:      Return only counts, no details (boolean)
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
| Non-compliant policies | `find_resources(textSearch="NonCompliant", kind="Policy")` |
| Spoke-side addon deploys | `find_resources(kind="Deployment", cluster="<cluster>", namespace="open-cluster-management-agent-addon", outputMode="list")` |

## Architecture

**Source:** [stolostron/search-mcp-server](https://github.com/stolostron/search-mcp-server) (Go, Helm)

The MCP server runs as a pod on the ACM hub cluster (deployed into the
MCH namespace, e.g. `ocm`). It connects directly to the ACM Search
PostgreSQL database within the same namespace and exposes an HTTP
endpoint via an OpenShift route. Auth uses OCP bearer tokens validated
via K8s TokenReview API.

**Transport:** Streamable HTTP at `/mcp`, bridged via `mcp-remote` for
TLS handling (self-signed OCP routes).

## Connectivity (Cursor)

**Auto-connect wrapper**: `~/Documents/work/ai/tools/mcp/acm-search-mcp-connect.sh`

The wrapper script is the MCP `command` in `mcp.json`. Every time the
MCP is toggled on, it:
1. Reads cluster credentials from `~/Documents/work/notes/notes.md` (lines 1-3)
2. Logs into the cluster automatically
3. Deploys the Helm chart if not already present
4. Creates a 1-year ServiceAccount token
5. Connects via `mcp-remote`

**Cluster rotation:** Update `notes/notes.md` lines 1-3 with new cluster
info, then toggle acm-search off/on in Cursor Settings.

**Standalone deploy script:** `~/Documents/work/ai/tools/mcp/deploy-acm-search.sh`
(for manual use or `--uninstall`).

### Detecting unavailability

The MCP is unavailable when:
- Cursor shows "Error" status for acm-search
- Tool calls return connection errors or timeouts
- The cluster in `notes/notes.md` was torn down

### Recovery

Toggle acm-search off/on in Cursor Settings. The wrapper handles
login, deploy, and token creation automatically.

### Fallback

If the MCP cannot connect after toggling, skip `acm-search` usage and
rely on `oc` commands. The agent works without it, just with reduced
spoke-side visibility.
