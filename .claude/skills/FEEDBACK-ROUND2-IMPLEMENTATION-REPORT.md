# Feedback Round 2: Implementation Report

**Source:** Second NotebookLM audio overview + user corrections
**Date:** 2026-05-02
**Purpose:** Address 3 refined issues with detailed implementation plans for Claude Code

---

## Critical Correction: Context Window Architecture

### I Was Wrong About Context Sharing

In my previous analysis, I stated: "The pipeline runs in ONE context window. Skills execute sequentially in the same Claude conversation."

**This is only partially true.** Here's the actual situation on Claude Code:

1. **Standard skills** (no `context: fork`): Load their SKILL.md body into the CURRENT conversation context. They share the context window with the orchestrator. This is how our skills currently work.

2. **Skills with `context: fork`** (Claude Code feature): Run in an ISOLATED subagent with their OWN context window. They do NOT have access to conversation history. The SKILL.md content becomes the subagent's prompt.

3. **When the orchestrator uses the `Agent()` tool** (which it does for investigation agents): Each spawned agent gets its OWN context window. The parent passes a prompt, the child returns a result. Context does NOT flow automatically.

**Evidence from our ACM-32282 skill run** (terminal logs):
```
3 agents finished (ctrl+o to expand)
 ├ Feature investigator agent · 11 tool uses · 66.1k tokens
 │ ⎿  Done
 ├ Code change analyzer agent · 15 tool uses · 66.0k tokens
 │ ⎿  Done
 └ UI discovery agent · 27 tool uses · 76.6k tokens
   ⎿  Done
```

These ran as separate Agent() calls. Each had ~66-77K tokens of its OWN context. They did NOT share the orchestrator's context. The orchestrator passed them a prompt with the JIRA ID and PR info, they did their work in isolation, and returned their findings as text.

**This means the NotebookLM feedback was MORE right than I initially said.** Context passing IS a real concern because:
- Agent subprocesses get their own context windows
- The orchestrator must serialize investigation results into text to pass between phases
- The synthesis phase must reconstruct relational insights from that serialized text
- Context degradation between phases is a REAL risk, not theoretical

### What Needs to Change

Currently, the orchestrator spawns investigation agents and receives their results as unstructured text. The synthesis template merges that text. This works but is fragile.

**Two-layer approach:**

**Layer 1 (immediate): Structured handoff files.** After each investigation agent completes, write its findings to a structured JSON file in the run directory:
- `phase2-jira-findings.json` -- structured JIRA data (ACs as array, comments as array, linked tickets)
- `phase3-code-analysis.json` -- structured analysis (changed files, field orders, filter conditions as exact code)
- `phase4-ui-discovery.json` -- structured discovery (routes as key-value, translations as key-value, selectors as array)

The synthesis phase reads these JSON files instead of parsing natural language text. This is the "JSON context ledger" the feedback suggested.

**Layer 2 (Claude Code optimization): Use `context: fork` for heavy investigation skills.** Add `context: fork` to investigation skills that benefit from isolated context:
- `acm-code-analyzer` -- needs a clean context to read a large PR diff without interference
- `acm-cluster-investigator` -- needs focused context per test group

This is a Claude Code-specific optimization that doesn't affect portability (other platforms ignore `context: fork`).

---

## Issue 1: Phase 4.5 Quality Loop Deadlock -- Smart Recovery Before Placeholder

### The Problem (refined)

When the quality reviewer flags an issue the LLM can't fix (e.g., a filter prefix it hallucinated because it didn't read the source correctly), retrying 3 times without new information is wasteful. The current behavior:

```
Iteration 1: Reviewer flags "wrong filter prefix" -> Writer retries with same context -> Same error
Iteration 2: Same flag -> Same retry -> Same error  
Iteration 3: Same flag -> Give up -> Show issues to user (pipeline stalls)
```

### The Fix (3-tier escalation)

Instead of blind retry, implement a 3-tier escalation:

**Tier 1: Targeted MCP re-investigation (smart recovery)**

When the reviewer flags a specific factual error (wrong filter prefix, wrong field order, wrong component name), the orchestrator should NOT just ask the writer to "fix it." Instead:

1. Parse the reviewer's BLOCKING issue to identify WHAT is wrong (e.g., "filter prefixes don't match source code")
2. Launch a TARGETED MCP investigation to get the correct answer:
   ```
   get_component_source("frontend/src/routes/Governance/utils/label-utils.ts")
   -> Extract exact filter conditions from the source code
   -> Pass the CORRECT data to the writer
   ```
3. Re-run the writer with the CORRECTED context, not the original (wrong) context

This addresses the root cause: the writer had wrong data, not a wrong writing process.

**Tier 2: Context refresh with compact**

