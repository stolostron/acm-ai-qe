# Grill with Docs, `context.md`, and Cross-Repo Documentation — Implementation Specification

**Audience:** Implementer using **Claude Code** (or any editor) inside the local clone **`ai_systems_v2/`** (see that tree’s **`README.md`** and **`git remote -v`** for upstream naming).
**Purpose:** Single authoritative document describing **how the “Grill with Docs” pattern is supposed to work**, how **`context.md`** relates to **every other doc layer** in this repo, and **exactly what to implement** so portable skills and agents behave consistently.  
**Non-goal:** This file does not replace `CLAUDE.md` for day-to-day commands; it defines **policy and integration** so those files stay aligned.

---

## Part A — Background (from the source idea)

### A.1 Original “Grill Me”

**Grill Me** is a skill pattern where the LLM **interviews the user relentlessly** until shared understanding: one question at a time, recommended answer alongside each question, systematic walk down the decision tree, contradiction surfacing, and a **Decision Summary** at the end. It does **not** assume a glossary exists; the session discovers language from scratch.

### A.2 Pain that motivated “Grill with Docs”

In long-lived codebases, the same session problems repeat:

- The user re-explains **domain jargon** every time (“standalone video”, “Stage 1.5”, “classification path”).
- The model is **verbose** because no stable term exists or the term conflicts with code.
- Agreed vocabulary **is not written down**, so the next session starts cold.

**Ubiquitous language** (Domain-Driven Design): developers, domain experts, and **artifacts** (code, tests, UI copy) should share one vocabulary. A thin glossary file (`context.md` in the video) holds that vocabulary for **this bounded context**.

### A.3 “Grill with Docs” = Grill Me + glossary + optional decision log

**Grill with Docs** keeps all Grill Me behaviors and adds:

1. **Session initialization** — Before the first grilling question, load existing shared language from agreed sources (glossary file, optional knowledge bases, optional persistent memory MCP).
2. **Language sharpening** — During the session, challenge fuzzy terms, map them to the glossary, name repeated concepts, cross-check against code (identifiers, routes, test IDs).
3. **Closing with persistence** — Decision Summary plus **Language Updates**; offer to **append** glossary and durable “why” to the right store (not mid-session without user approval).

The video also used **ADRs** for hard architectural choices. **This repo’s policy** (as of the authoring of this spec): **no required `adr/` tree**; fold short **“Repo design”** rationale into `context.md` and expand in `CLAUDE.md` / `docs/` when needed. Other repos may still use `adr/`; the skill must support **both**.

---

## Part B — Bounded contexts (do not merge layers)

This monorepo has **two distinct “knowledge” layers**. Confusing them causes duplicate or contradictory docs.

| Layer | Primary location | Subject matter | Update cadence | Consumed by |
|--------|------------------|----------------|----------------|-------------|
| **B.1 ACM product / platform knowledge** | `.claude/knowledge/` (plus optional app-local `knowledge/` for runtime YAML) | How **ACM** works: subsystems, UI routes, failure signatures, baselines, health issues | When **verified** product facts change (JIRA, cluster, upstream docs) | Z-stream gather/oracle, hub health, TC-gen investigators, classifiers |
| **B.2 Repo + tooling ubiquitous language** | Repo root **`context.md`** | What **this repository’s tools** mean: stages, phases, artifacts, enums, overloaded words, pipeline contracts | When **tooling vocabulary** or **repo structure** changes | All agents/skills working at repo root; Grill with Docs **must** read this first when present |
| **B.3 Operational “how to run” and policy** | `CLAUDE.md`, `AGENTS.md`, `README.md`, `docs/**`, app `CLAUDE.md` | Commands, MCP table, directory map, test commands, deep dives | When behavior or onboarding changes | Humans + agents for execution |

**Rule:** Do **not** move repo glossary content into `.claude/knowledge/` just to have one folder — that tree is for **ACM QE durable facts**, not “what is Stage 2” (unless the team explicitly changes policy). **Do** cross-link: `context.md` should say where ACM facts live (`.claude/knowledge/`), and the knowledge README can mention `context.md` for tooling terms.

---

