# 8-Source Introspection Framework

When the knowledge base doesn't cover a component, reverse-engineer its role from the cluster.

## Sources (in order of reliability)

### 1. ownerReferences
Traces the controller hierarchy: Pod -> ReplicaSet -> Deployment -> CSV -> Operator.
```bash
oc get pod <name> -n <ns> -o jsonpath='{.metadata.ownerReferences[*].kind}'
oc get deploy <name> -n <ns> -o jsonpath='{.metadata.ownerReferences[*].name}'
```

### 2. OLM Labels
`olm.owner` maps managed resources back to their CSV.
```bash
oc get deploy <name> -n <ns> -o jsonpath='{.metadata.labels.olm\.owner}'
```

### 3. CSV Metadata
The ClusterServiceVersion defines owned CRDs and managed deployments.
```bash
oc get csv <csv-name> -n <ns> -o jsonpath='{.spec.customresourcedefinitions.owned[*].name}'
oc get csv <csv-name> -n <ns> -o jsonpath='{.spec.install.spec.deployments[*].name}'
```

### 4. Kubernetes Labels
Standard labels reveal organizational metadata.
Key labels: `app.kubernetes.io/managed-by`, `app.kubernetes.io/part-of`, `app.kubernetes.io/component`, `app.kubernetes.io/name`

### 5. Environment Variables
Runtime dependencies are revealed by service references in env vars.
Patterns: `*.svc`, `*_HOST`, `*_URL`, `*_ENDPOINT`, `*_ADDRESS`
```bash
oc get deploy <name> -n <ns> -o jsonpath='{.spec.template.spec.containers[*].env}' | python3 -m json.tool
```

### 6. Webhooks
Validating and mutating webhooks reveal what resources a component intercepts.
```bash
oc get validatingwebhookconfigurations -o json | jq '.items[] | select(.webhooks[].clientConfig.service.name == "<svc-name>")'
```

### 7. ConsolePlugins
UI integration reveals frontend dependencies and proxy targets.
```bash
oc get consoleplugins -o json | jq '.items[] | select(.spec.backend.service.name == "<svc-name>")'
```

### 8. APIServices
Non-local API aggregation reveals which APIs the component serves.
```bash
oc get apiservices -o json | jq '.items[] | select(.spec.service.name == "<svc-name>")'
```
