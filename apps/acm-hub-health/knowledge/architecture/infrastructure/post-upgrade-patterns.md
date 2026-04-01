# Post-Upgrade Health Patterns

After an ACM/MCE upgrade, certain behaviors are EXPECTED and resolve on their
own. This document distinguishes normal settling from actual failures.

Use this during Phase 3 (Check) and Phase 4 (Pattern Match) to avoid
reporting expected post-upgrade behavior as issues.

---

## Normal Post-Upgrade Behaviors

### 1. GRC Compliance Status Reset (5-15 minutes)

**What happens:** governance-policy-framework addon restarts on all spokes.
During restart, compliance status resets to Unknown. After restart, all
policies are re-evaluated.

**Timeline:**
- 0-2 min: Addon pods terminating on spokes
- 2-5 min: New addon pods starting, registering
- 5-10 min: Policies being re-evaluated
- 10-15 min: Compliance status should be stable

**When to escalate:** If compliance is still Unknown after 20 minutes AND
governance addon pods are Running (not restarting).

**Diagnostic:**
```bash
oc get managedclusteraddons -A | grep governance
# All should show Available within 15 min of upgrade completion
```

### 2. Addon Re-Registration Delay (5-10 minutes)

**What happens:** After MCE upgrade, addon controllers restart. Addons on
spokes need to re-register with the new controller versions.

**Affected addons:** All ManagedClusterAddons (search-collector,
governance-policy-framework, observability-controller, cluster-proxy, etc.)

**Timeline:**
- 0-3 min: Hub-side addon controllers restarting
- 3-7 min: Spoke-side agents detecting new controller, re-registering
- 7-10 min: All addons should show Available

**When to escalate:** If specific addons remain Unavailable after 15 minutes
while others have recovered.

### 3. RBAC ClusterRoleBinding Recreation (5-10 minutes)

**What happens:** Some addon ClusterRoleBindings (particularly cluster-proxy)
may need recreation after upgrade if the service account reference changed.

**Pattern:** `clusterrolebindings is forbidden: User system:serviceaccount:
multicluster-engine:cluster-proxy cannot update`

**This error in the FIRST 10 minutes after upgrade is NORMAL.** The addon
controller recreates the binding. Only escalate if it persists beyond 15 min.

### 4. MCH/MCE CR Status Transition (2-5 minutes)

**What happens:** During upgrade, MCH phase transitions:
Running -> Updating -> Running (or Installing -> Running for MCE).

**Expected conditions during upgrade:**
- ComponentsNotReady (temporary while pods restart)
- Progressing (normal during upgrade)

**When to escalate:** If MCH/MCE stays in Updating/Progressing for more than
30 minutes, or if it transitions to a failed state.

### 5. Image Pull Delays (5-20 minutes)

**What happens:** New ACM images need to be pulled on all nodes running ACM
pods. In air-gapped or bandwidth-constrained environments, this can take
significant time.

**Signals:** Pods in ImagePullBackOff or ContainerCreating for extended periods.

**When to escalate:** If ImagePullBackOff persists beyond 20 minutes -- likely
a registry authentication or image availability issue, not just slow pull.

### 6. Search Re-Collection After Postgres Restart (10-30 minutes)

**What happens:** If search-postgres pod was restarted during upgrade (uses
emptyDir, not PVC), all search data is lost. Collectors on all spokes need
to re-send their data.

**Timeline depends on fleet size:**
- 10 managed clusters: ~5 minutes
- 50 managed clusters: ~15 minutes
- 200+ managed clusters: ~30 minutes

**Signals:** Search returns empty results but all search pods are Running.
This is expected and resolves itself.

---

## How to Distinguish Normal Settling from Real Issues

| Signal | Normal Settling | Real Issue |
|--------|----------------|------------|
| Pods restarting | 1-2 restarts in first 10 min | Continuous restarts (CrashLoopBackOff) |
| Status Unknown | First 15 min after upgrade | Persists beyond 20 min |
| ImagePullBackOff | First 10 min (pulling new images) | Persists beyond 20 min |
| API errors in logs | Transient during transition | Persistent after pods stabilized |
| Compliance non-compliant | First 15 min (re-evaluation) | Persists with addon pods healthy |

## Key Diagnostic: Check Operator Pod Age

The most reliable indicator that an upgrade is still settling:

```bash
# If operator pods are younger than 15 minutes, settling is expected
oc get pods -n <mch-ns> -l name=multiclusterhub-operator \
  -o jsonpath='{.items[0].metadata.creationTimestamp}'
```

If the operator pod is older than 30 minutes and issues persist, they are
NOT settling -- investigate as real issues.
