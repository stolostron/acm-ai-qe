# Test Case Generator — Portable Skill Health Report

**Date:** 2026-05-19
**Scope:** All 6 portable skills under `.claude/skills/` that participate in test case generation
**Purpose:** Comprehensive issue list with fix instructions for Claude Code to execute

## Skills in Scope

| # | Skill | Version | Role |
|---|-------|---------|------|
| 1 | `acm-test-case-generator` | 2.1.0 | Orchestrator (Phases 0–8) |
| 2 | `acm-test-case-writer` | 1.0.0 | Test case author (Phase 6) |
| 3 | `acm-test-case-reviewer` | 1.0.0 | Quality gate (Phase 7) |
| 4 | `acm-qe-code-analyzer` | 1.1.0 | PR diff analysis (Phase 2 / standalone) |
| 5 | `acm-knowledge-base` | 1.0.0 | Domain knowledge repository |
| 6 | `acm-cluster-health` | 1.0.0 | Cluster diagnostic methodology |

All skills live under `/Users/ashafi/Documents/work/ai/ai_systems_v2/.claude/skills/`.
The unified knowledge DB lives at `/Users/ashafi/Documents/work/ai/ai_systems_v2/.claude/knowledge/`.

---

## Critical Rule: `.claude/` is Self-Contained

**Everything under `.claude/` must be self-contained.** Portable skills read from `.claude/knowledge/` and `.claude/skills/` only. No dependency on `apps/test-case-generator/knowledge/`, no dependency on external workspaces, no dependency on anything outside the `.claude/` tree. The app directory (`apps/test-case-generator/`) is a separate concern — it may maintain its own copies or symlinks, but the portable skill pack must not reference it.

---

## Issue 1: `gather.py` area knowledge path is broken (HIGH)

### Problem

The portable `gather.py` at `.claude/skills/acm-test-case-generator/scripts/gather.py` resolves knowledge via `KNOWLEDGE_DIR` which points to `.claude/knowledge/`. The script then looks for area architecture files at `architecture/{area}.md` (e.g., `architecture/governance.md`).

But `.claude/knowledge/` has a different layout:
- **Area knowledge** lives under `ui/{area}.md` (e.g., `ui/governance.md`)
- **Architecture** is organized by subsystem (e.g., `architecture/governance/architecture.md`) — NOT flat `architecture/governance.md`
- **Conventions** live under `conventions/` — this path works correctly

Result: `read_area_knowledge()` in `gather.py` silently returns `None` for area knowledge in most portable skill runs, even though the content exists at `ui/{area}.md`.

### Files to fix

- `.claude/skills/acm-test-case-generator/scripts/gather.py` — the `read_area_knowledge()` function

### Fix

Update the area knowledge resolution in `gather.py` to look for area files at `ui/{area}.md` first (the canonical location in `.claude/knowledge/`), then fall back to `architecture/{area}.md` for backward compatibility. The conventions path (`conventions/*.md`) is already correct and should not change.

```
Resolution order:
1. KNOWLEDGE_DIR/ui/{area}.md          ← canonical in .claude/knowledge/
2. KNOWLEDGE_DIR/architecture/{area}.md ← fallback
```

Also remove the dead `import sys` from the same file.

---

## Issue 2: Knowledge file duplication — three copies, no sync (HIGH)

### Problem

The same 14 knowledge files (9 architecture + 4 conventions + 1 example) exist in three locations:

| Location | Role |
|----------|------|
| `.claude/knowledge/` (unified DB) | Canonical source for portable skills |
| `.claude/skills/acm-knowledge-base/references/` | Embedded copy in the knowledge-base skill |
| `apps/test-case-generator/knowledge/` | App-local copy |

Two convention files (`cli-in-steps-rules.md` and `polarion-html-templates.md`) already diverge between copies. The skill pack copy of `cli-in-steps-rules.md` has a "When CLI Backend Validation Is NOT Needed" section that the app copy lacks. The app copy of `polarion-html-templates.md` has description section templates, nested-bold rules, and numbered-list rules that the skill pack copy lacks.

`applications.md` in the skill/app is older than `.claude/knowledge/ui/applications.md` (missing Create Application dropdown, deprecation notes).

### Fix

**Step 1:** The `acm-knowledge-base` skill's `references/` directory should NOT contain copies of knowledge files. Instead, the SKILL.md should instruct agents to read directly from `${CLAUDE_SKILL_DIR}/../../knowledge/` (which resolves to `.claude/knowledge/`). Update the SKILL.md file paths from `references/architecture/{area}.md` to `../../knowledge/ui/{area}.md` and from `references/conventions/{file}` to `../../knowledge/conventions/{file}`.

