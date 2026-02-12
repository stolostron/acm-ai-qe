# Z-Stream Pipeline Analysis (v2.5)

Enterprise Jenkins pipeline failure analysis with definitive PRODUCT BUG | AUTOMATION BUG | INFRASTRUCTURE classification.

## Quick Start

```bash
# Step 1: Gather data from Jenkins
python -m src.scripts.gather "<JENKINS_URL>"

# Step 2: AI analyzes core-data.json (creates analysis-results.json)
# Read core-data.json, use extracted_context, classify each test

# Step 3: Generate reports
python -m src.scripts.report runs/<dir>
```

## MANDATORY: Read Schema Before Writing analysis-results.json

Before writing analysis-results.json, ALWAYS read `src/schemas/analysis_results_schema.json` and the output example in `.claude/agents/z-stream-analysis.md` (lines 970-1079). The report generator (`report.py`) will reject the file if required fields are missing or named incorrectly. Key fields that must be exact:
- `per_test_analysis` (NOT `failed_tests`)
- `summary.by_classification` (NOT `classification_breakdown`)
- `investigation_phases_completed` (required array)

## Architecture

```
STAGE 1: gather.py    → core-data.json + repos/
STAGE 2: AI Analysis  → analysis-results.json (5-phase investigation)
STAGE 3: report.py    → Detailed-Analysis.md + per-test-breakdown.json + SUMMARY.txt
```

See `docs/00-OVERVIEW.md` for detailed diagrams.

## Run Directory

```
runs/<job>_<timestamp>/
├── core-data.json          ← Primary data for AI
├── run-metadata.json       ← Run metadata (timing, version)
├── element-inventory.json  ← MCP data (if available)
├── repos/                  ← Cloned repos (fallback)
├── analysis-results.json   ← AI output
├── Detailed-Analysis.md    ← Final report
├── per-test-breakdown.json ← Structured data for tooling
└── SUMMARY.txt             ← Brief summary
```

## Classification Guide

