# Search Subsystem -- Known Issues

## 1. Search API RBAC -- Only Checks `list` Verb

**Versions:** ACM 2.15+
**Severity:** Medium
**Fix:** Code change needed

Search-api RBAC check only verifies `list` verb, not `*` (wildcard). Users with
`*` verb access but not explicit `list` see unexpected permission denials.

**Signals:** User has ClusterRole with `*` verb but search returns no results.
`oc auth can-i list <resource>` returns `yes` but search filters it out.

---

## 2. Fine-Grained RBAC Bypasses ManagedClusterView

**Versions:** ACM 2.15, 2.16
**Severity:** High
**Fix:** Ongoing code changes
**JIRAs:** ACM-30228, ACM-24887

Search bypasses ManagedClusterView permission check. RBAC filtering relies
solely on hub-side permissions (MCRA/ClusterPermission scope) without
validating spoke-side ManagedClusterView grants.

**Signals:** Compare resources visible via `oc get` vs search results. Check
ClusterPermission on spoke. Verify MCRA status conditions.

---

## 3. Collector Restarts on MCH Component Toggle

**Versions:** ACM 2.15+
**Severity:** Low
**Fix:** Code change needed + cluster-fixable workaround

When MCH components are toggled, addon reconciliation restarts search-collector.
Can reset memory resource overrides applied via annotations.

**Workaround:** Reapply memory annotations after MCH changes.

---

## 4. ImagePullBackOff on search-postgres

**Versions:** Any (common during z-stream upgrades)
**Severity:** High (total outage)
**Fix:** Cluster-fixable

PostgreSQL image not pullable due to registry auth, image not promoted, or
air-gapped without mirror.

**Signals:** `oc get pods -n <mch-ns> -l app=search-postgres` -- ImagePullBackOff.
Check Events for image pull errors.

**Fix:** Ensure image available. For air-gapped, mirror the image. For
promotion issues, wait for pipeline or manually tag.

---

## 5. search-pause Annotation Blocks MCH Deletion

**Versions:** ACM 2.15+
**Severity:** Medium
**Fix:** Cluster-fixable

The `search-pause` annotation on MCH CR prevents search operator cleanup during
uninstallation. MCH deletion hangs.

**Fix:** Remove annotation before uninstall:
`oc annotate mch multiclusterhub -n <ns> search-pause-`

---

## 6. VM Search Unstable for Fine-Grained RBAC Users

**Versions:** ACM 2.15, 2.16
**Severity:** High
**Fix:** Partially fixed in 2.16
**JIRAs:** ACM-30228, ACM-30764, ACM-24887

Multiple overlapping issues:
1. Missing resource kinds from virt ClusterRoles (StorageClass, ClusterOperator)
2. Aggregate API misses kubevirt roles from ClusterPermission `clusterRoleBindings` field
3. Search field exposure gaps -- fields in dropdown but not functional as filters

**Signals:** VMs not showing: check ClusterPermission for kubevirtprojects.
Missing kinds: search `kind:StorageClass cluster:<spoke>` as RBAC user.

---

## 7. Fleet Virt Tree View Needs Full Namespace Access

**Versions:** ACM 2.15, 2.16
**Severity:** Medium
**Fix:** Code change needed

Tree view constructs hierarchy from search results, requires full namespace
access within permitted scope. Without it, tree renders empty.

**Signals:** Tree empty for RBAC user but works for cluster-admin. Search
`kind:Namespace cluster:<spoke>` returns empty for that user.

---

## 8. Search Stops After Cluster Changes

**Versions:** All
**Severity:** Medium
**Fix:** Usually cluster-fixable

After import/detach/upgrade: collector addon may not auto-install, indexer
may lose postgres connection, collector may fail to reconnect.

**Fix:** Restart unhealthy pods, verify addon deployment, check postgres.

---

## Summary

| # | Issue | Cluster-Fixable? | Severity |
|---|-------|:---:|---|
| 1 | RBAC only checks `list` | No | Medium |
| 2 | FG-RBAC bypasses ManagedClusterView | No | High |
| 3 | Collector restarts on MCH toggle | Workaround | Low |
| 4 | ImagePullBackOff on postgres | Yes | High |
| 5 | search-pause blocks MCH deletion | Yes | Medium |
| 6 | VM search unstable for RBAC | Partial (2.16) | High |
| 7 | Tree view needs full NS access | No | Medium |
| 8 | Search stops after cluster changes | Usually | Medium |
