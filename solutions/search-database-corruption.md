---
title: Search database schema corruption
symptom: "ERROR: relation \"search.resources\" does not exist"
keywords: [search, postgres, resources, relation does not exist, search-postgres, database, schema]
affected_versions: "ACM 2.12+"
last_verified: 2026-05-26
status: active
---

## Symptom

Search queries fail with `ERROR: relation "search.resources" does not exist`. The search page may show empty results or error states. The search-postgres pod shows Running but the database schema is corrupted.

## Root Cause

The search-postgres database uses emptyDir storage. The schema was dropped or corrupted (possibly from an interrupted migration or OOM kill during index rebuild). Since postgres uses emptyDir, the data is ephemeral -- restarting the pod rebuilds the index from scratch, but while running the corruption persists.

## Fix

```bash
# 1. Verify the issue
oc exec -n open-cluster-management deploy/search-postgres -- \
  psql -U searchuser -d search -c "SELECT count(*) FROM search.resources"
# If this returns "relation does not exist", proceed

# 2. Restart search-postgres to rebuild the schema
oc delete pod -n open-cluster-management -l name=search-postgres

# 3. Wait for the pod to restart and the search-collector to repopulate
# (takes 2-5 minutes depending on cluster size)
oc get pods -n open-cluster-management -l name=search-postgres -w

# 4. Verify recovery
oc exec -n open-cluster-management deploy/search-postgres -- \
  psql -U searchuser -d search -c "SELECT count(*) FROM search.resources"
```

After restart, search-collector addons on all spokes will re-send their resource inventory and the index rebuilds automatically.

## References

- Knowledge DB: `.claude/knowledge/failures/search/failure-signatures.md` (Search Database Corruption)
- Classification: INFRASTRUCTURE (95% confidence)
