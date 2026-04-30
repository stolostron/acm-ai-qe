# Skill Architecture

How all 18 portable ACM skills fit together.

## Skill Inventory

### Shared Capability Skills (6)

These are vanilla tools with no app-specific logic. Any skill or workflow can use them.

| Skill | Purpose | MCP Required |
|-------|---------|-------------|
| `acm-knowledge-base` | ACM domain knowledge (9 area architectures, conventions, examples) | None |
| `acm-neo4j-explorer` | RHACM component dependency graph queries | neo4j-rhacm |
| `acm-ui-source` | ACM Console source code queries (routes, translations, selectors, components) | acm-ui |
| `acm-jira-client` | JIRA ticket reading and JQL search | jira |
| `acm-polarion-client` | Polarion test case queries and work item access | polarion |
| `acm-cluster-health` | 12-layer diagnostic methodology, 14 traps, evidence tiers | None (methodology only) |

### Test Case Generator Skills (4)

| Skill | Purpose | Uses Shared Skills |
|-------|---------|-------------------|
| `acm-test-case-generator` | Orchestrator: 10-phase pipeline from JIRA to Polarion-ready test case | All 6 shared + 3 below |
| `acm-code-analyzer` | PR diff analysis for ACM Console | acm-ui-source, acm-knowledge-base, acm-neo4j-explorer |
| `acm-test-case-writer` | Test case markdown authoring with conventions and self-review | acm-ui-source, acm-knowledge-base |
| `acm-test-case-reviewer` | Quality gate with mandatory MCP verification | acm-ui-source, acm-polarion-client, acm-knowledge-base |

### Hub Health Skills (3)

| Skill | Purpose | Uses Shared Skills |
|-------|---------|-------------------|
| `acm-hub-health-check` | Orchestrator: 6-phase cluster diagnosis with 4 depth modes | acm-cluster-health, acm-neo4j-explorer, acm-ui-source |
| `acm-cluster-remediation` | Cluster mutation execution with structured approval gates | acm-cluster-health, acm-hub-health-check |
| `acm-knowledge-learner` | Discover unknown components and build knowledge from live cluster | acm-neo4j-explorer, acm-ui-source |

### Z-Stream Analysis Skills (5)

| Skill | Purpose | Uses Shared Skills |
|-------|---------|-------------------|
| `acm-z-stream-analyzer` | Orchestrator: 4-stage pipeline (gather, diagnose, classify, report) | All shared + 4 below |
| `acm-failure-classifier` | 5-phase classification engine (A through E) with 7 classification types | acm-cluster-health, acm-ui-source, acm-neo4j-explorer, acm-jira-client, acm-polarion-client |
| `acm-cluster-investigator` | Per-group 12-layer root cause investigation | acm-cluster-health, acm-ui-source, acm-neo4j-explorer, acm-jira-client, acm-polarion-client |
| `acm-data-enricher` | Data enrichment (selector verification, timeline analysis, knowledge gaps) | acm-ui-source, acm-jira-client |
| `acm-jenkins-client` | Jenkins CI MCP interface | None (vanilla shared) |

## Design Principles

### 1. Shared Skills are Tools, Not Workflows
Shared skills expose raw capabilities (MCP interfaces, query syntax, methodology frameworks). They contain zero app-specific workflow logic. All analytical intelligence lives in the orchestrator skills.

### 2. Graceful Degradation
Every skill works independently. Skills that benefit from prior context (writer, remediation, learner) perform lightweight self-investigation when invoked standalone. Quality is reduced but functionality is preserved.

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
