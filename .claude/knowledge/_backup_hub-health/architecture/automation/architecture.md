# Automation (ClusterCurator) -- Architecture

## What Automation Does

Integrates ACM with Ansible Automation Platform (AAP) for lifecycle hook
execution during cluster operations. The ClusterCurator CR orchestrates
pre/post hooks for install, upgrade, destroy, and scale operations on
managed clusters.

When a user configures an automation template (via console or CR), the
cluster-curator-controller creates Kubernetes Jobs that call AAP to
execute Ansible playbooks at each lifecycle stage. The controller monitors
Job completion and reports status via conditions on the ClusterCurator CR.

---

## Core CRDs

### ClusterCurator

- **Kind:** `ClusterCurator`
- **API Group:** `cluster.open-cluster-management.io/v1beta1`
- **Scope:** Namespaced (in managed cluster's namespace on hub)

**Spec fields:**
- `desiredCuration` (string) -- Operation type: `install`, `upgrade`,
  `destroy`, `scale`
- `install` / `upgrade` / `destroy` / `scale` (object) -- Per-operation
  configuration, each containing:
  - `prehook` (array) -- Ansible jobs to run before the operation
  - `posthook` (array) -- Ansible jobs to run after the operation
  - `towerAuthSecret` (string) -- Secret with AAP credentials
  - `jobMonitorTimeout` (integer) -- Minutes to wait for hook completion
  - `overrideJob` (object) -- Custom Job spec override
- `upgrade.desiredUpdate` (string) -- Target OCP version
- `upgrade.channel` (string) -- OCP update channel
- `upgrade.intermediateUpdate` (string) -- Intermediate version for EUS
- `upgrade.monitorTimeout` (integer) -- Minutes to monitor upgrade progress
- `upgrade.upgradeType` (string) -- Upgrade strategy
- `upgrade.nodePoolNames` (array) -- HyperShift node pool targeting
- `curatorJob` (string) -- Name of the Kubernetes Job created for this curation
- `providerCredentialPath` (string) -- Cloud/Ansible credential secret ref
- `inventory` (string) -- Ansible inventory values

**Status fields:**
- `conditions` (array) -- Conditions track each pipeline stage:
  - `type: clustercurator-job` -- Overall curation status
  - `type: prehook-ansiblejob` -- Pre-hook Ansible execution
  - `type: posthook-ansiblejob` -- Post-hook Ansible execution
  - `type: hive-provisioning-job` -- Hive cluster provisioning (install only)
  - `type: activate-and-monitor` -- Cluster activation (install only)
  - `type: monitor-import` -- Import monitoring (install only)
  - `type: monitor-upgrade` -- Upgrade monitoring (message contains
    percentage like "Working on 45%")
  - `reason: Job_has_finished` / `Job_failed` -- Result of each stage
  - `message` -- Contains Job name, curation type, version info

**Template vs Active ClusterCurator:**
A ClusterCurator is a **template** when its namespace does not match any
ManagedCluster name, `desiredCuration` is undefined, and `status` is empty.
Templates appear in the Console Automations page. Active curators live in
the managed cluster's namespace alongside the ManagedCluster resource.

### AnsibleJob (external CRD)

- **Kind:** `AnsibleJob`
- **API Group:** `tower.ansible.com/v1alpha1`
- **Owner:** AAP operator (must be installed separately)

Used by the curator Job to launch Ansible playbooks on AAP. The curator
creates AnsibleJob CRs that reference job templates in AAP.

---

## Key Components

### cluster-curator-controller

- **Deployment:** `cluster-curator-controller`
- **Namespace:** `multicluster-engine`
- **Pod label:** `name=cluster-curator-controller`
- **Expected replicas:** 2
- **Owner:** MultiClusterEngine CR (owned by MCE, not MCH)

Controller logic:
1. Watches ClusterCurator CRs across all namespaces
2. When `desiredCuration` is set, creates a Kubernetes Job using its own
   image (IMAGE_URI env var)
3. The Job executes the curation workflow: pre-hook → operation → post-hook
4. For hooks, the Job creates AnsibleJob CRs that trigger AAP execution
5. Monitors hook Job completion, updates ClusterCurator status conditions
6. For upgrades, patches the spoke cluster's ClusterVersion CR

**Health check:**
```bash
oc get deploy cluster-curator-controller -n multicluster-engine -o jsonpath='{.status.availableReplicas}'
# Expected: 2
```

### AAP Operator (external dependency)

- **Subscription:** In `openshift-operators` namespace
- **Not part of ACM** -- must be installed separately via OLM
- **Required for:** Template execution (not required for curator controller itself)

**Detection:**
```bash
oc get subscriptions.operators.coreos.com -A | grep -i aap
oc get csv -A | grep -i aap
```

### AAP Credential Secrets

- **Label:** `cluster.open-cluster-management.io/type: ans`
- **Required fields:** `stringData.host` (AAP URL), `stringData.token` (API token)
- **Copying mechanism:** When a curator template is linked to a cluster,
  the secret is copied to the cluster's namespace with
  `copiedFromSecretName`/`copiedFromNamespace` labels

**Detection:**
```bash
oc get secrets -A -l cluster.open-cluster-management.io/type=ans
```

---

## Console Integration

The ACM console provides UI for configuring automation templates:

- **Route:** Automation template configuration within cluster details
- **Backend proxy:** `ansibletower.ts` in the console backend proxies
  requests to the AAP API for template discovery
- **Template dropdown:** Populated via `GET /ansibletower/api/v2/job_templates/`
  (and `workflow_job_templates/`) proxied through the console backend
- **Status display:** ClusterCurator conditions shown in cluster details
- **SSE events:** ClusterCurator status changes delivered via `events.ts`

---

## Curation Workflow

```
User sets desiredCuration on ClusterCurator CR
  │
  ▼
cluster-curator-controller detects CR change
  │
  ▼
Creates Kubernetes Job (curator-job-xxxxx)
  │
  ├── Reads prehook config → Creates AnsibleJob CR → AAP executes playbook
  │       ↓
  │   Monitors AnsibleJob status (polls until complete or timeout)
  │       ↓
  ├── Executes operation (e.g., patches ClusterVersion for upgrade)
  │       ↓
  │   Monitors operation progress (monitorTimeout)
  │       ↓
  ├── Reads posthook config → Creates AnsibleJob CR → AAP executes playbook
  │       ↓
  │   Monitors AnsibleJob status
  │       ↓
  ▼
Updates ClusterCurator status conditions (Job_has_finished / Job_failed)
```

### Install Pipeline (sequential stages)
```
prehook-ansiblejob → hive-provisioning-job → activate-and-monitor
→ monitor-import → posthook-ansiblejob
```

### Upgrade Pipeline (sequential stages)
```
prehook-ansiblejob → monitor-upgrade → posthook-ansiblejob
```

The `monitor-upgrade` stage patches the spoke ClusterVersion with
`desiredUpdate` and monitors until complete or `monitorTimeout` exceeded.
The condition message contains upgrade percentage (e.g., "Working on 45%").

### Scale/Destroy Pipelines
`scale` and `destroy` curations are only available when the MCH
`ansibleIntegration` setting is `enabled`. Destroy supports pre-hooks
only (no post-hook after cluster deletion).

---

## Dependencies

| Dependency | Why | Impact When Missing |
|---|---|---|
| MCE operator | Owns the curator controller deployment | Controller not deployed |
| AAP operator | Provides AnsibleJob CRD and job execution | Hooks cannot execute; template list empty |
| Cluster lifecycle (Hive/Import) | Target must be a managed cluster | No kubeconfig available for spoke |
| Spoke kubeconfig | Curator Job patches spoke ClusterVersion | Upgrade operation fails |

## What Depends on Automation

| Consumer | Impact When Automation Is Down |
|---|---|
| Cluster upgrades via curator | Cannot use automated upgrade workflow |
| Console automation UI | Template selection empty, status stale |
| Pre/post lifecycle hooks | No Ansible execution at cluster lifecycle stages |

---

## Failure Modes

### cluster-curator-controller not running
- **Impact:** No new curations start; existing Jobs may complete but no
  new ones are created
- **Scope:** All clusters using ClusterCurator
- **Symptom:** ClusterCurator CRs with `desiredCuration` set but no Job
  created; no `curatorJob` in status
- **Detection:** `oc get deploy cluster-curator-controller -n multicluster-engine`

### AAP operator not installed
- **Impact:** AnsibleJob CRD doesn't exist; hook execution fails
- **Scope:** All clusters using automation hooks
- **Symptom:** Template dropdown empty, hook Jobs fail with CRD not found
- **Detection:** `oc get csv -A | grep aap`

### AAP unreachable from hub
- **Impact:** Hook execution timeout
- **Scope:** All automation hooks
- **Symptom:** AnsibleJob CR stuck, curator Job times out
- **Detection:** Check network connectivity from hub to AAP endpoint

### Curator Job timeout
- **Impact:** Curation marked as failed
- **Scope:** Single cluster's curation
- **Symptom:** ClusterCurator condition shows `Job_failed`,
  `jobMonitorTimeout` exceeded
- **Detection:** Check Job logs: `oc logs job/<curator-job-name> -n <cluster-ns>`

### Spoke kubeconfig expired (hosted mode)
- **Impact:** Upgrade operation fails at ClusterVersion patch step
- **Scope:** Single cluster upgrade
- **Symptom:** Curator Job logs show authentication errors
- **Cross-ref:** infrastructure/known-issues.md #2 (certificate rotation
  in hosted mode)
