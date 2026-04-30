---
name: acm-test-case-generator
description: Generate Polarion-ready ACM Console UI test cases from JIRA tickets. Runs a multi-phase pipeline with JIRA investigation, PR diff analysis, UI discovery, synthesis, optional live validation, test case writing, and mandatory quality review. Use when asked to generate a test case, write test coverage, or process an ACM JIRA ticket for testing.
compatibility: "Required MCPs: acm-ui, jira, polarion. Recommended: neo4j-rhacm. Optional: acm-search (fleet queries, deploy with 'bash mcp/deploy-acm-search.sh'), acm-kubectl (spoke access), playwright (browser). Also needs gh CLI (gh auth login). Run /onboard to configure all MCPs."
---

# ACM Console Test Case Generator

Generates Polarion-ready test cases for ACM Console UI features from JIRA tickets. Uses a 10-phase pipeline: input resolution, data gathering, JIRA investigation, PR code analysis, UI discovery, synthesis, optional live validation, test case writing, mandatory quality review with programmatic enforcement, and report generation.

## Skills Used

This skill orchestrates the following skills. Each provides raw capabilities; this skill provides the workflow intelligence.

| Skill | Phase | How This Skill Uses It |
|-------|-------|----------------------|
| **acm-jira-client** | 2 | Investigate the JIRA story: read summary, description, ALL comments, ACs, fix version, components. Search for QE tracking ticket, sub-tasks, related bugs, sibling stories in same epic. Find PR references in comments. Check if story is done/merged. |
| **acm-code-analyzer** | 3 | Analyze the PR diff: identify changed components, new UI elements, modified behavior, filtering functions, field orders, conditional rendering, translation strings. Read full source of primary target file. Cross-reference with area knowledge. |
| **acm-ui-source** | 4, 7, 8 | Discover UI elements: set ACM version, search routes, translations, selectors, component source. Verify entry point route exists. Spot-check labels. Read filtering function source to extract exact rules. |
| **acm-knowledge-base** | 2-8 | Read area architecture (field orders, filtering behavior, component patterns). Read test case conventions. Read examples for format reference. Area knowledge constrains the test case writer. |
| **acm-neo4j-explorer** | 2-4 | Query component dependencies and subsystem membership. Understand impact of changes. Optional -- skip if Neo4j unavailable. |
| **acm-polarion-client** | 2, 8 | Check existing Polarion test case coverage before writing. Verify metadata during review. Search for duplicates. |
| **acm-cluster-health** | 6 | If live validation: verify cluster health before testing. Use diagnostic methodology to check environment readiness. |
| **acm-test-case-writer** | 7 | Write the test case markdown from synthesized context. Follows conventions, applies knowledge constraints, does self-review. |
| **acm-test-case-reviewer** | 8 | Quality gate: validate format, verify UI elements via MCP, check AC vs implementation, cross-reference knowledge, enforce minimum 3 MCP verifications. |

## Pipeline Phases

Read `references/phase-gates.md` for gate rules and progress indicators.

### Phase 0: Determine Inputs

Before running the pipeline, resolve these inputs:

1. **JIRA ID** (required): The ticket to generate a test case for (e.g., ACM-30459)
2. **ACM Version**: From JIRA fix_versions, or ask: "Which ACM version?"
3. **PR Number**: Auto-detected from JIRA description/comments, or ask if not found
4. **Area**: Auto-detected from PR file paths (governance, rbac, fleet-virt, clusters, search, applications, credentials, cclm, mtv)
5. **Cluster URL** (optional): For live validation. Auto-detect before asking:
   - Run `oc whoami --show-server 2>/dev/null` -- if this returns a URL, the user is logged in
   - If logged in, derive console URL: `oc get route console -n openshift-console -o jsonpath='{.spec.host}' 2>/dev/null`
   - If console route found, use `https://<host>` as the cluster URL without asking
   - If `oc` is not logged in or not available, ask: "Do you have a hub console URL, or should I skip live validation?"
   - In headless mode (`-p`), auto-detect from `oc` login -- do not ask interactively
6. **CNV Version** (Fleet Virt only): Ask: "What CNV version on the spoke?"

If all inputs can be inferred from the JIRA ticket, proceed without asking.

### Phase 1: Gather Data

Run the deterministic gather script to collect PR data:

```bash
python scripts/gather.py <JIRA_ID> [--version VERSION] [--pr PR_NUMBER] [--area AREA] [--repo REPO]
```

This produces:
- `gather-output.json` -- PR metadata, file list, existing test case paths, conventions, area knowledge
- `pr-diff.txt` -- full PR diff

Show a summary: "Gathered PR #NNNN, N files changed. Area: [area]."

### Phase 2: Investigate JIRA Story

Using the **acm-jira-client** skill, deeply investigate the JIRA ticket:

