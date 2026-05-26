---
title: Governance propagator TLS certificate corrupted
symptom: "Policy creation returns 500 or propagator CrashLoopBackOff"
keywords: [propagator, CrashLoopBackOff, TLS, certificate, webhook-server-cert, policy 500, governance]
affected_versions: "ACM 2.12+"
last_verified: 2026-05-26
status: active
---

## Symptom

All policy operations fail. New policies return HTTP 500. Existing policies on spokes continue running but no updates propagate. Propagator pods are in CrashLoopBackOff.

## Root Cause

The TLS secret `propagator-webhook-server-cert` in the `ocm` namespace was corrupted. The service-CA operator manages this cert but does not auto-repair corruption -- it only rotates on schedule. While the cert is corrupted, the propagator webhook can't serve TLS and the pod crashes on startup.

## Fix

```bash
# 1. Verify the cert is corrupted
oc get secret propagator-webhook-server-cert -n ocm -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -dates

# 2. Delete the corrupted secret (service-CA will regenerate)
oc delete secret propagator-webhook-server-cert -n ocm

# 3. Restart propagator to pick up the new cert
oc delete pods -n ocm -l name=governance-policy-propagator
```

Wait 30-60 seconds for the service-CA operator to regenerate the cert and the propagator pod to restart.

## References

- Knowledge DB: `.claude/knowledge/failures/governance/failure-signatures.md` (Propagator TLS Certificate Corrupted)
- Classification: INFRASTRUCTURE (90% confidence)
