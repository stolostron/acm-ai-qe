# Application Lifecycle (ALC) Architecture

Application Lifecycle manages application deployment across managed clusters
using subscriptions, channels, and placement rules.

---

## Components

| Component | Type | Namespace | Pod Label | Role |
|-----------|------|-----------|-----------|------|
| multicluster-operators-application | Hub deployment | ocm | app=multicluster-operators-application | Application CR reconciliation |
| multicluster-operators-channel | Hub deployment | ocm | app=multicluster-operators-channel | Channel CR management |
| multicluster-operators-hub-subscription | Hub deployment | ocm | app=multicluster-operators-hub-subscription | Hub-side subscription processing |
| multicluster-operators-standalone-subscription | Hub deployment | ocm | app=multicluster-operators-standalone-subscription | Standalone subscription processing |
| multicluster-operators-subscription-report | Hub deployment | ocm | app=multicluster-operators-subscription-report | Subscription status reporting |
| application-manager | Spoke addon | varies | app=application-manager | Spoke-side app lifecycle management |

## Prerequisites

- `app-lifecycle` component enabled in MCH (enabled by default)
- `application-manager` addon deployed to spoke clusters
- `applications.app.k8s.io` CRD registered (critical -- missing CRD breaks all app tests)
- For ArgoCD: `openshift-gitops` operator installed, ApplicationSet CRD registered

## Key CRDs

| CRD | API Group | Purpose |
|-----|-----------|---------|
| Application | app.k8s.io/v1beta1 | Application grouping resource |
| Subscription | apps.open-cluster-management.io/v1 | Defines what to deploy and from where |
| Channel | apps.open-cluster-management.io/v1 | Source repository (Git, Helm, Object Storage) |
| PlacementRule | apps.open-cluster-management.io/v1 | Target cluster selection |
| ApplicationSet | argoproj.io/v1alpha1 | ArgoCD application set (requires GitOps operator) |

## Channel Types

| Type | Description | Common issues |
|------|-------------|---------------|
| Git | Git repository source | Auth failures, branch not found |
| HelmRepo | Helm chart repository | Chart version not found |
| ObjectBucket | S3-compatible storage | Credential/connectivity issues |
| Namespace | Same-cluster namespace | Namespace not found |

## Console Integration

ALC pages: `/multicloud/applications`

The application table shows status, sync state, and topology. ArgoCD
applications display sync/health status from the GitOps controller.
CSV export functionality uses `cy.readFile()` to verify downloaded files.

## Test Repository Structure

ALC tests are in `stolostron/application-ui-test` (local clone: alc-ui).
Tests organized by app type: Git, Helm, ObjectStorage, Argo, Flux, Ansible.
Common views in `tests/cypress/views/common.js` -- uses `.within()` scoping
which causes PF6 portal visibility issues with menu items.
