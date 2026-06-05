# Skill Architecture

How all 17 portable ACM skills fit together. Skills are organized by domain under `skills/<category>/`. For skill authoring standards, see [skill-authoring-guide.md](skill-authoring-guide.md).

## Skill Inventory

### Shared Capability Skills — `skills/shared/` (4)

These are vanilla tools with no app-specific logic. Any skill or workflow can use them.

| Skill | Purpose | MCP Required |
|-------|---------|-------------|
| `acm-knowledge-base` | ACM domain knowledge (9 area architectures, conventions, examples) | None |
| `acm-cluster-health` | 12-layer diagnostic methodology, 14 traps, evidence tiers | None (methodology only) |
| `acm-jenkins-client` | Jenkins CI MCP interface | jenkins |

MCP tools (acm-source, jira, polarion, neo4j-rhacm) are called directly by subagents -- no wrapper skill needed.

### Test Case Generator Skills — `skills/test-case-gen/` (4)

| Skill | Purpose | Uses Shared Skills / MCPs |
|-------|---------|--------------------------|
| `acm-test-case-generator` | Orchestrator: 10-phase pipeline from JIRA to Polarion-ready test case | All 3 shared + MCP tools + 3 below |
| `acm-qe-code-analyzer` | PR diff analysis for ACM Console | acm-knowledge-base (+ acm-source, neo4j-rhacm MCPs) |
| `acm-test-case-writer` | Test case markdown authoring with conventions and self-review | acm-knowledge-base (+ acm-source MCP) |
| `acm-test-case-reviewer` | Quality gate with mandatory MCP verification | acm-knowledge-base (+ acm-source MCP) |

Skill selection / description disambiguation for this workflow: [test-case-generator/SKILL-DISAMBIGUATION-REPORT.md](test-case-generator/SKILL-DISAMBIGUATION-REPORT.md).

### Hub Health Skills — `skills/hub-health/` (3)

| Skill | Purpose | Uses Shared Skills / MCPs |
|-------|---------|--------------------------|
| `acm-hub-health-check` | Orchestrator: 6-phase cluster diagnosis with 4 depth modes | acm-cluster-health (+ neo4j-rhacm, acm-source MCPs) |
| `acm-cluster-remediation` | Cluster mutation execution with structured approval gates | acm-cluster-health, acm-hub-health-check |
| `acm-knowledge-learner` | Discover unknown components and build knowledge from live cluster | (neo4j-rhacm, acm-source MCPs) |

### Z-Stream Analysis Skills — `skills/z-stream/` (5)

| Skill | Purpose | Uses Shared Skills / MCPs |
|-------|---------|--------------------------|
| `acm-z-stream-analyzer` | Orchestrator: 5-stage pipeline (oracle, gather, diagnose, classify, report) | All 3 shared + MCP tools + 4 below |
| `acm-failure-classifier` | 5-phase classification engine (A through E) with 7 classification types | acm-cluster-health (+ acm-source, neo4j-rhacm, jira, polarion MCPs) |
| `acm-cluster-investigator` | Per-group 12-layer root cause investigation | acm-cluster-health (+ acm-source, neo4j-rhacm, jira, polarion MCPs) |
| `acm-data-enricher` | Data enrichment (selector verification, timeline analysis, knowledge gaps) | (acm-source, jira MCPs) |
| `acm-jenkins-client` | Jenkins CI MCP interface | None |

### Bug Investigation Skills — `skills/investigation/` (2)

| Skill | Purpose | Uses Shared Skills / MCPs |
|-------|---------|--------------------------|
| `acm-bug-hunter` | Orchestrator: 10-dimension implementation audit using test cases as starting points | acm-qe-code-analyzer, acm-knowledge-base (+ jira, acm-source, polarion, neo4j-rhacm MCPs) |
| `acm-bug-fix-verifier` | Orchestrator: 7-phase pipeline to verify bug fixes landed in target environments | acm-qe-code-analyzer (+ jira, neo4j-rhacm, acm-source, playwright, acm-search, acm-kubectl MCPs) |

### Utility Skills — in `skills/shared/` (1)

| Skill | Purpose | MCP Required |
|-------|---------|-------------|
| `onboard` | First-run MCP configuration wizard | Various |

---

## Design Principles

### 1. Shared Skills are Tools, Not Workflows
Shared skills expose raw capabilities (MCP interfaces, query syntax, methodology frameworks). They contain zero app-specific workflow logic. All analytical intelligence lives in the orchestrator skills.

