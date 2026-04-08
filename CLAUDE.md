# AI Systems Suite

Multi-app repository for ACM quality engineering tools, built on Claude Code.

## Applications

### Z-Stream Analysis (`apps/z-stream-analysis/`) — Active

Jenkins pipeline failure analysis (v3.9) with classification: PRODUCT_BUG | AUTOMATION_BUG | INFRASTRUCTURE | FLAKY | NO_BUG | MIXED | UNKNOWN. v3.9 adds provably linked grouping (Phase A4), per-test verification within groups (4-point check), and expanded counterfactual verification (D-V5) with 9 templates. v3.8 features 12-layer diagnostic investigation with per-group investigation agents for root-cause-first classification. Includes comprehensive cluster diagnostic (Stage 1.5) with hub-health-style investigation, diagnostic trap detection, self-healing knowledge, assertion value extraction, per-feature-area graduated infrastructure scoring, per-test causal link verification, failure mode categorization, blank page pre-routing, hook failure deduplication, temporal evidence routing, feature investigation playbooks, tiered cluster investigation, classification feedback, and standalone knowledge database (`knowledge/`).

Five-stage pipeline:
0. **Environment Oracle** (inside gather.py) — Feature-aware dependency health & knowledge database (`cluster_oracle`)
1. **gather.py** — Extracts test data from Jenkins (builds `core-data.json` with cluster landscape, backend API probes, and feature grounding; persists `cluster.kubeconfig` for Stage 2)
1.5. **Cluster Diagnostic** (AI agent) — Comprehensive 6-phase cluster investigation producing `cluster-diagnosis.json` with subsystem health, classification guidance, and dependency chain verification
2. **AI Analysis** — 12-layer diagnostic investigation: groups tests by shared signals, traces root cause through infrastructure layers (Compute→UI), classifies based on WHO caused breakage. Per-group investigation agents for deeper analysis. Produces `analysis-results.json` with `root_cause_layer` per test.
3. **report.py** — Generates `Detailed-Analysis.md` + `analysis-report.html` from analysis results

See `apps/z-stream-analysis/CLAUDE.md` for schema requirements, classification guide, and MCP tool reference.

### ACM Hub Health Agent (`apps/acm-hub-health/`) — Active

AI-powered diagnostic and remediation agent for ACM hub clusters. Uses Claude Code with embedded ACM domain knowledge to perform health checks at any depth -- from quick sanity checks to deep component-level investigations. Natural language driven, no dependencies beyond `oc` + `claude`. Diagnosis is read-only; cluster fixes are executed only after presenting a structured remediation plan and getting explicit user approval. Includes structured knowledge database (`knowledge/`) with baseline, dependency chains (8 cascade paths with layer annotations), 12-layer diagnostic model (vertical root cause tracing), webhooks, certificates, addon catalog, and 13 diagnostic traps. Phase 3 uses layer-organized health checks (foundational layers first, then component layers). Phase 5 traces both horizontally (dependency chains) and vertically (12 infrastructure layers). Falls back to cluster metadata introspection (8 live metadata sources) and the Neo4j knowledge graph MCP (`neo4j-rhacm`) for dependency analysis when the curated knowledge doesn't cover a component or path. Optional CLI wrapper (`acm-hub`) enables running diagnostics from any terminal without launching an interactive session. Session tracing via Claude Code hooks captures all tool calls, MCP interactions, prompts, and errors to structured JSONL files (`.claude/traces/`) with diagnostic-specific enrichment (oc command parsing, phase inference, mutation detection, session-level aggregate stats).

Usage: `cd apps/acm-hub-health && bash setup.sh && oc login <hub> && claude`

### Claude Test Generator (`apps/claude-test-generator/`) — In Progress

Test plan generation from JIRA tickets. Not currently functional — do not use.

## Running Z-Stream Analysis

Open Claude Code in this repository (root or `apps/z-stream-analysis/`) and ask:

```
Analyze this run: <JENKINS_URL>
```

