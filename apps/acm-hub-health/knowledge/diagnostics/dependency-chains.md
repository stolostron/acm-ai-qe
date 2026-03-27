# Dependency Chains

6 critical paths where failures cascade across ACM subsystems. When diagnosing
an issue, trace UPSTREAM through the relevant chain to find the root cause.

---

## Chain 1: Console -> Search -> Managed Clusters

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

## Cross-Chain Patterns

When multiple chains are affected simultaneously, look for shared dependencies:

| Symptom | Shared Cause |
|---|---|
| Search + Observability both broken | Shared storage or node pressure |
| All features broken on one spoke | klusterlet disconnected (affects chains 1,2,5,6) |
| Multiple addons failing on same spoke | addon-manager down or spoke connectivity |
| Nothing works | MCH/MCE/backplane issue (chain 3) |
| UI shows "everything broken" but oc commands work | Console issue only (chain 1 top) |
