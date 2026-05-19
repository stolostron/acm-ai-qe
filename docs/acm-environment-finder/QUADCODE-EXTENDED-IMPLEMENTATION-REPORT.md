# Quadcode handoff: portable hub preflight gate (`acm-environment-finder`)

**Audience:** Quadcode / platform engineers integrating **any** agent or automation host that loads this repository’s skill pack from disk (CI, internal runners, IDE agents, headless workers).  
**Not scoped to:** a single vendor IDE or runtime; this document is **host-agnostic**.

**Repository:** `ai_systems_v2`  
**Skill path (in repo):** `.claude/skills/acm-environment-finder/`  
**Skill version:** `1.1.1` (`SKILL.md` metadata)  
**Re-analysis (this revision):** Normative invocation docs were corrected to **not** assume `CLAUDE_SKILL_DIR` or any Claude-branded environment variable. Canonical instructions use **repository root** (`git rev-parse --show-toplevel`) or a **host-defined** `SKILL_DIR` pointing at the finder skill folder.

---

## 1. Executive summary

The portable skill pack adds **`scripts/hub_validation_gate.py`**: a **stdlib-only Python** preflight that emits **one JSON object on stdout** and stable **exit codes**, immediately before the agent must execute **`../acm-hub-health-check/SKILL.md`** (Quick depth by default).

The gate:

- Confirms the **sibling hub skill file exists** (packaging / clone integrity).
- Confirms **`oc`** is available.
- With default flags: confirms **`KUBECONFIG`** is set, the first path is a **regular file**, and **`oc whoami --show-server`** succeeds.

It does **not** perform ACM hub diagnosis. That remains **only** in `acm-hub-health-check`.

---

## 2. Why this exists (agent behavior)

| Problem | Effect |
|---------|--------|
| Prose-only “open the hub skill” | Soft constraint; models may substitute a short `oc` checklist. |
| No structured handoff | Hosts cannot branch deterministically on success/failure. |
| Duplicating hub logic in the finder | Two sources of truth; drift and false “healthy” signals. |

The gate adds a **cheap, machine-checkable step** that does **not** duplicate hub phases.

---

## 3. Repository layout (language-agnostic)

The directory name **`.claude/skills/`** in this repo follows the common **Anthropic-style** layout for markdown + asset skills shipped **inside a git repository**. Quadcode may:

- Consume skills **directly from clone** (recommended for fidelity), or
- Copy/symlink this subtree into another packaging root, **preserving** sibling layout: `acm-environment-finder/` next to `acm-hub-health-check/`.

The gate script resolves `../acm-hub-health-check/SKILL.md` from **`Path(__file__).resolve().parent.parent`**, so the **path to the `.py` file on disk** must remain under `acm-environment-finder/scripts/` relative to the rest of the pack.

---

## 4. Normative invocation (no vendor env vars)

### 4.1 Recommended (CI, humans, generic agents)

From the **clone root** of `ai_systems_v2`:

```bash
export KUBECONFIG=/path/to/session-kubeconfig   # team policy: unique path per session
python3 "$(git rev-parse --show-toplevel)/.claude/skills/acm-environment-finder/scripts/hub_validation_gate.py"
```

Same pattern applies to **`refresh-inventory.py`**.

### 4.2 Alternative (host supplies skill root)

If the integration layer already knows the absolute path to the finder skill directory (the folder containing `SKILL.md`):

```bash
export SKILL_DIR=/absolute/path/to/acm-environment-finder
python3 "${SKILL_DIR}/scripts/hub_validation_gate.py"
```

`SKILL_DIR` is a **generic placeholder name** in documentation; Quadcode may map it to whatever their runner exports. It is **not** required to match any upstream product’s internal variable name.

### 4.3 Absolute path to the script

Because resolution uses `__file__`, invoking:

```bash
python3 /abs/path/.../acm-environment-finder/scripts/hub_validation_gate.py
```

is valid **from any working directory**, provided the rest of the clone (including `acm-hub-health-check/SKILL.md`) is intact at the expected relative location.

---

