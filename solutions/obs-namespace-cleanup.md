---
title: Observability reinstall blocked by orphaned resources
symptom: "MCO CR creation fails with resource conflict errors"
keywords: [observability, reinstall, conflict, orphaned, PVC, namespace, open-cluster-management-observability, cleanup, uninstall]
affected_versions: "ACM 2.15+"
last_verified: 2026-05-26
status: active
---

## Symptom

Creating or re-creating the MultiClusterObservability (MCO) CR fails with resource conflict errors. Orphaned PVCs, secrets, or configmaps remain in the `open-cluster-management-observability` namespace from a failed uninstall or partial upgrade.

## Root Cause

Resources left behind in the `open-cluster-management-observability` namespace after a failed uninstall or interrupted upgrade. The MCO operator expects a clean namespace but finds conflicting resources with ownership annotations pointing to a previous MCO instance.

## Fix

```bash
# 1. Delete the MCO CR if it exists
oc delete mco observability --ignore-not-found

# 2. Delete the namespace (may hang on finalizers)
oc delete ns open-cluster-management-observability --wait=false

# 3. Wait for termination (check every 10s)
oc get ns open-cluster-management-observability -w

# 4. If namespace is stuck in Terminating, force-remove finalizers
oc get ns open-cluster-management-observability -o json | \
  jq '.spec.finalizers = []' | \
  oc replace --raw "/api/v1/namespaces/open-cluster-management-observability/finalize" -f -

# 5. Verify namespace is gone
oc get ns open-cluster-management-observability
# Should return "not found"

# 6. Now safe to recreate MCO
```

## References

- Knowledge DB: `.claude/knowledge/health/observability/known-issues.md` (issue #10)
- Severity: Medium (blocks observability deployment)
