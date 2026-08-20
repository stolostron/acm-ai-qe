---
type: versions
acm_version: "5.0"
last_verified: 2026-08-10
related:
  - architecture/install/olm-install-chain.md
  - architecture/install/architecture.md
  - architecture/acm-platform.md
  - versions/acm-2x-to-5x-changes.md
---

# ACM Version Matrix

Version compatibility reference for ACM, MCE, OCP, CNV, and MTV.
Data sourced from Red Hat support matrices, live cluster verification, and
official documentation.

---

## ACM-to-MCE Version Alignment

ACM and MCE maintain strict version alignment. The MCH operator pins the MCE
version it installs. Mismatched versions cause installation failures.

| ACM Version | MCE Version | CSV Name Pattern | OLM Channel (ACM) | OLM Channel (MCE) |
|-------------|-------------|------------------|--------------------|--------------------|
| 2.13 | 2.8 | `advanced-cluster-management.v2.13.x` | `release-2.13` | `stable-2.8` |
| 2.14 | 2.9 | `advanced-cluster-management.v2.14.x` | `release-2.14` | `stable-2.9` |
| 2.15 | 2.10 | `advanced-cluster-management.v2.15.x` | `release-2.15` | `stable-2.10` |
| 2.16 | 2.11 | `advanced-cluster-management.v2.16.x` | `release-2.16` | `stable-2.11` |
| 5.0 | 5.0 | `advanced-cluster-management.v5.0.0-xxx` | `release-5.0` | `stable-5.0` |