1. **Read the story** via `get_issue(issue_key)`:
   - Extract summary, description, acceptance criteria
   - Extract fix version (determines ACM version), components (determines area)
   - Note status (is it done/merged?)

2. **Read ALL comments** -- they contain:
   - Implementation decisions ("changed the approach to...")
   - Edge cases ("what happens when...")
   - Design trade-offs ("decided not to...")
   - QE feedback ("should also test...")
   - PR links, design docs

3. **Find linked tickets** using acm-jira-client JQL patterns:
   - QE tracking: `summary ~ "[QE] --- ACM-XXXXX"`
   - Sub-tasks: `parent = ACM-XXXXX`
   - Related bugs: `type = Bug AND summary ~ "keyword"`
   - Sibling stories in the same fixVersion + component:
     JQL: `project = ACM AND fixVersion = "<version>" AND component = "<component>" AND type = Story AND key != <target-key> ORDER BY key ASC`
     For each sibling found, check if it renames fields/metrics/labels referenced by the target story, is a follow-up fix for the same feature area, or modifies the same component files. Sibling stories often contain renames, behavior changes, or edge cases that the target story's JIRA description does not know about. Note relevant siblings in the synthesis as "SIBLING CONTEXT"

4. **Check existing Polarion coverage** using acm-polarion-client:
   - Search: `get_polarion_work_items(project_id="RHACM4K", query='type:testcase AND title:"feature"')`
   - If found, read summaries to avoid duplication

5. **Check architecture context** using acm-neo4j-explorer (if available):
   - What subsystem does this feature belong to?
   - What depends on it? What does it depend on?

**Output:** Story summary, ACs, implementation details from comments, edge cases, RBAC impact, linked tickets, existing coverage, test scenarios suggested.

### Phase 3: Analyze PR Code Changes

Using the **acm-code-analyzer** skill, analyze the PR diff:

1. Read PR metadata from `gather-output.json`
2. Read the full diff from `pr-diff.txt`
3. **Set ACM version** via acm-ui-source skill FIRST
4. For each changed file, identify: new UI elements, modified behavior, routes, translations, filtering logic, conditional rendering, error handling
5. **MANDATORY: Read full source** of the primary target file via `get_component_source` -- do NOT rely solely on the diff
6. **Distinguish test files from production code** -- data in `.test.tsx` files is MOCK DATA
7. **Multi-story PRs**: Tag each file with its JIRA story. Focus on the target story.
8. **Read filtering function source** if the diff introduces filters: call `get_component_source` on the utility file, extract exact conditions (string comparisons, `startsWith`, regex)
9. **Cross-reference with area knowledge** from acm-knowledge-base. Flag contradictions.
10. **Follow-up PR detection**: For each primary changed file in the diff, check for subsequent merged PRs:
    ```bash
    gh pr list --repo stolostron/console --search "path:<filepath>" --state merged --limit 5 --json number,title,mergedAt
    ```
    If any merged PR has a `mergedAt` date AFTER the target PR, read its title. If it touches the same component, flag as "FOLLOW-UP PR: #NNNN -- [title]" in the output. This catches post-merge renames, fixes, and refactors that would make the test case stale.

**Output:** Changed components, new UI elements, modified behavior, filtering logic with exact conditions, field orders, component dependencies, follow-up PRs, test scenarios.

### Phase 4: Discover UI Elements

Using the **acm-ui-source** skill, discover UI elements:

1. `set_acm_version` (and `set_cnv_version` for Fleet Virt/CCLM/MTV)
2. `search_code` for the feature's components
3. `get_component_source` for key files -- read complete source, not just snippets
4. `find_test_ids` for data-test attributes
5. `search_translations` for all key UI labels
6. `get_routes` for navigation paths -- find the specific route for the feature under test
7. `get_wizard_steps` if the feature involves a wizard
8. `get_acm_selectors` for existing QE selectors
9. `get_patternfly_selectors` for PF6 CSS fallbacks if needed

**Output:** Component files, selectors, translation keys, routes, entry point, wizard structure, existing QE selectors.

### Phase 5: Synthesize

Read `references/synthesis-template.md` for the synthesis template.

Merge all investigation results into a SYNTHESIZED CONTEXT block:
1. Combine JIRA findings, code analysis, and UI discovery
2. **Resolve conflicts**: trust UI discovery for UI elements, JIRA for requirements, code analysis for what changed, knowledge files for architecture constraints
3. **Scope gate**: only plan steps for the target story's ACs, not the broader PR
4. **AC vs Implementation cross-reference**: if ACs disagree with code behavior, flag as discrepancy
5. **Plan the test case**: step count, setup, per-step validations, CLI checkpoints, teardown
6. **Negative scenario enforcement**: If the code analysis identified conditional rendering (ternary operators, feature gates, permission checks, addon dependencies), plan at least ONE negative scenario step that verifies the feature is NOT visible/accessible when the condition is not met. The negative step should verify absence (element not rendered, action not available), not an error state. If no conditional rendering was identified, this does not apply.

