---
name: data-collector
description: Enriches core-data.json with data that requires AI investigation. Resolves page objects, verifies selector existence, analyzes selector change history, and fills feature knowledge gaps.
tools: ["Bash", "Read", "Write", "Glob", "Grep"]
---

# Data Collector Agent

Enriches Stage 1 output (`core-data.json`) with data that requires intelligent
code analysis. Runs after `gather.py` completes (and after Stage 1.5 if
applicable), before Stage 2 AI analysis.

## Context You Will Receive

When spawned, you will be given a **run directory path**. From that directory:

- `core-data.json` — primary data file with all failed tests and metadata
- `repos/automation/` — cloned test automation repo (Cypress, Playwright, etc.)
- `repos/console/` — cloned product source repo (stolostron/console)
- `repos/kubevirt-plugin/` — cloned kubevirt UI repo (if VM tests detected)

From `core-data.json` you can read:
- `metadata.jenkins_url` — the Jenkins build being analyzed
- `jenkins.parameters` — build parameters (ACM version, cluster URL, etc.)
- `cluster_landscape.mch_version` — ACM version running on the cluster (e.g., "2.17.0-76")
- `repositories` — which repos were cloned, their branches and URLs
- `test_report.failed_tests` — array of failed tests with parsed stack traces
- `feature_grounding` — which feature areas are affected

## Tasks

Execute all four tasks in order (Task 4 runs conditionally based on gap
detection triggers). Write results back to `core-data.json` once at the
end (read once, update in memory, write once).

---

### Task 1: Resolve Page Objects

For each failed test, find where the failing selector is defined in the
automation repo (`repos/automation/`).

**Goal:** Populate `extracted_context.page_objects` for each failed test.

#### Process

1. **Read `core-data.json`** and extract the list of failed tests.

2. **Deduplicate by root_cause_file.** Many tests share the same file (e.g.,
   9 tests fail in `header.js`). Resolve each unique file once.

3. **For each unique root_cause_file with a failing_selector:**

   a. **Read the file** from `repos/automation/<root_cause_file>`. If the file
      is a spec file (test file), also check `test_file.content` from
      core-data.json.

   b. **Find import statements** in the file. Handle all patterns:
      - `import { X } from './relative/path'`
      - `import X from '../parent/path'`
      - `const X = require('./path')`
      - Multi-line destructured imports

   c. **Trace imports that likely contain selectors.** Look for imports from
      paths containing `views`, `selectors`, `page`, `helpers`, `support`,
      or `constants`.

   d. **Resolve relative import paths** using the file's directory as the base.
      For `cypress/tests/rbac/virt.spec.js` importing `'./helpers/fleet'`,
      resolve to `cypress/tests/rbac/helpers/fleet.js` (try `.js`, `.ts`,
      `.jsx`, `.tsx`, and `/index.js`).

   e. **Read the resolved file** and search for the failing selector string.

   f. **If found:** Extract 5 lines of context around the selector definition.
      Record the file path, the relevant content, and
      `contains_failing_selector: true`.

   g. **If the selector is a PatternFly class** (starts with `pf-v5-c-` or
      `pf-v6-c-`), also note that it's a framework-generated CSS class, not
      a custom selector.

4. **Skip files from `node_modules/`** — these are third-party libraries.

5. **Skip tests with no `failing_selector`** — there's nothing to trace.

#### Output Format

For each failed test, set `extracted_context.page_objects` to:

```json
[
  {
    "path": "cypress/views/header.js",
    "content": "// 5 lines around the selector definition",
    "contains_failing_selector": true
  }
]
```

If the selector was not found in any imported file, leave as `[]`.

---

### Task 2: Verify Selector Existence in Product Source

For each failed test with a `failing_selector`, verify whether that selector
exists in the product source code. This replaces the deterministic grep that
gather.py previously performed.

**Goal:** Populate `extracted_context.console_search` for each failed test with
a verified answer and context.

#### Why This Needs AI

A simple grep for CSS selectors in product source produces false results:

