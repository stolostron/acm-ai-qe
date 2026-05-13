# Automation (Ansible) Architecture

The Automation subsystem integrates ACM with Ansible Automation Platform (AAP)
for pre/post cluster lifecycle hooks via ClusterCurator resources.

---

## Components

| Component | Type | Namespace | Role |
|-----------|------|-----------|------|
| cluster-curator-controller | Hub deployment | ocm | Orchestrates Ansible pre/post hooks |
| AAP operator (external) | OLM subscription | openshift-operators | Ansible Automation Platform |

## Prerequisites

- `cluster-lifecycle` enabled in MCH (enables ClusterCurator)
- AAP operator installed via OLM (subscription in openshift-operators)
- Ansible Tower/AWX accessible from the hub cluster
- Job templates configured in Tower (e.g., 'Demo Workflow Template')

## ClusterCurator Workflow

```
User configures automation template for a cluster
  -> ClusterCurator CR created/updated
  -> cluster-curator-controller watches for curator events
    -> evaluates pre/post hooks
    -> calls Ansible Tower API to execute job template
    -> monitors job status
    -> reports completion/failure
  -> Console UI shows automation status
```

## Console Integration

Automation pages: within cluster details, automation templates tab.
The console proxies Ansible Tower API calls through `backend/src/routes/ansibletower.ts`.
Template dropdown is populated from Tower's job template list API.

SSE events: ClusterCurator events are delivered to the UI via events.ts.
If ClusterCurator events are dropped, automation status appears stale.

## Known Failure Modes

- **ansibletower.ts returns empty results**: Console proxy intercepts Tower API calls and returns `{count:0, results:[]}` without contacting Tower
- **ClusterCurator SSE events dropped**: events.ts filters out ClusterCurator events, automation status doesn't update in real-time
- **AAP operator not installed**: Template dropdown is empty because there's no Tower to query
- **Tower connectivity**: Tower host unreachable, job template doesn't exist
