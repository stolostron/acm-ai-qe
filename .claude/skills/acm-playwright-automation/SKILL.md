---
name: acm-playwright-automation
description: >-
  Write or update Playwright E2E automation scripts for ACM Console in
  stolostron/console-e2e. Covers any ACM Console area (RBAC, Clusters,
  Fleet Virt, Search, ALC, GRC, Credentials, etc.) for any ACM version.
  Uses subagents for parallel context gathering, MCP servers (acm-source,
  jira, polarion, playwright) for UI discovery, enforces repo conventions
  via code quality review, and self-corrects failures via failure debugger.
  Trigger on: Playwright, spec file, console-e2e, e2e test, write automation,
  automate test case.
  DO NOT TRIGGER: for Cypress tests (use acm-cypress-automation), for test
  case writing (use acm-test-case-generator), for test case validation
  (use acm-test-case-validator).
compatibility: >-
  Required: acm-source MCP (selectors, routes, translations), polarion MCP
  (test steps), jira MCP (story details). Recommended: playwright MCP
  (live browser validation), neo4j-rhacm MCP (architecture context).
  Optional: jenkins MCP (CI failure investigation), acm-search MCP
  (cluster resource queries), acm-kubectl MCP (multicluster ops).
  CLI: oc (OpenShift CLI), gh (GitHub CLI), npx (Node.js).
metadata:
  author: acm-qe
  version: "1.0.0"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Bash(npx:*)
  - Bash(npm:*)
  - Bash(node:*)
  - Bash(oc:*)
  - Bash(gh:*)
  - Bash(git:*)
  - Bash(ls:*)
  - Bash(cat:*)
  - Bash(rg:*)
  - Bash(mkdir:*)
  - Bash(echo:*)
  - Bash(head:*)
  - Bash(tail:*)
  - mcp__acm-source__set_acm_version
  - mcp__acm-source__set_cnv_version
  - mcp__acm-source__list_repos
  - mcp__acm-source__search_code
  - mcp__acm-source__get_component_source
  - mcp__acm-source__find_test_ids
  - mcp__acm-source__search_translations
  - mcp__acm-source__get_wizard_steps
  - mcp__acm-source__get_acm_selectors
  - mcp__acm-source__get_fleet_virt_selectors
  - mcp__acm-source__get_routes
  - mcp__acm-source__get_patternfly_selectors
  - mcp__acm-source__get_component_types
  - mcp__polarion__get_polarion_work_item
  - mcp__polarion__get_polarion_test_steps
  - mcp__polarion__get_polarion_setup_html
  - mcp__polarion__get_polarion_test_case_summary
  - mcp__jira__get_issue
  - mcp__jira__search_issues
---

# Write Automation Script -- Playwright (console-e2e)

Write or update Playwright E2E automation scripts for any ACM Console UI feature using a subagent-orchestrated pipeline.

