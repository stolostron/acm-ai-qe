# Testing and iteration (for this skill)

Based on Anthropic *Testing and iteration* guidance: validate **triggering**, **function**, and optionally **efficiency** whenever you change `SKILL.md`, references, `refresh-inventory.py`, or `hub_validation_gate.py`.

## 1. Triggering tests

**Should load this skill (examples):**

- "Find me an environment with ACM 2.17"
- "I need an Azure hub with ACM 2.15.2 and spokes"
- "Refresh the environment inventory"
- "Provision ACM on GCP"
- "Destroy cluster `https://api....:6443`"

**Should prefer another workflow (negative examples):**

- "What build tag is on this cluster?" → cluster introspection / `oc` on current login, not environment discovery.
- "Why did virt_console_e2e_tests fail?" → Jenkins test logs / `acm-jenkins-client` sibling skill, not this finder’s primary job.
- "Deep hub diagnostic only" → follow `../acm-hub-health-check/SKILL.md` alone, without a find/provision/destroy flow.

If the model under-triggers, add concrete verbs to the YAML `description`. If it over-triggers, tighten scope in `description` and the **Negative triggers** section in `SKILL.md`.

## 2. Functional tests

| Test | Pass criteria |
|------|----------------|
| Sheet (optional) | If Sheets access exists, rows load; else flow still works from cache/Jenkins only |
| Hub gate | `hub_validation_gate.py` exits 0 with `exit_reason: preflight_passed` when `KUBECONFIG` valid |
| Cache refresh | `refresh-inventory.py` exits 0; `inventory.json` has `entries` array |
| Dry run | `python3 .../refresh-inventory.py --dry-run` prints JSON without writing |
| Rank | Filter by `build_result == "SUCCESS"` returns plausible candidates |
| Artifact URL | When MCP is available, `get_build` lists `ocp_credentials/kubeconfig` for successful install; otherwise confirm from build JSON (REST) or UI |
| Hub check | After kubeconfig, steps in `../acm-hub-health-check/SKILL.md` Quick depth succeed (no substitute checklists) |

## 3. Metrics (aspirational)

- Fewer user round-trips vs ad-hoc Jenkins browsing for the same outcome.
- Zero remote Jenkins triggers without documented user approval in the transcript.

## 4. Iteration habit

After a failed real run, paste the failure into a **skill-creator** review request: improve troubleshooting rows and script error messages rather than growing `SKILL.md` without bound.
