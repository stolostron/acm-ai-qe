# Output Format and Reporting

The agent produces structured health reports whose format varies based on the
depth level and investigation type. This document covers the report structure,
verdict system, and output conventions.

---

## Overview

```
  Depth Level                    Output Format
  ────────────────────────────────────────────────
  Quick Pulse ──────────────►  Compact table + verdict
  Standard Check ───────────►  Full health report
  Deep Audit ───────────────►  Full health report + deep findings
  Targeted Investigation ───►  Narrative format
```

---

## Verdict System

Every health report opens with an overall verdict:

| Verdict | Meaning | Criteria |
|---------|---------|----------|
| **HEALTHY** | Hub is operating normally | All components OK, all nodes Ready, managed clusters Available |
| **DEGRADED** | Hub is partially functional | One or more components have warnings, non-critical issues present |
| **CRITICAL** | Hub has significant issues | Core component failure, nodes NotReady, MCH not Running |

### Per-Component Verdicts

Each component gets an individual status:

| Status | Meaning |
|--------|---------|
| **OK** | All pods Running, healthy conditions, no anomalies |
| **WARN** | Minor issue: high restart count (but stable), non-critical degradation, pending state |
| **CRIT** | Failure: pods CrashLooping, critical condition False, functionality impaired |

The overall verdict is derived from individual component verdicts:

```
  All OK                           ──► HEALTHY
  Any WARN, no CRIT                ──► DEGRADED
  Any CRIT                         ──► CRITICAL
```

---

## Standard Health Report Format

Used for standard checks and deep audits:

```markdown
# Hub Health Report: <cluster-name>
## Overall Verdict: HEALTHY | DEGRADED | CRITICAL

## Summary
<2-3 sentence executive summary of hub state>

## Component Status
| Component | Status | Details |
|-----------|--------|---------|
| MCH       | OK/WARN/CRIT | Phase, version, condition message |
| MCE       | OK/WARN/CRIT | Phase, version |
| OCP       | OK/WARN/CRIT | Version, upgrade status |
| Nodes     | OK/WARN/CRIT | X Ready, Y total |
| Managed Clusters | OK/WARN/CRIT | X Available, Y total |
| <component> | OK/WARN/CRIT | Component-specific details |
| ...       | ...    | ... |

## Issues Found (if any)
### [SEVERITY] <issue title>
- **What**: Description of the problem
- **Evidence**: Tier 1/2 evidence that supports this conclusion
- **Root Cause**: Best assessment with confidence level
- **Layer**: Diagnostic layer (e.g., Layer 7 → Layer 9)
- **Known Issue**: JIRA reference, or "No match"
- **Fix Version**: ACM version with fix, or "N/A"
- **Cluster-Fixable**: Yes / Workaround / No
- **Impact**: What is affected
- **Recommended Action**: What to do (fix, upgrade, workaround)

## Cluster Overview
- **ACM Version**: X.Y.Z
- **OCP Version**: X.Y.Z
- **MCH Namespace**: <namespace>
- **Nodes**: X Ready, Y total (roles breakdown)
- **Managed Clusters**: X Available, Y total
- **Enabled Components**: comma-separated list
```

### Component Status Table

The component status table is the core of every standard report. Components
included depend on what's deployed:

```
  Always Present                  If Deployed
  ────────────────────────────────────────────────
  MCH                             Observability
  MCE                             Search
  OCP                             Governance (GRC)
  Nodes                           App Lifecycle
  Managed Clusters                Console
  ACM CSV                         Cluster Backup
  MCE CSV                         Fine-Grained RBAC
                                  Submariner
                                  Volsync
                                  SiteConfig
                                  CNV/MTV Integrations
```

---

## Quick Pulse Output

For `/sanity` checks, the output is compact -- just the component table,
cluster overview, and verdict. No issue details unless something is clearly
wrong.

```markdown
# Hub Health Report: <cluster-name>
## Overall Verdict: HEALTHY

## Component Status
| Component | Status | Details |
|-----------|--------|---------|
| MCH | OK | Phase: Running, v2.16.0 |
| MCE | OK | Phase: Available, v2.11.0 |
| OCP | OK | v4.21.5, not progressing |
| Nodes | OK | 6/6 Ready |
| Managed Clusters | OK | 2/2 Available |
| ACM CSV | OK | Succeeded |
| MCE CSV | OK | Succeeded |

## Cluster Overview
- **ACM Version**: 2.16.0
- ...
```

---

## Targeted Investigation Output

For `/investigate <target>` or natural language targeted requests, the output
uses a narrative format instead of the standard report:

