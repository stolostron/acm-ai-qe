# Application Lifecycle -- Data Flow

## Subscription Deployment Flow

```
Hub: Channel (Git/Helm/ObjectBucket)
  |
  v
Hub: Subscription references Channel, selects content
  |
  v
Hub: PlacementRule / Placement evaluates target clusters
  |
  v
Hub: subscription-controller reconciles
  |   - resolves channel content (git clone, helm fetch)
  |   - evaluates placement decisions
  |   - generates ManifestWork per target cluster
  v
Hub -> Spoke: ManifestWork delivered via work-agent
  |
  v
Spoke: Resources created/updated from ManifestWork payload
  |
  v
Spoke -> Hub: application-manager reports status
  |
  v
Hub: Application Status Controller updates Application CRD
```

### Console-Originated Subscription Deployment

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

---

## Step 1: Channel Content Sourcing

Channel defines content source. Three types:

- **Git:** Clones repository, selects path within repo
- **Helm:** Fetches chart from Helm repository
- **ObjectBucket:** Pulls objects from S3-compatible storage

**Failure:** Channel auth fails (wrong Git SSH key, expired Helm credentials)
-> subscription stuck, no explicit error in UI. Channel network unreachable ->
same symptom. ObjectBucket Kustomization handling bugs can cause silent failures.

---

## Step 2: Subscription Reconciliation

subscription-controller watches Subscription resources:
1. Resolves channel content into Kubernetes manifests
2. Applies Subscription filters (package filters, label selectors)
3. Evaluates PlacementRule/Placement for target cluster list
4. Generates ManifestWork in each target cluster's namespace on hub

**Failure:** subscription-controller down -> subscriptions not reconciled, stuck
in "Propagated" or empty status. PlacementRule matches no clusters -> no
ManifestWork created, subscription shows "no clusters matched."

---

## Step 3: ManifestWork Delivery

Generated ManifestWork resources are picked up by work-agent (part of klusterlet)
on each spoke and applied.

**Failure:** klusterlet disconnected -> ManifestWork pending, resources not
deployed. ManifestWork rejected by spoke admission controllers -> remains in
"Applied=False" state.

---

## Step 4: Status Aggregation

Application Status Controller collects deployment status from spokes:
1. application-manager on spoke reports resource health
2. Status flows back via ManifestWork status and work-agent
3. Application CRD updated with aggregated status

**Failure:** application-manager addon down on spoke -> no status reported from
that cluster, shows as unknown. Status aggregation controller down -> stale
status on hub.

### Console Application Health and Status

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

---

## GitOps / ArgoCD Deployment Flow

```
Hub: ApplicationSet CRD created
  |
  v
Hub: GitOps Addon Controller processes ApplicationSet
  |
  v (push model)                    (pull model)
  |                                  |
Hub ArgoCD deploys                  Hub distributes ApplicationSet
to spokes directly                  definition via ManifestWork
  |                                  |
  v                                  v
Spoke: Resources applied            Spoke: Local ArgoCD reconciles
via hub ArgoCD                      ApplicationSet locally
  |                                  |
  v                                  v
Hub: ArgoCD reports status          Spoke -> Hub: MulticlusterApplicationSetReport
```

### Console-Originated ArgoCD ApplicationSet Deployment

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

---

## Push Model

Hub-side ArgoCD has credentials for spoke clusters:
1. `GitOpsCluster` CRD imports managed cluster credentials into ArgoCD
2. ApplicationSet generates Application per cluster
3. ArgoCD syncs directly to spoke API servers

**Failure:** GitOpsCluster not created -> ArgoCD doesn't know about the cluster.
Spoke API unreachable -> ArgoCD sync fails with connection errors.

---

## Pull Model

Each spoke runs its own ArgoCD instance:
1. Hub distributes ApplicationSet definition to spoke via ManifestWork
2. Spoke ArgoCD reconciles locally from Git source
3. `MulticlusterApplicationSetReport` CRD aggregates status back to hub

**Failure:** OpenShift GitOps operator not installed on spoke -> pull model
fails silently. Status report not aggregated -> hub shows stale/missing status.
Application stuck "Refreshing" due to controller issues (ACM-22654).

---

## Failure Modes at Each Hop

### channel-controller down
- **Symptom:** Channel status not updated. New channels not validated.
- **Scope:** New subscriptions may reference invalid channels.
- **Detection:** `oc get pods -n <mch-ns> -l app=channel-controller`

### subscription-controller down
- **Symptom:** Subscriptions stuck, not reconciled. No ManifestWork generated.
- **Scope:** All subscription-based applications.
- **Detection:** `oc get pods -n <mch-ns> -l app=subscription-controller`

### application-manager addon missing on spoke
- **Symptom:** No status from that spoke. Application health unknown.
- **Scope:** Single spoke.
- **Detection:** `oc get managedclusteraddon application-manager -n {cluster}`

### GitOps operator not installed
- **Symptom:** ArgoCD path fails silently. No error in ACM UI -- applications
  simply never deploy.
- **Scope:** All ArgoCD-based applications.
- **Detection:** Check for GitOps operator CSV:
  `oc get csv -A | grep gitops`

### ManifestWork delivery failure
- **Symptom:** Resources not deployed to spoke. Subscription shows "Propagated"
  but spoke has no resources.
- **Scope:** Affected spoke(s).
- **Detection:** `oc get manifestworks -n {cluster} | grep subscription`

### ArgoCD sync stuck
- **Symptom:** Resources never appear on target. Route/deployment never created.
- **Scope:** ArgoCD-based applications on affected clusters.
- **Detection:** Check ArgoCD Application sync status.

### Ansible Tower unreachable
- **Symptom:** Pre/post hooks fail. "posthook not triggered within time limit".
- **Scope:** Applications with Ansible hooks.
- **Detection:** Check Tower connectivity and credentials.

### Additional Console-Specific Failure Points

| Point | What Breaks | Symptom |
|-------|------------|---------|
| applications.app.k8s.io CRD missing | All oc apply for Application CRs fail | "resource mapping not found" |
| ApplicationSet CRD missing | ArgoCD appset operations fail | No route created, empty status |
| subscription-controller down | App deployments stop | "subscription not ready within time limit" |
| PF6 menu portal issue | UI tests can't select menu items | "visibility:hidden" on menu items |
