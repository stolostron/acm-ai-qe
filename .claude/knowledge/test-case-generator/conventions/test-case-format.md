# Test Case Conventions

Conventions extracted from 85+ existing test cases in `documentation/acm-components/virt/test-cases/`.

---

## File Naming

**Naming:** `RHACM4K-{ID}-{Feature-Description}.md`

Examples:
- `RHACM4K-61726-RBAC-UI-GlobalAccess.md`
- `RHACM4K-59217-SINGLE-VM-LIVE-MIGRATION.md`
- `RHACM4K-60558-Fleet-Virt-TreeView-Toggle-Button.md`

---

## Document Structure

Every test case follows this section order:

### 1. Title (H1)

```markdown
# RHACM4K-XXXXX - [Tag-Version] Area - Test Name
```

Replace `X.XX` with ACM version from JIRA `fix_versions`. See `area-naming-patterns.md` for tag patterns per area.

### 2. Metadata Block

```markdown
**Polarion ID:** RHACM4K-XXXXX
**Status:** Draft | proposed
**Created:** YYYY-MM-DD
**Updated:** YYYY-MM-DD
```

### 3. Polarion Fields (H2 lines)

```markdown
## Type: Test Case
## Level: System
## Component: Virtualization | Cluster Lifecycle | Governance | ...
## Subcomponent: RBAC | Fleet Virtualization | CCLM | Discovered Policies | ...
## Test Type: Functional
## Pos/Neg: Positive | Negative
## Importance: High | Medium | Low
## Automation: Not Automated | Automated
## Tags: ui, rbac, mcra, ...
## Release: 2.17
```

### 4. Description

What the test validates. Include:
- Feature being tested (1-2 paragraphs)
- Numbered list of what is verified
- **Entry Point** (discovered via MCP `get_routes`, not assumed)
- **Dev JIRA Coverage** with primary and secondary tickets

### 5. Setup

- **Prerequisites** (ACM version, CNV, RBAC, cluster-admin, etc.)
- **Test Environment** (hub name, console URL, IDP, test users)
- **Setup Commands** (numbered bash steps with expected output)

Setup command format:
```bash
# N. Description of what this verifies
oc get <resource> ...
# Expected: Description of expected output
```

### 6. Test Steps (H3 per step)

Each step:
```markdown
### Step N: Step Title

1. Action one
2. Action two

**Expected Result:**
- Expected outcome one
- Expected outcome two
```

Rules:
- Steps are UI-focused (user interactions in the console)
- Each step should verify ONE distinct behavior or interaction — don't combine passive observation (reading text) with active interaction (clicking/navigating) in the same step
- CLI is allowed ONLY for backend validation, in DEDICATED steps placed after UI steps (not embedded within UI steps)
- Implementation details from code (sort algorithms, default values, parsing logic) must be translated into observable verifications (e.g., `compareNumbers` → "sorting is numeric, not alphabetical")
- Each step has a clear title and numbered actions
- Expected results use bullet points (target 2-3 bullets covering the same behavior)
- Steps are separated by `---`

### 7. Teardown

```markdown
## Teardown

\`\`\`bash
# Cleanup commands
oc delete <resource> ... --ignore-not-found
\`\`\`
```

### 8. Notes (optional)

Implementation details, known issues, code references, test scope limitations.

### 9. Known Issues and Code References (optional)

References to source code components and implementation tickets.

---

## CLI-in-Test-Steps Rule

| Section | CLI Commands |
|---------|-------------|
| Setup | Allowed (bash scripts with `oc` commands) |
| Test Steps | UI-only by default. Exception: CLI allowed for backend validation in a DEDICATED step titled "Verify [what] via CLI (Backend Validation)" — placed after UI steps, not embedded within them |
| Teardown | Allowed (cleanup commands) |

---

## Test Case Complexity Levels

| Complexity | Steps | Lines | Example |
|-----------|-------|-------|---------|
| Simple | 2-4 | ~100 | Tree view toggle, status check |
| Medium | 5-8 | ~200 | Role assignment creation, VM actions |
| Complex | 9-15+ | 500+ | End-to-end migration, multi-step RBAC validation |
