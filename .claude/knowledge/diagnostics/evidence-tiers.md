# Evidence Tiers

How to weight evidence when making diagnostic conclusions. Stronger evidence
should carry more weight. Every conclusion should be backed by at least 2
evidence sources, with at least one from Tier 1.

This model serves two purposes:
- **Hub health diagnosis** (acm-hub-health): determining root cause
  confidence when diagnosing cluster issues
- **Failure classification** (z-stream-analysis): determining classification
  confidence when assigning PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE,
  or NO_BUG

---

## Tier 1: Definitive / Direct Evidence

These signals directly indicate the problem. A single Tier 1 finding can be
the basis for a conclusion (but still verify with a second source).

### Cluster Health Evidence (Hub Health)

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

### Classification Evidence (Z-Stream)

| Evidence Type | Source | What It Tells You |
|---|---|---|
| `console_search.found` | Step 7 (console search in extracted_context) | Does the selector exist in the product? true/false |
| `automation_last_modified` | Step 7 (temporal_summary from data-collector) | When was the test file last changed? |
| `recent_selector_changes` | Step 7 (recent_selector_changes in extracted_context) | Was the selector renamed in recent product commits? |
| `subsystem_health` | Stage 1.5 (cluster-diagnosis.json) | Is the subsystem healthy, degraded, or critical? |
| `oracle.dependency_health` | Step 5 (environment oracle) | Are feature dependencies healthy? |
| `is_cascading_hook_failure` | Step 3 (JUnit parser) | Is this an after-all hook from a prior failure? |
| `blank_page_detected` | Step 2 (console log) | Did the page fail to load entirely? |
| `image_integrity.matches_expected` | Stage 1.5 (cluster-diagnosis.json) | Is the console running an official image? false = tampered/non-standard |
| `layer_discrepancy` | Layer investigation (Phase B) | Two layers disagree about resource state. Lower layer verified healthy, higher layer shows defect. Proves product code at higher layer is wrong. |

## Tier 2: Strong / Contextual Evidence

These signals strongly suggest a cause but need confirmation. Combine 2+
Tier 2 findings or pair with 1 Tier 1 for a conclusion.

### Cluster Health Evidence (Hub Health)

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

### Classification Evidence (Z-Stream)

| Evidence Type | Source | What It Tells You |
|---|---|---|
| ACM Source MCP selector verification | MCP tool call | Does the selector exist in a specific ACM version? |
| JIRA bug search | MCP tool call | Is there a known bug for this component? |
| KG dependency analysis | Neo4j query | What components depend on the failing one? |
| `environment_health_score` | Stage 1.5 (cluster-diagnosis.json) | How healthy is the cluster overall? (0.0-1.0) |
| `feature_area` | Step 8 | Which ACM area does this test belong to? |
| Console log 500 errors | Step 2 | Were there HTTP 500 errors during the test? |

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

- **1x Tier 1 + 1x Tier 2** (or higher) -- sufficient
- **2x Tier 1** -- sufficient
- **3x Tier 2** -- sufficient if no Tier 1 available, but flag lower confidence
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

### Classification Weight System (Z-Stream)

For z-stream classification, Tier 1 evidence has weight 1.0 and Tier 2
evidence has weight 0.5. A classification needs **minimum 1.8 combined
weight** for high confidence:

**Example 1: AUTOMATION_BUG via Path A**
- console_search.found = false (Tier 1: 1.0)
- automation_last_modified = 2022 (Tier 1: 1.0)
- Total: 2.0 >= 1.8 -> high confidence (0.90)

**Example 2: INFRASTRUCTURE via PR-7**
- oracle.dependency_health.cnv_operator.phase = Failed (Tier 1: 1.0)
- environment_health_score = 0.65 (Tier 2: 0.5)
- managed_clusters NotReady (Tier 2: 0.5)
- Total: 2.0 >= 1.8 -> high confidence (0.90)

**Example 3: PRODUCT_BUG via layer discrepancy (strong)**
- layer_discrepancy: L7 says permission granted, L12 shows button disabled (Tier 1: 1.0)
- console_search.found = true, selector exists (Tier 1: 1.0)
- Total: 2.0 >= 1.8 -> high confidence (0.85-0.90)

**Example 4: PRODUCT_BUG via Path B2 without layer discrepancy (weaker)**
- console_search.found = true (Tier 1: 1.0)
- JIRA bug found for component (Tier 2: 0.5)
- Total: 1.5 < 1.8 -> moderate confidence (0.65-0.75)

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

## Counter-Bias Validation

After concluding a diagnosis or classification, check for counter-evidence:

### Hub Health
- If concluding infrastructure issue: Is it version-specific? (might be a product bug)
- If concluding product bug: Is the environment correctly configured? Are prerequisites met?
- If concluding component-specific failure: Is it actually a cascade from an upstream dependency?
- If concluding upgrade regression: Was it broken before the upgrade too?
- If concluding resource pressure (OOM/CPU): Is the workload legitimately larger, or is there a leak?
- If concluding network/connectivity: Is the spoke actually down, or just the klusterlet?
- If concluding storage issue: Is the storage backend healthy, or is it a configuration problem?

### Failure Classification
- If classified as AUTOMATION_BUG: Could a backend failure cause this element to not render?
- If classified as INFRASTRUCTURE: Is this actually a product code issue masquerading as infra?
- If classified as PRODUCT_BUG: Is this an intentional product change that automation didn't follow?

---

## Evidence Collection Checklist

For each diagnosed issue, collect and document:

1. **What was observed** (Tier 1/2/3 evidence with tier label)
2. **What commands were run** (reproducibility)
3. **What was ruled out** (alternatives considered)
4. **Version context** (ACM, MCE, OCP versions)
5. **Scale context** (number of clusters, policies, etc.)
6. **Timeline** (when did it start, recent changes)
