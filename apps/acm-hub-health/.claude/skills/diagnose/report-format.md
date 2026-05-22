# Health Report Format

## Verdict Derivation

Verdict is mechanical -- do not soften or qualify:

- All component statuses OK -> `HEALTHY`
- Any component WARN, no CRIT -> `DEGRADED`
- Any component CRIT -> `CRITICAL`

Never append qualifiers like "(with N issues)" to the verdict.

## Report Template

```
# Hub Health Report: <cluster-name>
## Overall Verdict: HEALTHY | DEGRADED | CRITICAL

## Summary
<2-3 sentence executive summary>

## Component Status
| Component | Status | Details |
|-----------|--------|---------|
| MCH       | OK/WARN/CRIT | ... |
| MCE       | OK/WARN/CRIT | ... |

## Issues Found
### [SEVERITY] <issue title>
- **What**: Description of the problem
- **Evidence**: Tier 1/2 evidence
- **Root Cause**: Best assessment with confidence level
- **Layer**: Diagnostic layer identification (e.g., Layer 7 -> Layer 9)
- **Known Issue**: JIRA reference, or "No match"
- **Fix Version**: ACM version with fix, or "N/A"
- **Cluster-Fixable**: Yes / Workaround / No
- **Impact**: What is affected
- **Recommended Action**: What to do (fix, upgrade, workaround)

## Cluster Overview
- ACM Version: ...
- OCP Version: ...
- Nodes: X Ready
- Managed Clusters: X Available
- Enabled Components: list

## Remediation Plan (only if cluster-fixable issues exist)
<see remediate skill for the exact format>
```

All nine issue fields are required. Use "N/A" or "No match" when a field
does not apply rather than omitting it.

For targeted investigations, use narrative format with evidence chain
instead of the tabular health report.
