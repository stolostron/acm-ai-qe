# ACM Console Test Case Generator (v1.0)

Generates Polarion-ready test cases for ACM Console features from JIRA tickets. Uses a 3-stage pipeline: deterministic data gathering, AI-powered investigation and generation via MCP servers, and deterministic report/validation. Produces markdown test cases following conventions from 85+ existing test cases, plus Polarion HTML for direct import.

## Pipeline Execution UX (MANDATORY)

When a user asks to generate a test case, **do NOT delegate the entire pipeline to a single agent**. The user must see stage-by-stage progress in their terminal. Run each stage yourself in the main conversation with visible status updates between them.

**Required behavior:**

1. **Stage 1** -- Run `gather.py` yourself. Before running, output:
   ```
   Stage 1: Gathering data for <JIRA_ID>...
   ```
   After it completes, summarize what was collected (e.g., "Found PR #5790, 11 files changed. Area: governance. Loaded 3 peer test cases and governance architecture knowledge.").

2. **Stage 2** -- Perform MCP-powered investigation and test case generation. Before starting, output:
   ```
   Stage 2: Investigating and generating test case...
   ```
   Use MCP servers (JIRA, Polarion, ACM UI, Neo4j) to investigate the feature deeply, then generate the test case markdown. After completion, show what was produced (e.g., "Generated RHACM4K-XXXXX-GRC-Policy-Details-Labels.md (8 steps, medium complexity). Self-review: PASS.").

3. **Stage 3** -- Run `report.py` yourself. Before running, output:
   ```
   Stage 3: Generating reports...
   ```
   After it completes, confirm the output files and show the summary.

**Why:** When everything runs inside a single agent, the user only sees collapsed tool calls with no sense of progress. Stage-by-stage updates keep the user informed.

## Quick Start

```bash
# Full pipeline via slash command
/generate ACM-30459

# Or manual stage-by-stage
python -m src.scripts.gather ACM-30459 --version 2.17
# ... Stage 2: AI investigation + generation ...
python -m src.scripts.report runs/ACM-30459/<run-dir>
```

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

## Architecture

```
STAGE 1: gather.py       -> gather-output.json + pr-diff.txt
                             (deterministic: gh CLI + local files)

STAGE 2: AI Generation   -> test-case.md + analysis-results.json
                             (MCP-powered: JIRA, Polarion, ACM UI, Neo4j)
                             (optional: browser MCP for live validation)

STAGE 3: report.py       -> test-case-setup.html + test-case-steps.html
                             + review-results.json + SUMMARY.txt
                             + pipeline.log.jsonl
                             (deterministic: validation + HTML generation)
```

### Run Directory Layout

Each run produces artifacts under `runs/<JIRA_ID>/<JIRA_ID>-<timestamp>/`:

```
runs/ACM-30459/ACM-30459-2026-04-08T12-00-00/
  gather-output.json        # Stage 1: all gathered data
  pr-diff.txt               # Stage 1: full PR diff (if PR found)
  test-case.md              # Stage 2: primary deliverable
  analysis-results.json     # Stage 2: investigation metadata
  test-case-setup.html      # Stage 3: Polarion setup section HTML
  test-case-steps.html      # Stage 3: Polarion steps table HTML
  review-results.json       # Stage 3: structural validation
  SUMMARY.txt               # Stage 3: human-readable summary
  pipeline.log.jsonl        # All stages: telemetry
```

## MCP Servers

| Server | Tools | Purpose |
|--------|-------|---------|
| acm-ui | ~20 | ACM Console source discovery: selectors, routes, translations, wizard steps, test IDs |
| jira | ~25 | JIRA ticket investigation: full details, comments, linked tickets, QE tracking |
| polarion | ~25 | Existing test case coverage: search, read, compare |
| neo4j-rhacm | 2 | Architecture dependencies: component relationships, subsystem impact |

Setup: `bash mcp/setup.sh` from repo root, select "Test Case Generator".

### MCP Usage Rules

- **acm-ui**: ALWAYS call `set_acm_version` before any search/get operation
- **jira**: `get_issue` does NOT return issue links; use `search_issues` with JQL for linked tickets
- **polarion**: Project ID is ALWAYS `RHACM4K`; query syntax is Lucene, not JQL
- **neo4j-rhacm**: Requires Podman with `neo4j-rhacm` container running; optional for test case generation

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
  patterns/                  # Agent-written: grows from successful runs
    README.md
  diagnostics/               # Known quality issues
    common-mistakes.md       # Frequent test case errors
```

**Reading rules**: Always read conventions before generating. Read architecture for the relevant area.
**Writing rules**: Only write to `patterns/` and `diagnostics/`. Never modify `conventions/` or `architecture/` programmatically.

## Agent Definitions

- **`.claude/agents/test-case-generator.md`**: Main Stage 2 agent. Reads gather output, uses MCPs to investigate, generates test case markdown, self-reviews.
- **`.claude/agents/quality-reviewer.md`**: Review sub-agent. Validates generated test case against conventions, checks discovered vs assumed elements, reports verdict.

## Safety Rules

1. **Read-only investigation**: Never modify JIRA tickets, Polarion work items, or cluster resources
2. **No assumed UI elements**: All UI labels, routes, and selectors must come from MCP discovery (acm-ui translations, routes) or PR diff -- never from memory
3. **Evidence-based**: Every expected result in a test step must trace to a discovered source (JIRA AC, PR code, acm-ui translation, live validation)
4. **Convention compliance**: Output must pass structural validation in Stage 3
5. **File isolation**: Only write to `runs/` directory and `knowledge/patterns/`

## Quality Standards

Test cases are validated against these criteria (Stage 3 + quality-reviewer agent):

1. **Metadata completeness**: All Polarion fields present, correct release version
2. **Section order**: Title -> Metadata -> Fields -> Description -> Setup -> Steps -> Teardown
3. **Entry point discovered**: Navigation path verified via acm-ui `get_routes()`
4. **UI elements discovered**: Labels/strings verified via `search_translations()`
5. **CLI-in-steps rule**: CLI only for backend validation, never as substitute for UI testing
6. **Setup completeness**: Numbered bash commands with `# Expected:` comments
7. **Step format**: H3 title, numbered actions, bullet expected results, `---` separators
8. **Teardown**: Cleanup commands that reverse setup, `--ignore-not-found` on deletes

## Supported Areas

| Area | Tag Pattern | Knowledge File |
|------|------------|----------------|
| Governance | `[GRC-X.XX]` | `architecture/governance.md` |
| RBAC | `[FG-RBAC-X.XX]` | `architecture/rbac.md` |
| Fleet Virtualization | `[FG-RBAC-X.XX] Fleet Virtualization UI` | `architecture/fleet-virt.md` |
| CCLM | `[FG-RBAC-X.XX] CCLM` | -- |
| MTV | `[MTV-X.XX]` | -- |
| Search | `[FG-RBAC-X.XX] Search` | `architecture/search.md` |
| Clusters | `[Clusters-X.XX]` | `architecture/clusters.md` |
| Applications | `[Apps-X.XX]` | `architecture/applications.md` |
| Credentials | `[Credentials-X.XX]` | `architecture/credentials.md` |

## Document Index

- `README.md` -- Setup, usage, examples
- `CLAUDE.md` -- This file (app constitution)
- `knowledge/README.md` -- Knowledge database index
- `knowledge/conventions/test-case-format.md` -- Test case format conventions
- `knowledge/conventions/polarion-html-templates.md` -- Polarion HTML rules
