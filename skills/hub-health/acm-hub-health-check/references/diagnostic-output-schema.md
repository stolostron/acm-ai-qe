# cluster-diagnosis.json Output Schema

When used by the acm-z-stream-analyzer pipeline (Stage 1.5), produce `cluster-diagnosis.json` with these structured fields. Stage 2 (acm-failure-classifier) reads this as its primary cluster context.

## Required Top-Level Fields

```json
{
  "cluster_diagnosis": {
    "overall_verdict": "HEALTHY|DEGRADED|CRITICAL",
    "environment_health_score": 0.0-1.0,
    "critical_issue_count": 0,
    "warning_issue_count": 0,
    "cluster_connectivity": true,

    "cluster_identity": {
      "api_url": "...", "mch_namespace": "...", "mch_version": "...",
      "mce_version": "...", "ocp_version": "...", "node_count": 0,
      "managed_cluster_count": 0
    },

    "operator_health": {
      "mch_status": "Available|Degraded|Progressing",
      "mch_replicas": "1/1",
      "mce_status": "...",
      "mce_replicas": "1/1",
      "degraded_operators": []
    },

    "infrastructure_issues": [
      {
        "severity": "critical|warning",
        "category": "...",
        "component": "...",
        "namespace": "...",
        "impact": "...",
        "trap_ref": "Trap N or null",
        "attribution_rule": "When to attribute test failures to this issue",
        "NOT_affected": "What this issue does NOT explain"
      }
    ],

    "subsystem_health": {
      "<subsystem>": {
        "status": "healthy|degraded|critical",
        "root_cause": "...",
        "evidence_detail": "...",
        "traps_triggered": [],
        "health_depth": "pod_level|connectivity_verified|data_verified|full",
        "unchecked_layers": []
      }
    },

    "managed_cluster_detail": [
      {"name": "...", "available": true, "joined": true, "conditions": [], "addon_health": {}}
    ],

    "console_plugins": ["..."],

    "image_integrity": {
      "console_image": "...",
      "matches_expected": true,
      "expected_prefixes": ["registry.redhat.io/", "quay.io/stolostron/"]
    },

    "baseline_comparison": {
      "missing_deployments": [],
      "under_replicated": [],
      "unexpected_resources": []
    },

    "component_log_excerpts": {
      "<pod>": {"error_lines": ["..."], "log_pattern": "OOM|nil_pointer|..."}
    },

    "component_restart_counts": {
      "<pod>": 0
    },

    "classification_guidance": {
      "pre_classified_infrastructure": [
        {"feature_area": "...", "issue": "...", "evidence_tier": 1}
      ],
      "confirmed_healthy": ["..."],
      "affected_feature_areas": ["..."]
    },

    "counter_signals": {
      "potential_false_infrastructure": [
        "Test X has console_search.found=false -- should be AUTOMATION_BUG regardless"
      ],
      "infrastructure_context_notes": ["..."]
    },

    "diagnostic_traps_applied": {
      "trap_1": "triggered|not_triggered|n_a",
      "trap_1b": "...",
      "...": "..."
    },

    "self_healing_discoveries": []
  }
}
```

## Environment Health Score Formula

Weighted penalty system with 5 categories:

| Category | Penalty | Condition |
|---|---|---|
| Operator health | -0.30 | MCH or MCE at 0 replicas |
| Operator health | -0.15 | MCH or MCE degraded |
| Infrastructure guards | -0.10 | NetworkPolicy or ResourceQuota present in ACM namespace |
| Infrastructure guards | -0.05 | Service with 0 endpoints |
| Subsystem health | -0.10 | Per critical subsystem |
| Subsystem health | -0.05 | Per warning subsystem |
| Managed clusters | -0.05 | Per unavailable managed cluster (max -0.15) |
| Image integrity | -0.10 | Console image from non-standard registry |

Start at 1.0, apply penalties. Clamp to [0.0, 1.0].

## Health Depth Per Subsystem

Each subsystem in `subsystem_health` MUST include `health_depth`:

- `pod_level` -- only checked pod status (Running/not Running)
- `connectivity_verified` -- checked pod + verified service endpoints respond
- `data_verified` -- checked pod + endpoints + verified data integrity (e.g., psql row count)
- `full` -- all layers checked including data flow and UI tab presence

Also include `unchecked_layers` listing which diagnostic layers were NOT verified for this subsystem. Stage 2 uses this to decide whether to run additional investigation.
