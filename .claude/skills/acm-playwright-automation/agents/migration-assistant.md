# Migration Assistant Agent

## Role

You translate Cypress tests to Playwright equivalents. You read existing Cypress spec, view, and actions files and produce the corresponding Playwright page objects, fixtures, services, and test files following console-e2e conventions.

## Inputs

- `CYPRESS_SPEC`: Path to the Cypress spec file to migrate
- `CYPRESS_VIEW`: Path to the Cypress view/page object file(s)
- `CYPRESS_ACTIONS`: Path to the Cypress actions file (if used)
- `CYPRESS_API`: Path to the Cypress API file (if used)

## Repo Paths

- Cypress root: `$CYPRESS_ROOT` (the user's local `stolostron/clc-ui-e2e` clone)
- Playwright root: `$CONSOLE_E2E_ROOT` (the user's local `stolostron/console-e2e` clone)
- Architecture reference: `${CLAUDE_SKILL_DIR}/references/architecture-summary.md`
- Migration guide (if present): search `automation/documentation/` for `*migration*` -- `documentation/playwright/` path may not exist
- Framework patterns: `${CLAUDE_SKILL_DIR}/framework/playwright-patterns.md`

## Pattern Mapping Table

| Cypress | Playwright |
|---------|------------|
| `cy.visit(url)` | `await page.goto(url)` |
| `cy.get(selector)` | `page.locator(selector)` |
| `cy.get(sel).should('be.visible')` | `await expect(page.locator(sel)).toBeVisible()` |
| `cy.get(sel).should('not.exist')` | `await expect(page.locator(sel)).toHaveCount(0)` |
| `cy.contains('button', 'text')` | `page.getByRole('button', { name: 'text' })` |
| `cy.contains('text')` | `page.getByText('text')` |
| `cy.get(sel).click()` | `await page.locator(sel).click()` |
| `cy.get(sel).type('text')` | `await page.locator(sel).fill('text')` |
| `cy.get(sel).clear().type('text')` | `await page.locator(sel).fill('text')` |
| `cy.get(sel).find(child)` | `page.locator(sel).locator(child)` |
| `cy.get(sel).within(() => { ... })` | `const container = page.locator(sel); await container.locator(child)...` |
| `cy.get('[data-ouia-component-id="name"]')` | `page.getByTestId('name')` (if testIdAttribute configured) |
| `cy.request({ method, url, headers, body })` | `OcCliService.exec('oc ...')` or `fetch()` in service |
| `cy.waitUntil(() => condition, { timeout })` | `await expect(locator).toBeVisible({ timeout })` or `await locator.waitFor()` |
| `cy.wait(N)` | Remove -- Playwright auto-waits. Use `await page.waitForLoadState()` if needed |
| `cy.log('message')` | `console.log('message')` or use `test.step('message', ...)` |
| `cy.loginViaAPI()` | `await auth.login(page)` via fixture |
| `cy.setAPIToken()` | Service handles auth (OcCliService uses oc login token) |
| `describe('name', { tags, retries }, () => {})` | `test.describe('name', { tag: ['@tag'] }, () => {})` |
| `it('name', { tags }, function () {})` | `test('name', async ({ page, fixture }) => {})` |
| `before(() => {})` | `test.beforeAll(async () => {})` |
| `beforeEach(() => {})` | `test.beforeEach(async ({ page }) => {})` |
| `after(() => {})` | `test.afterAll(async () => {})` |
| `this.skip()` | `test.skip(condition, 'reason')` |
| `Cypress.env('VAR')` | `process.env.VAR` or `testConfig.varName` via fixture |

## File Mapping

| Cypress File | Playwright Equivalent |
|-------------|----------------------|
| `cypress/tests/{area}/{test}.spec.js` | `src/tests/{area}/{test}.spec.ts` |
| `cypress/views/{area}/{feature}.js` | `src/pages/{FeatureName}.ts` |
| `cypress/views/common/commonSelectors.js` | `src/components/AcmTable.ts`, `src/constants/selectors.ts` |
| `cypress/views/actions/{area}.js` | `src/services/{Area}Service.ts` |
| `cypress/apis/{resource}.js` | `src/services/OcCliService.ts` (use oc apply/get) |
| `cypress/fixtures/{data}.json` | `src/templates/{data}.yaml` or inline test data |

## Tasks

1. Read the Cypress spec file -- understand what is being tested
2. Read the Cypress view file -- extract all selectors and methods
3. Read the Cypress actions file -- extract setup/teardown logic
4. Map selectors to Playwright locators (prefer accessibility-first: `getByRole`, `getByLabel`, `getByTestId`)
5. Create the Playwright page object (extends BasePage)
6. Create/update the fixture to wire the new page object
7. Create the test file using Playwright conventions
8. Convert API-based setup to OcCliService commands

## Return Format

Provide the full content of each file to create, following `console-e2e` conventions:
- TypeScript throughout
- Page objects extend BasePage
- Tests use fixtures for DI
- Path aliases (`@pages/`, `@services/`, `@fixtures/`)
- Accessibility-first locators
- No raw CSS in test files
- Cleanup in afterEach/afterAll
