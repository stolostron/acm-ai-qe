# ACM Console Test Case Generator (v2.0)

Generates Polarion-ready test cases for ACM Console features from JIRA tickets. Uses a 6-phase subagent pipeline: deterministic data gathering, parallel AI investigation (3 subagents), synthesis, optional live validation, AI-powered test case writing, mandatory quality review, and deterministic report/validation.

## Pipeline Architecture

```
Phase 0: Parse inputs + ask missing questions
  |
  v
Stage 1: gather.py               -> gather-output.json + pr-diff.txt
  |                                  (deterministic: gh CLI + local files)
  v
Phase 1 (PARALLEL):
  [feature-investigator]          -> JIRA deep dive, linked tickets, Polarion coverage
  [code-change-analyzer]          -> PR diff analysis, UI elements, Neo4j impact
  [ui-discovery]                  -> Selectors, translations, routes, wizards
  |
  v
Phase 2: Synthesize              -> Test plan (steps, setup, validations, teardown)
  |                                  STOP: "Investigation complete."
  v
Phase 3 (CONDITIONAL):
  [live-validator]                -> Browser + oc + acm-search + acm-kubectl
  |                                  (skip if --skip-live or no cluster)
  v
Phase 4:
  [test-case-generator]           -> test-case.md + analysis-results.json
  |                                  STOP: "Test case written."
  v
Phase 4.5 (MANDATORY GATE):
  [quality-reviewer]              -> PASS or NEEDS_FIXES (loop until PASS)
  |                                  STOP: "Quality review passed."
  v
Stage 3: report.py               -> HTML + review-results.json + SUMMARY.txt
                                     (deterministic: validation + HTML generation)
```

---

## Pipeline Execution

The pipeline is invoked via `/generate`. See `.claude/skills/generate/SKILL.md` for the full execution procedure, phase gates, question-asking protocol, and STOP checkpoints. For batch runs: `/batch`. For standalone reviews: `/review`.

---

## Quick Start

```bash
# Full pipeline via slash command
/generate ACM-30459

# With overrides
/generate ACM-30459 --version 2.17 --pr 5790 --area governance

# With live validation
/generate ACM-30459 --cluster-url https://console-openshift-console.apps.hub.example.com

# Skip live validation
/generate ACM-30459 --skip-live

# Batch mode
/batch ACM-30459,ACM-30460,ACM-30461 --version 2.17

# Review existing test case
/review runs/ACM-30459/<run-dir>/test-case.md
```

---

## MANDATORY: Read Conventions Before Writing Test Cases

Before writing any test case markdown, ALWAYS read:
- `knowledge/conventions/test-case-format.md` -- section order, naming, complexity levels
- `knowledge/conventions/area-naming-patterns.md` -- title patterns by area
- `knowledge/conventions/cli-in-steps-rules.md` -- when CLI is allowed in test steps

The report generator (`report.py`) validates the output against these conventions. Key rules:
- Title: `# RHACM4K-XXXXX - [Tag-Version] Area - Test Name`
- All Polarion metadata fields must be present
- Steps: H3 with numbered actions and bullet expected results
- CLI allowed in test steps ONLY for backend validation (not as a substitute for UI testing)

---

## Agent Definitions

Six agents, each with a dedicated role in the pipeline:

| Agent | File | Pipeline Phase | Role |
|-------|------|---------------|------|
| **Feature Investigator** | `.claude/agents/feature-investigator.md` | Phase 1 (parallel) | Deep JIRA investigation: story, comments, linked tickets, Polarion coverage, PR discovery |
| **Code Change Analyzer** | `.claude/agents/code-change-analyzer.md` | Phase 1 (parallel) | PR diff analysis: changed components, new UI elements, Neo4j impact, test scenarios |
| **UI Discovery** | `.claude/agents/ui-discovery.md` | Phase 1 (parallel) | Source code discovery: selectors, translations, routes, wizard steps, test IDs + optional live browser verification |
| **Live Validator** | `.claude/agents/live-validator.md` | Phase 3 | Live cluster verification: browser UI, oc CLI, acm-search, acm-kubectl |
| **Test Case Generator** | `.claude/agents/test-case-generator.md` | Phase 4 | Write test case markdown from synthesized investigation context |
| **Quality Reviewer** | `.claude/agents/quality-reviewer.md` | Phase 4.5 | Validate conventions, verify discovered vs assumed, AC vs implementation, scope alignment, numeric thresholds, peer consistency, PASS/NEEDS_FIXES |

