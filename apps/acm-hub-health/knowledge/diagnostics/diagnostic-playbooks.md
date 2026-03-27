# Diagnostic Playbooks

Per-subsystem investigation procedures for deep dives. Use these when you've
identified an issue in a specific area and need to dig deeper. These are
reference procedures -- adapt them to what you actually find on the cluster.

---

## MCH / MCE Lifecycle

**When to use**: MCH phase is not Running, MCE is not Available, or upgrade
appears stuck.

**Investigation steps**:

1. Get MCH full status
   ```
   oc get mch -A -o yaml
   ```
   Look at `.status.phase`, `.status.conditions`, and `.status.components`.
   Identify which specific component is blocking.

2. Get MCE full status
   ```
   oc get multiclusterengines -A -o yaml
   ```
   Check `.status.conditions` for degraded or progressing.

3. Check operator pods (use the MCH namespace discovered in Phase 1)
   ```
   oc get pods -n <mch-namespace> -l name=multiclusterhub-operator
   oc get pods -n multicluster-engine
   ```

4. Check operator logs for the blocking component
   ```
   oc logs -n <mch-namespace> -l name=multiclusterhub-operator --tail=100
   ```
   Look for error messages, reconciliation failures, or resource conflicts.

5. Check events in the namespace
   ```
   oc get events -n <mch-namespace> --sort-by=.lastTimestamp | tail -30
   ```

6. If upgrade-related, check install plans
   ```
   oc get installplans -n <mch-namespace>
   oc get sub -n <mch-namespace> -o yaml
   ```

---

## Managed Cluster Connectivity

**When to use**: One or more managed clusters show Unknown, NotReady, or
AVAILABLE=False.

**Investigation steps**:

1. Get managed cluster status details
   ```
   oc get managedclusters
   oc get managedcluster <cluster-name> -o yaml
   ```
   Check all conditions in `.status.conditions`.

2. Check lease renewal (hub-side indicator of spoke health)
   ```
   oc get lease -n <cluster-namespace> --sort-by=.spec.renewTime
   ```
   If lease hasn't been renewed recently, the klusterlet isn't reporting.

3. Check the cluster's namespace for events
   ```
   oc get events -n <cluster-namespace> --sort-by=.lastTimestamp | tail -20
   ```

4. Check addon status for the cluster
   ```
   oc get managedclusteraddons -n <cluster-namespace>
   ```
   If all addons are unavailable, it's connectivity, not addon-specific.

5. Check registration controller on hub
   ```
   oc get pods -n open-cluster-management-hub -l app=registration-controller
   oc logs -n open-cluster-management-hub -l app=registration-controller --tail=50
   ```

6. If you have access to the spoke cluster, check klusterlet
   ```
   oc get pods -n open-cluster-management-agent
   oc logs -n open-cluster-management-agent -l app=klusterlet --tail=50
   ```

---

## Search Subsystem

**When to use**: Search returns no/partial results, search pods are failing,
or search-related UI features are broken.

**Investigation steps**:

1. Check all search pods (use the MCH namespace discovered in Phase 1)
   ```
   oc get pods -n <mch-namespace> | grep search
   ```

2. Check search-api specifically
   ```
   oc get pods -n <mch-namespace> | grep search-api
   oc logs -n <mch-namespace> -l app=search-api --tail=50
   ```
   Look for connection errors to the database backend.

3. Check search storage (postgres in ACM 2.12+)
   ```
   oc get pods -n <mch-namespace> | grep search-postgres
   oc get pvc -n <mch-namespace> | grep search
   ```
   Check if PVCs are Bound and if storage is full.

4. Check search-collector addon on spokes
   ```
   oc get managedclusteraddons -A | grep search-collector
   ```
   If collector is unavailable on some spokes, those spokes' resources
   won't appear in search.

5. Check MCH to verify search is enabled
   ```
   oc get mch -A -o yaml | grep -A2 '"search"'
   ```

---

## Observability Stack

