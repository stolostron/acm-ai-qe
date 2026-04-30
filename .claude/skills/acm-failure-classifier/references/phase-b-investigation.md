# Phase B: Investigation

## Investigation Dispatch

For each group (or individual test) from Phase A4, dispatch to the acm-cluster-investigator skill with:
- Test failure data (name, error, selector, extracted_context)
- cluster-diagnosis.json excerpt for the feature area
- Paths (kubeconfig, knowledge directory, repos)
- Feature area

## Tiered Playbook (B8)

Investigations escalate through tiers based on clarity of the failure:

### Tier 0: Extracted Context Only
Sufficient for clear cases:
- `console_search.found=false` with no recent changes -> AUTOMATION_BUG
- `hooks.afterAll.failed=true` with prior failure -> NO_BUG
- `assertion_analysis.has_data_assertion=true` with clear expected vs actual

### Tier 1: + MCP Selector Verification
When Tier 0 is ambiguous:
- Use acm-ui-source `search_code` to verify selector in official source
- Use acm-ui-source `search_translations` to verify UI text
- Use acm-ui-source `get_component_source` to read the component

### Tier 2: + Repo Code Reading
When MCP alone is insufficient:
- Read actual test code from repos/automation/
- Trace imports to page objects
- Read product component source from repos/console/

### Tier 3: + Backend Verification
When code reading doesn't resolve:
- `oc get` commands to check resource state
- `oc logs` for pod errors
- `oc exec` for data verification (psql, curl)
- Cross-reference UI state with backend state

### Tier 4: + Cross-System
For complex cases:
- acm-jira-client: search for known bugs matching the pattern
- acm-polarion-client: read test case expected behavior
- acm-neo4j-explorer: query component dependencies
- Knowledge graph subsystem analysis

## Backend Cross-Check (B7)

For every UI failure, verify whether the backend is healthy:
1. Identify the backend component for the failing UI element
2. Check pod health: `oc get pods -n <ns> | grep <component>`
3. If backend unhealthy -> the UI failure is caused by backend -> adjust routing

If backend confirms the test's expected behavior is correct but UI shows wrong data -> PRODUCT_BUG (UI transformation bug).

## Mandatory Root Cause Layer

Every classification MUST include:
- `root_cause_layer`: integer 1-12
- `root_cause_layer_name`: string (e.g., "Network / Connectivity", "UI / Rendering")

If no specific layer can be identified, use the layer where the symptom manifests and note the uncertainty.
