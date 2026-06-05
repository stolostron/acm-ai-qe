---
name: acm-bug-fix-verifier
description: >-
  Verifies whether a known ACM bug fix has landed on a target environment. Takes
  a JIRA ticket and a cluster, runs a 7-phase pipeline: parallel JIRA/PR/environment
  investigation, three-tier fix presence check (branch reachability, build date,
  code presence), PR code review for fix correctness, Neo4j prerequisite gap
  analysis with heuristic fallback, Playwright-driven UI/API verification, and
  verdict with optional JIRA update. Produces BLOCKED, NOT_FIXED, PRESENT, or
  VERIFIED verdicts with evidence trail.
  TRIGGER: verify bug fix, confirm fix landed, check if fixed, is the bug fixed,
  verify ACM-NNNNN on cluster, test fix on environment.
  DO NOT TRIGGER: hunt for new bugs (use acm-bug-hunter), write test cases
  (use acm-test-case-generator), cluster health check (use acm-hub-health-check),
  PR-only code review (use acm-qe-code-analyzer).
compatibility: >-
  Required: jira MCP, gh CLI.
  Required for UI verification: playwright MCP, console credentials.
  Recommended: neo4j-rhacm MCP (prerequisite gap analysis; degrades to heuristics).
  Optional: acm-search MCP, acm-kubectl MCP, acm-source MCP, oc CLI.
  Run /onboard to configure MCPs.
metadata:
  author: acm-qe
  version: "1.1.0"
  skill-standard: "anthropic-agent-skills-v1"
  category: verification
---

# ACM Bug Fix Verifier

Verifies whether a specific ACM bug fix is present and working in a target environment. Distinct from `acm-bug-hunter` (which hunts for *unknown* bugs) -- this skill confirms whether a *known* bug has been fixed.

## ASK QUESTIONS FIRST

| Category | Questions to Ask |
|----------|------------------|
| **JIRA Key** | "What is the bug JIRA key? (e.g., ACM-12345)" |
| **Environment** | "Which environment? (cluster URL, `oc whoami --show-server`, or ACM version like 2.17)" |
| **Scope** | "Full verification (UI + backend) or fix-presence-only? (default: full)" |
| **Credentials** | "Console password? (needed for UI verification; skip for backend-only)" |

If the user provides a JIRA key and is already `oc login`-ed, proceed without asking further.

## Progressive Disclosure

| Level | Content | When loaded |
|-------|---------|-------------|
| **1 -- Frontmatter** | Description, triggers, compatibility | Always (system prompt) |
| **2 -- This file** | Full workflow, phases 0-4, MCP reference, safety rules | On skill activation |
| **3 -- References** | [verification-patterns.md](references/verification-patterns.md) -- verdict logic, decision tree, evidence scoring | During Phases 2-4 |
| | [environment-checks.md](references/environment-checks.md) -- build tags, OIDC, Neo4j, cherry-pick detection | During Phase 1 |
| | [investigation-notes.md](references/investigation-notes.md) -- design decisions, known limitations | Author reference |

## MANDATORY: Phase Gate Enforcement

On skill start, create tasks for ALL phases:

```
TaskCreate: Phase 0: Intake -- parse JIRA ticket, resolve environment
TaskCreate: Phase 1: Parallel investigation (JIRA + Environment + PR)
TaskCreate: Phase 2: Fix presence assessment (three-tier)
TaskCreate: Phase 2b: PR code review (fix correctness)
TaskCreate: Phase 2.5: Prerequisite gap analysis
TaskCreate: Phase 3: Live verification (Playwright + oc)
TaskCreate: Phase 4: Verdict and optional JIRA update
```

Gate rules:
1. A phase CANNOT be marked `completed` without executing it.
2. Phase 1 subagents run in parallel. All three must complete before Phase 2.
3. Phase 2 produces a preliminary verdict. If BLOCKED, skip Phases 2b, 2.5, and 3.
4. Phase 2b MUST complete before Phase 2.5.
5. Phase 2.5 MUST complete before Phase 3 starts.
6. Phase 3 runs INLINE (not as subagent) due to Playwright MCP limitation.
7. Phase 4 MUST NOT write to JIRA without explicit user approval.

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