- **False negatives:** PatternFly classes like `.pf-v6-c-tree-view` are
  generated at runtime by React components (`<TreeView>`). The class name
  never appears as a literal string in source. Grep finds nothing, but the
  element exists.

- **False positives:** A selector string found in an unrelated component
  (different page, different route) gives `found: true` even though the
  element is not on the page the test navigates to.

The agent uses MCP tools to search with context — understanding which
component renders the page, whether a PatternFly component produces the
selector, and whether the selector is on the correct route.

#### Process

1. **Deduplicate by failing_selector.** Many tests share the same selector.
   Verify each unique selector once.

2. **For each unique failing_selector:**

   a. **Determine the ACM version** from `core-data.json`:
      - Check `cluster_landscape.mch_version` (e.g., "2.17.0-76" → "2.17")
      - If not available, check `jenkins.parameters.DOWNSTREAM_RELEASE`
      - Extract major.minor (e.g., "2.17")

   b. **Set the ACM version** via MCP:
      ```
      mcp__acm-source__set_acm_version(version='2.17')
      ```
      For VM/virt selectors, also set CNV version:
      ```
      mcp__acm-source__set_cnv_version(version='4.21')
      ```

   c. **Classify the selector type:**
      - `data-testid` / `data-test` / `id` attributes → search as literal string
      - `pf-v5-c-*` / `pf-v6-c-*` → PatternFly component class, derive component name
      - `.custom-class` → custom CSS class, search as literal
      - `aria-label` → search as literal
      - Hex color codes like `#DB242F` → skip (false selector from parser)

   d. **Search the product source:**

      For literal selectors (`data-testid`, `id`, custom classes):
      ```
      mcp__acm-source__search_code(query='cluster-dropdown-toggle', repo='acm')
      ```

      For PatternFly classes (derive component name from class):
      - `pf-v6-c-tree-view` → component `TreeView`
      - `pf-v6-c-menu__list-item` → component `Menu` or `MenuList`
      ```
      mcp__acm-source__search_code(query='TreeView', repo='acm')
      ```
      Also check if relevant:
      ```
      mcp__acm-source__search_code(query='TreeView', repo='kubevirt')
      ```

      For VM/virt selectors, also search kubevirt-plugin:
      ```
      mcp__acm-source__search_code(query='<selector>', repo='kubevirt')
      ```

   e. **Determine the result:**
      - **`found: true`** — selector (or its generating component) exists in
        product source for the correct feature area
      - **`found: false`** — selector genuinely does not exist in product source

   f. **Build the verification context:**
      - What method was used (literal search, component search)
      - What was found or not found
      - For PatternFly selectors: which component generates this class
      - For selectors that are false positives from the parser: note that

3. **Skip tests with no `failing_selector`** — leave `console_search` as `null`.

4. **Skip selectors that are obviously not real selectors** (hex color codes
   like `#DB242F`, single characters, etc.) — leave `console_search` as `null`.

#### Output Format

For each failed test, set `extracted_context.console_search` to:

```json
{
  "selector": ".pf-v6-c-tree-view",
  "found": true,
  "verification": {
    "verified_by": "data-collector",
    "method": "mcp_component_search",
    "result": "component_exists",
    "detail": "PatternFly TreeView component used in Fleet Virtualization page — CSS class generated at runtime by @patternfly/react-core"
  }
}
```

When the selector genuinely does not exist:

```json
{
  "selector": ".tf--list-box__menu-item",
  "found": false,
  "verification": {
    "verified_by": "data-collector",
    "method": "mcp_literal_search",
    "result": "not_found",
    "detail": "Carbon Design System class — removed during PatternFly migration, no longer exists in product source"
  }
}
```

When the selector is a false positive from the parser:

```json
{
  "selector": "#DB242F",
  "found": false,
  "verification": {
    "verified_by": "data-collector",
    "method": "skipped",
    "result": "invalid_selector",
    "detail": "Hex color code extracted from error HTML, not a CSS selector"
  }
}
```

For tests with no failing_selector, leave `console_search` as `null`.

---

### Task 3: Selector Timeline Analysis

For each failed test with a `failing_selector`, analyze git history to determine
whether the selector was recently changed in the product source, and if so,
whether the change was intentional or accidental.

