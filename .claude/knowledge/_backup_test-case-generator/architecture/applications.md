# Applications Area Knowledge

## Overview

Application Lifecycle (ALC) in ACM Console manages application deployments across managed clusters using two deployment models: Subscription-based and ArgoCD/GitOps.

## Key Components

| Component | Namespace | Role |
|-----------|-----------|------|
| `multicluster-operators-application` | ocm | Application CR reconciliation |
| `multicluster-operators-channel` | ocm | Channel CR management |
| `multicluster-operators-hub-subscription` | ocm | Hub-side subscription processing |
| `multicluster-operators-standalone-subscription` | ocm | Standalone subscriptions |
| `multicluster-operators-subscription-report` | ocm | Status reporting |
| `application-manager` addon | open-cluster-management-agent-addon (spoke) | Spoke-side application management |

## CRDs / Resources

| CRD | API Group | Purpose |
|-----|-----------|---------|
| Application | `app.k8s.io/v1beta1` | Grouping resource for deployed apps |
| Subscription | `apps.open-cluster-management.io/v1` | What to deploy, from where |
| Channel | `apps.open-cluster-management.io/v1` | Source repository (Git, Helm, Object, Namespace) |
| PlacementRule | `apps.open-cluster-management.io/v1` | Target cluster selection |
| ApplicationSet | `argoproj.io/v1alpha1` | ArgoCD model (requires GitOps operator) |

## Channel Types

| Type | Description | Required Fields |
|------|-------------|-----------------|
| Git | Git repository source | URL, branch, path, credentials |
| HelmRepo | Helm chart repository | URL, chart name, version |
| ObjectBucket | S3-compatible storage | Endpoint, bucket, access key |
| Namespace | Same-cluster namespace | Namespace name |

## Navigation Routes

| Route Key | Path | Page |
|-----------|------|------|
| `applications` | `/multicloud/applications` | Applications overview |
| `createApplicationArgo` | `/multicloud/applications/create/argo` | Create ArgoCD app |
| `createApplicationSubscription` | `/multicloud/applications/create/subscription` | Create subscription app |
| `applicationDetails` | `/multicloud/applications/details/:namespace/:name` | App details |
| `applicationTopology` | `/multicloud/applications/details/:namespace/:name/topology` | Topology view |

## Deployment Models

### 1. Subscription Model
Channel → Subscription → PlacementRule → ManifestWork → spokes
- User selects source (channel), target (placement), and configuration
- Subscription controller creates ManifestWork for each target cluster
- Status aggregated from spoke addon reports

### 2. ArgoCD/GitOps Model
ApplicationSet → GitOps Addon → ArgoCD on hub or spokes
- Requires `openshift-gitops` operator installed
- ApplicationSet CRD must be registered
- Different creation wizard from Subscription model

## Setup Prerequisites

- `app-lifecycle` component enabled in MCH (enabled by default)
- `application-manager` addon deployed to spokes
- **CRITICAL**: `applications.app.k8s.io` CRD must be registered (missing CRD breaks ALL app tests)
- For ArgoCD: `openshift-gitops` operator installed, ApplicationSet CRD registered
- At least one managed cluster with AVAILABLE=True for deployment targeting

## Translation Keys

| Key | English Text | Context |
|-----|-------------|---------|
| `Applications` | "Applications" | Navigation tab |
| `Create application` | "Create application" | Button |
| `Subscription` | "Subscription" | Application type in create wizard |
| `Argo CD` | "Argo CD" | Application type in create wizard |
| `Topology` | "Topology" | Tab in application details |
| `Sync` | "Sync" | ArgoCD sync status/action |
| `Healthy` | "Healthy" | ArgoCD health status |

## Testing Considerations

- Argo CD and Subscription models have different creation flows and different wizard steps
- Topology view requires application actually deployed to managed clusters (can't test on empty app)
- Channel types affect available configuration options in the creation wizard
- ArgoCD sync/health status depends on GitOps operator (external dependency)
- Subscription status aggregation depends on spoke addon health
- Known issue: PF6 portal visibility — `.within()` scope can't reach flyout items with `visibility:hidden` (use `{ withinSubject: null }`)
- Known issue: CSV export fragility — file download timing issues in tests
- Test repository for e2e: `stolostron/application-ui-test`
