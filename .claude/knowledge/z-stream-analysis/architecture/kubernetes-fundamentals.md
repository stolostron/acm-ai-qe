# Kubernetes Fundamentals for Failure Analysis

Key Kubernetes concepts that affect how test failures are classified.

---

## Pod Lifecycle and Failure Modes

A pod can be in these states:
- **Running**: all containers started and passing probes
- **Pending**: waiting for scheduling (resource constraints, node affinity)
- **CrashLoopBackOff**: container exits repeatedly, kubelet backs off restarts
- **ImagePullBackOff**: can't pull container image
- **Terminating**: pod is being deleted

For failure classification:
- Pod in CrashLoopBackOff = INFRASTRUCTURE (unless caused by our code bug)
- Pod in Pending = INFRASTRUCTURE (resource pressure, scheduling failure)
- Pod Running but returning errors = could be PRODUCT_BUG or INFRASTRUCTURE

## Deployment Reconciliation

Deployments maintain desired replica count. If a pod crashes, the deployment
controller creates a new one. However:
- ResourceQuotas can block new pod creation
- Node resource pressure can prevent scheduling
- ImagePullBackOff prevents container start

The deployment shows "Available" even if pods are restarting, as long as
minAvailable is met. Check `restarts` count for crash loops.

## Services and Networking

Services route traffic to pods via label selectors. NetworkPolicies can
block pod-to-pod communication even when both pods are healthy.

For failure classification:
- Both pods Running but can't communicate = check NetworkPolicies (INFRASTRUCTURE)
- Service exists but no endpoints = pods don't match the service selector

## Custom Resource Definitions (CRDs)

CRDs extend the Kubernetes API. If a CRD is missing:
- `oc apply` fails with "resource mapping not found"
- `oc get <resource>` fails with "the server doesn't have a resource type"

CRD absence = INFRASTRUCTURE. The operator that registers the CRD is not
installed or not healthy.

## Webhooks

Validating/mutating webhooks intercept API requests. If a webhook service
is unavailable:
- failurePolicy=Fail: ALL requests to that resource type fail with 500
- failurePolicy=Ignore: requests proceed without validation

Webhook failures look like product bugs (500 errors) but are infrastructure.
Check: `oc get validatingwebhookconfigurations` and verify the service exists.

## Server-Sent Events (SSE)

SSE is a mechanism where the server pushes updates to the client over a
long-lived HTTP connection. ACM console uses SSE (events.ts) to deliver
real-time updates.

If SSE events are dropped for a resource type:
- The API call succeeds (201 Created)
- The resource exists in the backend
- The UI table does NOT update
- The user must manually refresh

This looks like "element not found in table" (same as stale selector) but
is actually a data delivery issue. Very hard to distinguish without
inspecting the SSE event pipeline.

## Resource Quotas

ResourceQuotas limit resource consumption per namespace. If a quota is
exceeded, new pod creation fails even though existing pods keep running.
This creates a slow-motion degradation: components fail one by one as
pods restart and can't come back.

## Operator Pattern

Operators watch custom resources and reconcile desired state. Key behaviors:
- Reconciliation loop runs periodically (typically every few minutes)
- If the operator pod itself is down, reconciliation stops
- Operators typically reconcile deployments, services, and their own CRs
- Operators do NOT typically reconcile: secrets content, configmaps content,
  NetworkPolicies, ResourceQuotas, or resources owned by other operators
