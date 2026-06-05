# 14 Diagnostic Traps

Traps are common diagnostic pitfalls where the obvious conclusion is wrong.

## Standard Traps

**Trap 1 (Stale MCH):** MCH operator at 0 replicas. MCH status says "Running" but it's stale -- the operator is not reconciling. Always check operator deployment BEFORE trusting MCH/MCE status.

**Trap 1b (Leader Election):** Operator pods Running/Ready but no leader holds the Lease. Reconciliation has stopped. Check `oc get lease -n $NS` for stale `renewTime`.

**Trap 2 (Console Tabs):** Console plugin backend pod crashes. Console tabs silently disappear. Check `oc get consoleplugins` and verify backend service pods.

**Trap 3 (Search Empty):** All search pods Running, 0 restarts. But search-postgres has 0 rows -- data was lost. Run `psql SELECT count(*)` to verify data exists.

**Trap 4 (Observability S3):** Thanos pods healthy but S3 credentials expired. No data flowing. Check thanos-store and compactor logs for S3 errors.

**Trap 5 (GRC Post-Upgrade):** Governance addon pods restarting after ACM upgrade. This is transient (settling), not broken. Compare pod ages to MCH upgrade timestamp.

**Trap 6 (Cluster NotReady):** Managed cluster shows NotReady. Check lease freshness -- klusterlet may be healthy but the lease renewal is delayed.

**Trap 7 (All Addons Down):** If ALL managed cluster addons are unavailable on ALL clusters, check addon-manager-controller pod first. One broken controller explains all addon failures.

**Trap 8 (Console Cascade):** Multiple console features broken simultaneously? Check search-api first. Many console features depend on search as a data source.

**Trap 9 (ResourceQuota):** ResourceQuota in ACM namespaces silently blocks pod scheduling. Pods can't be (re)created. ACM does NOT create ResourceQuotas -- their presence is suspicious.

**Trap 10 (Cert Rotation):** Certificate rotation failure. Pods run, APIs respond, but mutual TLS handshakes fail at connection time. Silent failure. Check cert ages and CSR status.

**Trap 11 (NetworkPolicy Hidden):** NetworkPolicy in ACM namespaces makes pods appear healthy (Running, 0 restarts) while being completely non-functional. ACM does NOT create NetworkPolicies -- their presence is suspicious.

## Counter-Traps (prevent false classifications)

**Trap 12 (Selector Doesn't Exist):** A test references a CSS selector that was NEVER in the official product source. Regardless of infrastructure state, this is an automation bug (stale test). Verify via acm-source MCP `search_code`.

**Trap 13 (Backend Wrong Data):** Backend API returns incorrect data (wrong values, missing fields). If the component is healthy and responding, this is a product code bug, not infrastructure.

**Trap 14 (Disabled Prerequisite):** A feature operator/addon is not installed, but deployment parameters indicate it SHOULD be enabled. The absence is a setup failure (infrastructure), not intentional disablement.
