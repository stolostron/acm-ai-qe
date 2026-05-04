# Phase Gate Enforcement

## Gate Rules

1. A phase CANNOT be marked complete without executing it.
2. The Quality Review phase is a HARD STOP. If the review returns NEEDS_FIXES, escalate through 3 tiers: targeted MCP re-investigation, focused retry with evidence, then placeholder and proceed. Never retry with the same context.
3. Never skip Live Validation when a cluster URL was provided. If the cluster is unreachable, log why.
4. Test case writing MUST complete before quality review. Write first, then review.

## Phase Progress Indicators

Print a progress line before each phase:
```
[Phase 0] Determining area and inputs...
[Phase 1] Gathering data + investigating JIRA story...
[Phase 2] Analyzing PR code changes...
[Phase 3] Discovering UI elements...
[Phase 4] Synthesizing investigation results...
[Phase 5] Running live validation... (or: Skipping -- no cluster URL)
[Phase 6] Writing test case...
[Phase 7] Running quality review...
[Phase 8] Generating reports...
```

## Stop Checkpoints

- After Phase 4: "Investigation complete. [N] test scenarios identified."
- After Phase 6: "Test case written: [filename] ([N] steps)."
- After Phase 7: "Quality review PASSED." (or "Quality review: N steps flagged for manual verification.")