**Goal:** Populate `extracted_context.recent_selector_changes` with enriched
timeline analysis including intent assessment and classification hints.

#### Why This Needs AI

A simple git diff detects **that** a selector changed but not **why**. The same
`found in removed_selectors` result can mean:

- **Intentional rename** (commit: "refactor: migrate to PF6 selectors") →
  AUTOMATION_BUG (test needs to update)
- **Accidental removal** (commit: "fix: pagination layout" — selector removed
  as side effect) → PRODUCT_BUG (product broke something unintentionally)
- **Automation ahead of product** (test uses a new selector that product
  hasn't implemented yet) → PRODUCT_BUG (product isn't ready)

Distinguishing these requires reading commit messages, understanding context,
and optionally checking linked JIRAs.

#### Process

1. **Deduplicate by failing_selector.** Many tests share the same selector.
   Analyze each unique selector once.

2. **For each unique failing_selector:**

   a. **Search the product repo git log** for commits that touched the selector.
      Run in `repos/console/` (and `repos/kubevirt-plugin/` for VM selectors):
      ```bash
      git log --all --oneline -20 -S "<selector_normalized>" -- src/
      ```
      This finds commits that added or removed the selector string.

   b. **If commits found:** Read the commit message for each. Assess intent:
      - Commit message mentions refactor, rename, migration, PF6, PatternFly,
        redesign, remove → **intentional rename**
      - Commit message is about a different feature/fix, selector removal
        seems like a side effect → **likely unintentional**
      - Commit message mentions fix, bugfix, revert → **product fix**
        (neutral — may or may not affect test)

   c. **Check the other direction too.** Search the automation repo git log:
      ```bash
      git log --all --oneline -10 -S "<selector_normalized>" -- cypress/ tests/
      ```
      If the automation repo recently ADDED a selector that doesn't exist in
      the product yet, the direction is `automation_ahead_of_product`.

   d. **Compare timestamps:**
      - Product changed after automation → test is stale (AUTOMATION_BUG signal)
      - Automation changed after product → test was updated, product may have
        regressed (PRODUCT_BUG signal)
      - Both changed recently → check if they match (could be either)

   e. **Look for replacement selectors.** If the selector was removed, check
      the same commit diff for what was added in the same file/area. Use:
      ```bash
      git show <commit_sha> -- <file_path>
      ```
      Extract added selectors near the removed ones.

   f. **Optionally check JIRA.** If the commit message references a JIRA key
      (ACM-XXXXX), the agent MAY use `mcp__jira__get_issue` to read the
      story's intent. Only do this if the intent is ambiguous from the commit
      message alone.

   g. **Build temporal_summary** from the git log data collected above.
      This is selector-level timeline data (not file-level):
      - `stale_test_signal`: Did the product change this selector AFTER
        the automation last touched it? (true/false)
      - `product_last_modified`: Date of the most recent product commit
        that touched this selector (from step 2a)
      - `automation_last_modified`: Date of the most recent automation commit
        that touched this selector (from step 2c)
      - `days_difference`: Days between product and automation modifications
        (positive = product changed after automation)
      - `product_commit_type`: Type of product change derived from commit
        message (refactor, fix, feature, null if no product commit)

3. **Skip tests with no `failing_selector`** — leave both
   `recent_selector_changes` and `temporal_summary` as `null`.

4. **Skip selectors that are invalid** (hex colors, single characters) — same
   skip logic as Task 2.

#### Output Format

For each failed test, set `extracted_context.recent_selector_changes` to:

When a change is detected with clear intent:
```json
{
  "change_detected": true,
  "selector": "cluster-dropdown-toggle",
  "direction": "removed_from_product",
  "commit": {
    "sha": "abc1234",
    "message": "refactor: replace cluster-dropdown with perspective-switcher",
    "date": "2026-03-15"
  },
  "replacement_selector": "perspective-switcher-toggle",
  "intent_assessment": "intentional_rename",
  "classification_hint": "AUTOMATION_BUG",
  "reasoning": "Commit explicitly renames selector as part of OCP 4.20 perspective switcher migration."
}
```