## Part C — `context.md` (canonical contract)

### C.1 File placement and name

- **Path:** `ai_systems_v2/context.md` (repository root).
- **Name:** exactly `context.md` (lowercase) so skills and `CLAUDE.md` can point to a stable string.

### C.2 Required sections (structure contract)

1. **Title + one-line purpose** — e.g. “Ubiquitous Language: … Read this before touching any app.”
2. **Bounded context** — One paragraph naming the context (**ACM AI Quality Engineering** for this repo).
3. **Repo design (where “why” lives)** — Short, scannable paragraph(s) capturing **non-obvious structural choices** that would otherwise live in ADRs: pipeline split (deterministic gather vs Claude analysis vs deterministic report), schema validation gate, knowledge format (no in-repo vector store), portable skills location, `.mcp.json` policy, trace format, playbook merge strategy, **two taxonomies** (12-layer z-stream vs 10-dimension bug hunter) with pointers to the right doc/schema. **No duplicate prose** of full `CLAUDE.md`; link out for procedures.
4. **System-level entity table** — Apps, portable skill, subagent, Knowledge DB, MCP, run directory, session trace, etc.
5. **Per-app sections** — Z-stream, TC-gen, hub health: classifications, phases, key artifacts, overload disambiguation.
6. **Relationship / pipeline ASCII** — Optional but high value for agents.
7. **Known issues / gaps** — Bullet list (dead imports, version drift, dual knowledge paths) so agents do not “discover” them as new every session.

### C.3 What `context.md` must NOT contain

- Ephemeral cluster state (“bm12 is on build X”).
- Full API or function-level documentation (belongs in code/docstrings).
- A copy-paste of entire `CLAUDE.md` or long `docs/*` bodies — **link** instead.
- Unverified claims (violates team knowledge rules if mirrored into `.claude/knowledge/`).

### C.4 Maintenance rules (for humans + implementer)

- When a **term** changes or is added (new artifact name, new phase): update **tables** in `context.md` in the same PR as the code change, or immediately after.
- When **architecture** changes (e.g. new pipeline stage): update **Repo design** blurb + `CLAUDE.md` + relevant `docs/*/00-OVERVIEW.md` as needed.
- Treat `context.md` as **versioned** like code — reviewers should glance at it when PRs touch pipelines, schemas, or skill contracts.

### C.5 How other documents must reference `context.md`

| Document | Required reference pattern |
|----------|----------------------------|
| **Root `CLAUDE.md`** | Directory map line: `context.md` — ubiquitous language glossary + repo design summary — **read this first** (already present; keep when directory map changes). |
| **`AGENTS.md`** | Directory structure includes `context.md` with same meaning for tool-agnostic agents. |
| **`README.md`** | Optional one sentence in “For AI assistants” or Contributing: “See `context.md` for shared vocabulary.” |
| **Portable skill `grill-me/SKILL.md`** | Session init step 3: read repo root `context.md` if it exists. |
| **Other portable skills** (`acm-z-stream-analyzer`, `acm-test-case-generator`, etc.) | When a skill’s output uses **named artifacts or phases**, it should **not redefine** them if `context.md` exists; link or say “terms as defined in `context.md`”. |
| **App-level `apps/*/CLAUDE.md`** | If an app introduces app-specific terms, either (a) add a subsection to root `context.md` or (b) add “See root `context.md` for shared terms; app-specific: …” to avoid drift. |
| **`docs/CONTEXT-MD-SPECIFICATION.md`** | Stays the **research artifact** that led to `context.md`; update only when changing the **contract** for what `context.md` should contain. |

---

## Part D — Grill with Docs: portable skill specification

### D.1 Skill identity in this repo

- **Directory:** `.claude/skills/grill-me/` (folder name **unchanged** for portability and existing references in `CLAUDE.md`, `PORTABLE-CONSTRAINTS.md`, and team habits).
- **Canonical entry:** `.claude/skills/grill-me/SKILL.md`.
- **YAML `name` field:** `grill-with-docs` (matches semantic behavior; slash commands and docs may still say “grill me” colloquially).
- **`description`:** Must mention: Grill with Docs behavior, `context.md`, Knowledge DB path, Engram (if available), optional `adr/`, trigger phrases.

