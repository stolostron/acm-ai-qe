# Quality Review Checklist

## Structural Checks (BLOCKING if wrong)

- [ ] Title: `# RHACM4K-XXXXX - [Tag-Version] Area - Test Name`
- [ ] `## Type: Test Case` (not "Functional")
- [ ] All Polarion fields: Type, Level, Component, Subcomponent, Test Type, Pos/Neg, Importance, Automation, Tags, Release
- [ ] Polarion ID present (RHACM4K-XXXXX format)
- [ ] Status set (Draft or proposed)
- [ ] Created/Updated dates
- [ ] Description has Entry Point (MCP-verified)
- [ ] Description has Dev JIRA Coverage
- [ ] `## Test Steps` header before first step
- [ ] Each step: `### Step N: Title`
- [ ] Each step: numbered actions
- [ ] Each step: bullet expected results
- [ ] Steps separated by `---`
- [ ] CLI-in-steps rule: CLI only for backend validation, not as UI substitute

## MCP Verification (minimum 3, BLOCKING if fewer)

- [ ] `search_translations` for 1-2 key labels
- [ ] `get_routes` for entry point route
- [ ] `get_component_source` for at least ONE factual claim verification

## Content Checks (BLOCKING if wrong)

- [ ] Filter prefixes/conditions match actual source code (not fabricated)
- [ ] Field order matches area knowledge file
- [ ] Empty state behavior matches source code
- [ ] No numeric thresholds stated without evidence
- [ ] AC vs Implementation discrepancies noted with source citations
- [ ] Scope matches target JIRA story (not broader PR)

## Format Checks (WARNING if wrong)

- [ ] Setup commands have `# Expected:` comments
- [ ] Teardown has `--ignore-not-found` on deletes
- [ ] Tags match area conventions
- [ ] Release matches JIRA fix version

## Common Mistakes to Flag

- Entry point assumed (not from `get_routes`)
- UI labels from memory (not from `search_translations` or source)
- CLI used for something that should be a UI check
- Missing expected results after numbered actions
- Missing `---` between steps
- Setup missing ACM version check as first command
- Test case validates broader PR scope instead of target story scope