Agent launch procedures (Phase 1 parallel launch, Phase 4.5 quality review loop) are in `.claude/skills/generate/SKILL.md`.

---

## MCP Servers

| Server | Tools | Purpose | Used By |
|--------|-------|---------|---------|
| acm-ui | ~20 | ACM Console source: selectors, routes, translations, wizard steps, test IDs | UI Discovery, Code Analyzer, Generator, Reviewer |
| jira | ~3 | JIRA investigation: full details, comments, linked tickets | Feature Investigator |
| polarion | ~7 | Existing test case coverage: search, read, compare | Feature Investigator, Reviewer |
| neo4j-rhacm | 2 | Architecture dependencies: component relationships, subsystem impact | Feature Investigator, Code Analyzer, UI Discovery |
| acm-search | ~5 | Live cluster resources: search K8s resources across clusters | Live Validator |
| acm-kubectl | 3 | Multicluster kubectl: list clusters, run commands on hub/spokes | Live Validator |
| playwright | 24 | Browser automation: navigate, snapshot, interact, screenshot, verify | UI Discovery (conditional), Live Validator |

First-time setup: from the repo root, run `claude` then `/onboard`.

### MCP Usage Rules

- **acm-ui**: ALWAYS call `set_acm_version` before any search/get operation. For Fleet Virt, also call `set_cnv_version`.
- **jira**: `get_issue` does NOT return issue links; use `search_issues` with JQL for linked tickets
- **polarion**: Project ID is ALWAYS `RHACM4K`; query syntax is Lucene, not JQL
- **neo4j-rhacm**: Requires Podman with `neo4j-rhacm` container running; optional but recommended
- **acm-search**: Use for verifying test prerequisites exist on cluster (namespaces, pods, policies)
- **acm-kubectl**: Use for checking spoke cluster state and running kubectl across managed clusters
- **playwright**: Always `browser_snapshot()` before interactions; use short waits (1-3s) with checks

### Agent-to-MCP Matrix

```
Feature Investigator:
  jira      -> get_issue, search_issues, get_project_components
  polarion  -> get_polarion_work_items, get_polarion_test_case_summary
  neo4j     -> read_neo4j_cypher (architecture context)
  bash      -> gh pr view (GitHub CLI via bash)

Code Change Analyzer:
  bash      -> gh pr view, gh pr diff (GitHub CLI via bash)
  acm-ui    -> set_acm_version, search_code, get_component_source,
               get_component_types, search_translations, get_routes
  neo4j     -> read_neo4j_cypher (component dependencies)

UI Discovery:
  acm-ui    -> set_acm_version, set_cnv_version, search_code, get_component_source,
               search_translations, get_wizard_steps, get_routes, get_acm_selectors,
               get_fleet_virt_selectors, find_test_ids, get_patternfly_selectors
  playwright -> browser_navigate, browser_snapshot, browser_take_screenshot (conditional: only when cluster URL provided)
  bash       -> oc login, oc whoami, oc get mch -A (for cluster auth before browser verification)

Live Validator:
  playwright -> browser_navigate, browser_snapshot, browser_click, browser_fill_form,
                browser_take_screenshot, browser_console_messages, browser_network_requests
  bash       -> oc get pods/csv/mch/managedcluster (oc CLI via bash)
  acm-search -> find_resources, query_database
  acm-kubectl -> clusters, kubectl, connect_cluster

Test Case Generator (spot-check only -- does NOT do primary investigation):
  acm-ui    -> set_acm_version, get_routes, search_translations

Quality Reviewer:
  acm-ui    -> set_acm_version, search_translations, get_routes, get_wizard_steps
  polarion  -> get_polarion_work_item, get_polarion_test_case_summary
  files     -> read existing test cases for consistency comparison
```