**Step 2:** After updating the SKILL.md paths, delete the duplicated files under `.claude/skills/acm-knowledge-base/references/architecture/`, `.claude/skills/acm-knowledge-base/references/conventions/`, and `.claude/skills/acm-knowledge-base/references/examples/`. Keep the `references/` directory if the skill has other non-duplicated reference files, otherwise remove it.

**Step 3:** Before deleting, merge any content that exists only in the skill pack copies INTO the canonical `.claude/knowledge/` files:
- Merge the "When CLI Backend Validation Is NOT Needed" section from the skill pack `cli-in-steps-rules.md` into `.claude/knowledge/conventions/cli-in-steps-rules.md`
- Merge the description section templates, nested-bold rules, and numbered-list rules from the app `polarion-html-templates.md` into `.claude/knowledge/conventions/polarion-html-templates.md`
- Update `.claude/knowledge/ui/applications.md` if the skill/app copy has any unique content (check first)

**Step 4:** Update all agent instruction files under `.claude/skills/acm-test-case-generator/references/agents/` that reference knowledge paths to use the canonical `KNOWLEDGE_DIR` resolution (`${CLAUDE_SKILL_DIR}/../../knowledge/`).

**Step 5:** The app directory (`apps/test-case-generator/knowledge/`) is out of scope for this fix. It can maintain its own copies or symlink to `.claude/knowledge/`. Do not modify app files.

---

## Issue 3: `acm-test-case-writer` has no references/ directory (MEDIUM)

### Problem

The writer is the only core pipeline skill with zero reference files. Its 160-line SKILL.md carries ALL writing logic: the 6-step process, 3 quality rules (step granularity, backend validation placement, implementation detail translation), 14-point self-review checklist, 5 gotchas, and critical rules. This violates the progressive disclosure principle used by all other skills.

Additionally, the writer SKILL.md Step 4.5 says "Follow Synthesis Design Optimizations" but does not explicitly mention **coverage gap handling**. Phase 4 synthesis produces coverage gap triage (ADD TO TEST PLAN / NOTE ONLY / SKIP), and the docs (`07-SKILL-ARCHITECTURE.md`) say the writer should create steps for ADD gaps. This instruction is missing from the writer SKILL.md.

### Fix

Create `.claude/skills/acm-test-case-writer/references/` with two files:

**`references/writing-process.md`** — Extract from the SKILL.md body:
- The 6-step writing process (Steps 1–6) with full detail
- The 3 quality rules with examples (step granularity, backend validation placement, implementation detail translation)
- The 14-point self-review checklist
- The 5 gotchas

**`references/coverage-gap-handling.md`** — New content:
- Explicit instructions for handling synthesis coverage gap triage output
- If synthesized context includes gaps triaged as "ADD TO TEST PLAN": create corresponding test steps
- If synthesized context includes gaps triaged as "NOTE ONLY": mention in Notes section
- If synthesized context includes gaps triaged as "SKIP": ignore
- Example of translating a coverage gap into a test step

Then update the writer SKILL.md body to be a routing layer:
- Keep the modes section (full context vs standalone) and prerequisites
- Replace the detailed process with "Read `${CLAUDE_SKILL_DIR}/references/writing-process.md` for the full writing process"
- Add explicit Step 4.5 instruction: "Read `${CLAUDE_SKILL_DIR}/references/coverage-gap-handling.md` and apply coverage gap triage decisions from the synthesized context"
- Keep Critical Rules and a summary of the self-review checklist in the SKILL.md body (for quick reference)

---

## Issue 4: Reviewer SKILL.md is thinner than the pipeline agent brief (MEDIUM)

### Problem

The `acm-test-case-reviewer` SKILL.md (standalone review mode) is missing several behaviors that exist in the pipeline's `quality-reviewer.md` agent file:

| Missing from SKILL.md | Present in `quality-reviewer.md` |
|------------------------|----------------------------------|
| Entry-point label verification (route-key vs UI-label known mismatches like `managedClusters` → "Cluster list") | Yes |
| `set_cnv_version` for Fleet Virt/CCLM/MTV reviews | Yes |
| Live validation cross-check (`phase5-live-validation.md`) | Yes |
| "Assumed vs Discovered" audit section in output | Yes (also in description) |
| 3-tier review escalation protocol | Yes (in SKILL.md orchestrator, not reviewer) |
| Stale JIRA text / metric name verification against source | Yes (enforcement script) |

