# Knowledge Database Reference

The knowledge database (`knowledge/`) provides domain reference data that the AI agent reads at the start of Stage 2 analysis. It complements the feature playbooks (`src/data/feature_playbooks/`) consumed programmatically during Stage 1.

---

## Architecture

```
                    ┌─────────────────────────────────┐
                    │         AI Agent (Stage 2)       │
                    │                                  │
                    │  1. Read knowledge/*.yaml        │
                    │  2. Match failure-patterns.yaml  │
                    │  3. Trace dependencies.yaml      │
                    │  4. Check components.yaml health │
                    │  5. Classify with evidence       │
                    │                                  │
                    └────────────┬──────────────────────┘
                                │ reads at start
                    ┌───────────▼───────────┐
                    │   knowledge/          │
                    │                       │
                    │   Static Reference    │      ┌─────────────────────┐
                    │   ────────────────    │      │   learned/          │
                    │   components.yaml     │      │                     │
                    │   dependencies.yaml   │◄─────│   corrections.yaml  │
                    │   failure-patterns.yaml│      │   new-patterns.yaml │
                    │   selectors.yaml      │      │   selector-changes  │
                    │   api-endpoints.yaml  │      │                     │
                    │   feature-areas.yaml  │      │   (agent writes,    │
                    │   test-mapping.yaml   │      │    refresh.py       │
                    │                       │      │    promotes)         │
                    └───────────┬───────────┘      └─────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │   refresh.py          │
                    │                       │
                    │   Sources:            │
                    │   - oc get (cluster)  │
                    │   - ACM-UI MCP        │
                    │   - Neo4j KG          │
                    │   - learned/ entries  │
                    └───────────────────────┘
```

### Data Flow

```
  Stage 1 (gather.py)               Stage 2 (AI Agent)              Between Runs
  ───────────────────               ──────────────────              ──────────────
                                                                         │
  feature_playbooks/                knowledge/*.yaml ◄─── reads ──┐     │
  (programmatic)                    (reference)          at start  │     │
       │                                 │                         │     │
       ▼                                 ▼                         │     │
  core-data.json ───────────► classification decisions             │     │
  (cluster_oracle,                       │                         │     │
   feature_knowledge,                    ▼                         │     │
   feature_grounding)            analysis-results.json             │     │
                                         │                         │     │
                                         ▼                         │     │
                                  learned/*.yaml ─────────────────►│     │
                                  (agent writes new               │     │
                                   patterns/corrections)           │     │
                                                                   │     │
                                                            refresh.py ──┘
                                                            (promotes learned/
                                                             to main files)
```

---

## File Reference

| File | Records | Purpose | Refresh Source |
|------|---------|---------|----------------|
| `components.yaml` | 30+ components | Component registry with health checks | `oc get` via refresh.py |
| `dependencies.yaml` | 8 chains | Cascade failure tracing | Neo4j KG + manual |
| `failure-patterns.yaml` | 15+ patterns | Short-circuit classification | Manual + learned/ promotion |
| `selectors.yaml` | 50+ selectors | UI selector ground truth | ACM-UI MCP |
| `api-endpoints.yaml` | 5 endpoints | Backend probe reference | ACM-UI MCP code search |
| `feature-areas.yaml` | 11 areas | Test-to-feature mapping | Manual + code sync |
| `test-mapping.yaml` | 10+ suites | Suite-to-area mapping | Manual |
| `learned/` | 3 files | Agent-contributed knowledge | AI agent writes |
| `refresh.py` | — | Updates knowledge from live sources | — |

---

## components.yaml

Registry of ACM components with health check commands, dependency chains, and operational context. The AI agent uses this to:
- Understand which pods serve which features
- Know what health checks to run (via `health_check` commands)
- Trace upstream dependencies when a component fails

### Structure

```yaml
acm_version: "2.17"
last_refreshed: "2026-03-27"

components:
  search-api:
    subsystem: Search
    type: hub-deployment
    namespace: open-cluster-management
    pod_label: "app=search-api"
    health_check: "oc get deploy search-api -n {ns} -o jsonpath='{.status.readyReplicas}'"
    depends_on: [search-postgres, search-indexer]
    critical_for: [search-page, vm-search, resource-lookup]
    tls_secret: search-api-certs
    notes: "Serves GraphQL queries from console. If down, all search UI breaks."
```

### Fields

