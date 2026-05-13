# Agent Skills design primer (Anthropic)

This skill follows the **Agent Skills** model: a folder with `SKILL.md`, optional `scripts/`, and optional `references/` ([Anthropic skills documentation](https://www.anthropic.com/news/skills) and community guides).

## Core principles (apply to every change)

1. **Progressive disclosure** -- YAML `description` is level 1 (when to use). `SKILL.md` body is level 2. `references/*.md` and `scripts/*` are level 3 (load only when needed).
2. **MCP + skills** -- If the host exposes MCP (e.g. Jenkins, Google), use it for speed. If not, this pack still works: the refresh script uses Jenkins REST only; sheet data is optional. See [jenkins-without-mcp.md](jenkins-without-mcp.md).
3. **Composability (repo-local only)** -- Delegate to sibling skills **in this repository** under `.claude/skills/` using relative paths (see [sibling-skills.md](sibling-skills.md)). Do not assume skills that exist only outside this clone.
4. **Portability** -- All authoritative instructions live under this repo’s `.claude/skills/acm-environment-finder/`. Optional host config (`~/.jenkins/config.json`, VPN) is documented in `compatibility`, not committed.
5. **Scripts as tools** -- Prefer the bundled `refresh-inventory.py` so behavior stays deterministic and reviewable.

## Further reading

- Video (skills architecture, scripts, ecosystem): [YouTube: Agent skills and general agents](https://www.youtube.com/watch?v=CEvIs9y1uog)
- Iteration: use Anthropic’s **skill-creator** workflow (“review this skill and suggest improvements”) after real sessions.

## What not to put in the skill folder

- No `README.md` inside the skill directory (repo-level README for GitHub is separate).
- No secrets in git; use local `~/.jenkins/config.json` or env vars only.
