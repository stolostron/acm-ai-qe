# Specification: `context.md` for ai_systems_v2

**Purpose:** This report is a specification for Claude Code to create a `context.md` ubiquitous language document at the repo root. It contains everything discovered about the domain model, entities, terminology, relationships, and conventions. Claude Code should use this to produce a clean, concise `context.md` that all agents and skills can reference.

**Why:** Every Claude Code session in this repo re-discovers what terms mean ("what's a classification path?", "what's the oracle?", "what's Stage 1.5?"). A `context.md` at the repo root establishes shared vocabulary so agents use fewer tokens reasoning, produce more aligned code, and don't reinvent terminology.

**Source:** Synthesized from full repo investigation (May 2026) covering all 3 apps, 20+ skills, 133 Python files, MCP servers, knowledge DB, schemas, and documentation.

---

## Instructions for Claude Code

1. Create `/context.md` at the repo root
2. Follow the format and structure below exactly
3. Every definition must be grounded in what the code actually does (file paths referenced in this spec)
4. Do NOT pad with marketing language -- every word should earn its place
5. This document will be read by Claude agents at session start -- keep it scannable
6. Do **not** require a separate `adr/` directory for this repo; capture durable “why” in the **Repo design** paragraph of `context.md` plus `CLAUDE.md` / `docs/` as needed.
7. After creating `context.md`, add a pointer in `CLAUDE.md` under the directory map section:
   ```
   context.md          # Ubiquitous language glossary -- read this first
   ```

---

## 1. Bounded Context

This is a single bounded context: **ACM AI Quality Engineering**.

The repo is a monorepo of Claude Code-driven QE tools for Red Hat Advanced Cluster Management (ACM). It combines deterministic Python (data gathering, validation, reporting) with Claude Code agents (investigation, classification, synthesis) connected to external systems via MCP servers.

Three applications share a unified knowledge base and portable skills:
- **Z-Stream Analysis** -- classifies Jenkins pipeline test failures
- **ACM Hub Health** -- diagnoses hub cluster state
- **Test Case Generator** -- produces Polarion test cases from JIRA stories

---

## 2. Entity Glossary

### 2.1 System-Level Entities

#### App
One of the three primary applications in the `apps/` directory. Each has its own `CLAUDE.md`, agents, commands, knowledge subset, and run artifact structure. The fourth directory (`claude-test-generator`) is legacy/experimental and not part of the documented trio.

- **Z-Stream Analysis:** `apps/z-stream-analysis/`
- **ACM Hub Health:** `apps/acm-hub-health/`
- **Test Case Generator:** `apps/test-case-generator/`

#### Portable Skill
A Claude Code skill (under `.claude/skills/`) that encodes methodology and orchestration logic. Skills are tool-agnostic -- they work in Claude Code, Cursor, or any agent runtime that reads `SKILL.md`. There are 20 portable skills, organized as:
- **Shared/utility:** `acm-knowledge-base`, `acm-cluster-health`, `acm-jenkins-client`, `onboard`, `youtube-digest`, `grill-me`
- **Test-case workflow:** `acm-test-case-generator`, `acm-qe-code-analyzer`, `acm-test-case-writer`, `acm-test-case-reviewer`
- **Hub health:** `acm-hub-health-check`, `acm-cluster-remediation`, `acm-knowledge-learner`
- **Z-stream:** `acm-z-stream-analyzer`, `acm-failure-classifier`, `acm-cluster-investigator`, `acm-data-enricher`
- **Bug workflows:** `acm-bug-hunter`, `acm-bug-fix-verifier`
- **Environment:** `acm-environment-finder`

#### Subagent
A Claude Code `Agent` subtask launched by an orchestrator skill. Subagents run in isolation with artifacts written to disk to limit context bleed. Used heavily in test-case generator (parallel investigators) and z-stream (cluster-diagnostic, data-collector, analysis, investigation agents).

Defined in: `apps/*/. claude/agents/*.md`

