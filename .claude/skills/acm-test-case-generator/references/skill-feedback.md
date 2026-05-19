# Skill Feedback Protocol

When a skill file produces incorrect guidance during pipeline execution, report the issue so it can be fixed for future runs.

## When to Report

- A knowledge-base architecture file has stale field orders, component names, or filter conditions
- An MCP gotcha in an agent instruction file is wrong or outdated (tool behavior changed)
- A phase gate rule causes incorrect pass/fail decisions
- The synthesis template's conflict resolution hierarchy produces wrong results
- A convention rule in the writer or reviewer produces incorrect test case formatting
- A credential extraction pattern fails to match a valid input format

## Where to Report

File a GitHub issue on the repository configured as **`origin`** for your **`ai_systems_v2`** clone (see **`git remote -v`** from that directory). From the repo root:

```bash
cd /path/to/ai_systems_v2
gh issue create \
  --title "Skill feedback: <brief description>" \
  --label "skill-feedback" \
  --body "$(cat <<'EOF'
## Skill File
`<path relative to .claude/skills/>`

## Current Guidance
<quote the incorrect instruction from the skill file>

## Correct Behavior
<what the instruction should say, with evidence>

## Evidence
<MCP output, source code reference, live UI observation, or pipeline run that demonstrates the correct behavior>

## Pipeline Run
<JIRA ID and run directory path, if applicable>
EOF
)"
```

## What NOT to Report

- Transient MCP failures (tool timeout, network error) -- these are infrastructure, not skill defects
- Test case quality issues caused by missing investigation data -- the skill worked correctly with the data it had
- Feature requests or architectural suggestions -- use the repo's standard issue template instead
