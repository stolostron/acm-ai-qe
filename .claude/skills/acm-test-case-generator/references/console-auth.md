# Headless Browser Authentication for ACM Console

Reference for authenticating to the ACM Console via form-based OAuth login using Playwright MCP tools. Used by the live-validator agent (Phase 5) before any UI validation.

## Step 1: Resolve Credentials

The orchestrator provides credentials via the subagent input block:
- `CONSOLE_USERNAME` -- the username (default: `kubeadmin`)
- `CONSOLE_PASSWORD` -- the password, or `"NONE"` if unavailable

Use these values directly. Do NOT re-check environment variables -- the orchestrator already resolved credentials from all available sources (env vars, user input, oc login commands, password patterns).

If `CONSOLE_PASSWORD` is `"NONE"`: set `AUTH_STATUS=no-credentials`, skip all browser auth steps. Backend validation (oc CLI, acm-search, acm-kubectl) still runs.

### What NOT to try

- `oc extract secret/kubeadmin` -- yields a bcrypt hash, not cleartext
- Cookie injection (`openshift-session-token` via `browser_evaluate`) -- OCP uses server-side session validation; raw tokens are rejected
- Header injection (`Authorization: Bearer` via `browser_run_code`) -- OCP requires the full OAuth authorization code flow

## Step 2: Detect IDP and Navigate

1. Discover available IDPs:
   ```bash
   oc get oauth cluster -o jsonpath='{.spec.identityProviders[*].name}'
   ```

2. Navigate to the console:
   ```
   browser_navigate(CONSOLE_URL)
   browser_wait_for(time=3)
   browser_snapshot()
   ```

3. Detect page state from the snapshot:

   | State | Signature | Action |
   |-------|-----------|--------|
   | IDP selection page | Heading "Log in with..." with links per IDP | Proceed to Step 3 (click IDP) |
   | Login form directly | `textbox "Username"` + `textbox "Password"` visible | Proceed to Step 3 (fill form) |
   | Already authenticated | Console nav elements visible (e.g., "Infrastructure") | Set `AUTH_STATUS=authenticated`, done |
   | Error / unexpected | None of the above | Set `AUTH_STATUS=failed`, record error |

## Step 3: Authenticate via Form Login

### IDP Selection (if applicable)

Click the IDP link matching the username type:

| Username | IDP Link to Click |
|----------|------------------|
| `kubeadmin` | "kube:admin" |
| HTPasswd user | Link containing "htpasswd" (case-insensitive) |
| LDAP user | Link containing "ldap" (case-insensitive) |
| Other | First IDP link as fallback |

After clicking: `browser_wait_for(time=2)` then `browser_snapshot()` to get the login form.

### Form Fill and Submit

```
browser_fill_form(ref=<username_field_ref>, value=<username>)
browser_fill_form(ref=<password_field_ref>, value=<password>)
browser_click(ref=<login_button_ref>)
browser_wait_for(time=5)
browser_snapshot()
```

### Verify Authentication

Check the post-login snapshot:
- **Success**: Console navigation elements visible (not the login page). Set `AUTH_STATUS=authenticated`.
- **Failure**: Still on login page, or error message visible. Set `AUTH_STATUS=failed`, record the error.

## Error Handling

Auth failure NEVER blocks the pipeline. The output records `AUTH_STATUS` and the pipeline continues:

| AUTH_STATUS | Meaning | Effect on Validation |
|-------------|---------|---------------------|
| `authenticated` | Login succeeded | Full UI + backend validation |
| `no-credentials` | No password env vars set | Backend-only validation (oc, acm-search, acm-kubectl) |
| `failed` | Login attempted but failed | Backend-only validation |

When not authenticated, all UI validation steps produce "SKIPPED -- browser not authenticated" but backend validation runs normally.

## Login Page Signatures (confirmed via POC)

These signatures were verified against a live OCP 4.x QE hub (generic cluster name omitted):

- **IDP selection page**: `heading "Log in with..."` followed by one link per IDP name
- **Login form**: `textbox "Username"`, `textbox "Password"`, `button "Log in"` (button disabled until both fields have values)
- **Authenticated console**: Navigation elements include items like "Infrastructure", "Governance", "Networking"
- **Common IDP names**: "kube:admin" (built-in kubeadmin), "*-htpasswd" (HTPasswd provider), "*-ldap" (LDAP provider), "*-e2e-*" (test providers)