#### Knowledge Base (Knowledge DB)
The unified markdown/YAML knowledge store at `.claude/knowledge/`. Organized by 14 ACM subsystems (addon-framework, application-lifecycle, automation, cluster-lifecycle, console, foundation, governance, infrastructure, install, networking, observability, rbac, search, virtualization). Contains:
- `architecture/` -- how subsystems work
- `data-flow/` -- how data moves through subsystems
- `baselines/` -- expected healthy state (YAML: pods, services, webhooks, certs)
- `diagnostics/` -- diagnostic traps and patterns
- `ui/` -- console area knowledge (routes, selectors, translations)
- `health/` -- known issues per subsystem
- `failures/` -- failure signature patterns for classification
- `conventions/` -- test and code conventions
- `examples/` -- reference examples
- `learned/` -- new discoveries not yet categorized

Apps may also have local `knowledge/` directories that mirror or extend the root knowledge.

#### Session Trace
JSONL telemetry written to `.claude/traces/` by `agent_trace.py` hooks in each app. Captures tool calls, MCP interactions, subagent launches, and metadata. Used for audit and debugging.

#### MCP Server
A Model Context Protocol server providing Claude agents with tools to interact with external systems. Configured in `.mcp.json` (gitignored, generated by `/onboard`). See Section 5 for the full inventory.

#### Run Directory
The output directory for a single execution of an app's pipeline. Contains all artifacts from gather through report. Location varies:
- Z-stream: `apps/z-stream-analysis/runs/<timestamp>_<descriptor>/`
- Test case generator: `runs/test-case-generator/<JIRA-ID>/<run-timestamp>/`

### 2.2 Z-Stream Analysis Entities

#### Classification
The root cause category assigned to a failed test. This is the single most important output of z-stream analysis.

| Value | Meaning |
|-------|---------|
| `PRODUCT_BUG` | Failure caused by a defect in the ACM product code |
| `AUTOMATION_BUG` | Failure caused by a defect in the test automation code |
| `INFRASTRUCTURE` | Failure caused by cluster/environment issues (not product or test code) |
| `FLAKY` | Test fails intermittently without a consistent root cause |
| `NO_BUG` | Test failure is expected or not a real failure |
| `MIXED` | Multiple root causes contribute (must specify `mixed_components[]`) |
| `UNKNOWN` | Insufficient evidence to classify (confidence < 0.50) |

Summary-level only (never on individual tests):
| `REQUIRES_INVESTIGATION` | Needs human review -- insufficient automated evidence |

Defined in: `apps/z-stream-analysis/src/schemas/analysis_results_schema.json` (lines 272-276) and `src/services/schema_validation_service.py` (lines 52-56).

#### Classification Path
The evidence trail that led to a classification decision.

| Path | Meaning |
|------|---------|
| `A` | Direct, high-confidence classification from primary evidence |
| `B1` | Classification via correlation with known patterns |
| `B2` | Classification via elimination/counterfactual reasoning |

Defined in: `analysis_results_schema.json` (lines 277-280).

#### Root Cause Layer
A 12-layer infrastructure model mapping where in the stack a failure originates. Layer 1 (Compute/Storage) through Layer 12 (UI/Frontend). Used to ground classifications in specific technology boundaries.

Defined in: `analysis_results_schema.json` (lines 352-374). Layer names: Compute/Storage, Networking/DNS, Certificates/TLS, etcd/API Server, Authentication/RBAC, Operators/Controllers, CRDs/Resources, Addons/Agents, Application Logic, Data/State, API/Integration, UI/Frontend.

#### Confidence
A float 0.0-1.0 indicating certainty of a classification. Below 0.50 forces `UNKNOWN`. Must be supported by at least two evidence sources.

#### Evidence Tier
The weight assigned to a piece of evidence:
- **Tier 1:** Direct observation (cluster state, logs, error messages) -- highest weight
- **Tier 2:** Correlation (patterns, JIRA matches, historical data)
- **Tier 3:** Inference (reasoning, heuristics)

