# Jenkins MCP Tool Reference

## Build Data Fields

A `get_build` response typically includes:
- `result`: SUCCESS | FAILURE | UNSTABLE | ABORTED | null (running)
- `building`: true/false
- `duration`: milliseconds
- `timestamp`: epoch milliseconds
- `actions`: array of build parameters, causes, test results
- `changeSet`: SCM changes

## Pipeline Stage Fields

A `get_pipeline_stages` response includes per-stage:
- `name`: stage name
- `status`: SUCCESS | FAILED | ABORTED | NOT_EXECUTED
- `durationMillis`: stage duration
- `id` / `parentId`: for nesting

## Test Result Fields

A `get_test_results` response includes:
- `totalCount`, `failCount`, `passCount`, `skipCount`
- `suites[]`: test suite groupings
- `suites[].cases[]`: individual test cases
  - `name`, `className`, `status` (PASSED/FAILED/SKIPPED)
  - `errorDetails`, `errorStackTrace` (for failures)
  - `duration`: seconds

## ACM-Specific Jenkins Patterns

### E2E Test Pipelines
ACM E2E pipelines typically:
- Run Cypress or Playwright tests against a live cluster
- Store test results as JUnit XML
- Include cluster URL, ACM version, and test suite in build parameters

### Common Build Parameters
- `DOWNSTREAM_RELEASE`: ACM version (e.g., "2.17")
- `CLUSTER_URL`: Hub cluster API URL
- `TEST_SUITE`: Which test suite to run
- `INSTALL_AAP`, `ENABLE_OBSERVABILITY`: Feature flags
