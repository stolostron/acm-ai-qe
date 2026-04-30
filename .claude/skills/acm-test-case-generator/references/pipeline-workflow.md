# Pipeline Workflow Reference

## Phase Summary

| Phase | Action | Output | Skills Used |
|-------|--------|--------|-------------|
| 0 | Determine inputs | JIRA ID, version, area, PR, cluster URL | None |
| 1 | Gather data (deterministic) | gather-output.json, pr-diff.txt | scripts/gather.py |
| 2 | Investigate JIRA story | Story, ACs, comments, linked tickets, coverage | acm-jira-client, acm-polarion-client, acm-neo4j-explorer |
| 3 | Analyze PR code changes | Components, UI elements, filtering, field orders | acm-code-analyzer, acm-ui-source, acm-knowledge-base |
| 4 | Discover UI elements | Routes, translations, selectors, entry point | acm-ui-source |
| 5 | Synthesize | Merged context, test plan, conflict resolutions | acm-knowledge-base |
| 6 | Live validation (optional) | Confirmed behavior, discrepancies | acm-cluster-health, browser/oc |
| 7 | Write test case | test-case.md | acm-test-case-writer |
| 8 | Quality review (mandatory) | PASS/NEEDS_FIXES | acm-test-case-reviewer, scripts/review_enforcement.py |
| 9 | Generate reports (deterministic) | HTML, validation, summary | scripts/report.py |

## Deterministic vs AI Steps

**Deterministic (Python scripts):**
- Phase 1: gather.py (gh CLI, file operations)
- Phase 8: review_enforcement.py (parse reviewer output, count MCP verifications)
- Phase 9: report.py (convention validation, HTML generation)

**AI (Claude follows skill instructions):**
- Phases 2-7: investigation, analysis, discovery, synthesis, validation, writing
- Phase 8: quality review (AI does the review, Python enforces the output)
