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

```
references/architecture/governance.md    -- Policy types, discovered vs managed, label filtering, field orders
references/architecture/rbac.md          -- FG-RBAC, MCRA, ClusterPermission, scope types
references/architecture/fleet-virt.md    -- Fleet Virtualization tree view, VM actions, saved searches
references/architecture/cclm.md          -- Cross-cluster live migration wizard, kubevirt-plugin
references/architecture/mtv.md           -- Migration toolkit for virtualization, fleet migration status
references/architecture/clusters.md      -- Cluster lifecycle, cluster sets, import, cluster pools
references/architecture/search.md        -- Search API, managed hub clusters, resource queries
references/architecture/applications.md  -- ALC, subscriptions, channels, Argo
references/architecture/credentials.md   -- Provider credentials, credential forms
```

These files are **authoritative constraints**. If your analysis of source code or PR diffs contradicts an architecture file on field order, filtering behavior, or component structure, flag the contradiction and verify via source code before overriding.

### Test Case Conventions

```
references/conventions/test-case-format.md       -- Section order, naming, complexity levels (from 85+ existing test cases)
references/conventions/polarion-html-templates.md -- HTML generation rules for Polarion import
references/conventions/area-naming-patterns.md    -- Title tag patterns and Polarion component mapping by area
references/conventions/cli-in-steps-rules.md      -- When CLI is allowed in test steps
```

### Examples

```
references/examples/sample-test-case.md  -- Convention-compliant sample test case (format reference)
```

## Rules

- Architecture files are **read-only** -- never modify programmatically
- Architecture files represent **verified behavior** -- trust them over unverified analysis
- When architecture files are insufficient, supplement with MCP verification (acm-source, neo4j) and note the gap
- Conventions files are **authoritative format rules** -- test case output must comply
