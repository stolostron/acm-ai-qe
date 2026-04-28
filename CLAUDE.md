# AI Systems Suite

Multi-app repository for ACM quality engineering tools, built on Claude Code.

## Applications

### Z-Stream Analysis (`apps/z-stream-analysis/`) — Active

Jenkins pipeline failure analysis (v4.0) with classification: PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE | FLAKY | NO_BUG | MIXED | UNKNOWN. v4.0 moves cluster health to Stage 1.5 cluster-diagnostic agent with structured health fields, changes PR-7 to context signals (not binding), adds PR-6b Polarion check, symmetric counterfactual (D-V5c/D-V5e), and layer discrepancy detection. v3.9 added provably linked grouping (Phase A4), per-test verification within groups (4-point check), and expanded counterfactual verification (D-V5) with 9 templates. v3.8 features 12-layer diagnostic investigation with per-group investigation agents for root-cause-first classification. Includes comprehensive cluster diagnostic (Stage 1.5) with hub-health-style investigation, diagnostic trap detection, self-healing knowledge, assertion value extraction, per-feature-area graduated infrastructure scoring, per-test causal link verification, failure mode categorization, blank page pre-routing, hook failure deduplication, temporal evidence routing, feature investigation playbooks, tiered cluster investigation, classification feedback, and standalone knowledge database (`knowledge/`).

Five-stage pipeline:
0. **Environment Oracle** (inside gather.py) — Feature-aware dependency health & knowledge database (`cluster_oracle`)
1. **gather.py** — Extracts test data from Jenkins (builds `core-data.json` with cluster landscape and feature grounding; persists `cluster.kubeconfig` for Stage 1.5 and Stage 2)
1.5. **Cluster Diagnostic** (AI agent) — Comprehensive 6-phase cluster investigation producing `cluster-diagnosis.json` with environment health score, subsystem health, operator health, image integrity validation, classification guidance, dependency chain verification, 14 diagnostic trap checks (+ Trap 1b leader-election variant), service endpoint verification, OLM foundational health, sub-operator CR status, and structured data for Stage 2 routing
2. **AI Analysis** — 12-layer diagnostic investigation: groups tests by shared signals, traces root cause through infrastructure layers (Compute→UI), classifies based on WHO caused breakage. Per-group investigation agents for deeper analysis. Produces `analysis-results.json` with `root_cause_layer` per test.
3. **report.py** — Generates `Detailed-Analysis.md` + `analysis-report.html` from analysis results

3 slash commands: `/analyze` (full pipeline), `/gather` (Stage 1 only), `/quick` (skip cluster diagnostic). 4 agents in `.claude/agents/` (analysis, cluster-diagnostic, data-collector, investigation-agent). Session tracing via Claude Code hooks captures all tool calls, MCP interactions, prompts, and subagent operations to structured JSONL files (`.claude/traces/`) with pipeline-specific enrichment (oc command parsing, pipeline stage detection, knowledge read categorization, session-level aggregate stats).

See `apps/z-stream-analysis/CLAUDE.md` for schema requirements, classification guide, and MCP tool reference.

### ACM Hub Health Agent (`apps/acm-hub-health/`) — Active

AI-powered diagnostic and remediation agent for ACM hub clusters. Uses Claude Code with embedded ACM domain knowledge to perform health checks at any depth -- from quick sanity checks to deep component-level investigations. Natural language driven, no dependencies beyond `oc` + `claude`. Diagnosis is read-only; cluster fixes are executed only after presenting a structured remediation plan and getting explicit user approval. Includes structured knowledge database (`knowledge/`) with baseline, dependency chains (12 cascade paths with layer annotations), 12-layer diagnostic model (vertical root cause tracing), webhooks, certificates, addon catalog, and 14 diagnostic traps. Phase 3 uses layer-organized health checks (foundational layers first, then component layers). Phase 5 traces both horizontally (dependency chains) and vertically (12 infrastructure layers). Uses the ACM search database MCP (`acm-search`) for fleet-wide spoke-side resource queries across all managed clusters. Falls back to cluster metadata introspection (8 live metadata sources) and the Neo4j knowledge graph MCP (`neo4j-rhacm`) for dependency analysis when the curated knowledge doesn't cover a component or path. Optional CLI wrapper (`acm-hub`) enables running diagnostics from any terminal without launching an interactive session. Session tracing via Claude Code hooks captures all tool calls, MCP interactions, prompts, and errors to structured JSONL files (`.claude/traces/`) with diagnostic-specific enrichment (oc command parsing, phase inference, mutation detection, session-level aggregate stats).