---

## Knowledge System

```
knowledge/
  conventions/               # Authoritative: test case format rules
    test-case-format.md      # Section order, naming, 85-case conventions
    polarion-html-templates.md  # HTML generation rules for Polarion
    area-naming-patterns.md  # Title patterns by area
    cli-in-steps-rules.md    # When CLI allowed in test steps
  architecture/              # Domain knowledge per console area
    governance.md            # Policy types, discovered vs managed
    rbac.md                  # FG-RBAC, MCRA, scopes
    fleet-virt.md            # Tree view, VM actions
    clusters.md              # Cluster lifecycle
    search.md                # Search API
    applications.md          # ALC, subscriptions
    credentials.md           # Provider credentials
  examples/                  # Complete sample test cases for format reference
    sample-test-case.md      # Convention-compliant sample (fallback when no peers)
  patterns/                  # Agent-written: grows from successful runs
    README.md
```

**Reading rules**: Always read conventions before generating. Read architecture for the relevant area. Read patterns for successful past runs in the same area.

**Writing rules**: Only write to `patterns/`. Never modify `conventions/` or `architecture/` programmatically.

**Persistent knowledge** (planned): After a successful run, the test-case-generator agent may write area-specific patterns to `knowledge/patterns/<area>-patterns.json` with discovered selectors, routes, translations, and common test structures. When present, read these at the start of future runs for the same area.

---

## Run Directory Layout

Each run produces artifacts under `runs/<JIRA_ID>/<JIRA_ID>-<timestamp>/`:

```
runs/ACM-30459/ACM-30459-2026-04-08T12-00-00/
  gather-output.json                 # Stage 1: all gathered data
  pr-diff.txt                        # Stage 1: full PR diff (if PR found)
  phase1-feature-investigation.md    # Phase 1: feature investigator agent output
  phase1-code-change-analysis.md     # Phase 1: code change analyzer agent output
  phase1-ui-discovery.md             # Phase 1: UI discovery agent output
  phase2-synthesized-context.md      # Phase 2: merged investigation + test plan
  phase3-live-validation.md          # Phase 3: live validator agent output (or skip note)
  test-case.md                       # Phase 4: primary deliverable
  analysis-results.json              # Phase 4: investigation metadata (audit/debugging)
  phase4.5-quality-review.md         # Phase 4.5: quality reviewer agent output (JSON block + review)
  test-case-setup.html               # Stage 3: Polarion setup section HTML
  test-case-steps.html               # Stage 3: Polarion steps table HTML
  review-results.json                # Stage 3: structural validation
  SUMMARY.txt                        # Stage 3: human-readable summary
  pipeline.log.jsonl                 # All stages + phases: telemetry (gather, log_phase, report)
```

---

## Safety Rules

1. **Read-only investigation**: Never modify JIRA tickets, Polarion work items, or cluster resources
2. **No assumed UI elements**: All UI labels, routes, and selectors must come from MCP discovery (acm-ui translations, routes) or PR diff -- never from memory
3. **Evidence-based**: Every expected result in a test step must trace to a discovered source (JIRA AC, PR code, acm-ui translation, live validation)
4. **Convention compliance**: Output must pass structural validation in Stage 3 and quality review in Phase 4.5
5. **File isolation**: Only write to `runs/` directory and `knowledge/patterns/`
6. **Quality gate**: NEVER deliver a test case that has not passed Phase 4.5 quality review
7. **Knowledge file authority**: Area knowledge files (`knowledge/architecture/<area>.md`) define verified behavior (field order, filtering, empty states). If agent analysis contradicts a knowledge file, trust the knowledge file and verify via `get_component_source()` before overriding
8. **Mandatory source verification**: Phase 4 (writer) and Phase 4.5 (reviewer) must each call `get_component_source()` on the primary changed file to verify at least one behavioral claim against actual source code
9. **Test vs production code**: Data from `.test.tsx`/`.test.ts` files (mock objects, fixture data) is NOT rendering behavior. Mark any claim derived from test files as "FROM TEST MOCK DATA"

