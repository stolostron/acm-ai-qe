<div align="center">

# AI Systems Suite

**AI-powered quality engineering tools for ACM, built on Claude Code.**


</div>

---

## What's Inside

| App | What It Does | Try It |
|-----|-------------|--------|
| **[Hub Health](apps/acm-hub-health/)** | Diagnose ACM hub clusters in natural language. Finds root causes across 12 infrastructure layers with 59 knowledge files backing every finding. | `/health-check` |
| **[Z-Stream Analysis](apps/z-stream-analysis/)** | Classify Jenkins pipeline failures as product bug, automation bug, or infrastructure. 5-stage pipeline with per-test evidence chains. | `/analyze <URL>` |
| **[Test Case Generator](apps/test-case-generator/)** | Generate Polarion-ready test cases from JIRA tickets. Investigates the story, discovers UI selectors, writes the test case, reviews it for quality. | `/generate ACM-XXXXX` |

## Get Started

```bash
git clone <repo-url> && cd ai_systems_v2
claude
```

```
/onboard
```

That's it. The onboarding skill detects your environment, walks you through MCP server setup and credentials, and gets you ready to use any app.

> [!TIP]
> `/onboard` is idempotent -- run it again anytime to check what's configured and what's missing.

## Usage at a Glance

<details>
<summary><b>Hub Health</b> -- diagnose an ACM hub cluster</summary>

```bash
cd apps/acm-hub-health
oc login https://api.my-hub.example.com:6443
claude
```

```
/sanity                    # 30-second pulse check
/health-check              # Standard diagnostic
/deep                      # Full 6-phase audit
/investigate search        # Deep dive into a subsystem
```

</details>

<details>
<summary><b>Z-Stream Analysis</b> -- classify pipeline failures</summary>

```bash
cd apps/z-stream-analysis
claude
```

```
/analyze https://jenkins.example.com/job/pipeline/123/
/quick https://jenkins.example.com/job/pipeline/123/    # skip cluster diagnostic
/gather https://jenkins.example.com/job/pipeline/123/   # data collection only
```

</details>

<details>
<summary><b>Test Case Generator</b> -- create Polarion test cases</summary>

```bash
cd apps/test-case-generator
claude
```

```
/generate ACM-30459
/generate ACM-30459 --version 2.17 --area governance
/batch ACM-30459,ACM-30460,ACM-30461
/review runs/ACM-30459/.../test-case.md
```

</details>

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/getting-started)
- Python 3.10+
- GitHub CLI ([`gh`](https://cli.github.com/))

> [!NOTE]
> Some apps need additional tools (`oc`, `jq`, `podman`, Node.js). The `/onboard` skill checks for everything and tells you exactly what's missing.

## How It Works

Each app combines **deterministic Python scripts** (data gathering, report generation) with **AI agents** (investigation, classification, test writing) orchestrated by Claude Code. Agents access external systems through [MCP servers](https://modelcontextprotocol.io/) -- JIRA, Jenkins, Polarion, ACM cluster APIs, and a Neo4j knowledge graph.

```
You ──> Claude Code ──> Slash Command ──> Pipeline
                            │
                   ┌────────┼────────┐
                   v        v        v
              Python     AI Agent   MCP Servers
              Scripts    (Claude)   (JIRA, Jenkins,
                                    Polarion, oc, ...)
```

## Project Layout

```
ai_systems_v2/
├── apps/
│   ├── acm-hub-health/        # Cluster diagnostic agent
│   ├── z-stream-analysis/     # Pipeline failure classifier
│   └── test-case-generator/   # JIRA-to-Polarion test cases
├── mcp/                       # MCP server code + setup
│   ├── setup.sh               # Automated MCP setup (also used by /onboard)
│   ├── verify.py              # Standalone health checker (run anytime)
│   ├── acm-ui-mcp-server/     # ACM Console source search
│   └── polarion/              # Polarion test case access
├── .claude/                   # Claude Code configuration
│   ├── commands/pre-push.md   # /pre-push quality gate
│   ├── skills/onboard/        # /onboard interactive setup
│   └── statusline.sh          # Status line (model, branch, context %)
├── AGENTS.md                  # Agent reference for external AI tools
├── CLAUDE.md                  # Claude Code instructions
└── README.md                  # You are here
```

## Contributing

```bash
cd apps/z-stream-analysis
python -m pytest tests/unit/ tests/regression/ -q    # 686 tests, no external deps
```

See each app's `CLAUDE.md` for architecture details and development conventions.
