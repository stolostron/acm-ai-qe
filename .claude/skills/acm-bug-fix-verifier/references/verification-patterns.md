# Verification Patterns

Decision trees and evidence model for ACM bug fix verification. Referenced by SKILL.md Phases 2 and 4.

---

## Verdict Definitions

| Verdict | Meaning | Condition |
|---------|---------|-----------|
| **BLOCKED** | Fix cannot be on the environment | PR merged only to `main` (or non-release branch). No cherry-pick PR merged to the environment's release branch. Downstream builds are cut from release branches, never from `main`. |
| **NOT_FIXED** | Fix could be present but is not | PR is reachable from the release branch (directly or via cherry-pick), but the running image was built before the merge, OR the specific code change cannot be confirmed in the running container. |
| **PRESENT** | Fix code confirmed on the environment | Branch reachability + build date evidence confirm the fix is included. Optionally confirmed via in-container code grep. |
| **VERIFIED** | Fix confirmed working | PRESENT + Phase 3 live validation confirms the bug behavior no longer reproduces. |

**BLOCKED vs NOT_FIXED distinction matters for recommended action:**
- BLOCKED: development team must create a cherry-pick PR to `release-2.XX` (process gap)
- NOT_FIXED: QE team must rebuild the environment with a newer snapshot (build timing gap)

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

### Tier B — Build Date Comparison

Compares the PR merge timestamp against the environment's image build date.

1. Get PR merge date: `gh pr view <N> --repo <REPO> --json mergedAt --jq '.mergedAt'`
2. Get image tag date: parse the DOWNSTREAM tag (see `environment-checks.md` downstream tag extraction)
3. Compare (both normalized to UTC):
   - Image date >= PR merge date: **PASS** (build includes the fix)
   - Image date within 2h before PR merge date: **AMBIGUOUS** (build pipeline race; treat as FAIL with note)
   - Image date < PR merge date - 2h: **FAIL** (image predates the fix)

The 2-hour window accounts for CI pipeline queuing and build time (~30-90 min for ACM downstream builds), git merge to image registry publish delay, and timezone conversion edge cases.

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
  |            |            +-- YES --> VERDICT: BLOCKED
  |            |            |           (note: cherry-pick in progress)
  |            |            |
  |            |            +-- NO ---> VERDICT: BLOCKED
  |            |                        (action: file cherry-pick PR)
  |            |
  |            +-- YES --> Use cherry-pick SHA, restart Tier A
  |
  +-- YES --> TIER B: Image date >= PR merge date?
               |
               +-- FAIL ------> VERDICT: NOT_FIXED
               |                 (action: rebuild with newer snapshot)
               |
               +-- AMBIGUOUS --> VERDICT: NOT_FIXED
               |                  (note: build may be a race; rebuild)
               |
               +-- PASS ------> TIER C: Code found in running container?
                                  |
                                  +-- PASS ---------> VERDICT: PRESENT
                                  |
                                  +-- FAIL ---------> VERDICT: NOT_FIXED
                                  |                    (note: possible rollback)
                                  |
                                  +-- UNAVAILABLE --> VERDICT: PRESENT
                                                       (confidence: lower)
                                                       |
                                                       v
                                                 PHASE 3 available?
                                                       |
                                                  +-- YES --> Bug behavior gone?
                                                  |            |
                                                  |       +-- YES -> VERIFIED
                                                  |       +-- NO --> NOT_FIXED
                                                  |                  (regression?)
                                                  |
                                                  +-- NO ---> Keep PRESENT