### PRODUCT_BUG (Owner: Product Team)
- 500/502/503 server errors
- Backend API failures
- UI feature broken (element exists but doesn't render)

### AUTOMATION_BUG (Owner: Automation Team)
- Element not found + selector not in product code
- Selector changed in product, test not updated
- Test expects outdated response format

### INFRASTRUCTURE (Owner: Platform Team)
- Cluster not accessible
- Network/DNS failures
- Multiple unrelated tests failing

### MIXED
- Multiple distinct root causes identified
- Provide breakdown per cause

### UNKNOWN
- Insufficient evidence (confidence < 0.50)
- Needs manual investigation

### FLAKY
- Test passes on retry without code changes
- Intermittent timing-dependent failure
- No product or automation code change explains failure

### NO_BUG
- Test failure is expected given recent intentional changes
- Test validates deprecated behavior that was removed by design

## Decision Quick Reference (3-Path Routing)

| Evidence | Path | Classification |
|----------|------|----------------|
| `console_search.found = false` | A | AUTOMATION_BUG |
| `element_removed = true` in timeline | A | AUTOMATION_BUG |
| `failure_type = element_not_found` | A | AUTOMATION_BUG |
| Timeout waiting for missing selector | A | AUTOMATION_BUG |
| Timeout (non-selector) | B1 | INFRASTRUCTURE |
| `environment.cluster_accessible = false` | B1 | INFRASTRUCTURE |
| Multiple unrelated tests timeout | B1 | INFRASTRUCTURE |
| 500 errors in console log | B2 | → JIRA investigation → PRODUCT_BUG |
| Assertion failure / unexpected response | B2 | → JIRA investigation → PRODUCT_BUG or AUTOMATION_BUG |
| Auth errors / feature broken | B2 | → JIRA investigation → PRODUCT_BUG or AUTOMATION_BUG |
| Feature story contradicts product behavior | B2/E | PRODUCT_BUG |
| Acceptance criteria changed, test unchanged | E | AUTOMATION_BUG |
| Linked PR regression + test failure | E | PRODUCT_BUG |
| Test passes on retry, no code changes | Any | FLAKY |
| Failure matches intentional product change | E | NO_BUG |

## Multi-Evidence Requirement

**Every classification needs 2+ evidence sources:**

```json
"evidence_sources": [
  {"source": "console_search", "finding": "found=false", "tier": 1},
  {"source": "timeline_evidence", "finding": "element_removed", "tier": 1}
]
```

## Extracted Context (v2.4+)

Each failed test includes pre-extracted context in core-data.json:

- `test_file.content` - actual test code (up to 200 lines)
- `page_objects` - imported selector definitions
- `console_search.found` - whether selector exists in product
- `detected_components` - backend components for Knowledge Graph

Use extracted_context first. Only access repos/ if insufficient.

## MCP Servers Available

Three MCP servers provide tools during Stage 2 (AI Analysis). New users: run `bash mcp/setup.sh` from the repo root to configure all servers.

### ACM-UI MCP (20 tools)

Provides access to ACM Console and kubevirt-plugin source code via GitHub.

**Version Management:**
| Tool | Purpose |
|------|---------|
| `set_acm_version` | Set ACM Console branch (2.11-2.17, latest=2.16) |
| `set_cnv_version` | Set kubevirt-plugin branch (4.14-4.22, latest=4.21) |
| `detect_cnv_version` | Auto-detect CNV version from connected cluster |
| `list_versions` | Show all supported version mappings |
| `get_current_version` | Get active version for a repo |
| `list_repos` | List repos with current settings |
| `get_cluster_virt_info` | Cluster virtualization details |

**Code Discovery:**
| Tool | Purpose |
|------|---------|
| `search_code` | GitHub code search across repos |
| `find_test_ids` | Find data-testid/aria-label attributes in a file |
| `get_component_source` | Get raw source code for a file |
| `search_component` | Search for component files by name |
| `get_route_component` | Map URL path to source files |

**Specialized:**
| Tool | Purpose |
|------|---------|
| `get_acm_selectors` | QE-proven selectors from test repos (clc, search, app, grc) |
| `get_fleet_virt_selectors` | Fleet Virt UI selectors from kubevirt-plugin |
| `search_translations` | Find exact UI text (button labels, messages) |
| `get_wizard_steps` | Extract wizard step structure and conditions |
| `get_component_types` | Extract TypeScript type/interface definitions |
| `get_routes` | All ACM Console navigation paths |
| `get_patternfly_selectors` | PatternFly v6 CSS selector reference |

### JIRA MCP (23 tools)

Full JIRA integration for issue search, creation, and management.

**Issue Operations:**
| Tool | Purpose |
|------|---------|
| `search_issues` | JQL search for related bugs |
| `get_issue` | Get full issue details |
| `create_issue` | Create new bug/task |
| `update_issue` | Update issue fields |
| `transition_issue` | Move issue status (e.g., In Progress, Done) |
| `add_comment` | Add comment to issue |
| `log_time` | Log work time on issue |
| `link_issue` | Create links between issues (Blocks, Relates, etc.) |

**Project & Component:**
| Tool | Purpose |
|------|---------|
| `get_projects` | List accessible projects |
| `get_project_components` | List components in a project |
| `get_link_types` | List available link types |
| `debug_issue_fields` | Show all raw fields for an issue |

**Team Management:**
| Tool | Purpose |
|------|---------|
| `list_teams` | List configured teams |
| `add_team` / `remove_team` | Manage team configurations |
| `search_issues_by_team` | Find issues assigned to team members |
| `assign_team_to_issue` | Add all team members as watchers |
| `add_watcher_to_issue` / `remove_watcher_from_issue` | Manage watchers |
| `get_issue_watchers` | List watchers on an issue |
| `list_component_aliases` / `add_component_alias` / `remove_component_alias` | Manage component aliases |

### Knowledge Graph MCP (Neo4j RHACM)

Component dependency analysis and feature workflow context via Cypher queries. Optional - may not be connected.

Based on [stolostron/knowledge-graph](https://github.com/stolostron/knowledge-graph/tree/main/acm/agentic-docs/dependency-analysis), forked with additional queries and MCP integration docs. 291 components across 7 subsystems, 419 relationships.

**Usage in investigation:**
- Phase B5: Component dependency analysis, cascading failure detection
- Phase C2: Cascading failure validation
- Phase E0: Subsystem context building and feature workflow understanding

| Tool | Purpose |
|------|---------|
| `read_neo4j_cypher` | Execute Cypher queries against RHACM component graph |

## Key Principle

**Don't guess. Investigate.**

AI has full repo access - use it to understand exactly what went wrong before classifying. Read actual test code, trace imports, search for elements, check git history.

For non-obvious failures (not simple selector mismatches or timeouts), use Knowledge Graph
to understand the subsystem context and JIRA to read feature stories before classifying.
Understanding what a feature SHOULD do is key to classifying what went WRONG.

## Detailed Documentation

| Topic | File |
|-------|------|
| Pipeline overview & classification guide | `docs/00-OVERVIEW.md` |
| Stage 1: Data gathering (Steps 1-8) | `docs/01-STAGE1-DATA-GATHERING.md` |
| Stage 2: AI analysis (Phases A-E) | `docs/02-STAGE2-AI-ANALYSIS.md` |
| Stage 3: Report generation | `docs/03-STAGE3-REPORT-GENERATION.md` |
| All services reference | `docs/04-SERVICES-REFERENCE.md` |
| MCP integration guide | `docs/05-MCP-INTEGRATION.md` |

## CLI Options

```bash
python -m src.scripts.gather <url> --skip-env    # Skip cluster validation
python -m src.scripts.gather <url> --skip-repo   # Skip repository cloning
python -m src.scripts.report <dir> --keep-repos  # Don't cleanup repos/
```

## File Structure

```
z-stream-analysis/
├── main.py                 # Entry point
├── src/scripts/
│   ├── gather.py          # Stage 1: Data collection
│   └── report.py          # Stage 3: Report generation
├── src/services/          # 12 Python services
├── src/schemas/           # JSON Schema validation
├── .claude/agents/
│   └── z-stream-analysis.md  # Agent definition
└── docs/                  # Detailed documentation
```
