# Automation Data Flow

How Ansible automation hooks are triggered and monitored.

---

## Template Selection Flow

```
User opens automation template configuration
  -> frontend requests job template list
  -> GET /ansibletower/api/v2/job_templates/ (or workflow_job_templates)
    -> backend/src/routes/ansibletower.ts
      -> constructs Ansible Tower API URL from credentials
      -> proxies request to Tower
      -> returns template list
  -> frontend populates template dropdown
  -> user selects template and saves
  -> ClusterCurator CR updated with hook configuration
```

Bug injection point: ansibletower.ts can intercept the request and return
`{count:0, results:[]}` without contacting Tower. Template dropdown is empty.

## Hook Execution Flow

```
Cluster operation triggers curator hook (e.g., pre-upgrade)
  -> cluster-curator-controller detects hook trigger
    -> reads ClusterCurator spec for hook configuration
    -> constructs Ansible Tower job launch request
    -> POST to Tower API to launch job
    -> monitors job status via polling
    -> updates ClusterCurator status with result
  -> SSE event pushes status to UI
  -> Console shows automation progress
```

## Failure Points

| Point | What breaks | Symptom |
|-------|------------|---------|
| ansibletower.ts intercepts | Empty template list | "Template selection dropdown empty" |
| Tower unreachable | Hook execution fails | "Ansible posthook not triggered within time limit" |
| AAP operator missing | No Tower to connect to | Empty templates + INFRASTRUCTURE |
| ClusterCurator events dropped | Status doesn't update | Automation appears stale until refresh |
| Job template doesn't exist | Launch returns 404 | Hook fails after trigger |
