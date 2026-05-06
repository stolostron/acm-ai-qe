# Bug Report: Entry Point Label Derived from Route Key Instead of UI Tab Label

**Date:** 2026-05-05
**Severity:** Medium (factual inaccuracy in test case output)
**Affected Run:** ACM-32280-2026-05-04T15-09-19
**Component:** UI Discoverer Agent (Phase 3) + Quality Reviewer (Phase 7)

---

## Summary

The test case generator produced `Entry Point: Infrastructure > Clusters > Managed clusters` but the actual UI shows the tab as **"Cluster list"**. The correct entry point is `Infrastructure > Clusters > Cluster list`.

---

## Root Cause (Detailed)

### What Happened

The UI discoverer agent (Phase 3) constructed the `entry_point` field by inferring a human-readable label from the route key name in the ACM Console source code, rather than verifying the actual rendered tab label via translations.

### Data Trail

**1. `get_routes()` MCP tool returned this route data (from `NavigationPath.tsx`):**

```
Route key: managedClusters
Path: /multicloud/infrastructure/clusters/managed
```

**2. The UI discoverer agent wrote to `phase3-ui.json` (line 89):**

```json
"entry_point": "Infrastructure > Clusters > Managed clusters"
```

The agent derived "Managed clusters" by:
- Taking the route key `managedClusters`
- Splitting camelCase: "managed" + "Clusters"
- Title-casing: "Managed clusters" (or "Managed Clusters")

**3. The synthesized context (Phase 4) propagated the error unchanged (line 113):**

```
Entry Point: Infrastructure > Clusters > Managed clusters
```

**4. The live validator (Phase 5) navigated correctly and noted the REAL label (line 23):**

```
Step 1: Navigate to Infrastructure > Clusters > Cluster list (managed clusters)
```

The live validator wrote "Cluster list" as the primary label and "(managed clusters)" as a parenthetical -- but this was a report observation, not a correction fed back to the entry_point field.

**5. The quality reviewer (Phase 7) did NOT catch this because:**
- It verified that an entry_point field EXISTS (structural check = PASS)
- It verified that the route URL is real (`/multicloud/infrastructure/clusters/managed` = valid)
- It did NOT verify that the label text matches the actual rendered tab/breadcrumb in the UI

### Actual UI (from screenshot and live validation)

The Clusters page has these tabs (visible in the screenshot):
- **Cluster list** ← this is what `/clusters/managed` shows
- **Cluster sets**
- **Cluster pools**
- **Discovered clusters**

There is NO tab called "Managed clusters". The route key `managedClusters` is an internal source code identifier, not a user-facing label.

### What the Agent SHOULD Have Done

Called `search_translations("Cluster list")` or `search_translations("Managed clusters")` to verify which string actually renders in the UI. The translations file in stolostron/console would return:
- "Cluster list" → exists (used as tab label)
- "Managed clusters" → does NOT exist as a tab label in the UI

Alternatively, if live validation is available, the entry_point should be corrected based on what the browser actually shows.

---

## Three Gaps to Fix

### Gap 1: UI Discoverer Does Not Verify Tab/Breadcrumb Labels

**Location:** `.claude/skills/acm-test-case-generator/references/agents/ui-discoverer.md`

**Current behavior (step 6):**
```markdown
6. **Get navigation routes:**
   - `get_routes()` -- find the entry point for the feature
```

The agent calls `get_routes()` and then constructs the entry_point string from route key names. It never verifies the actual UI label.

**Fix:** Add explicit instruction to verify entry point labels via translations:

```markdown
6. **Get navigation routes:**
   - `get_routes()` -- find the URL path for the feature
   - THEN verify the actual UI label for each navigation segment:
     - `search_translations("suspected label")` for each breadcrumb/tab segment
     - The route KEY (e.g., `managedClusters`) is an internal code identifier, NOT the UI label
     - The UI label is whatever string renders in the tab/breadcrumb (found in translations)
   - Common mismatch patterns:
     - Route key `managedClusters` → UI tab is "Cluster list" (NOT "Managed clusters")
     - Route key `clusterSets` → UI tab is "Cluster sets"
     - Route key `discoveredClusters` → UI tab is "Discovered clusters"
   - When in doubt, check the parent page's tab component source via `get_component_source`
```

### Gap 2: Live Validator Does Not Feed Corrections Back

**Location:** `.claude/skills/acm-test-case-generator/references/agents/live-validator.md`

**Current behavior:** The live validator observes the real UI and reports its findings, but doesn't produce structured corrections for fields that were set by earlier phases.

**Fix:** Add a "Corrections" section to the live validation output format:

In the live-validator.md instructions, add to the Output section:

```markdown
## Output Format Addition

At the end of your validation report, include a `## Corrections` section:

