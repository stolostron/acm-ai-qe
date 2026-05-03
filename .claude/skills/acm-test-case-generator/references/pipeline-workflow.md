# Pipeline Workflow Reference

## Execution Model

Phases 2-8 run as isolated **subagents** via the Agent tool. Each subagent gets fresh context, reads its inputs from disk, writes structured output, and terminates. The orchestrator (SKILL.md) is thin routing logic that spawns subagents and verifies outputs -- it never accumulates MCP responses.

Agent instruction files: `references/agents/` directory (7 files, one per subagented phase).

## Phase Summary

| Phase | Action | Execution | Output | Agent File |
|-------|--------|-----------|--------|------------|
| 0 | Determine inputs | Inline | JIRA ID, version, area, PR, cluster URL | -- |
| 1 | Gather data | Inline (script) | gather-output.json, pr-diff.txt | -- |
| 2 | Investigate JIRA story | Subagent | phase2-jira.json | jira-investigator.md |
| 3 | Analyze PR code changes | Subagent | phase3-code.json | code-analyzer.md |
| 4 | Discover UI elements | Subagent | phase4-ui.json | ui-discoverer.md |
| 5 | Synthesize | Subagent | synthesized-context.md | synthesizer.md |
| 6 | Live validation (optional) | Subagent | phase6-live-validation.md | live-validator.md |
| 7 | Write test case | Subagent | test-case.md | test-case-writer.md |
| 8 | Quality review (mandatory) | Subagent + inline escalation | PASS/NEEDS_FIXES | quality-reviewer.md |
| 9 | Generate reports | Inline (script) | HTML, validation, summary | -- |

## Deterministic vs AI Steps

**Deterministic (Python scripts, inline):**
- Phase 1: gather.py (gh CLI, file operations)
- Phase 8: review_enforcement.py (parse reviewer output, count MCP verifications)
- Phase 9: report.py (convention validation, HTML generation)

**AI (subagents with isolated context):**
- Phases 2-7: each runs in its own subagent, writes structured JSON/markdown to disk
- Phase 8: quality reviewer subagent + orchestrator-managed 3-tier escalation

## Context Flow

```
Orchestrator context: ~10-15KB peak (inputs + progress tracking)
  ├── Phase 2 subagent: ~30-50KB → writes phase2-jira.json → terminates
  ├── Phase 3 subagent: ~30-60KB → writes phase3-code.json → terminates
  ├── Phase 4 subagent: ~20-40KB → writes phase4-ui.json → terminates
  ├── Phase 5 subagent: ~25-35KB → reads 3 JSONs → writes synthesized-context.md → terminates
  ├── Phase 6 subagent: ~15-30KB → writes phase6-live-validation.md → terminates
  ├── Phase 7 subagent: ~15-25KB → writes test-case.md → terminates
  └── Phase 8 subagent: ~10-20KB → writes review output → terminates
```

Structured files (JSON, markdown) are genuine cross-context bridges: written by one subagent, read by the next. The orchestrator never loads them.