### Step 1: Extract JIRA ticket

Parse the JIRA key (e.g., `ACM-12345`) from user input. Use JIRA MCP:

```
mcp__jira__get_issue(issue_key="ACM-12345")
```

Extract:
- **Summary** and **description** (what the bug is)
- **Fix versions** (target ACM release)
- **Status** (should be Resolved/Verified/Closed for verification)
- **Resolution** (should be Fixed or Done)
- **Linked PRs** (from description, comments, or dev panel links)
- **Components** (to determine feature area)

If JIRA MCP is unavailable, stop the pipeline and inform the user.

### Step 2: Resolve target environment

Priority cascade:
1. User-provided cluster URL
2. Current `oc login` session: `oc whoami --show-server 2>/dev/null`
3. Ask the user

After resolving, verify connectivity:
```bash
oc whoami --show-server
oc whoami
```

### Step 3: Detect ACM version on cluster

```bash
oc get mch -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.status.currentVersion}{"\n"}{end}'
```

Read [environment-checks.md](references/environment-checks.md) for the full downstream tag extraction procedure.

### Step 4: Determine verification scope

Compare the JIRA fix version against the detected ACM version. If they don't match, warn the user:

> "JIRA says fix is for ACM 2.13, but cluster is running 2.12.0. Fix may not be present. Continue?"

### Step 5: Resolve console credentials

For UI verification in Phase 3. Priority cascade:
1. Environment variables: `CONSOLE_USER` / `CONSOLE_PASSWORD`
2. User-provided in conversation
3. `kubeadmin` password from `oc extract secret/kubeadmin-password -n kube-system --to=-` (may return bcrypt hash -- unusable)

If no cleartext password is available, Phase 3 runs backend-only. UI verification is skipped with a note.

---

## Phase 1: Parallel Investigation

Launch three subagents in parallel to gather context.

Read [environment-checks.md](references/environment-checks.md) before spawning subagents.

### Subagent 1A: JIRA Deep Dive

Spawn via the Agent tool (`subagent_type: "general-purpose"`). Brief:

- Use JIRA MCP to get the full ticket, all comments, linked issues
- Extract: reproduction steps, affected component, fix description, acceptance criteria
- Find all linked PRs (from comments, description, remote links)
- Search for related bugs: `mcp__jira__search_issues(jql="project = ACM AND issue in linkedIssues('ACM-12345')")`
- Check for QE verification sub-tasks or linked verification tickets
- Return: structured summary with PR list (repo + number), fix description, component, prerequisites

### Subagent 1B: Environment Profile

Spawn via the Agent tool (`subagent_type: "general-purpose"`). Brief:

- Read [environment-checks.md](references/environment-checks.md) for downstream tag extraction
- Discover MCH namespace: `oc get mch -A --no-headers -o custom-columns=NS:.metadata.namespace`
- Extract the DOWNSTREAM build tag (full `...-DOWNSTREAM-YYYY-MM-DD-HH-MM-SS` format)
- Get component image versions relevant to the fix (use component-to-deployment mapping in environment-checks.md)
- Record ACM version, OCP version, node count
- If neo4j-rhacm MCP is available: query prerequisite dependencies (Cypher patterns in environment-checks.md)
- If neo4j-rhacm is unavailable: note for Phase 2.5 heuristic fallback
- Return: cluster profile with build tag, component image tags, parsed dates, dependency map (if Neo4j available)

### Subagent 1C: PR and Cherry-pick Analysis

Spawn via the Agent tool (`subagent_type: "general-purpose"`). Brief:

- For each PR identified from JIRA:
  ```bash
  gh pr view <REPO>#<number> --json state,mergedAt,mergeCommit,baseRefName,title
  ```
- Check if merged to `main` or to `release-2.XX` branch
- Cherry-pick detection (see environment-checks.md section 4):
  ```bash
  gh pr list --repo <REPO> --search "ACM-XXXXX" --base release-2.YY --state merged --json number,title,mergedAt,mergeCommit
  ```