| Framework | Repo | Local Clone | Status |
|-----------|------|-------------|--------|
| **Playwright** | `stolostron/console-e2e` | `$CONSOLE_E2E_ROOT` (user's local clone -- see Variable Resolution below) | Active development |

---

## Variable Resolution

Before executing any phase, resolve these variables:

| Variable | How to resolve | Fallback |
|----------|---------------|----------|
| `CONSOLE_E2E_ROOT` | `$CONSOLE_E2E_ROOT` env var → `git rev-parse --show-toplevel` if cwd is inside the clone → locate via `find ~ -maxdepth 5 -type d -name console-e2e -path "*/stolostron/*" 2>/dev/null` | Ask the user for the path to their `stolostron/console-e2e` clone |
| `CYPRESS_ROOT` | `$CYPRESS_ROOT` env var → sibling of `CONSOLE_E2E_ROOT` named `clc-ui` | Ask the user |
| `CLAUDE_SKILL_DIR` | Provided by Claude Code runtime | N/A |

---

## Core Philosophy

1. **Discover, don't assume** -- use `acm-source` MCP for source code selectors, playwright MCP for live page validation. ACM Console spans many areas (Clusters, Applications, Governance, Search, Credentials, Fleet Virt, RBAC, Observability, etc.) -- each has different UI patterns, resources, and behaviors. Always investigate the specific area.
2. **Tests are self-contained** -- every test creates its own prerequisites (`beforeAll`) and cleans up (`afterAll`). Never assume the cluster has VMs, namespaces, policies, applications, or any resource. Analyze Polarion steps to identify what must exist, then create it via `OcCliService`. Each test case is different.
3. **Reuse before creating** -- before creating ANY new function, interface, config getter, service method, or fixture property, answer: "Does something that already exists return this data or perform this action?" If yes, use it. If it covers 50% or more of what you need, extend it or compose it with a small addition rather than creating a parallel abstraction. Only create entirely new code when nothing existing covers the need. This applies to every layer: config, services, page objects, fixtures, constants. Two functions with different names and return types can still be semantic duplicates if they draw from the same underlying data -- that is a defect, not a design choice.
4. **Follow existing patterns** -- subagent reads neighboring files before you write anything
5. **One test per scenario** -- one `test()` per Polarion ID (or split for retry granularity)
6. **Centralize selectors** -- constants files + page object locators, never inline in tests
7. **Only what the test needs** -- create new page objects, services, fixtures, and constants files when they don't exist. But inside each file, only add the methods, fields, and exports that the current test spec will call. Do not pre-build methods for future tests, even if they are correct and will be needed later. A wizard page object starts with the 3 methods this test uses; the next PR adds more when the next test needs them.
8. **Separate concerns by layer** -- Pages / Components / Services / Fixtures / Tests
9. **Fixtures provide, tests consume** -- tests request only the fixtures they need; Playwright instantiates lazily
10. **Backend via CLI, not UI** -- setup and teardown use `OcCliService`, not UI wizards
11. **Quality gate before testing** -- code quality reviewer catches issues before the test runs
12. **Self-correcting failures** -- failure debugger diagnoses and fixes automation bugs automatically
13. **Never commit/push** -- after tests pass, report to user and stop
14. **Branch from latest remote main** -- always create a fresh branch from `origin/main` before writing code (see Branch Management below)

---

## Branch Management (MANDATORY)

Before writing any code, ensure you are on a **clean branch created from the latest remote main**. Never add automation to an existing feature branch unless the user explicitly instructs otherwise.

```
cd $CONSOLE_E2E_ROOT
git fetch origin main
git checkout -b <descriptive-branch-name> origin/main
```

**Branch naming:** `<area>-<feature-or-polarion-id>` (e.g., `governance-policy-labels`, `fg-rbac-role-assignment-61726`, `fleet-virt-advanced-search`)

**Rules:**
- Always `git fetch origin main` first to get the latest remote state
- Create the branch from `origin/main`, NOT from the current HEAD or local main
- If the current working directory has uncommitted changes on another branch, stash or confirm with the user before switching
- If the user says "work on branch X" or "add to my current branch", follow their instruction instead

---

## ACM Hybrid Playwright Architecture

The console-e2e repo follows an **ACM Hybrid Architecture** that separates "Test Intent" (what to verify) from "Implementation Details" (how to interact with UI/CLI).

```
+--------------------------------------------------------------+
|  TESTS (src/tests/)                                           |
|  - Polarion: one test() per ID + test.step() per step         |
|  - ALC sanity: multi test() in one describe (app/)            |
|  - Destructure fixtures: { clusterListPage, oc }              |
|  - No selectors, page.goto, or oc.run in specs                |
+----------------+--------------------+-------------------------+
                 |                    |
    +------------v------------+  +---v--------------------------+
    |  FIXTURES (7 files)     |  |  PAGES + COMPONENTS          |
    |  acm-test (cluster+gov) |  |  BasePage(page) only         |
    |  app-test (ALC)         |  |  30 domain pages (page, oc)  |
    |  governance-test (GRC)  |  |  10 components (AcmTable+)   |
    |  rbac-test (asUser)     |  |  goto() on each page          |
    |  fg-rbac-test, fleet-*  |  |                              |
    |  search-test            |  |                              |
    |  setup -> @playwright   |  |                              |
    +-----+-------------------+  +---+--------------------------+
          |                          |
    +-----v---------------------+  +--v----------------------------+
    |  LIB (5 subdirs)          |  |  SERVICES (no Playwright)     |
    |  openshift-login.ts       |  |  OcCliService (37 methods)    |
    |  app/, cluster/, gov/     |  |  ObservabilityService         |
    |  assertions/, placement/  |  |  mcra*, vm*, policy*, app*    |
    +---------------------------+  +-------------------------------+
```

### Key Architectural Rules

- **Login runs once** in setup projects -- `auth.setup.ts` logs in admin (saves `.auth/admin.json`), `rbac-auth.setup.ts` logs in RBAC users (saves `.auth/{role}.json` per user). Single login implementation: `openshiftLogin()` in `src/lib/openshift-login.ts`. Tests do NOT log in -- they load pre-saved cookies via `storageState`. Playwright projects control which setup runs: admin-only projects depend on `['setup']`, RBAC projects depend on `['setup', 'rbac-setup']`.
- **Multi-user login via storageState** -- `openshiftLogin(page, LoginOptions)` in `src/lib/openshift-login.ts`. Admin: `auth.setup.ts` -> `.auth/admin.json` (not `user.json`). RBAC: `rbac-auth.setup.ts` -> `.auth/{role}.json` per user from `getRbacUsers(RBAC_DOMAIN)`; **41 users** in `presets.ts` across 3 tiers (rbac-ui, vm, full). Config getters: `getRbacConfig()` for RBAC settings, `getVirtConfig()` for Fleet Virt settings. `rbac-test.ts` provides `asUser(role)` -> `{ page }` (~50ms). Area fixtures (e.g. `fg-rbac-test.ts`) extend `rbac-test` to wire **same-domain** page objects (UserDetailsPage, RoleAssignmentWizardPage, RoleAssignmentsTable) via fixture DI. **Cross-domain page objects MUST NOT be wired into fixtures** -- tests that need page objects from another domain construct them inline from `asUser(role).page`. This prevents compile-time coupling between unrelated areas.
- **Fixtures create pages and services.** 7 fixture files: `acm-test` (cluster + governance shared), `app-test` (ALC), `governance-test` (GRC), `rbac-test` (base), `fg-rbac-test`, `fleet-virt-test`, `search-test`. Examples: `async ({ clusterListPage, observabilityService }) => {}` (cluster); `async ({ applicationListPage }) => {}` (app).
- **Cleanup in afterEach/afterAll** so retries start clean. Playwright re-runs the full test on retry.
- **No selectors in tests.** All locators live in page objects (as `private readonly` properties) or constants.
- **Services are backend-only.** `OcCliService` has 37 methods: generic CLI (`run`, `applyYaml`, `deleteYaml`, `getConsoleUrl`, `hasResourcesInCluster`) and domain-specific (prefixed by resource type: `mcra*`, `vm*`, `policy*`, `application*`, `cluster*`, `placement*`, `subscription*`). When 2+ tests share the same `oc.run()` pattern, add a named method to `OcCliService` directly. Services MUST NOT import Playwright.
- **Browser interaction logic lives in `lib/`.** 5 subdirectories (`app/`, `assertions/`, `cluster/`, `governance/`, `placement/`) plus root files (`openshift-login.ts`, `utils.ts`). UI assertion helpers, browser context management, area-specific setup helpers. This is the line between `services/` (no browser) and `lib/` (browser OK). RBAC login is handled by storageState in the setup project, not `lib/`.
- **Backend setup via OcCliService** -- use `oc.run()` or named OcCliService methods instead of UI wizards for creating resources.
- **Tests own their prerequisites.** Every test must be self-contained. When analyzing test steps, identify what must exist on the cluster (VMs, namespaces, ConfigMaps, Secrets, applications, policies, roles -- whatever the specific test case requires). Create those resources in `beforeAll` via OcCliService and clean up in `afterAll`. Never assume cluster state. Each ACM area has different prerequisites -- there is no default set.
- **Constants: one authoritative location.** Large domains (20+ selectors) have their own constants file that owns routes, selectors, AND text labels. Do NOT duplicate selectors between `selectors.ts` and domain files.

### Reference Documentation (read in this order)

1. **Architecture summary (agent-optimized, AUTHORITATIVE):** `${CLAUDE_SKILL_DIR}/references/architecture-summary.md` -- layer table, file inventory, rules, placement decisions. Verified against the live repo.
2. **Framework patterns:** `${CLAUDE_SKILL_DIR}/framework/playwright-patterns.md` -- locator strategy, config, auth, test structure examples.
3. **Target / migration (aspirational):** `docs/architecture-overview.md` in the repo -- superset; verify with `Glob`/`ls`
4. **Knowledge base:** `.claude/knowledge/automation/playwright/{area}.md`

---

## MANDATORY: Phase Gate Enforcement

**This section is NON-NEGOTIABLE. Every phase must be tracked and gated.**

### On skill start, IMMEDIATELY create tasks for ALL phases using TaskCreate:

```
TaskCreate: Phase 0 -- Determine area and read knowledge base
TaskCreate: Phase 1 -- Context gathering (3 parallel subagents)
TaskCreate: Phase 2 -- GATE: Synthesize + coverage map (user approval)
TaskCreate: Phase 3 -- Code generation (Page -> Service -> Test)
TaskCreate: Phase 3.5 -- GATE: Code quality + lint check (must pass)
TaskCreate: Phase 4 -- GATE: Local test execution (must pass)
TaskCreate: Phase 4.5 -- Failure debugging (if test failed)
TaskCreate: Phase 5 -- GATE: Polarion coverage verification
```

Use TaskUpdate to mark each phase `in_progress` when starting and `completed` when done.

### Gate rules:

1. **A phase CANNOT be marked `completed` without executing it.** Skipping a phase and marking it done is a violation. **Phase 1 specifically requires ALL THREE subagents to return results** -- launching 2 of 3 and marking Phase 1 complete is a violation. If a subagent fails or is unavailable, report the gap to the user and ask how to proceed.
2. **GATE phases (2, 3.5, 4, 5) are HARD STOPS.** You MUST execute them before proceeding. If you find yourself about to commit, push, or report success without Phase 4 completing, STOP and run the test first.
3. **Phase 4 MUST complete before ANY git commit, git push, or Jenkins trigger.** No exceptions. If the user says "push it," respond: "The skill requires local test execution first. Let me run the test before pushing."
4. **Phase 2 MUST get user approval** on the coverage map before Phase 3 begins.
5. **Phase 3.5 MUST include `npm run lint:check`** and the full anti-pattern + dead code checklist. Every item must be checked individually -- do not batch-skip. Fix and re-run the entire checklist until every item passes.
6. **Phase 5 MUST re-fetch Polarion steps** and verify 100% coverage before reporting success.
7. **On failure in Phase 4**, mark Phase 4 as `pending` (not completed), mark Phase 4.5 as `in_progress`, and launch the failure debugger. After fix, re-run Phase 4.
8. **Never mark Phase 5 complete until Phase 4 shows a passing test.**

### STOP checkpoints (pause and verify before proceeding):

- **STOP after Phase 2:** "Coverage map ready. Awaiting your approval before code generation."
- **STOP after Phase 3:** "Code generation complete. Starting quality review and lint check."
- **STOP after Phase 3.5:** "Quality review passed. Running local test now."
- **STOP after Phase 4 pass:** "Test passed locally. Verifying Polarion coverage."
- **STOP after Phase 4 fail:** "Test failed. Launching failure debugger to diagnose."

---

## Knowledge Base

Before starting work, check the knowledge base for relevant area context:

```
Read .claude/knowledge/automation/playwright/{area}.md
```

Where `{area}` maps to: `app.md` (ALC), `clusters.md` (cluster), `rbac.md` (FG-RBAC), `fleet-virt.md` (Fleet Virt), `credentials.md`, `cluster-sets.md`, `search.md`, `automation-ansible.md`, `ecosystem-cim.md`, `hosted-clusters.md`.

Also cross-reference `.claude/knowledge/ui/{area}.md` for domain context (UI behavior, known issues, component architecture).

After completing work, if you discover new verified patterns or gotchas, write them to the appropriate knowledge base file following the format in `.claude/knowledge/` (see repo CLAUDE.md for write protocol).

---

## ASK QUESTIONS FIRST

| Category | Question |
|----------|----------|
| **ACM Version** | "Which ACM version? (e.g., 2.15, 2.16, 2.17)" |
| **Input Source** | "Polarion ID, JIRA ID, or feature description?" |
| **New or Update** | "New script, or updating an existing one?" |
| **Area** | "Which area? (cluster, app/ALC, fg-rbac, fleet-virt, search, GRC, credentials, etc.)" |
| **Environment** | "Hub URL, password, spoke cluster name?" |
| **CNV Version** | (Fleet Virt only) "CNV version on spoke cluster?" |
| **Test User** | "Existing test user, or need a new one?" |

---

## Phase 0: Determine Area

Map user input to area, test directory, fixture, and Playwright project:

| User area | `src/tests/` dir | Fixture | Playwright `--project` |
|-----------|------------------|---------|-------------------------|
| cluster / clusters | `cluster/` | `acm-test` | `cluster` |
| app / alc / applications | `app/` | `app-test` | `alc` |
| governance / grc / policy | `governance/` | `governance-test` | `governance` |
| search | `search/` | `search-test` | `search` |
| fg-rbac | `fg-rbac/` | `fg-rbac-test` (extends `rbac-test`) | `fg-rbac` |
| fleet-virt | `fleet-virt/` | `fleet-virt-test` | `fleet-virt` |

**Actions:**

1. **Architecture (AUTHORITATIVE):** `${CLAUDE_SKILL_DIR}/references/architecture-summary.md` (layer table, file inventory, rules, placement)
2. **Framework guide:** `${CLAUDE_SKILL_DIR}/framework/playwright-patterns.md` (locator patterns, test structure)
4. **Knowledge base:** `.claude/knowledge/automation/playwright/{area}.md` -- use `app.md` for ALC; `cluster` -> `clusters.md`. Also cross-reference `.claude/knowledge/ui/{area}.md` for domain context.
5. Before creating files, `Glob`/`ls` the repo -- do not assume fg-rbac, fleet-virt, or specific OcCliService methods exist because documentation lists them

**Repo root:** `$CONSOLE_E2E_ROOT`

---

## Phase 1: Context Gathering (3 Parallel Subagents)

**ALL THREE SUBAGENTS ARE MANDATORY. Skipping any subagent is a skill violation.**

Launch **three Agent calls IN PARALLEL** (in a single response). Read each agent's instruction file, then spawn the Agent with those instructions plus the phase-specific input.

**Phase 1 completion checklist (ALL must be true before marking Phase 1 complete):**
- [ ] Agent A (Requirements Extractor) returned Polarion steps
- [ ] Agent B (UI Discovery) returned selectors, DOM structure, and component paths
- [ ] Agent C (Pattern Analyzer) returned existing code patterns and reuse opportunities

**Why UI Discovery cannot be skipped:** Without verifying the actual DOM structure and selectors from source code, specs will use guessed selectors that fail at runtime. Every role locator must be validated against the real component source.

**CRITICAL -- Polarion Test Steps:** If a Polarion ID is provided, fetch full steps via `get_polarion_test_steps` BEFORE writing code. Map each Polarion step to a `test.step()` in the spec. For non-Polarion sanity suites, multiple `test()` blocks without per-step mapping is valid. No Polarion steps may be skipped without explicit user approval.

### Agent A: Requirements Extractor

Read `${CLAUDE_SKILL_DIR}/agents/requirements-extractor.md` for the full agent instructions.

Spawn an Agent with those instructions plus:
- `POLARION_ID`: from user input
- `JIRA_ID`: from user input
- `PR_LINK`: from user input (if provided)
- `FEATURE_DESCRIPTION`: from user input (if no ticket IDs)

When Polarion ID is provided, the agent MUST call `get_polarion_test_steps(project_id='RHACM4K', work_item_id=POLARION_ID)` to fetch every test step and identify prerequisites.

### Agent B: UI Discovery Agent

Read `${CLAUDE_SKILL_DIR}/agents/ui-discovery.md` for the full agent instructions.

Spawn an Agent with those instructions plus:
- `ACM_VERSION`: from user input
- `CNV_VERSION`: from user input (Fleet Virt only)
- `FEATURE_NAME`: component or feature to discover
- `AREA`: determined in Phase 0
- `UI_PAGES`: from user input or inferred from area

### Agent C: Pattern Analyzer

Read `${CLAUDE_SKILL_DIR}/agents/pattern-analyzer.md` for the full agent instructions.

Spawn an Agent with those instructions plus:
- `AREA`: determined in Phase 0
- `KNOWLEDGE_BASE_CONTENT`: the full content of `.claude/knowledge/automation/playwright/{area}.md` (include it in the prompt so the agent has area-specific context)
- `SPEC_DIR`: `src/tests/{area}/`
- `VIEW_DIR`: `src/pages/`
- `ACTIONS_DIR`: `src/services/`

---

## Phase 2: Synthesize Results

Merge outputs from all three agents:

1. **From Requirements Extractor:** Test name, steps, prerequisites, API resources, UI pages
2. **From UI Discovery:** Selectors map, routes, translations, wizard structure, component paths
3. **From Pattern Analyzer:** Patterns to follow, utilities to reuse, existing selectors, cleanup conventions

**Before using the placement table below:** For each file you plan to create or modify, first check if existing code already provides what you need. The table tells you WHERE to put new code -- but only AFTER you've confirmed the code is actually needed. If existing functions, services, or page objects already cover 50%+ of the requirement, compose or extend them instead of creating new files. Use the Pattern Analyzer's sufficiency matrix to verify.

| File Type | Location |
|-----------|----------|
| Test | `src/tests/{area}/{feature}.spec.ts` |
| Page object | `src/pages/{area}/{PageName}.ts` (area subdirectory) |
| Component | `src/components/{area}/{ComponentName}.ts` (area subdirectory) |
| Constants (<20 selectors) | `src/constants/selectors.ts` (add to `SELECTORS.{area}` section) |
| Constants (20+ selectors) | `src/constants/{area}.ts` (routes + selectors + text -- single authoritative file) |
| CLI methods | Add domain-specific methods directly to `src/services/OcCliService.ts` (prefix by resource: `mcra*`, `vm*`) |
| Browser helpers | `src/lib/{ClassName}.ts` (assertions, shared test logic) |
| Template | `src/templates/{resource}.yaml` |
| Fixture | `src/fixtures/{area}-test.ts` |
| Config | Check existing getters in `config/index.ts` first. Only add a new interface + getter if existing ones genuinely don't cover the need. |

Decide: update existing files or create new ones. Always prefer updating.
Follow architecture doc: `selectors.ts` for PF globals + small domains, `{area}.ts` for large domains (routes + selectors + text in one file).

### Polarion Coverage Map (MANDATORY when Polarion ID provided)

Before proceeding to code generation, create a coverage map:

| Polarion Step | Step Title | Planned test.step() | Page Objects Needed | New PO Required? | Prerequisites |
|---|---|---|---|---|---|
| 1 | (from Polarion) | Step 1: ... | (list pages/components) | Yes/No | (what must exist) |
| 2 | (from Polarion) | Step 2: ... | ... | ... | ... |

**Rules:**
- Every Polarion step MUST have a corresponding `test.step()` in the spec
- If a step requires page objects that don't exist, list them as "New PO Required"
- If a step cannot be automated (e.g., visual-only verification), document why and get user approval to skip
- If a step requires a sub-tab or page not yet built, BUILD IT -- do not skip the step
- **Identify prerequisites for every step.** Ask: "What cluster resources must exist for this step to work?" (VMs, namespaces, ConfigMaps, roles, applications, policies, etc.). Aggregate all prerequisites into a `test.beforeAll` block. Each test case is different -- the prerequisites depend entirely on what the test is verifying.
- Present this coverage map to the user for approval before writing code

---

## Phase 3: Code Generation

Write code following the framework guide (`${CLAUDE_SKILL_DIR}/framework/playwright-patterns.md`).

**Order:** Prerequisites -> Service (if needed) -> Page Object / Component -> Fixture wiring -> Test spec

**Scope rule:** At every step, add ONLY what the current test spec requires. Every line of code you write must have a caller in the spec you are writing. No exceptions.

### Test Prerequisites Analysis (MANDATORY)

**Core Principle:** Every test must be self-contained. Never assume the cluster has the resources the test needs. When analyzing a test case (from Polarion steps, JIRA story, or feature description), ALWAYS identify what prerequisites exist and handle them programmatically.

**When to analyze:** During Phase 2 (Synthesize Results), as part of the Polarion Coverage Map. For each test step, ask: "What must already exist on the cluster for this step to succeed?"

**Common prerequisite types (not exhaustive -- each test case is different):**

| Prerequisite | Example | How to Handle |
|-------------|---------|---------------|
| VirtualMachine exists and is running | Fleet Virt tests | `oc.vmEnsureTestVM(name, ns, labels)` in `beforeAll` -- creates a lightweight cirros VM (no PVC, starts in seconds). Poll with `oc.vmIsRunning()` |
| Namespace exists | Test needs resources in a specific namespace | `oc.run('oc create ns ... --dry-run=client -o yaml \| oc apply -f -')` |
| ConfigMap / Secret exists | Test verifies environment tab or credential binding | `oc.run('oc apply -f ...')` with inline YAML |
| RBAC user exists with IDP | FG-RBAC tests that login as a non-admin user | Managed externally (htpasswd), guarded by `test.skip(!config.user)` |
| ManagedCluster is available | Tests that need a spoke cluster | Guarded by `test.skip(!spoke)`, cluster managed externally |
| Role / ClusterRole exists | Tests that assign custom roles | `oc.run('oc apply -f ...')` or verified via `oc get clusterrole` |
| Application / Policy deployed | ALC or GRC tests | `oc.run('oc apply ...')` with YAML templates |
| Snapshot / PVC exists | Storage-related VM tests | `oc.run('oc apply ...')` |

**Pattern:** `test.beforeAll` creates resources via `OcCliService`, `test.afterAll` cleans up.

```typescript
// src/lib/governance/policy-labels-setup.ts (lib helper -- encapsulates OcCliService)
import { OcCliService } from '@services/OcCliService';
const oc = new OcCliService();

export async function ensurePolicyLabelsClean(policyName: string, ns: string, keys: string[]): Promise<boolean> {
  const exists = await oc.policyExists(policyName, ns);
  if (exists) await oc.policyRemoveLabels(policyName, ns, keys);
  return exists;
}
```

```typescript
// spec file -- NO OcCliService import, uses lib helper + fixture
import { test, expect } from '@fixtures/governance-test';
import { ensurePolicyLabelsClean, cleanupPolicyLabels } from '@lib/governance/policy-labels-setup';

test.describe('Feature', { tag: ['@governance'] }, () => {
  let hasResource = false;

  test.beforeAll(async () => {
    hasResource = await ensurePolicyLabelsClean('my-policy', 'local-cluster', ['env']);
  });

  test.afterAll(async () => {
    if (!hasResource) return;
    await cleanupPolicyLabels('my-policy', 'local-cluster', ['env']);
  });

  test('RHACM4K-XXXXX: ...', async ({ oc }) => {
    // In-test operations use fixture-injected oc
    await oc.policyAddLabels('my-policy', 'local-cluster', { env: 'prod' });
  });
});
```

For one-off CLI operations, add a named method to `OcCliService` (prefixed by resource type), then call it from a lib helper:

```typescript
import { OcCliService } from '@services/OcCliService';

test.beforeAll(async () => {
  const oc = new OcCliService();
  await oc.run(`oc apply -f - <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: e2e-test-${Date.now()}
  namespace: default
  labels:
    e2e-test: "true"
data:
  key: value
EOF`);
});
```

**Specific examples across different ACM areas:**

| Area | What the test verifies | What beforeAll creates | What afterAll deletes |
|------|----------------------|----------------------|---------------------|
| Fleet Virt | VM details tabs, search results | `oc.vmEnsureTestVM()` (cirros, no PVC) | `oc.vmDeleteTestVM()` |
| Clusters | Cluster import flow | ManagedCluster YAML via `oc apply` | `oc delete managedcluster` |
| ALC | Application topology, sync status | Application + Channel + Subscription YAMLs | Delete all 3 resources |
| GRC | Policy compliance, violations | Policy + PlacementRule + PlacementBinding | Delete all 3 resources |
| Credentials | Credential list, cloud provider binding | Secret in target namespace | `oc delete secret` |
| Search | Search result accuracy | Any searchable resource (Deployment, ConfigMap) | Delete the resource |
| FG-RBAC | Role assignment wizard, permission checks | RBAC user exists (external), roles assigned in test steps | MCRAs deleted in afterEach |

**Rules:**
- **Analyze first, code second.** Read every Polarion step and ask "what must exist for this to work?" before writing any code. Every test case across every ACM area will have different prerequisites -- there is no one-size-fits-all.
- Resource names include `Date.now()` suffix to avoid collisions between parallel runs
- Label all created resources with `e2e-test: "true"` and `test-case: "rhacm4k-xxxxx"` for traceability and emergency cleanup
- Make creation idempotent (check-then-create, or `--dry-run=client -o yaml | oc apply -f -`) so reruns don't fail
- Always poll for readiness after creation -- every resource type has different readiness signals (VM: Running status, Pod: Ready condition, ManagedCluster: Available condition, Application: Synced status)
- Guard `beforeAll`/`afterAll` with config checks when test may be skipped (e.g., `if (!spokeCluster) return`)
- If a prerequisite cannot be created programmatically (e.g., a physical spoke cluster, an IDP, a cloud provider account), guard with `test.skip(condition, 'reason')` and document what the environment must provide
- For complex prerequisites, add named methods to `OcCliService` (e.g., `vmEnsureTestVM`, `mcraDeleteAllForUser`) rather than inlining raw `oc.run()` calls
- When a test creates resources as PART of its test steps (e.g., creating a role assignment via the wizard IS the test), the prerequisite is the environment needed for that creation (user exists, cluster available) -- not the resource itself

**OcCliService (37 methods -- generic + domain, all areas):**
- Generic: `run(cmd)`, `applyYaml(path)`, `deleteYaml(path)`, `getConsoleUrl()`, `hasResourcesInCluster(resource)`, `deleteNamespace()`, `deleteSecret()`
- MCRA: `mcraGetForUser()`, `mcraGetRolesForUser()`, `mcraDeleteAllForUser()`
- VM: `vmEnsureTestVM(name, ns, labels)`, `vmIsRunning(name, ns)`, `vmDeleteTestVM(name, ns)`
- Policy: `policyExists()`, `policyAddLabels()`, `policyRemoveLabels()`, `policyGetLabels()`
- Application: `application*`, `applicationSetExists()`, `deleteApplicationSet()`
- Cluster: `cluster*`, `labelManagedCluster()`
- Placement: `placement*`, Subscription: `subscription*`

**Domain services (compose OcCliService):**
- **Implemented:** `ObservabilityService` -- `isInstalled()`, `getManagedClusters()`, `getGrafanaAnnotation()`, `restoreGrafanaAnnotation()` (GPU specs use it in `beforeAll`/`afterAll`)
- In hooks: `new ObservabilityService(new OcCliService())`. In tests: prefer fixture-injected service when available.
- Add new domain-specific methods directly to `OcCliService` (prefixed by resource type). Separate service classes only when the domain needs constructor-injected state (like `ObservabilityService`).

### Layer-by-Layer Guide

**1. OcCliService methods (if needed):**
- Add domain-specific methods directly to `src/services/OcCliService.ts`
- Prefix methods by resource type: `mcra*`, `vm*`, `policy*` etc.
- No Playwright imports -- pure CLI
- No separate `services/domains/` directory -- everything goes in `OcCliService`
- Injected via `oc` fixture (already wired in all area fixtures)

**2. Page Object / Component:**
- Page objects extend `BasePage`; table components may extend `AcmTable` OR be standalone
- `private readonly` locators in constructor -- only declare locators that are used by a method the test calls
- Public methods for actions -- only add methods the current test spec will call. A wizard page object for a test that exercises 3 of 7 steps gets methods for those 3 steps, not all 7. Add the rest when a future test needs them.
- Accessibility-first locators: `getByRole` > `getByLabel` > `getByText` > `getByTestId` > `locator`
- **Table component decision:** Check UI Discovery results for the table type. ACM Console pages use `AcmTable` (check `keyFn` for OUIA ID usability); kubevirt-plugin pages use OCP SDK `VirtualizedTable` (different DOM). This informs whether to extend `AcmTable` or build standalone. See `${CLAUDE_SKILL_DIR}/framework/playwright-patterns.md` "AcmTable Component" section.
- **Constants file:** Prefer hierarchical structure grouped by UI location (page, table, wizard) over flat label bags. See `${CLAUDE_SKILL_DIR}/framework/playwright-patterns.md` "Constants Design Pattern" section.

```typescript
import { Page, Locator } from '@playwright/test';
import { BasePage } from '@pages/BasePage';
import { OcCliService } from '@services/OcCliService';
import { CLUSTER_ROUTES } from '@constants/cluster';

export class ClusterListPage extends BasePage {
  constructor(
    page: Page,
    private readonly oc: OcCliService,
  ) {
    super(page);
    // private readonly locators...
  }

  async goto(): Promise<void> {
    const consoleUrl = await this.oc.getConsoleUrl();
    await this.page.goto(`${consoleUrl}${CLUSTER_ROUTES.managed}`);
    await this.waitForLoad();
  }
}
```

**3. Fixture wiring:**
- Import the new page object in the fixture file
- Add to the generic type and wire

```typescript
clusterListPage: async ({ page, oc }, use) => {
  await use(new ClusterListPage(page, oc));
},
```

**4. Test spec:**
- Import from `@fixtures/acm-test` (or area fixture)
- Single `test.describe()` with tag
- One `test()` per Polarion ID
- Destructure only needed fixtures
- Use `test.step()` for logical grouping
- Cleanup in `test.afterEach` / `test.afterAll`

```typescript
import { test, expect } from '@fixtures/acm-test';

// Simple non-Polarion example (AcmTable usage):
test.describe('Cluster List Page', { tag: ['@clusters'] }, () => {
  test('should display the local-cluster in the list', async ({ clusterListPage }) => {
    await clusterListPage.goto();
    await clusterListPage.table.search('local-cluster');
    await clusterListPage.table.verifyRowVisible('local-cluster');
  });
});

// Polarion-mapped example:
test.describe('GPU Features', { tag: ['@clusters'] }, () => {
  test('RHACM4K-63953: ...', async ({ clusterListPage }) => {
    await test.step('Verify GPU count column is visible', async () => {
      await clusterListPage.goto();
      // expect on locators from page / constants
    });
  });
});
```

### Key Rules

- Reuse utilities identified by Pattern Analyzer (do NOT reinvent)
- UI Discovery returns all elements on a page -- use only the selectors the current test needs. Do not create locators, constants, or page object methods for discovered elements that the test does not interact with. Discovery is input for decision-making, not a checklist to implement.
- Follow the structure patterns found by Pattern Analyzer
- Apply the knowledge base gotchas
- Always use path aliases (`@pages/`, `@services/`, `@fixtures/`)

---

## Phase 3.5: Code Quality Review

Read `${CLAUDE_SKILL_DIR}/agents/code-quality-reviewer.md` for the full agent instructions.

Spawn an Agent with:
- `GENERATED_FILES`: list of files created/modified
- `AREA`: from Phase 0
- `KNOWLEDGE_BASE_CONTENT`: area knowledge base content

The reviewer checks:
- Architecture compliance (page objects extend BasePage, fixtures for DI, services for backend)
- Prerequisite completeness (test creates its own resources in beforeAll, cleans up in afterAll, never assumes cluster state)
- Reuse opportunities (existing utils, services, page objects)
- **Anti-pattern scan (MANDATORY -- check EVERY item, do NOT skip):**
  - `page.waitForTimeout()` in any file
  - `test.only` in any file
  - Selectors or CSS locators in spec files (must be in page objects or constants)
  - `page.goto()` in spec files (all navigation must be in page object methods)
  - `page.reload()` in retry loops (use `page.goto(url).catch(() => {})` via PO method)
  - CSS class selectors for assertions (use role-based locators)
  - `not.toBeVisible()` (use `toBeHidden()`)
  - Raw `oc.run()` in spec **files** (hooks should use named OcCliService methods; one-off `oc.run` in hooks only until a named method is added)
  - Separate service class files under `services/domains/` (add methods to OcCliService directly)
  - Inline domain constants in spec files (API groups, resource names, cluster names must be in `constants/{area}.ts`)
  - String literal `'local-cluster'` in spec files (must come from constants or config)
  - Hardcoded column indices `td.nth(N)` (use header-based column resolution)
  - Duplicated methods across multiple page objects (extract to shared component in `components/`)
  - CSS class selectors inline in page objects (move to `SELECTORS` or area constants file)
- **Dead code sweep (MANDATORY -- check EVERY export with grep evidence):**
  - Page object methods with zero callers (check every method -- if no test or fixture calls it, remove it)
  - Unused imports (constants, types, services that were added speculatively but never referenced)
  - Constants exports that are not imported by ANY other file in the PR (remove them)
  - Hardcoded strings that duplicate a constant (use the constant instead)
  - Fixture properties that no test destructures
  - Convenience/shortcut methods that compose other public methods (e.g. `createGlobalAccess()` that calls `selectScopeGlobal()` + `clickNext()` + `selectRole()` + `submitCreate()`) -- if no test calls them, they are dead code even if they "look useful"
  - Every method in a page object must have at least one caller in a test or fixture written in THIS PR. Methods "for future tests" are dead code even if they are correct, well-implemented, and will definitely be needed later. The next PR adds them when the next test needs them. This is non-negotiable -- a page object with 30 methods but only 10 callers in the current specs has 20 methods that must be deleted.
  - **Verification method (NON-NEGOTIABLE):** For EVERY public method in new/modified page objects, run `rg "methodName" src/` and include the grep output in the review. If zero callers outside the defining file, delete the method. Do NOT self-certify -- show the evidence. Same for every exported constant: `rg "CONSTANT_NAME" src/` must show at least one importer.
- **Lint gate:** Run `npm run lint:check` (Prettier + ESLint + TypeScript) on the repo. Fix any errors introduced by generated code before proceeding. **Prettier checks ALL file types** (`.ts`, `.json`, `.md`, `.yml`, `.yaml`) -- if you created or modified any non-TypeScript file (JSON configs, YAML templates, scripts), run `npm run lint:fix` to format them. CI will fail on unformatted files of any type.

**If ANY blocking issue is found:** Fix it, then RE-RUN the entire Phase 3.5 checklist from the top. Do NOT proceed to Phase 4 until every anti-pattern item and every dead code item passes. This is the most common source of review feedback -- skipping items here means reviewer rejection.

---

## Phase 4: Test Execution

Read `${CLAUDE_SKILL_DIR}/agents/test-runner.md` for the full agent instructions.

Spawn an Agent with:
- `SPEC_PATH`: path to the spec file
- `WORKING_DIR`: `$CONSOLE_E2E_ROOT`
- `PROJECT`: `cluster` | `alc` | `governance` | `search` | `fg-rbac` | `fleet-virt` | `unit` (from spec path -- never `chromium` or `app`)

**If test passes:** Proceed to Phase 5.

---

## Phase 4.5: Failure Debugging (if test failed)

Read `${CLAUDE_SKILL_DIR}/agents/failure-debugger.md` for the full agent instructions.

Spawn an Agent with:
- `FAILURE_OUTPUT`: raw test runner output
- `SPEC_PATH`: path to failing spec
- `VIEW_FILES`: paths to page object and component files
- `AREA`: from Phase 0
- `ACM_VERSION`: from user input
- `CLUSTER_URL`: hub API URL

The debugger returns a diagnosis:
- **automation_bug:** Apply the suggested fix, go back to Phase 4
- **environment_issue:** Report to user with evidence
- **product_bug:** Report to user, offer to file JIRA

---

## Phase 5: Report Results

- **All passed:** Report files created/modified, test duration. Ask user about commit.
- **Environment issue:** Report what's wrong, what the user needs to fix.
- **Product bug:** Report the issue, offer to file JIRA.
- **NEVER** commit, push, or modify `build/` directory.
- **ALWAYS** provide a "Local headed run" command so the user can watch the test in a visible browser. Use the test-runner agent's headed command template with the actual KUBECONFIG, spec path, and project name filled in. This is non-optional -- the user expects to see a ready-to-paste command to run the test with UI visible and 2-second slowMo after every successful execution.

### Coverage Verification (MANDATORY)

After all tests pass, re-fetch the Polarion test steps and verify 100% coverage:

1. Call `get_polarion_test_steps` for each Polarion ID
2. Map each Polarion step to the corresponding `test.step()` in the spec
3. Report coverage as a table:

| Polarion Step | Spec Step | Covered? |
|---|---|---|
| Step 1: ... | Step 1: ... | YES/NO |

4. If any step is NOT covered, flag it and implement it before reporting completion
5. Only report "complete" when every Polarion step has a corresponding `test.step()` that exercises the described action and verifies the expected result (N/A for multi-scenario ALC sanity files without Polarion IDs)

### Skip Detection (MANDATORY)

After test execution passes, check the output for ANY skipped steps or conditional early returns. Report ALL skips to the user with this format:

```
SKIPPED STEPS (require attention):
- Step N: [step name] -- SKIPPED because: [reason from console.log or test.skip message]
  Action needed: [fix the skip condition / environment limitation / etc.]
```

**Rules:**
- The goal is ALWAYS to execute ALL Polarion steps via automation. A skip is NOT a pass.
- If a step is skipped due to environment limitations (e.g., only 1 cluster when 2 needed), report it clearly and suggest what the user can do (add a cluster, use a different env, etc.)
- If a step is skipped due to a code bug (shell escaping, wrong command, etc.), FIX IT before reporting success.
- NEVER report "all tests pass" if any Polarion step was skipped without explicitly calling it out.
- Conditional skips (`if (condition) return`) are acceptable ONLY when the environment genuinely cannot support the step -- but they MUST be reported.

---

## Migration Mode (Cypress to Playwright)

When user asks to migrate a Cypress test to Playwright:

1. Read `${CLAUDE_SKILL_DIR}/agents/migration-assistant.md` for the agent instructions
2. Launch an Agent with the Cypress file paths
3. The agent produces Playwright equivalents using the pattern mapping table
4. Run through Phase 3.5 (quality review) and Phase 4 (test execution) as normal

---

## RBAC Test User Convention

Every FG-RBAC test user follows a strict naming convention tied to Polarion test case IDs.

### Naming Format

| Field | Pattern | Example |
|-------|---------|---------|
| Role key (presets.ts) | `fg-rbac-<descriptor>-<polarionId>` | `fg-rbac-csfull-61727` |
| Username (cluster) | `clc-e2e-<descriptor>-<polarionId>` | `clc-e2e-csfull-61727` |
| Lookup key in specs | `rbacConfig.users['<descriptor>-<polarionId>']` | `rbacConfig.users['csfull-61727']` |

### Adding a New RBAC Test User

1. Add to `src/config/presets.ts`:
   ```typescript
   { role: 'fg-rbac-newtest-12345', username: 'clc-e2e-newtest-12345', domains: ['fg-rbac'] },
   ```
2. Add to `scripts/rbac/gen-rbac.sh`:
   ```bash
   "clc-e2e-newtest-12345"    # Description, RHACM4K-12345
   ```
3. The `rbacConfig.users` map auto-populates -- no changes to `index.ts` or `schema.ts`.
4. Spec accesses via: `rbacConfig.users['newtest-12345']`

### RbacConfig Interface (simplified)

```typescript
export interface RbacConfig {
  readonly idpName: string;                        // 'clc-e2e-htpasswd' or env override
  readonly spokeCluster: string;                   // from RBAC_SPOKE_CLUSTER or VIRT_SPOKE_CLUSTER
  readonly users: Readonly<Record<string, string>>; // auto-built from presets.ts
}
```

Do NOT add per-user fields (e.g., `managedAdminUser`). All users go through `rbacConfig.users['key']`.

### IDP Configuration

`presets.ts` uses `idp: 'clc-e2e-htpasswd'`. All users inherit it uniformly. Per-user IDP override (e.g., for LDAP users) is not yet implemented -- add it when the first LDAP test case lands, not before.

### MCRA Propagation Wait

After creating MCRAs via the wizard, wait for `Applied: True` status on ALL MCRAs before verifying permissions:
```typescript
await expect(async () => {
  const userMCRAs = await oc.mcraGetForUser(user);
  expect(userMCRAs.length).toBeGreaterThanOrEqual(1);
  for (const mcra of userMCRAs) {
    const conditions = (mcra.status as Record<string, unknown>)?.conditions as Record<string, unknown>[] | undefined;
    const applied = conditions?.find((c) => c.type === 'Applied');
    expect(applied?.status).toBe('True');
  }
}).toPass({ intervals: [5000, 10000, 15000], timeout: 120000 });
```
Do NOT check only existence (`length >= 1`). The MCRA controller needs time to create RoleBindings on target clusters.

### Cleanup Pattern

Always clean BEFORE and AFTER each test:
```typescript
// At start of test body:
await oc.mcraDeleteAllForUser(user);

// At end of test body (or afterEach):
await oc.mcraDeleteAllForUser(user);
```
- `before`: ensures retry starts clean even if previous afterEach failed
- `after`: leaves cluster clean for next test
- For debugging failures: use `npx playwright test --retries 0` and inspect screenshots/traces/error-context

---

## FG-RBAC Local Environment Setup

1. **Enable FG-RBAC:**
   ```bash
   oc patch mch multiclusterhub -n ocm --type merge -p '{"spec":{"overrides":{"components":[{"name":"fine-grained-rbac","enabled":true}]}}}'
   ```
2. **Create IDP + users:** `bash scripts/rbac/gen-rbac.sh` (set `RBAC_TEST_PASSWORD`, `VIRT_TIER=full`)
3. **Create MCRAs/placements:** `bash scripts/rbac/setup-test-roles.sh`
4. **Re-login as admin** after gen-rbac.sh (it leaves you logged in as the last test user)
5. **Set env vars:**
   ```bash
   export E2E_SKIP_MANAGED_KUBECONFIG_MERGE=true  # if spoke kubeconfig merge fails
   export E2E_SKIP_ANSIBLE_PREP=true               # if Ansible not configured
   ```
6. **Run:** `npx playwright test --project=fg-rbac --reporter=list`

Alternatively, `./start.sh fg-rbac` runs steps 2-6 automatically (requires full pipeline environment).

### Known: ACM Console Plugin 404 on First Navigation

ACM routes (`/multicloud/*`) may return 404 on the first browser navigation because the ACM console plugin loads after the OCP shell. The `toPass()` retry loops in specs handle this automatically by navigating fresh on each retry. This is expected OCP dynamic plugin behavior, not a bug.

---

## Fleet Virt CNV 4.22 Updates

Routes and selectors changed in CNV 4.22. Key breaking changes documented in `documentation/acm-components/virt/guides/CNV-422-SELECTOR-MAPPING.md`.

### Route Changes
| Route | Old | New (4.22) |
|-------|-----|------------|
| VM list | `/k8s/all-clusters/...` | `/fleet-virtualization/kubevirt.io~v1~VirtualMachine/all-clusters/all-namespaces` |
| VM details | `/k8s/cluster/:cluster/...` | `/fleet-virtualization/kubevirt.io~v1~VirtualMachine/cluster/:cluster/ns/:ns/:name` |

### New Tab Split
The VM list page now has two tabs: **Overview** (default) and **Virtual machines**. Tests must call `fleetVirtPage.gotoVmTab()` to reach the VM table. The Overview tab has cluster status skeletons that may never resolve for RBAC users with limited permissions.

---

## Style Rules

### Must Do

| Rule | Convention |
|------|-----------|
| Single test per scenario | One `test()` per Polarion ID |
| Centralize selectors | Constants files + page object `private readonly` locators |
| Text-based buttons | `page.getByRole('button', { name: 'Next' })` |
| Logical grouping | `test.step('Step description', async () => { ... })` |
| Condition-based waits | `expect(locator).toBeVisible()`, `locator.waitFor()` |
| Environment guards | `test.skip(condition, 'reason')` |
| Self-contained prerequisites | `test.beforeAll` creates resources via OcCliService methods; never assume cluster state |
| Setup/teardown in lib helpers | Move `beforeAll`/`afterAll` setup logic (resource creation, cleanup) into helper functions in `src/lib/{area}/`. Specs should NOT import `OcCliService` directly -- the helper encapsulates the service. Specs call `ensureResourceClean()` / `cleanupResource()` from the lib helper. This keeps specs focused on test intent, not backend orchestration. |
| Cleanup on retry | Clean BEFORE each test (ensures retry starts clean) AND AFTER each test (leaves cluster clean). Use `--retries 0` for failure debugging. |
| Path aliases | `@pages/`, `@services/`, `@fixtures/`, `@utils/` |
| Locator hierarchy | getByRole > getByLabel > getByText > getByTestId > locator |
| TypeScript | All files `.ts`, strict mode, no `any` |
| Page objects extend BasePage | `super(page)` only; implement `goto()` on the page class (BasePage has no `goto`) |
| Backend ops via OcCliService | Add domain-specific methods directly to `OcCliService` (prefix by resource: `mcra*`, `vm*`). Tests call named methods (e.g., `oc.mcraGetForUser()`), not raw CLI strings. `beforeAll`/`afterAll` hooks instantiate `new OcCliService()` at module scope. |

### Must NOT Do

| Anti-Pattern | Why |
|-------------|-----|
| Raw `oc.run()` or `OcCliService` import in specs | Specs must NOT import `OcCliService`. Move setup/teardown logic into lib helpers (`src/lib/{area}/`). The helper encapsulates the service; specs call exported functions like `ensureResourceClean()`. Test body uses fixture-injected `oc` for in-test operations only. |
| `.catch(() => {})` on single CLI commands | `--ignore-not-found` already handles the expected case. Adding `.catch(() => {})` silently hides real errors (permission denied, API down). Use `.catch` only for multi-step cleanup where partial completion is acceptable. Never double up both on the same call. |
| Legacy env var fallbacks (`OPTIONS_*`, etc.) | The console-e2e repo uses `HUB_PASSWORD`, `CONSOLE_USERNAME`, `CONSOLE_IDP`. Do NOT add fallbacks for env vars from other repos (e.g. `OPTIONS_HUB_PASSWORD` from clc-ui-e2e). Use only the vars documented in architecture-summary.md. |
| New abstraction for already-available data | Before creating any new getter, service method, or interface, verify each field or capability isn't already provided by existing code. Creating a new function that returns data already reachable through existing functions produces two sources of truth. Compose existing code instead. |
| Domain CLI logic in page objects | Page objects are for UI interaction. Domain CLI operations (label CRUD, resource lifecycle, multi-step backend flows) belong in `OcCliService` as named methods. Page objects may only wrap one-liner OcCliService calls (e.g., `oc.hasResourcesInCluster()`). |
| Direct `page.goto()` in test files | All navigation belongs in page object methods. For retry loops (`toPass()`), add a `navigateTo*()` variant on the PO that skips `waitForLoad()` and includes `.catch(() => {})`. Tests must never construct URLs. |
| Inline domain constants in spec files | Move API groups, resource names, policy names, cluster names to `constants/{area}.ts`. Only truly ephemeral test data (random values, test-specific label values) may stay in the spec. |
| Hardcoded column indices (`td.nth(N)`) | Fragile if columns reorder. Use `getCellByColumnHeader(row, 'Labels')` which resolves the column index from header text at runtime. |
| Selectors in test files | Fragile, duplicated -- use page object |
| Multiple unrelated tests per describe | Breaks Polarion mapping |
| `page.waitForTimeout(N)` | Forbidden by architecture doc. Use `expect(locator).toBeVisible()`, `expect().toPass()` with retry, `page.waitForURL()`, or `page.waitForLoadState()` |
| `page.reload()` in retry loops | Crashes if Chromium tab is dead. Use `page.goto(url).catch(() => {})` -- recreates navigation from scratch |
| CSS class selectors for assertions | Internal OCP/PF classes break across versions. Use role-based locators: `getByRole('heading')`, `getByRole('button')` |
| `not.toBeVisible()` for hidden checks | Use `toBeHidden()` instead -- more explicit and matches repo ESLint/convention |
| Clicking combobox `<input>` for PF6 dropdowns | Unreliable after other form interactions. Click the adjacent PF6 toggle button instead |
| Using `textContent()` for multi-element cells | Concatenates child text without spaces. Parse with regex or use `innerText()` |
| Assuming menu items without live verification | Actions menu items differ by RBAC role -- view users don't see Start/Stop/Restart |
| Assume UI text without MCP discovery | Text changes between versions |
| `test.only` | Breaks CI |
| Commit or push | User decides |
| Cross-domain page objects in fixtures | Area fixtures wire same-domain POs only. For cross-domain: `const s = await asUser(role); const po = new OtherDomainPage(s.page);` inline in the test. Coupling FG-RBAC fixture to Fleet Virt POs means a compile error in Fleet Virt breaks all RBAC tests. |
| Browser interaction in `services/` | Services are backend-only (no Playwright). RBAC login uses storageState from the setup project, not runtime browser context creation |
| Separate service files for CLI ops | Do NOT create `services/domains/` or separate service classes. Add domain-specific methods directly to `OcCliService`, prefixed by resource type (`mcra*`, `vm*`). |
| Duplicate selectors across files | Each selector lives in exactly ONE location. Large domains own their own constants file -- do NOT also add to `selectors.ts` |
| UI-based setup (wizard for test data) | Use OcCliService methods for backend setup |
| Raw `process.env` in tests | Use config layer or fixture |
| Relative imports (`../../`) | Use path aliases (`@pages/`, `@lib/`, `@services/`, etc.) |
| Complex assertions in page objects | Page objects expose locators; tests assert. Exceptions: `waitForLoad()`; `AcmTable.verifyRow*` (ESLint-whitelisted) |
| Methods or code for future tests | Every method, getter, fixture property, and constant must have a caller in the test being written NOW. Do not pre-build page object methods for wizard steps, tabs, or actions that the current test does not exercise. Even if the method is correct and will be needed by the next Polarion test case, it does not belong in this PR. Add it in the PR that adds the test that needs it. |
| Modifying existing code you are not working on | NEVER change existing functions, comments, or code that is not part of your implementation. Only add new code or modify code you are explicitly working on. Leave everything else untouched -- do not "improve" comments, rename variables, or refactor code that is not directly related to the task. |

---

## MCP Quick Reference

| Need | MCP / Tool |
|------|-----------|
| Test case steps | `polarion` -> `get_polarion_work_item`, `get_polarion_test_steps` |
| Story requirements | `jira` -> `get_issue` |
| UI components, source code | `acm-source` -> `search_code`, `get_component_source` |
| Wizard step structure | `acm-source` -> `get_wizard_steps` |
| UI text / labels | `acm-source` -> `search_translations` |
| Existing QE selectors | `acm-source` -> `get_acm_selectors('catalog', component)` |
| PF6 CSS selectors | `acm-source` -> `get_patternfly_selectors(component)` |
| Navigation routes | `acm-source` -> `get_routes` |
| Fleet Virt selectors | `acm-source` -> `get_fleet_virt_selectors` |
| Live page snapshot | `playwright` -> `browser_navigate`, `browser_snapshot` |
| Architecture dependencies | `neo4j-rhacm` -> `read_neo4j_cypher` |
| Live cluster resources (pods, policies, namespaces) | `acm-search` -> `find_resources`, `query_database` (on-cluster; if unavailable, fall back to `oc` CLI) |
| Managed cluster list and kubectl on spoke | `acm-kubectl` -> `clusters`, `kubectl`, `connect_cluster` |
| PR analysis | `gh` CLI: `gh pr view`, `gh pr diff` |
| Pipeline failures | `jenkins` -> `analyze_pipeline`, `get_test_results` |
| Polarion test case writing | `acm-test-case-generator` skill |
| JIRA operations | `jira` MCP -> `create_issue`, `edit_issue`, `add_comment` |

**Version management (always do first):**
```
set_acm_version('2.16')    # ACM Console version
set_cnv_version('4.20')    # Fleet Virt only -- match spoke CNV
list_repos()               # Verify active versions
```

---

## Skill File Structure

```
.claude/skills/acm-playwright-automation/
  SKILL.md                           # This file (orchestrator)
  agents/                            # Agent prompt templates
    requirements-extractor.md        # Phase 1: Polarion/JIRA/PR extraction
    ui-discovery.md                  # Phase 1: selectors, routes, translations
    pattern-analyzer.md              # Phase 1: existing code analysis
    code-quality-reviewer.md         # Phase 3.5: code review
    test-runner.md                   # Phase 4: test execution
    failure-debugger.md              # Phase 4.5: failure diagnosis
    migration-assistant.md           # Optional: Cypress-to-Playwright migration
  references/                        # Detailed docs (progressive disclosure)
    architecture-summary.md          # Agent-optimized console-e2e architecture
    phase-gates.md                   # Phase tracking format, gate rules
  framework/                         # Framework-specific patterns
    playwright-patterns.md           # Locators, fixtures, async/await, repo structure
```

**Knowledge base (shared, not in skill directory):**
```
.claude/knowledge/automation/playwright/
  app.md, rbac.md, clusters.md, fleet-virt.md, credentials.md,
  cluster-sets.md, search.md, automation-ansible.md, ecosystem-cim.md, hosted-clusters.md
```
