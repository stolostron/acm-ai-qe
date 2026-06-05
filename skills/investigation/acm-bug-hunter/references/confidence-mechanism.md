# Confidence Mechanism

Hybrid model inspired by the [ralph-orchestrator "Confession" pattern](https://github.com/mikeyobrien/ralph-orchestrator/issues/74) and [OpenAI's confessions research](https://alignment.openai.com/confessions/). Decouples investigation findings (optimized for thoroughness) from self-assessment (optimized for honesty).

## Subagent Return Format

Each dimension subagent returns TWO outputs:

### A) Investigation Findings

For each question investigated:
- **Question**: What was asked
- **Evidence**: Tool calls made, output received, code snippets found
- **Classification**: CLEAN | GAP | POTENTIAL_BUG | CONFIRMED_BUG
- **New questions**: Any questions that emerged during investigation

### B) Confidence Report (the "confession")

- **Evidence Inventory** (authoritative signal -- this is what the orchestrator trusts):
  - Source code verified: YES/NO (list which files were read)
  - API/CLI verified: YES/NO (list which commands were run)
  - Counter-case checked: YES/NO (describe what counter-evidence was sought)
  - Contradicting evidence found: YES/NO (describe any contradictions)
  - JIRA/docs cross-referenced: YES/NO
- **Self-Assessed Confidence Score**: 0-100% per finding (secondary signal)
- **Uncertainties and Assumptions**: What the subagent is NOT sure about
- **Single Easiest Item to Verify**: One concrete, verifiable claim the orchestrator can spot-check

## Orchestrator Evaluation Logic

The orchestrator uses the Evidence Inventory as the authoritative signal. The self-assessed number is a secondary gut-check:

### Case 1: Thorough evidence + high self-assessed score
Accept the finding. Move on.

### Case 2: Shallow evidence + any score
PUSHBACK. Specify exactly what checks are missing:
"You said permissions are checked, but you only verified 'create'. Check 'delete' and 'update' as well."

### Case 3: Thorough evidence + LOW self-assessed score
The subagent noticed something it couldn't articulate. Push on it:
"Your evidence looks solid but your confidence is 55%. What's bothering you?"

### Case 4: Spot-check calibration
Pick the "Single Easiest Item to Verify" from the confidence report.
- If spot-check passes -> trust the rest of the report
- If spot-check fails -> treat the entire report skeptically, pushback

## Pushback Mechanics

When the orchestrator pushes back, it resumes the SAME subagent with:
1. The specific objection (what evidence is missing or wrong)
2. Concrete instructions (which file to read, which command to run)
3. Request for an updated Confidence Report

Max 3 back-and-forth rounds. Each round should produce more evidence and increase the confidence score.

## Fresh Subagent Trigger

After 3 rounds with no convergence, spawn a FRESH subagent with:
- The original brief (same questions, same context)
- The orchestrator's specific objections and counter-evidence
- NO access to the prior subagent's reasoning (unbiased second opinion)
- Also gets max 3 rounds

Compare both subagents' evidence inventories side by side:
- Stronger evidence wins
- If tied -> report as POTENTIAL_BUG with both perspectives

## No-Cluster Confidence Adjustments

When no live cluster is available:
- Accept lower evidence inventory scores (API/CLI verified = NO is expected)
- Backend logic bugs CAN reach CONFIRMED_BUG from source code alone
- UI bugs are capped at POTENTIAL_BUG (cannot confirm without live validation)
- Do not drill more than 2 rounds per dimension
