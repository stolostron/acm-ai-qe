---
type: health
subsystem: virtualization
acm_version: "5.0"
last_verified: 2026-08-12
related:
  - architecture/virtualization/architecture.md
  - failures/virtualization/failure-signatures.md
version_notes:
  - "All JIRA bugs in this file resolved before ACM 5.0 (historical context)"
---

# Virtualization -- Known Issues

Based on 99 virtualization/CNV bugs from ACM 2.14-2.17.

---

## 1. MCRA Controller Panics on Concurrent PATCH (ACM-24737)

**Versions:** 2.15, 2.16 | **Severity:** Critical | **Fix:** Code change (PR#41)
**JIRA Status:** Closed -- Fixed in ACM 2.15.0. Resolved in ACM 5.0.

MCRA controller panics when multiple concurrent PATCH requests arrive. Uses
stale in-memory state for optimistic updates, causing conflict panics.

**Root cause:** Controller caches MCRA resource in memory. Concurrent PATCHes
read same stale version, both try to update, one hits conflict, panic path
lacks recovery.

**Signals:** `panic: runtime error` in mcra-operator logs. MCRA status shows
partial updates. Role assignments created via UI sometimes silently fail.
**Fix:** Refactored reconcile flow, added conflict requeue logic (PR#41).

---

## 2. Aggregate API Misses kubevirt Roles (ACM-24887)

**Versions:** 2.15, 2.16 | **Severity:** Blocker | **Fix:** Code change (PR#1052)
**JIRA Status:** Closed -- Fixed in MCE 2.10.0. Resolved in ACM 5.0.

Search aggregate API doesn't pick up kubevirt roles from the
`clusterRoleBindings` array field in ClusterPermission. Only honors the older
single ClusterRole reference, not the newer array format.

**Root cause:** API extension only checked the original `clusterRole` field,
not the `clusterRoleBindings` array added for fine-grained VM RBAC.

**Signals:** RBAC user with kubevirt ClusterPermission sees no VMs in search.
`oc get clusterpermission -n {cluster} -o yaml` shows roles but search ignores them.
**Fix:** Extended API to honor clusterRoleBindings array (PR#1052).

---

## 3. MCRA CRD Breaking Change Blocks Upgrades (ACM-28211)

**Versions:** 2.15 -> 2.16 upgrade | **Severity:** Blocker | **Fix:** Code change (PR#3260)
**JIRA Status:** Closed -- Fixed in ACM 2.16.0. Resolved in ACM 5.0.

MCRA CRD removed `v1alpha1` version during 2.16 upgrade without a conversion
webhook. Existing MCRAs stored as v1alpha1 fail CRD validation post-upgrade.

**Root cause:** CRD version removal without conversion webhook. Kubernetes
requires stored versions to match CRD spec.

**Signals:** ACM upgrade from 2.15 to 2.16 fails or hangs. MCRA resources
become inaccessible. `oc get mcra` returns validation errors.
**Fix:** Restored v1alpha1 in CRD (PR#3260).

---

## 4. MTV Finalizer Race on ManagedCluster Deletion (ACM-29920)

**Versions:** 2.16 | **Severity:** Normal | **Fix:** Code change (PR#253)
**JIRA Status:** Closed -- Fixed in ACM 2.15.2 / ACM 2.16.0. Resolved in ACM 5.0.

mtv-integrations-controller adds finalizer to ManagedCluster while it's being
deleted. Race condition between controller reconciliation and cluster deletion.

**Root cause:** Controller doesn't check deletion timestamp before adding
finalizer. When ManagedCluster deletion starts, controller's next reconcile
adds finalizer, blocking deletion.

**Signals:** ManagedCluster stuck in "Terminating" state. Finalizer
`mtv-integrations.open-cluster-management.io` present. Manual finalizer
removal required.
**Fix:** Added deletion timestamp check before finalizer addition (PR#253).

---

## 5. RBAC UI Wizard Bugs (51 bugs cluster)

**Versions:** 2.15, 2.16 | **Severity:** Various (Normal to Blocker)

Extensive bugs in the fine-grained RBAC UI wizard for VM role assignments:
- Cluster selection saves all clusters instead of selected subset
- Project selection not filtering correctly
- Duplicate entries in cluster/project tables
- Search within wizard not working
- Review section showing wrong scope for global access (ACM-29966)
- Form state not resetting between wizard steps

**Root cause:** Fine-grained RBAC is a new feature (2.14 TP, 2.15-2.16 GA).
Wizard state management has extensive edge cases. PatternFly multiselect
components have state inconsistencies.

**Signals:** Role assignment creation via UI produces incorrect MCRA spec.
Manual `oc get mcra -o yaml` shows different scope than what was selected
in wizard.

---

## 6. VM Lifecycle Issues (30 bugs cluster)

**Versions:** 2.15, 2.16 | **Severity:** Various

VM operations failing or behaving incorrectly:
- Start/stop/pause actions failing for RBAC users
- VM details page timeout on large clusters
- Snapshot timestamps showing milliseconds instead of human-readable format
- VM status not updating after operations

**Root cause:** Multiple issues -- ManagedClusterView permission gaps,
search-v2-api connectivity issues, frontend rendering bugs.

**Signals:** VM action buttons return errors. Details page spinner doesn't
resolve. Check search-cluster-proxy logs for connectivity issues to spoke.

---

## 7. ManagedServiceAccount Rolebinding Conflicts (ACM-25546)

**Versions:** 2.15, 2.16 | **Severity:** Normal | **Fix:** Code change

MSA rolebinding uses wrong namespace, conflicting with HCO (HyperConverged
Operator) namespace on spoke.

**Root cause:** mtv-integrations-controller creates rolebinding in HCO namespace
instead of the dedicated MSA namespace.

**Signals:** MTV provider creation fails. Check spoke for conflicting
RoleBindings in `openshift-cnv` namespace.

---

## 8. Providers Go to Staging Mode (ACM-22762)

**Versions:** 2.15 | **Severity:** Normal | **Fix:** Code change

MTV providers transition to "staging" mode when ManagedServiceAccount token
rotation occurs. Forklift doesn't detect the new token.

**Root cause:** Token rotation updates the Secret but Forklift controller
doesn't watch for Secret changes on the provider credential.

**Signals:** Provider shows "staging" in MTV UI. Migration plans can't execute.
Check MSA token expiry and Forklift controller logs.

---

## 9. CCLM WaitingForReceiver Due to Sync Controller TLS Cert Mismatch

**Versions:** ACM 5.0, CNV 4.23 | **Severity:** Critical (blocks all CCLM) | **Fix:** Certificate regeneration

VM live migration stuck in `WaitForStateTransfer` / `WaitingForReceiver`. The spoke
cluster's `virt-synchronization-controller` gRPC server cannot bind port 9185 because
the server TLS certificate has a mismatched private key.

**Root cause:** The `kubevirt-synchronization-controller-server-certs` secret on the
spoke cluster has a TLS cert where the private key doesn't match the public key.
This prevents the gRPC server from starting, so the hub's sync controller cannot
establish the live migration data channel.

**Signals:**
- Spoke sync controller log: `"failed to load certificate: tls: private key does not match public key"`
- Hub sync controller log: `"transport: Error while dialing: dial tcp <spoke-pod-ip>:9185: connect: connection refused"`
- `/proc/net/tcp` on spoke sync pod shows NO LISTEN socket
- VMIM status: `DecentralizedNotLiveMigratable`

**Diagnostic:**
```bash
oc logs -n openshift-cnv -l kubevirt.io=virt-synchronization-controller --context=<spoke> | grep "failed to load"
oc exec -n openshift-cnv <sync-pod> --context=<spoke> -- cat /proc/net/tcp  # check for LISTEN on 23E1 (9185 hex)
```

**Fix:**
```bash
oc delete secret kubevirt-synchronization-controller-server-certs -n openshift-cnv --context=<spoke>
oc delete secret kubevirt-synchronization-controller-certs -n openshift-cnv --context=<spoke>
oc delete pods -n openshift-cnv -l kubevirt.io=virt-synchronization-controller --context=<spoke>
```
KubeVirt's cert-manager regenerates the secrets automatically on pod restart.

---

## 10. MTV forklift-operator CrashLoop on ARM (Exec format error)

**Versions:** MTV 2.12.5 on OCP arm64 (verified ACM 5.0.0-203 / OCP 4.22.8 AWS ARM)
**Severity:** High for MTV feature tests | **Cluster-Fixable:** Workaround only (use x86 cluster or ARM-capable MTV image)
**JIRA:** Related discussion MTV-2434 (ARM image build); no closed product bug matched for this exact CrashLoop.

On arm64 hubs, `forklift-operator` in `openshift-mtv` CrashLoopBackOff with:
`exec container process /usr/libexec/catatonit/catatonit: Exec format error`

**Root cause:** Operator image architecture mismatch — binary cannot execute on aarch64 nodes.

**Signals:**
- `oc get csv -n openshift-mtv` shows `mtv-operator` Failed
- Pod restarts climbing; logs are only the Exec format error line
- CNV/HCO can still be healthy (`Available=True`) — MTV failure is independent of CNV

**Diagnostic:**
```bash
oc logs -n openshift-mtv -l app=forklift --tail=5
oc get nodes -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.nodeInfo.architecture}{"\n"}{end}'
```

**Impact:** MTV migration UI/tests fail. Does not by itself abort Jenkins Cypress agent pods.

---

## Bug Pattern Distribution

| Category | Count | Top Issues |
|---|---|---|
| RBAC UI wizard | 51 | Cluster selection, project selection, duplicate entries, search |
| VM lifecycle | 30 | Start/stop failures, details timeout, snapshot display |
| MTV / migration | 4 | CCLM preflight, webhook blocking, provider staging |
| MCRA controller | ~6 | Concurrent PATCH panic, CRD breaking change, aggregate API |
| Build pipeline | ~8 | mtv-integrations Konflux compliance |

## Root Cause Themes

1. **New feature maturity:** Fine-grained RBAC is 2.14 TP / 2.15-2.16 GA with extensive wizard bugs
2. **Concurrent access:** MCRA controller lacks conflict handling for parallel updates
3. **API evolution:** CRD field additions (clusterRoleBindings array) not picked up by all consumers
4. **Lifecycle gaps:** Finalizer races, token rotation detection, MSA namespace conflicts
5. **Multi-layer RBAC:** VM access requires correct state across MCRA -> ClusterPermission -> search -> spoke roles

## Summary

| # | Issue | Cluster-Fixable? | Severity |
|---|-------|:---:|---|
| 1 | MCRA concurrent PATCH panic | No (code fix) | Critical |
| 2 | Aggregate API misses kubevirt roles | No (code fix) | Blocker |
| 3 | MCRA CRD breaking change | No (code fix) | Blocker |
| 4 | MTV finalizer race | Manual workaround | Normal |
| 5 | RBAC UI wizard bugs | No (code fix) | Various |
| 6 | VM lifecycle issues | Partial | Various |
| 7 | MSA rolebinding conflicts | Manual workaround | Normal |
| 8 | Providers go to staging | Restart provider | Normal |
| 9 | CCLM sync controller TLS cert mismatch | Manual workaround | Critical |
| 10 | MTV forklift Exec format error on ARM | Use x86 or ARM image | High |
