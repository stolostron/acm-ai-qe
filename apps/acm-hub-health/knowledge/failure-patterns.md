# Known Failure Patterns & Correlation Heuristics

Reference guide for cross-component failure patterns observed in ACM hubs.
Use these as heuristics to guide your investigation, not as deterministic rules.
Always verify with actual cluster state before concluding.

---

## How to Use This File

When you find multiple issues during a health check, consult these patterns
to look for connections. A pattern that matches your observations is a
hypothesis to investigate, not a conclusion to report. Verify before stating.

---

## Platform-Level Patterns

### MCH Stuck Progressing + Component Pods Failing

**Symptoms**: MCH phase is not "Running", specific component shows
ComponentNotReady or degraded condition, pods in that component's namespace
are not Running.

**Heuristic**: The failing component is usually the blocker. MCH waits for
all components before reporting healthy. Find the specific component that's
failing, fix it, and MCH will recover.

**Investigate**: Check `.status.components` in MCH to identify which component
is stuck. Then check that component's pods and logs.

### MCH Shows OldComponentNotRemoved

**Heuristic**: Usually transient during an upgrade. The old version's resources
haven't been cleaned up yet. Wait 10-15 minutes and recheck. If it persists,
something is stuck in the cleanup process.

### CSVs Not Succeeded + Pods Failing

**Symptoms**: `oc get csv -n <mch-namespace>` shows CSVs not in
Succeeded phase. Pods in the namespace are CrashLooping or not starting.

**Heuristic**: An operator upgrade is stuck. The CSV can't complete because
the operator pod won't start. Check operator pod logs for the root cause
(image pull failure, resource constraints, webhook issues).

### Nodes NotReady + Pods Pending

**Symptoms**: One or more nodes show NotReady condition. Multiple pods across
namespaces are in Pending state.

**Heuristic**: This is an infrastructure problem, not an ACM problem. Pod
scheduling fails because nodes aren't available. Fix the node issue first.
ACM components will recover once pods can be scheduled.

**Investigate**: `oc describe node <node>` for conditions and events.
`oc adm top nodes` for resource pressure.

---

## Managed Cluster Patterns

### Multiple Managed Clusters Show Unknown/NotReady

**Symptoms**: Several managed clusters simultaneously change to Unknown or
NotReady status.

**Heuristic**: If multiple clusters go Unknown at the same time, the problem
is almost certainly hub-side (networking, API server, or registration
controllers), not individual cluster failures. Independent spoke failures
don't usually happen simultaneously.

**Investigate**: Check hub API server health, registration-operator pods,
and any recent network policy changes on the hub.

### Single Managed Cluster Unknown, Others Fine

**Symptoms**: One managed cluster shows Unknown, all others are healthy.

**Heuristic**: Likely a spoke-side issue -- klusterlet can't reach the hub,
or the spoke cluster itself is down. Check the lease renewal for that cluster's
namespace.

**Investigate**: `oc get lease -n <cluster-namespace>` -- if the lease is
stale, the klusterlet isn't renewing it.

### Managed Cluster Joined=False

**Symptoms**: Managed cluster shows JOINED=False.

**Heuristic**: The cluster was registered but the klusterlet never completed
the join handshake. Could be klusterlet bootstrap failure, networking, or
certificate issues on the spoke side.

---

## Cross-Component Correlation Patterns

### Search Broken + Observability Broken (Simultaneously)

**Symptoms**: Search pods are failing AND observability pods are failing at
the same time. Both were working before.

**Heuristic**: Check shared infrastructure first. Both use persistent storage
(PVCs). If the storage backend (storage class, CSI driver) is having issues,
both components fail together. Also check if node pressure is causing both
to be evicted.

**Investigate**: `oc get pvc -n <mch-namespace>` and
`oc get pvc -n open-cluster-management-observability`. Check if PVCs are Bound
and if the storage class is healthy.

### Search Empty Results + Managed Clusters Unknown

**Symptoms**: Search returns no results or partial results. Some managed
clusters show Unknown status.

**Heuristic**: These are likely the same problem. Search-collector runs as
an addon on spokes. If the spoke is disconnected (Unknown), the collector
can't send data. The missing search results are FROM the disconnected clusters.

**Investigate**: Compare which clusters are Unknown with which clusters have
missing search results. If they match, fix the connectivity issue.

### Multiple Add-ons Unavailable on Same Spoke

**Symptoms**: Several managed cluster addons (search-collector, governance,
metrics-collector) all show unavailable for the same spoke cluster.

**Heuristic**: If multiple independent addons fail on the same spoke, the
problem is with the spoke's klusterlet connectivity or the addon-manager's
ability to reach that spoke, not with individual addons.

**Investigate**: Check klusterlet health on that spoke. Check if the addon-manager
pod on the hub is healthy.

### Console 500 Errors Across All Features

**Symptoms**: Multiple UI features show 500 errors -- governance pages,
search pages, cluster pages all broken.

**Heuristic**: Console-api is the single backend for all UI features. If
it's down, everything breaks. Check console-api pod first before investigating
individual feature backends.

