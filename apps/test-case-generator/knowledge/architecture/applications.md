# Applications Area Knowledge

## Overview

Application Lifecycle (ALC) in ACM Console manages application deployments across managed clusters using subscriptions, channels, and placement rules.

## Key Features
- Application creation (Argo CD, Subscription-based)
- Application topology view
- Channel management (Git, Helm, ObjectBucket)
- Subscription management
- Placement integration

## Navigation Routes
- `applications`: `/multicloud/applications`
- `createApplicationArgo`: `/multicloud/applications/create/argo`
- `createApplicationSubscription`: `/multicloud/applications/create/subscription`
- `applicationDetails`: `/multicloud/applications/details/:namespace/:name`
- `applicationTopology`: `/multicloud/applications/details/:namespace/:name/topology`

## Testing Considerations
- Argo CD and Subscription models have different creation flows
- Topology view requires application deployment to managed clusters
- Channel types affect available configuration options
