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
├── learned/               # Shared: agent-contributed discoveries
│   ├── corrections.yaml
│   ├── feature-gaps.yaml
│   ├── new-patterns.yaml
│   ├── selector-changes.yaml
│   └── flux-operator.md
│
└── refresh.py             # Refresh YAML baselines from live cluster
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

All skills resolve `KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/` and then access specific subdirectories.

**TC-Gen** reads: `architecture/`, `ui/`, `conventions/`, `examples/`, `data-flow/`
**Hub-Health** reads: `architecture/`, `data-flow/`, `baselines/`, `diagnostics/`, `health/`, `learned/`
**Z-Stream** reads: `architecture/`, `data-flow/`, `baselines/`, `diagnostics/`, `failures/`, `learned/`

## Updating Baselines

Run `python refresh.py` from a cluster with `oc` access to refresh YAML baselines from live state.

## Contributing Discoveries

All apps write agent-discovered knowledge to `learned/`. See individual YAML files for schema.
