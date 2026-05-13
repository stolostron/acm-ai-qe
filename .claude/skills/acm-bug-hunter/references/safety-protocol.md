# Safety Protocol -- Dimension 6 Probe Resource Creation

Dimension 6.4 (Integration Probing) creates minimal resources on the live test cluster to verify integration paths. This protocol is MANDATORY for all resource creation.

## Pre-Creation Checklist

```
BEFORE creating ANY resource:
  1. PLAN: Write out the exact YAML/command that will be executed
  2. NAMESPACE: Always use a dedicated probe namespace:
     "tca-probe-<timestamp>" (e.g., tca-probe-1747012800)
  3. LABEL: Every created resource MUST have the label:
     "tca-probe=true" and "tca-session=<timestamp>"
  4. SCOPE: Never create cluster-scoped resources unless
     absolutely necessary. Prefer namespaced resources.
  5. MINIMAL: Use the smallest possible resource definition.
     No real workloads, no real images, no real secrets.
  6. INVENTORY: Maintain a running list of every resource
     created (kind, name, namespace) for cleanup.
  7. DRY-RUN FIRST: Run `oc apply --dry-run=server -f <yaml>`
     before actual creation to catch validation errors without
     side effects.
  8. IMPACT CHECK: Before creating, verify the resource won't
     trigger reconciliation loops, webhook side effects, or
     quota exhaustion by checking:
     - oc get resourcequota -n <namespace>
     - oc get limitrange -n <namespace>
     - oc get validatingwebhookconfigurations (for relevant CRDs)
  9. ONE AT A TIME: Create resources one by one, verify each
     before creating the next. Never batch-apply.
 10. TIMEOUT: If a created resource doesn't reach expected
     state within 60 seconds, abandon the probe and record
     the finding without further resource creation.
```

## Allowed Probe Types (exhaustive list)

- Namespaces (prefixed `tca-probe-`)
- ConfigMaps (for configuration flow verification)
- Labels/annotations on the probe namespace itself
- ManagedClusterSetBindings (if testing RBAC/cluster set features)
- Minimal CRs for the feature's own CRDs (empty/skeleton spec)

## Prohibited (never create these)

- Deployments, Pods, StatefulSets (no workloads)
- Secrets with real credentials
- ClusterRoleBindings or ClusterRoles (cluster-wide RBAC impact)
- ManagedClusterActions or ManagedClusterViews (spoke-side effects)
- Anything that triggers external cloud provider calls

## Cleanup Rules (non-negotiable)

Cleanup runs ALWAYS -- even if 6.4 fails or errors out.

```
  1. Only delete resources with label "tca-probe=true" AND
     "tca-session=<this-session-timestamp>"
  2. NEVER delete resources in system namespaces
     (openshift-*, kube-*, open-cluster-management*)
  3. NEVER use broad selectors like "oc delete all"
  4. Delete namespace LAST (after verifying no non-probe
     resources were accidentally placed in it)
  5. Verify cleanup with a final label-based query:
     oc get all -l tca-probe=true -A
  6. Log every deletion in the investigation trail
```

## Cleanup Failure Handling

If ANY resource from the inventory list survives cleanup:
- Report it prominently in the audit report as a "CLEANUP FAILURE"
- Provide the exact `oc delete` command for manual removal
- NEVER delete any resource that was NOT created by this session (no `tca-probe=true` label = hands off)