Usage: `cd apps/acm-hub-health && oc login <hub> && claude`

### Test Case Generator (`apps/test-case-generator/`) — Active

Generates Polarion-ready test cases for ACM Console features from JIRA tickets. 6-phase subagent pipeline: deterministic data gathering (gh CLI), parallel AI investigation (3 subagents: feature-investigator, code-change-analyzer, ui-discovery), synthesis with scope gating and AC cross-referencing, optional live validation (browser + oc + acm-search + acm-kubectl), AI-powered test case writing, mandatory quality review gate (AC vs implementation check, scope alignment, numeric threshold validation), and deterministic report/validation with Polarion HTML output. 6 specialized agents, 7 MCP integrations (JIRA, Polarion, ACM UI, Neo4j, ACM Search, ACM Kubectl, Playwright). Supports 9 console areas (Governance, RBAC, Fleet Virt, CCLM, MTV, Clusters, Search, Applications, Credentials). 3 skills in `.claude/skills/`: `/generate` (full pipeline with phase gates and synthesis template), `/review` (standalone quality review), `/batch` (multi-ticket generation). Session tracing via Claude Code hooks captures all tool calls, MCP interactions, prompts, subagent launches, and errors to structured JSONL files (`.claude/traces/`) with pipeline-specific enrichment (phase detection, command type inference, oc command parsing, MCP server extraction, session-level aggregate stats).

## Getting Started

New to this repo? Run `/onboard` for interactive setup -- it detects your environment, explains the apps, and guides MCP server configuration with credential setup. Works for both new team members and fresh AI agent sessions.

For manual setup: launch `claude` from the repo root and run `/onboard`.

## CodeRabbit Review Policy

After modifying code in any app (`z-stream-analysis`, `acm-hub-health`, `test-case-generator`), run `/coderabbit:review uncommitted` when changes touch:
- Python source or tests (`src/`, `tests/`)
- Agent instructions (`.claude/agents/`)
- Schema/model files (`src/schemas/`, `src/models/`)

**Skip** reviews for `knowledge/` YAML/markdown, `docs/` files, and `runs/` output.

On review results — **do NOT blindly implement suggestions**:
1. For each finding, independently read the relevant code and verify the issue is real.
2. Check whether the suggested fix would break downstream contracts, tests, or conventions.
3. Only implement findings confirmed by your own investigation. Skip false positives.
4. After implementing confirmed fixes, re-run `/coderabbit:review uncommitted` to confirm no regressions.

## Running Z-Stream Analysis

Open Claude Code in this repository (root or `apps/z-stream-analysis/`) and use:

```
/analyze <JENKINS_URL>
```

Or use natural language: `Analyze this run: <JENKINS_URL>`

Other commands: `/gather <URL>` (Stage 1 only), `/quick <URL>` (skip cluster diagnostic for fast triage).

Claude Code runs each stage with visible progress updates — do NOT delegate the entire pipeline to a single agent. See `apps/z-stream-analysis/CLAUDE.md` "Pipeline Execution UX" section.

### Manual Pipeline (Advanced)

