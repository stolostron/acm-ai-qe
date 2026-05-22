# Hosted Clusters Area Knowledge Base

Domain knowledge for writing Hosted Clusters (HyperShift) automation tests.

---

## Test Area

| Directory | Specs |
|-----------|-------|
| `cypress/tests/hostedClusters/aws/` | 2 specs (AWS hosted cluster) |
| `cypress/tests/hostedClusters/virtualization/` | 1 spec (virtualization hosted cluster) |

---

## Key Patterns

- HyperShift (hosted control planes): control plane runs as pods in hosting cluster
- AWS hosted: requires AWS credential + infrastructure
- Virtualization hosted: uses KubeVirt to run control plane VMs on hosting cluster
- Hosted clusters appear as ManagedClusters but with `hypershift` annotations
- Creation wizard differs from standard cluster creation

---

## Tags

`@CLC`, `@e2e`