The MCP verification output format in the SKILL.md uses `[tool]: [query] -> [result]` placeholders, while `review_enforcement.py` parses numbered lines starting with bare tool names (`search_translations`, `get_routes`, `get_component_source`). Format mismatch can cause the enforcement script to under-count verifications.

### Fix

Update `.claude/skills/acm-test-case-reviewer/SKILL.md`:

1. Add entry-point label verification to Step 4 MCP checks (known route-key vs UI-label mismatches)
2. Add `set_cnv_version` instruction for Fleet Virt/CCLM/MTV area reviews in Step 4
3. Add "Assumed vs Discovered" section to the output format template
4. Clarify that `set_acm_version` is a prerequisite, NOT one of the 3 counted verifications
5. Fix the MCP verification output format to match what `review_enforcement.py` parses: numbered lines with bare tool names, e.g.:
   ```
   1. search_translations -- query: "policy.table.labels", result: "Labels", matches: yes
   2. get_routes -- query: "governance", result: "/multicloud/governance/...", matches: yes
   3. get_component_source -- query: "PolicyTemplateDetails", result: field order [Name, Engine...], matches: yes
   ```
6. Fix the programmatic enforcement paragraph: the SKILL says "calling skill runs `report.py`" but should say `review_enforcement.py` for Phase 7 enforcement and `report.py` for Phase 8 structural validation — these are separate scripts

Also update `.claude/skills/acm-test-case-reviewer/references/review-checklist.md` to include Steps 6.5 (design efficiency) and 6.6 (coverage gap verification), and reference it from the SKILL.md.

---

## Issue 5: Code analyzer SKILL.md missing follow-up PR detection (MEDIUM)

### Problem

The `acm-qe-code-analyzer` SKILL.md does not include follow-up PR detection, which is documented in `07-SKILL-ARCHITECTURE.md` (lines 267–268) and implemented in the pipeline's `code-analyzer.md` agent file (step 11 + `follow_up_prs` in JSON output). This feature checks for subsequent merged PRs that modify the same files, flagging post-merge renames, fixes, and refactors that would make the test case stale.

Also, `07-SKILL-ARCHITECTURE.md` says the code analyzer has "no separate reference files" but it actually has `references/analysis-rules.md`. The SKILL.md doesn't reference this file.

### Fix

1. Add Step 11 to the code analyzer SKILL.md process: "Follow-up PR Detection"
   - For each primary changed file, check for subsequent merged PRs: `gh pr list --search "path:<filepath>" --state merged --limit 5`
   - Flag post-merge renames, fixes, and refactors
   - Include `follow_up_prs` section in the Return Format

2. Reference `references/analysis-rules.md` from the SKILL.md body: "Read `${CLAUDE_SKILL_DIR}/references/analysis-rules.md` for analysis heuristics"

3. Update `07-SKILL-ARCHITECTURE.md` to acknowledge that the code analyzer has a `references/` directory

---

## Issue 6: `review_enforcement.py` regex is brittle (MEDIUM)

### Problem

The MCP verification counting function `count_mcp_verifications()` in `.claude/skills/acm-test-case-generator/scripts/review_enforcement.py` uses a regex that only counts numbered lines starting with specific tool names (`search_translations`, `get_routes`, `get_component_source`, etc.). Variations in formatting (backticks around tool names, bullet lists instead of numbered lists, different wording) cause under-counting, which triggers false NEEDS_FIXES verdicts.

Additionally, `check_source_verification()` and `check_translation_verification()` search the **entire** review text, not just the `MCP VERIFICATIONS` section. A mention of `get_component_source` in a BLOCKING issue description could satisfy the check without a real MCP call (false PASS).

### Fix

1. Make the MCP counting regex more tolerant: accept both `1. search_translations` and `1. \`search_translations\`` formats, and both `--` and `→` separators
2. Scope `check_source_verification` and `check_translation_verification` to only search within the `MCP VERIFICATIONS` section (extract that section first using the existing `extract_section()` pattern)
3. Add unit tests for both the tolerant regex and the scoped verification checks

---

## Issue 7: `acm-cluster-health` integration with live-validator is loose (MEDIUM)

### Problem

