# Knowledge Sweep

Investigate ACM subsystems and update the shared knowledge database with verified findings.

## Trigger

- On demand: "investigate [topic]", "learn about [subsystem]", "update knowledge", "deep dive into [area]"
- Uses the `investigate-and-learn` portable skill (Cursor) or `acm-knowledge-learner` skill (Claude Code)

## Phases

1. **Gather** -- parallel MCP queries across JIRA, GitHub, Polarion, Neo4j, acm-source, acm-search, acm-kubectl
2. **Correlate** -- cross-source correlation to identify verified facts
3. **Store** -- write verified, durable facts to `.claude/knowledge/` following the directory map and format conventions
4. **Report** -- structured report to user with findings and what was stored

## Write Protocol

1. Identify target file from directory map (architecture, failures, health, ui, automation, baselines, data-flow)
2. Read the target file first
3. Check for duplicates (semantic match, not exact string)
4. Append to appropriate section, matching existing format
5. Only write verified facts (confirmed via live cluster, source code, docs, or JIRA)

## Knowledge DB Structure

- Architecture: `.claude/knowledge/architecture/<subsystem>/architecture.md`
- Failure patterns: `.claude/knowledge/failures/<subsystem>/failure-signatures.md`
- Health issues: `.claude/knowledge/health/<subsystem>/known-issues.md`
- UI behavior: `.claude/knowledge/ui/<area>.md`
- Baselines: `.claude/knowledge/baselines/*.yaml`
- Automation: `.claude/knowledge/automation/{cypress,playwright}/<area>.md`

## References

- Knowledge DB: [`.claude/knowledge/README.md`](../.claude/knowledge/README.md)
- CLAUDE.md knowledge write protocol section
