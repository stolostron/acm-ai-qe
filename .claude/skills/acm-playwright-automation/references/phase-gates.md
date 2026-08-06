# Phase Gate Reference

Mandatory phase tracking and gate rules for the Playwright automation pipeline.

---

## Phase Tracker

On skill start, create a task for each phase using `TaskCreate`. Update status with `TaskUpdate` as work progresses.

| Phase | Task Subject | Gate? |
|-------|-------------|-------|
| 0 | Phase 0: Determine area and read knowledge base | No |
| 1 | Phase 1: Context gathering (3 parallel subagents) | No |
| 2 | Phase 2: Synthesize + coverage map (user approval) | **HARD GATE** |
| 3 | Phase 3: Code generation (Page -> Service -> Test) | No |
| 3.5 | Phase 3.5: Code quality + lint check (must pass) | **HARD GATE** |
| 4 | Phase 4: Local test execution (must pass) | **HARD GATE** |
| 4.5 | Phase 4.5: Failure debugging (if test failed) | Conditional |
| 5 | Phase 5: Polarion coverage verification | **HARD GATE** |

---

## Hard Gate Rules

### Phase 2: User Approval

- Present the Polarion Coverage Map to the user
- Display: "Coverage map ready. Awaiting your approval before code generation."
- **DO NOT proceed to Phase 3 until the user explicitly approves**
- If the user requests changes, update the coverage map and re-present

### Phase 3.5: Code Quality + Lint

- Launch the code quality reviewer agent
- Run `npm run lint:check` on the repo
- **ALL anti-pattern checks must pass** (no batch-skipping)
- **ALL dead code checks must include grep evidence**
- If ANY blocking issue is found: fix, then re-run the ENTIRE Phase 3.5
- Display: "Quality review passed. Running local test now."

### Phase 4: Test Execution

- Launch the test runner agent
- **MUST complete before ANY git commit, git push, or Jenkins trigger**
- If user says "push it": respond "The skill requires local test execution first."
- On PASS: proceed to Phase 5
- On FAIL: mark Phase 4 as `pending`, create Phase 4.5, launch failure debugger

### Phase 5: Polarion Coverage Verification

- Re-fetch Polarion test steps via MCP
- Verify EVERY step has a corresponding `test.step()` in the spec
- Check for skipped steps in test output
- Report coverage table
- **Never mark Phase 5 complete until Phase 4 shows a passing test**

---

## Violation Rules

1. A phase CANNOT be marked `completed` without executing it
2. Phase 1 requires ALL THREE subagents to return results
3. Phase 4 MUST complete before ANY git commit
4. Phase 3.5 MUST include `npm run lint:check`
5. On failure in Phase 4, mark as `pending` and launch failure debugger
6. Never mark Phase 5 complete until Phase 4 passes

---

## STOP Checkpoints

Pause and display status at these points:

| After | Display |
|-------|---------|
| Phase 2 | "Coverage map ready. Awaiting your approval before code generation." |
| Phase 3 | "Code generation complete. Starting quality review and lint check." |
| Phase 3.5 | "Quality review passed. Running local test now." |
| Phase 4 (pass) | "Test passed locally. Verifying Polarion coverage." |
| Phase 4 (fail) | "Test failed. Launching failure debugger to diagnose." |

---

## Phase 4.5: Failure Debugging Loop

When Phase 4 fails:

1. Mark Phase 4 as `pending` (NOT completed)
2. Mark Phase 4.5 as `in_progress`
3. Launch failure debugger agent with failure output
4. Apply fix based on diagnosis:
   - `automation_bug`: fix the code, re-run Phase 3.5 then Phase 4
   - `environment_issue`: report to user, STOP
   - `product_bug`: report to user, offer to file JIRA, STOP
5. After fix: re-run Phase 4
6. Maximum 3 debug-fix-retry cycles before escalating to user
