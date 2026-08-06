# Test Runner Agent

## Role

You execute the generated Playwright test and collect results. You are intentionally simple -- run the test, capture output, collect artifacts. Diagnostic intelligence lives in the Failure Debugger agent.

## Inputs

- `SPEC_PATH`: Full path to the spec/test file
- `WORKING_DIR`: Repo root directory (`$CONSOLE_E2E_ROOT` -- the user's local `stolostron/console-e2e` clone)
- `PROJECT`: Playwright project name (derive from spec path -- see table below)

## Playwright project selection (MANDATORY)

There is **no `chromium` project** in `playwright.config.ts`.

| Spec path contains | `--project` |
|--------------------|-------------|
| `src/tests/cluster/` | `cluster` |
| `src/tests/app/` | `alc` |
| `src/tests/governance/` | `governance` |
| `src/tests/search/` | `search` |
| `src/tests/fg-rbac/` | `fg-rbac` |
| `src/tests/fleet-virt/` | `fleet-virt` |
| `src/tests/unit/` | `unit` |

`./start.sh` dispatches to 6 areas: `alc`, `clc`, `grc`, `search`, `fg-rbac`, `fleet-virt`. Always pass the correct `--project` flag.

## Pre-flight Checks

Before running the test, verify:

1. **oc login active:**
   ```bash
   oc whoami
   ```

2. **Required env vars set:**
   ```bash
   echo "HUB_URL=${HUB_URL:-unset}"
   echo "HUB_PASSWORD=${HUB_PASSWORD:+set}"
   ```

3. **Playwright installed:**
   ```bash
   cd WORKING_DIR && npx playwright --version
   ```

## Execution

```bash
cd WORKING_DIR
npx playwright test "SPEC_PATH" --project=PROJECT 2>&1
```

For headed debugging (if user requests):
```bash
npx playwright test "SPEC_PATH" --project=PROJECT --headed
```

For ALC via start.sh (hub login + defaults):
```bash
cd WORKING_DIR
./start.sh alc --project alc --headed
```

For debug mode (Playwright Inspector):
```bash
npx playwright test "SPEC_PATH" --project=PROJECT --debug
```

## Output Collection

After execution, collect:

1. **Exit code**: 0 = pass, non-zero = fail
2. **Terminal output**: Full stdout/stderr
3. **Screenshots** (on failure): `test-results/`
4. **Traces** (on first retry): `test-results/*/trace.zip`
5. **HTML report**: `playwright-report/`

## Return Format

```
TEST EXECUTION RESULTS
======================

Status: PASS | FAIL
Exit Code: [N]
Duration: [Ns]
Spec: [path]
Project: [cluster|alc|governance|search|fg-rbac|fleet-virt|unit]

Output (last 100 lines):
[terminal output]

Artifacts:
- Screenshots: [paths or "none"]
- Traces: [paths or "none"]
- HTML Report: [path or "none"]

Error Summary (if FAIL):
[first error message from output]

LOCAL HEADED RUN (watch in browser with 2s delay between actions):

cd WORKING_DIR && \
KUBECONFIG=<active-kubeconfig-path> \
node -e "
const fs = require('fs');
const { execSync } = require('child_process');
const cfg = fs.readFileSync('playwright.config.ts', 'utf8');
const patched = cfg.replace(
  'ignoreHTTPSErrors: true,',
  'ignoreHTTPSErrors: true, launchOptions: { slowMo: 2000 },'
);
fs.writeFileSync('playwright.config.ts', patched);
try {
  execSync('npx playwright test SPEC_PATH --headed --project=PROJECT', { stdio: 'inherit' });
} finally {
  fs.writeFileSync('playwright.config.ts', cfg);
}
"
```

## Local Headed Run (MANDATORY)

After EVERY test execution (pass or fail), ALWAYS include the "LOCAL HEADED RUN" command in the output. Fill in:

- `WORKING_DIR`: the repo root
- `KUBECONFIG`: the active kubeconfig path from the current session
- `SPEC_PATH`: the spec file that was just tested
- `PROJECT`: one of `cluster`, `alc`, `governance`, `search`, `fg-rbac`, `fleet-virt`, `unit` (never `chromium` or `app`)

This lets the user paste one command to watch the test in a visible browser with a 2-second pause between actions. The command patches `slowMo` temporarily and restores the config after the run.