**STOP checkpoint:** "Investigation complete. [N] test scenarios identified."

### Phase 6: Live Validation (conditional)

If a cluster URL was provided (or auto-detected from `oc` login in Phase 0):

Use ALL available tools in this priority order:

1. **Playwright MCP** (primary -- UI validation): Playwright runs headless Chromium, no display needed.
   - `browser_navigate` to the ACM console URL (auto-detected or provided)
   - `browser_navigate` to the feature page (e.g., Infrastructure > Clusters > cluster > Nodes)
   - `browser_snapshot` to capture the accessibility tree
   - Verify expected UI elements: column headers, tooltip text, links, sort indicators
   - Verify field order matches expectations
   - Check for console errors via `browser_console_messages`
   - Log screenshots/snapshots as evidence in the run directory

2. **ACM-Search MCP** (complementary -- backend/fleet validation):
   - `find_resources` to verify environment state: MultiClusterHub Running, MultiClusterObservability Ready, ManagedClusters Available, relevant ClusterManagementAddons exist
   - `query_database` for cross-cluster resource counts and verification that expected resources exist before testing
   - This adds backend evidence that browser validation alone cannot provide

3. **oc CLI** (last fallback -- only if neither Playwright nor acm-search available):
   - `oc get mch -A`, `oc get multiclusterobservability -A`, `oc get managedclusters`
   - Verify feature backend state (operator health, CRDs, expected resources)
   - Log as "CLI-only live validation"

The combination of Playwright (UI) + acm-search (backend) gives better coverage than either tool alone.

If no cluster URL and no `oc` session: "Skipping live validation -- no cluster URL or oc session detected."

### Phase 7: Write Test Case

Using the **acm-test-case-writer** skill, write the test case:

1. Provide the synthesized context from Phase 5
2. Provide live validation results from Phase 6 (if performed)
3. The writer reads conventions, applies area knowledge constraints, spot-checks via MCP, writes the markdown, and self-reviews

Output: `test-case.md` in the run directory.

**STOP checkpoint:** "Test case written: [filename] ([N] steps)."

### Phase 8: Quality Review (MANDATORY GATE)

Using the **acm-test-case-reviewer** skill, review the test case:

1. The reviewer validates format, metadata, discovered vs assumed elements, AC consistency, knowledge cross-reference, Polarion coverage
2. The reviewer MUST perform at least 3 MCP verifications

**After the reviewer returns:**

Run programmatic enforcement:
```bash
python scripts/review_enforcement.py <review-output-file>
```

This script verifies the reviewer's output contains 3+ MCP verification entries, at least one `get_component_source` call, and at least one `search_translations` call. For any metric name, field label, or translation string in expected results, the reviewer MUST verify it against current source code -- stale JIRA description text is a BLOCKING issue. If enforcement fails, the verdict is overridden to NEEDS_FIXES. The script also warns (non-blocking) if the test case describes a conditional feature but lacks a negative scenario step.

**Review loop:**
1. If PASS -> proceed to Phase 9
2. If NEEDS_FIXES -> fix the issues in the test case, re-run the review (max 3 iterations)
3. If still failing after 3 iterations -> show remaining issues to the user

**STOP checkpoint:** "Quality review PASSED."

### Phase 9: Generate Reports

Run the deterministic report script:
```bash
python scripts/report.py <run-directory>
```

This produces:
- `test-case-setup.html` -- Polarion setup section HTML
- `test-case-steps.html` -- Polarion test steps table HTML
- `review-results.json` -- structural validation results
- `SUMMARY.txt` -- human-readable summary

Show the final summary with all output file paths.

## Run Directory Layout

Each run produces artifacts under `runs/<JIRA_ID>/<timestamp>/`:
```
gather-output.json        -- Phase 1: collected data
pr-diff.txt               -- Phase 1: full PR diff
test-case.md              -- Phase 7: primary deliverable
test-case-setup.html      -- Phase 9: Polarion setup HTML
test-case-steps.html      -- Phase 9: Polarion steps HTML
review-results.json       -- Phase 9: structural validation
SUMMARY.txt               -- Phase 9: human-readable summary
```

## Safety Rules

1. **Read-only investigation** -- never modify JIRA tickets, Polarion work items, or cluster resources
2. **No assumed UI elements** -- all labels, routes, selectors come from MCP or investigation
3. **Evidence-based** -- every expected result traces to a source (JIRA AC, code, MCP, live validation)
4. **Convention compliance** -- output passes structural validation
5. **Quality gate** -- never deliver a test case that hasn't passed quality review AND programmatic enforcement