---

## Tests

```bash
# Unit tests (38 tests, no external deps):
python -m pytest tests/unit/ -q
```

Test structure: `tests/unit/test_convention_validator.py` (convention validation rules), `tests/unit/test_models.py` (analysis result model fields), `tests/unit/test_file_service.py` (file operations). No cluster access, MCP, or JIRA credentials required.

---

## Session Tracing

Claude Code hooks capture every tool call, MCP interaction, prompt, subagent launch, and error into structured JSONL trace files. This provides full observability across all pipeline phases, including the AI agent phases (1-4.5) that the Python telemetry doesn't cover.

**Trace files:** `.claude/traces/<session_id>.jsonl` (gitignored, generated at runtime)
**Session index:** `.claude/traces/sessions.jsonl` (one-line summary per session)
**Hook implementation:** `.claude/hooks/agent_trace.py`

### Events captured

| Event | Hook | Fields |
|-------|------|--------|
| `prompt` | UserPromptSubmit | prompt text, `pipeline_command` (generate/review/batch) |
| `tool_call` | PreToolUse | tool, input summary, mcp_server/mcp_tool, oc_verb/resource/namespace, pipeline_phase, knowledge_category |
| `tool_result` | PostToolUse | tool, output (truncated) |
| `tool_error` | PostToolUseFailure | tool, error message |
| `subagent_complete` | SubagentStop | agent_id, agent_type, pipeline_phase |
| `turn_complete` | Stop | triggers session summary |

### Pipeline phase detection

Subagent launches are tagged with their pipeline phase:

| Subagent Type | Phase |
|---------------|-------|
| feature-investigator | phase_1 |
| code-change-analyzer | phase_1 |
| ui-discovery | phase_1 |
| live-validator | phase_3 |
| test-case-generator | phase_4 |
| quality-reviewer | phase_4_5 |

### Session summary fields

Written to `sessions.jsonl` on each Stop event: `pipeline_command`, `phases_seen`, `duration_sec`, `prompts`, `tool_calls`, `subagent_launches`, `mcp_calls`, `oc_commands`, `mutations`, `knowledge_reads`, `pattern_writes`, `pipeline_outputs`, `errors`.

---

## Validation Layers

The pipeline has two independent validation systems. Both must pass:

| Layer | When | What it checks | Authoritative for |
|-------|------|---------------|-------------------|
| **Phase 4.5** (quality-reviewer agent) | Before Stage 3 | MCP verification of UI elements, AC vs implementation, scope alignment, numeric thresholds, Polarion coverage, peer consistency, discovered vs assumed | Semantic correctness (are the right things tested?) |
| **Stage 3** (report.py / convention_validator.py) | After Phase 4.5 | Title pattern, metadata fields, section order, step format, entry point, teardown | Structural correctness (is the format right?) |

If Stage 3 fails after Phase 4.5 passed, fix the structural issue and re-run `report.py`. Do not re-run the quality reviewer unless the fix changed test content.

---

## Quality Standards

Test cases are validated against these criteria (Phase 4.5 + Stage 3):

