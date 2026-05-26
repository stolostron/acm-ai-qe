# Z-Stream Analysis

Analyze Jenkins pipeline failures with a 5-stage classification pipeline.

## Trigger

- `/analyze <JENKINS_URL>` -- full pipeline (5 stages)
- `/gather <JENKINS_URL>` -- stage 1 only (data extraction)
- `/quick <JENKINS_URL>` -- skip cluster diagnostic (stages 1 + 2 + 3, no 1.5)
- Natural language: "Analyze this run: `<JENKINS_URL>`"

## Prerequisites

- Red Hat VPN (Jenkins access)
- `oc login` to the ACM hub cluster (for Stage 1.5 cluster diagnostic)
- MCP servers configured (run `/onboard` if not done)

## Phases

1. **Stage 1** -- `gather.py` extracts test data from Jenkins, produces `core-data.json`
2. **Post-Stage 1** -- `data-collector` agent enriches `core-data.json` with selector verification, page objects, timeline analysis
3. **Stage 1.5** -- `cluster-diagnostic` agent runs cluster health investigation, produces `cluster-diagnosis.json` (skipped by `/quick`)
4. **Stage 2** -- `analysis` agent performs 12-layer diagnostic investigation, produces `analysis-results.json`
5. **Stage 3** -- `report.py` generates `Detailed-Analysis.md` + HTML report

## Classifications

PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, NO_BUG, MIXED, UNKNOWN, FLAKY

## Output

Run artifacts are saved to `runs/z-stream-analysis/<timestamp>/`.

## References

- App: [`apps/z-stream-analysis/CLAUDE.md`](../apps/z-stream-analysis/CLAUDE.md)
- Agents: `apps/z-stream-analysis/.claude/agents/` (4 agents)
- Commands: `apps/z-stream-analysis/.claude/commands/` (`/analyze`, `/gather`, `/quick`)
- Skills: `acm-z-stream-analyzer`, `acm-failure-classifier`, `acm-cluster-investigator`, `acm-data-enricher`
- Docs: [`docs/z-stream-analysis/`](../docs/z-stream-analysis/)