The `acm-cluster-health` skill provides a 12-layer diagnostic model and 14 trap patterns, but the `live-validator.md` agent file doesn't systematically invoke it. The live-validator has its own lighter environment verification (3-method tiered check) and only vaguely references the cluster-health skill. The connection is implicit — the validator should explicitly call the health skill for a sanity check before trusting its observations.

### Fix

1. Update `.claude/skills/acm-test-case-generator/references/agents/live-validator.md` to add an explicit step: "Before feature validation, invoke `acm-cluster-health` skill for a quick sanity check. Read `${SKILLS_DIR}/acm-cluster-health/SKILL.md` and run a Layer 9 (Operators) + Layer 10 (Cross-Cluster) check. If the cluster is DEGRADED or CRITICAL at these layers, flag in output as `Cluster Health: DEGRADED — observations may be unreliable` and proceed with caution."

2. Update `.claude/skills/acm-cluster-health/SKILL.md` to add a "Quick Sanity Mode" section: a lightweight subset of the 12-layer model (Layers 1, 2, 9, 10 only) designed for callers that need a fast go/no-go assessment without a full diagnostic. This mode checks: nodes ready (L1), cluster operators degraded (L2), ACM operator pods running (L9), managed clusters connected (L10). Output: HEALTHY / DEGRADED / CRITICAL with one-line evidence per layer.

---

## Issue 8: Generator orchestrator loads `pipeline-detail.md` upfront (~500 lines) (MEDIUM)

### Problem

The `acm-test-case-generator` SKILL.md says at line 69: "Read `${CLAUDE_SKILL_DIR}/references/pipeline-detail.md` for input schemas, validation commands, credential resolution, MCP availability checks, retry protocol, and run directory structure."

This loads ~500 lines of reference material into orchestrator context before Phase 0 even starts. Most of this content is only needed at specific phases (credentials at Phase 0, validation commands at Phase 1+, retry protocol on failure). This wastes context window and violates the progressive disclosure principle.

### Fix

Split `pipeline-detail.md` into per-concern files:

| New file | Content from current `pipeline-detail.md` | Loaded when |
|----------|-------------------------------------------|-------------|
| `references/phase0-inputs.md` | Input schemas, credential resolution cascade, MCP availability check | Phase 0 |
| `references/validation-protocol.md` | `validate_artifact.py` commands per phase, retry protocol, `validation-warnings.json` handling | On first validation failure |
| `references/run-directory.md` | Run directory structure, artifact naming, timestamp format | Phase 1 (before creating run dir) |

Keep `pipeline-detail.md` as a short index pointing to the three split files (for backward compatibility if any agent references it directly). Update the SKILL.md Phase 0 to read `phase0-inputs.md`, and each subsequent phase section to reference the validation protocol only when needed.

---

## Issue 9: Sample test case violates CLI rules (MEDIUM)

### Problem

`.claude/knowledge/examples/sample-test-case.md` (and all copies) has Step 5 titled "Verify Backend State Matches UI" with `oc` commands embedded in a UI-focused step. This contradicts `.claude/knowledge/conventions/cli-in-steps-rules.md` which requires:
- CLI backend validation in a **dedicated step** titled "Verify [what] via CLI (Backend Validation)"
- CLI steps placed **after** UI steps, not embedded within them

An agent learning from this example will produce test cases that fail the reviewer's structural validation.

### Fix

Update `.claude/knowledge/examples/sample-test-case.md` Step 5:
- Rename to "Verify Policy Compliance Status via CLI (Backend Validation)"
- Ensure it's a dedicated CLI-only step (no browser actions)
- Place it after the UI verification steps
- Follow the exact naming convention from `cli-in-steps-rules.md`

---

## Issue 10: Evals not runnable (MEDIUM)

### Problem

`.claude/skills/acm-test-case-generator/evals/evals.json` contains 35 skill disambiguation queries with expected skill assignments, but there is no harness to run them. They are documentation-only.

### Fix

Create `.claude/skills/acm-test-case-generator/evals/run_evals.py` — a Python script (stdlib-only) that:

1. Loads `evals.json`
2. For each query, applies the disambiguation rules from the 5 SKILL.md description fields (keyword matching, TRIGGER/DO NOT TRIGGER patterns)
3. Compares predicted skill vs expected skill
4. Reports accuracy: total correct, false positives per skill, false negatives per skill
5. Exits with code 0 if accuracy >= 90%, code 1 otherwise

The eval runner should be deterministic (rule-based keyword matching, not LLM-based) so it can run in CI. It tests whether the TRIGGER/DO NOT TRIGGER language in descriptions is sufficient to disambiguate the 35 query patterns.

