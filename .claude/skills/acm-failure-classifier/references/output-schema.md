# Output Schema: analysis-results.json

## Critical Field Names

These must be EXACT -- the report generator rejects the file if wrong:
- `per_test_analysis` (NOT `failed_tests`)
- `summary.by_classification` (NOT `classification_breakdown`)
- `investigation_phases_completed` (required array)

## Required Top-Level Sections

```json
{
  "analysis_metadata": {
    "version": "4.0",
    "timestamp": "<ISO-8601>",
    "run_directory": "<path>",
    "jenkins_url": "<url>",
    "total_failures_analyzed": "<int>"
  },
  "investigation_phases_completed": ["A", "B", "C", "D", "E"],
  "mcp_queries_executed": {
    "acm_ui": "<count>",
    "jira": "<count>",
    "polarion": "<count>",
    "neo4j": "<count>"
  },
  "cross_test_correlations": [...],
  "cascading_failure_analysis": {...},
  "per_test_analysis": [...],
  "cluster_investigation_summary": {...},
  "feature_context_summary": {...},
  "summary": {
    "total_analyzed": "<int>",
    "by_classification": {
      "PRODUCT_BUG": "<int>",
      "AUTOMATION_BUG": "<int>",
      "INFRASTRUCTURE": "<int>",
      "NO_BUG": "<int>",
      "MIXED": "<int>",
      "FLAKY": "<int>",
      "UNKNOWN": "<int>"
    }
  },
  "jira_correlation": {...},
  "action_items": [...]
}
```

## Per-Test Analysis Fields (required)

Each entry in `per_test_analysis[]`:

```json
{
  "test_name": "<full test name>",
  "classification": "<PRODUCT_BUG|AUTOMATION_BUG|INFRASTRUCTURE|NO_BUG|MIXED|FLAKY|UNKNOWN>",
  "confidence": "<float 0.0-1.0>",
  "root_cause_layer": "<int 1-12>",
  "root_cause_layer_name": "<string>",
  "root_cause": "<description>",
  "cause_owner": "<product|automation|infrastructure|external>",
  "evidence_sources": [
    {"source": "<tool/method>", "finding": "<what was found>", "tier": "<1|2|3>"}
  ],
  "ruled_out_alternatives": [
    {"classification": "<type>", "reason": "<why not>"}
  ],
  "reasoning": {
    "summary": "<1-2 sentences>",
    "evidence": ["<evidence point 1>", "<evidence point 2>"],
    "conclusion": "<final assessment>"
  },
  "investigation_steps_taken": ["<step 1>", "<step 2>"],
  "recommended_fix": {
    "action": "<what to do>",
    "owner": "<who>",
    "steps": ["<step 1>"]
  },
  "jira_correlation": {
    "existing_bugs": ["<JIRA keys>"],
    "related_stories": ["<JIRA keys>"]
  },
  "feature_context": {
    "area": "<feature area>",
    "component": "<backend component>"
  },
  "backend_cross_check": {
    "performed": "<true|false>",
    "result": "<healthy|unhealthy|n/a>"
  }
}
```
