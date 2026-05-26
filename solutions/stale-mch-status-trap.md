---
title: MCH CR reports Running but operator is down (stale status)
symptom: "MCH phase: Running but components are degraded or not reconciling"
keywords: [MCH, Running, stale, status, multiclusterhub-operator, operator down, phase, frozen, reconciliation]
affected_versions: "ACM 2.12+"
last_verified: 2026-05-26
status: active
---

## Symptom

`oc get mch` shows `phase: Running` and everything looks healthy on the surface. But components are not reconciling -- crashed pods stay down, configuration changes are not applied, and addon deployments are stale.

## Root Cause

The MCH operator reconciles the MCH CR and updates `.status.phase`. If the operator pod is scaled to 0 or crashed, the status field **freezes** at its last-known value. The CR says "Running" because nobody is updating it to say otherwise. This is Diagnostic Trap #1 in the hub health methodology.

A variant (Trap 1b) occurs when both operator replicas show Running/Ready and health probes pass, but the Kubernetes leader election Lease expired (often due to etcd latency) and neither replica re-acquired it. Reconciliation has silently stopped.

## Fix

```bash
# 1. ALWAYS check operator pod health before trusting MCH status
oc get deploy multiclusterhub-operator -n <mch-ns> \
  -o jsonpath='{.spec.replicas}/{.status.availableReplicas}'
# If 0/0 or replicas mismatch, the MCH status is STALE

# 2. If operator is down, check why
oc describe deploy multiclusterhub-operator -n <mch-ns>
oc get events -n <mch-ns> --sort-by='.lastTimestamp' | tail -20

# 3. For Trap 1b (leader election stuck), check the Lease
oc get lease -n <mch-ns> -o yaml | grep -A5 holderIdentity

# 4. Restart the operator to recover
oc delete pods -n <mch-ns> -l name=multiclusterhub-operator
```

Same applies to MCE status -- check the `multicluster-engine` operator pod before trusting MCE `.status.phase`.

## References

- Knowledge DB: `.claude/knowledge/diagnostics/diagnostic-traps.md` (Trap 1 + Trap 1b)
- Classification impact: Missed trap causes INFRASTRUCTURE failures to be classified as PRODUCT_BUG
