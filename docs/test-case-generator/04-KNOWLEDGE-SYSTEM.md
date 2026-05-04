# Knowledge System

The `knowledge/` directory contains curated domain knowledge that agents read during the pipeline. Knowledge is organized into three categories: conventions (authoritative format rules), architecture (per-area domain knowledge), and examples (sample test cases).

**Location:** `.claude/knowledge/test-case-generator/`, resolved via `KNOWLEDGE_DIR = ${CLAUDE_SKILL_DIR}/../../knowledge/test-case-generator/` from the portable skill pack. Contains 14 files.

## Directory Structure

```
knowledge/
├── conventions/                    # Authoritative: test case format rules
│   ├── test-case-format.md         # Section order, naming, 85-case conventions
│   ├── polarion-html-templates.md  # HTML generation rules for Polarion import
│   ├── area-naming-patterns.md     # Title tag patterns by console area
│   └── cli-in-steps-rules.md       # When CLI is allowed in test steps
├── architecture/                   # Domain knowledge per console area
│   ├── governance.md               # Policy types, discovered vs managed
│   ├── rbac.md                     # FG-RBAC, MCRA, scopes
│   ├── fleet-virt.md               # Tree view, VM actions, KubeVirt
│   ├── cclm.md                     # Cross-cluster live migration wizard
│   ├── mtv.md                      # Migration toolkit for virtualization
│   ├── clusters.md                 # Cluster lifecycle, import/detach
│   ├── search.md                   # Search API
│   ├── applications.md             # ALC, subscriptions
│   └── credentials.md              # Provider credentials
├── examples/                       # Sample test cases for format reference
│   └── sample-test-case.md         # Convention-compliant sample (fallback)
└── patterns/                       # Learned patterns from successful runs
    └── README.md                   # Index (grows over time)
```

## Reading Rules

Agents read knowledge at specific pipeline phases:

| Phase | What is read | Why |
|-------|-------------|-----|
| Phase 1 | `conventions/test-case-format.md`, `conventions/polarion-html-templates.md`, `architecture/<area>.md` | Loaded into `gather-output.json` for downstream subagents |
| Phase 6 (writer) | All conventions files, `architecture/<area>.md` (constraints), peer test cases, patterns | Format and behavioral constraints before writing |
| Phase 7 (reviewer) | Conventions files, `architecture/<area>.md` (cross-reference), common mistakes (built into agent) | Validation reference + knowledge cross-reference |
| Phase 8 | `conventions/polarion-html-templates.md` (baked into `generate_html.py`) | HTML generation rules |

## Validation Authority

Architecture knowledge files serve as **validation constraints**, not just context. When an agent's analysis of a PR diff contradicts a knowledge file on field order, filtering behavior, or empty state rendering, the knowledge file is the default authority. Agents must verify via `get_component_source()` before overriding a knowledge file claim.

## Writing Rules

- Only write to `patterns/`
- Never modify `conventions/` or `architecture/` programmatically
- Patterns are written after successful pipeline runs (planned)

---

## Conventions

### test-case-format.md

Extracted from 85+ existing test cases. Defines the authoritative section order, naming conventions, and format rules that every generated test case must follow.

**Section order (mandatory):**
1. Title: `# RHACM4K-XXXXX - [Tag-Version] Area - Test Name`
2. Metadata: Polarion ID, Status, Created/Updated dates
3. Polarion Fields: 10 fields as `## Field: Value` lines
4. Description: Feature explanation, verification list, Entry Point, JIRA Coverage
5. Setup: Prerequisites, Test Environment, numbered bash commands with `# Expected:`
6. Test Steps: `### Step N: Title` with numbered actions, bullet expected results, `---` separators
7. Teardown: Cleanup commands with `--ignore-not-found`
8. Notes (optional): Implementation details, code references

**Complexity levels:**

| Level | Steps | Lines | Example |
|-------|-------|-------|---------|
| Simple | 2-4 | ~100 | Tree view toggle, status check |
| Medium | 5-8 | ~200 | Role assignment, VM actions |
| Complex | 9-15+ | 500+ | End-to-end migration, multi-step RBAC |

### area-naming-patterns.md

Maps console areas to Polarion title tag patterns and component/subcomponent fields:

