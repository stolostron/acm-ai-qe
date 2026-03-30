# Infrastructure Architecture (Failure Analysis Context)

Infrastructure-level components that affect all ACM features: nodes, etcd,
cluster operators, networking, and resource management.

---

## OCP Foundation

| Component | What it does | Impact if unhealthy |
|-----------|-------------|---------------------|
| etcd | Cluster state store | ALL operations fail |
| kube-apiserver | API request processing | ALL operations fail |
| OCP ClusterOperators (34) | Platform services | Specific features degrade |
| Ingress | Route/service exposure | Console inaccessible |
| service-ca | TLS certificate management | TLS failures across services |

## Node Health

Node issues affect pod scheduling and resource availability:
- **NotReady**: Node can't run workloads, pods get evicted
- **MemoryPressure**: Nodes under memory stress, OOM kills possible
- **DiskPressure**: Disk space exhaustion, pods may fail to start
- **CPU throttled**: Pods run but extremely slowly

For failure classification:
- Multiple nodes NotReady = INFRASTRUCTURE (broad impact)
- Single node pressure = INFRASTRUCTURE (specific pods affected)
- All nodes healthy but pods failing = look at pod-level issues

## Resource Quotas

ResourceQuotas limit namespace resource consumption. If a quota is set on
the ocm namespace with limits below current usage:
- Existing pods continue running
- Any pod that crashes can't restart (quota exceeded)
- Creates slow-motion cascading failure as pods naturally restart

This is a realistic production scenario (cluster admin applies quotas
without exempting system namespaces).

## NetworkPolicies

NetworkPolicies control pod-to-pod communication. A policy that blocks
ingress to a critical pod (like search-postgres) causes:
- Both pods show Running (healthy individually)
- Communication fails with connection timeout
- Very hard to diagnose (no error messages, no pod crashes)

## Webhook Infrastructure

Validating webhooks intercept API requests. Issues:
- Webhook service down: ALL requests to that resource type fail with 500
- CA bundle expired: TLS validation fails, webhook unreachable
- failurePolicy=Fail: requests blocked (safe but disruptive)
- failurePolicy=Ignore: requests pass without validation (unsafe)

## TLS Certificate Infrastructure

OCP service-CA operator manages internal TLS certificates:
- Generates certs for services with `service.beta.openshift.io/serving-cert-secret-name` annotation
- Rotates on ~2 year schedule
- Does NOT auto-repair manual corruption
- MCH operator does NOT reconcile cert content

If a cert is manually corrupted:
- The affected service fails TLS handshakes
- Pod may CrashLoopBackOff or run with TLS errors
- Persists until next scheduled rotation or manual fix
