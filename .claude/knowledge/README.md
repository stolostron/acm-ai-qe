# ACM Knowledge Database

Unified knowledge database for all ACM quality engineering tools. Shared reference for architecture, diagnostics, and baselines; app-specific sections for domain-specific content.

## Structure

```
knowledge/
├── architecture/          # Shared: subsystem architecture (14 subsystems)
│   ├── acm-platform.md
│   ├── kubernetes-fundamentals.md
│   └── <subsystem>/architecture.md
│
├── data-flow/             # Shared: how data moves through each subsystem
│   └── <subsystem>/data-flow.md
│
├── baselines/             # Shared: YAML baselines (expected cluster state)
│   ├── healthy-baseline.yaml
│   ├── addon-catalog.yaml
│   ├── service-map.yaml
│   ├── version-constraints.yaml
│   ├── webhook-registry.yaml
│   ├── certificate-inventory.yaml
│   ├── dependency-chains.yaml
│   ├── components.yaml
│   └── component-registry.md
│
├── diagnostics/           # Shared: investigation methodology
│   ├── diagnostic-layers.md       # 12-layer model
│   ├── diagnostic-traps.md        # 14 trap patterns
│   ├── evidence-tiers.md          # Tier 1/2/3 evidence framework
│   ├── dependency-chains.md       # Chain tracing methodology
│   ├── diagnostic-playbooks.md    # Investigation procedures
│   ├── cluster-introspection.md   # 8-source reverse engineering
│   ├── acm-search-reference.md    # ACM Search MCP patterns
│   └── neo4j-reference.md         # Neo4j Knowledge Graph patterns
│
├── ui/                    # TC-Gen specific: console UI knowledge
│   └── <area>.md          # Field orders, translations, routes, components
│
├── health/                # Hub-Health specific: health assessment
│   ├── failure-patterns.md
│   └── <subsystem>/known-issues.md (+ health-patterns.md, post-upgrade-patterns.md)
│
├── failures/              # Z-Stream specific: failure classification
│   ├── <subsystem>/failure-signatures.md (+ test-dependencies.md, post-upgrade-patterns.md)
│   ├── failure-patterns.yaml
│   ├── selectors.yaml
│   ├── feature-areas.yaml
│   ├── test-mapping.yaml
│   ├── api-endpoints.yaml
│   ├── prerequisites.yaml
│   ├── classification-decision-tree.md
│   └── common-misclassifications.md
│
├── conventions/           # TC-Gen specific: test case format rules
├── examples/              # TC-Gen specific: format examples
│
├── automation/            # Cursor skills: test automation knowledge
│   ├── playwright/        # Playwright E2E (console-e2e) area knowledge
│   │   ├── app.md, clusters.md, rbac.md, fleet-virt.md, ...
│   └── cypress/           # Cypress E2E (clc-ui-e2e) area knowledge
│       ├── clusters.md, rbac.md, fleet-virt.md, ...
│
├── versions/              # Shared: version compatibility and migration docs
│   ├── version-matrix.md          # ACM/MCE/OCP/CNV/MTV version mappings
│   └── acm-2x-to-5x-changes.md   # Breaking changes from ACM 2.x to 5.0
│
└── learned/               # DEPRECATED -- all agents write directly to target files
    └── .gitkeep
```

## Subsystems (14)

| Subsystem | Architecture | Data Flow | Health | Failures |
|-----------|:---:|:---:|:---:|:---:|
| addon-framework | x | x | x | |
| application-lifecycle | x | x | x | x |
| automation | x | x | x | x |
| cluster-lifecycle | x | x | x | x |
| console | x | x | x | x |
| foundation | x | | | x |
| governance | x | x | x | x |
| infrastructure | x | x | x | x |
| install | x | | | x |
| networking | x | x | x | |
| observability | x | x | x | x |
| rbac | x | x | x | x |
| search | x | x | x | x |
| virtualization | x | x | x | x |

## How Each App Uses This Database

All Claude Code skills resolve `KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/` and then access specific subdirectories.

**TC-Gen** reads: `architecture/`, `ui/`, `conventions/`, `examples/`, `data-flow/`
**Hub-Health** reads: `architecture/`, `data-flow/`, `baselines/`, `diagnostics/`, `health/`
**Z-Stream** reads: `architecture/`, `data-flow/`, `baselines/`, `diagnostics/`, `failures/`
**Cursor Playwright skill** reads: `automation/playwright/`, `ui/`, `architecture/`
**Cursor Cypress skill** reads: `automation/cypress/`, `ui/`, `architecture/`

Cursor skills reference this DB via absolute path: `<repo-root>/.claude/knowledge/automation/{framework}/{area}.md`

## Local Mirror (per-user, not in repo)

Individual users may maintain a read-only mirror of this knowledge DB elsewhere on their machine (e.g., a notes workspace). This is optional and configured per-user via local hooks or sync scripts -- not part of this repo.

Agents always write to this canonical location (`<repo-root>/.claude/knowledge/`). Any mirror is read-only and auto-synced by user-local tooling.

## Contributing Knowledge

ALL agents (Cursor, Claude Code, z-stream, hub-health) write directly to the appropriate target file. No staging area, no intermediate format. Read the target file first, check for duplicates, append in the correct format.

The `learned/` directory is deprecated and empty. Do not write to it.
