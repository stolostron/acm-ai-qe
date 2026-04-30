# RBAC -- Known Issues

Based on RBAC-related bugs from ACM 2.14-2.17 (spanning Console, Virtualization,
Cluster Lifecycle, and Search components).

---

## 1. MCRA Controller Concurrent PATCH Panic (ACM-24737)

**Versions:** 2.15, 2.16 | **Severity:** Critical | **Fix:** Code change (PR#41)

MCRA operator panics on concurrent PATCH commands. Controller caches MCRA
resource in memory and uses stale state for optimistic updates. When multiple
updates arrive simultaneously, conflict handling is missing.

**Signals:** `panic: runtime error` in mcra-operator logs. Role assignments
created via console wizard partially applied. MCRA status shows incomplete
conditions.
**Fix:** Refactored reconcile flow with conflict requeue (PR#41).

---

## 2. Aggregate API Gaps for kubevirt Roles (ACM-24887)

**Versions:** 2.15, 2.16 | **Severity:** Blocker | **Fix:** Code change (PR#1052)

Search aggregate API only checks the original `clusterRole` field in
ClusterPermission, ignoring the `clusterRoleBindings` array field used for
multi-role VM assignments.

**Root cause:** API extension code predates the multi-role ClusterPermission
format. New field added for VM RBAC but aggregate API not updated.

**Signals:** RBAC user with kubevirt ClusterPermission sees no VMs in search.
`oc get clusterpermission -n {cluster} -o yaml` shows roles in
`clusterRoleBindings` array but search ignores them. cluster-admin sees VMs fine.

---

## 3. ClusterPermission Controller OOM at Scale (ACM-24032)

**Versions:** 2.15 | **Severity:** Important | **Fix:** Code change (PR#69, PR#77)

ClusterPermission controller uses `Owns` watch on ManifestWork, caching all
ManifestWorks in memory. At scale (hundreds of clusters, thousands of
ManifestWorks), this causes OOMKilled.

**Root cause:** Informer caches entire ManifestWork objects. Combined with
aggressive resync interval, memory usage grows unbounded.

**Signals:** `cluster-permission` pod OOMKilled. Memory usage climbs linearly
with ManifestWork count. Pod restart cycle.
**Fix:** Removed Owns ManifestWork watch, reduced resync rate (PR#69, PR#77).

---

## 4. MCRA CRD Breaking Change Blocks Upgrades (ACM-28211)

**Versions:** 2.15 -> 2.16 upgrade | **Severity:** Blocker | **Fix:** Code change (PR#3260)

MCRA CRD removed `v1alpha1` version in 2.16 without a conversion webhook.
Existing MCRAs stored as v1alpha1 in etcd fail CRD validation after upgrade.

**Signals:** ACM upgrade from 2.15 to 2.16 hangs or fails. MCRA resources
become inaccessible. `oc get mcra` returns validation errors referencing
stored version mismatch.
**Fix:** Restored v1alpha1 in CRD spec (PR#3260).

---

## 5. RBAC Pages Empty or Stop Displaying (ACM-26185)

**Versions:** 2.15, 2.16 | **Severity:** Critical | **Fix:** Code change (PR#5212)

User/Group/Role pages in User Management tab stop displaying intermittently,
especially at scale (many users, clusters, or role assignments).

**Root cause:** Incomplete rendering with large datasets. Frontend component
receives partial data and renders empty instead of waiting for complete response.

**Signals:** User Management pages load spinner then show empty tables.
Refreshing sometimes fixes temporarily. More frequent with large environments.

---

## 6. RBAC Wizard Scope Alignment Bugs (ACM-29966, ACM-28902)

**Versions:** 2.16 | **Severity:** Blocker | **Fix:** Code change (PR#5516)

RBAC wizard review section shows wrong scope information:
- Global access review doesn't show projects scope correctly
- Cluster selection in wizard saves all clusters instead of selected subset
- Review copy doesn't match what was configured in wizard steps

**Signals:** Review step in wizard shows different scope than configured.
Created MCRA spec doesn't match what user selected in wizard.

---

## 7. IDP-Related Empty User Lists

**Versions:** All (when fine-grained-rbac enabled) | **Severity:** Medium | **Fix:** Cluster-fixable

User Management tab renders but user/group lists are empty when:
- No IDP configured on hub cluster
- IDP connectivity issues (timeout, auth failure)
- IDP returns too many users (pagination not handled)

**Signals:** User Management tab loads but user table is empty. `oc get oauth
cluster -o jsonpath='{.spec.identityProviders}'` returns empty or no providers.

**Fix:** Configure IDP on hub cluster. Verify IDP connectivity.

---

## 8. Search RBAC Only Checks `list` Verb

**Versions:** 2.15+ | **Severity:** Medium | **Fix:** Code change needed

Search-api RBAC check verifies `list` verb but not `*` (wildcard). Users with
wildcard verb access but no explicit `list` see empty search results despite
having full access.

**Signals:** User with `*` verb ClusterRole sees no results in search.
`oc auth can-i list <resource>` returns yes but search filters it out.
cluster-admin works fine (separate code path).

---

## 9. ClusterPermission RoleBinding Namespace Wrong (ACM-22985)

**Versions:** 2.15 | **Severity:** Normal | **Fix:** Code change (PR#68)

ManagedServiceAccount addon namespace not updated in ClusterPermission after
the addon namespace was moved. RoleBinding created in wrong namespace on spoke.

**Signals:** RBAC user can't access resources in expected namespace despite
ClusterPermission existing. Check RoleBinding namespace on spoke vs expected.

---

## Bug Pattern Distribution

| Category | Count | Top Issues |
|---|---|---|
| MCRA controller | ~10 | Concurrent PATCH, CRD breaking change, OOM |
| Console RBAC UI | ~55 | Wizard state, scope alignment, empty pages |
| Search integration | ~8 | Aggregate API gaps, `list` verb, VM filtering |
| ClusterPermission propagation | ~5 | OOM, namespace wrong, ManifestWork scale |
| IDP / identity | ~3 | Empty user lists, connectivity |

## Root Cause Themes

1. **New feature maturity:** Fine-grained RBAC is young (2.14 TP, 2.15-2.16 GA)
2. **Multi-layer propagation:** MCRA -> ClusterPermission -> ManifestWork -> spoke RBAC
   has failure points at every layer
3. **API evolution:** New fields (clusterRoleBindings array) not honored by all consumers
4. **Scale issues:** In-memory caching of ManifestWorks and MCRAs doesn't scale
5. **CRD lifecycle:** Version removal without conversion webhook breaks upgrades

## Summary

| # | Issue | Cluster-Fixable? | Severity |
|---|-------|:---:|---|
| 1 | MCRA concurrent PATCH panic | No (code fix) | Critical |
| 2 | Aggregate API misses kubevirt roles | No (code fix) | Blocker |
| 3 | ClusterPermission OOM at scale | Partial (memory limits) | Important |
| 4 | MCRA CRD breaking change | No (code fix) | Blocker |
| 5 | RBAC pages empty at scale | No (code fix) | Critical |
| 6 | Wizard scope alignment | No (code fix) | Blocker |
| 7 | IDP empty user lists | Yes (configure IDP) | Medium |
| 8 | Search only checks `list` | No (code fix) | Medium |
| 9 | ClusterPermission NS wrong | No (code fix) | Normal |
