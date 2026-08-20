# Verification Patterns

Decision trees and evidence model for ACM bug fix verification. Referenced by SKILL.md Phases 2 and 4.

---

## Verdict Model -- 3 Verdicts x Qualifiers

Every verification resolves to one of three verdicts, each carrying a qualifier that records *why* and drives the JIRA action. This replaces the older linear model (BLOCKED -> NOT_FIXED -> PRESENT -> VERIFIED); see `investigation-notes.md` D4 for the rationale. This is the canonical verdict model; the verdict + qualifier set must match the Phase 4 verdict table in SKILL.md exactly (that table adds operational "Recommended Action" detail).

| Verdict | Qualifier | When | JIRA Action |
|---------|-----------|------|-------------|
| **FIXED** | (full) | Code present + UI verified (Phase 3A + 3B pass) | Close ticket |
| **FIXED** | (code-only) | Code confirmed, UI not possible (no credentials) | Close with note |
| **FIXED** | (backend-only) | Backend verified, Playwright unavailable/failed | Close with note |
| **NOT FIXED** | (standard) | Bug still reproduces in Phase 3B | Reopen |
| **NOT FIXED** | (code review) | Fix is incorrect per Phase 2b analysis | Reopen with PR feedback |
| **BLOCKED** | (cherry-pick) | Fix not in target branch (main-only) | Comment, leave open |
| **BLOCKED** | (pipeline lag) | Merged to branch but build predates the fix | Comment, leave open |
| **BLOCKED** | (environment) | Cluster unhealthy for valid verification (Phase 2.75 or failure-sig gate) | Comment, leave open |

---

## Three-Tier Evidence Model

### Tier A — Branch Reachability (git-level)

Checks whether the PR's merge commit SHA is reachable from the environment's release branch.

```bash
gh api repos/<REPO>/compare/release-<VER>...<MERGE_SHA> --jq '.status'
```

| `status` value | Meaning | Tier A result |
|---------------|---------|---------------|
| `behind` | SHA is an ancestor of the release branch tip | PASS |
| `identical` | SHA equals the release branch tip | PASS |
| `ahead` | SHA is a descendant — not reachable from release branch | FAIL |
| `diverged` | Branches diverged — not directly reachable | FAIL |

When Tier A fails: search for a cherry-pick PR (see `environment-checks.md` cherry-pick detection). If a merged cherry-pick is found, re-run Tier A using the cherry-pick's merge commit SHA.

### Tier B — Build Date Comparison (24-hour pipeline-lag model)

Compares the PR merge timestamp against the environment's image build date.

1. Get PR merge date: `gh pr view <N> --repo <REPO> --json mergedAt --jq '.mergedAt'`
2. Get image tag date: parse the DOWNSTREAM tag (see `environment-checks.md` downstream tag extraction)
3. Compare (both normalized to UTC):
   - **Image date < PR merge date** (image clearly predates the merge): **FAIL** -> verdict **BLOCKED (pipeline lag)**, not NOT FIXED. The fix is in the branch; the build is just stale. Action: rebuild/redeploy with a snapshot newer than the merge.
   - **Image date >= PR merge date**: the build *could* include the fix. When Tier C is available, confirm directly. When Tier C is unavailable, grade by the merge->build gap (ACM downstream builds run several hours, so a small positive gap does not guarantee inclusion):

| Gap (build_date − merge_date) | Fix in build? | Action |
|-------------------------------|---------------|--------|
| 0-6h | NO (likely) | Build probably started before the merge landed. Get Tier C or a newer build. |
| 6-12h | MAYBE | Ambiguous. Strongly recommend a Tier C grep before verifying. |
| 12-24h | LIKELY | Probably included. Confirm with Tier C if possible. |
| 24h+ | YES | Enough time for the build to include the merge. Proceed. |

The graduated window accounts for CI pipeline queuing and build time (~30-90 min for ACM downstream builds), git merge to image registry publish delay, and timezone conversion edge cases. This model must read identically in `environment-checks.md` section 2.

### Tier C — Code Presence (strongest evidence)

Confirms the actual code change exists in the running container.

1. Identify a unique pattern from the PR diff: a new function name, error string, config key, or CSS class that did not exist before the fix.
2. Locate the component's pod:
   ```bash
   oc get deploy <component-deploy> -n <mch-ns> -o jsonpath='{.spec.template.spec.containers[0].name}'
   ```