#### Per-Test Analysis
One entry in `analysis-results.json` for each failed test. Contains: classification, classification_path, confidence, root_cause_layer, failure_mode_category, verification_status, priority, jira_correlation, assertion_analysis, evidence_sources, prerequisite_analysis, playbook_investigation, cluster_investigation_detail, feature_context.

Defined in: `analysis_results_schema.json` top-level `per_test_analysis[]`.

#### Investigation Phases (A-E)
The 5-phase systematic investigation framework used in Stage 2:
- **Phase A:** Ground and group failures (A1-A4 substeps)
- **Phase B:** 12-layer root cause investigation per group
- **Phase C:** Cross-test correlation and pattern detection
- **Phase D:** Validation, routing, and bias checks (PR-1 through PR-7, counterfactuals D-V5c/D-V5e, D4b/D5 bias checks)
- **Phase E:** JIRA correlation and action items

#### Pipeline Stages (Z-Stream)
The top-level execution flow:

| Stage | Actor | Input | Output |
|-------|-------|-------|--------|
| **Stage 0 -- Environment Oracle** | Python (inside gather) | Knowledge YAML + cluster state | Feature-aware dependency map |
| **Stage 1 -- Gather** | Python `gather.py` | Jenkins URL | `core-data.json`, `cluster.kubeconfig`, `repos/`, `pipeline.log.jsonl` |
| **Stage 1.5 -- Cluster Diagnostic** | Claude `cluster-diagnostic` agent | `core-data.json` + live cluster | `cluster-diagnosis.json` |
| **Post-1 Enrichment** | Claude `data-collector` agent | `core-data.json` | Enriched `core-data.json` (selectors, page objects, temporal analysis) |
| **Stage 2 -- AI Analysis** | Claude `analysis` agent (Phases A-E) | All gathered artifacts | `analysis-results.json` (must validate against schema) |
| **Stage 3 -- Report** | Python `report.py` | `analysis-results.json` | `Detailed-Analysis.md`, `analysis-report.html`, `per-test-breakdown.json`, `SUMMARY.txt` |

Stage 3 uses NO MCP servers -- it is purely deterministic transformation.

#### Core Data (`core-data.json`)
The primary gathered artifact from Stage 1. Contains Jenkins metadata, test reports, console logs, stack traces, repository clones info, and cluster context. This is the foundation that all subsequent stages build upon.

#### Environment Oracle
A feature-aware validation engine that runs inside `gather.py` (Stage 0). Cross-references feature playbooks, knowledge graph data, Polarion test expectations, and live cluster state to produce dependency health assessments. Feeds `INFRASTRUCTURE` vs `PRODUCT_BUG` routing in Stage 2.

Key entities: `DependencyTarget` (type: operator | addon | crd | component | managed_clusters), `DependencyHealth` (status: healthy | degraded | missing | unknown | unchecked), `OracleResult`.

Defined in: `src/services/environment_oracle_service.py` (lines 42-94).

#### Cluster Diagnosis (`cluster-diagnosis.json`)
Output of Stage 1.5. Contains health score, diagnostic trap matches, operator/subsystem status, and routing hints for Stage 2. Bridges infrastructure health observations into classification reasoning.

#### Feature Area
A named ACM functional domain used to group tests and route investigation. Examples: GRC (Governance Risk Compliance), Search, CLC (Cluster Lifecycle), ALC (Application Lifecycle), Console, Observability, RBAC, Virtualization/Fleet-Virt, MTV, Submariner.

Defined in: `src/services/feature_area_service.py` (line 50+, `FEATURE_AREAS` dict).

#### Feature Playbook
A YAML file under `knowledge/` (or `.claude/knowledge/`) that defines per-feature-area: prerequisites, known failure paths, suggested classifications, component mappings, and version-specific overlays. Base playbook: `base.yaml`. Version overlays: `acm-2.16.yaml`, `acm-2.17.yaml` (deep-merged by `id`).

