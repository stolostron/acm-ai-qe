# Phase 0: Credential Resolution and MCP Availability

## Credential Resolution

Resolve console credentials via priority cascade (stop at first match):

a. **Environment variables** (highest priority): `CONSOLE_PASSWORD` or `KUBEADMIN_PASSWORD` env var is set and non-empty.

b. **oc login command in user input**: If the user's message contains an `oc login` command with `-p` flag, extract the password value. Also extract the username from `-u` flag if present (default: `kubeadmin`). Example: `oc login https://api.cluster.com:6443 -u kubeadmin -p 'WXHWj-C25aT-fQ9cF-FQFUB'`.

c. **URL + password pair in user input**: If the user provides a console or API URL alongside a string matching the kubeadmin password format (4 groups of 4-6 alphanumeric characters separated by hyphens, e.g., `WXHWj-C25aT-fQ9cF-FQFUB`), extract the password. The URL and password may appear on the same line, adjacent lines, or in the same message.

d. **Explicit label in user input**: If the user writes something like `password: VALUE`, `pw VALUE`, `credentials VALUE`, or `creds: VALUE` near a cluster URL, extract the password value.

e. **oc whoami fallback** (backend-only): If `oc whoami` succeeds, the existing session supports oc CLI validation but NOT browser auth (session tokens don't work for OAuth form login). Browser auth requires an explicit password.

If NO credentials are found: Phase 5 uses backend-only validation (oc CLI, acm-search, acm-kubectl).

Store resolved values as `CONSOLE_PASSWORD` and `CONSOLE_USERNAME` (default: `kubeadmin`) for Phase 5.

## MCP Availability Check

Before starting Phase 1, probe each MCP server with one lightweight call. Classify results by tier:

| Tier | MCP Server | Probe Call | If Unavailable |
|------|-----------|------------|----------------|
| REQUIRED | jira | `mcp__jira__get_issue(issue_key=<JIRA_ID>)` | Warn user: "JIRA MCP is unavailable. Check MCP config with /onboard. Pipeline cannot produce meaningful output without JIRA data." Ask whether to proceed with user-provided context or stop. |
| IMPORTANT | acm-source | `mcp__acm-source__list_repos()` | Warn: "ACM Source MCP is unavailable. Source verification will be skipped -- test case quality may be reduced." Proceed. |
| OPTIONAL | polarion | `mcp__polarion__check_polarion_status()` | Note silently. Existing coverage check skipped. |
| OPTIONAL | neo4j-rhacm | Skip probe | Agent files handle gracefully. |
| OPTIONAL | acm-search | Skip probe | Live validator falls back to oc CLI. |
| OPTIONAL | acm-kubectl | Skip probe | Live validator falls back to oc CLI. |
| OPTIONAL | playwright | Skip probe | Live validator uses backend-only validation. |

Each probe is ONE call with no retries. If the call errors or times out, classify the MCP as unavailable.