**Investigate**: `oc get pods -n <mch-namespace> -l app=console-api`

---

## Storage-Related Patterns

### Component CrashLoop + PVC Full

**Symptoms**: A component pod is in CrashLoopBackOff. Container logs show
write errors or "no space left on device."

**Heuristic**: The PVC backing that component is full. Common for:
- Search (redisgraph/postgres) -- index grows with cluster count
- Observability (thanos components) -- metrics volume grows over time
- etcd -- if the cluster is large

**Investigate**: `oc get pvc -n <namespace>`. Check PV utilization.

### Observability Thanos-Store CrashLoop

**Symptoms**: `observability-thanos-store-shard-*` pods are CrashLooping or
show high restart counts. Other Thanos components may also be failing.

**Heuristic**: Two common causes:
1. S3/object storage configuration issue -- thanos-store connects to external
   S3 (or Minio) and crashes if the connection fails
2. BucketStore InitialSync failure -- block fetcher panics on corrupted or
   oversized block metadata in the object store. This causes a CrashLoop
   that can accumulate hundreds or thousands of restarts before self-recovering

**Investigate**: Check thanos-store logs for S3 connection errors OR
BucketStore/InitialSync stack traces. Check if the pod is currently Running
with a high restart count (self-recovered) vs actively CrashLooping.
A pod with 1000+ restarts but currently Running and stable for days is a
historical issue, not an active one -- note it but don't alarm.

**Verify**: `oc get pods -n open-cluster-management-observability | grep thanos-store`

---

## Upgrade-Related Patterns

### Components Degraded After OCP Upgrade

**Symptoms**: ACM components start failing shortly after an OCP upgrade.
Pods restarting, webhooks failing.

**Heuristic**: OCP upgrades restart all pods. Some ACM components may have
issues with the new OCP version (API deprecations, cert rotations during
upgrade, or temporary scheduling disruptions).

**Investigate**: Check if the OCP upgrade is still in progress
(`oc get clusterversion` -- Progressing=True). If yes, wait for it to
complete. If completed, check which specific ACM components are failing.

### ACM Upgrade Stuck (MCH Progressing)

**Symptoms**: MCH shows phase Progressing for an extended period after
initiating an ACM upgrade.

**Heuristic**: Check which component is blocking the upgrade. MCH upgrades
components sequentially. A failing component blocks the entire upgrade.

**Investigate**: `oc get mch -o yaml` -- check `.status.components` for
the component that's not ready. Check that component's pods and events.

---

## Certificate Patterns

### Intermittent Failures Across Multiple Components

**Symptoms**: Multiple components experience intermittent connection failures.
Errors mention TLS, certificate, or x509 in logs. Not all requests fail --
some succeed, some don't.

**Heuristic**: A certificate has expired or is about to expire. Internal
communication uses TLS, and expired certs cause intermittent failures because
some cached connections still work while new ones fail.

**Investigate**: Check cert secrets in the MCH namespace. Look for
secrets of type `kubernetes.io/tls` and check their expiration.

### Webhook Failures After Cert Rotation

**Symptoms**: Resource creation/update fails with "connection refused" or
"TLS handshake failure" errors mentioning webhook.

**Heuristic**: The webhook's serving cert was rotated but the
ValidatingWebhookConfiguration or MutatingWebhookConfiguration still
references the old CA bundle.

**Investigate**: Check webhook configurations and compare their CA bundles
with the current serving cert.

---

## Resource Pressure Patterns

### OOMKilled Pods

**Symptoms**: Pods show OOMKilled in their last termination reason.
`oc get pods -A -o json | jq -r '.items[] | select(.status.containerStatuses[]?.lastState.terminated.reason=="OOMKilled")'`

**Heuristic**: The pod's memory limit is too low for the workload. Common
in large-scale clusters for:
- search-indexer (large index from many clusters)
- observability components (high cardinality metrics)
- governance propagator (many policies across many clusters)

**Investigate**: Check the pod's resource limits vs actual usage.
`oc adm top pod -n <namespace>` shows current usage.

---

---

## Namespace Gotcha: MCH Not in Expected Namespace

**Symptoms**: Running `oc get pods -n open-cluster-management` returns no
resources or very few pods (because the MCH is in a different namespace),
yet MCH reports all components as Available.

**Heuristic**: The MCH was installed in a non-default namespace (e.g., `ocm`).
All ACM hub pods live in the MCH namespace, which may differ from
`open-cluster-management`. This is NOT a problem -- it's just a different
installation choice.

**Resolution**: Always use `oc get mch -A` first to discover the actual
MCH namespace. Use that namespace for all subsequent pod checks.

---

## Anti-Patterns: Things That Look Related But Usually Aren't

### Different Components Failing for Different Reasons

If search-indexer is OOMKilled and governance-propagator has a webhook error,
these are probably independent issues despite both being in the same namespace.
Don't force a correlation -- investigate each independently.

### Spoke Addon Failure vs Hub Component Failure

