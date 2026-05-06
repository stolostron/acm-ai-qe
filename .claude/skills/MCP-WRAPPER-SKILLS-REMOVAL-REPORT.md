# MCP Wrapper Skills Removal Report

**Date:** 2026-05-04
**Issue:** 4 skills (`acm-jira-client`, `acm-ui-source`, `acm-polarion-client`, `acm-neo4j-explorer`) are thin wrappers around MCP tools that add no analytical logic. They are never invoked at runtime by the test case generator pipeline. The subagent instruction files already contain the necessary MCP tool knowledge (gotchas, patterns, usage). These skills can be removed without regression.
**Goal:** Remove the wrapper skills, ensure all MCP tool knowledge is properly embedded in the subagent instruction files that actually use it, and verify no functionality is lost.

---

## Skills to Remove

| Skill | What It Wraps | Lines | Why It's Redundant |
|-------|--------------|-------|-------------------|
| `acm-jira-client` | jira MCP (`get_issue`, `search_issues`) | 83 | Subagent `data-gatherer.md` already has all JIRA gotchas, JQL patterns, component mapping |
| `acm-ui-source` | acm-ui MCP (20 tools: routes, translations, selectors, source) | 98 | Subagents `code-analyzer.md`, `ui-discoverer.md`, `test-case-writer.md`, `quality-reviewer.md` already document which tools to use and how |
| `acm-polarion-client` | polarion MCP (work items, test steps, setup HTML) | 83 | Subagent `data-gatherer.md` and `quality-reviewer.md` already have Polarion usage documented |
| `acm-neo4j-explorer` | neo4j-rhacm MCP (`read_neo4j_cypher`) | 70 | Subagent `code-analyzer.md` already has Cypher query patterns |

**Total:** 4 skills, 334 lines, 7 files (4 SKILL.md + 3 reference files)

---

## Why They're Safe to Remove

### 1. The pipeline never invokes them

Evidence from `acm-test-case-generator/SKILL.md`:
- Phase 1: Spawns `data-gatherer.md` agent (calls JIRA + Polarion MCP directly)
- Phase 2: Spawns `code-analyzer.md` agent (calls acm-ui + neo4j MCP directly)
- Phase 3: Spawns `ui-discoverer.md` agent (calls acm-ui MCP directly)
- Phase 4-8: Other agents call MCPs directly

At NO point does the orchestrator or any subagent use the `Skill()` tool to invoke `acm-jira-client`, `acm-ui-source`, `acm-polarion-client`, or `acm-neo4j-explorer`.

### 2. Subagent instruction files already contain the knowledge

Example -- `references/agents/data-gatherer.md` already has:
```markdown
## JIRA MCP Tools
| Tool | Purpose |
|------|---------|
| `mcp__jira__get_issue(issue_key)` | Full story details |
| `mcp__jira__search_issues(jql)` | Search by JQL |

**Gotchas:**
- `get_issue` does NOT return issue links -- use `search_issues` with JQL
- `get_issue` returns comments inline -- read ALL of them

**JQL patterns:**
search_issues(jql='summary ~ "[QE] --- ACM-XXXXX"')   # QE tracking
search_issues(jql='parent = ACM-XXXXX')                # Sub-tasks
...
```

This is the SAME content that `acm-jira-client/SKILL.md` contains. It's duplicated.

### 3. Standalone use cases don't need skills

If a user says "search JIRA for ACM-30459," Claude Code can call `mcp__jira__get_issue(issue_key="ACM-30459")` directly -- it doesn't need a skill to tell it how. The MCP tool descriptions in the MCP server itself are sufficient for Claude to use them. Skills add value when there's WORKFLOW logic (which tool to call first, what to do with the result). For simple "call this MCP tool," Claude already knows how.

### 4. The `SKILLS_DIR` pattern already accounts for this

The subagent instructions have a `Step 0: Load Skill References` section:
```markdown
## Step 0: Load Skill References (MANDATORY -- before any work)

Read these skill files for MCP tool documentation:
- `${SKILLS_DIR}/acm-jira-client/SKILL.md`
- `${SKILLS_DIR}/acm-polarion-client/SKILL.md`

Use the MCP tools directly as documented in the skills. Do NOT invoke the Skill tool.
```

