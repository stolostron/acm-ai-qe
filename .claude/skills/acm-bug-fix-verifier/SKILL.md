---
name: acm-bug-fix-verifier
description: >-
  Verifies whether a known ACM bug fix has landed on a target environment. Takes
  a JIRA ticket and a cluster, runs a 9-phase pipeline: parallel JIRA/PR/environment
  investigation, three-tier fix presence check (branch reachability, build date,
  code presence), PR code review for fix correctness, Neo4j prerequisite gap
  analysis with heuristic fallback, environment health gate, Playwright-driven
  UI/API verification, verdict with optional JIRA update, and post-verdict
  learning. Produces FIXED, NOT FIXED, or BLOCKED verdicts (each with a qualifier)
  and a HIGH/MEDIUM/LOW confidence level backed by an evidence trail.
  TRIGGER: verify bug fix, confirm fix landed, check if fixed, is the bug fixed,
  verify ACM-NNNNN on cluster, test fix on environment.
  DO NOT TRIGGER: hunt for new bugs (use acm-bug-hunter), write test cases
  (use acm-test-case-generator), cluster health check (use acm-hub-health-check),
  PR-only code review (use acm-qe-code-analyzer).
compatibility: >-
  Required: jira MCP, gh CLI.
  Required for UI verification: playwright MCP, console credentials.
  Recommended: neo4j-rhacm MCP (prerequisite gap analysis; degrades to heuristics),
  acm-source MCP (code cross-validation; degrades gracefully).
  Optional: acm-search MCP, acm-kubectl MCP, oc CLI, engram MCP (cross-session
  recall/learning; skipped silently if absent).
  File-based knowledge DB at .claude/knowledge/ (failure signatures, diagnostic traps).
  Run /onboard to configure MCPs.
metadata:
  author: acm-qe
  version: "1.3.0"
  skill-standard: "anthropic-agent-skills-v1"
  category: verification
---

# ACM Bug Fix Verifier

Verifies whether a specific ACM bug fix is present and working in a target environment. Distinct from `acm-bug-hunter` (which hunts for *unknown* bugs) -- this skill confirms whether a *known* bug has been fixed.

## ASK QUESTIONS FIRST

| Category | Questions to Ask |
|----------|------------------|
| **JIRA Key** | "What is the bug JIRA key? (e.g., ACM-12345)" |
| **Environment** | "Which environment? (cluster URL, `oc whoami --show-server`, or ACM version)" |
| **Scope** | "Full (UI + backend, default), presence-only (code check only?), or prereq-only?" |
| **Credentials** | "Console password? (needed for UI verification; skip for backend-only)" |

If the user provides a JIRA key and is already `oc login`-ed, proceed without asking further.

## Progressive Disclosure

| Level | Content | When loaded |
|-------|---------|-------------|
| **1 -- Frontmatter** | Description, triggers, compatibility | Always (system prompt) |
| **2 -- This file** | Full workflow, phases 0-4.5, rules | On skill activation |
| **3 -- References** | [verification-patterns.md](references/verification-patterns.md) -- verdict logic, decision tree, evidence scoring | During Phases 2-4 |
| | [environment-checks.md](references/environment-checks.md) -- build tags, OIDC, Neo4j, cherry-pick detection | During Phase 1 |
| | [investigation-notes.md](references/investigation-notes.md) -- design decisions, examples, troubleshooting | Author reference |

## MANDATORY: Phase Gate Enforcement

On skill start, create tasks for ALL phases:

```
TaskCreate: Phase 0: Intake -- parse JIRA, resolve environment, scope, Engram recall
TaskCreate: Phase 1: Parallel investigation (JIRA + Environment + PR)
TaskCreate: Phase 2: Fix presence assessment (three-tier)
TaskCreate: Phase 2b: PR code review (fix correctness)
TaskCreate: Phase 2.5: Prerequisite gap analysis
TaskCreate: Phase 2.75: Environment health gate
TaskCreate: Phase 3A: Backend verification (always runs)
TaskCreate: Phase 3B: UI verification (conditional)
TaskCreate: Phase 4: Verdict + optional JIRA update
TaskCreate: Phase 4.5: Post-verdict learning (non-blocking)
```

