---
name: acm-cluster-remediation
description: Remediate ACM hub cluster issues with structured approval workflow. Proposes fixes based on diagnosis findings, executes approved mutations, and verifies results. Use when asked to fix, remediate, repair, or resolve ACM cluster issues.
compatibility: "Requires oc CLI logged into an ACM hub with permissions to patch, scale, and restart resources. Uses acm-hub-health-check skill for verification. Uses acm-cluster-health skill for post-fix validation."
metadata:
  author: acm-qe
  version: "1.0.0"
---

# ACM Cluster Remediation

Executes cluster mutations to fix diagnosed issues. Works with structured approval gates to ensure safety.

**Standalone operation:** This skill works independently. If invoked directly (without prior diagnosis), it performs a quick health assessment first to understand what needs fixing:

1. Run a lightweight Phase 1 (Discover) to inventory the hub
2. Check operator health, pod status, and obvious issues
3. Propose fixes based on observed problems
4. Follow the same approval and verification protocol

When invoked after a full diagnosis (via acm-hub-health-check), it receives comprehensive findings and proposes more targeted, evidence-based fixes.

## Mandatory Protocol (cannot skip or reorder)

### Step 1: Complete Diagnosis First

If diagnosis findings are available from acm-hub-health-check in the current conversation, use them. If not, perform a lightweight assessment:

```bash
oc get mch -A -o yaml
oc get pods -n <mch-ns> --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers
oc get pods -n multicluster-engine --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers
```

Identify what's broken and why before proposing any fix.

### Step 2: Present Remediation Plan

Present a structured plan to the user. Use this exact format:

```
Remediation Plan
================

Based on [diagnosis / quick assessment], the following fixes are proposed:

Fix 1: [Title]
  Issue: [What's wrong]
  Action: [Exact command to run]
  Risk: [Low / Medium / High]
  Expected outcome: [What should happen after]

Fix 2: [Title]
  ...

Issues NOT fixable on-cluster:
  - [Issue that requires external action]

Should I proceed? (yes/no, or specify which fixes to apply)
```

### Step 3: Get Explicit Approval

Do NOT proceed until the user explicitly approves. Accept:
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

### Step 5: Post-Remediation Verification

After all fixes are executed, re-run Phase 1 (Discover) and Phase 3 (Check) on affected components. Report before/after comparison.

## Allowed Mutations

These commands may be used for remediation (each prompts for user permission):

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

## Rules

- NEVER execute mutations without a complete plan presented to the user
- NEVER skip the approval step
- NEVER execute fixes during diagnosis -- diagnosis MUST complete first
- ALWAYS verify after each fix
- ALWAYS run post-remediation validation
- If a fix fails, report the failure and stop -- do not attempt the next fix without user acknowledgment

## Gotchas

1. **Delete pod, not deployment** -- `oc delete pod` restarts a single pod. `oc delete deployment` destroys the entire workload and its replica management. Always delete the pod to trigger a restart; never delete the deployment.
2. **Wait after rollout restart** -- `oc rollout restart` returns immediately but pods take 30-60 seconds to cycle. Always run `oc rollout status` or poll pod readiness before declaring the fix successful.
3. **ResourceQuota is an artifact, not a fix target** -- If a ResourceQuota is blocking pod scheduling, it was externally applied. Deleting it may fix the symptom but violates the cluster admin's intent. Report it and let the user decide.
4. **Scale to 0 then back is not the same as delete pod** -- Scaling to 0 removes ALL replicas and may trigger dependent failures (leader election loss, webhook unavailability). Prefer `oc rollout restart` for deployment restarts.
5. **Post-remediation verification must re-check dependents** -- Fixing a root cause (e.g., search-postgres) does not instantly fix dependents (search-api, console). Verify the full dependency chain, not just the fixed component.
