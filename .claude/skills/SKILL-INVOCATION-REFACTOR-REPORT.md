# Skill Invocation Refactor: From Self-Contained to Skill-to-Skill Delegation

**Date:** 2026-05-03
**Purpose:** Refactor the acm-test-case-generator orchestrator to directly invoke shared skills via the Claude Code `Skill` tool instead of embedding duplicate instructions in `references/agents/*.md` files.

---

## Current Architecture (Option A: Self-Contained)

The orchestrator currently embeds ALL investigation logic in 7 agent instruction files under `references/agents/`:

```
acm-test-case-generator/
├── SKILL.md                           # Orchestrator: spawns Agent() with instructions from references/agents/
├── references/
│   └── agents/
│       ├── jira-investigator.md       # 121 lines -- DUPLICATES acm-jira-client + acm-polarion-client content
│       ├── code-analyzer.md           # ~150 lines -- DUPLICATES acm-code-analyzer content
│       ├── ui-discoverer.md           # ~120 lines -- DUPLICATES acm-ui-source content
│       ├── synthesizer.md             # ~100 lines
│       ├── live-validator.md          # ~130 lines
│       ├── test-case-writer.md        # ~150 lines -- DUPLICATES acm-test-case-writer content
│       └── quality-reviewer.md        # ~160 lines -- DUPLICATES acm-test-case-reviewer content
```

**Flow:** Orchestrator reads `references/agents/jira-investigator.md` → spawns Agent() with that text as the prompt → agent works in isolated context → returns results.

**Problem:** The agent instruction files duplicate content from the shared skills. When you update `acm-jira-client/SKILL.md` with a new JQL pattern, the `jira-investigator.md` still has the old patterns. Two copies of the same knowledge that drift apart.

## Target Architecture (Option B: Skill-to-Skill Invocation)

The orchestrator invokes shared skills directly via the `Skill` tool. No duplicated content.

```
acm-test-case-generator/
├── SKILL.md                           # Orchestrator: invokes skills by name via Skill tool
├── references/
│   └── agents/
│       ├── synthesizer.md             # KEPT -- synthesis is TC-gen specific, not a shared skill
│       └── live-validator.md          # KEPT -- live validation combines multiple tools uniquely
```

**Flow:** Orchestrator calls `Skill(acm-jira-client)` with task context → skill loads in conversation → performs JIRA investigation → returns results. OR Orchestrator calls `Skill(acm-code-analyzer)` → skill loads → analyzes PR → returns results.

## Why This Works (Technical Verification)

### 1. The `Skill` tool exists and is available

