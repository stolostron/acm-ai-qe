# Stage 1.5 cluster-diagnosis.json Schema and Health-Score Formula

Stage 1.5 (cluster diagnostic) writes `cluster-diagnosis.json` to the run directory. Stage 2
(failure classifier) reads it as Tier 1 evidence, and Stage 3 (`report.py`) renders its fields in
the Environment tab of the HTML report. The field names and the `environment_health_score` formula
below are the single source of truth for the skill — ported verbatim from the app agent
`apps/z-stream-analysis/.claude/agents/cluster-diagnostic.md` (Step 6.2). Keep them in sync with
that file, NOT with `acm-hub-health-check/references/diagnostic-output-schema.md`, whose penalty
values diverge (see the note at the end).

## `environment_health_score` (float 0.0–1.0)

Compute using this weighted penalty formula. Start at 1.0, subtract penalties:

| Category | Weight | Penalty |
|----------|--------|---------|
| Operator health | 30% | -0.30 if ANY critical operator has 0 replicas; -0.15 if under-replicated |
| Infrastructure guards | 20% | -0.10 per NetworkPolicy/ResourceQuota in ACM namespaces (cap 0.20) |
| Subsystem health | 30% | -0.06 per critical subsystem; -0.03 per degraded |
| Managed clusters | 10% | -0.10 if <50% ready; -0.05 if 50-99% ready |
| Image integrity | 10% | -0.10 if console image from non-standard registry |

Floor at 0.0. Round to 2 decimal places. Show the math in the completion summary.

**Test-artifact awareness:** NetworkPolicies and ResourceQuotas in ACM namespaces are almost always
test artifacts (no ownerReferences, created recently, not ACM-managed). Note in
`counter_signals.infrastructure_context_notes` whether each finding is a test artifact or a real
production issue. The score applies the penalty regardless (it reflects actual cluster state), but
the context helps Stage 2 weight the finding appropriately.

**Score bands → verdict:** `< 0.8` is DEGRADED/CRITICAL; `>= 0.8` is HEALTHY. In Stage 2 Phase A1,
a score `< 0.8` makes infrastructure a hypothesis but NOT an automatic classification — per-test
causal-link verification is still required (see `../../acm-failure-classifier/references/phase-d-validation.md`).

## Required cluster-diagnosis.json fields

Stage 2 routing and the HTML report depend on these fields. If any are missing, Stage 2 loses its
fast-path routing and the report's Environment tab renders blank. Compute all of them before writing
the file.

- **`cluster_connectivity`** (boolean) — `true` if `oc whoami` succeeded, `false` otherwise.
- **`environment_health_score`** (float 0.0–1.0) — the weighted score above.
- **`critical_issue_count`** (integer) — count of `infrastructure_issues` entries with severity `critical`.
- **`warning_issue_count`** (integer) — count of `infrastructure_issues` entries with severity `warning`.
- **`cluster_identity`** (object) — `api_url`, `ocp_version`, `acm_version`, `mce_version`,
  `mch_namespace`, `mch_phase`, `node_count`, `node_ready_count`, `managed_cluster_count`,
  `managed_cluster_ready_count`.
- **`operator_health`** (object keyed by deployment name) — each entry: `namespace`,
  `desired_replicas`, `available_replicas`, `status` (`OK | DEGRADED | CRITICAL`), `detail`
  (empty if OK), `critical` (bool, from `healthy-baseline.yaml`).
- **`subsystem_health`** (object keyed by subsystem name) — each entry: `status`
  (`healthy | degraded | critical`), **`health_depth`** (`pod_level | connectivity_verified |
  data_verified | full`), `health_depth_explanation`, **`unchecked_layers`** (array of layer numbers
  NOT verified, e.g. `[3, 4, 11]`), `root_cause` (only if not healthy), `evidence_tier` (`1` or `2`),
  `evidence_detail`, `affected_components`, `healthy_components`, `log_patterns_detected`,
  `traps_checked`, `traps_triggered`.
- **`image_integrity`** (object) — `console_image`, `expected_prefixes` (from `healthy-baseline.yaml`),
  `matches_expected` (bool), `flag` (`null` if it matches, else a description when the console image
  comes from a non-standard registry). A non-standard registry means `console_search` was checked
  against a TAMPERED console — Stage 2 must re-verify selectors via the acm-source MCP against the
  OFFICIAL source.
- **`console_plugins`** (array) — each: `name`, `service`, `namespace`.
- **`classification_guidance`** (object) — `pre_classified_infrastructure` (array of
  `{feature_areas, reason, confidence, evidence_tier, evidence, affected_tests_hint}`),
  `confirmed_healthy` (array of feature areas), `partial_impact` (array of
  `{feature_area, reason, confidence, scope}`), `diagnostic_traps_applied` (array of triggered trap names).
