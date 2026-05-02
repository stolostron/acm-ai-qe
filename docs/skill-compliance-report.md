# Agent Skills Open Standard Compliance Report

**Source:** https://agentskills.io (official Agent Skills open standard specification)
**Date:** 2026-05-01
**Scope:** All 19 skills (18 ACM + onboard) on the `skill-implementation` branch
**Purpose:** Identify strengths, gaps, and implementation instructions for each skill pack (test-case-generator, hub-health, z-stream) against the agentskills.io standard and best practices.

---

## Implementation Status

| Priority | Gap | Status | Details |
|---|---|---|---|
| P1 | Eval frameworks (evals.json) | **Implemented** | 3 orchestrator skills: acm-test-case-generator (5 evals), acm-hub-health-check (4 evals), acm-z-stream-analyzer (4 evals). Process/behavior-focused, no ticket-specific bias. |
| P2 | Gotchas in SKILL.md | **Implemented** | 5 skills added (acm-test-case-writer, acm-failure-classifier, acm-hub-health-check, acm-cluster-remediation, acm-data-enricher). Total: 9 skills with gotchas. |
| P3 | `metadata.version` | **Implemented** | All 19 skills (18 acm-* + onboard) have `metadata: { author: acm-qe, version: "1.0.0" }` in frontmatter. |
| P4 | Description triggering test | Deferred | Manual testing required. Not automatable without running Claude Code sessions. |

### Eval Design Note

Evals were redesigned from the original proposal to prevent circular overfitting. The original report proposed ticket-specific evals using ACM-30459 (7 pipeline runs) and ACM-32282 (4 pipeline runs), but these tickets were used iteratively to improve the pipeline. Using them as eval targets would test memorized answers, not skill robustness.

The implemented evals test **process compliance**, **structural validity**, **cross-area robustness**, **edge-case handling**, and **graceful degradation** — all without referencing specific tickets.

---

## Part 1: Current Strengths (What We Do Right)

### 1.1 Specification Compliance

All 19 skills fully comply with the agentskills.io specification:

| Spec Requirement | Our Status | Evidence |
|---|---|---|
| `name` field: 1-64 chars, lowercase+hyphens, matches directory | PASS | All 19 skills verified |
| `description` field: 1-1024 chars, WHAT + WHEN | PASS | All descriptions include trigger phrases |
| `compatibility` field: environment requirements | PASS | All 19 skills have it |
| `metadata.version` field | PASS | All 19 skills have `version: "1.0.0"` |
| Directory structure: SKILL.md + optional scripts/references/assets | PASS | Consistent structure across all skills |
| SKILL.md under 800 lines | PASS | Largest is ~247 lines (acm-hub-health-check with gotchas) |
| Progressive disclosure: metadata → body → references | PASS | All skills use references/ for detail |
| File references use relative paths from skill root | PASS | All reference links are relative |

### 1.2 Best Practices Compliance

| Best Practice | Our Status | Evidence |
|---|---|---|
| "Start from real expertise" | PASS | Skills extracted from 3 working apps with real production runs |
| "Refine with real execution" | PASS | Tested across multiple ACM areas and cluster configurations |
| "Design coherent units" | PASS | Each skill has a single clear purpose; composes with others |
| "Provide defaults, not menus" | PASS | Shared skills give one interface; orchestrators specify usage |
| "Favor procedures over declarations" | PASS | Steps describe HOW, not just WHAT |
| "Gotchas sections" | PASS | 9 of 19 skills have inline gotchas (all app-specific skills that need them) |
| "Templates for output format" | PASS | Output schemas in failure-classifier, report templates in hub-health |
| "Checklists for multi-step workflows" | PASS | Phase-gates.md, self-review checklists in writer/reviewer |
| "Validation loops" | PASS | Quality review + programmatic enforcement loop in TC-gen |
| "Plan-validate-execute" | PASS | Synthesis → write → review → enforce pattern |
| "Bundling reusable scripts" | PASS | gather.py, report.py, review_enforcement.py, validate_conventions.py |
| "Eval framework" | PASS | 3 orchestrator skills have evals/evals.json with bias-free assertions |

### 1.3 Cross-Platform Portability

Our skills work on 35+ platforms that support the Agent Skills standard (confirmed via agentskills.io client showcase):
- Claude Code, Claude.ai, Claude API
- Cursor, VS Code, GitHub Copilot
- Gemini CLI, OpenAI Codex
- Roo Code, Goose, Junie (JetBrains)
- Factory, Amp, OpenHands, and more

---

## Part 2: Gaps by Skill Pack

### 2.1 Test Case Generator Skills

**Eval framework:** Implemented in `acm-test-case-generator/evals/evals.json` with 5 evals covering process compliance, structural validity, cross-area robustness, missing inputs, and MCP degradation.

**Gotchas:** Implemented in `acm-test-case-writer/SKILL.md` with 5 items covering filter rule sourcing, field order assumptions, translation keys, test file mock data, and array append semantics.

**metadata.version:** Implemented in all 4 TC-gen skills.

### 2.2 Hub Health Skills

**Eval framework:** Implemented in `acm-hub-health-check/evals/evals.json` with 4 evals covering depth routing, diagnostic integrity, cluster variety, and failure handling.

**Gotchas:** Implemented in both `acm-hub-health-check/SKILL.md` (5 items: top diagnostic traps with cross-reference to full list) and `acm-cluster-remediation/SKILL.md` (5 items: common remediation mistakes).

**metadata.version:** Implemented in all 3 hub-health skills.

### 2.3 Z-Stream Analysis Skills

**Eval framework:** Implemented in `acm-z-stream-analyzer/evals/evals.json` with 4 evals covering process compliance, classification rigor, anti-anchoring, and varied failure modes.

**Gotchas:** Implemented in both `acm-failure-classifier/SKILL.md` (7 items: anchoring bias, selector+backend confusion, mock data, grouping criteria, dead selectors, layer discrepancy, test file evidence) and `acm-data-enricher/SKILL.md` (5 items: PatternFly classes, hex colors, git case sensitivity, direction field computation, schema validation).

**metadata.version:** Implemented in all 4 z-stream skills.

### 2.4 Shared Skills

**metadata.version:** Implemented in all 7 shared skills + onboard.

**Gotchas:** 4 shared skills already had gotchas (acm-jenkins-client, acm-jira-client, acm-polarion-client, acm-ui-source). Remaining shared skills (acm-knowledge-base, acm-neo4j-explorer, acm-cluster-health, acm-knowledge-learner) don't need inline gotchas — their reference files serve this purpose.

---

## Part 3: Remaining Work

| Item | Status | Notes |
|---|---|---|
| P4: Description triggering test | Deferred | Manual testing — run prompts in Claude Code and verify correct skill activation |
| Eval workspace structure | Future | Set up iteration-based eval tracking when skills reach v1.1+ |
| Token/time benchmarking | Future | Add timing and cost tracking to eval runs |

---

## Verification Commands

```bash
# All 19 have metadata.version
grep -l "version:" .claude/skills/*/SKILL.md | wc -l  # → 19

# 9 skills have gotchas (4 existing + 5 new)
grep -rl "## Gotchas" .claude/skills/*/SKILL.md | wc -l  # → 9

# 3 evals.json files exist and are valid
for f in .claude/skills/*/evals/evals.json; do python3 -m json.tool "$f" > /dev/null && echo "OK: $f"; done

# No SKILL.md exceeds 800 lines
for f in .claude/skills/*/SKILL.md; do l=$(wc -l < "$f"); [ "$l" -gt 800 ] && echo "OVER: $f ($l)"; done
```
