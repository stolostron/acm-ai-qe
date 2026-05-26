# Pre-Push Quality Gate

Verify code quality before pushing to remote.

## Trigger

- `/pre-push` slash command from Claude Code

## Checks

1. **Unit tests** -- run pytest for all affected apps
2. **Credential scan** -- check staged files for secrets, API tokens, passwords
3. **Forbidden files** -- verify `.mcp.json`, `settings.local.json`, and other gitignored files are not staged
4. **Conventional commits** -- verify commit message format (`type: description`)
5. **CodeRabbit review** -- run `/coderabbit:review uncommitted` if Python source, agents, or schema files changed

## References

- Command: [`.claude/commands/pre-push.md`](../.claude/commands/pre-push.md)