Gate rules:
1. A phase CANNOT be marked `completed` without executing it.
2. Phase 1 subagents run in parallel. All three must complete before Phase 2.
3. Phase 2 produces a preliminary verdict. If BLOCKED, skip Phases 2b, 2.5, 2.75, and 3.
4. Phase 2b MUST complete before Phase 2.5.
5. Phase 2.5 MUST complete before Phase 2.75; Phase 2.75 MUST complete before Phase 3.
6. Phase 2.75 can force **BLOCKED (environment)** and skip Phase 3 when the bug's subsystem is critically degraded.
7. Phase 3A always runs. Phase 3B is skipped when credentials or Playwright are unavailable -- set the verdict qualifier; never silently drop a tier.
8. Phase 3 runs INLINE (not as subagent) due to Playwright MCP limitation.
9. Phase 4 MUST NOT write to JIRA without explicit user approval.
10. Phase 4.5 is non-blocking: skip silently if Engram/knowledge-DB is unavailable. Never changes the verdict.
11. Scope gating: **presence-only** stops after Phase 2b (max verdict FIXED (code-only), MUST NOT offer to close ticket); **prereq-only** stops after Phase 2.5 (gap table, no verdict).

### Approval Gates

| Action | Gate |
|--------|------|
| Read JIRA, read PRs, query Neo4j, oc get/describe/logs | No approval needed |
| oc exec (read-only grep inside containers) | No approval needed |
| Create/patch any cluster resource | **Explicit user approval** |
| Post JIRA comment | **Explicit user approval** -- show draft first |
| Transition JIRA status | **Explicit user approval** -- never auto-transition |

---

## Phase 0: Intake

Parse the user's request and resolve all inputs.

**Step 1 -- JIRA ticket:** Parse the JIRA key from user input. Use `mcp__jira__get_issue(issue_key="ACM-XXXXX")`. Extract: summary, description, fix versions, status, resolution, linked PRs, components. If JIRA MCP unavailable, stop the pipeline.

**Step 2 -- Target environment:** Priority: (1) user-provided cluster URL, (2) current `oc whoami --show-server`, (3) ask the user. Verify connectivity with `oc whoami`.

**Step 3 -- ACM version:** `oc get mch -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.status.currentVersion}{"\n"}{end}'`. Read [environment-checks.md](references/environment-checks.md) for full downstream tag extraction.

**Step 4 -- Scope:**

| Scope | Phases run | Max verdict | Notes |
|-------|-----------|-------------|-------|
| **Full** (default) | 0 -> 4.5 | any | UI + backend verification |
| **Presence-only** | 0 -> 2b | FIXED (code-only) | No ticket close. Note: "Fix presence confirmed. Full verification pending." |
| **Prereq-only** | 0 -> 2.5 | none (gap table) | Outputs gap table; no verdict |

**Step 5 -- Version check:** Compare JIRA fix version against detected ACM version. Warn on mismatch.

**Step 6 -- Console credentials:** Priority: (1) `CONSOLE_USER`/`CONSOLE_PASSWORD` env vars, (2) user-provided, (3) `oc extract secret/kubeadmin-password -n kube-system --to=-` (may return bcrypt -- unusable). No cleartext password -> Phase 3B skipped, qualifier = **code-only**.

**Step 7 -- Engram recall (optional):** If Engram MCP available, `mcp__engram__engram_recall(query="verify <JIRA-KEY>")`. If prior attempt found, surface to user. If unavailable, skip silently.

---

## Phase 1: Parallel Investigation

Launch three subagents in parallel. Read [environment-checks.md](references/environment-checks.md) before spawning.

**1A: JIRA Deep Dive** -- Spawn `general-purpose` subagent. Use JIRA MCP: get full ticket, comments, linked issues. Extract repro steps, component, fix description, all linked PRs (from comments, description, remote links). Search for related bugs and QE verification sub-tasks. Return structured summary with PR list.

**1B: Environment Profile** -- Spawn `general-purpose` subagent. Extract DOWNSTREAM build tag (full `...-DOWNSTREAM-YYYY-MM-DD-HH-MM-SS` format), component image versions, ACM/OCP version, node count. If neo4j-rhacm available, query prerequisite dependencies. See environment-checks.md for tag extraction and component-to-deployment mapping.

