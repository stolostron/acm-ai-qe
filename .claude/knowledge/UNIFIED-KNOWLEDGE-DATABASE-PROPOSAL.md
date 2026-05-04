# Unified Knowledge Database Proposal

**Date:** 2026-05-03
**Current state:** 3 separate knowledge databases (14 + 61 + 63 = 138 total files)
**Goal:** Single unified database that all current and future apps/skills can use

---

## Current Databases

| Database | Location | Files | Used By |
|----------|----------|-------|---------|
| `test-case-generator/` | `.claude/knowledge/test-case-generator/` | 14 | TC-gen skill (conventions, area architecture for UI, examples) |
| `hub-health/` | `.claude/knowledge/hub-health/` | 61 | Hub-health skill (diagnostics, baselines, architecture for health assessment) |
| `z-stream-analysis/` | `.claude/knowledge/z-stream-analysis/` | 63 | Z-stream skill (diagnostics, baselines, architecture for failure classification) |

---

## Overlap Analysis

### Architecture Files (the biggest overlap area)

All three databases have `architecture/` subdirectories about ACM subsystems. But the CONTENT is different:

| Subsystem | TC-Gen Has | Hub-Health Has | Z-Stream Has |
|-----------|-----------|---------------|-------------|
| governance | `governance.md` (UI: field orders, filtering, translation keys, routes) | `governance/architecture.md` + `data-flow.md` + `known-issues.md` (health: controllers, pods, reconciliation) | `governance/architecture.md` + `data-flow.md` + `failure-signatures.md` (failures: error patterns, classification hints) |
| search | `search.md` (UI: search API, routes, components) | `search/architecture.md` + `data-flow.md` + `known-issues.md` (health: postgres, indexer, collector) | `search/architecture.md` + `data-flow.md` + `failure-signatures.md` (failures: empty results, timeout patterns) |
| rbac | `rbac.md` (UI: MCRA, ClusterPermission, scopes) | `rbac/architecture.md` + `data-flow.md` + `known-issues.md` | `rbac/architecture.md` + `data-flow.md` + `failure-signatures.md` |
| clusters | `clusters.md` (UI: lifecycle, sets, import, pools) | `cluster-lifecycle/architecture.md` + `data-flow.md` + `known-issues.md` + `health-patterns.md` | `cluster-lifecycle/architecture.md` + `data-flow.md` + `failure-signatures.md` |
| virtualization | `fleet-virt.md` (UI: tree view, VM actions) | `virtualization/...` (health) | `virtualization/...` (failures) |
| applications | `applications.md` (UI: ALC, subscriptions) | `application-lifecycle/...` (health) | `application-lifecycle/...` (failures) |

**Key insight:** Each app looks at the SAME subsystem from a DIFFERENT angle:
- **TC-Gen** needs: UI components, routes, translation keys, field orders, filtering behavior
- **Hub-Health** needs: pod topology, health baselines, known-issues, reconciliation patterns
- **Z-Stream** needs: failure signatures, error patterns, classification hints, test dependencies

These are NOT the same files with different names. They're fundamentally different information about the same subsystems.

### Diagnostics (shared methodology, different application)

| File | Hub-Health | Z-Stream | Identical? |
|------|-----------|----------|-----------|
| `diagnostic-layers.md` | 12-layer model for health diagnosis | Same 12-layer model adapted for failure classification | ~80% similar, different framing |
| `diagnostic-traps.md` / `common-diagnostic-traps.md` | 14 traps for health diagnosis | Same 14 traps + classification context | ~70% similar |
| `evidence-tiers.md` | Tier 1/2/3 for health conclusions | Same tiers for classification confidence | ~90% similar |
| `dependency-chains.md` | Chains for health correlation | Same chains (via `dependencies.yaml`) | ~85% similar |

**Key insight:** The diagnostic METHODOLOGY is shared. But the APPLICATION differs. Hub-health says "if Layer 3 is broken, the cluster is DEGRADED." Z-stream says "if Layer 3 is broken, tests in affected areas are INFRASTRUCTURE."

### YAML Baselines (structurally similar, shared content)

