# Application Lifecycle -- Known Issues

Based on 102 ALC bugs from ACM 2.12-2.17.

---

## 1. Pull Model Apps Stuck "Refreshing" (ACM-22654)

**Versions:** 2.15, 2.16 | **Severity:** Normal | **Fix:** Code change (PR#190)

Pull model ArgoCD applications stuck in "Refreshing" state indefinitely.
multicluster-operators-application controller has status aggregation bug --
never transitions to a final state.

**Root cause:** Controller status aggregation logic doesn't handle all
ArgoCD application health states, leaving the MulticlusterApplicationSetReport
in a perpetual "refreshing" state.

**Signals:** Application dashboard shows "Refreshing" with no progress.
Check `multicluster-operators-application` pod logs for status aggregation
errors.

---

## 2. Time Window Causes Application Manager Crash (ACM-25667)

**Versions:** 2.15, 2.16 | **Severity:** Important | **Fix:** Code change

Subscription with time window configuration causes application-manager pod
to crash with nil pointer dereference during time parsing.

**Root cause:** Nil pointer in time window parsing logic. When time window
spec contains edge-case formats, the parser dereferences a nil time struct.

**Signals:** `panic: runtime error: invalid memory address or nil pointer
dereference` in application-manager logs. Pod enters CrashLoopBackOff.
**Workaround:** Remove time window from subscription, redeploy.

---

## 3. GitOps Operator Detection Fails for Non-Default NS (ACM-18820)

**Versions:** 2.14, 2.15 | **Severity:** Important | **Fix:** Code change (PR#4328)

Console shows "GitOps operator required" error even when OpenShift GitOps
operator is installed -- if installed in a namespace other than the default
`openshift-gitops`.

**Root cause:** Operator detection logic hardcodes namespace check. When GitOps
operator is installed in a custom namespace, detection fails.

**Signals:** Console shows "GitOps operator is required" banner on ArgoCD
application creation page. `oc get csv -A | grep gitops` shows operator installed
and Succeeded.

---

## 4. AppSet Destination Namespace Overridden (ACM-25479)

**Versions:** 2.15, 2.16 | **Severity:** Normal | **Fix:** Code change

Pull model ApplicationSet controller overwrites user-specified destination
namespace with its own value. Applications deployed to wrong namespace on spoke.

**Root cause:** Controller overwriting user's namespace in ApplicationSet spec
during reconciliation.

**Signals:** Resources appear in unexpected namespace on spoke. Application
status shows correct cluster but wrong namespace.

---

## 5. 503 Service Unavailable via cluster-proxy (ACM-29934)

**Versions:** 2.16, 2.17 | **Severity:** Critical | **Fix:** Code change

Fetching OpenAPI schema via cluster-proxy returns 503 Service Unavailable.
Breaks application resource discovery and validation against spoke APIs.

**Root cause:** cluster-proxy integration path has routing issue for OpenAPI
endpoints.

**Signals:** 503 errors in console when interacting with application resources
via cluster-proxy. Application creation wizards may fail validation.

---

## 6. Subscription Status Not Updating

**Versions:** 2.15, 2.16 | **Severity:** Normal | **Fix:** Various

Multiple issues cause subscriptions to remain in stale status:
- Subscription phase stuck at empty instead of "Propagated"
- Status not updated after channel content changes
- ManifestWork status not reflected back to subscription

**Signals:** Subscription shows old status. `oc get subscriptions.apps -A`
shows stale phase. Manual `oc get manifestwork` shows applied resources differ.

---

## 7. Helm Version Incompatibility

**Versions:** 2.15+ | **Severity:** Normal | **Fix:** Code change

Subscription controller uses specific Helm library versions that may be
incompatible with newer Helm chart features. Charts using newer Helm
capabilities fail to resolve.

**Signals:** Helm subscription fails with chart rendering errors.
Channel connectivity is fine but content resolution fails.

---

## Bug Pattern Distribution

| Category | Count | Top Issues |
|---|---|---|
| GitOps/ArgoCD reconciliation | 42 | Pull model stuck, ManifestWork not deleted, cluster secret sync |
| Subscription sync | 27 | Time window crash, Helm version, status not updating |
| Channel management | 5 | ObjectBucket Kustomization, channel type filtering |
| AppSet rendering | 4 | YAML paste not setting fields, remote namespace editing |
| Build pipeline / Konflux | ~24 | EC compliance, stale Tekton bundles |

## Root Cause Themes

1. **Pull model immaturity:** Status aggregation for pull model ArgoCD is incomplete
2. **Nil pointer safety:** Missing nil checks in time parsing and template processing
3. **Hardcoded assumptions:** Operator detection relies on default namespace locations
4. **Controller overwrites:** Reconciliation overwrites user-specified fields
5. **External dependency brittleness:** OpenShift GitOps operator version/location matters