Add to `AGENTS.md` test commands:
```bash
cd ai_systems_v2
python .claude/skills/acm-test-case-generator/evals/run_evals.py
```

---

## Issue 11: No integration test for the skill pipeline (MEDIUM)

### Problem

The 93 unit tests in `apps/test-case-generator/tests/unit/` cover convention validation, models, file operations, and artifact validation. But there is no test that exercises the deterministic pipeline stages end-to-end with fixture data. The only way to test the pipeline is to run `/generate` manually with a real JIRA ticket.

### Fix

Create `apps/test-case-generator/tests/integration/test_pipeline_stages.py` with fixture-based tests:

1. **Stage 1 fixture test:** Provide a pre-built `gather-output.json` fixture (mock PR data, conventions, area knowledge). Run `validate_artifact.py` on it. Assert it passes.

2. **Pre-synthesis fixture test:** Provide fixture `phase1-jira.json`, `phase2-code.json`, `phase3-ui.json`. Run `validate_artifact.py --pre-synthesis`. Assert the 8-point check passes.

3. **Stage 8 fixture test:** Provide a fixture `test-case.md` (convention-compliant). Run `report.py` on a fixture run directory. Assert it produces `test-case-description.html`, `test-case-setup.html`, `test-case-steps.html`, `review-results.json`, `SUMMARY.txt`.

4. **Review enforcement fixture test:** Provide a fixture review output (with 3+ MCP verifications in correct format). Run `review_enforcement.py`. Assert exit code 0.

5. **Negative tests:** Provide deliberately broken fixtures (missing metadata, 0 MCP verifications, broken step format). Assert the validators catch them.

All fixtures should be JSON/markdown files in `tests/integration/fixtures/`. No MCP, JIRA, or cluster access needed. Mark with `@pytest.mark.integration`.

Add to `AGENTS.md`:
```bash
cd apps/test-case-generator
python -m pytest tests/integration/ -q
```

---

## Issue 12: `phase7-review.md` output file not documented in reviewer agent (LOW)

### Problem

The run directory layout in `pipeline-detail.md` lists `phase7-review.md` as a Phase 7 output file. But neither the `quality-reviewer.md` agent file nor the `acm-test-case-reviewer` SKILL.md instructs the agent to write this file. The orchestrator must save the reviewer's output to disk, but this responsibility is not documented.

### Fix

Add to the `quality-reviewer.md` agent's output section: "Write your complete review output to `${RUN_DIR}/phase7-review.md`."

Also add the same instruction to the reviewer's output format section in the SKILL.md (for standalone reviews, the user provides the output path).

---

## Issue 13: `07-SKILL-ARCHITECTURE.md` minor doc drift (LOW)

### Problem

Several claims in `07-SKILL-ARCHITECTURE.md` don't match current state:
- Says code analyzer has "no separate reference files" — it has `references/analysis-rules.md`
- Says reviewer has "SKILL.md (standalone with inlined validation)" — it has `references/review-checklist.md`
- MCP tool matrix shows reviewer not using `get_wizard_steps`, but SKILL.md lists it in Step 4

### Fix

Update `07-SKILL-ARCHITECTURE.md`:
1. Code analyzer entry: change to "SKILL.md + references/analysis-rules.md"
2. Reviewer entry: change to "SKILL.md + references/review-checklist.md"
3. MCP tool matrix: add `get_wizard_steps` to the reviewer column, or remove it from the SKILL.md if it's not actually used (check which is correct)

---

## Issue 14: Convention files have unique content in different copies (LOW)

### Problem (to be resolved as part of Issue 2)

Before deleting duplicate knowledge files, merge unique content:

| File | Unique content in skill/unified copy | Unique content in app copy |
|------|--------------------------------------|----------------------------|
| `cli-in-steps-rules.md` | "When CLI Backend Validation Is NOT Needed" section + rule of thumb | (subset of skill copy) |
| `polarion-html-templates.md` | (subset of app copy) | Description section template, nested-bold rules, backtick/`---` stripping, numbered-list rules |

### Fix

This is handled as part of Issue 2 Step 3. Merge BEFORE deleting. The canonical `.claude/knowledge/conventions/` files must contain the superset of all unique content from both copies.

---

## Issue 15: fleet-virt.md has misplaced governance content (LOW)

### Problem