**When to use**: Observability pods failing, Grafana dashboards empty, metrics
not flowing from spokes.

**Investigation steps**:

1. Check if observability is deployed
   ```
   oc get multiclusterobservability -A
   oc get pods -n open-cluster-management-observability
   ```
   If the namespace doesn't exist, observability isn't enabled.

2. Check the MCO CR status
   ```
   oc get multiclusterobservability observability -o yaml
   ```
   Look at `.status.conditions`.

3. Check Thanos components individually (pod names use `observability-` prefix)
   ```
   oc get pods -n open-cluster-management-observability | grep thanos
   ```
   Key components: query, query-frontend, receive-default (StatefulSet),
   store-shard (sharded StatefulSets), compact, rule. Check restart counts
   carefully -- store shards can accumulate high restarts from S3 sync issues.

4. Check storage configuration and PVCs
   ```
   oc get pvc -n open-cluster-management-observability
   ```
   Observability uses many PVCs: alertmanager, compactor, receive (per replica),
   rule (per replica), and store shards. All must be Bound.
   Thanos requires S3-compatible storage. Missing storage config is the #1
   cause of observability failures. Check for Minio or external S3 config.

5. Check Thanos store logs for S3/bucket errors
   ```
   oc get pods -n open-cluster-management-observability | grep thanos-store
   oc logs -n open-cluster-management-observability <store-pod-name> --tail=50
   ```
   Look for BucketStore InitialSync failures or block fetcher errors.

6. Check observability addon on spokes
   ```
   oc get managedclusteraddons -A | grep observability-controller
   ```
   Also check hub-side metrics collectors:
   ```
   oc get pods -n open-cluster-management-observability | grep metrics-collector
   ```

7. Check Grafana and supporting services
   ```
   oc get pods -n open-cluster-management-observability | grep -E 'grafana|observatorium|rbac-query'
   ```

---

## Governance / Policy Framework

**When to use**: Policies not propagating, compliance status stuck or Unknown,
governance UI showing errors.

**Investigation steps**:

1. Check policy propagator (use the MCH namespace discovered in Phase 1)
   ```
   oc get pods -n <mch-namespace> | grep grc-policy-propagator
   oc logs -n <mch-namespace> -l app=grc-policy-propagator --tail=50
   ```

2. Check policy summary
   ```
   oc get policies -A --no-headers | wc -l
   oc get policies -A -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name}: {.status.compliant}{"\n"}{end}'
   ```
   Look for policies with empty or missing compliance status.

3. Check governance addons on spokes
   ```
   oc get managedclusteraddons -A | grep -E 'governance|config-policy|cert-policy'
   ```

4. Check work-manager (responsible for distributing work to spokes)
   ```
   oc get pods -n open-cluster-management-hub -l app=work-manager
   oc logs -n open-cluster-management-hub -l app=work-manager --tail=50
   ```
   Backlog in work-manager delays compliance updates.

5. If specific policies are stuck, check their status
   ```
   oc get policy <policy-name> -n <namespace> -o yaml
   ```
   Look at `.status.status` for per-cluster compliance.

---

## Application Lifecycle

**When to use**: Applications not deploying, subscriptions stuck, channels
unreachable.

**Investigation steps**:

1. Check subscription controller (use the MCH namespace discovered in Phase 1)
   ```
   oc get pods -n <mch-namespace> | grep subscription
   oc logs -n <mch-namespace> -l app=multicluster-operators-hub-subscription --tail=50
   ```

2. Check subscriptions status
   ```
   oc get subscriptions.apps.open-cluster-management.io -A
   ```
   Look for subscriptions not in Propagated phase.

3. Check channels
   ```
   oc get channels -A
   ```

4. Check placement decisions
   ```
   oc get placementdecisions -A
   ```
   If decisions are empty, no clusters matched the placement criteria.

5. For GitOps path, check if OpenShift GitOps is installed
   ```
   oc get csv -A | grep gitops
   ```

6. Check application-manager addon on spokes
   ```
   oc get managedclusteraddons -A | grep application-manager
   ```

