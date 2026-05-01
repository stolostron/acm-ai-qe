---
description: |
  Remediate diagnosed ACM hub cluster issues with a structured approval
  workflow. Proposes fixes based on diagnosis findings, executes only
  after user approval, and verifies results. Use AFTER diagnosis.
when_to_use: |
  When the user asks to fix, remediate, repair, or resolve issues found
  during diagnosis, says "yes" to a remediation plan, or asks "can you
  fix that". Never invoke during diagnosis -- diagnosis must complete first.
argument-hint: "[specific issues to fix]"
disable-model-invocation: true
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(oc get:*)
  - Bash(oc describe:*)
  - Bash(oc logs:*)
  - Bash(oc whoami:*)
  - Bash(oc adm top:*)
  - Bash(oc version:*)
  - Bash(oc patch:*)
  - Bash(oc scale:*)
  - Bash(oc rollout restart:*)
  - Bash(oc delete pod:*)
  - Bash(oc annotate:*)
  - Bash(oc label:*)
  - Bash(oc apply:*)
  - Bash(grep:*)
  - Bash(jq:*)
  - Bash(wc:*)
  - Bash(sort:*)
  - Bash(head:*)
  - Bash(tail:*)
  - Bash(awk:*)
  - Bash(cut:*)
  - Bash(cat:*)
  - Bash(ls:*)
  - Bash(find:*)
---

# ACM Cluster Remediation

Executes cluster mutations to fix diagnosed issues. Uses the
`acm-cluster-remediation` portable skill protocol. Every step is mandatory
and cannot be skipped or reordered.

## Mandatory Protocol

### Step 1: Verify Diagnosis Exists

If diagnosis findings are available in the current conversation (from the
`diagnose` or `investigate` skill), use them directly. If not, perform a
lightweight assessment first:

```bash
oc get mch -A -o yaml
oc get pods -n <mch-ns> --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers
oc get pods -n multicluster-engine --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers
```

Identify what's broken and why before proposing any fix.

### Step 2: Present Remediation Plan

Present a structured plan to the user:

```
Remediation Plan
================

Based on [diagnosis / quick assessment], the following fixes are proposed:

Fix 1: [Title]
  Issue: [What's wrong]
  Evidence: [Tier 1/2 evidence]
  Action: [Exact oc command to run]
  Risk: [Low / Medium / High]
  Expected outcome: [What should happen after]

Fix 2: [Title]
  ...

Issues NOT fixable on-cluster:
  - [Issue]: Requires ACM upgrade to [version] (JIRA: ACM-XXXXX)
  - [Issue]: Requires infrastructure change

Should I proceed? (yes/no, or specify which fixes to apply)
```

### Step 3: Wait for Explicit Approval

Do NOT proceed until the user explicitly says yes.

- "yes" -- execute all proposed fixes
- "yes, fix 1 and 3 only" -- execute only specified fixes
- "no" -- abort remediation entirely

### Step 4: Execute Approved Fixes

For each approved fix, run the command and immediately verify:

```
Executing Fix 1: [Title]
  Command: oc rollout restart deploy/search-v2-operator -n <ns>
  Result: deployment.apps/search-v2-operator restarted
  Verification: oc get pods -n <ns> | grep search-v2
  Status: [OK / FAILED]
```

If a fix fails, report the failure and STOP. Do not attempt the next fix
without user acknowledgment.

### Step 5: Post-Remediation Verification

Re-run Phase 1 (Discover) and Phase 3 (Check) on affected components.
Report before/after comparison.

## Allowed Mutations

These commands may be used (each prompts for user permission via Claude Code):

- `oc patch` -- modify resource spec/status
- `oc scale` -- adjust replica count
- `oc rollout restart` -- restart a deployment
- `oc delete pod` -- restart a pod (NOT deployment, NOT CRD)
- `oc annotate` -- add/modify annotations
- `oc label` -- add/modify labels
- `oc apply` -- apply a manifest

## Forbidden Operations (even with user approval)

- `oc delete` on non-pod resources (CRDs, namespaces, deployments, PVCs, StatefulSets)
- `oc adm drain` or `oc adm cordon`
- `oc create namespace`
- Anything that destroys data or removes infrastructure
- Any mutation during Phases 1-6 of diagnosis