### 2. Explicit Context Requirements
Skills that depend on prior context (writer, remediation) declare their requirements and inform the user when context is missing rather than silently degrading. The knowledge learner is the exception -- discovery IS its primary function.

### 3. Progressive Disclosure
- Level 1 (YAML frontmatter): Always loaded (~100 tokens per skill). Tells Claude when to use the skill.
- Level 2 (SKILL.md body): Loaded when relevant. Full instructions.
- Level 3 (references/): Loaded on demand. Detailed reference material.

### 4. Anthropic Guide Compliance
All skills follow the Anthropic "Complete Guide to Building Skills for Claude". Full standards in [skill-authoring-guide.md](skill-authoring-guide.md).

---

## Blast Radius Map

When you modify a skill, here's what could be affected.

### Shared Skills (safe to modify independently)

| Skill | What Could Break | Risk |
|---|---|---|
| `acm-jenkins-client` | Nothing (vanilla MCP interface) | Low |
| `acm-cluster-health` | Nothing (methodology/reference only) | Low |
| `acm-knowledge-base` | Area knowledge consumers (writer, reviewer) may see different constraints | Low |

### App-Specific Skills

| Skill | Consumed By | What Could Break | Risk |
|---|---|---|---|
| `acm-qe-code-analyzer` | TC-gen Phase 2, bug-fix-verifier Phase 2b | Code analysis output format changes affect synthesis | Medium |
| `acm-test-case-writer` | TC-gen Phase 6 | Test case markdown format changes affect quality review | Medium |
| `acm-test-case-reviewer` | TC-gen Phase 7 | Verdict logic changes affect whether pipeline proceeds | Medium |
| `acm-failure-classifier` | Z-stream Stage 2 | Classification logic changes affect all failure reports | High |
| `acm-cluster-investigator` | Z-stream Stage 2 | Investigation evidence changes affect classification | High |
| `acm-data-enricher` | Z-stream Stage 2 | Enrichment data format changes affect analysis | Medium |
| `acm-hub-health-check` | Hub health pipeline; remediation depends on findings | Diagnostic logic changes affect report and remediation | High |
| `acm-cluster-remediation` | Hub health pipeline | Mutation behavior changes affect cluster state | High |
| `acm-knowledge-learner` | Hub health pipeline | Knowledge file writes change what future runs see | Low |

### Orchestrators (modify with full system understanding)

| Skill | What Could Break | Risk |
|---|---|---|
| `acm-test-case-generator` | Entire TC-gen pipeline (9 phases, 7 agent files, 6 skills) | High |
| `acm-z-stream-analyzer` | Entire z-stream pipeline (4 stages, 3 agents, 5 skills) | High |
| `acm-hub-health-check` | Full diagnostic pipeline (6 phases, remediation, learning) | High |
| `acm-bug-hunter` | Bug hunt pipeline (6 phases, per-dimension subagents) | High |
| `acm-bug-fix-verifier` | Verification pipeline (7 phases, JIRA/PR/env investigation, Playwright) | High |

---

## Contributing

### Testing a Skill in Isolation

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

### Reusing Shared Skills for a New Domain

The 3 shared skills are designed for reuse by any ACM-related workflow. To build a new application:

1. Create a new orchestrator skill: `skills/<category>/acm-new-workflow/SKILL.md`
2. Reference shared skills by name in the description and body
3. Write your pipeline phases -- shared skills provide the capabilities
4. Add app-specific skills if needed (e.g., `acm-new-validator/`)
5. Add domain knowledge to `acm-knowledge-base/references/` or your own skill's `references/`

You don't modify any shared skill. You just use them with different instructions in your orchestrator.

### Modifying an Orchestrator

Orchestrators are the highest-risk files. Before modifying one:

1. **Read the full SKILL.md** to understand all phases and their dependencies
2. **Check the blast radius** tables above -- which skills does this orchestrator call?
3. **Run the evals** after your change: check `evals/evals.json` in the orchestrator's directory
4. **Verify downstream**: if you changed phase ordering or output format, check that downstream phases still consume the correct data

---

## Detailed Documentation

- Test Case Generator workflow: [test-case-generator/](test-case-generator/)
- Hub Health workflow: [hub-health/](hub-health/)
- MCP setup: [mcp-setup-guide.md](mcp-setup-guide.md)
- Skill authoring standards: [skill-authoring-guide.md](skill-authoring-guide.md)
