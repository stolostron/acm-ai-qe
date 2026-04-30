# Health Report Template

## Report Structure

```markdown
# ACM Hub Health Report

**Cluster:** <api-url>
**ACM Version:** <from MCH>
**OCP Version:** <from clusterversion>
**Date:** <timestamp>
**Depth:** Quick | Standard | Deep | Targeted
**Verdict:** HEALTHY | DEGRADED | CRITICAL

## Summary
<1-3 sentence overview>

## Issues Found

### [CRIT] <issue title>
- **What:** <problem description>
- **Evidence:** <Tier 1/2 evidence>
- **Root Cause:** <assessment + confidence>
- **Layer:** <diagnostic layer>
- **Known Issue:** <JIRA ref or "No match">
- **Fix Version:** <ACM version or "N/A">
- **Cluster-Fixable:** Yes | Workaround | No
- **Impact:** <what is affected>
- **Recommended Action:** <what to do>

### [WARN] <issue title>
<same 9 fields>

## Healthy Components
<list of components confirmed healthy>

## Diagnostic Coverage
- Layers checked: <list>
- Traps evaluated: <N>/14
- Dependency chains verified: <N>/12
- Evidence sources: <count>
```

## Verdict Rules (mechanical)

- **HEALTHY:** All components OK. No qualifiers.
- **DEGRADED:** Any component WARN, no CRIT. No qualifiers.
- **CRITICAL:** Any component CRIT. No qualifiers.

Do NOT append qualifiers like "(with N issues)". Details live in Issues Found.

## Per Issue: 9 Required Fields

Every issue MUST include all 9 fields. Use "N/A" or "No match" when not applicable. Never omit a field.

1. What
2. Evidence
3. Root Cause
4. Layer
5. Known Issue
6. Fix Version
7. Cluster-Fixable
8. Impact
9. Recommended Action