`.claude/knowledge/ui/fleet-virt.md` (and copies) contains a testing consideration bullet: "For Gatekeeper mutation policies, the Clusters tab table uses a reduced column set." This belongs in the governance area file, not fleet-virt.

### Fix

Move the Gatekeeper mutation policies bullet from `fleet-virt.md` to `governance.md` in `.claude/knowledge/ui/`.

---

## Issue 16: Test case generator produces UI/integration tests only — no E2E functional outcome verification (HIGH)

### Problem

The test case generator pipeline produces test cases that validate the **data path** (UI form → YAML → API resource) but stop short of verifying the **functional outcome** the feature is designed to deliver. The generated steps test "does the UI set the right field?" but not "does the feature actually work end-to-end?"

### Evidence: ACM-34028 (`preserveResourcesOnDeletion` toggle)

The generated test case for ACM-34028 (run: `ACM-34028-2026-06-13T18-01-39`) contains 8 steps:

| Step | What it tests | Test type |
|------|---------------|-----------|
| 1 | Checkbox default state (unchecked) | UI state |
| 2 | Create AppSet with toggle ON, review step display | UI workflow |
| 3 | CLI cross-check: `spec.syncPolicy.preserveResourcesOnDeletion: true` | Integration (UI → API) |
| 4 | Pull model default state | UI state |
| 5 | Edit pull model, enable toggle | UI workflow |
| 6 | Re-edit, disable toggle (round-trip) | UI workflow |
| 7 | YAML editor bidirectional binding | UI integration |
| 8 | Section separation (AppSet sync policy vs per-app sync policy) | UI structure |

**What's missing:** Not a single step tests the actual user-facing outcome — that deleting an ApplicationSet with `preserveResourcesOnDeletion: true` actually **preserves the child Application resources**. This is the entire reason the feature exists (born from production incident ACM-33654).

A complete E2E step would be:

1. Create AppSet with toggle ON → verify child apps are created on target cluster
2. Delete the ApplicationSet
3. Verify child Application resources **still exist** (preserved)
4. Contrast: create a second AppSet with toggle OFF → delete it → verify child resources **are removed**

This step takes ~60 seconds and closes the gap between "the UI sets the right field" and "the feature protects users as intended."

### Why this matters

- The PR description says "No backend work is needed — the Argo CD ApplicationSet controller already supports this field." The generator correctly scoped to the PR's code changes (UI only). But from a QE perspective, the test should verify the full user journey, not just the code delta.
- If the Argo CD version shipped with ACM had a regression in `preserveResourcesOnDeletion` handling, the generated test case would pass green while the feature is completely broken from the user's perspective.
- Features born from production incidents (like ACM-33654) deserve E2E outcome verification — the cost of missing a regression is high.

### Root cause in the pipeline

The test case generator's scoping logic (Phase 2: code analysis → Phase 6: writing) correctly identifies the **code change boundary** (what files/components were modified) and generates steps within that boundary. But it has no heuristic for:

1. **Cross-component outcome testing** — when a UI change enables a backend behavior that was already implemented, the generator should consider whether the backend behavior warrants an E2E verification step
2. **Feature intent analysis** — the JIRA story's value statement describes a user outcome ("safety net against accidental child Application deletion"), but the generator doesn't translate feature intent into outcome verification steps
3. **Incident-driven features** — when a feature links to a bug/incident (ACM-33654), the test case should verify the incident scenario is resolved, not just that the UI toggle works

### Proposed fix

**Option A (writer skill enhancement):** Add a "Functional Outcome Verification" phase to the `acm-test-case-writer` skill. After writing UI/integration steps, the writer should ask: "Does this feature enable a backend behavior with a user-visible outcome? If yes, add an E2E step that verifies the outcome." This requires:
- Extracting the feature's value statement from JIRA (already available in Phase 1 gather)
- A heuristic: if the JIRA description contains outcome language ("prevents deletion", "enables access", "blocks unauthorized") AND the code change is UI-only, flag for E2E outcome step
- Adding the E2E step as a clearly labeled final step (e.g., "Step N: Verify Functional Outcome — End-to-End")

**Option B (reviewer skill enhancement):** Add a quality gate to the `acm-test-case-reviewer` that checks: "Does the test case verify the feature's stated user outcome, or only the UI mechanics?" If only UI mechanics, flag as a coverage gap with severity HIGH when the feature is incident-driven, MEDIUM otherwise.

**Option C (both):** Writer generates the E2E step; reviewer validates it exists. This is the most complete approach.

### Affected skills