This means the subagents READ the skill files as documentation but call MCPs directly. After removal, we need to ensure the tool documentation that was in those skills is available elsewhere (either in the subagent instructions themselves, or in a reference file).

---

## What Needs to Change After Removal

### 1. Subagent `Step 0: Load Skill References` sections

Currently, several agents have:
```markdown
## Step 0: Load Skill References (MANDATORY -- before any work)
Read these skill files for MCP tool documentation:
- `${SKILLS_DIR}/acm-jira-client/SKILL.md`
- `${SKILLS_DIR}/acm-ui-source/SKILL.md`
```

**After removal:** These lines must be updated. Two options:

**Option A (recommended): Inline the essential knowledge into each agent file.**

The agents already have 80% of the MCP knowledge inline. The remaining 20% (gotchas, edge cases) from the skill files needs to be merged into the agent instructions. This makes each agent fully self-contained.

**Option B: Create a single `references/mcp-tools.md` reference file.**

Move all MCP tool documentation (gotchas, patterns, tool tables) into ONE reference file at `acm-test-case-generator/references/mcp-tools.md`. Update `Step 0` to read this file instead of the skill files.

### 2. Files to modify (Option A -- inline)

| Agent File | Currently Reads | Action |
|---|---|---|
| `references/agents/data-gatherer.md` | `acm-jira-client`, `acm-polarion-client` | Already has full JIRA docs. Add Polarion Lucene gotchas (project_id always RHACM4K, query syntax is Lucene not JQL). |
| `references/agents/code-analyzer.md` | `acm-ui-source`, `acm-neo4j-explorer` (via `SKILLS_DIR`) | Already has acm-ui tool list. Add: "ALWAYS set_acm_version before any search" gotcha, neo4j graph stats (370 nodes, 541 rels). |
| `references/agents/ui-discoverer.md` | `acm-ui-source` | Already has full acm-ui tool list. Add: "QE repos always use main branch regardless of version" gotcha. |
| `references/agents/test-case-writer.md` | `acm-ui-source`, `acm-knowledge-base` | Already has spot-check instructions. Add version-first gotcha. Keep `acm-knowledge-base` reference (that skill has actual value -- it's a knowledge store, not an MCP wrapper). |
| `references/agents/quality-reviewer.md` | `acm-ui-source`, `acm-polarion-client`, `acm-knowledge-base` | Already has MCP verification list. Add Polarion project_id gotcha. Keep `acm-knowledge-base`. |
| `references/agents/synthesizer.md` | `acm-knowledge-base` | No MCP wrapper skills used. Keep `acm-knowledge-base`. No changes needed. |
| `references/agents/live-validator.md` | None of the wrapper skills | No changes needed. |

### 3. The orchestrator SKILL.md

Remove `SKILLS_DIR` from input blocks if no agent needs it for skill file reading anymore. OR keep it if agents still need `acm-knowledge-base` (which they do -- that skill IS valuable because it's a knowledge store, not an MCP wrapper).

**Decision:** Keep `SKILLS_DIR` because `acm-knowledge-base` is still needed by writer, reviewer, and synthesizer.

### 4. `acm-knowledge-base` stays

To be clear: `acm-knowledge-base` is NOT an MCP wrapper. It contains curated architecture files, conventions, and examples. It provides actual CONTENT (knowledge), not just tool documentation. It stays.

### 5. `acm-jenkins-client` stays (for now)

`acm-jenkins-client` is used by the z-stream pipeline, not the test case generator. It should be evaluated separately when z-stream is reviewed. For this change, leave it untouched.

### 6. `acm-cluster-health` stays

`acm-cluster-health` is NOT an MCP wrapper. It provides the 12-layer diagnostic METHODOLOGY (layers, traps, evidence tiers, dependency chains). It's a knowledge skill, not a tool wrapper. It stays.

---

## Essential Gotchas That MUST Be Preserved

When removing the skills, ensure these critical gotchas are present in the agent instruction files:

### From `acm-jira-client` (must be in `data-gatherer.md`):
- `get_issue` does NOT return issue links -- use `search_issues` with JQL
- Comment field is `comment`, NOT `body`
- `get_issue` returns comments inline -- read ALL of them
- JQL component mapping: Governance=`Governance`, RBAC/Virt=`Virtualization`, Clusters=`Cluster Lifecycle`, Search=`Search`, Apps=`Application Lifecycle`

### From `acm-ui-source` (must be in `code-analyzer.md` and `ui-discoverer.md`):
- MUST call `set_acm_version` before ANY search/get operation
- QE repos always use `main` branch regardless of version setting
- For Fleet Virt/CCLM/MTV: set BOTH `set_acm_version` AND `set_cnv_version` (independent)
- `search_translations` is partial match by default -- set `exact=true` for exact

### From `acm-polarion-client` (must be in `data-gatherer.md` and `quality-reviewer.md`):
- Project ID is ALWAYS `RHACM4K`
- Query syntax is Lucene, NOT JQL (e.g., `type:testcase AND title:"feature"`)
- `get_polarion_work_item_text` sometimes returns empty -- use `fields="@all"` instead

### From `acm-neo4j-explorer` (must be in `code-analyzer.md`):
- Graph has ~370 components, 7 subsystems, 541 relationships
- Requires Podman with `neo4j-rhacm` container running
- All queries are read-only (`--read-only` flag)
- If unavailable, skip dependency analysis (graceful degradation)

---

## Verification After Changes

1. **Run the pipeline on a known ticket** (ACM-30459 or ACM-32282) and verify the test case quality matches the previous run
2. **Check that each agent's JIRA/MCP calls work** -- the gotchas must be correctly applied (e.g., does the JIRA agent still find linked tickets using search_issues, not get_issue?)
3. **Verify Polarion coverage check works** in quality reviewer (project_id = RHACM4K, Lucene query syntax)
4. **Verify acm-ui version setting** -- code analyzer and UI discoverer must still call `set_acm_version` before any search

---

## What This Achieves

| Before | After |
|--------|-------|
| 18 skills | 14 skills (remove 4 MCP wrappers) |
| Duplicated MCP knowledge (in skills AND in agent files) | Single source per agent (no duplication) |
| `SKILLS_DIR` passed to read skill files that just document MCPs | `SKILLS_DIR` only for `acm-knowledge-base` (actual content) |
| Confusion about whether skills are runtime dependencies | Clear: skills are standalone capabilities, agents call MCPs directly |
| 334 lines of redundant skill content | 0 (knowledge merged into agent files where it's actually used) |

---

## Files to Delete

```
.claude/skills/acm-jira-client/SKILL.md
.claude/skills/acm-jira-client/references/jql-patterns.md
.claude/skills/acm-jira-client/references/component-mapping.md
.claude/skills/acm-ui-source/SKILL.md
.claude/skills/acm-ui-source/references/mcp-tool-guide.md
.claude/skills/acm-polarion-client/SKILL.md
.claude/skills/acm-polarion-client/references/query-guide.md
.claude/skills/acm-neo4j-explorer/SKILL.md
.claude/skills/acm-neo4j-explorer/references/cypher-patterns.md
```

## Files to Modify

```
.claude/skills/acm-test-case-generator/references/agents/data-gatherer.md    -- add Polarion gotchas
.claude/skills/acm-test-case-generator/references/agents/code-analyzer.md    -- add acm-ui + neo4j gotchas
.claude/skills/acm-test-case-generator/references/agents/ui-discoverer.md    -- add acm-ui gotchas
.claude/skills/acm-test-case-generator/references/agents/test-case-writer.md -- update Step 0 (remove skill file reads)
.claude/skills/acm-test-case-generator/references/agents/quality-reviewer.md -- add Polarion gotchas, update Step 0
.claude/skills/onboard/SKILL.md                                              -- remove references to deleted skills
.claude/skills/onboard/app-summaries.md                                      -- update skill inventory
docs/skill-architecture.md                                                    -- update skill count and inventory
docs/developer-guide.md                                                       -- update blast radius map
```

## Files to Keep (NOT removing)

```
.claude/skills/acm-knowledge-base/     -- KEEP (actual knowledge content, not MCP wrapper)
.claude/skills/acm-cluster-health/     -- KEEP (diagnostic methodology, not MCP wrapper)
.claude/skills/acm-jenkins-client/     -- KEEP (used by z-stream, evaluate separately)
```
