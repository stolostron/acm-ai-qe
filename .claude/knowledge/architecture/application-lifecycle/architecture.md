# Application Lifecycle (ALC) -- Architecture

## What Application Lifecycle Does

Provides application deployment and management across managed clusters using two
distinct models: the **Subscription model** (Channel-based) and the
**ArgoCD/GitOps model** (ApplicationSet-based). Handles content sourcing from
Git, Helm, and ObjectBucket channels, placement-driven distribution, status
aggregation, and lifecycle management of deployed applications.

---

## Deployment Models

### Subscription Model

Traditional ACM application model using four core resources:

1. **Channel** -- defines content source (Git repo, Helm repo, ObjectBucket)
2. **Subscription** -- references a Channel and selects specific content
3. **PlacementRule / Placement** -- selects target managed clusters
4. **Application** -- groups subscriptions under a single lifecycle

Resources flow: Channel -> Subscription -> PlacementRule -> ManifestWork ->
spoke clusters. The hub subscription-controller reconciles subscriptions and
generates ManifestWork resources per target cluster.

### ArgoCD / GitOps Model

Integrates with OpenShift GitOps (ArgoCD) for pull/push model deployment:

1. **ApplicationSet** -- ArgoCD CRD defining application templates
2. **GitOps Addon Controller** -- bridges ACM placement with ArgoCD
3. **OpenShift GitOps Operator** -- runs on hub (push) or spokes (pull)
4. **GitOpsCluster** -- CRD that imports managed clusters into ArgoCD

Push model: Hub ArgoCD deploys to spokes.
Pull model: Each spoke runs its own ArgoCD. Hub distributes ApplicationSet
definition; spoke ArgoCD reconciles locally.

---

## Hub-Side Components

### subscription-controller

- **Pod label:** `app=subscription-controller`
- **Namespace:** MCH namespace

Reconciles Subscription resources on hub. Resolves channel content, evaluates
placement decisions, generates ManifestWork for each target cluster. Handles
both Git and Helm channel types.

### channel-controller

- **Pod label:** `app=channel-controller`
- **Namespace:** MCH namespace

Manages Channel resources. Validates channel connectivity (Git auth, Helm repo
access, ObjectBucket credentials). Updates channel status with connectivity
information.

### multicluster-operators-subscription

- **Pod label:** `app=multicluster-operators-subscription`
- **Namespace:** MCH namespace (ocm)

Core subscription operator containing multiple controllers:
- **hub:** Manages subscription lifecycle on hub
- **standalone:** Handles local-cluster subscriptions
- **application:** Application CRD controller, creates ManifestWork for distribution
- **report:** Application Status Controller, syncs status back to Application CRD

### multicluster-operators-hub-subscription

- **Pod label:** `app=multicluster-operators-hub-subscription`
- **Namespace:** MCH namespace (ocm)

Hub-side subscription processing.

### multicluster-operators-standalone-subscription

- **Pod label:** `app=multicluster-operators-standalone-subscription`
- **Namespace:** MCH namespace (ocm)

Standalone subscription processing.

### multicluster-operators-subscription-report

- **Pod label:** `app=multicluster-operators-subscription-report`
- **Namespace:** MCH namespace (ocm)

Subscription status reporting.

### multicloud-operators-application

- **Pod label:** `app=multicluster-operators-application`
- **Namespace:** MCH namespace (ocm)

Watches Application CRDs, coordinates status aggregation across managed
clusters. For pull model ArgoCD apps, aggregates status into
`MulticlusterApplicationSetReport` CRD.

### multicluster-operators-channel

- **Pod label:** `app=multicluster-operators-channel`
- **Namespace:** MCH namespace (ocm)

Channel CR management.

### GitOps Addon Controller

- **Namespace:** MCH namespace

Bridges ACM placement with ArgoCD ApplicationSet:
- Reconciles `GitOpsCluster` CRDs
- Imports managed cluster credentials into ArgoCD
- Manages `GitOps Sync Resource Controller` for ApplicationSet processing

---

## Spoke-Side Components

### application-manager (addon)

- **Addon name:** `application-manager`
- **Namespace:** `open-cluster-management-agent-addon` on spoke
- **Default:** Enabled

Spoke-side agent that:
- Validates application resources via Application Webhooks
- Reports application deployment status to hub
- Manages local subscription reconciliation for pull model

---

## Prerequisites

- `app-lifecycle` component enabled in MCH (enabled by default)
- `application-manager` addon deployed to spoke clusters
- `applications.app.k8s.io` CRD registered (critical -- missing CRD breaks all app tests)
- For ArgoCD: `openshift-gitops` operator installed, ApplicationSet CRD registered

---

## Key CRDs

| CRD | API Group | Purpose |
|-----|-----------|---------|
| Application | app.k8s.io/v1beta1 | Application grouping resource |
| Subscription | apps.open-cluster-management.io/v1 | Defines what to deploy and from where |
| Channel | apps.open-cluster-management.io/v1 | Source repository (Git, Helm, Object Storage) |
| PlacementRule | apps.open-cluster-management.io/v1 | Target cluster selection |
| ApplicationSet | argoproj.io/v1alpha1 | ArgoCD application set (requires GitOps operator) |

---

## Channel Types

| Type | Description | Common Issues |
|------|-------------|---------------|
| Git | Git repository source | Auth failures, branch not found |
| HelmRepo | Helm chart repository | Chart version not found |
| ObjectBucket | S3-compatible storage | Credential/connectivity issues |
| Namespace | Same-cluster namespace | Namespace not found |

---

## Console Integration

ALC pages: `/multicloud/applications`

The application table shows status, sync state, and topology. ArgoCD
applications display sync/health status from the GitOps controller.
CSV export functionality uses `cy.readFile()` to verify downloaded files.

---

## Test Repository Structure

ALC tests are in `stolostron/application-ui-test` (local clone: alc-ui).
Tests organized by app type: Git, Helm, ObjectStorage, Argo, Flux, Ansible.
Common views in `tests/cypress/views/common.js` -- uses `.within()` scoping
which causes PF6 portal visibility issues with menu items.

---

## Cross-Subsystem Dependencies

| Dependency | Why |
|---|---|
| Infrastructure (klusterlet) | ManifestWork delivery requires spoke connectivity |
| Console | Resource Proxy proxies application resources for the UI |
| Placement / PlacementRule | Shared resource with CLC and GRC for cluster selection |
| OpenShift GitOps Operator | External dependency for ArgoCD path -- not part of ACM |
| Search | Application resources indexed for console search and resource views |

## What Depends on Application Lifecycle

| Consumer | Impact When ALC Is Down |
|---|---|
| Console Applications page | No applications listed, creation wizards fail |
| GitOps integration | ApplicationSet distribution stops |
| ManifestWork delivery | Application resources not deployed to spokes |
| Status aggregation | Application health/status not reported to hub |
