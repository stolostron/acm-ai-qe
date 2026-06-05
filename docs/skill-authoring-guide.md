# Skill Authoring Guide

Standards for writing portable skills in this repository. Based on Anthropic's "The Complete Guide to Building Skills for Claude" (2026) and "Why We Stopped Building Agents and Started Building Skills Instead" (Barry Zhang & Mahesh Murag, Anthropic talk, 2026).

---

## What is a Skill

A skill is a set of instructions -- packaged as a folder -- that teaches an agent how to handle specific tasks. Skills provide expertise (HOW); MCP servers provide connectivity (WHAT the agent CAN do).

| MCP (Connectivity) | Skills (Knowledge) |
|---------------------|--------------------|
| Connects the agent to services | Teaches the agent how to use them well |
| Real-time data access and tool invocation | Captures workflows and best practices |
| What the agent can do | How the agent should do it |

"MCP provides the professional kitchen: access to tools, ingredients, and equipment. Skills provide the recipes: step-by-step instructions on how to create something valuable." -- Anthropic

---

## File Structure

```
skill-name/
├── SKILL.md              # Required -- exactly this name (case-sensitive)
├── scripts/              # Optional -- executable code (Python stdlib only)
├── references/           # Optional -- documentation loaded on demand
└── assets/               # Optional -- templates, static assets
```

**Naming rules:**
- Folder: kebab-case only (`acm-bug-hunter`, not `ACM_Bug_Hunter`)
- No README.md inside the skill folder
- No spaces, underscores, or capitals in folder name

---

## YAML Frontmatter

Every SKILL.md starts with YAML frontmatter between `---` delimiters.

**Required fields:**

```yaml
---
name: skill-name-in-kebab-case
description: >-
  What it does. When to use it. Specific trigger phrases.
  DO NOT TRIGGER: negative triggers (what skill to use instead).
compatibility: >-
  Required: list required MCPs and CLIs.
  Recommended: list recommended MCPs (with degradation note).
  Optional: list optional MCPs.
metadata:
  author: acm-qe
  version: "1.0.0"
---
```

**Security:**
- No XML angle brackets in frontmatter (could inject instructions)
- No "claude" or "anthropic" in skill names (reserved)

---

## Description Writing

The description field determines whether the skill ever gets loaded. Structure: `[WHAT it does] + [WHEN to use it] + [trigger phrases] + [negative triggers]`.

**Rules:**
- Write in third person ("Verifies whether a bug fix has landed" not "I verify bug fixes")
- Include trigger phrase variations users might say
- Include file types if relevant
- Add "DO NOT TRIGGER" with alternative skills for disambiguation

---

## Progressive Disclosure

Skills use a three-level system to manage token cost:

| Level | Content | When Loaded | Budget |
|-------|---------|-------------|--------|
| 1 -- Frontmatter | description, compatibility | Always (~100 tokens) | Keep under 200 words |
| 2 -- SKILL.md body | Full instructions, phases, MCP reference | On skill activation | Keep under 500 lines |
| 3 -- references/ | Decision trees, templates, detailed procedures | On demand during execution | No limit |

Move detailed tables, decision trees, and verbose examples to `references/*.md`. Reference them with relative links: `[verification-patterns.md](references/verification-patterns.md)`.

---

## Instruction Quality

1. **Be specific and actionable**: "Run `gh pr diff <PR_NUMBER> --repo <REPO>`" not "Review the PR diff."
2. **Include error handling**: Document common failures with causes and solutions in a Troubleshooting table.
3. **Reference bundled resources clearly**: "Read [environment-checks.md](references/environment-checks.md) sections 5-6 for Cypher patterns."
4. **Use scripts for deterministic validation**: Code is deterministic; language interpretation isn't. Bundle a script when consistency matters.
5. **Explicit phase gates**: For multi-step workflows, define phases with completion criteria and gate rules.

---

## Skill Patterns

**Sequential Orchestration**: Multi-phase pipelines with explicit gates. Used by: `acm-test-case-generator`, `acm-bug-fix-verifier`, `acm-z-stream-analyzer`.

**Multi-MCP Coordination**: Parallel subagents each using different MCPs, results merged by orchestrator. Used by: `acm-bug-hunter` (Phase 1), `acm-bug-fix-verifier` (Phase 1).

**Iterative Refinement**: Investigation loop with pushback rounds and fresh-agent escalation. Used by: `acm-bug-hunter` (Phase 2 dimension loop).

**Sibling Delegation**: Orchestrator calls a shared skill for a focused sub-task rather than re-implementing. Used by: `acm-bug-fix-verifier` calling `acm-qe-code-analyzer` for Phase 2b.

---

## Portable Skill Principles (This Repo)

1. **Composability via sibling paths**: Within the same category, reference other skills as `../skill-name/SKILL.md`. For cross-category references, use `../../<category>/skill-name/SKILL.md`. Never use absolute paths (`~/.cursor/`, `~/.claude/`, `/Users/`).
2. **No cross-environment references**: Skills here must work for anyone who clones the repo. No machine-specific paths.
3. **MCP fallback patterns**: When a skill uses an MCP that may not be available, document the fallback (e.g., "If jenkins MCP is unavailable, use REST per references/jenkins-without-mcp.md").
4. **Scripts are stdlib-only**: Python scripts in `scripts/` use only the standard library. No pip dependencies. This ensures they run on any machine with Python 3.
5. **Version bumps on functional changes**: Bump `metadata.version` when you change behavior. Cosmetic/doc-only changes don't need a bump.
6. **Subagent spawning**: Use `subagent_type: "general-purpose"` with inline briefs. Never reference Cursor-specific subagent types.

---

## Testing

### Triggering Tests
Verify the skill loads when it should and doesn't when it shouldn't:
- Paraphrases of the trigger phrases should activate the skill
- Unrelated queries should not load it
- If over-triggering: tighten negative triggers in description
- If under-triggering: add more keyword variations

### Functional Tests
Run the skill end-to-end with a known input and verify the output matches expectations. For orchestrators, test individual phases in isolation first.

### Regression
After edits: re-check that `references/` paths resolve, `compatibility` still lists true requirements, and sibling skill paths are valid.

---

## Anti-Patterns

- No `README.md` inside skill folders (all docs go in SKILL.md or references/)
- No cross-environment references (Cursor paths in repo skills or vice versa)
- No secrets in git (use `~/.jenkins/config.json` or env vars, documented in `compatibility`)
- No silent scope downgrade (if a capability is missing, state it; don't silently skip)
- No duplicating sibling skill logic (delegate instead)
- No absolute paths (use `../` relative or `$(git rev-parse --show-toplevel)`)

---

## Reference

- Anthropic: "The Complete Guide to Building Skills for Claude" (2026)
- Anthropic: "Why We Stopped Building Agents and Started Building Skills Instead" (Barry Zhang & Mahesh Murag, 2026)
- This repo's skill inventory and dependency map: [skill-architecture.md](skill-architecture.md)