| Field | Type | Purpose |
|-------|------|---------|
| `subsystem` | string | Logical grouping (Search, Governance, Cluster-Lifecycle, etc.) |
| `type` | string | `hub-deployment`, `addon`, `operator`, `spoke-agent` |
| `namespace` | string | Kubernetes namespace where the component runs |
| `pod_label` | string | Label selector for `oc get pods -l` |
| `health_check` | string | Command template (`{ns}` = actual namespace) |
| `depends_on` | list | Upstream components this depends on |
| `critical_for` | list | Features/pages that break if this component fails |
| `tls_secret` | string | TLS secret name (for certificate-related failures) |
| `notes` | string | Operational context for the AI agent |

### Subsystems Covered

| Subsystem | Components | Key Chain |
|-----------|-----------|-----------|
| Search | search-api, search-postgres, search-indexer, search-collector, search-v2-operator | collector → indexer → postgres → api → console |
| Governance | grc-policy-propagator, governance-policy-framework, config-policy-controller | policy → propagator → framework → controller |
| Cluster-Lifecycle | hive-controllers, managedcluster-import-controller, klusterlet, registration-agent | hive → import → klusterlet → registration |
| Console | console-chart (console-api) | OAuth → console-api → ConsolePlugin CRs |
| Observability | observability-operator, metrics-collector, thanos-receive, thanos-store, thanos-query | collector → receive → S3 → store → query → grafana |
| Application-Lifecycle | application-manager, application-chart, subscription-controller | subscription → channel → app-manager |
| Infrastructure | cert-manager, service-ca-operator | cert-manager → service-ca → TLS certs |

### How the Agent Uses It

During Phase B investigation, when a test fails with a timeout or 500 error, the agent:

1. Identifies the feature area (e.g., Search)
2. Looks up components in that subsystem from `components.yaml`
3. Checks `depends_on` chains to find the root cause
4. Uses `notes` to understand operational implications

Example investigation flow for a Search test failure:
```
Test: "search should return managed clusters"
Error: "Timed out waiting for search results"

Agent reads components.yaml:
  → search-api depends on [search-postgres, search-indexer]
  → search-indexer depends on [search-postgres]
  → search-postgres uses emptyDir (index rebuilt after restart)

Agent checks cluster_oracle from core-data.json:
  → search-postgres: 0/1 ready replicas
  → Root cause: search-postgres down → all search queries fail

Classification: INFRASTRUCTURE (0.95 confidence)
Evidence: component health check shows 0 ready replicas
```

---

## dependencies.yaml

Dependency chains with cascade failure descriptions and classification hints. Enables the AI agent to trace from a symptom back to the root cause.

### Structure

```yaml
dependency_chains:
  search:
    chain: "search-collector (spoke) -> search-indexer -> search-postgres -> search-api -> console UI"
    if_postgres_down: "All search queries fail. VM discovery fails. No error in UI -- just empty results."
    if_collector_missing: "Resources from that spoke silently absent from search."
    if_indexer_restarting: "Index rebuild in progress -- temporarily stale results."
    classification_hint:
      postgres_down: INFRASTRUCTURE
      collector_missing: INFRASTRUCTURE
      indexer_stale: PRODUCT_BUG
```

### Chains Defined

| Chain | Components | Common Failure Mode |
|-------|-----------|---------------------|
| `search` | collector → indexer → postgres → api → UI | postgres down = empty results |
| `governance` | policy → propagator → framework → controller → status-sync | propagator down = no policy distribution |
| `cluster_lifecycle` | hive → import-controller → klusterlet → registration | klusterlet disconnect = all spoke features fail |
| `console` | OAuth → console-api → ConsolePlugin → feature UIs | console-api down = all 500 errors |
| `observability` | MCO → collector → thanos-receive → S3 → store → query → grafana | S3 misconfigured = most common obs failure |
| `application` | subscription → channel → app-manager → placement | subscription-controller CRD issue = cascade |
| `virtualization` | CNV operator → HyperConverged → virt-controller → virt-handler → VMs | CNV not installed = all VM tests INFRA |
| `addon` | klusterlet → work-manager → ManagedClusterAddon → addon pods | klusterlet disconnect = all addons fail |

### Classification Hints

The `classification_hint` map provides deterministic routing. When the agent identifies a broken component, it uses the hint:

