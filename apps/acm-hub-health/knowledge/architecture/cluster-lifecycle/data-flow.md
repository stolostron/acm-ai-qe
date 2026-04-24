# Cluster Lifecycle (CLC) -- Data Flow

## Overview of Flows

CLC has three primary data flows, each using different controllers and
namespaces. Unlike Search (single pipeline) or GRC (single propagation
path), CLC flows are independent and involve cross-namespace resource
creation.

---

## Flow 1: Cluster Provisioning (Hive)

```
User / Console UI
  |
  v  (creates in <cluster-ns>)
ClusterDeployment + InstallConfig + Cloud Credential Secret
  |
  v  (hive namespace)
hive-controllers watches ClusterDeployment
  |
  v  (creates in <cluster-ns>)
Install Pod (runs openshift-install)
  |
  v  (cloud provider API)
Infrastructure provisioned (VMs, networking, DNS, LB)
  |
  v  (cluster bootstraps)
OCP cluster boots, kubeadmin-password + kubeconfig Secrets created
  |
  v  (hub: open-cluster-management)
managedcluster-import-controller detects completed CD
  |
  v  (auto-import)
ManagedCluster CR created, klusterlet deployed to spoke
  |
  v
ManagedCluster becomes Available=True
```

### Step-by-Step

**Step 1: ClusterDeployment creation**

User creates ClusterDeployment (CD), InstallConfig, and cloud credential
Secret in the cluster's namespace (auto-created by Hive if missing).
Console's create wizard generates all three resources.

**Failure:** Invalid InstallConfig -> CD rejected by webhook. Missing
cloud credential Secret -> CD accepted but install pod fails. Webhook
validation broken -> CD with bad metadata accepted but can't deprovision
later (ACM-26271).

**Step 2: hive-controllers picks up CD**

hive-controllers (in `hive` namespace) watches ClusterDeployments across
all namespaces. Creates an install pod in the cluster's namespace.

**Failure:** hive-controllers down -> CD stays in Provisioning indefinitely.
No error on the CD itself -- just no progress. Check:
`oc get pods -n hive -l app=hive-controllers`

**Step 3: Install pod provisions infrastructure**

Install pod runs `openshift-install create cluster` using the InstallConfig
and cloud credentials. Creates cloud resources (VMs, networking, DNS).

**Failure:** Cloud API errors (quota, permissions, networking) -> install
pod fails. Install pod logs contain the specific cloud error. Install pod
stuck -> check `oc logs -n <cluster-ns> -l hive.openshift.io/install=true`.

**Step 4: Cluster boots and secrets generated**

OCP bootstrap completes. Hive writes `kubeconfig` and `kubeadmin-password`
Secrets to the cluster's namespace on the hub.

**Failure:** Bootstrap timeout -> install pod timeout after 30-45 min.
Check CD `.status.conditions` for `ProvisionFailed`.

**Step 5: Auto-import**

managedcluster-import-controller detects the completed CD (has kubeconfig),
creates ManagedCluster CR, generates klusterlet manifests, applies them
to the new cluster using the kubeconfig.

**Failure:** Import controller down -> cluster provisioned but not imported.
kubeconfig invalid or expired -> import fails. Check ManagedCluster
`.status.conditions` for `ManagedClusterJoined`.

**Step 6: Klusterlet registration**

Klusterlet on the new cluster registers with the hub via bootstrap
kubeconfig. Once registered, hub issues a signed certificate. Klusterlet
renews its lease periodically (heartbeat).

**Failure:** Network connectivity issues -> klusterlet can't reach hub
API. Certificate issues -> registration fails silently, ManagedCluster
stays in Unknown state.

### Layer-Annotated Provisioning Flow

Each provisioning step maps to a diagnostic layer. When provisioning
fails, identify which step failed and check that layer:

| Step | Layer | What Can Break |
|------|-------|---------------|
| Console resource creation | L8 (webhook) | hiveadmission webhook down (Trap 10) |
| HiveConfig check | L5 (configuration) | HiveConfig missing or misconfigured |
| ClusterImageSet resolution | L5 (configuration) | ClusterImageSet doesn't exist (disconnected env) |
| hive-controllers picks up CD | L9 (operator) | hive-controllers pod down |
| Credential validation | L6 (auth) | Cloud credentials expired or invalid |
| Install pod scheduling | L1 (compute) | Insufficient resources, node taints |
| Cloud API provisioning | External | Cloud quota, API errors, networking |
| OCP bootstrap | External | Bootstrap timeout, DNS resolution |
| Kubeconfig/secret creation | L4 (storage) | Namespace missing, secret write failure |
| Import controller handoff | L9 (operator) | managedcluster-import-controller down |
| Klusterlet registration | L6 (auth) + L3 (network) | Certificate issues, firewall |
| ManagedCluster Available | L10 (cross-cluster) | Lease renewal failure |