### D.2 Session initialization (mandatory order)

Before the **first** grilling question:

1. **Engram** — If the `engram` MCP is available, `engram_recall` on the topic. If MCP unavailable, **skip** and note in opening summary.
2. **Knowledge DB** — If the topic maps to an ACM subsystem, read the relevant files under **this repo’s** `.claude/knowledge/` (not `~/.cursor/...`).
3. **`context.md`** — If `context.md` exists at **repository root**, read it fully before grilling.
4. **Optional decision log** — If `adr/` or `decisions/` exists at repo root, list titles only. If absent, treat **`context.md` “Repo design”** + root `CLAUDE.md` as the decision narrative.

Then **surface** a short paragraph: which sources were loaded and one-line accuracy check with the user.

### D.3 Core behavior (unchanged from Grill Me)

- One question at a time; recommendation with each question; explore codebase instead of asking when possible; systematic tree; challenge vagueness; closing Decision Summary + open questions + “proceed to implementation?”

### D.4 Language sharpening (additive)

- Glossary conflict detection (term in `context.md` vs user’s usage).
- Forcing precision on overloaded words (documented in `context.md` “Overloaded terms” if present).
- Naming unnamed recurring concepts.
- Code cross-check (symbol names vs agreed terms).

### D.5 Closing and persistence (mandatory offers)

Output sections:

- **Decisions Resolved**
- **Language Updates** (New / Refined / Conflicts resolved)
- **Open Questions**
- **Next Steps**

Persistence ( **ask before editing files** in-session; batch at end):

1. **`engram_remember`** — when MCP available and user agrees.
2. **`context.md`** — offer updates to tables and Repo design bullets when language or structure changed.
3. **ADRs** — only if `adr/` exists **or** user explicitly requests ADR-style files; else offer **`CLAUDE.md`** or **`docs/`** updates for durable “why.”

### D.6 Modes

- **Code mode (default in repo):** codebase exploration + code cross-reference for terms.
- **General mode:** no `context.md`/code requirement; Engram still allowed; vocabulary sharpening still applies.

### D.7 Anti-patterns

Listed in canonical skill (no multi-question spam, no lecture, no mid-session file writes without permission, etc.).

---

## Part E — Canonical source of truth for the skill body (sync policy)

**Problem observed:** Cursor global skill at `~/.cursor/skills/grill-me/SKILL.md` was upgraded to **Grill with Docs**, while **`ai_systems_v2/.claude/skills/grill-me/SKILL.md` remained legacy “Grill Me”** — Claude Code launched from this repo therefore did **not** get Grill with Docs behavior from the portable skill.

**Policy to implement (choose one and document in this repo’s contributor notes):**

### Option 1 — Single canonical file in repo (recommended for `ai_systems_v2`)

- Treat **`.claude/skills/grill-me/SKILL.md` in this repository** as the **canonical** Grill with Docs definition.
- **Cursor / personal clones:** periodically **copy** from repo to `~/.cursor/skills/grill-me/SKILL.md` when the canonical file changes, **or** use the symlink workflow described in `.claude/skills/CURSOR-SYMLINK-INTEGRATION.md` if the team accepts that constraint.

### Option 2 — Canonical in global, repo is a downstream copy

- Less ideal for a **versioned product repo** because clones would not get updates from git alone.

**Implementer action:** Apply **Option 1**: replace the body of `ai_systems_v2/.claude/skills/grill-me/SKILL.md` with the same content as the current Grill with Docs spec (use the repo after merge, or copy from the latest `~/.cursor/skills/grill-me/SKILL.md` and then **commit** so git becomes source of truth).

---

## Part F — Claude Code vs Cursor (parity notes)

| Concern | Claude Code (this repo) | Cursor IDE |
|--------|--------------------------|------------|
| Skill discovery | Reads `.claude/skills/*/SKILL.md` from repo | User rules / `.cursorrules` intent table + global `~/.cursor/skills/` |
| `context.md` | Loaded when agents follow root `CLAUDE.md` + skill | Same if workspace includes repo and rules mention skill |
| Engram | Only if MCP configured in that product | Same |