- Check for backport labels and cherry-pick bot comments
- Branch reachability:
  ```bash
  gh api repos/<REPO>/compare/release-2.YY...<merge-sha> --jq '.status'
  ```
- Return: per-PR merge status, target branch, cherry-pick PRs found, merge commit SHAs, merge dates

---

## Phase 2: Fix Presence Assessment

Merge subagent results and determine fix presence using the three-tier model.

Read [verification-patterns.md](references/verification-patterns.md) for the full tier definitions and decision tree.

### Three-Tier Evidence Model

| Tier | Check | Method |
|------|-------|--------|
| **A (Branch)** | Is the merge SHA reachable from the release branch? | `gh api repos/<REPO>/compare/release-<VER>...<SHA>` |
| **B (Build)** | Is the image build date >= PR merge date? | DOWNSTREAM tag date vs `mergedAt` |
| **C (Code)** | Is the fix code present in the running container? | `oc exec deploy/<component> -- grep "<pattern>"` |

### Decision Logic

```
TIER A: Is SHA reachable from release branch?
  |
  +-- FAIL --> Cherry-pick PR exists?
  |              +-- Merged --> Use cherry-pick SHA, re-check Tier A
  |              +-- Open ----> VERDICT: BLOCKED (cherry-pick in progress)
  |              +-- None ----> VERDICT: BLOCKED (file cherry-pick PR)
  |
  +-- PASS --> TIER B: Image date >= PR merge date?
                |
                +-- FAIL ------> VERDICT: NOT_FIXED (rebuild with newer snapshot)
                +-- AMBIGUOUS --> VERDICT: NOT_FIXED (build pipeline race)
                +-- PASS ------> TIER C: Code found in container?
                                   |
                                   +-- PASS ---------> VERDICT: PRESENT
                                   +-- FAIL ---------> VERDICT: NOT_FIXED (rollback?)
                                   +-- UNAVAILABLE --> VERDICT: PRESENT (lower confidence)
```

### Build-Tag Timestamp Gate

When Tier A passes, compare the PR merge timestamp against the cluster's DOWNSTREAM build-tag timestamp (from Phase 1B):

- **PR merged BEFORE build-tag**: fix is in the deployed image. Proceed.
- **PR merged AFTER build-tag**: image predates the fix. Verdict: **NOT_FIXED**.
- **Within 2 hours**: ambiguous (build pipeline race). Treat as NOT_FIXED with note.

See [environment-checks.md](references/environment-checks.md) section 2 for the 2-hour ambiguity window rationale.

### Verdict Matrix

| Tier A (Branch) | Tier B (Build) | Tier C (Code) | Verdict |
|-----------------|---------------|--------------|---------|
| FAIL (main-only, no cherry-pick) | any | any | **BLOCKED** |
| PASS | FAIL | any | **NOT_FIXED** |
| PASS | PASS | FAIL | **NOT_FIXED** |
| PASS | PASS | PASS | **PRESENT** |
| PASS | PASS | UNAVAILABLE | **PRESENT** (lower confidence) |
| PASS | UNAVAILABLE | PASS | **PRESENT** |

If Phase 2 yields BLOCKED: skip Phases 2b, 2.5, and 3. Proceed directly to Phase 4.

---

## Phase 2b: PR Code Review (Fix Correctness)

**Purpose**: Understand what the code change actually does so that Phase 3 verification is informed and thorough. A fix being "in the build" is necessary but not sufficient -- the code must logically address the root cause.

### Step 1 -- Read the diff

Delegate PR diff analysis to the **`../../test-case-gen/acm-qe-code-analyzer/SKILL.md`** sibling skill. Spawn a subagent with:
- PR number and repo from Phase 1C
- Instruction: focus on changed files related to the JIRA component -- skip full test-impact analysis, return only the structural summary (what files changed, what logic changed, shared call sites)

If the code analyzer skill is unavailable or the PR is small (< 5 files), use `gh pr diff` directly:

```bash
gh pr diff <PR_NUMBER> --repo <REPO>
```

For large PRs, focus on:
- The file(s) directly related to the bug (e.g. the component/page mentioned in JIRA)
- Test files -- do they cover the reported scenario?

### Step 2 -- Assess fix correctness

| Question | How to answer |
|----------|---------------|
| Does the change address the root cause described in JIRA? | Compare PR diff against bug description / dev comments |
| Is the change minimal and scoped? | Large refactors alongside a one-line fix -> higher risk |
| Are tests added/updated for the fix? | Check if test expectations match the expected behavior from JIRA |
| Could the change break adjacent functionality? | Check if modified code is shared by other call sites |

### Step 3 -- Risk and side-effect assessment

Classify:
- **Low risk**: Single-value change, default removed/added, CSS-only fix with test coverage.
- **Medium risk**: Logic change affecting shared utility, API parameter addition, refactored flow.
- **High risk**: Large refactor bundled with fix, changed function signatures used by multiple callers.

For medium/high risk: note specific areas to watch during UI verification (Phase 3). For example, if a utility function was refactored, verify both the originally-broken page AND any other page that uses the same utility.

### Step 4 -- Record findings

Add to the evidence bundle:
- Fix summary (what the code change actually does, in plain language).
- Risk level.
- Any areas to spot-check during verification beyond the direct repro.

If the code review reveals the fix is **clearly wrong** (e.g. addresses wrong component, introduces obvious null-ref), verdict **NOT_FIXED (code review)** without needing UI verification. Proceed directly to Phase 4.

---

## Phase 2.5: Prerequisite Gap Analysis

Before live verification, check whether the fix has unmet prerequisites that could cause false negatives.

### With Neo4j (preferred)

Read [environment-checks.md](references/environment-checks.md) sections 5-6 for Cypher patterns and heuristic table.

Query the component dependency graph:
```cypher
MATCH (t)-[:DEPENDS_ON]->(req)
WHERE t.label CONTAINS '<component>'
RETURN req.label, req.subsystem
```

For each dependency: verify pod health and image currency via `oc get deploy`.

### Without Neo4j (heuristic fallback)

Read [environment-checks.md](references/environment-checks.md) section 6 for the static dependency table and section 7 for oc-based discovery.

1. Check heuristic dependency table (7 common ACM component chains)
2. Parse operator CSV dependencies: `oc get csv -n $MCH_NS -o json | jq ...`
3. Check pod start time vs build tag timestamp
4. Search JIRA comments for prerequisite mentions

### Gap Table Output

| Prerequisite | Status | Evidence |
|-------------|--------|----------|
| [dependency] | HEALTHY / DEGRADED / MISSING | [image date, pod status] |

### User Approval Gate

If gaps are found that require cluster modification (restart pod, patch config):

> "Found prerequisite gaps. Options:
> 1. Proceed anyway (results may show false negatives)
> 2. Stop and resolve prerequisites first
> 3. Skip UI verification, do backend-only check"

**NEVER** create, patch, or delete any cluster resource without explicit user approval.

If no gaps: proceed to Phase 3 automatically.

---

## Phase 3: Live Verification

Verify the fix is working on the live cluster.

**IMPORTANT: This phase runs INLINE in the orchestrator -- do NOT spawn a subagent.** Playwright MCP tools are not accessible from within Claude Code subagents. This is a known platform limitation (see [investigation-notes.md](references/investigation-notes.md) section D1).

### Path A: Backend Verification (always runs)

Using `oc` CLI and optionally acm-search / acm-kubectl MCPs:

1. **Resource state**: `oc get` resources affected by the bug
2. **API behavior**: verify API endpoints return correct responses
3. **Log inspection**: `oc logs deploy/<component> --tail=100` -- check for error patterns from the JIRA
4. **Tier C evidence**: `oc exec deploy/<component> -- grep "<fix-indicator>" <path>` when the fix changes specific files

### Path B: UI Verification (requires Playwright + credentials)

Skip if no console credentials are available. Set `AUTH_STATUS=no-credentials` and proceed with backend-only results.

