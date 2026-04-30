# Phase Gate Enforcement

## Gate Rules

1. A phase CANNOT be marked complete without executing it.
2. The Quality Review phase is a HARD STOP. If the review returns NEEDS_FIXES, fix the issues and re-review. Loop until pass or max 3 iterations.
3. Never skip Live Validation when a cluster URL was provided. If the cluster is unreachable, log why.
4. Test case writing MUST complete before quality review. Write first, then review.

## Phase Progress Indicators

Print a progress line before each phase:
```
[Phase 0] Determining area and inputs...
[Phase 1] Gathering pipeline data...
[Phase 2] Investigating JIRA story...
[Phase 3] Analyzing PR code changes...
[Phase 4] Discovering UI elements...
[Phase 5] Synthesizing investigation results...
[Phase 6] Running live validation... (or: Skipping -- no cluster URL)
[Phase 7] Writing test case...
[Phase 8] Running quality review...
[Phase 9] Generating reports...
```

## Stop Checkpoints

- After Phase 5: "Investigation complete. [N] test scenarios identified."
- After Phase 7: "Test case written: [filename] ([N] steps)."
- After Phase 8 pass: "Quality review PASSED."