| YAML File | Hub-Health | Z-Stream | Overlap |
|-----------|-----------|----------|---------|
| `healthy-baseline.yaml` | Expected pod counts, phases, image prefixes | Same structure, same purpose | ~95% identical |
| `addon-catalog.yaml` | Addon health expectations, dependencies | Same | ~95% identical |
| `service-map.yaml` | Service-to-pod mapping, consumers | Same | ~95% identical |
| `version-constraints.yaml` | Version incompatibility matrix | Same | ~95% identical |
| `webhook-registry.yaml` | Expected webhooks, failure policies | Same | ~95% identical |
| `certificate-inventory.yaml` | TLS secrets, rotation | Same | ~95% identical |
| `dependency-chains.yaml` / `dependencies.yaml` | Dependency chains | Same structure | ~90% similar |
| `component-registry.md` / `components.yaml` | Component inventory | Same content, different format (md vs yaml) | ~85% similar |

**Key insight:** The YAML baselines are almost identical between hub-health and z-stream. They describe the same cluster state. Only `failure-patterns.yaml` (z-stream) and `failure-patterns.md` (hub-health) differ significantly. TC-gen doesn't use these at all.

### TC-Gen Unique Content (no overlap)

| Content | Only in TC-Gen | Why |
|---------|---------------|-----|
| `conventions/test-case-format.md` | Polarion test case format rules | Only TC-gen writes test cases |
| `conventions/polarion-html-templates.md` | Polarion HTML import format | Only TC-gen generates HTML |
| `conventions/area-naming-patterns.md` | Title tag patterns by area | Only TC-gen names test cases |
| `conventions/cli-in-steps-rules.md` | When CLI allowed in test steps | Only TC-gen writes test steps |
| `examples/sample-test-case.md` | Convention-compliant example | Only TC-gen needs format examples |

---

## Proposed Unified Structure