If an addon on a spoke is unhealthy but the hub-side component for that feature
is fine, the problem is spoke-side (klusterlet, node resources, networking),
not hub-side. Don't chase the hub component.

### Pod Restart Count > 0 Is Not Always a Problem

Pods restart during upgrades, node maintenance, and normal operations. A
restart count of 1-3 with the pod currently Running and recent restart time
(during a known maintenance window) is not a health issue. High restart count
with recent restarts and short uptime IS a problem (CrashLoop).

---

## NetworkPolicy Blocking Inter-Pod Communication

**Symptoms**: All pods Running and Ready but specific inter-service
communication fails. Search-api can't reach search-postgres. Console backend
can't reach search-api. Features that depend on the blocked path return
errors or empty results.

**Heuristic**: ACM does NOT create NetworkPolicies. Any NetworkPolicy in an
ACM namespace (`<mch-ns>`, `multicluster-engine`, `open-cluster-management-hub`)
was added externally -- by an admin, a policy, or a cluster operator. It may
silently block traffic that ACM expects to flow freely.

**Investigate**:
```bash
oc get networkpolicy -n <mch-ns> --no-headers
oc get networkpolicy -n multicluster-engine --no-headers
oc get networkpolicy -n open-cluster-management-hub --no-headers
# If any found, describe to see what traffic is blocked
```

**Cross-ref**: Trap 11 in `common-diagnostic-traps.md`

---

## Webhook Service Unreachable

**Symptoms**: Resource creation, update, or deletion fails with errors like
`failed calling webhook` or `connection refused`. Operations on a specific
CRD type ALL fail. The operator managing the resource may be healthy.

**Heuristic**: Most ACM webhooks have `failurePolicy: Fail`. If the webhook
service pod is down, crashed, or has expired TLS certs, the API server rejects
ALL operations on resources validated by that webhook. The operator may be
perfectly healthy -- it's the webhook admission that's blocking.

**Investigate**:
```bash
# Check which webhooks exist and their failure policies
oc get validatingwebhookconfigurations -o json | jq '.items[] | {name: .metadata.name, rules: [.webhooks[].rules[].resources], failurePolicy: .webhooks[0].failurePolicy}'
# Check the webhook service endpoints
oc get validatingwebhookconfiguration <name> -o jsonpath='{.webhooks[0].clientConfig.service}'
```

**Cross-ref**: `webhook-registry.yaml` for expected webhook configurations,
Trap 10 for Hive webhook specifically

---

## Addon-Framework Cascade (Mass Addon Failure)

**Symptoms**: Multiple addons fail across multiple clusters simultaneously.
Search-collector, governance-policy-framework, application-manager all
showing Unavailable on the same set of clusters (or all clusters).

**Heuristic**: When the SAME set of addons fail on MULTIPLE clusters at the
same time, the root cause is almost always a single hub-side failure:
1. **addon-manager pod down** -- No addon deployments or health monitoring
2. **work-agent connectivity lost** -- ManifestWorks not applied on spokes
3. **Spoke connectivity lost** -- All addons on that spoke affected

**Investigate**: Check hub-side components FIRST:
```bash
# addon-manager
oc get pods -n open-cluster-management-hub -l app=clustermanager-addon-manager-controller
# If healthy, check per-cluster connectivity
oc get managedclusters | grep -v True
```

**Cross-ref**: Trap 7 in `common-diagnostic-traps.md`

---

## Console Plugin Rendering Failure

**Symptoms**: Feature tabs present in console navigation but render with
loading spinners, blank content, or JavaScript errors. Not missing entirely
-- present but broken.

**Heuristic**: The ConsolePlugin CR is registered (so the tab appears in
navigation), but the plugin's backend pod is unhealthy. The OCP console
loads the plugin shell successfully but fails to fetch content at runtime.

Different from "tabs missing" (Trap 2): tabs present means the plugin is
registered; broken rendering means the plugin backend is down.

**Investigate**:
```bash
# Check ConsolePlugin CRs and their backend services
oc get consoleplugins -o json | jq '.items[] | {name: .metadata.name, service: .spec.backend.service}'
# Check the backend pods
oc get pods -n <mch-ns> -l app=console-chart-console-v2
oc get pods -n multicluster-engine -l app=console-mce-console
```

**Cross-ref**: Trap 13 in `common-diagnostic-traps.md`

---

## ResourceQuota Blocking Pod Restart

**Symptoms**: Pods gradually disappear from ACM namespaces. Services degrade
over time. Deployment shows desired replicas but 0 available. No pod restart
events because the pod isn't being created.

**Heuristic**: ACM does NOT create ResourceQuotas. Any ResourceQuota in an
ACM namespace limits what Kubernetes can schedule. When a pod crashes, the
replacement can't be created if it would exceed the quota.

**Investigate**:
```bash
oc get resourcequota -n <mch-ns> --no-headers
oc get resourcequota -n multicluster-engine --no-headers
# If found, check limits
oc describe resourcequota -n <mch-ns>
```

**Cross-ref**: Trap 9 in `common-diagnostic-traps.md`
