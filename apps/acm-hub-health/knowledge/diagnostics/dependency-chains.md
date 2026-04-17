# Dependency Chains

11 critical paths where failures cascade across ACM subsystems. When diagnosing
an issue, trace UPSTREAM through the relevant chain to find the root cause.

---

## Chain 1: Console -> Search -> Managed Clusters

**Layers spanned:** 12 (UI) → 11 (data flow) → 9 (operators) → 4 (storage) → 3 (network) → 10 (cross-cluster)

```
Console UI (VM page, search page, RBAC resource views)
  <- depends on ->
    console-api Resource Proxy
      <- depends on ->
        search-api (GraphQL queries)
          <- depends on ->
            search-indexer (data processing)
              <- depends on ->
                search-postgres (storage)
              <- depends on ->
                search-collector addon (on each spoke)
                  <- depends on ->
                    klusterlet (spoke connectivity)
```

**Impact:** If search-collector is down on a spoke, resources from that spoke
don't appear in search. If search-postgres is down, ALL search queries fail.
If search-api is down, Console VM pages show empty, RBAC resource views are
blank, and search page is broken.

**Tracing procedure:**
1. Is the Console page itself loading? If not -> check console-api pods
2. Is search-api healthy? `oc get pods -n <mch-ns> -l app=search-api`
3. Is search-postgres healthy? `oc get pods -n <mch-ns> -l app=search-postgres`
4. Are results missing from specific clusters? Check search-collector addon:
   `oc get managedclusteraddon search-collector -n <cluster>`
5. Is that cluster reachable? `oc get managedclusters` -- check AVAILABLE

---

## Chain 2: Governance -> Framework Addon -> Config Policy -> Managed Clusters

**Layers spanned:** 9 (operators) → 10 (cross-cluster) → 7 (RBAC) → 11 (data flow)

```
Hub: Policy + PlacementBinding + Placement
  <- propagated by ->
    grc-policy-propagator (creates replicated policies)
      <- delivered by ->
        governance-policy-framework-addon (Spec Sync Controller)
          <- evaluated by ->
            config-policy-controller (on spoke)
              <- status reported by ->
                Status Sync Controller (back to hub)
                  <- aggregated by ->
                    Root Compliance Calculator (hub)
```

**Impact:** If propagator is down, no new policies distribute. If framework
addon is missing on a spoke, policies don't reach that spoke. If
config-policy-controller is down, policies aren't evaluated (compliance Unknown).
If Status Sync can't reach hub, compliance appears stale.

**Tracing procedure:**
1. Is the policy non-compliant or status Unknown?
   - Unknown -> check framework addon on spoke
   - Non-compliant -> check if it's actually non-compliant on spoke or status is stale
2. Check propagator: `oc get pods -n <mch-ns> -l app=grc-policy-propagator`
3. Check framework addon: `oc get managedclusteraddon governance-policy-framework -n <cluster>`
4. Check config-policy-controller: `oc get managedclusteraddon config-policy-controller -n <cluster>`
5. Check work-manager (delivers ManifestWorks): `oc get pods -n open-cluster-management-hub -l app=work-manager`

---

## Chain 3: MCH Operator -> Backplane Operator -> Component Operators

**Layers spanned:** 9 (operators) → 5 (configuration/OLM) → 8 (CRDs)

```
OLM (Subscription + CSV)
  <- manages ->
    MCH Operator (multiclusterhub-operator)
      <- manages ->
        MCE CR -> Backplane Operator
          <- deploys ->
            All MCE component operators
              |- cluster-manager
              |- hive-operator
              |- managedcluster-import-controller
              |- placement-controller
              |- addon-manager
              +- foundation-controller
      <- deploys ->
        All ACM component operators
              |- search-api, search-indexer
              |- grc-policy-propagator
              |- subscription-controller
              |- console
              |- observability-operator
              +- cluster-permission
```

**Impact:** If OLM/CSV is unhealthy, the MCH operator can't be updated. If
MCH operator is down, ACM component lifecycle stops. If backplane operator
is down, MCE components can't be deployed or updated. This is the ultimate
root cause chain -- a failure here affects everything.