```
.claude/knowledge/
├── README.md                           # Master index, usage rules

├── architecture/                       # SHARED: subsystem architecture (what each component IS)
│   ├── acm-platform.md                 # MCH/MCE hierarchy, foundation
│   ├── kubernetes-fundamentals.md      # K8s basics for ACM context
│   ├── governance/
│   │   └── architecture.md             # Controllers, CRDs, reconciliation, component list
│   ├── search/
│   │   └── architecture.md             # search-v2 topology, postgres, indexer, collector
│   ├── cluster-lifecycle/
│   │   └── architecture.md             # Hive, assisted-service, cluster provisioning
│   ├── ... (12 subsystems total)

├── data-flow/                          # SHARED: how data moves through each subsystem
│   ├── governance/data-flow.md
│   ├── search/data-flow.md
│   ├── cluster-lifecycle/data-flow.md
│   ├── ...

├── baselines/                          # SHARED: YAML baselines (cluster state reference)
│   ├── healthy-baseline.yaml           # Expected pod counts, phases, images
│   ├── addon-catalog.yaml              # Addon health expectations
│   ├── service-map.yaml                # Service-to-pod mapping
│   ├── version-constraints.yaml        # Version incompatibility
│   ├── webhook-registry.yaml           # Expected webhooks
│   ├── certificate-inventory.yaml      # TLS secrets
│   ├── dependency-chains.yaml          # Component dependency chains
│   ├── components.yaml                 # Component registry (YAML version)
│   └── component-registry.md           # Component registry (narrative version)

├── diagnostics/                        # SHARED: investigation methodology
│   ├── diagnostic-layers.md            # 12-layer model (shared methodology)
│   ├── diagnostic-traps.md             # 14 trap patterns (shared)
│   ├── evidence-tiers.md               # Tier 1/2/3 evidence framework (shared)
│   ├── dependency-chains.md            # How to trace chains (methodology)
│   ├── diagnostic-playbooks.md         # Investigation procedures
│   ├── cluster-introspection.md        # 8-source reverse engineering
│   ├── acm-search-reference.md         # ACM Search MCP usage patterns
│   └── neo4j-reference.md              # Neo4j Knowledge Graph patterns

├── ui/                                 # TC-GEN SPECIFIC: console UI knowledge
│   ├── governance.md                   # UI: field orders, filtering, translations, routes
│   ├── rbac.md                         # UI: MCRA, ClusterPermission, scopes
│   ├── fleet-virt.md                   # UI: tree view, VM actions
│   ├── clusters.md                     # UI: lifecycle, sets, import
│   ├── search.md                       # UI: search API, routes
│   ├── applications.md                 # UI: ALC, subscriptions
│   ├── credentials.md                  # UI: provider credentials
│   ├── cclm.md                         # UI: cross-cluster migration
│   └── mtv.md                          # UI: migration toolkit

├── health/                             # HUB-HEALTH SPECIFIC: health assessment knowledge
│   ├── governance/known-issues.md      # Known health issues per subsystem
│   ├── search/known-issues.md
│   ├── cluster-lifecycle/known-issues.md
│   ├── cluster-lifecycle/health-patterns.md
│   ├── infrastructure/post-upgrade-patterns.md
│   ├── ... (per subsystem)
│   └── failure-patterns.md             # Health failure pattern heuristics

├── failures/                           # Z-STREAM SPECIFIC: failure classification knowledge
│   ├── governance/failure-signatures.md
│   ├── search/failure-signatures.md
│   ├── cluster-lifecycle/failure-signatures.md
│   ├── foundation/failure-signatures.md
│   ├── foundation/test-dependencies.md
│   ├── install/failure-signatures.md
│   ├── install/test-dependencies.md
│   ├── ... (per subsystem)
│   ├── failure-patterns.yaml           # Structured failure patterns for matching
│   ├── selectors.yaml                  # Selector registry for automation
│   ├── feature-areas.yaml              # Feature area mapping
│   ├── test-mapping.yaml               # Test-to-feature mapping
│   ├── api-endpoints.yaml              # API endpoint registry
│   ├── prerequisites.yaml              # Feature prerequisites
│   └── classification-decision-tree.md # Classification routing logic
│   └── common-misclassifications.md    # Gotchas for classification

├── conventions/                        # TC-GEN SPECIFIC: test case format rules
│   ├── test-case-format.md
│   ├── polarion-html-templates.md
│   ├── area-naming-patterns.md
│   └── cli-in-steps-rules.md

├── examples/                           # TC-GEN SPECIFIC: format examples
│   └── sample-test-case.md

├── learned/                            # SHARED: agent-contributed discoveries (all apps write here)
│   ├── corrections.yaml                # Z-stream classification corrections
│   ├── feature-gaps.yaml               # Z-stream playbook gaps
│   ├── new-patterns.yaml               # Z-stream new failure patterns
│   ├── selector-changes.yaml           # Z-stream selector timeline
│   ├── flux-operator.md                # Operator discovery (any app)
│   └── .gitkeep

└── refresh.py                          # Script to refresh YAML baselines from live cluster
```

---

## Why This Works for All Apps

### TC-Gen reads:
- `architecture/<area>/architecture.md` -- component knowledge (WHAT the subsystem is)
- `ui/<area>.md` -- UI-specific knowledge (field orders, translations, routes)
- `conventions/*.md` -- test case format rules
- `examples/` -- format reference
- `data-flow/<area>/data-flow.md` -- how data flows (for understanding backend behavior)
- `diagnostics/` -- NOT used by TC-gen currently, but could be used in Phase 6 live validation

### Hub-Health reads:
- `architecture/<area>/architecture.md` -- component knowledge
- `data-flow/<area>/data-flow.md` -- data flow for tracing
- `baselines/*.yaml` -- healthy state reference
- `diagnostics/*.md` -- methodology (12 layers, traps, evidence, playbooks)
- `health/<area>/known-issues.md` -- known health issues
- `health/<area>/health-patterns.md` -- settling patterns, upgrade behavior

### Z-Stream reads:
- `architecture/<area>/architecture.md` -- component knowledge
- `data-flow/<area>/data-flow.md` -- data flow for root cause tracing
- `baselines/*.yaml` -- healthy state reference (same as hub-health)
- `diagnostics/*.md` -- methodology (same 12 layers, traps, evidence)
- `failures/<area>/failure-signatures.md` -- failure patterns for classification
- `failures/*.yaml` -- structured failure patterns, selectors, test mappings

