---
name: acm-jenkins-client
description: Interface to Jenkins CI for reading build status, test results, pipeline stages, console logs, and downstream trees. Use when you need to access Jenkins pipeline data, check build results, or extract test failure information.
compatibility: "Requires MCP server: jenkins (jenkins-mcp). Needs JENKINS_USER, JENKINS_API_TOKEN. Run /onboard to configure."
---

# Jenkins CI Client

Provides access to Jenkins CI via the `jenkins` MCP server. This skill exposes raw Jenkins capabilities -- reading builds, test results, pipeline stages, and console logs. It contains no app-specific workflow logic. The calling skill provides all instructions for what to extract and how to analyze results.

## Prerequisites

- Jenkins MCP server configured and connected
- VPN connection to Red Hat network (Jenkins is internal)

## MCP Tools

### Build Information
| Tool | Purpose |
|------|---------|
| `get_build(job_name, build_number)` | Get full build details (result, parameters, duration, timestamp) |
| `get_build_status(job_name, build_number)` | Quick build result check (SUCCESS, FAILURE, UNSTABLE, ABORTED) |
| `get_build_log(job_name, build_number, start, max_lines)` | Download console log (supports pagination) |
| `get_job(job_name)` | Get job configuration and recent builds |
| `get_all_jobs(folder)` | List all jobs in a folder |

### Pipeline Analysis
| Tool | Purpose |
|------|---------|
| `get_pipeline_stages(job_name, build_number)` | Get pipeline stage breakdown with status and duration |
| `get_downstream_tree(job_name, build_number)` | Get downstream build tree (parent -> child relationships) |
| `analyze_pipeline(job_name, build_number)` | AI-assisted pipeline analysis with failure identification |

### Test Results
| Tool | Purpose |
|------|---------|
| `get_test_results(job_name, build_number)` | Get JUnit test results (pass/fail/skip counts, per-test details) |
| `analyze_test_results(job_name, build_number)` | AI-assisted test result analysis with failure categorization |

### Build Triggering
| Tool | Purpose |
|------|---------|
| `trigger_build(job_name, parameters)` | Trigger a new build with parameters (use with caution) |

## Gotchas

1. **Job names include folder paths.** Use the full path: `folder/subfolder/job-name`, not just `job-name`.
2. **Build logs can be very large.** Use `start` and `max_lines` parameters for pagination. Start with the tail (last 500 lines) for error extraction.
3. **Pipeline stages may be nested.** `get_pipeline_stages` returns a flat list -- parent-child relationships are in the `id` and `parentId` fields.
4. **Test results follow JUnit format.** `failedTests` array contains `name`, `className`, `errorDetails`, `errorStackTrace`.
5. **VPN required.** Jenkins is behind the Red Hat VPN.

## Common Patterns

### Get a build's test failures
```
get_build(job_name, build_number)          -- build metadata
get_test_results(job_name, build_number)   -- JUnit results with per-test details
```

### Get console log errors
```
get_build_log(job_name, build_number, start=-500)  -- last 500 lines
```

### Trace downstream builds
```
get_downstream_tree(job_name, build_number)  -- full downstream tree
```

## Rules

- NEVER trigger builds without explicit user approval
- If the MCP is unavailable (VPN disconnected), note it and proceed without Jenkins data