Defined in: `apps/z-stream-analysis/src/data/feature_playbooks/` and `.claude/knowledge/`.

#### Diagnostic Trap
A known pattern where investigation can go wrong (misclassification, false confidence, misleading symptoms). 14 traps documented in `diagnostics/diagnostic-traps.md`. Used in hub health and z-stream to prevent common reasoning errors.

#### Two-Agent Framework
An investigation pattern where an **Investigation Agent** gathers evidence and an **Solution Agent** proposes fixes. Phases: `INVESTIGATION` → `SOLUTION` → `COMPLETE`.

Defined in: `src/services/two_agent_intelligence_framework.py` (lines 19-56).

#### Jenkins Intelligence
The extraction layer that parses Jenkins builds into structured data. Key entities:
- `JenkinsTestCaseFailure` (status: FAILED | REGRESSION | PASSED | SKIPPED; failure_type: timeout | element_not_found | etc.)
- `JenkinsTestReport` (counts, pass_rate, failed_tests[])
- `JenkinsMetadata` (build_result: SUCCESS | UNSTABLE | FAILURE | ABORTED | NOT_BUILT)
- `JenkinsIntelligence` (full extraction result)

Defined in: `src/services/jenkins_intelligence_service.py` (lines 51-121).

#### Stack Frame / Parsed Stack Trace
Parsed representation of JavaScript/TypeScript test stack traces. Each `StackFrame` flags whether it's from test code, framework code, or support code. `ParsedStackTrace` identifies root_cause_frame and test_file_frame.

Defined in: `src/services/stack_trace_parser.py` (lines 28-59).

#### Feedback
Post-analysis correction records. `ClassificationFeedback` captures human overrides of AI classifications. `RunFeedback` wraps all corrections for a run. Stored as JSON (not in a database).

Defined in: `src/services/feedback_service.py` (lines 21-41).

#### Manifest
A `manifest.json` in multi-file run directories that indexes all artifacts and their roles. Schema: `src/schemas/manifest_schema.json`.

### 2.3 Test Case Generator Entities

#### Pipeline Phases (Test Case Generator)
The portable skill uses a 9-phase model (Phase 0-8):

| Phase | Purpose | Artifact |
|-------|---------|----------|
| 0 | Input validation | -- |
| 1 | JIRA investigation | `phase1-jira.json` |
| 2 | Code/PR analysis | `phase2-code.json` |
| 3 | UI discovery | `phase3-ui.json` |
| 4 | Context synthesis | `synthesized-context.md` |
| 5 | Live validation (optional) | `phase5-live-validation.md` |
| 6 | Test case writing | `test-case.md` |
| 7 | Quality review | `phase7-review.md`, `review-results.json` |
| 8 | Report generation | HTML + validation JSON |

The app-level `CLAUDE.md` consolidates investigation into one parallel phase (gather.py → parallel investigators → synthesize → writer → reviewer → report.py). The skill-level 9-phase model is the authoritative sequencing.

#### Gather Output (`gather-output.json`)
Stage 1 output from `gather.py`. Pydantic model containing JIRA data, PR data, and gather options.

Entities: `GatherOutput`, `PRData` (state default "merged"), `GatherOptions`.

Defined in: `apps/test-case-generator/src/models/gather_output.py` (lines 9-44).

#### Analysis Result (TC-Gen)
Phase 4 audit metadata. Contains routes discovered, selectors found, Polarion coverage flags, complexity rating (low | medium | high), and self_review_verdict (PASS | FAIL). Explicitly noted as "not consumed by downstream pipeline stages" -- it's metadata for humans.

Defined in: `apps/test-case-generator/src/models/analysis_result.py` (lines 9-31).

#### Review Result
Phase 7 structural/convention review output. Contains:
- `Verdict`: PASS | FAIL
- `ValidationIssue`: severity (blocking | warning | suggestion), category (metadata | description | setup | steps | teardown | title)
- `ReviewResult`: verdict + boolean flags per section

Defined in: `apps/test-case-generator/src/models/review_result.py` (lines 9-42).

