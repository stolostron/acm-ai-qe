---
type: versions
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - versions/version-matrix.md
  - architecture/install/olm-install-chain.md
  - architecture/acm-platform.md
  - baselines/component-registry.md
---

# ACM 2.x to 5.0 Migration Reference

Documents all breaking changes, renames, deprecations, and new components
between the ACM 2.x line (specifically 2.16, the last 2.x release) and
ACM 5.0. Derived from the KB accuracy audit (Phase 2) and verified against
a live ACM 5.0.0-193 cluster on 2026-08-10.

---

## 1. Version Numbering Change

ACM jumped from 2.16 to 5.0 -- there is no ACM 2.17 release.

| Aspect | ACM 2.16 | ACM 5.0 |
|--------|----------|---------|
| CSV name | `advanced-cluster-management.v2.16.x` | `advanced-cluster-management.v5.0.0-xxx` |
| MCE CSV | `multicluster-engine.v2.11.x` | `multicluster-engine.v5.0.0-xxx` |
| ACM OLM channel | `release-2.16` | `release-5.0` |
| MCE OLM channel | `stable-2.11` | `stable-5.0` |

The build-number format also changed: ACM 2.x used `v2.16.0`, `v2.16.1` for
z-streams. ACM 5.0 uses `v5.0.0-193` with a build counter suffix for
nightly/dev builds.

---

## 2. Namespace Changes

### MCH Namespace

| ACM 2.x | ACM 5.0 | Impact |
|---------|---------|--------|
| `open-cluster-management` (default) | `ocm` (default) | All `oc` commands referencing the MCH namespace must be updated |

This is the most pervasive change. Every diagnostic command, health check,
and automation script that hardcodes `open-cluster-management` as the MCH
namespace breaks on ACM 5.0 clusters. Always discover dynamically:
`oc get mch -A -o jsonpath='{.items[0].metadata.namespace}'`

### Other Namespace Changes

| Component | ACM 2.x Namespace | ACM 5.0 Namespace | Notes |
|-----------|-------------------|-------------------|-------|
| `cluster-proxy` | `open-cluster-management` | `multicluster-engine` | Moved to MCE namespace |
| `hive-operator` | `hive` | `multicluster-engine` | Operator in MCE ns; still deploys controllers INTO `hive` ns |

---

## 3. Renamed Components

### Deployments

| Old Name (ACM 2.x) | New Name (ACM 5.0) | Namespace | Notes |
|---------------------|---------------------|-----------|-------|
| `registration-operator` | `cluster-manager` | `multicluster-engine` | 3 replicas. Creates 6 hub controllers in `open-cluster-management-hub` |
| `subscription-controller` | `multicluster-operators-hub-subscription` | MCH namespace | Standalone `subscription-controller` deployment no longer exists |
| `channel-controller` | (integrated into multicluster-operators-channel) | MCH namespace | No standalone deployment |
| `addon-manager` (hub reference) | `cluster-manager-addon-manager-controller` | `open-cluster-management-hub` | 3 replicas; old name used as shorthand in docs |
| `registration-operator` (hub controller) | `cluster-manager-registration-controller` | `open-cluster-management-hub` | 3 replicas |
| `work-manager` (hub deployment) | (removed as standalone) | -- | Spoke-side `klusterlet-addon-workmgr` still exists; `work-manager` ClusterManagementAddon still exists |
| `console-mce` (deployment) | `console-mce-console` | `multicluster-engine` | Pod label remains `app=console-mce` (label NOT renamed) |

### Pod Labels (Unchanged Despite Deployment Renames)

| Deployment | Label | Notes |
|------------|-------|-------|
| `console-mce-console` | `app=console-mce` | Deployment renamed but pod label preserved from ACM 2.x |

---

## 4. Removed Features

### iam-policy-controller

| Aspect | Details |
|--------|---------|
| Deprecated in | ACM 2.16 |
| Removed in | ACM 5.0 |
| What it did | IAM policy enforcement on spoke clusters |
| ClusterManagementAddon | Not present on ACM 5.0 clusters |
| Impact | Policies referencing IamPolicy kind will not be enforced |
| Migration | Use ConfigurationPolicy to audit IAM settings instead |

### work-manager Hub Deployment

| Aspect | Details |
|--------|---------|
| Removed in | ACM 5.0 |
| What changed | No standalone `work-manager` deployment on the hub side |
| Still exists | `work-manager` ClusterManagementAddon (hub-side definition), `klusterlet-addon-workmgr` (spoke-side) |
| Impact | Diagnostic commands looking for `work-manager` pods on the hub return no results |
| Hub equivalent | `cluster-manager-work-webhook` in `open-cluster-management-hub` |

---

## 5. CRD API Version Status

