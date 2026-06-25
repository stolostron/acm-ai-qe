# AI Systems Suite

Multi-app repository for ACM quality engineering tools, built on Claude Code.

## Applications

### Z-Stream Analysis (`apps/z-stream-analysis/`) — Active

Jenkins pipeline failure analysis with 7 classification types (PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, FLAKY, NO_BUG, MIXED, UNKNOWN). Five-stage pipeline: Environment Oracle → gather.py → Cluster Diagnostic (AI agent) → AI Analysis (12-layer investigation) → report.py. 3 slash commands (`/analyze`, `/gather`, `/quick`), 4 agents, standalone knowledge database. See `apps/z-stream-analysis/CLAUDE.md` for details.

### ACM Hub Health Agent (`apps/acm-hub-health/`) — Active

AI-powered diagnostic and remediation agent for ACM hub clusters. Read-only diagnosis with 12-layer model, 14 diagnostic traps, dependency chain tracing; cluster fixes only after explicit user approval. Uses `oc` + Claude Code with embedded knowledge database, ACM Search MCP for fleet queries, Neo4j for dependency analysis. Optional CLI wrapper (`acm-hub`). Usage: `oc login <hub> && claude`

### Test Case Generator (`apps/test-case-generator/`) — Active

Generates Polarion-ready test cases for ACM Console features from JIRA tickets. 9-phase subagent pipeline (Phases 0-8) with mandatory quality review gate. 7 specialized agents, 7 MCP integrations, 9 console areas supported. 3 skills: `/generate` (full pipeline), `/review` (quality review), `/batch` (multi-ticket). Portable skill pack with standalone scripts for repo-root execution.

## Skills (`.claude/skills/`)

20 portable skills in a flat layout under `.claude/skills/`. Each skill has a `SKILL.md` entry point with YAML frontmatter, kebab-case folder name, and stdlib-only scripts. Shared skills expose raw capabilities; orchestrators compose them into multi-phase pipelines.

**By domain:**

| Domain | Skills | Key orchestrators |
|--------|--------|-------------------|
| Shared | `acm-knowledge-base`, `acm-cluster-health`, `acm-jenkins-client` | — (tools, no workflow) |
| Test Case Gen | `acm-test-case-generator`, `acm-qe-code-analyzer`, `acm-test-case-writer`, `acm-test-case-reviewer` | `/generate`, `/review`, `/batch` |
| Test Case Validation | `acm-test-case-validator` | `/acm-test-case-validator` |
| Hub Health | `acm-hub-health-check`, `acm-cluster-remediation`, `acm-knowledge-learner` | `/acm-hub-health-check` |
| Z-Stream | `acm-z-stream-analyzer`, `acm-failure-classifier`, `acm-cluster-investigator`, `acm-data-enricher` | `/analyze`, `/gather`, `/quick` |
| Bug Investigation | `acm-bug-hunter`, `acm-bug-fix-verifier` | `/acm-bug-hunter` |
| Utility | `onboard`, `grill-me`, `youtube-digest` | `/onboard` |

**Conventions:** SKILL.md is the single entry point (no README). Progressive disclosure: frontmatter (~100 tokens) → body (<500 lines) → `references/` (on-demand). Orchestrators delegate to sibling skills via relative paths. See `docs/skill-architecture.md` for the full inventory, blast radius map, and `docs/skill-authoring-guide.md` for authoring standards.

## Getting Started

New to this repo? Run `/onboard` for interactive setup -- it detects your environment, explains the apps, and guides MCP server configuration with credential setup. It creates a root `.mcp.json` (union of all app configs) so portable skills have full MCP access from the repo root. Works for both new team members and fresh AI agent sessions.

For manual setup: launch `claude` from the repo root and run `/onboard`.

### Claude Code permissions (`settings.local.json`)

`settings.local.json` is **not** in git (machine-specific allow/deny lists). It is listed in `.gitignore`.

After cloning, create yours from the template:

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

Edit `permissions.allow` / `permissions.deny` as needed. The example uses **repo-relative** Bash paths only (no home-directory absolutes). `/pre-push` and onboarding remind you not to commit this file.

## Org-Level Workflows (Inherited)