**Step 1: Authenticate**

Resolve the console URL:
```bash
oc get route multicloud-console -n $MCH_NS -o jsonpath='{.spec.host}'
```

Follow the console auth procedure in `${CLAUDE_SKILL_DIR}/../../test-case-gen/acm-test-case-generator/references/console-auth.md`. If that sibling is unavailable, use the inline minimum procedure in [environment-checks.md](references/environment-checks.md) section 10.

Use Playwright MCP for form-based OAuth login:
1. `browser_navigate` to the console URL
2. Detect IDP selection or direct login form
3. Fill credentials with `browser_fill_form` and submit with `browser_click`
4. Verify authentication via `browser_snapshot` (console nav elements visible)

If auth fails: set `AUTH_STATUS=failed`, proceed with backend-only results.

**Step 2: Navigate to affected feature**

Based on the JIRA component and fix description, navigate to the relevant console page.

**Step 3: Reproduce the original bug scenario**

Follow the JIRA reproduction steps using Playwright:
- `browser_click`, `browser_fill_form` for user interactions
- `browser_snapshot` after each significant action
- `browser_wait_for` between actions for page loads

**Step 4: Verify fix behavior**

Check that the bug no longer manifests:
- Expected elements present / absent
- Expected text/values appear
- No error messages matching the bug description

**Step 5: Regression spot-checks (informed by Phase 2b)**

After confirming the direct fix works, run targeted regression checks based on Phase 2b findings:

- **If Phase 2b identified shared code** (e.g. a utility function was refactored): verify the same flow on another page/component that uses it.
- **If Phase 2b identified a default/value removal**: verify the manual path still works (e.g. if a checkbox default was removed, manually check the box and confirm the feature still functions when enabled).
- **If Phase 2b identified test coverage gaps**: manually exercise the uncovered path in the UI.
- **If Phase 2b rated LOW risk with good test coverage**: skip regression checks -- direct repro is sufficient.

The regression scope should be proportional to the risk level:
- **Low risk**: Direct repro only (Steps 3-4 are sufficient).
- **Medium risk**: Direct repro + 1-2 adjacent spot-checks on shared code paths.
- **High risk**: Direct repro + systematic check of all call sites identified in Phase 2b.

**Step 6: CSRF-aware API verification (when applicable)**

For bugs involving API behavior through the console proxy, use in-page `fetch` with CSRF header:

```
browser_evaluate("fetch('/multicloud/api/v1/<endpoint>', {headers: {'X-CSRFToken': document.cookie.match(/csrf-token=([^;]+)/)?.[1] || ''}}).then(r => r.json())")
```

### Verdict Upgrade

If Phase 2 verdict was PRESENT and Phase 3 confirms the bug behavior is resolved:
- Backend pass + UI pass: upgrade to **VERIFIED**
- Backend pass only (UI skipped): keep **PRESENT** with note

### OIDC Note

For `oc login` via browser-obtained token: the OIDC flow yields an **ID token** (not access token). Use `oc login --token=<id-token>` if re-authentication is needed. See [environment-checks.md](references/environment-checks.md) section 9.

---

## Phase 4: Verdict and Optional JIRA Update

### Step 1: Determine Final Verdict

Read [verification-patterns.md](references/verification-patterns.md) for the full verdict table and evidence scoring.

| Verdict | Condition | Recommended Action |
|---------|-----------|-------------------|
| **BLOCKED** | Fix in main but not in release branch (no merged cherry-pick) | File cherry-pick PR to release-2.XX |
| **NOT_FIXED** | Fix not present on environment (image predates merge, code absent) | Rebuild with newer snapshot |
| **PRESENT** | Fix code confirmed via branch + build evidence | Complete live verification for full confidence |
| **VERIFIED** | PRESENT + live verification confirms bug behavior resolved | Close JIRA ticket |

### Step 2: Build Evidence Report

The report MUST include (see [verification-patterns.md](references/verification-patterns.md) for the template):