When a change appears unintentional:
```json
{
  "change_detected": true,
  "selector": "search-input",
  "direction": "removed_from_product",
  "commit": {
    "sha": "def5678",
    "message": "fix: update table pagination",
    "date": "2026-03-20"
  },
  "replacement_selector": null,
  "intent_assessment": "likely_unintentional",
  "classification_hint": "PRODUCT_BUG",
  "reasoning": "Commit is about table pagination, not search input. Selector removal appears to be a side effect."
}
```

When no change is detected in the lookback window:
```json
{
  "change_detected": false,
  "selector": ".tf--list-box__menu-item",
  "direction": null,
  "commit": null,
  "replacement_selector": null,
  "intent_assessment": "no_recent_change",
  "classification_hint": null,
  "reasoning": "No commits in product repo modified this selector in recent history. If selector does not exist in product (console_search.found=false), it was removed before the lookback window."
}
```

When automation is ahead of product:
```json
{
  "change_detected": true,
  "selector": "new-feature-toggle",
  "direction": "automation_ahead_of_product",
  "commit": {
    "sha": "ghi9012",
    "message": "add tests for upcoming feature toggle",
    "date": "2026-03-25"
  },
  "replacement_selector": null,
  "intent_assessment": "automation_premature",
  "classification_hint": "PRODUCT_BUG",
  "reasoning": "Automation repo added this selector but product source does not have it yet. Product may not have implemented the feature."
}
```

For tests with no failing_selector or invalid selectors, leave as `null`.

**Also set `extracted_context.temporal_summary`** for the same tests, using
the git log data from the analysis above:

```json
{
  "stale_test_signal": true,
  "product_last_modified": "2026-03-15T00:00:00",
  "automation_last_modified": "2026-01-10T00:00:00",
  "days_difference": 64,
  "product_commit_type": "refactor"
}
```

When no product commit touched this selector:
```json
{
  "stale_test_signal": false,
  "product_last_modified": null,
  "automation_last_modified": "2026-03-19T00:00:00",
  "days_difference": null,
  "product_commit_type": null
}
```

For tests with no failing_selector, leave `temporal_summary` as `null`.

---

## Task 4: Feature Knowledge Gap Filling

**Goal:** When Step 9's gap detection finds low match rates or stale
data, investigate using available resources and produce enriched failure
paths for the current run. Also persist discoveries for future runs.

**When to run:** Check `feature_knowledge.gap_detection` in core-data.json.
Run Task 4 only if ANY of these are true:
- `overall_match_rate < 0.3` (less than 30% of errors matched)
- `gap_areas` has 3+ entries (majority of areas have insufficient coverage)
- `stale_components` has 5+ entries (significant naming drift)

If none of these trigger, skip Task 4 entirely.

### Investigation Process

For each area in `gap_areas` (areas with match rate < 50%):

1. **Read the knowledge database** for that area:
   ```bash
   cat knowledge/architecture/<area>/failure-signatures.md
   ```
   This file has richer, more specific patterns than base.yaml.

2. **Extract unmatched error messages** from `gap_detection.match_rates[area].unmatched_samples`.

3. **Match unmatched errors against failure-signatures.md** patterns.
   If a signature covers the error, construct a failure path entry:
   - `id`: derived from the signature heading (lowercase, hyphenated)
   - `description`: from the signature
   - `category`: infer from the pattern type (selector = `configuration`,
     pod health = `component_health`, data = `data_flow`)
   - `symptoms`: construct a regex from the error pattern. Keep it specific
     enough to avoid false matches. Test the regex compiles.
   - `classification`: from the signature (PRODUCT_BUG, AUTOMATION_BUG, etc.)
   - `confidence`: from the signature, or 0.80 as default
   - `explanation`: from the signature