3. Grep for the pattern:
   ```bash
   oc exec deploy/<component-deploy> -n <mch-ns> -- grep -rl "<unique-pattern>" /path/to/files 2>/dev/null
   ```

| Container type | Grep target | Notes |
|---------------|-------------|-------|
| Node.js / JS bundles | `/opt/app-root/src/public/` or `/app/` | Bundled JS is grep-friendly |
| Go binaries | Limited — try `strings` if available | Often no shell; Tier C may be UNAVAILABLE |
| Java (Spring) | `/app/classes/` or extracted JAR paths | Class files may need `strings` |
| CRD-only change | `oc get crd <name> -o yaml \| grep <pattern>` | No pod exec needed |
| Webhook-only change | `oc get validatingwebhookconfigurations -o yaml \| grep <pattern>` | No pod exec needed |

| Tier C result | Meaning |
|--------------|---------|
| PASS | Pattern found in running container |
| FAIL | Pattern not found (stale build, rollback, or wrong grep target) |
| UNAVAILABLE | Cannot exec into pod (RBAC, no shell, distroless image) |

---

## Decision Tree

```
START: Have JIRA key + environment
  |
  v
PHASE 1: Gather JIRA details, PR info, environment profile
  |
  v
TIER A: Is merge SHA reachable from release branch?
  |
  +-- NO --> Cherry-pick PR exists (merged)?
  |            |
  |            +-- NO --> Cherry-pick PR exists (open/draft)?
  |            |            |
  |            |            +-- YES --> VERDICT: BLOCKED (cherry-pick)
  |            |            |           (note: cherry-pick in progress)
  |            |            |
  |            |            +-- NO ---> VERDICT: BLOCKED (cherry-pick)
  |            |                        (action: file cherry-pick PR)
  |            |
  |            +-- YES --> Use cherry-pick SHA, restart Tier A
  |
  +-- YES --> TIER B: Image build date vs PR merge date? (24-hour model)
               |
               +-- image predates merge --> VERDICT: BLOCKED (pipeline lag)
               |                             (action: rebuild with newer snapshot;
               |                              NOT "reopen" -- the fix is in the branch)
               |
               +-- in build (>= merge) --> TIER C: Code found in running container?
                                             |
                                             +-- PASS ---------> Fix IN BUILD -> Phase 2b
                                             |
                                             +-- UNAVAILABLE --> Fix in build (branch+build)
                                             |                    -> Phase 2b (confidence lower)
                                             |
                                             +-- FAIL ---------> Red flag: code absent despite
                                                                  branch+build. Re-check grep target
                                                                  + acm-source (Phase 3A). If truly
                                                                  absent: BLOCKED (pipeline lag).
  |
  v
PHASE 2b: PR code review -- is the fix correct?
  |
  +-- clearly wrong --> VERDICT: NOT FIXED (code review)   [skip 2.5/2.75/3]
  +-- correct ------->  PHASE 2.5 (prereq gaps) -> PHASE 2.75 (health gate)
                          |
                          +-- subsystem critically degraded --> VERDICT: BLOCKED (environment)  [skip 3]
                          +-- healthy --------------------------> PHASE 3: 3A backend + 3B UI
                                                                    |
                                                                    +-- 3B skipped (no creds) ---> FIXED (code-only)
                                                                    +-- 3B skipped (Playwright) -> FIXED (backend-only)
                                                                    +-- bug behavior gone -------> FIXED (full)
                                                                    +-- bug still reproduces ----> PHASE 4 pre-verdict gate:
                                                                                                    known trap / failure sig?
                                                                                                     +-- match --> BLOCKED (environment)
                                                                                                     +-- none --> NOT FIXED (standard)
```

**Note on the FAIL branch of Tier C:** code absent despite Tier A + Tier B passing is a red flag (stale pod, wrong grep target, or a change dropped in a merge conflict), not an automatic NOT FIXED. Re-check the grep target and cross-validate with acm-source in Phase 3A before concluding; if the code is genuinely absent from the running image, the correct verdict is **BLOCKED (pipeline lag)**.

---

## Evidence Tier Weights and Confidence

Confidence is derived from the evidence achieved, not from a fixed combination table. Per `diagnostics/evidence-tiers.md` in the knowledge DB. This is the canonical source for evidence tier weights. SKILL.md Phase 4 references this file rather than duplicating the table.

