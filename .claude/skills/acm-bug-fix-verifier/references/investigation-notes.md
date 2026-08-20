# Investigation Notes

Independent investigation findings from implementing the `acm-bug-fix-verifier` skill. Documents contradictions, gaps, design decisions, and mitigations applied during authoring.

---

## Design Decisions

### D1. Playwright Subagent Limitation

**Finding:** Playwright MCP tools are not accessible from within Claude Code subagents (Agent tool). This is a known platform limitation also documented in `acm-test-case-generator` ISSUES-REPORT-2026-05-11.

**Impact:** Phase 3 (live verification) cannot be delegated to a subagent for browser-based validation.

**Mitigation:** Phase 3 runs entirely inline in the orchestrator context. This is acceptable because Phase 3 is procedural (authenticate, navigate, verify) rather than open-ended investigation. All other phases use subagents where appropriate.

### D2. MCP Naming Discrepancy

**Finding:** The handoff document (Appendix B) referenced `user-playwright` as the Playwright MCP name. The repo convention uses bare `playwright` (tools prefixed `mcp__playwright__*` in Claude Code). The `neo4j-rhacm` name matches the repo convention.

**Resolution:** SKILL.md uses `playwright` (bare name) consistent with the repo's `.mcp.json` configuration and other skills. The handoff's `user-` prefix was a Cursor-specific convention.

### D3. Phase 2.5 Without Neo4j

**Question:** Is Phase 2.5 still useful if Neo4j is unavailable?

**Finding:** Yes. Three independent fallback mechanisms provide useful prerequisite analysis:
1. **Heuristic dependency table** (7 common ACM component chains): covers frequently fixed components. Confidence adjustment: reduce one level.
2. **oc-based discovery** (CRD ownership, endpoint mapping, configmap references): discovers operator-level dependencies dynamically. Confidence adjustment: reduce two levels.
3. **JIRA link analysis** (linked tickets with dependency relationships): surfaces explicit developer-documented dependencies via JIRA MCP.

The confidence adjustment is explicitly stated in the verdict (see D8 -- confidence is a HIGH/MEDIUM/LOW level in v1.2.0, not a numeric score).

### D4. Verdict Model — verdict × qualifier (v1.2.0)

**History:** v1.1.0 used a 4-state linear model (BLOCKED -> NOT_FIXED -> PRESENT -> VERIFIED). PRESENT was introduced to distinguish "fix code is deployed" from "behavior confirmed working" (VERIFIED). That split solved a real problem but created two new ones: (1) it read as a *progression*, so a PRESENT result felt like a partial VERIFIED rather than its own outcome; and (2) it had no vocabulary for *why* UI verification was incomplete, so "code confirmed, no credentials" and "code confirmed, Playwright crashed" collapsed into the same PRESENT verdict despite meaning different things.

**v1.2.0 model:** three verdicts, each with a qualifier that carries the "why" and drives the JIRA action:
- **FIXED** (full / code-only / backend-only)
- **NOT FIXED** (standard / code review)
- **BLOCKED** (cherry-pick / pipeline lag / environment)

**Why this is better:** the qualifier encodes the exact evidence state and the correct next action in one token. "FIXED (code-only)" says *close with a note that UI wasn't checked*; "FIXED (backend-only)" says *the same, but the reason was a Playwright failure worth investigating separately*. The verdict stays honest (the fix IS in and correct) while the qualifier prevents over-claiming.

**Migration from v1.1.0:**

| Old (v1.1.0) | New (v1.2.0) |
|--------------|--------------|
| VERIFIED | FIXED (full) |
| PRESENT (code confirmed, no credentials) | FIXED (code-only) |
| PRESENT (backend confirmed, Playwright unavailable/failed) | FIXED (backend-only) |
| NOT_FIXED (behavior still reproduces) | NOT FIXED (standard) |
| NOT_FIXED (fix wrong per code review) | NOT FIXED (code review) |
| NOT_FIXED (image predates merge) | **BLOCKED (pipeline lag)** — reclassified |
| BLOCKED (main-only / no cherry-pick) | BLOCKED (cherry-pick) |
| *(new)* cluster unhealthy for valid verification | BLOCKED (environment) |

