# Test Case Generation

Generate Polarion-ready test cases from JIRA tickets via a 6-phase subagent pipeline.

## Trigger

- `/generate <JIRA_ID>` -- full pipeline (6 phases with quality review gate)
- `/review <run_dir>` -- quality review only on existing output
- `/batch <JIRA_ID_1> <JIRA_ID_2> ...` -- multi-ticket batch generation

## Prerequisites

- MCP servers configured (JIRA, ACM Source, Polarion, Playwright -- run `/onboard`)
- For live validation: `oc login` to ACM hub + browser MCP available

## Phases

1. **Phase 0** -- JIRA intake and context gathering
2. **Phase 1** -- Feature investigation (6 specialized agents run in parallel: feature-investigator, code-change-analyzer, ui-discovery, live-validator, test-case-generator, quality-reviewer)
3. **Phase 2** -- Analysis synthesis and gap identification
4. **Phase 3** -- Test case writing (Polarion HTML format)
5. **Phase 4** -- Quality review gate (mandatory -- blocks pipeline if quality score < threshold)
6. **Phase 5** -- Output finalization and artifact packaging

## Output

Run artifacts are saved to `runs/test-case-generator/<JIRA_ID>/`. Includes 9 expected files (artifact completeness check in `report.py`).

## References

- App: [`apps/test-case-generator/CLAUDE.md`](../apps/test-case-generator/CLAUDE.md)
- Agents: `apps/test-case-generator/.claude/agents/` (6 agents)
- Skills: `acm-test-case-generator`, `acm-qe-code-analyzer`, `acm-test-case-writer`, `acm-test-case-reviewer`
- Docs: [`docs/test-case-generator/`](../docs/test-case-generator/)