1. **JIRA ticket**: key, summary, fix version
2. **Cluster**: API URL, ACM version, full DOWNSTREAM build tag (`...-DOWNSTREAM-YYYY-MM-DD-HH-MM-SS`)
3. **PR status**: per-PR merge state, branch, cherry-pick status
4. **Evidence tiers**: A/B/C results with detail
5. **Live verification**: backend + UI results (or skip reason)
6. **Prerequisites**: gap table (if Phase 2.5 found issues)
7. **Verdict**: BLOCKED / NOT_FIXED / PRESENT / VERIFIED
8. **Confidence**: 0.00-1.00 (see scoring table in verification-patterns.md)
9. **Recommended action**

### Step 3: Optional JIRA Update (user approval required)

If verdict is VERIFIED, offer to update the JIRA ticket:

> "Verification complete: VERIFIED. Update JIRA?
> - Add verification comment with evidence summary
> - Transition to Verified (if workflow allows)
>
> Approve? (yes/no)"

**NEVER write to JIRA without explicit user approval.** This includes comments, transitions, labels, and field changes.

If approved, use JIRA MCP (param is `comment`, not `body`). For QE verify with a screenshot, pass `attachment_paths` and `inline_attachment_paths` so the image appears inline in the comment:
```
mcp__jira__add_comment(
  issue_key="ACM-12345",
  comment="Verified on <DOWNSTREAM-tag> (CSV <version>), closing the ticket.",
  attachment_paths=["/absolute/path/to/screenshot.png"],
  inline_attachment_paths=["/absolute/path/to/screenshot.png"],
)
```

See [verification-patterns.md](references/verification-patterns.md) for the full JIRA comment template.

### Step 4: Cleanup

- Delete any temporary files created during verification
- If a temporary kubeconfig was created, remove it
- Report all actions taken

---

## MCP and Tool Reference

### JIRA MCP (`jira`) -- Required

| Tool | Phase | Purpose |
|------|-------|---------|
| `get_issue(issue_key)` | 0, 1A | Full ticket details, comments, links |
| `search_issues(jql)` | 1A | Linked bugs, verification tickets |
| `add_comment(issue_key, comment, attachment_paths?, inline_attachment_paths?)` | 4 | Verification comment; inline screenshot when paths provided (user approval required) |
| `add_issue_attachments(issue_key, file_paths)` | 4 | Issue-level attachments only (no inline comment) |

### Playwright MCP (`playwright`) -- Required for UI verification

| Tool | Phase | Purpose |
|------|-------|---------|
| `browser_navigate(url)` | 3 | Navigate to console page |
| `browser_snapshot()` | 3 | Capture page state for evidence |
| `browser_click(ref)` | 3 | Interact with UI elements |
| `browser_fill_form(ref, value)` | 3 | Fill form fields |
| `browser_wait_for(time)` | 3 | Wait for page loads |
| `browser_evaluate(expression)` | 3 | CSRF fetch for API verification |

### Neo4j RHACM MCP (`neo4j-rhacm`) -- Recommended

| Tool | Phase | Purpose |
|------|-------|---------|
| `read_neo4j_cypher(query)` | 1B, 2.5 | Component dependency queries |

See [environment-checks.md](references/environment-checks.md) sections 5-6 for Cypher patterns and caveats.

### Optional MCPs

| MCP | Tool | Phase | Purpose |
|-----|------|-------|---------|
| acm-search | `find_resources(...)` | 1B, 3 | Fleet-wide resource queries |
| acm-kubectl | `clusters()`, `kubectl(cmd, cluster)` | 1B, 3 | Managed cluster inspection |
| acm-source | `search_code(query, repo, scope)` | 1C, 3 | Fix-related code search |

### CLI Tools

| Tool | Phase | Purpose |
|------|-------|---------|
| `oc get/describe/logs/exec` | 0-3 | Cluster state, pod inspection, Tier C evidence |
| `oc whoami --show-server` | 0 | Verify cluster connectivity (mandatory after kubeconfig changes) |
| `gh pr view/list` | 1C, 2 | PR status, cherry-pick detection |
| `gh api repos/.../compare` | 2 | Branch reachability check |

