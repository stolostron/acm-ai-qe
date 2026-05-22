# Application Lifecycle (ALC) — Playwright Knowledge

Domain knowledge for ALC / Applications list tests in `console-e2e`.

> **As-built (May 2026):** `src/tests/app/applications-list.spec.ts` (~534 lines, 16 `test()` blocks, tags `@app` `@alc`). Fixture: `@fixtures/app-test`. Project: `--project app` (not `chromium`). Page: `ApplicationListPage`. Component: `ApplicationsTable` extends `AcmTable`. Constants: `src/constants/app.ts`. No Polarion IDs or `test.step()` in this file — multi-scenario sanity pattern.

---

## Playwright paths

| Item | Path |
|------|------|
| Spec | `src/tests/app/applications-list.spec.ts` |
| Fixture | `src/fixtures/app-test.ts` |
| Page | `src/pages/app/ApplicationListPage.ts` |
| Component | `src/components/app/ApplicationsTable.ts` |
| Constants | `src/constants/app.ts` |
| Runner | `./start.sh alc` → `src/tests/app/start.sh` (pass `--project app`) |

---

## Route

`/multicloud/applications` — `APP_ROUTES.list` in `constants/app.ts`

---

## Cypress reference (legacy)

ALC Cypress automation may live in `clc-ui-e2e` / `acmqe-autotest` Jenkins jobs. Use Cypress docs only for domain concepts; implement in Playwright paths above.