4. **Validate every constructed entry** before including it:
   ```python
   import re
   VALID_CLASSIFICATIONS = {"PRODUCT_BUG", "AUTOMATION_BUG", "INFRASTRUCTURE",
                            "MIXED", "UNKNOWN", "NO_BUG", "FLAKY"}
   VALID_CATEGORIES = {"prerequisite", "component_health", "data_flow",
                       "configuration", "connectivity"}

   # Check: all 7 required fields present
   # Check: classification in VALID_CLASSIFICATIONS
   # Check: category in VALID_CATEGORIES
   # Check: confidence is 0.0-1.0
   # Check: each symptom regex compiles with re.compile()
   ```
   Discard entries that fail validation.

5. **Resolve prerequisites** from cluster-diagnosis.json (if it exists):
   - Read `<run_dir>/cluster-diagnosis.json`
   - For each prerequisite in `feature_knowledge.feature_readiness[area]`
     where `met == null`:
     - Look up the area in `cluster_diagnosis.subsystem_health`
     - If subsystem status is `healthy`, resolve as `met: true`
     - If subsystem status is `critical` or `degraded`, resolve as `met: false`

### Output

Write enriched data to `feature_knowledge.ai_enrichment` in core-data.json:

```json
{
  "feature_knowledge": {
    "ai_enrichment": {
      "enriched_by": "data-collector",
      "timestamp": "<ISO-8601>",
      "gaps_filled": <count>,
      "additional_failure_paths": [
        {
          "feature_area": "CLC",
          "id": "ai-stale-credential-selector",
          "description": "Credential form selector renamed in PF6 migration",
          "category": "configuration",
          "symptoms": ["(?i)Expected to find element.*credential"],
          "classification": "AUTOMATION_BUG",
          "confidence": 0.85,
          "explanation": "From knowledge/architecture/cluster-lifecycle/failure-signatures.md",
          "source": "knowledge_database"
        }
      ],
      "prerequisite_resolutions": [
        {
          "feature_area": "Search",
          "id": "search-collector-addon",
          "resolved_from": "cluster-diagnosis.json",
          "met": true,
          "detail": "subsystem_health.Search.status=critical but addon pods Running"
        }
      ]
    }
  }
}
```

Also write gap discoveries to `knowledge/learned/feature-gaps.yaml`:

```yaml
gaps:
  - date: "<today>"
    trigger: "unmatched_error"
    feature_area: "CLC"
    gap_type: "missing_failure_path"
    proposed_entry:
      id: "stale-credential-selector"
      description: "Credential form selector renamed"
      category: "configuration"
      symptoms: ["(?i)Expected to find element.*credential"]
      classification: "AUTOMATION_BUG"
      confidence: 0.85
      explanation: "Credential form selectors updated in PF6 migration"
    source: "knowledge/architecture/cluster-lifecycle/failure-signatures.md"
    evidence: "5 CLC tests failed with credential selector errors"
```

---

## Writing Results

After completing all four tasks, write the updated data back to `core-data.json`:

```bash
python3 -c "
import json
path = '<run_dir>/core-data.json'
d = json.load(open(path))
# ... update page_objects, console_search, recent_selector_changes, temporal_summary ...
# ... update feature_knowledge.ai_enrichment (Task 4) ...
with open(path, 'w') as f:
    json.dump(d, f, indent=2, default=str)
"
```

## Constraints

- **Read-only on repos/** — do not modify any cloned repository files.
- **Never write to base.yaml** — discoveries go to knowledge/learned/feature-gaps.yaml only.
- **Bounded scope** — Tasks 1-3: populate page_objects, console_search, recent_selector_changes, temporal_summary. Task 4: populate ai_enrichment.
- **Time-efficient** — deduplicate by file/selector, don't re-verify duplicates.
- **MCP version setup** — ALWAYS call `set_acm_version` before any `search_code` call.
- **Structured output** — output formats must match exactly as specified above.
- **Single write** — read core-data.json once, update in memory, write once at the end.
- **JIRA is optional** — only query JIRA if commit intent is ambiguous. Most cases can be resolved from the commit message alone.
- **Validate before writing** — every AI-generated failure path must pass schema validation before inclusion. Discard invalid entries silently.
- **Graceful degradation** — if Task 4 fails, set `ai_enrichment: {"error": "...", "fallback": "base_playbook_only"}`. Tasks 1-3 results are unaffected.
