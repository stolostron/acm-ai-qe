# Search Area Knowledge

## Overview

ACM Search provides a unified search experience across all managed clusters, with RBAC-scoped results based on user permissions.

## Key Features
- Global resource search across all managed clusters
- RBAC-scoped results (users see only resources they have access to)
- Saved searches
- Resource detail views (YAML, related resources, logs)

## Navigation Routes
- `search`: `/multicloud/search`
- `resources`: `/multicloud/search/resources`
- `resourceYAML`: `/multicloud/search/resources/yaml`
- `resourceRelated`: `/multicloud/search/resources/related`
- `resourceLogs`: `/multicloud/search/resources/logs`

## Testing Considerations
- Search results depend on user RBAC permissions
- Search API uses GraphQL
- Resource details link to external Search resource views
