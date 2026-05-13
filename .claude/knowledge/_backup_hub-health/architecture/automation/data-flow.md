# Automation (ClusterCurator) -- Data Flow

## End-to-End Curation Flow

```
Console UI / API                     Hub Cluster                       Spoke Cluster
─────────────────                    ───────────                       ─────────────
User sets desiredCuration     →  ClusterCurator CR updated
                                       │
                                 cluster-curator-controller
                                 watches ClusterCurator CRs
                                       │
                                 Creates K8s Job (curator-job-xxxxx)
                                       │
                              ┌────────┴────────┐
                              │   PRE-HOOK      │
                              │ Creates          │          AAP / Tower
                              │ AnsibleJob CR ──────────→  Launches playbook
                              │ Polls status  ←──────────  Returns result
                              └────────┬────────┘
                                       │
                              ┌────────┴────────┐
                              │   OPERATION      │
                              │ Reads kubeconfig │
                              │ from hub secret  │
                              │ Patches          ├───────→  ClusterVersion
                              │ ClusterVersion   │          updated
                              │ Monitors status  ←───────  Upgrade progress
                              └────────┬────────┘
                                       │
                              ┌────────┴────────┐
                              │   POST-HOOK     │
                              │ Creates          │          AAP / Tower
                              │ AnsibleJob CR ──────────→  Launches playbook
                              │ Polls status  ←──────────  Returns result
                              └────────┬────────┘
                                       │
                                 Updates ClusterCurator
                                 status conditions
                                       │
Console shows updated status  ←  SSE event via events.ts
```

---

## Flow 1: Template Selection (Console)

```
User opens automation config page
  → Console frontend requests template list
  → GET /ansibletower/api/v2/job_templates/
  → Console backend (ansibletower.ts) proxies to AAP
    → Reads AAP credentials from towerAuthSecret
    → Constructs AAP API URL
    → Proxies request to Tower
    → Returns template list as JSON
  → Frontend populates template dropdown
  → User selects template and saves
  → ClusterCurator CR updated with hook configuration
```

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| Console → ansibletower.ts | Proxy intercepts request | Template dropdown empty despite AAP healthy | Check console backend logs |
| ansibletower.ts → AAP | AAP unreachable | Template dropdown empty, backend logs show connection error | `oc logs -n <mch-ns> -l app=console-chart-console-v2 --tail=50` |
| AAP API | Auth secret invalid | 401/403 error | Check towerAuthSecret exists and is valid |
| Response → frontend | Empty results returned | Dropdown shows "No templates" | Probe AAP API directly to confirm |

---

## Flow 2: Hook Execution

```
Curator Job starts hook phase
  → Reads ClusterCurator spec for prehook/posthook config
  → Resolves towerAuthSecret for AAP credentials
  → Creates AnsibleJob CR in cluster namespace
    → AAP operator watches AnsibleJob CRs
    → Launches job template on AAP
    → Polls job status until complete
    → Updates AnsibleJob status
  → Curator Job reads AnsibleJob status
  → If success: proceeds to next phase
  → If failure/timeout: marks curation as failed
```

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| Curator → AnsibleJob CR | AnsibleJob CRD missing (AAP not installed) | Job fails immediately | `oc get crd ansiblejobs.tower.ansible.com` |
| AnsibleJob → AAP | AAP unreachable or auth failed | AnsibleJob stuck in pending | `oc get ansiblejob -n <cluster-ns>` |
| AAP execution | Playbook fails | AnsibleJob status shows failure | Check AnsibleJob status + AAP job log |
| Timeout | Hook exceeds jobMonitorTimeout | ClusterCurator condition: Job_failed | Check curator Job logs for timeout message |

---

## Flow 3: Upgrade Execution

```
Curator Job starts upgrade phase
  → Reads upgrade.desiredUpdate from ClusterCurator spec
  → Retrieves spoke kubeconfig from hub secret
    (secret: <cluster-name>-admin-kubeconfig in cluster namespace)
  → Patches spoke ClusterVersion with desiredUpdate
  → Monitors spoke ClusterVersion conditions:
    - Progressing=True → upgrade in progress
    - Available=True, Progressing=False → upgrade complete
    - Failing=True → upgrade failed
  → Loops until complete or monitorTimeout exceeded
  → Reports result in ClusterCurator status
```

### Failure modes

| Hop | What Breaks | Symptom | Detection |
|-----|------------|---------|-----------|
| Kubeconfig retrieval | Secret missing or expired | Curator Job fails at auth | `oc get secret <cluster>-admin-kubeconfig -n <cluster-ns>` |
| ClusterVersion patch | API incompatibility (OCP 4.21+) | Patch rejected | Check curator Job logs (ACM-30314) |
| Upgrade monitoring | Spoke upgrade stalls | Curator Job times out at monitorTimeout | Check spoke ClusterVersion conditions |
| intermediateUpdate | EUS hop required but not specified | Upgrade blocked by OCP | Check if intermediateUpdate needed |

---

## Data Freshness

- **Template list:** Fetched on-demand from AAP; no caching
- **ClusterCurator status:** Updated in near-real-time by curator Job
- **Console display:** Depends on SSE events; if events.ts drops
  ClusterCurator events, UI shows stale status until manual refresh
- **AnsibleJob status:** Polled by curator Job; frequency depends on
  controller implementation
