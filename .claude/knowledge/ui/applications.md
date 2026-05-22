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

## Create Application Dropdown

The "Create application" button on the Overview tab presents three options:

| Option | Description (from UI) | Status |
|--------|----------------------|--------|
| Argo CD ApplicationSet - Pull model | "Considered the better choice for security although you cannot deploy to hub cluster. Managed clusters pull application resources from the Git repository." | Active (recommended) |
| Argo CD ApplicationSet - Push model | "Hub cluster pushes application resources to managed clusters requiring credentials for each cluster." | Active |
| Subscription | (legacy model) | **Deprecated** |

A "Compare application types" link is shown next to the Create button for side-by-side comparison.

## Deployment Models

### 1. Subscription Model (DEPRECATED)
Channel → Subscription → PlacementRule → ManifestWork → spokes
- User selects source (channel), target (placement), and configuration
- Subscription controller creates ManifestWork for each target cluster
- Status aggregated from spoke addon reports
- Deprecated in favor of ArgoCD ApplicationSets; still functional but no longer recommended

### 2. ArgoCD/GitOps -- Pull Model (Recommended)
ApplicationSet definition distributed to spokes → each spoke's ArgoCD pulls from Git → deploys locally
- Each managed cluster runs its own ArgoCD instance (via OpenShift GitOps Operator on spokes)
- Hub distributes the ApplicationSet definition; spokes independently reconcile
- Hub does NOT need credentials to target clusters for deployment
- More secure: spoke compromise does not expose other spokes
- **Limitation:** cannot deploy to the hub cluster itself (hub is not a target in pull model)

### 3. ArgoCD/GitOps -- Push Model
Hub ArgoCD connects to spokes → pushes resources directly
- ArgoCD runs only on the hub cluster
- Hub needs credentials (kubeconfig/service account token) for every target cluster
- Simpler to set up (single ArgoCD instance)
- **Risk:** hub compromise exposes all spoke clusters via stored credentials

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
| `Subscription` | "Subscription" | Application type in create dropdown (deprecated) |
| `Argo CD ApplicationSet - Pull model` | "Argo CD ApplicationSet - Pull model" | Application type in create dropdown |
| `Argo CD ApplicationSet - Push model` | "Argo CD ApplicationSet - Push model" | Application type in create dropdown |
| `Compare application types` | "Compare application types" | Link next to Create button |
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
