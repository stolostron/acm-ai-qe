# Output Schema: analysis-results.json

Stage 2 (AI analysis) writes `analysis-results.json`; Stage 3 (`report.py`) reads it
to render the report. Field names below are EXACT — they mirror
`apps/z-stream-analysis/src/schemas/analysis_results_schema.json` and the fields
`report.py` actually reads. A wrong or missing name renders **blank** in the report.

## Report-critical field names (must be exact)

`report.py` / its `SchemaValidationService` rejects the file if these are wrong:
- `per_test_analysis` (array) — NOT `failed_tests`. Must be a list.
- `summary` (object) — must be a dict.
- `summary.by_classification` (object) — NOT `classification_breakdown`.

The JSON schema additionally requires `investigation_phases_completed` (array) at the
top level. `report.py`'s runtime validator does NOT enforce it, but the schema and the
analysis contract do — always emit it (`["A","B","C","D","E"]` for a full run, `[]` for
an empty/ABORTED short-circuit).

## Classification enum (7 values)

`per_test_analysis[].classification` and the keys of `summary.by_classification` use
exactly these 7 values:
`PRODUCT_BUG`, `AUTOMATION_BUG`, `INFRASTRUCTURE`, `NO_BUG`, `MIXED`, `FLAKY`, `UNKNOWN`.

`REQUIRES_INVESTIGATION` is **not** a per-test value. It is valid ONLY on
`summary.overall_classification` (that enum adds it; `report.py:235` defaults to it when
the overall classification is absent).

## Required Top-Level Sections

```json
{
  "analysis_metadata": {
    "jenkins_url": "<url>",
    "analyzed_at": "<ISO-8601>",
    "analyzer": "analysis-agent-v4.0",
    "analyzer_version": "4.0.0",
    "investigation_framework": "5-phase-systematic",
    "build_result": "<SUCCESS|UNSTABLE|FAILURE|ABORTED|NOT_BUILT>",
    "branch": "<git branch>",
    "run_directory": "<path>"
  },
  "investigation_phases_completed": ["A", "B", "C", "D", "E"],
  "mcp_queries_executed": [
    {"tool": "mcp__acm-source__search_code", "query": "search_code('selector', 'acm')", "success": true, "result_summary": "Found in 2 files"},
    {"tool": "mcp__jira__search_issues", "query": "project=ACM AND type=Bug", "success": true, "result_summary": "3 results"}
  ],
  "cross_test_correlations": {
    "shared_selectors": {"#create-btn": ["test1", "test2"]},
    "shared_components": {"search-api": ["test3", "test4"]},
    "pattern_type": "single_component_failure",
    "root_cause_affects_count": 2
  },
  "cascading_failure_analysis": {
    "analysis_performed": true,
    "root_cause_component": "search-api",
    "root_cause_subsystem": "Search",
    "dependent_components": ["search-collector", "search-indexer"],
    "tests_affected_by_cascade": ["test_search_results", "test_search_filter"],
    "knowledge_graph_query": "MATCH (c:RHACMComponent)-[:DEPENDS_ON]->(common) ... component_count >= 2"
  },
  "per_test_analysis": [...],
  "cluster_investigation_summary": {...},
  "feature_context_summary": {...},
  "summary": {
    "total_tests": 217,
    "passed_count": 122,
    "failed_count": 95,
    "total_failures": 95,
    "pass_rate": 56.2,
    "by_classification": {
      "PRODUCT_BUG": 0,
      "AUTOMATION_BUG": 0,
      "INFRASTRUCTURE": 7,
      "NO_BUG": 0,
      "MIXED": 0,
      "FLAKY": 0,
      "UNKNOWN": 0
    },
    "overall_classification": "INFRASTRUCTURE",
    "overall_confidence": 0.82
  },
  "jira_correlation": {
    "search_performed": true,
    "queries_executed": 3,
    "related_issues_found": ["ACM-12345"],
    "known_issue_matches": []
  },
  "action_items": [...]
}
```

### `analysis_metadata` (use schema field names, not `version`/`timestamp`)
- `analyzer_version` — e.g. `"4.0.0"`. Use this exact key (the legacy `version` key is not read).
- `analyzed_at` — ISO-8601. Use this exact key (the legacy `timestamp` key is not read).
- `build_result` — enum `SUCCESS | UNSTABLE | FAILURE | ABORTED | NOT_BUILT`. `report.py:315-319`
  reads it (falling back to `raw_data.jenkins.build_result`) to render **Build Result** and to
  decide the "Build Aborted" branch.
- Failure counts do NOT live here — they live in `summary` (`total_failures`, `failed_count`).

### `summary` (use schema field names)
`report.py` reads `total_tests` (`:253,255`), `pass_rate` (`:258`),
`overall_classification` (`:235`), and `overall_confidence` (`:236`).
- `total_tests`, `passed_count`, `failed_count`, `total_failures` — integers ≥ 0.
- `pass_rate` — number 0–100 (percent).
- `overall_classification` — one of the 7 values, or `REQUIRES_INVESTIGATION`.
- `overall_confidence` — number 0.0–1.0.
- `by_classification` — object holding the 7 classification counts (see enum above).
- Counts come from `total_tests` / `passed_count` / `failed_count` / `total_failures`;
  there is no separate "analyzed" total.
- Optional (see schema): `cascading_hook_failures`, `blank_page_failures`,
  `data_assertion_failures`, `feature_area_health`, `priority_order`.

### `cascading_failure_analysis` (Phase C2 component-dependency cascade)

