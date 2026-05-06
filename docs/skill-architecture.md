# Skill Architecture

How all 14 portable ACM skills fit together.

## Skill Inventory

### Shared Capability Skills (3)

These are vanilla tools with no app-specific logic. Any skill or workflow can use them.

| Skill | Purpose | MCP Required |
|-------|---------|-------------|
| `acm-knowledge-base` | ACM domain knowledge (9 area architectures, conventions, examples) | None |
| `acm-cluster-health` | 12-layer diagnostic methodology, 14 traps, evidence tiers | None (methodology only) |
| `acm-jenkins-client` | Jenkins CI MCP interface | jenkins |

MCP tools (acm-source, jira, polarion, neo4j-rhacm) are called directly by subagents -- no wrapper skill needed.

### Test Case Generator Skills (4)

| Skill | Purpose | Uses Shared Skills / MCPs |
|-------|---------|--------------------------|
| `acm-test-case-generator` | Orchestrator: 10-phase pipeline from JIRA to Polarion-ready test case | All 3 shared + MCP tools + 3 below |
| `acm-qe-code-analyzer` | PR diff analysis for ACM Console | acm-knowledge-base (+ acm-source, neo4j-rhacm MCPs) |
| `acm-test-case-writer` | Test case markdown authoring with conventions and self-review | acm-knowledge-base (+ acm-source MCP) |
| `acm-test-case-reviewer` | Quality gate with mandatory MCP verification | acm-knowledge-base (+ acm-source MCP) |

### Hub Health Skills (3)

| Skill | Purpose | Uses Shared Skills / MCPs |
|-------|---------|--------------------------|
| `acm-hub-health-check` | Orchestrator: 6-phase cluster diagnosis with 4 depth modes | acm-cluster-health (+ neo4j-rhacm, acm-source MCPs) |
| `acm-cluster-remediation` | Cluster mutation execution with structured approval gates | acm-cluster-health, acm-hub-health-check |
| `acm-knowledge-learner` | Discover unknown components and build knowledge from live cluster | (neo4j-rhacm, acm-source MCPs) |

### Z-Stream Analysis Skills (5)

| Skill | Purpose | Uses Shared Skills / MCPs |
|-------|---------|--------------------------|
| `acm-z-stream-analyzer` | Orchestrator: 4-stage pipeline (gather, diagnose, classify, report) | All 3 shared + MCP tools + 4 below |
| `acm-failure-classifier` | 5-phase classification engine (A through E) with 7 classification types | acm-cluster-health (+ acm-source, neo4j-rhacm, jira, polarion MCPs) |
| `acm-cluster-investigator` | Per-group 12-layer root cause investigation | acm-cluster-health (+ acm-source, neo4j-rhacm, jira, polarion MCPs) |
| `acm-data-enricher` | Data enrichment (selector verification, timeline analysis, knowledge gaps) | (acm-source, jira MCPs) |
| `acm-jenkins-client` | Jenkins CI MCP interface | None |

## Design Principles

### 1. Shared Skills are Tools, Not Workflows
Shared skills expose raw capabilities (MCP interfaces, query syntax, methodology frameworks). They contain zero app-specific workflow logic. All analytical intelligence lives in the orchestrator skills.

### 2. Explicit Context Requirements
Skills that depend on prior context (writer, remediation) declare their requirements and inform the user when context is missing rather than silently degrading into lower-quality investigation. The knowledge learner is the exception -- discovery IS its primary function, so standalone operation is appropriate.

### 3. Progressive Disclosure
- Level 1 (YAML frontmatter): Always loaded (~100 tokens per skill). Tells Claude when to use the skill.
- Level 2 (SKILL.md body): Loaded when relevant. Full instructions.
- Level 3 (references/): Loaded on demand. Detailed reference material.

### 4. Anthropic Guide Compliance
All skills follow the Anthropic "Complete Guide to Building Skills for Claude":
- `name` field: kebab-case, required
- `description` field: WHAT + WHEN, required
- `compatibility` field: MCP requirements declared
- No angle brackets in frontmatter
- No README.md inside skill folders
- `scripts/` for executable code, `references/` for documentation, `assets/` for templates

## Detailed Documentation

- Test Case Generator workflow: [test-case-generator/](test-case-generator/)
- Hub Health workflow: [hub-health/](hub-health/)
- MCP setup: [mcp-setup-guide.md](mcp-setup-guide.md)