**1C: PR and Cherry-pick Analysis** -- Spawn `general-purpose` subagent. For each PR: `gh pr view --json state,mergedAt,mergeCommit,baseRefName`, check merge target (main vs release-2.XX), cherry-pick detection (see environment-checks.md section 4), branch reachability via `gh api repos/.../compare`. Return per-PR merge status, cherry-pick PRs, merge commit SHAs, merge dates.

---

## Phase 2: Fix Presence Assessment

Merge subagent results. Read [verification-patterns.md](references/verification-patterns.md) for the full tier definitions, decision tree, verdict matrix, and pipeline-lag model.

### Three-Tier Evidence Model

| Tier | Check | Method |
|------|-------|--------|
| **A (Branch)** | Is the merge SHA reachable from the release branch? | `gh api repos/<REPO>/compare/release-<VER>...<SHA>` |
| **B (Build)** | Is the image build date >= PR merge date? | DOWNSTREAM tag date vs `mergedAt` (24-hour graduated model) |
| **C (Code)** | Is the fix code present in the running container? | `oc exec deploy/<component> -- grep "<pattern>"` |

Apply the decision tree in verification-patterns.md: Tier A fail -> check cherry-picks -> BLOCKED (cherry-pick). Tier B fail (image predates merge) -> BLOCKED (pipeline lag). Tier C pass -> fix in build -> Phase 2b. See verification-patterns.md for the graduated pipeline-lag model, edge cases, and the complete verdict matrix.

A "fix in build" outcome is **not** a final verdict -- Phase 3 decides FIXED vs NOT FIXED. If Phase 2 yields any **BLOCKED**: skip Phases 2b, 2.5, 2.75, and 3; proceed to Phase 4.

### Multi-PR Fixes

If multiple PRs reference the JIRA key: (1) classify each as PRIMARY/RELATED/TEST-ONLY, (2) order by dependency (use `neo4j-rhacm` if available; fallback: backend before frontend, framework before consumer), (3) ALL PRIMARY PRs must pass Tier A/B -- worst result is the overall verdict, (4) document every PR number + verification order.

---

## Phase 2b: PR Code Review (Fix Correctness)

Delegate to **`../acm-qe-code-analyzer/SKILL.md`** sibling skill (spawn `general-purpose` subagent). If unavailable or PR is small (<5 files), use `gh pr diff` directly.

Assess: Does the change address the root cause? Is it minimal and scoped? Are tests updated? Could it break adjacent functionality via shared call sites?

Classify risk: **Low** (single-value change, CSS fix with tests), **Medium** (shared utility, API change), **High** (large refactor bundled with fix). For medium/high: note specific areas to watch in Phase 3.

Record: fix summary (plain language), risk level, regression spots for Phase 3.

If code review reveals the fix is **clearly wrong**: verdict **NOT FIXED (code review)**, skip Phases 2.5, 2.75, 3; proceed to Phase 4.

---

## Phase 2.5: Prerequisite Gap Analysis

Read [environment-checks.md](references/environment-checks.md) sections 5-7 for Cypher patterns and heuristic table.

**With Neo4j:** Query component dependency graph (`MATCH (t)-[:DEPENDS_ON]->(req) WHERE t.label CONTAINS '<component>'`). For each dependency, verify pod health and image currency via `oc get deploy`.

**Without Neo4j (heuristic fallback):** (1) Heuristic dependency table (7 component chains, environment-checks.md section 6), (2) CSV dependency parsing, (3) pod start time vs build tag, (4) JIRA link analysis for prerequisite mentions.

Output a gap table (`| Prerequisite | Status | Evidence |`). If gaps require cluster modification: ask user (proceed / stop / backend-only). **NEVER** create, patch, or delete cluster resources without explicit approval. No gaps -> proceed to Phase 2.75.

---

## Phase 2.75: Environment Health Gate

Scope checks to the bug's subsystem. Run inline with `oc` (read-only), following `../acm-hub-health-check/SKILL.md` methodology and `.claude/knowledge/diagnostics/diagnostic-traps.md`:

