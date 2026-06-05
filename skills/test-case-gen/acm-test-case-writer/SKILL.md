---
name: acm-test-case-writer
description: >-
  Use ONLY when a Polarion-style ACM Console test case markdown must be authored from
  ALREADY-SYNTHESIZED investigation context (JIRA + code + UI summary present in the
  thread or artifacts)—not for starting from a bare JIRA ID. For starting from JIRA,
  use acm-test-case-generator instead. TRIGGER: user explicitly asks to convert existing
  synthesis into test-case.md; Phase-6-style write with context already in hand. DO NOT
  TRIGGER: user gives only ACM-#### and expects full pipeline; user wants PR diff analysis
  only (acm-qe-code-analyzer); user wants quality review only (acm-test-case-reviewer).
disable-model-invocation: true
compatibility: "Requires acm-source MCP for spot-check verification. Uses acm-knowledge-base skill (no MCP needed)."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Test Case Writer

Produces Polarion-ready test case markdown files. Works in two modes depending on available context:

**Full context mode (via orchestrator):** Receives pre-analyzed investigation data (JIRA analysis, code analysis, UI discovery) and converts it into a formatted test case. This produces the highest quality output.

**Standalone mode (direct invocation):** If no investigation context is available in the conversation, this skill does NOT perform its own investigation. Instead:

1. Check if synthesized context (JIRA findings, code analysis, UI discovery) exists in the conversation history
2. If context IS present: proceed to write the test case
3. If context is NOT present: inform the user:

   "I need investigation context before I can write a test case. Two options:

   Option A: Run the full pipeline -- ask me to 'generate a test case for ACM-XXXXX' and the acm-test-case-generator skill will run investigation, synthesis, and writing with full context.

   Option B: Provide context manually -- give me the JIRA ticket details, PR diff summary, and the UI elements to test, and I'll write from that."

This ensures missing context is always visible. If the test case has errors, the input data was wrong -- not a hidden investigation path.

## Prerequisites

- acm-source MCP server available for spot-check verification
- Knowledge database available at `${SKILLS_DIR}/../../.claude/knowledge/`

## Process

Read `${CLAUDE_SKILL_DIR}/references/writing-process.md` for the full 6-step writing process, quality rules (step granularity, backend validation placement, implementation detail translation), self-review checklist, and gotchas.

Key steps:
1. Read conventions from `${SKILLS_DIR}/../../.claude/knowledge/conventions/`
2. Read area knowledge from `${SKILLS_DIR}/../../.claude/knowledge/ui/<area>.md`
3. Scope gate: only write steps that validate the target story's Acceptance Criteria
4. Spot-check key UI elements via acm-source MCP
4.5. Follow synthesis design optimizations and apply coverage gap triage — read `${CLAUDE_SKILL_DIR}/references/coverage-gap-handling.md`
5. Write the test case following conventions exactly
6. Self-review against the 14-point checklist

## Critical Rules

- NEVER assume UI labels -- use labels from investigation context or MCP verification
- NEVER assume navigation paths -- use routes from MCP verification
- NEVER state specific numeric thresholds unless found in PR diff, JIRA AC, MCP source, or area knowledge
- NEVER fabricate filter rules -- extract exact conditions from source code via `get_component_source`
- If investigation context is incomplete for a step, note it as "[NEEDS VERIFICATION]"
- If a filtering function is referenced, read its source via MCP and extract exact conditions -- do NOT paraphrase from the PR diff
- Always include a `## Test Steps` section header before the first `### Step N:`