---

## Console & UI

**When to use**: Console returning 500 errors, feature tabs missing, UI
not loading.

**Investigation steps**:

1. Check console pods (use the MCH namespace discovered in Phase 1)
   ```
   oc get pods -n <mch-namespace> | grep console
   ```
   Look for `console-chart-console-v2-*` pods. In ACM 2.16+, console-api
   may be integrated into the console chart rather than a separate deployment.

2. Check console plugins
   ```
   oc get consoleplugins
   ```
   Should show `acm` and `mce` plugins. Missing plugins = missing feature tabs.

3. Check console plugin pods (use the MCH namespace discovered in Phase 1)
   ```
   oc get pods -n <mch-namespace> -l app=acm-console 2>/dev/null
   oc get pods -n multicluster-engine -l app=mce-console 2>/dev/null
   ```

4. Check console route
   ```
   oc get routes -n openshift-console
   ```

5. Check OAuth configuration
   ```
   oc get oauth cluster -o yaml
   ```
   Look for identity provider configuration.

---

## Node & Infrastructure

**When to use**: Nodes showing NotReady, resource pressure warnings, or
pods unable to schedule.

**Investigation steps**:

1. Check node status
   ```
   oc get nodes -o wide
   ```

2. Check node conditions
   ```
   oc get nodes -o json | jq '.items[] | {name: .metadata.name, conditions: [.status.conditions[] | {type, status}]}'
   ```
   Look for MemoryPressure, DiskPressure, PIDPressure.

3. Check node resource usage
   ```
   oc adm top nodes
   ```

4. Check for unschedulable nodes
   ```
   oc get nodes -o json | jq '.items[] | select(.spec.unschedulable==true) | .metadata.name'
   ```

5. Check cluster version and upgrade status
   ```
   oc get clusterversion -o yaml
   ```
   An in-progress upgrade can cause temporary node disruptions.

6. Check etcd health (if accessible)
   ```
   oc get pods -n openshift-etcd
   oc logs -n openshift-etcd -l app=etcd --tail=20
   ```

---

## Certificates

**When to use**: Intermittent TLS errors, x509 certificate errors in logs,
webhook failures.

**Investigation steps**:

1. List TLS secrets in MCH namespace (use namespace discovered in Phase 1)
   ```
   oc get secrets -n <mch-namespace> -o json | jq -r '.items[] | select(.type=="kubernetes.io/tls") | .metadata.name'
   ```

2. Check cert expiration (requires openssl)
   ```
   for secret in $(oc get secrets -n <mch-namespace> -o json | jq -r '.items[] | select(.type=="kubernetes.io/tls") | .metadata.name'); do
     echo "=== $secret ==="
     oc get secret $secret -n <mch-namespace> -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -enddate 2>/dev/null
   done
   ```

3. Check webhook configurations
   ```
   oc get validatingwebhookconfigurations | grep -i 'ocm\|acm\|multicluster'
   oc get mutatingwebhookconfigurations | grep -i 'ocm\|acm\|multicluster'
   ```

4. If a specific webhook is failing, check its service and endpoint
   ```
   oc get validatingwebhookconfiguration <name> -o yaml
   ```
   Verify the service exists and the endpoint is reachable.

---

## Add-ons (General)

**When to use**: Specific addon showing unavailable, addon deployments stuck.

**Investigation steps**:

1. List all addons across clusters
   ```
   oc get managedclusteraddons -A
   ```

2. Check specific addon status
   ```
   oc get managedclusteraddon <addon-name> -n <cluster-namespace> -o yaml
   ```
   Look at `.status.conditions`.

3. Check addon-manager on hub (use the MCH namespace discovered in Phase 1)
   ```
   oc get pods -n <mch-namespace> -l app=addon-manager
   oc logs -n <mch-namespace> -l app=addon-manager --tail=50
   ```

4. Check if the addon's ClusterManagementAddon exists
   ```
   oc get clustermanagementaddons
   ```
   This is the hub-side definition of available addons.