- **`counter_signals`** (object) — `potential_false_infrastructure` (array of
  `{signal, reason, recommendation}`) and `infrastructure_context_notes` (array of
  `{finding, note, scoring_impact}`). These guard against anchoring bias: a degraded cluster does
  NOT make every failure INFRASTRUCTURE.

### Schema shape

```json
{
  "cluster_diagnosis": {
    "version": "1.0.0",
    "timestamp": "<ISO-8601>",
    "overall_verdict": "<HEALTHY | DEGRADED | CRITICAL>",
    "cluster_connectivity": "<true | false>",
    "environment_health_score": "<float 0.0-1.0>",
    "critical_issue_count": "<integer>",
    "warning_issue_count": "<integer>",
    "cluster_identity": {
      "api_url": "<oc whoami --show-server>",
      "ocp_version": "<from clusterversion>",
      "acm_version": "<from MCH .status.currentVersion>",
      "mce_version": "<from MCE .status.currentVersion>",
      "mch_namespace": "<discovered>",
      "mch_phase": "<from MCH .status.phase>",
      "node_count": "<int>",
      "node_ready_count": "<int>",
      "managed_cluster_count": "<int>",
      "managed_cluster_ready_count": "<int>"
    },
    "operator_health": {
      "<deployment-name>": {
        "namespace": "<ns>",
        "desired_replicas": "<int>",
        "available_replicas": "<int>",
        "status": "<OK | DEGRADED | CRITICAL>",
        "detail": "<string, empty if OK>",
        "critical": "<true | false>"
      }
    },
    "subsystem_health": {
      "<SubsystemName>": {
        "status": "<healthy | degraded | critical>",
        "health_depth": "<pod_level | connectivity_verified | data_verified | full>",
        "health_depth_explanation": "<what was checked and what was NOT>",
        "unchecked_layers": ["<layer numbers not verified, e.g. 3, 4, 11>"],
        "root_cause": "<string, only if not healthy>",
        "evidence_tier": "<1 or 2>",
        "evidence_detail": "<what was found>",
        "affected_components": ["<unhealthy components>"],
        "healthy_components": ["<healthy components>"],
        "log_patterns_detected": ["<OOM, nil_pointer, etc.>"],
        "traps_checked": ["<trap names checked>"],
        "traps_triggered": ["<trap names that fired>"]
      }
    },
    "image_integrity": {
      "console_image": "<actual image string>",
      "expected_prefixes": ["<from healthy-baseline.yaml>"],
      "matches_expected": "<true | false>",
      "flag": "<null if matches, description if non-standard registry>"
    },
    "console_plugins": [
      {"name": "<plugin-name>", "service": "<backend-service>", "namespace": "<ns>"}
    ],
    "classification_guidance": {
      "pre_classified_infrastructure": [
        {"feature_areas": ["<list>"], "reason": "<root cause>", "confidence": "<0.80-0.95>",
         "evidence_tier": "<1 or 2>", "evidence": "<what was found>", "affected_tests_hint": "<scope>"}
      ],
      "confirmed_healthy": ["<healthy feature areas>"],
      "partial_impact": [
        {"feature_area": "<name>", "reason": "<why partial>", "confidence": "<0.80-0.85>", "scope": "<which tests>"}
      ],
      "diagnostic_traps_applied": ["<triggered trap names>"]
    },
    "counter_signals": {
      "potential_false_infrastructure": [
        {"signal": "<tests that may NOT be infrastructure>", "reason": "<why>", "recommendation": "<what Stage 2 should verify>"}
      ],
      "infrastructure_context_notes": [
        {"finding": "<infrastructure finding>", "note": "<real issue or test artifact>", "scoring_impact": "<how it affects the score>"}
      ]
    }
  }
}
```

The app agent's `cluster-diagnosis.json` carries additional optional diagnostic arrays for deeper
investigation (`operator_inventory`, `addon_health`, `webhook_status`, `component_log_excerpts`,
`component_restart_counts`, `managed_cluster_detail`, `ocp_operators_degraded`,
`console_plugin_status`, `infrastructure_issues`, `dependency_chains_verified`,
`baseline_comparison`, `self_healing_discoveries`). Populate them when the investigation surfaces
the data; the fields listed above are the ones Stage 2 routing and the HTML report require.

## Known out-of-scope discrepancy

`acm-hub-health-check/references/diagnostic-output-schema.md` documents a DIFFERENT health-score
formula (subsystem `-0.10`/`-0.05`, managed clusters `-0.05` per cluster capped at `-0.15`, no
infrastructure-guard `cap 0.20`, and no weight column). That divergence pre-dates this skill and is
OUT OF SCOPE here — do NOT "reconcile" it by editing the shared hub-health file. This reference
tracks the z-stream app agent (`cluster-diagnostic.md`) only.