## 5. Success and failure contract

### 5.1 Success

- Exit code **0**
- Stdout parses as JSON with `ok: true` and `exit_reason: "preflight_passed"` (when kube checks run).
- Next step for the agent: **load** `hub_skill_abspath` from JSON and execute **`acm-hub-health-check`** at **Quick** unless the user explicitly requests deeper analysis **inside that skill**.

### 5.2 Failure

- Exit **2**: sibling hub `SKILL.md` missing (broken tree or wrong artifact).
- Exit **3**: `oc` missing, kubeconfig unset/invalid, auth failure, or timeout.
- Parse stdout JSON for `exit_reason` and optional `hint`. **Do not** rely on stderr for the contract (reserved; typically empty).

**Hard rule:** Do not recommend a hub candidate if the gate failed for that kubeconfig.

---

## 6. CI / packaging mode

```bash
python3 "$(git rev-parse --show-toplevel)/.claude/skills/acm-environment-finder/scripts/hub_validation_gate.py" --no-kubeconfig-required
```

Verifies hub sibling + `oc version --client` only (no cluster). Use in pipelines that lack live clusters.

---

## 7. Why Python (stdlib)

- Single JSON object on stdout without requiring `jq`.
- `subprocess` timeouts on `oc` (`--oc-timeout`, default 45s).
- Same dependency policy as **`refresh-inventory.py`** (no extra pip packages).
- Runs the same from **CI shells**, **local terminals**, or **agent tool runners** that can execute a process.

---

## 8. Quadcode implementation checklist

1. **Runner wiring:** After kubeconfig is written and `KUBECONFIG` exported, invoke the gate; gate exit **0** is a **hard prerequisite** before loading `acm-hub-health-check/SKILL.md`.
2. **Parser:** Treat stdout as UTF-8 text containing **exactly one** JSON object (pretty-printed with newlines is fine; parse as JSON, not line-based).
3. **Telemetry (optional):** Histogram of `exit_reason` to split clone errors vs auth vs timeouts.
4. **PR CI:** Run `--no-kubeconfig-required` when PRs touch `acm-environment-finder/` or `acm-hub-health-check/`.
5. **Mirrors:** If skills are vendored outside this repo, preserve **directory siblings** so `../acm-hub-health-check` from the finder folder still resolves.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Confusing gate `ok` with “hub healthy” | JSON field `mandatory_next` and docs: gate ≠ diagnosis. |
| Wrong packaging layout | Exit 2 + `hub_skill_missing`; CI smoke catches early. |
| Secret leakage in logs | Gate never reads kubeconfig file into stdout; operators must not paste tokens in transcripts (see main `SKILL.md`). |

---

## 10. Changelog vs prior draft of this report

| Prior issue | Correction |
|-------------|------------|
| Examples used `CLAUDE_SKILL_DIR` | Removed from normative paths; **git-based** and **`SKILL_DIR`** patterns only. |
| “Claude Code, CI, and local shells” in rationale | Replaced with **host-agnostic** wording. |
| Implied a single product runtime | Clarified: **any** host that can run `python3` + `oc`. |

---

## 11. Artifact manifest

| Path | Role |
|------|------|
| `.claude/skills/acm-environment-finder/scripts/hub_validation_gate.py` | Preflight + JSON stdout |
| `.claude/skills/acm-environment-finder/references/hub-validation-gate.md` | Maintainer reference |
| `.claude/skills/acm-environment-finder/SKILL.md` | Orchestration; Mode 1 Step F + Mode 2 post-install |
| `.claude/skills/acm-environment-finder/references/sibling-skills.md` | Gate → hub ordering |
| `.claude/skills/acm-environment-finder/references/testing-and-metrics.md` | Functional test expectations |

---

## 12. Reviewer sign-off

- [ ] Gate stdout is valid JSON on pass and fail.  
- [ ] No vendor-specific env var required for documented “recommended” path.  
- [ ] `acm-hub-health-check/SKILL.md` exists beside finder in canonical layout.  
- [ ] `SKILL.md` version matches this report (`1.1.1`).
