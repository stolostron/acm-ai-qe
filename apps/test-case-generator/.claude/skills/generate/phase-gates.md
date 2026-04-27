# Phase Gate Enforcement & Pipeline Execution UX

Mandatory phase tracking, gate rules, and execution UX requirements for the generate pipeline. These are non-negotiable.

## Phase Tracking

Print a phase tracker line before each phase:

```
[Phase 0] Determining area and inputs...
[Phase 1] Launching 3 parallel investigation agents...
[Phase 2] Synthesizing investigation results...
[Phase 3] Running live validation...        (or: Skipping live validation.)
[Phase 4] Writing test case...
[Phase 4.5] Running quality review...
[Stage 3] Generating reports...
```

## Gate Rules

1. **A phase CANNOT be marked complete without executing it.**
2. **Phase 4.5 is a HARD STOP.** Launch the quality-reviewer agent. If it returns NEEDS_FIXES, fix the issues in the test case and re-run the reviewer. Loop until all blocking issues are resolved. Do NOT proceed to Stage 3 before this passes.
3. **Never skip Phase 3** when a `--cluster-url` was provided. If the cluster is unreachable, log why and note it (don't silently skip).
4. **Phase 4 MUST complete before Phase 4.5.** Write the document first, then review it.

## STOP Checkpoints

Print these to the terminal at each checkpoint:

- **After Phase 2:** `"Investigation complete. [N] test scenarios identified. Starting [live validation | test case writing]."`
- **After Phase 4:** `"Test case written: [filename] ([N] steps, [complexity]). Running quality review."`
- **After Phase 4.5 pass:** `"Quality review PASSED. Generating reports."`

## Pipeline Execution UX

When generating a test case, do NOT delegate the entire pipeline to a single agent. The user must see phase-by-phase progress in their terminal. Run each phase yourself in the main conversation with visible status updates.

Required behavior:

1. **Phase 0 + Stage 1** -- Ask missing questions, then run `gather.py`. Show what was collected.
2. **Phase 1** -- Launch 3 investigation agents in parallel. Show what each discovered.
3. **Phase 2** -- Synthesize all investigation outputs into a `SYNTHESIZED CONTEXT` block. Show the plan. If agents disagree: trust UI Discovery for UI elements, Feature Investigator for requirements, Code Change Analyzer for what changed.
4. **Phase 3** -- Run live validation if applicable. Show results or explain why skipped.
5. **Phase 4** -- Launch test-case-generator agent. Show what was produced.
6. **Phase 4.5** -- Launch quality-reviewer agent. Show verdict. Fix and re-run if needed.
7. **Stage 3** -- Run `report.py`. Show summary and output files.
