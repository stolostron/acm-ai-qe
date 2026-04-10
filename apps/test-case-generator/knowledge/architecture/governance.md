# Governance Area Knowledge

## Overview

The Governance area covers policy management in ACM Console, including policy creation, discovered policies, policy sets, and compliance reporting.

## Key Components

### Policy Types (8 kinds)
1. **ConfigurationPolicy** -- Most common; enforces configuration on managed clusters
2. **CertificatePolicy** -- Certificate expiration and compliance
3. **OperatorPolicy** -- Operator installation and update management
4. **Gatekeeper Constraints** (`constraints.gatekeeper.sh`) -- OPA-based admission control
5. **Gatekeeper Mutations** (`mutations.gatekeeper.sh`) -- OPA-based resource mutation (reduced table columns on Clusters tab)
6. **Kyverno ClusterPolicy** (`kyverno.io`) -- Cluster-scoped Kyverno policies
7. **Kyverno Policy** (`kyverno.io`, namespaced) -- Namespace-scoped Kyverno policies (adds Namespace column)
8. **ValidatingAdmissionPolicyBinding** (`admissionregistration.k8s.io`) -- K8s native admission

### Discovered vs Managed Policies
- **Discovered policies**: Found via search API on managed clusters; no parent policy in ACM
- **Managed policies**: Created through ACM Policy framework; have a parent Policy resource
- Both use `PolicyTemplateDetails` component for individual policy view

### Key Components
- `PolicyTemplateDetails.tsx` -- Individual policy details page (description list)
- `DiscoveredByCluster.tsx` -- Clusters tab showing policy instances across clusters
- `DiscoveredPolicies.tsx` -- Main discovered policies table
- `label-utils.ts` -- Label filtering utilities (system label exclusion)

### System Label Filtering
System labels filtered from display:
- `cluster-name` (exact match)
- `cluster-namespace` (exact match)
- `policy.open-cluster-management.io/*` (prefix match)

### Description List Field Order (PolicyTemplateDetails)
1. Name
2. Engine (with SVG icon)
3. Cluster
4. Kind
5. API version
6. Labels (after API version, before type-specific fields)
7. (Type-specific: Match Kinds for Gatekeeper, VAPB for Kyverno, Deployment/Update for OperatorPolicy)

For namespaced policies, Namespace appears between Name and Engine.

## Navigation Routes
- `discoveredPolicies`: `/multicloud/governance/discovered`
- `discoveredByCluster`: `/multicloud/governance/discovered/:apiGroup/:apiVersion/:kind/:policyName`
- `discoveredPolicyDetails`: `/multicloud/governance/discovered/:apiGroup/:apiVersion/:kind/:templateName/:templateNamespace?/:clusterName/detail`
- `policyTemplateDetails`: `/multicloud/governance/policies/details/:namespace/:name/template/:clusterName/:apiGroup?/:apiVersion/:kind/:templateName`

## Translation Keys
- `table.labels` -> "Labels"
- `Label` -> "Label" (filter)

## Testing Considerations
- Test both discovered AND managed policy paths (same component serves both)
- Gatekeeper mutations have reduced Clusters tab columns (no Labels column)
- Label filter supports equality (OR logic) and inequality (AND logic)
- AcmLabels uses compact mode in tables, full mode in details
