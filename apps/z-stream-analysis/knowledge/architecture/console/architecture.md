# Console Architecture

The ACM console is the web UI for Advanced Cluster Management. It runs as an
OCP dynamic plugin with both a React frontend and a Node.js backend.

---

## Deployment

| Component | Namespace | Replicas | Image |
|-----------|-----------|----------|-------|
| console-chart-console-v2 | ocm | 2 (HA) | quay.io/stolostron/console or quay.io:443/acm-d/console-rhel9 |

The console is registered as an OCP ConsolePlugin. The OCP console loads
it at runtime and renders ACM navigation items (Fleet Management perspective,
Clusters, Search, Governance, Applications, etc.).

## Frontend (React/TypeScript)

Source: `stolostron/console/frontend/`

Key directories:
- `frontend/src/routes/` -- page components (Search, Clusters, Credentials, etc.)
- `frontend/src/ui-components/` -- reusable components (AcmTable, AcmButton, etc.)
- `frontend/src/wizards/` -- wizard flows (RoleAssignment, ClusterCreation, etc.)
- `frontend/src/resources/` -- API path construction and resource utilities
- `frontend/packages/multicluster-sdk/` -- multi-cluster SDK

Key UI frameworks:
- PatternFly 6 (PF6) -- CSS classes: `pf-v6-c-*`
- Previously PatternFly 5 (PF5): `pf-v5-c-*`
- Before that Carbon Design: `.tf--*` (completely removed)

## Backend (Node.js)

Source: `stolostron/console/backend/`

The backend serves as a proxy layer between the frontend and Kubernetes/external APIs.

Key routes:
| Route file | Path | Purpose |
|------------|------|---------|
| `proxy.ts` | `/api/proxy/*` | Generic Kubernetes API proxy |
| `search.ts` | `/api/proxy/search` | Search GraphQL proxy |
| `virtualMachineProxy.ts` | `/api/proxy/vm` | VM action proxy (start, stop, migrate) |
| `ansibletower.ts` | `/ansibletower/*` | Ansible Tower API proxy |
| `username.ts` | `/api/username` | Current user identity |
| `hub.ts` | `/api/hub` | Hub cluster metadata |
| `events.ts` | `/api/events` | SSE real-time event stream |
| `aggregators/statuses.ts` | `/api/statuses` | Application status aggregation |
| `aggregators/applications.ts` | `/api/applications` | Application health/sync |

## Server-Sent Events (SSE)

The SSE endpoint (`events.ts`) delivers real-time updates to the UI. When a
Kubernetes resource is created, modified, or deleted, the event is pushed to
all connected browser sessions via SSE. The UI tables auto-refresh without
requiring a manual page reload.

The `eventFilter()` function in `events.ts` determines which events are
delivered to each client based on RBAC permissions. This is a critical code
path -- if events for a resource type are dropped here, the UI table never
updates even though the API call succeeded.

## Console Plugins

The console loads multiple OCP ConsolePlugins:
- `acm` -- ACM hub management
- `mce` -- MCE cluster management
- `forklift` -- MTV migration UI
- `gitops` -- ArgoCD integration
- `kubevirt` -- Fleet Virtualization UI
- `monitoring` -- OCP monitoring
- `networking` -- OCP networking

Each plugin contributes routes, navigation items, and page components.
If a plugin fails to load, its features disappear from the UI.

## TLS

Console uses the TLS secret `console-chart-console-certs` in the ocm namespace.
Managed by OCP service-CA operator. If corrupted, the console HTTPS endpoint
fails, and the OCP console can't load the ACM plugin.
