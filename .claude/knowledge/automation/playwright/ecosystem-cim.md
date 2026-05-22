# Ecosystem / CIM Area Knowledge Base

Domain knowledge for writing CIM (Central Infrastructure Management) and AI-assisted install tests.

---

## Test Area

| Directory | Specs |
|-----------|-------|
| `cypress/tests/ecosystem/centrallyManagedClusters/standalone/` | 7 specs (standalone cluster creation via CIM) |
| `cypress/tests/ecosystem/centrallyManagedClusters/hosted/` | 3 specs (hosted cluster creation via CIM) |
| `cypress/tests/ecosystem/centrallyManagedClusters/` | 1 spec (general CIM) |

---

## Key Files

| File | Purpose |
|------|---------|
| `cypress/views/clusters/centrallyManagedClusters.js` | CIM page object |
| `cypress/views/infrastructureEnv/infraEnv.js` | Infrastructure environment page object |

---

## Navigation

- Infrastructure environments: `constants.hostInventoryPath` = `/multicloud/infrastructure/environments`

---

## Tags

`@CLC`, `@e2e`

---

## Key Patterns

- CIM uses InfraEnv and BareMetalHost CRDs
- AI-assisted install flow: create InfraEnv -> discover hosts -> create cluster
- Tests typically require bare metal infrastructure or simulated BMC