```
if_postgres_down      → INFRASTRUCTURE  (database layer, not product code)
if_indexer_stale      → PRODUCT_BUG     (indexer should handle restarts gracefully)
if_collector_missing  → INFRASTRUCTURE  (addon not deployed on spoke)
```

---

## failure-patterns.yaml

Known failure signatures that enable short-circuit classification. When a test error matches a pattern, the AI agent can classify with high confidence without full investigation.

### Structure

```yaml
patterns:
  - id: carbon-selector
    category: selector
    signature: "tf--list-box|tf--dropdown|tf--combo-box|tf--text-input"
    classification: AUTOMATION_BUG
    confidence: 0.95
    explanation: "Carbon Design System selector. Console migrated to PatternFly in 2023."
    fix: "Replace with PatternFly equivalent (pf-v6-c-menu, pf-v6-c-select, etc.)"
```

### Pattern Categories

| Category | Patterns | Typical Classification |
|----------|---------|----------------------|
| `selector` | carbon-selector, pf5-selector-deprecated, pf6-portal-visibility, data-ouia-deprecated | AUTOMATION_BUG |
| `infrastructure` | vm-scheduling-no-kvm, certificate-expired, oauth-redirect-loop, etcd-leader-timeout | INFRASTRUCTURE |
| `product` | api-500-error, graphql-null-response, empty-list-with-resources | PRODUCT_BUG |
| `flaky` | cypress-detached-dom, element-animation-race | FLAKY |

### How Pattern Matching Works

```
Test error: "expected '[data-ouia-component-id=create-cluster]' to exist"

AI agent reads failure-patterns.yaml:
  → Matches pattern "data-ouia-deprecated" (signature: "data-ouia-component-id.*not found")
  → Classification: AUTOMATION_BUG
  → Confidence: 0.80
  → Explanation: "OUIA selectors may have changed in PF6 migration"

Agent proceeds with standard investigation but starts with
AUTOMATION_BUG hypothesis at 0.80 confidence.
```

Pattern matching does NOT short-circuit the investigation. It sets an initial hypothesis. The full 5-phase investigation can override it with stronger evidence.

---

## selectors.yaml

Ground truth for UI selectors by feature area. Used to verify whether a selector referenced in a failing test actually exists in the product code.

### Structure

```yaml
acm_version: "2.17"
last_refreshed: "2026-03-27"

selectors:
  Search:
    search-input: "[data-test-id='search-input']"
    search-results-table: ".pf-v6-c-table"
    search-filter-dropdown: "[data-test-id='filter-dropdown']"
    saved-searches-menu: "[data-test-id='saved-searches']"

  GRC:
    create-policy-button: "[data-test-id='create-policy']"
    policy-table: ".pf-v6-c-table"
    policy-status-badge: ".pf-v6-c-label"
```

### Usage

When a test fails because an element is not found, the agent checks:
1. Is the selector in `selectors.yaml`? (ground truth)
2. Does `extracted_context.console_search.found` confirm it exists in product code?
3. If selector is in ground truth but `found=false`, it was likely recently removed → AUTOMATION_BUG

---

## api-endpoints.yaml

Backend API endpoints probed during Stage 1 (gather.py Step 4c). Provides the AI agent with context about what each probe validates and what anomalies mean.

### Structure

```yaml
endpoints:
  - path: /authenticated
    method: GET
    component: console-api
    feature_areas: [all]
    expected: "200 with JSON body, response time < 5s"
    validates: "Console backend is reachable and auth works"
    anomalies:
      slow_response: "Response time > 5s indicates backend under load"

  - path: /hub
    method: GET
    component: console-api
    feature_areas: [CLC, Infrastructure, Observability]
    expected: "200 with JSON body containing hub cluster name"
    validates: "Hub name matches MCH metadata"
    ground_truth: "oc get mch -A -o jsonpath='{.items[0].metadata.name}'"
    anomalies:
      wrong_hub_name: "Hub name in response doesn't match MCH -- data routing issue"
```

### Probes and Feature Areas

| Endpoint | Validates | Feature Areas | Anomaly → Classification |
|----------|-----------|---------------|--------------------------|
| `/authenticated` | Backend reachable, auth works | All | Slow response → INFRASTRUCTURE |
| `/hub` | Hub name matches MCH metadata | CLC, Infrastructure, Observability | Wrong name → PRODUCT_BUG |
| `/username` | Username format correct | RBAC | Reversed format → PRODUCT_BUG |
| `/ansibletower` | AAP integration healthy | Automation | Empty when AAP exists → PRODUCT_BUG |
| `/proxy/search` | Search API returning data | Search | Empty when resources exist → PRODUCT_BUG |