| CRD | API Version in ACM 5.0 | Notes |
|-----|------------------------|-------|
| `Placement` | `v1beta1` only | No promotion to v1; still `cluster.open-cluster-management.io/v1beta1` |
| `PlacementDecision` | `v1beta1` only | Same; `cluster.open-cluster-management.io/v1beta1` |
| `ManagedClusterSet` | `v1beta2` | `cluster.open-cluster-management.io/v1beta2` |
| `ManagedCluster` | `v1` | `cluster.open-cluster-management.io/v1` (stable) |
| `ManifestWork` | `v1` | `work.open-cluster-management.io/v1` (stable) |
| `ManagedClusterAddon` | `v1alpha1` | `addon.open-cluster-management.io/v1alpha1` |
| `ClusterManagementAddon` | `v1alpha1` | `addon.open-cluster-management.io/v1alpha1` |
| `Policy` | `v1` | `policy.open-cluster-management.io/v1` (stable) |
| `MultiClusterHub` | `v1` | `operator.open-cluster-management.io/v1` (stable) |
| `MultiClusterEngine` | `v1` | `multicluster.openshift.io/v1` (stable) |
| `MultiClusterRoleAssignment` | `v1alpha1` | `rbac.open-cluster-management.io/v1alpha1` |
| `ClusterPermission` | `v1alpha1` | `rbac.open-cluster-management.io/v1alpha1` |

---

## 6. JIRA Bugs Resolved Before ACM 5.0

All 43 JIRA bugs referenced in health/known-issues files were resolved before
ACM 5.0. These were reclassified as historical context during the Phase 2
audit. They remain in the KB for failure pattern recognition but are marked
with resolution status.

---

## 7. New or Changed Components in ACM 5.0

### New MCH Components (since 2.16)

| Component | Namespace | Purpose |
|-----------|-----------|---------|
| `fine-grained-rbac` | MCH namespace | MCRA controller for multicluster RBAC. Disabled by default. |
| `siteconfig` | MCH namespace | Zero Touch Provisioning for telco/edge. |
| `cnv-mtv-integrations` | MCH namespace | CNV and MTV console integration. Disabled by default. |

### Changed Replica Counts

| Deployment | ACM 2.x | ACM 5.0 | Namespace |
|------------|---------|---------|-----------|
| `multiclusterhub-operator` | 1 | 2 | MCH namespace |
| `multicluster-engine-operator` | 1 | 2 | `multicluster-engine` |
| `cluster-manager` | 1 | 3 | `multicluster-engine` |

### ConsolePlugin Changes

Registered ConsolePlugin CRs on ACM 5.0:
`acm`, `mce`, `forklift-console-plugin`, `gitops-plugin`, `kubevirt-plugin`,
`monitoring-plugin`, `monitoring-console-plugin`, `networking-console-plugin`

---

## 8. Diagnostic Command Migration

Commands that need updating for ACM 5.0:

| Purpose | ACM 2.x Command | ACM 5.0 Command |
|---------|-----------------|-----------------|
| List ACM pods | `oc get pods -n open-cluster-management` | `oc get pods -n ocm` (or discover with `oc get mch -A`) |
| ACM CSV | `oc get csv -n open-cluster-management` | `oc get csv -n ocm` |
| ACM Subscription | `oc get subscription -n open-cluster-management` | `oc get subscription -n ocm` |
| Search pods | `oc get pods -n open-cluster-management \| grep search` | `oc get pods -n ocm \| grep search` |
| GRC propagator | `oc get pods -n open-cluster-management -l app=grc-policy-propagator` | `oc get pods -n ocm -l app=grc-policy-propagator` |
| Work manager pods | `oc get pods -n open-cluster-management-hub -l app=work-manager` | `oc get pods -n open-cluster-management-hub -l app=cluster-manager-work-webhook` |
| Registration controller | `oc get deploy registration-operator -n open-cluster-management-hub` | `oc get deploy cluster-manager-registration-controller -n open-cluster-management-hub` |

**Best practice:** Always discover the MCH namespace dynamically:
```bash
MCH_NS=$(oc get mch -A -o jsonpath='{.items[0].metadata.namespace}')
oc get pods -n $MCH_NS
```

---

## 9. OLM Installation Chain Changes

| Aspect | ACM 2.x | ACM 5.0 |
|--------|---------|---------|
| MCH namespace (default) | `open-cluster-management` | `ocm` |
| ACM subscription channel | `release-2.16` | `release-5.0` |
| MCE subscription channel | `stable-2.11` | `stable-5.0` |
| ACM CSV version format | `v2.16.x` | `v5.0.0-xxx` |
| MCE CSV version format | `v2.11.x` | `v5.0.0-xxx` |
| MCH operator replicas | 1 | 2 (HA) |
| MCE operator replicas | 1 | 2 (HA) |

---

## 10. Migration Checklist for KB Authors

When writing or updating KB files:

1. **Never hardcode** `open-cluster-management` as the MCH namespace -- use
   `<mch-namespace>` or the discovery command
2. **Check deployment names** against live cluster -- several were renamed in 5.0
3. **Check pod labels** separately from deployment names -- some labels were
   preserved despite renames (e.g., `console-mce`)
4. **Verify ClusterManagementAddons** -- `iam-policy-controller` was removed
5. **Use correct OLM channels** -- `release-5.0` / `stable-5.0`, not `2.17`
6. **Note version context** -- add "Changed in ACM 5.0" annotations for
   version-dependent content
