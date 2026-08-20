---
type: architecture
subsystem: install
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - architecture/install/architecture.md
  - architecture/foundation/mce-architecture.md
  - versions/acm-2x-to-5x-changes.md
version_notes:
  - "OLM channels changed from release-2.x/stable-2.x to release-5.0/stable-5.0"
  - "CSV version format changed from v2.x.y to v5.0.0-xxx"
  - "MCH namespace default changed from open-cluster-management to ocm"
  - "MCH and MCE operators increased from 1 to 2 replicas (HA) in ACM 5.0"
---

# OLM Installation Chain -- Architecture

ACM is installed through two sequential OLM chains. The first installs the ACM
(MCH) operator; the second, triggered automatically by the MCH operator, installs
the MCE operator. Understanding this two-chain model is critical for diagnosing
install failures, version mismatches, and component health issues.

---

## OLM Primer

OLM (Operator Lifecycle Manager) is a built-in OCP component that manages
operator installation. It watches `Subscription` objects and handles catalog
resolution, CRD registration, CSV creation, and operator pod deployment. OLM
itself is always running -- it ships with OpenShift.

Key OLM pods in `openshift-operator-lifecycle-manager`:

| Pod | Role |
|-----|------|
| `catalog-operator` | Resolves Subscriptions against CatalogSources |
| `olm-operator` | Executes InstallPlans, creates CSVs and Deployments |
| `packageserver` (x2) | Serves package metadata to the OCP console |

---

## Chain 1: ACM Operator Installation

The user creates three resources to start the ACM install. Everything else is
automatic.

### User-Created Prerequisites

1. **Namespace `ocm`** -- the target namespace for all ACM hub resources.
2. **OperatorGroup `acm-operator-group`** -- scopes the operator to the `ocm`
   namespace. OLM refuses to install without this.
3. **Subscription `advanced-cluster-management`** -- the trigger. Tells OLM to
   install ACM from a specific catalog and channel. Channel is `release-5.0` in ACM 5.0 (previously `release-2.16` in ACM 2.x).

### OLM Execution Flow

```
Subscription (user creates)
  → OLM reads, queries CatalogSource via gRPC
    → CatalogSource (registry of operator bundles, openshift-marketplace)
      → OLM resolves operator bundle at requested channel
        → InstallPlan (execution plan: what CSVs and CRDs to install)
          → [Manual approval if installPlanApproval: Manual]
            → CRD: multiclusterhubs.operator.open-cluster-management.io
            → CSV: advanced-cluster-management.v5.0.0-xxx (e.g., v5.0.0-193; previously v2.16.x in ACM 2.x)
              → Deployment: multiclusterhub-operator (2 replicas)
```

### Key Resources

| Resource | Name | Namespace | Created By |
|----------|------|-----------|------------|
| Subscription | `advanced-cluster-management` | `ocm` | User |
| CatalogSource | `acm-dev-catalog` | `openshift-marketplace` | Admin (pre-existing) |
| InstallPlan | `install-<hash>` | `ocm` | OLM |
| CRD | `multiclusterhubs.operator.open-cluster-management.io` | cluster-scoped | OLM |
| CSV | `advanced-cluster-management.v5.0.0-xxx` | `ocm` | OLM |
| Deployment | `multiclusterhub-operator` | `ocm` | OLM (from CSV) |

### CatalogSource

A CatalogSource is the registry of available operator versions. OLM's
catalog-operator queries it via gRPC on port 50051 to resolve what to install.
The Subscription references it by name (`source: acm-dev-catalog`).

### InstallPlan and Approval

The InstallPlan is OLM's execution plan listing exactly which CSVs, CRDs, and
bundles to install. With `installPlanApproval: Manual`, it stays pending until
a human sets `spec.approved: true`. Once approved, OLM registers the CRD and
creates the CSV.

### CSV to Deployment

The CSV's `spec.install.spec.deployments` section lists exactly one deployment:
`multiclusterhub-operator`. OLM reads this and creates the Deployment in `ocm`.
This is how the operator pod comes into existence -- the CSV is the bridge
between OLM metadata and the actual running operator.

---

## MCH Operator Reconciliation

The `multiclusterhub-operator` Deployment runs 2 replicas for HA with leader
election. It watches for a `MultiClusterHub` CR and reconciles 14 components.

### MultiClusterHub CR

The MCH CR is the second user-created object (after the Subscription). It
is the master switch for all of ACM. Each of the 14 components can be
individually enabled or disabled via `spec.overrides.components`.

The 14 components:

