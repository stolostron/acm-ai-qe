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

This is the primary data flow for all ACM UI operations. The request
traverses multiple hops before reaching the backend service.

### Request Path (5-Hop Chain)

Every console API request follows this 5-hop path. Each hop can fail
independently, and the error at each hop looks different:

```
Browser
  |
  |  POST /api/proxy/plugin/acm/console/multicloud/proxy/<target>
  v
OCP Ingress Router (HAProxy) [hop 1]
  |
  |  TLS re-encrypt via Route object (openshift-console namespace)
  v
OCP Console Pod (openshift-console namespace) [hop 2]
  |
  |  ConsolePlugin proxy: matches /api/proxy/plugin/acm/console/*
  |  Strips prefix, forwards to plugin backend Service
  |  Injects user's OAuth token (authorization: UserToken)
  v
console-api (BFF) -- console-chart-console-v2 Service, port 3000 [hop 3/4]
  |
  |  1. Authentication Handler: validate OAuth token
  |  2. RBAC Middleware: check user permissions (SubjectAccessReview)
  |  3. Route handler: determine target backend
  v
Resource Proxy [hop 5]
  |
  |  Forward request with user's token to backend service
  |  Upstream URL constructed dynamically using MCH namespace
  v
Backend Service (search-api / grc-propagator / subscription-ctrl / observability)
  |
  |  Process request, apply backend RBAC, return data
  v
Response flows back through the same chain to the browser
```

The OCP Console and ConsolePlugin proxy hops are transparent to
application logic but are distinct failure domains. If the OCP Console
pod is down or the ConsolePlugin is not registered, no ACM feature is
accessible through the UI -- even though all backend services are healthy.

### Error Handling at Each Hop

| Hop | Failure Symptom | Root Cause Layer |
|-----|----------------|-----------------|
| 1 - Ingress Router | Connection refused, 503 | Layer 3 (Network) |
| 2 - OCP Console Pod | 502 Bad Gateway | Layer 9 (OCP operator) |
| 3 - ConsolePlugin proxy | 404 plugin not found, blank tab | Layer 8 (ConsolePlugin CR) |
| 4 - console-api | 500, auth errors, wrong data | Layer 9 or 12 |
| 5 - target service | Empty results, timeout | Layer 9 or 11 |

When diagnosing "403 on console feature", check token forwarding at each
hop. The ConsolePlugin proxy must have `authorization: UserToken` configured.

### Proxy Target Resolution

| URL Prefix | Target Service | Namespace | Port |
|---|---|---|---|
| `/proxy/search` | search-search-api | MCH namespace | 4010 |
| `/proxy/cluster` | cluster-management services | MCH namespace | varies |
| `/proxy/observability` | observability services | open-cluster-management-observability | varies |
| `/proxy/app` | subscription-controller / channel-controller | MCH namespace | varies |
| `/proxy/grc` | grc-policy-propagator | MCH namespace | 8381 |

### Detailed Error Handling

**Browser -> OCP Ingress Router:** Route object misconfigured or HAProxy
overloaded -> connection timeout. Check: `oc get route console -n
openshift-console -o yaml`.

**OCP Console -> ConsolePlugin proxy:** ConsolePlugin CR not registered
or plugin backend Service unreachable -> 502/504. Check: `oc get
consoleplugins`, then `oc get endpoints -n <mch-ns> console-chart-console-v2`.

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

### API Proxy Detail (console-api Onward)

Most console API calls from the console-api onward follow this pattern:

```
console-api (plugin backend)
  -> backend/src/routes/proxy.ts doProxy()
    -> constructs Kubernetes API URL
    -> authenticates with forwarded user token or service account token
    -> proxies request to kube-apiserver or target service
    -> returns response to frontend
```

The proxy adds authentication, handles RBAC, and may transform responses.

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

## 5. WebSocket / SSE Flow (Real-Time Updates)

### WebSocket: Overview Dashboard

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

### SSE: Resource Change Events

```
Browser opens SSE connection to /api/events
  -> backend/src/routes/events.ts
    -> watches Kubernetes API for resource changes
    -> for each event:
      -> eventFilter() checks RBAC permissions
      -> if allowed, pushes event to client via SSE
      -> if filtered out, event is silently dropped
  -> frontend receives SSE event
    -> updates React state
    -> table/page re-renders with new data
```

If eventFilter() drops events for a resource type:
- CREATE events: resource created but never appears in UI table
- UPDATE events: status changes not reflected
- DELETE events: deleted resources still show in UI

This is the hardest failure mode to detect because:
1. The HTTP API call succeeds (201 Created)
2. The resource exists in the backend
3. No error message is generated
4. The UI just "doesn't update"
5. Manual refresh shows the change

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

### Console Backend Search Detail

```
console-api receives proxied request
  -> backend/src/lib/search.ts constructs search request
  -> proxies to search-api pod (HTTP)
    -> search-api executes SQL against search-postgres
    -> returns matching resources with pagination
  -> backend returns results to frontend
  -> frontend renders results in accordion groups by resource type
```

Bug injection points in this flow:
- `search.ts`: can inject limits, modify query variables
- `search-helper.tsx`: can break query operators (!=, etc.)
- `searchDefinitions.tsx`: can swap URL parameters

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

## 8. VM Action Flow

```
User clicks "Stop VM" in Fleet Virt UI
  -> frontend sends action request
  -> POST /api/proxy/vm
    -> backend/src/routes/virtualMachineProxy.ts
      -> determines action (start, stop, migrate, etc.)
      -> proxies to managed cluster's kubevirt API
      -> returns result to frontend
  -> frontend shows success/failure toast
```

Bug injection point: virtualMachineProxy.ts can return fake success
without contacting the managed cluster. The UI shows "VM stopped" but
the VM keeps running.

---

## 9. Username Resolution Flow

```
UI needs to display current user
  -> GET /api/username
    -> backend/src/routes/username.ts
      -> reads user identity from request
      -> returns { name: "kube:admin", ... }
  -> UI displays username in header
```

Bug injection point: username.ts can reverse the name parts
(kube:admin -> admin:kube). RBAC tests that check user identity fail.

---

## 10. Hub Metadata Flow

```
UI needs hub cluster info
  -> GET /api/hub
    -> backend/src/routes/hub.ts
      -> reads MCH, MCE, observability status
      -> returns { localHubName, isObservabilityInstalled, ... }
  -> UI conditionally renders features based on hub metadata
```

Bug injection points: hub.ts can append "-replica" to hub name or
invert the observability flag, causing conditional rendering failures.

---

## 11. Failure Modes Summary

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
