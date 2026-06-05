# Run Directory Structure

Each run: `runs/test-case-generator/<JIRA_ID>/<JIRA_ID>-<YYYY-MM-DDTHH-MM-SS>/` (e.g., `runs/test-case-generator/ACM-32280/ACM-32280-2026-05-04T15-09-19/`).

The directory is created by `gather.py` -- do NOT pre-create it. The orchestrator captures the path from gather.py's stdout (last line) via the data-gatherer agent.

```
gather-output.json        -- Phase 1: PR metadata, conventions
pr-diff.txt               -- Phase 1: full PR diff
phase1-jira.json          -- Phase 1: JIRA findings
phase2-code.json          -- Phase 2: code analysis
phase3-ui.json            -- Phase 3: UI elements
synthesized-context.md    -- Phase 4: merged test plan
phase5-live-validation.md -- Phase 5: live results (optional)
test-case.md              -- Phase 6: primary deliverable
analysis-results.json     -- Phase 6: investigation metadata
phase7-review.md          -- Phase 7: quality review output
test-case-description.html -- Phase 8: Polarion description HTML
test-case-setup.html      -- Phase 8: Polarion setup HTML
test-case-steps.html      -- Phase 8: Polarion steps HTML
validation-warnings.json  -- Retry Protocol: present only if validation failed after 3 attempts
review-results.json       -- Phase 8: structural validation
SUMMARY.txt               -- Phase 8: human-readable summary
pipeline.log.jsonl        -- All phases: telemetry log
```
