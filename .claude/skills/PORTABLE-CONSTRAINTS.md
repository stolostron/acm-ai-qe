# Portable skills (`.claude/skills/`)

Skills in this directory are meant to work for **anyone who clones this repository**. Keep them self-contained:

1. **References** -- Link only files under this repo (e.g. sibling skills via `../other-skill/SKILL.md`, `references/*.md`, `scripts/*`). Do not require personal-only paths such as `~/.cursor/skills/...` or skill names that exist only on one developer’s machine.
2. **Host tools (MCP)** -- Skills may assume **MCP is configured** for interactive agents (e.g. Jenkins, JIRA, Google) when that matches your team’s dual setup (Cursor + Claude Code, same stack except Engram). Still document **REST / stdlib / `oc`** fallbacks so a clone or CI job works without loading an MCP.
3. **Secrets** -- Never commit tokens. Local config paths (e.g. `~/.jenkins/config.json`) are OK to mention as runtime expectations.
4. **Sibling skills** -- If you depend on another workflow, that skill should live under `.claude/skills/` in the same repo and be referenced by **relative** path from your skill folder.
5. **Cursor `~/.cursor/skills/`** -- Optional. The file `CURSOR-SYMLINK-INTEGRATION.md` is **only** for mirroring repo skills into Cursor’s global directory; **clone + `.claude/skills/` use never requires it.**

When adding a new portable skill, review it for hard-coded dependencies on tooling that the repository does not ship.
