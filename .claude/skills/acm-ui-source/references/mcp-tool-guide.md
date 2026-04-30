# ACM UI MCP Tool Reference

## Search Strategies

### Finding a component by name
```
search_code("PolicyTemplateDetails", repo="acm")
search_component("PolicyTemplateDetails", repo="acm")
```
`search_code` finds files containing the string. `search_component` finds React component definitions.

### Reading full source
```
get_component_source("frontend/src/routes/Governance/policies/policy-details/PolicyTemplateDetail/PolicyTemplateDetails.tsx", repo="acm")
```
Always read the FULL source of key components, not just snippets. Context matters for understanding conditional rendering, state management, and field ordering.

### Finding UI text (translations)
```
search_translations("Labels")              -- partial match, returns all containing "Labels"
search_translations("table.labels", exact=true)  -- exact key match
```
Translation keys are defined in `frontend/public/locales/en/translation.json`. The `t('key')` function in source code maps to these translations.

### Discovering routes
```
get_routes()                    -- all 117 ACM Console routes
get_route_component("policyTemplateDetails")  -- which component renders this route
```
Routes are defined in `frontend/src/NavigationPath.tsx`.

### Finding selectors for automation
```
find_test_ids("frontend/src/routes/Governance/policies/...", repo="acm")   -- data-test attributes in source
get_acm_selectors(source="acm", component="governance")                    -- existing QE selectors
get_patternfly_selectors("Table")                                           -- PF6 CSS class selectors
```

### Analyzing wizard structure
```
get_wizard_steps("frontend/src/routes/Infrastructure/Clusters/...", repo="acm")
```
Returns step names, order, and validation rules for multi-step wizards.

## Common Patterns

### Verify a filtering function
1. `search_code("functionName", repo="acm")` -- find where it's defined
2. `get_component_source("path/to/utils.ts", repo="acm")` -- read the full function
3. Extract exact filter conditions from the source code (string comparisons, `startsWith`, regex)

### Verify field order in a description list
1. Find the component that renders the description list
2. `get_component_source(path)` -- read full source
3. Look for the array construction (`useMemo`, `cols`, `descriptionItems`)
4. Note the order of `push()` calls and array construction

### Verify a route exists
1. `get_routes()` -- get all routes
2. Search for the specific route key or URL pattern
3. Note the full parameterized path and any optional parameters (`:param?`)
