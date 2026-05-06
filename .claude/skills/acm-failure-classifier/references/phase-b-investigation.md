# Phase B: Investigation

## Investigation Dispatch

For each group (or individual test) from Phase A4, dispatch to the acm-cluster-investigator skill with:
- Test failure data (name, error, selector, extracted_context)
- cluster-diagnosis.json excerpt for the feature area
- Paths (kubeconfig, knowledge directory, repos)
- Feature area

## B1: Extracted Context Analysis

Questions to answer for each test:
- What does the test do? (read `test_file.content`)
- Is the failing selector defined correctly? (check `page_objects`)
- Does the selector exist in the product? (`console_search.found`)
- What does the verification say? (`console_search.verification.detail`)
- Is this a data-level failure? (check `assertion_analysis.has_data_assertion` and `failure_mode_category`)
- If `failure_mode_category == 'data_incorrect'`: the page rendered but showed wrong data -- focus on the backend API data path, NOT selectors

## B3b: External Service Dependencies

When subscription/channel tests fail with timeouts, check Jenkins parameters for external service URLs:
- `OBJECTSTORE_PRIVATE_URL` -- Minio/S3 endpoint for Object Storage channel tests
- `TOWER_HOST` -- Ansible Tower/AAP endpoint for pre/post hook tests
- Git repo URLs in test setup -- External Gogs servers for Git channel tests

**Console log patterns indicating external service failure:**
- `"failed to push to testrepo"` -- Gogs Git server down or inaccessible
- `"SSL certificate problem"` -- Certificate issue with external service (Gogs mTLS)
- `"minio.*connection refused"` or `"objectstore.*fail"` -- Minio/S3 server down
- `"tower.*unreachable"` or `"ansible.*connection refused"` -- Tower/AAP endpoint down

**Decision logic:**
1. Object Storage tests timeout AND objectstore/minio connection errors: **INFRASTRUCTURE**
2. Git subscription tests fail at setup AND "failed to push to testrepo": **INFRASTRUCTURE**
3. Ansible tests show CreateContainerConfigError AND AAP version >= 2.5: check `version-constraints.yaml` -- may be **PRODUCT_BUG** (compatibility gap)
4. Subscription tests timeout with no external service evidence: check `failure-patterns.yaml` for ACM-32244 (timestamp reconciliation)

## MCP Tool Trigger Matrix

**Set correct versions first:** Before any MCP queries, call `set_acm_version()` with the ACM version from `cluster_landscape.mch_version`. For VM tests, call `detect_cnv_version()`.

| Trigger Condition | MCP Tool | Query |
|---|---|---|
| Start of investigation | `set_acm_version` | Set to latest GA version |
| VM test failure | `detect_cnv_version` | Auto-sets kubevirt branch |
| Selector not found | `get_acm_selectors` | `get_acm_selectors('catalog', '<component>')` |
| Cross-repo search needed | `search_code` | `search_code('<selector>', 'acm')` |
| Exact file lookup | `find_test_ids` | `find_test_ids('path/to/file.tsx', 'acm')` |
| Verify UI text | `search_translations` | `search_translations('Create cluster')` |
| Understand wizard flow | `get_wizard_steps` | `get_wizard_steps('path/wizard.tsx', 'acm')` |
| PatternFly fallback | `get_patternfly_selectors` | `get_patternfly_selectors('button')` |
| Component in error | `read_neo4j_cypher` | Cypher query for dependencies |
| Need live cluster resources | `find_resources` | Search pods/deployments across clusters |
| Need fleet-wide stats | `query_database` | SQL against ACM Search PostgreSQL |
| Need managed cluster list | `clusters` | List all managed clusters |
| Need spoke cluster data | `kubectl` | `kubectl(command="kubectl get pods -n <ns>", cluster="<spoke>")` |
| Path B2: Polarion ID found | `search_issues` | JQL for Polarion test case ID |
| Feature story found | `get_issue` | Read story, acceptance criteria, linked PRs |
| Subsystem identified | `read_neo4j_cypher` | Get all components in subsystem |
| Feature stories by component | `search_issues` | JQL by component/subsystem |
| POR or Epic linked | `get_issue` | Read POR for planned behavior |
| Any classification | `search_issues` | JQL for related bugs |
| Polarion test context | `get_polarion_test_case_summary` | Test case expected behavior |
| Need test steps | `get_polarion_test_steps` | Step-by-step test procedure |

## Tiered Playbook (B8)

Investigations escalate through tiers based on clarity of the failure:

### Tier 0: Extracted Context Only
Sufficient for clear cases:
- `console_search.found=false` with no recent changes -> AUTOMATION_BUG
- `hooks.afterAll.failed=true` with prior failure -> NO_BUG
- `assertion_analysis.has_data_assertion=true` with clear expected vs actual

### Tier 1: + MCP Selector Verification
When Tier 0 is ambiguous:
- Use acm-source MCP `search_code` to verify selector in official source
- Use acm-source MCP `search_translations` to verify UI text
- Use acm-source MCP `get_component_source` to read the component

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

**B5/B5b is MANDATORY** when cluster access is available -- always check pod health for the failing test's backend component:
```bash
oc get pods -n <ns> | grep <component>
```

### Tier 4: + Cross-System
For complex cases:
- jira MCP: search for known bugs matching the pattern
- polarion MCP: read test case expected behavior
- neo4j-rhacm MCP: query component dependencies
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