| Component | Namespace | Description |
|-----------|-----------|-------------|
| `app-lifecycle` | `ocm` | Application deployment via Subscriptions and Channels |
| `cluster-backup` | `open-cluster-management-backup` | Backup/restore of hub resources via Velero |
| `cluster-lifecycle` | `ocm` | Addon coordination and cluster integrations |
| `cnv-mtv-integrations` | `ocm` | CNV and MTV console integration |
| `console` | `ocm` | ACM web UI (ConsolePlugin) |
| `fine-grained-rbac` | `ocm` | Multicluster role assignment controller |
| `grc` | `ocm` | Governance, risk, and compliance (policy engine) |
| `insights` | `ocm` | Red Hat Insights integration |
| `multicluster-engine` | `multicluster-engine` | **Triggers Chain 2** -- the platform layer |
| `multicluster-observability` | `ocm` | Metrics collection and Grafana dashboards |
| `search` | `ocm` | Cross-cluster resource search (GraphQL + PostgreSQL) |
| `siteconfig` | `ocm` | Zero Touch Provisioning for telco/edge |
| `submariner-addon` | `ocm` | Cross-cluster networking |
| `volsync` | `ocm` | Asynchronous PVC replication |

---

## Chain 2: MCE Operator Installation

The `multicluster-engine` component is unique among the 14. Unlike the others
(which deploy directly into `ocm`), it triggers an entire second OLM chain.
This separation allows MCE to be installed standalone without ACM.

### What MCH Creates for MCE

The MCH operator creates four resources to bootstrap the MCE OLM chain:

1. **Namespace `multicluster-engine`**
2. **OperatorGroup `default`** (targets `multicluster-engine` namespace)
3. **Subscription `multicluster-engine`** (channel: `stable-5.0`, source: `mce-dev-catalog`; previously `stable-2.11` in ACM 2.x)
4. **MultiClusterEngine CR** (created after MCE operator is running)

### MCE OLM Execution Flow

```
MCH operator creates Subscription in multicluster-engine namespace
  → OLM reads, queries mce-dev-catalog CatalogSource via gRPC
    → InstallPlan (MCE)
      → CRD: multiclusterengines.multicluster.openshift.io (cluster-scoped)
      → CSV: multicluster-engine.v5.0.0-xxx
        → Deployment: multicluster-engine-operator (2 replicas)
          → MCH operator then creates MultiClusterEngine CR
            → MCE operator reconciles 21 deployments
              → cluster-manager creates 6 hub controllers
```

### Key Resources (MCE Chain)

| Resource | Name | Namespace | Created By |
|----------|------|-----------|------------|
| Namespace | `multicluster-engine` | -- | MCH operator |
| OperatorGroup | `default` | `multicluster-engine` | MCH operator |
| Subscription | `multicluster-engine` | `multicluster-engine` | MCH operator |
| CatalogSource | `mce-dev-catalog` | `openshift-marketplace` | Admin (pre-existing) |
| InstallPlan | `install-<hash>` | `multicluster-engine` | OLM |
| CRD | `multiclusterengines.multicluster.openshift.io` | cluster-scoped | OLM |
| CSV | `multicluster-engine.v5.0.0-xxx` | `multicluster-engine` | OLM |
| Deployment | `multicluster-engine-operator` | `multicluster-engine` | OLM (from CSV) |
| MultiClusterEngine CR | `multiclusterengine` | cluster-scoped | MCH operator |

### Version Numbering

In ACM 2.x, ACM and MCE used separate version numbers (e.g., ACM 2.16 shipped
with MCE 2.11). In ACM 5.0 the two are aligned at 5.0 (ACM v5.0.0-193, MCE
v5.0.0-204 -- same major, independent build suffixes). The MCH operator pins
the MCE version it installs.

---

## Full Installation Hierarchy

```
OLM (built-in platform controller)
  └─ Subscription: advanced-cluster-management
       └─ CatalogSource → InstallPlan → CSV
            └─ Deployment: multiclusterhub-operator (2 replicas, ocm)
                 └─ Watches: MultiClusterHub CR
                      ├─ 13 components deployed directly in ocm namespace
                      └─ multicluster-engine component triggers Chain 2:
                           └─ Namespace + OperatorGroup + Subscription (MCE)
                                └─ OLM: CatalogSource → InstallPlan → CSV
                                     └─ Deployment: multicluster-engine-operator (2 replicas)
                                          └─ Watches: MultiClusterEngine CR
                                               ├─ 21 deployments in multicluster-engine ns
                                               └─ cluster-manager deployment
                                                    └─ ClusterManager CR
                                                         └─ 6 hub controllers in
                                                            open-cluster-management-hub ns
```

---

## Diagnostic Commands

```bash
# Chain 1: ACM OLM resources
oc get subscription -n ocm
oc get installplan -n ocm
oc get csv -n ocm
oc get multiclusterhub -n ocm

# Chain 2: MCE OLM resources
oc get subscription -n multicluster-engine
oc get installplan -n multicluster-engine
oc get csv -n multicluster-engine
oc get multiclusterengine

# Operator health
oc get pods -n ocm -l name=multiclusterhub-operator
oc get pods -n multicluster-engine -l name=multicluster-engine-operator

# CatalogSource health
oc get catalogsource -n openshift-marketplace
```
