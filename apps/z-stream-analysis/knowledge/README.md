# Z-Stream Analysis Knowledge Database

Standalone knowledge database for the z-stream pipeline analysis app.
These files provide domain knowledge that the AI agent reads directly during
Stage 2 analysis to inform classification decisions.

## Relationship to Feature Playbooks

The feature playbooks at `src/data/feature_playbooks/` are programmatically
consumed by `FeatureKnowledgeService` during Stage 1 (gather.py). They define
architecture, prerequisites, and failure paths per feature area.

This knowledge database is different -- it provides reference data that the AI
agent reads directly during Stage 2 for context that playbooks don't cover:
component registries, dependency chains, selector inventories, API endpoints,
known failure patterns, and test mappings.

## Files

### Structured Domain Knowledge

- `components.yaml` -- ACM component registry: name, subsystem, namespace, pod
  labels, health checks, and operational notes
- `dependencies.yaml` -- Component dependency chains and cascade failure paths
- `selectors.yaml` -- UI selector ground truth per feature area (for stale
  selector detection)
- `api-endpoints.yaml` -- Backend API endpoints with probe commands and
  expected responses
- `feature-areas.yaml` -- Feature area index mapping test patterns to
  subsystems and components (lightweight complement to playbooks)
- `failure-patterns.yaml` -- Known failure signatures for short-circuit
  classification without full investigation
- `test-mapping.yaml` -- Test suite to feature area mapping with known issues

### Agent-Contributed Knowledge

- `learned/corrections.yaml` -- Classification corrections from feedback
- `learned/new-patterns.yaml` -- New failure patterns discovered during runs
- `learned/selector-changes.yaml` -- Selector renames detected during runs

### Refresh

- `refresh.py` -- Updates knowledge from ACM-UI MCP, KG, GitHub, JIRA

## How the AI Agent Uses These Files

During Stage 2 analysis:
1. Read `components.yaml` to understand what components exist and their health
2. Check `failure-patterns.yaml` for fast pattern matching before investigation
3. Consult `dependencies.yaml` when tracing cascade failures
4. Reference `selectors.yaml` when investigating selector mismatch failures
5. Use `api-endpoints.yaml` to understand backend probe results
6. Check `feature-areas.yaml` for test-to-feature mapping context
7. Reference `test-mapping.yaml` for known test issues
8. Check `learned/` for patterns from previous runs
