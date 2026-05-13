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

---

## 7. GlobalNet IP Allocation Exhaustion

**Versions:** All (when GlobalNet enabled) | **Severity:** High | **Fix:** Cluster-fixable

When GlobalNet is enabled with overlapping CIDRs, the GlobalNet controller
allocates GlobalIPs from a configured CIDR range. If the range is too small
for the number of services/pods requiring cross-cluster access, new services
fail to get GlobalIPs.

**Signals:** New ServiceExport CRs don't get a GlobalIngressIP assigned.
Cross-cluster connectivity works for existing services but fails for new ones.
`oc get clusterglobalegressips -A` shows CIDR utilization near capacity.

---

## 8. Service Discovery DNS Not Resolving (.clusterset.local)

**Versions:** All | **Severity:** High | **Fix:** Investigation needed

`.clusterset.local` DNS queries return NXDOMAIN despite Lighthouse and
ServiceExport/ServiceImport being configured. Root causes include:
Lighthouse CoreDNS plugin not loaded, ServiceImport not created on the
querying cluster, or CoreDNS forwarding rules missing.

**Signals:** `nslookup <svc>.<ns>.svc.clusterset.local` fails. Regular
`.svc.cluster.local` DNS works fine. ServiceExport exists on source
cluster. Check if ServiceImport was created on the destination cluster.

---

## 9. Gateway Node Label Removed After Node Replacement

**Versions:** All | **Severity:** Medium | **Fix:** Cluster-fixable

When a gateway node is drained, replaced, or scaled down by the cloud
provider's auto-scaler, the replacement node does not automatically get
the `submariner.io/gateway=true` label. The Gateway DaemonSet has 0
ready pods, and all tunnels are down.

**Signals:** `oc get nodes -l submariner.io/gateway=true` returns no nodes.
Gateway DaemonSet shows 0/0 pods. All cross-cluster connectivity lost.

**Fix:** Label a new node: `oc label node <node-name> submariner.io/gateway=true`

---

## 10. SubmarinerConfig Custom Settings Reverted After Addon Reconciliation

**Versions:** 2.14-2.17 | **Severity:** Medium | **Fix:** Code change needed

Broader instance of issue #5 (airGapped setting). The addon reconciliation
loop overwrites custom SubmarinerConfig settings beyond just the
`airGappedDeployment` field. Custom cable driver selection, gateway count,
and other tuning parameters can be reverted to defaults.

**Signals:** After reconciliation (triggered by MCH changes, addon restarts,
or periodic sync), previously configured Submariner settings revert.
Cross-cluster connectivity may break if the reverted settings are
incompatible with the environment (e.g., wrong cable driver).

---

## 11. OVN-Kubernetes Transit Switch Mode Incompatibility (OCP 4.19+)

**Versions:** 2.16+ with OCP 4.19+ | **Severity:** High | **Fix:** Ongoing

OCP 4.19+ introduces OVN-Kubernetes transit switch mode which changes
the internal routing topology. Submariner's RouteAgent assumes the
previous routing model and installs incorrect routes, causing
cross-cluster packet drops.

**Signals:** Tunnels establish successfully (Gateway shows Connected)
but actual data traffic fails. One-way connectivity or intermittent
packet loss. RouteAgent logs show route installation but traffic
doesn't flow.

---

## 12. Broker Connectivity Loss After Hub Certificate Rotation

**Versions:** All | **Severity:** High | **Fix:** Cluster-fixable

When the hub cluster's serving certificates rotate (via service-ca-operator
or manual rotation), the Broker API endpoint certificates change. Spoke
Submariner instances that have cached the old Broker CA fail to connect.
The Broker sync stops, preventing endpoint updates and service discovery
propagation.

**Signals:** Submariner tunnel health degrades gradually as spoke
clusters can't sync with Broker. New clusters can't join the
ManagedClusterSet. Broker sync logs show TLS handshake failures.

**Fix:** Re-trigger BrokerJoin on affected clusters to refresh the
Broker CA bundle.

---

## Summary

| # | Issue | Cluster-Fixable? | Severity |
|---|-------|:---:|---|
| 1 | RouteAgent race condition | No (code fix) | Important |
| 2 | Submariner breaks 4.18+ | No (code fix) | Critical |
| 3 | MCH uninstall hangs | Manual workaround | Critical |
| 4 | Orphaned iptables rules | Manual workaround | Important |
| 5 | airGapped setting reverted | Reapply after reconcile | Normal |
| 6 | Connectivity on 4.20+ | No (ongoing) | High |
| 7 | GlobalNet IP exhaustion | Yes (expand CIDR) | High |
| 8 | DNS not resolving | Investigation needed | High |
| 9 | Gateway node label removed | Yes (re-label) | Medium |
| 10 | Custom settings reverted | No (code fix) | Medium |
| 11 | OVN-K transit switch mode | No (ongoing) | High |
| 12 | Broker CA rotation | Yes (re-trigger BrokerJoin) | High |
