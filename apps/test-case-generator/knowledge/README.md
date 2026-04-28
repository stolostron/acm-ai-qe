# Knowledge Database

Domain knowledge for ACM Console test case generation.

## Structure

### conventions/ (read-only, curated)
Authoritative test case format rules. Never modify programmatically.

- `test-case-format.md` -- Section order, naming, complexity levels (from 85+ existing test cases)
- `polarion-html-templates.md` -- HTML generation rules for Polarion import
- `area-naming-patterns.md` -- Title tag patterns and Polarion component mapping by area
- `cli-in-steps-rules.md` -- When CLI is allowed in test steps

### architecture/ (read-only, curated)
Per-area domain knowledge. Covers component architecture, common patterns, and area-specific testing considerations.

- `governance.md` -- Policy types, discovered vs managed policies, label filtering
- `rbac.md` -- FG-RBAC, MCRA, ClusterPermission, scope types
- `fleet-virt.md` -- Fleet Virtualization tree view, VM actions
- `cclm.md` -- Cross-cluster live migration wizard, kubevirt-plugin
- `mtv.md` -- Migration toolkit for virtualization, fleet migration status
- `clusters.md` -- Cluster lifecycle, cluster sets, import
- `search.md` -- Search API, managed hub clusters
- `applications.md` -- ALC, subscriptions, channels
- `credentials.md` -- Provider credentials

### patterns/ (agent-written, grows over time)
Learned patterns from successful test case generation runs. The agent writes here after producing validated test cases.

## Usage Rules

- **Always** read `conventions/test-case-format.md` before generating any test case
- **Always** read `conventions/area-naming-patterns.md` to get the correct title tag
- **Read** `architecture/{area}.md` for domain context AND as validation constraints (field order, filtering, empty states are authoritative)
- **Write** to `patterns/` after a successful run with new discoveries
- **Never** modify `conventions/` or `architecture/` programmatically
- **Validation authority**: If agent analysis contradicts an architecture file, trust the architecture file and verify via `get_component_source()` before overriding
