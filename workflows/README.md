# Workflows

Workflows are **user-triggered or scheduled** multi-phase processes. The user knows the workflow exists and invokes it by name (e.g., "analyze this Jenkins run"), or a slash command triggers it.

**Key trait:** The human (or scheduler) initiates. The agent follows the defined phases in order.

> Compare with [Solutions](../solutions/README.md): solutions are **agent-discovered** -- the agent searches `solutions/` when it encounters a specific problem during work and needs a known fix.
> Compare with [Skills](../.claude/skills/README.md): skills are atomic, step-by-step checklists called by workflows or on demand.

| Workflow | Description | Trigger |
|----------|-------------|---------|
| [z-stream-analysis](z-stream-analysis.md) | Analyze Jenkins pipeline failures with 5-stage classification pipeline | `/analyze`, `/gather`, `/quick` or natural language |
| [test-case-generation](test-case-generation.md) | Generate Polarion-ready test cases from JIRA tickets via 6-phase subagent pipeline | `/generate`, `/review`, `/batch` |
| [hub-health-check](hub-health-check.md) | Diagnose ACM hub cluster health using 6-phase diagnostic methodology | `/health-check`, `/deep`, `/sanity`, `/investigate` |
| [pre-push](pre-push.md) | Quality gate before pushing code (tests, lint, credentials, forbidden files) | `/pre-push` |
| [knowledge-sweep](knowledge-sweep.md) | Investigate ACM subsystems and update the shared knowledge database | On demand via `investigate-and-learn` skill |

## Org-level workflows (inherited)

These workflows are defined at the org level in [stolostron/agentic-sdlc](https://github.com/stolostron/agentic-sdlc) and apply to this repo:

| Workflow | When to use | Reference |
|----------|-------------|-----------|
| CVE & dependency updates | Scheduled or on-demand security audit | [agentic-sdlc/workflows/cve-updates.md](https://github.com/stolostron/agentic-sdlc/blob/main/workflows/cve-updates.md) |
| SR&ED filing | Annual tax credit reporting cycle | [agentic-sdlc/workflows/sred.md](https://github.com/stolostron/agentic-sdlc/blob/main/workflows/sred.md) |
| Coding process | New feature, bug fix, or refactor | [agentic-sdlc/workflows/coding.md](https://github.com/stolostron/agentic-sdlc/blob/main/workflows/coding.md) |

## Adding a New Workflow

1. Create `workflows/<workflow-name>.md` with trigger, phases, and references
2. Update the table above
3. Open a PR
