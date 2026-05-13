# Cluster Introspection Sources

When the static knowledge doesn't cover a component, reverse-engineer its
dependencies from these 8 metadata sources (all read-only `oc` commands).

## 1. Owner References

Trace `.metadata.ownerReferences` up the chain:
```
oc get deploy <name> -n <ns> -o jsonpath='{.metadata.ownerReferences}'
```
Follows: Pod -> Deployment -> CSV or CR -> Operator. MCE deployments
have rich owner refs; ACM's own deployments often lack them.

## 2. OLM Labels

The `olm.owner` label maps resources to their CSV:
```
oc get clusterroles -l olm.owner=<csv-name> -o json
```
The RBAC rules reveal which API groups the operator accesses -- these
are its implicit dependencies (e.g., `monitoring.coreos.com` means it
depends on the monitoring stack).

## 3. CSV Metadata

What the operator provides:
```
oc get csv <name> -n <ns> -o jsonpath='{.spec.customresourcedefinitions.owned}'
oc get csv <name> -n <ns> -o jsonpath='{.spec.install.spec.deployments[*].name}'
```
Maps an operator to its owned CRDs and managed deployments. Note: the
`.spec.customresourcedefinitions.required` field is almost always empty
-- operators do not formally declare OLM dependencies.

## 4. Kubernetes Labels

Logical grouping:
```
oc get deploy <name> -n <ns> -o jsonpath='{.metadata.labels}'
```
Look for `app.kubernetes.io/managed-by`, `part-of`, `component`. Not
all operators set these, but when present they're authoritative.

## 5. Environment Variables and Volumes

Runtime service dependencies:
```
oc get deploy <name> -n <ns> -o jsonpath='{.spec.template.spec.containers[*].env}'
```
Scan for: `*.svc` references (service deps), `DB_HOST`/`*_HOST` (database),
`*_URL`/`*_ENDPOINT` (API deps), `OPERAND_IMAGE_*` (managed operands),
secret/configmap references (configuration deps). This is the richest
source for runtime dependencies.

The `OPERAND_IMAGE_*` pattern is particularly important: the MCH operator
CSV contains 40+ such env vars, each specifying the exact image digest
for a managed component (console, search, governance, etc.). If the CSV
is corrupted, these values propagate bad image references to all managed
deployments, causing ImagePullBackOff across multiple subsystems (see
diagnostic-layers.md Layer 5 cross-layer note).

## 6. Webhooks

Cross-operator validation dependencies:
```
oc get validatingwebhookconfigurations -o json
oc get mutatingwebhookconfigurations -o json
```
Check `.webhooks[*].clientConfig.service` -- this reveals which service
handles validation for which resources. Webhook services that are down
can block resource creation across operators.

## 7. ConsolePlugins

UI integration topology:
```
oc get consoleplugins -o json
```
Shows which operators extend the console UI and what backend services
they proxy to. Critical for "why is this console tab broken" questions.

## 8. APIServices

API aggregation dependencies:
```
oc get apiservices -o json
```
Non-local APIServices (those with `.spec.service`) identify operators
that extend the Kubernetes API. If the serving pod is down, the entire
API group becomes unavailable.

## Combining Introspection Results

Build a dependency map from the 8 sources:
- **Owner refs + OLM labels + CSV** identify the operator hierarchy
- **Env vars** identify runtime service dependencies
- **Webhooks + APIServices** identify cross-operator API dependencies
- **ConsolePlugins** identify UI integration dependencies
- Cross-reference with MCH `.status.components` and MCE `.status.components`
  to determine whether the component is ACM-managed or independent

The cluster-derived map is always available (just `oc` commands). The
knowledge graph supplements it with broader ACM-specific relationships.
The acm-source MCP provides implementation details for each dependency.
