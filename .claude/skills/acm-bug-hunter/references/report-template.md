# Bug Hunt Report Template

Use this format for the final output of every bug hunt run.

```markdown
# Bug Hunt Report

## Input
- **Source**: [Polarion ID or file path]
- **Feature**: [Feature name from JIRA]
- **JIRA**: [ACM-XXXXX]
- **ACM Version**: [X.XX]
- **Feature Area**: [detected area]
- **Environment**: [cluster URL or "source-code only"]

## Executive Summary
- Dimensions analyzed: [N]/10 (N applicable, M skipped)
- Questions investigated: [N]
- Subagent interactions: [N total, N pushbacks, N fresh spawns]
- Confirmed bugs found: [N]
- Potential bugs found: [N]
- Coverage gaps identified: [N]
- Probe resources created/cleaned: [N created, N cleaned, N remaining]

## Findings (by severity)

### CONFIRMED BUGS
1. **[Dim N - Title]**
   - Question: [what was asked]
   - Evidence: [MCP tool output, code snippet, JIRA reference]
   - Confidence: [score]% | Evidence inventory: [summary]
   - Corroboration: [how orchestrator verified via different path]
   - Impact: [what could go wrong for end users]
   - Suggested action: [file JIRA bug / update test case / verify manually]

### POTENTIAL BUGS
1. **[Dim N - Title]**
   - Question: [what was asked]
   - Evidence: [what was found]
   - Confidence: [score]% | Evidence inventory: [summary]
   - Why not confirmed: [what verification is missing]
   - Suggested action: [manual verification steps]

### COVERAGE GAPS
1. **[Dim N - Title]**
   - Gap: [what the test case doesn't cover]
   - Risk assessment: [how likely this gap hides a bug]
   - Suggested action: [add test step / create new test case / accept risk]

## Dimension Analysis Summary

| Dimension | Status | Questions | Rounds | Findings |
|-----------|--------|-----------|--------|----------|
| 1. Specification Fidelity | CLEAN | 3 | 1 | 0 |
| 2. Resource Lifecycle | GAP | 2 | 2 | 1 gap |
| 3. Authorization Chain | SKIPPED | - | - | hub-admin test |
| 4. Multicluster Propagation | CLEAN | 4 | 1 | 0 |
| 5. Data Pipeline Integrity | POTENTIAL_BUG | 3 | 3 | 1 potential |
| 6. Integration Surface | CLEAN | 5 | 2 | 0 |
| 7. State & Transition Logic | CONFIRMED_BUG | 4 | 3+fresh | 1 confirmed |
| 8. Boundary & Edge Cases | GAP | 2 | 1 | 1 gap |
| 9. Failure & Recovery | CLEAN | 2 | 1 | 0 |
| 10. Observable Output | CLEAN | 3 | 1 | 0 |

## Investigation Trail
[Condensed log of every dimension investigated, questions asked, tools used, evidence found, pushback rounds, and final classification. For traceability -- anyone reviewing can trace each finding back to its evidence source.]
```