From the [Claude Code tools reference](https://code.claude.com/docs/en/tools-reference):

```
| Skill | Executes a skill within the main conversation | Yes (permission required) |
```

The `Skill` tool is a first-class tool in Claude Code. It loads a skill's SKILL.md body into the conversation and executes it.

### 2. Our shared skills do NOT have `disable-model-invocation: true`

Verified: only `onboard/SKILL.md` has `disable-model-invocation: true`. All 18 ACM skills have it either absent or `false`. This means the `Skill` tool CAN invoke them.

### 3. Skills with `context: fork` get isolated context

From the [Claude Code skills documentation](https://code.claude.com/docs/en/skills.md#run-skills-in-a-subagent):

> "Add `context: fork` to your frontmatter when you want a skill to run in isolation. The skill content becomes the prompt that drives the subagent. It won't have access to your conversation history."

This gives us the SAME isolated context behavior we get from the `Agent()` tool, but using proper skills instead of embedded instruction files.

### 4. Subagents can have skills preloaded

From the same documentation:

> "Subagent with `skills` field: Subagent's markdown body is system prompt, Claude's delegation message is the task, and preloaded skills + CLAUDE.md are also loaded."

This means a subagent can be launched with specific skills available to it.

## What Changes

### Phase 2: JIRA Investigation

**Current:**
```markdown
Read `${CLAUDE_SKILL_DIR}/references/agents/jira-investigator.md`. 
Spawn a subagent (Agent tool) with the full agent instructions.
```

**New (Option B1 -- Skill with context: fork):**

Update `acm-jira-client/SKILL.md` to add `context: fork` support and a task-oriented mode:

```yaml
---
name: acm-jira-client
description: Interface to Red Hat JIRA...
context: fork    # When invoked by Skill tool, runs in isolated subagent
---
```

Then the orchestrator says:
```markdown
### Phase 2: Investigate JIRA Story

Invoke the `acm-jira-client` skill with this task:

"Investigate JIRA ticket <JIRA_ID>. Read the story, ALL comments, acceptance criteria, 
fix versions, components. Search for QE tracking ticket, sub-tasks, related bugs, 
sibling stories. Check Polarion for existing test case coverage. Write findings to 
<RUN_DIR>/phase2-jira.json in the structured format specified below."
```

**BUT WAIT -- there's a problem with `context: fork`.** The Claude Code docs say:

> "`context: fork` only makes sense for skills with explicit instructions. If your skill contains guidelines like 'use these API conventions' without a task, the subagent receives the guidelines but no actionable prompt."

Our shared skills are GUIDELINES (how to use JIRA MCP, gotchas, JQL patterns) -- not TASKS. They don't have a built-in task to execute. With `context: fork`, the skill would load as the subagent's prompt, but without a specific task, it wouldn't know what to do.

**New (Option B2 -- Skill tool in main context + Agent for isolation):**

The orchestrator uses the `Skill` tool to load the shared skill's instructions INTO its own context (progressive disclosure), then spawns an Agent() with a task that references those loaded instructions:

```markdown
### Phase 2: Investigate JIRA Story

1. Use the Skill tool to load `acm-jira-client` (loads gotchas, JQL patterns, tool reference into context)
2. Use the Skill tool to load `acm-polarion-client` (loads Lucene query syntax, project ID)
3. Spawn a subagent (Agent tool) with this task:

"Using the JIRA and Polarion MCP tools loaded in this session:
- Investigate JIRA ticket <JIRA_ID>
- Read story, ALL comments, ACs, fix versions, components
- Search for QE tracking, sub-tasks, related bugs, siblings
- Check Polarion for existing coverage
- Write to <RUN_DIR>/phase2-jira.json"
```

**Problem:** The Skill tool loads content into the MAIN conversation context, not the subagent's context. The Agent() subagent won't see the skill content that was loaded.

**New (Option B3 -- Subagent with preloaded skills -- CORRECT APPROACH):**

From the docs: "Subagent with `skills` field: Subagent's markdown body is system prompt, Claude's delegation message is the task, and **preloaded skills + CLAUDE.md are also loaded**."

This means we can define subagents (in `.claude/agents/`) that have specific skills preloaded. The subagent gets the skill instructions automatically.

Create `.claude/agents/jira-investigator.md`:
```yaml
---
name: jira-investigator
description: Investigates JIRA tickets for test case generation
skills:
  - acm-jira-client
  - acm-polarion-client
---

You are a JIRA investigation specialist for ACM test case generation. 
Use the acm-jira-client and acm-polarion-client skills loaded in this session.

## Your Task

Given a JIRA ticket ID, investigate it thoroughly and write structured findings 
to a JSON file.

## Process

1. Use JIRA MCP tools (per acm-jira-client skill) to read the story
2. Read ALL comments for implementation decisions and edge cases
3. Search for linked tickets using JQL patterns from the skill
4. Check Polarion for existing coverage using acm-polarion-client skill
5. Write findings to <RUN_DIR>/phase2-jira.json
```

Then the orchestrator spawns this subagent:
```markdown
### Phase 2: Investigate JIRA Story

Spawn a subagent using the `jira-investigator` agent definition:

Agent(description: "JIRA Investigation", prompt: "Investigate <JIRA_ID>. RUN_DIR: <path>")
```

The subagent automatically gets `acm-jira-client` and `acm-polarion-client` skills preloaded via the `skills` field. No duplication needed.

## The Correct Implementation: Option B3

### New Architecture

```
.claude/
├── agents/                                # Subagent definitions with preloaded skills
│   ├── jira-investigator.md               # skills: [acm-jira-client, acm-polarion-client]
│   ├── code-analyzer.md                   # skills: [acm-code-analyzer, acm-knowledge-base]
│   ├── ui-discoverer.md                   # skills: [acm-ui-source]
│   ├── synthesizer.md                     # skills: [acm-knowledge-base]
│   ├── live-validator.md                  # skills: [acm-cluster-health]
│   ├── test-case-writer.md                # skills: [acm-test-case-writer, acm-knowledge-base]
│   └── quality-reviewer.md               # skills: [acm-test-case-reviewer, acm-knowledge-base]
│
├── skills/
│   ├── acm-test-case-generator/           # Orchestrator -- SLIMMED DOWN
│   │   ├── SKILL.md                       # References agents by name, no embedded instructions
│   │   ├── scripts/
│   │   └── references/                    # Only TC-gen specific references (synthesis template, phase gates)
│   │       ├── synthesis-template.md
│   │       └── phase-gates.md
│   │       # NO MORE references/agents/ directory -- moved to .claude/agents/
│   │
│   ├── acm-jira-client/                   # Shared skill -- NOW ACTUALLY USED AT RUNTIME
│   ├── acm-code-analyzer/                 # Shared skill -- NOW ACTUALLY USED AT RUNTIME
│   ├── acm-ui-source/                     # Shared skill -- NOW ACTUALLY USED AT RUNTIME
│   ├── acm-polarion-client/               # Shared skill -- NOW ACTUALLY USED AT RUNTIME
│   ├── acm-neo4j-explorer/                # Shared skill -- NOW ACTUALLY USED AT RUNTIME
│   ├── acm-cluster-health/                # Shared skill -- NOW ACTUALLY USED AT RUNTIME
│   ├── acm-knowledge-base/                # Shared skill -- NOW ACTUALLY USED AT RUNTIME
│   ├── acm-test-case-writer/              # TC-gen skill -- NOW ACTUALLY USED AT RUNTIME
│   └── acm-test-case-reviewer/            # TC-gen skill -- NOW ACTUALLY USED AT RUNTIME
```

### Key Mechanism: `.claude/agents/` with `skills` field

Each subagent definition in `.claude/agents/` uses the `skills` field to declare which skills should be preloaded when the subagent spawns. The subagent gets:
- Its own markdown body as the system prompt (the mission briefing)
- The preloaded skills' SKILL.md content (the tool reference manuals)
- CLAUDE.md content
- The orchestrator's delegation message (the specific task with parameters)

This means:
- **No duplication.** The subagent reads `acm-jira-client/SKILL.md` directly -- no need for a copy in `references/agents/`.
- **Single source of truth.** Update the shared skill, and ALL subagents that use it get the update automatically.
- **Proper skill composition.** The skills ARE runtime dependencies now, not just documentation.
- **Isolated context.** Each subagent has its own context window (same as current Agent() approach).

### What Changes in the Orchestrator SKILL.md

**Current Phase 2:**
```markdown
Read `${CLAUDE_SKILL_DIR}/references/agents/jira-investigator.md`. Spawn a subagent 
(Agent tool, description: "JIRA Investigation") with the full agent instructions.
```

**New Phase 2:**
```markdown
Spawn the `jira-investigator` subagent (Agent tool, description: "JIRA Investigation") with:

<input>
JIRA_ID: <value>
ACM_VERSION: <value>
AREA: <value>
RUN_DIR: <path>
</input>

The subagent has acm-jira-client and acm-polarion-client skills preloaded.
Verify `phase2-jira.json` exists in the run directory.
```

Same pattern for all 7 phases that spawn subagents.

## Migration Plan

### Step 1: Create `.claude/agents/` directory with subagent definitions

Create 7 subagent files at the REPO ROOT `.claude/agents/` level (NOT inside the skill):

| File | Skills Preloaded | Purpose |
|------|-----------------|---------|
| `.claude/agents/jira-investigator.md` | acm-jira-client, acm-polarion-client | Phase 2: JIRA investigation |
| `.claude/agents/code-analyzer.md` | acm-code-analyzer, acm-knowledge-base | Phase 3: PR code analysis |
| `.claude/agents/ui-discoverer.md` | acm-ui-source | Phase 4: UI element discovery |
| `.claude/agents/synthesizer.md` | acm-knowledge-base | Phase 5: Context synthesis |
| `.claude/agents/live-validator.md` | acm-cluster-health | Phase 6: Live validation |
| `.claude/agents/test-case-writer.md` | acm-test-case-writer, acm-knowledge-base | Phase 7: Test case writing |
| `.claude/agents/quality-reviewer.md` | acm-test-case-reviewer, acm-knowledge-base | Phase 8: Quality review |

Each file contains:
- YAML frontmatter with `skills:` list
- A focused mission briefing (WHAT to do, not HOW to use the tools -- the skills handle the HOW)
- The structured output format expected (JSON schema for the output file)

### Step 2: Slim down subagent instructions

The current `references/agents/jira-investigator.md` is 121 lines because it duplicates all the JIRA MCP gotchas, JQL patterns, and Polarion query syntax. The new `.claude/agents/jira-investigator.md` only needs:

```markdown
---
name: jira-investigator
description: Investigates JIRA tickets for test case generation
skills:
  - acm-jira-client
  - acm-polarion-client
---

# JIRA Investigation Agent

You investigate a JIRA ticket to understand what feature changed, why, and what to test.
The acm-jira-client and acm-polarion-client skills are loaded -- use their tools and patterns.

## Your Task

Given a JIRA_ID, ACM_VERSION, AREA, and RUN_DIR:

1. Read the JIRA story: summary, description, acceptance criteria, fix version, components
2. Read ALL comments (implementation decisions, edge cases, QE feedback)
3. Find linked tickets (QE tracking, sub-tasks, related bugs, sibling stories)
4. Check Polarion for existing test case coverage
5. Write structured findings to `<RUN_DIR>/phase2-jira.json`

## Output Format

Write `phase2-jira.json` with this structure:
[... JSON schema ...]
```

~40 lines instead of 121. The tool reference (gotchas, JQL patterns, etc.) comes from the preloaded skills.

### Step 3: Update orchestrator SKILL.md

Replace all "Read references/agents/*.md and spawn Agent()" instructions with "Spawn the <name> subagent" instructions. Remove the `references/agents/` directory entirely.

### Step 4: Test the full pipeline

Run the same test: "Generate a test case for ACM-32282" and verify:
- All 10 phases execute correctly
- Subagents receive the preloaded skills
- Output quality matches or exceeds current implementation
- JSON handoff files are produced correctly

## What This Achieves

| Aspect | Before (Option A) | After (Option B3) |
|--------|-------------------|-------------------|
| Shared skills at runtime | NOT used (documentation only) | ACTUALLY used by subagents |
| Knowledge duplication | 7 agent files duplicate skill content | Zero duplication -- skills are single source of truth |
| Updating a gotcha | Must update skill AND agent file | Update skill once -- all subagents get it |
| Subagent instructions | 121+ lines each (tool reference + mission) | ~40 lines each (mission only, tools from skills) |
| Orchestrator size | References 7 large agent files | References 7 slim agent files |
| Skill value | Standalone use + documentation | Standalone use + documentation + runtime dependency |
| Context isolation | Agent() with embedded prompt | Agent() with preloaded skills (same isolation) |

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| `skills` field in subagent definitions is a Claude Code feature -- not portable | The skills themselves remain portable. Only the subagent wiring is Claude Code-specific. On other platforms, the orchestrator falls back to inline instructions (keep `references/agents/` as a fallback directory). |
| Preloaded skills increase subagent context size | Skills are loaded via progressive disclosure. Only ~600-800 tokens per skill. 2 skills = ~1,400 tokens overhead vs embedding 121-line instructions. NET SAVINGS. |
| Shared skill changes could break the pipeline | This is a FEATURE, not a bug. If someone updates `acm-jira-client` incorrectly, the pipeline breaks immediately -- making the error visible. Currently, the pipeline uses stale copies and the error is hidden. |

## Portability Fallback

For platforms that don't support `.claude/agents/` with `skills` preloading, keep the current `references/agents/` files as a fallback. The orchestrator can check: "If `.claude/agents/jira-investigator.md` exists, use the subagent definition. Otherwise, fall back to `references/agents/jira-investigator.md`."

This gives us:
- **Claude Code:** Full skill-to-skill delegation via subagent preloading
- **Other platforms:** Self-contained fallback with embedded instructions
- **No regression:** Both paths produce the same output