| Area | Tag Pattern | Polarion Component | Polarion Subcomponent |
|------|------------|-------------------|---------------------|
| Governance | `[GRC-X.XX]` | Governance | Discovered Policies |
| RBAC | `[FG-RBAC-X.XX]` | Virtualization | RBAC |
| Fleet Virt | `[FG-RBAC-X.XX] Fleet Virtualization UI` | Virtualization | Fleet Virtualization |
| CCLM | `[FG-RBAC-X.XX] CCLM` | Virtualization | CCLM |
| MTV | `[MTV-X.XX]` | Virtualization | MTV |
| Search | `[FG-RBAC-X.XX] Search` | Search | Search |
| Clusters | `[Clusters-X.XX]` | Cluster Lifecycle | Clusters |
| Applications | `[Apps-X.XX]` | Application Lifecycle | Applications |
| Credentials | `[Credentials-X.XX]` | Cluster Lifecycle | Credentials |

### cli-in-steps-rules.md

Rules for when CLI commands are allowed in test steps:

| Section | CLI Allowed? | Notes |
|---------|-------------|-------|
| Setup | Yes | Bash scripts with `oc` commands |
| Test Steps | UI-only by default | Exception: CLI for backend validation (verify resource YAML, check config state) |
| Teardown | Yes | Cleanup commands |

CLI is NOT allowed as a substitute for navigating the UI.

### polarion-html-templates.md

Fixed HTML templates for Polarion import:

- No spaces after `;` in CSS styles
- Bold: `<span style="font-weight:bold;">` (not `<b>`)
- Escape `&&` as `&amp;&amp;`
- Line breaks: `<br>` (not `\n`)
- Table header: `contenteditable="false"`, `id` attributes, `background-color:#F0F0F0`
- Code blocks: `<pre>` with monospace font (not `<code>`)

---

## Architecture Knowledge

Per-area domain knowledge files that help agents understand the feature context. All nine supported areas have architecture files.

Each file covers:
- Component names and paths in the ACM Console source
- Navigation routes and entry points
- Translation keys for UI labels
- Key data types and relationships
- Testing considerations specific to the area

### governance.md

Covers 8 policy types (ConfigurationPolicy, CertificatePolicy, OperatorPolicy, Gatekeeper Constraints, Gatekeeper Mutations, Kyverno ClusterPolicy, Kyverno Policy, ValidatingAdmissionPolicyBinding), discovered vs managed policy distinction, system label filtering patterns (`cluster-name`, `cluster-namespace`, `policy.open-cluster-management.io/*`), description list field order, and navigation routes.

### rbac.md

FG-RBAC feature, ManagedClusterRoleAssignment (MCRA), scope management, DirectAuth, OIDC, MergedIdentities, role assignment creation/editing.

### fleet-virt.md

Fleet Virtualization tree view, VM actions (start, stop, pause, restart, migrate), KubeVirt integration, spoke cluster virtual machine management.

### cclm.md

Cross-Cluster Live Migration: wizard for migrating VMs between managed clusters, kubevirt-plugin components, target cluster/namespace selection, migration status monitoring. Requires `repo="kubevirt"` for MCP searches.

### mtv.md

Migration Toolkit for Virtualization (Forklift): fleet-level visibility of MTV migration plans across managed clusters, provider types (VMware, RHV, OpenStack, OVA), migration plan status monitoring. ACM provides fleet visibility, not plan management. Requires `repo="kubevirt"` for MCP searches.

### clusters.md

Cluster lifecycle: import, detach, destroy, cluster sets, managed cluster status.

### search.md

ACM Search API, global search queries, search-based resource discovery.

### applications.md

Application Lifecycle Controller (ALC), subscriptions, channels, deployments.

### credentials.md

Provider credentials: AWS, Azure, GCP, VMware, bare metal. Secret management and credential rotation.

---

## Examples

### sample-test-case.md

A convention-compliant sample test case used as the format reference when no peer test cases are found for the area/version. This is the fallback that ensures the test-case-generator agent always has a format reference.

The sample uses governance area conventions (`[GRC-2.17]` tag, Governance component, Discovered Policies subcomponent) with 6 test steps.

---

## Diagnostics

Common mistake checks are built into the quality-reviewer agent definition (`references/agents/quality-reviewer.md`, "Common Mistakes to Flag" section) rather than stored as a separate knowledge file. The reviewer also reads conventions files directly during its validation process (see Step 2 in the agent definition).

---

## Patterns (Planned)

The `patterns/` directory is designed to store patterns learned from successful pipeline runs. After a validated test case is produced, the pipeline may write area-specific patterns (`<area>-patterns.json`) containing discovered selectors, routes, translations, and common test structures.

No patterns have been written yet. Files will accumulate as runs complete successfully.

**Planned format:**
```json
{
  "area": "governance",
  "last_updated": "2026-04-18T12:00:00Z",
  "selectors": {...},
  "routes": {...},
  "translations": {...},
  "common_structures": [...]
}
```