**Key reclassification:** "merged to the release branch but the running image predates the merge" was NOT_FIXED in v1.1.0; it is **BLOCKED (pipeline lag)** in v1.2.0. The fix is not absent from the code -- the build is stale -- so the action is "deploy a newer build," not "reopen." NOT FIXED is now reserved for *code present + behavior still reproduces* (Phase 3) or *fix clearly wrong* (Phase 2b).

### D5. Console Auth Reference Strategy

**Decision:** Phase 3 references `${CLAUDE_SKILL_DIR}/../acm-test-case-generator/references/console-auth.md` for browser authentication.

**Portability:** Allowed per `PORTABLE-CONSTRAINTS.md` (sibling skills in the same repo). If the sibling is removed, `references/environment-checks.md` section 10 has an inline minimum auth procedure.

### D6. main vs release-2.XX Semantics

ACM branching model: `main` receives all development; release branches receive cherry-picks; downstream builds are cut from release branches. A PR merged to `main` is NOT present on any downstream environment until cherry-picked to the release branch AND a build is created after that merge. Tier A checks the release branch, not `main`. This is a process gap -- BLOCKED (cherry-pick), requiring developer action -- as distinct from a build-timing gap -- BLOCKED (pipeline lag), requiring QE to deploy a newer build (see D4 and D7).

### D7. Pipeline-lag reclassification and the 24-hour model (v1.2.0)

**Change:** "merged to release branch but image predates the merge" moved from NOT_FIXED to **BLOCKED (pipeline lag)** (see D4). The binary "2-hour ambiguity window" was replaced with a graduated 24-hour model: merge->build gap 0-6h = NO (fix likely not in build), 6-12h = MAYBE, 12-24h = LIKELY, 24h+ = YES.

**Why:** ACM downstream builds run on a multi-hour cadence, so a 2-hour window was too tight -- a build finishing 3 hours after a merge could still have *started* before it. The graduated model matches real pipeline behavior and tells the operator when to insist on a Tier C grep rather than trusting the date alone.

**Lockstep:** the 24-hour table appears in two places -- `verification-patterns.md` Tier B and `environment-checks.md` section 2. Edit both together. (Previously also in SKILL.md Phase 2; removed in the v1.3.0 cost optimization -- SKILL.md now references verification-patterns.md instead of duplicating the table.)

### D8. Evidence tier weights replace numeric confidence (v1.2.0)

**Change:** the combination-based numeric confidence table (0.40-0.95) became a tier-weight model: Tier 1 evidences (Branch A, Build B, Code C, acm-source cross-validation, UI repro) weight 1.0; Tier 2 (PR code review, clean backend logs) weight 0.5. Confidence = Σ achieved ÷ max -> HIGH (>= 0.8, 4+ Tier 1), MEDIUM (0.5-0.79, 2-3 Tier 1), LOW (< 0.5).

**Why:** numeric scores implied false precision (is 0.75 meaningfully different from 0.70?) and were hard to keep consistent across the skill and its references. Levels are easier to reason about and to report in a JIRA comment. The old Neo4j penalty and UI scope-downgrade rule became "reduce one/two levels" adjustments rather than numeric subtractions. Source: `.claude/knowledge/diagnostics/evidence-tiers.md`.

### D9. Environment health gate via inline oc + sibling skill (v1.2.0)

