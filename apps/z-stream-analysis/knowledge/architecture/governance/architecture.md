# Governance (GRC) Architecture

Governance, Risk, and Compliance (GRC) enables policy-based management across
managed clusters. Policies are created on the hub and enforced on spokes.

---

## Components

| Component | Type | Namespace | Pod Label | Role |
|-----------|------|-----------|-----------|------|
| grc-policy-propagator | Hub deployment (2 replicas) | ocm | app=grc-policy-propagator | Distributes policies to managed clusters |
| grc-policy-addon-controller | Hub deployment (2 replicas) | ocm | app=grc-policy-addon-controller | Manages GRC addons on spoke clusters |
| config-policy-controller | Spoke addon | varies | app=config-policy-controller | Enforces configuration policies on spoke |
| governance-policy-framework | Spoke addon | varies | app=governance-policy-framework | Framework for policy enforcement on spoke |
| cert-policy-controller | Spoke addon | varies | app=cert-policy-controller | Certificate policy enforcement |
| iam-policy-controller | Spoke addon | varies | app=iam-policy-controller | IAM policy enforcement |

## Prerequisites

- `grc` component enabled in MCH (enabled by default)
- `governance-policy-framework` addon deployed to spoke clusters
- `config-policy-controller` addon deployed to spoke clusters
- TLS secret `propagator-webhook-server-cert` valid in ocm namespace

## Policy Types

- ConfigurationPolicy -- enforce Kubernetes resource configuration
- CertificatePolicy -- enforce certificate expiration/validity
- IamPolicy -- enforce RBAC constraints
- Custom policies via policy templates

## Console Integration

GRC pages live at `/multicloud/governance/policies`. The frontend displays
policy lists, compliance status, and policy details. Key selectors include
PatternFly table components for the policy list.

## Webhook

The GRC propagator registers a webhook using the TLS secret
`propagator-webhook-server-cert`. If this cert is corrupted:
- The propagator pod may CrashLoopBackOff or fail TLS handshakes
- Policy creation/modification fails
- Existing policies on spokes continue running but stop getting updates