| Evidence | Tier | Weight | Source |
|----------|------|--------|--------|
| Branch match (Tier A) | 1 | 1.0 | `gh api repos/.../compare` |
| Build date >= merge date (Tier B) | 1 | 1.0 | DOWNSTREAM tag vs `mergedAt` |
| Code grep in container (Tier C) | 1 | 1.0 | `oc exec` |
| acm-source cross-validation | 1 | 1.0 | acm-source MCP `search_code` |
| UI repro passes (Phase 3B) | 1 | 1.0 | Playwright |
| PR code review positive (Phase 2b) | 2 | 0.5 | `gh pr diff` analysis |
| Backend logs clean (Phase 3A) | 2 | 0.5 | `oc logs` |

**Confidence = Σ achieved weights ÷ maximum possible weight:**
- **HIGH** (>= 0.8): 4+ Tier 1 evidences achieved.
- **MEDIUM** (0.5-0.79): 2-3 Tier 1 evidences.
- **LOW** (< 0.5): mostly Tier 2 / inference.

Report confidence as a level, e.g. `FIXED (full, confidence: HIGH -- 5 Tier 1 evidences)`.

### Confidence Adjustments (reduce one level -- never a silent drop)

- **Neo4j unavailable for Phase 2.5 prerequisites**: reduce confidence one level (heuristic-table fallback) or two levels (oc-only discovery fallback). See `environment-checks.md` section 6.
- **UI scope downgrade**: if the bug is UI-specific (console rendering, form behavior, display issue) and UI verification was skipped (no Playwright -> backend-only, or no credentials -> code-only), confidence is capped by the qualifier and the verdict report MUST state:

  > "UI verification was skipped (reason: [no credentials / Playwright unavailable]). Backend checks passed but cannot confirm UI-specific behavior."

Never silently claim FIXED (full) from backend-only evidence when the bug category is UI -- use the code-only / backend-only qualifier.

---

## Verdict Table Template

Use this format for Phase 4 output:

```markdown
## Bug Fix Verification Report

| Field | Value |
|-------|-------|
| JIRA | ACM-XXXXX |
| Summary | [bug title from JIRA] |
| Environment | [cluster API URL] |
| Image Tag | [full tag including DOWNSTREAM timestamp] |
| PR | [org/repo]#[number] (merged [ISO date]) |
| Cherry-pick | [org/repo]#[number] or "None found" or "N/A (direct merge)" |
| Release Branch | release-2.XX |
| **Verdict** | **[FIXED / NOT FIXED / BLOCKED]** |
| **Qualifier** | **[full / code-only / backend-only / standard / code review / cherry-pick / pipeline lag / environment]** |
| Confidence | [HIGH / MEDIUM / LOW] (N Tier 1 evidences) |

### Evidence

| Tier | Check | Result | Detail |
|------|-------|--------|--------|
| A (Branch) | SHA reachable from release-2.XX | PASS / FAIL | [gh api compare output] |
| B (Build) | Image date >= PR merge date | PASS / BLOCKED (pipeline lag) | [24-hour-model gap] |
| C (Code) | Code pattern in running container | PASS / FAIL / UNAVAILABLE | [grep output or reason] |
| acm-source | Fix string present at deployed version | PASS / FAIL / UNAVAILABLE | [search_code result] |
| 3A Backend | Resource/log state matches fix | PASS / FAIL / SKIPPED | [oc evidence] |
| 3B UI | Bug behavior resolved | PASS / FAIL / SKIPPED (qualifier) | [Playwright evidence or skip reason] |

### Environment Health Gate (Phase 2.75)

| Subsystem | Result | Evidence |
|-----------|--------|----------|
| [bug subsystem] | HEALTHY / MINOR / CRITICAL | [trap checks: MCH phase, pod status] |

### Prerequisites (Phase 2.5)

| Component | Status | Evidence |
|-----------|--------|----------|
| [dependency] | HEALTHY / DEGRADED / MISSING | [image date, pod status] |

### Recommended Action

[Based on verdict + qualifier -- see the verdict model above]
```

---

## Edge Cases

