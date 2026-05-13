# Sibling skills (same repo, same `.claude/skills/` tree)

This pack is portable: everything a clonee needs is under the repository. Other orchestration lives next to this skill.

Paths are relative to **this** skill directory (`acm-environment-finder/`). From any shell, `SKILL_DIR` can be the directory containing this skill’s `SKILL.md`.

| Goal | Open |
|------|------|
| Hub health after kubeconfig works | `../acm-hub-health-check/SKILL.md` |
| Jenkins (MCP when host exposes it; REST in references) | `../acm-jenkins-client/SKILL.md` and `../acm-jenkins-client/references/jenkins-remote-api.md` |
| Optional: editor-global skill mirror (not required for clones) | `../CURSOR-SYMLINK-INTEGRATION.md` |

**Hub validation — no substitutes:** After `KUBECONFIG` points at a downloaded hub kubeconfig, run **`scripts/hub_validation_gate.py`** (see [hub-validation-gate.md](hub-validation-gate.md)); require exit code **0**. Then open **`../acm-hub-health-check/SKILL.md`** (Quick by default). The gate is preflight only — do not treat it as hub diagnosis, and do not replace the hub skill with ad-hoc `oc` checks or unrelated skills.

There is **no** `acm-operations` or `jenkins-expert` skill in this repository; do not reference those names in portable docs. Use [pipeline-parameters.md](pipeline-parameters.md), [provisioning-pipelines.md](provisioning-pipelines.md), and [jenkins-without-mcp.md](jenkins-without-mcp.md) instead.