#### Console Area
An ACM console functional area that test cases target. Used for tagging, routing, and convention validation. Areas: governance, rbac, fleet-virt, cclm, mtv, clusters, search, applications, credentials, observability, etc.

Defined in: `apps/test-case-generator/src/services/convention_validator.py` (lines 9-36, `AREA_TAG_PATTERNS`).

### 2.4 Hub Health Entities

#### Health Verdict
The overall cluster health assessment: `HEALTHY` | `DEGRADED` | `CRITICAL` | `UNKNOWN`.

#### 6-Phase Methodology
The hub health diagnostic loop: Discover → Learn → Check → Pattern Match → Correlate → Output.

#### Health Finding
A single diagnostic observation. Severity: `CRITICAL` | `WARNING` | `INFO`.

#### Subsystem Health
Per-subsystem status assessment. Status: `OK` | `DEGRADED` | `CRITICAL`.

#### Cluster Identity
Hub identity metadata: API URL, version, platform.

#### Managed Cluster Health
Status of a spoke/managed cluster as observed from the hub.

All hub health entities defined in: `apps/z-stream-analysis/src/services/cluster_health_service.py` (lines 42-115). Note: this service is in the z-stream app but used cross-app.

#### Slash Commands (Hub Health)
Interactive entry points: `/sanity`, `/health-check`, `/deep`, `/investigate`, `/learn`. The `/learn` command persists discoveries to `knowledge/learned/` as markdown.

### 2.5 Bug Hunter Entities (Separate from Z-Stream)

#### 10-Dimension Model
An implementation audit framework distinct from the 12-layer infrastructure model. Evaluates spec fidelity through observable output across 10 dimensions. Used proactively (before bugs happen), unlike z-stream (after failures happen).

#### Dimension Classification
Per-dimension finding: `CLEAN` | `GAP` | `POTENTIAL_BUG` | `CONFIRMED_BUG`. Uses a "confidence confession" pattern where agents express uncertainty.

Defined in: `docs/acm-bug-hunter/IMPLEMENTATION-SPEC.md`.

---

## 3. Relationship Map

```
User
 └── invokes → Slash Command / Skill
      └── orchestrates → Subagent(s)
           ├── runs → Python Script (gather.py, report.py)
           │    └── produces → Run Artifacts (JSON, MD, HTML)
           ├── calls → MCP Server(s)
           │    └── queries → External System (Jenkins, JIRA, Polarion, cluster, GitHub)
           └── reads → Knowledge Base (.claude/knowledge/)
                └── contains → Feature Playbooks, Baselines, Failure Patterns

Z-Stream specific:
 core-data.json ← Stage 1 (gather.py)
      ↓
 cluster-diagnosis.json ← Stage 1.5 (cluster-diagnostic agent)
      ↓
 enriched core-data.json ← data-collector agent
      ↓
 analysis-results.json ← Stage 2 (analysis agent, Phases A-E)
      ↓
 Detailed-Analysis.md + HTML + SUMMARY.txt ← Stage 3 (report.py)

TC-Gen specific:
 gather-output.json ← gather.py
      ↓
 phase1-jira.json + phase2-code.json + phase3-ui.json ← parallel investigators
      ↓
 synthesized-context.md ← synthesis
      ↓
 test-case.md ← writer
      ↓
 review-results.json ← reviewer
      ↓
 HTML output ← report.py
```

---

## 4. Overloaded / Ambiguous Terms (Must Be Precise)

