# Addon Framework -- Data Flow

## End-to-End Addon Deployment Flow

```
Hub Cluster                                              Spoke Cluster
───────────                                              ─────────────

ClusterManagementAddon (cluster-scoped)
  defines addon globally
         │
         ▼
ManagedClusterAddon (in cluster ns)
  per-cluster instance
         │
         ▼
addon-manager-controller                                 work-agent
  (open-cluster-management-hub)                          (klusterlet)
  watches ManagedClusterAddon                                │
         │                                                   │
  generates ManifestWork ─────────────────────────────────►  applies payload
  (addon-<name>-deploy-0)                                    │
         │                                                   ▼
         │                                              Spoke resources:
         │                                              - Namespace
         │                                              - Deployment
         │                                              - ServiceAccount
         │                                              - ClusterRoleBinding
         │                                              - ConfigMap
         │                                                   │
         │                                                   ▼
         │                                              Addon pods start
         │                                                   │
  monitors health ◄──────────────────────────────────────  Lease renewal
  updates ManagedClusterAddon status                     (periodic heartbeat)
```

---

## Flow 1: Addon Deployment

1. ClusterManagementAddon registered on hub (created by operator or MCH
   reconciliation during install)
2. ManagedClusterAddon created in managed cluster's namespace on hub
   (automatically for default-enabled addons via install strategy, or
   manually for optional addons)
3. addon-manager-controller detects new ManagedClusterAddon
4. addon-manager merges configuration:
   - Global config from ClusterManagementAddon
   - Per-cluster overrides from ManagedClusterAddon annotations
   - AddOnDeploymentConfig references
5. addon-manager generates ManifestWork named `addon-<name>-deploy-0`
   in the cluster's namespace, containing:
   - Namespace on spoke (`open-cluster-management-agent-addon` typically)
   - ServiceAccount with required permissions
   - ClusterRole/ClusterRoleBinding for spoke-level RBAC
   - Deployment (or DaemonSet) for addon pods
   - ConfigMap for addon configuration
   - Secrets for credentials (if needed)
6. ManifestWork owned by ManagedClusterAddon (ownerReference set)
7. work-agent on spoke detects ManifestWork, applies payload
8. Addon pods start on spoke cluster

### Failure modes at each hop

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| 1. CMA registration | CMA missing after upgrade | ManagedClusterAddon can't be created | `oc get clustermanagementaddons` |
| 2. MCA creation | Addon not enabled in MCH | No MCA in cluster namespace | `oc get managedclusteraddons -n <cluster>` |
| 3. addon-manager | Controller down or OOM | MCA stuck in Progressing | `oc get pods -n open-cluster-management-hub -l app=clustermanager-addon-manager-controller` |
| 4. Config merge | Invalid config reference | MCA condition Configured=False | Check MCA status conditions |
| 5. ManifestWork gen | Resource conflict on spoke | ManifestWork created but status shows error | `oc get manifestwork addon-<name>-deploy-0 -n <cluster> -o yaml` |
| 6. work-agent | Spoke unreachable | ManifestWork stuck in Applying | Check ManagedCluster conditions |
| 7. Pod start | Image pull / resource limits | Spoke pods in ImagePullBackOff or Pending | Check addon pod status on spoke |

---

## Flow 2: Addon Upgrade

1. Addon operator or MCH reconciliation updates image references or config
2. ClusterManagementAddon or AddOnDeploymentConfig updated
3. addon-manager detects config change
4. addon-manager regenerates ManifestWork with new spec
5. work-agent on spoke detects ManifestWork update
6. work-agent applies updated resources (Deployment rolling update)
7. New addon pods start, old pods terminate
8. Health check verifies new version is healthy

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| Config update | addon-manager doesn't detect change | Old version persists | Compare ManifestWork content with expected |
| ManifestWork regen | Conflict with manual changes on spoke | ManifestWork status shows Apply error | Check ManifestWork conditions |
| Rolling update | Insufficient spoke resources | New pods Pending, old pods still running | Check addon pods on spoke |
| Health check | New version crashes | MCA Available=False, Degraded=True | `oc get managedclusteraddon -n <cluster> <addon> -o yaml` |

---

## Flow 3: Health Reporting (Lease-Based)

Most ACM addons use lease-based health reporting (the default strategy):

1. Addon pod on spoke creates/renews a Lease object periodically
   (in the addon namespace on the spoke)
2. addon-manager on hub monitors Lease status via ManifestWork feedback
3. If Lease renewed within threshold: ManagedClusterAddon condition
   `Available=True`, reason `ManagedClusterAddOnLeaseUpdated`
4. If Lease not renewed (addon pod crashed, network partition):
   ManagedClusterAddon condition `Available=False`

### ManagedClusterAddon standard conditions

| Condition | Meaning |
|-----------|---------|
| `Configured` | Configuration has been applied |
| `RegistrationApplied` | Registration and RBAC set up |
| `ClusterCertificateRotated` | Client certificate rotated (with validity window) |
| `ManifestApplied` | ManifestWork payload applied on spoke |
| `Progressing` | Addon is being installed or upgraded (False when done) |
| `Available` | Addon is healthy (lease renewed, pods running) |

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| Lease renewal | Addon pod crashed | Available=False after timeout | Check addon pod status on spoke |
| ManifestWork feedback | Spoke connectivity lost | Lease status stale on hub | Check ManagedCluster connectivity |
| addon-manager watch | Controller down | Health status frozen | Check addon-manager pods |
| False positive | Lease renewed but pod CrashLooping | Available=True but addon non-functional | Compare Lease status with actual pod status |

---

## Flow 4: Addon Removal

1. ManagedClusterAddon deleted (manually or by operator/MCH component toggle)
2. Finalizer on MCA triggers pre-delete tasks (if addon defines them)
3. Pre-delete task executes on spoke (e.g., cleanup, deregistration)
4. addon-manager deletes corresponding ManifestWork
5. work-agent on spoke removes resources (unless orphan annotation set)
6. Addon pods terminated, RBAC cleaned up
7. Finalizer removed, ManagedClusterAddon deleted

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| Pre-delete task | Task crashes (nil pointer, ACM-22679) | MCA stuck in Terminating | `oc get managedclusteraddon -n <cluster> <addon>` -- check finalizers |
| ManifestWork deletion | work-agent unreachable | ManifestWork stuck with finalizer | Check ManifestWork in cluster namespace |
| Resource cleanup | Orphan annotation prevents removal | Spoke resources persist after addon removed | Check spoke namespace for leftover resources |