1. **Metadata completeness**: All Polarion fields present, correct release version
2. **Section order**: Title -> Metadata -> Fields -> Description -> Setup -> Steps -> Teardown
3. **Entry point discovered**: Navigation path verified via acm-ui `get_routes()`
4. **UI elements discovered**: Labels/strings verified via `search_translations()`
5. **CLI-in-steps rule**: CLI only for backend validation, in dedicated steps placed after UI steps (not embedded within UI steps)
6. **Step granularity**: Each step verifies one behavior — no mixing observation (read/check) with interaction (click/navigate)
7. **Implementation detail translation**: Code details (sort algorithms, default values, parsing logic) translated into observable verifications
8. **Setup completeness**: Numbered bash commands with `# Expected:` comments
9. **Step format**: H3 title, numbered actions, bullet expected results, `---` separators
10. **Teardown**: Cleanup commands that reverse setup, `--ignore-not-found` on deletes
11. **Peer consistency**: Format matches existing test cases in the same area/version
12. **Discovered vs assumed**: Reviewer verifies UI elements against MCP sources

---

## Supported Areas

| Area | Tag Pattern | Knowledge File |
|------|------------|----------------|
| Governance | `[GRC-X.XX]` | `architecture/governance.md` |
| RBAC | `[FG-RBAC-X.XX]` | `architecture/rbac.md` |
| Fleet Virtualization | `[FG-RBAC-X.XX] Fleet Virtualization UI` | `architecture/fleet-virt.md` |
| CCLM | `[FG-RBAC-X.XX] CCLM` | `architecture/cclm.md` |
| MTV | `[MTV-X.XX]` | `architecture/mtv.md` |
| Search | `[FG-RBAC-X.XX] Search` | `architecture/search.md` |
| Clusters | `[Clusters-X.XX]` | `architecture/clusters.md` |
| Applications | `[Apps-X.XX]` | `architecture/applications.md` |
| Credentials | `[Credentials-X.XX]` | `architecture/credentials.md` |

---

## Document Index

- `README.md` -- Setup, usage, examples
- `CLAUDE.md` -- This file (app constitution)
- `docs/00-OVERVIEW.md` -- Architecture overview, pipeline/agent/MCP summary
- `docs/01-PIPELINE-PHASES.md` -- Phase-by-phase pipeline execution
- `docs/02-AGENTS.md` -- Agent definitions, inputs, outputs, MCP tools
- `docs/03-MCP-INTEGRATION.md` -- MCP server setup, tools, usage patterns
- `docs/04-KNOWLEDGE-SYSTEM.md` -- Conventions, architecture knowledge, patterns
- `docs/05-QUALITY-GATES.md` -- Phase 4.5 reviewer + Stage 3 validator
- `docs/06-SESSION-TRACING.md` -- Claude Code hooks, JSONL traces, session summaries
- `docs/architecture-diagrams.html` -- Interactive pipeline workflow visualization
- `knowledge/README.md` -- Knowledge database index
- `knowledge/conventions/test-case-format.md` -- Test case format conventions
- `knowledge/conventions/polarion-html-templates.md` -- Polarion HTML rules
- `knowledge/conventions/area-naming-patterns.md` -- Title patterns by area
- `knowledge/conventions/cli-in-steps-rules.md` -- When CLI allowed in test steps
- `.claude/skills/generate/SKILL.md` -- Pipeline orchestration skill (Phase 0 through Stage 3)
- `.claude/skills/generate/phase-gates.md` -- Phase tracking and gate enforcement rules
- `.claude/skills/generate/synthesis-template.md` -- Phase 2 synthesis context template
- `.claude/skills/review/SKILL.md` -- Test case quality review skill
- `.claude/skills/batch/SKILL.md` -- Batch generation skill
- `.claude/agents/feature-investigator.md` -- Phase 1: JIRA deep dive
- `.claude/agents/code-change-analyzer.md` -- Phase 1: PR diff analysis
- `.claude/agents/ui-discovery.md` -- Phase 1: ACM UI source discovery
- `.claude/agents/live-validator.md` -- Phase 3: Live cluster verification
- `.claude/agents/test-case-generator.md` -- Phase 4: Test case writer
- `.claude/agents/quality-reviewer.md` -- Phase 4.5: Quality gate