| Trap | Symptom it masks | Inline check |
|------|------------------|--------------|
| Trap 1 -- MCH status stale | Operators not reconciling | `oc get mch -A` -- phase should be `Running` |
| Trap 2 -- console-mce pod down | Feature tabs missing despite CSV healthy | `oc get pods -n multicluster-engine -l app=console-mce` |
| Trap 13 -- ConsolePlugin backend | Plugins registered but broken | `oc get pods -n <plugin-ns>` for affected backend |
| Trap 3 -- search-postgres empty | Search indexer healthy, DB empty | (search bugs only) check search-postgres pods + row-count |

| Health result | Action |
|---------------|--------|
| **Critical** (crashlooping, unreachable, empty DB) | **BLOCKED (environment)** -- skip Phase 3, go to Phase 4 |
| **Minor** (non-critical warnings) | Warn user, ask to proceed |
| **Healthy** | Proceed to Phase 3 |

For deeper investigation, spawn a `general-purpose` subagent following `../acm-hub-health-check/SKILL.md`. If checks cannot run: proceed with a warning ("Health gate skipped"). Never silently skip.

---

## Phase 3: Live Verification

**IMPORTANT: This phase runs INLINE -- do NOT spawn a subagent.** Playwright MCP tools are not accessible from subagents (see [investigation-notes.md](references/investigation-notes.md) D1).

### Phase 3A: Backend Verification (ALWAYS runs)

Using `oc` CLI and optionally acm-search/acm-kubectl MCPs:

1. **Resource state**: `oc get`/`oc describe` resources affected by the bug.
2. **Tier C evidence** (if not done in Phase 2): `oc exec deploy/<component> -- grep "<fix-indicator>" <path>`.
3. **Source cross-validation** (if acm-source MCP available): `mcp__acm-source__search_code(query="<fix string>")` -- Tier 1 evidence (weight 1.0). Not found despite Tier A passing -> red flag (merge conflict?).
4. **API behavior**: `browser_evaluate` fetch with CSRF for console proxy endpoints.
5. **Log inspection**: `oc logs deploy/<component> --tail=100` -- Tier 2 evidence when clean.

### Phase 3B: UI Verification (conditional)

**Skip conditions:** No credentials -> qualifier = **code-only**. Playwright unavailable -> qualifier = **backend-only**. State skip reason explicitly.

**If proceeding:**

1. **Authenticate**: Resolve console URL via `oc get route multicloud-console -n $MCH_NS -o jsonpath='{.spec.host}'`. Follow auth in `${CLAUDE_SKILL_DIR}/../acm-test-case-generator/references/console-auth.md`; if unavailable, use [environment-checks.md](references/environment-checks.md) section 10.
2. **Navigate** to affected feature based on JIRA component.
3. **Reproduce** the original bug scenario using Playwright (`browser_click`, `browser_fill_form`, `browser_snapshot`, `browser_wait_for`).
4. **Verify** fix behavior: expected elements present/absent, expected values, no bug-related errors.
5. **CSRF-aware API** (when applicable): `browser_evaluate("fetch('/multicloud/api/v1/<endpoint>', {headers: {'X-CSRFToken': document.cookie.match(/csrf-token=([^;]+)/)?.[1] || ''}}).then(r => r.json())")`.
6. **Save screenshots** to `/tmp/screenshots/verify-<JIRA-KEY>-<step>.png` for JIRA comment.

### Playwright Recovery Protocol

On any Playwright failure: (1) capture error + last `browser_snapshot`, (2) retry once with fresh `browser_navigate`, (3) if retry fails, fall back to 3A evidence only with qualifier = **backend-only**. **Never** declare NOT FIXED based on a Playwright failure alone.

### Regression Spot-Checks

| Risk (from Phase 2b) | Regression scope |
|----------------------|------------------|
| Low, tests in PR | Direct repro only |
| Low, no tests | Direct repro + one adjacent check |
| Medium, tests in PR | Direct repro + shared call sites (up to 3) |
| Medium, no tests | Direct repro + all shared call sites from Phase 2b |
| High (any) | Direct repro + systematic check of ALL call sites from Phase 2b |

### OIDC Note

For `oc login` via browser-obtained token: use the **ID token** (not access token). See [environment-checks.md](references/environment-checks.md) section 9.

---

## Phase 4: Verdict and Optional JIRA Update

### Pre-verdict gate: failure-signature disambiguation

