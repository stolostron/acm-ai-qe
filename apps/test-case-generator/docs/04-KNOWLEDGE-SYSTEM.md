# Knowledge System

The `knowledge/` directory contains curated domain knowledge that agents read during the pipeline. Knowledge is organized into three categories: conventions (authoritative format rules), architecture (per-area domain knowledge), and examples (sample test cases).

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
| Stage 1 | `conventions/test-case-format.md`, `conventions/polarion-html-templates.md`, `architecture/<area>.md` | Loaded into `gather-output.json` for downstream agents |
| Phase 4 (writer) | All conventions files, peer test cases from `examples/`, patterns for the area | Format reference before writing |
| Phase 4.5 (reviewer) | Conventions files, common mistakes checklist (built into agent) | Validation reference |
| Stage 3 | `conventions/polarion-html-templates.md` (baked into `html_generator.py`) | HTML generation rules |

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

Per-area domain knowledge files that help agents understand the feature context. Each file covers:
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

Common mistakes are now built into the quality-reviewer agent (`.claude/agents/quality-reviewer.md`, "Common Mistakes to Flag" section) rather than stored as a separate knowledge file.

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