This repo participates in org-wide workflows defined in [stolostron/agentic-sdlc](https://github.com/stolostron/agentic-sdlc):

| Workflow | When to use | Reference |
|----------|-------------|-----------|
| CVE & dependency updates | Scheduled or on-demand security audit | [agentic-sdlc/workflows/cve-updates.md](https://github.com/stolostron/agentic-sdlc/blob/main/workflows/cve-updates.md) |
| SR&ED filing | Annual tax credit reporting cycle | [agentic-sdlc/workflows/sred.md](https://github.com/stolostron/agentic-sdlc/blob/main/workflows/sred.md) |
| Coding process | New feature, bug fix, or refactor | [agentic-sdlc/workflows/coding.md](https://github.com/stolostron/agentic-sdlc/blob/main/workflows/coding.md) |

Squad-specific workflows are documented in [`workflows/`](workflows/README.md). Problem-specific SOPs are in [`solutions/`](solutions/README.md).

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

## Git Discipline

Commit messages use conventional format: `type: concise description`

**Types**: `feat` (new capability), `fix` (bug fix), `docs` (documentation only), `chore` (maintenance, config), `refactor` (no behavior change), `test` (test-only changes).

**Rules:**
- Subject line under 72 characters, lowercase after the type prefix
- Body (optional) explains WHY, not what -- the diff shows the what
- Do not amend published commits on shared branches
- Before pushing, run `/pre-push` to verify tests pass, no credentials are staged, and no forbidden files are included

## Running Z-Stream Analysis

```
/analyze <JENKINS_URL>          # Full pipeline (5 stages)
/gather <JENKINS_URL>           # Stage 1 only
/quick <JENKINS_URL>            # Skip cluster diagnostic
```

Or natural language: `Analyze this run: <JENKINS_URL>`. Claude Code runs each stage with visible progress updates — do NOT delegate the entire pipeline to a single agent. For manual pipeline commands, see `apps/z-stream-analysis/CLAUDE.md`.

## MCP Servers (`mcp/`)

From the repo root, launch `claude` and run `/onboard`. It detects your environment, prompts for credentials, configures MCP servers, generates `.mcp.json` for each app, and creates a root `.mcp.json` (union of all app configs) so portable skills have full MCP access.

| Server | Tools | Source | Purpose |
|--------|-------|--------|---------|
| ACM Source (`mcp/acm-source-mcp-server/`) | 18 | This repo | ACM Console + kubevirt-plugin source code search via GitHub |
| Jenkins | 7+4 | [upstream](https://github.com/redhat-community-ai-tools/jenkins-mcp) + `mcp/jenkins-acm-tools.py` | Jenkins pipeline API + ACM analysis tools |
| JIRA | 29 | [atifshafi/jira-mcp-server@feat/redhat-fields](https://github.com/atifshafi/jira-mcp-server/tree/feat/redhat-fields) | Issue search, creation, attachments, list/download attachments, inline comment images (Jira Cloud; [PR #24](https://github.com/stolostron/jira-mcp-server/pull/24)) |
| Neo4j RHACM | 2 | [mcp-neo4j-cypher](https://pypi.org/project/mcp-neo4j-cypher/) (PyPI) | Component dependency analysis via Cypher queries |
| ACM Search | 5 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | Fleet-wide resource queries via search-postgres (spoke-side visibility) |
| Polarion (`mcp/polarion/`) | 25 | This repo | Polarion test case management |
| ACM Kubectl | 3 | [stolostron/acm-mcp-server](https://github.com/stolostron/acm-mcp-server) | Multicluster kubectl for hub and spoke clusters |
| Playwright | 24 | [@playwright/mcp](https://www.npmjs.com/package/@anthropic-ai/playwright-mcp) (npm) | Browser automation for live UI validation |

External MCPs (JIRA, Jenkins, Knowledge Graph, ACM Search, ACM Kubectl) are cloned at setup time into `mcp/.external/` (gitignored).
This repo only contains our original MCP code: ACM Source, Polarion wrapper, Jenkins ACM tools.

**Jenkins Setup:** Run `/onboard` and provide your Jenkins username and API token when prompted. Credentials are stored in `mcp/.external/jenkins-mcp/.env` and injected into `.mcp.json` automatically. Requires Red Hat VPN for internal Jenkins access.

**JIRA Cloud Setup:** Run `/onboard` and provide credentials when prompted, or create `mcp/.external/jira-mcp-server/.env` with your Jira Cloud credentials after setup. Get a token at https://id.atlassian.com/manage-profile/security/api-tokens.

**ACM Search Setup:** Runs as a pod on the ACM hub cluster, accessed via SSE through an OpenShift route. The z-stream analysis pipeline auto-deploys acm-search during Step 4 after cluster login — no manual setup required. For manual deployment or other apps, run `bash mcp/deploy-acm-search.sh` after `oc login`. If acm-search is unavailable, agents fall back to `oc` CLI for direct queries.

## Knowledge Database (`.claude/knowledge/`)

When you discover a verified, durable fact about ACM (architecture, failure pattern, UI behavior, health issue, test automation gotcha), write it directly to the appropriate file in `.claude/knowledge/`. Do NOT use `learned/` as a staging area — it is deprecated.

**Write protocol:**
1. Identify the target file from the directory map (architecture, failures, health, ui, automation, baselines, data-flow)
2. Read the target file first
3. Check for duplicates (semantic — same concept even if different wording)
4. Append to the appropriate section, matching the existing format
5. Only write verified facts (confirmed via live cluster, source code, docs, or JIRA)

**Directory map (key paths):**
- Architecture: `.claude/knowledge/architecture/<subsystem>/architecture.md`
- Failure patterns: `.claude/knowledge/failures/<subsystem>/failure-signatures.md`
- Health issues: `.claude/knowledge/health/<subsystem>/known-issues.md`
- UI behavior: `.claude/knowledge/ui/<area>.md`
- Baselines: `.claude/knowledge/baselines/*.yaml`
- Playwright automation: `.claude/knowledge/automation/playwright/<area>.md`
- Cypress automation: `.claude/knowledge/automation/cypress/<area>.md`

**Do NOT write** ephemeral cluster state, speculative info, duplicates, or personal workflow notes.

## Directory Structure

```
ai_systems_v2/
├── .mcp.json                  # Root MCP config for skills (generated by /onboard, gitignored)
├── apps/
│   ├── acm-hub-health/        # Active — hub health diagnostic agent
│   ├── z-stream-analysis/     # Active — pipeline failure analysis
│   └── test-case-generator/   # Active — Polarion-ready test case generation from JIRA tickets
├── mcp/
│   ├── setup.sh               # Interactive setup (clones external MCPs, creates venvs)
│   ├── deploy-acm-search.sh   # Non-interactive ACM Search MCP deploy (cluster → .mcp.json)
│   ├── verify.py              # Standalone health checker (run anytime)
│   ├── acm-source-mcp-server/     # Our code: ACM Console source search
│   ├── polarion/              # Our code: Polarion wrapper
│   ├── jenkins-acm-tools.py   # Our code: ACM-specific Jenkins analysis tools
│   └── .external/             # Cloned at setup time (gitignored)
├── .claude/
│   ├── skills/                # 20 portable skills (usable from repo root via root .mcp.json)
│   ├── knowledge/             # Shared knowledge database for skills (3 domains: tc-gen, z-stream, hub-health)
│   ├── commands/pre-push.md   # /pre-push quality gate slash command
│   ├── statusline.sh          # Status line script (model, branch, context %)
│   └── settings.json          # Root-level Claude Code settings
├── docs/
│   ├── skill-architecture.md  # Full skill inventory, blast radius map, contributing guide
│   └── skill-authoring-guide.md # SKILL.md structure, progressive disclosure, quality checklist
├── workflows/                 # Named multi-phase processes (user/cron triggered)
├── solutions/                 # Battle-tested SOPs for known problems (agent self-help)
├── repos/
│   └── repos.yaml             # QE repo registry (console, e2e, MCP source repos)
├── team-members/
│   └── team-members.md        # Console QE squad roster
├── AGENTS.md                  # Agent reference (tool-agnostic, for external AI tools)
├── CLAUDE.md                  # This file — Claude Code agent instructions
├── context.md                 # Ubiquitous language glossary + repo design summary — read this first
└── README.md                  # User-facing setup and onboarding guide
```

## Tests

```bash
# Z-stream analysis (from app directory)
cd apps/z-stream-analysis/
python -m pytest tests/unit/ tests/regression/ -q    # 759 tests, no external deps
python -m pytest tests/ -q --timeout=300             # 804 tests (requires Jenkins VPN)

# Hub health (from app directory)
cd apps/acm-hub-health/
python -m pytest tests/regression/ -q                # 22 tests, no external deps

# Test case generator (from app directory)
cd apps/test-case-generator/
python -m pytest tests/unit/ tests/integration/ -q   # 119 tests, no external deps

# Portable skill eval harness (from repo root)
python .claude/skills/acm-test-case-generator/evals/run_evals.py
```
