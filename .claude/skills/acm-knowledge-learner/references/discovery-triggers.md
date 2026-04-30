# Discovery Triggers

## When to Investigate

| Trigger | Evidence | Action |
|---------|----------|--------|
| Unknown CSV in ACM namespace | CSV not in component-registry.md | Full 8-source introspection, write to learned/<operator>.md |
| Unknown pod failure pattern | Log error not matching failure-patterns.md | Extract pattern, write to learned/new-patterns.yaml |
| Two unrelated subsystems failing | No known dependency chain connects them | Trace env vars + owner refs, write to learned/new-chains.yaml |
| TLS handshake failures | Pod logs show certificate errors | Check secret ages + CSR status, write to learned/cert-issues.yaml |
| Post-upgrade pod instability | Pod restarts within 30 min of MCH upgrade | Compare pod ages vs upgrade time, write to learned/upgrade-observations.yaml |
| ConsolePlugin with unknown backend | Plugin registered but backend not in registry | Introspect backend service, write to learned/<plugin>.md |
| Third-party operator in ACM namespace | Non-ACM CSV managing resources in MCH namespace | Full introspection, assess ACM integration level |

## Skip Triggers

Do NOT investigate:
- Pods in terminal states (Succeeded, Completed) -- these are jobs, not components
- Resources in `openshift-*` namespaces (OCP infrastructure, not ACM)
- Resources older than 90 days with no recent changes (stable, unlikely new discovery)