```bash
cd apps/z-stream-analysis/

# Stage 1: Gather data
python -m src.scripts.gather "<JENKINS_URL>"
python -m src.scripts.gather "<JENKINS_URL>" --skip-env    # Skip cluster validation
python -m src.scripts.gather "<JENKINS_URL>" --skip-repo   # Skip repo cloning

# Stage 2: AI Analysis (12-layer diagnostic investigation)
# Read core-data.json + cluster-diagnosis.json
# Classify each failure using 12-layer model + MCP tools
# MUST read src/schemas/analysis_results_schema.json before writing analysis-results.json

# Stage 3: Generate reports
python -m src.scripts.report runs/<run_dir>
```

## MCP Servers (`mcp/`)

From the repo root, launch `claude` and run `/onboard`. It detects your environment, prompts for credentials, configures MCP servers, and generates `.mcp.json` for the selected app(s).

| Server | Tools | Source | Purpose |
|--------|-------|--------|---------|
| ACM UI (`mcp/acm-ui-mcp-server/`) | 20 | This repo | ACM Console + kubevirt-plugin source code search via GitHub |
| Jenkins | 7+4 | [upstream](https://github.com/redhat-community-ai-tools/jenkins-mcp) + `mcp/jenkins-acm-tools.py` | Jenkins pipeline API + ACM analysis tools |
| JIRA | 25 | [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server) | Issue search, creation, management for bug correlation (Jira Cloud) |
| Neo4j RHACM | 2 | [mcp-neo4j-cypher](https://pypi.org/project/mcp-neo4j-cypher/) (PyPI) | Component dependency analysis via Cypher queries (optional) |
| ACM Search | 5 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | Fleet-wide resource queries via search-postgres (spoke-side visibility) |
| Polarion (`mcp/polarion/`) | 25 | This repo | Polarion test case access (optional) |
| ACM Kubectl | 3 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | Multicluster kubectl for hub and spoke clusters |
| Playwright | 24 | [@playwright/mcp](https://www.npmjs.com/package/@anthropic-ai/playwright-mcp) (npm) | Browser automation for live UI validation |

External MCPs (JIRA, Jenkins, Knowledge Graph, ACM Search, ACM Kubectl) are cloned at setup time into `mcp/.external/` (gitignored).
This repo only contains our original MCP code: ACM UI, Polarion wrapper, Jenkins ACM tools.

**Jenkins Setup:** Run `/onboard` and provide your Jenkins username and API token when prompted. Credentials are stored in `mcp/.external/jenkins-mcp/.env` and injected into `.mcp.json` automatically. Requires Red Hat VPN for internal Jenkins access.

**JIRA Cloud Setup:** Run `/onboard` and provide credentials when prompted, or create `mcp/.external/jira-mcp-server/.env` with your Jira Cloud credentials after setup. Get a token at https://id.atlassian.com/manage-profile/security/api-tokens.

## Directory Structure

```
ai_systems_v2/
├── apps/
│   ├── acm-hub-health/        # Active — hub health diagnostic agent
│   ├── z-stream-analysis/     # Active — pipeline failure analysis
│   └── test-case-generator/   # Active — Polarion-ready test case generation from JIRA tickets
├── mcp/
│   ├── setup.sh               # Interactive setup (clones external MCPs, creates venvs)
│   ├── verify.py              # Standalone health checker (run anytime)
│   ├── acm-ui-mcp-server/     # Our code: ACM Console source search
│   ├── polarion/              # Our code: Polarion wrapper
│   ├── jenkins-acm-tools.py   # Our code: ACM-specific Jenkins analysis tools
│   └── .external/             # Cloned at setup time (gitignored)
├── AGENTS.md                  # Agent reference (tool-agnostic, for external AI tools)
├── CLAUDE.md                  # This file — Claude Code agent instructions
└── README.md                  # User-facing setup and onboarding guide
```

## Tests

```bash
# Z-stream analysis tests (from app directory)
cd apps/z-stream-analysis/

# Fast — unit + regression (686 tests, no external deps):
python -m pytest tests/unit/ tests/regression/ -q

# Full suite (731 tests, requires Jenkins VPN for integration):
python -m pytest tests/ -q --timeout=300
```