**Implementer:** Do not assume Cursor behavior; ensure **repo** artifacts are correct for **Claude Code** first.

---

## Part G — Implementation checklist (for Claude Code executor)

Use this as a PR-sized task list.

### G.1 Portable skill

- [ ] Replace `.claude/skills/grill-me/SKILL.md` with **Grill with Docs** full text (session init, language sharpening, closing persistence, optional ADR section, modes, anti-patterns).
- [ ] Set YAML `name` to `grill-with-docs` and expand `description` to include “grill with docs”, `context.md`, Knowledge DB, Engram, optional `adr/`.
- [ ] Verify no broken relative references inside `SKILL.md` (use repo-relative paths only per `PORTABLE-CONSTRAINTS.md`).

### G.2 Root documentation cross-links

- [ ] Confirm root `CLAUDE.md` directory map includes `context.md` with “read this first” semantics.
- [ ] Confirm `AGENTS.md` directory structure mentions `context.md` consistently.
- [ ] Optional: one sentence in `README.md` pointing to `context.md`.

### G.3 `context.md` health

- [ ] Read full `context.md` against Part C; fill gaps if pipeline or taxonomy text drifted from code.
- [ ] Ensure “Overloaded terms” table exists and matches actual ambiguity in the codebase (Stage vs Phase, etc.).

### G.4 Other portable skills (light touch)

- [ ] Grep `.claude/skills/*/SKILL.md` for inline definitions of terms that are now in `context.md`; replace with “see root `context.md`” where appropriate (avoid duplication, not a full rewrite unless needed).

### G.5 Verification

- [ ] From repo root in Claude Code, invoke the skill (natural language: “grill with docs on X”) and confirm opening behavior includes reading `context.md` and summarizing loaded sources.
- [ ] Confirm `engram_*` steps degrade gracefully when MCP absent (no hard failure).

### G.6 Post-merge hygiene (optional)

- [ ] If using symlink to global Cursor skill, update `CURSOR-SYMLINK-INTEGRATION.md` with “grill-me skill” note.
- [ ] Announce in team channel: canonical skill is now in git; refresh local Cursor copy.

---

## Part H — Current repository state (as of authoring)

| Artifact | State |
|----------|--------|
| `context.md` | Present; includes bounded context, **Repo design** paragraph, entity tables, pipelines, known issues. |
| Root `CLAUDE.md` / `AGENTS.md` | Reference `context.md` in directory map. |
| `.claude/skills/grill-me/SKILL.md` | **Still legacy “Grill Me”** (`name: grill-me`, no session init block, no language sharpening, no persistence offers). **Requires replacement per Part G.** |
| `adr/` | **Not used**; rationale folded into `context.md` + docs. Skill must treat `adr/` as optional. |
| Global Cursor `~/.cursor/skills/grill-me/SKILL.md` | **Grill with Docs** (may differ from repo until G.1 completes). |

---

## Part I — Optional future extensions (out of scope unless requested)

- **Intent table in repo** — Claude Code does not read `.cursorrules`; if the team wants in-repo triggers, document slash commands or `CLAUDE.md` “When user says … read skill X.”
- **Second glossary** — Only if true monorepo bounded contexts multiply (unlikely here).
- **Automated check** — CI grep ensuring `analysis_results_schema.json` terms appear in `context.md` (high effort; optional).

---

## Part J — Handoff paragraph (paste into Claude Code)

```
Implement Part G of docs/GRILL-WITH-DOCS-PORTABLE-SKILL-AND-CONTEXT-SPECIFICATION.md in this repository.

Primary deliverable: replace .claude/skills/grill-me/SKILL.md with the full Grill with Docs skill (sync from the canonical text described in Part E — use the current Grill with Docs SKILL.md content as the source of truth if the repo file is still legacy).

Secondary: verify root CLAUDE.md, AGENTS.md, and context.md match Parts C and F; make minimal edits only where mismatched.

Do not reintroduce adr/ unless the user later asks. Do not edit the specification file itself unless you find factual errors while implementing.
```

---

**End of specification.**