```

---

## Evidence Quality Scoring

| Evidence combination | Confidence | Notes |
|---------------------|------------|-------|
| A + B + C + Live | 0.95 | Maximum — all tiers pass plus behavioral confirmation |
| A + B + C | 0.90 | Code confirmed without live testing |
| A + B + Live | 0.85 | No container grep but behavior confirmed |
| A + B | 0.75 | Branch + date evidence only |
| A + C | 0.70 | Branch + code but date comparison failed or unavailable |
| A only | 0.50 | Branch reachability alone — weak |
| B only | 0.40 | Date match without branch confirmation — unreliable |

When Neo4j was unavailable for Phase 2.5 prerequisites: subtract 0.10 from confidence (heuristic table fallback) or 0.20 (oc-only discovery fallback).

### Scope Downgrade Rule

If the bug is UI-specific (console rendering, form behavior, display issue) and UI verification was skipped (no Playwright, no credentials), the maximum verdict confidence is LOW. The verdict report MUST state:

> "UI verification was skipped (reason: [no credentials / Playwright unavailable]). Backend checks passed but cannot confirm UI-specific behavior."

Never silently claim VERIFIED from backend-only evidence when the bug category is UI.

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
| **Verdict** | **[BLOCKED / NOT_FIXED / PRESENT / VERIFIED]** |
| Confidence | [0.00-1.00] |

### Evidence

| Tier | Check | Result | Detail |
|------|-------|--------|--------|
| A (Branch) | SHA reachable from release-2.XX | PASS / FAIL | [gh api compare output] |
| B (Build) | Image date >= PR merge date | PASS / FAIL / AMBIGUOUS | [date comparison] |
| C (Code) | Code pattern in running container | PASS / FAIL / UNAVAILABLE | [grep output or reason] |
| Live | Bug behavior resolved | PASS / FAIL / SKIPPED | [Playwright evidence or skip reason] |

### Prerequisites (Phase 2.5)

| Component | Status | Evidence |
|-----------|--------|----------|
| [dependency] | HEALTHY / DEGRADED / MISSING | [image date, pod status] |

### Recommended Action

[Based on verdict - see verdict definitions above]
```

---

## Edge Cases

**Multiple PRs for one JIRA:** Some bugs require multiple PRs across different repos (e.g., backend + frontend). Verify ALL linked PRs independently. The final verdict is the WORST verdict across all PRs. If one PR is PRESENT and another is BLOCKED, the overall verdict is BLOCKED.

**Open cherry-pick PR (not yet merged):** Verdict is BLOCKED with a note that a cherry-pick is in progress. Include the cherry-pick PR number and its current state (draft, review, approved).

**No DOWNSTREAM tag prefix:** Some environments run upstream/community images (`quay.io/stolostron/...`) or custom builds without the DOWNSTREAM date format. Tier B is UNAVAILABLE. Fall back to MCH version heuristic: parse `X.Y.Z-NNN` build number and compare against known nightly cadence.

**CRD-only or webhook-only change:** No application pod to exec into. Tier C uses:
```bash
oc get crd <crd-name> -o yaml | grep "<pattern>"
```

**PR merged to release branch directly (no cherry-pick needed):** Some repos merge directly to the release branch. In this case, Tier A passes on the first check, and "Cherry-pick" in the verdict table shows "N/A (direct merge)".

**Backport to multiple release branches:** If the environment could be running any of several versions, ask the user to confirm the exact version. Verify against that specific release branch only.

---

## JIRA Comment Template

When the user approves a JIRA update, use this template:

```
h3. QE Verification - [VERDICT]

*Cluster:* [api-url]
*ACM Version:* [version] ([DOWNSTREAM-tag])
*Verified:* [date]

*Fix Presence:*
- PR #[number]: [merged to release-2.XX | cherry-pick #[cp-number] merged]
- Evidence tiers: A=[PASS/FAIL] B=[PASS/FAIL] C=[PASS/FAIL/UNAVAILABLE]

*Live Verification:*
- Backend: [PASS/FAIL/SKIPPED] - [detail]
- UI: [PASS/FAIL/SKIPPED] - [detail]

*Verdict:* *[BLOCKED / NOT_FIXED / PRESENT / VERIFIED]* (confidence: [0.00-1.00])

[If BLOCKED: "Cherry-pick PR to release-2.XX needed."]
[If NOT_FIXED: "Rebuild environment with snapshot newer than [date]."]
```
