# ACM JIRA Component Mapping

Maps ACM Console areas to their JIRA component values for use in JQL queries.

| Area | JIRA Component | Example JQL |
|------|---------------|-------------|
| Governance | `Governance` | `component = "Governance"` |
| RBAC | `Virtualization` | `component = "Virtualization"` |
| Fleet Virtualization | `Virtualization` | `component = "Virtualization"` |
| CCLM | `Virtualization` | `component = "Virtualization"` |
| MTV | `Virtualization` | `component = "Virtualization"` |
| Clusters | `Cluster Lifecycle` | `component = "Cluster Lifecycle"` |
| Credentials | `Cluster Lifecycle` | `component = "Cluster Lifecycle"` |
| Search | `Search` | `component = "Search"` |
| Applications | `Application Lifecycle` | `component = "Application Lifecycle"` |

If the area is not listed above, read the `components` field from the source JIRA ticket via `get_issue`. The ticket's own component is authoritative.