---

## Flow 2: Cluster Import

### Manual Import

```
User creates ManagedCluster CR on hub
  |
  v  (hub: open-cluster-management)
managedcluster-import-controller generates import manifests
  |
  v  (import-secret created in <cluster-ns>)
Bootstrap kubeconfig + klusterlet manifests generated
  |
  v  (user applies to spoke, or auto-import secret provided)
klusterlet deployed to spoke cluster
  |
  v
klusterlet registers with hub (bootstrap -> signed cert)
  |
  v
ManagedCluster becomes Available=True
  |
  v  (hub: open-cluster-management)
addon-manager deploys addons (search-collector, governance, etc.)
```

**Step 1: ManagedCluster creation**

User creates ManagedCluster CR. For manual import, user also downloads
import manifests from the console or retrieves from the import-secret.

**Step 2: Import manifest generation**

Import controller creates:
- `<cluster-name>-import` Secret containing klusterlet CRDs and deployment
- Bootstrap kubeconfig secret for initial registration

**Failure:** Import controller CrashLoopBackOff -> no import secrets
generated. Check `oc get pods -n open-cluster-management -l app=managedcluster-import-controller`.

**Step 3: Klusterlet deployment**

For manual: user applies the import manifests (`oc apply -f`).
For auto-import: import controller uses the provided kubeconfig
(via `auto-import-secret`) to apply manifests to the spoke.

**Failure:** Wrong kubeconfig -> `oc apply` fails. Spoke cluster
unreachable -> timeout. Auto-import secret with expired token -> import
fails silently.

**Step 4: Registration and addon deployment**

Same as provisioning flow steps 5-6. After ManagedCluster becomes
Available, addon-manager deploys configured addons.

### Auto-Import (HyperShift)

For hosted clusters, the import is fully automatic:

```
hypershift-addon-operator watches HostedCluster
  |
  v  (HostedCluster becomes Available)
Addon operator creates ManagedCluster CR
  |
  v
Generates external-managed-kubeconfig from HC's kubeconfig
  |
  v
managedcluster-import-controller imports using that kubeconfig
```

**Critical failure mode (ACM-20695):** When a HostedCluster is destroyed,
the ManagedCluster should also be deleted. But the auto-import logic
watches for HostedClusters and recreates the ManagedCluster if it
doesn't exist -- causing a loop where the MC is deleted then immediately
recreated. Fix: suppress auto-import when HC is being deleted.

---

## Flow 3: Cluster Upgrade (ClusterCurator)

```
User creates/updates ClusterCurator CR
  |
  v  (hub: open-cluster-management)
cluster-curator-controller creates upgrade Job in <cluster-ns>
  |
  v  (optional: AAP integration)
Pre-upgrade AnsibleJob executes via AAP
  |
  v
Curator Job patches ClusterVersion on spoke (via kubeconfig)
  |
  v
OCP performs rolling upgrade on spoke cluster
  |
  v  (curator monitors)
Curator polls ClusterVersion status until complete
  |
  v  (optional)
Post-upgrade AnsibleJob executes
  |
  v
ClusterCurator status updated to Completed
```

**Step 1: ClusterCurator CR**

User sets `spec.desiredCuration: upgrade` with target version. Curator
controller creates a Job pod in the cluster's namespace.

**Failure:** Curator controller down -> no Job created. Invalid version
string -> Job fails immediately.

**Step 2: Pre-upgrade hooks (optional)**

If configured, curator creates AnsibleJob CRD referencing an AAP
template. Waits for AnsibleJob completion before proceeding.

**Failure:** AAP not installed -> AnsibleJob CR stays pending. AAP
template not found -> Job fails.

**Step 3: Upgrade trigger**

Curator Job patches the spoke cluster's ClusterVersion resource to
trigger the OCP upgrade.

**Failure:** kubeconfig expired or invalid -> patch fails. Spoke cluster
unreachable -> timeout. OCP 4.21 introduced API changes that broke
curator's upgrade logic (ACM-30314).

**Step 4: Monitoring and completion**

Curator Job polls ClusterVersion status on the spoke. Checks for
upgrade progress (operators upgrading, nodes draining, etc.).