---

## Subagent Usage

### Phase 1 Subagents (Parallel)

Spawn via Agent tool (`subagent_type: "general-purpose"`):
- **JIRA Deep Dive (1A)** -- JIRA MCP access for ticket investigation
- **Environment Profile (1B)** -- oc CLI + optional Neo4j for cluster inspection
- **PR/Cherry-pick Analysis (1C)** -- gh CLI for PR status and cherry-pick detection

### Phase 2b Subagent (Optional)

For large PRs (5+ files), spawn a subagent following **`../../test-case-gen/acm-qe-code-analyzer/SKILL.md`** process. For small PRs, run `gh pr diff` inline in the orchestrator.

### Phase 3 (NO SUBAGENT)

Phase 3 runs **inline** in the orchestrator. Playwright MCP tools are not accessible from subagents. This is a known platform limitation also observed in `acm-test-case-generator` Phase 5.

---

## Hard Rules

From the handoff document (§6). These are non-negotiable.

1. **main is not release-2.XX.** A PR merged to `main` is NOT considered present on a downstream build until merged/cherry-picked to the release branch AND a build is created after that merge. Verdict: BLOCKED.
2. **Full DOWNSTREAM tag in verdicts.** When the cluster was read, always include the complete `...-DOWNSTREAM-YYYY-MM-DD-HH-MM-SS` in the verdict table. Never abbreviate.
3. **Playwright for console/OIDC.** Use Playwright MCP for browser authentication. Do not prescribe non-Playwright browser tools for login-heavy flows.
4. **OIDC ID token for oc login.** When extracting tokens from the browser session, use the ID token, not the access token.
5. **Console proxy: in-page fetch + CSRF.** For console API calls, use `browser_evaluate` with `fetch()` and include the CSRF header.
6. **oc exec + grep is valid Tier C.** Grepping for code patterns inside running containers is acceptable evidence.
7. **gh pr list for cherry-pick detection.** Use `gh pr list --search "ACM-XXXXX" --base release-2.YY` to find cherry-pick PRs.
8. **No silent scope downgrade.** If a verification tier fails or is unavailable, state it explicitly in the verdict. Never silently omit a tier or claim higher confidence than evidence supports.
9. **PR code review is mandatory.** Before declaring FIXED/VERIFIED, review the actual code diff (`gh pr diff`) to confirm the change is correct, minimal, and doesn't introduce side effects. A fix being "in the build" is necessary but not sufficient.

---

## Safety Rules

| Rule | Detail |
|------|--------|
| Read-only cluster access | `oc get`, `oc describe`, `oc logs`, `oc exec` (grep only). Never `oc apply/create/delete/patch/scale`. |
| No JIRA writes without approval | Draft comment shown to user first. Never auto-transition. |
| No cluster mutations without approval | If prerequisites need fixing, show proposed action first. |
| No silent scope downgrade | If UI verification is skipped, state the reason and adjust confidence. |
| No credential logging | Never echo, log, or persist passwords or tokens in output. |
| Full DOWNSTREAM tag | Always include the complete tag in verdicts for traceability. |

---

## Examples

### Example 1: VERIFIED verdict

```
User: verify ACM-30001 on https://api.slot03.example.com:6443

Phase 0: ACM-30001 -- "GRC policy table shows wrong compliance count"
         Cluster: slot03, ACM 2.12.1, DOWNSTREAM-2026-05-01-12-00-00
Phase 1: PR #4521 merged to release-2.12 on 2026-04-28
         Image date 2026-05-01 >= merge date 2026-04-28
Phase 2: Tier A PASS, Tier B PASS, Tier C PASS -> PRESENT
Phase 2b: gh pr diff #4521 -- fix corrects count aggregation logic.
          Risk: LOW (single function, test updated). No regression spots needed.
Phase 3: Backend -- grc-ui pod running, no errors
         UI -- compliance count correct after policy creation
Phase 4: Verdict: VERIFIED (confidence: 0.95)
         JIRA update offered -> user approves -> comment added
```

### Example 2: BLOCKED verdict