**Change:** new Phase 2.75 runs subsystem-scoped health checks before live verification. The Cursor twin delegates this to an `acm-live-investigator` skill; this repo has no such skill, so the gate is implemented as **inline `oc` checks** for the four highest-value traps (Trap 1 MCH stale, Trap 2 console-mce down, Trap 13 ConsolePlugin backend unreachable, Trap 3 search-postgres empty), referencing the sibling `../acm-hub-health-check/SKILL.md` methodology and `.claude/knowledge/diagnostics/diagnostic-traps.md`. For a deeper look, the gate may spawn a `general-purpose` subagent following that sibling.

**Why:** Phase 2.5 confirms operators/CRDs *exist*; it cannot tell whether the subsystem actually *works*. Without this gate, a degraded cluster produces a false NOT FIXED. Critical degradation -> BLOCKED (environment) and skip Phase 3.

### D10. File-based knowledge DB, not an MCP (v1.2.0)

**Finding:** the Cursor twin reads failure signatures and traps through an `acm-knowledge` MCP. That MCP is **not configured** in this repo and no skill uses it. The knowledge base here is **file-based** under `.claude/knowledge/`.

**Resolution:** the Phase 4 failure-signature gate and the Phase 4.5 knowledge-DB update read/write files directly (`failures/<subsystem>/failure-signatures.md`, `diagnostics/diagnostic-traps.md`, `diagnostics/evidence-tiers.md`). Because `.claude/knowledge/` is **git-tracked**, Phase 4.5 follows the repo write protocol (read target first, check duplicates, verified facts only) and **surfaces** proposed additions to the user rather than committing silently. New-trap discoveries are flagged for manual review, never auto-appended.

### D11. Engram integration is wrapped and non-blocking (v1.2.0)

**Finding:** Engram is a user-global MCP; it may be absent in a given clone or CI run.

**Resolution:** both the Phase 0 recall and the Phase 4.5 store are wrapped in availability checks and skip silently when Engram is unavailable. Learning is always additive -- it never changes or delays the verdict.

### D12. Phase 3 split (3A backend / 3B UI) + Playwright Recovery (v1.2.0)

**Change:** Phase 3 now has 3A (backend, always runs) and 3B (UI, conditional on credentials + Playwright). A mid-run Playwright failure triggers the Recovery Protocol: capture error + last snapshot, retry once with a fresh navigate, and on second failure fall back to 3A-only with qualifier **backend-only**.

**Key rule:** never declare NOT FIXED on a Playwright failure alone -- the fix may work; the browser tooling just couldn't confirm it. Skip conditions map to qualifiers: no credentials -> code-only, Playwright unavailable/failed -> backend-only. Phase 3 still runs **inline** (the D1 constraint is unchanged).

---

## Implementation Findings (Skeptical Review)

### F1. Phantom Playwright tool: `browser_select_option` (FIXED)