```markdown
## Corrections (feed back to test case)

If live validation reveals that Phase 3 data was inaccurate, list corrections here:

| Field | Phase 3 Value | Correct Value (from live UI) | Evidence |
|-------|---------------|------------------------------|----------|
| entry_point | Infrastructure > Clusters > Managed clusters | Infrastructure > Clusters > Cluster list | Tab label observed in browser snapshot |
```

The orchestrator MUST apply these corrections before writing the final test case.
```

### Gap 3: Quality Reviewer Does Not Cross-Check Entry Point Against Live Validation

**Location:** `.claude/skills/acm-test-case-generator/references/agents/quality-reviewer.md`

**Current MCP verification checks (Step 4):**
- `search_translations(query)` -- verify UI labels
- `get_routes()` -- verify entry point route exists
- `get_component_source(path, repo)` -- verify factual claims

**Missing check:** The reviewer verifies that the route EXISTS but not that the entry point LABEL matches translations.

**Fix:** Add to the quality reviewer's Step 4 MCP verification:

```markdown
### Entry Point Label Verification (MANDATORY)

For the entry_point field in the test case:
1. Extract the last segment of the entry point (e.g., "Managed clusters" from "Infrastructure > Clusters > Managed clusters")
2. Call `search_translations("last segment text")`
3. If the translation is NOT found:
   - Search for alternative labels: `search_translations("Cluster")` with partial match
   - Check if a different label matches the route (e.g., "Cluster list" for route /clusters/managed)
4. If live validation output exists (phase5-live-validation.md), cross-check the entry point against
   what the browser actually showed

KNOWN MISMATCHES (route key ≠ UI label):
- managedClusters → "Cluster list" (NOT "Managed clusters")
- The route key is a code identifier. The UI label comes from the translations file.

If a mismatch is found, classify as BLOCKING and require correction.
```

---

## Orchestrator Update

**Location:** `.claude/skills/acm-test-case-generator/SKILL.md`

In Phase 6 (Live Validation) processing, add:

```markdown
### Phase 6 Post-Processing: Apply Live Validation Corrections

After the live validator returns, check for a `## Corrections` section in its output.
If corrections exist:
1. Update the synthesized context with the corrected values
2. Specifically: if entry_point was corrected, use the live-validated value
3. Log the correction in the pipeline: "Entry point corrected from '{old}' to '{new}' based on live validation"

Arbitration hierarchy (unchanged): Source code < Live UI observation
The live UI always wins for user-visible labels (tab names, button text, breadcrumbs).
```

---

## Implementation Checklist

1. [ ] Update `ui-discoverer.md` -- add translation verification step for entry point labels
2. [ ] Update `live-validator.md` -- add `## Corrections` output section
3. [ ] Update `quality-reviewer.md` -- add entry point label verification check
4. [ ] Update `SKILL.md` orchestrator -- add Phase 6 post-processing for corrections
5. [ ] Add known route-key-to-label mappings as a reference (prevent repeat errors):
   ```
   managedClusters → "Cluster list"
   clusterSets → "Cluster sets"
   clusterPools → "Cluster pools"
   discoveredClusters → "Discovered clusters"
   ```

---

## Testing the Fix

After implementation, re-run: `/acm-test-case-generator ACM-32280`

Expected: Entry point should now be `Infrastructure > Clusters > Cluster list` because:
1. UI discoverer calls `search_translations("Managed clusters")` → not found
2. UI discoverer calls `search_translations("Cluster list")` → found
3. Entry point is written as "Cluster list" instead of inferring from route key
4. Quality reviewer verifies the label exists in translations → PASS

---

## Prompt for Claude Code

```
Read /Users/ashafi/Documents/work/ai/ai_systems_v2/.claude/skills/acm-test-case-generator/BUG-ENTRY-POINT-LABEL-INFERENCE.md and implement ALL fixes described in the "Three Gaps to Fix" section plus the "Orchestrator Update" section.

Files to modify:
1. .claude/skills/acm-test-case-generator/references/agents/ui-discoverer.md (Gap 1)
2. .claude/skills/acm-test-case-generator/references/agents/live-validator.md (Gap 2)
3. .claude/skills/acm-test-case-generator/references/agents/quality-reviewer.md (Gap 3)
4. .claude/skills/acm-test-case-generator/SKILL.md (Orchestrator Update)

For each file:
- Read the current content
- Find the exact location described in the bug report
- Insert the new instructions at the appropriate location
- Ensure consistency with existing formatting and style

Do NOT change any other logic. Only add the entry point verification improvements.

After implementation, verify:
- grep for "route key" in ui-discoverer.md -- should find the new warning
- grep for "Corrections" in live-validator.md -- should find the new output section
- grep for "Entry Point Label Verification" in quality-reviewer.md -- should find the new check
- grep for "Apply Live Validation Corrections" in SKILL.md -- should find the new post-processing step
```