**Multiple PRs for one JIRA:** Some bugs require multiple PRs across different repos (e.g., backend + frontend). Verify ALL linked PRs independently. Classify each as PRIMARY / RELATED / TEST-ONLY, and order verification by dependency (upstream/backend before consumer/frontend -- use `neo4j-rhacm` when available, otherwise the fallback ordering); see SKILL.md Phase 2 "Multi-PR Fixes." ALL PRIMARY PRs must pass Tier A/B. The final verdict is the WORST across all PRs: if one PR is FIXED and another is BLOCKED, the overall verdict is BLOCKED.

**Open cherry-pick PR (not yet merged):** Verdict is BLOCKED with a note that a cherry-pick is in progress. Include the cherry-pick PR number and its current state (draft, review, approved).

**No DOWNSTREAM tag prefix:** Some environments run upstream/community images (`quay.io/stolostron/...`) or custom builds without the DOWNSTREAM date format. Tier B is UNAVAILABLE. Fall back to MCH version heuristic: parse `X.Y.Z-NNN` build number and compare against known nightly cadence.

**CRD-only or webhook-only change:** No application pod to exec into. Tier C uses:
```bash
oc get crd <crd-name> -o yaml | grep "<pattern>"
```

**PR merged to release branch directly (no cherry-pick needed):** Some repos merge directly to the release branch. In this case, Tier A passes on the first check, and "Cherry-pick" in the verdict table shows "N/A (direct merge)".

**Backport to multiple release branches:** If the environment could be running any of several versions, ask the user to confirm the exact version. Verify against that specific release branch only.

---

## JIRA Comment Templates

Use the template matching the verdict + qualifier. Prefer a one-line QE close comment for FIXED verdicts.

| Verdict + Qualifier | Comment template |
|---------------------|-----------------|
| **FIXED (full)** | `Verified on <TAG> (CSV <VER>), closing the ticket.` |
| **FIXED (code-only)** | `Verified (code-only) on <TAG> (CSV <VER>), closing the ticket. Note: UI verification not possible (no credentials). Fix confirmed via branch match + code grep + PR review.` |
| **FIXED (backend-only)** | `Verified (backend-only) on <TAG> (CSV <VER>), closing the ticket. Note: UI verification incomplete (Playwright failure). Backend confirmed via oc exec + log inspection.` |
| **NOT FIXED** | `Re-tested on <TAG> (CSV <VER>): bug still reproduces. [standard: repro steps below. / code review: PR #<N> does not address root cause -- <reason>.] Reopening.` |
| **BLOCKED (cherry-pick)** | `Fix present in <main / PR #<N>> but not on release-2.XX. Cherry-pick PR needed.` |
| **BLOCKED (pipeline lag)** | `PR #<N> merged to release-2.XX on <date>, but this build (<TAG>) predates the merge. Rebuild with newer snapshot, then re-verify.` |
| **BLOCKED (environment)** | `Could not validly verify on <TAG>: <subsystem> is degraded (<finding>). Re-verify after cluster is healthy.` |

Attach screenshots **inline** via `add_comment(attachment_paths, inline_attachment_paths)` (same path in both lists). Do not add `!filename|thumbnail!` wiki lines (the MCP appends them).

For detailed evidence, use the expanded template:

```
h3. QE Verification - [VERDICT] ([QUALIFIER])

*Cluster:* [api-url]
*ACM Version:* [version] ([FULL_DOWNSTREAM_TAG])
*Verified:* [date]

*Fix Presence:*
- PR #[number]: [merged to release-2.XX | cherry-pick #[cp-number] merged]
- Evidence tiers: A=[PASS/FAIL] B=[PASS/BLOCKED-pipeline-lag] C=[PASS/FAIL/UNAVAILABLE] acm-source=[PASS/FAIL/UNAVAILABLE]

*Environment Health Gate:* [HEALTHY / MINOR / CRITICAL]

*Live Verification:*
- Backend (3A): [PASS/FAIL/SKIPPED] - [detail]
- UI (3B): [PASS/FAIL/SKIPPED (qualifier)] - [detail]

*Verdict:* *[FIXED / NOT FIXED / BLOCKED] ([qualifier])* (confidence: [HIGH/MEDIUM/LOW])

[If BLOCKED (cherry-pick): "Cherry-pick PR to release-2.XX needed."]
[If BLOCKED (pipeline lag): "Rebuild environment with snapshot newer than [merge date]."]
[If BLOCKED (environment): "Environment degraded; re-verify after cluster is healthy."]
[If NOT FIXED: repro details / PR feedback.]
```
