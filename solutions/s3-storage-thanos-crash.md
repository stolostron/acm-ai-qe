---
title: thanos-store/compactor crash from S3 misconfiguration
symptom: "thanos-store CrashLoopBackOff, bucket operation failed, Access Denied, NoSuchBucket"
keywords: [thanos-store, thanos-compactor, CrashLoopBackOff, S3, bucket, thanos-object-storage, observability, Access Denied]
affected_versions: "ACM 2.12+"
last_verified: 2026-05-26
status: active
---

## Symptom

thanos-store, thanos-compactor, and/or thanos-receive pods in `open-cluster-management-observability` namespace are in CrashLoopBackOff. Logs show S3 connection errors: `msg="bucket operation failed"`, `err="Access Denied"`, or `err="NoSuchBucket"`. This is the most common observability deployment issue.

## Root Cause

The `thanos-object-storage` secret contains missing, incorrect, or expired S3 credentials. This can happen when:
- AWS credentials rotated but the secret was not updated
- Bucket was deleted or renamed
- Endpoint URL includes the protocol prefix (should not)
- Region mismatch between secret and actual bucket location

## Fix

```bash
# 1. Check the current secret
oc get secret thanos-object-storage -n open-cluster-management-observability -o yaml

# 2. Decode and verify the config
oc get secret thanos-object-storage -n open-cluster-management-observability \
  -o jsonpath='{.data.thanos\.yaml}' | base64 -d

# 3. Verify: bucket exists, endpoint is correct (no protocol prefix),
#    credentials are valid and not expired, region matches

# 4. If credentials need updating, patch the secret:
oc create secret generic thanos-object-storage \
  -n open-cluster-management-observability \
  --from-file=thanos.yaml=/path/to/corrected-thanos.yaml \
  --dry-run=client -o yaml | oc apply -f -

# 5. Restart affected pods
oc delete pods -n open-cluster-management-observability -l app.kubernetes.io/name=thanos-store
oc delete pods -n open-cluster-management-observability -l app.kubernetes.io/name=thanos-compactor
```

## References

- Knowledge DB: `.claude/knowledge/health/observability/known-issues.md` (issue #4)
- Severity: High (total historical query outage)
