# Cursor + portable skills (optional mirror only)

> **Not required for the repository.** Anyone who **clones this repo** and uses skills from **`ai_systems_v2/.claude/skills/`** (e.g. Claude Code with `CLAUDE_SKILL_DIR` under the clone) already has a **self-contained** layout: sibling paths like `../acm-hub-health-check/SKILL.md` and knowledge at **`.claude/knowledge/`** resolve **inside the clone only**. No `~/.cursor` directory is involved.

This document is **only** for developers who **also** want the **same files** to appear under **`~/.cursor/skills/`** (Cursor's global skill directory) **without** maintaining a second copy. That is a **personal IDE convenience**, not a dependency of the portable skill pack.

---

Portable skills live under this directory (`ai_systems_v2/.claude/skills/`). To mirror them into Cursor `~/.cursor/skills/` via **symlinks** (optional):

## Why symlinks (Cursor mirror only)

Skills such as `acm-hub-health-check` resolve knowledge with:

`KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/`

- **From the clone:** `.claude/skills/acm-hub-health-check/` → `../../knowledge` = `.claude/knowledge/` in the repo. **Works with no symlinks.**
- **From `~/.cursor/skills/`:** if you symlink only the skill, `../../knowledge` becomes `~/.cursor/knowledge/`, so you must also symlink **`~/.cursor/knowledge/`** → the repo's `.claude/knowledge/` tree. **Only applies to that optional Cursor layout.**

## One-time setup (adjust `REPO` to your clone path)

```bash
REPO="/path/to/your/clone/ai_systems_v2"
CUR="$HOME/.cursor/skills"
KN="$HOME/.cursor/knowledge"
mkdir -p "$CUR"
ln -sfn "$REPO/.claude/skills/acm-hub-health-check" "$CUR/acm-hub-health-check"
ln -sfn "$REPO/.claude/skills/acm-cluster-health" "$CUR/acm-cluster-health"
ln -sfn "$REPO/.claude/skills/acm-cluster-remediation" "$CUR/acm-cluster-remediation"
ln -sfn "$REPO/.claude/knowledge" "$KN"
```

Keep **`acm-environment-finder`** (and other Cursor-only orchestration) as normal files under `~/.cursor/skills/` if you customize them; have them **delegate** to `~/.cursor/skills/acm-hub-health-check/SKILL.md` after kubeconfig is ready.

## Verify

```bash
test -f "$HOME/.cursor/skills/acm-hub-health-check/SKILL.md" && echo OK
test -f "$HOME/.cursor/knowledge/README.md" && echo OK
```
