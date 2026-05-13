# Hub validation gate (`scripts/hub_validation_gate.py`)

## Why this exists

Agents sometimes **shortcut** hub validation with a few ad-hoc `oc` commands. That bypasses the **authoritative** procedure in `../acm-hub-health-check/SKILL.md`.

This script is a **preflight + handoff contract**:

- It **does not** replace the hub skill (no duplicated diagnostics).
- It **does** give a deterministic, machine-readable checkpoint before the agent opens the hub skill.

## When to run

During **Mode 1 Step F** (and **Mode 2 After success**), **after** kubeconfig is downloaded and `KUBECONFIG` is exported, **before** reading `../acm-hub-health-check/SKILL.md`.

**Recommended invocation** (from repository clone root):

```bash
python3 "$(git rev-parse --show-toplevel)/.claude/skills/acm-environment-finder/scripts/hub_validation_gate.py"
```

**Alternative:** `SKILL_DIR` = absolute path to the `acm-environment-finder` folder (the directory that contains this skill’s `SKILL.md`):

```bash
python3 "${SKILL_DIR}/scripts/hub_validation_gate.py"
```

The script resolves the sibling hub skill using **`__file__`**, so you may also call it with an **absolute path** to `hub_validation_gate.py` from any working directory, as long as the script file still lives under `.../acm-environment-finder/scripts/` in an intact clone.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Sibling hub skill exists; `oc` works; with default flags, `KUBECONFIG` authenticates. Proceed to hub skill **Quick** depth. |
| 2 | `../acm-hub-health-check/SKILL.md` missing — incomplete clone or `hub_validation_gate.py` not from this skill tree. |
| 3 | `oc` missing, `KUBECONFIG` unset/invalid path, `oc` timeout, or `oc whoami --show-server` failed. |

## `exit_reason` values (stdout JSON)

| Value | Meaning |
|-------|---------|
| `preflight_passed` | Gate succeeded; cluster API URL in `api_server`. |
| `hub_skill_missing` | Sibling file not on disk. |
| `oc_not_found` | `oc` binary not on PATH. |
| `oc_client_failed` | `oc version --client` failed. |
| `oc_timeout` | `oc version --client` timed out. |
| `kubeconfig_env_unset` | `KUBECONFIG` not set. |
| `kubeconfig_file_missing` | First path in `KUBECONFIG` is not a file. |
| `oc_whoami_failed` | Auth or network failure talking to cluster. |
| `oc_whoami_timeout` | `oc whoami` timed out. |
| `hub_skill_and_oc_only` | `--no-kubeconfig-required` mode; hub file + `oc` client only. |

## Stdout contract

Exactly **one JSON object** per run (pretty-printed). Key fields:

| Field | Use |
|-------|-----|
| `ok` | Boolean overall preflight result |
| `exit_reason` | Stable machine string (`preflight_passed`, `hub_skill_missing`, etc.) |
| `hub_skill_abspath` | Absolute path to open |
| `hub_skill_relative` | Stable relative path from this finder skill |
| `mandatory_next` | Human-readable instruction; same intent every run |
| `api_server` | Present when `ok` and kube checks ran |

Agents should parse **stdout JSON**; do not rely on stderr (unused in normal runs).

## Optional flags

- `--no-kubeconfig-required` — Only verify hub skill file + `oc version --client` (no cluster login). Rare; mostly for doc checks in CI without a cluster.

## Boundaries

- **Not** a health verdict: no HEALTHY/DEGRADED/CRITICAL from this script.
- **Not** a substitute for Phase 1+ of the hub skill.
- **Secrets:** The script does not print kubeconfig contents. Keep tokens out of the transcript per main `SKILL.md`.
