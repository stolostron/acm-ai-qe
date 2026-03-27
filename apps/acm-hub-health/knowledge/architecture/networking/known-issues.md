# Networking -- Known Issues

Based on 34 Submariner/MCN bugs from ACM 2.12-2.17.

---

## 1. RouteAgent Race Condition (ACM-25262)

**Versions:** 2.15, 2.16 | **Severity:** Important | **Fix:** Code change (PR#3679)

RouteAgent uses `CreationTimestamp` with second granularity to detect stale
endpoint events. When two endpoint events arrive within the same second,
timestamps tie, causing incorrect stale event detection and route removal.

**Root cause:** RouteAgent compares `CreationTimestamp` to determine which
endpoint event is newer. With second-level granularity, events created in
the same second have identical timestamps. The "stale detection" logic
incorrectly marks one as stale, removing its routes.

**Signals:** Submariner shows "Degraded" status intermittently. Connectivity
flaps. RouteAgent logs show endpoint removal followed by re-addition.
Gateway pod logs show conflicting endpoint handling.

---

## 2. Submariner Breaks OCP 4.18+ (ACM-22805)

**Versions:** 2.14, 2.15 | **Severity:** Critical | **Fix:** Code change (PR#3577)

Submariner gateway connectivity fails on OCP 4.18+ due to OVN-Kubernetes
changes. The OVN network plugin made changes to how external traffic is
handled on gateway nodes.

**Root cause:** OVN-Kubernetes in OCP 4.18 changed external traffic handling.
Submariner's gateway tunnel establishment code assumes older OVN behavior for
traffic routing through the gateway node.

**Signals:** Submariner gateway shows "Connecting" but never establishes tunnel.
Gateway pod logs show connection timeouts. `subctl show connections` shows no
active connections. Clusters on OCP < 4.18 in the same cluster set work fine.

**Workaround:** Pin OCP version below 4.18 until compatible Submariner version
is deployed.

---

## 3. MCH Uninstall Hangs with Submariner (ACM-15538)

**Versions:** 2.13, 2.14, 2.15 | **Severity:** Critical | **Fix:** Code change (PR#1745)

MCH uninstallation hangs indefinitely when Submariner is deployed. ManifestWork
deletion races with submariner-addon operator cleanup.

**Root cause:** Submariner-addon cleanup creates a circular dependency:
addon operator needs to delete ManifestWork, but ManifestWork controller
waits for addon operator cleanup. Both block on each other.

**Signals:** MCH stuck in "Terminating" state. ManifestWork resources in
cluster namespaces won't delete. `oc get manifestwork -A | grep submariner`
shows stuck resources.

**Workaround:** Manually remove Submariner ManifestWork finalizers:
```bash
oc patch manifestwork <name> -n <cluster-ns> --type=merge \
  -p '{"metadata":{"finalizers":[]}}'
```

---

## 4. Orphaned iptables After nftables Migration (ACM-26965)

**Versions:** 2.16 | **Severity:** Important | **Fix:** Code change needed

When RouteAgent/GlobalNet pods migrate from iptables to nftables (as part of
OCP or Submariner upgrades), old iptables rules are not cleaned up. Orphaned
rules accumulate and can cause routing conflicts.

**Root cause:** Migration logic only installs new nftables rules but doesn't
clean up previously programmed iptables rules. The old rules remain in the
kernel's netfilter table.

**Signals:** Duplicate routing rules visible via `iptables-save` and
`nft list ruleset`. Intermittent connectivity issues after upgrade.
GlobalNet address translation may route through old rules.

**Workaround:** Manually flush orphaned iptables rules on affected nodes
(requires node SSH access and careful rule identification).

---

## 5. airGappedDeployment Setting Reverted (Recurring)

**Versions:** 2.15, 2.16 | **Severity:** Normal | **Fix:** Code change needed

`airGappedDeployment` setting in SubmarinerConfig gets reverted to `false`
by addon reconciliation. Air-gapped deployments lose their configuration
after addon reconciliation cycles.

**Root cause:** Addon reconciliation logic doesn't preserve the
`airGappedDeployment` field from SubmarinerConfig. Each reconcile cycle
resets it to the default value.

**Signals:** After reconciliation, previously working air-gapped Submariner
deployment starts pulling images from public registries. Image pull failures
on disconnected nodes.

---

## 6. Submariner Connectivity Failures on OCP 4.20+ (Ongoing)

**Versions:** 2.16, 2.17 | **Severity:** High | **Fix:** Ongoing

Continuing OVN-Kubernetes changes in OCP 4.20+ introduce additional
compatibility issues with Submariner gateway establishment.

**Signals:** Similar to ACM-22805 but on newer OCP versions. Check
Submariner version compatibility matrix before OCP upgrades.

---

## Bug Pattern Distribution

| Category | Count | Top Issues |
|---|---|---|
| Submariner connectivity | ~12 | OVN compatibility, gateway race, tunnel failures |
| RouteAgent | ~6 | Race conditions, iptables/nftables migration |
| Addon lifecycle | ~5 | MCH uninstall, airGapped config reversion |
| GlobalNet | ~4 | Orphaned rules, CIDR allocation |
| Build pipeline / Konflux | ~7 | submariner-addon EC compliance |

## Root Cause Themes

1. **OVN-Kubernetes evolution:** Each OCP release changes OVN behavior, breaking Submariner's networking assumptions
2. **Timestamp granularity:** Second-level timestamps insufficient for event ordering in fast reconciliation loops
3. **Migration cleanup:** New technology adoption (nftables) without cleaning up old technology (iptables)
4. **Circular dependencies:** Operator cleanup and ManifestWork deletion can deadlock
5. **Config persistence:** Addon reconciliation doesn't preserve non-default configuration values

## Summary

| # | Issue | Cluster-Fixable? | Severity |
|---|-------|:---:|---|
| 1 | RouteAgent race condition | No (code fix) | Important |
| 2 | Submariner breaks 4.18+ | No (code fix) | Critical |
| 3 | MCH uninstall hangs | Manual workaround | Critical |
| 4 | Orphaned iptables rules | Manual workaround | Important |
| 5 | airGapped setting reverted | Reapply after reconcile | Normal |
| 6 | Connectivity on 4.20+ | No (ongoing) | High |
