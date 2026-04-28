# /pre-push -- Quality gate before pushing

Run this checklist before pushing. If any step fails, fix the issue and restart from Step 1.

## Step 1: Detect which apps changed

```bash
git diff --name-only origin/main...HEAD
```

Identify which app directories have changes: `apps/z-stream-analysis`, `apps/acm-hub-health`, `apps/test-case-generator`, or root-level files.

## Step 2: Run tests for changed apps

For each app with changes, run its test suite:

- **z-stream-analysis**: `cd apps/z-stream-analysis && python -m pytest tests/unit/ tests/regression/ -q`
- **acm-hub-health**: `cd apps/acm-hub-health && python -m pytest tests/regression/ -q`
- **test-case-generator**: `cd apps/test-case-generator && python -m pytest tests/unit/ -q`

Skip apps with no changes. If any test fails, STOP -- fix the failure before proceeding.

## Step 3: Check for credential leaks

```bash
git diff --cached --name-only | grep -iE '\.env$|credentials|\.pem$|\.key$' || echo "Clean"
```

If any matches found, STOP and warn the user. Do not proceed.

## Step 4: Check for forbidden files

Confirm none of these are staged: `.mcp.json`, `settings.local.json`, files under `runs/`, `.claude/traces/`, `.external/`.

```bash
git diff --cached --name-only | grep -iE 'settings\.local\.json|\.mcp\.json|\.claude/traces/|/runs/|\.external/' || echo "Clean"
```

If any matches found, STOP and warn the user.

## Step 5: Summary

Report results:

```
Pre-push check complete.
  Tests:       PASS/FAIL (N apps tested)
  Credentials: CLEAN/WARNING
  Forbidden:   CLEAN/WARNING
```

If all steps passed, ask the user for explicit push approval.
If any step failed: **Do not push. Fix the issues above, then re-run `/pre-push`.**