**Failure:** Upgrade hangs on spoke -> curator Job times out.
Node drain blocked -> upgrade stalls, curator waits indefinitely.

---

## Klusterlet Deployment and Lifecycle

### How Klusterlet Gets Deployed

1. managedcluster-import-controller generates klusterlet manifests
2. Manifests include:
   - klusterlet CRD
   - klusterlet CR (configures hub API URL, cluster name)
   - registration-operator deployment
   - bootstrap-hub-kubeconfig Secret (temporary, for initial registration)
3. registration-operator on spoke creates:
   - registration-agent (handles CSR flow, lease renewal)
   - work-agent (applies ManifestWork resources from hub)

### Bootstrap to Full Registration

```
Bootstrap kubeconfig (temporary, limited permissions)
  -> klusterlet registration-agent creates CSR on hub
  -> hub auto-approves CSR
  -> Signed certificate issued to klusterlet
  -> klusterlet switches from bootstrap to signed cert
  -> Periodic lease renewal (heartbeat)
```

The bootstrap kubeconfig is single-use. After signed cert is obtained,
bootstrap kubeconfig can be rotated or deleted without impact.

### Heartbeat and Availability

klusterlet renews its lease on the hub every ~60 seconds. If lease
renewal stops:
- **After lease duration expires:** ManagedCluster condition changes
  to `ManagedClusterConditionAvailable=Unknown`
- **Hub detects:** cluster-manager updates ManagedCluster status
- **Addons affected:** All addon status becomes Unknown for that cluster

---

## Certificate and Kubeconfig Management

### Standard Clusters

- **Bootstrap kubeconfig:** Generated by import-controller, used once for
  initial CSR. Limited RBAC (can only create CSRs).
- **Hub kubeconfig:** Signed certificate stored in klusterlet's namespace
  on the spoke. Auto-renewed before expiry.
- **Spoke kubeconfig:** Stored in the cluster's namespace on the hub.
  Used by curator, import-controller for spoke API access.

### Hosted Clusters (HyperShift)

- **external-managed-kubeconfig:** Generated from HostedCluster's admin
  kubeconfig. Used by import-controller to deploy klusterlet to the
  hosted cluster's data plane.
- **Mounted kubeconfig secrets:** Control plane pods mount kubeconfig
  secrets. When certificates rotate, the mounted secret file updates
  BUT the pod doesn't restart. Controllers keep using stale certs until
  pod restarts. This is the root cause of 8 certificate-related bugs
  (ACM-17667 and related).

### Certificate Rotation Failure Modes

```
Certificate rotates on spoke
  -> Secret updated on hub (by HC controller)
  -> Mounted volume in pod sees new file
  -> Controller's in-memory client still uses old cert (no file watch)
  -> API calls start failing with 401
  -> Controller enters error loop
  -> Only fixes on pod restart
```

**Affected controllers:** config-policy-controller, hypershift-addon,
observability-addon (any controller that reads kubeconfig from a mounted
secret rather than a Kubernetes client that auto-refreshes).

---

## Failure Modes at Each Hop

### hive-controllers down
- **Symptom:** ClusterDeployments stay in Provisioning, no install pods.
- **Scope:** All new provisioning blocked.
- **Detection:** `oc get pods -n hive -l app=hive-controllers`

### managedcluster-import-controller down
- **Symptom:** Completed CDs not auto-imported. Manual imports pending.
- **Scope:** All imports blocked.
- **Detection:** `oc get pods -n open-cluster-management -l app=managedcluster-import-controller`

### cluster-curator-controller down
- **Symptom:** Upgrades not starting. ClusterCurator CRs stay pending.
- **Scope:** All upgrades blocked.
- **Detection:** `oc get pods -n open-cluster-management -l app=cluster-curator`

### klusterlet disconnected on spoke
- **Symptom:** ManagedCluster shows Available=Unknown. All addons stale.
- **Scope:** Single cluster. Cascades to Search, GRC, Observability for
  that cluster.
- **Detection:** `oc get managedclusters` -- check AVAILABLE column.

### Cloud provider API failure
- **Symptom:** Install pods fail with cloud-specific errors.
- **Scope:** New provisioning for that provider.
- **Detection:** `oc logs -n <cluster-ns> -l hive.openshift.io/install=true`

### Webhook denial on ClusterDeployment
- **Symptom:** CD creation rejected, or CD accepted but can't deprovision
  later due to missing metadata.
- **Scope:** Specific cluster operation.
- **Detection:** `oc get clusterdeployment <name> -n <ns> -o yaml` -- check
  conditions and events.
