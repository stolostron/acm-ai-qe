# Work Summary Command

Generate a formal summary of work performed in the current AI session, based on repository changes and conversation context.

## Instructions

### Step 1: Gather Repository Changes

Run the following git commands in parallel using Bash:

1. `git diff --stat` — Get a summary of changed files
2. `git diff` — Get the full diff of all changes
3. `git log --oneline -5` — Get recent commits for context
4. `git branch --show-current` — Get the current branch name

### Step 2: Gather Session Context

Review the full conversation history to identify:

- Which Jira issues were referenced, created, updated, transitioned, or commented on
- What tasks were performed (code changes, bug fixes, new features, refactoring, etc.)
- Any decisions made or trade-offs discussed
- Any tools or MCP servers used

### Step 3: Generate the Formal Work Summary

Present a **Formal Work Summary** in this format:

```
## Work Summary — <current date>

**Branch:** <branch name>
**Session scope:** <1-line description of overall work>

### Changes
- <bullet list of meaningful changes, grouped by area/file>

### Notes
- <any relevant decisions, trade-offs, or follow-ups>
```

### Step 4: Generate Git Commit Message Version

Generate a plain-text version suitable for a git commit message:
- No markdown formatting, no special characters (no backticks, asterisks, pipes, or angle brackets)
- First line is a concise summary under 72 characters
- Followed by a blank line and bullet points describing the changes
- Use only ASCII characters, hyphens, and standard punctuation
- This message will be used directly in CLI commands (e.g., `git commit -m`), so avoid characters that interfere with shell interpretation (quotes, backticks, dollar signs, parentheses, etc.)

Present it in a code block labeled **Git Commit Message**.

### Step 5: Offer to Add Summary to Jira

Use `AskUserQuestion` to ask the user:

> "Would you like to add this summary as a comment to a Jira issue? If so, provide the issue key (e.g., ACM-12345)."

- If the user provides an issue key, add the Formal Work Summary (from Step 3) as a comment using `add_comment`.
- If the user declines, skip this step.

### Step 6: Remind About Git References

After the summary is posted (or skipped), display this reminder:

```
Reminder: Once you commit and push your changes, remember to add the following to the Jira issue:
  - Git Commit SHA (from `git log --oneline -1`)
  - Git Pull Request URL (after creating the PR)
```

## Notes

- If there are no repository changes (clean working tree), still generate the summary based on conversation context and Jira activity
- If there is no Jira activity in the session, omit the "Jira Activity" section
- Keep the summary factual and concise — no filler or speculation