---

## feature-areas.yaml

Maps test patterns to feature areas, subsystems, and components. Lightweight complement to the programmatic `FeatureAreaService` in `src/services/feature_area_service.py`.

### Structure

```yaml
feature_areas:
  Search:
    subsystems: [search]
    test_patterns:
      - "(?i)search"
      - "(?i)saved.*search"
    key_components: [search-api, search-postgres, search-indexer, search-collector]
    mch_component: search
    default_enabled: true
    playbook_ref: "src/data/feature_playbooks/base.yaml#Search"
```

### Defined Areas

| Area | Subsystems | Key Components | MCH Component |
|------|-----------|----------------|---------------|
| Search | search | search-api, search-postgres, search-indexer | search |
| GRC | governance | grc-policy-propagator, governance-policy-framework | grc |
| CLC | cluster-lifecycle | hive-controllers, managedcluster-import-controller | — |
| Observability | observability | observability-operator, thanos-query | observability |
| Virtualization | virtualization | cnv-operator, kubevirt-hyperconverged | — |
| Application | application-lifecycle | application-manager, subscription-controller | — |
| Console | console | console-chart | console |
| Infrastructure | infrastructure | cert-manager, service-ca-operator | — |
| RBAC | iam | — | — |
| Automation | automation | — | — |
| CrossClusterMigration | virtualization | forklift-controller, kubevirt-operator | cnv-mtv-integrations |

---

## test-mapping.yaml

Maps test suites (Cypress spec files / describe blocks) to feature areas, with known issue annotations.

### Structure

```yaml
suites:
  - pattern: "Search/*"
    feature_area: Search
    owner: search-team
    known_issues:
      - jira: ACM-12345
        description: "Saved search filter intermittently empty"
        status: open

  - pattern: "GRC/*"
    feature_area: GRC
    owner: grc-team
```

---

## learned/ Directory

Agent-contributed knowledge accumulated across analysis runs. Three files:

### learned/corrections.yaml

When the feedback CLI (`python -m src.scripts.feedback`) records a misclassification, it's stored here for review:

```yaml
corrections:
  - date: "2026-03-28"
    test_name: "Search should filter by label"
    original_classification: AUTOMATION_BUG
    correct_classification: INFRASTRUCTURE
    reason: "search-postgres was down, not a selector issue"
    pattern_to_add:
      id: search-empty-results-postgres
      signature: "search.*empty.*results"
      classification: INFRASTRUCTURE
```

### learned/new-patterns.yaml

When the agent discovers a failure pattern not in `failure-patterns.yaml`, it writes the pattern here:

```yaml
patterns:
  - date: "2026-03-28"
    id: "applicationset-crd-missing"
    signature: "applicationsets\\.argoproj\\.io.*not found|no matches for kind.*ApplicationSet"
    classification: INFRASTRUCTURE
    confidence: 0.90
    explanation: "ApplicationSet CRD not installed -- operator missing or MCE component disabled"
    evidence: "7 tests failed with same CRD-not-found error"
```

### learned/selector-changes.yaml

When the agent identifies a selector change (old selector removed, new one added):

```yaml
changes:
  - date: "2026-03-28"
    old_selector: ".pf-c-dropdown__toggle"
    new_selector: ".pf-v6-c-menu-toggle"
    feature_area: Console
    component: "All dropdown components"
    acm_version: "2.17"
```

---

## refresh.py

Script that updates knowledge files from live sources. Supports selective refresh and dry-run mode.

### Commands

```bash
# Refresh everything (cluster + learned/ promotion)
python -m knowledge.refresh

# Refresh only components from connected cluster
python -m knowledge.refresh --components

# Show what would change without writing
python -m knowledge.refresh --dry-run

# Promote learned/ entries to main files
python -m knowledge.refresh --promote

# Set ACM version explicitly
python -m knowledge.refresh --acm-version 2.17
```

### What Each Refresh Does

| Flag | Source | Target | Automated? |
|------|--------|--------|------------|
| `--components` | `oc get deployments` across ACM namespaces | `components.yaml` | Fully automated |
| `--selectors` | ACM-UI MCP `get_acm_selectors` | `selectors.yaml` | Prints instructions (requires MCP) |
| `--dependencies` | Neo4j KG transitive queries | `dependencies.yaml` | Prints instructions (requires KG) |
| `--promote` | `learned/*.yaml` entries | `failure-patterns.yaml` | Fully automated |