Before finalizing a **NOT FIXED** verdict, check whether the symptom matches a known infrastructure trap. The knowledge base is **file-based in this repo** (there is no `acm-knowledge` MCP):

1. Read `.claude/knowledge/failures/<subsystem>/failure-signatures.md` directly.
2. Cross-reference `.claude/knowledge/diagnostics/diagnostic-traps.md` for matching trap patterns.
3. Match found -> reclassify as **BLOCKED (environment)**.
4. No match -> proceed with NOT FIXED.

This gate applies **only** before NOT FIXED; it does not run for FIXED or BLOCKED verdicts.

### Final Verdict

Read [verification-patterns.md](references/verification-patterns.md) for the full verdict table, evidence tier weights, confidence calculation, verdict report template, and JIRA comment templates.

| Verdict | Qualifier | Condition |
|---------|-----------|-----------|
| **FIXED** | (full) | Code present + UI verified (3A + 3B pass) |
| **FIXED** | (code-only) | Code confirmed, no credentials for UI |
| **FIXED** | (backend-only) | Backend verified, Playwright unavailable/failed |
| **NOT FIXED** | (standard) | Code present + bug still reproduces in Phase 3 |
| **NOT FIXED** | (code review) | Fix is incorrect per Phase 2b |
| **BLOCKED** | (cherry-pick) | Fix not in target branch (main-only) |
| **BLOCKED** | (pipeline lag) | Merged but build predates the merge |
| **BLOCKED** | (environment) | Cluster unhealthy (Phase 2.75 or failure-sig gate) |

Confidence from evidence tier weights (verification-patterns.md): HIGH (>= 0.8, 4+ Tier 1), MEDIUM (0.5-0.79), LOW (< 0.5). Adjustments: Neo4j unavailable -> reduce one level; Phase 3B skipped -> caps per qualifier.

### JIRA Update (user approval required)

**NEVER write to JIRA without explicit user approval.** Presence-only scope MUST NOT offer to close. Show draft to user first.

If approved, use `mcp__jira__add_comment(issue_key, comment, attachment_paths?, inline_attachment_paths?)`. See [verification-patterns.md](references/verification-patterns.md) for JIRA comment templates matching each verdict + qualifier.

---

## Phase 4.5: Post-Verdict Learning

Non-blocking. Never changes or delays the verdict.

**Engram store:** If available, `mcp__engram__engram_remember("Verified <JIRA-KEY>: <verdict> (<qualifier>) on <TAG>. Confidence <LEVEL>. Key finding: <1 sentence>.")`. Skip silently if unavailable.

**Knowledge DB update:** `.claude/knowledge/` is file-based and git-tracked. New failure pattern: read target file first, check for duplicates, surface proposed addition to user. New diagnostic trap: flag for manual review, never auto-append. Follow the repo write protocol.

If Engram or knowledge-DB is unreachable, skip silently.

---

## Hard Rules

1. **main is not release-2.XX.** A PR in `main` is NOT present downstream until cherry-picked to the release branch AND a build is created after that merge.
2. **Full DOWNSTREAM tag in verdicts.** Always include the complete `...-DOWNSTREAM-YYYY-MM-DD-HH-MM-SS`.
3. **Playwright for console/OIDC.** Use Playwright MCP for browser auth.
4. **OIDC ID token** for `oc login`, not access token.
5. **Console proxy: in-page fetch + CSRF.** Use `browser_evaluate` with CSRF header.
6. **oc exec + grep is valid Tier C.**
7. **gh pr list for cherry-pick detection.** `gh pr list --search "ACM-XXXXX" --base release-2.YY`.
8. **No silent scope downgrade.** State every unavailable tier explicitly; use a qualifier.
9. **PR code review is mandatory** before declaring FIXED.
10. **No credential logging.** Never echo, log, or persist passwords or tokens in output.

## Anti-Patterns

- Declaring FIXED without build-tag evidence or without reading the PR diff (Phase 2b).
- Declaring NOT FIXED without the failure-signature check (Phase 4 pre-verdict gate) or on a Playwright failure alone.
- Skipping Phase 2.75 health gate then blaming a broken cluster on the fix.
- Closing a ticket from presence-only scope or silently downgrading scope.