**File:** SKILL.md, Phase 3
**Issue:** `browser_select_option` was listed but does not exist in the Playwright MCP. The sibling skill only uses: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_fill_form`, `browser_wait_for`, `browser_evaluate`.
**Fix:** Removed.

### F2. Phase count in description (FIXED)

**File:** SKILL.md, YAML description
**Issue:** The original v1.1.0 description undercounted the phases defined in the body.
**Fix:** Corrected to match the body. As of v1.2.0 the pipeline is **9 phases** (0, 1, 2, 2b, 2.5, 2.75, 3, 4, 4.5) and the description says "9-phase pipeline". Keep this count in sync with the phase headings and the Phase Gate `TaskCreate` list whenever phases are added or removed.

### F3. Missing build-tag timestamp gate in Phase 2 (FIXED)

**File:** SKILL.md, Phase 2
**Issue:** Phase 2 did not check build-tag timestamps — went straight to Phase 2.5 on Tier A confirmation. The "image predates fix" case would be missed.
**Fix:** Added build-tag timestamp gate step to Phase 2.

### F4. "close this bug" over-triggering risk (FIXED)

**File:** SKILL.md, YAML description
**Issue:** The trigger "close this bug" could match intent to administratively close a JIRA ticket without verification.
**Fix:** Removed from trigger phrases. Remaining triggers are specific enough.

### F5. Phase 2.5 compounding degradation (FIXED)

**File:** references/environment-checks.md
**Issue:** If both Neo4j and JIRA MCP are down, only 3 of 4 heuristics work (all oc-based). Not documented.
**Fix:** Added compounding degradation note to environment-checks.md section 7.

### F6. JIRA MCP write tools unverifiable at author time (ACCEPTED)

**File:** SKILL.md, Phase 4
**Resolved:** JIRA MCP is the fork at `mcp/.external/jira-mcp-server` ([atifshafi/jira-mcp-server@feat/redhat-fields](https://github.com/atifshafi/jira-mcp-server/tree/feat/redhat-fields)). `add_comment` uses parameter `comment` (not `body`); optional `attachment_paths` / `inline_attachment_paths` embed screenshots inline. Refresh with `bash mcp/setup.sh` after fork updates.
**Resolution:** Kept as-is. Phase 4 writes are gated behind user approval, so a tool-name mismatch surfaces at runtime without harm.

### F7. Portability scan (CLEAN)

All files scanned for `~`, `/Users/`, `.cursor`, `.cursorrules` references. None found. Portability contract satisfied.

### F8. Trigger overlap with acm-bug-hunter (CLEAN)

Verifier triggers ("verify bug fix", "confirm fix landed", "check if fixed", "is the bug fixed") vs bug-hunter triggers ("hunt bugs", "find bugs", "stress test this test case", "probe for bugs"). No overlap. Negative triggers cross-reference each other.

### F9. `compatibility` field format (ACCEPTED)

Uses freetext (`>-`) matching the convention of all other skills in this repo.

---

## Examples

### Example 1: FIXED (full) verdict

```
User: verify ACM-30001 on https://api.slot03.example.com:6443

Phase 0: ACM-30001 -- "GRC policy table shows wrong compliance count"
         Scope: full. Cluster: slot03, ACM 2.12.1, DOWNSTREAM-2026-05-01-12-00-00
Phase 1: PR #4521 merged to release-2.12 on 2026-04-28
         Image date 2026-05-01 >= merge date 2026-04-28
Phase 2: Tier A PASS, Tier B PASS (in build), Tier C PASS -> fix in build
Phase 2b: gh pr diff #4521 -- fix corrects count aggregation logic.
          Risk: LOW (single function, test updated). No regression spots needed.
Phase 2.75: Health gate -- GRC subsystem healthy.
Phase 3: 3A backend -- grc-ui pod running, no errors; acm-source confirms the fix string.
         3B UI -- compliance count correct after policy creation.
Phase 4: Verdict: FIXED (full, confidence: HIGH -- 5 Tier 1 evidences)
         JIRA update offered -> user approves -> comment + inline screenshot added
Phase 4.5: Engram store; no new failure pattern.
```

### Example 2: BLOCKED (cherry-pick) verdict

```
User: is ACM-30002 fixed on my cluster?

Phase 0: ACM-30002 -- "Search returns stale results after import"
         Scope: full. Cluster: current oc login, ACM 2.13.0
Phase 1: PR #892 merged to main. Cherry-pick PR #901 open targeting release-2.13.
Phase 2: Tier A FAIL (main-only). Cherry-pick not merged -> BLOCKED (cherry-pick).
         (Phases 2b, 2.5, 2.75, 3 skipped)
Phase 4: Verdict: BLOCKED (cherry-pick)
         "Fix in main. Cherry-pick PR #901 to release-2.13 is open.
          Monitor for merge, then re-verify."
```

### Example 3: BLOCKED (pipeline lag) verdict

```
User: confirm fix for ACM-30003 on my 2.16 hub

Phase 0: ACM-30003 -- "Console crash on credentials page"
         Scope: full. Cluster: hub-az, ACM 2.16.2, DOWNSTREAM-2026-04-15-08-30-00
