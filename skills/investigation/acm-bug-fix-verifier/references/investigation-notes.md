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
1. **Heuristic dependency table** (7 common ACM component chains): covers frequently fixed components. Confidence penalty: -0.10.
2. **oc-based discovery** (CRD ownership, endpoint mapping, configmap references): discovers operator-level dependencies dynamically. Confidence penalty: -0.20.
3. **JIRA link analysis** (linked tickets with dependency relationships): surfaces explicit developer-documented dependencies via JIRA MCP.

The confidence penalty is explicitly stated in the verdict.

### D4. Four-Verdict Model

**Finding:** The handoff and Cursor reference used a simpler FIXED/BLOCKED/NOT_FIXED model. The implemented skill uses: BLOCKED/NOT_FIXED/PRESENT/VERIFIED.

**Rationale:** PRESENT distinguishes "fix code is deployed" from "fix behavior confirmed working" (VERIFIED). A code change can be present but ineffective (wrong fix, incomplete fix, masked by another issue). The split encourages completing Phase 3 rather than stopping at Phase 2 evidence.

**Mapping:** Handoff "FIXED" maps to VERIFIED. Handoff "NOT FIXED" maps to NOT_FIXED or BLOCKED depending on root cause.

### D5. Console Auth Reference Strategy

**Decision:** Phase 3 references `${CLAUDE_SKILL_DIR}/../../test-case-gen/acm-test-case-generator/references/console-auth.md` for browser authentication.

**Portability:** Allowed per `PORTABLE-CONSTRAINTS.md` (sibling skills in the same repo). If the sibling is removed, `references/environment-checks.md` section 10 has an inline minimum auth procedure.

### D6. main vs release-2.XX Semantics

ACM branching model: `main` receives all development; release branches receive cherry-picks; downstream builds are cut from release branches. A PR merged to `main` is NOT present on any downstream environment until cherry-picked to the release branch AND a build is created after that merge. Tier A checks the release branch, not `main`. This is a process gap (BLOCKED) requiring developer action, not a build timing gap (NOT_FIXED) requiring QE action.

---

## Implementation Findings (Skeptical Review)

### F1. Phantom Playwright tool: `browser_select_option` (FIXED)

**File:** SKILL.md, Phase 3
**Issue:** `browser_select_option` was listed but does not exist in the Playwright MCP. The sibling skill only uses: `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_fill_form`, `browser_wait_for`, `browser_evaluate`.
**Fix:** Removed.

### F2. Phase count mismatch in description (FIXED)

**File:** SKILL.md, YAML description
**Issue:** Description said "5-phase pipeline" but the body defines 6 phases (0, 1, 2, 2.5, 3, 4).
**Fix:** Changed to "6-phase pipeline".

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
