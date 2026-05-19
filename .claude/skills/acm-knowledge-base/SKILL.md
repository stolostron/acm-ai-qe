---
name: acm-knowledge-base
description: >-
  Use when you need READ-ONLY ACM Console domain reference: per-area architecture,
  Polarion conventions, naming patterns, examples. Load the specific references/ file for
  the task. This skill does NOT gather JIRA, PRs, or UI via MCP and does NOT run the
  test-case pipeline. TRIGGER: conventions, field order, area architecture, template
  rules while executing another skill. DO NOT TRIGGER: user asks to generate a test case
  from ACM-#### (acm-test-case-generator); PR-only analysis (acm-qe-code-analyzer).
compatibility: "No MCP servers required. Self-contained reference files."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Knowledge Base

Provides curated domain knowledge for ACM Console areas. This skill contains architecture reference files, test case conventions, and example artifacts that other skills consume.

## How to Use

Read the relevant reference file for your task:

### Area Architecture (factual, authoritative)

Each file describes an ACM Console area: key components, CRDs, navigation routes, translation keys, description list field orders, filtering behavior, setup prerequisites, and testing considerations.

All area files live in the unified knowledge database at `${CLAUDE_SKILL_DIR}/../../knowledge/ui/`:

```
../../knowledge/ui/governance.md    -- Policy types, discovered vs managed, label filtering, field orders
../../knowledge/ui/rbac.md          -- FG-RBAC, MCRA, ClusterPermission, scope types
../../knowledge/ui/fleet-virt.md    -- Fleet Virtualization tree view, VM actions, saved searches
../../knowledge/ui/cclm.md          -- Cross-cluster live migration wizard, kubevirt-plugin
../../knowledge/ui/mtv.md           -- Migration toolkit for virtualization, fleet migration status
../../knowledge/ui/clusters.md      -- Cluster lifecycle, cluster sets, import, cluster pools
../../knowledge/ui/search.md        -- Search API, managed hub clusters, resource queries
../../knowledge/ui/applications.md  -- ALC, subscriptions, channels, Argo
../../knowledge/ui/credentials.md   -- Provider credentials, credential forms
```

These files are **authoritative constraints**. If your analysis of source code or PR diffs contradicts an architecture file on field order, filtering behavior, or component structure, flag the contradiction and verify via source code before overriding.

### Test Case Conventions

Convention files live in the unified knowledge database at `${CLAUDE_SKILL_DIR}/../../knowledge/conventions/`:

```
../../knowledge/conventions/test-case-format.md       -- Section order, naming, complexity levels (from 85+ existing test cases)
../../knowledge/conventions/polarion-html-templates.md -- HTML generation rules for Polarion import
../../knowledge/conventions/area-naming-patterns.md    -- Title tag patterns and Polarion component mapping by area
../../knowledge/conventions/cli-in-steps-rules.md      -- When CLI is allowed in test steps
```

### Examples

```
../../knowledge/examples/sample-test-case.md  -- Convention-compliant sample test case (format reference)
```

## Rules

- Architecture files are **read-only** -- never modify programmatically
- Architecture files represent **verified behavior** -- trust them over unverified analysis
- When architecture files are insufficient, supplement with MCP verification (acm-source, neo4j) and note the gap
- Conventions files are **authoritative format rules** -- test case output must comply
