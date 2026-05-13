# Console Subsystem -- Known Issues

Based on 100 Console/UI bugs from ACM 2.12-2.17.

---

## 1. console-mce CrashLoopBackOff (ACM-24965, ACM-25039)

**Versions:** 2.13, 2.14, 2.15 | **Severity:** Major | **Fix:** Code change (PR#5053)

console-mce pod enters CrashLoopBackOff due to readiness/liveness probe
timeouts. Backend connections to search-api or cluster services are not pooled,
causing connection exhaustion under load. Each request opens a new TCP
connection; on large clusters with many managed clusters, probe responses
arrive after the timeout threshold.

**Root cause:** No HTTP connection pooling in console-mce backend. Probe
timeout default (10s) too low for slow backend responses during heavy load.

**Signals:**
- Pod events: `Liveness probe failed`, `Readiness probe failed`
- `oc get pods -n multicluster-engine -l app=console-mce` -- CrashLoopBackOff
- console-mce logs: connection timeout errors to backend services
- MCE feature tabs disappear from UI (clusters, infrastructure)

**Fix:** Connection pooling added + increased probe timeouts (PR#5053, 5071).
Merged in 2.15.1 z-stream.

---

## 2. RBAC Pages Stop Displaying at Scale (ACM-26185)

**Versions:** 2.15, 2.16 | **Severity:** Critical | **Fix:** Code change (PR#5212)

User Management, Group, and Role pages intermittently stop displaying content
when handling large datasets. The React table component fails to complete
rendering when the data set exceeds a threshold, leaving the page blank or
partially rendered.

**Root cause:** Incomplete rendering pipeline in AcmTableStateProvider when
processing large result sets. Race condition between data fetch and table
state initialization.

**Signals:**
- RBAC pages show loading spinner indefinitely or render blank
- Other pages work fine (search, governance, clusters)
- Console-api logs show successful RBAC endpoint responses (data is returned,
  rendering fails client-side)
- Reproducible with 50+ identities or roles

**Workaround:** Page refresh sometimes recovers. Reduce number of identities
displayed via browser filter.

---

## 3. PatternFly 5/6 Upgrade Regressions (11 bugs)

**Versions:** 2.14-2.17 | **Severity:** Normal-Major | **Fix:** Individual PRs

Each PatternFly major version upgrade generates a wave of layout, spacing,
and styling regressions. These are not single bugs but a pattern of breakage
across the console.

### PF5 Regressions (ACM 2.14-2.15)
- **Dark mode text invisible** (ACM-23651): Overview page text uses PF5 theme
  tokens that produce no contrast in dark mode
- **Sidebar layout broken** in governance pages
- **Spacing changes** in table headers, card layouts

### PF6 Regressions (ACM 2.16-2.17)
- **Argo Server modal margins broken** (ACM-28598): Modal dialog renders with
  wrong margins after PF6 CSS changes (PR#5605)
- **Wizard input styling** changes in cluster create/import flows
- **Form spacing** inconsistencies across all wizard-based pages
- **Button alignment** shifts in action menus and toolbars

**Root cause:** PatternFly major versions change CSS variable names, component
APIs, and layout defaults. ACM console code assumes specific PF behavior that
breaks when PF internals change.

**Signals:** Visual regressions (elements overlap, wrong spacing, invisible
text). No functional failure -- data still loads, but presentation is broken.
Check PatternFly version in console image: `oc exec <console-pod> -- npm ls @patternfly/react-core`

---

## 4. Form Validation Failures (21 bugs)

**Versions:** 2.14-2.17 | **Severity:** Normal-Major | **Fix:** Individual PRs

Form validation is the largest single bug category in Console (21% of 100
bugs). Wizard multi-step flows have persistent state management issues.

### Common Patterns

- **Multiselect not reflected in YAML** (ACM-25584): ClusterSet multiselect
  in AppSet wizard updates the form but generated YAML doesn't include
  selections
- **Stale error messages**: Validation error persists after user corrects input.
  Error banner remains visible even after field is valid.
- **Required field enforcement**: Required fields not enforced on specific
  wizard steps, allowing form submission with missing data
- **YAML/form toggle inconsistency**: Switching between form and YAML editor
  loses or corrupts field values
- **attachDefaultNetwork GUI broken** (ACM-24961): Form prop not propagated
  in HCP cluster creation

**Root cause:** React state management in multi-step wizard flows. Form state
is managed across wizard steps with complex dependencies. State updates are
not atomic, leading to race conditions between step transitions, YAML
serialization, and validation checks.

**Signals:** Wizard completes successfully but created resource is missing
fields. Validation error blocks form submission even after correction.
YAML preview shows different values than form fields.

---

## 5. Navigation and Redirect Issues (16 bugs)

**Versions:** 2.14-2.17 | **Severity:** Normal | **Fix:** Individual PRs

After completing wizard flows or actions, the UI redirects to wrong pages
or shows stale breadcrumbs.

### Common Patterns

- **Wrong page after wizard completion**: Cluster create wizard redirects
  to wrong cluster details page
- **Breadcrumb inconsistencies**: Breadcrumb trail doesn't match actual
  navigation path
- **Stale URL parameters**: Query parameters from previous page leak into
  next page, causing wrong filters or empty results
- **Back button behavior**: Browser back button skips wizard steps or
  navigates to unexpected routes

**Root cause:** React Router history management. Wizard components push
routes during step transitions, polluting the browser history stack.
Redirect targets sometimes hardcode routes instead of using dynamic
navigation.

**Signals:** URL doesn't match displayed content. Breadcrumb shows wrong
hierarchy. User lands on unexpected page after completing an action.

---

## 6. Data Display Errors (16 bugs)

**Versions:** 2.14-2.17 | **Severity:** Normal-Major | **Fix:** Individual PRs

Console displays wrong or missing data despite backend returning correct
responses.

### Common Patterns

- **Wrong version shown** (ACM-23897): Upgrade popup shows wrong nodepool
  version for HCP clusters. Version display logic reads wrong field.
- **Missing status icons**: Status column shows empty or wrong icon for
  cluster/policy/application state
- **Truncated text**: Long resource names or labels truncated without
  tooltip, hiding information
- **Stale data after action**: After performing an action (start VM,
  enforce policy), UI doesn't refresh to show new state. Requires manual
  page refresh.
- **Sort state persistence** (ACM-29242): Identities filter shows wrong
  list due to sort state bug in AcmTableStateProvider (PR#5623)

**Root cause:** Mix of frontend rendering bugs (wrong field references,
missing React effect dependencies) and stale cache issues (React Query
cache not invalidated after mutations).

**Signals:** Data in UI doesn't match `oc get` output. Resource shows
stale status. Version numbers are wrong compared to actual resource spec.

---

## 7. RBAC UI Wizard Bugs (9 bugs)

**Versions:** 2.15, 2.16 | **Severity:** Normal-Blocker | **Fix:** Multiple PRs

The RBAC role assignment wizard (MCRA creation/edit) has extensive state
management bugs.

### Specific Issues

- **Global access review scope wrong** (ACM-29966/ACM-28902, Blocker):
  Review section in wizard shows wrong scope for global access role
  assignments. The "placements" label doesn't align with the actual global
  scope (PR#5516).
- **Cluster selection saves all instead of selected**: Wizard step for
  cluster selection saves all available clusters instead of user's selection
- **Search not working in wizard**: Search/filter within cluster or project
  selection steps returns no results
- **Duplicate clusters in tables**: Same cluster appears multiple times in
  selection tables
- **Transient error banners** (ACM-29897): Loading/error state management
  bug shows error banners during multi-assignment edits even though operation
  succeeds (PR#5714)
- **Namespace list latency** (ACM-26218): Shared namespace list for RBAC
  users uses search, which is slow at 500+ clusters

**Root cause:** Fine-grained RBAC is a new feature (TP in 2.14, GA in
2.15-2.16). The MCRA wizard has complex multi-step state with scope
combinations (global, cluster sets, clusters, projects) that interact in
non-obvious ways. State management bugs in wizard step transitions.

**Signals:** MCRA creation fails or creates wrong scope. Review step shows
different selections than user chose. Console-api logs show successful API
calls (failure is client-side rendering).

---

## 8. Hardcoded `local-cluster` References

**Versions:** 2.14-2.17 | **Severity:** Normal | **Fix:** Code changes (ongoing)

Multiple console components hardcode `local-cluster` as the hub cluster
name. When the hub cluster has a custom name (via MCH `spec.overrides.localClusterName`),
these references break.

**Affected areas:**
- Dashboard widgets filtering for hub metrics
- Cluster details page assuming hub is always `local-cluster`
- Search queries filtering hub resources
- Navigation links to hub cluster details

**Signals:** Hub cluster data missing from dashboard. Hub cluster appears
as "Unknown" or is not found. Cluster details page returns 404 for hub.

**Workaround:** Don't rename local-cluster. If already renamed, many UI
features may show incorrect or missing hub data.

---

## 9. Search API Integration Failures Cascade to Multiple Pages

**Versions:** All | **Severity:** High | **Fix:** N/A (architectural)

Console proxies search queries for multiple features. When search-api is
down or slow, the impact cascades:

| Feature | Dependency on Search | Impact When Search Down |
|---|---|---|
| Search UI | Direct | Search page errors |
| Fleet Virt VM list | Via multicluster-sdk | VM list empty |
| Fleet Virt tree view | Via multicluster-sdk | Tree view empty |
| RBAC resource views | Via aggregate API | RBAC pages empty |
| Policy status (some views) | Via resource proxy | Stale policy data |

**Signals:** Multiple seemingly unrelated pages fail simultaneously.
Check search-api first: `oc get pods -n <mch-ns> -l app=search-api`

---

## 10. "Oh no! Something went wrong" Error Page

**Versions:** All | **Severity:** Varies | **Fix:** Debug-specific

Console shows a generic error page with React error boundary catch. Indicates
an unhandled JavaScript exception in the React component tree.

**Common causes:**
1. console-api returns unexpected response shape (missing fields, null where
   object expected)
2. Backend returns HTML error page instead of JSON (proxy misconfiguration)
3. PatternFly component receives props of wrong type after upgrade
4. Resource data missing expected fields (schema change in backend)

**Signals:** Browser console shows React error with component stack trace.
Network tab shows the request that returned unexpected data. Check
console-api pod logs for backend errors.

**Investigation:** Open browser DevTools -> Console tab -> look for React
error boundary stack trace. Identify which component threw. Check network
tab for the failing API request.

---

## Bug Pattern Distribution

| Category | Count | Top Issues |
|---|---|---|
| Form validation | 21 | Multiselect, stale errors, YAML toggle, required fields |
| Navigation/redirect | 16 | Wrong page after wizard, breadcrumbs, stale params |
| Data display errors | 16 | Wrong version, missing icons, truncated text, stale data |
| PatternFly regressions | 11 | Dark mode, modal margins, spacing, wizard input styling |
| RBAC UI | 9 | Wizard scope, cluster selection, search, duplicates |
| console-mce crashes | 3 | Probe timeouts, connection pooling |
| Other rendering | ~24 | Error pages, plugin loading, WebSocket, misc |

## Root Cause Themes

1. **PatternFly major upgrades:** Each PF version change breaks layout assumptions across the console
2. **Wizard state management:** Multi-step forms with complex dependencies have race conditions between steps
3. **Hardcoded `local-cluster`:** Custom hub names break multiple components
4. **Search as single dependency:** Multiple features depend on search-api through the Resource Proxy; search outage cascades
5. **console-mce probe sensitivity:** Backend slowness triggers probe failures, causing CrashLoopBackOff and feature tab disappearance
6. **Fine-grained RBAC maturity:** New feature (2.14 TP, 2.15-2.16 GA) with extensive wizard and state management bugs

## Fix Pattern Distribution (from Console PRs)

| Pattern | Frequency | Example |
|---|---|---|
| UI_COMPONENT_FIX | 7 PRs | Component prop corrections, redirect paths, a11y fixes |
| CODE_LOGIC_FIX | 4 PRs | Connection pooling, table state, filter persistence |
| ERROR_HANDLING_FIX | 1 PR | Transient error banner suppression during edits |

## Key Reference Bugs

| Key | Summary | Severity | Status |
|---|---|---|---|
| ACM-24965 | console-mce CrashLoopBackOff | Major | Fixed (PR#5053) |
| ACM-26185 | RBAC pages stop displaying at scale | Critical | Fixed (PR#5212) |
| ACM-29966 | RBAC wizard placements label wrong | Blocker | Fixed (PR#5516) |
| ACM-28598 | Argo Server modal margins (PF6) | Normal | Fixed (PR#5605) |
| ACM-23897 | Wrong nodepool version in upgrade popup | Major | Fixed |
| ACM-23651 | Overview dark mode text invisible (PF5) | Normal | Fixed |
| ACM-29897 | RBAC edit transient error banners | Normal | Fixed (PR#5714) |
| ACM-29242 | Identities filter wrong list | Normal | Fixed (PR#5623) |
| ACM-24961 | attachDefaultNetwork GUI broken for HCP | Normal | Fixed (PR#5067) |
| ACM-25584 | ClusterSet multiselect in AppSet wizard | Normal | Fixed |
| ACM-26218 | RBAC namespace list slow at scale | Normal | Ongoing |
| ACM-28902 | Global access review scope wrong | Blocker | Fixed (PR#5516) |