| Skill | Change needed |
|-------|---------------|
| `acm-test-case-writer` | Add E2E outcome verification heuristic (Option A) |
| `acm-test-case-reviewer` | Add outcome coverage quality gate (Option B) |
| `acm-test-case-generator` | Phase 4 synthesis should flag "UI-only change enabling backend behavior" as a coverage consideration |
| `acm-qe-code-analyzer` | Output should include a `backend_behavior_enabled` field when the code change exposes an existing backend capability |

### Live Verification Session (2026-06-18) — What the Refined Test Case Looks Like

The generated 8-step test case was manually refined to 5 steps through human review. The refinements demonstrate what the generator SHOULD produce:

**Steps dropped (framework behavior, not PR-specific):**
- Pull model separate testing (same `ArgoWizard.tsx` component, same code path as push model — testing both is redundant)
- Round-trip edit (enable → disable toggle) — tests the `react-form-wizard` framework's edit/save lifecycle, not this PR's code
- YAML bidirectional binding — tests the framework's `WizCheckbox` path binding, not this PR's code
- Negative contrast (toggle OFF behavior) — that's the pre-existing default, not new behavior

**Steps kept:**
1. Verify default checkbox state (unchecked) — new UI element
2. Create push model with toggle ON, verify Review step — core feature
3. CLI: backend field at correct spec level + child app exists with ownerReference — backend validation
4. Section separation (General step vs Sync policy step) — new UI structure
5. **Delete AppSet, verify deployed resources survive** — E2E functional outcome

**Critical correction discovered during live testing:**

The initial E2E step (Step 5) was written to verify that **child Application CRs** survive deletion. Live testing showed they do NOT survive — they are cascade-deleted via Kubernetes GC (ownerReference). This is **expected behavior per ArgoCD design**.

What `preserveResourcesOnDeletion` actually does (from `argoproj/argo-cd/applicationset/utils/utils.go` lines 294-302):
- When `true`: does NOT stamp the `resources-finalizer` on child Applications → when child Apps are GC-deleted, the deployed K8s resources (Deployments, Services, namespaces) are **orphaned and preserved**
- When `false`: stamps the `resources-finalizer` → when child Apps are deleted, ArgoCD processes the finalizer and **cleans up deployed resources**

The correct E2E verification is:
```
1. Create AppSet with toggle ON, wait for child apps to sync and deploy resources
2. Delete the AppSet
3. Verify child Application CRs are GONE (expected — ownerRef cascade)
4. Verify deployed resources (namespace, Deployment, Service) STILL EXIST on target cluster
```

The first test attempt also failed because the Git repo branch was `master` not `main` — the child apps never synced, so there were no deployed resources to preserve. The generator should validate source repo accessibility or note the correct branch in setup prerequisites.

**Desired generator behavior:** When generating the E2E outcome step, the generator must:
1. Understand what "preserve" means in context (read the ArgoCD docs, not just the JIRA description)
2. Verify what specifically should survive vs what is expected to be deleted
3. Ensure the test environment actually deploys resources before attempting the deletion test (wait for sync, verify health)
4. Include correct repo/branch details in setup prerequisites

### Verified test case (Polarion RHACM4K-64825)

The refined 5-step test case was verified on build `5.0.0-DOWNSTREAM-2026-06-15-23-36-22` (ACM 5.0.0-109, OpenShift GitOps 1.20.4). All 5 steps PASS. The Polarion HTML files are at:
- `runs/test-case-generator/ACM-34028/ACM-34028-2026-06-13T18-01-39/test-case-description-v2.html`
- `runs/test-case-generator/ACM-34028/ACM-34028-2026-06-13T18-01-39/test-case-setup-v2.html`
- `runs/test-case-generator/ACM-34028/ACM-34028-2026-06-13T18-01-39/test-case-steps-v2.html`

### Priority justification

HIGH — this is a systematic gap, not a one-off. Every UI-only feature that exposes an existing backend behavior will produce test cases that stop at the integration boundary. The generator needs a heuristic to cross that boundary for features where the user outcome is the point. The ACM-34028 live verification session proved this: without the E2E step, the test case would pass while completely missing what the feature actually does (and an initial misunderstanding of the behavior would have produced a false-negative bug report).

---

## Execution Order

Recommended order to minimize conflicts:

