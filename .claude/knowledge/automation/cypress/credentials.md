# Credentials Area Knowledge Base

Domain knowledge for writing Credentials automation tests.

---

## Test Area

| Directory | Specs |
|-----------|-------|
| `cypress/tests/credentials/` | 4 specs (add, edit, delete, validate credentials) |

---

## Key Files

| File | Purpose |
|------|---------|
| `cypress/views/credentials/credentials.js` | Page object with selectors and methods |
| `cypress/views/actions/credential.js` | Credential state setup/teardown actions |
| `cypress/apis/credentials.js` | Credential API wrappers |

---

## Navigation

- Path: `constants.credentialsPath` = `/multicloud/credentials`

---

## Credential Types

| Provider | Secret Type |
|----------|-------------|
| AWS | `aws` |
| Azure | `azr` |
| GCP | `gcp` |
| VMware vSphere | `vmw` |
| Red Hat OpenStack | `ost` |
| Bare Metal | `bmc` |
| Ansible Automation | `ans` |
| Red Hat Cloud | `rhocm` |

---

## Tags

`@CLC`, `@e2e`

---

## Key Patterns

- Credentials are K8s Secrets in a specific namespace
- Credential creation requires provider-specific fields (access key, secret key, etc.)
- Tests use fixtures for test data (`cypress/fixtures/`)
