# Common Test Case Mistakes

Known quality issues found during test case review. Avoid these when generating test cases.

## Metadata Mistakes

1. **Missing Release field** -- Every test case must have `## Release: X.XX` matching the JIRA fix_versions
2. **Wrong Component** -- Governance area uses `Component: Governance`, not `Component: Virtualization`
3. **Missing Tags** -- Tags should include area-specific keywords (e.g., `ui, governance, discovered-policies`)

## Description Mistakes

1. **Assumed Entry Point** -- Entry point must be discovered via `get_routes()`, not written from memory. Include the route key.
2. **Missing JIRA Coverage** -- Always list the primary JIRA ticket and related tickets
3. **Vague verification list** -- Each numbered item should be a specific testable assertion

## Step Mistakes

1. **CLI as UI substitute** -- Using `oc get` to verify something that should be checked in the UI
2. **Assumed UI labels** -- Using label text without verifying via `search_translations()`
3. **Missing expected results** -- Every step must have explicit expected results
4. **Steps not separated by `---`** -- Horizontal rules between steps are required

## Setup Mistakes

1. **Missing expected output** -- Each `oc` command needs a `# Expected:` comment
2. **Assuming cluster state** -- Setup should verify prerequisites, not assume them
3. **Missing ACM version check** -- First setup command should verify ACM version

## Implementation vs AC Discrepancies

When the JIRA acceptance criteria contradicts the actual code implementation:
- Always test against the **implementation** (what the code does)
- Note the discrepancy in the **Notes** section
- Reference the specific code behavior with file path