| Term | Ambiguity | Resolution |
|------|-----------|------------|
| **Stage** vs **Phase** | Z-stream uses "Stage" (0, 1, 1.5, 2, 3) for top-level pipeline and "Phase" (A-E) for investigation substeps. TC-gen uses "Phase" (0-8) for top-level pipeline. | Always qualify: "Z-stream Stage 2" or "TC-gen Phase 7" or "Investigation Phase D". Never use bare "stage" or "phase". |
| **Classification** | Z-stream: test failure root cause. Bug hunter: implementation dimension verdict. | Z-stream classification = `PRODUCT_BUG` / `AUTOMATION_BUG` / etc. Bug hunter classification = `CLEAN` / `GAP` / `POTENTIAL_BUG` / `CONFIRMED_BUG`. Always specify which system. |
| **Knowledge** | Could mean: the `.claude/knowledge/` directory, app-local `knowledge/`, feature playbooks, or the Neo4j knowledge graph. | Use "Knowledge DB" for `.claude/knowledge/`, "playbook" for feature YAML, "KG" or "knowledge graph" for Neo4j. |
| **Agent** | Could mean: Claude Code agent (`.claude/agents/*.md`), a portable skill, a subagent task, or the `AgentOrchestrator` Python class. | Use "Claude agent" for `.claude/agents/` definitions, "subagent" for `Agent` subtasks, "skill" for `.claude/skills/`, "orchestrator" for the Python adapter. |
| **Pipeline** | Z-stream top-level (Stage 0-3), z-stream 9-step gather, TC-gen Phase 0-8, hub health 6-phase, or Jenkins CI pipeline. | Always qualify: "z-stream pipeline", "gather pipeline", "TC-gen pipeline", "health pipeline", "Jenkins pipeline". |
| **Oracle** | The Environment Oracle (Python service) vs. general "oracle" usage. | Always capitalize: "the Oracle" or "Environment Oracle". |
| **Area** | Feature area (GRC, Search, etc.) vs. console area (governance, rbac, etc.). | These overlap but are defined in different places. Feature areas are z-stream groupings. Console areas are TC-gen convention tags. When they overlap (e.g., governance = GRC), prefer the context-specific term. |
| **Report** | `report.py` output, `Detailed-Analysis.md`, `analysis-report.html`, or `ClusterHealthReport` dataclass. | Use "z-stream report" (Stage 3 output), "health report" (hub health verdict), or reference the specific artifact name. |
| **Validation** | Schema validation (JSON), environment validation (cluster state), review validation (TC-gen quality), or artifact validation (`validate_artifact.py`). | Always qualify: "schema validation", "environment validation", "review validation", "artifact validation". |
| **Baseline** | YAML files in `baselines/` (expected healthy state) vs. a "baseline" in general conversation. | "Baseline YAML" or "healthy baseline" for the knowledge files. |

---

## 5. MCP Server Inventory

| Server | Tools (approx.) | Used By | Purpose |
|--------|-----------------|---------|---------|
| **acm-source** | 18 | All apps | GitHub-backed search of stolostron/console + kubevirt-plugin (selectors, routes, translations, components) |
| **jenkins** | 11 + 4 ACM helpers | Z-stream | Build metadata, logs, test reports, pipeline analysis |
| **jira** | 25 | Z-stream, TC-gen | Issue read/search/create, story details, bug correlation |
| **polarion** | 25 | Z-stream, TC-gen | Test case read/write, work items, expected behavior (PR-6b path) |
| **neo4j-rhacm** | 2 | All (optional) | Cypher queries against 370-component/541-relationship ACM architecture graph |
| **acm-search** | 5 | Z-stream, Hub health | Query the ACM Search database on a live hub |
| **acm-kubectl** | 3 | Z-stream, Hub health | Run kubectl across managed clusters |
| **playwright** | 24 | TC-gen | Browser automation for live validation (Phase 5) |

Configuration: `.mcp.json` at repo root (gitignored, generated by `/onboard` command).

---

## 6. Conventions and Patterns

### Code Layout (Python)
- `src/services/` -- business logic (dataclasses, service classes)
- `src/scripts/` -- CLI entry points (`gather.py`, `report.py`)
- `src/schemas/` -- JSON Schema files for artifact validation
- `src/models/` -- Pydantic models (TC-gen)
- `src/data/` -- static data (feature playbooks)
- `tests/` -- pytest (unit + regression)