```markdown
# <Target> Investigation

## What Was Checked
<List of specific resources, pods, logs, and configurations examined>

## What Was Found
<Detailed description of the current state>

## Issues Found (if any)
### [SEVERITY] <issue>
- **What**: ...
- **Impact**: ...
- **Root Cause**: ...
- **Recommended Action**: ...

## <Target>-Specific Details
<Subsystem-specific information: pod table, storage details,
addon status, log excerpts, etc.>

## Bottom Line
<1-2 sentence summary of the target's health>
```

### Investigation-Specific Sections

Different targets produce different detail sections:

| Target | Specific Sections |
|--------|-------------------|
| Observability | Pod inventory (35+ pods), PVC listing, Thanos component status, S3 config, metrics pipeline verification, route listing |
| Search | Search pod status, postgres storage, search-collector addon status per cluster |
| Managed Clusters | Per-cluster status, lease renewal, addon status per cluster |
| Governance | Policy summary, propagator status, per-cluster compliance |
| Console | Console pod status, ConsolePlugin CRs, route accessibility |

---

## Issue Severity Levels

Issues found during the health check are tagged with severity:

| Severity | Tag | Criteria |
|----------|-----|----------|
| Critical | `[CRITICAL]` | Core functionality impaired, data loss risk, immediate action needed |
| Warning | `[WARNING]` | Degraded but functional, potential future issue, non-critical anomaly |
| Info | `[INFO]` | Notable observation, cosmetic issue, historical artifact |

### Issue Detail Fields

Each issue includes nine fields. All fields are required -- use "N/A" or
"No match" when a field does not apply rather than omitting it.

| Field | Content | When Included |
|-------|---------|--------------|
| **What** | Factual description of what was observed | Always |
| **Evidence** | Tier 1/2 evidence supporting the conclusion | Always |
| **Root Cause** | Best assessment with confidence level | Always |
| **Layer** | Diagnostic layer identification (e.g., "Layer 7 (RBAC) → Layer 9 (pod crash)") | Always |
| **Known Issue** | JIRA reference (ACM-XXXXX), or "No match" | Always |
| **Fix Version** | ACM version containing the fix, or "N/A" | Always |
| **Cluster-Fixable** | Yes / Workaround / No -- resolved on-cluster, workaround exists, or needs upgrade | Always |
| **Impact** | What is affected by this issue (scope, downstream effects) | Always |
| **Recommended Action** | Specific remediation steps the user can take | Always |

When cluster-fixable issues are found, the agent presents a structured
remediation plan after the health report (see below). Fixes are only
executed after the user explicitly approves the plan.

---

## Uncertainty Handling

The agent is honest about uncertainty in its findings:

| Confidence Level | Phrasing |
|-----------------|----------|
| High confidence | "This is caused by X" |
| Medium confidence | "This is likely caused by X, based on Y evidence" |
| Low confidence | "This might indicate X, but I'd need to verify Y to confirm" |
| Insufficient evidence | "I can see X but don't have enough information to determine the cause" |

The agent never fabricates certainty. If logs have aged out, if events are
missing, or if the evidence is ambiguous, the report says so.

---

## Output Conventions

### Command References

When describing what was checked, the agent cites specific commands:
```
Checked: oc get pods -n open-cluster-management-observability | grep thanos-store
```

### Restart Count Interpretation

The agent interprets restart counts in context:

| Pattern | Interpretation |
|---------|---------------|
| 0 restarts | Normal |
| 1-3 restarts, pod currently Running, recent creation time during maintenance | Normal (upgrade/restart) |
| High restarts, pod currently Running, stable for days | Historical issue, self-recovered |
| High restarts, pod currently CrashLooping | Active issue |

### Namespace Awareness

Reports always note the actual MCH namespace when it differs from the default:
```
- **MCH Namespace**: `ocm`  (not the default `open-cluster-management`)
```

### Addon Status Interpretation

Addon status conditions are interpreted as a whole, not individually:

| Available | Degraded | Progressing | Interpretation |
|-----------|----------|-------------|---------------|
| True | False | False | Healthy |
| True | True | False | Functional but has a non-blocking issue |
| False | True | False | Unhealthy, investigate |
| False | False | True | Still deploying |

---

## Remediation Plan Format

When the health report includes cluster-fixable issues, the agent appends a
remediation plan after the report. Each fix includes root cause, evidence,
the exact command to run, and risk level. Issues that require an ACM upgrade
or infrastructure change are listed separately.

The agent waits for explicit user approval before executing any fixes. After
executing approved fixes, it runs a quick verification check and reports
before/after status for each affected component.

See the Remediation Protocol section in [CLAUDE.md](../CLAUDE.md) for the
exact format and 5-step approval flow.

---

## See Also

- [01-DEPTH-ROUTER.md](01-DEPTH-ROUTER.md) -- how depth determines output format
- [02-DIAGNOSTIC-PIPELINE.md](02-DIAGNOSTIC-PIPELINE.md) -- what each phase produces
- [00-OVERVIEW.md](00-OVERVIEW.md) -- top-level overview
