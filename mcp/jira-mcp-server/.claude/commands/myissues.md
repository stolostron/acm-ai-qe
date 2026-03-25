# My Issues Command

Show a table of all my Jira issues for a specific ACM release version.

## Instructions

### Step 1: Determine ACM Version

Check if a version was already selected earlier in this conversation (from a previous `/myissues` invocation). If so, reuse that version silently — do NOT prompt again.

Only use `AskUserQuestion` to ask for the version if:
- This is the first time `/myissues` is run in this session, OR
- The user explicitly asks to change the version (e.g., "show me 2.16.0 issues", "switch to ACM 2.18.0")

When prompting, pre-fill with the most likely current version based on context. If CLAUDE.md mentions a `fix_version`, use the next minor version as the default guess (e.g., if fix_version is "ACM 2.16.0", guess "ACM 2.17.0"). Common options:

- ACM 2.17.0 (Recommended)
- ACM 2.16.0
- ACM 2.18.0

### Step 2: Search for Issues

Run TWO parallel Jira searches using `search_issues`:

**Query 1 — Fix Version:**
```
project = ACM AND fixVersion = "<version>" AND (assignee = "jpacker@redhat.com" OR reporter = "jpacker@redhat.com") ORDER BY status ASC, priority DESC
```

**Query 2 — Target Version:**
```
project = ACM AND "Target Version" = "<version>" AND (assignee = "jpacker@redhat.com" OR reporter = "jpacker@redhat.com") ORDER BY status ASC, priority DESC
```

Merge the results, deduplicating by issue key.

### Step 3: Check for Recently Worked Issues

Before rendering the table, review the current conversation history. If you performed actions on any issues earlier in this session (e.g., added comments, transitioned, updated, summarized, created tasks for, or otherwise interacted with an issue), then:

1. Note which issues were worked on
2. **Exclude them from the table**
3. State clearly at the top: "Excluded issues worked on in this session: ACM-XXXXX, ACM-YYYYY"

This keeps the table focused on issues that still need attention.

### Step 4: Render the Table

Present the results as a markdown table with these columns:

| Key | Type | Summary | Status | Priority | Fix Version | Target Version |

Sort by: Status ASC (New first, then In Progress, then Closed), then Priority DESC (Critical first).

Add a summary line at the bottom with total counts by status.

### Notes

- Always quote email addresses in JQL to avoid the reserved `@` character error
- The "Target Version" field in JQL must be quoted as `"Target Version"` (not `targetVersion`)
- If both searches return no results, inform the user that no issues were found for that version
