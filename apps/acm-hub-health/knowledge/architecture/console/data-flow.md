# Console Subsystem -- Data Flow

## End-to-End Request Flow

```
Browser                    OCP Console              ACM/MCE Plugin Pods
  |                            |                          |
  |-- navigate to ACM page --> |                          |
  |                            |-- load plugin bundle --> |
  |                            |<-- JS bundle (Module Federation)
  |<-- render ACM page --------|                          |
  |                                                       |
  |                    console-api (BFF)          Backend Services
  |                         |                          |
  |-- REST/GraphQL -------> |                          |
  |                         |-- OAuth token check ---> | OCP API
  |                         |<-- token valid --------- |
  |                         |-- Resource Proxy ------> | search-api
  |                         |                          | grc-propagator
  |                         |                          | subscription-ctrl
  |                         |                          | observability
  |                         |<-- response ------------ |
  |<-- JSON response ------- |                          |
```

---

## 1. Authentication Flow

### Initial Login

1. User opens OCP Console URL
2. OCP OAuth server redirects to login page (LDAP, HTPasswd, OIDC, etc.)
3. User authenticates against configured Identity Provider
4. OAuth server issues access token
5. Token stored in browser session (cookie or Authorization header)
6. All subsequent requests carry this token

### Token Passthrough in console-api

1. Browser sends request to console-api with user's OAuth token
2. console-api's Authentication Handler validates token via
   `TokenReview` against OCP API server
3. Session Manager caches validated session for subsequent requests
4. For proxied requests, console-api forwards the user's original token
   to backend services (search-api, GRC, etc.)
5. Backend services perform their own RBAC checks using the forwarded token

**Failure: OAuth misconfiguration**
- OCP OAuth server misconfigured -> redirect loop, login fails
- Expired/invalid token -> 401 on proxied requests
- IDP unreachable -> cannot authenticate new sessions
- **Detection:** Check `oc get oauth cluster -o yaml`, OCP console pod logs

---

## 2. Plugin Loading Flow

### On OCP Console Startup

1. OCP Console pod reads registered `ConsolePlugin` CRs
2. For each enabled plugin, fetches `plugin-manifest.json` from plugin service
3. Plugin manifests declare available extensions (routes, nav items, flags)
4. Extensions registered in OCP Console's extension registry

### On Navigation to ACM Page

1. User clicks ACM navigation item (e.g., "All Clusters")
2. OCP Console's route handler resolves to ACM plugin extension
3. Webpack Module Federation runtime fetches the plugin's JS chunk
4. React component tree mounts within OCP Console's shell
5. ACM component makes REST/GraphQL calls to console-api

**Failure: Plugin not registered**
- `ConsolePlugin` CR missing -> entire feature section absent from navigation.
  No error. No "ACM" tab in side nav.
- Plugin pod down -> manifest fetch fails -> features absent on next refresh.
  Features cached in browser may still render until cache expires.
- Plugin service unreachable -> 502/504 from OCP Console proxy.
- **Detection:** `oc get consoleplugins` -- verify `acm` and `mce` listed.
  Check plugin pod health: `oc get pods -n <mch-ns> -l app=console-chart-console-v2`

---

## 3. Console-API Request Proxy Chain

This is the primary data flow for all ACM UI operations.

### Request Path
```
Browser
  |
  |  REST/GraphQL request (e.g., GET /multicloud/api/v1/proxy/search)
  v
console-api (BFF)
  |
  |  1. Authentication Handler: validate OAuth token
  |  2. RBAC Middleware: check user permissions (SubjectAccessReview)
  |  3. Route handler: determine target backend
  v
Resource Proxy
  |
  |  Forward request with user's token to backend service
  v
Backend Service (search-api / grc-propagator / subscription-ctrl / observability)
  |
  |  Process request, apply backend RBAC, return data
  v
Resource Proxy
  |
  |  Pass response back
  v
console-api
  |
  |  Serialize response, add cache headers
  v
Browser
  |
  |  React components render data
  v
User sees UI
```

### Proxy Target Resolution

| URL Prefix | Target Service | Namespace | Port |
|---|---|---|---|
| `/proxy/search` | search-api | MCH namespace | 4010 |
| `/proxy/cluster` | cluster-management services | MCH namespace | varies |
| `/proxy/observability` | observability services | open-cluster-management-observability | varies |
| `/proxy/app` | subscription-controller / channel-controller | MCH namespace | varies |
| `/proxy/grc` | grc-policy-propagator | MCH namespace | 8381 |

### Error Handling at Each Hop

**Browser -> console-api:** Network error, CORS failure, or console-api pod
down -> browser shows "Oh no! Something went wrong" error page or connection
refused.

**console-api -> Auth check:** Invalid/expired token -> 401 returned to browser,
user redirected to login.

**console-api -> RBAC Middleware:** User lacks permission -> 403 returned.
Fine-grained RBAC evaluation failure -> 500 (logged in console-api).

**Resource Proxy -> Backend:** Backend pod down -> 502/503 from proxy.
Backend slow -> proxy timeout (configurable, default 30s). Backend returns
error -> proxy passes error through to browser.