**Tracing procedure:**
1. Is MCH phase Running? `oc get mch -A`
2. If not, which component is blocking? Check `.status.components` map
3. Is MCE Available? `oc get multiclusterengines`
4. Check backplane operator: `oc get pods -n multicluster-engine | grep backplane`
5. Check OLM: `oc get csv -n <mch-ns>` and `oc get csv -n multicluster-engine`
6. Check subscriptions: `oc get sub -n <mch-ns>`

---

## Chain 4: HyperShift Addon -> Import Controller -> Klusterlet

**Layers spanned:** 9 (operators) → 10 (cross-cluster) → 6 (auth/registration)

```
HostedCluster CR (user creates)
  <- managed by ->
    hypershift-addon (creates ManagedCluster)
      <- imports ->
        managedcluster-import-controller (generates klusterlet manifests)
          <- deploys ->
            klusterlet on hosted cluster workers
              <- registers via ->
                registration-agent -> hub registration-operator
```

**Impact:** If hypershift-addon is down, new hosted clusters aren't imported.
If import controller is down, klusterlet isn't deployed. If registration fails,
the cluster stays in Pending state.

**Known issue:** hypershift-addon auto-import can recreate a ManagedCluster
after a HostedCluster is destroyed (ACM-20695). Detach operation can destroy
the hosted cluster namespace, killing the HostedCluster CR (ACM-15018).

**Tracing procedure:**
1. Is the HostedCluster created? `oc get hostedclusters -A`
2. Does a ManagedCluster exist for it? `oc get managedclusters`
3. Check hypershift-addon: `oc get pods -n <mch-ns> | grep hypershift`
4. Check import controller: `oc get pods -n <mch-ns> -l app=managedcluster-import-controller`
5. Check klusterlet on spoke: verify pods in `open-cluster-management-agent`

---

## Chain 5: MCRA Operator -> ClusterPermission -> ManifestWork -> Spoke RBAC

**Layers spanned:** 9 (operators) → 7 (RBAC) → 10 (cross-cluster) → 12 (UI)

```
MultiClusterRoleAssignment (user creates via RBAC wizard)
  <- processed by ->
    MCRA Operator (multicluster-role-assignment-controller)
      <- creates ->
        ClusterPermission (per target cluster)
          <- creates ->
            ManifestWork (contains Role + RoleBinding YAML)
              <- applied by ->
                klusterlet work-agent (on spoke)
                  <- creates ->
                    Role + RoleBinding (on spoke)
                      <- grants ->
                        User permissions on spoke resources
```

**Impact:** If MCRA operator is down, new role assignments aren't processed.
If ClusterPermission controller is down (OOM at scale -- ACM-24032), RBAC
isn't propagated. If klusterlet is disconnected, ManifestWork can't be delivered.
User doesn't get expected permissions, VM pages empty, RBAC-filtered views blank.

**Tracing procedure:**
1. Is the user missing permissions? What resource, what cluster?
2. Check MCRA status: `oc get mcra -A -o yaml | grep -A5 conditions`
3. Check ClusterPermission: `oc get clusterpermission -n <cluster>`
4. Check ManifestWork for RBAC: `oc get manifestwork -n <cluster> | grep permission`
5. Check cluster-permission controller: `oc get pods -n <mch-ns> | grep cluster-permission`
6. On spoke: verify Role/RoleBinding exists

---

## Chain 6: Observability Operator -> Addon -> Prometheus -> Thanos

**Layers spanned:** 9 (operators) → 10 (cross-cluster) → 4 (storage/S3) → 11 (data flow) → 12 (UI/Grafana)

```
MultiClusterObservability CR (configuration)
  <- managed by ->
    multicluster-observability-operator (deploys Thanos stack)
      <- deploys addon ->
        observability-controller addon (ManagedClusterAddon)
          <- deploys on spoke ->
            metrics-collector (scrapes Prometheus)
              <- sends to hub ->
                thanos-receive (ingests metrics)
                  <- stores in ->
                    S3 object storage (external)
                      <- served by ->
                        thanos-store (historical queries)
                          <- queried by ->
                            thanos-query -> Grafana dashboards
```

**Impact:** If MCO operator is down, observability stack can't be managed.
If metrics-collector addon is missing on spoke, no metrics from that cluster.
If S3 is misconfigured, thanos-store crashes (most common observability failure).
If thanos-query is down, Grafana dashboards show no data.