### Artifact Naming
- `core-data.json` -- Stage 1 gather output (z-stream)
- `cluster-diagnosis.json` -- Stage 1.5 output
- `analysis-results.json` -- Stage 2 output (must validate against schema)
- `gather-output.json` -- Stage 1 output (TC-gen)
- `phase{N}-*.json` -- TC-gen phase artifacts
- `pipeline.log.jsonl` -- execution log

### Git Conventions
- Commits: conventional format, no `--amend` on pushed commits
- PRs: CodeRabbit auto-review enabled (`.coderabbit.yaml`)
- Quality gate: `/pre-push` slash command before push

### Knowledge File Formats
- Architecture docs: Markdown with structured headings
- Baselines: YAML (pod counts, services, webhooks, certs)
- Feature playbooks: YAML with `id`, prerequisites, failure_paths, suggested_classification
- Learned facts: Markdown under `learned/` with prefix (`zs-`, `hh-`, `tc-`, `general-`)

---

## 7. What context.md Should NOT Contain

- Ephemeral state (which cluster is running what version)
- Implementation details (function signatures, line numbers)
- Full API documentation (that belongs in docstrings)
- Duplicated content from CLAUDE.md or AGENTS.md (reference them instead)
- Marketing language or aspirational descriptions

---

## 8. Repo design in `context.md` (no ADR track)

The maintainers chose **not** to keep a separate `adr/` tree. Fold the substance of the former ADR list into one scannable **Repo design** paragraph at the top of `context.md` (see live [context.md](../context.md)), and keep `CLAUDE.md` / overview docs aligned when those choices change.

---

## 9. Gaps Discovered During Investigation

These should be resolved and reflected in `context.md` if answers are found:

1. **`agent_orchestrator.py` imports `services.evidence_validation_engine`** -- no matching file exists. Dead import or missing module?
2. **`REQUIRES_INVESTIGATION` is summary-only** -- intentional, but easy to confuse with per-test classifications. Should be explicitly documented.
3. **`main.py` docstring says v3.5, docs say v4.0** -- version label drift. Which is authoritative?
4. **Dual knowledge paths** -- `apps/z-stream-analysis/knowledge/` and `.claude/knowledge/` are supposed to stay aligned but can drift. What's the source of truth?
5. ~~**`acm-ui-mcp-server/`**~~ **Resolved:** legacy `mcp/acm-ui-mcp-server/` removed; canonical tree is `mcp/acm-source-mcp-server/` (Cursor key `acm-source`).

---

## 10. Raw Entity Index (for Claude Code Reference)

Complete list of every named entity, enum, and dataclass discovered, with file locations:

### Z-Stream Dataclasses (`apps/z-stream-analysis/src/services/`)
| Entity | File | Lines |
|--------|------|-------|
| `JenkinsTestCaseFailure` | `jenkins_intelligence_service.py` | 51-70 |
| `JenkinsTestReport` | `jenkins_intelligence_service.py` | 77-91 |
| `JenkinsMetadata` | `jenkins_intelligence_service.py` | 98-110 |
| `JenkinsIntelligence` | `jenkins_intelligence_service.py` | 113-121 |
| `StackFrame` | `stack_trace_parser.py` | 28-45 |
| `ParsedStackTrace` | `stack_trace_parser.py` | 48-59 |
| `FeatureGrounding` | `feature_area_service.py` | 22-30 |
| `FeatureMapping` | `feature_area_service.py` | 32-38 |
| `FeatureGrouping` | `feature_area_service.py` | 40-46 |
| `PrerequisiteCheck` | `feature_knowledge_service.py` | 23-30 |
| `MatchedFailurePath` | `feature_knowledge_service.py` | 32-42 |
| `FeatureReadiness` | `feature_knowledge_service.py` | 44-56 |
| `ComponentInfo` | `knowledge_graph_client.py` | 32-50 |
| `DependencyChain` | `knowledge_graph_client.py` | 52-70 |
| `ExtractedComponent` | `component_extractor.py` | 16-21 |
| `FeatureAreaHealth` | `cluster_investigation_service.py` | 26-38 |
| `PodDiagnostics` | `cluster_investigation_service.py` | 40-48 |
| `ComponentDiagnostics` | `cluster_investigation_service.py` | 50-60 |
| `ClusterLandscape` | `cluster_investigation_service.py` | 62-74 |
| `HealthFinding` | `cluster_health_service.py` | 42-50 |
| `SubsystemHealth` | `cluster_health_service.py` | 52-62 |
| `ManagedClusterHealth` | `cluster_health_service.py` | 64-75 |
| `ClusterIdentity` | `cluster_health_service.py` | 77-85 |
| `ClusterHealthReport` | `cluster_health_service.py` | 87-115 |
| `ClusterInfo` | `environment_validation_service.py` | 36-45 |
| `EnvironmentValidationResult` | `environment_validation_service.py` | 47-58 |
| `DependencyTarget` | `environment_oracle_service.py` | 42-50 |
| `DependencyHealth` | `environment_oracle_service.py` | 52-65 |
| `PolarionDiscovery` | `environment_oracle_service.py` | 67-78 |
| `OracleResult` | `environment_oracle_service.py` | 80-94 |
| `SelectorHistory` | `repository_analysis_service.py` | 22-30 |
| `ClassificationFeedback` | `feedback_service.py` | 21-32 |
| `RunFeedback` | `feedback_service.py` | 34-41 |
| `AnalysisPhase` | `two_agent_intelligence_framework.py` | 19-23 |
| `InvestigationResult` | `two_agent_intelligence_framework.py` | 26-38 |
| `SolutionResult` | `two_agent_intelligence_framework.py` | 40-50 |
| `ComprehensiveAnalysis` | `two_agent_intelligence_framework.py` | 52-56 |
| `AgentContext` | `agent_orchestrator.py` | 31-40 |
| `AgentResult` | `agent_orchestrator.py` | 42-52 |
| `TimeoutConfig` | `shared_utils.py` | 21-50 |
| `RepositoryConfig` | `shared_utils.py` | 52-80 |
| `ThresholdConfig` | `shared_utils.py` | 82-154 |
| `ValidationSeverity` | `schema_validation_service.py` | 17-21 |
| `ValidationIssue` (z-stream) | `schema_validation_service.py` | 24-32 |
| `ValidationResult` | `schema_validation_service.py` | 34-41 |

### TC-Gen Pydantic Models (`apps/test-case-generator/src/models/`)
| Entity | File | Lines |
|--------|------|-------|
| `GatherOutput` | `gather_output.py` | 30-44 |
| `PRData` | `gather_output.py` | 18-28 |
| `GatherOptions` | `gather_output.py` | 9-16 |
| `AnalysisResult` (TC-gen) | `analysis_result.py` | 9-31 |
| `Verdict` | `review_result.py` | 9-11 |
| `ValidationIssue` (TC-gen) | `review_result.py` | 14-20 |
| `ReviewResult` | `review_result.py` | 22-42 |

### MCP Server Models
| Entity | File |
|--------|------|
| `UIAnalyzer` | `mcp/acm-source-mcp-server/acm_source_mcp_server/analyzer.py` |
| `ServerState` | MCP server modules |
| `GitHubClient` | MCP server modules |
| JIRA response DTOs (15+) | `mcp/.external/jira-mcp-server/jira_mcp_server/server.py` (after `setup.sh`; or `tools/mcp/jira-mcp-server/...` on a dev machine) (lines 77-203) |

### JSON Schema Contracts
| Schema | File | Validates |
|--------|------|-----------|
| Analysis Results Schema (v3.9) | `apps/z-stream-analysis/src/schemas/analysis_results_schema.json` | `analysis-results.json` |
| Manifest Schema | `apps/z-stream-analysis/src/schemas/manifest_schema.json` | `manifest.json` |
| HTML Report Template | `apps/z-stream-analysis/src/schemas/` | HTML output format |
