# Contributing

## Adding a New Skill

### 1. Choose a Category

| Category | When to use |
|----------|-------------|
| `shared/` | Cross-cutting tools used by multiple domains |
| `test-case-gen/` | Polarion test case generation pipeline |
| `hub-health/` | Hub cluster diagnostics and remediation |
| `z-stream/` | Jenkins pipeline failure analysis |
| `investigation/` | Bug hunting and fix verification |

If none fit, propose a new category in your PR description.

### 2. Create the Skill Directory

```
skills/<category>/acm-<name>/
├── SKILL.md              # Entry point (required)
├── references/            # Supporting docs (optional)
└── scripts/               # Python/shell scripts (optional)
```

### 3. Write SKILL.md

Every SKILL.md must have YAML frontmatter:

```yaml
name: acm-<name>
description: One-line description of what this skill does
```

Body guidelines:
- Under 500 lines total
- Use `${CLAUDE_SKILL_DIR}` for paths relative to the skill
- Use `${SKILLS_DIR}` (resolves to `skills/`) for cross-skill references
- Knowledge refs: `${CLAUDE_SKILL_DIR}/../../../.claude/knowledge/<domain>/`
- Same-category sibling: `../acm-other-skill/SKILL.md`
- Cross-category: `../../<category>/acm-other-skill/SKILL.md`

### 4. Update Catalogs

Add your skill to:
- `skills/README.md` — under the appropriate category table
- `docs/skill-architecture.md` — in the domain section

### 5. Validate

```bash
make lint        # Frontmatter checks
make validate    # Catalog consistency
bash scripts/test-skill-paths.sh  # Path integrity
```

## Modifying Existing Skills

When changing paths or cross-references, run `bash scripts/test-skill-paths.sh` before committing. This catches broken relative paths.

## Commit Messages

Use conventional format: `type: concise description`

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`

## Pre-Push

Run `/pre-push` or `make test` before pushing. This runs all app test suites plus skill validation.