Written by Phase C2 when a component-dependency cascade is detected
(`analysis_results_schema.json:220-250`). Fields:
- `analysis_performed` (bool) — whether cascade analysis ran.
- `root_cause_component` (string) — the upstream component all the failures depend on.
- `root_cause_subsystem` (string) — its subsystem (e.g. `Search`, `CLC`).
- `dependent_components` (array of strings) — components that failed as downstream symptoms.
- `tests_affected_by_cascade` (array of strings) — tests collapsed into the single root-cause bug.
- `knowledge_graph_query` (string) — the neo4j-rhacm Cypher query used (or the
  `baselines/dependency-chains.yaml` lookup when the KG is unavailable).

When a cascade is found, the dependents are symptoms — not separate bugs — and collapse to a
SINGLE PRODUCT_BUG for `root_cause_component`. See
`phase-c-correlation.md` for the detection method and the KG-unavailable fallback.

## Empty / ABORTED short-circuit (minimal artifact)

When the build was `ABORTED` (or there are zero failed tests), Stage 2 does not run a full
analysis. For an **ABORTED** build, write this minimal artifact and let `report.py` render a
"Build Aborted" section:

```json
{
  "analysis_metadata": {"build_result": "ABORTED"},
  "per_test_analysis": [],
  "summary": {"by_classification": {}},
  "investigation_phases_completed": [],
  "pipeline_failure": {
    "root_cause": "<why the build aborted, if known>",
    "recommendation": "<what to do next>"
  }
}
```

- It satisfies `report.py`'s validator (`per_test_analysis` list, `summary` dict,
  `summary.by_classification` dict) and the schema's top-level `required`
  (`per_test_analysis`, `summary`, `investigation_phases_completed`).
- `pipeline_failure` (object, optional, top-level) — `report.py:321` reads
  `pipeline_failure.root_cause` and `.recommendation` for the "Build Aborted" section. The
  top-level schema is `additionalProperties: true`, so this extra key validates. Omit it if
  the cause is unknown (`report.py` falls back to a default root-cause line).
- **Only `build_result == "ABORTED"` renders "Build Aborted".** An empty `per_test_analysis`
  with any other `build_result` makes `report.py` raise (`report.py:341`). For a zero-failure
  or `NOT_BUILT` build, do not write this empty artifact — skip Stage 2 output and let
  `report.py` render from `core-data.json`.

## Per-Test Analysis Fields

Each entry in `per_test_analysis[]`. Schema-required: `test_name`, `classification`,
`confidence`, `evidence_sources`.

```json
{
  "test_name": "<full test name>",
  "test_file": "<path to test file>",
  "class_name": "<test class or suite>",
  "feature_area": "<GRC|Search|CLC|Observability|Virtualization|Application|Console|Infrastructure|RBAC|...>",
  "classification": "<PRODUCT_BUG|AUTOMATION_BUG|INFRASTRUCTURE|NO_BUG|MIXED|FLAKY|UNKNOWN>",
  "classification_path": "<A|B1|B2>",
  "confidence": "<float 0.0-1.0>",
  "failure_mode_category": "<render_failure|element_missing|data_incorrect|timeout_general|assertion_logic|server_error|unknown>",
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
  "root_cause": "<description>",
  "root_cause_layer": "<int 1-12>",
  "root_cause_layer_name": "<layer name — see schema enum>",
  "investigation_steps_taken": ["<Layer N: ... -> HEALTHY/verdict>"],
  "cause_owner": "<free-form; e.g. product operator | test code | external/manual | platform | cascading | environment>",
  "verification_status": "<verified_in_group|split_from_group|individually_investigated>",
  "recommended_fix": {
    "action": "<what to do>",
    "owner": "<who>",
    "steps": ["<step 1>"]
  },
  "jira_correlation": {
    "search_performed": "<true|false>",
    "related_issues": ["<JIRA keys>"],
    "match_confidence": "<high|medium|low|none>"
  },
  "owner": "<free-form team; e.g. GRC Squad | CI / Infrastructure Platform Team>",
  "priority": "<CRITICAL|HIGH|MEDIUM|LOW>"
}
```

### Per-test field notes
- `evidence_sources` — **minimum 2 entries** (schema `minItems: 2`). Each item requires
  `source` + `finding`; `tier` (1=definitive, 2=strong, 3=supportive) is recommended.
- `classification` — 7 values only (no `REQUIRES_INVESTIGATION`; see enum above).
- `classification_path` — `A` (selector mismatch), `B1` (timeout/infra), `B2` (JIRA
  investigation).
- `failure_mode_category` — used by Phase D causal-link verification. `data_incorrect` =
  page rendered but wrong data; `element_missing` = selector not found; `render_failure` =
  page didn't load.
- `root_cause_layer_name` — human-readable name matching `root_cause_layer` (1–12); the
  schema constrains it to a fixed enum of the 12 layer names.
- `verification_status` — how the test was verified during group investigation.
- `cause_owner` — **free-form string** (the schema defines NO enum;
  `analysis_results_schema.json:381-384`). Describes WHO caused the issue at the root-cause
  layer. App example vocabulary: `product operator`, `test code`, `external/manual`,
  `platform`, `cascading`, `environment`. Do NOT constrain it to the per-test `owner`
  VALID_OWNERS set — that governs a different field.
- `owner` — **free-form string**, the team responsible for the fix
  (`analysis_results_schema.json:435`). `SchemaValidationService` soft-checks it against a
  recommended VALID_OWNERS set at INFO level only — non-matching values are NOT rejected.
  The golden artifact populates it on every test.