### Component Refresh Flow

```
refresh.py --components
    │
    ├── oc whoami (verify cluster access)
    ├── oc get mch -A (discover MCH namespace)
    ├── oc get deployments -n open-cluster-management -o json
    ├── oc get deployments -n multicluster-engine -o json
    ├── oc get deployments -n open-cluster-management-hub -o json
    ├── oc get deployments -n hive -o json
    │
    ├── Compare discovered vs existing components.yaml
    │   ├── New components → add with "[NEW] auto-discovered" tag
    │   └── Existing components → no change (preserves manual curation)
    │
    └── Update acm_version + last_refreshed timestamp
```

### Promotion Flow

```
refresh.py --promote
    │
    ├── Read learned/corrections.yaml
    │   └── Display corrections for manual review
    │
    ├── Read learned/new-patterns.yaml
    │   ├── Check for duplicate IDs against failure-patterns.yaml
    │   ├── Append non-duplicates to failure-patterns.yaml
    │   └── Remove promoted entries from learned/new-patterns.yaml
    │
    └── Read learned/selector-changes.yaml
        └── Display changes for manual review
```

---

## Interaction with Pipeline Stages

### Stage 1 (gather.py) — Produces Data

Stage 1 does NOT read `knowledge/` directly. Instead it uses:
- `src/data/feature_playbooks/` — YAML playbooks consumed by `FeatureKnowledgeService` and `EnvironmentOracleService`
- `FeatureAreaService` — programmatic test-to-feature-area mapping
- `KnowledgeGraphClient` — Neo4j queries for dependency context

These produce `feature_knowledge`, `cluster_oracle`, and `feature_grounding` in `core-data.json`.

### Stage 2 (AI Agent) — Reads Knowledge

The AI agent reads `knowledge/` files at the start of analysis:
1. `failure-patterns.yaml` — first check for known patterns (fast path)
2. `components.yaml` — component health context during investigation
3. `dependencies.yaml` — cascade failure tracing during root cause analysis
4. `selectors.yaml` — ground truth comparison for selector mismatches
5. `api-endpoints.yaml` — understanding backend probe results
6. `feature-areas.yaml` — cross-referencing feature area mappings
7. `test-mapping.yaml` — scoping investigation to relevant areas

### Between Runs — Learning Loop

```
Run N: Agent classifies test failures
         │
         ├── Discovers new pattern → writes learned/new-patterns.yaml
         ├── Feedback CLI records correction → writes learned/corrections.yaml
         └── Identifies selector change → writes learned/selector-changes.yaml

Before Run N+1: refresh.py --promote
         │
         ├── Promotes validated patterns to failure-patterns.yaml
         └── Clears promoted entries from learned/

Run N+1: Agent reads updated failure-patterns.yaml
         └── Short-circuits classification for promoted patterns
```

---

## Maintenance

### When to Refresh

| Event | Action |
|-------|--------|
| New ACM version deployed | `python -m knowledge.refresh --components --acm-version X.Y` |
| After analysis run | `python -m knowledge.refresh --promote` |
| Selector test failures increasing | Refresh selectors via ACM-UI MCP |
| New dependency chain discovered | Add to `dependencies.yaml` manually |

### Adding a New Component

Add to `components.yaml`:

```yaml
  new-component-name:
    subsystem: FeatureArea
    type: hub-deployment
    namespace: open-cluster-management
    pod_label: "app=new-component-name"
    health_check: "oc get deploy new-component-name -n {ns} -o jsonpath='{.status.readyReplicas}'"
    depends_on: [upstream-dependency]
    critical_for: [feature-page, related-tests]
    notes: "Description of what this component does and impact when down."
```

### Adding a New Failure Pattern

Add to `failure-patterns.yaml`:

```yaml
  - id: short-identifier
    category: selector|infrastructure|product|flaky
    signature: "regex pattern matching the error"
    classification: PRODUCT_BUG|AUTOMATION_BUG|INFRASTRUCTURE|FLAKY
    confidence: 0.80
    explanation: "Why this pattern maps to this classification"
    fix: "What to do about it"
```

Or let the agent discover it — the agent writes to `learned/new-patterns.yaml`, then `refresh.py --promote` moves it to `failure-patterns.yaml`.
