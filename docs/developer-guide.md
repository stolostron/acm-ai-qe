# Developer Guide: Contributing to the ACM Skill Pack

## Architecture Overview

The skill pack has 3 layers:

1. **Shared skills** (3): Methodology and domain knowledge with zero workflow logic. Safe to modify independently.
2. **App-specific skills** (8): Workflow logic for specific use cases. Modify with awareness of the orchestrator that calls them.
3. **Orchestrators** (3): Pipeline controllers that compose shared and app-specific skills. Modify with full system understanding.

MCP tools (acm-source, jira, polarion, neo4j-rhacm) are called directly by subagents -- no wrapper skill needed.

See `docs/skill-architecture.md` for the complete inventory with MCP dependencies.

## Blast Radius Map

When you modify a skill, here's what could be affected:

### Shared Skills (safe to modify independently)

| Skill | What Could Break | Risk |
|---|---|---|
| `acm-jenkins-client` | Nothing (vanilla MCP interface) | Low |
| `acm-cluster-health` | Nothing (methodology/reference only, no executable logic) | Low |
| `acm-knowledge-base` | Area knowledge consumers (writer, reviewer) may see different constraints | Low -- verify downstream |

### App-Specific Skills

| Skill | Consumed By | What Could Break | Risk |
|---|---|---|---|
| `acm-qe-code-analyzer` | TC-gen Phase 3 | Code analysis output format changes affect synthesis | Medium |
| `acm-test-case-writer` | TC-gen Phase 7 | Test case markdown format changes affect quality review and report.py | Medium |
| `acm-test-case-reviewer` | TC-gen Phase 8 | Verdict logic changes affect whether pipeline proceeds | Medium |
| `acm-failure-classifier` | Z-stream Stage 2 | Classification logic changes affect all failure reports | High |
| `acm-cluster-investigator` | Z-stream Stage 2 | Investigation evidence changes affect classification | High |
| `acm-data-enricher` | Z-stream Stage 2 | Enrichment data format changes affect analysis | Medium |
| `acm-hub-health-check` | Hub health pipeline; remediation depends on its findings | Diagnostic logic changes affect report and remediation | High |
| `acm-cluster-remediation` | Hub health pipeline | Mutation behavior changes affect cluster state | High |
| `acm-knowledge-learner` | Hub health pipeline | Knowledge file writes change what future runs see | Low |

### Orchestrators (modify with full system understanding)

| Skill | What Could Break | Risk |
|---|---|---|
| `acm-test-case-generator` | Entire TC-gen pipeline (10 phases, 6 agents, 9 skills) | High |
| `acm-z-stream-analyzer` | Entire z-stream pipeline (4 stages, 3 agents, 5 skills) | High |
| `acm-hub-health-check` | Full diagnostic pipeline (6 phases, remediation, learning) | High |

## Hello World: Your First Contribution

### Task 1: Add an area architecture file to acm-knowledge-base

You've been asked to document a new ACM area's architecture.

**Step 1:** Create the file:
```
.claude/skills/acm-knowledge-base/references/architecture/new-area.md
```

**Step 2:** Add the architecture documentation following the pattern in existing area files (governance.md, rbac.md, etc.).

**Step 3:** Test it in isolation:
```bash
claude
> Use the acm-knowledge-base skill. What do you know about the new-area architecture?
```

Claude loads the acm-knowledge-base skill and reads your new area file. No orchestrator involved, no pipeline, no risk to other skills.

### Task 2: Fix an area knowledge file

You've discovered that the governance area's field order documentation is wrong.

**Step 1:** Open:
```
.claude/skills/acm-knowledge-base/references/architecture/governance.md
```

**Step 2:** Fix the field order to match the actual product.

**Step 3:** Verify via MCP (recommended):
```bash
claude
> Set ACM version to 2.17, then read the source of
  PolicyTemplateDetails.tsx and tell me the description list field order.
```

**Step 4:** The knowledge file is used as a constraint by the writer and reviewer. Your fix ensures future test cases use the correct field order. No orchestrator changes needed.

### Task 3: Add an eval assertion

**Step 1:** Open:
```
.claude/skills/acm-test-case-generator/evals/evals.json
```

**Step 2:** Add an assertion to an existing eval:
```json
{
  "id": 1,
  "assertions": [
    "... existing assertions ...",
    "Setup section includes ACM version verification as the first command"
  ]
}
```

**Step 3:** Run the eval by generating a test case and checking the assertion manually.

## Testing a Skill in Isolation

Every skill can be tested independently without the full pipeline:

```bash
# Test code analyzer
claude
> Use the acm-qe-code-analyzer skill to analyze PR #5790 in stolostron/console.

# Test writer (with manual context)
claude
> Use the acm-test-case-writer skill. Here's the context:
  JIRA: ACM-30459, ACs: [paste], PR diff: [summary], UI elements: [list]

# Test reviewer
claude
> Use the acm-test-case-reviewer skill to review the test case at
  runs/ACM-30459/.../test-case.md

# Test MCP tools directly (no wrapper skill needed)
claude
> Read JIRA ticket ACM-30459, show me the ACs and comments.
> Set ACM version to 2.17, search translations for "Labels".
```

Each runs in isolation -- no orchestrator, no pipeline, no multi-minute wait.

## Reusing Shared Skills for a New Domain

The 3 shared skills (cluster-health, jenkins-client, knowledge-base) are designed for reuse by any ACM-related application. MCP tools (acm-source, jira, polarion, neo4j-rhacm) are called directly by subagents without wrapper skills.

To build a new application (e.g., "ACM Release Readiness Checker"):

1. Create a new orchestrator skill: `.claude/skills/acm-release-readiness/SKILL.md`
2. In its SKILL.md, reference the shared skills by name in the description and body
3. Write your pipeline phases -- the shared skills provide the capabilities
4. Add app-specific skills if needed (e.g., `acm-release-validator/`)
5. Add domain knowledge to `acm-knowledge-base/references/` or your own skill's `references/`

You don't modify any shared skill. You just use them with different instructions in your orchestrator.

## Modifying an Orchestrator

Orchestrators are the highest-risk files. Before modifying one:

1. **Read the full SKILL.md** to understand all phases and their dependencies
2. **Check the blast radius** -- which skills does this orchestrator call? Which scripts?
3. **Run the evals** after your change: check `evals/evals.json` in the orchestrator's directory
4. **Verify downstream**: if you changed phase ordering or output format, check that downstream phases still consume the correct data

## File Locations

```
.claude/skills/
  <skill-name>/
    SKILL.md              -- Skill definition (frontmatter + instructions)
    references/           -- Reference material loaded on demand
    scripts/              -- Executable scripts (gather.py, report.py, etc.)
    evals/                -- Eval definitions (orchestrators only)
    assets/               -- Templates and static assets
```

## Conventions

- Skill names: `acm-<name>`, kebab-case, 1-64 characters
- SKILL.md: under 800 lines
- Frontmatter: `name`, `description`, `compatibility`, `metadata` (author, version)
- No README.md inside skill directories
- Reference files use relative paths from the skill root
- Scripts have zero external dependencies (stdlib only)
