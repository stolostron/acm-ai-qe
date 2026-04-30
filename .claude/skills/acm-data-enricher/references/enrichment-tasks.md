# Data Enrichment Tasks -- Detailed Reference

## Task 1: Resolve Page Objects

### Process
1. Read `core-data.json`, extract failed tests list
2. Deduplicate by `root_cause_file` -- many tests share the same file
3. For each unique `root_cause_file` with a `failing_selector`:
   a. Read the file from `repos/automation/<root_cause_file>`
   b. Find import statements (ES6 imports, require, multi-line destructured)
   c. Trace imports from paths containing `views`, `selectors`, `page`, `helpers`, `support`, `constants`
   d. Resolve relative import paths using the file's directory as base (try .js, .ts, .jsx, .tsx, /index.js)
   e. Read resolved files, search for the failing selector string
   f. If found: extract 5 lines of context, record `contains_failing_selector: true`
   g. If PatternFly class (pf-v5-c-*, pf-v6-c-*): note it's framework-generated

### Skip conditions
- No `failing_selector` on the test
- Files from `node_modules/`

### Output format per test
```json
{"extracted_context": {"page_objects": [{"path": "cypress/views/header.js", "content": "...", "contains_failing_selector": true}]}}
```

---

## Task 2: Verify Selector Existence

### Process
1. Deduplicate by `failing_selector`
2. Determine ACM version from `cluster_landscape.mch_version` (extract major.minor)
3. Set ACM version via acm-ui-source skill
4. Classify selector type:
   - `data-testid` / `data-test` / `id` -> search as literal string
   - `pf-v5-c-*` / `pf-v6-c-*` -> derive PatternFly component name, search for component
   - `.custom-class` -> search as literal
   - Hex colors like `#DB242F` -> skip (false selector from parser)
5. Search product source via acm-ui-source `search_code`
6. For VM/virt selectors: also search `repo="kubevirt"`

### Result values
- `found: true` -- selector or its generating component exists for correct feature area
- `found: false` -- genuinely does not exist
- `found: false, method: "skipped", result: "invalid_selector"` -- hex color, single char, etc.

---

## Task 3: Selector Timeline Analysis

### Process
1. Deduplicate by `failing_selector`
2. Search product repo git log: `git log --all --oneline -20 -S "<selector>" -- src/`
3. If commits found: assess intent from commit message:
   - refactor/rename/migration/PF6/redesign/remove -> **intentional_rename** -> AUTOMATION_BUG signal
   - different feature/fix, side-effect removal -> **likely_unintentional** -> PRODUCT_BUG signal
   - fix/bugfix/revert -> **product_fix** (neutral)
4. Search automation repo too: `git log --all --oneline -10 -S "<selector>" -- cypress/ tests/`
5. Compare timestamps (product vs automation last modified)
6. Look for replacement selectors in the same commit diff
7. Build `temporal_summary`: stale_test_signal, product_last_modified, automation_last_modified, days_difference, product_commit_type

### Intent classification values
- `intentional_rename` -> AUTOMATION_BUG hint
- `likely_unintentional` -> PRODUCT_BUG hint
- `automation_premature` -> PRODUCT_BUG hint (test ahead of product)
- `no_recent_change` -> null hint

---

## Task 4: Feature Knowledge Gap Filling

### Trigger conditions (ALL must be checked)
- `overall_match_rate < 0.3` OR
- `gap_areas` has 3+ entries OR
- `stale_components` has 5+ entries

If none trigger, skip Task 4 entirely.

### Process
1. For each area in `gap_areas` (match rate < 50%):
   a. Read `knowledge/architecture/<area>/failure-signatures.md`
   b. Extract unmatched error messages from `gap_detection.match_rates[area].unmatched_samples`
   c. Match against failure-signatures.md patterns
   d. Construct failure path entries (id, description, category, symptoms regex, classification, confidence, explanation)
   e. Validate every entry: all 7 fields present, valid classification, valid category, confidence 0.0-1.0, regex compiles
   f. Discard invalid entries
2. Resolve prerequisites from `cluster-diagnosis.json` if it exists
3. Write to `feature_knowledge.ai_enrichment` in core-data.json
4. Write discoveries to `knowledge/learned/feature-gaps.yaml`

### Valid values
- Classifications: PRODUCT_BUG, AUTOMATION_BUG, INFRASTRUCTURE, MIXED, UNKNOWN, NO_BUG, FLAKY
- Categories: prerequisite, component_health, data_flow, configuration, connectivity
