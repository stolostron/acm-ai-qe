# Console Data Flow

How data moves through the console from user action to API response.

---

## UI Rendering Flow

```
Browser loads OCP console
  -> OCP console fetches ConsolePlugin manifests
    -> loads ACM plugin (console-chart-console-v2 service)
      -> React app renders with ACM routes and navigation
        -> user navigates to /multicloud/search (or other ACM page)
          -> React component fetches data via backend API
```

## Console-API Request Proxy Chain (Corrected)

Every console API request follows this 5-hop path. Each hop can fail
independently, and the error at each hop looks different:

```
Browser
  -> OCP Ingress Router (HAProxy) [hop 1]
    -> OCP Console Pod (openshift-console namespace) [hop 2]
      -> ConsolePlugin proxy (routes to ACM plugin backend) [hop 3]
        -> console-api / plugin backend (port 3000) [hop 4]
          -> target service (search-api, grc-propagator, etc.) [hop 5]
```

**Error handling at each hop:**
| Hop | Failure symptom | Root cause layer |
|-----|----------------|-----------------|
| 1 - Ingress Router | Connection refused, 503 | Layer 3 (Network) |
| 2 - OCP Console Pod | 502 Bad Gateway | Layer 9 (OCP operator) |
| 3 - ConsolePlugin proxy | 404 plugin not found, blank tab | Layer 8 (ConsolePlugin CR) |
| 4 - console-api | 500, auth errors, wrong data | Layer 9 or 12 |
| 5 - target service | Empty results, timeout | Layer 9 or 11 |

When diagnosing "403 on console feature", check token forwarding at each
hop. The ConsolePlugin proxy must have `authorization: UserToken` configured.

## API Proxy Flow (Detail)

Most console API calls from hop 4 onward follow this pattern:

```
console-api (plugin backend)
  -> backend/src/routes/proxy.ts doProxy()
    -> constructs Kubernetes API URL
    -> authenticates with forwarded user token or service account token
    -> proxies request to kube-apiserver or target service
    -> returns response to frontend
```

The proxy adds authentication, handles RBAC, and may transform responses.

## Search Query Flow

```
Search page
  -> frontend constructs GraphQL query with filters
  -> POST /api/proxy/search
    -> backend/src/lib/search.ts
      -> constructs search request options
      -> proxies to search-api pod
        -> search-api queries search-postgres
        -> returns results with pagination
      -> backend returns JSON to frontend
  -> frontend renders accordion groups by resource type
```

Bug injection points in this flow:
- `search.ts`: can inject limits, modify query variables
- `search-helper.tsx`: can break query operators (!=, etc.)
- `searchDefinitions.tsx`: can swap URL parameters

## SSE Event Flow (Real-time Updates)

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

## VM Action Flow

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

## Username Resolution Flow

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

## Hub Metadata Flow

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
