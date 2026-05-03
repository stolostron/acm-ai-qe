# Console Subsystem -- Architecture

## What Console Does

ACM Console is the web UI layer for all ACM features. It runs as an OpenShift
dynamic plugin loaded into the OpenShift Console at runtime via Webpack Module
Federation. Two separate plugins -- `acm` (ACM features) and `mce` (MCE
features) -- register via `ConsolePlugin` CRs and inject ACM navigation items,
pages, and dashboards into the stock OpenShift Console.

The console-api backend (sometimes called the "BFF" -- Backend for Frontend)
proxies API requests from the browser to backend services (search-api, cluster
resources, observability, application, GRC), handles authentication and session
management, and serves RBAC endpoints for fine-grained RBAC UI.

Every ACM UI feature -- Search, Governance, Clusters, Applications, Fleet
Virtualization, RBAC User Management, Observability dashboards, Credentials --
is rendered through the Console subsystem. If Console is down, all UI tests
fail.

---

## Plugin Architecture

### OpenShift Dynamic Plugin Model

ACM Console uses the OpenShift dynamic plugin system introduced in OCP 4.10+:

1. Plugins register via `ConsolePlugin` CRs (`consoleplugins.console.openshift.io`)
2. The OCP Console pod discovers registered plugins at startup/reload
3. Plugin static assets (JS bundles) are loaded at runtime via Webpack Module
   Federation -- no OCP Console rebuild needed
4. Each plugin exposes extension points (routes, navigation items, flags,
   dashboard cards) consumed by the host console

### Two Plugin Deployments

| Plugin | CR Name | Namespace | Pod Label | What It Provides |
|--------|---------|-----------|-----------|------------------|
| ACM plugin | `acm` | MCH namespace (`open-cluster-management`) | `app=console-chart-console-v2` | ACM-specific UI: Search, Governance, Applications, Credentials, Overview, Fleet Virtualization, RBAC User Management |
| MCE plugin | `mce` | MCE namespace (`multicluster-engine`) | `app=console-mce` | MCE-layer UI: Cluster Lifecycle, Infrastructure, Import/Create wizards, cluster details |

Both plugins serve their JS bundles via HTTPS. The OCP Console fetches and
mounts them at runtime through Webpack's `ModuleFederationPlugin`. If either
plugin's pod is down or the `ConsolePlugin` CR is missing, the corresponding
feature tabs silently disappear from the UI -- no error, just missing
navigation items.

### Webpack Module Federation

Each plugin declares a `container` entry in its webpack config:
- Shared dependencies (React, PatternFly, @openshift-console/dynamic-plugin-sdk)
  are declared as shared singletons to avoid duplication
- The host console loads plugin manifests (`plugin-manifest.json`) to discover
  available extensions
- Extensions are lazy-loaded when the user navigates to a plugin-provided route

---

## Key Components

### console-chart-console-v2 (ACM plugin pod)

- **Pod label:** `app=console-chart-console-v2`
- **Namespace:** MCH namespace
- **CR:** `ConsolePlugin/acm`

Serves the ACM plugin bundle and console-api backend in the same pod. Contains:
- Frontend: React + PatternFly components for ACM features
- Backend (console-api): Express.js BFF serving REST endpoints, resource proxy,
  RBAC middleware, session management

The console-api backend handles:
- `/multicloud/api/v1/...` -- REST API endpoints
- `/multicloud/api/v1/proxy/...` -- Resource Proxy forwarding to backend services
- `/multicloud/api/v1/rbac/...` -- RBAC endpoints for fine-grained RBAC UI
- Authentication via OpenShift OAuth token passthrough
- WebSocket connections for real-time dashboard updates

### console-mce (MCE plugin pod)

- **Pod label:** `app=console-mce`
- **Namespace:** MCE namespace (`multicluster-engine`)
- **CR:** `ConsolePlugin/mce`

Serves the MCE plugin bundle. Provides cluster lifecycle UI: cluster
list/details, create/import wizards, cluster sets, cluster pools, environments.
Uses the same PatternFly and dynamic plugin SDK as the ACM plugin.

**Known issue:** console-mce is prone to CrashLoopBackOff from readiness/liveness
probe timeouts when backend services respond slowly. Connection pooling was
added in ACM 2.15.1 to mitigate (ACM-24965).

### acm-cli-downloads

- **Pod label:** `app=acm-cli-downloads`
- **Namespace:** MCH namespace

Serves CLI binary downloads (subctl, cm CLI, etc.) for the console's CLI
download page. Registers as a ConsoleCLIDownload extension.

### multicluster-integrations

- **Pod label:** `app=multicluster-integrations`
- **Namespace:** MCH namespace

Watches and reconciles integration resources needed for multi-cluster features.
Acts as a bridge between ACM-level and MCE-level resource management.

---

## Resource Proxy

The Resource Proxy is a component within console-api that forwards browser
requests to backend services. It avoids direct browser-to-backend connections,
centralizing auth, error handling, and CORS.

| Target Service | Route Prefix | What It Proxies |
|---|---|---|
| Search API | `/proxy/search` | GraphQL search queries |
| Cluster Resources | `/proxy/cluster` | Managed cluster details, status, actions |
| Observability | `/proxy/observability` | Grafana dashboards, metrics queries |
| Application Resources | `/proxy/app` | Application lifecycle data, subscriptions, channels |
| GRC Resources | `/proxy/grc` | Policy data, compliance status, policy sets |