If Tier 1 fails (MCP unavailable, source code doesn't resolve the conflict):
1. Write the current test case state to a file (`test-case-draft.md`)
2. Use `/compact` to summarize the conversation and free context
3. Re-read the draft and the reviewer's specific flags
4. Attempt the fix with refreshed context (the LLM may have been confused by context overload)

**Tier 3: Placeholder and proceed (last resort)**

If Tier 2 also fails (3rd iteration reached with no resolution):
1. Mark the specific failing step(s) with `[MANUAL VERIFICATION REQUIRED: <specific issue>]`
2. Proceed to Phase 9 (report generation) with the rest of the test case intact
3. The summary reports which steps need manual verification and why
4. The 95% that passed review gets output; the 5% gets flagged

**Implementation in `acm-test-case-generator/SKILL.md` Phase 8:**

```markdown
### Phase 8: Quality Review (MANDATORY GATE)

Using the **acm-test-case-reviewer** skill, review the test case.

**Review loop with 3-tier escalation:**

**Iteration 1:** If NEEDS_FIXES:
  - Parse each BLOCKING issue
  - For factual errors (wrong filter logic, wrong field order, wrong component):
    → Tier 1: Launch targeted MCP investigation to get correct data
    → Pass corrected data to writer skill for targeted fix
  - For format errors (missing separator, wrong title pattern):
    → Fix directly (deterministic)
  - Re-run review

**Iteration 2:** If still NEEDS_FIXES:
  - Tier 2: Write draft to file, compact context, re-read with fresh perspective
  - Attempt fix with refreshed context
  - Re-run review

**Iteration 3:** If still NEEDS_FIXES:
  - Tier 3: Mark unresolvable steps with [MANUAL VERIFICATION REQUIRED: <issue>]
  - Proceed to Phase 9 with partially-verified test case
  - Summary reports flagged steps
  - Pipeline does NOT abort

**NEVER** retry with the same context and same instruction. Each retry must bring NEW information or a NEW approach.
```

---

## Issue 2: Live Validation Environment Verification

### The Problem (refined by user feedback)

Live validation (Phase 6) currently navigates to the cluster and checks if features work. But it doesn't verify WHETHER the cluster actually has the code changes being tested. If the PR hasn't been deployed to the test cluster, live validation finds "missing" features and potentially causes the pipeline to drop valid test steps.

### The Fix: Pre-validation Environment Check

**Before ANY live validation, verify the environment has the change:**

**Step 1: Check if the PR's changes are deployed**

```bash
# Get the expected commit SHA from the PR
PR_SHA=$(gh pr view <PR_NUMBER> --repo stolostron/console --json mergeCommit -q '.mergeCommit.oid' 2>/dev/null)

# Get the console image running on the cluster
CONSOLE_IMAGE=$(oc get deploy console-chart-console-v2 -n <mch-ns> -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null)

# Get the MCH version (the build that's deployed)
MCH_VERSION=$(oc get mch -A -o jsonpath='{.items[0].status.currentVersion}' 2>/dev/null)
```

**Step 2: Determine if the change should be present**

Compare the PR merge date against the MCH build date:
- PR merged BEFORE the MCH build -> change SHOULD be in the environment
- PR merged AFTER the MCH build -> change is NOT in the environment yet

For ACM, the build tag encodes the snapshot date. Example: `2.17.0-176` -- the 176 is the nightly build number. Compare against the PR merge timestamp.

**Step 3: Proceed accordingly**

| Scenario | Action |
|---|---|
| Change IS deployed (PR in build) | Proceed with full live validation. Discrepancies are real findings. |
| Change is NOT deployed (PR newer than build) | Skip UI validation for the new feature. Note: "Environment does not contain PR changes (MCH build predates PR merge). Live validation covers only existing features." Backend validation for prerequisites still runs. |
| Cannot determine (no build info) | Proceed with live validation but treat all discrepancies as "environmental -- verify on a cluster with the change deployed." |

**Step 4: When change IS deployed but discrepancy found**

This is the hierarchy you asked about:

1. **Source code is structural truth** (the intended design)
2. **Live cluster is environmental truth** (current state)
3. When they disagree AND the change should be deployed:
   - The discrepancy is significant -- it could be a real bug, misconfiguration, or deployment issue
   - Keep the source-code-based test step (don't drop it)
   - Add a prerequisite note: "Verified: PR is included in MCH build, but feature did not render on live cluster. Possible causes: feature flag disabled, prerequisite not met, or deployment issue. Verify environment configuration."
   - This is MORE than just "trust source code" -- it's flagging a potentially real issue

**Implementation in `acm-test-case-generator/SKILL.md` Phase 6:**

```markdown
### Phase 6: Live Validation (conditional)

If a cluster URL was provided or auto-detected:

**Step 0: Environment verification (MANDATORY before any feature validation)**

Before validating the NEW feature, verify the environment has the change:

1. Get the PR merge date from gather-output.json
2. Get the MCH version: `oc get mch -A -o jsonpath='{.items[0].status.currentVersion}'`
3. Compare: is the PR included in this build?
   - If YES: proceed with full validation, discrepancies are significant
   - If NO: note "Environment does not contain PR changes" and skip
     new-feature UI checks. Validate only prerequisites and existing features.
   - If UNKNOWN: proceed but flag all discrepancies as "environmental -- verify
     on a cluster with the change"

**Arbitration hierarchy (when change IS deployed but discrepancy found):**

1. Source code = structural truth (what the developer built)
2. Live cluster = environmental truth (what's running now)
3. When they disagree:
   - KEEP the source-based test step (do not drop it)
   - ADD prerequisite note explaining the discrepancy
   - If environment has the change but feature doesn't render:
     flag as potential configuration issue, not as "feature doesn't exist"
   - NEVER let a transient cluster state remove a source-code-verified step

**Then proceed with validation using Playwright, acm-search, and oc CLI...**
```

---

## Issue 3: Structured Context Passing Between Investigation Agents

### The Problem (corrected understanding)

Investigation agents (JIRA, code, UI) run as Agent() subprocesses with their OWN context windows. They receive a prompt and return text results. The orchestrator must serialize their findings and pass them to the synthesis phase.

Currently, findings are returned as natural language text and written to `phase2-synthesized-context.md`. Relational insights (e.g., "selector X maps to route Y via component Z") risk degradation when re-parsed by the synthesis logic.

### The Fix: Structured JSON Handoff + Synthesis Contract

**Each investigation agent writes structured JSON to the run directory:**

**Phase 2 JIRA investigation writes `phase2-jira.json`:**
```json
{
  "story": {"key": "ACM-30459", "summary": "...", "status": "Done"},
  "acceptance_criteria": [
    {"id": 1, "text": "Labels field appears after API version", "verified_in_code": null}
  ],
  "comments_with_decisions": [
    {"author": "dev1", "key_insight": "Changed approach to filter system labels", "date": "2026-03-01"}
  ],
  "linked_tickets": {"qe": "ACM-30525", "bugs": ["ACM-33072"], "siblings": ["ACM-30457"]},
  "pr_references": [{"number": 5790, "repo": "stolostron/console", "merged": "2026-03-11"}],
  "existing_polarion": []
}
```

**Phase 3 code analysis writes `phase3-code.json`:**
```json
{
  "primary_file": "PolicyTemplateDetails.tsx",
  "field_order": ["Name", "Engine", "Cluster", "Kind", "API version", "Labels"],
  "filter_function": {
    "name": "isUserDefinedPolicyLabel",
    "file": "label-utils.ts",
    "conditions": [
      {"type": "exact_match", "key": "cluster-name", "result": false},
      {"type": "exact_match", "key": "cluster-namespace", "result": false},
      {"type": "prefix_match", "prefix": "policy.open-cluster-management.io/", "result": false}
    ]
  },
  "empty_state": {"behavior": "shows_dash", "code": "Object.keys(labels).length > 0 ? <AcmLabels/> : '-'"},
  "component_used": "AcmLabels",
  "translations": {"table.labels": "Labels"}
}
```

**Phase 4 UI discovery writes `phase4-ui.json`:**
```json
{
  "routes": {"policyTemplateDetails": "/multicloud/governance/policies/details/:namespace/:name/template/:clusterName/:apiGroup?/:apiVersion/:kind/:templateName"},
  "translations_verified": {"table.labels": "Labels", "GPU count": "GPU count"},
  "selectors": ["#template-details-section", ".pf-v6-c-label"],
  "entry_point": "Governance > Policies > {policy} > Results > {cluster}"
}
```

**Phase 5 synthesis reads these JSON files** instead of parsing markdown text. Filter conditions are exact code extracts, not LLM paraphrases. Field order is a deterministic array, not a sentence to parse.

**Implementation changes:**

1. Update orchestrator Phase 2-4 instructions to write JSON files to run directory
2. Update orchestrator Phase 5 to read JSON files instead of parsing synthesized markdown
3. Keep the markdown synthesis as an ADDITIONAL human-readable artifact (audit trail), but the JSON files are the authoritative state

The markdown synthesis (`phase2-synthesized-context.md`) still gets written for human readability, but the JSON files are what the writer actually consumes.

---

## Implementation Summary

| Issue | What to Change | Files Affected | Priority |
|---|---|---|---|
| Context architecture correction | Document that Agent() spawns have separate contexts; add structured JSON handoff | `acm-test-case-generator/SKILL.md` Phases 2-5, `references/synthesis-template.md` | High |
| Phase 4.5 smart recovery | 3-tier escalation (targeted MCP → context refresh → placeholder) | `acm-test-case-generator/SKILL.md` Phase 8 | High |
| Live validation env check | Pre-validate environment has PR changes before testing features | `acm-test-case-generator/SKILL.md` Phase 6 | High |
| Structured JSON handoff | Investigation agents write JSON files, synthesis reads JSON | `acm-test-case-generator/SKILL.md` Phases 2-5, potentially agent skill instructions | Medium |

### Implementation Order

1. **Phase 6 environment verification** -- straightforward, no architectural change
2. **Phase 8 smart recovery** -- changes the retry logic, high impact on quality
3. **Structured JSON handoff** -- requires changes to how investigation phases write output
4. **Context architecture documentation** -- update docs to reflect reality

### What NOT to Change

- Shared skills remain vanilla (no changes)
- The review_enforcement.py script stays (it's working correctly)
- The basic skill structure stays (SKILL.md + references/ + scripts/)
- The 10-phase pipeline order stays (phases are correct, just improving data passing)
