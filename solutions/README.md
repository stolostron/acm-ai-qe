# Solutions

Solutions are the agent's **error correction notebook** -- a collection of battle-tested SOPs for problems the agent has encountered before.

When the agent encounters an error during work, it searches `solutions/` by extracting keywords from the error context and matching them against solution descriptions. If a match is found, it follows the proven fix.

**Key traits:**
- **Passive trigger** -- not read proactively; only consulted when the agent gets stuck
- **Experience-driven** -- each solution captures a real problem that was hard to solve, along with the verified fix
- **Keyword matching** -- the agent extracts error signatures and searches this directory

> **How solutions differ from skills and workflows:**
>
> | Layer | Analogy | Who initiates |
> |-------|---------|---------------|
> | **Skills** (`.claude/skills/`) | Toolkit | Called by workflows or on demand |
> | **Workflows** (`workflows/`) | Named processes | Human says "start" |
> | **Solutions** (`solutions/`) | Error notebook | Agent self-consults when stuck |
>
> **Relationship to Knowledge DB:** The knowledge database (`.claude/knowledge/`) contains broad architectural knowledge, failure signatures, and health issues. Solutions are narrower -- each one is a specific, actionable SOP for a single problem with exact steps to resolve it.

## Solution Catalog

No solutions yet. Solutions are added organically as agents encounter and resolve real problems during work.

| Solution | Description |
|----------|-------------|
| <!-- add entries as they are created --> | |

## Adding a New Solution

A good solution candidate is a problem that:
- Took significant effort to diagnose or fix
- Is likely to recur (e.g., on other clusters, future upgrades)
- Has a non-obvious root cause or fix that the agent would struggle to rediscover

### Required Frontmatter

```yaml
---
title: Short descriptive title of the problem
symptom: "Exact error message or observable behavior (grep-friendly)"
keywords: [keyword1, keyword2, keyword3]
affected_versions: "ACM 2.x-2.y"
last_verified: 2026-05-26
status: active
---
```

| Field | Purpose |
|-------|---------|
| `title` | Human-readable problem name |
| `symptom` | Exact error string -- agent greps for this |
| `keywords` | Grep-friendly terms (error codes, component names) |
| `affected_versions` | Agent checks if current task version falls in range |
| `last_verified` | Staleness indicator -- solutions older than 6 months get lower trust |
| `status` | `active` = usable, `deprecated` = kept for history but skipped |

### Required Body Structure

```markdown
## Symptom
What the error looks like -- exact error messages, failing commands, observable behavior.

## Root Cause
Why it happens -- the non-obvious explanation.

## Fix
Step-by-step resolution. Include commands, code snippets, or config changes.

## References
Links to JIRA issues, knowledge DB entries, or docs.
```

### Steps

1. Create `solutions/<solution-name>.md` with the frontmatter and body structure above
2. Update the Solution Catalog table in this file
3. Open a PR
