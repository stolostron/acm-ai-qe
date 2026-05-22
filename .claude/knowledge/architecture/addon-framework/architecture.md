# Addon Framework -- Architecture

## What the Addon Framework Does

Provides a standardized mechanism for deploying, configuring, upgrading, and
monitoring agent components on managed clusters. Nearly every ACM spoke-side
component is deployed via the addon framework: search-collector,
governance-policy-framework, config-policy-controller, metrics-collector,
application-manager, acm-roles, and more.

The framework abstracts the complexity of multi-cluster agent deployment into
two CRDs: `ClusterManagementAddon` (hub-level definition) and
`ManagedClusterAddon` (per-cluster instance).

---

## Core CRDs

### ClusterManagementAddon (hub-level)

Defines an addon globally:
- **Kind:** `ClusterManagementAddon`
- **API Group:** `addon.open-cluster-management.io/v1alpha1`
- **Scope:** Cluster-scoped (hub)

Specifies:
- Addon name and description
- Installation namespace on spoke
- Supported configuration types (AddOnDeploymentConfig)
- Health check strategy (Lease, Work, Custom)

### ManagedClusterAddon (per-cluster)

Per-cluster addon instance:
- **Kind:** `ManagedClusterAddon`
- **API Group:** `addon.open-cluster-management.io/v1alpha1`
- **Scope:** Namespaced (in managed cluster's namespace on hub)

Controls:
- Addon deployment to specific cluster
- Per-cluster configuration overrides (via annotations)
- Addon health status and conditions
- Installation namespace override

---

## Addon Lifecycle

### Deploy

1. ClusterManagementAddon registered on hub (by operator or MCH)
2. ManagedClusterAddon created in managed cluster's namespace
   (automatically for default-enabled addons, manually for others)
3. addon-manager detects ManagedClusterAddon
4. addon-manager generates ManifestWork containing spoke-side resources
   (Deployment, ServiceAccount, RBAC, ConfigMaps)
5. work-agent on spoke applies ManifestWork payload
6. Addon pods start on spoke

### Upgrade

1. Addon operator updates ClusterManagementAddon or image references
2. addon-manager regenerates ManifestWork with new specs
3. work-agent applies updated ManifestWork
4. Spoke pods rolling-updated to new version

Upgrade strategy depends on addon implementation:
- Most addons use rolling update via Deployment spec
- Some addons have pre/post-upgrade hooks
- Addon framework supports automatic rollback on failed health checks

### Remove

1. ManagedClusterAddon deleted (manually or by operator)
2. addon-manager deletes corresponding ManifestWork
3. work-agent removes spoke-side resources
4. Addon pods terminated, RBAC cleaned up

**Pre-delete tasks:** Some addons define pre-delete jobs. Failures in pre-delete
can block addon removal (e.g., config-policy-controller nil pointer crash
during uninstall, ACM-22679).

---

## addon-manager

- **Pod label:** `app=addon-manager`
- **Namespace:** MCH namespace

Central hub controller that orchestrates all addon deployments:
1. Watches ClusterManagementAddon and ManagedClusterAddon resources
2. Generates ManifestWork for each addon on each target cluster
3. Monitors addon health based on configured health check strategy
4. Handles addon configuration merging (global + per-cluster overrides)

addon-manager is critical infrastructure. If it goes down, no new addons
deploy, no addon upgrades proceed, and addon health monitoring stops.

---

## Health Reporting

### Strategies

Addons report health to the hub through one of three mechanisms:

**1. Lease-based (default):**
- Addon pods periodically renew a Lease object on the managed cluster
- addon-manager on hub watches Lease renewal via ManifestWork feedback
- If Lease not renewed within timeout, addon marked unhealthy
- Simple and reliable for most addons

**2. Work-based:**
- Health derived from ManifestWork status
- If all resources in ManifestWork are Applied, addon is healthy
- If any resource fails, addon marked degraded
- Good for addons without long-running pods

**3. Custom:**
- Addon operator implements its own health check logic
- Reports health via ManagedClusterAddon status conditions
- Used by complex addons with multiple sub-components

### Health Conditions

ManagedClusterAddon status includes standard conditions:
- `Available` -- addon is healthy and functioning
- `Degraded` -- addon is partially functional
- `Progressing` -- addon is being installed/upgraded

---

## Configuration

### Global Configuration (ClusterManagementAddon)

Applied to all instances of the addon across all clusters:
- Image references
- Default resource limits
- Feature flags
- Log levels

### Per-Cluster Configuration (ManagedClusterAddon annotations)

Override global settings for specific clusters:
- Resource limits: `addon.open-cluster-management.io/<addon>_memory_limit`
- Log level: `addon.open-cluster-management.io/<addon>_log_level`
- Custom parameters per addon

### AddOnDeploymentConfig

Reusable configuration object that can be referenced by ManagedClusterAddon:
- Defines configuration values in a structured format
- Can be shared across clusters
- Supports environment variables, volume mounts, resource overrides

---

## Common Addons in ACM

| Addon Name | Component | Default | Namespace on Spoke |
|---|---|---|---|
| `search-collector` | Search | Enabled | `open-cluster-management-agent-addon` |
| `governance-policy-framework` | GRC | Enabled | `open-cluster-management-agent-addon` |
| `config-policy-controller` | GRC | Enabled | `open-cluster-management-agent-addon` |
| `cert-policy-controller` | GRC | Enabled | `open-cluster-management-agent-addon` |
| `application-manager` | ALC | Enabled | `open-cluster-management-agent-addon` |
| `metrics-collector` | Observability | Enabled (when obs enabled) | `open-cluster-management-addon-observability` |
| `acm-roles` | RBAC | Enabled (when FG-RBAC enabled) | `open-cluster-management-agent-addon` |
| `work-manager` | Infrastructure | Enabled | `open-cluster-management-agent-addon` |
| `cluster-proxy` | Infrastructure | Enabled | `open-cluster-management-agent-addon` |
| `managed-serviceaccount` | Infrastructure | Enabled | `open-cluster-management-agent-addon` |
| `hypershift-addon` | CLC | Enabled | `open-cluster-management-agent-addon` |

---

## ManifestWork Generation

addon-manager generates ManifestWork resources in each managed cluster's
namespace on hub. ManifestWork payload typically includes:

1. **Namespace** for addon on spoke
2. **ServiceAccount** with appropriate permissions
3. **ClusterRole/ClusterRoleBinding** for spoke-level RBAC
4. **Deployment** (or DaemonSet) for addon pods
5. **ConfigMap** for addon configuration
6. **Secret** for credentials (if needed)

ManifestWork uses orphan annotations for cleanup control:
- Resources deleted when ManifestWork is deleted (default)
- Orphan annotation prevents deletion for resources that should persist

---

## Failure Modes

### addon-manager down
- **Impact:** No new addon deployments, no upgrades, no health monitoring
- **Scope:** All addons across all clusters
- **Symptom:** ManagedClusterAddon stuck in "Progressing"
- **Detection:** `oc get pods -n <mch-ns> -l app=addon-manager`

### ManifestWork rejected on spoke
- **Impact:** Addon not deployed on that cluster
- **Scope:** Single cluster
- **Symptom:** ManagedClusterAddon shows Available=False
- **Detection:** Check ManifestWork status conditions

### Addon health check failure
- **Impact:** Addon marked unhealthy, may trigger remediation
- **Scope:** Single addon on single cluster
- **Symptom:** ManagedClusterAddon condition Degraded=True
- **Detection:** `oc get managedclusteraddon -n {cluster} {addon} -o yaml`

### Pre-delete task failure
- **Impact:** Addon removal hangs, ManagedClusterAddon stuck in Terminating
- **Scope:** Single addon on single cluster
- **Symptom:** ManagedClusterAddon won't delete, finalizer present
- **Detection:** Check addon pod logs for pre-delete task errors

---

## Cross-Subsystem Dependencies

| Dependency | Why |
|---|---|
| Infrastructure (klusterlet) | ManifestWork delivery requires spoke connectivity |
| work-agent | Applies ManifestWork payloads on spoke |
| MCH/MCE operators | Lifecycle management of addon operators |
| registration-operator | Manages hub-side registration for addon communication |

## What Depends on Addon Framework

| Consumer | Impact When Addon Framework Is Down |
|---|---|
| Search (search-collector) | No resource collection from new/changed spokes |
| GRC (governance-framework, config-policy) | No policy enforcement on new spokes |
| Observability (metrics-collector) | No metrics from new spokes |
| ALC (application-manager) | No app status from new spokes |
| RBAC (acm-roles) | No ACM roles deployed to new spokes |
| ALL addons | Upgrades stalled, health monitoring blind |