```
User: is ACM-30002 fixed on my cluster?

Phase 0: ACM-30002 -- "Search returns stale results after import"
         Cluster: current oc login, ACM 2.13.0
Phase 1: PR #892 merged to main. Cherry-pick PR #901 open targeting release-2.13.
Phase 2: Tier A FAIL (main-only). Cherry-pick not merged -> BLOCKED.
         (Phase 2b, 2.5, 3 skipped)
Phase 4: Verdict: BLOCKED
         "Fix in main. Cherry-pick PR #901 to release-2.13 is open.
          Monitor for merge, then re-verify."
```

### Example 3: NOT_FIXED (code review)

```
User: confirm fix for ACM-30003 on my 2.16 hub

Phase 0: ACM-30003 -- "Console crash on credentials page"
         Cluster: hub-az, ACM 2.16.2, DOWNSTREAM-2026-04-15-08-30-00
Phase 1: PR #1234 merged to release-2.16 on 2026-04-20.
         Image date 2026-04-15 < merge date 2026-04-20.
Phase 2: Tier A PASS, Tier B FAIL (image predates fix) -> NOT_FIXED.
Phase 4: Verdict: NOT_FIXED
         "PR merged to release-2.16 but image was built 5 days before merge.
          Rebuild environment with snapshot newer than 2026-04-20."
```

### Example 4: VERIFIED with regression check (medium risk)

```
User: verify ACM-30004 on bm12

Phase 0: ACM-30004 -- "RBAC role table shows wrong permission count"
         Cluster: bm12, ACM 2.17.0, DOWNSTREAM-2026-05-18-10-00-00
Phase 1: PR #5678 merged to release-2.17 on 2026-05-15.
Phase 2: Tier A PASS, Tier B PASS -> PRESENT
Phase 2b: gh pr diff #5678 -- refactored shared utility `aggregatePermissions()`.
          Risk: MEDIUM (utility used by 3 pages). Regression spots: role detail page, user detail page.
Phase 2.5: No gaps (RBAC prereqs met).
Phase 3: Direct repro passes (role table correct).
         Regression: role detail page OK, user detail page OK.
Phase 4: Verdict: VERIFIED (confidence: 0.92)
```

---

## Troubleshooting

| Symptom | Cause | Action |
|---------|-------|--------|
| JIRA MCP returns 401 | Expired token | Re-authenticate: check `mcp/.external/jira-mcp-server/.env` |
| `gh pr view` fails | Not authenticated or wrong repo | Run `gh auth status`; verify repo org (stolostron vs open-cluster-management) |
| Playwright login fails | Wrong credentials or IDP mismatch | Check IDP names: `oc get oauth cluster -o jsonpath='{.spec.identityProviders[*].name}'` |
| Neo4j returns empty results | Graph not imported or schema drift | Fall back to heuristics (see Phase 2.5) |
| Build tag not found | Community build or non-standard install | Use `oc get csv` createdAt as fallback; note reduced confidence |
| Cherry-pick detection misses | PR title doesn't contain JIRA key | Check PR descriptions and commit messages manually |
| CSRF fetch returns 403 | Session expired or wrong token path | Re-authenticate via Playwright |

---

## Scope Boundary: acm-bug-fix-verifier vs acm-bug-hunter

| Dimension | This skill (verifier) | acm-bug-hunter |
|-----------|----------------------|----------------|
| **Input** | JIRA ticket (known bug) | Test case (known test) |
| **Goal** | Confirm a specific fix landed | Find unknown bugs in implementation |
| **Method** | PR tracking + three-tier evidence + live verification | 10-dimension adversarial investigation |
| **Output** | BLOCKED / NOT_FIXED / PRESENT / VERIFIED | Bug report with CONFIRMED / POTENTIAL findings |
| **Cluster writes** | None (read-only) | Probe resources in dedicated namespace |
| **JIRA writes** | Optional, with approval | None |

If the user says "hunt for bugs" or "stress test this feature", use `acm-bug-hunter`.
If the user says "verify this fix" or "is ACM-12345 fixed", use this skill.
