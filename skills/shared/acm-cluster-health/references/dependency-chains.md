# Dependency Chain Verification

## Principle

Trace from symptom to root cause by following dependency chains. If Component A depends on Component B and B is broken, A's failures are CAUSED BY B. One root cause can explain multiple symptoms.

## Key ACM Dependency Chains

### Console -> Search
```
Console UI -> search-api -> search-collector -> search-postgres
```
If search-postgres is unhealthy, search results are empty, and multiple console features that depend on search data break simultaneously (Trap 8).

### Console -> Governance
```
Console UI -> governance-policy-propagator -> governance-policy-addon
```
Policy views depend on the propagator being healthy and addons running on managed clusters.

### Console -> Cluster Lifecycle
```
Console UI -> cluster-curator -> hive -> assisted-service
```
Cluster creation flows depend on the full chain. Hive uses StatefulSets (check separately from Deployments).

### Observability
```
Console UI -> observability-grafana -> thanos-query -> thanos-store -> S3 storage
```
Observability data flows through Thanos components to external storage.

### Fleet Virtualization
```
Console UI (kubevirt-plugin) -> search-api -> managed cluster VMs
```
Fleet Virt tree view depends on search indexing VM resources from spoke clusters.

## Verification Process

For each chain with a broken component:
1. Identify the broken link
2. Check what depends on it (upstream impact)
3. Check what it depends on (is there a deeper root cause?)
4. Count how many test failures this single root cause explains
5. Verify EACH upstream failure is actually CAUSED by this (not coincidental)