**Tracing procedure:**
1. Check MCO CR: `oc get mco observability -o yaml | grep -A10 status`
2. Check observability pods: `oc get pods -n open-cluster-management-observability`
3. Check for S3 errors in thanos-store logs
4. Check metrics-collector addon: `oc get managedclusteraddon -A | grep observability`
5. Check PVCs: `oc get pvc -n open-cluster-management-observability`

---

## Chain 7: Addon Manager -> Addon Framework -> Spoke Addon Pods

**Layers spanned:** 9 (operators) → 10 (cross-cluster) → 3 (network/connectivity)

```
addon-manager (hub MCE namespace)
  <- deploys ->
    ManagedClusterAddon CRs (per cluster namespace)
      <- delivered by ->
        addon framework (ManifestWork-based delivery)
          <- applied by ->
            klusterlet work-agent (on spoke)
              <- runs ->
                spoke addon pods (governance, search-collector, observability, etc.)
```

**Impact:** addon-manager is a single point of failure for ALL spoke addons.
If it's down, no addons deploy to any spoke. New clusters import successfully
(import-controller is independent) but arrive with zero addons.

**Tracing procedure:**
1. Are ALL addons Unavailable across multiple clusters? -> check addon-manager first
2. `oc get pods -n multicluster-engine | grep addon-manager`
3. If addon-manager is healthy, check per-cluster addon CRs:
   `oc get managedclusteraddons -n <cluster>`
4. If a specific addon is stuck, check its ManifestWork:
   `oc get manifestwork -n <cluster> | grep <addon-name>`

---

## Chain 8: StorageClass -> CSI Driver -> PV -> PVC -> Pod

**Layers spanned:** 4 (storage) → 1 (compute) → 9 (operators/StatefulSets)

```
StorageClass (cluster-scoped config)
  <- provisions via ->
    CSI Driver (dynamic provisioner)
      <- creates ->
        PersistentVolume
          <- bound to ->
            PersistentVolumeClaim (in component namespace)
              <- mounted by ->
                Stateful pod (thanos-receive, thanos-store, alertmanager)
```

**Impact:** Storage failures affect all stateful ACM components. Observability
is the most affected subsystem (thanos-receive, thanos-store, alertmanager all
use StatefulSet PVCs). Search-postgres defaults to emptyDir but can optionally
use a PVC.

**Affected components:**
- `thanos-receive` -- observability metric ingestion
- `thanos-store` -- observability historical queries (sharded StatefulSet)
- `alertmanager` -- observability alerting
- `search-postgres` -- search data (emptyDir by default)

**Tracing procedure:**
1. Check PVC status: `oc get pvc -n open-cluster-management-observability`
2. If PVCs are Pending: `oc describe pvc <name>` -- look for provisioner errors
3. Check default StorageClass: `oc get sc` -- is one marked `(default)`?
4. Check CSI driver pods: `oc get pods -n openshift-cluster-csi-drivers`
5. If PVCs are Bound but pods crash: check disk usage (volume full)

---

## Chain 9: Channel -> Subscription -> ManifestWork -> Spoke Application

**Layers spanned:** 9 (operators) → 5 (configuration) → 10 (cross-cluster) → 11 (data flow)

```
Channel CR (Git, Helm, or ObjectStorage source)
  <- validated by ->
    multicluster-operators-channel (channel controller)
      <- referenced by ->
        Subscription CR + Placement/PlacementRule
          <- reconciled by ->
            multicluster-operators-hub-subscription (generates ManifestWorks)
              <- delivered by ->
                ManifestWork (via klusterlet work-agent)
                  <- applied by ->
                    application-manager addon (on spoke)
```

**Impact:** If hub-subscription controller is down, subscriptions are not
reconciled and no ManifestWorks are generated -- app deployment halts. If
channel auth fails (Git/Helm credentials invalid), subscription is stuck in
Propagated with no explicit error in status. If placement matches zero
clusters, app deploys nowhere with no error.

**Tracing procedure:**
1. Is the Subscription status showing Propagated? `oc get sub -n <app-ns>`
2. Check subscription controller: `oc get pods -n <mch-ns> | grep hub-subscription`
3. Check channel controller: `oc get pods -n <mch-ns> | grep channel`
4. Check placement: `oc get placement -n <app-ns>` -- does it match clusters?
5. Check ManifestWork: `oc get manifestwork -n <cluster> | grep <app-name>`
6. Check application-manager addon: `oc get managedclusteraddon application-manager -n <cluster>`

