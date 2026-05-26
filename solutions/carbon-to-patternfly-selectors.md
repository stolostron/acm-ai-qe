---
title: E2E test failures from stale Carbon Design System selectors
symptom: "Timed out retrying: Expected to find element: .tf--list-box__menu-item"
keywords: [Carbon, tf--, PatternFly, pf-v6, selector, migration, Timed out, element not found, console]
affected_versions: "ACM 2.12+"
last_verified: 2026-05-26
status: active
---

## Symptom

Cypress or Playwright E2E tests fail with timeout errors on selectors starting with `.tf--` (e.g., `.tf--list-box__menu-item`, `.tf--dropdown`, `.tf--combo-box`). Multiple search or console tests fail simultaneously with "element not found" errors.

## Root Cause

ACM Console migrated from Carbon Design System to PatternFly in 2023. Selectors starting with `.tf--` are from the pre-PatternFly era and no longer exist in the DOM. The automation code was not updated after the migration.

Evidence: `console_search.found = false`, automation file last modified in 2022.

## Fix

Replace Carbon selectors with PatternFly equivalents:

| Carbon Selector | PatternFly Replacement |
|----------------|----------------------|
| `.tf--list-box__menu-item` | `.pf-v6-c-menu__list-item` |
| `.tf--dropdown` | `.pf-v6-c-select` |
| `.tf--combo-box` | `.pf-v6-c-select__toggle` |
| `.tf--text-input` | `.pf-v6-c-form-control input` |

Use the ACM Source MCP server (`search_test_ids`, `search_selectors`) to find the current selectors in the console source code.

Related: OCP 4.20+ replaced `[data-test-id="cluster-dropdown-toggle"]` with `[data-test-id="perspective-switcher-toggle"]` in the header.

## References

- Knowledge DB: `.claude/knowledge/failures/search/failure-signatures.md` (Carbon Design System Selector)
- Classification: AUTOMATION_BUG (95% confidence)
