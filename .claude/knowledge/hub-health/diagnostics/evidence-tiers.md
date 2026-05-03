# Evidence Tiers

How to weight evidence when diagnosing ACM hub issues. Stronger evidence should
carry more weight in determining root cause. Every conclusion should be backed
by at least 2 evidence sources, with at least one from Tier 1.

---

## Tier 1: Definitive Evidence

These signals directly indicate the problem. A single Tier 1 finding can be
the basis for a root cause conclusion (but still verify with a second source).

| Evidence Type | Example | What It Proves |
|---|---|---|
| Pod status OOMKilled | Exit code 137 in `oc describe pod` | Container exceeded memory limit |
| CrashLoopBackOff with error in logs | `nil pointer dereference` in `oc logs --previous` | Specific code bug causing crash |
| HTTP 5xx from backend service | 500/503 in console-api logs | Backend service is failing |
| Resource missing from cluster | `oc get <resource>` returns not found | Resource doesn't exist |
| CRD version removed | `oc get crd` shows missing version | CRD upgrade issue |
| MCH phase not Running | `oc get mch` shows Pending/Error | ACM platform unhealthy |
| ManagedCluster Available=False | `oc get managedclusters` | Spoke disconnected |
| Explicit error message in logs | "template-error", "failed to sync", "conflict" | Specific failure identified |
| S3 connection error in thanos-store | Bucket operation errors in logs | Storage misconfiguration |
| Webhook denial in events | "denied the request" in events | Admission controller blocking |

## Tier 2: Strong Evidence

These signals strongly suggest a cause but need confirmation. Combine 2+
Tier 2 findings or pair with 1 Tier 1 for a conclusion.

| Evidence Type | Example | What It Suggests |
|---|---|---|
| High restart count on pod | Restart count >10, recent restarts | Pod is unstable |
| Elevated memory/CPU usage | `oc adm top pod` near limits | Resource pressure |
| Stale lease timestamp | Lease not renewed recently | Connectivity issue |
| Multiple pods failing in same namespace | Several non-Running pods | Namespace-wide issue |
| Event correlation | BackOff events followed by OOMKilled | Crash-OOM cycle |
| Version mismatch | ACM version known to have this bug | Known issue match |
| Dependency chain alignment | Upstream dependency is degraded | Cascade failure |
| Pattern match to known issue | Symptoms match a known-issues.md entry | Likely known bug |
| Reconciliation frequency | Log entries every 10s for same resource | Hot-loop pattern |
| PVC status not Bound | PVC Pending, pod Pending | Storage provisioning issue |

## Tier 3: Supportive Evidence

These signals provide context but are not conclusive on their own. Use them
to strengthen or weaken other evidence, not as primary findings.

| Evidence Type | Example | What It Adds |
|---|---|---|
| Pod age | Pod recently restarted (minutes old) | Something happened recently |
| Timing correlation | Issue appeared after upgrade | Possible upgrade regression |
| Similar symptoms in related components | Two addons failing on same spoke | Pattern emerging |
| Resource counts | Unusually high ManifestWork count | Scale factor |
| Node resource utilization | Worker node at 78% memory | Background pressure |
| Cluster topology | Hub vs spoke, number of clusters | Scale context |
| ACM/OCP version info | Running 2.16.0 on OCP 4.21 | Version compatibility context |

---

## Evidence Combination Rules

### Minimum for a Root Cause Conclusion
- **1x Tier 1 + 1x Tier 2** (or higher)
- **2x Tier 1** (sufficient)
- **3x Tier 2** (sufficient if no Tier 1 available, but flag lower confidence)
- **Tier 3 alone is NEVER sufficient** for a conclusion

### Confidence Levels

| Evidence Combination | Confidence |
|---|---|
| 2+ Tier 1 | High (90%+) |
| 1 Tier 1 + 1+ Tier 2 | High (80-90%) |
| 3+ Tier 2 | Medium (70-85%) |
| 1 Tier 1 only | Medium (65-80%) |
| 1-2 Tier 2 only | Low (50-70%) -- investigate further |
| Tier 3 only | Insufficient -- do not conclude |

### Confidence Modifiers

| Factor | Adjustment |
|---|---|
| Known issue match (exact JIRA) | +10% |
| Version confirmed affected | +5% |
| Multiple independent evidence sources | +5% per additional source |
| Conflicting evidence present | -15% |
| No cluster access (limited diagnostics) | -15% |
| Operator log confirms exact error | +10% |
| Only pod status checked (no logs) | -10% |

---

## Rule-Out Matrix

Before concluding a root cause, explicitly rule out alternatives:

| If concluding... | Must rule out... |
|---|---|
| Infrastructure issue | Is it version-specific? (might be a product bug) |
| Product bug | Is the environment correctly configured? Are prerequisites met? |
| Component-specific failure | Is it actually a cascade from an upstream dependency? |
| Upgrade regression | Was it broken before the upgrade too? |
| Resource pressure (OOM/CPU) | Is the workload legitimately larger, or is there a leak? |
| Network/connectivity | Is the spoke actually down, or just the klusterlet? |
| Storage issue | Is the storage backend healthy, or is it a configuration problem? |

---

## Evidence Collection Checklist

For each diagnosed issue, collect and document:

1. **What was observed** (Tier 1/2/3 evidence)
2. **What commands were run** (reproducibility)
3. **What was ruled out** (alternatives considered)
4. **Version context** (ACM, MCE, OCP versions)
5. **Scale context** (number of clusters, policies, etc.)
6. **Timeline** (when did it start, recent changes)
