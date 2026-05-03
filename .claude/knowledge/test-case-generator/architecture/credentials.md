# Credentials Area Knowledge

## Overview

Credential management in ACM Console handles provider credentials used for cluster creation and infrastructure access. Credentials are stored as Kubernetes Secrets with provider-specific fields.

## Key Components

| Component | Role |
|-----------|------|
| Credentials Page | Lists all provider credentials with usage tracking |
| Add Credential Wizard | Multi-step form for creating provider-specific credentials |
| Provider Adapters | Convert wizard input to Secret YAML per provider type |

## CRDs / Resources

Credentials are stored as Kubernetes Secrets with the label `cluster.open-cluster-management.io/type=<provider>`:

| Provider Type | Secret Label Value | Purpose |
|---------------|-------------------|---------|
| AWS | `aws` | EC2/EKS cluster provisioning |
| Azure | `azr` | AKS/ARO cluster provisioning |
| GCP | `gcp` | GKE cluster provisioning |
| vSphere | `vmw` | vSphere cluster provisioning |
| Bare Metal | `bmc` | Bare metal provisioning |
| Red Hat OpenStack | `ost` | OpenStack cluster provisioning |
| Ansible Automation Platform | `ans` | Tower/AAP integration for upgrades |
| Red Hat Cloud | `rhocm` | RHOCM integration |

## Provider-Specific Required Fields

| Provider | Required Fields |
|----------|----------------|
| AWS | Access Key ID, Secret Access Key, Base DNS Domain |
| Azure | Client ID, Client Secret, Subscription ID, Tenant ID, Base DNS Domain |
| GCP | Service Account JSON Key, Project ID, Base DNS Domain |
| vSphere | vCenter URL, Username, Password, Datacenter, Cluster, Default Datastore |
| Bare Metal | libvirt URI, SSH Private Key, Pull Secret |
| Ansible | Ansible Tower URL, Token |

## Navigation Routes

| Route Key | Path | Page |
|-----------|------|------|
| `credentials` | `/multicloud/credentials` | Credentials list |
| `addCredentials` | `/multicloud/credentials/create` | Add credential wizard |
| `editCredentials` | `/multicloud/credentials/edit/:namespace/:name` | Edit credential |
| `viewCredentials` | `/multicloud/credentials/details/:namespace/:name` | View credential details |

## UI Flows

### Add Credential Wizard
1. **Select Provider Type** — AWS, Azure, GCP, vSphere, etc.
2. **Enter Connection Details** — Provider-specific fields (API keys, URLs)
3. **Enter Base DNS Domain** (for cloud providers)
4. **Enter Pull Secret** (optional, for cluster provisioning)
5. **Review and Create** — Creates Secret with provider labels

### Credential Validation
- Some providers support connection validation (AWS STS, Azure login)
- Validation may require external API access (VPN, firewall rules)
- Validation failure doesn't block creation (credential may still be valid for different region/endpoint)

## Setup Prerequisites

- cluster-admin access to the hub cluster
- For validation testing: network access to the provider API endpoints
- For usage testing: at least one cluster using the credential

## Translation Keys

| Key | English Text | Context |
|-----|-------------|---------|
| `Credentials` | "Credentials" | Navigation tab |
| `Add credential` | "Add credential" | Button |
| `Provider type` | "Provider type" | Wizard step label |
| `Base DNS domain` | "Base DNS domain" | Cloud credential field |
| `Connection` | "Connection" | Connection details section |
| `Pull secret` | "Pull secret" | Optional field for cluster provisioning |

## Secret Structure

Credentials are stored as Kubernetes Secrets with specific annotations:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: <credential-name>
  namespace: <credential-namespace>
  labels:
    cluster.open-cluster-management.io/type: <provider>
    cluster.open-cluster-management.io/credentials: ""
type: Opaque
data:
  # Provider-specific base64-encoded fields
```

## Testing Considerations

- Credentials contain secrets — **never display actual values** in test expected results
- Different provider types have different required fields and different wizard steps
- Credential validation requires external API access (may not work in isolated environments)
- Editing a credential doesn't affect running clusters using it (changes only apply to new operations)
- Credential namespace matters for cluster set binding and RBAC scoping
- Secret data is base64-encoded in Kubernetes — CLI verification must decode
- Test with both valid and invalid credentials to verify error handling
- Credential usage tracking shows which ClusterDeployments reference the credential
