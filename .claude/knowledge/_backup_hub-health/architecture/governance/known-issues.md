# Governance (GRC) -- Known Issues

Based on 100 GRC bugs from ACM 2.12-2.17.

---

## 1. ConfigurationPolicy Hot-Loop (ACM-25694)

**Versions:** 2.15, 2.16 | **Severity:** Normal | **Fix:** Code change

config-policy-controller re-evaluates compliant policies every ~10s even when
nothing changed. Lookup watchers trigger on status-only changes.

**Root cause:** Controller evaluates -> compliant -> watched resource status
updates -> watcher fires -> re-evaluates -> still compliant -> repeat.

**Signals:** Frequent "Evaluating" in controller logs. Elevated CPU. Constant
`config_policies_evaluation_duration_seconds` activity.

**Workaround:** Set `evaluationInterval.compliant: "1h"` for stable policies.

---

## 2. Status Updates Overload Framework (ACM-28668)

**Versions:** 2.15.1 | **Severity:** Blocker | **Fix:** Code change (z-stream)

History calculation bug causes Status Sync to re-emit compliance events on
every cycle even when state unchanged. At scale: hub API throttling, propagator
memory pressure, stale compliance data.

**Signals:** Compliance "flickering" in UI. High propagator memory.
Framework addon logs show continuous status writes.

---

## 3. pruneObjectBehavior=DeleteAll + objectSelector (ACM-26186)

**Versions:** 2.15, 2.16 | **Severity:** Blocker | **Fix:** Code change (PR#1560)

Objects incorrectly deleted on policy removal. Pruning logic didn't filter by
objectSelector -- deleted objects no longer matching the selector.

**Signals:** Resources unexpectedly deleted after policy removal.
**Workaround:** Use `DeleteIfCreated` instead of `DeleteAll` with objectSelector.

---

## 4. config-policy-controller Crash During Uninstall (ACM-22679)

**Versions:** 2.14, 2.15 | **Severity:** Major | **Fix:** Code change

Nil pointer in addon pre-delete task (`triggeruninstall.go`). CrashLoopBackOff
during addon removal.

**Signals:** `panic: runtime error: invalid memory address or nil pointer
dereference` in logs. Addon removal hangs.
**Workaround:** Force-delete the pod and ManagedClusterAddon.

---

## 5. Gatekeeper ConstraintTemplate Oscillation (ACM-29231)

**Versions:** 2.16 | **Severity:** Critical | **Fix:** Code change

Gatekeeper Sync Controller treats identical audit results as "new" on each
cycle, flipping compliance status repeatedly.

**Signals:** Compliance status oscillating in dashboard. `cluster_policy_governance_info`
metric flips between 0 and 1.

---

## 6. Policy Template Namespace Mismatch (ACM-17666)

**Versions:** 2.13, 2.14, 2.15 | **Severity:** Normal | **Fix:** Code change (PR#625)

Namespace validation runs BEFORE template resolution. Go template expressions
in namespace field compared literally against expected value.

**Signals:** `error: namespace does not match` for policies using `{{ }}`
in namespace field.

---

## 7. OperatorPolicy Multi-CSV InstallPlan (ACM-20500)

**Versions:** 2.14, 2.15 | **Severity:** Normal | **Fix:** Code change

Approval logic expects 1:1 InstallPlan-to-CSV mapping. Fails with multi-CSV
InstallPlans.

**Signals:** InstallPlan stuck `RequiresApproval`. OperatorPolicy non-compliant.
**Workaround:** Manually approve InstallPlan or use `upgradeApproval: Automatic`.

---

## 8. Template Library Crashes on Arrays (ACM-20863)

**Versions:** 2.14, 2.15 | **Severity:** Normal | **Fix:** Code change

Template engine panics when `lookup` returns an array assigned to context variable.
Type assertion fails.

**Signals:** Panic in template processing. Stack trace references template evaluation.
**Workaround:** Use `range` to iterate arrays, don't assign directly to context.

---

## 9. mustnothave Behavior Change (ACM-15772)

**Versions:** 2.12 -> 2.13+ | **Severity:** Normal | **Fix:** Upgrade regression

Field comparison semantics changed for `mustnothave` across versions. Policies
compliant in 2.12 may become non-compliant in 2.13+ without policy/cluster changes.

**Signals:** mustnothave policies change compliance state after upgrade.
**Fix:** Review and adjust mustnothave policies after upgrade.

---

## Bug Pattern Distribution

| Category | Count | Top Issues |
|---|---|---|
| ConfigurationPolicy | 29 | Hot-loop, pruning, namespaceSelector, objectSelector |
| Compliance reporting | 13 | Wrong counts, status overload, Kyverno fields |
| OperatorPolicy | 7 | Multi-CSV, invalid status, mustonlyhave |
| Gatekeeper | 6 | ConstraintTemplate oscillation, mutator discovery |
| Upgrade regressions | 10 | mustnothave behavior, PF5 sidebar, CLI version |
| Template processing | ~5 | Namespace mismatch, array crash, encryption |
| Addon lifecycle | ~5 | Uninstall crash, framework overload |

## Root Cause Themes

1. **Watch sensitivity:** Controllers watching too broadly, triggering on status-only changes
2. **Template resolution ordering:** Validation before resolution
3. **Nil pointer safety:** Missing nil checks in error/cleanup paths
4. **Multi-resource edge cases:** Logic for single resources failing with multiple
5. **Behavioral assumptions across versions:** Comparison semantics changing