Each proxy route authenticates via the user's OAuth token, applies RBAC
middleware checks, and forwards to the respective backend service.

---

## Authentication and Session Management

### Auth Flow

1. User navigates to OCP Console (or direct ACM URL)
2. OCP OAuth server handles login, issues token
3. Console-api receives token via Authorization header or cookie
4. Token validated against OCP API server
5. Session established: token cached for subsequent requests
6. All proxied requests forward the user's token to backend services

### RBAC Middleware

Console-api applies RBAC checks at the middleware level:
- Standard K8s RBAC: checks user's ClusterRole/Role bindings via
  SubjectAccessReview
- Fine-grained RBAC: when `fine-grained-rbac` MCH component is enabled,
  evaluates MCRA-based permissions for resource filtering
- RBAC endpoints (`/rbac/...`) serve the User Management UI (identities,
  roles, role assignments)

---

## Access Management and RBAC UI

### Access Management Section

The ACM Console includes an "Access Management" section providing:
- **User Management** tab (requires `fine-grained-rbac` MCH component):
  - Identities page: Users, Groups, Service Accounts lists
  - Roles page: ACM role definitions
  - Role Assignments: MCRA wizard for creating/editing MultiClusterRoleAssignments
- **Cluster-level role assignments:** Per-cluster RBAC assignment tab in cluster details

### RBAC UI Components

The RBAC wizard is a multi-step form for creating MCRAs:
1. Select identity (user/group/service account)
2. Select role
3. Select scope (global, cluster sets, clusters, projects)
4. Review and create

**Known issues:** The RBAC wizard has significant state management bugs in
ACM 2.15-2.16 (9+ bugs), including scope alignment errors in the review step,
duplicate clusters in tables, search not working within the wizard, and
intermittent rendering failures at scale.

---

## Fleet Virtualization UI

Fleet Virtualization is a console extension that renders VM management UI:
- VM list (cross-cluster, powered by Search)
- VM details page (via ManagedClusterView + search-cluster-proxy)
- VM actions: start, stop, pause, restart, migrate
- VM tree view: cluster > project > VM hierarchy

Requires both:
1. `cnv-mtv-integrations` MCH component enabled on hub
2. CNV operator installed on spoke clusters

The kubevirt-plugin console extension integrates with ACM's multicluster-sdk
to query VMs across clusters via the Search subsystem.

---

## UI Routes

| Route | Feature |
|---|---|
| `/multicloud/home/overview` | ACM Overview dashboard |
| `/multicloud/home/welcome` | Welcome page |
| `/multicloud/search` | Search |
| `/multicloud/governance` | Governance policies |
| `/multicloud/applications` | Application lifecycle |
| `/multicloud/infrastructure/clusters` | Cluster management |
| `/multicloud/infrastructure/environments` | Environments |
| `/multicloud/infrastructure/automations` | Ansible Automation |
| `/multicloud/credentials` | Credentials management |
| `/multicloud/user-management/identities` | RBAC: Users/Groups/SAs |
| `/multicloud/user-management/roles` | RBAC: Roles |
| `/multicloud/infrastructure/clusters/details/:ns/:name/role-assignments` | Cluster RBAC |

---

## PatternFly Dependency

Console uses Red Hat's PatternFly component library for all UI elements.
PatternFly major version upgrades are a recurring source of regressions:

| Migration | ACM Versions | Impact |
|---|---|---|
| PF4 -> PF5 | 2.14, 2.15 | Dark mode contrast, spacing, sidebar layout |
| PF5 -> PF6 | 2.16, 2.17 | Modal margins, wizard input styling, form spacing |

Each migration generates 10-15 layout/spacing/accessibility regressions that
must be individually fixed.

---

## Configuration

### MCH Component Toggle

Console is enabled by default in MCH. When disabled, all ACM UI disappears.

### console-mce-config ConfigMap

Controls console-api behavior (in MCE namespace):
```yaml
SEARCH_RESULT_LIMIT: "1000"
SEARCH_AUTOCOMPLETE_LIMIT: "10000"
SAVED_SEARCH_LIMIT: "10"
```

### Plugin Registration

```bash
oc get consoleplugins
# Expected: acm, mce listed (and kubevirt-plugin if CNV enabled)
```

If plugins are not listed, feature tabs are absent. Check ConsolePlugin CR
creation and plugin service health.

---

## Dependencies

| Dependency | Why |
|---|---|
| OpenShift Console | Host for dynamic plugins; provides plugin loading framework |
| OpenShift OAuth | Authentication; console-api validates tokens against OCP API |
| search-api | Search queries proxied through Resource Proxy |
| grc-policy-propagator | GRC data proxied through Resource Proxy |
| subscription-controller | Application data proxied through Resource Proxy |
| Observability stack | Grafana/metrics proxied for dashboards |
| MCH/MCE operators | Lifecycle management of plugin deployments |

## What Depends on Console

| Consumer | Impact When Console Is Down |
|---|---|
| ALL UI tests | Every Cypress/Playwright test fails (no UI to test) |
| Search UI | Search page unreachable |
| Governance UI | Policy management unreachable |
| Cluster management UI | Cluster create/import/upgrade unreachable |
| Application UI | App deployment/management unreachable |
| RBAC User Management | Role assignments unreachable |
| Fleet Virtualization | VM management unreachable |
| Observability dashboards | Dashboard widgets unavailable |
