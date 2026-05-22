# Install Test Dependencies

External and internal dependencies required for Install (ACM/MCE installation) tests.

---

## Cluster Requirements

| Requirement | Details |
|-------------|---------|
| ROSA HCP cluster | Tests run on a ROSA Hosted Control Plane cluster |
| OCP version | Must match the ACM version's supported OCP range |
| Sufficient resources | Install tests create multiple operators; resource pressure causes timeouts |

## Downstream Image Dependencies

| Parameter | Purpose | Impact if Missing |
|-----------|---------|-------------------|
| `ACM_DS_TAG` | Downstream ACM operator image tag | Install uses upstream images, may fail version checks |
| `CUSTOM_REGISTRY_REPO` | Custom image registry | Operator images not found, CSV stays in Pending |

## Sub-Job Dependencies

Install pipeline runs downstream sub-jobs sequentially:

1. `install_mce_e2e_tests` -- runs first
2. `install_acm_e2e_tests` -- depends on MCE being installed

If MCE install fails (CSV never reaches `Succeeded`), all ACM install tests cascade-fail
because ACM depends on MCE.

## OLM Dependencies

| Dependency | Check Command |
|------------|---------------|
| CatalogSource healthy | `oc get catalogsource -n openshift-marketplace` |
| PackageManifest available | `oc get packagemanifest multiclusterhub-operator` |
| CSV phase Succeeded | `oc get csv -n open-cluster-management` |

## CRD Dependencies

Install tests validate CRD creation as part of the installation sequence:

| CRD | Created By | When |
|-----|-----------|------|
| `multiclusterhubs.operator.open-cluster-management.io` | ACM operator | During ACM install |
| `multiclusterengines.multicluster.openshift.io` | MCE operator | During MCE install |
| `klusterletconfigs.config.open-cluster-management.io` | MCE operator | After MCE CSV Succeeded |