**Backend -> Response:** Data processing error -> 500 from backend.
Empty result set -> empty response (not an error, but UI may show "no results").

---

## 4. RBAC UI Data Flow

### User Management Page

```
Browser
  |-- GET /multicloud/api/v1/rbac/identities --> console-api
  |                                                  |
  |                           console-api queries:   |
  |                           - OCP Users (users.user.openshift.io)
  |                           - OCP Groups (groups.user.openshift.io)
  |                           - ServiceAccounts (core/v1)
  |                           - ClusterRoleBindings (for role resolution)
  |                           - MCRAs (for current assignments)
  |                                                  |
  |<-- JSON: identity list with roles/scopes --------|
```

### MCRA Creation Flow (Role Assignment Wizard)

```
Browser: User completes wizard
  |
  |-- POST /multicloud/api/v1/rbac/role-assignments --> console-api
  |                                                       |
  |                         console-api creates:          |
  |                         - MultiClusterRoleAssignment CR
  |                                                       |
  |                         MCRA Operator reconciles:     |
  |                         - Creates ClusterPermission CRs
  |                         - ClusterPermission creates ManifestWork
  |                         - ManifestWork deploys RBAC to spokes
  |                                                       |
  |<-- 201 Created (MCRA resource) -----------------------|
```

**Failure: MCRA at scale**
- RBAC pages stop displaying intermittently when handling large datasets
  (ACM-26185). console-api returns partial data, React rendering incomplete.
- Concurrent PATCH requests to MCRAs cause controller panics from stale
  in-memory state (ACM-24737).
- **Detection:** Check console-api logs for RBAC endpoint errors. Check
  MCRA status conditions: `oc get mcra -A -o yaml`

---

## 5. WebSocket Flow (Dashboard Updates)

### Overview Dashboard

```
Browser
  |
  |-- WebSocket upgrade request --> console-api
  |                                    |
  |                    WebSocket Manager establishes connection
  |                                    |
  |       (on interval or event)       |
  |                                    |-- query backend services
  |                                    |<-- updated data
  |<-- WebSocket push: dashboard data --|
  |
  |  Dashboard Renderer updates UI
```

Used for:
- Overview dashboard widgets (cluster status, compliance summary)
- Real-time status updates during cluster operations

**Failure:** WebSocket connection drops -> dashboard shows stale data, may
show "reconnecting" indicator. Usually recovers on reconnect. Persistent
failure indicates console-api or network issues.

---

## 6. Search Query Flow (via Console)

```
Browser: User types search query
  |
  |-- POST /multicloud/api/v1/proxy/search
  |   Body: { query: "kind:Pod namespace:default" }
  |
  v
console-api (Resource Proxy)
  |
  |-- POST search-api:4010/searchapi/graphql
  |   Headers: Authorization: Bearer <user-token>
  |   Body: GraphQL query with filters
  |
  v
search-api
  |-- RBAC filter: determine user's visible clusters/namespaces
  |-- Translate to PostgreSQL query
  |-- Execute against search-postgres
  |
  v
  |<-- JSON: filtered search results
  |
  v (back through proxy)
Browser: render search results table
```

---

## 7. Fleet Virt VM Query Flow

```
kubevirt-plugin (ACM Console extension)
  |
  |-- multicluster-sdk.listResources({ kind: "VirtualMachine" })
  |
  v
multicluster-sdk
  |-- GraphQL query to search-api (via console-api proxy)
  |
  v
search-api
  |-- RBAC-filtered query for VirtualMachine resources
  |-- Returns: VM metadata from all permitted clusters
  |
  v (back through proxy + SDK)
kubevirt-plugin
  |-- Renders VM list / tree view
  |-- For VM details: uses search-cluster-proxy for direct spoke queries
```

**Failure:** Search down -> VM list empty, no error message. Fine-grained
RBAC misconfigured -> partial or empty VM list. search-cluster-proxy
unavailable -> VM details/actions fail.

---

## 8. Failure Modes Summary

### Per-Hop Impact

| Component Down | Immediate Effect | User Sees |
|---|---|---|
| OCP Console pod | No web UI at all | Connection refused |
| ACM plugin pod | ACM tabs disappear | Missing nav items |
| MCE plugin pod | MCE tabs disappear (clusters, infra) | Missing nav items |
| console-api | All ACM API calls fail | "Oh no! Something went wrong" |
| Resource Proxy target (e.g., search-api) | That feature's data unavailable | Empty page or error for that feature |
| OAuth server | Cannot authenticate | Login loop |
| WebSocket connection | Dashboard stale | Old data displayed |

### Cascading Failures

1. **search-api down** -> Search UI empty, Fleet Virt VM list empty, RBAC
   resource views empty (three features affected through one backend)
2. **console-api down** -> ALL UI features broken (single point of failure
   for ACM UI)
3. **OCP Console pod restart** -> temporary UI outage, plugins re-fetched,
   sessions may need re-authentication
4. **Backend service slow** -> console-mce probe timeouts -> CrashLoopBackOff
   -> MCE features disappear (ACM-24965 pattern)