Phase 1: PR #1234 merged to release-2.16 on 2026-04-20.
         Image build date 2026-04-15 < merge date 2026-04-20 (image predates the merge).
Phase 2: Tier A PASS, Tier B FAIL (image predates merge) -> BLOCKED (pipeline lag).
         (Phases 2b, 2.5, 2.75, 3 skipped)
Phase 4: Verdict: BLOCKED (pipeline lag)
         "PR merged to release-2.16 on 2026-04-20 but the image was built 5 days
          earlier (2026-04-15). The fix is in the branch, not yet in this build.
          Rebuild/redeploy with a snapshot newer than 2026-04-20, then re-verify."
```

Note: this is **not** NOT FIXED -- the fix is not absent, the build is just stale.

### Example 4: FIXED (full) with regression check (medium risk)

```
User: verify ACM-30004 on bm12

Phase 0: ACM-30004 -- "RBAC role table shows wrong permission count"
         Scope: full. Cluster: bm12, ACM 2.17.0, DOWNSTREAM-2026-05-18-10-00-00
Phase 1: PR #5678 merged to release-2.17 on 2026-05-15.
Phase 2: Tier A PASS, Tier B PASS (in build) -> fix in build
Phase 2b: gh pr diff #5678 -- refactored shared utility `aggregatePermissions()`.
          Risk: MEDIUM (utility used by 3 pages). Regression spots: role detail, user detail.
Phase 2.5: No gaps (RBAC prereqs met).
Phase 2.75: Health gate -- RBAC/console subsystem healthy.
Phase 3: 3A backend clean. 3B direct repro passes (role table correct).
         Regression: role detail page OK, user detail page OK.
Phase 4: Verdict: FIXED (full, confidence: HIGH -- 4 Tier 1 evidences)
```

---

## Troubleshooting

| Symptom | Cause | Action | Verdict Impact |
|---------|-------|--------|----------------|
| JIRA MCP returns 401 | Expired token | Re-authenticate: check `mcp/.external/jira-mcp-server/.env` | None (JIRA update is optional/manual) |
| `gh pr view` fails | Not authenticated or wrong repo | Run `gh auth status`; verify repo org (stolostron vs open-cluster-management) | Blocks Tier A/B -- may force BLOCKED if PR state unknown |
| Playwright login fails / stuck after navigate | Wrong credentials, IDP mismatch, or hung session | Apply the Playwright Recovery Protocol (retry once, then backend-only) | Qualifier -> backend-only; never NOT FIXED on this alone |
| acm-source MCP unavailable | Server not configured | Rely on Tier A/B/C; note the gap | Loses 1 Tier 1 evidence point (confidence may drop a level) |
| acm-search / acm-kubectl unavailable | Not deployed / not configured | Fall back to `oc` CLI for the same queries | None if `oc` covers it; otherwise state the gap |
| Neo4j returns empty results | Graph not imported or schema drift | Fall back to heuristics (see Phase 2.5) | Unresolved prereq gap -> reduce confidence one level |
| Health gate can't run | No cluster access / `oc` unavailable | Proceed with a warning; do not silently skip | Phase 2.75 recorded as "skipped" |
| Symptom matches a known trap (Phase 2.75 / Phase 4 gate) | Environment degraded, not a failed fix | Reclassify per the gate | NOT FIXED -> BLOCKED (environment) |
| Build tag not found | Community build or non-standard install | Use `oc get csv` createdAt as fallback; note reduced confidence | Weakens Tier B -- reduce confidence one level |
| Cherry-pick detection misses | PR title doesn't contain JIRA key | Check PR descriptions and commit messages manually | Risk of a false BLOCKED (cherry-pick) if missed |
| CSRF fetch returns 403 | Session expired or wrong token path | Re-authenticate via Playwright | Blocks API check; may reduce 3B coverage |
| Engram / knowledge-DB unreachable | Not configured / path missing | Skip Phase 4.5 silently | None -- learning skipped, no verdict impact |