1. **Issue 2** (knowledge consolidation — merge unique content first, then delete copies, update paths)
2. **Issue 1** (`gather.py` area knowledge path fix — depends on Issue 2 being done)
3. **Issue 9** (sample test case CLI rule violation)
4. **Issue 15** (fleet-virt misplaced content)
5. **Issue 16** (E2E functional outcome verification gap — affects writer, reviewer, code analyzer, orchestrator)
6. **Issue 3** (writer references/ directory)
7. **Issue 4** (reviewer SKILL.md gaps)
8. **Issue 5** (code analyzer follow-up PR detection)
9. **Issue 8** (orchestrator progressive disclosure)
10. **Issue 7** (cluster-health integration with live-validator)
11. **Issue 6** (review_enforcement.py regex)
12. **Issue 12** (phase7-review.md output)
13. **Issue 13** (07-SKILL-ARCHITECTURE.md doc drift)
14. **Issue 14** (handled by Issue 2)
15. **Issue 10** (evals harness)
16. **Issue 11** (integration tests)

Issues 10 and 11 (evals + integration tests) should be done last since they validate the fixes from Issues 1–9.

---

## Files Modified (Summary)

| File | Issues |
|------|--------|
| `.claude/skills/acm-test-case-generator/scripts/gather.py` | 1 |
| `.claude/skills/acm-knowledge-base/SKILL.md` | 2 |
| `.claude/skills/acm-knowledge-base/references/` (delete duplicates) | 2 |
| `.claude/knowledge/conventions/cli-in-steps-rules.md` | 2, 14 |
| `.claude/knowledge/conventions/polarion-html-templates.md` | 2, 14 |
| `.claude/knowledge/examples/sample-test-case.md` | 9 |
| `.claude/knowledge/ui/fleet-virt.md` | 15 |
| `.claude/knowledge/ui/governance.md` | 15 |
| `.claude/skills/acm-test-case-writer/SKILL.md` | 3, 16 |
| `.claude/skills/acm-test-case-writer/references/writing-process.md` (new) | 3 |
| `.claude/skills/acm-test-case-writer/references/coverage-gap-handling.md` (new) | 3 |
| `.claude/skills/acm-test-case-reviewer/SKILL.md` | 4, 12, 16 |
| `.claude/skills/acm-test-case-reviewer/references/review-checklist.md` | 4 |
| `.claude/skills/acm-qe-code-analyzer/SKILL.md` | 5, 16 |
| `.claude/skills/acm-test-case-generator/scripts/review_enforcement.py` | 6 |
| `.claude/skills/acm-test-case-generator/references/agents/live-validator.md` | 7 |
| `.claude/skills/acm-cluster-health/SKILL.md` | 7 |
| `.claude/skills/acm-test-case-generator/SKILL.md` | 8, 16 |
| `.claude/skills/acm-test-case-generator/references/pipeline-detail.md` | 8 |
| `.claude/skills/acm-test-case-generator/references/phase0-inputs.md` (new) | 8 |
| `.claude/skills/acm-test-case-generator/references/validation-protocol.md` (new) | 8 |
| `.claude/skills/acm-test-case-generator/references/run-directory.md` (new) | 8 |
| `.claude/skills/acm-test-case-generator/references/agents/quality-reviewer.md` | 12 |
| `docs/test-case-generator/07-SKILL-ARCHITECTURE.md` | 13 |
| `.claude/skills/acm-test-case-generator/evals/run_evals.py` (new) | 10 |
| `apps/test-case-generator/tests/integration/test_pipeline_stages.py` (new) | 11 |
| `apps/test-case-generator/tests/integration/fixtures/` (new dir) | 11 |

---

## Validation

After all fixes, run:

```bash
# Unit tests (should still pass — 93 tests)
cd apps/test-case-generator && python -m pytest tests/unit/ -q

# Integration tests (new — should pass)
python -m pytest tests/integration/ -q

# Eval harness (new — should achieve >= 90% accuracy)
python .claude/skills/acm-test-case-generator/evals/run_evals.py

# Verify no broken knowledge paths
python -c "
from pathlib import Path
kb = Path('.claude/knowledge')
for area in ['governance','rbac','fleet-virt','cclm','mtv','clusters','search','applications','credentials']:
    p = kb / 'ui' / f'{area}.md'
    assert p.exists(), f'MISSING: {p}'
for conv in ['test-case-format.md','area-naming-patterns.md','cli-in-steps-rules.md','polarion-html-templates.md']:
    p = kb / 'conventions' / conv
    assert p.exists(), f'MISSING: {p}'
print('All knowledge paths verified.')
"
```