---

## Chain 10: CNV -> Search Collector -> Search API -> kubevirt-plugin -> Console

**Layers spanned:** 10 (cross-cluster) → 11 (data flow) → 9 (operators) → 4 (storage) → 12 (UI/plugin)

```
CNV HyperConverged Operator (spoke -- prerequisite for VMs)
  <- VMs indexed by ->
    search-collector addon (indexes VM, VMI, DataVolume)
      <- processed by ->
        search-indexer (hub)
          <- stored in ->
            search-postgres
              <- queried by ->
                search-api (GraphQL)
                  <- consumed by ->
                    kubevirt-plugin (ConsolePlugin -- Fleet Virt UI)
                      <- hosted by ->
                        console-chart-console-v2 (ACM console)
```

**Impact:** If CNV is not installed on a spoke, no VMs to index -- not an
error, just no data. If search-collector is missing, VMs exist but don't
appear in hub UI (silent absence). If kubevirt-plugin is unregistered,
Fleet Virt VM tab is absent from console navigation. If MCRA controller
panics, users with fine-grained roles can't manage VMs (ACM-24737).

**Tracing procedure:**
1. Is Fleet Virt VM tab visible in console? If not -> check ConsolePlugins
2. Is kubevirt-plugin registered? `oc get consoleplugins | grep kubevirt`
3. Are VMs showing in search? Query search-api directly
4. Check search-collector on spoke: `oc get managedclusteraddon search-collector -n <cluster>`
5. Is CNV installed on spoke? `oc get csv -A | grep kubevirt-hyperconverged`
6. For MTV: check mtv-integrations-controller if migration features are broken

---

## Chain 11: SubmarinerConfig -> Addon -> Gateway -> Tunnel -> Service Discovery

**Layers spanned:** 9 (operators) → 10 (cross-cluster) → 3 (network) → 11 (data flow)

```
SubmarinerConfig CR (per-cluster config on hub)
  <- managed by ->
    submariner-addon (hub-side controller)
      <- deploys via ManifestWork ->
        submariner-operator (spoke)
          <- deploys ->
            gateway (IPsec tunnels: UDP 4500, UDP 4800)
              <- routes via ->
                routeagent (programs routes on spoke nodes)
              <- exports via ->
                lighthouse-agent (ServiceExport -> broker)
                  <- resolves via ->
                    lighthouse-coredns (clusterset.local DNS)
              <- NAT via (if overlapping CIDRs) ->
                globalnet-controller (GlobalEgressIP/GlobalIngressIP)
```

**Impact:** If gateway is unhealthy, all cross-cluster tunnels are down for
that cluster. If lighthouse is down, cross-cluster service discovery fails
(clusterset.local DNS unresolvable). If globalnet is missing with overlapping
CIDRs, traffic fails with IP conflicts. Submariner breaks on OCP 4.18+ due
to OVN-Kubernetes changes (ACM-22805).

**Tracing procedure:**
1. Check SubmarinerConfig: `oc get submarinerconfig -A`
2. Check submariner-addon: `oc get pods -n <mch-ns> | grep submariner`
3. Check addon status: `oc get managedclusteraddon submariner -n <cluster>`
4. On spoke: check gateway pods: `oc get pods -n submariner-operator | grep gateway`
5. Check tunnel connections: `oc get gateways.submariner.io -A`
6. Check DNS: `oc get pods -n submariner-operator | grep lighthouse`
7. OCP version compatibility: `oc get clusterversion` (4.18+ needs Submariner 0.18+)

---

## Cross-Chain Patterns

When multiple chains are affected simultaneously, look for shared dependencies:

| Symptom | Shared Cause |
|---|---|
| Search + Observability both broken | Shared storage or node pressure |
| All features broken on one spoke | klusterlet disconnected (affects chains 1,2,5,6) |
| Multiple addons failing on same spoke | addon-manager down or spoke connectivity |
| Nothing works | MCH/MCE/backplane issue (chain 3) |
| UI shows "everything broken" but oc commands work | Console issue only (chain 1 top) |
| ALL addons Unavailable across ALL clusters | addon-manager down (chain 7) |
| Observability + search both have storage errors | Shared storage infrastructure failure (chain 8) |
| New clusters import but get no addons | addon-manager down; import works independently (chains 4,7) |