### Future apps read:
- `architecture/` -- always useful for any ACM-related work
- `baselines/` -- always useful for anything comparing against expected state
- `diagnostics/` -- reusable methodology for any investigation task
- Add a new app-specific subdirectory (e.g., `performance/`, `security/`) for their unique knowledge

---

## Migration Path

### What merges cleanly (no conflicts):
- `baselines/` -- hub-health and z-stream YAML files are ~95% identical. Use z-stream's (newer) as the base.
- `architecture/` -- both have `architecture.md` per subsystem. Content is similar. Merge into one authoritative file per subsystem.
- `data-flow/` -- both have `data-flow.md`. Very similar. Merge.
- `diagnostics/` -- nearly identical methodology. Z-stream has 2 extra files (`classification-decision-tree.md`, `common-misclassifications.md`). Keep all.
- `conventions/` and `examples/` -- TC-gen only, no conflict.
- `learned/` -- z-stream already has content, hub-health has only .gitkeep. Merge.

### What stays app-specific (different content, same subsystem):
- `ui/` -- TC-gen's view of each subsystem (field orders, translations) -- unique to test case writing
- `health/` -- hub-health's view (known-issues, health patterns) -- unique to health diagnosis
- `failures/` -- z-stream's view (failure signatures, classification hints) -- unique to failure analysis

### What needs human review:
- `architecture/<subsystem>/architecture.md` -- hub-health and z-stream versions differ slightly. Need to merge into one authoritative version that serves both.
- `component-registry.md` vs `components.yaml` -- same data, different format. Keep both (narrative for humans, YAML for programmatic access).
- `failure-patterns.md` (hub-health) vs `failure-patterns.yaml` (z-stream) -- different format AND different content. Keep both in their respective sections.

---

## How Skills Would Reference the Unified Database

Update all `KNOWLEDGE_DIR` references to point to the single root:

```
KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/
```

Then each phase reads specific paths within:
- TC-gen Phase 7: `${KNOWLEDGE_DIR}/conventions/test-case-format.md`, `${KNOWLEDGE_DIR}/ui/<area>.md`
- Hub-health Phase 2: `${KNOWLEDGE_DIR}/architecture/<subsystem>/architecture.md`, `${KNOWLEDGE_DIR}/baselines/healthy-baseline.yaml`
- Z-stream Stage 1.5: `${KNOWLEDGE_DIR}/baselines/healthy-baseline.yaml`, `${KNOWLEDGE_DIR}/diagnostics/diagnostic-traps.md`

Each app reads from the SAME database but accesses DIFFERENT subdirectories based on its needs.

---

## Benefits

1. **Single source of truth** for shared knowledge (architecture, baselines, diagnostics)
2. **No duplication** of YAML baselines between hub-health and z-stream
3. **Consistent architecture docs** -- one version per subsystem, not 2-3 drifting copies
4. **Future apps** just add their app-specific subdirectory (e.g., `security/`) and use shared sections
5. **One `refresh.py`** updates baselines for all apps simultaneously
6. **One `learned/`** directory where all apps contribute discoveries
7. **Clearer ownership** -- shared files are everyone's responsibility, app-specific files belong to that app

---

## File Count Comparison

| Approach | Total Files | Duplication |
|----------|-------------|-------------|
| Current (3 separate) | 138 | ~40 files are duplicated between hub-health and z-stream |
| Unified | ~100 | Zero duplication |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Changing shared architecture file breaks one app | Tests in each app verify their expected content is present (existing regression tests) |
| One app's `refresh.py` overwrites another's data | Single `refresh.py` at the root; no app-specific refresh scripts |
| `learned/` gets cluttered with mixed app contributions | Prefix learned files with app context: `zs-corrections.yaml`, `hh-new-chains.yaml` |
| App needs a field in architecture that another doesn't care about | Include ALL fields -- extra information doesn't hurt, missing information does |