Source: [Red Hat Solutions - RHACM/MCE alignment](https://access.redhat.com/solutions/7061435)

**Version numbering change:** ACM jumped from 2.16 to 5.0 (no 2.17 release).
The `2.17` references found in some documentation and CatalogSource channels
were from the development branch before the rebrand. CSV version format also
changed from `v2.x.y` to `v5.0.0-nnn` build-number format.

---

## OCP Version Requirements

Each ACM version supports the current OCP release plus two previous versions,
and the immediate next OCP version when released. Even-numbered OCP releases
(4.16, 4.18, 4.20, 4.22) are EUS (Extended Update Support).

| ACM Version | OCP Minimum | OCP Maximum (at release) | EUS Versions Supported |
|-------------|-------------|--------------------------|------------------------|
| 2.13 | 4.16 | 4.19 | 4.16, 4.18 |
| 2.14 | 4.17 | 4.20 | 4.18, 4.20 |
| 2.15 | 4.18 | 4.21 | 4.18, 4.20 |
| 2.16 | 4.19 | 4.21 | 4.20 |
| 5.0 | 4.20 | 4.22+ | 4.20, 4.22 |

Source: Red Hat ACM support matrices per version ([2.13](https://access.redhat.com/articles/7099672), [2.14](https://access.redhat.com/articles/7120842), [2.15](https://access.redhat.com/articles/7133095), [2.16](https://access.redhat.com/articles/7136928))

**Verified on live cluster:** ACM 5.0.0-193 running on OCP 4.22.8.

---

## CNV/MTV Compatibility

CNV (OpenShift Virtualization) and MTV (Migration Toolkit for Virtualization)
are OCP-level operators installed on spoke clusters. They are not directly
versioned against ACM -- compatibility depends on the OCP version on the spoke.

### CNV Feature Requirements

| CNV Version | Feature |
|-------------|---------|
| 4.14+ | Basic VM management (create, start, stop, delete) |
| 4.15+ | Live migration support, migration policies |
| 4.16+ | CCLM (cross-cluster live migration) support |
| 4.17+ | instancetype/preference API stable |
| 4.22+ | Current version with ACM 5.0 (verified: 4.22.2) |

### MTV Version Notes

MTV provides VM migration from external platforms (VMware, RHV, etc.) to OCP.

| MTV Version | Notes |
|-------------|-------|
| 2.6+ | Supported with ACM 2.13+ |
| 2.12.x | Current version with ACM 5.0 (verified: 2.12.4) |

### ACM Fleet Virtualization Hub Requirements

Fleet Virtualization features require BOTH:
1. **Hub-side:** MCH component `cnv-mtv-integrations` enabled (disabled by default)
2. **Spoke-side:** CNV operator installed (namespace: `openshift-cnv`)

The `kubevirt-plugin` ConsolePlugin on the hub provides the Fleet Virtualization
UI. Without it, VM-related navigation items are absent.

---

## MCH Namespace Changes

| ACM Version | Default MCH Namespace | Notes |
|-------------|----------------------|-------|
| 2.13 - 2.16 | `open-cluster-management` | Traditional namespace |
| 5.0 | `ocm` | Changed in ACM 5.0 |

The MCH namespace is configurable at install time. Always discover it with
`oc get mch -A` rather than assuming a fixed namespace. The change to `ocm`
as default in ACM 5.0 affects all diagnostic commands that reference the
MCH namespace.

---

## Key Infrastructure Versions (Live Cluster Reference)

Verified on hub-50 (ACM 5.0) cluster on 2026-08-10:

| Component | CSV | Version |
|-----------|-----|---------|
| ACM | `advanced-cluster-management.v5.0.0-193` | 5.0.0-193 |
| MCE | `multicluster-engine.v5.0.0-204` | 5.0.0-204 |
| CNV | `kubevirt-hyperconverged-operator.v4.22.2` | 4.22.2 |
| MTV | `mtv-operator.v2.12.4` | 2.12.4 |
| OCP | -- | 4.22.8 |
| Cluster Observability Operator | `cluster-observability-operator.v1.5.1` | 1.5.1 |
| OpenShift GitOps | `openshift-gitops-operator.v1.21.2` | 1.21.2 |
| Ansible Automation Platform | `aap-operator.v2.6.0-0.xxx` | 2.6.0 |
| Flux | `flux.v2.3.0` | 2.3.0 |

---

## Hosted Control Planes OCP Support

Hosted Control Planes (HCP) do NOT automatically support the next OCP version.
MCE must be upgraded to the next y-stream release for HCP to support newer OCP.

| MCE Version | HCP OCP Range |
|-------------|---------------|
| 2.8 (ACM 2.13) | 4.16 - 4.18 |
| 2.9 (ACM 2.14) | 4.17 - 4.19 |
| 2.10 (ACM 2.15) | 4.18 - 4.20 |
| 2.11 (ACM 2.16) | 4.19 - 4.21 |
| 5.0 (ACM 5.0) | 4.20 - 4.22 |

---

## Managed Cluster Kubernetes Support (Non-OCP)

MCE supports importing non-OCP Kubernetes clusters as managed clusters:

| Provider | Kubernetes Versions (MCE 2.11 / ACM 2.16) |
|----------|-------------------------------------------|
| Amazon EKS | 1.32 - 1.35 |
| Google GKE | 1.32 - 1.35 |
| Microsoft AKS | 1.32 - 1.35 |
| IBM Cloud Kubernetes Service | 1.32 - 1.34 |
| CNCF conformant clusters | 1.32 - 1.35 |

---

## Usage Notes

- **Support policy:** The most current ACM version plus two previous versions
  are supported. All z-stream releases within supported versions are covered.
- **Version discovery on cluster:**
  ```bash
  oc get csv -n <mch-ns> | grep advanced-cluster-management   # ACM version
  oc get csv -n multicluster-engine | grep multicluster-engine  # MCE version
  oc get clusterversion                                         # OCP version
  oc get csv -n openshift-cnv | grep kubevirt                   # CNV version
  oc get csv -n openshift-mtv | grep mtv                        # MTV version
  ```
- **MCH namespace discovery:** `oc get mch -A -o jsonpath='{.items[0].metadata.namespace}'`