Claude Code runs each stage with visible progress updates — do NOT delegate the entire pipeline to a single agent. See `apps/z-stream-analysis/CLAUDE.md` "Pipeline Execution UX" section.

### Manual Pipeline (Advanced)

```bash
cd apps/z-stream-analysis/

# Stage 1: Gather data
python -m src.scripts.gather "<JENKINS_URL>"
python -m src.scripts.gather "<JENKINS_URL>" --skip-env    # Skip cluster validation
python -m src.scripts.gather "<JENKINS_URL>" --skip-repo   # Skip repo cloning

# Stage 2: AI Analysis (12-layer diagnostic investigation)
# Read core-data.json + cluster-health.json + cluster-diagnosis.json
# Classify each failure using 12-layer model + MCP tools
# MUST read src/schemas/analysis_results_schema.json before writing analysis-results.json

# Stage 3: Generate reports
python -m src.scripts.report runs/<run_dir>
```

## MCP Servers (`mcp/`)

Run `bash mcp/setup.sh` from repo root. The script prompts you to select which app(s) to configure, clones external MCP servers, and installs dependencies.

| Server | Tools | Source | Purpose |
|--------|-------|--------|---------|
| ACM UI (`mcp/acm-ui-mcp-server/`) | 20 | This repo | ACM Console + kubevirt-plugin source code search via GitHub |
| Jenkins | 7+4 | [upstream](https://github.com/redhat-community-ai-tools/jenkins-mcp) + `mcp/jenkins-acm-tools.py` | Jenkins pipeline API + ACM analysis tools |
| JIRA | 25 | [stolostron/jira-mcp-server](https://github.com/stolostron/jira-mcp-server) | Issue search, creation, management for bug correlation (Jira Cloud) |
| Neo4j RHACM | 2 | [mcp-neo4j-cypher](https://pypi.org/project/mcp-neo4j-cypher/) (PyPI) | Component dependency analysis via Cypher queries (optional) |
| Polarion (`mcp/polarion/`) | 25 | This repo | Polarion test case access (optional) |

External MCPs (JIRA, Jenkins) are cloned at setup time into `mcp/.external/` (gitignored).
This repo only contains our original MCP code: ACM UI, Polarion wrapper, Jenkins ACM tools.

**Jenkins Setup:** Run `bash mcp/setup.sh` and provide your Jenkins username and API token when prompted. Credentials are stored in `mcp/.external/jenkins-mcp/.env` and injected into `.mcp.json` automatically. Requires Red Hat VPN for internal Jenkins access.

**JIRA Cloud Setup:** Run `bash mcp/setup.sh` and provide credentials when prompted, or create `mcp/.external/jira-mcp-server/.env` with your Jira Cloud credentials after setup. Get a token at https://id.atlassian.com/manage-profile/security/api-tokens.

## Directory Structure

```
ai_systems_v2/
├── apps/
│   ├── acm-hub-health/        # Active — hub health diagnostic agent
│   ├── z-stream-analysis/     # Active — pipeline failure analysis
│   └── claude-test-generator/ # In progress — not functional
├── mcp/
│   ├── setup.sh               # Interactive setup (clones external MCPs, creates venvs)
│   ├── acm-ui-mcp-server/     # Our code: ACM Console source search
│   ├── polarion/              # Our code: Polarion wrapper
│   ├── jenkins-acm-tools.py   # Our code: ACM-specific Jenkins analysis tools
│   └── .external/             # Cloned at setup time (gitignored)
├── CLAUDE.md                  # This file — Claude Code agent instructions
└── README.md                  # User-facing setup and onboarding guide
```

## Tests

```bash
# Z-stream analysis tests (from app directory)
cd apps/z-stream-analysis/

# Fast — unit + regression (719 tests, no external deps):
python -m pytest tests/unit/ tests/regression/ -q

# Full suite (765+ tests, requires Jenkins VPN for integration):
python -m pytest tests/ -q --timeout=300
```
