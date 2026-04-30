# Application Lifecycle Data Flow

How applications are deployed from the console through subscriptions to spoke clusters.

---

## Subscription-Based Deployment

```
User creates application via console wizard
  -> Application CR + Subscription CR + Channel CR + PlacementRule CR created
  -> multicluster-operators-hub-subscription processes the Subscription
    -> resolves Channel to get source (Git repo, Helm chart, S3 bucket)
    -> evaluates PlacementRule to determine target clusters
    -> creates propagated Subscription in each target cluster namespace
  -> application-manager addon on spoke
    -> detects propagated Subscription
    -> fetches resources from Channel source
    -> applies resources to spoke cluster
    -> reports status back to hub
  -> Hub aggregates deployment status
  -> Console UI shows application topology and health
```

## ArgoCD ApplicationSet Deployment

```
User creates ApplicationSet via console wizard
  -> ApplicationSet CR created in openshift-gitops namespace
  -> GitOps controller processes the ApplicationSet
    -> generates Application CRs based on placement
    -> each Application syncs from Git source
    -> ArgoCD deploys resources to target clusters
  -> Sync status flows back to hub
  -> Console shows sync/health status per application
```

## Application Health and Status

```
subscription-report aggregates status from all targets
  -> backend/src/routes/aggregators/applications.ts
    -> computes health score
    -> returns Healthy/Unhealthy status
  -> backend/src/routes/aggregators/statuses.ts
    -> counts applications by status
    -> returns itemCount
  -> Console displays status in application table
```

Bug injection points:
- applications.ts can invert health logic (Healthy <-> Unhealthy)
- statuses.ts can inflate item count (+3)

## Failure Points

| Point | What breaks | Symptom |
|-------|------------|---------|
| applications.app.k8s.io CRD missing | All oc apply for Application CRs fail | "resource mapping not found" |
| ApplicationSet CRD missing | ArgoCD appset operations fail | No route created, empty status |
| subscription-controller down | App deployments stop | "subscription not ready within time limit" |
| ArgoCD sync stuck | Resources never appear on target | Route/deployment never created |
| Ansible Tower unreachable | Pre/post hooks fail | "posthook not triggered within time limit" |
| PF6 menu portal issue | UI tests can't select menu items | "visibility:hidden" on menu items |
